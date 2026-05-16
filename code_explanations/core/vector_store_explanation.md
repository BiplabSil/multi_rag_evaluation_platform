# core/vector_store.py Explained Simply

This file is a thin wrapper around Qdrant - the vector database that stores document embeddings and enables similarity search. It provides simple functions for common operations like storing vectors, searching, and deleting.

---

# 1. What is a Vector Database?

A vector database stores and searches **vectors** (lists of numbers).

Regular database:
- Find exact matches
- "Give me the row where id = 123"

Vector database:
- Find similar items
- "Give me the most similar vectors to this query vector"

This is called **semantic search** - finding things by meaning, not exact text.

---

# 2. What is Qdrant?

```python
from qdrant_client import QdrantClient
```

**Qdrant** is a vector database (can be cloud-hosted or local).

It stores embeddings and enables fast similarity search.

In this project:
- Document chunks are converted to embeddings
- Embeddings are stored in Qdrant
- Queries are converted to embeddings and searched against Qdrant

---

# 3. The Settings Object

```python
from core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()
```

At module load time, we create the settings object once.

This gives us access to Qdrant URL, API key, collection name, etc.

---

# 4. get_qdrant_client()

```python
def get_qdrant_client() -> QdrantClient:
    """Return a Qdrant client connected to Qdrant Cloud."""
    return QdrantClient(
        url=_settings.qdrant_url,
        api_key=_settings.qdrant_api_key,
        timeout=60,
    )
```

This function creates a Qdrant client connected to your cloud instance.

---

# 5. What Does QdrantClient Do?

```python
QdrantClient(url=..., api_key=..., timeout=60)
```

The client is the connection to Qdrant.

It can:
- Create collections
- Add vectors
- Search for vectors
- Delete vectors
- Manage indexes

The timeout is 60 seconds - how long to wait for responses.

---

# 6. ensure_collection()

```python
def ensure_collection(client: QdrantClient, vector_size: int = 1536) -> None:
    """Create the Qdrant collection if it does not already exist."""
    existing = {c.name for c in client.get_collections().collections}
    if _settings.qdrant_collection not in existing:
        client.create_collection(...)
        _create_metadata_indexes(client)
    else:
        _ensure_metadata_indexes(client)
```

This function ensures the collection exists, creating it if needed.

---

# 7. What is a Collection?

A **collection** in Qdrant is like a table in a regular database.

It contains:
- A set of vectors (embeddings)
- Associated payloads (text, metadata)
- Configuration (vector size, distance metric)

The collection name is set in config: `"rag_documents"`

---

# 8. Why Check if Collection Exists?

```python
existing = {c.name for c in client.get_collections().collections}
if _settings.qdrant_collection not in existing:
    # Create it
else:
    # Skip creation
```

We check first to avoid errors.

If we tried to create a collection that already exists, Qdrant would raise an error.

This pattern (check then create) is called **idempotent** - running it multiple times has the same result.

---

# 9. Vector Parameters

```python
client.create_collection(
    collection_name=_settings.qdrant_collection,
    vectors_config=qdrant_models.VectorParams(
        size=vector_size,           # 1536 dimensions
        distance=qdrant_models.Distance.COSINE,  # Similarity metric
    ),
)
```

When creating a collection, we specify:

| Parameter | Value | Meaning |
|-----------|-------|---------|
| size | 1536 | Embedding dimensions (OpenAI ada-002) |
| distance | COSINE | How to measure similarity |

---

# 10. What is Cosine Distance?

**Cosine similarity** measures the angle between two vectors.

```
Vectors pointing same direction → High similarity (close to 1)
Vectors at 90° → No similarity (0)
Vectors opposite → Negative similarity (-1)
```

For embeddings:
- Similar meanings have vectors pointing in similar directions
- Cosine similarity finds those

---

# 11. Metadata Indexes

```python
def _create_metadata_indexes(client: QdrantClient) -> None:
    for field in ["document_name", "document_version", "document_id"]:
        client.create_payload_index(
            collection_name=_settings.qdrant_collection,
            field_name=field,
            field_schema=qdrant_models.KeywordIndexParams(type=KeywordIndexType.KEYWORD),
        )
```

