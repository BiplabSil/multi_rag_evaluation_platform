"""
agents/retrieval_agent.py
-------------------------
Retrieval Agent — responsible for turning a natural-language question into
a ranked list of relevant text chunks from Qdrant.

Responsibilities:
- Embed the user query.
- Query Qdrant for nearest neighbours.
- Return structured RetrievalResult objects.
"""

from dataclasses import dataclass, field

from langchain_openai import OpenAIEmbeddings

from core.config import get_settings
from core.vector_store import get_qdrant_client, search_vectors

_settings = get_settings()
_embeddings = OpenAIEmbeddings(
    api_key=_settings.openai_api_key,
    model=_settings.embedding_model,
)


@dataclass
class RetrievalResult:
    """Output of the Retrieval Agent for a single query.

    Attributes:
        query:        The original user question.
        chunks:       Ordered list of retrieved text chunks.
        chunk_ids:    Qdrant vector IDs corresponding to each chunk.
        scores:       Cosine similarity scores for each chunk.
    """

    query: str
    chunks: list[str] = field(default_factory=list)
    chunk_ids: list[str] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)


class RetrievalAgent:
    """Agent that retrieves relevant context chunks for a user query.

    Uses OpenAI embeddings + Qdrant ANN search under the hood.

    Example::

        agent = RetrievalAgent()
        result = agent.run("What is retrieval-augmented generation?")
        for chunk, score in zip(result.chunks, result.scores):
            print(f"[{score:.3f}] {chunk[:80]}")
    """

    def __init__(self, top_k: int | None = None) -> None:
        """Initialise the agent.

        Args:
            top_k: Override the default number of chunks to retrieve.
        """
        self.top_k = top_k or _settings.top_k_retrieval

    def _embed_query(self, query: str) -> list[float]:
        """Embed a query string into a vector.

        Args:
            query: The user's natural-language question.

        Returns:
            Embedding vector (list of floats).
        """
        # Use LangChain's OpenAIEmbeddings for LangSmith tracing compatibility
        embedding = _embeddings.embed_query(query)
        return embedding

    def run(self, query: str) -> RetrievalResult:
        """Retrieve the most relevant chunks for ``query``.

        Args:
            query: Natural-language question from the user.

        Returns:
            :class:`RetrievalResult` with ranked chunks and scores.
        """
        query_vector = self._embed_query(query)
        qdrant_client = get_qdrant_client()
        raw_results = search_vectors(qdrant_client, query_vector, top_k=self.top_k)

        return RetrievalResult(
            query=query,
            chunks=[r["payload"]["text"] for r in raw_results],
            chunk_ids=[r["id"] for r in raw_results],
            scores=[r["score"] for r in raw_results],
        )
