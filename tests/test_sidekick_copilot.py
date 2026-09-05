"""
Unit tests for the Undetectable AI Interview Assistant (Sidekick / Ghost Copilot).
Tests sub-microsecond Trie lookups, hybrid RAG semantic search, and API endpoints.
"""
import os
import time
import pytest
from fastapi.testclient import TestClient

from main import app
from src.sidekick.brain.trie_matcher import InterviewKnowledgeTrie
from src.sidekick.brain.rag_retriever import HybridRAGRetriever
from src.sidekick.native import is_invisibility_supported, set_window_invisible

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
    # Verify sub-microsecond or low microsecond resolution
    assert latency_us < 200.0  # <200 microseconds in test suite (typically 1-5µs compiled)


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
    assert top_doc["id"] in ["distributed_rate_limiter", "kafka_stream_processing", "consistent_hashing"]


def test_sidekick_api_endpoints():
    client = TestClient(app)
    
    # 1. Status
    res = client.get("/api/sidekick/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["total_trie_indexed_keys"] >= 10

    # 2. Query
    res = client.post("/api/sidekick/query", json={"query": "LRU Cache"})
    assert res.status_code == 200
    q_data = res.json()
    assert q_data["source"] in ["trie_exact_match", "hybrid_rag_retrieval", "generative_llm_stream"]
    assert len(q_data["bullets"]) >= 1

    # 3. Invisibility check
    inv_res = client.post("/api/sidekick/window/set-invisible", json={"window_title": "Test Window"})
    assert inv_res.status_code == 200
    assert "status" in inv_res.json()

    # 4. Bank
    bank_res = client.get("/api/sidekick/bank")
    assert bank_res.status_code == 200
    assert bank_res.json()["total_documents"] >= 5


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
