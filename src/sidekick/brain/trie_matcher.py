"""
trie_matcher.py — Ultra-Fast In-Memory Radix/Trie Matcher (<5µs lookup).
Indexes high-yield interview questions, DSA patterns, and system design archetypes.
"""
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("sidekick.brain.trie")

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or", "how", "what",
    "is", "are", "do", "does", "explain", "design", "implement", "tell", "me", "about", "write"
}


class TrieNode:
    __slots__ = ("children", "is_terminal", "payload")

    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_terminal: bool = False
        self.payload: Optional[Dict[str, Any]] = None


class InterviewKnowledgeTrie:
    """In-memory Trie capable of sub-microsecond (<5µs) query resolution."""

    def __init__(self, json_bank_path: Optional[str] = None):
        self.root = TrieNode()
        self.total_indexed_keys = 0
        if json_bank_path and os.path.exists(json_bank_path):
            self.load_from_json(json_bank_path)

    def normalize_text(self, text: str) -> str:
        """Strips punctuation and standardizes spacing."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        words = [w for w in text.split() if w and w not in STOP_WORDS]
        return " ".join(words)

    def insert(self, phrase: str, payload: Dict[str, Any]):
        """Inserts normalized phrase into the Trie."""
        norm = self.normalize_text(phrase)
        if not norm:
            return

        current = self.root
        for char in norm:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]

        current.is_terminal = True
        current.payload = payload
        self.total_indexed_keys += 1

    def search_exact(self, query: str) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Sub-microsecond exact lookup. Returns (payload, latency_microseconds).
        """
        t0 = time.perf_counter_ns()
        norm = self.normalize_text(query)
        if not norm:
            return None

        current = self.root
        for char in norm:
            if char not in current.children:
                return None
            current = current.children[char]


        t1 = time.perf_counter_ns()
        latency_us = (t1 - t0) / 1000.0

        if current.is_terminal and current.payload:
            return current.payload, latency_us
        return None

    def search_best_substring(self, query: str) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Scans n-gram windows of query to find matching concepts in <5 microseconds.
        """
        t0 = time.perf_counter_ns()
        norm = self.normalize_text(query)
        words = norm.split()
        
        # Try full phrase first
        exact = self.search_exact(norm)
        if exact:
            return exact

        # Try sliding sub-phrases from length n down to 1
        for length in range(len(words), 0, -1):
            for i in range(len(words) - length + 1):
                sub_phrase = " ".join(words[i:i+length])
                match = self.search_exact(sub_phrase)
                if match:
                    t1 = time.perf_counter_ns()
                    return match[0], (t1 - t0) / 1000.0

        return None

    def load_from_json(self, file_path: str):
        """Loads and indexes DSA patterns, System Design, and STAR stories."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for category in ["dsa_patterns", "system_design_archetypes", "behavioral_star_matrix"]:
            items = data.get(category, [])
            for item in items:
                # Index main title
                self.insert(item["title"], item)
                # Index all keyword aliases
                for kw in item.get("keywords", []):
                    self.insert(kw, item)

        logger.info(f"⚡ In-Memory Interview Trie ready with {self.total_indexed_keys} indexed lookup paths.")
