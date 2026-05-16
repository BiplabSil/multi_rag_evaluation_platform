"""
tests/conftest.py
-----------------
Pytest fixtures for all test modules.

Provides reusable mocks for database, OpenAI, Qdrant, and other external dependencies.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest


def pytest_configure(config):
    """Set environment variables before any tests are collected."""
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "test-openai-key")
    os.environ["QDRANT_URL"] = os.environ.get("QDRANT_URL", "https://test.qdrant.io")
    os.environ["QDRANT_API_KEY"] = os.environ.get("QDRANT_API_KEY", "test-qdrant-key")
    os.environ.setdefault("MYSQL_HOST", "localhost")
    os.environ.setdefault("MYSQL_PORT", "3306")
    os.environ.setdefault("MYSQL_USER", "test")
    os.environ.setdefault("MYSQL_PASSWORD", "test")
    os.environ.setdefault("MYSQL_DATABASE", "test_db")


@pytest.fixture(autouse=True)
def mock_settings():
    """Auto-applied fixture that provides mock settings for all tests."""
    mock = MagicMock()
    mock.openai_api_key = "test-openai-key"
    mock.openai_model = "gpt-4o"
    mock.embedding_model = "text-embedding-3-small"
    mock.qdrant_url = "https://test.qdrant.io"
    mock.qdrant_api_key = "test-qdrant-key"
    mock.qdrant_collection = "test_collection"
    mock.chunk_size = 512
    mock.chunk_overlap = 50
    mock.top_k_retrieval = 5
    mock.bm25_candidate_multiplier = 5
    mock.hyde_generation_count = 3
    mock.hyde_search_multiplier = 2
    mock.query_rewrite_model = "gpt-4o-mini"
    mock.hyde_model = "gpt-4o-mini"
    mock.dense_sparse_mix_weight = 0.65
    mock.cohere_api_key = None
    mock.cohere_rerank_model = "rerank-v4.0-pro"
    mock.mysql_host = "localhost"
    mock.mysql_port = 3306
    mock.mysql_user = "test"
    mock.mysql_password = "test"
    mock.mysql_database = "test_db"
    mock.mysql_url = "mysql+pymysql://test:test@localhost:3306/test_db"
    mock.github_failure_threshold = 0.1
    mock.github_api_token = ""
    mock.github_repo = ""
    mock.github_head_sha = None

    with patch("core.config.get_settings", return_value=mock):
        with patch("core.vector_store._settings", mock):
            yield mock


@pytest.fixture
def mock_db_session():
    """Create a mock SQLAlchemy session."""
    session = MagicMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.close = MagicMock()
    session.execute = MagicMock()
    return session


@pytest.fixture
def sample_retrieval_result():
    """Sample RetrievalResult for testing."""
    from agents.retrieval_agent import RetrievalResult
    return RetrievalResult(
        query="What is RAG?",
        chunks=[
            "RAG combines retrieval and generation.",
            "RAGAS evaluates RAG pipelines.",
        ],
        chunk_ids=["chunk-1", "chunk-2"],
        scores=[0.95, 0.88],
    )


@pytest.fixture
def sample_generator_result():
    """Sample GeneratorResult for testing."""
    from agents.generator_agent import GeneratorResult
    return GeneratorResult(
        question="What is RAG?",
        answer="RAG combines retrieval and generation.",
        context=["RAG combines retrieval and generation."],
    )


@pytest.fixture
def sample_eval_scores():
    """Sample EvalScores for testing."""
    from agents.evaluator_agent import EvalScores
    return EvalScores(
        faithfulness=0.95,
        answer_relevancy=0.90,
        context_precision=0.88,
        context_recall=0.85,
        raw={"faithfulness": 0.95, "answer_relevancy": 0.90},
    )


@pytest.fixture
def mock_llm():
    """Mock LangChain LLM for generator testing."""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content="Test answer from LLM.")
    return mock