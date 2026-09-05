"""
Unit tests for Week 1-2 Sprint implementations:
1. AgentContext DB candidate profile & target companies dynamic loader.
2. FeedbackStrategistAgent with Funnel Event learning.
3. LaborMarketReportService report generation.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, CandidateProfile, TargetCompanyRecord, OutreachFunnelEvent
from src.agents.base import AgentContext, _profile_from_db, _companies_from_db
from src.agents.agent_09_feedback_strategist import FeedbackStrategistAgent
from src.services.labor_market_report import LaborMarketReportService

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

def test_labor_market_report_generation(db_session):
    # Add a target company
    comp = TargetCompanyRecord(
        user_identifier="default_user",
        name="Walmart Global Tech",
        domain="walmart.com",
        tier="tier1",
        industry="Retail Tech / Supply Chain",
        signal_score=94.0,
        funding_stage="Enterprise",
        signal_notes="High growth GCC in Bengaluru",
        is_active=True,
    )
    db_session.add(comp)
    db_session.commit()

    service = LaborMarketReportService(db=db_session)
    report = service.generate_report(target_sector="GCC & FinTech")

    assert report["status"] == "success"
    assert "GCC" in report["target_sector"]
    assert len(report["macro_trends"]["macro_metrics"]) >= 4
    assert len(report["ranked_target_companies"]) >= 1
    assert any(c["name"] == "Walmart Global Tech" for c in report["ranked_target_companies"])
    assert len(report["abm_playbook_rules"]) >= 4

def test_agent_context_dynamic_loading():
    ctx = AgentContext.load()
    assert ctx is not None
    assert ctx.profile is not None
    assert "candidate" in ctx.profile
    assert len(ctx.companies) >= 1

def test_feedback_strategist_run():
    ctx = AgentContext.load()
    agent = FeedbackStrategistAgent(context=ctx)
    result = agent.run()
    assert result.ok is True
    assert result.agent == "feedback_strategist"
    assert "tier_reply_rates" in result.data
