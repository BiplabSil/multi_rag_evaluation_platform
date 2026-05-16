"""
agents/orchestrator.py
-----------------------
Orchestrator Agent — the single entry point for the multi-agent pipeline.

Coordinates the three specialist agents using LangGraph state machine.

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
    PersistNode    ──→  persisted to MySQL, returned to API
"""

import math
from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
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


class PipelineState(TypedDict):
    """State for the LangGraph pipeline."""
    question: str
    db: Session
    ground_truth: str | None
    retrieval: RetrievalResult | None
    generation: GeneratorResult | None
    scores: EvalScores | None
    query_id: str | None


class Orchestrator:
    """Coordinates the retrieval → generation → evaluation → persist pipeline using LangGraph.

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

        # Build the LangGraph
        self.graph = StateGraph(PipelineState)
        self.graph.add_node("retrieve_chunks", self.retrieval_node)
        self.graph.add_node("generate_answer", self.generation_node)
        self.graph.add_node("evaluate_quality", self.evaluation_node)
        self.graph.add_node("save_results", self.persist_node)

        self.graph.add_edge(START, "retrieve_chunks")
        self.graph.add_edge("retrieve_chunks", "generate_answer")
        self.graph.add_edge("generate_answer", "evaluate_quality")
        self.graph.add_edge("evaluate_quality", "save_results")
        self.graph.add_edge("save_results", END)

        self.compiled_graph = self.graph.compile()

    def retrieval_node(self, state: PipelineState) -> dict:
        """Node for retrieval step."""
        retrieval = self.retrieval_agent.run(state["question"])
        return {"retrieval": retrieval}

    def generation_node(self, state: PipelineState) -> dict:
        """Node for generation step."""
        generation = self.generator_agent.run(state["retrieval"])
        return {"generation": generation}

    async def evaluation_node(self, state: PipelineState) -> dict:
        """Node for evaluation step."""
        scores = await self.evaluator_agent.run(state["generation"], state["ground_truth"])
        return {"scores": scores}

    def persist_node(self, state: PipelineState) -> dict:
        """Node for persisting results to database."""
        scores = state["scores"]
        generation = state["generation"]
        retrieval = state["retrieval"]

        # Sanitise scores
        safe_faithfulness = _safe_float(scores.faithfulness)
        safe_answer_relevancy = _safe_float(scores.answer_relevancy)
        safe_context_precision = _safe_float(scores.context_precision)
        safe_context_recall = _safe_float(scores.context_recall)

        safe_raw = {
            k: (0.0 if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
            for k, v in scores.raw.items()
        }

        # Persist to MySQL
        query_row = Query(
            question=state["question"],
            answer=generation.answer,
            retrieved_chunk_ids=retrieval.chunk_ids,
        )
        state["db"].add(query_row)
        state["db"].flush()

        eval_row = EvalResult(
            query_id=query_row.id,
            faithfulness=safe_faithfulness,
            answer_relevancy=safe_answer_relevancy,
            context_precision=safe_context_precision,
            context_recall=safe_context_recall,
            raw_scores=safe_raw,
        )
        state["db"].add(eval_row)
        state["db"].commit()

        # Update scores with sanitised values
        scores.faithfulness = safe_faithfulness
        scores.answer_relevancy = safe_answer_relevancy
        scores.context_precision = safe_context_precision
        scores.context_recall = safe_context_recall

        return {"query_id": query_row.id, "scores": scores}

    async def run(
        self,
        question: str,
        db: Session,
        ground_truth: str | None = None,
    ) -> PipelineResult:
        """Execute the full multi-agent pipeline for a user question using LangGraph.

        Args:
            question:     Natural-language query from the user.
            db:           Active SQLAlchemy session for persisting results.
            ground_truth: Optional reference answer for context-recall scoring.

        Returns:
            PipelineResult with all intermediate and final outputs.
        """
        initial_state: PipelineState = {
            "question": question,
            "db": db,
            "ground_truth": ground_truth,
            "retrieval": None,
            "generation": None,
            "scores": None,
            "query_id": None,
        }

        final_state = await self.compiled_graph.ainvoke(initial_state)

        return PipelineResult(
            query_id=final_state["query_id"],
            question=question,
            answer=final_state["generation"].answer,
            retrieval=final_state["retrieval"],
            generation=final_state["generation"],
            scores=final_state["scores"],
        )
