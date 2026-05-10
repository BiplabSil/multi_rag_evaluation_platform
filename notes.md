@property
python@property
def mysql_url(self) -> str:
    return f"mysql+pymysql://{self.mysql_user}:..."
This turns a method into an attribute. Without it you'd call settings.mysql_url() with parentheses. With it, you just write settings.mysql_url like a normal variable — but it's computed on the fly each time from the other fields.
Think of it as a computed/derived value — you don't store it separately, you just build it from parts you already have.

@lru_cache
python@lru_cache
def get_settings() -> Settings:
    return Settings()
lru_cache stands for Least Recently Used Cache. It means: run this function once, remember the result, and return the same object every time after that.
Without it, every time any module calls get_settings(), Python would re-read the .env file and create a brand new Settings object. That's wasteful.
With it, the first call does the real work, and every subsequent call just gets back the same cached object instantly.
1st call → reads .env, creates Settings object, caches it
2nd call → returns cached object (no file reading)
3rd call → returns cached object (no file reading)

Key difference between the two
@property@lru_cacheApplied toa method inside a classa standalone functionPurposeaccess it like an attribute, not a function callcache the result so it only runs onceRuns every time?Yes, recomputes each accessNo, only runs once then returns cached result

Simply put — @property is about how you access it, @lru_cache is about how often it runs.

What is SQLAlchemy?
SQLAlchemy is a Python library that lets you interact with a database using Python code instead of raw SQL queries.

Without SQLAlchemy (raw SQL)
pythoncursor.execute("INSERT INTO documents (id, filename) VALUES ('abc', 'file.pdf')")
cursor.execute("SELECT * FROM documents WHERE id = 'abc'")
You write SQL strings manually. Error-prone, messy, no autocomplete.

With SQLAlchemy (Python objects)
pythondoc = Document(id="abc", filename="file.pdf")
db.add(doc)
db.commit()

doc = db.query(Document).filter(Document.id == "abc").first()
You work with Python classes and objects. No raw SQL strings needed.

The two things SQLAlchemy does in this project
1. ORM (Object Relational Mapper) — models/orm.py
Maps Python classes to database tables.
pythonclass Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
This Python class represents the documents table. Each instance of Document is one row.

2. Engine + Session — core/database.py
Manages the actual connection to MySQL.
pythonengine = create_engine(settings.mysql_url)  # connects to MySQL
SessionLocal = sessionmaker(bind=engine)    # factory to create sessions
A session is like a conversation with the database — you open it, do your reads/writes, then close it.

Key terms you'll see in the code
TermWhat it meansengineThe actual connection to MySQLsessionA single unit of work with the DBBaseParent class all ORM models inherit frommapped_columnDefines a column in the tabledb.add()Stage a new row to be inserteddb.commit()Actually write it to the databasedb.flush()Send to DB but don't commit yetdb.query()Read data from the database

Simple analogy
Think of SQLAlchemy as a translator sitting between your Python code and MySQL. You speak Python, it translates to SQL, sends it to MySQL, and brings back the result as Python objects.
Your Python code
      ↓
  SQLAlchemy          ← translator
      ↓
    MySQL             ← actual database