# 1. High-Level Flow of This Retrieval Agent

The complete flow is:

```text
User Query
   ↓
Rewrite Query
   ↓
Generate HyDE fake answers
   ↓
Convert queries to embeddings
   ↓
Search Qdrant vector DB
   ↓
Apply BM25 keyword scoring
   ↓
Combine Dense + Sparse scores
   ↓
(Optional) Cohere rerank
   ↓
Return top chunks
```

---

# 2. Imports Explained

```python
import re
```

Used for:
- cleaning text
- regex operations
- token extraction

Example:
```python
re.findall(r"\w+", "Hello World!")
```

Output:
```python
["Hello", "World"]
```

---

```python
from dataclasses import dataclass, field
```

Used to create lightweight classes.

Instead of writing:

```python
class User:
    def __init__(self, name):
        self.name = name
```

You can write:

```python
@dataclass
class User:
    name: str
```

Cleaner and easier.

---

```python
from typing import Any
```

Used for type hints.

Example:
```python
def test(data: Any):
```

Means:
- data can be anything.

---

```python
import math
```

Needed for BM25 math calculations.

---

```python
import requests
```

Used to call external APIs.

Here:
- used for Cohere rerank API.

---

```python
from collections import Counter
```

Used for counting words.

Example:

```python
Counter(["cat", "dog", "cat"])
```

Output:

```python
{"cat": 2, "dog": 1}
```

Used heavily in BM25.

---

```python
from langchain_openai import OpenAIEmbeddings
```

Used to convert text → vectors (embeddings).

Example:

```text
"I love AI"
↓
[0.123, 0.98, 0.44, ...]
```

---

```python
from openai import OpenAI
```

Used to call OpenAI models directly.

---

# 3. Config & Vector DB

```python
from core.config import get_settings
from core.vector_store import get_qdrant_client, search_vectors
```

These are custom project files.

Probably:

```python
get_settings()
```

loads:
- API keys
- model names
- retrieval settings

---

```python
get_qdrant_client()
```

connects to Qdrant vector database.

---

```python
search_vectors()
```

searches embeddings inside Qdrant.

---

# 4. Global Objects

```python
_settings = get_settings()
```

Loads application settings.

---

```python
_embeddings = OpenAIEmbeddings(
    api_key=_settings.openai_api_key,
    model=_settings.embedding_model,
)
```

Creates embedding model object.

Purpose:
- convert text → vectors.

---

```python
_openai = OpenAI(api_key=_settings.openai_api_key)
```

Creates OpenAI client.

Used for:
- query rewriting
- HyDE generation

---

# 5. RetrievalResult Dataclass

```python
@dataclass
class RetrievalResult:
```

This stores final retrieval output.

---

## Fields

```python
query: str
```

Original user query.

---

```python
chunks: list[str]
```

Retrieved text chunks.

Example:

```python
[
   "LangChain is a framework...",
   "RAG improves LLM responses..."
]
```

---

```python
chunk_ids: list[str]
```

IDs from Qdrant.

Useful for:
- tracing
- debugging
- citations

---

```python
scores: list[float]
```

Final relevance scores.

---

# 6. RetrievalAgent Class

Main retrieval engine.

---

# 7. Constructor

```python
def __init__(self, top_k: int | None = None):
```

Initializes retrieval settings.

---

## Why top_k?

Controls:
- how many chunks to return.

Example:

```python
top_k = 5
```

Means:
- return best 5 chunks.

---

## Settings

```python
self.hyde_count
```

How many fake answers to generate.

---

```python
self.hyde_search_multiplier
```

How many additional chunks to search using HyDE.

---

```python
self.bm25_candidate_multiplier
```

Increase candidate pool before reranking.

---

```python
self.dense_weight
self.sparse_weight
```

Controls hybrid scoring balance.

Example:

```python
dense = 0.7
sparse = 0.3
```

Meaning:
- semantic meaning gets 70% importance
- keyword match gets 30%

---

# 8. _normalize_text()

```python
def _normalize_text(text: str) -> str:
```

Cleans text.

---

```python
re.sub(r"\s+", " ", text).strip()
```

What it does:

Before:
```text
"Hello     world\n\nAI"
```

After:
```text
"Hello world AI"
```

Why needed?
- cleaner embeddings
- consistent scoring

---

# 9. _tokenize()

```python
re.findall(r"\w+", text.lower())
```

Converts sentence into tokens.

Example:

```text
"AI is Awesome!"
```

Becomes:

```python
["ai", "is", "awesome"]
```

Needed for BM25.

---

# 10. _rewrite_query()

VERY IMPORTANT STEP.

---

## Why rewrite query?

Users ask messy questions:

```text
"Hey can you tell me something about transformers in AI?"
```

Search works better with:

```text
"transformers architecture in artificial intelligence"
```

So LLM rewrites query.

---

## Prompt

```python
prompt = (
    "Rewrite the following user question..."
)
```

This tells LLM:
- remove noise
- preserve meaning
- make it searchable

---

## OpenAI Call

```python
response = _openai.responses.create(
```

Calls LLM.

---

## Fallback Logic

Sometimes response formats differ.

So code safely extracts text.

Very production-grade handling.

---

# 11. _hyde_expand()

MOST IMPORTANT ADVANCED RAG TECHNIQUE.

---

# What is HyDE?

HyDE = Hypothetical Document Embedding

Idea:

Instead of embedding only the query:

```text
"What is vector database?"
```

LLM first generates fake answers:

```text
"A vector database stores embeddings..."
```

