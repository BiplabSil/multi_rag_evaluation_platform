"""
api/schemas.py
--------------
Pydantic request and response models for all API endpoints.

Keeping schemas separate from ORM models ensures the API contract is
independent of the database layer.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    """Request body for POST /ingest."""

    source: str = Field(..., description="File path or URL to ingest.")
    source_type: str = Field(
        ...,
        description="Type of source: 'pdf', 'txt', or 'url'.",
        pattern="^(pdf|txt|url)$",
    )


class IngestResponse(BaseModel):
    """Response body for POST /ingest."""

    document_id: str
    filename: str
    total_chunks: int
    message: str = "Document ingested successfully."


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Request body for POST /query."""

    question: str = Field(..., min_length=3, description="User's natural-language question.")
    ground_truth: str | None = Field(
        None,
        description="Optional reference answer for evaluation context-recall scoring.",
    )


class ScoresSchema(BaseModel):
    """Serialized RAGAS evaluation scores."""

    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


class QueryResponse(BaseModel):
    """Response body for POST /query."""

    query_id: str
    question: str
    answer: str
    retrieved_chunks: list[str]
    scores: ScoresSchema


# ── Metrics ───────────────────────────────────────────────────────────────────

class MetricsRow(BaseModel):
    """A single row in the metrics history list."""

    query_id: str
    question: str
    answer: str
    faithfulness: float | None
    answer_relevancy: float | None
    context_precision: float | None
    context_recall: float | None
    evaluated_at: datetime

    class Config:
        from_attributes = True


class MetricsSummary(BaseModel):
    """Aggregate statistics over all evaluated queries."""

    total_queries: int
    avg_faithfulness: float
    avg_answer_relevancy: float
    avg_context_precision: float
    avg_context_recall: float
    recent: list[MetricsRow]
