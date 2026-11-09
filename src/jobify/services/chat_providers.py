"""
chat_providers.py — the seam between Jobify chat and whichever LLM answers it.

A provider turns a conversation into a stream of text chunks:

    async for chunk in provider.stream(messages, mode=mode):
        ...

`messages` is the OpenAI-style list [{"role": "system"|"user"|"assistant", "content": str}],
newest last. Providers must not perform side effects (no email, no posting): agent mode may
only return drafts for the user to approve (CLAUDE.md §1). After a stream finishes,
`provider.last_usage` holds token counts when the API reported them.

settings.chat_provider is a comma-separated chain, tried in order until one starts replying:
  echo        no-network stub (default)
  ollama      local Ollama  (CHAT_OLLAMA_BASE_URL, CHAT_OLLAMA_MODEL; dev only, no Ollama on PaaS)
  openrouter  OpenRouter    (OPENROUTER_API_KEY, CHAT_OPENROUTER_MODEL; ":free" models available)
  hf          Hugging Face  (HF_TOKEN, CHAT_HF_MODEL)
  custom      any OpenAI-compatible API: Alibaba Qwen, Moonshot Kimi, MiniMax, NVIDIA NIM
              (CHAT_CUSTOM_BASE_URL, CHAT_CUSTOM_API_KEY, CHAT_CUSTOM_MODEL)
Unconfigured entries are skipped. A provider that fails BEFORE producing text falls through to
the next; once text has streamed, a failure ends the reply (no mixing of two models' output).

Reasoning ("thinking") is never shown to users: `reasoning`/`reasoning_content` deltas are
dropped and inline <think>...</think> blocks are stripped. Thinking is also switched off where
the API supports it, because reasoning tokens count against max_tokens.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from src.config import settings

log = logging.getLogger(__name__)

Message = dict[str, str]

_NO_INVENTION = (
    " Never invent facts about the user: no made-up employers, projects, results, metrics or numbers. "
    "Use only what the user has told you. Where a draft needs a detail you don't have, write a bracketed "
    "placeholder such as [a project you shipped] or [measurable result] for the user to fill in."
    " If the user asks you to add claims that aren't in their profile, especially ones they suggest are "
    "exaggerated or unverifiable, don't write them in: say in one sentence that you'll only state what they can "
    "back up, then offer an honest alternative built from their real profile. Such claims stay out for the rest of "
    "the conversation, even in later drafts. Never write anything implying recruiters won't check. Never invent "
    "contact details (emails, phone numbers): use placeholders."
    " Write plain text with no Markdown (no **bold**, # headings or tables): replies are shown as-is and "
    "drafts get pasted straight into email or LinkedIn."
)
SYSTEM_PROMPTS = {
    "ask": "You are Jobify's job-search assistant. Answer concisely and only from facts you are given." + _NO_INVENTION,
    "agent": ("You are Jobify's job-search agent. You may research and draft outreach, but you never send "
              "anything: every email is returned as a draft for the user to review and approve. If asked to send, "
              "say plainly that you can't send messages and that they can copy the draft." + _NO_INVENTION),
}


class ChatProvider(Protocol):
    name: str

    def stream(self, messages: list[Message], *, mode: str) -> AsyncIterator[str]:
        """Yield reply text in chunks. Raise ChatProviderError if no reply can be produced."""
        ...


class ChatProviderError(RuntimeError):
    """The provider could not produce a reply (network, auth, quota). The message is user-safe."""


# --- echo stub -------------------------------------------------------------------------

class EchoProvider:
    """Stand-in until an LLM is configured: streams the last user message back, word by word."""

    name = "echo"
    last_usage: dict[str, Any] | None = None

    def __init__(self, delay_ms: int = 40):
        self.delay = max(0, delay_ms) / 1000

    async def stream(self, messages: list[Message], *, mode: str) -> AsyncIterator[str]:
        last = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        reply = f"Echo ({mode} mode, no AI model connected yet): {last}"
        words = reply.split(" ")
        for i, word in enumerate(words):
            if self.delay:
                await asyncio.sleep(self.delay)
            yield word if i == len(words) - 1 else word + " "


# --- OpenAI-compatible -------------------------------------------------------------------

class ThinkFilter:
    """Removes <think>...</think> spans from a stream whose tags may be split across chunks."""

    OPEN, CLOSE = "<think>", "</think>"

    def __init__(self) -> None:
        self.buf = ""
        self.inside = False

    def feed(self, text: str) -> str:
        self.buf += text
        out = []
        while self.buf:
            tag = self.CLOSE if self.inside else self.OPEN
            i = self.buf.find(tag)
            if i >= 0:
                if not self.inside:
                    out.append(self.buf[:i])
                self.buf = self.buf[i + len(tag):]
                self.inside = not self.inside
                continue
            # keep a possible partial tag at the end for the next chunk
            keep = next((n for n in range(len(tag) - 1, 0, -1) if self.buf.endswith(tag[:n])), 0)
            if not self.inside:
                out.append(self.buf[:len(self.buf) - keep])
            self.buf = self.buf[len(self.buf) - keep:]
            break
        return "".join(out)

    def flush(self) -> str:
        rest, self.buf = ("" if self.inside else self.buf), ""
        return rest


_STATUS_MESSAGES = {
    401: "The AI model rejected the server's API key.",
    403: "The AI model rejected the server's API key.",
    404: "The configured AI model was not found.",
    429: "The AI model is busy or out of free quota. Try again shortly.",
}


@dataclass
class OpenAICompatibleProvider:
    """Streams /chat/completions from any OpenAI-compatible API."""

    name: str
    base_url: str
    model: str
    api_key: str | None = None
    extra_body: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    timeout_s: float = 60.0
    max_tokens: int = 1024
    temperature: float = 0.4
    transport: httpx.AsyncBaseTransport | None = None  # tests inject a MockTransport
    last_usage: dict[str, Any] | None = None

    async def stream(self, messages: list[Message], *, mode: str) -> AsyncIterator[str]:  # noqa: PLR0912 -- SSE parse loop
        body = {"model": self.model, "messages": messages, "stream": True, "max_tokens": self.max_tokens,
                "temperature": self.temperature, **self.extra_body}
        headers = {"Accept": "text/event-stream", **self.headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        timeout = httpx.Timeout(self.timeout_s, connect=10.0)
        think = ThinkFilter()
        try:
            async with (
                httpx.AsyncClient(timeout=timeout, transport=self.transport) as client,
                client.stream("POST", self.base_url.rstrip("/") + "/chat/completions",
                              json=body, headers=headers) as res,
            ):
                    if res.status_code >= 400:
                        detail = (await res.aread())[:300].decode("utf-8", "replace")
                        log.warning("chat provider %s HTTP %s: %s", self.name, res.status_code, detail)
                        raise ChatProviderError(_STATUS_MESSAGES.get(
                            res.status_code, f"The AI model returned an error ({res.status_code})."))
                    async for raw_line in res.aiter_lines():
                        line = raw_line.strip()
                        if not line.startswith("data:"):
                            continue  # blank lines, "event:" lines, ": keep-alive" comments
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except ValueError:
                            continue
                        if chunk.get("error"):
                            log.warning("chat provider %s stream error: %s", self.name, chunk["error"])
                            raise ChatProviderError("The AI model stopped with an error.")
                        if chunk.get("usage"):
                            self.last_usage = chunk["usage"]
                        for choice in chunk.get("choices") or []:
                            text = (choice.get("delta") or {}).get("content")  # reasoning fields ignored
                            if text:
                                visible = think.feed(text)
                                if visible:
                                    yield visible
            tail = think.flush()
            if tail:
                yield tail
        except httpx.TimeoutException as exc:
            raise ChatProviderError("The AI model took too long to respond.") from exc
        except httpx.HTTPError as exc:
            log.warning("chat provider %s unreachable: %s", self.name, exc)
            raise ChatProviderError("The AI model is unreachable right now.") from exc


# --- fallback chain ------------------------------------------------------------------------

class FallbackProvider:
    """Tries providers in order; moves on only if the current one fails before any text."""

    def __init__(self, providers: list[ChatProvider]):
        self.providers = providers
        self.name = providers[0].name
        self.last_usage: dict[str, Any] | None = None

    async def stream(self, messages: list[Message], *, mode: str) -> AsyncIterator[str]:
        last_error: ChatProviderError | None = None
        for provider in self.providers:
            started = False
            try:
                async for chunk in provider.stream(messages, mode=mode):
                    if not started:
                        started = True
                        self.name = provider.name  # recorded on the saved message
                    yield chunk
                self.last_usage = getattr(provider, "last_usage", None)
                return
            except ChatProviderError as exc:
                if started:
                    raise
                log.warning("chat provider %s failed before replying, trying next: %s", provider.name, exc)
                last_error = exc
        raise last_error or ChatProviderError("No AI model is available.")


# --- configuration ---------------------------------------------------------------------------

def _common() -> dict[str, Any]:
    # Reasoning tokens count against max_tokens, so thinking needs a bigger budget.
    max_tokens = settings.chat_reasoning_max_tokens if settings.chat_reasoning else settings.chat_max_tokens
    return {"timeout_s": settings.chat_timeout_s, "max_tokens": max_tokens, "temperature": settings.chat_temperature}


def _ollama() -> ChatProvider | None:
    if not settings.chat_ollama_model:
        return None
    extra: dict[str, Any] = {"stream_options": {"include_usage": True}}
    if not settings.chat_reasoning:
        extra["reasoning_effort"] = "none"  # disables qwen3-style thinking on Ollama
    return OpenAICompatibleProvider(name="ollama", base_url=settings.chat_ollama_base_url,
                                    model=settings.chat_ollama_model, extra_body=extra, **_common())


def _openrouter() -> ChatProvider | None:
    if not (settings.openrouter_api_key and settings.chat_openrouter_model):
        return None
    return OpenAICompatibleProvider(
        name="openrouter", base_url="https://openrouter.ai/api/v1", model=settings.chat_openrouter_model,
        api_key=settings.openrouter_api_key, extra_body={"reasoning": {"exclude": True}},
        headers={"HTTP-Referer": settings.frontend_url, "X-Title": "Jobify"}, **_common())


def _hf() -> ChatProvider | None:
    if not (settings.hf_token and settings.chat_hf_model):
        return None
    return OpenAICompatibleProvider(name="hf", base_url="https://router.huggingface.co/v1",
                                    model=settings.chat_hf_model, api_key=settings.hf_token, **_common())


def _custom() -> ChatProvider | None:
    if not (settings.chat_custom_base_url and settings.chat_custom_model):
        return None
    return OpenAICompatibleProvider(name="custom", base_url=settings.chat_custom_base_url,
                                    model=settings.chat_custom_model, api_key=settings.chat_custom_api_key,
                                    **_common())


PROVIDERS = {
    "echo": lambda: EchoProvider(settings.chat_echo_delay_ms),
    "ollama": _ollama,
    "openrouter": _openrouter,
    "hf": _hf,
    "custom": _custom,
}


def get_chat_provider() -> ChatProvider:
    names = [n.strip().lower() for n in (settings.chat_provider or "echo").split(",") if n.strip()] or ["echo"]
    unknown = [n for n in names if n not in PROVIDERS]
    if unknown:
        raise ChatProviderError(f"Unknown CHAT_PROVIDER '{unknown[0]}'. Available: {', '.join(sorted(PROVIDERS))}")
    chain = [p for p in (PROVIDERS[n]() for n in names) if p is not None]
    if not chain:
        raise ChatProviderError("No AI model is configured on the server.")
    return chain[0] if len(chain) == 1 else FallbackProvider(chain)


def build_prompt(history: list[Message], mode: str, max_turns: int = 20, context: str = "") -> list[Message]:
    """System prompt for the mode (+ the user's profile facts) + the most recent turns."""
    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["ask"])
    if context:
        system += "\n\n" + context
    return [{"role": "system", "content": system}, *history[-max_turns:]]
