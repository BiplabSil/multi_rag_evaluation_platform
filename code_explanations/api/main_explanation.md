# 1. High-Level Flow of This API Main

The complete flow is:

```text
Environment Variables
        ↓
Load Settings
        ↓
Configure LangSmith (optional)
        ↓
Create FastAPI App
        ↓
Add CORS Middleware
        ↓
Include Router
        ↓
Ready to Serve
```

---

# 2. What is FastAPI?

FastAPI is a modern Python web framework.

Used for:
- Building REST APIs
- Automatic documentation
- Type validation

Example:
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
def hello():
    return {"message": "Hello!"}
```

---

# 3. Imports Explained

```python
import logging
import os
import sys
```

Standard library modules:
- logging: for structured logging
- os: for environment variables
- sys: for system configuration

---

```python
from core.config import get_settings
```

Custom module to load application settings.

---

# 4. Settings & Configuration

```python
_settings = get_settings()
```

Loads all settings at startup:
- API keys
- Database credentials
- Feature flags

---

# 5. LangSmith Tracing Setup

```python
if _settings.langsmith_tracing.lower() == "true":
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_ENDPOINT"] = _settings.langsmith_endpoint
    os.environ["LANGSMITH_API_KEY"] = _settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = _settings.langsmith_project
```

---

## What is LangSmith?

LangSmith = LangChain's debugging and tracing service.

It records:
- Every LLM call
- Chain execution
- Tokens used
- Latency

---

## Why Set It Here?

Because:
- Must be configured BEFORE importing agent modules
- Those modules may initialize tracing on import
- Sets environment variables for all downstream code

---

## Only When Enabled

```python
if _settings.langsmith_tracing.lower() == "true"
```

Tracing is optional.

Most users: disabled.
Debugging: enabled.

---

# 6. FastAPI App Creation

```python
app = FastAPI(
    title="Multi-Agent RAG Evaluation Platform",
    description=(
        "Ingest documents, query them with a multi-agent RAG pipeline, "
        "and get automatic RAGAS quality metrics per response."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
```

---

## Configuration

| Parameter | Purpose |
|-----------|---------|
| title | API name in documentation |
| description | What the API does |
| version | Version number |
| docs_url | Swagger UI at /docs |
| redoc_url | Alternative docs at /redoc |

---

## Why Two Docs?

- **Swagger UI** (/docs): Interactive, can test directly
- **ReDoc** (/redoc): Clean, readable documentation

Both auto-generated from route definitions.

---

# 7. CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _settings.app_env == "development" else [],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## What is CORS?

CORS = Cross-Origin Resource Sharing

Controls which web pages can access your API.

---

## Development vs Production

| Environment | allow_origins |
|-------------|---------------|
| development | ["*"] (everyone) |
| production | [] (none) |

---

## Why?

Development:
- Frontend runs on different port
- Need to test locally

Production:
- Security: restrict to specific domains
- Prevent unauthorized access

---

# 8. Router Inclusion

```python
app.include_router(router)
```

Includes all API routes defined in routes.py.

---

# 9. Logging Setup

```python
logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, _settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
```

---

## Format Breakdown

```
2024-01-15 10:30:45 | INFO     | api.routes | Request received
```

| Part | Meaning |
|------|---------|
| asctime | Timestamp |
| levelname | INFO/WARNING/ERROR |
| name | Module name (logger) |
| message | What happened |

---

## Level Control

```python
level=getattr(logging, _settings.log_level.upper(), logging.INFO)
```

Reads from settings:
- DEBUG: lots of detail
- INFO: normal operations
- WARNING: problems
- ERROR: failures

---

# 10. Lifespan Context Manager

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Qdrant collection and indexes on startup."""
    try:
        client = get_qdrant_client()
        ensure_collection(client)
        logging.info("Qdrant collection and indexes initialized")
    except Exception as exc:
        logging.warning(f"Could not initialize Qdrant collection: {exc}")
    yield
```

---

## What is asynccontextmanager?

This creates a context manager for startup/shutdown logic.

It runs when the server **starts** (before yield) and can run cleanup code **after** yield when the server stops.

---

## What Happens on Startup?

1. `get_qdrant_client()` - Connect to Qdrant
2. `ensure_collection(client)` - Create collection + indexes
3. Create metadata indexes for document_name, document_version, document_id

---

## Why Handle Errors?

```python
except Exception as exc:
    logging.warning(f"Could not initialize Qdrant collection: {exc}")
```

If Qdrant is not available, the app still starts. The API can work without Qdrant for metrics viewing and health checks.

---

## App Uses Lifespan

```python
app = FastAPI(
    lifespan=lifespan,  # ← This connects the lifespan
    title="Multi-Agent RAG Evaluation Platform",
    ...
)
```

---

# 11. Startup Flow

```
1. Python loads this file
2. get_settings() runs
3. LangSmith configured (if enabled)
4. FastAPI app created (with lifespan)
5. CORS middleware added
6. Router included
7. Server starts → Lifespan runs → Qdrant initialized
8. Ready to receive requests!
```

---

# 12. Running the API

```bash
uvicorn api.main:app --reload --port 8000
```

This command:
- Loads the app from api.main module
- Starts server on port 8000
- --reload: auto-restart on code changes

---

# 12. What Happens When Request Arrives

```
Request → FastAPI
    ↓
Match route (/api/ingest, /api/query, etc.)
    ↓
Call route handler in routes.py
    ↓
Return response
```

---

# 13. Architecture Summary

```
┌─────────────────────────────────────────────┐
│              api/main.py                     │
├─────────────────────────────────────────────┤
│                                              │
│  ┌──────────────┐    ┌──────────────┐       │
│  │  Settings    │───▶│   FastAPI    │       │
│  │  (config)    │    │    App       │       │
│  └──────────────┘    └──────┬───────┘       │
│         │                    │               │
│         │           ┌───────▼───────┐       │
│         │           │    Router     │       │
│         │           │   (routes)    │       │
│         │           └───────────────┘       │
│         │                                   │
│  ┌──────▼──────┐                            │
│  │ LangSmith   │  (optional tracing)        │
│  │  (tracing)  │                            │
│  └─────────────┘                            │
│                                              │
└─────────────────────────────────────────────┘
```

---

# 14. Why This Setup Is Production-Grade

| Feature | Purpose |
|---------|---------|
| Environment-based CORS | Secure in prod, easy in dev |
| LangSmith tracing | Debug complex agent flows |
| Structured logging | Easy to search/filter |
| Version in docs | Track API changes |
| Auto docs | Self-documenting API |
| Settings from config | No hardcoded values |

---

# 15. Industry-Level Understanding

This is a standard FastAPI production setup:

- **Middleware pattern**: Cross-cutting concerns (CORS, logging)
- **Router pattern**: Clean separation of endpoints
- **Settings pattern**: Environment-based configuration
- **Logging pattern**: Structured, searchable logs

These patterns scale to enterprise applications.