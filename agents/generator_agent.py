"""
agents/generator_agent.py
--------------------------
Generator Agent — synthesises a grounded answer from retrieved context chunks.

Uses a strict system prompt to prevent hallucination: the model is instructed
to answer *only* from the provided context and to say "I don't know" when the
context is insufficient.
"""

from dataclasses import dataclass

from openai import OpenAI

from agents.retrieval_agent import RetrievalResult
from core.config import get_settings

_settings = get_settings()
_openai = OpenAI(api_key=_settings.openai_api_key)

_SYSTEM_PROMPT = """You are a precise question-answering assistant.

Rules:
1. Answer ONLY using the information in the provided context.
2. If the context does not contain enough information, respond with:
   "I don't have enough context to answer this question."
3. Be concise. Do not add information beyond what the context provides.
4. Cite the context implicitly (do not use footnotes).
"""


@dataclass
class GeneratorResult:
    """Output of the Generator Agent.

    Attributes:
        question: The original user question.
        answer:   The generated answer grounded in the retrieved context.
        context:  The context chunks that were fed to the model.
    """

    question: str
    answer: str
    context: list[str]


class GeneratorAgent:
    """Agent that generates a grounded answer from retrieval results.

    Wraps the OpenAI chat completion API with an anti-hallucination system
    prompt and formats the retrieved chunks into a numbered context block.

    Example::

        from agents.retrieval_agent import RetrievalAgent
        from agents.generator_agent import GeneratorAgent

        retrieval = RetrievalAgent()
        generator = GeneratorAgent()

        retrieved = retrieval.run("What is RAGAS?")
        result = generator.run(retrieved)
        print(result.answer)
    """

    def _build_context_block(self, chunks: list[str]) -> str:
        """Format chunks into a numbered context block for the prompt.

        Args:
            chunks: Retrieved text chunks.

        Returns:
            Multi-line string with numbered context entries.
        """
        lines = [f"[{i + 1}] {chunk}" for i, chunk in enumerate(chunks)]
        return "\n\n".join(lines)

    def run(self, retrieval_result: RetrievalResult) -> GeneratorResult:
        """Generate an answer from the retrieval result.

        Args:
            retrieval_result: Output from :class:`agents.retrieval_agent.RetrievalAgent`.

        Returns:
            :class:`GeneratorResult` with the generated answer.
        """
        context_block = self._build_context_block(retrieval_result.chunks)
        user_message = (
            f"Context:\n{context_block}\n\n"
            f"Question: {retrieval_result.query}"
        )

        response = _openai.chat.completions.create(
            model=_settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,  # deterministic for evaluation reproducibility
        )

        answer = response.choices[0].message.content.strip()

        return GeneratorResult(
            question=retrieval_result.query,
            answer=answer,
            context=retrieval_result.chunks,
        )
