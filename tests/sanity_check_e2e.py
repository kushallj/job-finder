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

    print("=" * 60)
    print("🎉 ALL 14 E2E API CHECKS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_all_checks()
