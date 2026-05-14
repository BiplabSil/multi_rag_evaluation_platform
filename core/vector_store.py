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


def search_by_metadata(
    client: QdrantClient,
    document_name: str | None = None,
    document_version: str | None = None,
) -> list[dict[str, Any]]:
    """Search for vectors by metadata filters.

    Args:
        client:           Connected Qdrant client.
        document_name:    Filter by document_name in payload.
        document_version: Filter by document_version in payload.

    Returns:
        List of dicts with ``id`` and ``payload`` keys matching the filters.
    """
    must_conditions = []
    if document_name is not None:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="document_name",
                match=qdrant_models.MatchValue(value=document_name),
            )
        )
    if document_version is not None:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="document_version",
                match=qdrant_models.MatchValue(value=document_version),
            )
        )

    if not must_conditions:
        raise ValueError("At least one filter (document_name or document_version) must be provided.")

    results = client.query_points(
        collection_name=_settings.qdrant_collection,
        query_filter=qdrant_models.Filter(must=must_conditions),
        limit=1000,
        with_payload=True,
    )
    return [
        {"id": r.id, "payload": r.payload}
        for r in results.points
    ]


def delete_by_metadata(
    client: QdrantClient,
    document_name: str | None = None,
    document_version: str | None = None,
    document_id: str | None = None,
) -> int:
    """Delete vectors from Qdrant based on metadata filters.

    Args:
        client:           Connected Qdrant client.
        document_name:    Delete all chunks with this document_name.
        document_version: Delete all chunks with this document_version.
        document_id:      Delete all chunks with this document_id.

    Returns:
        Number of points deleted.
    """
    must_conditions = []
    if document_name is not None:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="document_name",
                match=qdrant_models.MatchValue(value=document_name),
            )
        )
    if document_version is not None:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="document_version",
                match=qdrant_models.MatchValue(value=document_version),
            )
        )
    if document_id is not None:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="document_id",
                match=qdrant_models.MatchValue(value=document_id),
            )
        )

    if not must_conditions:
        raise ValueError("At least one filter (document_name, document_version, or document_id) must be provided.")

    # First, get the points to delete
    results = client.query_points(
        collection_name=_settings.qdrant_collection,
        query_filter=qdrant_models.Filter(must=must_conditions),
        limit=1000,
        with_payload=False,
    )

    if not results.points:
        return 0

    point_ids = [r.id for r in results.points]

    client.delete(
        collection_name=_settings.qdrant_collection,
        points_selector=point_ids,
    )

    return len(point_ids)
