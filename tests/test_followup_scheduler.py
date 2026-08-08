"""
Tests for follow-up scheduling functionality.

This module tests the FollowUpScheduler component which handles:
- First follow-up scheduling (day 5) - Requirement 18.1
- Second follow-up scheduling (day 12) - Requirement 18.2
- Third follow-up scheduling (day 21) - Requirement 18.3
- Follow-up cancellation on reply - Requirement 18.4
- Different follow-up content generation - Requirement 18.5
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Job, Contact, OutreachRecord
from src.outreach.followup_scheduler import (
    FollowUpScheduler,
    FOLLOWUP_SCHEDULE,
    FOLLOWUP_TEMPLATES,
    MAX_FOLLOWUPS,
    SKIP_STATUSES,
)


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_session_factory(test_engine):
    """Create a session factory for testing."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    return TestingSessionLocal


@pytest.fixture
def test_db(test_session_factory):
    """Create and yield a test database session."""
    session = test_session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_job(test_db):
    """Create a sample job in the test database."""
    job = Job(
        job_id="followup_test_job_123",
        title="Software Engineer",
        company="TestCorp",
        location="Remote",
        description="Python developer needed",
        url="https://testcorp.com/jobs/123",
        source="test",
    )
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)
    return job


@pytest.fixture
def sample_contact(test_db):
    """Create a sample contact in the test database."""
    contact = Contact(
        name="Jane Smith",
        title="Hiring Manager",
        email="jane.smith@testcorp.com",
        company="TestCorp",
        department="Engineering",
        confidence_score=85,
    )
    test_db.add(contact)
    test_db.commit()
    test_db.refresh(contact)
    return contact


@pytest.fixture
def outreach_record_initial(test_db, sample_job, sample_contact):
    """Create an initial outreach record ready for follow-up scheduling."""
    now = datetime.now(timezone.utc)
    record = OutreachRecord(
        contact_id=sample_contact.id,
        job_id=sample_job.id,
        subject="Application for Software Engineer",
        body="Initial outreach email body",
        template_type="hr_outreach",
        status="sent",
        sent_at=now,
        email_sent=True,
        contact_email=sample_contact.email,
        contact_name=sample_contact.name,
        follow_up_scheduled=now + timedelta(days=5),
        follow_up_sent=False,
        follow_up_count=0,
    )
    test_db.add(record)
    test_db.commit()
    test_db.refresh(record)
    return record


@pytest.fixture
def mock_email_outreach():
    """Create a mock email outreach service."""
    outreach = AsyncMock()
    outreach.send_email = AsyncMock(return_value=True)
    return outreach


@pytest.fixture
def mock_rate_limiter():
    """Create a mock rate limiter that always allows."""
    limiter = AsyncMock()
    limiter.check = AsyncMock(return_value=(True, "allowed"))
    limiter.consume = AsyncMock()
    return limiter


class TestFollowUpScheduleConstants:
    """Test that follow-up schedule constants match requirements."""

    def test_first_followup_on_day_5(self):
        """
        Requirement 18.1: THE FollowUpScheduler SHALL schedule first follow-up
        on day 5 after initial send.
        """
        # FOLLOWUP_SCHEDULE is: [(follow_up_count, days_since_last)]
        # First entry (index 0) is for follow_up_count=0, which is the first follow-up
        first_followup = FOLLOWUP_SCHEDULE[0]
        assert first_followup[0] == 0, "First follow-up should be for count=0"
        assert first_followup[1] == 5, f"First follow-up should be 5 days after initial, got {first_followup[1]}"

    def test_second_followup_on_day_12(self):
        """
        Requirement 18.2: THE FollowUpScheduler SHALL schedule second follow-up
        on day 12 after initial send.
        
        Day 5 (first) + 7 days = Day 12 (second)
        """
        # The second follow-up is at index 1
        second_followup = FOLLOWUP_SCHEDULE[1]
        assert second_followup[0] == 1, "Second follow-up should be for count=1"
        # Total days from initial: 5 (first) + 7 (interval) = 12
        total_days = FOLLOWUP_SCHEDULE[0][1] + FOLLOWUP_SCHEDULE[1][1]
        assert total_days == 12, f"Second follow-up should be day 12, got day {total_days}"

    def test_third_followup_on_day_21(self):
        """
        Requirement 18.3: THE FollowUpScheduler SHALL schedule third follow-up
        on day 21 after initial send.
        
        Day 5 (first) + 7 (second) + 9 (third) = Day 21
        """
        third_followup = FOLLOWUP_SCHEDULE[2]
        assert third_followup[0] == 2, "Third follow-up should be for count=2"
        # Total days from initial: 5 + 7 + 9 = 21
        total_days = sum(s[1] for s in FOLLOWUP_SCHEDULE)
        assert total_days == 21, f"Third follow-up should be day 21, got day {total_days}"


    def test_max_followups_is_three(self):
        """Test that maximum follow-ups is 3 (matching the schedule length)."""
        assert MAX_FOLLOWUPS == 3
        assert MAX_FOLLOWUPS == len(FOLLOWUP_SCHEDULE)
        assert MAX_FOLLOWUPS == len(FOLLOWUP_TEMPLATES)


