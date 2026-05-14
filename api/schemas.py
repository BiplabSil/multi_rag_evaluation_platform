"""
api/schemas.py
--------------
Pydantic request and response models for all API endpoints.

Keeping schemas separate from ORM models ensures the API contract is
independent of the database layer.
"""

from datetime import datetime
from typing import Any

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
    document_name: str | None = Field(
        None,
        description="Optional human-readable name for the document (e.g., 'HR Policy').",
    )
    document_version: str | None = Field(
        None,
        description="Optional version string for the document (e.g., '1.0', '2.0').",
    )


class IngestResponse(BaseModel):
    """Response body for POST /ingest."""

    document_id: str
    filename: str
    document_name: str | None = None
    document_version: str | None = None
    total_chunks: int
    message: str = "Document ingested successfully."


# ── Metadata Search ────────────────────────────────────────────────────────────

class MetadataSearchRequest(BaseModel):
    """Request body for POST /search-by-metadata."""

    document_name: str | None = Field(
        None,
        description="Filter by document_name stored in vector metadata.",
    )
    document_version: str | None = Field(
        None,
        description="Filter by document_version stored in vector metadata.",
    )


class MetadataSearchResponse(BaseModel):
    """Response body for POST /search-by-metadata."""

    results: list[dict[str, Any]]
    total: int


# ── Document Delete ────────────────────────────────────────────────────────────

class DocumentDeleteRequest(BaseModel):
    """Request body for DELETE /documents."""

    document_name: str | None = Field(
        None,
        description="Delete all chunks with this document_name in metadata.",
    )
    document_version: str | None = Field(
        None,
        description="Delete all chunks with this document_version in metadata.",
    )
    document_id: str | None = Field(
        None,
        description="Delete all chunks associated with this document_id.",
    )


class DocumentDeleteResponse(BaseModel):
    """Response body for DELETE /documents."""

    deleted_count: int
    message: str


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
