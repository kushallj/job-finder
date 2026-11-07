"""Jobify Phase 4: Founders list, facets, saved, credit-debited unlock (emails gated)."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import get_db
from src.models import Base, CompanyFounder, CreditTransaction, FounderUnlock, Job, PortfolioCompany, User, VCFirm
from src.jobify.services import founders as jf


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client(db_session, clerk_auth):
    from main import app

    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def data(db_session):
    india_vc = VCFirm(name="Blume", slug="blume", country_focus="India")
    global_vc = VCFirm(name="YC", slug="yc", country_focus="Global")
    db_session.add_all([india_vc, global_vc])
    db_session.flush()
    fresh = PortfolioCompany(vc_firm_id=india_vc.id, name="Freshworks", slug="freshworks", domain="freshworks.com",
                             description="CRM and ITSM", industry_tags=json.dumps(["Enterprise SaaS", "CRM"]))
    zepto = PortfolioCompany(vc_firm_id=global_vc.id, name="Zepto", slug="zepto", domain="zeptonow.in",
                             description="Quick commerce", industry_tags="Consumer, Delivery")
    stripe = PortfolioCompany(vc_firm_id=global_vc.id, name="Stripe", slug="stripe", website="https://stripe.com",
                              description="Payments", industry_tags=json.dumps(["Fintech"]))
    db_session.add_all([fresh, zepto, stripe])
    db_session.flush()
    db_session.add_all([
        CompanyFounder(company_id=fresh.id, full_name="Girish Mathrubootham", title="Founder & CEO", email="girish@freshworks.com",
                       linkedin_url="https://linkedin.com/in/girish", twitter_handle="@mrgirish"),
        CompanyFounder(company_id=fresh.id, full_name="Shan Krishnasamy", title="Co-founder", email="shan@freshworks.com"),
        CompanyFounder(company_id=zepto.id, full_name="Aadit Palicha", title="CEO", email="aadit@zeptonow.com"),
    ])
    db_session.add(Job(job_id="j1", title="Backend Engineer", company="Freshworks", url="https://x"))
    db_session.commit()
    return {"fresh": fresh, "zepto": zepto, "stripe": stripe}


def _auth(clerk_auth, who="a"):
    return clerk_auth.headers(f"user_{who}", f"{who}@example.com")


def _list(client, h, **params):
    return client.get("/api/founders", headers=h, params=params).json()


def test_requires_auth(client):
    assert client.get("/api/founders").status_code == 401


def test_list_shape_and_derived_fields(client, clerk_auth, data):
    body = _list(client, _auth(clerk_auth))
    assert set(body) == {"items", "total", "page", "pageSize"} and body["total"] == 3
    by = {c["name"]: c for c in body["items"]}
    fresh = by["Freshworks"]
    assert set(fresh) == {"id", "name", "website", "location", "country", "industry", "description", "hiring", "founders"}
    assert (fresh["country"], fresh["industry"], fresh["hiring"], fresh["website"]) == ("India", "Enterprise SaaS", True, "https://freshworks.com")
    assert by["Zepto"]["country"] == "India" and by["Zepto"]["industry"] == "Consumer"   # .in ccTLD, comma tags
    assert by["Stripe"]["country"] == "Unknown" and by["Stripe"]["location"] == ""      # global VC, .com: not guessed
    g = fresh["founders"][0]
    assert g == {"id": g["id"], "name": "Girish Mathrubootham", "initials": "GM", "role": "Founder & CEO",
                 "linkedin": "https://linkedin.com/in/girish", "x": "https://x.com/mrgirish"}
    assert fresh["founders"][1]["linkedin"] is None


def test_emails_never_in_list_before_unlock(client, clerk_auth, data):
    raw = client.get("/api/founders", headers=_auth(clerk_auth)).text
    assert "@freshworks.com" not in raw and "@zeptonow.com" not in raw and '"email"' not in raw


def test_filters_search_and_pagination(client, clerk_auth, data):
    h = _auth(clerk_auth)
    names = lambda **p: [c["name"] for c in _list(client, h, **p)["items"]]
    assert names(country="India") == ["Freshworks", "Zepto"]
    assert names(industry="Fintech") == ["Stripe"]
    assert names(hiringOnly="true") == ["Freshworks"]
    assert names(q="aadit") == ["Zepto"]          # founder name search
    assert names(q="itsm") == ["Freshworks"]       # description search
    page2 = _list(client, h, page=2, pageSize=2)
    assert (page2["total"], len(page2["items"]), page2["page"]) == (3, 1, 2)


def test_facets(client, clerk_auth, data):
    f = client.get("/api/founders/facets", headers=_auth(clerk_auth)).json()
    assert f == {"countries": ["India", "Unknown"], "industries": ["Consumer", "Enterprise SaaS", "Fintech"], "unlockCost": 5}


def test_unlock_charges_once_and_reveals_emails(client, clerk_auth, db_session, data):
    h = _auth(clerk_auth)
    cid = data["fresh"].id
    res = client.post(f"/api/founders/{cid}/unlock", headers=h)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True and body["cost"] == 5 and body["state"]["unlocked"] == [str(cid)]
    assert [f["email"] for f in body["company"]["founders"]] == ["girish@freshworks.com", "shan@freshworks.com"]
    assert client.get("/api/me/subscription", headers=h).json()["creditsRemaining"] == 45
    again = client.post(f"/api/founders/{cid}/unlock", headers=h).json()
    assert again["cost"] == 0
    assert client.get("/api/me/subscription", headers=h).json()["creditsRemaining"] == 45
    listed = {c["name"]: c for c in _list(client, h)["items"]}
    assert listed["Freshworks"]["founders"][0]["email"] == "girish@freshworks.com"
    assert "email" not in listed["Zepto"]["founders"][0]      # other companies stay locked
    tx = db_session.query(CreditTransaction).filter(CreditTransaction.action == "founder_unlock").all()
    assert len(tx) == 1 and tx[0].amount == -5


def test_unlock_without_credits_is_402_and_reveals_nothing(client, clerk_auth, db_session, data):
    h = _auth(clerk_auth)
    client.get("/api/me", headers=h)
    user = db_session.query(User).filter(User.clerk_user_id == "user_a").one()
    user.credits_balance = 3
    db_session.commit()
    res = client.post(f"/api/founders/{data['fresh'].id}/unlock", headers=h)
    assert res.status_code == 402 and res.json()["error"]["code"] == "CREDITS_REQUIRED"
    assert db_session.query(FounderUnlock).count() == 0
    assert "@freshworks.com" not in client.get("/api/founders", headers=h).text
    db_session.refresh(user)
    assert user.credits_balance == 3


def test_unlock_is_per_user(client, clerk_auth, data):
    a, b = _auth(clerk_auth, "a"), _auth(clerk_auth, "b")
    client.post(f"/api/founders/{data['fresh'].id}/unlock", headers=a)
    assert "@freshworks.com" not in client.get("/api/founders", headers=b).text
    assert client.get("/api/me/founders/state", headers=b).json() == {"saved": [], "unlocked": []}


def test_concurrent_duplicate_unlock_is_refunded(db_session, data, monkeypatch):
    user = User(email="u@example.com", credits_balance=50)
    db_session.add(user)
    db_session.commit()
    cid = data["fresh"].id
    real_query = db_session.query

    def racing_query(*args, **kw):
        q = real_query(*args, **kw)
        if args and args[0] is FounderUnlock.id:  # pretend the "already unlocked?" check lost the race
            db_session.query = real_query
            return real_query(FounderUnlock.id).filter(False)
        return q

    db_session.add(FounderUnlock(user_id=user.id, company_id=cid, credits_spent=5))
    db_session.commit()
    monkeypatch.setattr(db_session, "query", racing_query)
    result = jf.unlock(db_session, user, cid)
    db_session.refresh(user)
    assert result == {"cost": 0, "already": True} and user.credits_balance == 50


def test_unlock_unknown_company_404_no_charge(client, clerk_auth, data):
    h = _auth(clerk_auth)
    res = client.post("/api/founders/99999/unlock", headers=h)
    assert res.status_code == 404 and res.json()["error"]["code"] == "NOT_FOUND"
    assert client.get("/api/me/subscription", headers=h).json()["creditsRemaining"] == 50


def test_saved_toggle_explicit_and_isolation(client, clerk_auth, data):
    a, b = _auth(clerk_auth, "a"), _auth(clerk_auth, "b")
    cid = str(data["zepto"].id)
    assert client.put(f"/api/me/founders/{cid}/saved", headers=a).json()["saved"] == [cid]
    assert client.put(f"/api/me/founders/{cid}/saved", headers=a).json()["saved"] == []
    assert client.put(f"/api/me/founders/{cid}/saved", headers=a, json={"saved": True}).json()["saved"] == [cid]
    assert client.put(f"/api/me/founders/{cid}/saved", headers=a, json={"saved": True}).json()["saved"] == [cid]
    assert client.get("/api/me/founders/state", headers=b).json()["saved"] == []
    assert client.put("/api/me/founders/99999/saved", headers=a).status_code == 404

# --- imported repo datasets (src/vc_intelligence/import_founder_data.py) --------------------------

def test_import_real_repo_datasets_idempotent_and_honest(db_session):
    from sqlalchemy import func
    from src.vc_intelligence.import_founder_data import run_import

    first = run_import(db_session)
    assert first["companies_created"] > 1500 and first["founders_created"] > 700
    assert first["placeholders_skipped"] > 0
    second = run_import(db_session)
    assert second["companies_created"] == 0 and second["founders_created"] == 0       # idempotent
    names = [n for (n,) in db_session.query(CompanyFounder.full_name)]
    assert not any(n.lower().endswith(" founder") for n in names)                    # placeholders never imported
    assert db_session.query(CompanyFounder).filter(CompanyFounder.email_verified == True).count() == 0  # noqa: E712
    dup = (db_session.query(PortfolioCompany.domain).filter(PortfolioCompany.domain.isnot(None))
           .group_by(PortfolioCompany.domain).having(func.count() > 1).count())
    assert dup == 0


def test_placeholder_detection_and_email_confidence():
    from src.vc_intelligence.import_founder_data import email_confidence, is_placeholder

    assert is_placeholder("Reevo Founder", "founder@reevo.com", None)
    assert is_placeholder("Jane Doe", "hello@x.com", None)
    assert is_placeholder("Jane Doe", "jane@x.com", "https://linkedin.com/company/x")
    assert not is_placeholder("Kevin Tian", "kevin.tian@doppel.com", "https://linkedin.com/in/ktian00")
    assert email_confidence("Kevin Tian", "kevin.tian@doppel.com") == 0.3   # pure name pattern = guess
    assert email_confidence("Kevin Tian", "kt@doppel.com") == 0.5


def test_stored_location_wins_and_companies_with_founders_first(client, clerk_auth, db_session, data):
    data["stripe"].location = "San Francisco, United States"
    data["stripe"].jobs_count = 12
    db_session.commit()
    items = _list(client, _auth(clerk_auth))["items"]
    stripe = next(c for c in items if c["name"] == "Stripe")
    assert (stripe["country"], stripe["location"], stripe["hiring"]) == ("USA", "San Francisco, United States", True)
    assert [bool(c["founders"]) for c in items] == sorted([bool(c["founders"]) for c in items], reverse=True)


def test_cannot_unlock_company_without_founders(client, clerk_auth, data):
    h = _auth(clerk_auth)
    res = client.post(f"/api/founders/{data['stripe'].id}/unlock", headers=h)
    assert res.status_code == 409 and res.json()["error"]["code"] == "NO_FOUNDERS"
    assert client.get("/api/me/subscription", headers=h).json()["creditsRemaining"] == 50


def test_unlocked_emails_are_flagged_unverified(client, clerk_auth, data):
    body = client.post(f"/api/founders/{data['fresh'].id}/unlock", headers=_auth(clerk_auth)).json()
    assert all(f["emailVerified"] is False for f in body["company"]["founders"])


@pytest.mark.parametrize("raw,expected", [
    ("San Francisco, United States", "USA"), ("France, European Union, United Kingdom · Oct 15, 2026", "UK"),
    ("Singapore / Asia", "Singapore"), ("US", "USA"), ("Global", None), ("2026", None), ("Remote", None),
    ("Auckland, New Zealand and growing fast!", "New Zealand"), ("Offices in Melbourne and Sydney.", None)])
def test_normalize_country(raw, expected):
    assert jf.normalize_country(raw) == expected


def test_import_keeps_catalog_industries(db_session):
    from src.vc_intelligence.import_founder_data import run_import

    run_import(db_session)
    notion = db_session.query(PortfolioCompany).filter(PortfolioCompany.domain == "makenotion.com").one()
    assert json.loads(notion.industry_tags) and "Productivity" in json.loads(notion.industry_tags)