Then embed those answers.

Why?

Because:
- answers contain richer semantic meaning
- embeddings become more accurate

---

# Example

Query:
```text
"What causes memory leak?"
```

HyDE may generate:

```text
"Memory leaks occur when unused memory..."
```

This retrieves better documents.

---

## Why multiple answers?

```python
self.hyde_count
```

Multiple hypothetical answers increase retrieval recall.

---

## Cleanup

```python
re.sub(r"^[\-\*\d\.\)\s]+", "", line)
```

Removes:
- bullets
- numbering

Example:

```text
"1. Memory leak occurs..."
```

Becomes:

```text
"Memory leak occurs..."
```

---

# 12. _embed_query()

```python
return _embeddings.embed_query(query)
```

Converts text → vector.

Example:

```python
[0.12, 0.98, 0.44, ...]
```

Vectors capture semantic meaning.

---

# 13. _dedupe_candidates()

Purpose:
- remove duplicate chunks.

---

Why duplicates happen?

Because:
- original query search
- multiple HyDE searches

may return same chunk.

---

Logic:

Keep only highest score per chunk ID.

---

# 14. BM25 Section

VERY IMPORTANT.

---

# What is BM25?

BM25 is classic keyword search algorithm.

Dense vectors understand meaning.

BUT:
- sometimes exact keywords matter.

Example:

Query:
```text
"Python list comprehension"
```

Exact words are important.

BM25 handles that.

---

# Key Parameters

```python
k1 = 1.5
b = 0.75
```

Industry-standard defaults.

---

# Document Frequency

```python
document_frequency.update(set(doc))
```

Counts:
- how many documents contain each word.

Used for IDF.

---

# IDF

```python
inverse_document_frequency
```

Rare words get higher weight.

Example:
- "the" → low importance
- "transformer" → high importance

---

# 15. _score_candidates()

This is HYBRID SEARCH MAGIC.

---

# Dense Search Score

Comes from embeddings.

Measures:
- semantic similarity

---

# Sparse Score

Comes from BM25.

Measures:
- keyword overlap

---

# Why combine both?

Dense alone fails sometimes:
- exact keyword search weak

Sparse alone fails sometimes:
- semantic meaning weak

Hybrid gives best of both.

---

# Normalization

```python
dense_norm = item["score"] / max_dense
```

Converts scores between 0–1.

Needed because:
- dense scores and BM25 scores have different ranges.

---

# Final Hybrid Score

```python
item["score"] =
    dense_weight * dense_norm
    +
    sparse_weight * sparse_norm
```

Weighted combination.

---

# 16. _hybrid_search()

This is actual retrieval pipeline.

---

# Step 1 — Dense Search

```python
search_vectors(client, query_vector)
```

Search Qdrant using embeddings.

---

# Step 2 — HyDE Search

Generate fake answers.

Then:
- embed fake answers
- search again

This expands search space.

---

# Step 3 — Merge Results

```python
_dedupe_candidates()
```

Remove duplicates.

---

# Step 4 — Hybrid Scoring

```python
_score_candidates()
```

Combine:
- dense
- sparse

---

# 17. _cohere_rerank()

VERY ADVANCED STEP.

---

# Why reranking?

Initial retrieval is approximate.

Reranker deeply analyzes:
- query
- documents

and improves ordering.

---

# Difference

Initial retrieval:
- fast
- approximate

Reranker:
- slower
- highly accurate

---

# Example

Initial:
```text
1. AI history
2. Vector DB
3. Embeddings
```

After rerank:
```text
1. Embeddings
2. Vector DB
3. AI history
```

---

# API Call

```python
requests.post(
    "https://api.cohere.ai/rerank"
)
```

Sends:
- query
- candidate texts

Gets:
- better relevance scores

---

# 18. run()

MAIN ENTRY POINT.

---

# Complete Flow

```python
rewritten_query = self._rewrite_query(query)
```

Clean query.

---

```python
query_vector = self._embed_query(rewritten_query)
```

Create embeddings.

---

```python
candidates = self._hybrid_search()
```

Retrieve chunks.

---

```python
final_candidates = self._cohere_rerank()
```

Improve ranking.

---

```python
selected = final_candidates[: self.top_k]
```

Take top chunks.

---

# Final Return

Returns:

```python
RetrievalResult(
    query=...,
    chunks=...,
    chunk_ids=...,
    scores=...
)
```

---

# Final Architecture Summary

```text
USER QUESTION
      ↓
QUERY REWRITE
      ↓
HyDE GENERATION
      ↓
EMBEDDINGS
      ↓
QDRANT VECTOR SEARCH
      ↓
BM25 KEYWORD SCORING
      ↓
HYBRID SCORE MERGE
      ↓
COHERE RERANK
      ↓
TOP-K CHUNKS
```

---

# Why This Retrieval System Is Strong

This is actually a very production-level RAG retrieval pipeline because it includes:

| Feature | Purpose |
|---|---|
| Query Rewrite | Better search query |
| HyDE | Better semantic retrieval |
| Dense Search | Meaning understanding |
| BM25 | Keyword matching |
| Hybrid Scoring | Combines both strengths |
| Deduplication | Removes repeated chunks |
| Cohere Rerank | Final accuracy improvement |

---

# Industry-Level Understanding

This architecture is similar to what advanced RAG systems use in:
- OpenAI
- Anthropic
- Perplexity
- enterprise search systems
- AI copilots
- document QA systems

because:
- retrieval quality matters more than LLM quality in RAG.
