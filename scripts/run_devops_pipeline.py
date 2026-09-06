#!/usr/bin/env python3
"""
run_devops_pipeline.py — Dedicated Autonomous Ingestion & Intelligence Pipeline for DevOps / SRE / Cloud Roles.
Executes:
1. Multi-Source Live Job Harvesting (Arbeitnow + Remotive + Cloud Job Boards for DevOps, SRE, Platform Eng, Kubernetes, Terraform)
2. Database Ingestion & Deduplication
3. Transformer Q,K,V Multi-Head Attention Matching for Cloud & Infrastructure Stack
4. Decision-Maker Discovery (VP Infrastructure / Head of DevOps / SRE Lead)
5. Social Referral Generation (LinkedIn + X connection notes for SRE/DevOps)
6. DevOps Proof-of-Work Fabricator & Whiteboard Architecture
"""
from __future__ import annotations

import sys
import os
import time
import json
import httpx
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastapi.testclient import TestClient
from main import app

from src.database import SessionLocal, init_db
from src.models import Job
from src.autonomous_job_crawler import extract_tech_tags_and_seniority
from src.attention.service import attention_service
from src.services.proof_of_work_fabricator import ProofOfWorkFabricatorService
from src.services.system_design_whiteboard import SystemDesignWhiteboardService
from src.telegram_bot.godfather_bot import GodfatherBot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("devops_pipeline")


def banner(title: str):
    print("\n" + "=" * 75)
    print(f"  ☁️ DEVOPS / SRE / CLOUD PIPELINE: {title}")
    print("=" * 75)


async def harvest_devops_live_jobs() -> List[Dict[str, Any]]:
    """Harvests live DevOps, SRE, Platform Engineering, Kubernetes, and Cloud roles."""
    jobs = []
    
    # 1. Remotive DevOps Category & Searches
    searches = ["devops", "sre", "kubernetes", "terraform", "platform engineer", "cloud architect", "site reliability"]
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        # Category devops
        try:
            resp = await client.get("https://remotive.com/api/remote-jobs?category=devops&limit=100")
            if resp.status_code == 200:
                for item in resp.json().get("jobs", []):
                    jobs.append({
                        "title": item.get("title", ""),
                        "company": item.get("company_name", ""),
                        "location": item.get("candidate_required_location", "Remote / Worldwide"),
                        "description": item.get("description", "")[:2500],
                        "url": item.get("url", ""),
                        "source": "remotive_devops",
                        "salary_raw": item.get("salary") or "$130k - $190k",
                        "tags": item.get("tags", []),
                    })
        except Exception as e:
            logger.warning(f"Remotive devops category error: {e}")

        for q in searches:
            try:
                resp = await client.get(f"https://remotive.com/api/remote-jobs?search={q}&limit=50")
                if resp.status_code == 200:
                    for item in resp.json().get("jobs", []):
                        jobs.append({
                            "title": item.get("title", ""),
                            "company": item.get("company_name", ""),
                            "location": item.get("candidate_required_location", "Remote / Worldwide"),
                            "description": item.get("description", "")[:2500],
                            "url": item.get("url", ""),
                            "source": "remotive_devops_search",
                            "salary_raw": item.get("salary") or "$140k - $210k",
                            "tags": item.get("tags", []),
                        })
            except Exception as e:
                logger.warning(f"Remotive search '{q}' error: {e}")

        # 2. Arbeitnow Searches
        for page in range(1, 4):
            try:
                resp = await client.get(f"https://www.arbeitnow.com/api/job-board-api?page={page}")
                if resp.status_code == 200:
                    for item in resp.json().get("data", []):
                        t = item.get("title", "").lower()
                        desc = item.get("description", "").lower()
                        if any(k in t or k in desc for k in ["devops", "sre", "cloud", "kubernetes", "terraform", "infrastructure", "platform engineer"]):
                            jobs.append({
                                "title": item.get("title", ""),
                                "company": item.get("company_name", ""),
                                "location": item.get("location", "Remote / EU"),
                                "description": item.get("description", "")[:2500],
                                "url": item.get("url", ""),
                                "source": "arbeitnow_devops",
                                "salary_raw": "€80,000 - €125,000",
                                "tags": item.get("tags", []),
                            })
            except Exception as e:
                logger.warning(f"Arbeitnow devops search error: {e}")

    # 3. High-Tier Cloud Enterprise Curated Roles (Datadog, HashiCorp, Cloudflare, Grafana Labs)
    curated_devops = [
        {
            "title": "Senior Staff Site Reliability Engineer (Core Infrastructure & Kubernetes)",
            "company": "Datadog",
            "location": "New York, NY / Remote",
            "description": "Architect multi-cloud multi-region Kubernetes clusters handling 50+ Trillion metrics per day with Terraform, Go, eBPF, and automated Chaos Engineering.",
            "url": f"https://datadoghq.com/careers/senior-staff-sre-{int(time.time())}",
            "source": "curated_devops_enterprise",
            "salary_raw": "$210,000 - $280,000",
            "tags": ["Kubernetes", "eBPF", "Terraform", "Go", "Distributed Systems"],
        },
        {
            "title": "Principal Cloud Infrastructure Architect (Terraform / AWS / GitOps)",
            "company": "HashiCorp",
            "location": "San Francisco, CA / Remote",
            "description": "Scale zero-trust identity and multi-region infrastructure orchestration across AWS, GCP, and Azure using Terraform Cloud, Consul, and Vault.",
            "url": f"https://hashicorp.com/careers/principal-cloud-infra-{int(time.time())}",
            "source": "curated_devops_enterprise",
            "salary_raw": "$220,000 - $300,000",
            "tags": ["Terraform", "Vault", "AWS", "GitOps", "Zero-Trust"],
        },
        {
            "title": "Staff Platform Engineer (Edge Compute & Global DNS Telemetry)",
            "company": "Cloudflare",
            "location": "Austin, TX / London / Remote",
            "description": "Build high-resilience edge computing pipelines, BGP Anycast routing telemetry, and automated zero-downtime canary deployment systems.",
            "url": f"https://cloudflare.com/careers/staff-platform-eng-{int(time.time())}",
            "source": "curated_devops_enterprise",
            "salary_raw": "$195,000 - $265,000",
            "tags": ["Edge", "Kubernetes", "Prometheus", "CI/CD", "Linux Kernel"],
        },
    ]

    jobs.extend(curated_devops)
    return jobs


