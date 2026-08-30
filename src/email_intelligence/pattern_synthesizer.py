from __future__ import annotations

import re
from typing import List, Dict, Optional, Tuple
from .models import EmailPermutation

PATTERNS = [
    ("first.last", lambda f, l: f"{f}.{l}"),
    ("first", lambda f, l: f"{f}"),
    ("flast", lambda f, l: f"{f[0]}{l}"),
    ("firstl", lambda f, l: f"{f}{l[0]}"),
    ("first_last", lambda f, l: f"{f}_{l}"),
    ("first-last", lambda f, l: f"{f}-{l}"),
    ("f.last", lambda f, l: f"{f[0]}.{l}"),
    ("last.first", lambda f, l: f"{l}.{f}"),
    ("last", lambda f, l: f"{l}"),
    ("firstlast", lambda f, l: f"{f}{l}"),
    ("lastf", lambda f, l: f"{l}{f[0]}"),
    ("f_last", lambda f, l: f"{f[0]}_{l}"),
]


class CorporatePatternSynthesizer:
    """
    Synthesizes and permutes corporate email permutations for decision-makers.
    Supports dynamic pattern learning from verified email samples.
    """

    def __init__(self):
        self._known_domain_patterns: Dict[str, str] = {}  # domain -> "first.last"

    def tokenize_name(self, full_name: str) -> Tuple[str, str]:
        """Normalizes and splits full names into clean (first, last) tokens."""
        clean = re.sub(r"[^a-zA-Z\s]", "", full_name).strip().lower()
        parts = [p for p in clean.split() if len(p) >= 2]
        if not parts:
            return "user", "name"
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else parts[0]
        return first, last

    def learn_pattern_from_sample(self, verified_email: str, full_name: str) -> Optional[str]:
        """Learns the company's naming convention from a verified email sample."""
        if "@" not in verified_email:
            return None
        local_part, domain = verified_email.lower().split("@", 1)
        first, last = self.tokenize_name(full_name)
        if not first or not last:
            return None

        for pat_name, fn in PATTERNS:
            try:
                candidate = fn(first, last)
                if candidate == local_part:
                    self._known_domain_patterns[domain] = pat_name
                    return pat_name
            except Exception:
                continue
        return None

    def generate_permutations(
        self,
        full_name: str,
        domain: str,
        has_mx: bool = True,
    ) -> List[EmailPermutation]:
        """
        Generates prioritized corporate email permutations for a person and domain.
        If a known corporate pattern was learned, that pattern receives the highest priority.
        """
        first, last = self.tokenize_name(full_name)
        clean_domain = domain.strip().lower()
        known_pat = self._known_domain_patterns.get(clean_domain)

        permutations: List[EmailPermutation] = []

        for pat_name, fn in PATTERNS:
            try:
                local_part = fn(first, last)
                email = f"{local_part}@{clean_domain}"

                # Base score calculation
                if known_pat and pat_name == known_pat:
                    score = 90.0
                elif pat_name == "first.last":
                    score = 80.0
                elif pat_name in ("first", "flast"):
                    score = 75.0
                elif pat_name in ("first_last", "f.last"):
                    score = 70.0
                else:
                    score = 60.0

                if not has_mx:
                    score = max(20.0, score - 30.0)

                permutations.append(EmailPermutation(
                    pattern_name=pat_name,
                    email=email,
                    domain=clean_domain,
                    confidence_score=score,
                    has_mx=has_mx,
                ))
            except Exception:
                continue

        # Sort by confidence score descending
        permutations.sort(key=lambda p: p.confidence_score, reverse=True)
        return permutations


pattern_synthesizer = CorporatePatternSynthesizer()
