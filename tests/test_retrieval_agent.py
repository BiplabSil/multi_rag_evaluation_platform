"""
tests/test_retrieval_agent.py
-----------------------------
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


@pytest.fixture
def mock_openai_responses():
    """Mock OpenAI responses API for query rewrite and HyDE."""
    mock_response = MagicMock()
    mock_response.output_text = "What is RAG"
    return mock_response


@pytest.fixture
def mock_openai_embeddings():
    """Mock OpenAI embeddings API."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    return mock_response


def test_retrieval_agent_returns_result(mock_search_results, mock_openai_responses, mock_openai_embeddings):
    """RetrievalAgent.run() should return a populated RetrievalResult."""
    with (
        patch("agents.retrieval_agent._openai") as mock_openai,
    ):
        # Mock responses for query rewrite and HyDE
        mock_openai.responses.create.return_value = mock_openai_responses
        # Mock embeddings
        mock_openai.embeddings.create.return_value = mock_openai_embeddings
        # Mock Qdrant
        with patch("agents.retrieval_agent.get_qdrant_client"):
            with patch("agents.retrieval_agent.search_vectors", return_value=mock_search_results):
                # Mock Cohere rerank (no API key)
                with patch.object(RetrievalAgent, "_cohere_rerank", return_value=mock_search_results):
                    agent = RetrievalAgent(top_k=2)
                    result = agent.run("What is RAG?")

    assert isinstance(result, RetrievalResult)
    assert result.query == "What is RAG?"
    assert len(result.chunks) == 2
    assert len(result.chunk_ids) == 2
    assert len(result.scores) == 2


def test_retrieval_agent_empty_results(mock_openai_responses, mock_openai_embeddings):
    """RetrievalAgent.run() should handle empty search results gracefully."""
    with (
        patch("agents.retrieval_agent._openai") as mock_openai,
    ):
        mock_openai.responses.create.return_value = mock_openai_responses
        mock_openai.embeddings.create.return_value = mock_openai_embeddings

        with patch("agents.retrieval_agent.get_qdrant_client"):
            with patch("agents.retrieval_agent.search_vectors", return_value=[]):
                with patch.object(RetrievalAgent, "_cohere_rerank", return_value=[]):
                    agent = RetrievalAgent()
                    result = agent.run("Unknown topic")

    assert result.chunks == []
    assert result.chunk_ids == []
    assert result.scores == []


def test_normalize_text():
    """Test _normalize_text removes extra whitespace."""
    agent = RetrievalAgent()

    result = agent._normalize_text("Hello    world\n\nAI")
    assert result == "Hello world AI"


def test_tokenize():
    """Test _tokenize splits text into lowercase words."""
    agent = RetrievalAgent()

    result = agent._tokenize("AI is Awesome!")
    assert result == ["ai", "is", "awesome"]


def test_dedupe_candidates():
    """Test _dedupe_candidates removes duplicates keeping highest score."""
    agent = RetrievalAgent()
    candidates = [
        {"id": "chunk-1", "score": 0.9, "payload": {"text": "Text 1"}},
        {"id": "chunk-1", "score": 0.7, "payload": {"text": "Text 1"}},
        {"id": "chunk-2", "score": 0.8, "payload": {"text": "Text 2"}},
    ]

    result = agent._dedupe_candidates(candidates)

    assert len(result) == 2
    # Should keep the highest score for chunk-1
    assert any(item["id"] == "chunk-1" and item["score"] == 0.9 for item in result)


def test_bm25_scores():
    """Test _bm25_scores computes relevance scores."""
    agent = RetrievalAgent()
    texts = [
        ["rag", "is", "retrieval"],
        ["rag", "is", "generation"],
        ["llm", "is", "model"],
    ]
    query = ["rag"]

    scores = agent._bm25_scores(texts, query)

    assert len(scores) == 3
    # First two docs have "rag", third doesn't
    assert scores[0] > 0
    assert scores[1] > 0
    assert scores[2] == 0


def test_score_candidates(mock_search_results):
    """Test _score_candidates combines dense and sparse scores."""
    agent = RetrievalAgent()
    agent.dense_weight = 0.7
    agent.sparse_weight = 0.3

    result = agent._score_candidates("what is rag", mock_search_results)

    assert len(result) == 2
    # Should be sorted by score descending
    assert result[0]["score"] >= result[1]["score"]


def test_hyde_expand_returns_list(mock_openai_responses):
    """Test _hyde_expand returns a list of hypothetical answers."""
    mock_openai_responses.output_text = "Answer 1\nAnswer 2\nAnswer 3"

    with patch("agents.retrieval_agent._openai") as mock_openai:
        mock_openai.responses.create.return_value = mock_openai_responses

        agent = RetrievalAgent()
        result = agent._hyde_expand("What is RAG?")

    assert isinstance(result, list)
    assert len(result) <= agent.hyde_count


def test_cohere_rerank_skips_without_api_key(mock_search_results):
    """Test _cohere_rerank returns candidates unchanged when no API key."""
    with patch("agents.retrieval_agent._settings") as mock_settings:
        mock_settings.cohere_api_key = None

        agent = RetrievalAgent()
        result = agent._cohere_rerank("query", mock_search_results)

    assert result == mock_search_results