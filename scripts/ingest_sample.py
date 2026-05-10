"""
scripts/ingest_sample.py
------------------------
Ingest a small set of sample documents to populate the platform for demos.

Creates two TXT files on-the-fly (no external assets required) and ingests
them via the ingestion pipeline.

Usage:
    python scripts/ingest_sample.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging

from core.database import db_session
from ingestion.pipeline import ingest_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_DOCS = [
    {
        "filename": "rag_overview.txt",
        "content": """
Retrieval-Augmented Generation (RAG) is a technique that combines information retrieval
with large language model generation. Instead of relying solely on the model's parametric
knowledge, RAG first retrieves relevant documents from an external knowledge base and then
conditions the generation on those retrieved documents.

The core components of a RAG system are:
1. An embedding model that converts text into dense vector representations.
2. A vector database that stores and indexes these embeddings.
3. A retrieval mechanism (typically nearest-neighbour search) that finds relevant chunks.
4. A language model that generates an answer conditioned on the retrieved context.

RAG is particularly useful for domain-specific question answering, reducing hallucination,
and keeping knowledge up-to-date without retraining the language model.
        """.strip(),
    },
    {
        "filename": "ragas_metrics.txt",
        "content": """
RAGAS (Retrieval-Augmented Generation Assessment) is an open-source framework for
evaluating RAG pipelines. It measures four core dimensions:

Faithfulness: Measures whether the generated answer is factually consistent with the
retrieved context. A low faithfulness score indicates hallucination.

Answer Relevancy: Measures how relevant the generated answer is to the user's question.
It penalises incomplete or off-topic answers.

Context Precision: Measures whether the retrieved chunks are all actually relevant to
answering the question. High precision means few irrelevant chunks were retrieved.

Context Recall: Measures whether all necessary information was present in the retrieved
context. It requires a ground-truth reference answer to compute.

All metrics are scored between 0 and 1, with 1 being best. RAGAS uses an LLM internally
to perform these evaluations, making it reference-free for faithfulness and relevancy.
        """.strip(),
    },
]

filepath = "../docs/apjAbdulKalamStory.pdf"

def main() -> None:
    """Ingest all sample documents."""
    with db_session() as db:
        # for doc in SAMPLE_DOCS:
        #     with tempfile.NamedTemporaryFile(
        #         mode="w",
        #         suffix=".txt",
        #         prefix=doc["filename"].replace(".txt", "_"),
        #         delete=False,
        #         encoding="utf-8",
        #     ) as tmp:
        #         tmp.write(doc["content"])
        #         tmp_path = tmp.name

        # Convert relative path to absolute path
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        pdf_path = project_root / "docs" / "apjAbdulKalamStory.pdf"
        
        result = ingest_document(str(pdf_path), "pdf", db)
        logger.info(
            "Ingested '%s' → document_id=%s, chunks=%d",
            pdf_path,
            result.id,
            result.total_chunks,
        )

    logger.info("Sample ingestion complete.")


if __name__ == "__main__":
    main()
