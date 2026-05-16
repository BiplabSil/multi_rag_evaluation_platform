# core/config.py Explained Simply

This file is the **configuration center** of the entire application. It reads settings from environment variables and provides them to every part of the code.

---

# 1. What is Configuration?

Configuration is the set of values that your application needs to run.

Examples:
- API keys (OpenAI, Qdrant, Cohere)
- Database connection details
- Model names (gpt-4o, text-embedding-3-small)
- Chunk sizes, overlap values

Instead of hardcoding these values, they are stored in environment variables (or a .env file).

---

# 2. Pydantic BaseSettings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ...
```

**BaseSettings** is a Pydantic class that automatically:
- Reads environment variables
- Validates data types
- Provides default values
- Converts strings to proper types (e.g., "3306" → 3306)

---

# 3. Why Use Pydantic for Config?

Traditional way (manual):
```python
import os
db_host = os.environ.get("MYSQL_HOST", "localhost")
db_port = int(os.environ.get("MYSQL_PORT", "3306"))
```

Pydantic way (automatic):
```python
class Settings(BaseSettings):
    mysql_host: str = "localhost"
    mysql_port: int = 3306
```

Benefits:
- Less boilerplate code
- Type validation
- Default values in one place
- Easy to understand

---

# 4. LLM Settings

```python
# ── LLM ──────────────────────────────────────────────────────────────────
openai_api_key: str = ""
openai_model: str = "gpt-4o"
embedding_model: str = "text-embedding-3-small"
```

These settings control which AI models are used:

| Setting | Default | Purpose |
|---------|---------|---------|
| openai_api_key | "" | Your OpenAI API key |
| openai_model | gpt-4o | The LLM for generating answers |
| embedding_model | text-embedding-3-small | The model for creating embeddings |

---

# 5. MySQL Settings

```python
# ── MySQL ─────────────────────────────────────────────────────────────────
mysql_host: str = "localhost"
mysql_port: int = 3306
mysql_user: str = "root"
mysql_password: str = "ragpassword"
mysql_database: str = "rag_eval"
```

These connect to your MySQL database where query history and metrics are stored.

| Setting | Default | Purpose |
|---------|---------|---------|
| mysql_host | localhost | Database server address |
| mysql_port | 3306 | MySQL port number |
| mysql_user | root | Database username |
| mysql_password | ragpassword | Database password |
| mysql_database | rag_eval | Database name |

---

# 6. Qdrant Settings

```python
# ── Qdrant Cloud ──────────────────────────────────────────────────────────
qdrant_url: str = ""
qdrant_api_key: str = ""
qdrant_collection: str = "rag_documents"
```

These connect to Qdrant, the vector database.

| Setting | Default | Purpose |
|---------|---------|---------|
| qdrant_url | "" | Your Qdrant Cloud URL |
| qdrant_api_key | "" | Qdrant API key |
| qdrant_collection | rag_documents | Name of the collection |

---

# 7. RAG Knobs

```python
# ── RAG knobs ─────────────────────────────────────────────────────────────
chunk_size: int = 512
chunk_overlap: int = 50
top_k_retrieval: int = 5
bm25_candidate_multiplier: int = 5
hyde_generation_count: int = 3
hyde_search_multiplier: int = 2
query_rewrite_model: str = "gpt-4o-mini"
hyde_model: str = "gpt-4o-mini"
dense_sparse_mix_weight: float = 0.65
```

These "knobs" control how the RAG pipeline works:

| Knob | Default | What It Does |
|------|---------|---------------|
| chunk_size | 512 | Characters per text chunk |
| chunk_overlap | 50 | Overlap between chunks |
| top_k_retrieval | 5 | Number of chunks to return |
| bm25_candidate_multiplier | 5 | Extra candidates for BM25 |
| hyde_generation_count | 3 | Number of fake answers |
| hyde_search_multiplier | 2 | Extra search with HyDE |
| dense_sparse_mix_weight | 0.65 | Balance between semantic and keyword search |

---

# 8. Cohere Settings

```python
# ── Cohere ─────────────────────────────────────────────────────────────────
cohere_api_key: str | None = None
cohere_rerank_model: str = "rerank-v4.0-pro"
```

Optional settings for reranking (improves retrieval quality):

| Setting | Default | Purpose |
|---------|---------|---------|
| cohere_api_key | None | Your Cohere API key (optional) |
| cohere_rerank_model | rerank-v4.0-pro | Cohere reranking model |

---

# 9. App Settings

```python
# ── App ───────────────────────────────────────────────────────────────────
app_env: str = "development"
log_level: str = "INFO"
```

General application settings:

| Setting | Default | Purpose |
|---------|---------|---------|
| app_env | development | Environment (development/production) |
| log_level | INFO | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |

---

# 10. LangSmith Settings

```python
# ── LangSmith ─────────────────────────────────────────────────────────────
langsmith_tracing: str = "false"
langsmith_endpoint: str = ""
langsmith_api_key: str = ""
langsmith_project: str = ""
```

LangSmith is a tracing and debugging tool for LLM applications.

| Setting | Default | Purpose |
|---------|---------|---------|
| langsmith_tracing | "false" | Enable/disable tracing |
| langsmith_endpoint | "" | LangSmith API endpoint |
| langsmith_api_key | "" | Your LangSmith API key |
| langsmith_project | "" | Project name for organization |

---

# 11. GitHub Checks Settings

```python
# ── GitHub Checks ─────────────────────────────────────────────────────────
github_api_token: str = ""
github_repo: str = ""
github_head_sha: str | None = None
github_check_name: str = "RAGAS Evaluation"
github_failure_threshold: float = 0.1
```

These settings enable posting evaluation results as GitHub Checks:

| Setting | Default | Purpose |
|---------|---------|---------|
| github_api_token | "" | GitHub personal access token |
| github_repo | "" | Repository (owner/repo) |
| github_head_sha | None | Commit SHA to check |
| github_check_name | "RAGAS Evaluation" | Name shown in GitHub UI |
| github_failure_threshold | 0.1 | Fail if any score < this |

---

# 12. The mysql_url Property

```python
@property
def mysql_url(self) -> str:
    """SQLAlchemy-compatible MySQL connection string."""
    return (
        f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
        f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
    )
