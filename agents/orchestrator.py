"""
agents/orchestrator.py
-----------------------
Orchestrator Agent — the single entry point for the multi-agent pipeline.

Coordinates the three specialist agents in sequence:

    User Query
        │
        ▼
    RetrievalAgent  ──→  relevant chunks from Qdrant
        │
        ▼
    GeneratorAgent  ──→  grounded answer from LLM
        │
        ▼
    EvaluatorAgent  ──→  RAGAS quality scores
        │
        ▼
    PipelineResult  ──→  persisted to MySQL, returned to API
"""

import math
from dataclasses import dataclass

from sqlalchemy.orm import Session

from agents.evaluator_agent import EvalScores, EvaluatorAgent
from agents.generator_agent import GeneratorAgent, GeneratorResult
from agents.retrieval_agent import RetrievalAgent, RetrievalResult
from models.orm import EvalResult, Query


def _safe_float(value: float) -> float:
    """Convert a float to a MySQL-safe value.

    RAGAS can return NaN or Infinity when it cannot compute a metric
    (e.g. context_recall without a ground truth, or answer_relevancy
    when the answer is too short). MySQL rejects both — replace with 0.0.

    Args:
        value: Raw float from RAGAS scores.

    Returns:
        0.0 if value is NaN or Infinity, otherwise the original value.
    """
    if value is None or math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)


@dataclass
class PipelineResult:
    """Complete output of the multi-agent pipeline for a single query.

    Attributes:
        query_id:   MySQL row ID of the persisted Query.
        question:   Original user question.
        answer:     Generated answer.
        retrieval:  Intermediate retrieval details.
        generation: Intermediate generation details.
        scores:     RAGAS evaluation scores.
    """

    query_id: str
    question: str
    answer: str
    retrieval: RetrievalResult
    generation: GeneratorResult
    scores: EvalScores


class Orchestrator:
    """Coordinates the retrieval → generation → evaluation pipeline.

    Instantiate once (e.g. as an app-level singleton) and call
    :meth:`run` for each incoming user query.

    Example::

        orchestrator = Orchestrator()
        result = orchestrator.run(
            question="What is RAGAS?",
            db=db_session,
            ground_truth="RAGAS is a framework for evaluating RAG pipelines.",
        )
        print(result.answer)
        print(result.scores.faithfulness)
    """

    def __init__(self) -> None:
        self.retrieval_agent = RetrievalAgent()
        self.generator_agent = GeneratorAgent()
        self.evaluator_agent = EvaluatorAgent()

    def run(
        self,
        question: str,
        db: Session,
        ground_truth: str | None = None,
    ) -> PipelineResult:
        """Execute the full multi-agent pipeline for a user question.

        Args:
            question:     Natural-language query from the user.
            db:           Active SQLAlchemy session for persisting results.
            ground_truth: Optional reference answer for context-recall scoring.

        Returns:
            PipelineResult with all intermediate and final outputs.
        """
        # ── Step 1: Retrieve ─────────────────────────────────────────────────
        retrieval: RetrievalResult = self.retrieval_agent.run(question)

        # ── Step 2: Generate ─────────────────────────────────────────────────
        generation: GeneratorResult = self.generator_agent.run(retrieval)

        # ── Step 3: Evaluate ─────────────────────────────────────────────────
        scores: EvalScores = self.evaluator_agent.run(generation, ground_truth)

        # ── Step 4: Sanitise scores before saving to MySQL ───────────────────
        # RAGAS returns NaN when a metric cannot be computed (e.g. no ground
        # truth for context_recall). MySQL rejects NaN — replace with 0.0.
        safe_faithfulness        = _safe_float(scores.faithfulness)
        safe_answer_relevancy    = _safe_float(scores.answer_relevancy)
        safe_context_precision   = _safe_float(scores.context_precision)
        safe_context_recall      = _safe_float(scores.context_recall)

        # Also sanitise the raw_scores dict stored as JSON
        safe_raw = {
            k: (0.0 if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
            for k, v in scores.raw.items()
        }

        # ── Step 5: Persist to MySQL ─────────────────────────────────────────
        query_row = Query(
            question=question,
            answer=generation.answer,
            retrieved_chunk_ids=retrieval.chunk_ids,
        )
        db.add(query_row)
        db.flush()  # get the auto-generated ID before adding EvalResult

        eval_row = EvalResult(
            query_id=query_row.id,
            faithfulness=safe_faithfulness,
            answer_relevancy=safe_answer_relevancy,
            context_precision=safe_context_precision,
            context_recall=safe_context_recall,
            raw_scores=safe_raw,
        )
        db.add(eval_row)
        db.commit()

        # Update scores with sanitised values so the API response is also clean
        scores.faithfulness      = safe_faithfulness
        scores.answer_relevancy  = safe_answer_relevancy
        scores.context_precision = safe_context_precision
        scores.context_recall    = safe_context_recall

        return PipelineResult(
            query_id=query_row.id,
            question=question,
            answer=generation.answer,
            retrieval=retrieval,
            generation=generation,
            scores=scores,
        )
