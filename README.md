# Multi-Agent RAG Evaluation Platform

A production-grade platform for evaluating Retrieval-Augmented Generation (RAG) pipelines
using multiple specialized agents, MySQL for metadata, and Qdrant for vector search.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI Layer                     │
│         /ingest  /query  /evaluate  /metrics        │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Orchestrator Agent                      │
│   Routes tasks to specialized sub-agents             │
└───┬──────────────┬──────────────┬───────────────────┘
    │              │              │
┌───▼───┐    ┌─────▼────┐  ┌─────▼──────┐
│Retrieval│  │Generator │  │Evaluator   │
│ Agent  │  │  Agent   │  │  Agent     │
└───┬───┘    └─────┬────┘  └─────┬──────┘
    │              │              │
┌───▼───┐    ┌─────▼────┐  ┌─────▼──────┐
│Qdrant │  │  OpenAI  │  │  MySQL     │
│Vector │  │   LLM    │  │  Metrics   │
│  DB   │  │          │  │    DB      │
└───────┘    └──────────┘  └────────────┘
```

## Tech Stack

| Layer        | Technology          |
|-------------|---------------------|
| API          | FastAPI + Uvicorn   |
| Agents       | LangChain Agents    |
| Vector DB    | Qdrant              |
| Metadata DB  | MySQL               |
| LLM          | OpenAI GPT-4o       |
| Embeddings   | OpenAI Ada-002      |
| Evaluation   | RAGAS Framework     |
| Containerize | Docker + Compose    |
| Testing      | Pytest              |

## Project Structure

```
rag_eval_platform/
├── agents/           # Specialized agent implementations
├── api/              # FastAPI routes and schemas
├── core/             # Config, database connections
├── evaluation/       # RAGAS-based evaluation logic
├── ingestion/        # Document loading and chunking
├── models/           # SQLAlchemy ORM models
├── services/         # Business logic layer
├── utils/            # Shared utilities
├── tests/            # Unit and integration tests
├── docker/           # Dockerfiles
└── scripts/          # Setup and migration scripts
```

## Agent Pipeline

The platform uses a **multi-agent architecture** with specialized agents:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Pipeline Flow                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   User Query                                                     │
│        │                                                         │
│        ▼                                                         │
│   ┌────────────┐                                                 │
│   │Retrieval   │  1. Query Rewrite (LLM)                         │
│   │  Agent     │  2. HyDE Expansion (fake answers)               │
│   │            │  3. Dense (embedding) + Sparse (BM25) search   │
│   │            │  4. Hybrid score fusion                         │
│   │            │  5. Cohere reranking (optional)                 │
│   └─────┬──────┘                                                 │
│         │ chunks                                                 │
│         ▼                                                        │
│   ┌────────────┐                                                 │
│   │Generator   │  1. Format context into numbered blocks         │
│   │  Agent     │  2. System prompt (anti-hallucination)          │
│   │            │  3. Call LLM with context + question           │
│   └─────┬──────┘                                                 │
│         │ answer                                                 │
│         ▼                                                        │
│   ┌────────────┐                                                 │
│   │Evaluator   │  1. RAGAS metrics computation                  │
│   │  Agent     │  2. Faithfulness, Answer Relevancy             │
│   │            │  3. Context Precision, Context Recall          │
│   └─────┬──────┘                                                 │
│         │ scores                                                 │
│         ▼                                                        │
│   ┌────────────┐                                                 │
│   │ Persist    │  1. Save Query + EvalResult to MySQL           │
│   │   Node     │  2. Return PipelineResult                       │
│   └────────────┘                                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 1. Advanced Retrieval (RetrievalAgent)

- **Query Rewrite**: LLM improves user query for better search results
- **HyDE (Hypothetical Document Embedding)**: Generate fake answers to improve semantic retrieval
- **Hybrid Search**: Combines dense (embedding-based) and sparse (BM25 keyword) search
- **Cohere Reranking**: Optional second-pass reranking for better accuracy
- **Deduplication**: Removes duplicate chunks from multiple search passes

### 2. Grounded Generation (GeneratorAgent)

- **Anti-Hallucination Prompt**: Strict system prompt prevents fabricating information
- **Context-Only Answers**: LLM can only use provided context chunks
- **Fallback Response**: Explicit "I don't know" when context is insufficient
- **Deterministic Output**: Temperature 0.0 ensures reproducible results

### 3. Automated Evaluation (EvaluatorAgent)

- **RAGAS Metrics**: Industry-standard evaluation framework
  - Faithfulness: Does answer match context?
  - Answer Relevancy: Is answer on-topic?
  - Context Precision: Are chunks relevant?
  - Context Recall: Was all information retrieved? (requires ground truth)
- **Async Execution**: Non-blocking evaluation
- **GitHub Integration**: Post results to CI/CD pipelines

### 4. Production Infrastructure

- **LangGraph Orchestration**: State machine for clean agent coordination
- **MySQL Persistence**: Stores queries, answers, and evaluation scores
- **Qdrant Vector DB**: Fast semantic search at scale
- **FastAPI API**: REST endpoints for ingestion, querying, and metrics

---

## Pros and Cons

| Feature | Pros | Cons |
|---------|------|------|
| **Hybrid Search (Dense + Sparse)** | ✅ Better accuracy than pure embedding or keyword search<br>✅ Captures both semantic meaning AND exact keywords<br>✅ Handles diverse query types well | ❌ Higher computational cost (two search paths)<br>❌ More complex to tune weights<br>❌ Slower than single-method search |
| **HyDE (Hypothetical Document Embedding)** | ✅ Significantly improves recall<br>✅ Better semantic matching<br>✅ Works well for abstract queries | ❌ Extra LLM call per query (cost)<br>❌ Latency increase<br>❌ Generated documents may mislead in edge cases |
| **Query Rewrite** | ✅ Cleans messy user queries<br>✅ Improves search precision<br>✅ Handles conversational queries | ❌ Extra LLM call (cost)<br>❌ May lose nuance in original query<br>❌ Rewritten query may not match user's intent |
| **Cohere Reranking** | ✅ Major accuracy boost<br>✅ Better precision than initial retrieval<br>✅ Handles complex relevance logic | ❌ Additional API call (cost)<br>❌ Only top candidates reranked (may miss relevant docs)<br>❌ Third-party dependency |
| **RAGAS Evaluation** | ✅ Industry-standard metrics<br>✅ Comprehensive quality assessment<br>✅ Automated, no human annotation needed | ❌ LLM-based evaluation (cost + potential inconsistency)<br>❌ Context Recall requires ground truth<br>❌ NaN values possible for edge cases |
| **Temperature 0.0 (Deterministic)** | ✅ Reproducible results<br>✅ Fair evaluation comparisons<br>✅ Consistent behavior | ❌ Less creative/nuanced answers<br>❌ May miss contextual variations<br>❌ Can't adapt to different question styles |
| **LangGraph Orchestration** | ✅ Clean state management<br>✅ Visualizable pipeline<br>✅ Easy to modify/debug<br>✅ Built-in async support | ❌ Additional abstraction layer<br>❌ More setup code<br>❌ Learning curve for team members |
| **MySQL + Qdrant Combo** | ✅ MySQL: ACID compliance, mature, familiar<br>✅ Qdrant: Fast vector search, filtering<br>✅ Clear separation of concerns | ❌ Two systems to maintain<br>❌ Data sync complexity<br>❌ Additional infrastructure cost |
| **System Prompt Anti-Hallucination** | ✅ Prevents fabrications<br>✅ Explicit fallback handling<br>✅ Grounded answers | ❌ LLM may be too conservative<br>❌ May refuse valid questions<br>❌ Prompt engineering required |

---

## Quick Start

```bash
# 1. Clone and setup environment
cp .env.example .env
# Fill in your API keys and DB credentials

