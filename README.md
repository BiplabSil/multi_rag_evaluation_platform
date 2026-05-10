# Multi-Agent RAG Evaluation Platform

An orchestration system where specialized agents handle ingestion, retrieval, generation, and self-evaluation — with a full CI/CD pipeline that auto-runs RAG evals on every PR using RAGAS/TruLens.

# skills covered

LangGraph / CrewAIRAGRAGAS evalsGitHub ActionsAWS / GCPvector DBobservability

# Wow factor
"Our CI pipeline fails the build if faithfulness drops below 0.85"

# system overview — data flow
<img width="991" height="227" alt="image" src="https://github.com/user-attachments/assets/918c17db-be44-40bc-8382-4f34e1487a9d" />

# the four agents
<img width="1022" height="305" alt="image" src="https://github.com/user-attachments/assets/254d4ff1-5cad-4b31-ac21-a8293136e93a" />
<img width="1023" height="313" alt="image" src="https://github.com/user-attachments/assets/0cca9d4d-143d-4106-98f2-e1d082840e46" />

# full tech stack
## Orchestration
LangGraph (state machine nodes) + LangChain LCEL
## LLMs
GPT-4o · Claude 3.5 Sonnet · Cohere (reranking)
## Vector DB
ChromaDB (local dev/test)
## Embeddings
text-embedding-3-large · cached in Redis
## Evaluation
RAGAS · TruLens · custom LLM-as-judge prompts
## Observability
LangSmith · OpenTelemetry → Grafana · Sentry
## Backend API
FastAPI · Celery workers · Redis broker
## Data store
local folder (raw docs, eval snapshots)
## Cloud
AWS ECS Fargate · ECR · RDS · ElastiCache (Redis)
## IaC
Terraform · modules for ECS task defs, VPC, RDS, ECR
## CI/CD
GitHub Actions · Docker multi-stage · pytest + RAGAS eval suite
## Frontend
Next.js dashboard · Recharts · real-time score streaming

# CI/CD pipeline — what runs on every PR
## 1 lint + unit tests
ruff, mypy, pytest -m unit · agent logic mocked · <60s
## 2 Docker build (multi-stage)
builder → runtime · push to ECR with SHA tag · layer cache via GitHub Actions cache
## 3 integration tests
spins up ChromaDB + Postgres in docker-compose · runs 50-query golden dataset end-to-end
## 4 RAG eval gate passfail
RAGAS scores computed · faithfulness ≥ 0.85, context_precision ≥ 0.80, answer_relevancy ≥ 0.82 · writes JSON report to S3 · posts as GitHub Check
## 5 Terraform plan (on main)
tf plan posted as PR comment · tf apply only after manual approval
## 6 deploy to ECS staging
blue/green via CodeDeploy · smoke test hits /health + /eval/latest · rollback on 5xx spike

<img width="978" height="217" alt="image" src="https://github.com/user-attachments/assets/af199181-2d62-4c7e-b0a6-567bae34d93a" />

# what makes this stand out
 Most RAG demos stop at "it retrieves and answers." This project treats RAG as a software system — with a CI gate that fails builds on quality regression, infra-as-code, observability traces, cost tracking per query, and an agent that evaluates itself. That's the gap between a demo and production engineering.
