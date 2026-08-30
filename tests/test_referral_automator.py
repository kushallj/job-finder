import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from src.referral.models import ReferralProfile, ReferralContext
from src.referral.rate_limiter import InMemoryTokenBucket
from src.referral.message_generator import ReferralMessageGenerator
from src.referral.linkedin_client import LinkedInClient
from src.referral.service import ReferralService
from src.models import Contact, OutreachRecord, Job
from src.database import db_session


@pytest.fixture
def client():
    return TestClient(app)


def test_referral_models():
    prof = ReferralProfile(
        full_name="Bob Smith",
        first_name="Bob",
        company="Stripe",
        title="Staff Engineer",
        linkedin_url="https://linkedin.com/in/bobsmith",
    )
    assert prof.full_name == "Bob Smith"
    assert prof.company == "Stripe"
    assert prof.source == "csv"

    ctx = ReferralContext(
        job_title="Senior Backend Engineer",
        job_link="https://stripe.com/jobs/123",
        company="Stripe",
        sender_name="Kushal",
    )
    assert ctx.job_title == "Senior Backend Engineer"


def test_token_bucket_rate_limiter():
    limiter = InMemoryTokenBucket(rate=10.0, capacity=2.0)
    assert limiter.allow("test", 1.0) is True
    assert limiter.allow("test", 1.0) is True
    assert limiter.allow("test", 1.0) is False  # capacity reached


def test_message_generator():
    gen = ReferralMessageGenerator()
    prof = ReferralProfile(
        full_name="Sarah Jenkins",
        company="Meta",
        title="Engineering Manager",
    )
    ctx = ReferralContext(
        job_title="Staff AI Engineer",
        job_link="https://meta.com/jobs/456",
        short_bio="distributed AI infrastructure",
        highlight="cutting latency by 40%",
        sender_name="Kushal",
    )

    letter = gen.generate_letter(prof, ctx)
    assert "Sarah" in letter
    assert "Meta" in letter
    assert "Staff AI Engineer" in letter
    assert "Kushal" in letter

    note_200 = gen.generate_connection_note(prof, ctx, max_length=200)
    assert len(note_200) <= 200
    assert "Sarah" in note_200


def test_linkedin_client_csv_search():
    client = LinkedInClient()
    results = client.search_by_company("Meta", limit=5)
    assert len(results) >= 1
    assert any(p.company and "Meta" in p.company for p in results)

    # Fuzzy search case insensitive
    google_res = client.search_by_company("google", limit=5)
    assert len(google_res) >= 1
    assert any("Google" in (p.company or "") for p in google_res)


def test_referral_service_sync_and_log():
    service = ReferralService()
    uid = uuid.uuid4().hex[:8]

    with db_session() as db:
        # 1. Targets
        targets = service.get_active_targets(db, limit=10)
        assert isinstance(targets, list)

        # 2. Sync profiles
        profiles_payload = [
            {
                "full_name": f"Test Referral {uid}",
                "company": f"TestCorp-{uid}",
                "title": "Lead Architect",
                "linkedin_url": f"https://linkedin.com/in/test-referral-{uid}",
            }
        ]
        sync_res = service.sync_profiles_to_contacts(db, profiles_payload)
        assert sync_res["synced_count"] >= 1

        # Verify DB entry
        saved = db.query(Contact).filter(Contact.linkedin_url == f"https://linkedin.com/in/test-referral-{uid}").first()
        assert saved is not None
        assert saved.company == f"TestCorp-{uid}"

        # 3. Log action
        rec = service.log_referral_action(
            db,
            contact_name=f"Test Referral {uid}",
            company=f"TestCorp-{uid}",
            action_type="connection_sent",
            linkedin_url=f"https://linkedin.com/in/test-referral-{uid}",
            message_body="Hi Test, would love to connect!",
        )
        assert rec.id is not None
        assert rec.status == "sent"
        assert rec.template_type == "linkedin_referral"


def test_referrals_api_endpoints(client):
    uid = uuid.uuid4().hex[:8]

    # 1. GET /api/referrals/targets
    res = client.get("/api/referrals/targets")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "targets" in data

    # 2. POST /api/referrals/search
    res = client.post("/api/referrals/search", json={"company": "Meta", "limit": 5})
    assert res.status_code == 200
    search_data = res.json()
    assert search_data["status"] == "success"
    assert search_data["company"] == "Meta"
    assert len(search_data["profiles"]) >= 1

    # 3. POST /api/referrals/generate-note
    note_req = {
        "full_name": "Carol Singh",
        "company": "Meta",
        "job_title": "Software Engineer",
        "sender_name": "Kushal",
        "max_length": 200,
    }
    res = client.post("/api/referrals/generate-note", json=note_req)
    assert res.status_code == 200
    note_data = res.json()
    assert note_data["status"] == "success"
    assert note_data["is_under_limit"] is True
    assert note_data["char_count"] <= 200

    # 4. POST /api/referrals/sync
    sync_req = {
        "profiles": [
            {
                "full_name": f"Endpoint User {uid}",
                "company": f"SyncCorp-{uid}",
                "title": "Staff Engineer",
                "linkedin_url": f"https://linkedin.com/in/endpoint-{uid}",
            }
        ]
    }
    res = client.post("/api/referrals/sync", json=sync_req)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # 5. POST /api/referrals/log-action
    log_req = {
        "contact_name": f"Endpoint User {uid}",
        "company": f"SyncCorp-{uid}",
        "action_type": "message_sent",
        "linkedin_url": f"https://linkedin.com/in/endpoint-{uid}",
        "message_body": "Sent referral pitch!",
    }
    res = client.post("/api/referrals/log-action", json=log_req)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert "outreach_id" in res.json()
