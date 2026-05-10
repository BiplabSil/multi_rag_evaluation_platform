"""
ingestion/pipeline.py
---------------------
Document ingestion pipeline.

Steps:
1. Load raw text from PDF, TXT, or URL source.
2. Split into overlapping chunks.
3. Embed each chunk with OpenAI Ada-002.
4. Upsert vectors into Qdrant.
5. Persist document + chunk metadata in MySQL.
"""

import uuid
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader
from openai import OpenAI
from sqlalchemy.orm import Session

from core.config import get_settings
from core.vector_store import ensure_collection, get_qdrant_client, upsert_vectors
from models.orm import Chunk, Document

_settings = get_settings()
_openai = OpenAI(api_key=_settings.openai_api_key)


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_documents(source: str, source_type: str) -> list[str]:
    """Load raw text from a source.

    Args:
        source:      File path or URL string.
        source_type: One of ``pdf``, ``txt``, or ``url``.

    Returns:
        List of page/section strings.
    """
    if source_type == "pdf":
        loader = PyPDFLoader(source)
    elif source_type == "txt":
        loader = TextLoader(source)
    elif source_type == "url":
        loader = WebBaseLoader(source)
    else:
        raise ValueError(f"Unsupported source_type: {source_type!r}")

    docs = loader.load()
    return [d.page_content for d in docs]


# ── Chunking ──────────────────────────────────────────────────────────────────

def _split_text(texts: list[str]) -> list[str]:
    """Split a list of text strings into overlapping chunks.

    Args:
        texts: Raw text sections from the loader.

    Returns:
        Flat list of chunk strings.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=_settings.chunk_size,
        chunk_overlap=_settings.chunk_overlap,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = []
    for text in texts:
        chunks.extend(splitter.split_text(text))
    return chunks


# ── Embedding ─────────────────────────────────────────────────────────────────

def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embed a list of strings using OpenAI Ada-002.

    Args:
        texts: Strings to embed (max 2048 items per batch recommended).

    Returns:
        List of embedding vectors in the same order as ``texts``.
    """
    response = _openai.embeddings.create(
        input=texts,
        model=_settings.embedding_model,
    )
    return [item.embedding for item in response.data]


# ── Main ingest function ──────────────────────────────────────────────────────

def ingest_document(source: str, source_type: str, db: Session) -> Document:
    """Full ingestion pipeline for a single document.

    Loads, chunks, embeds, and stores the document; returns the ORM Document
    record with its auto-assigned ID.

    Args:
        source:      File path or URL.
        source_type: ``pdf``, ``txt``, or ``url``.
        db:          Active SQLAlchemy session.

    Returns:
        Persisted :class:`models.orm.Document` instance.
    """
    filename = Path(source).name if source_type != "url" else source

    # 1. Load
    raw_texts = _load_documents(source, source_type)

    # 2. Chunk
    chunks = _split_text(raw_texts)

    # 3. Embed
    vectors = _embed_texts(chunks)

    # 4. Upsert into Qdrant
    qdrant_client = get_qdrant_client()
    ensure_collection(qdrant_client)

    qdrant_points = []
    chunk_records = []
    doc_id = str(uuid.uuid4())

    for idx, (text, vector) in enumerate(zip(chunks, vectors)):
        vector_id = str(uuid.uuid4())
        qdrant_points.append(
            {
                "id": vector_id,
                "vector": vector,
                "payload": {"text": text, "document_id": doc_id, "chunk_index": idx},
            }
        )
        chunk_records.append(
            Chunk(
                document_id=doc_id,
                chunk_index=idx,
                text=text,
                vector_id=vector_id,
            )
        )

    upsert_vectors(qdrant_client, qdrant_points)

    # 5. Persist to MySQL
    document = Document(
        id=doc_id,
        filename=filename,
        source_type=source_type,
        total_chunks=len(chunks),
    )
    db.add(document)
    db.add_all(chunk_records)
    db.commit()
    db.refresh(document)

    return document
