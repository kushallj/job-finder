"""
Integration tests for personalization pipeline.

Tests Requirements 15.1, 15.2, 15.3, 15.4, 15.5:
- 15.1: PersonalizationEngine SHALL research the target company
- 15.2: PersonalizationEngine SHALL research the target contact
- 15.3: PersonalizationEngine SHALL generate a personalized hook based on research
- 15.4: PersonalizationEngine SHALL compose a complete email with the hook
- 15.5: PersonalizationEngine SHALL include the tailored resume in the outreach email

Task 20.1: Verify personalization pipeline
- Test company research data collection
- Test contact research data collection
- Test personalized hook generation
- Test email composition with hook integration
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.personalization.personalization_engine import PersonalizationEngine
from src.personalization.company_researcher import CompanyResearcher
from src.personalization.contact_researcher import ContactResearcher
from src.personalization.hook_generator import HookGenerator
from src.personalization.email_composer import EmailComposer
from src.personalization.models import (
    CompanyProfile,
    ContactProfile,
    Hook,
    HookType,
    PersonalizedEmail,
    PersonalizedOutreach,
)


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_company_profile():
    """Return a rich company profile for testing."""
    return CompanyProfile(
        domain="stripe.com",
        name="Stripe",
        tagline="Online payment processing for internet businesses",
        tech_stack=["Python", "Ruby", "Go", "React", "PostgreSQL", "Redis"],
        recent_news=[
            "Stripe launches new financial connections API",
            "How we scaled our payment processing to 1M TPS",
        ],
        growth_signals=["Series H funding raised $600M", "Expanded to APAC region"],
        pain_points=["high-scale transactions", "payment security"],
        culture_keywords=["ownership", "async-first", "open source"],
        github_org="stripe",
        recent_repos=[
            "stripe-android: Android SDK for Stripe payments",
            "veneur: High-performance metrics aggregation",
        ],
        hn_mentions=["Stripe's new approach to API versioning"],
        research_sources=["https://stripe.com", "https://github.com/stripe"],
    )


@pytest.fixture
def sample_contact_profile():
    """Return a rich contact profile for testing."""
    return ContactProfile(
        name="Jane Smith",
        github_username="janesmith",
        bio="Infrastructure engineer interested in distributed systems and Rust",
        languages=["Python", "Go", "Rust"],
        recent_repos=[
            "distributed-cache: A high-performance distributed caching system",
            "config-parser: Fast configuration parser in Rust",
        ],
        pinned_repos=["distributed-cache: My best work on distributed systems"],
        recent_topics=["distributed-systems", "infrastructure", "performance"],
        blog_posts=["Building fault-tolerant systems at scale"],
        technical_keywords=["distributed", "systems", "Rust", "infrastructure", "performance"],
        research_sources=["https://github.com/janesmith"],
    )


@pytest.fixture
def minimal_company_profile():
    """Return a minimal company profile (limited data)."""
    return CompanyProfile(
        domain="example.com",
        name="Example Corp",
        tagline="",
        tech_stack=["Python"],
        recent_news=[],
        growth_signals=[],
        pain_points=[],
        culture_keywords=[],
        github_org="",
        recent_repos=[],
        hn_mentions=[],
        research_sources=[],
    )


@pytest.fixture
def minimal_contact_profile():
    """Return a minimal contact profile (limited data)."""
    return ContactProfile(
        name="John Doe",
        github_username="",
        bio="",
        languages=[],
        recent_repos=[],
        pinned_repos=[],
        recent_topics=[],
        blog_posts=[],
        technical_keywords=[],
        research_sources=[],
    )


@pytest.fixture
def sample_jd_text():
    """Return a sample job description."""
    return """
    Senior Backend Engineer - Stripe

    We're looking for an experienced backend engineer to join our payments infrastructure team.

    Requirements:
    - 5+ years of backend development experience
    - Expert knowledge of Python and/or Go
    - Experience building distributed systems at scale
    - Strong understanding of payment systems and security
    - Experience with PostgreSQL, Redis, and message queues

    What you'll do:
    - Design and build high-throughput payment processing systems
    - Optimize database performance for millions of transactions
    - Collaborate with security team on payment fraud detection
    - Mentor junior engineers and drive technical decisions

    Our stack: Python, Go, PostgreSQL, Redis, Kafka, Docker, Kubernetes
    """


# ══════════════════════════════════════════════════════════════════════════════
# Test 1: Company Research Data Collection (Requirement 15.1)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_company_researcher_collects_data():
    """
    Test that CompanyResearcher collects relevant company data from public sources.
    
    Validates Requirement 15.1:
    PersonalizationEngine SHALL research the target company
    """
    researcher = CompanyResearcher()
    
    # Mock HTTP responses for company research
    with patch.object(researcher, '_research_github') as mock_github, \
         patch.object(researcher, '_research_website') as mock_website, \
         patch.object(researcher, '_research_hn') as mock_hn:
        
        # Setup mock return values
        mock_github.return_value = {
            "org": "stripe",
            "repos": ["stripe-python: Python library", "veneur: Metrics"],
            "tech": ["Python", "Go"],
            "sources": ["https://github.com/stripe"],
        }
        
        mock_website.return_value = {
            "headlines": ["Stripe launches new API"],
            "tech": ["React", "PostgreSQL"],
            "growth_signals": ["Series H funding"],
            "pain_points": [],
            "culture_keywords": ["ownership"],
            "tagline": "Payment processing for the internet",
            "sources": ["https://stripe.com"],
        }
        
        mock_hn.return_value = {
            "stories": ["Stripe's new API design"],
            "sources": ["https://hn.algolia.com"],
        }
        
        # Execute research
        profile = await researcher.research("stripe.com", "Stripe")
        
        # Verify data collection
        assert profile.domain == "stripe.com"
        assert profile.name == "Stripe"
        assert profile.github_org == "stripe"
        assert len(profile.recent_repos) > 0
        assert len(profile.tech_stack) > 0
        assert "Python" in profile.tech_stack
        assert len(profile.recent_news) > 0
        assert len(profile.research_sources) > 0
        
        # Verify is_rich property
        assert profile.is_rich is True


@pytest.mark.asyncio
async def test_company_researcher_handles_minimal_data():
    """
    Test that CompanyResearcher gracefully handles limited data availability.
    """
    researcher = CompanyResearcher()
    
    # Mock minimal HTTP responses
    with patch.object(researcher, '_research_github') as mock_github, \
         patch.object(researcher, '_research_website') as mock_website, \
         patch.object(researcher, '_research_hn') as mock_hn:
        
        # Setup minimal mock return values
        mock_github.return_value = {}
        mock_website.return_value = {
            "headlines": [], "tech": [], "growth_signals": [],
            "pain_points": [], "culture_keywords": [], "tagline": "",
            "sources": [],
        }
        mock_hn.return_value = {"stories": [], "sources": []}
        
        # Execute research
        profile = await researcher.research("unknown.com", "Unknown Corp")
        
        # Verify graceful handling
        assert profile.domain == "unknown.com"
        assert profile.name == "Unknown Corp"
        assert profile.is_rich is False  # No rich data available


# ══════════════════════════════════════════════════════════════════════════════
# Test 2: Contact Research Data Collection (Requirement 15.2)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_contact_researcher_collects_data():
    """
    Test that ContactResearcher collects relevant contact data from public sources.
    
    Validates Requirement 15.2:
    PersonalizationEngine SHALL research the target contact
    """
    researcher = ContactResearcher()
    
    # Mock GitHub user research
    with patch.object(researcher, '_research_github_user') as mock_research:
        mock_research.return_value = ContactProfile(
            name="Jane Smith",
            github_username="janesmith",
            bio="Backend engineer at Stripe",
            languages=["Python", "Go", "Rust"],
            recent_repos=[
                "payment-processor: High-throughput payment system",
                "cache-layer: Distributed caching",
            ],
            pinned_repos=["payment-processor: My main project"],
            recent_topics=["distributed-systems", "golang"],
            blog_posts=["Building scalable payment systems"],
            technical_keywords=["distributed", "payment", "Go"],
            research_sources=["https://github.com/janesmith"],
        )
        
        # Mock username discovery
        with patch.object(researcher, '_find_github_username') as mock_find:
            mock_find.return_value = "janesmith"
            
            # Execute research
            profile = await researcher.research(
                name="Jane Smith",
                email="jane@stripe.com",
                linkedin_url="",
                github_hint="",
            )
            
            # Verify data collection
            assert profile.name == "Jane Smith"
            assert profile.github_username == "janesmith"
            assert profile.bio != ""
            assert len(profile.languages) > 0
            assert len(profile.recent_repos) > 0
            assert len(profile.technical_keywords) > 0
            assert len(profile.research_sources) > 0
            
            # Verify is_rich property
            assert profile.is_rich is True


@pytest.mark.asyncio
async def test_contact_researcher_handles_no_github():
    """
    Test that ContactResearcher handles contacts with no GitHub presence.
    """
    researcher = ContactResearcher()
    
    # Mock no GitHub username found
    with patch.object(researcher, '_find_github_username') as mock_find:
        mock_find.return_value = ""
        
        # Execute research
        profile = await researcher.research(
            name="Unknown Person",
            email="unknown@example.com",
        )
        
        # Verify graceful handling
        assert profile.name == "Unknown Person"
        assert profile.github_username == ""
        assert profile.is_rich is False


# ══════════════════════════════════════════════════════════════════════════════
# Test 3: Personalized Hook Generation (Requirement 15.3)
# ══════════════════════════════════════════════════════════════════════════════

def test_hook_generator_creates_personalized_hooks(
    sample_company_profile, sample_contact_profile
):
    """
    Test that HookGenerator generates personalized hooks based on research.
    
    Validates Requirement 15.3:
    PersonalizationEngine SHALL generate a personalized hook based on research
    """
    generator = HookGenerator(ai_service=None)
    
    # Create a minimal JD stub
    class JDStub:
        required_skills = ["Python", "PostgreSQL"]
        tech_stack = ["Python", "Go"]
        pain_points = ["high-scale transactions"]
        culture_keywords = ["ownership"]
    
    jd = JDStub()
    
    # Generate hooks
    hooks = generator.generate(
        company=sample_company_profile,
        contact=sample_contact_profile,
        jd=jd,
        resume=None,
        max_hooks=5,
    )
    
    # Verify hooks are generated
    assert len(hooks) > 0
    assert len(hooks) <= 5
    
    # Verify hook structure
    for hook in hooks:
        assert isinstance(hook, Hook)
        assert isinstance(hook.type, HookType)
        assert hook.text != ""
        assert hook.evidence != ""
        assert 0.0 <= hook.strength <= 1.0
    
    # Verify hooks are ordered by strength
    strengths = [h.strength for h in hooks]
    assert strengths == sorted(strengths, reverse=True)
    
    # Verify at least one non-generic hook (we have rich data)
    non_generic_hooks = [h for h in hooks if h.type != HookType.GENERIC]
    assert len(non_generic_hooks) > 0


def test_hook_generator_prioritizes_contact_resonance(sample_contact_profile):
    """
    Test that HookGenerator prioritizes contact-specific hooks (highest strength).
    """
    generator = HookGenerator(ai_service=None)
    
    minimal_company = CompanyProfile(domain="test.com", name="Test")
    
    class JDStub:
        required_skills = []
        tech_stack = []
        pain_points = []
        culture_keywords = []
    
    jd = JDStub()
    
    # Generate hooks with rich contact profile
    hooks = generator.generate(
        company=minimal_company,
        contact=sample_contact_profile,
        jd=jd,
        resume=None,
        max_hooks=3,
    )
    
    # The top hook should be CONTACT_RESONANCE (highest priority)
    assert len(hooks) > 0
    top_hook = hooks[0]
    assert top_hook.type == HookType.CONTACT_RESONANCE
    assert top_hook.strength >= 0.75  # High strength for contact-specific


def test_hook_generator_creates_generic_fallback(
    minimal_company_profile, minimal_contact_profile
):
    """
    Test that HookGenerator creates generic fallback when no data available.
    """
    generator = HookGenerator(ai_service=None)
    
    class JDStub:
        required_skills = []
        tech_stack = []
        pain_points = []
        culture_keywords = []
        role_focus = "Software Engineer"
    
    jd = JDStub()
    
    # Generate hooks with minimal data
    hooks = generator.generate(
        company=minimal_company_profile,
        contact=minimal_contact_profile,
        jd=jd,
        resume=None,
        max_hooks=3,
    )
    
    # Should always return at least one hook (generic fallback)
    assert len(hooks) >= 1
    
    # Check if any hook is generic
    generic_hooks = [h for h in hooks if h.type == HookType.GENERIC]
    assert len(generic_hooks) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Test 4: Email Composition with Hook Integration (Requirement 15.4)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_email_composer_creates_personalized_email(
    sample_company_profile, sample_contact_profile
):
    """
    Test that EmailComposer composes a complete email with integrated hooks.
    
    Validates Requirement 15.4:
    PersonalizationEngine SHALL compose a complete email with the hook
    """
    composer = EmailComposer(ai_service=None)
    
    # Create sample hooks
    hooks = [
        Hook(
            type=HookType.CONTACT_RESONANCE,
            text="Your distributed-cache project caught my attention — I've worked on similar problems in production.",
            evidence="pinned_repo: distributed-cache",
            strength=0.88,
        ),
        Hook(
            type=HookType.COMPANY_SIGNAL,
            text="I've been following Stripe's open-source work — veneur is a pattern I've implemented.",
            evidence="github_repo: veneur",
            strength=0.78,
        ),
    ]
    
    class JDStub:
        required_skills = ["Python", "Go"]
        tech_stack = ["Python", "PostgreSQL"]
        pain_points = ["high-scale transactions"]
        culture_keywords = []
        role_focus = "Backend Engineer"
    
    jd = JDStub()
    
    # Compose email
    email = await composer.compose(
        hooks=hooks,
        company=sample_company_profile,
        contact=sample_contact_profile,
        jd=jd,
        resume=None,
    )
    
    # Verify email structure
    assert isinstance(email, PersonalizedEmail)
    assert email.subject != ""
    assert email.body != ""
    assert len(email.subject.split()) <= 10  # Subject should be concise
    assert email.word_count > 0
    
    # Verify hooks are integrated into body
    assert hooks[0].text in email.body or "distributed-cache" in email.body.lower()
    
    # Verify personalization score
    assert email.personalization_score > 0
    assert email.personalization_score <= 100
    
    # Verify hooks are tracked
    assert len(email.hooks_used) > 0
    
    # Verify subject variants for A/B testing
    assert len(email.subject_variants) > 0


@pytest.mark.asyncio
async def test_email_composer_respects_word_limit():
    """
    Test that EmailComposer keeps emails under target word count.
    """
    composer = EmailComposer(ai_service=None)
    
    minimal_company = CompanyProfile(domain="test.com", name="TestCo")
    minimal_contact = ContactProfile(name="John Doe")
    
    hooks = [
        Hook(
            type=HookType.GENERIC,
            text="I've been following TestCo's work.",
            evidence="generic",
            strength=0.1,
        ),
    ]
    
    class JDStub:
        required_skills = []
        tech_stack = []
        pain_points = []
        culture_keywords = []
        role_focus = "Engineer"
    
    jd = JDStub()
    
    # Compose email
    email = await composer.compose(
        hooks=hooks,
        company=minimal_company,
        contact=minimal_contact,
        jd=jd,
        resume=None,
    )
    
    # Verify word count is reasonable (< 200 words for cold email)
    assert email.word_count < 200
    assert email.word_count > 30  # But not too short


@pytest.mark.asyncio
async def test_email_composer_creates_subject_variants():
    """
    Test that EmailComposer creates multiple subject variants for A/B testing.
    """
    composer = EmailComposer(ai_service=None)
    
    company = CompanyProfile(
        domain="stripe.com",
        name="Stripe",
        recent_repos=["stripe-python: Python SDK"],
    )
    contact = ContactProfile(name="Jane Smith")
    
    hooks = [
        Hook(
            type=HookType.COMPANY_SIGNAL,
            text="I noticed Stripe's Python SDK work.",
            evidence="github_repo: stripe-python",
            strength=0.75,
        ),
    ]
    
    class JDStub:
        required_skills = ["Python"]
        tech_stack = []
        pain_points = []
        culture_keywords = []
        role_focus = "Backend Engineer"
    
    jd = JDStub()
    
    # Compose email
    email = await composer.compose(
        hooks=hooks,
        company=company,
        contact=contact,
        jd=jd,
        resume=None,
    )
    
    # Verify multiple subject variants exist
    assert len(email.subject_variants) >= 2
    
    # Verify all variants are strings
    for variant in email.subject_variants:
        assert isinstance(variant, str)
        assert len(variant) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Test 5: Full Personalization Pipeline (Requirements 15.1-15.5)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_personalization_engine_full_pipeline(sample_jd_text):
    """
    Test the full PersonalizationEngine pipeline end-to-end.
    
    Validates Requirements 15.1, 15.2, 15.3, 15.4, 15.5:
    - Company research (15.1)
    - Contact research (15.2)
    - Hook generation (15.3)
    - Email composition (15.4)
    - Resume integration (15.5 - structure validated)
    """
    engine = PersonalizationEngine(ai_service=None)
    
    # Mock research components
    with patch.object(engine._company_researcher, 'research') as mock_company, \
         patch.object(engine._contact_researcher, 'research') as mock_contact, \
         patch.object(engine, '_analyze_jd') as mock_jd:
        
        # Setup mock company research
        mock_company.return_value = CompanyProfile(
            domain="stripe.com",
            name="Stripe",
            tech_stack=["Python", "Go"],
            recent_repos=["stripe-python: SDK"],
            hn_mentions=["Stripe's API design"],
            research_sources=["https://stripe.com"],
        )
        
        # Setup mock contact research
        mock_contact.return_value = ContactProfile(
            name="Jane Smith",
            github_username="janesmith",
            bio="Backend engineer",
            languages=["Python", "Go"],
            recent_repos=["payment-system: Distributed payments"],
            technical_keywords=["distributed", "payments"],
            research_sources=["https://github.com/janesmith"],
        )
        
        # Setup mock JD analysis
        class JDStub:
            jd_text = sample_jd_text
            required_skills = ["Python", "Go", "PostgreSQL"]
            tech_stack = ["Python", "Go"]
            pain_points = ["high-scale transactions"]
            culture_keywords = []
            role_focus = "Backend Engineer"
            seniority_level = "senior"
            tone = "professional"
        
        mock_jd.return_value = JDStub()
        
        # Execute full pipeline
        outreach = await engine.personalize(
            contact_name="Jane Smith",
            contact_email="jane@stripe.com",
            linkedin_url="",
            github_hint="",
            company_name="Stripe",
            domain="stripe.com",
            jd_text=sample_jd_text,
            job_title="Senior Backend Engineer",
            job_id=12345,
        )
        
        # Verify PersonalizedOutreach structure
        assert isinstance(outreach, PersonalizedOutreach)
        assert outreach.contact_name == "Jane Smith"
        assert outreach.contact_email == "jane@stripe.com"
        assert outreach.company == "Stripe"
        
        # Verify email was composed
        assert isinstance(outreach.email, PersonalizedEmail)
        assert outreach.email.subject != ""
        assert outreach.email.body != ""
        assert outreach.email.word_count > 0
        
        # Verify cover letter was generated
        assert outreach.cover_letter != ""
        
        # Verify personalization score
        assert outreach.personalization_score > 0
        assert outreach.personalization_score <= 100
        
        # Verify company profile is attached
        assert outreach.company_profile is not None
        assert outreach.company_profile.domain == "stripe.com"
        
        # Verify contact profile is attached
        assert outreach.contact_profile is not None
        assert outreach.contact_profile.name == "Jane Smith"
        
        # Verify research time tracked
        assert outreach.research_time_ms >= 0


@pytest.mark.asyncio
async def test_personalization_engine_handles_errors_gracefully():
    """
    Test that PersonalizationEngine handles research failures gracefully.
    """
    engine = PersonalizationEngine(ai_service=None)
    
    # Mock research failures
    with patch.object(engine._company_researcher, 'research') as mock_company, \
         patch.object(engine._contact_researcher, 'research') as mock_contact, \
         patch.object(engine, '_analyze_jd') as mock_jd:
        
        # Simulate company research failure
        mock_company.side_effect = Exception("GitHub API rate limit")
        
        # Simulate contact research failure
        mock_contact.side_effect = Exception("Network timeout")
        
        # Setup mock JD analysis
        class JDStub:
            jd_text = "Test job"
            required_skills = []
            tech_stack = []
            pain_points = []
            culture_keywords = []
            role_focus = "Engineer"
        
        mock_jd.return_value = JDStub()
        
        # Execute pipeline (should not raise exception)
        outreach = await engine.personalize(
            contact_name="John Doe",
            contact_email="john@example.com",
            company_name="Example Corp",
            domain="example.com",
            jd_text="Test job description",
            job_title="Engineer",
        )
        
        # Verify outreach was still generated (with fallbacks)
        assert isinstance(outreach, PersonalizedOutreach)
        assert outreach.email.subject != ""
        assert outreach.email.body != ""
        
        # Company and contact profiles should be minimal but valid
        assert outreach.company_profile is not None
        assert outreach.contact_profile is not None


@pytest.mark.asyncio
async def test_personalization_engine_batch_processing():
    """
    Test that PersonalizationEngine can batch process multiple contacts.
    """
    engine = PersonalizationEngine(ai_service=None)
    
    # Mock research components
    with patch.object(engine._company_researcher, 'research') as mock_company, \
         patch.object(engine._contact_researcher, 'research') as mock_contact, \
         patch.object(engine, '_analyze_jd') as mock_jd:
        
        mock_company.return_value = CompanyProfile(
            domain="test.com", name="TestCo"
        )
        mock_contact.return_value = ContactProfile(name="Test User")
        
        class JDStub:
            required_skills = []
            tech_stack = []
            pain_points = []
            culture_keywords = []
            role_focus = "Engineer"
        
        mock_jd.return_value = JDStub()
        
        # Batch process 3 contacts
        contacts = [
            {"name": "Alice", "email": "alice@test.com"},
            {"name": "Bob", "email": "bob@test.com"},
            {"name": "Carol", "email": "carol@test.com"},
        ]
        
        results = await engine.batch_personalize(
            contacts=contacts,
            jd_text="Test job",
            job_title="Engineer",
            concurrency=2,
        )
        
        # Verify all contacts were processed
        assert len(results) == 3
        
        # Verify all results are PersonalizedOutreach
        for result in results:
            assert isinstance(result, PersonalizedOutreach)
            assert result.email.subject != ""


# ══════════════════════════════════════════════════════════════════════════════
# Test 6: Cover Letter Generation (Requirement 15.5 structure)
# ══════════════════════════════════════════════════════════════════════════════

def test_email_composer_creates_cover_letter(
    sample_company_profile, sample_contact_profile
):
    """
    Test that EmailComposer creates a properly formatted cover letter.
    
    Validates part of Requirement 15.5:
    PersonalizationEngine SHALL include the tailored resume in the outreach email
    (This test verifies the cover letter structure that accompanies the resume)
    """
    composer = EmailComposer(ai_service=None)
    
    hooks = [
        Hook(
            type=HookType.CONTACT_RESONANCE,
            text="Your work on distributed systems caught my attention.",
            evidence="repo: distributed-cache",
            strength=0.88,
        ),
    ]
    
    class JDStub:
        required_skills = ["Python", "Go", "PostgreSQL"]
        tech_stack = ["Python"]
        pain_points = ["high-scale transactions"]
        culture_keywords = []
        role_focus = "Backend Engineer"
    
    jd = JDStub()
    
    # Generate cover letter
    cover_letter = composer.compose_cover_letter(
        hooks=hooks,
        company=sample_company_profile,
        contact=sample_contact_profile,
        jd=jd,
        resume=None,
    )
    
    # Verify cover letter structure
    assert isinstance(cover_letter, str)
    assert len(cover_letter) > 100  # Should be substantive
    
    # Verify key components are present
    assert "Stripe" in cover_letter  # Company name
    assert "Backend Engineer" in cover_letter  # Role title
    assert "Best regards" in cover_letter or "Best" in cover_letter  # Closing
    
    # Verify word count is appropriate (target is concise but substantive)
    word_count = len(cover_letter.split())
    assert word_count >= 80  # Minimum substantive length
    assert word_count <= 500  # Maximum to avoid being too long


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
