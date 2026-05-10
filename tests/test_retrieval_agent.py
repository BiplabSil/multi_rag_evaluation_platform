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
        patch("agents.retrieval_agent._openai") as mock_openai,
        patch("agents.retrieval_agent.get_qdrant_client") as mock_client_factory,
        patch("agents.retrieval_agent.search_vectors", return_value=mock_search_results),
    ):
        # Mock OpenAI embedding call
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=mock_embedding)]
        )

        agent = RetrievalAgent(top_k=2)
        result = agent.run("What is RAG?")

    assert isinstance(result, RetrievalResult)
    assert result.query == "What is RAG?"
    assert len(result.chunks) == 2
    assert len(result.chunk_ids) == 2
    assert len(result.scores) == 2
    assert result.scores[0] > result.scores[1]  # results should be in score order


def test_retrieval_agent_empty_results(mock_embedding):
    """RetrievalAgent.run() should handle empty search results gracefully."""
    with (
        patch("agents.retrieval_agent._openai") as mock_openai,
        patch("agents.retrieval_agent.get_qdrant_client"),
        patch("agents.retrieval_agent.search_vectors", return_value=[]),
    ):
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=mock_embedding)]
        )
        agent = RetrievalAgent()
        result = agent.run("Unknown topic")

    assert result.chunks == []
    assert result.chunk_ids == []
    assert result.scores == []
