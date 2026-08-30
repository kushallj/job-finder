from __future__ import annotations

from typing import Optional, Dict, Any
from jinja2 import Template
from .models import ReferralProfile, ReferralContext

BASE_REFERRAL_LETTER_TEMPLATE = """Hi {{ first_name }},

I hope you’re doing well. I noticed you're at {{ company }} as {{ title }} and thought to reach out because {{ reason }}.

I'm applying for {{ job_title }} at {{ company }}{% if job_link %} ({{ job_link }}){% endif %}. I’d really appreciate any referral or advice you could share — I have a background in {{ short_bio }} and recently worked on {{ highlight }}.

Thanks for considering — happy to share my resume or chat for 10 minutes.

Best,
{{ sender_name }}"""

BASE_CONNECTION_NOTE_TEMPLATE = "Hi {{ first_name }}, I saw your work at {{ company }}. I'm applying for {{ job_title }} and would love to connect. If open, I'd appreciate a referral. Thanks! - {{ sender_name }}"


class ReferralMessageGenerator:
    """Generates personalized referral request letters and connection notes."""

    def __init__(self, letter_template: Optional[str] = None, note_template: Optional[str] = None):
        self.letter_template = Template(letter_template or BASE_REFERRAL_LETTER_TEMPLATE)
        self.note_template = Template(note_template or BASE_CONNECTION_NOTE_TEMPLATE)

    def generate_letter(self, profile: ReferralProfile, context: ReferralContext | Dict[str, Any]) -> str:
        ctx = context.model_dump() if isinstance(context, ReferralContext) else dict(context)
        first_name = profile.first_name
        if not first_name and profile.full_name:
            first_name = profile.full_name.split()[0]

        data = {
            "first_name": first_name or "there",
            "company": profile.company or ctx.get("company", "the team"),
            "title": profile.title or profile.headline or "an engineer",
            "reason": ctx.get("reason") or "we share similar engineering interests",
            "job_title": ctx.get("job_title") or "an open role",
            "job_link": ctx.get("job_link") or "",
            "short_bio": ctx.get("short_bio") or "software engineering and scalable systems",
            "highlight": ctx.get("highlight") or "high-throughput backend architecture",
            "sender_name": ctx.get("sender_name") or "Candidate",
        }
        return self.letter_template.render(**data).strip()

    def generate_connection_note(self, profile: ReferralProfile, context: ReferralContext | Dict[str, Any], max_length: int = 200) -> str:
        ctx = context.model_dump() if isinstance(context, ReferralContext) else dict(context)
        first_name = profile.first_name
        if not first_name and profile.full_name:
            first_name = profile.full_name.split()[0]

        data = {
            "first_name": first_name or "there",
            "company": profile.company or ctx.get("company", "your team"),
            "job_title": ctx.get("job_title") or "an open role",
            "sender_name": ctx.get("sender_name") or "Candidate",
        }
        rendered = self.note_template.render(**data).strip()
        if len(rendered) <= max_length:
            return rendered

        # Concise fallback if rendered template exceeds limit
        compact = f"Hi {data['first_name']}, I'm applying for {data['job_title']} at {data['company']} and would love to connect for a quick referral chat. Thanks!"
        if len(compact) <= max_length:
            return compact

        # Hard trim respecting word boundary
        return compact[:max_length - 3].rsplit(" ", 1)[0] + "..."


message_generator = ReferralMessageGenerator()
