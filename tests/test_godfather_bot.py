"""
test_godfather_bot.py — Comprehensive Unit & Integration Tests for The Godfather Telegram Bot.
Verifies intent analyzer, command router, async bot client, 24x7 daemon, and FastAPI endpoints.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app
from src.telegram_bot.intent_analyzer import GodfatherIntentAnalyzer
from src.telegram_bot.command_router import GodfatherCommandRouter
from src.telegram_bot.godfather_bot import GodfatherBot
from src.telegram_bot.godfather_daemon import GodfatherDaemon


@pytest.fixture
def client():
    return TestClient(app)


def test_intent_analyzer_slash_commands():
    analyzer = GodfatherIntentAnalyzer()
    
    cmd, args = analyzer.parse_intent("/profile Stripe Staff Eng")
    assert cmd == "/profile"
    assert args == ["Stripe", "Staff", "Eng"]

    cmd, args = analyzer.parse_intent("/counter 50 40 Google")
    assert cmd == "/counter"
    assert args == ["50", "40", "Google"]

    cmd, args = analyzer.parse_intent("/whiteboard trading")
    assert cmd == "/whiteboard"
    assert args == ["trading"]

    cmd, args = analyzer.parse_intent("/simulate raft")
    assert cmd == "/simulate"
    assert args == ["raft"]

    cmd, args = analyzer.parse_intent("/autopilot off")
    assert cmd == "/autopilot"
    assert args == ["off"]


def test_intent_analyzer_natural_language():
    analyzer = GodfatherIntentAnalyzer()

    # 1. Counter intent
    cmd, args = analyzer.parse_intent("How do I counter an offer of 48 LPA from Uber with my current 36 LPA?")
    assert cmd == "/counter"
    assert "48" in args
    assert "Uber" in args

    # 2. Whiteboard intent
    cmd, args = analyzer.parse_intent("Show me the system design and architecture for a high frequency trading exchange orderbook")
    assert cmd == "/whiteboard"
    assert args == ["trading"]

    # 3. Frontier AI intent
    cmd, args = analyzer.parse_intent("Show me frontier AI RLHF gigs paying in USD dollars $/hr on Outlier")
    assert cmd == "/frontier"

    # 4. Anti-Ghosting intent
    cmd, args = analyzer.parse_intent("Recruiter at Apple hasn't replied in 7 days after onsite")
    assert cmd == "/escalate"
    assert "Apple" in args
    assert "7" in args

    # 5. Geo-Arbitrage intent
    cmd, args = analyzer.parse_intent("What is the net salary and PPP in Tokyo Japan?")
    assert cmd == "/geo"
    assert args == ["tokyo"]

    # 6. Web3 bounty intent
    cmd, args = analyzer.parse_intent("Find active Web3 bounties and grants on Solana")
    assert cmd == "/bounty"

    # 7. Proof of Work Fabricator
    cmd, args = analyzer.parse_intent("Fabricate a proof of work repo prototype for Databricks")
    assert cmd == "/fabricate"
    assert "Databricks" in args

    # 8. Executive Memo
    cmd, args = analyzer.parse_intent("Draft an executive decision memo justification for 55 LPA at Netflix")
    assert cmd == "/memo"
    assert "Netflix" in args

    # 9. Simulation intent
    cmd, args = analyzer.parse_intent("Run a simulation of cache eviction under high concurrency")
    assert cmd == "/simulate"
    assert args == ["cache"]

    # 10. Autopilot toggle
    cmd, args = analyzer.parse_intent("Please turn on 24x7 autopilot daemon status")
    assert cmd == "/autopilot"
    assert args == ["on"]


def test_command_router_all_thirteen_features():
    router = GodfatherCommandRouter()

    # 1. Menu
    res = router.handle_command("/menu", [])
    assert "THE GODFATHER" in res.text
    assert res.agent_invoked == "consigliere_menu"
    assert res.reply_markup is not None

    # 2. Profile
    res = router.handle_command("/profile", ["Google", "Engineering Director"])
    assert "Google" in res.text
    assert "Silver-Bullet" in res.text or "Silver" in res.text
    assert res.agent_invoked == "interviewer_profiler"

    # 3. Counter
    res = router.handle_command("/counter", ["50", "40", "Uber"])
    assert "Counter Target" in res.text or "ARBITRAGE" in res.text
    assert res.agent_invoked == "offer_arbitrage"

    # 4. Fabricate
    res = router.handle_command("/fabricate", ["Stripe", "Staff Backend"])
    assert "Stripe" in res.text
    assert "PROOF-OF-WORK" in res.text or "Artifacts" in res.text
    assert res.agent_invoked == "proof_of_work_fabricator"

    # 5. Escalate
    res = router.handle_command("/escalate", ["Databricks", "onsite", "6"])
    assert "Databricks" in res.text
    assert "ESCALATION" in res.text or "Ghosting" in res.text
    assert res.agent_invoked == "anti_ghosting"

    # 6. Frontier
    res = router.handle_command("/frontier", [])
    assert "Frontier AI" in res.text
    assert "$/hr" in res.text or "USD" in res.text
    assert res.agent_invoked == "frontier_ai_radar"

    # 7. Memo
    res = router.handle_command("/memo", ["Coinbase", "65"])
    assert "Coinbase" in res.text
    assert "Memo" in res.text
    assert res.agent_invoked == "executive_memo"

    # 8. Bounty
    res = router.handle_command("/bounty", [])
    assert "Bounty" in res.text or "Grants" in res.text
    assert res.agent_invoked == "web3_bounties"

    # 9. Geo
    res = router.handle_command("/geo", ["tokyo"])
    assert "Tokyo" in res.text
    assert "Savings" in res.text or "Relocation" in res.text
    assert res.agent_invoked == "geo_arbitrage"

    # 10. Whiteboard
    res = router.handle_command("/whiteboard", ["trading"])
    assert "Trading" in res.text
    assert "Peak QPS" in res.text or "Storage" in res.text
    assert res.agent_invoked == "system_design_whiteboard"

    # 11. Pitch
    res = router.handle_command("/pitch", ["Razorpay", "VP of Engineering"])
    assert "Razorpay" in res.text
    assert "Trojan Horse" in res.text
    assert res.agent_invoked == "executive_outreach"

    # 12. Simulate
    res = router.handle_command("/simulate", ["raft"])
    assert "Raft" in res.text or "Consensus" in res.text
    assert res.agent_invoked == "sandbox_simulation"

    # 13. Autopilot
    res = router.handle_command("/autopilot", ["on"])
    assert "Autopilot" in res.text
    assert res.agent_invoked == "autopilot_control"


@pytest.mark.asyncio
async def test_godfather_bot_operations():
    bot = GodfatherBot(token="mock_token_for_test")
    assert not bot.is_configured  # mock token treated safely as sandbox

    me = await bot.get_me()
    assert me["ok"] is True
    assert me["result"]["username"] == "GodfatherCopilotBot"

    # Sandbox send message
    send_res = await bot.send_message(chat_id="12345", text="<b>Test alert</b>")
    assert send_res["ok"] is True
    assert "12345" in bot.registered_chat_ids

    # Process user message directly
    resp = bot.process_user_message("I have an interview at Stripe", user_id="12345", user_name="Alex")
    assert resp.agent_invoked == "interviewer_profiler"
    assert "Stripe" in resp.text

    # Status
    status = bot.get_status()
    assert status.status == "active"
    assert status.is_running is True
    assert status.total_commands_executed >= 1


@pytest.mark.asyncio
async def test_godfather_daemon_and_radar():
    bot = GodfatherBot()
    daemon = GodfatherDaemon(bot=bot, scan_interval_seconds=1)

    # Execute radar scan
    scan = await daemon.execute_radar_scan()
    assert scan["status"] == "completed"
    assert scan["findings_count"] >= 1
    assert len(daemon.latest_radar_findings) >= 1

    # Broadcast test
    daemon.bot.registered_chat_ids.add("test_chat_999")
    dispatched = await daemon.broadcast("🚨 Radar finding alert")
    assert dispatched == 1
    assert daemon.total_alerts_dispatched == 1

    # Status
    status = daemon.get_status()
    assert status["total_alerts_dispatched"] == 1
    assert status["registered_subscribers_count"] == 1

    # Lifecycle start/stop
    await daemon.start()
    assert daemon.is_running is True
    await daemon.stop()
    assert daemon.is_running is False


def test_fastapi_godfather_endpoints(client):
    # 1. GET /api/godfather/status
    res = client.get("/api/godfather/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "bot_username" in data

    # 2. POST /api/godfather/interact
    interact_payload = {
        "message": "/whiteboard trading",
        "user_id": "web_test_user",
        "user_name": "Test Engineer",
    }
    res = client.post("/api/godfather/interact", json=interact_payload)
    assert res.status_code == 200
    interact_data = res.json()
    assert "Trading" in interact_data["text"]
    assert interact_data["agent_invoked"] == "system_design_whiteboard"

    # 3. POST /api/godfather/radar/scan
    res = client.post("/api/godfather/radar/scan")
    assert res.status_code == 200
    scan_data = res.json()
    assert scan_data["status"] == "completed"

    # 4. POST /api/godfather/autopilot/toggle
    res = client.post("/api/godfather/autopilot/toggle", json={"enabled": False})
    assert res.status_code == 200
    assert res.json()["autopilot_enabled"] is False

    res = client.post("/api/godfather/autopilot/toggle", json={"enabled": True})
    assert res.status_code == 200
    assert res.json()["autopilot_enabled"] is True

    # 5. POST /api/godfather/broadcast
    res = client.post("/api/godfather/broadcast", json={"message": "Broadcast test from FastAPI"})
    assert res.status_code == 200
    assert res.json()["status"] == "success"
