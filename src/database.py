from contextlib import contextmanager
from sqlalchemy import create_engine, event, inspect, text as _text  # type: ignore # pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker, Session  # type: ignore # pyrefly: ignore [missing-import]
from src.config import settings
from src.models import Base
from src.answer_bank import models as _answer_bank_models  # noqa: F401  (registers AnsweredQuestion on Base.metadata)
from src.nextraise import models as _nextraise_models      # noqa: F401  (registers NextRaise on Base.metadata)

def normalize_database_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy 2.0 (e.g. postgres:// -> postgresql://)."""
    if not url:
        return "sqlite:///./jobs.db"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

db_url = normalize_database_url(settings.database_url)

connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
else:
    # PostgreSQL / Supabase connection pooling
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(db_url, **engine_kwargs)

if db_url.startswith("sqlite"):
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
    """Initialize database tables and add nullable columns to existing SQLite/PostgreSQL DBs."""
    Base.metadata.create_all(bind=engine)
    if engine.url.get_backend_name() in ("sqlite", "postgresql"):
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
                "user_id": "INTEGER",
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

        if "resumes" in tables:
            existing_resumes = {c["name"] for c in inspector.get_columns("resumes")}
            if "user_id" not in existing_resumes:
                with engine.begin() as conn:
                    conn.execute(_text("ALTER TABLE resumes ADD COLUMN user_id INTEGER"))

        if "users" in tables:
            existing_users = {c["name"] for c in inspector.get_columns("users")}
            user_additions = {
                "stripe_subscription_id": "VARCHAR(255)",
                "subscription_status": "VARCHAR(50)",
                "current_period_end": "DATETIME",
            }
            with engine.begin() as conn:
                for name, ddl in user_additions.items():
                    if name not in existing_users:
                        conn.execute(_text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))

        if "contacts" in tables:
            existing_contacts = {c["name"] for c in inspector.get_columns("contacts")}
            if "twitter_url" not in existing_contacts:
                with engine.begin() as conn:
                    conn.execute(_text("ALTER TABLE contacts ADD COLUMN twitter_url TEXT"))

        if "startups_gallery_companies" in tables:
            existing_sg = {c["name"] for c in inspector.get_columns("startups_gallery_companies")}
            sg_additions = {
                "investors": "TEXT",
                "jobs": "TEXT",
                "jobs_count": "INTEGER DEFAULT 0",
            }
            with engine.begin() as conn:
                for name, ddl in sg_additions.items():
                    if name not in existing_sg:
                        conn.execute(_text(f"ALTER TABLE startups_gallery_companies ADD COLUMN {name} {ddl}"))

    # Local dev superuser: opt-in only (SEED_DEV_ADMIN=true + DEV_ADMIN_PASSWORD), never in
    # production. It used to be seeded unconditionally with a public password, which made
    # admin@jobfinder.ai / admin123 a working superuser login on every deployment.
    from src.config import settings as _settings
    if _settings.env.lower() != "production" and _settings.seed_dev_admin and _settings.dev_admin_password:
        try:
            from src.models import User, CreditTransaction
            from src.auth.crypto import hash_password
            with SessionLocal() as session:
                existing_user = session.query(User).filter(User.email == "admin@jobfinder.ai").first()
                if not existing_user:
                    admin_user = User(
                        email="admin@jobfinder.ai",
                        hashed_password=hash_password(_settings.dev_admin_password),
                        full_name="Default Administrator",
                        subscription_tier="unlimited",
                        credits_balance=1000,
                        is_active=True,
                        is_superuser=True,
                    )
                    session.add(admin_user)
                    session.flush()
                    # Record welcome transaction
                    tx = CreditTransaction(
                        user_id=admin_user.id,
                        amount=1000,
                        balance_after=1000,
                        action="system_seed",
                        notes="Initial system administrator provisioning",
                    )
                    session.add(tx)
                    session.commit()
        except Exception as exc:
            print(f"[WARN] Notice on default user seed: {exc}")

    # Seed premier VC firms for VC Intelligence Engine
    try:
        from src.models import VCFirm
        initial_vcs = [
            {
                "name": "Y Combinator",
                "slug": "y-combinator",
                "website": "https://www.ycombinator.com",
                "portfolio_url": "https://www.ycombinator.com/companies",
                "country_focus": "Global",
            },
            {
                "name": "Accel",
                "slug": "accel",
                "website": "https://www.accel.com",
                "portfolio_url": "https://www.accel.com/relationships",
                "country_focus": "Global",
            },
            {
                "name": "Blume Ventures",
                "slug": "blume-ventures",
                "website": "https://blume.vc",
                "portfolio_url": "https://blume.vc/portfolio",
                "country_focus": "India",
            },
            {
                "name": "Tiger Global",
                "slug": "tiger-global",
                "website": "https://www.tigerglobal.com",
                "portfolio_url": "https://www.tigerglobal.com",
                "country_focus": "Global",
            },
            {
                "name": "India Accelerator",
                "slug": "india-accelerator",
                "website": "https://www.indiaaccelerator.com",
                "portfolio_url": "https://www.indiaaccelerator.com/portfolio/",
                "country_focus": "India",
            },
        ]
        with SessionLocal() as session:
            for vc_data in initial_vcs:
                existing_vc = session.query(VCFirm).filter(VCFirm.slug == vc_data["slug"]).first()
                if not existing_vc:
                    vc = VCFirm(**vc_data)
                    session.add(vc)
            session.commit()
    except Exception as exc:
        print(f"[WARN] Notice on VC firms seed: {exc}")

    print("[OK] Database tables created")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
