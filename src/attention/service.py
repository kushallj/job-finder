from __future__ import annotations

from typing import List, Dict, Any, Optional

from .models import MultiHeadAttentionResult, TailoredBullet
from .engine import transformer_attention_engine, TransformerAttentionEngine
from .cross_attention_outreach import cross_attention_synthesizer, CrossAttentionOutreachSynthesizer


class AttentionService:
    """
    Main orchestrator for Transformer Q,K,V Attention operations across Job Matching,
    Resume Tailoring, and Outreach Hook Generation.
    """

    def __init__(
        self,
        engine: Optional[TransformerAttentionEngine] = None,
        outreach_synth: Optional[CrossAttentionOutreachSynthesizer] = None,
    ):
        self.engine = engine or transformer_attention_engine
        self.outreach_synth = outreach_synth or cross_attention_synthesizer

    def match_job(
        self,
        job_description: str,
        custom_bullets: Optional[List[str]] = None,
    ) -> MultiHeadAttentionResult:
        """Executes 4-head Q,K,V attention analysis on a job description."""
        return self.engine.compute_multi_head_match(
            job_description=job_description,
            custom_bullets=custom_bullets,
        )

    def tailor_resume(
        self,
        job_description: str,
        custom_bullets: Optional[List[str]] = None,
    ) -> List[TailoredBullet]:
        """Generates attention-ranked tailored bullets for a job description."""
        result = self.engine.compute_multi_head_match(
            job_description=job_description,
            custom_bullets=custom_bullets,
        )
        return result.tailored_bullets

    def synthesize_outreach_hooks(
        self,
        contact_name: str,
        contact_title: str,
        company: str,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generates personalized cold outreach hooks using cross-attention."""
        return self.outreach_synth.synthesize_outreach_for_contact(
            contact_name=contact_name,
            contact_title=contact_title,
            company=company,
            job_description=job_description,
        )


attention_service = AttentionService()
