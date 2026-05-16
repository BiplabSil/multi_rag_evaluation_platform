"""
tests/conftest.py
-----------------
Pytest fixtures for all test modules.

Provides reusable mocks for database, OpenAI, Qdrant, and other external dependencies.
"""

from unittest.mock import MagicMock

import pytest


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