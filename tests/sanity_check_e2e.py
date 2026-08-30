import sys
import uuid
from fastapi.testclient import TestClient
from main import app

def log_test(name, success, details=""):
    mark = "✓ PASS" if success else "✗ FAIL"
    print(f"[{mark}] {name} {('- ' + details) if details else ''}")
    if not success:
        sys.exit(1)

def run_all_checks():
    client = TestClient(app)
    print("=" * 60)
    print("JOBFINDER & REFERRAL AUTOMATOR — E2E ENDPOINT SUITE")
    print("=" * 60)

    # 1. Health check
    res = client.get("/api/health")
    log_test("GET /api/health", res.status_code == 200, f"Status={res.json().get('status')}")

    # 2. Jobs Listing
    res = client.get("/api/jobs?limit=5")
    log_test("GET /api/jobs", res.status_code == 200, f"Total={res.json().get('pagination', {}).get('total', 0)} jobs")

    # 3. 1-Click Job Capture
    uid = uuid.uuid4().hex[:8]
    cap_payload = {
        "title": f"Staff Distributed Systems Engineer ({uid})",
        "company": f"TestCorp-{uid}",
        "location": "Remote",
        "description": "Scale distributed microservices with Python, FastAPI, and Redis.",
        "url": f"https://www.linkedin.com/jobs/view/test-{uid}",
        "source": "linkedin_extension",
        "score": False,
    }
    res = client.post("/api/jobs/capture", json=cap_payload)
    log_test("POST /api/jobs/capture (New)", res.status_code == 200 and not res.json().get("already_existed"))
    job_id = res.json()["job"]["id"]

    # 4. Job Capture Deduplication
    res2 = client.post("/api/jobs/capture", json=cap_payload)
    log_test("POST /api/jobs/capture (Deduplication)", res2.status_code == 200 and res2.json().get("already_existed") is True)

    # 5. Opportunity Brief
    res = client.get(f"/api/opportunities/{job_id}/brief")
    log_test(f"GET /api/opportunities/{job_id}/brief", res.status_code == 200, f"Fit Score={res.json().get('fit_score')}%")

    # 6. Action Queue
    res = client.get("/api/action-queue")
    log_test("GET /api/action-queue", res.status_code == 200, f"Action Queue Total={res.json().get('total')}")

    # 7. Contacts CRM
    res = client.get("/api/contacts?limit=5")
    log_test("GET /api/contacts", res.status_code == 200, f"Contacts Total={res.json().get('pagination', {}).get('total')}")

    # 8. Stats
    res = client.get("/api/stats")
    log_test("GET /api/stats", res.status_code == 200, f"Jobs={res.json().get('stats', {}).get('total_jobs')}")

    # 9. Referral Targets
    res = client.get("/api/referrals/targets?limit=10")
    log_test("GET /api/referrals/targets", res.status_code == 200, f"Targets={res.json().get('total_targets')}")

    # 10. Referral Search (Company)
    res = client.post("/api/referrals/search", json={"company": "Meta", "limit": 3})
    log_test("POST /api/referrals/search", res.status_code == 200, f"Found {res.json().get('count')} profiles (Source: {res.json().get('source')})")

    # 11. Referral Note Generation
    note_payload = {
        "full_name": "Sarah Jenkins",
        "company": "Meta",
        "job_title": "Staff AI Engineer",
        "sender_name": "Candidate",
        "max_length": 200,
    }
    res = client.post("/api/referrals/generate-note", json=note_payload)
    note_data = res.json()
    log_test("POST /api/referrals/generate-note", res.status_code == 200 and note_data.get("is_under_limit") and note_data.get("char_count") <= 200, f"Length={note_data.get('char_count')}/200 chars")

    # 12. Referral Profile Sync to CRM
    sync_payload = {
        "profiles": [
            {
                "full_name": f"E2E Referrer {uid}",
                "company": f"TestCorp-{uid}",
                "title": "Director of Engineering",
                "linkedin_url": f"https://linkedin.com/in/e2e-referrer-{uid}",
            }
        ]
    }
    res = client.post("/api/referrals/sync", json=sync_payload)
    log_test("POST /api/referrals/sync", res.status_code == 200, f"Synced={res.json().get('synced_count')} (New={res.json().get('new_contacts_count')})")

    # 13. Referral Action Logging
    action_payload = {
        "contact_name": f"E2E Referrer {uid}",
        "company": f"TestCorp-{uid}",
        "action_type": "connection_sent",
        "linkedin_url": f"https://linkedin.com/in/e2e-referrer-{uid}",
        "message_body": "Hi, let's connect!",
        "job_id": job_id,
    }
    res = client.post("/api/referrals/log-action", json=action_payload)
    log_test("POST /api/referrals/log-action", res.status_code == 200, f"Outreach ID={res.json().get('outreach_id')}")

    # 14. Market Intelligence
    res = client.get("/api/market-intelligence?provider=mock")
    log_test("GET /api/market-intelligence", res.status_code == 200, "Intelligence retrieved")

    # 15. Provider Sync
    res = client.post("/api/providers/sync", json={"query": "python developer", "limit": 2})
    log_test("POST /api/providers/sync", res.status_code == 200, f"Sync Total={res.json().get('total_fetched')}")

    # 16. X Auth URL
    res = client.get("/api/x/auth/url")
    log_test("GET /api/x/auth/url", res.status_code == 200, "Auth URL generated")

    # 17. X Auth Callback (Mock)
    res = client.post("/api/x/auth/callback", json={"code": "code_e2e", "state": "state_e2e"})
    log_test("POST /api/x/auth/callback", res.status_code == 200, "X Auth saved")

    # 18. X Targets
    res = client.get("/api/x/targets")
    log_test("GET /api/x/targets", res.status_code == 200, f"X Targets={res.json().get('total_targets')}")

    # 19. X Search Profiles
    res = client.post("/api/x/search", json={"company": "OpenAI", "limit": 3})
    log_test("POST /api/x/search", res.status_code == 200, f"Found {res.json().get('count')} profiles")

    # 20. X Search Tweets
    res = client.post("/api/x/search-tweets", json={"company": "OpenAI", "limit": 3})
    log_test("POST /api/x/search-tweets", res.status_code == 200, f"Found {res.json().get('count')} hiring tweets")

    # 21. X Generate Message
    res = client.post("/api/x/generate-message", json={
        "action_type": "reply",
        "username": "sama",
        "company": "OpenAI",
        "role_title": "Distributed Systems Engineer",
    })
    log_test("POST /api/x/generate-message", res.status_code == 200 and res.json().get("is_under_limit"), f"Len={res.json().get('char_count')}/280")

    # 22. X Engage User (Like/Intent)
    res = client.post("/api/x/engage", json={
        "action_type": "like",
        "target_username": f"x_user_{uid}",
        "company": f"TestCorp-{uid}",
        "tweet_id": "18001001",
        "job_id": job_id,
    })
    log_test("POST /api/x/engage", res.status_code == 200, f"Outreach ID={res.json().get('outreach_id')}")

    # 23. X Profile Sync
    res = client.post("/api/x/sync", json={
        "profiles": [
            {
                "name": f"E2E X User {uid}",
                "username": f"e2e_x_{uid}",
                "company": f"TestCorp-{uid}",
                "title": "Staff Architect",
            }
        ]
    })
    log_test("POST /api/x/sync", res.status_code == 200, f"Synced={res.json().get('synced_count')} (New={res.json().get('new_contacts_count')})")

    # 24. Email Intelligence Discovery
    res = client.post("/api/email-intelligence/discover", json={
        "company": "Stripe",
        "job_title": "Senior Backend Engineer",
        "target_name": "Patrick Collison",
        "limit": 3,
    })
    log_test("POST /api/email-intelligence/discover", res.status_code == 200, f"Found {res.json().get('total_found')} contacts (Domain: {res.json().get('domain')})")

    # 25. Email Intelligence Verify
    res = client.post("/api/email-intelligence/verify", json={"email": "contact@stripe.com"})
    log_test("POST /api/email-intelligence/verify", res.status_code == 200, f"Provider={res.json().get('mail_provider')}, Score={res.json().get('confidence_score')}%")

    # 26. Email Intelligence Dorks
    res = client.post("/api/email-intelligence/dorks", json={"company": "OpenAI", "domain": "openai.com"})
    log_test("POST /api/email-intelligence/dorks", res.status_code == 200, f"Dorks Generated={res.json().get('total_dorks')}")

    # 27. Email Intelligence Permutations
    res = client.post("/api/email-intelligence/permutations", json={"full_name": "Sam Altman", "domain": "openai.com"})
    log_test("POST /api/email-intelligence/permutations", res.status_code == 200, f"Permutations={res.json().get('total_permutations')}")

    # 28. Transformer Q,K,V Attention Match
    res = client.post("/api/attention/match", json={
        "job_description": (
            "We are hiring a Senior Python Engineer with expertise in FastAPI, PostgreSQL, and distributed caching with Redis. "
            "Must have experience designing low-latency async services and mentoring team members."
        ),
    })
    log_test("POST /api/attention/match", res.status_code == 200, f"Score={res.json().get('overall_score')}% ({res.json().get('fit_label')})")

    # 29. Attention Tailored Bullets
    res = client.post("/api/attention/tailor", json={
        "job_description": "FastAPI async microservices and PostgreSQL latency optimization."
    })
    log_test("POST /api/attention/tailor", res.status_code == 200, f"Tailored Bullets={res.json().get('total_bullets')}")

    # 30. Cross-Attention Cold Outreach
    res = client.post("/api/attention/outreach", json={
        "contact_name": "David Marcus",
        "contact_title": "Head of Engineering",
        "company": "Stripe",
        "job_description": "Distributed asynchronous payments platform",
    })
    log_test("POST /api/attention/outreach", res.status_code == 200, f"Subject='{res.json().get('subject')}'")

    print("=" * 60)
    print("🎉 ALL 30 E2E API CHECKS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_all_checks()



