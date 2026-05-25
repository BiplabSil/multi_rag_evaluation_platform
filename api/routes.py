"""
api/routes.py
-------------
FastAPI route definitions.

Endpoints:
- POST /ingest              → ingest a document
- POST /query               → start async RAG pipeline, returns job_id immediately
- GET  /query/status/{id}   → poll for job result
- GET  /metrics             → aggregate evaluation statistics
- GET  /health              → liveness probe
"""

import logging
import uuid
import json
import threading

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
from core.database import SessionLocal, get_db
from core.vector_store import delete_by_metadata, get_qdrant_client, search_by_metadata
from ingestion.pipeline import ingest_document
from models.orm import Chunk, Document, EvalResult, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# App-level orchestrator singleton
_orchestrator = Orchestrator()

# In-memory job storage (works in Lambda)
_jobs = {}


# ── Job helpers ───────────────────────────────────────────────────────────────

def _set_job(job_id: str, status: str, result: dict | None = None, error: str | None = None):
    """Store job status in memory."""
    _jobs[job_id] = {
        "job_id": job_id,
        "status": status,
        "result": json.dumps(result) if result else None,
        "error": error,
    }


def _get_job(job_id: str) -> dict | None:
    """Retrieve job status from memory."""
    return _jobs.get(job_id)


def _run_pipeline_async(job_id: str, question: str, ground_truth: str | None = None):
    """Run pipeline in background thread with its own DB session."""
    logger.info(f"[{job_id}] Starting background pipeline thread")
    db = SessionLocal()
    try:
        import asyncio
        logger.info(f"[{job_id}] Creating new event loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        logger.info(f"[{job_id}] Running orchestrator")
        result = loop.run_until_complete(_orchestrator.run(
            question=question,
            db=db,
            ground_truth=ground_truth,
        ))

        loop.close()
        logger.info(f"[{job_id}] Orchestrator completed, saving result")

        _set_job(
            job_id,
            status="completed",
            result={
                "query_id": result.query_id,
                "question": result.question,
                "answer": result.answer,
                "retrieved_chunks": result.retrieval.chunks,
                "scores": {
                    "faithfulness": result.scores.faithfulness,
                    "answer_relevancy": result.scores.answer_relevancy,
                    "context_precision": result.scores.context_precision,
                    "context_recall": result.scores.context_recall,
                },
            },
        )
        logger.info(f"[{job_id}] Result saved successfully")
    except Exception as exc:
        logger.exception(f"[{job_id}] Pipeline failed: %s", exc)
        _set_job(job_id, status="failed", error=str(exc))
    finally:
        db.close()
        logger.info(f"[{job_id}] Database session closed")


# ── Ingest ────────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse, tags=["Ingestion"])
def ingest(payload: IngestRequest, db: Session = Depends(get_db)):
    """Ingest a document into the RAG platform."""
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
    """Search for stored document chunks by metadata filters."""
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
    """Delete document chunks from the vector store by metadata filters."""
    if not payload.document_name and not payload.document_version and not payload.document_id:
        raise HTTPException(
            status_code=400,
            detail="At least one of document_name, document_version, or document_id must be provided.",
        )
    try:
        doc_filter = []
        if payload.document_id:
            doc_filter.append(Document.id == payload.document_id)
        if payload.document_name:
            doc_filter.append(Document.document_name == payload.document_name)
        if payload.document_version:
            doc_filter.append(Document.version == payload.document_version)

        stmt = select(Document).where(*doc_filter)
        documents = db.execute(stmt).scalars().all()
        doc_ids = [doc.id for doc in documents]

        deleted_chunks_count = 0
        if doc_ids:
            chunks_stmt = select(Chunk).where(Chunk.document_id.in_(doc_ids))
            chunks = db.execute(chunks_stmt).scalars().all()
            deleted_chunks_count = len(chunks)
            for chunk in chunks:
                db.delete(chunk)
            for doc in documents:
                db.delete(doc)
            db.commit()

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


# ── Query (async job pattern) ─────────────────────────────────────────────────

@router.post("/query", tags=["Query"])
def query(payload: QueryRequest, db: Session = Depends(get_db)):
    """Start RAG pipeline asynchronously, return job_id for polling."""
    try:
        job_id = str(uuid.uuid4())
        _set_job(job_id, status="running")

        thread = threading.Thread(
            target=_run_pipeline_async,
            args=(job_id, payload.question, payload.ground_truth),
            daemon=False,
        )
        thread.start()

        logger.info(f"[{job_id}] Query job started, returning job_id to client")
        return {
            "job_id": job_id,
            "status": "running",
            "message": "Query processing started. Poll /api/query/status/{job_id} for results.",
        }
    except Exception as exc:
        logger.exception("Query submission failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/query/status/{job_id}", tags=["Query"])
def query_status(job_id: str):
    """Poll for job result."""
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    result = {
        "job_id": job["job_id"],
        "status": job["status"],
    }

    if job["status"] == "completed":
        result["result"] = json.loads(job["result"]) if job["result"] else None
    elif job["status"] == "failed":
        result["error"] = job["error"]

    return result


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics", response_model=MetricsSummary, tags=["Evaluation"])
def metrics(limit: int = 20, db: Session = Depends(get_db)):
    """Return aggregate RAGAS evaluation statistics."""
    agg = db.execute(
        select(
            func.count(EvalResult.id).label("total"),
            func.avg(EvalResult.faithfulness).label("avg_f"),
            func.avg(EvalResult.answer_relevancy).label("avg_ar"),
            func.avg(EvalResult.context_precision).label("avg_cp"),
            func.avg(EvalResult.context_recall).label("avg_cr"),
        )
    ).one()

    recent_rows = db.execute(
        select(Query, EvalResult)
        .join(EvalResult, EvalResult.query_id == Query.id)
        .order_by(EvalResult.evaluated_at.desc())
        .limit(limit)
    ).all()

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
    """Liveness probe."""
    return {"status": "ok"}


# ── Tables ────────────────────────────────────────────────────────────────────

@router.get("/tables", tags=["Tables"])
def get_tables_data(db: Session = Depends(get_db)):
    """Return real-time data from all 4 MySQL tables."""
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