**Indexes** make filtering by metadata faster.

Without indexes, Qdrant would scan every vector.

With indexes, it jumps directly to matching records.

The fields indexed:
- document_name - Which document this chunk belongs to
- document_version - Version of the document
- document_id - Unique ID for the document

---

# 12. upsert_vectors()

```python
def upsert_vectors(client: QdrantClient, points: list[dict[str, Any]]) -> None:
    """Insert or update a batch of vectors in Qdrant."""
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
        client.upsert(...)
```

**Upsert** means "insert or update".

If a vector with that ID exists, update it. If not, insert it.

This allows:
- Adding new documents
- Updating existing document chunks

---

# 13. What is a Point?

A **point** in Qdrant is a single vector with metadata:

```python
{
    "id": "chunk-123",
    "vector": [0.1, 0.2, 0.3, ...],  # 1536 numbers
    "payload": {
        "text": "The actual text content",
        "document_name": "report.pdf",
        "chunk_index": 5
    }
}
```

The **vector** is used for similarity search.
The **payload** stores the actual content and metadata.

---

# 14. Why Batch in 50s?

```python
for i in range(0, len(qdrant_points), 50):
    batch = qdrant_points[i : i + 50]
    client.upsert(..., points=batch)
```

Qdrant works best with batches of ~50 points.

Larger batches:
- Use more memory
- May timeout
- Risk losing entire batch on error

Smaller batches:
- More network round trips
- Slower

50 is a good balance.

---

# 15. search_vectors()

```python
def search_vectors(client: QdrantClient, query_vector: list[float], top_k: int | None = None):
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
```

This function finds the most similar vectors to a query.

---

# 16. How Search Works

```python
client.query_points(
    query=query_vector,
    limit=k,
)
```

1. Take the query vector (embedding of the user's question)
2. Compare it to all vectors in the collection
3. Return the top-k most similar

The **score** indicates similarity:
- 1.0 = identical
- 0.9 = very similar
- 0.5 = somewhat similar
- 0.1 = not similar

---

# 17. search_by_metadata()

```python
def search_by_metadata(client, document_name=None, document_version=None):
    must_conditions = []
    if document_name is not None:
        must_conditions.append(
            qdrant_models.FieldCondition(
                key="document_name",
                match=qdrant_models.MatchValue(value=document_name),
            )
        )
    # ... more conditions ...

    results = client.query_points(
        query_filter=qdrant_models.Filter(must=must_conditions),
        ...
    )
```

This function filters vectors by metadata instead of similarity.

Use case: Find all chunks from a specific document.

---

# 18. What is a Filter?

```python
qdrant_models.Filter(must=must_conditions)
```

A filter specifies which vectors to consider.

- **must** - All conditions must match (AND logic)
- **should** - At least one should match (OR logic)
- **must_not** - Must NOT match (NOT logic)

Example:
```
must: [document_name="HR Policy", document_version="1.0"]
```
This returns only chunks that are BOTH from "HR Policy" version "1.0".

---

# 19. delete_by_metadata()

```python
def delete_by_metadata(client, document_name=None, document_version=None, document_id=None):
    # 1. Build filter
    # 2. Find matching points
    # 3. Extract IDs
    # 4. Delete by ID
```

This deletes vectors matching the filter.

Use case: Remove an old version of a document.

Steps:
1. Build filter from parameters
2. Search for matching vectors
3. Get their IDs
4. Delete by IDs
5. Return count deleted

---

# 20. Summary of Functions

| Function | Purpose |
|----------|---------|
| get_qdrant_client() | Create Qdrant connection |
| ensure_collection() | Create collection if not exists |
| upsert_vectors() | Add/update vectors |
| search_vectors() | Find similar vectors |
| search_by_metadata() | Filter by metadata |
| delete_by_metadata() | Delete by metadata filter |

---

# The Flow

```
Document Ingestion:
  Text → Split → Embed → upsert_vectors() → Qdrant

Query Retrieval:
  Question → Embed → search_vectors() → Qdrant → Top chunks
```

The vector store is the backbone of RAG:
- Stores all document embeddings
- Enables fast semantic search
- Supports metadata filtering
- Allows document management

Without Qdrant, the RAG system could not find relevant information.