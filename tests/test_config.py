"""
tests/test_config.py
--------------------
Unit tests for core/config.py.

Tests Settings loading and validation.
"""

import os
from unittest.mock import patch

import pytest


def test_settings_has_expected_defaults():
    """Test that Settings has expected default values."""
    # Clear any cached settings
    from core.config import get_settings
    get_settings.cache_clear()

    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "QDRANT_URL": "https://test.qdrant.io",
        "QDRANT_API_KEY": "test-qdrant-key",
    }):
        from core.config import Settings
        settings = Settings()

        assert settings.openai_model == "gpt-4o"
        assert settings.embedding_model == "text-embedding-3-small"
        assert settings.chunk_size == 512
        assert settings.chunk_overlap == 50
        assert settings.top_k_retrieval == 5
        assert settings.bm25_candidate_multiplier == 5
        assert settings.hyde_generation_count == 3
        assert settings.hyde_search_multiplier == 2
        assert settings.dense_sparse_mix_weight == 0.65


def test_settings_mysql_url_property():
    """Test that mysql_url property generates correct URL."""
    from core.config import Settings
    settings = Settings(
        openai_api_key="key",
        qdrant_url="https://test.qdrant.io",
        qdrant_api_key="qdrant-key",
        mysql_host="localhost",
        mysql_port=3306,
        mysql_user="root",
        mysql_password="password",
        mysql_database="test_db",
    )

    expected = "mysql+pymysql://root:password@localhost:3306/test_db"
    assert settings.mysql_url == expected


def test_settings_custom_values():
    """Test that custom environment values are loaded."""
    from core.config import Settings
    get_settings = None

    # Import and clear cache
    import core.config
    core.config.get_settings.cache_clear()

    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "custom-key",
        "QDRANT_URL": "https://custom.qdrant.io",
        "QDRANT_API_KEY": "custom-qdrant-key",
        "MYSQL_HOST": "mysql-server",
        "MYSQL_PORT": "3307",
        "MYSQL_USER": "admin",
        "MYSQL_PASSWORD": "adminpass",
        "MYSQL_DATABASE": "admin_db",
        "OPENAI_MODEL": "gpt-4",
        "EMBEDDING_MODEL": "text-embedding-ada-002",
        "CHUNK_SIZE": "1024",
    }):
        settings = Settings()

        assert settings.mysql_host == "mysql-server"
        assert settings.mysql_port == 3307
        assert settings.mysql_user == "admin"
        assert settings.openai_model == "gpt-4"
        assert settings.embedding_model == "text-embedding-ada-002"
        assert settings.chunk_size == 1024


def test_settings_github_defaults():
    """Test GitHub check settings have correct defaults."""
    from core.config import get_settings
    get_settings.cache_clear()

    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "QDRANT_URL": "https://test.qdrant.io",
        "QDRANT_API_KEY": "test-qdrant-key",
    }):
        settings = get_settings()

        assert settings.github_failure_threshold == 0.1
        assert settings.github_check_name == "RAGAS Evaluation"
        assert settings.github_api_token == ""


def test_settings_cohere_optional():
    """Test that Cohere settings are optional."""
    from core.config import get_settings
    get_settings.cache_clear()

    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "QDRANT_URL": "https://test.qdrant.io",
        "QDRANT_API_KEY": "test-qdrant-key",
    }):
        settings = get_settings()

        assert settings.cohere_api_key is None
        assert settings.cohere_rerank_model == "rerank-v4.0-pro"


def test_get_settings_caching():
    """Test that get_settings returns cached instance."""
    from core.config import get_settings

    # Clear cache first
    get_settings.cache_clear()

    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "QDRANT_URL": "https://test.qdrant.io",
        "QDRANT_API_KEY": "test-qdrant-key",
    }):
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance due to caching
        assert settings1 is settings2