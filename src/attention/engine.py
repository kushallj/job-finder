from __future__ import annotations

import math
from typing import List, Dict, Tuple, Any, Optional

from .models import (
    QueryToken,
    KeyToken,
    ValuePayload,
    AttentionHeadResult,
    AttentionMatrix,
    TailoredBullet,
    MultiHeadAttentionResult,
    CrossAttentionOutreachHook,
)
from .embeddings import DenseSemanticEmbedder, embedder, D_MODEL, NUM_HEADS, D_K
from .tokenizer import SemanticClauseTokenizer, clause_tokenizer

HEAD_NAMES = [
    "tech_stack",
    "scale_systems",
    "business_impact",
    "seniority_leadership",
]

HEAD_WEIGHTS = {
    "tech_stack": 0.35,
    "scale_systems": 0.25,
    "business_impact": 0.20,
    "seniority_leadership": 0.20,
}


class TransformerAttentionEngine:
    """
    Transformer Multi-Head Scaled Dot-Product Attention Engine (H=4, d=128, d_k=32).
    Computes fine-grained semantic attention between Job Requirements (Q),
    Candidate Capabilities (K), and Quantifiable Proof Values (V).
    """

    def __init__(self, emb: Optional[DenseSemanticEmbedder] = None, tok: Optional[SemanticClauseTokenizer] = None):
        self.embedder = emb or embedder
        self.tokenizer = tok or clause_tokenizer

    def _dot_product(self, v1: List[float], v2: List[float]) -> float:
        """Computes dot product between two equal-length vectors."""
        return sum(a * b for a, b in zip(v1, v2))

    def _softmax(self, logits: List[float]) -> List[float]:
        """Numerically stable softmax."""
        if not logits:
            return []
        max_val = max(logits)
        exp_vals = [math.exp(x - max_val) for x in logits]
        total = sum(exp_vals)
        return [e / total for e in exp_vals] if total > 1e-9 else [1.0 / len(logits)] * len(logits)

    def scaled_dot_product_attention(
        self,
        Q: List[List[float]],  # N_q x d_k
        K: List[List[float]],  # N_k x d_k
        d_k: int = D_K,
        temperature_scale: float = 1.0,
    ) -> List[List[float]]:
        """
        Computes attention weight matrix alpha = softmax(Q * K^T / (sqrt(d_k) * temp)).
        Returns N_q x N_k matrix where each row sums to 1.0.
        """
        scale = math.sqrt(d_k) * temperature_scale
        matrix: List[List[float]] = []

        for q_vec in Q:
            row_logits: List[float] = []
            for k_vec in K:
                dot = self._dot_product(q_vec, k_vec)
                scaled_logit = dot / scale
                row_logits.append(scaled_logit)
            weights = self._softmax(row_logits)
            matrix.append(weights)

        return matrix

    def compute_multi_head_match(
        self,
        job_description: str,
        custom_bullets: Optional[List[str]] = None,
    ) -> MultiHeadAttentionResult:
        """
        Executes complete 4-Head Q,K,V Attention pipeline for a job description and candidate profile.
        """
        # 1. Tokenize Q, K, V
        queries = self.tokenizer.tokenize_job_description(job_description)
        keys, values = self.tokenizer.extract_keys_and_values(custom_bullets=custom_bullets)

        # 2. Embed all tokens into d_model space
        q_embeds = [self.embedder.embed_text(q.text) for q in queries]
        k_embeds = [self.embedder.embed_text(k.text) for k in keys]

        heads_output: Dict[str, AttentionHeadResult] = {}
        all_head_weights: List[List[List[float]]] = []  # 4 x N_q x N_k

        # 3. Compute Attention for each Head
        for h_idx, h_name in enumerate(HEAD_NAMES):
            # Project Q and K into this head's d_k subspace
            q_sub = [self.embedder.project_head_subspace(qe, h_idx) for qe in q_embeds]
            k_sub = [self.embedder.project_head_subspace(ke, h_idx) for ke in k_embeds]

            # Scaled Dot-Product Attention
            head_weights = self.scaled_dot_product_attention(q_sub, k_sub, d_k=D_K)
            all_head_weights.append(head_weights)

            # Compute head score: average of max alignment cosine per query
            q_scores = []
            for q_i, q_vec in enumerate(q_sub):
                max_dot = max(self._dot_product(q_vec, k_vec) for k_vec in k_sub)
                # Map dot product [-1, 1] to [0, 100]
                norm_score = max(0.0, min(100.0, ((max_dot + 1.0) / 2.0) * 100.0))
                q_scores.append(norm_score * queries[q_i].weight)

            total_weight = sum(queries[q_i].weight for q_i in range(len(queries)))
            head_score = (sum(q_scores) / total_weight) if total_weight > 0 else 75.0

            # Top matching query-key pairs
            top_pairs = []
            for q_i, row in enumerate(head_weights):
                best_k_idx = max(range(len(row)), key=lambda j: row[j])
                top_pairs.append({
                    "query_id": queries[q_i].id,
                    "query_text": queries[q_i].text,
                    "key_id": keys[best_k_idx].id,
                    "key_text": keys[best_k_idx].text,
                    "attention_weight": round(row[best_k_idx], 4),
                })

            heads_output[h_name] = AttentionHeadResult(
                head_name=h_name,
                head_score=round(head_score, 1),
                top_matches=top_pairs[:4],
            )

        # 4. Synthesize Combined Master Attention Matrix (Multi-Head Linear Output Projection)
        num_q = len(queries)
        num_k = len(keys)
        master_weights: List[List[float]] = []

        for q_i in range(num_q):
            master_row: List[float] = [0.0] * num_k
            for k_j in range(num_k):
                # Weighted combination across heads
                combined_weight = sum(
                    all_head_weights[h_idx][q_i][k_j] * HEAD_WEIGHTS[HEAD_NAMES[h_idx]]
                    for h_idx in range(NUM_HEADS)
                )
                master_row[k_j] = combined_weight
            # Re-normalize row so sum = 1.0
            row_sum = sum(master_row)
            if row_sum > 1e-9:
                master_row = [round(w / row_sum, 4) for w in master_row]
            master_weights.append(master_row)

        # 5. Calculate Overall Attention Alignment Score
        overall_score = sum(
            heads_output[h_name].head_score * HEAD_WEIGHTS[h_name]
            for h_name in HEAD_NAMES
        )
        overall_score = round(min(100.0, max(0.0, overall_score)), 1)

        fit_label = (
            "Exceptional Transformer Alignment (Top 1%)" if overall_score >= 88.0
            else "Strong Multi-Head Match" if overall_score >= 75.0
            else "Moderate Strategic Fit" if overall_score >= 60.0
            else "Partial Fit (Requires Upskilling/Pivoting)"
        )

        # 6. Synthesize Tailored Bullets (ranked by total received attention sum_i alpha_ij)
        key_total_attention = [0.0] * num_k
        for row in master_weights:
            for k_j, w in enumerate(row):
                key_total_attention[k_j] += w

        tailored_bullets: List[TailoredBullet] = []
        for k_j in range(num_k):
            # Find queries that attended most heavily to this key
            attending_queries = [
                queries[q_i].text for q_i in range(num_q) if master_weights[q_i][k_j] >= 0.15
            ]
            tailored_bullets.append(TailoredBullet(
                original_text=values[k_j].proof_point,
                tailored_text=values[k_j].proof_point,
                attention_score=round(key_total_attention[k_j], 3),
                matched_queries=attending_queries[:2],
                quant_metric=values[k_j].impact_metric,
            ))

        tailored_bullets.sort(key=lambda tb: tb.attention_score, reverse=True)

        # 7. Extract Top Attended Values
        top_value_indices = sorted(range(num_k), key=lambda j: key_total_attention[j], reverse=True)[:4]
        top_attended_values = [values[idx] for idx in top_value_indices]

        # 8. Cross-Attention Outreach Hooks
        outreach_hooks: List[CrossAttentionOutreachHook] = []
        for q_i in range(min(3, num_q)):
            best_k = max(range(num_k), key=lambda j: master_weights[q_i][j])
            q_text = queries[q_i].text
            v_point = values[best_k].proof_point
            metric = values[best_k].impact_metric or "production systems"

            hook = (
                f"I noticed your focus on {q_text[:45]}... In my recent work, "
                f"I engineered {v_point[:80]}."
            )
            outreach_hooks.append(CrossAttentionOutreachHook(
                target_pain_point=q_text,
                candidate_proof_point=v_point,
                attention_weight=master_weights[q_i][best_k],
                hook_sentence=hook,
                call_to_action="Would you be open to a brief 10-minute chat this Thursday to explore synergies?",
            ))

        summary_insight = (
            f"Q,K,V Attention computed across {num_q} requirement queries and {num_k} candidate keys. "
            f"Strongest head: {max(heads_output.values(), key=lambda h: h.head_score).head_name.replace('_', ' ').title()} "
            f"({max(heads_output.values(), key=lambda h: h.head_score).head_score}%)."
        )

        return MultiHeadAttentionResult(
            overall_score=overall_score,
            fit_label=fit_label,
            heads=heads_output,
            matrix=AttentionMatrix(
                query_tokens=queries,
                key_tokens=keys,
                weights=master_weights,
            ),
            top_attended_values=top_attended_values,
            tailored_bullets=tailored_bullets,
            outreach_hooks=outreach_hooks,
            summary_insight=summary_insight,
        )


transformer_attention_engine = TransformerAttentionEngine()
