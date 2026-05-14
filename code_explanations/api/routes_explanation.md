# 1. High-Level Flow of This Routes Module

The complete flow is:

```text
HTTP Request
        ↓
FastAPI matches route
        ↓
Call route handler
        ↓
Call agent/service
        ↓
Return response
```

---

# 2. What are Routes?

Routes = URL endpoints in an API.

Example:
```python
@router.post("/ingest")
def ingest(...):
    ...
```

This creates endpoint: POST /api/ingest

---

# 3. Imports Explained

```python
import logging
```

For tracking what happens.

---

```python
from fastapi import APIRouter, Depends, HTTPException
```

- APIRouter: groups routes
- Depends: dependency injection
- HTTPException: error responses

---

```python
from sqlalchemy import func, select
```

Database query helpers:
- func: aggregate functions (COUNT, AVG)
- select: SQL SELECT statements

---

```python
from sqlalchemy.orm import Session
```

Database session for queries.

---

```python
from agents.orchestrator import Orchestrator
```

The pipeline coordinator agent.

---

```python
from core.database import get_db
```

Database session factory.

---

```python
from core.vector_store import delete_by_metadata, get_qdrant_client, search_by_metadata
```

Qdrant vector DB functions.

---

```python
from ingestion.pipeline import ingest_document
```

Document ingestion logic.

---

# 4. Router Setup

```python
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
```

---

## prefix="/api"

All routes start with /api:
- POST /api/ingest
- POST /api/query
- GET /api/metrics

---

# 5. Orchestrator Singleton

```python
_orchestrator = Orchestrator()
```

Created once at module load.

---

## Why Singleton?

- Avoids recreating agents per request
- Expensive initialization (LLM clients)
- Shared state across requests

---

# 6. Ingest Route

```python
@router.post("/ingest", response_model=IngestResponse, tags=["Ingestion"])
def ingest(payload: IngestRequest, db: Session = Depends(get_db)):
```

---

## Flow

```
POST /api/ingest
        │
        ▼
IngestRequest (validated)
        │
        ▼
ingest_document(source, source_type, db, ...)
        │
        ▼
Returns Document object
        │
        ▼
IngestResponse (validated)
```

---

## Parameters

| Parameter | Source |
|-----------|--------|
| payload | Request body (validated) |
| db | Database session (auto-injected) |

---

## Error Handling

```python
try:
    doc = ingest_document(...)
except Exception as exc:
    logger.exception("Ingestion failed: %s", exc)
    raise HTTPException(status_code=500, detail=str(exc))
```

---

## HTTPException

| Status | Meaning |
|--------|---------|
| 500 | Internal server error |
| 400 | Bad request |
| 404 | Not found |

---

# 7. Metadata Search Route

```python
@router.post("/search-by-metadata", response_model=MetadataSearchResponse, tags=["Metadata"])
def search_by_doc_metadata(payload: MetadataSearchRequest):
```

---

## Purpose

Find chunks by metadata (name/version), not semantic search.

Use case:
- Find all chunks from "HR Policy v1.0"
- Not asking a question, just retrieving

---

## Validation

```python
if not payload.document_name and not payload.document_version:
    raise HTTPException(status_code=400, detail="...")
```

At least one filter required.

---

# 8. Document Delete Route

```python
@router.delete("/documents", response_model=DocumentDeleteResponse, tags=["Metadata"])
def delete_documents(payload: DocumentDeleteRequest):
```

---

## Use Case

Delete old document versions before uploading new ones.

Example:
- Delete "hr_policy" v1.0
- Upload v2.0
- No duplicate/old data

---

# 9. Query Route

```python
@router.post("/query", response_model=QueryResponse, tags=["Query"])
async def query(payload: QueryRequest, db: Session = Depends(get_db)):
```

---

## Async Function

```python
async def query(...)
```

Why async?
- Orchestrator uses async for evaluation
- Better performance under load

---

## Flow

```
POST /api/query
        │
        ▼
QueryRequest (question + optional ground_truth)
        │
        ▼
_orchestrator.run(question, db, ground_truth)
        │
        ▼
PipelineResult (query_id, answer, scores)
        │
        ▼
QueryResponse (validated)
```

---

## Orchestrator Call

```python
result = await _orchestrator.run(
    question=payload.question,
    db=db,
    ground_truth=payload.ground_truth,
)
```

Runs full pipeline:
1. Retrieval
2. Generation
3. Evaluation
4. Persistence

---

## Response Building

```python
return QueryResponse(
    query_id=result.query_id,
    question=result.question,
    answer=result.answer,
    retrieved_chunks=result.retrieval.chunks,
    scores=ScoresSchema(...),
)
```

Maps internal result to API response.

---

# 10. Metrics Route

```python
@router.get("/metrics", response_model=MetricsSummary, tags=["Evaluation"])
def metrics(limit: int = 20, db: Session = Depends(get_db)):
```

---

## Query Parameters

