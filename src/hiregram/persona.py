from __future__ import annotations

from typing import Dict, Any, List
from .models import InterviewerPersona


PERSONA_PROFILES: Dict[InterviewerPersona, Dict[str, Any]] = {
    InterviewerPersona.RECRUITER_SARA: {
        "name": "Sara Chen",
        "title": "Lead Technical Recruiter",
        "avatar_badge": "👩‍💼",
        "style": "Warm, conversational, and focused on career trajectory, motivation, and culture fit.",
        "voice_pitch": 1.0,
        "voice_rate": 1.0,
        "question_bank": [
            "Hi there! Thanks for taking the time to chat today. To start off, walk me through your recent engineering background and what specifically caught your eye about this role at {company}?",
            "Can you share a project where you had to collaborate closely with product managers or stakeholders? How did you align on tradeoffs?",
            "What type of engineering environment allows you to do your best work, and what are your expectations around compensation and career growth?",
            "Where do you see your technical focus evolving over the next 2 to 3 years?",
        ],
    },
    InterviewerPersona.ARCHITECT_ALEX: {
        "name": "Alex Mercer",
        "title": "Staff Distributed Systems Architect",
        "avatar_badge": "👨‍💻",
        "style": "Rigorous, deeply technical, and probing on system bottlenecks, concurrency, and reliability tradeoffs.",
        "voice_pitch": 0.9,
        "voice_rate": 1.05,
        "question_bank": [
            "Let's dive into system design. How would you design a high-throughput, low-latency rate limiter capable of handling 500k requests per second across distributed edge clusters at {company}?",
            "In your previous systems, how did you handle data consistency and replication lag across distributed datastores during network partitions?",
            "Tell me about the hardest production outage or concurrency race condition you personally investigated and resolved. What was the root cause and mitigation?",
            "If our event bus experiences a sudden 10x traffic spike and consumer queues back up, what architectural patterns would you apply to prevent cascading failures?",
        ],
    },
    InterviewerPersona.BAR_RAISER_MARCUS: {
        "name": "Marcus Vance",
        "title": "Principal Bar Raiser",
        "avatar_badge": "🎯",
        "style": "Direct, structured, demanding concrete STAR metrics, ownership, and deep self-reflection.",
        "voice_pitch": 0.95,
        "voice_rate": 0.95,
        "question_bank": [
            "Tell me about a time you strongly disagreed with a senior engineering decision or architecture direction. How did you challenge it, and what was the outcome?",
            "Describe a situation where a critical project was falling behind schedule or failing to meet quality standards. What specific actions did you take to turn it around?",
            "Give me an example of a mistake you made in production that impacted users or business metrics. How did you take ownership and prevent recurrence?",
            "Tell me about a time you went above and beyond your defined job responsibilities to solve a company-wide bottleneck.",
        ],
    },
    InterviewerPersona.STARTUP_CTO_ELENA: {
        "name": "Elena Rostova",
        "title": "VP of Engineering & Co-Founder",
        "avatar_badge": "🚀",
        "style": "Pragmatic, fast-paced, testing 0-to-1 building intuition, pragmatism, and shipping velocity.",
        "voice_pitch": 1.05,
        "voice_rate": 1.1,
        "question_bank": [
            "We need to ship an MVP feature in 2 weeks with minimal engineering resources. How do you decide what technical debt to accept and what architecture is non-negotiable?",
            "How do you evaluate new technologies or frameworks before adopting them into the core stack versus sticking with battle-tested tooling?",
            "Tell me about a time you had to pivot a product architecture mid-flight based on unexpected user feedback.",
            "If you joined {company} tomorrow, what is the first high-leverage initiative you would tackle in your first 30 days?",
        ],
    },
}


def get_persona_profile(persona: InterviewerPersona) -> Dict[str, Any]:
    return PERSONA_PROFILES.get(persona, PERSONA_PROFILES[InterviewerPersona.RECRUITER_SARA])
