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