```

This property combines individual MySQL settings into a connection string.

Example output:
```
mysql+pymysql://root:ragpassword@localhost:3306/rag_eval
```

---

# 13. What is a Property?

```python
@property
def mysql_url(self) -> str:
    ...
```

A property lets you call a method like an attribute:

```python
# Without property:
url = settings.mysql_url()  # Must call with parentheses

# With property:
url = settings.mysql_url  # Just access like a variable
```

---

# 14. The Config Class

```python
class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"
```

This tells Pydantic to read from a `.env` file.

If you have:
```
MYSQL_HOST=my-server
```

The Settings class will automatically use "my-server".

---

# 15. The get_settings() Function

```python
@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (avoids re-parsing .env on every call)."""
    return Settings()
```

This function returns a cached instance of Settings.

---

# 16. What is @lru_cache?

```python
from functools import lru_cache

@lru_cache
def get_settings():
    return Settings()
```

`@lru_cache` is a decorator that caches results.

**First call:**
- Creates new Settings()
- Stores result in cache

**Subsequent calls:**
- Returns cached result immediately
- Does not re-read .env file

This improves performance because reading and parsing configuration is slow.

---

# 17. How to Use Settings

Anywhere in your code:

```python
from core.config import get_settings

settings = get_settings()

# Use settings
print(settings.openai_model)  # gpt-4o
print(settings.chunk_size)    # 512
```

Never read `os.environ` directly - always use `get_settings()`.

---

# 18. Why Centralize Config?

Having one place for all settings makes it easy to:

1. **Change values** - Edit in one place
2. **Understand the app** - See all options in one file
3. **Test** - Mock settings easily
4. **Document** - Know what values are available
5. **Validate** - Pydantic ensures types are correct

---

# Summary

config.py is the **configuration hub**:

- Defines all settings with defaults
- Reads from environment variables / .env file
- Provides cached singleton via `get_settings()`
- Converts individual settings into useful properties like `mysql_url`

Every part of the application imports settings from here, ensuring consistent configuration across the entire codebase.