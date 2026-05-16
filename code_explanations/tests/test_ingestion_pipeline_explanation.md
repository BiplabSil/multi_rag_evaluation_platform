# test_ingestion_pipeline.py Explained Simply

This file tests the ingestion pipeline - the process of loading documents, splitting them into chunks, creating embeddings, and storing them in the vector database.

---

# 1. What is Document Ingestion?

Ingestion is the process of adding documents to the RAG system.

Steps:

1. **Load** - Read the document (PDF, text, URL)
2. **Split** - Break into smaller chunks
3. **Embed** - Convert chunks to vector embeddings
4. **Store** - Save to Qdrant vector database

---

# 2. Testing Document Loading

```python
def test_load_documents_pdf():
    with patch("ingestion.pipeline.PyPDFLoader") as mock_loader:
        mock_loader.return_value.load.return_value = [
            MagicMock(page_content="Page 1 content"),
            MagicMock(page_content="Page 2 content"),
        ]

        from ingestion.pipeline import _load_documents
        result = _load_documents("/path/to/file.pdf", "pdf")

        assert len(result) == 2
        assert result[0] == "Page 1 content"
```

Tests that PDF loading works.

The code uses PyPDFLoader from LangChain to read PDF files.

---

# 3. What is PyPDFLoader?

```python
from langchain_community.document_loaders import PyPDFLoader
```

PyPDFLoader is a LangChain library that extracts text from PDF files.

It returns a list of Document objects, each with:

- page_content - The text on that page
- metadata - Page number, source, etc.

---

# 4. Testing Text File Loading

```python
def test_load_documents_txt():
    with patch("ingestion.pipeline.TextLoader") as mock_loader:
        mock_loader.return_value.load.return_value = [
            MagicMock(page_content="Text file content"),
        ]

        from ingestion.pipeline import _load_documents
        result = _load_documents("/path/to/file.txt", "txt")

        assert len(result) == 1
        assert result[0] == "Text file content"
```

Tests loading plain text files.

Uses TextLoader from LangChain.

---

# 5. Testing URL Loading

```python
def test_load_documents_url():
    with patch("ingestion.pipeline.WebBaseLoader") as mock_loader:
        mock_loader.return_value.load.return_value = [
            MagicMock(page_content="Web page content"),
        ]

        from ingestion.pipeline import _load_documents
        result = _load_documents("https://example.com", "url")

        assert len(result) == 1
        assert result[0] == "Web page content"
```

Tests loading content from web URLs.

Uses WebBaseLoader from LangChain.

---

# 6. What is WebBaseLoader?

```python
from langchain_community.document_loaders import WebBaseLoader
```

WebBaseLoader fetches a web page and extracts the text content.

It can handle:

- Static HTML pages
- Simple websites

---

# 7. Testing Invalid Source Type

```python
def test_load_documents_invalid_source_type():
    with pytest.raises(ValueError, match="Unsupported source_type"):
        _load_documents("/path/to/file.doc", "doc")
```

Tests that unsupported file types raise an error.

Currently supported: pdf, txt, url

Unsupported: doc, docx, xlsx, etc.

---

# 8. Testing Text Splitting

```python
def test_split_text():
    from ingestion.pipeline import _split_text

    texts = ["First paragraph.\n\nSecond paragraph.", "Third paragraph."]

    chunks = _split_text(texts)

    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)
```

Tests that the text splitter creates chunks.

The splitter uses RecursiveCharacterTextSplitter from LangChain.

---

# 9. What is Text Splitting?

Documents are too large to fit in the LLM's context window.

Text splitting breaks documents into smaller pieces called "chunks".

Example:

```
Original: "This is a long document with many sentences..."

Split: ["This is a long document...", "with many sentences...", ...]
```

---

# 10. Why Chunk Size Matters

| Chunk Size | Pros | Cons |
|------------|------|------|
| Small (256) | Fits in context, precise | May lose context |
| Large (1024) | More context | May exceed context limit |

