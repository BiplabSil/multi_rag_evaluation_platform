CREATE DATABASE IF NOT EXISTS rag_eval;
USE rag_eval;

-- 1. Documents table
-- tracks every source file ingested into the platform
CREATE TABLE IF NOT EXISTS documents (
    id           VARCHAR(36)  NOT NULL PRIMARY KEY,
    filename     VARCHAR(255) NOT NULL,
    source_type  VARCHAR(50)  NOT NULL,   -- pdf | txt | url
    total_chunks INT          NOT NULL DEFAULT 0,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Chunks table
-- individual text chunks derived from each document
CREATE TABLE IF NOT EXISTS chunks (
    id           VARCHAR(36)  NOT NULL PRIMARY KEY,
    document_id  VARCHAR(36)  NOT NULL,
    chunk_index  INT          NOT NULL,
    text         LONGTEXT     NOT NULL,
    vector_id    VARCHAR(36)  NOT NULL,   -- Qdrant point ID
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_chunks_document
        FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE CASCADE
);

-- 3. Queries table
-- every user question submitted to the RAG pipeline
CREATE TABLE IF NOT EXISTS queries (
    id                   VARCHAR(36) NOT NULL PRIMARY KEY,
    question             LONGTEXT    NOT NULL,
    answer               LONGTEXT,
    retrieved_chunk_ids  JSON,              -- list of Qdrant IDs
    created_at           DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Eval results table
-- RAGAS scores for each query
CREATE TABLE IF NOT EXISTS eval_results (
    id                  VARCHAR(36) NOT NULL PRIMARY KEY,
    query_id            VARCHAR(36) NOT NULL UNIQUE,
    faithfulness        FLOAT,
    answer_relevancy    FLOAT,
    context_precision   FLOAT,
    context_recall      FLOAT,
    raw_scores          JSON,
    evaluated_at        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_eval_query
        FOREIGN KEY (query_id)
        REFERENCES queries(id)
        ON DELETE CASCADE
);