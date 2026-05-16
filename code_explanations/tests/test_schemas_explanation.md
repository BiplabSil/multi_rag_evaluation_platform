# test_schemas.py Explained Simply

This file tests the API schemas - the data validation models that define what data the API accepts and returns. These are written using Pydantic, a Python library for data validation.

---

# 1. What are Schemas?

Schemas define the structure of data.

Think of them like forms:

- What fields are required?
- What fields are optional?
- What values are valid?

Example:

```
IngestRequest:
  source: string (required)
  source_type: "pdf" | "txt" | "url" (required)
  document_name: string (optional)
  document_version: string (optional)
```

---

# 2. What is Pydantic?

```python
from pydantic import BaseModel

class IngestRequest(BaseModel):
    source: str
    source_type: str
```

Pydantic is a data validation library.

It automatically:

- Validates data types
- Enforces required fields
- Converts strings to proper types
- Generates documentation
- Creates type hints for editors

---

# 3. Testing IngestRequest Valid Data

```python
def test_ingest_request_valid():
    request = IngestRequest(source="/path/to/file.pdf", source_type="pdf")
    assert request.source == "/path/to/file.pdf"
    assert request.source_type == "pdf"
```

Tests that IngestRequest works with valid data.

---

# 4. Testing Source Types

```python
def test_ingest_request_all_source_types():
    for source_type in ["pdf", "txt", "url"]:
        request = IngestRequest(source="/test/file", source_type=source_type)
        assert request.source_type == source_type
```

Tests that all three source types (pdf, txt, url) are accepted.

---

# 5. What is Field Validation?

```python
class IngestRequest(BaseModel):
    source: str
    source_type: Literal["pdf", "txt", "url"]
```

The source_type is limited to specific values using Literal type.

This prevents invalid values like "doc" or "xlsx".

---

# 6. Testing Invalid Source Type

```python
def test_ingest_request_invalid_source_type():
    with pytest.raises(ValidationError):
        IngestRequest(source="/test/file", source_type="doc")
```

Tests that invalid source types are rejected.

"doc" is not in the allowed list, so Pydantic raises a ValidationError.

---

# 7. What is ValidationError?

```python
from pydantic import ValidationError
```

ValidationError is raised when data does not match the schema.

It contains:

- The error message
- The field that failed
- The invalid value

---

# 8. Testing Optional Fields

```python
def test_ingest_request_optional_fields():
    request = IngestRequest(source="/test.txt", source_type="txt")
    assert request.document_name is None
    assert request.document_version is None
```

Tests that document_name and document_version are optional.

If not provided, they default to None.

---

# 9. What is an Optional Field?

```python
class IngestRequest(BaseModel):
    source: str
    source_type: str
    document_name: str | None = None  # Optional - defaults to None
    document_version: str | None = None  # Optional - defaults to None
```

Optional fields have a default value (usually None).

They can be omitted when creating the object.

---

# 10. Testing IngestResponse

```python
def test_ingest_response():
    response = IngestResponse(
        document_id="doc-123",
        filename="test.pdf",
        total_chunks=10,
    )
    assert response.document_id == "doc-123"
    assert response.total_chunks == 10
    assert response.message == "Document ingested successfully."
```

Tests the IngestResponse schema.

This is what the API returns after successful ingestion.

---

# 11. What is a Response Schema?

```python
class IngestResponse(BaseModel):
    document_id: str
    filename: str
    total_chunks: int
    message: str = "Document ingested successfully."
```

Response schemas define what the API sends back.

The message field has a default value.

---

# 12. Testing Metadata Search

```python
def test_metadata_search_request_empty():
    request = MetadataSearchRequest()
    assert request.document_name is None
    assert request.document_version is None
```

Tests that MetadataSearchRequest works with no filters.

This allows searching all documents.

---

# 13. Testing Metadata Search With Filters

```python
def test_metadata_search_request_with_filters():
    request = MetadataSearchRequest(document_name="HR Policy", document_version="1.0")
    assert request.document_name == "HR Policy"
    assert request.document_version == "1.0"
```

Tests searching with specific filters.

This finds documents matching the name and version.

---

# 14. Testing Document Delete

