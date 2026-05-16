# test_retrieval_agent.py Explained Simply

This file tests the RetrievalAgent - the component that finds the most relevant document chunks for a user's question. This is the first and most critical step in the RAG pipeline.

---

# 1. What Does the RetrievalAgent Do?

The RetrievalAgent finds relevant information from the vector database.

Process:

```
User Question
      ↓
Rewrite Query (make it better for search)
      ↓
Generate HyDE (hypothetical answers)
      ↓
Embed Question + HyDE
      ↓
Search Qdrant (vector similarity)
      ↓
Apply BM25 (keyword matching)
      ↓
Combine Scores (hybrid search)
      ↓
Cohere Rerank (optional)
      ↓
Return Top Chunks
```

---

# 2. The RetrievalResult Dataclass

```python
@dataclass
class RetrievalResult:
    query: str
    chunks: list[str]
    chunk_ids: list[str]
    scores: list[float]
```

This holds the retrieval output:

- **query** - The original or rewritten question
- **chunks** - The text chunks that were retrieved
- **chunk_ids** - Unique IDs for each chunk
- **scores** - Relevance scores for each chunk

---

# 3. Testing Fixtures

```python
@pytest.fixture
def mock_embedding():
    return [0.0] * 1536

@pytest.fixture
def mock_search_results():
    return [
        {"id": "chunk-1", "score": 0.92, "payload": {"text": "RAG combines retrieval and generation."}},
        {"id": "chunk-2", "score": 0.85, "payload": {"text": "RAGAS evaluates RAG pipelines."}},
    ]
```

These fixtures provide mock data for tests:

- **mock_embedding** - A 1536-dimensional zero vector (standard OpenAI embedding size)
- **mock_search_results** - Fake Qdrant search results

---

# 4. Testing Basic Retrieval

```python
def test_retrieval_agent_returns_result(mock_search_results, mock_openai_responses, mock_openai_embeddings):
    with (
        patch("agents.retrieval_agent._openai") as mock_openai,
    ):
        mock_openai.responses.create.return_value = mock_openai_responses
        mock_openai.embeddings.create.return_value = mock_openai_embeddings
        with patch("agents.retrieval_agent.get_qdrant_client"):
            with patch("agents.retrieval_agent.search_vectors", return_value=mock_search_results):
                with patch.object(RetrievalAgent, "_cohere_rerank", return_value=mock_search_results):
                    agent = RetrievalAgent(top_k=2)
                    result = agent.run("What is RAG?")

    assert isinstance(result, RetrievalResult)
    assert result.query == "What is RAG?"
    assert len(result.chunks) == 2
```

Tests that retrieval returns a populated result.

Everything is mocked: OpenAI, Qdrant, Cohere.

---

# 5. Testing Empty Results

```python
def test_retrieval_agent_empty_results(mock_openai_responses, mock_openai_embeddings):
    with (
        patch("agents.retrieval_agent._openai") as mock_openai,
    ):
        mock_openai.responses.create.return_value = mock_openai_responses
        mock_openai.embeddings.create.return_value = mock_openai_embeddings

        with patch("agents.retrieval_agent.get_qdrant_client"):
            with patch("agents.retrieval_agent.search_vectors", return_value=[]):
                with patch.object(RetrievalAgent, "_cohere_rerank", return_value=[]):
                    agent = RetrievalAgent()
                    result = agent.run("Unknown topic")

    assert result.chunks == []
    assert result.chunk_ids == []
    assert result.scores == []
```

Tests that the agent handles empty results gracefully.

---

# 6. Why Handle Empty Results?

If the search finds nothing, the system should not crash.

It should return empty lists and let the pipeline continue.

Later, the generator can explain that no relevant information was found.

---

# 7. Testing Text Normalization

```python
def test_normalize_text():
    agent = RetrievalAgent()

    result = agent._normalize_text("Hello    world\n\nAI")
    assert result == "Hello world AI"
```

Tests the _normalize_text helper that cleans whitespace.

Before: "Hello    world\n\nAI"
After: "Hello world AI"

---

# 8. Why Normalize Text?

Text normalization:

- Removes extra spaces and newlines
- Makes embeddings more consistent
- Improves BM25 scoring accuracy

---

# 9. Testing Tokenization

```python
def test_tokenize():
    agent = RetrievalAgent()

    result = agent._tokenize("AI is Awesome!")
    assert result == ["ai", "is", "awesome"]
```

Tests the _tokenize method that splits text into words.

It converts to lowercase and extracts word tokens.

---

# 10. What is Tokenization?

Tokenization breaks text into individual words/tokens.

Example:

```
"AI is Awesome!" → ["ai", "is", "awesome"]
```

Tokenization is needed for BM25 scoring - BM25 counts word occurrences.

---

# 11. Testing Deduplication

