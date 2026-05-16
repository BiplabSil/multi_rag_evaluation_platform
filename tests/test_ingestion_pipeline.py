"""
tests/test_ingestion_pipeline.py
--------------------------------
Unit tests for ingestion/pipeline.py.

Mocks external dependencies (loaders, embeddings, vector store, database).
"""

from unittest.mock import MagicMock, patch

import pytest


def test_load_documents_pdf():
    """Test _load_documents with PDF source."""
    with patch("ingestion.pipeline.PyPDFLoader") as mock_loader:
        mock_loader.return_value.load.return_value = [
            MagicMock(page_content="Page 1 content"),
            MagicMock(page_content="Page 2 content"),
        ]

        from ingestion.pipeline import _load_documents
        result = _load_documents("/path/to/file.pdf", "pdf")

        assert len(result) == 2
        assert result[0] == "Page 1 content"
        mock_loader.assert_called_once_with("/path/to/file.pdf")


def test_load_documents_txt():
    """Test _load_documents with TXT source."""
    with patch("ingestion.pipeline.TextLoader") as mock_loader:
        mock_loader.return_value.load.return_value = [
            MagicMock(page_content="Text file content"),
        ]

        from ingestion.pipeline import _load_documents
        result = _load_documents("/path/to/file.txt", "txt")

        assert len(result) == 1
        assert result[0] == "Text file content"


def test_load_documents_url():
    """Test _load_documents with URL source."""
    with patch("ingestion.pipeline.WebBaseLoader") as mock_loader:
        mock_loader.return_value.load.return_value = [
            MagicMock(page_content="Web page content"),
        ]

        from ingestion.pipeline import _load_documents
        result = _load_documents("https://example.com", "url")

        assert len(result) == 1
        assert result[0] == "Web page content"


def test_load_documents_invalid_source_type():
    """Test _load_documents raises error for invalid source_type."""
    from ingestion.pipeline import _load_documents

    with pytest.raises(ValueError, match="Unsupported source_type"):
        _load_documents("/path/to/file.doc", "doc")


def test_split_text():
    """Test _split_text creates chunks from texts."""
    from ingestion.pipeline import _split_text

    texts = ["First paragraph.\n\nSecond paragraph.", "Third paragraph."]

    chunks = _split_text(texts)

    assert isinstance(chunks, list)
    assert len(chunks) > 0
    # All chunks should be strings
    assert all(isinstance(c, str) for c in chunks)


def test_split_text_empty():
    """Test _split_text handles empty input."""
    from ingestion.pipeline import _split_text

    chunks = _split_text([])
    assert chunks == []


def test_embed_texts():
    """Test _embed_texts calls OpenAI and returns embeddings."""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3]),
        MagicMock(embedding=[0.4, 0.5, 0.6]),
    ]

    with patch("ingestion.pipeline._openai") as mock_openai:
        mock_openai.embeddings.create.return_value = mock_response

        from ingestion.pipeline import _embed_texts
        result = _embed_texts(["text1", "text2"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        mock_openai.embeddings.create.assert_called_once()


def test_embed_texts_empty():
    """Test _embed_texts handles empty input."""
    with patch("ingestion.pipeline._openai") as mock_openai:
        from ingestion.pipeline import _embed_texts
        result = _embed_texts([])

        assert result == []


def test_ingest_document_full_flow(mock_db_session):
    """Test complete ingest_document flow with mocks."""
    # Mock load
    with patch("ingestion.pipeline._load_documents", return_value=["Text content"]):
        # Mock split
        with patch("ingestion.pipeline._split_text", return_value=["Chunk 1", "Chunk 2"]):
            # Mock embed
            with patch("ingestion.pipeline._embed_texts", return_value=[[0.1], [0.2]]):
                # Mock Qdrant
                with patch("ingestion.pipeline.get_qdrant_client") as mock_client:
                    with patch("ingestion.pipeline.ensure_collection"):
                        with patch("ingestion.pipeline.upsert_vectors"):
                            from ingestion.pipeline import ingest_document

                            result = ingest_document(
                                source="/test.txt",
                                source_type="txt",
                                db=mock_db_session,
                                document_name="Test Doc",
                                document_version="1.0",
                            )

    # Verify result
    assert result is not None
    assert result.filename == "test.txt"
    assert result.document_name == "Test Doc"
    assert result.version == "1.0"
    assert result.total_chunks == 2

    # Verify DB operations
    mock_db_session.add.assert_called()
    mock_db_session.add_all.assert_called()
    mock_db_session.commit.assert_called()


def test_ingest_document_url_filename(mock_db_session):
    """Test that URL source uses URL as filename."""
    with patch("ingestion.pipeline._load_documents", return_value=["Content"]):
        with patch("ingestion.pipeline._split_text", return_value=["Chunk"]):
            with patch("ingestion.pipeline._embed_texts", return_value=[[0.1]]):
                with patch("ingestion.pipeline.get_qdrant_client"):
                    with patch("ingestion.pipeline.ensure_collection"):
                        with patch("ingestion.pipeline.upsert_vectors"):
                            from ingestion.pipeline import ingest_document

                            result = ingest_document(
                                source="https://example.com/doc",
                                source_type="url",
                                db=mock_db_session,
                            )

    assert result.filename == "https://example.com/doc"


def test_ingest_document_without_optional_fields(mock_db_session):
    """Test ingest_document works without optional name/version."""
    with patch("ingestion.pipeline._load_documents", return_value=["Text"]):
        with patch("ingestion.pipeline._split_text", return_value=["Chunk"]):
            with patch("ingestion.pipeline._embed_texts", return_value=[[0.1]]):
                with patch("ingestion.pipeline.get_qdrant_client"):
                    with patch("ingestion.pipeline.ensure_collection"):
                        with patch("ingestion.pipeline.upsert_vectors"):
                            from ingestion.pipeline import ingest_document

                            result = ingest_document(
                                source="/test.pdf",
                                source_type="pdf",
                                db=mock_db_session,
                            )

    assert result.document_name is None
    assert result.version is None