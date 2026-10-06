"""
sidekick_router.py — FastAPI Router for Interview Sidekick / Ghost Copilot.
Exposes microsecond Trie queries, Inverted Index RAG, and window invisibility control.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from src.sidekick.native import set_window_invisible, is_invisibility_supported
from src.sidekick.brain.trie_matcher import InterviewKnowledgeTrie
from src.sidekick.brain.rag_retriever import HybridRAGRetriever
from src.sidekick.brain.llm_streamer import InterviewLLMStreamer

router = APIRouter(prefix="/api/sidekick", tags=["interview-sidekick"])

# Singleton instances initialized once
BANK_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge", "interview_bank.json")
trie_engine = InterviewKnowledgeTrie(BANK_PATH)
rag_engine = HybridRAGRetriever(BANK_PATH)
llm_streamer = InterviewLLMStreamer()

LATEST_LIVE_HINT: Dict[str, Any] = {
    "timestamp": time.time(),
    "transcript": "",
    "hint": None
}


class SidekickQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    stream: bool = False
    candidate_context: Optional[str] = None
    force_llm: bool = False


class CustomQuestionAddRequest(BaseModel):
    id: str
    title: str
    keywords: List[str] = Field(default_factory=list)
    category: str = "Technical Question"
    bullets: List[str] = Field(default_factory=list)


class InvisibilityToggleRequest(BaseModel):
    window_title: Optional[str] = "Job Finder Copilot"


@router.get("/status")
def get_sidekick_status() -> Dict[str, Any]:
    """Returns sidekick readiness and OS invisibility capabilities."""
    return {
        "status": "online",
        "invisibility_supported": is_invisibility_supported(),
        "total_trie_indexed_keys": trie_engine.total_indexed_keys,
        "rag_indexed_documents": len(rag_engine.documents),
        "local_llm_configured": True,
        "ollama_model": "qwen2.5:3b",
    }


@router.get("/live-hint")
def get_latest_live_hint() -> Dict[str, Any]:
    """Returns the latest hint transcribed by either native mic or desktop client."""
    return LATEST_LIVE_HINT


class FeedSpeechRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    accumulated_context: Optional[str] = None


@router.post("/feed-speech")
async def feed_speech_from_native_listener(req: FeedSpeechRequest) -> Dict[str, Any]:
    """Receives transcribed speech with rolling accumulated context and resolves best question card."""
    global LATEST_LIVE_HINT
    query_to_try = req.transcript
    accumulated = (req.accumulated_context or "").strip()

    # 1. Try resolving against the latest phrase
    res = await execute_sidekick_query(SidekickQueryRequest(query=query_to_try))

    # 2. If single phrase produced generic fallback and accumulated context exists, try full accumulated context
    if (res.get("tier", 3) >= 3) and accumulated and len(accumulated) > len(query_to_try):
        context_res = await execute_sidekick_query(SidekickQueryRequest(query=accumulated))
        if context_res.get("tier", 3) < 3:
            res = context_res
            query_to_try = accumulated

    display_transcript = accumulated if (accumulated and len(accumulated) > len(req.transcript)) else req.transcript

    LATEST_LIVE_HINT = {
        "timestamp": time.time(),
        "transcript": display_transcript,
        "hint": res
    }
    return {"status": "success", "hint": res}


@router.post("/ask-llm")
async def ask_local_ollama_direct(req: SidekickQueryRequest) -> Dict[str, Any]:
    """Forces direct inference on local Ollama (qwen2.5:3b) for complex/custom questions."""
    t0 = time.perf_counter_ns()
    query = req.query.strip()
    generated_tokens: List[str] = []
    async for token in llm_streamer.stream_bullets(question=query):
        generated_tokens.append(token)

    full_text = "".join(generated_tokens)
    bullets = [b.strip().lstrip("•").strip() for b in full_text.split("\n") if b.strip()]
    if not bullets:
        bullets = [full_text]

    t1 = time.perf_counter_ns()
    total_ms = (t1 - t0) / 1_000_000.0

    res = {
        "source": "local_ollama_qwen2.5",
        "tier": 3,
        "title": query,
        "category": "Ollama Local LLM",
        "bullets": bullets,
        "latency_milliseconds": round(total_ms, 2),
        "latency_display": f"{total_ms:.1f} ms (Ollama Qwen2.5:3b)",
    }
    global LATEST_LIVE_HINT
    LATEST_LIVE_HINT = {
        "timestamp": time.time(),
        "transcript": query,
        "hint": res
    }
    return res


@router.post("/window/set-invisible")
def toggle_window_invisibility(req: InvisibilityToggleRequest) -> Dict[str, Any]:
    """Applies OS-level screen share invisibility (NSWindowSharingNone / WDA_EXCLUDEFROMCAPTURE)."""
    return set_window_invisible(req.window_title)


CONV_PREFIXES = [
    re.compile(r"^(can you|could you|would you|please)?\s*(walk me through|tell me about|explain|describe|what is|what are|how does|how do you|how would you|what are the trade-offs of|what is the difference between|compare)\s+", re.IGNORECASE),
    re.compile(r"^(so|well|okay|now|next|also|tell me|give me|can you share)\s+", re.IGNORECASE),
]


def clean_query_intent(raw: str) -> str:
    cleaned = raw.strip()
    for rx in CONV_PREFIXES:
        cleaned = rx.sub("", cleaned)
    return cleaned.strip() or raw.strip()


@router.post("/query")
async def execute_sidekick_query(req: SidekickQueryRequest) -> Dict[str, Any]:
    """
    Multi-Tier Query Engine:
    Tier 1: Instant Trie Sub-Microsecond Match (<5µs)
    Tier 2: Inverted Index BM25 RAG (<1ms)
    Tier 3: Local LLM Stream Synthesis (<200ms TTFT)
    """
    global LATEST_LIVE_HINT
    t0 = time.perf_counter_ns()
    raw_query = req.query.strip()
    if not raw_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if req.force_llm:
        return await ask_local_ollama_direct(req)

    cleaned_query = clean_query_intent(raw_query)

    # 1. Tier 1: Trie search (try cleaned query first, then raw query)
    trie_match = trie_engine.search_best_substring(cleaned_query) or trie_engine.search_best_substring(raw_query)
    if trie_match:
        payload, latency_us = trie_match
        res = {
            "source": "trie_exact_match",
            "tier": 1,
            "title": payload.get("title", cleaned_query),
            "category": payload.get("category", "General"),
            "bullets": payload.get("bullets", []),
            "latency_microseconds": round(latency_us, 2),
            "latency_display": f"{latency_us:.2f} µs (Sub-Microsecond)",
        }
        LATEST_LIVE_HINT = {"timestamp": time.time(), "transcript": raw_query, "hint": res}
        return res

    # 2. Tier 2: Hybrid Inverted Index RAG Search
    rag_matches = rag_engine.search(cleaned_query, top_k=2) or rag_engine.search(raw_query, top_k=2)
    if rag_matches:
        top_doc, latency_ms = rag_matches[0]
        res = {
            "source": "hybrid_rag_retrieval",
            "tier": 2,
            "title": top_doc.get("title", cleaned_query),
            "category": top_doc.get("category", "Technical Concept"),
            "bullets": top_doc.get("bullets", []),
            "latency_milliseconds": round(latency_ms, 2),
            "latency_display": f"{latency_ms:.2f} ms (Inverted Index RAG)",
        }
        LATEST_LIVE_HINT = {"timestamp": time.time(), "transcript": raw_query, "hint": res}
        return res

    # 3. Tier 3: Fast Generative LLM Stream Fallback (Local Ollama qwen2.5:3b)
    generated_tokens: List[str] = []
    async for token in llm_streamer.stream_bullets(question=cleaned_query):
        generated_tokens.append(token)

    full_text = "".join(generated_tokens)
    bullets = [b.strip().lstrip("•").strip() for b in full_text.split("\n") if b.strip()]
    if not bullets:
        bullets = [full_text]

    t1 = time.perf_counter_ns()
    total_ms = (t1 - t0) / 1_000_000.0

    res = {
        "source": "generative_llm_stream",
        "tier": 3,
        "title": cleaned_query,
        "category": "Ollama Local LLM",
        "bullets": bullets,
        "latency_milliseconds": round(total_ms, 2),
        "latency_display": f"{total_ms:.1f} ms (LLM Synthesis)",
    }
    LATEST_LIVE_HINT = {"timestamp": time.time(), "transcript": raw_query, "hint": res}
    return res


class SyncSheetRequest(BaseModel):
    sheet_url: Optional[str] = None


@router.get("/bank")
def get_interview_knowledge_bank() -> Dict[str, Any]:
    """Returns all pre-compiled DSA patterns, System Design archetypes, and STAR stories."""
    return {
        "total_documents": len(rag_engine.documents),
        "documents": rag_engine.documents,
    }


@router.post("/sync-sheet")
async def sync_google_sheet_question_bank(req: Optional[SyncSheetRequest] = None) -> Dict[str, Any]:
    """Syncs real-world interview question bank directly from Google Sheets."""
    from src.services.question_bank_syncer import question_bank_syncer, DEFAULT_GOOGLE_SHEET_URL
    url = req.sheet_url if (req and req.sheet_url) else DEFAULT_GOOGLE_SHEET_URL
    res = await question_bank_syncer.run_sync_pipeline(url)
    return res


@router.post("/audio/transcribe")
async def transcribe_audio_chunk(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Transcribes an incoming audio chunk (WebM, WAV, OGG, MP4) via high-accuracy SpeechRecognition
    and automatically executes sub-microsecond Trie/RAG matching for instant live suggestions.
    """
    import subprocess
    import tempfile
    import speech_recognition as sr

    try:
        audio_bytes = await file.read()
        if not audio_bytes or len(audio_bytes) < 300:
            return {"status": "empty", "transcript": "", "query_response": None}

        # Save to temporary input file
        with tempfile.NamedTemporaryFile(suffix=".raw_audio", delete=False) as in_f:
            in_f.write(audio_bytes)
            in_f_path = in_f.name

        out_wav_path = in_f_path + ".wav"

        # Convert to 16kHz Mono WAV using ffmpeg
        ffmpeg_bin = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
        try:
            cmd = [
                ffmpeg_bin, "-y", "-i", in_f_path,
                "-ar", "16000", "-ac", "1", "-f", "wav", out_wav_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            wav_file_to_read = out_wav_path
        except Exception as ffmpeg_err:
            wav_file_to_read = in_f_path

        r = sr.Recognizer()
        r.energy_threshold = 300
        r.dynamic_energy_threshold = True
        transcript = ""
        try:
            with sr.AudioFile(wav_file_to_read) as source:
                audio_data = r.record(source)
                transcript = r.recognize_google(audio_data)
        except sr.UnknownValueError:
            # Silence or ambient noise
            return {"status": "no_speech", "transcript": "", "query_response": None}
        except Exception as e:
            return {"status": "transcribe_error", "message": str(e), "transcript": "", "query_response": None}
        finally:
            # Cleanup temp files
            for p in [in_f_path, out_wav_path]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        if not transcript or len(transcript.strip()) < 2:
            return {"status": "empty", "transcript": "", "query_response": None}

        # Automatically execute query against Trie & RAG knowledge bank
        query_res = await execute_sidekick_query(SidekickQueryRequest(query=transcript.strip()))

        return {
            "status": "success",
            "transcript": transcript.strip(),
            "query_response": query_res,
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc), "transcript": "", "query_response": None}


@router.post("/bank/add")
def add_custom_question(req: CustomQuestionAddRequest) -> Dict[str, Any]:
    """Inserts a custom question into both in-memory Trie AND Inverted Index RAG."""
    payload = req.model_dump()
    
    # 1. Update Trie
    trie_engine.insert(req.title, payload)
    for kw in req.keywords:
        trie_engine.insert(kw, payload)

    # 2. Update RAG Index
    rag_engine.add_document(payload)

    return {
        "status": "success",
        "message": f"Successfully indexed '{req.title}' into both Trie & RAG engines.",
        "total_trie_keys": trie_engine.total_indexed_keys,
        "total_rag_documents": len(rag_engine.documents),
    }

