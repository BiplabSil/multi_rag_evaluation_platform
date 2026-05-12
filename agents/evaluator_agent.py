"""
agents/evaluator_agent.py
--------------------------
Evaluator Agent — computes RAGAS metrics for a question/answer/context triple.

Metrics computed:
- faithfulness       : Does the answer only assert things supported by context?
- answer_relevancy   : Is the answer on-topic for the question?
- context_precision  : Are the retrieved chunks actually about the question?
- context_recall     : Did we retrieve all the chunks needed to answer?

RAGAS performs these evaluations by calling an LLM internally, so an OpenAI
API key must be available in the environment.
"""
import os
from dataclasses import dataclass

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from agents.generator_agent import GeneratorResult
from core.config import get_settings
os.environ["OPENAI_API_KEY"] = get_settings().openai_api_key


original = os.environ.get("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_TRACING_V2"] = "false"

@dataclass
class EvalScores:
    """RAGAS evaluation scores for a single QA sample.

    Attributes:
        faithfulness:       0.0–1.0, higher is better.
        answer_relevancy:   0.0–1.0, higher is better.
        context_precision:  0.0–1.0, higher is better.
        context_recall:     0.0–1.0, higher is better (requires ground truth).
        raw:                Full RAGAS output dict for debugging.
    """

    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    raw: dict


class EvaluatorAgent:
    """Agent that evaluates a RAG pipeline output using RAGAS.

    Optionally accepts a ground-truth answer to enable context-recall
    computation.

    Example::

        from agents.evaluator_agent import EvaluatorAgent

        scores = EvaluatorAgent().run(generator_result, ground_truth="...")
        print(f"Faithfulness: {scores.faithfulness:.2f}")
    """

    def run(
        self,
        generator_result: GeneratorResult,
        ground_truth: str | None = None,
    ) -> EvalScores:
        """Evaluate a generator result with RAGAS.

        Args:
            generator_result: Output from :class:`agents.generator_agent.GeneratorAgent`.
            ground_truth:     Optional reference answer. Required for
                              ``context_recall``; if omitted that metric returns 0.

        Returns:
            :class:`EvalScores` with all four metric values.
        """
        # RAGAS expects a HuggingFace Dataset with specific column names
        sample = {
            "question": [generator_result.question],
            "answer": [generator_result.answer],
            "contexts": [generator_result.context],
            "ground_truth": [ground_truth or ""],
        }
        dataset = Dataset.from_dict(sample)

        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ]

        try:
            result = evaluate(dataset, metrics=metrics)
        finally:
            if original:
                os.environ["LANGCHAIN_TRACING_V2"] = original
        
        scores_dict = result.to_pandas().iloc[0].to_dict()

        return EvalScores(
            faithfulness=float(scores_dict.get("faithfulness", 0.0)),
            answer_relevancy=float(scores_dict.get("answer_relevancy", 0.0)),
            context_precision=float(scores_dict.get("context_precision", 0.0)),
            context_recall=float(scores_dict.get("context_recall", 0.0)),
            raw=scores_dict,
        )