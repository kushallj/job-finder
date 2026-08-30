from __future__ import annotations

import json
import logging
import httpx
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import NotificationConfig, AlertPayload, ChannelDispatchResult

log = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches formatted alerts to Telegram, Discord, and Slack."""

    async def send_telegram(self, config: NotificationConfig, alert: AlertPayload) -> ChannelDispatchResult:
        if not config.telegram_bot_token or not config.telegram_chat_id:
            return ChannelDispatchResult(channel="telegram", status="disabled", detail="Missing Telegram Token or Chat ID")

        text = (
            f"🚀 <b>High-Fit Opportunity Discovered ({alert.fit_score}% Match)</b>\n\n"
            f"<b>Role:</b> {alert.title}\n"
            f"<b>Company:</b> {alert.company} ({alert.location})\n"
            f"<b>Posting:</b> <a href=\"{alert.job_url}\">View Job Posting</a>\n"
        )
        if alert.top_contact_name and alert.top_contact_email:
            text += f"<b>Decision-Maker:</b> {alert.top_contact_name} (<code>{alert.top_contact_email}</code>)\n"
        if alert.summary_hook:
            text += f"\n💡 <i>{alert.summary_hook}</i>"

        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": config.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    return ChannelDispatchResult(channel="telegram", status="success", detail="Delivered to Telegram chat")
                else:
                    return ChannelDispatchResult(channel="telegram", status="failed", detail=f"HTTP {res.status_code}: {res.text[:100]}")
        except Exception as exc:
            return ChannelDispatchResult(channel="telegram", status="failed", detail=str(exc))

    async def send_discord(self, config: NotificationConfig, alert: AlertPayload) -> ChannelDispatchResult:
        if not config.discord_webhook_url:
            return ChannelDispatchResult(channel="discord", status="disabled", detail="Missing Discord Webhook URL")

        embed = {
            "title": f"🚀 {alert.title} @ {alert.company}",
            "url": alert.job_url,
            "description": alert.summary_hook or "New high-priority career opportunity matches your profile.",
            "color": 0x4F46E5,  # Indigo
            "fields": [
                {"name": "🎯 Fit Score", "value": f"**{alert.fit_score}%**", "inline": True},
                {"name": "📍 Location", "value": alert.location or "Remote", "inline": True},
            ],
            "footer": {"text": "JobFinder Autonomous Career Engine"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        if alert.top_contact_name and alert.top_contact_email:
            embed["fields"].append({
                "name": "👤 Decision-Maker",
                "value": f"{alert.top_contact_name} (`{alert.top_contact_email}`)",
                "inline": False,
            })

        payload = {
            "username": "JobFinder Executive Bot",
            "embeds": [embed],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(config.discord_webhook_url, json=payload)
                if res.status_code in (200, 204):
                    return ChannelDispatchResult(channel="discord", status="success", detail="Delivered to Discord channel")
                else:
                    return ChannelDispatchResult(channel="discord", status="failed", detail=f"HTTP {res.status_code}: {res.text[:100]}")
        except Exception as exc:
            return ChannelDispatchResult(channel="discord", status="failed", detail=str(exc))

    async def send_slack(self, config: NotificationConfig, alert: AlertPayload) -> ChannelDispatchResult:
        if not config.slack_webhook_url:
            return ChannelDispatchResult(channel="slack", status="disabled", detail="Missing Slack Webhook URL")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🚀 High-Fit Opportunity: {alert.title} @ {alert.company}", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Match Score:*\n`{alert.fit_score}%`"},
                    {"type": "mrkdwn", "text": f"*Location:*\n{alert.location or 'Remote'}"},
                ]
            },
        ]
        if alert.top_contact_name and alert.top_contact_email:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Hiring Decision-Maker:*\n{alert.top_contact_name} (<mailto:{alert.top_contact_email}|{alert.top_contact_email}>)"}
            })
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open Job Posting ↗"},
                    "url": alert.job_url,
                    "style": "primary"
                }
            ]
        })

        payload = {"blocks": blocks}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(config.slack_webhook_url, json=payload)
                if res.status_code == 200:
                    return ChannelDispatchResult(channel="slack", status="success", detail="Delivered to Slack channel")
                else:
                    return ChannelDispatchResult(channel="slack", status="failed", detail=f"HTTP {res.status_code}: {res.text[:100]}")
        except Exception as exc:
            return ChannelDispatchResult(channel="slack", status="failed", detail=str(exc))


notification_dispatcher = NotificationDispatcher()
