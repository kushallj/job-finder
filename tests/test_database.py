"""Tests for src.database and src.models modules using in-memory SQLite."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from src.models import Base, Job, Application, Resume, Contact, OutreachRecord


# --- Fixtures ---

@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for test isolation."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """Create a test session bound to the in-memory engine."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    yield session
    session.close()


# --- Tests ---

class TestInitDbCreatesTables:
    """Verify init_db creates all expected tables."""

    def test_init_db_creates_tables(self):
        """Calling Base.metadata.create_all on in-memory engine should create all tables."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        assert "jobs" in table_names
        assert "applications" in table_names
        assert "resumes" in table_names
        assert "contacts" in table_names
        assert "outreach_records" in table_names

        engine.dispose()


class TestGetDbYieldsSession:
    """Verify get_db yields a session and closes it."""

    def test_get_db_yields_session(self, test_engine):
        """get_db pattern should yield a working session then close it."""
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

        def get_db():
            db = TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        gen = get_db()
        session = next(gen)

        # Session should be usable
        assert session is not None
        assert session.is_active

        # Exhaust the generator to trigger close
        with pytest.raises(StopIteration):
            next(gen)


class TestSessionCrudJob:
    """Test create/read/update/delete operations on Job."""

    def test_session_crud_job(self, test_session):
        """Full CRUD lifecycle for a Job record."""
        session = test_session

        # Create
        job = Job(
            job_id="test-123",
            title="Software Engineer",
            company="TestCorp",
            location="Remote",
            description="Build things",
            url="https://example.com/job/123",
            source="adzuna",
            posted_date=datetime(2026, 1, 15),
        )
        session.add(job)
        session.commit()

        # Read
        fetched = session.query(Job).filter_by(job_id="test-123").first()
        assert fetched is not None
        assert fetched.title == "Software Engineer"
        assert fetched.company == "TestCorp"
        assert fetched.source == "adzuna"

        # Update
        fetched.title = "Senior Software Engineer"
        session.commit()
        updated = session.query(Job).filter_by(job_id="test-123").first()
        assert updated.title == "Senior Software Engineer"

        # Delete
        session.delete(updated)
        session.commit()
        deleted = session.query(Job).filter_by(job_id="test-123").first()
        assert deleted is None


class TestSessionCrudContact:
    """Test create/read operations on Contact."""

    def test_session_crud_contact(self, test_session):
        """Create and read a Contact record."""
        session = test_session

        contact = Contact(
            name="Jane Doe",
            title="Engineering Manager",
            email="jane.doe@testcorp.com",
            company="TestCorp",
            department="Engineering",
            confidence_score=85,
            source="linkedin",
        )
        session.add(contact)
        session.commit()

        fetched = session.query(Contact).filter_by(email="jane.doe@testcorp.com").first()
        assert fetched is not None
        assert fetched.name == "Jane Doe"
        assert fetched.title == "Engineering Manager"
        assert fetched.company == "TestCorp"
        assert fetched.confidence_score == 85


class TestJobQueryBySource:
    """Test querying jobs by source."""

    def test_job_query_by_source(self, test_session):
        """Insert 3 jobs with different sources, query by source='adzuna'."""
        session = test_session

        jobs = [
            Job(job_id="az-1", title="Backend Dev", company="A", source="adzuna"),
            Job(job_id="rm-1", title="Frontend Dev", company="B", source="remotive"),
            Job(job_id="az-2", title="Fullstack Dev", company="C", source="adzuna"),
        ]
        session.add_all(jobs)
        session.commit()

        adzuna_jobs = session.query(Job).filter_by(source="adzuna").all()
        assert len(adzuna_jobs) == 2
        assert all(j.source == "adzuna" for j in adzuna_jobs)

        remotive_jobs = session.query(Job).filter_by(source="remotive").all()
        assert len(remotive_jobs) == 1


class TestApplicationJoinJob:
    """Test Job → Application relationship join."""

    def test_application_join_job(self, test_session):
        """Create a job and application, verify the join/relationship works."""
        session = test_session

        job = Job(
            job_id="join-test-1",
            title="Data Engineer",
            company="DataCorp",
            source="adzuna",
        )
        session.add(job)
        session.commit()

        application = Application(
            job_id=job.id,
            match_score=0.85,
            skills_matched='["python", "sql"]',
            status="pending",
        )
        session.add(application)
        session.commit()

        # Verify join via relationship
        fetched_app = session.query(Application).filter_by(job_id=job.id).first()
        assert fetched_app is not None
        assert fetched_app.job.title == "Data Engineer"
        assert fetched_app.job.company == "DataCorp"
        assert fetched_app.match_score == 0.85

        # Verify reverse relationship
        fetched_job = session.query(Job).filter_by(job_id="join-test-1").first()
        assert len(fetched_job.applications) == 1
        assert fetched_job.applications[0].match_score == 0.85


class TestOutreachRecordWithRelations:
    """Test full chain: Job → Contact → OutreachRecord."""

    def test_outreach_record_with_relations(self, test_session):
        """Create full chain and verify relationships work."""
        session = test_session

        # Create Job
        job = Job(
            job_id="outreach-test-1",
            title="ML Engineer",
            company="AIStartup",
            source="remotive",
        )
        session.add(job)
        session.commit()

        # Create Contact
        contact = Contact(
            name="Bob Smith",
            title="VP Engineering",
            email="bob@aistartup.com",
            company="AIStartup",
            source="website",
        )
        session.add(contact)
        session.commit()

        # Create OutreachRecord linking both
        outreach = OutreachRecord(
            contact_id=contact.id,
            job_id=job.id,
            subject="Interested in ML Engineer role",
            body="Hi Bob, I noticed the ML Engineer position...",
            template_type="engineering_manager",
            status="sent",
            email_sent=True,
            contact_email="bob@aistartup.com",
            contact_name="Bob Smith",
        )
        session.add(outreach)
        session.commit()

        # Verify relationships
        fetched_outreach = session.query(OutreachRecord).first()
        assert fetched_outreach.contact.name == "Bob Smith"
        assert fetched_outreach.job.title == "ML Engineer"
        assert fetched_outreach.template_type == "engineering_manager"

        # Verify reverse: contact → outreach_records
        fetched_contact = session.query(Contact).filter_by(email="bob@aistartup.com").first()
        assert len(fetched_contact.outreach_records) == 1
        assert fetched_contact.outreach_records[0].subject == "Interested in ML Engineer role"


class TestDuplicateJobIdRaises:
    """Test that duplicate job_id raises IntegrityError."""

    def test_duplicate_job_id_raises(self, test_session):
        """Inserting two jobs with the same job_id should raise IntegrityError."""
        session = test_session

        job1 = Job(
            job_id="duplicate-1",
            title="Engineer A",
            company="CompanyA",
            source="adzuna",
        )
        session.add(job1)
        session.commit()

        job2 = Job(
            job_id="duplicate-1",  # Same job_id — should fail
            title="Engineer B",
            company="CompanyB",
            source="remotive",
        )
        session.add(job2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()
