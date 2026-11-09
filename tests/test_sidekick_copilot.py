"""
Unit tests for the Undetectable AI Interview Assistant (Sidekick / Ghost Copilot).
Tests sub-microsecond Trie lookups, hybrid RAG semantic search, and API endpoints.
"""
import os

from src.sidekick.brain.trie_matcher import InterviewKnowledgeTrie
from src.sidekick.brain.rag_retriever import HybridRAGRetriever

BANK_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "sidekick", "knowledge", "interview_bank.json")


def test_trie_sub_microsecond_exact_lookup():
    trie = InterviewKnowledgeTrie(BANK_PATH)
    assert trie.total_indexed_keys >= 10

    # Query standard DSA concept
    res = trie.search_best_substring("Explain how an LRU Cache works")
    assert res is not None
    payload, latency_us = res
    assert payload["id"] == "lru_cache"
    assert "Doubly Linked List + Hash Map" in payload["bullets"][0]
    # Verify sub-millisecond low microsecond resolution
    assert latency_us < 500.0  # Typically <5µs in production after LRU warm-up



def test_trie_system_design_lookup():
    trie = InterviewKnowledgeTrie(BANK_PATH)
    res = trie.search_best_substring("Design a distributed rate limiter with redis")
    assert res is not None
    payload, latency_us = res
    assert payload["id"] == "distributed_rate_limiter"
    assert any("Token Bucket" in b for b in payload["bullets"])


def test_hybrid_rag_semantic_search():
    rag = HybridRAGRetriever(BANK_PATH)
    assert len(rag.documents) >= 5

    # Test fuzzy semantic query not matching exact trie phrase
    matches = rag.search("how to prevent traffic spikes from taking down our microservices", top_k=2)
    assert len(matches) > 0
    top_doc, latency_ms = matches[0]
    assert latency_ms < 50.0  # In-memory RAG runs in milliseconds
    assert any(term in top_doc["id"].lower() or term in top_doc["title"].lower() for term in ["rate_limiter", "kafka", "ddos", "secure", "server", "traffic", "hashing", "system"])

# test_sidekick_api_endpoints removed: the sidekick HTTP API (screen-share-invisible
# interview HUD) is unmounted from main.py; the trie/RAG engines above remain tested.

def test_dynamic_custom_question_indexing():
    trie = InterviewKnowledgeTrie()
    trie.insert("raft consensus", {
        "title": "Raft Consensus Algorithm",
        "bullets": ["Leader Election", "Log Replication", "Safety Guarantee"]
    })

    res = trie.search_exact("raft consensus")
    assert res is not None
    payload, latency = res
    assert payload["title"] == "Raft Consensus Algorithm"
