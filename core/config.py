"""
core/config.py
--------------
Centralised settings loaded from environment variables via Pydantic BaseSettings.
All other modules import from here — never read os.environ directly.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide configuration.

    All values are read from environment variables (or a .env file).
    Use `get_settings()` to access a cached singleton.
    """

    # ── LLM ──────────────────────────────────────────────────────────────────
    openai_api_key: str
    openai_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # ── MySQL ─────────────────────────────────────────────────────────────────
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "ragpassword"
    mysql_database: str = "rag_eval"

    # ── Qdrant Cloud ──────────────────────────────────────────────────────────
    qdrant_url: str                           # e.g. https://xyz.us-east4-0.gcp.cloud.qdrant.io
    qdrant_api_key: str                       # Qdrant Cloud API key
    qdrant_collection: str = "rag_documents"

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

    # ── Cohere ─────────────────────────────────────────────────────────────────
    cohere_api_key: str | None = None
    cohere_rerank_model: str = "rerank-v4.0-pro"

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"

    # ── LangSmith ─────────────────────────────────────────────────────────────
    langsmith_tracing: str = "false"
    langsmith_endpoint: str = ""
    langsmith_api_key: str = ""
    langsmith_project: str = ""

    # ── GitHub Checks ─────────────────────────────────────────────────────────
    github_api_token: str = ""
    github_repo: str = ""  # owner/repo
    github_head_sha: str | None = None
    github_check_name: str = "RAGAS Evaluation"
    github_failure_threshold: float = 0.8

    #This turns a method into an attribute. Without it you'd call settings.mysql_url() with parentheses. With it, you just write settings.mysql_url like a normal variable
    @property
    def mysql_url(self) -> str:
        """SQLAlchemy-compatible MySQL connection string."""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

#Least Recently Used Cache. It means: run this function once, remember the result, and return the same object every time after that.
@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (avoids re-parsing .env on every call)."""
    return Settings()
