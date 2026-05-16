"""
tests/test_schemas.py
---------------------
Unit tests for API schemas (Pydantic models).

Tests validation, serialization, and field constraints.
"""

import pytest
from pydantic import ValidationError

from api.schemas import (
    IngestRequest,
    IngestResponse,
    MetadataSearchRequest,
    MetadataSearchResponse,
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    QueryRequest,
    QueryResponse,
    ScoresSchema,
    MetricsRow,
    MetricsSummary,
)


# ── Ingest Schemas ────────────────────────────────────────────────────────────

def test_ingest_request_valid():
    """Test IngestRequest with valid data."""
    request = IngestRequest(source="/path/to/file.pdf", source_type="pdf")
    assert request.source == "/path/to/file.pdf"
    assert request.source_type == "pdf"


def test_ingest_request_all_source_types():
    """Test IngestRequest accepts pdf, txt, url."""
    for source_type in ["pdf", "txt", "url"]:
        request = IngestRequest(source="/test/file", source_type=source_type)
        assert request.source_type == source_type


def test_ingest_request_invalid_source_type():
    """Test IngestRequest rejects invalid source_type."""
    with pytest.raises(ValidationError):
        IngestRequest(source="/test/file", source_type="doc")


def test_ingest_request_optional_fields():
    """Test IngestRequest optional document_name and version."""
    request = IngestRequest(source="/test.txt", source_type="txt")
    assert request.document_name is None
    assert request.document_version is None


def test_ingest_request_with_optional_fields():
    """Test IngestRequest with optional fields set."""
    request = IngestRequest(
        source="/test.pdf",
        source_type="pdf",
        document_name="HR Policy",
        document_version="1.0",
    )
    assert request.document_name == "HR Policy"
    assert request.document_version == "1.0"


def test_ingest_response():
    """Test IngestResponse creation."""
    response = IngestResponse(
        document_id="doc-123",
        filename="test.pdf",
        total_chunks=10,
    )
    assert response.document_id == "doc-123"
    assert response.total_chunks == 10
    assert response.message == "Document ingested successfully."


# ── Metadata Search Schemas ───────────────────────────────────────────────────

def test_metadata_search_request_empty():
    """Test MetadataSearchRequest with no filters (should be valid for the model)."""
    request = MetadataSearchRequest()
    assert request.document_name is None
    assert request.document_version is None


def test_metadata_search_request_with_filters():
    """Test MetadataSearchRequest with filters."""
    request = MetadataSearchRequest(document_name="HR Policy", document_version="1.0")
    assert request.document_name == "HR Policy"
    assert request.document_version == "1.0"


def test_metadata_search_response():
    """Test MetadataSearchResponse creation."""
    results = [{"id": "1", "text": "chunk 1"}, {"id": "2", "text": "chunk 2"}]
    response = MetadataSearchResponse(results=results, total=2)
    assert len(response.results) == 2
    assert response.total == 2


# ── Document Delete Schemas ───────────────────────────────────────────────────

def test_document_delete_request_all_fields():
    """Test DocumentDeleteRequest with all filters."""
    request = DocumentDeleteRequest(
        document_name="HR Policy",
        document_version="1.0",
        document_id="doc-123",
    )
    assert request.document_name == "HR Policy"
    assert request.document_version == "1.0"
    assert request.document_id == "doc-123"


def test_document_delete_response():
    """Test DocumentDeleteResponse creation."""
    response = DocumentDeleteResponse(deleted_count=5, message="Deleted 5 chunks")
    assert response.deleted_count == 5


# ── Query Schemas ─────────────────────────────────────────────────────────────

def test_query_request_valid():
    """Test QueryRequest with valid question."""
    request = QueryRequest(question="What is RAG?")
    assert request.question == "What is RAG?"


def test_query_request_with_ground_truth():
    """Test QueryRequest with ground truth."""
    request = QueryRequest(
        question="What is RAG?",
        ground_truth="RAG is retrieval-augmented generation.",
    )
    assert request.ground_truth == "RAG is retrieval-augmented generation."


def test_query_request_question_min_length():
    """Test QueryRequest enforces min_length=3."""
    with pytest.raises(ValidationError):
        QueryRequest(question="ab")


def test_scores_schema():
    """Test ScoresSchema creation."""
    scores = ScoresSchema(
        faithfulness=0.95,
        answer_relevancy=0.90,
        context_precision=0.88,
        context_recall=0.85,
    )
    assert scores.faithfulness == 0.95
    assert scores.answer_relevancy == 0.90


def test_query_response():
    """Test QueryResponse with all fields."""
    response = QueryResponse(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG combines retrieval.",
        retrieved_chunks=["chunk1", "chunk2"],
        scores=ScoresSchema(faithfulness=0.9, answer_relevancy=0.8, context_precision=0.7, context_recall=0.6),
    )
    assert response.query_id == "qid-1"
    assert len(response.retrieved_chunks) == 2


# ── Metrics Schemas ───────────────────────────────────────────────────────────

def test_metrics_row():
    """Test MetricsRow creation."""
    from datetime import datetime

    row = MetricsRow(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG is retrieval.",
        faithfulness=0.95,
        answer_relevancy=0.90,
        context_precision=0.88,
        context_recall=0.85,
        evaluated_at=datetime.now(),
    )
    assert row.query_id == "qid-1"
    assert row.faithfulness == 0.95


def test_metrics_row_optional_scores():
    """Test MetricsRow allows None for scores."""
    from datetime import datetime

    row = MetricsRow(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG is retrieval.",
        faithfulness=None,
        answer_relevancy=None,
        context_precision=None,
        context_recall=None,
        evaluated_at=datetime.now(),
    )
    assert row.faithfulness is None


def test_metrics_summary():
    """Test MetricsSummary creation."""
    from datetime import datetime

    summary = MetricsSummary(
        total_queries=100,
        avg_faithfulness=0.85,
        avg_answer_relevancy=0.80,
        avg_context_precision=0.75,
        avg_context_recall=0.70,
        recent=[],
    )
    assert summary.total_queries == 100
    assert summary.avg_faithfulness == 0.85


def test_metrics_summary_with_recent():
    """Test MetricsSummary with recent rows."""
    from datetime import datetime

    recent_row = MetricsRow(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG is retrieval.",
        faithfulness=0.95,
        answer_relevancy=0.90,
        context_precision=0.88,
        context_recall=0.85,
        evaluated_at=datetime.now(),
    )

    summary = MetricsSummary(
        total_queries=1,
        avg_faithfulness=0.95,
        avg_answer_relevancy=0.90,
        avg_context_precision=0.88,
        avg_context_recall=0.85,
        recent=[recent_row],
    )

    assert len(summary.recent) == 1
    assert summary.recent[0].question == "What is RAG?"