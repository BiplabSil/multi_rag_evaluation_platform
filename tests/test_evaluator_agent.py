"""
tests/test_evaluator_agent.py
-----------------------------
Unit tests for EvaluatorAgent.

Mocks the RAGAS evaluation to avoid external API calls.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.evaluator_agent import EvalScores, EvaluatorAgent
from agents.generator_agent import GeneratorResult


@pytest.fixture
def sample_generator_result():
    """Sample generator result for testing."""
    return GeneratorResult(
        question="What is RAG?",
        answer="RAG combines retrieval and generation.",
        context=["RAG combines retrieval and generation.", "RAGAS evaluates RAG pipelines."],
    )


@pytest.fixture
def mock_ragas_result():
    """Mock RAGAS evaluation result that returns actual score values."""
    # Create a mock result that properly mimics the RAGAS evaluate() return value
    mock_result = MagicMock()

    # Create a mock row that returns actual values when to_dict is called
    mock_row = MagicMock()
    mock_row.to_dict.return_value = {
        "faithfulness": 0.95,
        "answer_relevancy": 0.90,
        "context_precision": 0.88,
        "context_recall": 0.85,
    }

    # Mock the to_pandas() method to return a DataFrame-like object with iloc
    mock_df = MagicMock()
    mock_df.iloc = MagicMock()
    mock_df.iloc.__getitem__.return_value = mock_row
    mock_result.to_pandas.return_value = mock_df

    return mock_result


@pytest.mark.asyncio
async def test_evaluator_returns_scores(sample_generator_result, mock_ragas_result):
    """EvaluatorAgent.run() should return EvalScores."""
    with patch("agents.evaluator_agent.evaluate", return_value=mock_ragas_result):
        with patch("agents.evaluator_agent._embeddings", MagicMock()):
            agent = EvaluatorAgent()
            result = await agent.run(sample_generator_result)

    assert isinstance(result, EvalScores)
    # Check it's a valid score in the expected range
    assert 0.0 <= result.faithfulness <= 1.0
    assert result.answer_relevancy == 0.90
    assert result.context_precision == 0.88
    # context_recall should be 0.0 when no ground truth is provided
    assert result.context_recall == 0.0


@pytest.mark.asyncio
async def test_evaluator_without_ground_truth(sample_generator_result, mock_ragas_result):
    """EvaluatorAgent should set context_recall to 0.0 when no ground truth."""
    with patch("agents.evaluator_agent.evaluate", return_value=mock_ragas_result):
        with patch("agents.evaluator_agent._embeddings", MagicMock()):
            agent = EvaluatorAgent()
            result = await agent.run(sample_generator_result, ground_truth=None)

    assert result.context_recall == 0.0


@pytest.mark.asyncio
async def test_evaluator_with_ground_truth(sample_generator_result, mock_ragas_result):
    """EvaluatorAgent should compute context_recall when ground truth provided."""
    with patch("agents.evaluator_agent.evaluate", return_value=mock_ragas_result):
        with patch("agents.evaluator_agent._embeddings", MagicMock()):
            agent = EvaluatorAgent()
            result = await agent.run(
                sample_generator_result,
                ground_truth="RAG is retrieval-augmented generation."
            )

    assert isinstance(result, EvalScores)


@pytest.mark.asyncio
async def test_safe_float_handles_nan(sample_generator_result):
    """Test that safe_float handles NaN values."""
    import math

    # Create a mock result with NaN
    mock_df = MagicMock()
    mock_df.iloc = [MagicMock(to_dict=lambda: {
        "faithfulness": float('nan'),
        "answer_relevancy": 0.90,
        "context_precision": 0.88,
        "context_recall": 0.85,
    })]

    with patch("agents.evaluator_agent.evaluate", return_value=mock_df):
        with patch("agents.evaluator_agent._embeddings", MagicMock()):
            agent = EvaluatorAgent()
            result = await agent.run(sample_generator_result)

    # NaN should be converted to 0.0
    assert result.faithfulness == 0.0 or math.isnan(result.faithfulness) == False


def test_eval_scores_dataclass():
    """Test EvalScores dataclass creation."""
    scores = EvalScores(
        faithfulness=0.95,
        answer_relevancy=0.90,
        context_precision=0.88,
        context_recall=0.85,
        raw={"faithfulness": 0.95},
    )

    assert scores.faithfulness == 0.95
    assert scores.raw["faithfulness"] == 0.95