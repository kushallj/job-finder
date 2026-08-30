"""
src/agents — Fifteen target-company agent strategies for the NEXUS job-acquisition system.

See docs/AGENT_STRATEGIES.md for the full rationale behind each agent, and
config/target_companies.yml for the researched company list they operate on.

    1. SignalScoutAgent          — agent_01_signal_scout.py
    2. ATSHunterAgent            — agent_02_ats_hunter.py
    3. FitScorerAgent            — agent_03_fit_scorer.py
    4. ResumeTailorAgent         — agent_04_resume_tailor.py
    5. ContactMapperAgent        — agent_05_contact_mapper.py
    6. OutreachComposerAgent     — agent_06_outreach_composer.py
    7. PriorityScheduleAgent     — agent_07_priority_scheduler.py
    8. InterviewPrepAgent        — agent_08_interview_prepper.py
    9. FeedbackStrategistAgent   — agent_09_feedback_strategist.py
   10. ChallengeSolverAgent      — agent_10_challenge_solver.py   ("Networker" — fixes a real problem)
   11. QueryHunterAgent          — agent_11_query_hunter.py       ("Hunter" — X-ray/boolean sourcing + lead CRM)
   12. InfluencerAgent           — agent_12_influencer.py         ("Influencer" — content drafts, never auto-posts)
   13. PitcherAgent              — agent_13_pitcher.py            ("Pitcher" — WIN one-pager)
   14. InterviewerAgent          — agent_14_interviewer.py        ("Interviewer" — mock Q&A + STAR feedback)
   15. NegotiatorAgent           — agent_15_negotiator.py         ("Negotiator" — comp benchmark + counter script)

Run the full pipeline: `python -m src.agents.orchestrator`
"""

from .base import AgentContext, AgentResult, BaseAgent
from .agent_01_signal_scout import SignalScoutAgent, Signal
from .agent_02_ats_hunter import ATSHunterAgent
from .agent_03_fit_scorer import FitScorerAgent
from .agent_04_resume_tailor import ResumeTailorAgent
from .agent_05_contact_mapper import ContactMapperAgent
from .agent_06_outreach_composer import OutreachComposerAgent
from .agent_07_priority_scheduler import PriorityScheduleAgent
from .agent_08_interview_prepper import InterviewPrepAgent
from .agent_09_feedback_strategist import FeedbackStrategistAgent
from .agent_10_challenge_solver import ChallengeSolverAgent
from .agent_11_query_hunter import QueryHunterAgent
from .agent_12_influencer import InfluencerAgent
from .agent_13_pitcher import PitcherAgent
from .agent_14_interviewer import InterviewerAgent
from .agent_15_negotiator import NegotiatorAgent

__all__ = [
    "AgentContext", "AgentResult", "BaseAgent",
    "SignalScoutAgent", "Signal",
    "ATSHunterAgent",
    "FitScorerAgent",
    "ResumeTailorAgent",
    "ContactMapperAgent",
    "OutreachComposerAgent",
    "PriorityScheduleAgent",
    "InterviewPrepAgent",
    "FeedbackStrategistAgent",
    "ChallengeSolverAgent",
    "QueryHunterAgent",
    "InfluencerAgent",
    "PitcherAgent",
    "InterviewerAgent",
    "NegotiatorAgent",
]
