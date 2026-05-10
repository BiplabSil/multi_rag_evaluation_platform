"""
models/orm.py
-------------
orm - Object Relational Mapper
SQLAlchemy ORM table definitions.

Tables:
- documents       → tracks ingested source documents
- chunks          → individual text chunks derived from documents
- queries         → user queries submitted to the platform
- eval_results    → per-query evaluation scores
"""

import datetime
import uuid

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Document(Base):
    """Represents a source document that was ingested into the platform."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf | txt | url
    total_chunks: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(Base):
    """A single text chunk derived from a Document."""

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(36), nullable=False)  # Qdrant point ID
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Query(Base):
    """A user query submitted to the RAG pipeline."""

    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text)
    retrieved_chunk_ids: Mapped[list | None] = mapped_column(JSON)  # list of Qdrant IDs
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    eval_result: Mapped["EvalResult | None"] = relationship(back_populates="query")


class EvalResult(Base):
    """RAGAS evaluation scores for a single Query."""

    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queries.id", ondelete="CASCADE"), unique=True
    )
    faithfulness: Mapped[float | None] = mapped_column(Float)
    answer_relevancy: Mapped[float | None] = mapped_column(Float)
    context_precision: Mapped[float | None] = mapped_column(Float)
    context_recall: Mapped[float | None] = mapped_column(Float)
    raw_scores: Mapped[dict | None] = mapped_column(JSON)  # full RAGAS output
    evaluated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    query: Mapped["Query"] = relationship(back_populates="eval_result")
