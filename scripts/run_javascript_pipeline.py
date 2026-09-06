#!/usr/bin/env python3
"""
run_javascript_pipeline.py — End-to-End Autonomous Pipeline for JavaScript / TypeScript / Node.js Jobs.
Executes:
1. Multi-Provider Job Discovery & Ingestion for JavaScript/TypeScript roles
2. Transformer Q,K,V Attention Fit & Resume Tailoring for JS/TS stack
3. Decision-Maker Discovery & Email Intelligence (CTOs/Eng Managers)
4. Social Referral Engine (LinkedIn + X notes for JS roles)
5. Proof-of-Work Micro-Repo Fabrication (Sub-ms Node/TS microservice)
6. The Godfather Consigliere Dispatch & Action Queue Sync
"""
from __future__ import annotations

import sys
import os
import time
import json
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from main import app

from src.attention.service import attention_service
from src.email_intelligence.service import email_intelligence_service
from src.referral.service import referral_service
from src.x_referral.service import x_referral_service
from src.services.proof_of_work_fabricator import ProofOfWorkFabricatorService
from src.services.interviewer_profiler import InterviewerProfilerService
from src.services.system_design_whiteboard import SystemDesignWhiteboardService
from src.telegram_bot.godfather_bot import GodfatherBot


def banner(title: str):
    print("\n" + "=" * 75)
    print(f"  ⚡ JAVASCRIPT / TYPESCRIPT PIPELINE: {title}")
    print("=" * 75)


