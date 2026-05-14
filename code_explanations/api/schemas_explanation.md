# 1. High-Level Flow of This Schemas Module

The complete flow is:

```text
Pydantic Models (Request/Response Schemas)
        ↓
Used by FastAPI Routes
        ↓
Validates Input / Formats Output
        ↓
Generated Documentation
```

---

# 2. What is Pydantic?

Pydantic is a Python library for data validation.

Example:
```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int
```

Automatically:
- Validates types
- Converts data
- Generates documentation

---

# 3. Why Separate Schemas?

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ API Routes  │ ←──→ │   Schemas   │ ←──→ │    DB/      │
│  (logic)    │      │ (contracts) │      │   External │
└─────────────┘      └─────────────┘      └─────────────┘
```

- Routes handle logic
- Schemas handle data format
- Database handles storage

Separation = independent evolution.

---

# 4. Imports Explained

```python
from datetime import datetime
```

For timestamps in responses.

---

```python
from typing import Any
```

For flexible dictionary values.

---

```python
from pydantic import BaseModel, Field
```

- BaseModel: creates validated data classes
- Field: adds validation rules and descriptions

---

# 5. Ingest Schema

## IngestRequest

```python
class IngestRequest(BaseModel):
    source: str = Field(..., description="File path or URL to ingest.")
    source_type: str = Field(..., pattern="^(pdf|txt|url)$")
    document_name: str | None = Field(None, description="...")
    document_version: str | None = Field(None, description="...")
```

---

## Fields Explained

| Field | Type | Purpose |
|-------|------|---------|
| source | str | File path or URL (required) |
| source_type | str | Must be pdf, txt, or url |
| document_name | str? | Optional human-readable name |
| document_version | str? | Optional version string |

---

## Field(...) Syntax

```python
Field(..., description="...")
```

- ... = required (no default)
- description = shows in documentation

---

## Pattern Validation

```python
pattern="^(pdf|txt|url)$"
```

Only these three values allowed.

Example:
```python
source_type: "pdf"  ✅ valid
source_type: "doc"  ❌ invalid
```

---

## IngestResponse

```python
class IngestResponse(BaseModel):
    document_id: str
    filename: str
    document_name: str | None = None
    document_version: str | None = None
    total_chunks: int
    message: str = "Document ingested successfully."
```

---

# 6. Metadata Search Schema

## MetadataSearchRequest

```python
class MetadataSearchRequest(BaseModel):
    document_name: str | None = Field(None, description="Filter by...")
    document_version: str | None = Field(None, description="Filter by...")
```

Both optional:
- Can search by name only
- Can search by version only
- Can search by both

---

## MetadataSearchResponse

```python
class MetadataSearchResponse(BaseModel):
    results: list[dict[str, Any]]
    total: int
```

Returns:
- list of matching chunks
- count of total results

---

# 7. Document Delete Schema

## DocumentDeleteRequest

```python
class DocumentDeleteRequest(BaseModel):
    document_name: str | None = None
    document_version: str | None = None
    document_id: str | None = None
```

Three ways to identify documents to delete:
1. By name
2. By version
3. By internal ID

---

## DocumentDeleteResponse

```python
class DocumentDeleteResponse(BaseModel):
    deleted_count: int
    message: str
```

Returns how many chunks were deleted.

---

# 8. Query Schema

## QueryRequest

```python
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="User's question")
    ground_truth: str | None = Field(None, description="Optional reference answer")
```

---

## min_length=3

Minimum 3 characters in question.

```python
question: "What"   ❌ too short
question: "What is RAG?"  ✅ valid
```

---

## ground_truth

Optional reference answer.

Why optional?
- Not required for most metrics
- Only needed for context_recall
- Users may not have reference answers

---

## ScoresSchema

```python
class ScoresSchema(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
```

Simple wrapper for four RAGAS scores.

---

## QueryResponse

```python
class QueryResponse(BaseModel):
    query_id: str
    question: str
    answer: str
    retrieved_chunks: list[str]
    scores: ScoresSchema
```

Complete response to client.

Includes everything:
- Original question
- Generated answer
- Chunks used
- Quality scores

---

# 9. Metrics Schema

## MetricsRow

```python
class MetricsRow(BaseModel):
    query_id: str
    question: str
    answer: str
    faithfulness: float | None
    answer_relevancy: float | None
    context_precision: float | None
    context_recall: float | None
    evaluated_at: datetime
```

One evaluation result.

---

## float | None

Some scores may be null if:
- Evaluation failed
- Metric not computed
- Database has NULL

---

## class Config

```python
class Config:
    from_attributes = True
```

Allows Pydantic to read from SQLAlchemy objects.

---

## MetricsSummary

```python
class MetricsSummary(BaseModel):
    total_queries: int
    avg_faithfulness: float
    avg_answer_relevancy: float
    avg_context_precision: float
    avg_context_recall: float
    recent: list[MetricsRow]
```

Aggregated statistics + recent history.

---

# 10. Schema Pattern Summary

| Category | Request | Response |
|----------|---------|----------|
| Ingest | IngestRequest | IngestResponse |
| Search | MetadataSearchRequest | MetadataSearchResponse |
| Delete | DocumentDeleteRequest | DocumentDeleteResponse |
| Query | QueryRequest | QueryResponse |
| Metrics | (none - GET) | MetricsSummary |

---

# 11. Why This Design Is Good

| Feature | Benefit |
|---------|---------|
| Type hints | IDE autocomplete, catching errors early |
| Field descriptions | Auto-generated documentation |
| Pattern validation | Prevents invalid values |
| Optional fields | Flexibility for different use cases |
| Separate request/response | Clear API contract |
| Pydantic BaseModel | Automatic validation + serialization |

---

# 12. FastAPI + Pydantic Magic

When you define schemas:

```python
@router.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest, ...):
```

FastAPI automatically:
1. Validates incoming JSON
2. Converts to QueryRequest
3. Runs your route function
4. Validates response against QueryResponse
5. Converts to JSON for client

All with zero boilerplate!

---

# 13. Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│                   Schemas (Contracts)                │
├─────────────────────────────────────────────────────┤
│                                                      │
│   ┌─────────────┐      ┌─────────────┐              │
│   │  Request    │      │  Response   │              │
│   │  Schemas    │      │   Schemas   │              │
│   └─────────────┘      └─────────────┘              │
│         │                    │                     │
│         ▼                    ▼                     │
│   IngestRequest        IngestResponse              │
│   QueryRequest         QueryResponse               │
│   MetricsRow           MetricsSummary              │
│                        ScoresSchema                 │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

# 14. Industry-Level Understanding

These schemas represent a typical REST API:

- **Resource-based**: Ingest, Query, Metrics map to resources
- **CRUD-ish**: POST for create/query, GET for retrieve
- **Validation**: Prevents bad data entering the system
- **Documentation**: Swagger UI shows all schemas

This pattern scales to any REST API.