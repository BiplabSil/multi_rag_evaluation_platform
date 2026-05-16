"""
tests/test_vector_store.py
--------------------------
Unit tests for core/vector_store.py.

Mocks Qdrant client to test vector operations.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = MagicMock()
    return client


def test_get_qdrant_client(mock_settings):
    """Test get_qdrant_client creates client with correct settings."""
    with patch("core.vector_store.QdrantClient") as mock_client:
        mock_settings.qdrant_url = "https://test.qdrant.io"
        mock_settings.qdrant_api_key = "test-key"

        from core.vector_store import get_qdrant_client
        get_qdrant_client()

        mock_client.assert_called_once_with(
            url="https://test.qdrant.io",
            api_key="test-key",
            timeout=60,
        )


def test_ensure_collection_creates_new(mock_qdrant_client, mock_settings):
    """Test ensure_collection creates collection when it doesn't exist."""
    mock_qdrant_client.get_collections.return_value = MagicMock(
        collections=[]
    )
    mock_settings.qdrant_collection = "test_collection"

    with patch("core.vector_store.get_settings", return_value=mock_settings):
        with patch("core.vector_store._settings", mock_settings):
            from core.vector_store import ensure_collection
            ensure_collection(mock_qdrant_client)

    mock_qdrant_client.create_collection.assert_called_once()


def test_ensure_collection_skips_existing(mock_qdrant_client, mock_settings):
    """Test ensure_collection skips creation when collection exists."""
    mock_qdrant_client.get_collections.return_value = MagicMock(
        collections=[MagicMock(name="test_collection")]
    )

    # Need to patch both the get_settings and the module-level _settings
    mock_settings.qdrant_collection = "test_collection"

    with patch("core.vector_store.get_settings", return_value=mock_settings):
        with patch("core.vector_store._settings", mock_settings):
            from core.vector_store import ensure_collection
            ensure_collection(mock_qdrant_client)

    mock_qdrant_client.create_collection.assert_not_called()


def test_upsert_vectors(mock_qdrant_client, mock_settings):
    """Test upsert_vectors converts points and calls client."""
    points = [
        {"id": "vec-1", "vector": [0.1, 0.2], "payload": {"text": "Hello"}},
        {"id": "vec-2", "vector": [0.3, 0.4], "payload": {"text": "World"}},
    ]
    mock_settings.qdrant_collection = "test_collection"

    from core.vector_store import upsert_vectors
    upsert_vectors(mock_qdrant_client, points)

    mock_qdrant_client.upsert.assert_called_once()


def test_search_vectors(mock_qdrant_client, mock_settings):
    """Test search_vectors returns properly formatted results."""
    mock_results = MagicMock()
    mock_results.points = [
        MagicMock(id="vec-1", score=0.95, payload={"text": "Result 1"}),
        MagicMock(id="vec-2", score=0.88, payload={"text": "Result 2"}),
    ]
    mock_qdrant_client.query_points.return_value = mock_results
    mock_settings.qdrant_collection = "test"
    mock_settings.top_k_retrieval = 5

    from core.vector_store import search_vectors
    result = search_vectors(mock_qdrant_client, [0.1, 0.2])

    assert len(result) == 2
    assert result[0]["id"] == "vec-1"
    assert result[0]["score"] == 0.95
    assert result[0]["payload"]["text"] == "Result 1"


def test_search_by_metadata(mock_qdrant_client, mock_settings):
    """Test search_by_metadata filters by document_name."""
    mock_results = MagicMock()
    mock_results.points = [
        MagicMock(id="vec-1", payload={"text": "Chunk 1", "document_name": "doc1"}),
    ]
    mock_qdrant_client.query_points.return_value = mock_results
    mock_settings.qdrant_collection = "test"

    from core.vector_store import search_by_metadata
    result = search_by_metadata(mock_qdrant_client, document_name="doc1")

    assert len(result) == 1
    assert result[0]["payload"]["document_name"] == "doc1"


def test_search_by_metadata_requires_filter(mock_qdrant_client):
    """Test search_by_metadata raises error without filters."""
    with pytest.raises(ValueError, match="At least one filter"):
        from core.vector_store import search_by_metadata
        search_by_metadata(mock_qdrant_client)


def test_delete_by_metadata(mock_qdrant_client, mock_settings):
    """Test delete_by_metadata deletes matching vectors."""
    mock_results = MagicMock()
    mock_results.points = [
        MagicMock(id="vec-1"),
        MagicMock(id="vec-2"),
    ]
    mock_qdrant_client.query_points.return_value = mock_results
    mock_settings.qdrant_collection = "test"

    from core.vector_store import delete_by_metadata
    count = delete_by_metadata(mock_qdrant_client, document_name="doc1")

    assert count == 2
    mock_qdrant_client.delete.assert_called_once()


def test_delete_by_metadata_no_results(mock_qdrant_client, mock_settings):
    """Test delete_by_metadata returns 0 when no matches."""
    mock_results = MagicMock()
    mock_results.points = []
    mock_qdrant_client.query_points.return_value = mock_results
    mock_settings.qdrant_collection = "test"

    from core.vector_store import delete_by_metadata
    count = delete_by_metadata(mock_qdrant_client, document_name="nonexistent")

    assert count == 0
    mock_qdrant_client.delete.assert_not_called()


def test_delete_by_metadata_requires_filter(mock_qdrant_client):
    """Test delete_by_metadata raises error without filters."""
    with pytest.raises(ValueError, match="At least one filter"):
        from core.vector_store import delete_by_metadata
        delete_by_metadata(mock_qdrant_client)