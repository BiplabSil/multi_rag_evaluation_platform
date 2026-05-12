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
    IngestRequest,
    IngestResponse,
    MetricsRow,
    MetricsSummary,
    QueryRequest,
    QueryResponse,
    ScoresSchema,
)
from core.database import get_db
from ingestion.pipeline import ingest_document
from models.orm import EvalResult, Query

logger = logging.getLogger(__name__)
router = APIRouter()

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
    """
    try:
        doc = ingest_document(payload.source, payload.source_type, db)
    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IngestResponse(
        document_id=doc.id,
        filename=doc.filename,
        total_chunks=doc.total_chunks,
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
