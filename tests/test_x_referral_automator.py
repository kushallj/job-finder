import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from main import app
from src.x_referral.models import XProfile, XTweet, XContext
from src.x_referral.auth import XOAuthHandler
from src.x_referral.rate_limiter import XRateLimiter
from src.x_referral.message_generator import XMessageGenerator
from src.x_referral.client import XClient
from src.x_referral.service import XReferralService
from src.models import Contact, OutreachRecord, XOAuthToken
from src.database import db_session, init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def test_x_models():
    prof = XProfile(
        x_user_id="101",
        username="sama",
        name="Sam Altman",
        company="OpenAI",
        title="CEO",
    )
    assert prof.username == "sama"
    assert prof.x_url == "https://x.com/sama"

    tweet = XTweet(
        tweet_id="998877",
        author_username="levelsio",
        text="We are hiring Python developers!",
    )
    assert tweet.tweet_id == "998877"
    assert tweet.tweet_url == "https://x.com/levelsio/status/998877"

    ctx = XContext(
        company="OpenAI",
        role_title="Systems Engineer",
        candidate_bio="scaling distributed systems",
        sender_name="Kushal",
    )
    assert ctx.company == "OpenAI"


def test_x_oauth_pkce():
    oauth = XOAuthHandler()
    verifier, challenge = oauth.generate_pkce_pair()
    assert len(verifier) >= 43
    assert len(challenge) > 0
    assert "=" not in challenge  # Unpadded base64url

    auth_data = oauth.get_authorization_url()
    assert "https://twitter.com/i/oauth2/authorize" in auth_data["authorization_url"]
    assert "code_challenge=" in auth_data["authorization_url"]
    assert "code_challenge_method=S256" in auth_data["authorization_url"]

    # Token save in DB
    with db_session() as db:
        token_data = {
            "access_token": "test_access_token_123",
            "refresh_token": "test_refresh_token_123",
            "expires_in": 7200,
            "scope": "tweet.read tweet.write",
        }
        token_rec = oauth.save_token(
            db, token_data, user_identifier="test_user_pkce", x_username="test_pkce"
        )
        assert token_rec.id is not None
        assert token_rec.x_username == "test_pkce"
        assert token_rec.access_token == "test_access_token_123"


def test_x_rate_limiter():
    limiter = XRateLimiter(rate_per_min=60.0, burst=2.0)
    assert limiter.allow(1.0) is True
    assert limiter.allow(1.0) is True
    assert limiter.allow(1.0) is False  # Capacity reached

    # Daily cap check
    assert limiter.check_daily_limit("dm") is True
    for _ in range(15):
        limiter.record_daily_action("dm")
    assert limiter.check_daily_limit("dm") is False  # 15/15 reached


def test_x_message_generator():
    gen = XMessageGenerator()
    prof = XProfile(
        x_user_id="101",
        username="sama",
        name="Sam Altman",
        company="OpenAI",
    )
    ctx = XContext(
        company="OpenAI",
        role_title="Distributed Systems Lead",
        candidate_bio="AI infra and fast streaming APIs",
        highlight="lowered inference latency by 45%",
        sender_name="Kushal",
        target_topic="training clusters",
    )

    dm = gen.generate_dm(prof, ctx, max_length=500)
    assert "@sama" in dm
    assert "OpenAI" in dm
    assert "Distributed Systems Lead" in dm
    assert len(dm) <= 500

    reply = gen.generate_tweet_reply(prof, context=ctx, max_length=280)
    assert len(reply) <= 280
    assert "@sama" in reply

    quote = gen.generate_quote_tweet(prof, context=ctx, max_length=280)
    assert len(quote) <= 280


