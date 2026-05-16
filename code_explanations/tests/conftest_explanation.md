# conftest.py Explained Simply

This file contains **pytest fixtures** - reusable test helpers that make writing tests easier.

---

# 1. What is a Fixture?

A fixture is a function that prepares something for your tests.

Instead of writing the same setup code in every test, you define it once in a fixture.

Example:

```python
@pytest.fixture
def sample_user():
    return {"name": "Alice", "age": 25}
```

Then use it in any test:

```python
def test_user_name(sample_user):
    assert sample_user["name"] == "Alice"
```

---

# 2. pytest_configure()

```python
def pytest_configure(config):
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "test-openai-key")
    os.environ["QDRANT_URL"] = os.environ.get("QDRANT_URL", "https://test.qdrant.io")
    # ... more env vars
```

This runs **before any tests are collected**.

It sets up environment variables that the app needs:

- OPENAI_API_KEY - for testing OpenAI calls
- QDRANT_URL - for testing vector database
- MYSQL settings - for testing database

**Why use test values?**

Real API keys cost money and require network calls.

Test values are fast and free.

---

# 3. mock_settings Fixture

```python
@pytest.fixture(autouse=True)
def mock_settings():
    mock = MagicMock()
    mock.openai_api_key = "test-openai-key"
    mock.openai_model = "gpt-4o"
    mock.embedding_model = "text-embedding-3-small"
    # ... more settings
```

**autouse=True** means this fixture runs automatically for every test.

**MagicMock** creates a fake object.

Instead of loading real config from `.env`, tests use this fake object.

---

# 4. What Does mock_settings Contain?

| Field | Test Value | Purpose |
|-------|------------|---------|
| openai_api_key | test-openai-key | OpenAI API access |
| openai_model | gpt-4o | LLM model name |
| embedding_model | text-embedding-3-small | Embeddings model |
| qdrant_url | https://test.qdrant.io | Vector DB URL |
| chunk_size | 512 | Text chunk size |
| top_k_retrieval | 5 | Number of results |
| cohere_api_key | None | Optional reranking |
| mysql settings | test values | Database config |

---

# 5. patch() Context Manager

```python
with patch("core.config.get_settings", return_value=mock):
    with patch("core.vector_store._settings", mock):
        yield mock
```

This temporarily replaces real code with mocks.

```python
patch("core.config.get_settings")
```

Means: "When code calls `get_settings()`, return `mock` instead."

The `yield` keyword makes it a context manager - it runs setup, then teardown after the test.

---

# 6. mock_db_session Fixture

```python
@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.close = MagicMock()
    return session
```

Creates a fake database session for testing.

Methods like `add()`, `commit()`, `close()` do nothing (they are mocks).

**Why?** Real database calls are slow and require a database server.

---

# 7. Sample Data Fixtures

```python
@pytest.fixture
def sample_retrieval_result():
    from agents.retrieval_agent import RetrievalResult
    return RetrievalResult(
        query="What is RAG?",
        chunks=["RAG combines retrieval and generation."],
        chunk_ids=["chunk-1"],
        scores=[0.95],
    )
```

Provides ready-to-use sample data for tests.

Instead of creating RetrievalResult from scratch in every test, just use this fixture.

---

# 8. Sample Fixtures Available

| Fixture | Returns | Used By |
|---------|---------|---------|
| sample_retrieval_result | RetrievalResult | generator, evaluator tests |
| sample_generator_result | GeneratorResult | evaluator tests |
| sample_eval_scores | EvalScores | orchestrator tests |
| mock_llm | Fake LangChain LLM | generator tests |

---

# 9. Why Fixtures Matter

Fixtures make tests:

- **Faster** - no real API calls or database connections
- **Reliable** - no flaky tests due to network issues
- **Maintainable** - change config in one place
- **Readable** - test code stays clean and focused

---

# 10. How Tests Use These Fixtures

Example test using fixtures:

```python
def test_generator_produces_answer(sample_retrieval_result, mock_llm):
    with patch("agents.generator_agent._llm", mock_llm):
        agent = GeneratorAgent()
        result = agent.run(sample_retrieval_result)

    assert isinstance(result, GeneratorResult)
```

The test gets:
- `sample_retrieval_result` - fake retrieval output
- `mock_llm` - fake language model

No real calls happen. Tests run in milliseconds.

---

# Summary

conftest.py is the **test setup center**:

- Sets environment variables
- Provides mock settings
- Creates fake database sessions
- Supplies sample data

Every test file automatically gets these fixtures thanks to `autouse=True`.

This makes writing tests as simple as using the fixtures.