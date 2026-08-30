from __future__ import annotations

import re
from typing import Optional, Dict, Any

try:
    from jinja2 import Template
    _JINJA_OK = True
except ImportError:
    _JINJA_OK = False

from .models import XProfile, XTweet, XContext

BASE_X_DM_TEMPLATE = """Hey @{{ username }}! Loved seeing what you're building at {{ company }}.

I'm applying for {{ role_title }}{% if job_link %} ({{ job_link }}){% endif %}. I specialize in {{ candidate_bio }} and recently worked on {{ highlight }}.

Would love to chat or ask for a referral if you're open to it! Thanks, {{ sender_name }}"""

BASE_TWEET_REPLY_TEMPLATE = """Hey @{{ username }}, really love your work at {{ company }} on {{ target_topic }}! Applying for {{ role_title }} and excited about what the team is shipping."""

BASE_QUOTE_TWEET_TEMPLATE = """Huge fan of the engineering culture at {{ company }}. Excited to apply for {{ role_title }} and contribute to {{ target_topic }}!"""


class XMessageGenerator:
    """Generates high-signal, character-constrained messages, tweet replies, and DMs for X networking."""

    def __init__(
        self,
        dm_template: Optional[str] = None,
        reply_template: Optional[str] = None,
        quote_template: Optional[str] = None,
    ):
        self._dm_tmpl_str = dm_template or BASE_X_DM_TEMPLATE
        self._reply_tmpl_str = reply_template or BASE_TWEET_REPLY_TEMPLATE
        self._quote_tmpl_str = quote_template or BASE_QUOTE_TWEET_TEMPLATE

    def _render(self, template_str: str, data: Dict[str, Any]) -> str:
        if _JINJA_OK:
            return Template(template_str).render(**data).strip()
        # Pure string replace fallback
        res = template_str
        for k, v in data.items():
            res = res.replace(f"{{{{ {k} }}}}", str(v or ""))
            res = res.replace(f"{{{{{k}}}}}", str(v or ""))
        # Strip Jinja conditional tags if jinja2 is missing
        res = re.sub(r"\{%.*?%\}", "", res)
        return res.strip()

    def generate_dm(
        self,
        profile: XProfile,
        context: XContext | Dict[str, Any],
        max_length: int = 1000,
    ) -> str:
        ctx = context.model_dump() if isinstance(context, XContext) else dict(context)
        username = profile.username.lstrip("@")
        data = {
            "username": username,
            "company": profile.company or ctx.get("company", "your team"),
            "role_title": ctx.get("role_title") or "the open position",
            "job_link": ctx.get("job_link") or "",
            "candidate_bio": ctx.get("candidate_bio") or "distributed backend systems and AI pipelines",
            "highlight": ctx.get("highlight") or "high-throughput real-time APIs",
            "sender_name": ctx.get("sender_name") or "Candidate",
        }
        rendered = self._render(self._dm_tmpl_str, data)
        if len(rendered) <= max_length:
            return rendered

        # Concise fallback
        compact = f"Hi @{username}, I'm applying for {data['role_title']} at {data['company']} ({data['candidate_bio']}). Would love to connect for a referral chat! - {data['sender_name']}"
        if len(compact) <= max_length:
            return compact

        return compact[:max_length - 3].rsplit(" ", 1)[0] + "..."

    def generate_tweet_reply(
        self,
        profile: XProfile,
        tweet: Optional[XTweet] = None,
        context: Optional[XContext | Dict[str, Any]] = None,
        max_length: int = 280,
    ) -> str:
        ctx = context.model_dump() if isinstance(context, XContext) else dict(context or {})
        username = profile.username.lstrip("@")
        data = {
            "username": username,
            "company": profile.company or ctx.get("company", "your team"),
            "role_title": ctx.get("role_title") or "the engineering team",
            "target_topic": ctx.get("target_topic") or "scalable architecture",
        }
        rendered = self._render(self._reply_tmpl_str, data)
        if len(rendered) <= max_length:
            return rendered

        compact = f"Great insights @{username}! Big fan of {data['company']}'s work in {data['target_topic']}."
        if len(compact) <= max_length:
            return compact
        return compact[:max_length - 3].rsplit(" ", 1)[0] + "..."

    def generate_quote_tweet(
        self,
        profile: XProfile,
        tweet: Optional[XTweet] = None,
        context: Optional[XContext | Dict[str, Any]] = None,
        max_length: int = 280,
    ) -> str:
        ctx = context.model_dump() if isinstance(context, XContext) else dict(context or {})
        data = {
            "company": profile.company or ctx.get("company", "this team"),
            "role_title": ctx.get("role_title") or "engineering",
            "target_topic": ctx.get("target_topic") or "high-scale infrastructure",
        }
        rendered = self._render(self._quote_tmpl_str, data)
        if len(rendered) <= max_length:
            return rendered
        return rendered[:max_length - 3].rsplit(" ", 1)[0] + "..."


x_message_generator = XMessageGenerator()
