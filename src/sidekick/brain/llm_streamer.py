"""
llm_streamer.py — Local & Cloud Low-Latency LLM Streaming Client.
Streams structured, glanceable interview bullet points.
"""
import json
import logging
import os
import time
from typing import AsyncGenerator, Dict, Any, Optional

import httpx

logger = logging.getLogger("sidekick.brain.llm")

TELEPROMPTER_SYSTEM_PROMPT = """You are a stealth interview copilot. Output EXACTLY 3 concise, high-impact bullet points for the candidate to read while speaking naturally.
Rules:
1. Bullet 1: Core Algorithm / Architectural Pattern & Key Mechanism.
2. Bullet 2: Time & Space Complexity or Concrete Scale Metrics (QPS, latency, storage).
3. Bullet 3: Critical Edge Case, Trade-off, or Bottleneck to verbally mention.
4. NO conversational filler, greetings, or markdown codeblocks. Only 3 bullet points starting with '•'."""


class InterviewLLMStreamer:
    """Streams fast responses from local LLM (llama.cpp / Ollama) or fast fallback."""

    def __init__(
        self,
        local_endpoint: str = "http://localhost:11434/api/generate",
        gemini_api_key: Optional[str] = None
    ):
        self.local_endpoint = local_endpoint
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

    async def stream_bullets(
        self,
        question: str,
        retrieved_context: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        Streams generated bullet tokens in real-time.
        """
        t0 = time.perf_counter()
        
        # 1. Try local Ollama / llama.cpp if accessible
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                payload = {
                    "model": "qwen2.5:3b",
                    "prompt": f"{TELEPROMPTER_SYSTEM_PROMPT}\n\nCONTEXT:\n{retrieved_context}\n\nQUESTION: {question}\n\nBULLETS:",
                    "stream": True,
                    "options": {"temperature": 0.2, "num_predict": 150}
                }
                async with client.stream("POST", self.local_endpoint, json=payload) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_bytes():
                            if chunk:
                                try:
                                    data = json.loads(chunk.decode("utf-8"))
                                    token = data.get("response", "")
                                    if token:
                                        yield token
                                except Exception:
                                    pass
                        return
        except Exception:
            logger.debug("Local Ollama endpoint offline, routing to fast cloud/template engine...")

        # 2. Try Gemini 1.5 Flash if API key is present
        if self.gemini_api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.gemini_api_key)
                prompt = f"{TELEPROMPTER_SYSTEM_PROMPT}\n\nCONTEXT:\n{retrieved_context}\n\nQUESTION: {question}"
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
                if response and response.text:
                    yield response.text
                    return
            except Exception as exc:
                logger.error(f"Gemini fallback failed: {exc}")

        # 3. Fast fallback bullets synthesized from retrieved context
        if retrieved_context:
            yield f"• Core Strategy: {retrieved_context[:120]}...\n• Complexity: O(N) optimized with in-memory hashing\n• Trade-off: Favoring low latency over heavy normalization"
        else:
            yield f"• Core Approach: Clarify input bounds, choose optimal hash/two-pointer traversal\n• Complexity: Target O(N) time with O(1) auxiliary space\n• Edge Case: Handle empty collections, duplicates, and integer overflow"
