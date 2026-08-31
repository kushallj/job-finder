"""
Tests for reply detection and classification (Requirements 17.1-17.4).

Requirements covered:
  17.1: THE ReplyDetector SHALL poll IMAP for new replies at 30-minute intervals
  17.2: WHEN a reply is detected, THE ReplyDetector SHALL update the outreach record status
  17.3: THE ReplyDetector SHALL classify reply sentiment (positive, negative, neutral, referral, unsubscribe)
  17.4: WHEN an unsubscribe reply is detected, THE ReplyDetector SHALL mark the contact as do-not-contact
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Contact, OutreachRecord, Job
from src.outreach.reply_detector import ReplyDetector, ReplyStats, DEFAULT_POLL_INTERVAL_SECS
from src.outreach.sentiment import SentimentClassifier, SentimentLabel


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def engine():
    """Create an in-memory SQLite engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session_factory(engine):
    """Factory function that returns new database sessions."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    def factory():
        return TestingSessionLocal()
    return factory


@pytest.fixture
def test_db(db_session_factory):
    """Return a session for direct test use."""
    session = db_session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_job(test_db):
    """Create a sample job in the test database."""
    job = Job(
        job_id="test_job_123",
        title="Software Engineer",
        company="TechCorp",
        location="Remote",
        description="Looking for a Python developer",
        url="https://example.com/job/123",
        source="test",
    )
    test_db.add(job)
    test_db.commit()
    return job


@pytest.fixture
def sample_job(test_db):
    """Create a sample job in the test database."""
    job = Job(
        job_id="test_job_123",
        title="Software Engineer",
        company="TechCorp",
        location="Remote",
        description="Looking for a Python developer",
        url="https://example.com/job/123",
        source="test",
    )
    test_db.add(job)
    test_db.commit()
    return job


@pytest.fixture
def sample_contact(test_db):
    """Create a sample contact in the test database."""
    contact = Contact(
        name="John Doe",
        title="Engineering Manager",
        email="john.doe@techcorp.com",
        company="TechCorp",
        department="Engineering",
        confidence_score=85,
        do_not_contact=False,
    )
    test_db.add(contact)
    test_db.commit()
    return contact


@pytest.fixture
def sample_outreach_record(test_db, sample_job, sample_contact):
    """Create a sample outreach record for testing reply detection."""
    record = OutreachRecord(
        contact_id=sample_contact.id,
        job_id=sample_job.id,
        subject="Interest in Software Engineer role at TechCorp",
        body="Hi John, I'm interested in the position...",
        template_type="engineering_manager",
        status="sent",
        sent_at=datetime.now(timezone.utc) - timedelta(days=2),
        contact_email="john.doe@techcorp.com",
        contact_name="John Doe",
    )
    test_db.add(record)
    test_db.commit()
    # Return the ID so we can re-query it
    return record.id


@pytest.fixture
def mock_sentiment_classifier():
    """Create a mock sentiment classifier."""
    classifier = AsyncMock(spec=SentimentClassifier)
    classifier.classify = AsyncMock(return_value=SentimentLabel.NEUTRAL)
    return classifier


# =====================================================================
# Test: Requirement 17.1 - IMAP Polling Interval
# =====================================================================

class TestPollingInterval:
    """Tests for Requirement 17.1: IMAP polling at 30-minute intervals."""

    def test_default_poll_interval_is_30_minutes(self):
        """Verify default poll interval is 30 minutes (1800 seconds)."""
        assert DEFAULT_POLL_INTERVAL_SECS == 1800
        assert DEFAULT_POLL_INTERVAL_SECS == 30 * 60

    def test_reply_detector_uses_default_poll_interval(self, db_session_factory):
        """Verify ReplyDetector uses 30-minute interval by default."""
        detector = ReplyDetector(db_session_factory)
        assert detector.poll_interval == 1800
        assert detector.poll_interval == 30 * 60

    def test_poll_interval_is_configurable(self, db_session_factory):
        """Verify poll interval can be configured."""
        # 15 minutes
        detector = ReplyDetector(db_session_factory, poll_interval_secs=900)
        assert detector.poll_interval == 900

        # 1 hour
        detector2 = ReplyDetector(db_session_factory, poll_interval_secs=3600)
        assert detector2.poll_interval == 3600

    @pytest.mark.asyncio
    async def test_poll_interval_tracked_in_stats(self, db_session_factory):
        """Verify polling updates statistics."""
        detector = ReplyDetector(
            db_session_factory,
            poll_interval_secs=1,  # 1 second for fast testing
        )
        
        # Manually set credentials to avoid early return
        detector._email = "test@gmail.com"
        detector._password = "test_password"
        
        # Mock IMAP fetch to return empty
        with patch.object(detector, '_fetch_replies', return_value=[]):
            await detector._run_poll()
        
        assert detector.stats.poll_count == 1
        assert detector.stats.last_poll_at is not None


# =====================================================================
# Test: Requirement 17.2 - Reply Detection and Status Updates
# =====================================================================

class TestReplyDetection:
    """Tests for Requirement 17.2: Reply detection and outreach record status updates."""

    @pytest.mark.asyncio
    async def test_reply_updates_outreach_record_status(
        self, db_session_factory, sample_outreach_record, mock_sentiment_classifier
    ):
        """Verify that detecting a reply updates the outreach record status to 'replied'."""
        record_id = sample_outreach_record
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_sentiment_classifier,
        )
        
        # Process a reply
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest in Software Engineer role at TechCorp",
            sender="John Doe <john.doe@techcorp.com>",
            body="Thanks for reaching out! I'd love to chat.",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        # Re-query the record
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        
        assert record.status == "replied"
        assert record.replied_at is not None

    @pytest.mark.asyncio
    async def test_reply_sets_replied_at_timestamp(
        self, db_session_factory, sample_outreach_record, mock_sentiment_classifier
    ):
        """Verify that replied_at timestamp is set when reply is detected."""
        record_id = sample_outreach_record
        before_reply = datetime.utcnow()  # Use naive datetime for SQLite compatibility
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_sentiment_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest in Software Engineer role at TechCorp",
            sender="john.doe@techcorp.com",
            body="Sounds good!",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        
        assert record.replied_at is not None
        # Compare without timezone info
        replied_at_naive = record.replied_at.replace(tzinfo=None) if record.replied_at.tzinfo else record.replied_at
        assert replied_at_naive >= before_reply


    @pytest.mark.asyncio
    async def test_reply_matches_by_email_address(
        self, db_session_factory, sample_outreach_record, mock_sentiment_classifier
    ):
        """Verify replies are matched by sender email address."""
        record_id = sample_outreach_record
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_sentiment_classifier,
        )
        
        # Process reply with email in angle brackets
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Something",
            sender="John Doe <john.doe@techcorp.com>",
            body="Thanks!",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        assert detector.stats.replies_matched == 1
        
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        assert record.status == "replied"

    @pytest.mark.asyncio
    async def test_unmatched_reply_does_not_update_records(
        self, db_session_factory, sample_outreach_record, mock_sentiment_classifier
    ):
        """Verify that replies from unknown senders don't update any records."""
        record_id = sample_outreach_record
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_sentiment_classifier,
        )
        
        # Process reply from unknown sender
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Something",
            sender="unknown@example.com",
            body="Thanks!",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        assert detector.stats.replies_matched == 0
        
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        assert record.status == "sent"  # Unchanged