```python
limit: int = 20
```

How many recent rows to return.

---

## Aggregation Query

```python
agg = db.execute(
    select(
        func.count(EvalResult.id).label("total"),
        func.avg(EvalResult.faithfulness).label("avg_f"),
        func.avg(EvalResult.answer_relevancy).label("avg_ar"),
        func.avg(EvalResult.context_precision).label("avg_cp"),
        func.avg(EvalResult.context_recall).label("avg_cr"),
    )
).one()
```

---

## SQL Equivalent

```sql
SELECT
    COUNT(*) as total,
    AVG(faithfulness) as avg_f,
    AVG(answer_relevancy) as avg_ar,
    AVG(context_precision) as avg_cp,
    AVG(context_recall) as avg_cr
FROM eval_results;
```

---

## Recent Rows Query

```python
recent_rows = (
    db.execute(
        select(Query, EvalResult)
        .join(EvalResult, EvalResult.query_id == Query.id)
        .order_by(EvalResult.evaluated_at.desc())
        .limit(limit)
    )
    .all()
)
```

---

## SQL Equivalent

```sql
SELECT q.*, e.*
FROM queries q
JOIN eval_results e ON e.query_id = q.id
ORDER BY e.evaluated_at DESC
LIMIT 20;
```

---

## Response Building

```python
recent = [
    MetricsRow(
        query_id=q.id,
        question=q.question,
        answer=q.answer or "",
        faithfulness=e.faithfulness,
        ...
    )
    for q, e in recent_rows
]

return MetricsSummary(
    total_queries=agg.total or 0,
    avg_faithfulness=round(agg.avg_f or 0.0, 4),
    ...
    recent=recent,
)
```

---

## Default Values

```python
agg.total or 0       # None → 0
agg.avg_f or 0.0     # None → 0.0
```

Handles empty database gracefully.

---

# 11. Health Route

```python
@router.get("/health", tags=["Ops"])
def health():
    return {"status": "ok"}
```

---

## Purpose

Liveness probe for:
- Docker healthcheck
- Kubernetes probes
- Load balancer checks

---

## Simple Response

```json
{"status": "ok"}
```

Always returns 200 OK when service is up.

---

# 12. Tags for Documentation

```python
tags=["Ingestion"]
tags=["Query"]
tags=["Evaluation"]
tags=["Ops"]
```

Groups endpoints in Swagger UI:

```
Ingestion
  POST /api/ingest

Query
  POST /api/query

Evaluation
  GET /api/metrics

Ops
  GET /api/health
```

---

# 13. Complete Route Summary

| Method | Path | Function | Purpose |
|--------|------|----------|---------|
| POST | /api/ingest | ingest | Add document to vector DB |
| POST | /api/search-by-metadata | search_by_doc_metadata | Find chunks by metadata |
| DELETE | /api/documents | delete_documents | Remove chunks by metadata |
| POST | /api/query | query | Run full RAG pipeline |
| GET | /api/metrics | metrics | Get evaluation statistics |
| GET | /api/health | health | Health check |

---

# 14. Database Flow

```
Routes Layer
     │
     ▼
SQLAlchemy Session
     │
     ▼
SQL Queries
     │
     ▼
MySQL Database
```

---

# 15. Vector DB Flow

```
Routes Layer
     │
     ▼
Qdrant Client
     │
     ▼
Vector Operations
     │
     ▼
Qdrant Database
```

---

# 16. Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│                   Routes (API Endpoints)            │
├─────────────────────────────────────────────────────┤
│                                                      │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│   │ Ingest   │  │  Query   │  │ Metrics  │          │
│   │  Route   │  │  Route   │  │  Route   │          │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│        │             │             │                │
│        ▼             ▼             ▼                │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐           │
│   │Ingestion│   │Orchestr.│   │  SQL    │           │
│   │Pipeline │   │ Agent   │   │ Queries │           │
│   └─────────┘   └─────────┘   └─────────┘           │
│                   │                                 │
│                   ▼                                 │
│            ┌─────────────────┐                     │
│            │  Qdrant + MySQL │                     │
│            └─────────────────┘                     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

# 17. Why This Route Design Is Production-Grade

| Feature | Benefit |
|---------|---------|
| Dependency Injection | Clean testability |
| Async for heavy ops | Non-blocking I/O |
| Proper HTTP methods | RESTful design |
| Error handling | Clear failure modes |
| Request validation | Pydantic handles it |
| Response validation | Type safety end-to-end |
| Structured logging | Debugging support |
| Health check | Container orchestration |
| Tags in docs | Organized API docs |

---

# 18. Industry-Level Understanding

These routes follow REST best practices:

- **Resource-based URLs**: /documents, /metrics
- **Proper HTTP verbs**: POST for create, GET for read, DELETE for delete
- **Status codes**: 200 for success, 500 for errors
- **Validation**: Request body validated before processing
- **Separation**: Routes don't contain business logic (delegates to agents)

This scales to any REST API.