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
import asyncio
import logging
import os
from dataclasses import dataclass

import requests
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
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)
settings = get_settings()
os.environ["OPENAI_API_KEY"] = settings.openai_api_key

original = os.environ.get("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Initialize embeddings for RAGAS
_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

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

    async def run(
        self,
        generator_result: GeneratorResult,
        ground_truth: str | None = None,
        enable_github_check: bool = False,
    ) -> EvalScores:
        """Evaluate a generator result with RAGAS asynchronously.

        Args:
            generator_result:   Output from :class:`agents.generator_agent.GeneratorAgent`.
            ground_truth:     Optional reference answer. Required for
                              ``context_recall``; if omitted that metric is skipped.
            enable_github_check: If True, post GitHub status check (for CI runs).
                              Default False (skip for user queries).

        Returns:
            :class:`EvalScores` with all four metric values. If ground_truth
            is not provided, context_recall will be 0.0 but other metrics will
            still show real scores.
        """
        # Determine metrics based on ground truth availability
        has_ground_truth = ground_truth and ground_truth.strip()

        # Metrics that work without ground truth
        base_metrics = [faithfulness, answer_relevancy, context_precision]

        # Set embeddings for each metric to avoid NaN issues
        for metric in base_metrics:
            metric.embeddings = _embeddings

        # Add context_recall only when ground truth is available
        if has_ground_truth:
            metrics = base_metrics + [context_recall]
            context_recall.embeddings = _embeddings
        else:
            metrics = base_metrics

        # RAGAS expects a HuggingFace Dataset with specific column names
        sample = {
            "question": [generator_result.question],
            "answer": [generator_result.answer],
            "contexts": [generator_result.context],
            "ground_truth": [ground_truth or ""],
        }
        dataset = Dataset.from_dict(sample)
        try:
            result = await asyncio.to_thread(evaluate, dataset, metrics=metrics)
        finally:
            if original:
                os.environ["LANGCHAIN_TRACING_V2"] = original

        scores_dict = result.to_pandas().iloc[0].to_dict()

        # Debug: Log raw RAGAS output to understand what's being returned
        logger.debug(f"RAGAS raw scores: {scores_dict}")

        # Helper to safely extract float, handling NaN
        def safe_float(value, default=0.0):
            if value is None:
                return default
            try:
                import math
                if math.isnan(value):
                    logger.warning(f"NaN detected for metric, using default {default}")
                    return default
            except (TypeError, ValueError):
                pass
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        computed_metrics = list(scores_dict.keys())
        logger.debug(f"Computed metrics: {computed_metrics}")

        scores = EvalScores(
            faithfulness=safe_float(scores_dict.get("faithfulness")),
            answer_relevancy=safe_float(scores_dict.get("answer_relevancy")),
            context_precision=safe_float(scores_dict.get("context_precision")),
            # context_recall is 0.0 when not computed (no ground truth)
            context_recall=safe_float(scores_dict.get("context_recall")) if has_ground_truth else 0.0,
            raw=scores_dict,
        )

        logger.info(
            f"Evaluation complete: faithfulness={scores.faithfulness}, "
            f"answer_relevancy={scores.answer_relevancy}, "
            f"context_precision={scores.context_precision}, "
            f"context_recall={scores.context_recall}"
        )

        if enable_github_check:
            await self._trigger_github_check(scores, generator_result.question, computed_metrics)
        return scores

    async def _trigger_github_check(
        self, scores: EvalScores, question: str, computed_metrics: list[str]
    ) -> None:
        """Create or update a GitHub check run for the evaluation."""
        if not self._can_create_check():
            logger.debug("Skipping GitHub check: missing configuration.")
            return

        threshold = settings.github_failure_threshold

        # Only evaluate metrics that were actually computed
        metrics_to_check = []
        if "faithfulness" in computed_metrics:
            metrics_to_check.append(("faithfulness", scores.faithfulness))
        if "answer_relevancy" in computed_metrics:
            metrics_to_check.append(("answer_relevancy", scores.answer_relevancy))
        if "context_precision" in computed_metrics:
            metrics_to_check.append(("context_precision", scores.context_precision))
        if "context_recall" in computed_metrics:
            metrics_to_check.append(("context_recall", scores.context_recall))

        failed = [
            (name, value) for name, value in metrics_to_check if value < threshold
        ]

        conclusion = "success" if not failed else "failure"
        summary = (
            "All metrics met the configured threshold."
            if conclusion == "success"
            else "One or more metrics fell below the configured threshold."
        )

        text_lines = [
            f"Question: {question}",
            "",
            "Metrics:",
            *[
                f"- {metric}: {value:.2f} (threshold: {threshold:.2f})"
                for metric, value in metrics_to_check
            ],
        ]

        payload = {
            "state": conclusion,
            "description": "RAG benchmark",
            "context": "ragas-eval",
        }

        print("PAYLOAD:", payload)

        url = f"https://api.github.com/repos/{settings.github_repo}/statuses/{settings.github_head_sha}"

        headers = {
            "Authorization": f"Bearer {settings.github_api_token}",
            "Accept": "application/vnd.github+json",
        }

        try:
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                headers=headers,
            )

            print("STATUS:", response.status_code)
            print("RESPONSE:", response.text)

            response.raise_for_status()

            logger.info(
                "GitHub status posted with conclusion=%s",
                conclusion,
            )

        except Exception as exc:
            logger.exception(
                "Failed to post GitHub status: %s",
                exc,
            )

    def _can_create_check(self) -> bool:
        return bool(
            settings.github_api_token
            and settings.github_repo
            and settings.github_head_sha
        )