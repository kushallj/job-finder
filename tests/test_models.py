"""Tests for SQLAlchemy models in src.models."""
import pytest
from sqlalchemy.exc import IntegrityError

from src.models import Job, Application, Resume, Contact, OutreachRecord


class TestJobModel:
    """Tests for the Job model."""

    def test_job_creation(self, test_db, sample_job):
        """Create a Job, commit, query back, verify all fields."""
        test_db.add(sample_job)
        test_db.commit()

        job = test_db.query(Job).filter_by(job_id="test_123").first()
        assert job is not None
        assert job.job_id == "test_123"
        assert job.title == "Senior Python Dev"
        assert job.company == "Stripe"
        assert job.location == "Remote"
        assert job.description == "Looking for senior Python developer with Django, FastAPI, PostgreSQL. 5+ years."
        assert job.url == "https://stripe.com/jobs/123"
        assert job.source == "adzuna"
        assert job.fetched_at is not None

    def test_job_unique_job_id(self, test_db):
        """Inserting two jobs with same job_id raises IntegrityError."""
        job1 = Job(
            job_id="duplicate_id",
            title="Engineer",
            company="Company A",
        )
        job2 = Job(
            job_id="duplicate_id",
            title="Developer",
            company="Company B",
        )
        test_db.add(job1)
        test_db.commit()

        test_db.add(job2)
        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()


class TestApplicationModel:
    """Tests for the Application model."""

    def test_application_creation(self, test_db, sample_job):
        """Create Job + Application with match_score=85.5, verify relationship."""
        test_db.add(sample_job)
        test_db.commit()

        application = Application(
            job_id=sample_job.id,
            match_score=85.5,
            skills_matched='["Python", "Django", "FastAPI"]',
            skills_missing='["Go"]',
            status="pending",
        )
        test_db.add(application)
        test_db.commit()

        app = test_db.query(Application).first()
        assert app is not None
        assert app.match_score == 85.5
        assert app.skills_matched == '["Python", "Django", "FastAPI"]'
        assert app.status == "pending"
        assert app.job.job_id == "test_123"


class TestContactModel:
    """Tests for the Contact model."""

    def test_contact_creation(self, test_db, sample_contact):
        """Create Contact, verify fields."""
        test_db.add(sample_contact)
        test_db.commit()

        contact = test_db.query(Contact).first()
        assert contact is not None
        assert contact.name == "John Doe"
        assert contact.title == "Engineering Manager"
        assert contact.email == "john.doe@stripe.com"
        assert contact.company == "Stripe"
        assert contact.department == "Engineering"
        assert contact.confidence_score == 85
        assert contact.found_at is not None


class TestOutreachRecordModel:
    """Tests for the OutreachRecord model."""

    def test_outreach_record_creation(self, test_db, sample_job, sample_contact):
        """Create OutreachRecord linked to Contact and Job."""
        test_db.add(sample_job)
        test_db.add(sample_contact)
        test_db.commit()

        outreach = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Interested in Senior Python Dev role",
            body="Hi John, I noticed Stripe is hiring...",
            template_type="engineering_manager",
            status="sent",
            email_sent=True,
            contact_email="john.doe@stripe.com",
            contact_name="John Doe",
        )
        test_db.add(outreach)
        test_db.commit()

        record = test_db.query(OutreachRecord).first()
        assert record is not None
        assert record.contact_id == sample_contact.id
        assert record.job_id == sample_job.id
        assert record.subject == "Interested in Senior Python Dev role"
        assert record.template_type == "engineering_manager"
        assert record.status == "sent"
        assert record.email_sent is True
        assert record.sent_at is not None


class TestResumeModel:
    """Tests for the Resume model."""

    def test_resume_creation(self, test_db):
        """Create Resume with is_active=True."""
        resume = Resume(
            original_content="Experienced Python developer with 7 years...",
            skills='["Python", "Django", "FastAPI", "PostgreSQL"]',
            experience_years=7.0,
            is_active=True,
        )
        test_db.add(resume)
        test_db.commit()

        saved_resume = test_db.query(Resume).first()
        assert saved_resume is not None
        assert saved_resume.original_content == "Experienced Python developer with 7 years..."
        assert saved_resume.skills == '["Python", "Django", "FastAPI", "PostgreSQL"]'
        assert saved_resume.experience_years == 7.0
        assert saved_resume.is_active is True
        assert saved_resume.created_at is not None


class TestRelationships:
    """Tests for model relationships."""

    def test_job_application_relationship(self, test_db, sample_job):
        """Verify job.applications returns the linked application."""
        test_db.add(sample_job)
        test_db.commit()

        application = Application(
            job_id=sample_job.id,
            match_score=90.0,
            status="applied",
        )
        test_db.add(application)
        test_db.commit()

        # Refresh to load relationships
        test_db.refresh(sample_job)
        assert len(sample_job.applications) == 1
        assert sample_job.applications[0].match_score == 90.0
        assert sample_job.applications[0].status == "applied"

    def test_contact_outreach_relationship(self, test_db, sample_job, sample_contact):
        """Verify contact.outreach_records returns linked outreach records."""
        test_db.add(sample_job)
        test_db.add(sample_contact)
        test_db.commit()

        outreach1 = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="First outreach",
            template_type="hr_outreach",
            status="sent",
        )
        outreach2 = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Follow up",
            template_type="follow_up",
            status="sent",
        )
        test_db.add_all([outreach1, outreach2])
        test_db.commit()

        # Refresh to load relationships
        test_db.refresh(sample_contact)
        assert len(sample_contact.outreach_records) == 2
        subjects = [r.subject for r in sample_contact.outreach_records]
        assert "First outreach" in subjects
        assert "Follow up" in subjects
