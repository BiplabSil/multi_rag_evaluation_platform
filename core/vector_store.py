"""
core/vector_store.py
--------------------
Thin wrapper around the Qdrant client.

Provides:
- Collection initialisation (idempotent)
- Upsert of vectors with metadata payloads
- Nearest-neighbour search
"""

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from core.config import get_settings

_settings = get_settings()


def get_qdrant_client() -> QdrantClient:
    """Return a Qdrant client connected to Qdrant Cloud.

    Authenticates using the cluster URL and API key from settings.
    Used as a FastAPI dependency or called directly from services.
    """
    return QdrantClient(
        url=_settings.qdrant_url,
        api_key=_settings.qdrant_api_key,
        timeout=60,
    )


def ensure_collection(client: QdrantClient, vector_size: int = 1536) -> None:
    """Create the Qdrant collection if it does not already exist.

    Args:
        client:      Connected Qdrant client.
        vector_size: Dimensionality of the embedding vectors (1536 for Ada-002).
    """
    existing = {c.name for c in client.get_collections().collections}
    if _settings.qdrant_collection not in existing:
        client.create_collection(
            collection_name=_settings.qdrant_collection,
            vectors_config=qdrant_models.VectorParams(
                size=vector_size,
                distance=qdrant_models.Distance.COSINE,
            ),
        )


def upsert_vectors(
    client: QdrantClient,
    points: list[dict[str, Any]],
) -> None:
    """Insert or update a batch of vectors in Qdrant.

    Args:
        client: Connected Qdrant client.
        points: List of dicts with keys ``id``, ``vector``, and ``payload``.

    Example::

        upsert_vectors(client, [
            {"id": "abc123", "vector": [...], "payload": {"text": "...", "source": "doc.pdf"}},
        ])
    """
    qdrant_points = [
        qdrant_models.PointStruct(
            id=p["id"],
            vector=p["vector"],
            payload=p["payload"],
        )
        for p in points
    ]
    for i in range(0, len(qdrant_points), 50):
        batch = qdrant_points[i : i + 50]
        client.upsert(
            collection_name=_settings.qdrant_collection,
            points=batch,
        )


def search_vectors(
    client: QdrantClient,
    query_vector: list[float],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Return the top-k nearest chunks for a query vector.

    Args:
        client:       Connected Qdrant client.
        query_vector: Embedding of the user query.
        top_k:        Number of results to return (defaults to config value).

    Returns:
        List of dicts with ``id``, ``score``, and ``payload`` keys.
    """
    k = top_k or _settings.top_k_retrieval
    results = client.query_points(
        collection_name=_settings.qdrant_collection,
        query=query_vector,
        limit=k,
        with_payload=True,
    )
    return [
        {"id": r.id, "score": r.score, "payload": r.payload}
        for r in results.points
    ]
