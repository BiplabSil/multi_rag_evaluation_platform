"""
tests/test_retrieval_agent.py
------------------------------
Unit tests for RetrievalAgent.

Uses unittest.mock to avoid hitting real OpenAI / Qdrant endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.retrieval_agent import RetrievalAgent, RetrievalResult


@pytest.fixture
def mock_embedding():
    """Return a deterministic 1536-dim zero vector."""
    return [0.0] * 1536


@pytest.fixture
def mock_search_results():
    """Fake Qdrant search response."""
    return [
        {"id": "chunk-1", "score": 0.92, "payload": {"text": "RAG combines retrieval and generation."}},
        {"id": "chunk-2", "score": 0.85, "payload": {"text": "RAGAS evaluates RAG pipelines."}},
    ]


def test_retrieval_agent_returns_result(mock_embedding, mock_search_results):
    """RetrievalAgent.run() should return a populated RetrievalResult."""
    with (
        patch("agents.retrieval_agent.RetrievalAgent._rewrite_query", return_value="What is RAG?"),
        patch("agents.retrieval_agent.RetrievalAgent._hyde_expand", return_value=[]),
        patch("agents.retrieval_agent.RetrievalAgent._embed_query", return_value=mock_embedding),
        patch("agents.retrieval_agent.get_qdrant_client"),
        patch("agents.retrieval_agent.search_vectors", return_value=mock_search_results),
        patch("agents.retrieval_agent.RetrievalAgent._cohere_rerank", side_effect=lambda query, candidates: candidates),
    ):
        agent = RetrievalAgent(top_k=2)
        result = agent.run("What is RAG?")

    assert isinstance(result, RetrievalResult)
    assert result.query == "What is RAG?"
    assert len(result.chunks) == 2
    assert len(result.chunk_ids) == 2
    assert len(result.scores) == 2
    assert result.scores[0] >= result.scores[1]


def test_retrieval_agent_empty_results(mock_embedding):
    """RetrievalAgent.run() should handle empty search results gracefully."""
    with (
        patch("agents.retrieval_agent.RetrievalAgent._rewrite_query", return_value="Unknown topic"),
        patch("agents.retrieval_agent.RetrievalAgent._hyde_expand", return_value=[]),
        patch("agents.retrieval_agent.RetrievalAgent._embed_query", return_value=mock_embedding),
        patch("agents.retrieval_agent.get_qdrant_client"),
        patch("agents.retrieval_agent.search_vectors", return_value=[]),
        patch("agents.retrieval_agent.RetrievalAgent._cohere_rerank", side_effect=lambda query, candidates: candidates),
    ):
        agent = RetrievalAgent()
        result = agent.run("Unknown topic")

    assert result.chunks == []
    assert result.chunk_ids == []
    assert result.scores == []