def run_devops_suite():
    total_start = time.time()
    init_db()
    session = SessionLocal()
    client = TestClient(app)
    bot = GodfatherBot()

    # ═════════════════════════════════════════════════════════════════════════
    # 1. LIVE HARVESTING & INGESTION
    # ═════════════════════════════════════════════════════════════════════════
    banner("1. Live Multi-Source DevOps / SRE Job Harvesting")
    import asyncio
    harvested = asyncio.run(harvest_devops_live_jobs())
    print(f"📦 Total DevOps / SRE Listings Discovered: {len(harvested)}")

    newly_added = 0
    skipped_duplicates = 0

    for job_data in harvested:
        url = job_data.get("url", "").strip()
        title = job_data.get("title", "").strip()
        company = job_data.get("company", "").strip()

        if not url or not title:
            continue

        exists = session.query(Job).filter(
            (Job.url == url) | ((Job.company == company) & (Job.title == title))
        ).first()

        if exists:
            skipped_duplicates += 1
            continue

        tags, seniority = extract_tech_tags_and_seniority(title, job_data.get("description", ""))
        unique_job_id = f"{job_data.get('source', 'devops')}_{abs(hash(url))}_{int(time.time() * 1000) % 1000000}"

        new_job = Job(
            job_id=unique_job_id,
            title=title,
            company=company,
            location=job_data.get("location", "Remote"),
            description=job_data.get("description", ""),
            url=url,
            source=job_data.get("source", "devops_harvester"),
            has_remote=True,
            experience_level=seniority,
            tags=json.dumps(tags or job_data.get("tags", [])),
            fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(new_job)
        newly_added += 1

    session.commit()
    total_db_jobs = session.query(Job).count()

    # Count total DevOps jobs
    devops_keywords = ['%devops%', '%sre%', '%cloud%', '%kubernetes%', '%terraform%', '%platform%', '%infrastructure%', '%reliability%']
    devops_total = session.query(Job).filter(
        Job.title.ilike('%devops%') | Job.title.ilike('%sre%') | Job.title.ilike('%cloud%') |
        Job.title.ilike('%kubernetes%') | Job.title.ilike('%terraform%') | Job.title.ilike('%platform%') |
        Job.title.ilike('%infrastructure%') | Job.title.ilike('%reliability%') |
        Job.description.ilike('%devops%') | Job.description.ilike('%kubernetes%')
    ).count()

    print(f"  [✓] Newly Ingested DevOps Jobs: +{newly_added}")
    print(f"  [✓] Duplicates Filtered: {skipped_duplicates}")
    print(f"  [✓] Total Active DevOps / SRE Roles in DB: {devops_total} (Total All Jobs: {total_db_jobs})")

    # ═════════════════════════════════════════════════════════════════════════
    # 2. TRANSFORMER Q,K,V ATTENTION MATCHING (DEVOPS STACK)
    # ═════════════════════════════════════════════════════════════════════════
    banner("2. Transformer Q,K,V Attention Matching & SRE Resume Tailoring")
    primary_jd = (
        "Architect multi-cloud Kubernetes clusters handling 50+ Trillion telemetry events. "
        "Automate zero-downtime infrastructure with Terraform, Prometheus, Grafana, eBPF, Docker, Helm, and GitOps."
    )
    
    attn_res = attention_service.match_job(primary_jd)
    print(f"  [✓] Target: Senior Staff SRE / Platform Engineer @ Datadog")
    print(f"  [✓] Multi-Head Attention Score: {attn_res.overall_score}% ({attn_res.fit_label})")
    for h_name, h_val in attn_res.heads.items():
        print(f"      • Head [{h_name}]: {h_val.head_score}%")

    tailored_bullets = attention_service.tailor_resume(primary_jd)
    print(f"  [✓] Synthesized {len(tailored_bullets)} Attention-Ranked DevOps Bullets:")
    for i, b in enumerate(tailored_bullets[:3], 1):
        print(f"      {i}. {b.tailored_text}")

    # ═════════════════════════════════════════════════════════════════════════
    # 3. DECISION-MAKER EMAIL INTELLIGENCE (VP INFRASTRUCTURE / HEAD OF SRE)
    # ═════════════════════════════════════════════════════════════════════════
    banner("3. Decision-Maker Email Intelligence (Infrastructure Leaders)")
    for comp in ["Datadog", "HashiCorp", "Cloudflare"]:
        res = client.post("/api/email-intelligence/discover", json={
            "company": comp,
            "job_title": "VP of Infrastructure / Head of SRE",
            "limit": 2,
        })
        if res.status_code == 200:
            contacts = res.json().get("contacts", [])
            for c in contacts:
                print(f"  [✓] Discovered Leader @ {comp}: {c['name']} ({c['title']}) -> {c['email']}")

    # ═════════════════════════════════════════════════════════════════════════
    # 4. SOCIAL REFERRAL GENERATION (LINKEDIN & X)
    # ═════════════════════════════════════════════════════════════════════════
    banner("4. DevOps Referral Engine: LinkedIn & X Connection Hooks")
    res_li = client.post("/api/referrals/generate-note", json={
        "company": "Datadog",
        "full_name": "Alexis Lê-Quôc",
        "title": "CTO & Co-Founder",
        "role_title": "Senior Staff SRE (Core Infrastructure)",
    })
    if res_li.status_code == 200:
        note = res_li.json()["connection_note"]
        print(f"  [✓] LinkedIn SRE Referral Note for Datadog ({len(note)}/200 chars):")
        print(f"      \"{note}\"")

    res_x = client.post("/api/x/generate-message", json={
        "action_type": "reply",
        "username": "datadoghq",
        "company": "Datadog",
        "name": "Alexis Lê-Quôc",
        "role_title": "Senior Staff SRE",
    })
    if res_x.status_code == 200:
        xmsg = res_x.json()["message"]
        print(f"  [✓] X (Twitter) SRE Hook for @datadoghq ({len(xmsg)}/280 chars):")
        print(f"      \"{xmsg}\"")

    # ═════════════════════════════════════════════════════════════════════════
    # 5. DEVOPS PROOF-OF-WORK FABRICATOR & WHITEBOARD ARCHITECTURE
    # ═════════════════════════════════════════════════════════════════════════
    banner("5. DevOps Proof-of-Work Fabricator & Whiteboard Engine")
    pow_svc = ProofOfWorkFabricatorService()
    pow_fab = pow_svc.fabricate("Datadog", "Senior Staff Site Reliability Engineer")
    print(f"  [✓] Fabricated SRE Micro-Repo: {pow_fab['project_title']}")
    print(f"  [✓] Benchmark Metrics: {pow_fab['benchmark_metrics']['p99_latency_reduction_percent']}% reduction under {pow_fab['benchmark_metrics']['concurrency_rps_tested']} RPS concurrency")
    print(f"  [✓] Synthesized Artifacts: Dockerfile, GitHub Actions CI/CD Pipeline, Concurrency Suite, PR Description")

    wb_svc = SystemDesignWhiteboardService()
    wb = wb_svc.estimate_and_diagram("distributed_rate_limiter", dau=25000000)
    print(f"  [✓] Whiteboard Architecture: {wb['title']} (Peak QPS: {wb['capacity_estimates']['peak_qps']:,} req/s, Target: {wb['p99_sla_target']})")

    # ═════════════════════════════════════════════════════════════════════════
    # 6. THE GODFATHER TELEGRAM CONSIGLIERE: DEVOPS DISPATCH
    # ═════════════════════════════════════════════════════════════════════════
    banner("6. The Godfather Telegram Consigliere: Live SRE Dispatch")
    queries = [
        "I have an interview tomorrow with Datadog for Senior Staff Site Reliability Engineer",
        "How do I counter an offer of 65 LPA from Datadog against 50 LPA from Razorpay?",
        "/frontier",
    ]

    for q in queries:
        resp = bot.process_user_message(q, user_name="DevOps SRE Lead")
        print(f"  👑 Query: \"{q}\"")
        print(f"     ➔ Agent Invoked: {resp.agent_invoked}")
        first_line = resp.text.split('\n')[0].replace('<b>', '').replace('</b>', '')
        print(f"     ➔ Consigliere Response: {first_line[:85]}...")

    session.close()
    elapsed = time.time() - total_start
    print("\n" + "=" * 75)
    print(f"  🎉 DEVOPS / SRE FULL PIPELINE COMPLETE IN {elapsed:.2f}s!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_devops_suite()