The default is 512 characters with 50 character overlap.

Overlap helps keep related content together.

---

# 11. Testing Empty Input

```python
def test_split_text_empty():
    from ingestion.pipeline import _split_text

    chunks = _split_text([])

    assert chunks == []
```

Tests that empty input returns empty output.

---

# 12. Testing Embedding Creation

```python
def test_embed_texts():
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
```

Tests that embedding creation works.

Embeddings are numeric vectors that represent text meaning.

---

# 13. What are Embeddings?

Embeddings convert text into vectors (lists of numbers).

```
"cat" → [0.1, 0.3, -0.2, ...]
"dog" → [0.1, 0.3, -0.1, ...]
```

Similar concepts have similar vectors.

This allows semantic search - finding similar content by comparing vectors.

---

# 14. Testing Empty Embedding Input

```python
def test_embed_texts_empty():
    with patch("ingestion.pipeline._openai") as mock_openai:
        from ingestion.pipeline import _embed_texts
        result = _embed_texts([])

        assert result == []
```

Tests that empty text input returns empty embeddings.

---

# 15. Testing Full Ingest Flow

```python
def test_ingest_document_full_flow(mock_db_session):
    with patch("ingestion.pipeline._load_documents", return_value=["Text content"]):
        with patch("ingestion.pipeline._split_text", return_value=["Chunk 1", "Chunk 2"]):
            with patch("ingestion.pipeline._embed_texts", return_value=[[0.1], [0.2]]):
                with patch("ingestion.pipeline.get_qdrant_client"):
                    with patch("ingestion.pipeline.ensure_collection"):
                        with patch("ingestion.pipeline.upsert_vectors"):
                            result = ingest_document(
                                source="/test.txt",
                                source_type="txt",
                                db=mock_db_session,
                                document_name="Test Doc",
                                document_version="1.0",
                            )

    assert result.filename == "test.txt"
    assert result.document_name == "Test Doc"
    assert result.total_chunks == 2
```

Tests the complete ingestion flow end-to-end.

All external dependencies are mocked.

---

# 16. What is Upsert?

```python
upsert_vectors(client, points)
```

Upsert means "insert or update".

If the vector ID exists, update it. If not, insert a new one.

This allows re-indexing documents without duplicates.

---

# 17. Testing URL as Filename

```python
def test_ingest_document_url_filename(mock_db_session):
    with patch("ingestion.pipeline._load_documents", return_value=["Content"]):
        # ... more patches ...
        result = ingest_document(
            source="https://example.com/doc",
            source_type="url",
            db=mock_db_session,
        )

    assert result.filename == "https://example.com/doc"
```

Tests that when the source is a URL, the URL becomes the filename.

---

# 18. Testing Optional Fields

```python
def test_ingest_document_without_optional_fields(mock_db_session):
    # ... patches ...
    result = ingest_document(
        source="/test.pdf",
        source_type="pdf",
        db=mock_db_session,
    )

    assert result.document_name is None
    assert result.version is None
```

Tests that document_name and version are optional.

---

# 19. Summary of Tests

| Test | What It Checks |
|------|----------------|
| test_load_documents_pdf | PDF loading works |
| test_load_documents_txt | Text file loading works |
| test_load_documents_url | URL loading works |
| test_load_documents_invalid_source_type | Invalid types rejected |
| test_split_text | Text splitting works |
| test_split_text_empty | Empty input handled |
| test_embed_texts | Embedding creation works |
| test_embed_texts_empty | Empty embedding handled |
| test_ingest_document_full_flow | Full pipeline works |
| test_ingest_document_url_filename | URL becomes filename |
| test_ingest_document_without_optional_fields | Optional fields work |

---

# Why Test the Ingestion Pipeline?

The ingestion pipeline is how data enters the RAG system.

Tests ensure:

- All file types load correctly
- Text splitting works properly
- Embeddings are created correctly
- The full flow works end-to-end
- Edge cases are handled

Without testing ingestion, you would not be able to add documents to the system.