"""
tests/test_api_integration.py
------------------------------
Integration tests for the FastAPI endpoints.

Uses FastAPI's TestClient with dependency overrides so no real DB,
Qdrant, or OpenAI calls are made.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.database import get_db


# ── DB override ───────────────────────────────────────────────────────────────

class FakeSession:
    """Minimal SQLAlchemy session mock for testing."""

    def add(self, obj): pass
    def add_all(self, objs): pass
    def flush(self): pass
    def commit(self): pass
    def refresh(self, obj): pass
    def close(self): pass


def override_get_db():
    yield FakeSession()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── Ingest ────────────────────────────────────────────────────────────────────

def test_ingest_endpoint():
    """POST /ingest should return a document ID and chunk count."""
    fake_doc = MagicMock()
    fake_doc.id = "doc-abc"
    fake_doc.filename = "test.txt"
    fake_doc.total_chunks = 5

    with patch("api.routes.ingest_document", return_value=fake_doc):
        response = client.post(
            "/api/ingest",
            json={"source": "/tmp/test.txt", "source_type": "txt"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "doc-abc"
    assert data["total_chunks"] == 5


# ── Query ─────────────────────────────────────────────────────────────────────

def test_query_endpoint():
    """POST /query should return an answer and evaluation scores."""
    from agents.evaluator_agent import EvalScores
    from agents.generator_agent import GeneratorResult
    from agents.orchestrator import PipelineResult
    from agents.retrieval_agent import RetrievalResult

    fake_result = PipelineResult(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG combines retrieval and generation.",
        retrieval=RetrievalResult(
            query="What is RAG?",
            chunks=["RAG combines retrieval and generation."],
            chunk_ids=["cid-1"],
            scores=[0.95],
        ),
        generation=GeneratorResult(
            question="What is RAG?",
            answer="RAG combines retrieval and generation.",
            context=["RAG combines retrieval and generation."],
        ),
        scores=EvalScores(
            faithfulness=0.95,
            answer_relevancy=0.90,
            context_precision=0.88,
            context_recall=0.85,
            raw={},
        ),
    )

    with patch("api.routes._orchestrator.run", new=AsyncMock(return_value=fake_result)):
        response = client.post(
            "/api/query",
            json={"question": "What is RAG?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "RAG combines retrieval and generation."
    assert data["scores"]["faithfulness"] == 0.95
