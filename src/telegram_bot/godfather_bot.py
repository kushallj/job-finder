"""
godfather_bot.py — Sovereign Godfather Telegram Bot Client.
Zero-bloat, pure async httpx client integrating with Telegram Bot HTTP API.
Supports both live Telegram polling/webhooks and sandbox web UI simulation.
"""
from __future__ import annotations

import os
import time
import logging
from typing import Any, Dict, List, Optional
import httpx

from src.telegram_bot.models import BotMessageResponse, BotStatusResponse
from src.telegram_bot.command_router import GodfatherCommandRouter
from src.telegram_bot.intent_analyzer import GodfatherIntentAnalyzer

logger = logging.getLogger("godfather_bot.client")


class GodfatherBot:
    """Async Telegram Bot client and executor for all sovereign engineering capabilities."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None
        self.router = GodfatherCommandRouter()
        self.intent_analyzer = GodfatherIntentAnalyzer()
        self.start_time = time.time()
        self.total_commands_executed = 0
        self.last_active_timestamp = None
        self.autopilot_enabled = True
        self.registered_chat_ids: set[str] = set()

    @property
    def is_configured(self) -> bool:
        return bool(self.token and len(self.token) > 10 and not self.token.startswith("mock_"))

    async def get_me(self) -> Dict[str, Any]:
        """Fetches Telegram bot user profile."""
        if not self.is_configured:
            return {
                "ok": True,
                "result": {
                    "id": 888888888,
                    "is_bot": True,
                    "first_name": "The Godfather Consigliere",
                    "username": "GodfatherCopilotBot",
                    "can_join_groups": True,
                    "can_read_all_group_messages": True,
                    "supports_inline_queries": True,
                },
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/getMe")
            return resp.json()

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Sends an HTML formatted message to a Telegram chat."""
        self.registered_chat_ids.add(str(chat_id))
        self.last_active_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        if not self.is_configured:
            # Sandbox simulated dispatch
            logger.info(f"[Sandbox Bot] Dispatched to chat {chat_id}: {text[:80]}...")
            return {"ok": True, "result": {"message_id": int(time.time() * 1000) % 1000000, "chat": {"id": chat_id}, "text": text}}

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{self.base_url}/sendMessage", json=payload)
            return resp.json()

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 10) -> List[Dict[str, Any]]:
        """Fetches pending updates using long polling."""
        if not self.is_configured:
            return []

        params: Dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset

        try:
            async with httpx.AsyncClient(timeout=timeout + 5.0) as client:
                resp = await client.get(f"{self.base_url}/getUpdates", params=params)
                data = resp.json()
                if data.get("ok"):
                    return data.get("result", [])
                return []
        except Exception as e:
            logger.error(f"Error fetching telegram updates: {e}")
            return []

    def process_user_message(
        self,
        message: str,
        user_id: str = "web_user",
        user_name: str = "Sovereign Engineer",
    ) -> BotMessageResponse:
        """
        Executes an incoming message (either slash command or natural language phrase)
        and returns the sovereign response.
        """
        self.total_commands_executed += 1
        self.last_active_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Parse intent
        cmd, args = self.intent_analyzer.parse_intent(message)

        # 2. Dispatch via Command Router
        response = self.router.handle_command(cmd, args, user_name=user_name)

        return response

    async def process_telegram_update(self, update: Dict[str, Any]) -> Optional[BotMessageResponse]:
        """Handles a raw Telegram Update dict from the long poller or webhook."""
        message = update.get("message")
        if not message:
            callback_query = update.get("callback_query")
            if callback_query:
                chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
                data = callback_query.get("data", "/menu")
                from_user = callback_query.get("from", {}).get("first_name", "Engineer")
                response = self.process_user_message(data, user_name=from_user)
                if chat_id:
                    await self.send_message(chat_id, response.text, reply_markup=response.reply_markup)
                return response
            return None

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        from_user = message.get("from", {}).get("first_name", "Engineer")

        if not text:
            return None

        response = self.process_user_message(text, user_id=str(message.get("from", {}).get("id", "")), user_name=from_user)
        if chat_id:
            await self.send_message(chat_id, response.text, reply_markup=response.reply_markup)

        return response

    def get_status(self) -> BotStatusResponse:
        """Returns the current runtime status of the Godfather Bot."""
        uptime = round(time.time() - self.start_time, 1)
        return BotStatusResponse(
            status="active" if self.autopilot_enabled else "paused",
            is_running=True,
            is_configured=self.is_configured,
            bot_username="GodfatherCopilotBot",
            uptime_seconds=uptime,
            total_commands_executed=self.total_commands_executed,
            autopilot_enabled=self.autopilot_enabled,
            active_monitors_count=13,
            last_active_timestamp=self.last_active_timestamp or time.strftime("%Y-%m-%d %H:%M:%S"),
        )