class TestFollowUpContentGeneration:
    """Test different follow-up content generation for each attempt."""

    def test_different_templates_for_each_followup(self):
        """
        Requirement 18.5: THE FollowUpScheduler SHALL generate different
        follow-up content for each attempt.
        """
        assert len(FOLLOWUP_TEMPLATES) == 3
        # Each template should be unique
        assert len(set(FOLLOWUP_TEMPLATES)) == 3
        # Templates should be: follow_up_1, follow_up_2, follow_up_final
        assert "follow_up_1" in FOLLOWUP_TEMPLATES
        assert "follow_up_2" in FOLLOWUP_TEMPLATES
        assert "follow_up_final" in FOLLOWUP_TEMPLATES

    def test_followup_body_generation_first(self):
        """Test that first follow-up body is generated correctly."""
        body = FollowUpScheduler._build_followup_body(
            follow_up_num=0,
            contact_name="John Doe",
            original_subject="Software Engineer Position"
        )
        assert "John" in body  # Uses first name
        assert "follow up" in body.lower()
        assert "Software Engineer Position" in body
        assert "didn't get buried" in body or "slip" in body

    def test_followup_body_generation_second(self):
        """Test that second follow-up body is generated with different content."""
        body = FollowUpScheduler._build_followup_body(
            follow_up_num=1,
            contact_name="John Doe",
            original_subject="Software Engineer Position"
        )
        assert "John" in body
        assert "circling back" in body.lower() or "thinking about" in body.lower()


    def test_followup_body_generation_final(self):
        """Test that final follow-up body is generated with closing content."""
        body = FollowUpScheduler._build_followup_body(
            follow_up_num=2,
            contact_name="John Doe",
            original_subject="Software Engineer Position"
        )
        assert "John" in body
        assert "last" in body.lower() or "final" in body.lower()
        assert "bother" in body.lower() or "stay in touch" in body.lower()

    def test_followup_bodies_are_different(self):
        """Test that each follow-up body has distinct content."""
        body_1 = FollowUpScheduler._build_followup_body(0, "Test User", "Test Subject")
        body_2 = FollowUpScheduler._build_followup_body(1, "Test User", "Test Subject")
        body_3 = FollowUpScheduler._build_followup_body(2, "Test User", "Test Subject")
        
        # All bodies should be different
        assert body_1 != body_2
        assert body_2 != body_3
        assert body_1 != body_3

    def test_followup_handles_unknown_contact_name(self):
        """Test that follow-up body handles 'there' for unknown contacts."""
        body = FollowUpScheduler._build_followup_body(
            follow_up_num=0,
            contact_name="there",
            original_subject="Test Subject"
        )
        assert "Hi there" in body


