"""
chat_providers.py — the seam between Jobify chat and whichever LLM answers it.

A provider turns a conversation into a stream of text chunks:

    async for chunk in provider.stream(messages, mode=mode):
        ...

`messages` is the OpenAI-style list [{"role": "system"|"user"|"assistant", "content": str}],
newest last. Providers must not perform side effects (no email, no posting): agent mode may
only return drafts for the user to approve (CLAUDE.md §1).

Selected by settings.chat_provider:
  - "echo" (default): deterministic stub that streams the user's message back. No network.

Planned: one OpenAI-compatible provider configured by base URL + model + key. That single
class covers Ollama (/v1), Hugging Face's router, OpenRouter, Alibaba Model Studio (Qwen),
Moonshot (Kimi), MiniMax and NVIDIA NIM, because they all accept /chat/completions with
stream=true. Add it here and register it in PROVIDERS; nothing else changes.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict, List, Protocol

from src.config import settings

Message = Dict[str, str]

SYSTEM_PROMPTS = {
    "ask": "You are Jobify's job-search assistant. Answer concisely and only from facts you are given.",
    "agent": ("You are Jobify's job-search agent. You may research and draft outreach, but you never send "
              "anything: every email is returned as a draft for the user to review and approve."),
}


class ChatProvider(Protocol):
    name: str

    def stream(self, messages: List[Message], *, mode: str) -> AsyncIterator[str]:
        """Yield reply text in chunks. Raise ChatProviderError if no reply can be produced."""
        ...


class ChatProviderError(RuntimeError):
    """The provider could not produce a reply (network, auth, quota). Shown to the user."""


class EchoProvider:
    """Stand-in until an LLM is chosen: streams the last user message back, word by word."""

    name = "echo"

    def __init__(self, delay_ms: int = 40):
        self.delay = max(0, delay_ms) / 1000

    async def stream(self, messages: List[Message], *, mode: str) -> AsyncIterator[str]:
        last = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        reply = f"Echo ({mode} mode, no AI model connected yet): {last}"
        words = reply.split(" ")
        for i, word in enumerate(words):
            if self.delay:
                await asyncio.sleep(self.delay)
            yield word if i == len(words) - 1 else word + " "


PROVIDERS = {
    "echo": lambda: EchoProvider(settings.chat_echo_delay_ms),
}


def get_chat_provider() -> ChatProvider:
    name = (settings.chat_provider or "echo").strip().lower()
    if name not in PROVIDERS:
        raise ChatProviderError(f"Unknown CHAT_PROVIDER '{name}'. Available: {', '.join(sorted(PROVIDERS))}")
    return PROVIDERS[name]()


def build_prompt(history: List[Message], mode: str, max_turns: int = 20) -> List[Message]:
    """System prompt for the mode + the most recent turns (keeps requests bounded)."""
    return [{"role": "system", "content": SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["ask"])}] + history[-max_turns:]
