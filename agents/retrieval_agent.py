"""
agents/retrieval_agent.py
-------------------------
Retrieval Agent — responsible for turning a natural-language question into
an ordered list of relevant text chunks.

Responsibilities:
- Rewrite the incoming query into a focused search prompt.
- Generate HyDE synthetic answers for dense expansion.
- Execute hybrid retrieval using dense vectors + BM25 sparse scoring.
- Optionally rerank the final top-k results using Cohere Rerank.
"""

import re
from dataclasses import dataclass, field
from typing import Any

import math
import requests
from collections import Counter
#from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

from core.config import get_settings
from core.vector_store import get_qdrant_client, search_vectors

_settings = get_settings()
# _embeddings = OpenAIEmbeddings(
#     api_key=_settings.openai_api_key,
#     model=_settings.embedding_model,
# )
_openai = OpenAI(api_key=_settings.openai_api_key)


@dataclass
class RetrievalResult:
    """Output of the Retrieval Agent for a single query.

    Attributes:
        query:        The original user question.
        chunks:       Ordered list of retrieved text chunks.
        chunk_ids:    Qdrant vector IDs corresponding to each chunk.
        scores:       Final relevance scores used for ranking.
    """

    query: str
    chunks: list[str] = field(default_factory=list)
    chunk_ids: list[str] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)


