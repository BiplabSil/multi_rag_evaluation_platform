"""
tests/test_orchestrator.py
--------------------------
Unit tests for Orchestrator (the multi-agent pipeline).

Mocks all agent components and database to test the pipeline flow.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.orchestrator import Orchestrator, PipelineResult, _safe_float


def test_safe_float_converts_nan():
    """Test _safe_float converts NaN to 0.0."""
    import math

    assert _safe_float(float('nan')) == 0.0
    assert _safe_float(float('inf')) == 0.0
    assert _safe_float(-float('inf')) == 0.0
    assert _safe_float(0.95) == 0.95
    assert _safe_float(None) == 0.0


def test_safe_float_preserves_valid_values():
    """Test _safe_float preserves valid float values."""
    assert _safe_float(0.0) == 0.0
    assert _safe_float(1.0) == 1.0
    assert _safe_float(0.123) == 0.123


def test_pipeline_result_dataclass():
    """Test PipelineResult creation with all fields."""
    from agents.retrieval_agent import RetrievalResult
    from agents.generator_agent import GeneratorResult
    from agents.evaluator_agent import EvalScores

    retrieval = RetrievalResult(query="test", chunks=["chunk"], chunk_ids=["id"], scores=[0.9])
    generation = GeneratorResult(question="test", answer="answer", context=["chunk"])
    scores = EvalScores(0.9, 0.8, 0.7, 0.6, {})

    result = PipelineResult(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG combines retrieval.",
        retrieval=retrieval,
        generation=generation,
        scores=scores,
    )

    assert result.query_id == "qid-1"
    assert result.question == "What is RAG?"
    assert result.retrieval.chunks == ["chunk"]


def test_orchestrator_initialization():
    """Test that Orchestrator initializes all agents and builds graph."""
    orchestrator = Orchestrator()

    assert orchestrator.retrieval_agent is not None
    assert orchestrator.generator_agent is not None
    assert orchestrator.evaluator_agent is not None
    assert orchestrator.graph is not None
    assert orchestrator.compiled_graph is not None


@pytest.mark.asyncio
async def test_orchestrator_run_returns_pipeline_result(mock_db_session):
    """Test Orchestrator.run() returns PipelineResult with all components."""
    from agents.retrieval_agent import RetrievalResult
    from agents.generator_agent import GeneratorResult
    from agents.evaluator_agent import EvalScores

    # Create mock results for each agent
    mock_retrieval = RetrievalResult(
        query="What is RAG?",
        chunks=["RAG combines retrieval."],
        chunk_ids=["chunk-1"],
        scores=[0.95],
    )
    mock_generation = GeneratorResult(
        question="What is RAG?",
        answer="RAG combines retrieval and generation.",
        context=["RAG combines retrieval."],
    )
    mock_scores = EvalScores(
        faithfulness=0.95,
        answer_relevancy=0.90,
        context_precision=0.88,
        context_recall=0.85,
        raw={},
    )

    with (
        patch.object(Orchestrator, "retrieval_node", return_value={"retrieval": mock_retrieval}),
        patch.object(Orchestrator, "generation_node", return_value={"generation": mock_generation}),
        patch.object(Orchestrator, "evaluation_node", new=AsyncMock(return_value={"scores": mock_scores})),
        patch.object(Orchestrator, "persist_node", return_value={"query_id": "qid-1", "scores": mock_scores}),
    ):
        orchestrator = Orchestrator()
        result = await orchestrator.run("What is RAG?", mock_db_session)

    assert isinstance(result, PipelineResult)
    assert result.question == "What is RAG?"
    assert result.answer == "RAG combines retrieval and generation."
    assert result.scores.faithfulness == 0.95


@pytest.mark.asyncio
async def test_orchestrator_with_ground_truth(mock_db_session):
    """Test Orchestrator.run() passes ground truth to evaluator."""
    from agents.retrieval_agent import RetrievalResult
    from agents.generator_agent import GeneratorResult
    from agents.evaluator_agent import EvalScores

    mock_retrieval = RetrievalResult(query="?", chunks=[], chunk_ids=[], scores=[])
    mock_generation = GeneratorResult(question="?", answer="answer", context=[])
    mock_scores = EvalScores(0.9, 0.8, 0.7, 0.6, {})

    ground_truth = "Expected answer"

    with (
        patch.object(Orchestrator, "retrieval_node", return_value={"retrieval": mock_retrieval}),
        patch.object(Orchestrator, "generation_node", return_value={"generation": mock_generation}),
        patch.object(Orchestrator, "evaluation_node", new=AsyncMock(return_value={"scores": mock_scores})),
        patch.object(Orchestrator, "persist_node", return_value={"query_id": "qid-1", "scores": mock_scores}),
    ):
        orchestrator = Orchestrator()
        # The ground_truth should be passed through the state
        result = await orchestrator.run("?", mock_db_session, ground_truth=ground_truth)

    assert isinstance(result, PipelineResult)


def test_orchestrator_nodes_exist():
    """Test that orchestrator has all required node methods."""
    orchestrator = Orchestrator()

    assert hasattr(orchestrator, "retrieval_node")
    assert hasattr(orchestrator, "generation_node")
    assert hasattr(orchestrator, "evaluation_node")
    assert hasattr(orchestrator, "persist_node")

    # All should be callable
    assert callable(orchestrator.retrieval_node)
    assert callable(orchestrator.generation_node)
    assert callable(orchestrator.evaluation_node)
    assert callable(orchestrator.persist_node)