import pytest
import math
from fastapi.testclient import TestClient

from main import app
from src.attention.tokenizer import SemanticClauseTokenizer
from src.attention.embeddings import DenseSemanticEmbedder, D_MODEL, NUM_HEADS, D_K
from src.attention.engine import TransformerAttentionEngine
from src.attention.cross_attention_outreach import CrossAttentionOutreachSynthesizer
from src.attention.service import AttentionService


@pytest.fixture
def client():
    return TestClient(app)


def test_semantic_clause_tokenizer():
    tokenizer = SemanticClauseTokenizer()
    sample_jd = (
        "We are looking for a Senior Backend Engineer to build high-throughput APIs in Python and FastAPI.\n"
        "You will design distributed architecture with PostgreSQL and Redis caching (<50ms p99 latency).\n"
        "Lead technical RFC reviews and mentor junior developers.\n"
        "Drive product growth and optimize checkout conversion rates."
    )
    queries = tokenizer.tokenize_job_description(sample_jd)
    assert len(queries) >= 3
    assert any(q.category == "tech" for q in queries)
    assert any(q.category == "scale" for q in queries)

    keys, values = tokenizer.extract_keys_and_values()
    assert len(keys) >= 4
    assert len(values) == len(keys)
    assert any(v.impact_metric is not None for v in values)


def test_dense_semantic_embedder():
    embedder = DenseSemanticEmbedder()
    vec = embedder.embed_text("FastAPI distributed microservices with PostgreSQL")
    assert len(vec) == D_MODEL
    # Check L2 normalization (sum of squares == 1.0)
    norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(norm, 1e-4) == 1.0

    # Check 4-head subspace projections
    for h in range(NUM_HEADS):
        sub_vec = embedder.project_head_subspace(vec, h)
        assert len(sub_vec) == D_K
        sub_norm = math.sqrt(sum(x * x for x in sub_vec))
        assert pytest.approx(sub_norm, 1e-4) == 1.0


def test_transformer_attention_engine_math():
    engine = TransformerAttentionEngine()
    sample_jd = (
        "Looking for a Senior Python Developer with FastAPI and PostgreSQL expertise.\n"
        "Experience building low-latency distributed systems handling high QPS.\n"
        "Strong mentorship, code review, and architecture ownership."
    )
    result = engine.compute_multi_head_match(sample_jd)

    assert result.overall_score >= 50.0
    assert len(result.heads) == 4
    for h_name, head in result.heads.items():
        assert 0.0 <= head.head_score <= 100.0

    # Check Softmax row sum invariant (each row in alpha_ij must sum to 1.0)
    for row in result.matrix.weights:
        row_sum = sum(row)
        assert pytest.approx(row_sum, 1e-3) == 1.0

    # Check tailored bullets ordering
    assert len(result.tailored_bullets) > 0
    scores = [b.attention_score for b in result.tailored_bullets]
    assert scores == sorted(scores, reverse=True)


def test_cross_attention_outreach():
    synth = CrossAttentionOutreachSynthesizer()
    res_em = synth.synthesize_outreach_for_contact(
        contact_name="Sarah Connor",
        contact_title="VP of Engineering",
        company="Stripe",
        job_description="Distributed backend systems and low latency APIs",
    )
    assert res_em["role_type"] == "engineering_manager"
    assert "Stripe" in res_em["subject"]
    assert "Sarah" in res_em["hook_message"]
    assert res_em["attended_proof_point"] is not None

    res_rec = synth.synthesize_outreach_for_contact(
        contact_name="John Miller",
        contact_title="Lead Technical Recruiter",
        company="Anthropic",
    )
    assert res_rec["role_type"] == "recruiter"
    assert "Anthropic" in res_rec["subject"]


def test_attention_api_endpoints(client):
    # 1. POST /api/attention/match
    res = client.post("/api/attention/match", json={
        "job_description": (
            "We need a Staff Software Engineer to build scalable async microservices using Python, FastAPI, and PostgreSQL. "
            "Experience optimizing database queries, handling Redis pub/sub, and mentoring junior engineers required."
        ),
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["overall_score"] > 0
    assert len(data["heads"]) == 4
    assert len(data["matrix"]["weights"]) > 0

    # 2. POST /api/attention/tailor
    res2 = client.post("/api/attention/tailor", json={
        "job_description": "FastAPI, PostgreSQL, Redis performance optimization and high throughput systems."
    })
    assert res2.status_code == 200
    assert res2.json()["total_bullets"] >= 4

    # 3. POST /api/attention/outreach
    res3 = client.post("/api/attention/outreach", json={
        "contact_name": "David Marcus",
        "contact_title": "Head of Engineering",
        "company": "OpenAI",
        "job_description": "Scalable inference backend and low latency routing",
    })
    assert res3.status_code == 200
    assert "OpenAI" in res3.json()["subject"]