class RetrievalAgent:
    """Agent that retrieves relevant context chunks for a user query.

    Uses query rewriting, HyDE expansion, hybrid dense + BM25 retrieval, and
    optional Cohere reranking for the final top-k result set.
    """

    def __init__(self, top_k: int | None = None) -> None:
        """Initialise the RetrievalAgent.

        Args:
            top_k: Override the default number of chunks to retrieve.
        """
        self.top_k = top_k or _settings.top_k_retrieval
        self.hyde_count = _settings.hyde_generation_count
        self.hyde_search_multiplier = _settings.hyde_search_multiplier
        self.bm25_candidate_multiplier = _settings.bm25_candidate_multiplier
        self.dense_weight = _settings.dense_sparse_mix_weight
        self.sparse_weight = 1.0 - self.dense_weight

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalise whitespace and punctuation for retrieval prompts."""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text for BM25 scoring."""
        return re.findall(r"\w+", text.lower())

    def _rewrite_query(self, query: str) -> str:
        """Rewrite the user query into a concise, search-focused prompt."""
        prompt = (
            "Rewrite the following user question into a concise search query that "
            "preserves intent and removes conversational noise. Return only the "
            "cleaned query text.\n\n"
            f"Question: {query}"
        )
        response = _openai.responses.create(
            model=_settings.query_rewrite_model,
            input=prompt,
        )
        output_text = getattr(response, "output_text", None)
        if output_text:
            return self._normalize_text(output_text)

        # Fallback for response objects with structured output.
        output = getattr(response, "output", [])
        text_parts: list[str] = []
        for block in output:
            if isinstance(block, dict) and "content" in block:
                for content in block["content"]:
                    if isinstance(content, dict) and "text" in content:
                        text_parts.append(content["text"])
        return self._normalize_text(" ".join(text_parts)) if text_parts else query

    def _hyde_expand(self, query: str) -> list[str]:
        """Generate HyDE synthetic answers to improve dense retrieval recall."""
        prompt = (
            "Produce up to {count} short hypothetical answers to the question "
            "below. Use these answers as alternative search signals for retrieval. "
            "Return each answer on a separate line.\n\n"
        ).format(count=self.hyde_count)
        prompt += f"Question: {query}"
        response = _openai.responses.create(
            model=_settings.hyde_model,
            input=prompt,
        )
        output_text = getattr(response, "output_text", None)
        raw = output_text or ""
        if not raw:
            output = getattr(response, "output", [])
            lines: list[str] = []
            for block in output:
                if isinstance(block, dict) and "content" in block:
                    for content in block["content"]:
                        if isinstance(content, dict) and "text" in content:
                            lines.append(content["text"])
            raw = "\n".join(lines)

        candidates = []
        for line in raw.splitlines():
            text = re.sub(r"^[\-\*\d\.\)\s]+", "", line).strip()
            if text:
                candidates.append(self._normalize_text(text))
            if len(candidates) >= self.hyde_count:
                break
        return candidates

    def _embed_query(self, query: str) -> list[float]:
        """Embed a query string into a dense vector."""

        response = _openai.embeddings.create(
            model=_settings.embedding_model,
            input=query,
        )

        return response.data[0].embedding

    def _dedupe_candidates(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep only the highest-scoring candidate for each unique Qdrant point."""
        best: dict[str, dict[str, Any]] = {}
        for item in candidates:
            if item["id"] not in best or item["score"] > best[item["id"]]["score"]:
                best[item["id"]] = item
        return list(best.values())

    @staticmethod
    def _bm25_scores(tokenised_texts: list[list[str]], query_tokens: list[str]) -> list[float]:
        """Compute BM25 scores for a list of tokenized documents."""
        if not tokenised_texts:
            return []

        k1 = 1.5
        b = 0.75
        num_docs = len(tokenised_texts)
        avg_doc_len = sum(len(doc) for doc in tokenised_texts) / num_docs

        document_frequency: Counter[str] = Counter()
        for doc in tokenised_texts:
            document_frequency.update(set(doc))

        scores: list[float] = []
        for doc in tokenised_texts:
            doc_len = len(doc)
            freqs = Counter(doc)
            score = 0.0
            for term in query_tokens:
                if freqs[term] == 0:
                    continue
                inverse_document_frequency = math.log(
                    (num_docs - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5) + 1
                )
                numerator = freqs[term] * (k1 + 1)
                denominator = freqs[term] + k1 * (1 - b + b * doc_len / avg_doc_len)
                score += inverse_document_frequency * numerator / denominator
            scores.append(score)
        return scores

    def _score_candidates(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compute a hybrid score for each candidate using cosine + BM25."""
        if not candidates:
            return []

        texts = [self._normalize_text(item["payload"]["text"]) for item in candidates]
        tokenised_texts = [self._tokenize(text) for text in texts]
        query_tokens = self._tokenize(query)
        bm25_scores = self._bm25_scores(tokenised_texts, query_tokens)

        max_dense = max(item["score"] for item in candidates) or 1.0
        max_bm25 = max(bm25_scores) or 1.0

        for item, sparse_score in zip(candidates, bm25_scores):
            dense_norm = item["score"] / max_dense
            sparse_norm = sparse_score / max_bm25
            item["score"] = self.dense_weight * dense_norm + self.sparse_weight * sparse_norm

        return sorted(candidates, key=lambda item: item["score"], reverse=True)

    def _hybrid_search(self, rewritten_query: str, query_vector: list[float]) -> list[dict[str, Any]]:
        """Combine dense vector search and HyDE expansion to build candidate chunks."""
        client = get_qdrant_client()
        dense_limit = max(self.top_k * self.bm25_candidate_multiplier, self.top_k * 2)
        candidates = search_vectors(client, query_vector, top_k=dense_limit)

        hyde_answers = self._hyde_expand(rewritten_query)
        for answer in hyde_answers:
            answer_vector = self._embed_query(answer)
            candidates.extend(
                search_vectors(
                    client,
                    answer_vector,
                    top_k=max(self.top_k * self.hyde_search_multiplier, self.top_k),
                )
            )

        unique_candidates = self._dedupe_candidates(candidates)
        return self._score_candidates(rewritten_query, unique_candidates)

    def _cohere_rerank(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Use Cohere Rerank to rescore and order the final candidate chunks."""
        if not _settings.cohere_api_key or not candidates:
            return candidates

        texts = [item["payload"]["text"] for item in candidates]
        payload = {
            "model": _settings.cohere_rerank_model,
            "query": query,
            "documents": texts,
            "top_n": len(texts),
        }
        
        response = requests.post(
            "https://api.cohere.ai/rerank",
            headers={
                "Authorization": f"Bearer {_settings.cohere_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        results = body.get("results") or body.get("ranks") or []
        if not results:
            return candidates

        reranked = []
        for record in results:
            index = record.get("index")
            if index is None or index >= len(candidates):
                continue
            item = candidates[index]
            item["score"] = float(record.get("score", item["score"]))
            reranked.append(item)

        return reranked if reranked else candidates

    def run(self, query: str) -> RetrievalResult:
        """Retrieve the most relevant chunks for ``query``."""
        rewritten_query = self._rewrite_query(query)
        query_vector = self._embed_query(rewritten_query)
        candidates = self._hybrid_search(rewritten_query, query_vector)
        final_candidates = self._cohere_rerank(rewritten_query, candidates)
        selected = final_candidates[: self.top_k]

        return RetrievalResult(
            query=query,
            chunks=[item["payload"]["text"] for item in selected],
            chunk_ids=[item["id"] for item in selected],
            scores=[item["score"] for item in selected],
        )