# =====================================================================
# Test: Requirement 17.3 - Sentiment Classification
# =====================================================================

class TestSentimentClassification:
    """Tests for Requirement 17.3: Sentiment classification of replies."""

    @pytest.mark.asyncio
    async def test_positive_sentiment_classification(
        self, db_session_factory, sample_outreach_record
    ):
        """Verify positive sentiment is classified and stored."""
        record_id = sample_outreach_record
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.POSITIVE)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="Let's schedule a call! I'm very interested.",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        
        assert record.reply_sentiment == "positive"
        assert detector.stats.sentiment_breakdown["positive"] == 1

    @pytest.mark.asyncio
    async def test_negative_sentiment_classification(
        self, db_session_factory, sample_outreach_record
    ):
        """Verify negative sentiment is classified and stored."""
        record_id = sample_outreach_record
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.NEGATIVE)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="Sorry, we're not hiring at the moment.",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        
        assert record.reply_sentiment == "negative"
        assert detector.stats.sentiment_breakdown["negative"] == 1


    @pytest.mark.asyncio
    async def test_neutral_sentiment_classification(
        self, db_session_factory, sample_outreach_record
    ):
        """Verify neutral sentiment is classified and stored."""
        record_id = sample_outreach_record
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.NEUTRAL)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="Thanks for your email.",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        
        assert record.reply_sentiment == "neutral"
        assert detector.stats.sentiment_breakdown["neutral"] == 1

    @pytest.mark.asyncio
    async def test_referral_sentiment_classification(
        self, db_session_factory, sample_outreach_record
    ):
        """Verify referral sentiment is classified and stored."""
        record_id = sample_outreach_record
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.REFERRAL)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="I'm CC'ing our recruiter Sarah who handles these.",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        
        assert record.reply_sentiment == "referral"
        assert detector.stats.sentiment_breakdown["referral"] == 1


    @pytest.mark.asyncio
    async def test_unsubscribe_sentiment_classification(
        self, db_session_factory, sample_outreach_record
    ):
        """Verify unsubscribe sentiment is classified and stored."""
        record_id = sample_outreach_record
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.UNSUBSCRIBE)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="Please remove me from your mailing list.",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        record = session.query(OutreachRecord).filter_by(id=record_id).first()
        session.close()
        
        assert record.reply_sentiment == "unsubscribe"
        assert detector.stats.sentiment_breakdown["unsubscribe"] == 1

    @pytest.mark.asyncio
    async def test_all_five_sentiment_labels_supported(self):
        """Verify all five sentiment labels are supported."""
        expected_labels = {"positive", "negative", "neutral", "referral", "unsubscribe"}
        actual_labels = {label.value for label in SentimentLabel}
        assert actual_labels == expected_labels