class TestInitialFollowUpScheduling:
    """Test initial follow-up scheduling after first email is sent."""

    def test_schedule_initial_followup(self, test_db, sample_job, sample_contact):
        """Test that initial follow-up is scheduled 5 days out."""
        now = datetime.now(timezone.utc)
        record = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Test Subject",
            body="Test Body",
            template_type="hr_outreach",
            status="sent",
            sent_at=now,
            email_sent=True,
            contact_email=sample_contact.email,
            contact_name=sample_contact.name,
        )
        test_db.add(record)
        test_db.commit()

        
        # Schedule initial follow-up
        FollowUpScheduler.schedule_initial_followup(record, test_db)
        
        # Verify follow-up is scheduled 5 days out
        assert record.follow_up_scheduled is not None
        expected_date = now + timedelta(days=5)
        # Handle timezone-aware/naive comparison
        scheduled = record.follow_up_scheduled
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=timezone.utc)
        # Allow 1 second tolerance for test execution time
        time_diff = abs((scheduled - expected_date).total_seconds())
        assert time_diff < 2, f"Follow-up should be ~5 days out, diff was {time_diff}s"
        assert record.follow_up_sent == False
        assert record.follow_up_count == 0


class TestFollowUpCancellationOnReply:
    """Test that follow-ups are cancelled when a reply is received."""

    def test_skip_statuses_include_replied(self):
        """
        Requirement 18.4: WHEN a reply is received, THE FollowUpScheduler
        SHALL cancel all pending follow-ups.
        
        The 'replied' status should be in SKIP_STATUSES.
        """
        assert "replied" in SKIP_STATUSES

    def test_skip_statuses_include_bounced(self):
        """Test that bounced emails don't get follow-ups."""
        assert "bounced" in SKIP_STATUSES

    def test_skip_statuses_include_unsubscribed(self):
        """Test that unsubscribed contacts don't get follow-ups."""
        assert "unsubscribed" in SKIP_STATUSES


    def test_followup_skipped_when_replied_at_set(
        self, test_session_factory, test_db, sample_job, sample_contact, mock_email_outreach
    ):
        """
        Requirement 18.4: Test that follow-ups are skipped when replied_at is set.
        """
        now = datetime.now(timezone.utc)
        record = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Test Subject",
            body="Test Body",
            template_type="hr_outreach",
            status="sent",
            sent_at=now - timedelta(days=6),  # Sent 6 days ago
            email_sent=True,
            contact_email=sample_contact.email,
            contact_name=sample_contact.name,
            follow_up_scheduled=now - timedelta(days=1),  # Due yesterday
            follow_up_sent=False,
            follow_up_count=0,
            replied_at=now - timedelta(hours=2),  # Reply received 2 hours ago
        )
        test_db.add(record)
        test_db.commit()
        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        # Fetch overdue records - should not include the replied-to record
        overdue = scheduler._fetch_overdue_records()
        assert record.id not in overdue

    def test_followup_skipped_when_status_replied(
        self, test_session_factory, test_db, sample_job, sample_contact, mock_email_outreach
    ):
        """Test that follow-ups are skipped when status is 'replied'."""
        now = datetime.now(timezone.utc)
        record = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Test Subject",
            body="Test Body",
            template_type="hr_outreach",
            status="replied",  # Status set to replied
            sent_at=now - timedelta(days=6),
            email_sent=True,
            contact_email=sample_contact.email,
            contact_name=sample_contact.name,
            follow_up_scheduled=now - timedelta(days=1),
            follow_up_sent=False,
            follow_up_count=0,
        )
        test_db.add(record)
        test_db.commit()
        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        overdue = scheduler._fetch_overdue_records()
        assert record.id not in overdue


class TestOverdueRecordFetching:
    """Test the fetching of overdue follow-up records."""

    def test_fetch_overdue_records_finds_due_records(
        self, test_session_factory, test_db, outreach_record_initial, mock_email_outreach
    ):
        """Test that records past their scheduled time are fetched."""
        # Update the record to be overdue
        now = datetime.now(timezone.utc)
        outreach_record_initial.follow_up_scheduled = now - timedelta(hours=1)
        test_db.commit()
        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        overdue = scheduler._fetch_overdue_records()
        assert outreach_record_initial.id in overdue

    def test_fetch_excludes_future_scheduled(
        self, test_session_factory, test_db, outreach_record_initial, mock_email_outreach
    ):
        """Test that future-scheduled records are not fetched."""
        # Record is scheduled 5 days out (fixture default)
        now = datetime.now(timezone.utc)
        outreach_record_initial.follow_up_scheduled = now + timedelta(days=3)
        test_db.commit()
        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        overdue = scheduler._fetch_overdue_records()
        assert outreach_record_initial.id not in overdue

    def test_fetch_excludes_max_followups_reached(
        self, test_session_factory, test_db, sample_job, sample_contact, mock_email_outreach
    ):
        """Test that records with max follow-ups are excluded."""
        now = datetime.now(timezone.utc)
        record = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Test Subject",
            body="Test Body",
            template_type="hr_outreach",
            status="sent",
            sent_at=now - timedelta(days=30),
            email_sent=True,
            contact_email=sample_contact.email,
            contact_name=sample_contact.name,
            follow_up_scheduled=now - timedelta(hours=1),
            follow_up_sent=False,
            follow_up_count=MAX_FOLLOWUPS,  # Max reached
        )
        test_db.add(record)
        test_db.commit()
        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        overdue = scheduler._fetch_overdue_records()
        assert record.id not in overdue