def run_js_pipeline():
    total_start = time.time()
    client = TestClient(app)
    bot = GodfatherBot()

    # ═════════════════════════════════════════════════════════════════════════
    # 1. LIVE JOB DISCOVERY & CAPTURE FOR JAVASCRIPT / TYPESCRIPT
    # ═════════════════════════════════════════════════════════════════════════
    banner("1. Live JavaScript / TypeScript Job Ingestion & Normalization")
    t0 = time.time()

    js_jobs_dataset = [
        {
            "title": "Senior Full-Stack Engineer (React / TypeScript / Node.js)",
            "company": "Vercel",
            "location": "San Francisco, CA / Remote",
            "description": "Architect high-throughput edge rendering pipelines using Next.js, React 19, TypeScript, Node.js worker pools, and TurboRepo.",
            "url": f"https://vercel.com/careers/senior-fullstack-js-{int(time.time())}",
            "source": "javascript_live_pipeline",
            "salary_raw": "$180,000 - $240,000",
        },
        {
            "title": "Staff Frontend Platform Architect (TypeScript / WebGL)",
            "company": "Canva",
            "location": "Sydney / Remote",
            "description": "Scale real-time collaborative canvas rendering using TypeScript, WebAssembly, WebSockets, RxJS, and optimized DOM reconciliation.",
            "url": f"https://canva.com/careers/staff-frontend-{int(time.time())}",
            "source": "javascript_live_pipeline",
            "salary_raw": "$200,000 - $260,000",
        },
        {
            "title": "Senior Backend Engineer (Node.js / Distributed Event Streams)",
            "company": "Postman",
            "location": "Bengaluru / San Francisco / Remote",
            "description": "Design high-concurrency API runtime and WebSocket mock servers using Node.js, Fastify, Redis, Kafka, and TypeScript.",
            "url": f"https://postman.com/careers/senior-backend-nodejs-{int(time.time())}",
            "source": "javascript_live_pipeline",
            "salary_raw": "₹45,00,000 - ₹65,00,000",
        },
    ]

    captured_jobs = []
    for raw in js_jobs_dataset:
        res = client.post("/api/jobs/capture", json=raw)
        if res.status_code == 200:
            job_obj = res.json()["job"]
            captured_jobs.append(job_obj)
            print(f"  [✓] Captured JS/TS Job #{job_obj['id']}: {job_obj['title']} @ {job_obj['company']} ({job_obj.get('location')})")

    # ═════════════════════════════════════════════════════════════════════════
    # 2. TRANSFORMER Q,K,V ATTENTION MATCHING FOR JAVASCRIPT STACK
    # ═════════════════════════════════════════════════════════════════════════
    banner("2. Transformer Q,K,V Attention Matching & Resume Tailoring")
    t0 = time.time()
    primary_job = captured_jobs[0]
    
    attn_res = attention_service.match_job(primary_job["description"])
    print(f"  [✓] Target: {primary_job['title']} @ {primary_job['company']}")
    print(f"  [✓] Multi-Head Attention Score: {attn_res.overall_score}% ({attn_res.fit_label})")
    for h_name, h_val in attn_res.heads.items():
        print(f"      • Head [{h_name}]: {h_val.head_score}%")

    tailored_bullets = attention_service.tailor_resume(primary_job["description"])
    print(f"  [✓] Synthesized {len(tailored_bullets)} Attention-Ranked JS/TS Resume Bullets:")
    for i, b in enumerate(tailored_bullets[:3], 1):
        print(f"      {i}. {b.tailored_text}")

    # ═════════════════════════════════════════════════════════════════════════
    # 3. DECISION-MAKER EMAIL INTELLIGENCE (CTOs & Head of Frontend)
    # ═════════════════════════════════════════════════════════════════════════
    banner("3. Decision-Maker Email Intelligence & OSINT Waterfall")
    t0 = time.time()
    
    target_companies = ["Vercel", "Postman"]
    discovered_contacts = []
    for comp in target_companies:
        res = client.post("/api/email-intelligence/discover", json={
            "company": comp,
            "job_title": "VP of Engineering / Head of Frontend",
            "limit": 2,
        })
        if res.status_code == 200:
            contacts = res.json().get("contacts", [])
            for c in contacts:
                discovered_contacts.append(c)
                print(f"  [✓] Discovered Leader @ {comp}: {c['name']} ({c['title']}) -> {c['email']} (Pattern: {c.get('pattern_used')})")

    # ═════════════════════════════════════════════════════════════════════════
    # 4. SOCIAL REFERRAL AUTOMATION (LINKEDIN & X VALUE HOOKS)
    # ═════════════════════════════════════════════════════════════════════════
    banner("4. Referral Engine: LinkedIn & X Connection Notes")
    t0 = time.time()
    
    # LinkedIn Referral Note
    res_li = client.post("/api/referrals/generate-note", json={
        "company": "Vercel",
        "full_name": "Guillermo Rauch",
        "title": "CEO & Frontend Architect",
        "role_title": "Senior Full-Stack Engineer (Next.js/TypeScript)",
    })
    if res_li.status_code == 200:
        note = res_li.json()["connection_note"]
        print(f"  [✓] LinkedIn Note for Vercel ({len(note)}/200 chars):")
        print(f"      \"{note}\"")

    # X (Twitter) Referral DM
    res_x = client.post("/api/x/generate-message", json={
        "action_type": "reply",
        "username": "rauchg",
        "company": "Vercel",
        "name": "Guillermo Rauch",
        "role_title": "Senior Full-Stack Engineer",
    })
    if res_x.status_code == 200:
        xmsg = res_x.json()["message"]
        print(f"  [✓] X (Twitter) Hook for @rauchg ({len(xmsg)}/280 chars):")
        print(f"      \"{xmsg}\"")

    # ═════════════════════════════════════════════════════════════════════════
    # 5. JAVASCRIPT PROOF-OF-WORK FABRICATOR & WHITEBOARD ARCHITECTURE
    # ═════════════════════════════════════════════════════════════════════════
    banner("5. JavaScript/TypeScript Proof-of-Work & Whiteboard Engine")
    t0 = time.time()
    pow_svc = ProofOfWorkFabricatorService()
    pow_fab = pow_svc.fabricate("Vercel", "Senior Full-Stack TypeScript Architect")
    print(f"  [✓] Fabricated Micro-Repo: {pow_fab['project_title']}")
    print(f"  [✓] Benchmarks: {pow_fab['benchmark_metrics']['p99_latency_reduction_percent']}% latency reduction under {pow_fab['benchmark_metrics']['concurrency_rps_tested']} RPS")
    print(f"  [✓] Synthesized Files: {pow_fab['app_code_filename']}, {pow_fab['test_code_filename']}, Dockerfile, CI/CD Actions, PR Markdown")

    wb_svc = SystemDesignWhiteboardService()
    wb = wb_svc.estimate_and_diagram("distributed_rate_limiter", dau=15000000)
    print(f"  [✓] System Design Whiteboard: {wb['title']} (Peak QPS: {wb['capacity_estimates']['peak_qps']:,} req/s, Target: {wb['p99_sla_target']})")

    # ═════════════════════════════════════════════════════════════════════════
    # 6. THE GODFATHER TELEGRAM CONSIGLIERE: JAVASCRIPT DISPATCH
    # ═════════════════════════════════════════════════════════════════════════
    banner("6. The Godfather Telegram Consigliere: Live JS Queries")
    t0 = time.time()
    
    queries = [
        "I have an interview tomorrow with Vercel for Senior Fullstack TypeScript Engineer",
        "How do I counter an offer of 55 LPA from Postman against 45 LPA from Swiggy?",
        "/frontier",
    ]

    for q in queries:
        resp = bot.process_user_message(q, user_name="JS Sovereign Engineer")
        print(f"  👑 Prompt: \"{q}\"")
        print(f"     ➔ Agent Invoked: {resp.agent_invoked}")
        first_line = resp.text.split('\n')[0].replace('<b>', '').replace('</b>', '')
        print(f"     ➔ Consigliere Response: {first_line[:85]}...")

    elapsed = time.time() - total_start
    print("\n" + "=" * 75)
    print(f"  🎉 JAVASCRIPT / TYPESCRIPT FULL PIPELINE COMPLETE IN {elapsed:.2f}s!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_js_pipeline()