# =====================================================================
# Test: Requirement 17.4 - Unsubscribe Handling (Do-Not-Contact)
# =====================================================================

class TestUnsubscribeHandling:
    """Tests for Requirement 17.4: Mark contacts as do-not-contact on unsubscribe."""

    @pytest.mark.asyncio
    async def test_unsubscribe_marks_contact_do_not_contact(
        self, db_session_factory, sample_outreach_record, sample_contact
    ):
        """Verify unsubscribe reply marks contact as do-not-contact."""
        record_id = sample_outreach_record
        contact_id = sample_contact.id
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.UNSUBSCRIBE)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        # Verify contact is initially not marked
        session = db_session_factory()
        contact = session.query(Contact).filter_by(id=contact_id).first()
        assert contact.do_not_contact is False
        session.close()
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="Please don't contact me again.",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        contact = session.query(Contact).filter_by(id=contact_id).first()
        session.close()
        
        assert contact.do_not_contact is True
        assert contact.do_not_contact_reason == "unsubscribe_reply"
        assert contact.do_not_contact_at is not None


    @pytest.mark.asyncio
    async def test_unsubscribe_increments_stats(
        self, db_session_factory, sample_outreach_record, sample_contact
    ):
        """Verify unsubscribe processing updates statistics."""
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.UNSUBSCRIBE)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="Unsubscribe",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        assert detector.stats.unsubscribes_processed == 1
        assert detector.stats.contacts_marked_dnc == 1

    @pytest.mark.asyncio
    async def test_non_unsubscribe_does_not_mark_do_not_contact(
        self, db_session_factory, sample_outreach_record, sample_contact
    ):
        """Verify non-unsubscribe replies don't mark contact as do-not-contact."""
        contact_id = sample_contact.id
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.POSITIVE)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="Let's schedule a call!",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        contact = session.query(Contact).filter_by(id=contact_id).first()
        session.close()
        
        assert contact.do_not_contact is False
        assert detector.stats.unsubscribes_processed == 0
        assert detector.stats.contacts_marked_dnc == 0

    @pytest.mark.asyncio
    async def test_do_not_contact_timestamp_is_set(
        self, db_session_factory, sample_outreach_record, sample_contact
    ):
        """Verify do_not_contact_at timestamp is set when marking contact."""
        contact_id = sample_contact.id
        before_process = datetime.utcnow()  # Use naive datetime for SQLite compatibility
        
        mock_classifier = AsyncMock()
        mock_classifier.classify = AsyncMock(return_value=SentimentLabel.UNSUBSCRIBE)
        
        detector = ReplyDetector(
            db_session_factory,
            sentiment_classifier=mock_classifier,
        )
        
        await detector._process_reply(
            msg_id="<test@msg.id>",
            subject="Re: Interest",
            sender="john.doe@techcorp.com",
            body="Remove me from your list",
            date_str="Mon, 1 Jan 2024 10:00:00 +0000",
        )
        
        session = db_session_factory()
        contact = session.query(Contact).filter_by(id=contact_id).first()
        session.close()
        
        assert contact.do_not_contact_at is not None
        # Compare without timezone info
        dnc_at_naive = contact.do_not_contact_at.replace(tzinfo=None) if contact.do_not_contact_at.tzinfo else contact.do_not_contact_at
        assert dnc_at_naive >= before_process


