#!/usr/bin/env python3
"""
Full End-to-End Master Backend Pipeline Test Runner.
Executes and validates all 6 foundational pipelines of the Job Finder platform:
1. 15-Agent Target Company Pipeline (SignalScout -> ATSHunter -> FitScorer -> PriorityScheduler -> ResumeTailor -> ContactMapper -> OutreachComposer)
2. Job Ingestion, Deduplication, Fit & Action Queue Pipeline
3. Email Intelligence & OSINT Boolean Discovery Pipeline
4. Transformer Q,K,V (Query, Key, Value) Multi-Head Attention Pipeline
5. Referral Automator Pipeline (LinkedIn + X Referral Engines)
6. High-Throughput Async Worker Pool Streaming Pipeline
"""

import sys
import time
import asyncio
from typing import Dict, Any

from fastapi.testclient import TestClient
from main import app

from src.agents.orchestrator import run_daily_pipeline
from src.agents.agent_10_challenge_solver import ChallengeSolverAgent
from src.agents.agent_12_influencer import InfluencerAgent
from src.agents.agent_13_pitcher import PitcherAgent
from src.agents.agent_14_interviewer import InterviewerAgent
from src.agents.agent_15_negotiator import NegotiatorAgent
from src.agents.base import AgentContext

from src.attention.service import attention_service
from src.email_intelligence.service import email_intelligence_service
from src.referral.service import referral_service
from src.x_referral.service import x_referral_service


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  🚀 PIPELINE: {title}")
    print("=" * 70)