class TestFollowUpProcessing:
    """Test the actual processing of follow-up records."""

    @pytest.mark.asyncio
    async def test_process_record_sends_followup(
        self, test_session_factory, test_db, sample_job, sample_contact, mock_email_outreach
    ):
        """Test that processing a record sends a follow-up email."""
        now = datetime.now(timezone.utc)
        record = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Software Engineer at TestCorp",
            body="Initial body",
            template_type="hr_outreach",
            status="sent",
            sent_at=now - timedelta(days=6),
            email_sent=True,
            contact_email=sample_contact.email,
            contact_name=sample_contact.name,
            follow_up_scheduled=now - timedelta(hours=1),
            follow_up_sent=False,
            follow_up_count=0,
        )
        test_db.add(record)
        test_db.commit()
        record_id = record.id
        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        await scheduler._process_record(record_id)
        
        # Verify email was sent
        mock_email_outreach.send_email.assert_called_once()
        
        # Verify record was updated
        test_db.refresh(record)
        assert record.follow_up_count == 1
        assert record.follow_up_sent == False  # Reset for next round
        assert record.last_follow_up_at is not None

    @pytest.mark.asyncio
    async def test_process_record_schedules_next_followup(
        self, test_session_factory, test_db, sample_job, sample_contact, mock_email_outreach
    ):
        """Test that after first follow-up, next is scheduled correctly."""
        now = datetime.now(timezone.utc)
        record = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Test Subject",
            body="Initial body",
            template_type="hr_outreach",
            status="sent",
            sent_at=now - timedelta(days=6),
            email_sent=True,
            contact_email=sample_contact.email,
            contact_name=sample_contact.name,
            follow_up_scheduled=now - timedelta(hours=1),
            follow_up_sent=False,
            follow_up_count=0,
        )
        test_db.add(record)
        test_db.commit()
        record_id = record.id

        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        await scheduler._process_record(record_id)
        
        # Verify next follow-up is scheduled 7 days out (from FOLLOWUP_SCHEDULE[1])
        test_db.refresh(record)
        expected_next = now + timedelta(days=7)
        # Handle timezone-aware/naive comparison
        scheduled = record.follow_up_scheduled
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=timezone.utc)
        # Allow some tolerance for test execution time
        time_diff = abs((scheduled - expected_next).total_seconds())
        assert time_diff < 5, f"Next follow-up should be ~7 days out, diff was {time_diff}s"

    @pytest.mark.asyncio
    async def test_no_followup_scheduled_after_final(
        self, test_session_factory, test_db, sample_job, sample_contact, mock_email_outreach
    ):
        """Test that no more follow-ups are scheduled after the third."""
        now = datetime.now(timezone.utc)
        record = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Test Subject",
            body="Initial body",
            template_type="hr_outreach",
            status="sent",
            sent_at=now - timedelta(days=22),
            email_sent=True,
            contact_email=sample_contact.email,
            contact_name=sample_contact.name,
            follow_up_scheduled=now - timedelta(hours=1),
            follow_up_sent=False,
            follow_up_count=2,  # About to send the final (3rd) follow-up
        )
        test_db.add(record)
        test_db.commit()
        record_id = record.id
        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        await scheduler._process_record(record_id)
        
        # Verify count is now 3 (max)
        test_db.refresh(record)
        assert record.follow_up_count == MAX_FOLLOWUPS

    @pytest.mark.asyncio
    async def test_rate_limited_followup_skipped(
        self, test_session_factory, test_db, sample_job, sample_contact, mock_email_outreach
    ):
        """Test that rate-limited follow-ups are skipped."""
        now = datetime.now(timezone.utc)
        record = OutreachRecord(
            contact_id=sample_contact.id,
            job_id=sample_job.id,
            subject="Test Subject",
            body="Initial body",
            template_type="hr_outreach",
            status="sent",
            sent_at=now - timedelta(days=6),
            email_sent=True,
            contact_email=sample_contact.email,
            contact_name=sample_contact.name,
            follow_up_scheduled=now - timedelta(hours=1),
            follow_up_sent=False,
            follow_up_count=0,
        )
        test_db.add(record)
        test_db.commit()
        record_id = record.id

        
        # Create a rate limiter that denies
        rate_limiter = AsyncMock()
        rate_limiter.check = AsyncMock(return_value=(False, "rate limited"))
        
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
            rate_limiter=rate_limiter,
        )
        
        await scheduler._process_record(record_id)
        
        # Verify email was NOT sent
        mock_email_outreach.send_email.assert_not_called()
        
        # Verify skip counter increased
        assert scheduler._skip_total == 1


