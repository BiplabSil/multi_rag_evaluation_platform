# test_api_integration.py Explained Simply

This file tests the FastAPI endpoints - the HTTP API that external clients use to interact with the RAG platform.

---

# 1. What is Integration Testing?

Integration tests check if different parts of the system work together.

Instead of testing a single function, you test entire workflows:

- Client sends HTTP request
- API processes request
- Returns HTTP response

This is closer to real usage than unit tests.

---

# 2. FastAPI TestClient

```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
```

**TestClient** lets you call FastAPI endpoints without running a real server.

It simulates HTTP requests and responses in memory.

---

# 3. Why Dependency Override?

```python
def override_get_db():
    yield FakeSession()

app.dependency_overrides[get_db] = override_get_db
```

FastAPI normally uses `get_db()` to get a real database connection.

We override it with `FakeSession()` - a mock that does nothing.

**Result:** API works but does not touch the real database.

---

# 4. FakeSession Class

```python
class FakeSession:
    def add(self, obj): pass
    def add_all(self, objs): pass
    def flush(self): pass
    def commit(self): pass
    def refresh(self, obj): pass
    def close(self): pass
```

This is a fake database session.

All methods are empty - they do nothing when called.

**Why?** FastAPI code expects a session object, but we do not need real database operations in tests.

---

# 5. Testing the Health Endpoint

```python
def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

This is the simplest test - check if the health check works.

**What it does:**

1. Call GET /api/health
2. Check status code is 200 (success)
3. Check response body is {"status": "ok"}

---

# 6. Testing the Ingest Endpoint

```python
def test_ingest_endpoint():
    fake_doc = MagicMock()
    fake_doc.id = "doc-abc"
    fake_doc.filename = "test.txt"
    fake_doc.total_chunks = 5

    with patch("api.routes.ingest_document", return_value=fake_doc):
        response = client.post(
            "/api/ingest",
            json={"source": "/tmp/test.txt", "source_type": "txt"},
        )

    assert response.status_code == 200
    assert data["document_id"] == "doc-abc"
    assert data["total_chunks"] == 5
```

Tests the document ingestion endpoint.

**Flow:**

1. Client POSTs to /api/ingest with JSON body
2. We mock the actual ingestion function to return a fake document
3. Check response contains the document ID and chunk count

---

# 7. Testing the Query Endpoint

```python
def test_query_endpoint():
    fake_result = PipelineResult(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG combines retrieval and generation.",
        retrieval=RetrievalResult(...),
        generation=GeneratorResult(...),
        scores=EvalScores(...),
    )

    with patch("api.routes._orchestrator.run", new=AsyncMock(return_value=fake_result)):
        response = client.post(
            "/api/query",
            json={"question": "What is RAG?"},
        )

    assert response.status_code == 200
    assert data["answer"] == "RAG combines retrieval and generation."
    assert data["scores"]["faithfulness"] == 0.95
```

Tests the main query endpoint.

**What happens:**

1. Client sends a question
2. We mock the orchestrator to return a complete pipeline result
3. API returns the answer and evaluation scores
4. We verify the response structure

---

# 8. Why Mock the Orchestrator?

```python
with patch("api.routes._orchestrator.run", new=AsyncMock(return_value=fake_result)):
```

The orchestrator does heavy work:

- Calls OpenAI for retrieval
- Calls embeddings API
- Uses Qdrant vector database
- Calls generator agent
- Calls evaluator agent

Mocking it makes tests fast and reliable.

---

# 9. What is Being Tested?

| Endpoint | Method | Tests |
|----------|--------|-------|
| /api/health | GET | Health check works |
| /api/ingest | POST | Document ingestion works |
| /api/query | POST | Query processing works |

Each test verifies:

- Correct HTTP status code
- Correct response structure
- Correct data values

---

# 10. Why This Approach Works

Testing with mocks and fakes gives:

| Benefit | Explanation |
|--------|-------------|
| Fast | No real API calls |
| Reliable | No network failures |
| Isolated | Each test is independent |
| Repeatable | Same results every time |

---

# 11. The Test Flow

```
Test Request
    ↓
FastAPI Route Handler
    ↓
Mocked Service (orchestrator, ingest_document)
    ↓
Return Fake Response
    ↓
Assertions Verify Response
```

The actual business logic is not executed - only the API layer is tested.

This is perfect for testing:

- Request validation
- Response formatting
- Error handling
- HTTP status codes

---

# 12. Key Concepts Summary

- **TestClient** - Simulates HTTP requests without a server
- **Dependency Override** - Replace real DB with fake
- **patch()** - Mock functions to return test data
- **AsyncMock** - Mock async functions for query endpoint
- **Assertions** - Verify status codes and response content

---

# Summary

test_api_integration.py tests the FastAPI HTTP layer:

- Health endpoint - basic status check
- Ingest endpoint - document upload
- Query endpoint - question answering

All tests use mocks to avoid real API calls, making tests fast and reliable.