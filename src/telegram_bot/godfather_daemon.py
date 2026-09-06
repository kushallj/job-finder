"""
godfather_daemon.py — 24x7 Resilient Background Engine for The Godfather Bot.
Maintains continuous autonomous polling, self-healing retries with exponential backoff,
and periodic radar scans across frontier platforms, bounties, and recruiter SLAs.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from src.telegram_bot.godfather_bot import GodfatherBot
from src.telegram_bot.models import BotStatusResponse

logger = logging.getLogger("godfather_bot.daemon")


class GodfatherDaemon:
    """24x7 Autonomous background daemon orchestrating Telegram events and periodic radar."""

    def __init__(self, bot: Optional[GodfatherBot] = None, scan_interval_seconds: int = 60):
        self.bot = bot or GodfatherBot()
        self.scan_interval = scan_interval_seconds
        self.is_running = False
        self._polling_task: Optional[asyncio.Task] = None
        self._radar_task: Optional[asyncio.Task] = None
        self.last_radar_scan_time: Optional[float] = None
        self.total_alerts_dispatched = 0
        self.latest_radar_findings: List[Dict[str, Any]] = []

    async def start(self) -> None:
        """Starts the 24x7 background poller and autonomous radar loops."""
        if self.is_running:
            logger.warning("GodfatherDaemon is already running.")
            return

        self.is_running = True
        logger.info("👑 Initializing The Godfather 24x7 Sovereign Autonomous Engine...")

        # Launch background tasks
        self._polling_task = asyncio.create_task(self._run_polling_loop())
        self._radar_task = asyncio.create_task(self._run_radar_loop())

    async def stop(self) -> None:
        """Gracefully halts the daemon."""
        self.is_running = False
        if self._polling_task:
            self._polling_task.cancel()
        if self._radar_task:
            self._radar_task.cancel()
        logger.info("👑 The Godfather Daemon has been safely paused.")

    async def _run_polling_loop(self) -> None:
        """Continuous long-polling loop with automatic reconnection and backoff."""
        offset: Optional[int] = None
        backoff = 1.0

        while self.is_running:
            try:
                if not self.bot.is_configured:
                    # In sandbox mode, sleep gently and wait for web interaction
                    await asyncio.sleep(2.0)
                    continue

                updates = await self.bot.get_updates(offset=offset, timeout=15)
                for update in updates:
                    offset = update.get("update_id", 0) + 1
                    await self.bot.process_telegram_update(update)

                backoff = 1.0  # Reset backoff on success
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Daemon polling loop encountered exception: {e}. Backoff {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 30.0)

    async def _run_radar_loop(self) -> None:
        """24x7 Periodic autonomous scan across Frontier AI, Web3 Bounties, and Recruiter SLAs."""
        while self.is_running:
            try:
                if self.bot.autopilot_enabled:
                    await self.execute_radar_scan()
                await asyncio.sleep(self.scan_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Daemon radar loop error: {e}")
                await asyncio.sleep(10.0)

    async def execute_radar_scan(self) -> Dict[str, Any]:
        """Performs a single complete autonomous radar pass."""
        self.last_radar_scan_time = time.time()
        findings = []

        # 1. Check Frontier AI gigs
        frontier_platforms = self.bot.router.frontier_svc.get_platforms()
        top_frontier = frontier_platforms[:2]
        if top_frontier:
            findings.append({
                "category": "Frontier AI",
                "title": f"New high-yield opportunities on {top_frontier[0].get('name', 'Alignerr')}",
                "rate": top_frontier[0].get("hourly_rate_range", "$50–$85/hr USD"),
                "badge": "USD Cashflow",
            })

        # 2. Check Web3 bounties
        bounties = self.bot.router.web3_svc.get_bounties()[:2]
        if bounties:
            findings.append({
                "category": "Web3 Bounty",
                "title": bounties[0].get("title", "Solana / Base Protocol Audit"),
                "reward": f"${bounties[0].get('reward_usd', 5000):,} {bounties[0].get('token', 'USDC')}",
                "badge": "Crypto Reward",
            })

        self.latest_radar_findings = findings

        # Broadcast alerts if we have connected chat users and findings
        if self.bot.registered_chat_ids and findings:
            alert_msg = (
                "👑 <b>[GODFATHER 24x7 RADAR ALERT]</b>\n"
                f"Autonomous scan identified <b>{len(findings)}</b> sovereign market opportunities:\n\n"
            )
            for f in findings:
                alert_msg += f"• <b>{f['category']}</b>: {f['title']} (<i>{f.get('rate') or f.get('reward')}</i>)\n"
            alert_msg += "\nType /frontier or /bounty to inspect full dossiers."

            await self.broadcast(alert_msg)

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "completed",
            "findings_count": len(findings),
            "findings": findings,
        }

    async def broadcast(self, message: str, chat_ids: Optional[List[str | int]] = None) -> int:
        """Dispatches an HTML alert message to all or specified Telegram chats."""
        targets = chat_ids or list(self.bot.registered_chat_ids)
        dispatched = 0
        for cid in targets:
            try:
                await self.bot.send_message(cid, message)
                dispatched += 1
                self.total_alerts_dispatched += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to chat {cid}: {e}")
        return dispatched

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive status of daemon and bot."""
        bot_status = self.bot.get_status().model_dump()
        bot_status.update({
            "daemon_running": self.is_running,
            "scan_interval_seconds": self.scan_interval,
            "last_radar_scan": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_radar_scan_time)) if self.last_radar_scan_time else None,
            "total_alerts_dispatched": self.total_alerts_dispatched,
            "registered_subscribers_count": len(self.bot.registered_chat_ids),
            "latest_findings": self.latest_radar_findings,
        })
        return bot_status
