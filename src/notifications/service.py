from __future__ import annotations

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import (
    NotificationConfig,
    AlertPayload,
    ChannelDispatchResult,
    NotificationDispatchResponse,
)
from .dispatcher import notification_dispatcher, NotificationDispatcher

CONFIG_FILE = Path("config/notifications.json")


class NotificationService:
    """Manages notification settings and multi-channel alert dispatching."""

    def __init__(self, dispatcher: Optional[NotificationDispatcher] = None):
        self.dispatcher = dispatcher or notification_dispatcher
        self.config = self._load_config()

    def _load_config(self) -> NotificationConfig:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    return NotificationConfig(**data)
            except Exception:
                pass
        return NotificationConfig(
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID"),
            discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
            slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
        )

    def save_config(self, new_config: NotificationConfig) -> NotificationConfig:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(new_config.model_dump(), f, indent=2)
        self.config = new_config
        return self.config

    def get_config(self) -> NotificationConfig:
        return self.config

    async def dispatch_alert(self, alert: AlertPayload) -> NotificationDispatchResponse:
        results: List[ChannelDispatchResult] = []
        if not self.config.enabled:
            return NotificationDispatchResponse(
                status="disabled",
                dispatched_count=0,
                results=[ChannelDispatchResult(channel="all", status="disabled", detail="Notifications globally disabled")],
                timestamp=datetime.utcnow().isoformat(),
            )

        # Dispatch concurrently to all configured channels
        tasks = [
            self.dispatcher.send_telegram(self.config, alert),
            self.dispatcher.send_discord(self.config, alert),
            self.dispatcher.send_slack(self.config, alert),
        ]
        res_list = await asyncio.gather(*tasks, return_exceptions=True)

        for r in res_list:
            if isinstance(r, ChannelDispatchResult):
                results.append(r)
            else:
                results.append(ChannelDispatchResult(channel="unknown", status="failed", detail=str(r)))

        success_count = sum(1 for r in results if r.status == "success")

        return NotificationDispatchResponse(
            status="success" if success_count > 0 else "completed",
            dispatched_count=success_count,
            results=results,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def send_test_alert(self, channel: str) -> ChannelDispatchResult:
        test_alert = AlertPayload(
            title="Staff Distributed Systems Engineer",
            company="OpenAI",
            location="San Francisco, CA / Remote",
            fit_score=94.5,
            job_url="https://openai.com/careers",
            top_contact_name="Sam Altman",
            top_contact_email="sama@openai.com",
            summary_hook="Led infrastructure scaling to 50k QPS in FastAPI & Redis.",
        )
        if channel == "telegram":
            return await self.dispatcher.send_telegram(self.config, test_alert)
        elif channel == "discord":
            return await self.dispatcher.send_discord(self.config, test_alert)
        elif channel == "slack":
            return await self.dispatcher.send_slack(self.config, test_alert)
        else:
            return ChannelDispatchResult(channel=channel, status="failed", detail="Unknown channel")


notification_service = NotificationService()
