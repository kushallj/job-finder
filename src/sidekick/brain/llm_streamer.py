"""
llm_streamer.py — Local & Cloud Low-Latency LLM Streaming Client.
Streams structured, glanceable interview bullet points with connection pooling and non-blocking I/O.
"""
from __future__ import annotations

import asyncio
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
    ) -> None:
        self.local_endpoint = local_endpoint
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        # Persistent HTTP client with connection pooling
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(4.0, connect=1.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )

    async def aclose(self) -> None:
        """Gracefully close HTTP connection pool."""
        await self._http_client.aclose()

    async def stream_bullets(
        self,
        question: str,
        retrieved_context: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        Streams generated bullet tokens in real-time.
        """
        prompt = f"{TELEPROMPTER_SYSTEM_PROMPT}\n\nCONTEXT:\n{retrieved_context}\n\nQUESTION: {question}\n\nBULLETS:"

        # 1. Try local Ollama / llama.cpp
        try:
            payload = {
                "model": "qwen2.5:3b",
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": 0.2, "num_predict": 150}
            }
            async with self._http_client.stream("POST", self.local_endpoint, json=payload) as response:
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
            logger.debug("Local Ollama endpoint offline, routing to cloud fallback...")

        # 2. Try Gemini 1.5 Flash via non-blocking executor
        if self.gemini_api_key:
            try:
                def _call_gemini() -> str:
                    from google import genai
                    client = genai.Client(api_key=self.gemini_api_key)
                    res = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=f"{TELEPROMPTER_SYSTEM_PROMPT}\n\nCONTEXT:\n{retrieved_context}\n\nQUESTION: {question}"
                    )
                    return res.text if res and res.text else ""

                gemini_text = await asyncio.to_thread(_call_gemini)
                if gemini_text:
                    yield gemini_text
                    return
            except Exception as exc:
                logger.error(f"Gemini generation error: {exc}")

        # 3. High-yield template fallback
        if retrieved_context:
            yield f"• Core Strategy: {retrieved_context[:140]}...\n• Complexity: O(N) linear time with O(1) auxiliary space\n• Trade-off: Optimized for low latency over heavy normalization"
        else:
            yield f"• Core Strategy: Clarify input bounds, choose optimal two-pointer or hash index\n• Complexity: Target O(N) time with O(1) space\n• Edge Case: Handle empty collections, null inputs, and integer overflow"