```python
def test_dedupe_candidates():
    agent = RetrievalAgent()
    candidates = [
        {"id": "chunk-1", "score": 0.9, "payload": {"text": "Text 1"}},
        {"id": "chunk-1", "score": 0.7, "payload": {"text": "Text 1"}},
        {"id": "chunk-2", "score": 0.8, "payload": {"text": "Text 2"}},
    ]

    result = agent._dedupe_candidates(candidates)

    assert len(result) == 2
    assert any(item["id"] == "chunk-1" and item["score"] == 0.9 for item in result)
```

Tests deduplication - removing duplicate chunks.

If the same chunk appears multiple times, keep only the highest-scoring one.

---

# 12. Why Deduplicate?

The original query and HyDE searches may return the same chunk.

Duplicates would:

- Waste space in the context
- Potentially bias the generator
- Confuse the reranking

Deduplication ensures unique chunks.

---

# 13. Testing BM25 Scoring

```python
def test_bm25_scores():
    agent = RetrievalAgent()
    texts = [
        ["rag", "is", "retrieval"],
        ["rag", "is", "generation"],
        ["llm", "is", "model"],
    ]
    query = ["rag"]

    scores = agent._bm25_scores(texts, query)

    assert len(scores) == 3
    assert scores[0] > 0
    assert scores[1] > 0
    assert scores[2] == 0
```

Tests BM25 scoring - keyword-based relevance.

The first two documents contain "rag", so they get positive scores.
The third document does not contain "rag", so it gets 0.

---

# 14. What is BM25?

BM25 is a classic information retrieval algorithm.

It ranks documents by keyword overlap:

- Term Frequency (TF) - How often does the word appear?
- Inverse Document Frequency (IDF) - How rare is the word?

BM25 is different from embeddings (semantic similarity) - it matches exact words.

---

# 15. Testing Hybrid Scoring

```python
def test_score_candidates(mock_search_results):
    agent = RetrievalAgent()
    agent.dense_weight = 0.7
    agent.sparse_weight = 0.3

    result = agent._score_candidates("what is rag", mock_search_results)

    assert len(result) == 2
    assert result[0]["score"] >= result[1]["score"]
```

Tests hybrid scoring - combining dense (embedding) and sparse (BM25) scores.

- dense_weight 0.7 - Semantic similarity is 70% of the score
- sparse_weight 0.3 - Keyword matching is 30% of the score

---

# 16. Why Hybrid Search?

- **Dense (Embeddings)** - Understand meaning, find semantically similar
- **Sparse (BM25)** - Match exact keywords

Each has strengths and weaknesses:

- Dense: Finds related concepts but misses exact terms
- Sparse: Matches exact terms but misses synonyms

Hybrid combines both for better results.

---

# 17. Testing HyDE Expansion

```python
def test_hyde_expand_returns_list(mock_openai_responses):
    mock_openai_responses.output_text = "Answer 1\nAnswer 2\nAnswer 3"

    with patch("agents.retrieval_agent._openai") as mock_openai:
        mock_openai.responses.create.return_value = mock_openai_responses

        agent = RetrievalAgent()
        result = agent._hyde_expand("What is RAG?")

    assert isinstance(result, list)
    assert len(result) <= agent.hyde_count
```

Tests HyDE (Hypothetical Document Embeddings) expansion.

The LLM generates fake answers, which are used to improve retrieval.

---

# 18. What is HyDE?

HyDE = Hypothetical Document Embeddings

Instead of just searching the query, the system:

1. Asks the LLM "What would a good answer look like?"
2. Embeds those hypothetical answers
3. Searches with the hypothetical answers

This helps find relevant documents because the hypothetical answers contain richer semantic information.

---

# 19. Testing Cohere Rerank

```python
def test_cohere_rerank_skips_without_api_key(mock_search_results):
    with patch("agents.retrieval_agent._settings") as mock_settings:
        mock_settings.cohere_api_key = None

        agent = RetrievalAgent()
        result = agent._cohere_rerank("query", mock_search_results)

    assert result == mock_search_results
```

Tests that reranking is skipped when no API key is provided.

When Cohere is disabled, return the original results unchanged.

---

# 20. Summary of Tests

| Test | What It Checks |
|------|----------------|
| test_retrieval_agent_returns_result | Basic retrieval works |
| test_retrieval_agent_empty_results | Empty results handled |
| test_normalize_text | Text cleaning works |
| test_tokenize | Tokenization works |
| test_dedupe_candidates | Deduplication works |
| test_bm25_scores | BM25 scoring works |
| test_score_candidates | Hybrid scoring works |
| test_hyde_expand_returns_list | HyDE expansion works |
| test_cohere_rerank_skips_without_api_key | Reranking optional |

---

# Why Test the Retrieval Agent?

Retrieval is the foundation of RAG - if you retrieve wrong content, the answer will be wrong.

Tests ensure:

- Retrieval returns correct structure
- Text processing works properly
- Hybrid scoring combines correctly
- HyDE expansion works
- Edge cases are handled

This is the most tested file because retrieval quality determines overall RAG quality.