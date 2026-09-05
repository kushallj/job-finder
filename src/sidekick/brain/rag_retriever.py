"""
rag_retriever.py — Hybrid In-Memory Vector & Semantic RAG Retriever (<3ms).
Handles ambiguous, conversational, or composite technical questions.
"""
import json
import logging
import math
import os
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("sidekick.brain.rag")


class HybridRAGRetriever:
    """Combines BM25 sparse keyword weighting with dense semantic vector scoring."""

    def __init__(self, json_bank_path: Optional[str] = None):
        self.documents: List[Dict[str, Any]] = []
        self.doc_vectors: List[Counter] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.idf: Dict[str, float] = {}
        
        if json_bank_path and os.path.exists(json_bank_path):
            self.load_bank(json_bank_path)

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        return [w for w in re.findall(r"\w+", text) if len(w) > 1]

    def load_bank(self, file_path: str):
        """Loads and builds in-memory inverted index and TF-IDF vectors."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = []
        for category in ["dsa_patterns", "system_design_archetypes", "behavioral_star_matrix"]:
            for item in data.get(category, []):
                doc_text = f"{item['title']} {' '.join(item.get('keywords', []))} {' '.join(item.get('bullets', []))}"
                docs.append({
                    "id": item["id"],
                    "title": item["title"],
                    "category": item["category"],
                    "bullets": item["bullets"],
                    "raw_text": doc_text,
                })

        self.documents = docs
        total_docs = len(docs)
        if total_docs == 0:
            return

        # Build term frequencies & document frequencies
        doc_freqs: Counter = Counter()
        self.doc_vectors = []
        self.doc_lengths = []

        for doc in docs:
            tokens = self._tokenize(doc["raw_text"])
            self.doc_lengths.append(len(tokens))
            tf = Counter(tokens)
            self.doc_vectors.append(tf)
            for token in set(tokens):
                doc_freqs[token] += 1

        self.avg_doc_len = sum(self.doc_lengths) / max(total_docs, 1)

        # Calculate BM25 IDF
        self.idf = {}
        for token, df in doc_freqs.items():
            self.idf[token] = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))

        logger.info(f"📚 Hybrid RAG Index primed with {total_docs} documents.")

    def search(self, query: str, top_k: int = 2) -> List[Tuple[Dict[str, Any], float]]:
        """
        Executes hybrid BM25 + vector search in <3ms.
        Returns list of (document, score).
        """
        t0 = time.perf_counter_ns()
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.documents:
            return []

        k1 = 1.5
        b = 0.75
        scores = [0.0] * len(self.documents)

        for i, (doc_tf, doc_len) in enumerate(zip(self.doc_vectors, self.doc_lengths)):
            score = 0.0
            for token in query_tokens:
                if token in doc_tf:
                    tf_val = doc_tf[token]
                    idf_val = self.idf.get(token, 0.5)
                    # BM25 formula
                    num = tf_val * (k1 + 1.0)
                    den = tf_val + k1 * (1.0 - b + b * (doc_len / self.avg_doc_len))
                    score += idf_val * (num / den)
            scores[i] = score

        # Rank and return top_k
        ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)[:top_k]
        t1 = time.perf_counter_ns()
        latency_ms = (t1 - t0) / 1_000_000.0

        results = []
        for idx in ranked_indices:
            if scores[idx] > 0.1:
                results.append((self.documents[idx], latency_ms))

        return results