# =====================================================================
# Test: ReplyStats
# =====================================================================

class TestReplyStats:
    """Tests for the ReplyStats dataclass."""

    def test_stats_initialization(self):
        """Verify stats are initialized to zero."""
        stats = ReplyStats()
        assert stats.replies_detected == 0
        assert stats.replies_matched == 0
        assert stats.unsubscribes_processed == 0
        assert stats.contacts_marked_dnc == 0
        assert stats.poll_count == 0
        assert stats.errors == 0

    def test_stats_as_dict(self):
        """Verify stats can be converted to dictionary."""
        stats = ReplyStats()
        stats.replies_detected = 5
        stats.replies_matched = 3
        stats.unsubscribes_processed = 1
        stats.poll_count = 10
        
        d = stats.as_dict()
        assert d["replies_detected"] == 5
        assert d["replies_matched"] == 3
        assert d["unsubscribes_processed"] == 1
        assert d["poll_count"] == 10

    def test_sentiment_breakdown_tracking(self):
        """Verify sentiment breakdown is tracked correctly."""
        stats = ReplyStats()
        stats.sentiment_breakdown["positive"] = 3
        stats.sentiment_breakdown["negative"] = 1
        stats.sentiment_breakdown["neutral"] = 2
        
        d = stats.as_dict()
        assert d["sentiment_breakdown"]["positive"] == 3
        assert d["sentiment_breakdown"]["negative"] == 1
        assert d["sentiment_breakdown"]["neutral"] == 2


# =====================================================================
# Test: Integration with SentimentClassifier
# =====================================================================

class TestSentimentClassifierIntegration:
    """Integration tests for the actual SentimentClassifier."""

    @pytest.mark.asyncio
    async def test_positive_sentiment_patterns(self):
        """Test that positive sentiment patterns are detected."""
        classifier = SentimentClassifier(use_llm=False)  # Keyword-only mode
        
        positive_texts = [
            "Let's schedule a call to discuss this further.",
            "I'm very interested in talking more about this opportunity.",
            "Sounds great! When are you available?",
            "I'd love to learn more about the position.",
        ]
        
        for text in positive_texts:
            result = await classifier.classify(text)
            assert result == SentimentLabel.POSITIVE, f"Expected POSITIVE for: {text}"

    @pytest.mark.asyncio
    async def test_negative_sentiment_patterns(self):
        """Test that negative sentiment patterns are detected."""
        classifier = SentimentClassifier(use_llm=False)
        
        negative_texts = [
            "We're not hiring at the moment.",
            "The position has been filled.",
            "We don't have a fit for your background.",
            "Good luck in your search, but we're not looking.",
        ]
        
        for text in negative_texts:
            result = await classifier.classify(text)
            assert result == SentimentLabel.NEGATIVE, f"Expected NEGATIVE for: {text}"


    @pytest.mark.asyncio
    async def test_unsubscribe_sentiment_patterns(self):
        """Test that unsubscribe patterns are detected."""
        classifier = SentimentClassifier(use_llm=False)
        
        unsubscribe_texts = [
            "Please remove me from your mailing list.",
            "Please unsubscribe me from these emails.",
            "Don't contact me again.",
            "Please opt out from further emails.",
        ]
        
        for text in unsubscribe_texts:
            result = await classifier.classify(text)
            assert result == SentimentLabel.UNSUBSCRIBE, f"Expected UNSUBSCRIBE for: {text}"

    @pytest.mark.asyncio
    async def test_referral_sentiment_patterns(self):
        """Test that referral patterns are detected."""
        classifier = SentimentClassifier(use_llm=False)
        
        # Use patterns that match the actual regex in sentiment.py
        referral_texts = [
            "I'm CC'ing our recruiter Sarah who handles hiring.",
            "Looping in our HR manager to help with this.",
            "Please apply at our careers page.",
        ]
        
        for text in referral_texts:
            result = await classifier.classify(text)
            assert result == SentimentLabel.REFERRAL, f"Expected REFERRAL for: {text}"

    @pytest.mark.asyncio
    async def test_neutral_sentiment_for_ambiguous_text(self):
        """Test that ambiguous text returns neutral sentiment."""
        classifier = SentimentClassifier(use_llm=False)
        
        neutral_texts = [
            "Thanks for your email.",
            "Received.",
            "OK",
        ]
        
        for text in neutral_texts:
            result = await classifier.classify(text)
            assert result == SentimentLabel.NEUTRAL, f"Expected NEUTRAL for: {text}"

    @pytest.mark.asyncio
    async def test_empty_text_returns_neutral(self):
        """Test that empty text returns neutral sentiment."""
        classifier = SentimentClassifier(use_llm=False)
        
        result = await classifier.classify("")
        assert result == SentimentLabel.NEUTRAL
        
        result = await classifier.classify("   ")
        assert result == SentimentLabel.NEUTRAL


