# core/database.py Explained Simply

This file sets up the database connection to MySQL. It creates the "engine" that connects to the database and provides "sessions" for running queries.

---

# 1. What is a Database?

A database is a system for storing and retrieving data.

In this project:
- **MySQL** is the database server
- **SQLAlchemy** is the library that talks to MySQL
- The database stores query history, evaluation scores, and document metadata

---

# 2. What is SQLAlchemy?

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
```

**SQLAlchemy** is a Python library that lets you interact with databases using Python code instead of raw SQL.

Instead of writing:
```sql
SELECT * FROM queries WHERE id = '123'
```

You can write:
```python
db.query(Query).filter_by(id='123').first()
```

This is called an ORM (Object-Relational Mapper).

---

# 3. What is an Engine?

```python
def _build_engine():
    settings = get_settings()
    return create_engine(
        settings.mysql_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=(settings.app_env == "development"),
    )
```

An **engine** is the connection between your code and the database.

Think of it as the wire that connects your application to the database server.

---

# 4. Engine Settings Explained

```python
return create_engine(
    settings.mysql_url,           # WHERE to connect
    pool_pre_ping=True,           # CHECK connections are alive
    pool_size=10,                 # KEEP 10 connections ready
    max_overflow=20,              # ALLOW 20 extra during spikes
    echo=(settings.app_env == "development"),  # PRINT SQL in dev
)
```

| Setting | Value | What It Does |
|---------|-------|--------------|
| mysql_url | From settings | The connection string |
| pool_pre_ping | True | Test connection before using it |
| pool_size | 10 | Always keep 10 connections open |
| max_overflow | 20 | Allow 20 more when busy |
| echo | True in dev | Print SQL queries to console |

---

# 5. What is Connection Pooling?

```python
pool_size=10
max_overflow=20
```

**Connection pooling** keeps database connections ready instead of creating new ones for each request.

Without pooling:
```
Request 1 → Create connection → Use → Close
Request 2 → Create connection → Use → Close
```

With pooling:
```
Request 1 → Use existing connection → Return to pool
Request 2 → Use existing connection → Return to pool
```

Benefits:
- Faster responses
- Less load on database
- Better handling of traffic spikes

---

# 6. What is pool_pre_ping?

```python
pool_pre_ping=True
```

Sometimes a connection sits idle and the database closes it.

`pool_pre_ping=True` tests the connection before using it:

1. Take connection from pool
2. Run quick test ("ping")
3. If dead, create new connection
4. Proceed with request

This prevents errors from stale connections.

---

# 7. The Session Factory

```python
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)
```

A **session** is a temporary workspace for talking to the database.

Think of it like opening a document in Google Docs:
- You make changes in your workspace
- When ready, you save (commit)
- If you close without saving, changes are lost

`sessionmaker` creates a factory for making sessions.

---

# 8. autocommit and autoflush

```python
autocommit=False  # Don't auto-save changes
autoflush=False   # Don't auto-send queries
```

These settings give you more control:

- **autocommit=False**: Changes must be explicitly committed
- **autoflush=False**: Queries are only sent when you explicitly ask

This prevents accidental partial saves.

---

# 9. The Base Class

```python
class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass
```

**Base** is the parent class for all database models.

When you define a model:

```python
class Query(Base):
    __tablename__ = "queries"
    id = Column(String, primary_key=True)
    question = Column(String)
```

The model automatically inherits from Base.

This connects your model to SQLAlchemy.

---

# 10. The get_db() Function

```python
def get_db() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This is a **FastAPI dependency** that provides a database session for each request.

---

# 11. What is a FastAPI Dependency?

```python
from fastapi import Depends

@app.get("/example")
def example(db: Session = Depends(get_db)):
    ...
```

FastAPI automatically calls `get_db()` and passes the session to your endpoint.

After the request finishes, the session is closed automatically.

This is called **Dependency Injection**.

---

# 12. How get_db() Works

```python
def get_db():
    db = SessionLocal()  # 1. Create new session
    try:
        yield db         # 2. Give session to route handler
    finally:
        db.close()       # 3. Close session when done
```

This is a **generator function**:

1. Creates a session
2. `yield` pauses and gives the session to the caller
3. When caller is done, `finally` runs and closes the session

This ensures sessions are always cleaned up, even if errors occur.

---

# 13. The db_session() Context Manager

```python
@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager version of get_db for use outside of FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

This is for **scripts and tests** - anywhere not using FastAPI.

---

# 14. What is a Context Manager?

```python
with db_session() as db:
    # Use db here
    db.add(new_query)
# Session automatically closed, changes committed
```

Context managers automatically set up and tear down resources.

The `with` statement handles:
- Opening the session
- Running your code
- Committing on success
- Rolling back on error
- Closing the session

---

# 15. Commit vs Rollback

```python
try:
    yield db
    db.commit()  # Save changes
except Exception:
    db.rollback()  # Undo changes
    raise         # Re-raise error
```

- **commit**: Save all changes permanently
- **rollback**: Undo all changes since last commit

If something goes wrong:
1. Rollback to undo partial changes
2. Raise the error so the caller knows something failed

---

# 16. Using Database in Routes

```python
from core.database import get_db

@app.post("/query")
def create_query(question: str, db: Session = Depends(get_db)):
    query = Query(question=question)
    db.add(query)
    db.commit()
    return {"id": query.id}
```

In FastAPI, just add `db: Session = Depends(get_db)` as a parameter.

FastAPI handles:
- Creating the session
- Passing it to your function
- Closing it when done

---

# 17. Using Database in Scripts

```python
from core.database import db_session

with db_session() as db:
    query = Query(question="What is RAG?")
    db.add(query)
# Automatically commits and closes
```

For scripts or tests, use the context manager directly.

---

# 18. Summary

database.py provides:

| Component | Purpose |
|-----------|---------|
| create_engine | Connect to MySQL |
| SessionLocal | Create sessions |
| Base | Parent class for models |
| get_db() | FastAPI dependency for sessions |
| db_session() | Context manager for scripts |

The database module is the backbone for storing:
- Query history
- Evaluation scores
- Document metadata
- User information

All data persistence goes through this module.