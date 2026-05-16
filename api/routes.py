"""
api/routes.py
-------------
FastAPI route definitions.

Endpoints:
- POST /ingest        → ingest a document
- POST /query         → run the full multi-agent RAG pipeline
- GET  /metrics       → aggregate evaluation statistics
- GET  /health        → liveness probe for Docker / k8s
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agents.orchestrator import Orchestrator
from api.schemas import (
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    IngestRequest,
    IngestResponse,
    MetadataSearchRequest,
    MetadataSearchResponse,
    MetricsRow,
    MetricsSummary,
    QueryRequest,
    QueryResponse,
    ScoresSchema,
)
from core.database import get_db
from core.vector_store import delete_by_metadata, get_qdrant_client, search_by_metadata
from ingestion.pipeline import ingest_document
from models.orm import Chunk, Document, EvalResult, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# App-level orchestrator singleton (avoid re-creating agents per request)
_orchestrator = Orchestrator()


# ── Ingest ────────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse, tags=["Ingestion"])
def ingest(payload: IngestRequest, db: Session = Depends(get_db)):
    """Ingest a document into the RAG platform.

    Loads the document from the given source, chunks and embeds it, then
    stores vectors in Qdrant and metadata in MySQL.

    - **source**: file path or URL
    - **source_type**: `pdf`, `txt`, or `url`
    - **document_name**: optional human-readable name for the document
    - **document_version**: optional version string for the document
    """
    try:
        doc = ingest_document(
            payload.source,
            payload.source_type,
            db,
            document_name=payload.document_name,
            document_version=payload.document_version,
        )
    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IngestResponse(
        document_id=doc.id,
        filename=doc.filename,
        document_name=doc.document_name,
        document_version=str(doc.version) if doc.version is not None else None,
        total_chunks=doc.total_chunks,
    )


# ── Metadata Search ───────────────────────────────────────────────────────────

@router.post("/search-by-metadata", response_model=MetadataSearchResponse, tags=["Metadata"])
def search_by_doc_metadata(payload: MetadataSearchRequest):
    """Search for stored document chunks by metadata filters.

    Use this to find all chunks from a specific document version without
    performing a semantic search.

    - **document_name**: filter by the document_name stored in vector metadata
    - **document_version**: filter by the document_version stored in vector metadata

    At least one filter is required.
    """
    if not payload.document_name and not payload.document_version:
        raise HTTPException(
            status_code=400,
            detail="At least one of document_name or document_version must be provided.",
        )

    try:
        client = get_qdrant_client()
        results = search_by_metadata(
            client,
            document_name=payload.document_name,
            document_version=payload.document_version,
        )
    except Exception as exc:
        logger.exception("Metadata search failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return MetadataSearchResponse(results=results, total=len(results))


# ── Document Delete ───────────────────────────────────────────────────────────

@router.post("/documents/delete", response_model=DocumentDeleteResponse, tags=["Metadata"])
def delete_documents(payload: DocumentDeleteRequest, db: Session = Depends(get_db)):
    """Delete document chunks from the vector store by metadata filters.

    Use this to remove old versions of a document (e.g., hr_policy_1.0) from
    the vector database before uploading a new version. Also deletes associated
    records from MySQL (documents and chunks tables).

    - **document_name**: delete all chunks with this document_name
    - **document_version**: delete all chunks with this document_version
    - **document_id**: delete all chunks with this document_id (from MySQL)

    At least one filter is required.
    """
    if not payload.document_name and not payload.document_version and not payload.document_id:
        raise HTTPException(
            status_code=400,
            detail="At least one of document_name, document_version, or document_id must be provided.",
        )

    try:
        # Step 1: Find matching documents in MySQL
        from sqlalchemy import select
        from models.orm import Document, Chunk

        doc_filter = []
        if payload.document_id:
            doc_filter.append(Document.id == payload.document_id)
        if payload.document_name:
            doc_filter.append(Document.document_name == payload.document_name)
        if payload.document_version:
            doc_filter.append(Document.version == payload.document_version)

        stmt = select(Document).where(*doc_filter)
        documents = db.execute(stmt).scalars().all()

        # Collect document IDs to delete from Qdrant
        doc_ids = [doc.id for doc in documents]

        # Step 2: Delete from MySQL (chunks + documents)
        deleted_chunks_count = 0
        if doc_ids:
            # Delete chunks first (explicit delete to get count)
            chunks_stmt = select(Chunk).where(Chunk.document_id.in_(doc_ids))
            chunks = db.execute(chunks_stmt).scalars().all()
            deleted_chunks_count = len(chunks)
            for chunk in chunks:
                db.delete(chunk)

            # Delete documents
            for doc in documents:
                db.delete(doc)

            db.commit()
            logger.info(f"Deleted {deleted_chunks_count} chunks and {len(documents)} documents from MySQL")

        # Step 3: Delete from Qdrant
        client = get_qdrant_client()
        qdrant_deleted_count = delete_by_metadata(
            client,
            document_name=payload.document_name,
            document_version=payload.document_version,
            document_id=payload.document_id,
        )

    except Exception as exc:
        logger.exception("Document deletion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DocumentDeleteResponse(
        deleted_count=qdrant_deleted_count,
        message=f"Successfully deleted {qdrant_deleted_count} chunks from Qdrant and {deleted_chunks_count} records from MySQL.",
    )


# ── Query ─────────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse, tags=["Query"])
async def query(payload: QueryRequest, db: Session = Depends(get_db)):
    """Run the multi-agent RAG pipeline for a user question.

    Retrieves relevant chunks from Qdrant, generates a grounded answer,
    evaluates the response with RAGAS, and persists all results to MySQL.

    - **question**: natural-language question
    - **ground_truth**: optional reference answer (improves context_recall score)
    """
    try:
        result = await _orchestrator.run(
            question=payload.question,
            db=db,
            ground_truth=payload.ground_truth,
        )
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(
        query_id=result.query_id,
        question=result.question,
        answer=result.answer,
        retrieved_chunks=result.retrieval.chunks,
        scores=ScoresSchema(
            faithfulness=result.scores.faithfulness,
            answer_relevancy=result.scores.answer_relevancy,
            context_precision=result.scores.context_precision,
            context_recall=result.scores.context_recall,
        ),
    )


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics", response_model=MetricsSummary, tags=["Evaluation"])
def metrics(limit: int = 20, db: Session = Depends(get_db)):
    """Return aggregate RAGAS evaluation statistics.

    - **limit**: number of recent queries to include in the ``recent`` list
    """
    # Aggregate averages
    agg = db.execute(
        select(
            func.count(EvalResult.id).label("total"),
            func.avg(EvalResult.faithfulness).label("avg_f"),
            func.avg(EvalResult.answer_relevancy).label("avg_ar"),
            func.avg(EvalResult.context_precision).label("avg_cp"),
            func.avg(EvalResult.context_recall).label("avg_cr"),
        )
    ).one()

    # Recent rows (joined with Query for question/answer text)
    recent_rows = (
        db.execute(
            select(Query, EvalResult)
            .join(EvalResult, EvalResult.query_id == Query.id)
            .order_by(EvalResult.evaluated_at.desc())
            .limit(limit)
        )
        .all()
    )

    recent = [
        MetricsRow(
            query_id=q.id,
            question=q.question,
            answer=q.answer or "",
            faithfulness=e.faithfulness,
            answer_relevancy=e.answer_relevancy,
            context_precision=e.context_precision,
            context_recall=e.context_recall,
            evaluated_at=e.evaluated_at,
        )
        for q, e in recent_rows
    ]

    return MetricsSummary(
        total_queries=agg.total or 0,
        avg_faithfulness=round(agg.avg_f or 0.0, 4),
        avg_answer_relevancy=round(agg.avg_ar or 0.0, 4),
        avg_context_precision=round(agg.avg_cp or 0.0, 4),
        avg_context_recall=round(agg.avg_cr or 0.0, 4),
        recent=recent,
    )


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["Ops"])
def health():
    """Liveness probe. Returns 200 OK when the service is up."""
    return {"status": "ok"}


# ── Tables ────────────────────────────────────────────────────────────────────

@router.get("/tables", tags=["Tables"])
def get_tables_data(db: Session = Depends(get_db)):
    """Return real-time data from all 4 MySQL tables.

    Returns documents, chunks, queries, and eval_results tables with their data.
    """
    # Get all documents
    documents = db.execute(select(Document).order_by(Document.created_at.desc()).limit(100)).scalars().all()
    documents_data = [
        {
            "id": d.id,
            "filename": d.filename,
            "document_name": d.document_name,
            "version": d.version,
            "source_type": d.source_type,
            "total_chunks": d.total_chunks,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in documents
    ]

    # Get all chunks (limit 100)
    chunks = db.execute(select(Chunk).order_by(Chunk.created_at.desc()).limit(100)).scalars().all()
    chunks_data = [
        {
            "id": c.id,
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "text": c.text[:200] + "..." if len(c.text) > 200 else c.text,
            "vector_id": c.vector_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in chunks
    ]

    # Get all queries (limit 100)
    queries = db.execute(select(Query).order_by(Query.created_at.desc()).limit(100)).scalars().all()
    queries_data = [
        {
            "id": q.id,
            "question": q.question,
            "answer": q.answer[:200] + "..." if q.answer and len(q.answer) > 200 else q.answer,
            "retrieved_chunk_ids": q.retrieved_chunk_ids,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in queries
    ]

    # Get all eval_results (limit 100)
    eval_results = db.execute(select(EvalResult).order_by(EvalResult.evaluated_at.desc()).limit(100)).scalars().all()
    eval_results_data = [
        {
            "id": e.id,
            "query_id": e.query_id,
            "faithfulness": e.faithfulness,
            "answer_relevancy": e.answer_relevancy,
            "context_precision": e.context_precision,
            "context_recall": e.context_recall,
            "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
        }
        for e in eval_results
    ]

    return {
        "documents": {"count": len(documents_data), "data": documents_data},
        "chunks": {"count": len(chunks_data), "data": chunks_data},
        "queries": {"count": len(queries_data), "data": queries_data},
        "eval_results": {"count": len(eval_results_data), "data": eval_results_data},
    }
