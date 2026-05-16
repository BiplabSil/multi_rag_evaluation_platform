# Multi-Agent RAG Evaluation Platform

A production-grade platform for evaluating Retrieval-Augmented Generation (RAG) pipelines using multiple specialized AI agents, MySQL for metadata storage, and Qdrant for vector search. This platform combines advanced retrieval techniques (hybrid search, HyDE, query rewriting) with industry-standard RAGAS evaluation metrics.

## Table of Contents

- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [MySQL Database Schema](#mysql-database-schema)
- [API Routes & How They Work](#api-routes--how-they-work)
- [Key Features & Highlights](#key-features--highlights)
- [Strengths & Weaknesses](#strengths--weaknesses)
- [Quick Start](#quick-start)
- [Configuration](#configuration)

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API Framework** | FastAPI + Uvicorn | REST API endpoints |
| **AI Agents** | LangGraph + LangChain | Multi-agent orchestration |
| **LLM** | OpenAI GPT-4o | Answer generation, query rewriting, HyDE |
| **Embeddings** | OpenAI text-embedding-3-small | Dense vector creation |
| **Vector Database** | Qdrant (Cloud) | Semantic similarity search |
| **Metadata DB** | MySQL 8.0 | Structured data persistence |
| **Evaluation** | RAGAS Framework | Quality metric computation |
| **Frontend** | React 18 + Vite | Dashboard (in `/dashboard`) |
| **Containerization** | Docker + Docker Compose | Local deployment |
| **Testing** | Pytest | Unit & integration tests |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Backend                                │
│                        http://localhost:8000                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│    │   /ingest   │    │   /query    │    │  /metrics   │                 │
│    │   (POST)    │    │   (POST)    │    │   (GET)     │                 │
│    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│           │                  │                  │                         │
│           ▼                  ▼                  ▼                         │
│    ┌─────────────────────────────────────────────────────────────────┐     │
│    │                    Orchestrator Agent                         │     │
│    │                (LangGraph State Machine)                      │     │
│    └─────────────────────────┬───────────────────────────────────────┘     │
│                              │                                              │
│           ┌──────────────────┼──────────────────┐                         │
│           ▼                  ▼                  ▼                          │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│    │ Retrieval   │    │ Generator   │    │ Evaluator   │                 │
│    │   Agent     │───▶│   Agent      │───▶│   Agent      │                 │
│    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│           │                  │                  │                         │
│           ▼                  ▼                  ▼                         │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│    │   Qdrant    │    │   OpenAI    │    │    MySQL    │                 │
│    │ (Vectors)   │    │    LLM      │    │  (Metrics)  │                 │
│    └─────────────┘    └─────────────┘    └─────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Flow (What Happens When You Query)

```
User Question
       │
       ▼
┌─────────────────┐
│ Retrieval Agent │ ──▶ Query Rewrite (LLM)
│                 │ ──▶ HyDE Expansion (synthetic answers)
│                 │ ──▶ Dense + Sparse (BM25) hybrid search
│                 │ ──▶ Optional Cohere reranking
│                 │ ──▶ Returns top-k relevant chunks
└────────┬────────┘
         │ chunks (context)
         ▼
┌─────────────────┐
│ Generator Agent │ ──▶ Format context into numbered blocks
│                 │ ──▶ Anti-hallucination system prompt
│                 │ ──▶ Call GPT-4o with context + question
│                 │ ──▶ Returns grounded answer
└────────┬────────┘
         │ answer
         ▼
┌─────────────────┐
│ Evaluator Agent│ ──▶ Compute RAGAS metrics:
│                 │     • Faithfulness
│                 │     • Answer Relevancy
│                 │     • Context Precision
│                 │     • Context Recall (if ground truth provided)
└────────┬────────┘
         │ scores
         ▼
┌─────────────────┐
│   Persist Node  │ ──▶ Save Query + EvalResult to MySQL
│                 │ ──▶ Return PipelineResult to API
└─────────────────┘
```

---

## Project Structure

```
multi_rag_evaluation_platform/
├── agents/                    # Specialized AI agents
│   ├── orchestrator.py       # LangGraph state machine coordinator
│   ├── retrieval_agent.py    # Hybrid search + HyDE + reranking
│   ├── generator_agent.py    # Grounded answer generation
│   └── evaluator_agent.py   # RAGAS metrics computation
│
├── api/                      # FastAPI application
│   ├── main.py               # App entry point + CORS setup
│   ├── routes.py             # All API endpoints
│   └── schemas.py            # Pydantic request/response models
│
├── core/                     # Core infrastructure
│   ├── config.py             # Settings from environment variables
│   ├── database.py          # MySQL connection + SQLAlchemy setup
│   └── vector_store.py      # Qdrant client + vector operations
│
├── models/                   # SQLAlchemy ORM models
│   └── orm.py               # 4 MySQL tables definition
│
├── ingestion/                # Document ingestion pipeline
│   └── pipeline.py          # Load → Chunk → Embed → Upsert
│
├── evaluation/               # Evaluation logic
│   └── batch_eval.py        # Batch evaluation scripts
│
├── dashboard/                # React frontend
│   ├── src/
│   │   ├── components/      # UI components (Ingestion, Chat, Metrics, Cleanup)
│   │   └── services/        # API client
│   └── package.json
│
├── docker/                   # Docker configuration
│   ├── docker-compose.yml   # MySQL + API containers
│   └── Dockerfile
│
├── scripts/                  # Utility scripts
│   └── migrate.py           # Database migrations
│
└── tests/                   # Unit tests
```

---

## MySQL Database Schema

The platform uses 4 MySQL tables to track the entire lifecycle of documents and queries:

### 1. `documents` - Source Document Tracking

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(36) | UUID primary key |
| `filename` | VARCHAR(255) | Original filename or URL |
| `document_name` | VARCHAR(255) | Human-readable name (optional) |
| `version` | VARCHAR(50) | Version string (e.g., "1.0") |
| `source_type` | VARCHAR(50) | `pdf`, `txt`, or `url` |
| `total_chunks` | INT | Number of chunks created |
| `created_at` | DATETIME | Timestamp of ingestion |

**Purpose**: Tracks every document ingested into the system with its metadata.

---

### 2. `chunks` - Individual Text Chunks

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(36) | UUID primary key |
| `document_id` | VARCHAR(36) | Foreign key to `documents` |
| `chunk_index` | INT | Position of chunk within document |
| `text` | TEXT | The actual chunk content |
| `vector_id` | VARCHAR(36) | Corresponding Qdrant point ID |
| `created_at` | DATETIME | Timestamp of creation |

**Purpose**: Stores individual text chunks with references to both the source document and the vector in Qdrant.

---

### 3. `queries` - User Query History

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(36) | UUID primary key |
| `question` | TEXT | Original user question |
| `answer` | TEXT | Generated answer (nullable) |
| `retrieved_chunk_ids` | JSON | List of Qdrant chunk IDs used |
| `created_at` | DATETIME | Timestamp of query |

**Purpose**: Logs every user query along with the generated answer and which chunks were retrieved.

---

### 4. `eval_results` - Evaluation Scores

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(36) | UUID primary key |
| `query_id` | VARCHAR(36) | Foreign key to `queries` (unique) |
| `faithfulness` | FLOAT | RAGAS faithfulness score |
| `answer_relevancy` | FLOAT | RAGAS answer relevancy score |
| `context_precision` | FLOAT | RAGAS context precision score |
| `context_recall` | FLOAT | RAGAS context recall score (nullable) |
| `raw_scores` | JSON | Full RAGAS output |
| `evaluated_at` | DATETIME | Timestamp of evaluation |

**Purpose**: Stores RAGAS evaluation metrics for each query, enabling trend analysis and quality monitoring.

---

## API Routes & How They Work

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ingest` | POST | Ingest a document (PDF/TXT/URL) into Qdrant + MySQL |
| `/api/query` | POST | Run full RAG pipeline and get answer + scores |
| `/api/metrics` | GET | Get aggregated evaluation statistics |
| `/api/search-by-metadata` | POST | Search chunks by document_name/version |
| `/api/documents/delete` | POST | Delete document chunks from Qdrant + MySQL |
| `/api/tables` | GET | View real-time data from all 4 MySQL tables |
| `/api/health` | GET | Health check for containers |

---

### Endpoint Details

#### `POST /api/ingest` - Document Ingestion

**Purpose**: Load a document, chunk it, embed it, and store in Qdrant + MySQL.

**Request**:
```json
{
  "source": "/path/to/document.pdf",
  "source_type": "pdf",
  "document_name": "HR Policy",
  "document_version": "1.0"
}
```

**What happens internally**:
1. Load document using LangChain loaders (PyPDFLoader/TextLoader/WebBaseLoader)
2. Split into overlapping chunks using RecursiveCharacterTextSplitter
3. Embed each chunk using OpenAI text-embedding-3-small
4. Upsert vectors to Qdrant with metadata (document_name, document_version)
5. Create Document and Chunk records in MySQL

**Response**:
```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "document_name": "HR Policy",
  "document_version": "1.0",
  "total_chunks": 42
}
```

---

#### `POST /api/query` - Run RAG Pipeline

**Purpose**: Ask a question and get a grounded answer with evaluation scores.

**Request**:
```json
{
  "question": "What is the company's remote work policy?",
  "ground_truth": "Employees can work remotely up to 3 days per week."
}
```

**What happens internally**:
1. **Retrieval Agent**:
   - Rewrite query using GPT-4o-mini
   - Generate HyDE synthetic answers
   - Perform dense (vector) + sparse (BM25) hybrid search
   - Optional: Cohere reranking
2. **Generator Agent**:
   - Format retrieved chunks as numbered context blocks
   - Apply anti-hallucination system prompt
   - Call GPT-4o with temperature=0 (deterministic)
3. **Evaluator Agent**:
   - Compute 4 RAGAS metrics
   - Use ground_truth for context_recall if provided
4. **Persist Node**:
   - Save Query + EvalResult to MySQL
   - Return complete PipelineResult

**Response**:
```json
{
  "query_id": "uuid",
  "question": "What is the company's remote work policy?",
  "answer": "According to the policy, employees can work remotely...",
  "retrieved_chunks": ["chunk1", "chunk2", ...],
  "scores": {
    "faithfulness": 0.92,
    "answer_relevancy": 0.88,
    "context_precision": 0.85,
    "context_recall": 0.78
  }
}
```

---

#### `GET /api/metrics` - Evaluation Statistics

**Purpose**: Get aggregated metrics for monitoring RAG pipeline quality.

**Response**:
```json
{
  "total_queries": 150,
  "avg_faithfulness": 0.89,
  "avg_answer_relevancy": 0.85,
  "avg_context_precision": 0.82,
  "avg_context_recall": 0.75,
  "recent": [...]
}
```

---

#### `POST /api/search-by-metadata` - Filter Old Embeddings

**Purpose**: Find chunks from specific document versions without semantic search.

**Request**:
```json
{
  "document_name": "HR Policy",
  "document_version": "1.0"
}
```

**Use case**: Filter out and identify old document versions before updating.

---

#### `POST /api/documents/delete` - Delete Documents

**Purpose**: Remove old document versions from both Qdrant and MySQL.

**Request**:
```json
{
  "document_name": "HR Policy",
  "document_version": "1.0"
}
```

**What happens internally**:
1. Find matching documents in MySQL
2. Delete chunks from MySQL (CASCADE)
3. Delete documents from MySQL
4. Delete vectors from Qdrant using metadata filters

---

#### `GET /api/tables` - Database Inspector

**Purpose**: View raw data from all 4 MySQL tables for debugging.

**Response**:
```json
{
  "documents": {"count": 5, "data": [...]},
  "chunks": {"count": 200, "data": [...]},
  "queries": {"count": 150, "data": [...]},
  "eval_results": {"count": 150, "data": [...]}
}
```

---

## Key Features & Highlights

### 1. Hybrid Search (Dense + Sparse)

Combines **dense vector search** (semantic meaning) with **BM25 sparse search** (exact keyword matching). This captures both semantic intent AND specific terminology.

- **Dense**: OpenAI embeddings capture meaning
- **Sparse**: BM25 algorithm matches exact terms
- **Fusion**: Weighted combination (default 65% dense, 35% sparse)

### 2. HyDE (Hypothetical Document Embedding)

Generates synthetic "fake" answers to the user's question, then uses those as additional search queries. This improves recall for abstract or poorly-formed queries.

- Generates 3 hypothetical answers (configurable)
- Embeds each to expand search space
- Captures concepts the original query didn't mention

### 3. Query Rewriting

Uses an LLM to clean up conversational queries into focused search prompts. Removes noise like "hey, can you tell me about..." and focuses on the core intent.

### 4. Optional Cohere Reranking

Second-pass reranking for improved precision. Takes the top candidates from hybrid search and reorders them using Cohere's rerank model.

### 5. Anti-Hallucination Prompts

Generator agent uses a strict system prompt that:
- Forces use of ONLY provided context chunks
- Requires explicit "I don't know" when insufficient
- Uses temperature=0.0 for deterministic output

### 6. Metadata Filtering & Versioning

Documents can be tagged with `document_name` and `document_version`. You can:
- Search by metadata without semantic search
- Delete old versions before uploading new ones
- Track document lineage

### 7. RAGAS Evaluation

Industry-standard metrics:
- **Faithfulness**: Does answer use only information from context?
- **Answer Relevancy**: Is answer on-topic and complete?
- **Context Precision**: Are top-ranked chunks actually relevant?
- **Context Recall**: Was all relevant information retrieved? (requires ground truth)

### 8. React Dashboard

Beautiful frontend with:
- Document ingestion UI
- Interactive chat interface
- Metrics visualization (bar charts, cards)
- Document cleanup interface

---

## Strengths & Weaknesses

| Feature | Strengths | Weaknesses |
|---------|-----------|------------|
| **Hybrid Search** | ✅ Better accuracy than pure embedding or keyword<br>✅ Captures semantic meaning AND exact keywords<br>✅ Handles diverse query types | ❌ Higher computational cost (two search paths)<br>❌ More complex weight tuning<br>❌ Slower than single-method |
| **HyDE** | ✅ Significantly improves recall<br>✅ Better semantic matching<br>✅ Works well for abstract queries | ❌ Extra LLM call per query (cost)<br>❌ Latency increase<br>❌ May mislead on edge cases |
| **Query Rewrite** | ✅ Cleans messy queries<br>✅ Improves precision<br>✅ Handles conversational input | ❌ Extra LLM call (cost)<br>⚠️ May lose nuance<br>⚠️ Rewritten query may not match intent |
| **Cohere Reranking** | ✅ Major accuracy boost<br>✅ Better precision<br>✅ Handles complex relevance | ❌ Additional API call (cost)<br>❌ Only top candidates reranked<br>❌ Third-party dependency |
| **RAGAS Evaluation** | ✅ Industry-standard metrics<br>✅ Comprehensive quality assessment<br>✅ No manual labeling needed | ❌ LLM-based evaluation (cost)<br>⚠️ Context recall needs ground truth<br>⚠️ NaN values possible |
| **Temperature 0.0** | ✅ Reproducible results<br>✅ Fair comparisons<br>✅ Consistent behavior | ❌ Less creative answers<br>❌ May miss contextual variations |
| **LangGraph Orchestration** | ✅ Clean state management<br>✅ Visualizable pipeline<br>✅ Easy debugging<br>✅ Built-in async | ❌ Additional abstraction layer<br>❌ More setup code<br>❌ Learning curve |
| **MySQL + Qdrant** | ✅ ACID compliance (MySQL)<br>✅ Fast vector search (Qdrant)<br>✅ Clear separation of concerns | ❌ Two systems to maintain<br>❌ Data sync complexity<br>❌ Additional infrastructure cost |
| **Dashboard** | ✅ Beautiful UI<br>✅ Easy to use<br>✅ Real-time metrics | ❌ React app needs npm install<br>❌ Requires separate port |

### Summary

**High Cost**: This platform makes many LLM calls per query (rewrite, HyDE, generate, evaluate). If budget is a constraint, consider disabling HyDE and query rewrite.

**Time**: Full pipeline with all features enabled takes 3-8 seconds per query due to multiple LLM calls.

**Best For**: Production systems where accuracy matters more than speed/cost.

---

## Quick Start

### Prerequisites

- Python 3.13+
- Docker & Docker Compose
- OpenAI API key
- Qdrant Cloud account

### Step 1: Clone & Setup

```bash
git clone <repository-url>
cd multi_rag_evaluation_platform

# Copy environment template
cp .env.example .env
```

### Step 2: Configure Environment

Edit `.env` with your credentials:

```env
# Required
OPENAI_API_KEY=sk-...

# Qdrant Cloud (get from https://cloud.qdrant.io/)
QDRANT_URL=https://your-cluster.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-key

# MySQL (default from docker-compose)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=raguser
MYSQL_PASSWORD=ragpassword
MYSQL_DATABASE=rag_eval
```

### Step 3: Start Infrastructure

```bash
docker-compose -f docker/docker-compose.yml up -d mysql
```

Wait for MySQL to be healthy:
```bash
docker-compose -f docker/docker-compose.yml ps
```

### Step 4: Run Migrations

```bash
python scripts/migrate.py
```

### Step 5: Start API

```bash
uvicorn api.main:app --reload --port 8000
```

### Step 6: Start Dashboard (Optional)

```bash
cd dashboard
npm install
npm run dev
```

Visit `http://localhost:5173`

---

## Configuration

Key environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | LLM for answer generation |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `CHUNK_SIZE` | `512` | Characters per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `TOP_K_RETRIEVAL` | `5` | Number of chunks to retrieve |
| `DENSE_SPARSE_MIX_WEIGHT` | `0.65` | Dense:sparse ratio (0-1) |
| `HYDE_GENERATION_COUNT` | `3` | Number of HyDE answers |
| `QUERY_REWRITE_MODEL` | `gpt-4o-mini` | LLM for query rewriting |
| `RERANKER_ENABLED` | `false` | Enable Cohere reranking |
| `COHERE_API_KEY` | (optional) | For reranking |
| `GITHUB_API_TOKEN` | (optional) | For CI/CD integration |

---

## When to Use This Platform

### Use It If:
- You need to rigorously evaluate RAG pipeline quality
- You want production-grade metrics tracking
- You need hybrid search accuracy
- You're building a system where precision matters
- You want automated evaluation without manual labeling
- You need to track and filter document versions

### Consider Alternatives If:
- Simple keyword search is sufficient
- Budget is very constrained (high LLM call count)
- You need real-time streaming responses
- Your data fits entirely in memory
- You just need quick prototyping (LangChain is simpler)