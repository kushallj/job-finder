from __future__ import annotations

from typing import List, Dict, Any, Optional
from .models import ValuePayload, CrossAttentionOutreachHook
from .embeddings import embedder, DenseSemanticEmbedder
from .tokenizer import clause_tokenizer, SemanticClauseTokenizer


class CrossAttentionOutreachSynthesizer:
    """
    Computes cross-attention between a Decision-Maker's Profile / Pain Point (Q)
    and the Candidate's Portfolio Values (V) to generate hyper-relevant cold outreach hooks.
    """

    def __init__(self, emb: Optional[DenseSemanticEmbedder] = None, tok: Optional[SemanticClauseTokenizer] = None):
        self.embedder = emb or embedder
        self.tokenizer = tok or clause_tokenizer

    def synthesize_outreach_for_contact(
        self,
        contact_name: str,
        contact_title: str,
        company: str,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Cross-attends the contact's persona and job requirements to generate tailored outreach angles.
        """
        _, values = self.tokenizer.extract_keys_and_values()

        # Build contact query string
        t_low = contact_title.lower()
        if "recruiter" in t_low or "talent" in t_low or "sourcer" in t_low:
            role_type = "recruiter"
        elif any(m in t_low for m in ("manager", "head", "director", "vp", "architect", "lead engineer", "tech lead", "engineering")):
            role_type = "engineering_manager"
        elif any(f in t_low for f in ("founder", "ceo", "cto", "co-founder")):
            role_type = "founder"
        else:
            role_type = "engineering_manager"

        query_text = f"{contact_title} at {company} hiring for {job_description or 'Software Engineer'}"

        q_vec = self.embedder.embed_text(query_text)
        v_embeds = [self.embedder.embed_text(v.proof_point) for v in values]

        # Dot product similarity
        sims = [sum(a * b for a, b in zip(q_vec, ve)) for ve in v_embeds]
        best_idx = max(range(len(sims)), key=lambda i: sims[i])
        best_val = values[best_idx]

        first_name = contact_name.split()[0] if contact_name else "there"

        if role_type == "engineering_manager":
            subject = f"Scaling backend & distributed systems at {company}"
            hook = (
                f"Hi {first_name}, I saw you lead engineering at {company}. "
                f"Given your focus on distributed architecture, I wanted to reach out: "
                f"in my recent work, I {best_val.proof_point.lower()}."
            )
        elif role_type == "recruiter":
            subject = f"Senior Full Stack & Python Engineer — {company}"
            hook = (
                f"Hi {first_name}, I noticed {company} is actively growing the engineering team. "
                f"With hands-on experience in high-concurrency Python/FastAPI and React/TypeScript, "
                f"I recently {best_val.proof_point.lower()}."
            )
        else:  # Founder / CTO
            subject = f"Building fast & scalable systems at {company}"
            hook = (
                f"Hi {first_name}, huge fan of what you're building at {company}. "
                f"I specialize in end-to-end full-stack velocity: {best_val.proof_point.lower()}."
            )

        return {
            "contact_name": contact_name,
            "contact_title": contact_title,
            "company": company,
            "role_type": role_type,
            "subject": subject,
            "hook_message": hook,
            "attended_proof_point": best_val.proof_point,
            "impact_metric": best_val.impact_metric,
            "call_to_action": "Would you be open to a quick 10-minute sync this week to explore if my background aligns?",
        }


cross_attention_synthesizer = CrossAttentionOutreachSynthesizer()