# =====================================================================
# Test: Helper Methods
# =====================================================================

class TestHelperMethods:
    """Tests for ReplyDetector helper methods."""

    def test_extract_email_from_header_with_brackets(self, db_session_factory):
        """Test email extraction from header with angle brackets."""
        detector = ReplyDetector(db_session_factory)
        
        result = detector._extract_email_from_header("John Doe <john@example.com>")
        assert result == "john@example.com"

    def test_extract_email_from_header_plain(self, db_session_factory):
        """Test email extraction from plain header."""
        detector = ReplyDetector(db_session_factory)
        
        result = detector._extract_email_from_header("john@example.com")
        assert result == "john@example.com"

    def test_extract_email_normalizes_case(self, db_session_factory):
        """Test that email extraction normalizes to lowercase."""
        detector = ReplyDetector(db_session_factory)
        
        result = detector._extract_email_from_header("John.Doe@EXAMPLE.COM")
        assert result == "john.doe@example.com"


# =====================================================================
# Test: Lifecycle Management
# =====================================================================

class TestLifecycleManagement:
    """Tests for ReplyDetector start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_detector_not_running_initially(self, db_session_factory):
        """Verify detector is not running initially."""
        detector = ReplyDetector(db_session_factory)
        assert detector.is_running is False

    @pytest.mark.asyncio
    async def test_start_without_credentials_logs_warning(self, db_session_factory):
        """Verify starting without credentials doesn't crash."""
        detector = ReplyDetector(db_session_factory)
        detector._email = ""
        detector._password = ""
        # Credentials are empty
        await detector.start()
        # Should not be running without credentials
        assert detector.is_running is False


    @pytest.mark.asyncio
    async def test_stop_cleans_up_resources(self, db_session_factory):
        """Verify stop cleans up resources properly."""
        detector = ReplyDetector(db_session_factory)
        detector._email = "test@gmail.com"
        detector._password = "test_password"
        detector._running = True
        
        # Mock the task
        detector._task = asyncio.create_task(asyncio.sleep(1000))
        
        await detector.stop()
        
        assert detector.is_running is False

    @pytest.mark.asyncio
    async def test_poll_once_for_testing(self, db_session_factory):
        """Verify poll_once method works for testing."""
        detector = ReplyDetector(db_session_factory)
        detector._email = "test@gmail.com"
        detector._password = "test_password"
        
        with patch.object(detector, '_fetch_replies', return_value=[]):
            count = await detector.poll_once()
        
        assert count == 0
        assert detector.stats.poll_count == 1


# =====================================================================
# Test: Contact Model do_not_contact field
# =====================================================================

class TestContactDoNotContactField:
    """Tests for the Contact model do_not_contact field."""

    def test_contact_has_do_not_contact_field(self, test_db):
        """Verify Contact model has do_not_contact field."""
        contact = Contact(
            name="Test User",
            email="test@example.com",
            company="TestCorp",
        )
        test_db.add(contact)
        test_db.commit()
        
        assert hasattr(contact, 'do_not_contact')
        assert contact.do_not_contact is False  # Default

    def test_contact_do_not_contact_can_be_set(self, test_db):
        """Verify do_not_contact field can be set to True."""
        contact = Contact(
            name="Test User",
            email="test@example.com",
            company="TestCorp",
            do_not_contact=True,
            do_not_contact_reason="unsubscribe_reply",
        )
        test_db.add(contact)
        test_db.commit()
        
        assert contact.do_not_contact is True
        assert contact.do_not_contact_reason == "unsubscribe_reply"

    def test_contact_do_not_contact_timestamp(self, test_db):
        """Verify do_not_contact_at timestamp field exists."""
        now = datetime.now(timezone.utc)
        contact = Contact(
            name="Test User",
            email="test@example.com",
            company="TestCorp",
            do_not_contact=True,
            do_not_contact_at=now,
        )
        test_db.add(contact)
        test_db.commit()
        
        assert contact.do_not_contact_at is not None