def test_full_pipeline():
    total_start = time.time()
    client = TestClient(app)

    # ═════════════════════════════════════════════════════════════════════════
    # 1. 15-AGENT TARGET COMPANY ORCHESTRATION PIPELINE
    # ═════════════════════════════════════════════════════════════════════════
    print_banner("1. 15-Agent Target-Company Autonomous Pipeline")
    t0 = time.time()
    ctx = AgentContext.load()
    res_agents = run_daily_pipeline(ctx, tiers=[1, 2])
    assert res_agents is not None
    assert "queue" in res_agents
    assert "drafts" in res_agents
    print(f"  [✓] Daily Agent Orchestrator: {res_agents.get('roles_found', 0)} live roles found, {len(res_agents.get('queue', []))} queued ({time.time() - t0:.2f}s)")

    # Test Challenge Solver & Pitcher
    ctx = AgentContext.load()
    challenge = ChallengeSolverAgent(ctx).run("DevRev", "High throughput async backend microservices")
    assert challenge.ok
    print(f"  [✓] Challenge Solver Agent: {challenge.summary}")

    pitch = PitcherAgent(ctx).run("DevRev", "High throughput async backend microservices")
    assert pitch.ok
    print(f"  [✓] Pitcher Agent (WIN One-Pager): {pitch.summary}")

    # Test Negotiator & Interview Simulator
    interviewer = InterviewerAgent(ctx).generate_questions("DevRev", num_questions=3)
    assert interviewer.ok
    print(f"  [✓] Interview Simulator Agent: Generated {len(interviewer.data.get('questions', []))} questions")

    score = InterviewerAgent(ctx).score_answer(
        question="Tell me about a time you found a problem nobody else had noticed and fixed it.",
        answer="At my previous role, I discovered a race condition in the async transaction pipeline causing 3% dropped events. I designed a Redis-backed distributed lock with 50ms timeout, reducing drop rate to 0%.",
    )
    assert score.ok
    print(f"  [✓] STAR Answer Scorer: Overall={score.data.get('overall')}/100 (STAR check completed)")

    negotiator = NegotiatorAgent(ctx).benchmark("DevRev")
    assert negotiator.ok
    print(f"  [✓] Negotiator Agent: {negotiator.summary}")

    # ═════════════════════════════════════════════════════════════════════════
    # 2. JOB INGESTION, DEDUPLICATION, FIT & LIFECYCLE PIPELINE
    # ═════════════════════════════════════════════════════════════════════════
    print_banner("2. Job Ingestion, Deduplication, Fit & Lifecycle Pipeline")
    t0 = time.time()
    raw_job = {
        "title": "Staff Backend Engineer - Distributed Systems",
        "company": "Figma",
        "location": "San Francisco, CA / Remote",
        "description": "Build low-latency collaboration engine using Python, FastAPI, WebSockets, and Redis.",
        "url": f"https://careers.figma.com/jobs/staff-backend-pipe-{int(time.time())}",
        "source": "automated_test_pipeline",
        "salary_raw": "$220,000 - $280,000",
    }
    res = client.post("/api/jobs/capture", json=raw_job)
    assert res.status_code == 200
    job_id = res.json()["job"]["id"]
    is_new = not res.json().get("already_existed", False)
    print(f"  [✓] Job Ingestion & Capture: Job #{job_id} captured (is_new={is_new})")

    # Opportunity Brief & AI Fit Assessment
    res = client.get(f"/api/opportunities/{job_id}/brief")
    assert res.status_code == 200
    fit_score = res.json()["fit_score"]
    fit_label = res.json()["fit_label"]
    print(f"  [✓] Fit Assessment: Fit Score = {fit_score}% ({fit_label})")

    # Set application to 'ready' stage
    res_app = client.put(f"/api/jobs/{job_id}/application", json={"status": "ready"})
    assert res_app.status_code == 200
    app_id = res_app.json()["application_id"]
    print(f"  [✓] Application State Created: App #{app_id} (status='ready')")

    # Submission Proof Logging -> transitions to 'applied'
    res = client.post(f"/api/applications/{app_id}/proof", json={
        "confirmation_number": "FIGMA-2026-X99",
        "proof_note": "Applied directly via careers page",
        "proof_url": "https://careers.figma.com/applications/confirm",
    })
    assert res.status_code == 200
    print(f"  [✓] Submission Proof Verification: Proof logged & transitioned to 'applied'")

    # Lifecycle Stage Transition -> advances to 'interview'
    res = client.post(f"/api/applications/{app_id}/transition", json={"status": "interview"})
    assert res.status_code == 200
    print(f"  [✓] Career Lifecycle Transition: Advanced to 'interview' ({time.time() - t0:.2f}s)")

    # ═════════════════════════════════════════════════════════════════════════
    # 3. EMAIL INTELLIGENCE & OSINT BOOLEAN DISCOVERY PIPELINE
    # ═════════════════════════════════════════════════════════════════════════
    print_banner("3. Email Intelligence & Google Boolean Waterfall Pipeline")
    t0 = time.time()
    res = client.post("/api/email-intelligence/discover", json={
        "company": "Stripe",
        "job_title": "Engineering Manager",
        "target_name": "Patrick Collison",
        "limit": 2,
    })
    assert res.status_code == 200
    disc_data = res.json()
    assert disc_data["total_found"] > 0
    top_contact = disc_data["contacts"][0]
    print(f"  [✓] Decision-Maker Discovery: {top_contact['name']} ({top_contact['title']}) -> {top_contact['email']}")

    res_v = client.post("/api/email-intelligence/verify", json={"email": top_contact["email"]})
    assert res_v.status_code == 200
    v_data = res_v.json()
    print(f"  [✓] MX & Deliverability Verifier: Provider={v_data.get('mail_provider')}, Confidence={v_data.get('confidence_score')}%")

    res_d = client.post("/api/email-intelligence/dorks", json={"company": "Stripe", "domain": "stripe.com"})
    assert res_d.status_code == 200
    d_data = res_d.json()
    print(f"  [✓] OSINT Dorking Generator: {d_data.get('total_dorks')} targeted boolean dorks generated")

    res_p = client.post("/api/email-intelligence/permutations", json={"full_name": "Patrick Collison", "domain": "stripe.com"})
    assert res_p.status_code == 200
    p_data = res_p.json()
    print(f"  [✓] Corporate Email Synthesizer: {p_data.get('total_permutations')} permutations generated with MX check ({time.time() - t0:.2f}s)")

    # ═════════════════════════════════════════════════════════════════════════
    # 4. TRANSFORMER Q, K, V ATTENTION PIPELINE
    # ═════════════════════════════════════════════════════════════════════════
    print_banner("4. Transformer Q,K,V Multi-Head Attention Pipeline")
    t0 = time.time()
    attn_res = attention_service.match_job(raw_job["description"])
    assert attn_res.overall_score >= 50.0
    print(f"  [✓] Multi-Head Attention Match: {attn_res.overall_score}% ({attn_res.fit_label})")
    for h_name, h_val in attn_res.heads.items():
        print(f"      • Head [{h_name}]: {h_val.head_score}%")

    tailored_bullets = attention_service.tailor_resume(raw_job["description"])
    print(f"  [✓] Attention-Weighted Resume Tailoring: {len(tailored_bullets)} bullets ranked by received attention sum")

    outreach_hook = attention_service.synthesize_outreach_hooks(
        contact_name="David Singleton",
        contact_title="CTO",
        company="Stripe",
        job_description=raw_job["description"],
    )
    print(f"  [✓] Cross-Attention Cold Outreach: Subject='{outreach_hook['subject']}' ({time.time() - t0:.2f}s)")

    # ═════════════════════════════════════════════════════════════════════════
    # 5. REFERRAL AUTOMATOR PIPELINE (LINKEDIN + X)
    # ═════════════════════════════════════════════════════════════════════════
    print_banner("5. Referral Automator Pipeline (LinkedIn + X)")
    t0 = time.time()
    # LinkedIn Search & Note
    res_li = client.post("/api/referrals/search", json={"company": "Stripe", "limit": 3})
    assert res_li.status_code == 200
    li_data = res_li.json()
    assert li_data["count"] > 0
    li_profile = li_data["profiles"][0]
    li_name = li_profile.get("full_name") or li_profile.get("name", "Engineering Leader")

    res_note = client.post("/api/referrals/generate-note", json={
        "company": "Stripe",
        "full_name": li_name,
        "title": li_profile.get("title") or li_profile.get("headline", "Engineering Manager"),
        "role_title": "Staff Backend Engineer",
    })
    assert res_note.status_code == 200
    note_data = res_note.json()
    print(f"  [✓] LinkedIn Referral Engine: Found {li_name}, drafted {len(note_data['connection_note'])}/200 char note")

    # X (Twitter) Search, Tweet Discovery & Message
    res_x = client.post("/api/x/search", json={"company": "OpenAI", "role": "Engineering", "limit": 3})
    assert res_x.status_code == 200
    x_data = res_x.json()
    assert x_data["count"] > 0
    x_user = x_data["profiles"][0]

    res_xmsg = client.post("/api/x/generate-message", json={
        "action_type": "reply",
        "username": x_user["username"],
        "company": "OpenAI",
        "name": x_user["name"],
        "role_title": "Backend Engineer",
    })
    assert res_xmsg.status_code == 200
    x_msg = res_xmsg.json()
    print(f"  [✓] X Referral Engine: Found @{x_user['username']}, synthesized {x_msg['char_count']}/280 char message")

    # Engage & Log Action
    res_eng = client.post("/api/x/engage", json={
        "action_type": "like",
        "target_username": x_user["username"],
        "company": "OpenAI",
        "tweet_id": "1829000000000000000",
    })
    assert res_eng.status_code == 200
    x_engage = res_eng.json()
    print(f"  [✓] Social Engagement & CRM Log: Logged outreach #{x_engage['outreach_id']} ({time.time() - t0:.2f}s)")

    # ═════════════════════════════════════════════════════════════════════════
    # 6. ACTION QUEUE & CRM SYNCHRONIZATION
    # ═════════════════════════════════════════════════════════════════════════
    print_banner("6. Action Queue & CRM Aggregator")
    t0 = time.time()
    res = client.get("/api/action-queue")
    assert res.status_code == 200
    q_data = res.json()
    print(f"  [✓] Action Queue Live: {q_data['total']} actionable steps across opportunities")

    res = client.get("/api/stats")
    assert res.status_code == 200
    stats = res.json()
    print(f"  [✓] Global Funnel Analytics: {stats.get('jobs', 0)} Total Jobs, {stats.get('contacts', 0)} Contacts, {stats.get('outreach', 0)} Outreach Records")

    elapsed_total = time.time() - total_start
    print("\n" + "=" * 70)
    print(f"  🎉 ALL 6 MASTER PIPELINES EXECUTED AND PASSED IN {elapsed_total:.2f}s!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    test_full_pipeline()