```python
def test_document_delete_request_all_fields():
    request = DocumentDeleteRequest(
        document_name="HR Policy",
        document_version="1.0",
        document_id="doc-123",
    )
    assert request.document_name == "HR Policy"
    assert request.document_version == "1.0"
    assert request.document_id == "doc-123"
```

Tests the DocumentDeleteRequest schema.

Can filter by name, version, or ID.

---

# 15. Testing QueryRequest

```python
def test_query_request_valid():
    request = QueryRequest(question="What is RAG?")
    assert request.question == "What is RAG?"
```

Tests the QueryRequest schema.

The main field is the question string.

---

# 16. Testing QueryRequest With Ground Truth

```python
def test_query_request_with_ground_truth():
    request = QueryRequest(
        question="What is RAG?",
        ground_truth="RAG is retrieval-augmented generation.",
    )
    assert request.ground_truth == "RAG is retrieval-augmented generation."
```

Tests that ground_truth is optional.

Ground truth helps evaluate context recall.

---

# 17. Testing Minimum Length Validation

```python
def test_query_request_question_min_length():
    with pytest.raises(ValidationError):
        QueryRequest(question="ab")
```

Tests that questions must be at least 3 characters.

"ab" is too short, so validation fails.

---

# 18. What is Field Constraints?

```python
class QueryRequest(BaseModel):
    question: str = Field(min_length=3)
```

Constraints like min_length:

- Validate input data
- Prevent empty or too-short values
- Give clear error messages

---

# 19. Testing ScoresSchema

```python
def test_scores_schema():
    scores = ScoresSchema(
        faithfulness=0.95,
        answer_relevancy=0.90,
        context_precision=0.88,
        context_recall=0.85,
    )
    assert scores.faithfulness == 0.95
    assert scores.answer_relevancy == 0.90
```

Tests the ScoresSchema for evaluation results.

Each score is a float between 0 and 1.

---

# 20. Testing QueryResponse

```python
def test_query_response():
    response = QueryResponse(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG combines retrieval.",
        retrieved_chunks=["chunk1", "chunk2"],
        scores=ScoresSchema(...),
    )
    assert response.query_id == "qid-1"
    assert len(response.retrieved_chunks) == 2
```

Tests the complete QueryResponse schema.

This is what the /query endpoint returns.

---

# 21. Testing MetricsRow

```python
def test_metrics_row():
    from datetime import datetime
    row = MetricsRow(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG is retrieval.",
        faithfulness=0.95,
        evaluated_at=datetime.now(),
    )
    assert row.query_id == "qid-1"
    assert row.faithfulness == 0.95
```

Tests the MetricsRow schema for historical tracking.

Stores one query's results.

---

# 22. Testing Optional Scores

```python
def test_metrics_row_optional_scores():
    from datetime import datetime
    row = MetricsRow(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG is retrieval.",
        faithfulness=None,
        answer_relevancy=None,
        evaluated_at=datetime.now(),
    )
    assert row.faithfulness is None
```

Tests that score fields can be None.

Useful when scores have not been computed yet.

---

# 23. Testing MetricsSummary

```python
def test_metrics_summary():
    summary = MetricsSummary(
        total_queries=100,
        avg_faithfulness=0.85,
        avg_answer_relevancy=0.80,
        recent=[],
    )
    assert summary.total_queries == 100
    assert summary.avg_faithfulness == 0.85
```

Tests the MetricsSummary schema for aggregate statistics.

Contains averages and recent queries.

---

# 24. Summary of Tests

| Test Category | Tests |
|---------------|-------|
| Ingest Schemas | Valid, all types, invalid type, optional fields |
| Metadata Search | Empty, with filters |
| Document Delete | All fields |
| Query Schemas | Valid, with ground truth, min length |
| Scores | ScoresSchema creation |
| Response | QueryResponse with all fields |
| Metrics | MetricsRow, optional scores, MetricsSummary |

---

# Why Test Schemas?

Schemas are the contract between client and server.

Tests ensure:

- Valid data is accepted
- Invalid data is rejected
- Optional fields work correctly
- Default values are applied
- Response structure is correct

Without testing schemas, you would not know if your API accepts the right data.