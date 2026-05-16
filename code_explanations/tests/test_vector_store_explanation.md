# test_vector_store.py Explained Simply

This file tests the vector store module - the code that interacts with Qdrant, the vector database that stores and searches document embeddings.

---

# 1. What is a Vector Store?

A vector store is a database specifically designed to store and search vectors (lists of numbers).

Why special database?

- Regular databases store exact matches
- Vector databases find similar items by comparing numbers

Example:

```
Query vector: [0.1, 0.3, 0.5]
Database vectors: 
  - [0.1, 0.3, 0.5] ← most similar (distance: 0)
  - [0.2, 0.4, 0.6] ← similar (distance: 0.1)
  - [0.9, 0.9, 0.9] ← different (distance: 1.2)
```

---

# 2. What is Qdrant?

Qdrant is the vector database used in this project.

Features:

- Cloud-hosted (or local)
- Fast similarity search
- Metadata filtering
- Scalable to billions of vectors

---

# 3. The Mock Qdrant Client

```python
@pytest.fixture
def mock_qdrant_client():
    client = MagicMock()
    return client
```

Creates a fake Qdrant client for testing.

Instead of connecting to a real Qdrant server, we use a mock object.

---

# 4. Testing get_qdrant_client

```python
def test_get_qdrant_client(mock_settings):
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
```

Tests that the Qdrant client is created with the correct settings.

---

# 5. What is get_qdrant_client?

```python
def get_qdrant_client():
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=60,
    )
```

This function creates a Qdrant client using settings from the config.

It's called by other parts of the code that need to search the vector database.

---

# 6. Testing ensure_collection (New Collection)

```python
def test_ensure_collection_creates_new(mock_qdrant_client, mock_settings):
    mock_qdrant_client.get_collections.return_value = MagicMock(
        collections=[]
    )
    mock_settings.qdrant_collection = "test_collection"

    from core.vector_store import ensure_collection
    ensure_collection(mock_qdrant_client)

    mock_qdrant_client.create_collection.assert_called_once()
```

Tests that a new collection is created when it does not exist.

---

# 7. What is a Collection?

A collection in Qdrant is like a table in a regular database.

It contains:

- A set of vectors
- Associated payloads (text, metadata)
- Configuration (vector size, distance metric)

---

# 8. What is ensure_collection?

```python
def ensure_collection(client):
    existing = client.get_collections()
    if collection_name not in existing:
        client.create_collection(...)
```

This function:

1. Checks if collection exists
2. If not, creates it
3. If yes, does nothing

---

# 9. Testing Upsert Vectors

```python
def test_upsert_vectors(mock_qdrant_client, mock_settings):
    points = [
        {"id": "vec-1", "vector": [0.1, 0.2], "payload": {"text": "Hello"}},
        {"id": "vec-2", "vector": [0.3, 0.4], "payload": {"text": "World"}},
    ]
    mock_settings.qdrant_collection = "test_collection"

    from core.vector_store import upsert_vectors
    upsert_vectors(mock_qdrant_client, points)

    mock_qdrant_client.upsert.assert_called_once()
```

Tests that vectors are inserted into the database.

---

# 10. What is Upsert?

Upsert = "Update or Insert"

- If the ID exists: Update the vector
- If the ID does not exist: Insert new

This allows:

- Adding new documents
- Updating existing documents
- Re-indexing without duplicates

---

# 11. What is a Point?

A point is a single vector with metadata in Qdrant:

```python
{
    "id": "unique-id",
    "vector": [0.1, 0.2, 0.3],
    "payload": {
        "text": "The actual text",
        "document_name": "doc.pdf",
        "chunk_index": 5
    }
}
```

The vector is used for similarity search.
The payload stores the actual content and metadata.

---

# 12. Testing Search Vectors

```python
def test_search_vectors(mock_qdrant_client, mock_settings):
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
```

Tests searching for similar vectors.

---

# 13. What is Search?

```python
def search_vectors(client, query_vector):
    results = client.query_points(
        collection=collection_name,
        query=query_vector,
        limit=top_k,
    )
    return format_results(results)
```

Search finds the most similar vectors to the query vector.

Similarity is measured by distance (lower = more similar).

---

# 14. Testing Search by Metadata

```python
def test_search_by_metadata(mock_qdrant_client, mock_settings):
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
```

Tests filtering search results by metadata.

---

# 15. What is Metadata Filtering?

Instead of searching by vector similarity, you can filter by payload fields:

```python
search_by_metadata(client, document_name="HR Policy")
```

This returns only vectors where the document_name field equals "HR Policy".

---

# 16. Testing Metadata Filter Validation

```python
def test_search_by_metadata_requires_filter(mock_qdrant_client):
    with pytest.raises(ValueError, match="At least one filter"):
        from core.vector_store import search_by_metadata
        search_by_metadata(mock_qdrant_client)
```

Tests that at least one filter must be provided.

You cannot search without a filter - it would return too many results.

---

# 17. Testing Delete by Metadata

```python
def test_delete_by_metadata(mock_qdrant_client, mock_settings):
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
```

Tests deleting vectors by metadata filter.

---

# 18. What is Delete by Metadata?

```python
def delete_by_metadata(client, **filters):
    # 1. Search for matching vectors
    results = search_by_metadata(client, **filters)
    # 2. Extract IDs
    ids = [r["id"] for r in results]
    # 3. Delete those IDs
    client.delete(ids=ids)
    return len(ids)
```

This deletes all vectors matching the filter.

Useful for removing old versions of documents.

---

# 19. Testing Delete with No Results

```python
def test_delete_by_metadata_no_results(mock_qdrant_client, mock_settings):
    mock_results = MagicMock()
    mock_results.points = []
    mock_qdrant_client.query_points.return_value = mock_results
    mock_settings.qdrant_collection = "test"

    from core.vector_store import delete_by_metadata
    count = delete_by_metadata(mock_qdrant_client, document_name="nonexistent")

    assert count == 0
    mock_qdrant_client.delete.assert_not_called()
```

Tests that deleting non-existent vectors returns 0 and does not call delete.

---

# 20. Summary of Tests

| Test | What It Checks |
|------|----------------|
| test_get_qdrant_client | Client created with correct settings |
| test_ensure_collection_creates_new | New collection created |
| test_upsert_vectors | Vectors inserted |
| test_search_vectors | Search returns results |
| test_search_by_metadata | Metadata filtering works |
| test_search_by_metadata_requires_filter | Filter required |
| test_delete_by_metadata | Delete works |
| test_delete_by_metadata_no_results | Delete returns 0 when no matches |

---

# Why Test the Vector Store?

The vector store is where all document embeddings are stored and retrieved.

Tests ensure:

- Client connections work
- Collections are created properly
- Vectors can be inserted and searched
- Metadata filtering works
- Deletion works correctly

Without testing the vector store, you would not be able to store or retrieve documents.