def test_x_client_csv_search():
    client = XClient()
    users = client.search_users_by_company("OpenAI", limit=5)
    assert len(users) >= 1
    assert any("OpenAI" in (u.company or "") for u in users)

    # Hiring tweets search
    tweets = client.search_hiring_tweets("Stripe", limit=5)
    assert len(tweets) >= 1
    assert any("Stripe" in t.text for t in tweets)

    # Intent URL builder
    reply_url = client.get_intent_url("reply", tweet_id="18001001", text="Great insights!")
    assert "https://x.com/intent/tweet" in reply_url
    assert "in_reply_to=18001001" in reply_url


@pytest.mark.asyncio
async def test_x_service_sync_and_engage():
    service = XReferralService()
    uid = uuid.uuid4().hex[:8]

    with db_session() as db:
        # 1. Active targets
        targets = service.get_active_targets(db, limit=10)
        assert isinstance(targets, list)

        # 2. Sync profiles
        profiles_payload = [
            {
                "name": f"X Tech Lead {uid}",
                "username": f"tech_lead_{uid}",
                "company": f"TechCorp-{uid}",
                "title": "Principal Architect",
            }
        ]
        sync_res = service.sync_profiles_to_contacts(db, profiles_payload)
        assert sync_res["synced_count"] >= 1

        # Verify DB contact
        saved = db.query(Contact).filter(Contact.linkedin_url == f"https://x.com/tech_lead_{uid}").first()
        assert saved is not None
        assert saved.source == "x_referral"

        # 3. Engage user
        res = await service.engage_user(
            db=db,
            action_type="follow",
            target_username=f"tech_lead_{uid}",
            company=f"TechCorp-{uid}",
            message_text=None,
        )
        assert res["status"] == "success"
        assert res["outreach_id"] is not None

        # Verify outreach record
        rec = db.query(OutreachRecord).filter(OutreachRecord.id == res["outreach_id"]).first()
        assert rec.template_type == "x_referral"


def test_x_api_endpoints(client):
    uid = uuid.uuid4().hex[:8]

    # 1. GET /api/x/auth/url
    res = client.get("/api/x/auth/url")
    assert res.status_code == 200
    assert "authorization_url" in res.json()

    # 2. POST /api/x/auth/callback (mock exchange)
    cb_req = {"code": "test_code_123", "state": "test_state_123"}
    res = client.post("/api/x/auth/callback", json=cb_req)
    assert res.status_code == 200
    assert res.json()["connected"] is True

    # 3. GET /api/x/auth/status
    res = client.get("/api/x/auth/status")
    assert res.status_code == 200
    assert res.json()["connected"] is True

    # 4. GET /api/x/targets
    res = client.get("/api/x/targets")
    assert res.status_code == 200
    assert "targets" in res.json()

    # 5. POST /api/x/search
    res = client.post("/api/x/search", json={"company": "OpenAI", "limit": 3})
    assert res.status_code == 200
    assert len(res.json()["profiles"]) >= 1

    # 6. POST /api/x/search-tweets
    res = client.post("/api/x/search-tweets", json={"company": "OpenAI", "limit": 3})
    assert res.status_code == 200
    assert len(res.json()["tweets"]) >= 1

    # 7. POST /api/x/generate-message
    gen_req = {
        "action_type": "reply",
        "username": "sama",
        "company": "OpenAI",
        "role_title": "AI Systems Engineer",
        "sender_name": "Kushal",
    }
    res = client.post("/api/x/generate-message", json=gen_req)
    assert res.status_code == 200
    assert res.json()["is_under_limit"] is True
    assert "intent_url" in res.json()

    # 8. POST /api/x/engage
    engage_req = {
        "action_type": "like",
        "target_username": f"user_{uid}",
        "company": f"Company-{uid}",
        "tweet_id": "18001001",
    }
    res = client.post("/api/x/engage", json=engage_req)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert "outreach_id" in res.json()

    # 9. POST /api/x/sync
    sync_req = {
        "profiles": [
            {
                "name": f"Endpoint X User {uid}",
                "username": f"endpoint_x_{uid}",
                "company": f"SyncX-{uid}",
                "title": "Staff Engineer",
            }
        ]
    }
    res = client.post("/api/x/sync", json=sync_req)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
