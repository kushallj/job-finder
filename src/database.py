from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from src.config import settings
from src.models import Base
from src.answer_bank import models as _answer_bank_models  # noqa: F401  (registers AnsweredQuestion on Base.metadata)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def db_session():
    """Synchronous context manager for database sessions."""
    s: Session = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def init_db():
    """Initialize database tables and add nullable columns to existing SQLite DBs."""
    Base.metadata.create_all(bind=engine)
    if engine.url.get_backend_name() == "sqlite":
        from sqlalchemy import inspect, text as _text
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if "jobs" in tables:
            existing_jobs = {c["name"] for c in inspector.get_columns("jobs")}
            job_additions = {
                "provider_id": "VARCHAR(255)",
                "company_website": "TEXT",
                "salary_min": "FLOAT",
                "salary_max": "FLOAT",
                "salary_currency": "VARCHAR(10)",
                "has_remote": "BOOLEAN",
                "work_mode": "VARCHAR(50)",
                "experience_level": "VARCHAR(20)",
                "tags": "TEXT",
                "expired_at": "DATETIME",
                "provider_payload": "TEXT",
                "provider_sources": "TEXT",
            }
            with engine.begin() as conn:
                for name, ddl in job_additions.items():
                    if name not in existing_jobs:
                        conn.execute(_text(f"ALTER TABLE jobs ADD COLUMN {name} {ddl}"))

        if "applications" in tables:
            existing_apps = {c["name"] for c in inspector.get_columns("applications")}
            app_additions = {
                "ats_detected": "VARCHAR(100)",
                "customized_resume_path": "TEXT",
                "cover_letter_path": "TEXT",
                "submission_notes": "TEXT",
                "proof_url": "TEXT",
                "proof_notes": "TEXT",
            }
            with engine.begin() as conn:
                for name, ddl in app_additions.items():
                    if name not in existing_apps:
                        conn.execute(_text(f"ALTER TABLE applications ADD COLUMN {name} {ddl}"))
    print("✅ Database tables created")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
