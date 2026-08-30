import pytest
from fastapi.testclient import TestClient

from main import app
from src.email_intelligence.domain_resolver import DomainResolver, clean_company_name, normalize_domain_from_url
from src.email_intelligence.dorking_engine import GoogleDorkingEngine
from src.email_intelligence.pattern_synthesizer import CorporatePatternSynthesizer
from src.email_intelligence.verifier import EmailVerifier
from src.email_intelligence.persona_scorer import PersonaScorer
from src.email_intelligence.service import EmailIntelligenceService
from src.models import DiscoveredEmailCache, Contact
from src.database import db_session, init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def test_clean_company_and_domain_normalization():
    assert clean_company_name("Stripe, Inc.") == "Stripe"
    assert clean_company_name("Anthropic Technologies LLC") == "Anthropic"
    assert clean_company_name("OpenAI Global LLC") == "OpenAI"

    assert normalize_domain_from_url("https://www.openai.com/careers/jobs") == "openai.com"
    assert normalize_domain_from_url("http://stripe.com") == "stripe.com"


@pytest.mark.asyncio
async def test_domain_resolver():
    resolver = DomainResolver()
    domain = await resolver.resolve_corporate_domain("Stripe Inc", website_hint="https://stripe.com/about")
    assert domain == "stripe.com"

    has_mx, hosts, provider = resolver.check_mx_records("google.com")
    assert has_mx is True
    assert provider == "Google Workspace"


def test_google_dorking_engine():
    dorker = GoogleDorkingEngine()
    dorks = dorker.generate_dorks("Stripe", domain="stripe.com", person_name="John Doe", role_title="Engineering Manager")
    assert len(dorks) >= 4
    assert any("site:linkedin.com/in/" in d.query for d in dorks)
    assert any("site:github.com" in d.query for d in dorks)

    # Obfuscation and extraction
    raw_sample = "Contact our team: alex.smith [at] stripe.com or reach John Doe at jdoe@stripe.com (Engineering Manager)"
    extracted = dorker.decode_and_extract_emails(raw_sample, domain="stripe.com")
    assert len(extracted) >= 2
    emails = [e[0] for e in extracted]
    assert "alex.smith@stripe.com" in emails
    assert "jdoe@stripe.com" in emails


def test_corporate_pattern_synthesizer():
    synth = CorporatePatternSynthesizer()
    first, last = synth.tokenize_name("Kushall Jain")
    assert first == "kushall"
    assert last == "jain"

    perms = synth.generate_permutations("Kushall Jain", domain="company.com", has_mx=True)
    assert len(perms) == 12
    emails = [p.email for p in perms]
    assert "kushall.jain@company.com" in emails
    assert "kushall@company.com" in emails
    assert "kjain@company.com" in emails

    # Pattern learning
    synth.learn_pattern_from_sample("kushall.jain@company.com", "Kushall Jain")
    learned_perms = synth.generate_permutations("Sarah Connor", domain="company.com", has_mx=True)
    assert learned_perms[0].email == "sarah.connor@company.com"
    assert learned_perms[0].confidence_score >= 90.0


def test_email_verifier():
    verifier = EmailVerifier()
    # 1. Valid syntax & MX
    res1 = verifier.verify_email("test@google.com")
    assert res1.is_valid_syntax is True
    assert res1.is_disposable is False
    assert res1.status == "valid"
    assert res1.confidence_score >= 80.0

    # 2. Disposable email
    res2 = verifier.verify_email("temporary@mailinator.com")
    assert res2.is_disposable is True
    assert res2.status == "disposable"

    # 3. Invalid syntax
    res3 = verifier.verify_email("not-an-email")
    assert res3.is_valid_syntax is False
    assert res3.status == "invalid"


def test_persona_scorer():
    assert PersonaScorer.score_title("Engineering Manager") == 100
    assert PersonaScorer.score_title("Head of Engineering") == 90
    assert PersonaScorer.score_title("VP of Engineering") == 85
    assert PersonaScorer.score_title("Technical Recruiter") == 80
    assert PersonaScorer.score_title("Director of Engineering") == 75
    assert PersonaScorer.score_title("Staff Software Engineer") == 70
    assert PersonaScorer.score_title("Co-Founder & CTO") == 65
    assert PersonaScorer.score_title("Senior Python Developer") == 50


@pytest.mark.asyncio
async def test_email_intelligence_service_waterfall():
    service = EmailIntelligenceService()
    with db_session() as db:
        res = await service.discover_company_decision_makers(
            db=db,
            company="OpenAI",
            job_title="Senior Backend Engineer",
            target_name="Sam Altman",
            limit=4,
        )
        assert res["company"] == "OpenAI"
        assert res["domain"] == "openai.com"
        assert res["total_found"] >= 1
        assert res["recommended_contact"] is not None

        # Verify DB Cache
        cached = db.query(DiscoveredEmailCache).filter(DiscoveredEmailCache.company == "OpenAI").all()
        assert len(cached) >= 1

        # Verify Contact CRM sync
        crm_contact = db.query(Contact).filter(Contact.company == "OpenAI").first()
        assert crm_contact is not None


def test_email_intelligence_api_endpoints(client):
    # 1. POST /api/email-intelligence/discover
    res = client.post("/api/email-intelligence/discover", json={
        "company": "Stripe",
        "job_title": "Distributed Systems Engineer",
        "target_name": "Patrick Collison",
        "limit": 3,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert len(res.json()["contacts"]) >= 1

    # 2. POST /api/email-intelligence/verify
    res = client.post("/api/email-intelligence/verify", json={"email": "contact@google.com"})
    assert res.status_code == 200
    assert res.json()["is_valid_syntax"] is True

    # 3. POST /api/email-intelligence/dorks
    res = client.post("/api/email-intelligence/dorks", json={
        "company": "Anthropic",
        "domain": "anthropic.com",
        "person_name": "Dario Amodei",
    })
    assert res.status_code == 200
    assert res.json()["total_dorks"] >= 4

    # 4. POST /api/email-intelligence/permutations
    res = client.post("/api/email-intelligence/permutations", json={
        "full_name": "Elena Vance",
        "domain": "anthropic.com",
    })
    assert res.status_code == 200
    assert res.json()["total_permutations"] == 12
