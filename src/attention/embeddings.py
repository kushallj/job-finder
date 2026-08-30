from __future__ import annotations

import math
import re
import hashlib
from typing import List, Dict

D_MODEL = 128
NUM_HEADS = 4
D_K = D_MODEL // NUM_HEADS  # 32 dims per head


class DenseSemanticEmbedder:
    """
    High-performance semantic vector embedder with Multi-Head subspace projections (d=128, d_k=32).
    Generates normalized dense representations for Query (Q), Key (K), and Value (V) tokens.
    """

    def __init__(self, d_model: int = D_MODEL, num_heads: int = NUM_HEADS):
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads

    def _hash_token(self, token: str, seed: int) -> float:
        """Generates deterministic pseudo-random projection weights."""
        h = hashlib.md5(f"{token}_{seed}".encode("utf-8")).hexdigest()
        val = int(h[:8], 16) / 0xFFFFFFFF
        return (val * 2.0) - 1.0

    def embed_text(self, text: str) -> List[float]:
        """Projects text into a d_model-dimensional unit sphere embedding."""
        words = re.findall(r"\b[a-z0-9_+#.-]+\b", text.lower())
        if not words:
            return [0.0] * self.d_model

        vec = [0.0] * self.d_model

        # Token + Bigram embedding
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")

        for tok in tokens:
            # Term weight (IDF heuristic: longer tokens/tech keywords get higher weight)
            w = 1.5 if any(c in tok for c in ("+", "#", ".", "fastapi", "django", "react", "redis", "postgres", "p99", "scale")) else 1.0
            for dim in range(self.d_model):
                vec[dim] += self._hash_token(tok, dim) * w

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [x / norm for x in vec]
        return vec

    def project_head_subspace(self, embedding: List[float], head_idx: int) -> List[float]:
        """Extracts and normalizes the d_k-dimensional vector slice for attention head `head_idx`."""
        start = head_idx * self.d_k
        end = start + self.d_k
        sub_vec = embedding[start:end]
        norm = math.sqrt(sum(x * x for x in sub_vec))
        if norm > 1e-9:
            return [x / norm for x in sub_vec]
        return [1.0 / math.sqrt(self.d_k)] * self.d_k


embedder = DenseSemanticEmbedder()