class TestSchedulerLifecycle:
    """Test scheduler start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(
        self, test_session_factory, mock_email_outreach
    ):
        """Test that scheduler can start and stop cleanly."""
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
            poll_interval_secs=1,  # Short interval for testing
        )
        
        await scheduler.start()
        assert scheduler._running == True
        assert scheduler._task is not None
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        await scheduler.stop()
        assert scheduler._running == False

    def test_scheduler_stats(
        self, test_session_factory, mock_email_outreach
    ):
        """Test that scheduler tracks statistics."""
        scheduler = FollowUpScheduler(
            db_session_factory=test_session_factory,
            email_outreach=mock_email_outreach,
        )
        
        stats = scheduler.stats()
        assert "sent" in stats
        assert "skipped" in stats
        assert "errors" in stats


class TestFollowUpDayCalculations:
    """Test that follow-up days are calculated correctly from initial send."""

    def test_day_5_calculation(self):
        """
        Requirement 18.1: First follow-up is day 5.
        Verify the schedule produces day 5.
        """
        initial_send = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        # First follow-up interval
        days_to_first = FOLLOWUP_SCHEDULE[0][1]
        first_followup = initial_send + timedelta(days=days_to_first)
        expected = datetime(2024, 1, 6, 10, 0, 0, tzinfo=timezone.utc)
        assert first_followup == expected

    def test_day_12_calculation(self):
        """
        Requirement 18.2: Second follow-up is day 12.
        Day 5 (first) + 7 days (second interval) = Day 12.
        """
        initial_send = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        # Total days to second follow-up
        days_to_second = FOLLOWUP_SCHEDULE[0][1] + FOLLOWUP_SCHEDULE[1][1]
        second_followup = initial_send + timedelta(days=days_to_second)
        expected = datetime(2024, 1, 13, 10, 0, 0, tzinfo=timezone.utc)  # Day 12 = Jan 13
        assert second_followup == expected

    def test_day_21_calculation(self):
        """
        Requirement 18.3: Third follow-up is day 21.
        Day 5 + 7 + 9 = Day 21.
        """
        initial_send = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        # Total days to third follow-up
        days_to_third = sum(s[1] for s in FOLLOWUP_SCHEDULE)
        third_followup = initial_send + timedelta(days=days_to_third)
        expected = datetime(2024, 1, 22, 10, 0, 0, tzinfo=timezone.utc)  # Day 21 = Jan 22
        assert third_followup == expected


class TestFollowUpTemplateTypes:
    """Test that correct template types are used for each follow-up."""

    def test_first_followup_uses_followup_1_template(self):
        """Test first follow-up uses 'follow_up_1' template."""
        template = FOLLOWUP_TEMPLATES[0]
        assert template == "follow_up_1"

    def test_second_followup_uses_followup_2_template(self):
        """Test second follow-up uses 'follow_up_2' template."""
        template = FOLLOWUP_TEMPLATES[1]
        assert template == "follow_up_2"

    def test_third_followup_uses_followup_final_template(self):
        """Test third follow-up uses 'follow_up_final' template."""
        template = FOLLOWUP_TEMPLATES[2]
        assert template == "follow_up_final"
