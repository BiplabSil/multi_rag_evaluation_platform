"""
tests/test_generator_agent.py
-----------------------------
Unit tests for GeneratorAgent.

Mocks the LangChain ChatOpenAI to keep tests fast and avoid external API calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.generator_agent import GeneratorAgent, GeneratorResult
from agents.retrieval_agent import RetrievalResult


@pytest.fixture
def sample_retrieval_result():
    """Sample retrieval result for testing."""
    return RetrievalResult(
        query="What is RAGAS?",
        chunks=[
            "RAGAS is a framework for evaluating RAG pipelines.",
            "It measures faithfulness, relevancy, precision, and recall.",
        ],
        chunk_ids=["id-1", "id-2"],
        scores=[0.95, 0.88],
    )


@pytest.fixture
def mock_llm():
    """Mock LangChain LLM that returns a predefined response."""
    mock = MagicMock()
    mock.invoke.return_value = MagicMock(content="RAGAS is a framework for evaluating RAG pipelines.")
    return mock


def test_generator_produces_answer(sample_retrieval_result, mock_llm):
    """GeneratorAgent.run() should produce a GeneratorResult with a non-empty answer."""
    with patch("agents.generator_agent._llm", mock_llm):
        agent = GeneratorAgent()
        result = agent.run(sample_retrieval_result)

    assert isinstance(result, GeneratorResult)
    assert result.question == "What is RAGAS?"
    assert len(result.answer) > 0
    assert result.context == sample_retrieval_result.chunks


def test_generator_includes_chunks_in_context(sample_retrieval_result, mock_llm):
    """GeneratorAgent.run() should include context chunks in the prompt."""
    with patch("agents.generator_agent._llm", mock_llm):
        agent = GeneratorAgent()
        result = agent.run(sample_retrieval_result)

    # Verify the LLM was invoked
    mock_llm.invoke.assert_called_once()
    call_args = mock_llm.invoke.call_args[0][0]

    # Check that system message is included
    assert len(call_args) >= 2  # SystemMessage + HumanMessage


def test_build_context_block_formats_chunks():
    """Test that _build_context_block formats chunks correctly."""
    agent = GeneratorAgent()
    chunks = ["First chunk", "Second chunk", "Third chunk"]

    result = agent._build_context_block(chunks)

    assert "[1] First chunk" in result
    assert "[2] Second chunk" in result
    assert "[3] Third chunk" in result


def test_generator_with_empty_chunks(mock_llm):
    """GeneratorAgent should handle empty chunks gracefully."""
    with patch("agents.generator_agent._llm", mock_llm):
        agent = GeneratorAgent()
        retrieval_result = RetrievalResult(
            query="What is RAG?",
            chunks=[],
            chunk_ids=[],
            scores=[],
        )
        result = agent.run(retrieval_result)

    assert isinstance(result, GeneratorResult)
    assert result.context == []


def test_generator_with_single_chunk(mock_llm):
    """GeneratorAgent should handle single chunk correctly."""
    with patch("agents.generator_agent._llm", mock_llm):
        agent = GeneratorAgent()
        retrieval_result = RetrievalResult(
            query="What is RAG?",
            chunks=["RAG is retrieval-augmented generation."],
            chunk_ids=["chunk-1"],
            scores=[0.95],
        )
        result = agent.run(retrieval_result)

    assert isinstance(result, GeneratorResult)
    assert len(result.context) == 1
    mock_llm.invoke.assert_called_once()