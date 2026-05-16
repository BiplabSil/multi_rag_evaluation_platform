# test_config.py Explained Simply

This file tests the configuration system - the part of the code that reads environment variables and provides settings throughout the application.

---

# 1. What is Configuration?

Configuration is the set of settings that your application needs to run.

Examples:

- Database connection details
- API keys for external services
- Model names (gpt-4o, text-embedding-3-small)
- Chunk sizes, overlap values
- Feature flags

In this project, settings come from environment variables in the `.env` file.

---

# 2. The Settings Class

```python
from core.config import Settings
settings = Settings()
```

`Settings` is a Pydantic model that:

- Reads environment variables
- Provides default values
- Validates the data
- Converts types (strings to integers, etc.)

---

# 3. Testing Default Values

```python
def test_settings_has_expected_defaults():
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "QDRANT_URL": "https://test.qdrant.io",
        "QDRANT_API_KEY": "test-qdrant-key",
    }):
        settings = Settings()

        assert settings.openai_model == "gpt-4o"
        assert settings.embedding_model == "text-embedding-3-small"
        assert settings.chunk_size == 512
        # ... more assertions
```

This test checks that when only required env vars are set, sensible defaults are used.

---

# 4. Why Use patch.dict()?

```python
with patch.dict(os.environ, {...}):
```

This temporarily adds environment variables to `os.environ`.

After the `with` block ends, the original environment is restored.

**Why not set real env vars?**

- Tests would affect each other
- Would require cleanup
- Not isolated

---

# 5. Testing the mysql_url Property

```python
def test_settings_mysql_url_property():
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
```

The `mysql_url` property combines individual MySQL settings into a connection string.

---

# 6. What is a Property?

```python
@property
def mysql_url(self) -> str:
    return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
```

A property is a method that looks like an attribute.

Instead of:

```python
url = get_mysql_url(settings)
```

You can write:

```python
url = settings.mysql_url
```

---

# 7. Testing Custom Environment Values

```python
def test_settings_custom_values():
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "custom-key",
        "MYSQL_HOST": "mysql-server",
        "MYSQL_PORT": "3307",
        "OPENAI_MODEL": "gpt-4",
        "CHUNK_SIZE": "1024",
    }):
        settings = Settings()

        assert settings.mysql_host == "mysql-server"
        assert settings.openai_model == "gpt-4"
        assert settings.chunk_size == 1024
```

This test verifies that environment variables override default values.

---

# 8. How Environment Variables Map to Settings

| Env Variable | Settings Field | Default |
|--------------|----------------|---------|
| OPENAI_API_KEY | openai_api_key | (required) |
| OPENAI_MODEL | openai_model | gpt-4o |
| EMBEDDING_MODEL | embedding_model | text-embedding-3-small |
| MYSQL_HOST | mysql_host | localhost |
| MYSQL_PORT | mysql_port | 3306 |
| CHUNK_SIZE | chunk_size | 512 |

---

# 9. Testing GitHub Settings

```python
def test_settings_github_defaults():
    settings = get_settings()

    assert settings.github_failure_threshold == 0.1
    assert settings.github_check_name == "RAGAS Evaluation"
    assert settings.github_api_token == ""
```

Tests that GitHub integration settings have sensible defaults.

---

# 10. Testing Optional Settings

```python
def test_settings_cohere_optional():
    settings = get_settings()

    assert settings.cohere_api_key is None
    assert settings.cohere_rerank_model == "rerank-v4.0-pro"
```

Tests that optional settings like Cohere API key can be absent.

---

# 11. Testing Caching

```python
def test_get_settings_caching():
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
```

The `get_settings()` function caches the settings object.

Why?

- Reading environment variables is slow
- Creating the Settings object takes time
- Caching makes subsequent calls instant

---

# 12. What is Caching?

```python
@lru_cache()
def get_settings():
    return Settings()
```

`@lru_cache` stores the result of the first call.

On subsequent calls, it returns the cached result instead of running the function again.

---

# 13. Why Clear the Cache?

```python
get_settings.cache_clear()
```

Before testing, the cache must be cleared.

Otherwise, tests would share the same cached settings object, causing unexpected behavior.

---

# 14. Test Coverage Summary

| Test | What It Checks |
|------|----------------|
| test_settings_has_expected_defaults | Default values are correct |
| test_settings_mysql_url_property | mysql_url property works |
| test_settings_custom_values | Env vars override defaults |
| test_settings_github_defaults | GitHub settings have defaults |
| test_settings_cohere_optional | Optional settings work |
| test_get_settings_caching | Caching works correctly |

---

# 15. Why Test Configuration?

Configuration is the foundation of the entire application.

If config is wrong, everything breaks.

Testing config ensures:

- Defaults are sensible
- Environment variables work
- Properties calculate correctly
- Caching behaves as expected

---

# Summary

test_config.py verifies the configuration system:

- Default values are correct when env vars are missing
- Custom env vars override defaults
- Generated properties (like mysql_url) work correctly
- Optional settings are handled properly
- Caching improves performance

These tests ensure the application reads settings correctly from the environment.