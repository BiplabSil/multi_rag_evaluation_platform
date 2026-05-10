"""
tests/test_generator_agent.py
------------------------------
Unit tests for GeneratorAgent.

Mocks the OpenAI chat completion call to keep tests fast and free.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.generator_agent import GeneratorAgent, GeneratorResult
from agents.retrieval_agent import RetrievalResult


@pytest.fixture
def sample_retrieval_result():
    return RetrievalResult(
        query="What is RAGAS?",
        chunks=[
            "RAGAS is a framework for evaluating RAG pipelines.",
            "It measures faithfulness, relevancy, precision, and recall.",
        ],
        chunk_ids=["id-1", "id-2"],
        scores=[0.95, 0.88],
    )


def test_generator_produces_answer(sample_retrieval_result):
    """GeneratorAgent.run() should produce a GeneratorResult with a non-empty answer."""
    with patch("agents.generator_agent._openai") as mock_openai:
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="RAGAS is a framework for evaluating RAG pipelines."
                    )
                )
            ]
        )

        agent = GeneratorAgent()
        result = agent.run(sample_retrieval_result)

    assert isinstance(result, GeneratorResult)
    assert result.question == "What is RAGAS?"
    assert len(result.answer) > 0
    assert result.context == sample_retrieval_result.chunks


def test_generator_passes_context_to_llm(sample_retrieval_result):
    """GeneratorAgent.run() should include both chunks in the LLM prompt."""
    with patch("agents.generator_agent._openai") as mock_openai:
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Answer."))]
        )

        GeneratorAgent().run(sample_retrieval_result)

        call_args = mock_openai.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        user_message = messages[-1]["content"]

    # Both chunks should appear in the prompt
    assert "RAGAS is a framework" in user_message
    assert "faithfulness" in user_message