# 2. Start infrastructure
docker-compose up -d mysql qdrant

# 3. Run DB migrations
python scripts/migrate.py

# 4. Start the API
uvicorn api.main:app --reload --port 8000

# 5. Ingest sample documents
python scripts/ingest_sample.py
```

## Evaluation Metrics

- **Faithfulness**: Does the answer stick to retrieved context?
- **Answer Relevancy**: Is the answer relevant to the question?
- **Context Precision**: Are retrieved chunks actually useful?
- **Context Recall**: Were all relevant chunks retrieved?

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest` | POST | Ingest documents into Qdrant |
| `/query` | POST | Run full RAG pipeline on a query |
| `/evaluate` | POST | Evaluate a question/answer/context triple |
| `/metrics` | GET | Retrieve aggregated evaluation metrics |
| `/health` | GET | Health check |

## Configuration

Key environment variables:

```
OPENAI_API_KEY=           # Required for LLM calls
QDRANT_HOST=localhost     # Qdrant connection
QDRANT_PORT=6333
MYSQL_HOST=localhost      # MySQL connection
MYSQL_PORT=3306
MYSQL_DATABASE=rag_eval
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_MODEL=gpt-4o
RERANKER_ENABLED=false    # Enable Cohere reranking
GITHUB_API_TOKEN=         # For CI integration (optional)
```

## When to Use This Platform

### Use It If:
- You need to evaluate RAG pipeline quality rigorously
- You want production-grade metrics tracking
- You need hybrid search accuracy
- You're building a system where precision matters
- You want automated evaluation without manual labeling

### Consider Alternatives If:
- Simple keyword search is sufficient
- Budget is very constrained (high LLM call count)
- You need real-time streaming responses
- Your data fits entirely in memory
- You just need quick prototyping (simpler frameworks exist)