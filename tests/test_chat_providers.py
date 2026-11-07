"""OpenAI-compatible chat provider, reasoning filtering, fallback chain, and config parsing."""

import asyncio
import json

import httpx
import pytest

from src.config import settings
from src.services import chat_providers as cp


def _sse(*chunks, done=True):
    lines = [": keep-alive", ""]
    for c in chunks:
        lines += [f"data: {json.dumps(c)}", ""]
    if done:
        lines += ["data: [DONE]", ""]
    return "\n".join(lines).encode()


def _delta(content=None, reasoning=None):
    d = {}
    if content is not None:
        d["content"] = content
    if reasoning is not None:
        d["reasoning"] = reasoning
    return {"choices": [{"index": 0, "delta": d}]}


def _provider(handler, **kw):
    return cp.OpenAICompatibleProvider(name=kw.pop("name", "t"), base_url="http://llm.test/v1", model="m",
                                       api_key=kw.pop("api_key", "k"), transport=httpx.MockTransport(handler), **kw)


def _collect(provider, messages=None):
    async def run():
        return [c async for c in provider.stream(messages or [{"role": "user", "content": "hi"}], mode="ask")]
    return asyncio.run(run())


def test_streams_content_drops_reasoning_and_captures_usage():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers.get("authorization")
        seen["url"] = str(request.url)
        return httpx.Response(200, content=_sse(
            _delta(content="", reasoning="secret plan"), _delta(content="Hello"), _delta(content=" there"),
            {"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 2}}))

    p = _provider(handler, extra_body={"reasoning_effort": "none"}, max_tokens=50)
    assert "".join(_collect(p)) == "Hello there"
    assert p.last_usage == {"prompt_tokens": 3, "completion_tokens": 2}
    assert seen["url"] == "http://llm.test/v1/chat/completions" and seen["auth"] == "Bearer k"
    assert seen["body"]["stream"] is True and seen["body"]["max_tokens"] == 50
    assert seen["body"]["reasoning_effort"] == "none" and seen["body"]["messages"][0]["content"] == "hi"


def test_inline_think_tags_stripped_even_when_split_across_chunks():
    def handler(request):
        return httpx.Response(200, content=_sse(_delta("<thi"), _delta("nk>hidden rea"), _delta("soning</th"),
                                                _delta("ink>Visible "), _delta("answer")))

    assert "".join(_collect(_provider(handler))) == "Visible answer"


def test_think_filter_keeps_text_that_only_looks_like_a_tag_prefix():
    f = cp.ThinkFilter()
    assert f.feed("a <") + f.feed("b") + f.flush() == "a <b"


@pytest.mark.parametrize("status,needle", [(401, "API key"), (404, "not found"), (429, "busy"), (500, "500")])
def test_http_errors_become_user_safe_provider_errors(status, needle):
    p = _provider(lambda r: httpx.Response(status, text="internal detail sk-secret"))
    with pytest.raises(cp.ChatProviderError) as exc:
        _collect(p)
    assert needle in str(exc.value) and "sk-secret" not in str(exc.value)


def test_unreachable_and_stream_error():
    def down(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(cp.ChatProviderError, match="unreachable"):
        _collect(_provider(down))

    p = _provider(lambda r: httpx.Response(200, content=_sse(_delta("par"), {"error": {"message": "overloaded"}})))
    with pytest.raises(cp.ChatProviderError, match="stopped with an error"):
        _collect(p)


def test_no_auth_header_without_key():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, content=_sse(_delta("ok")))

    _collect(_provider(handler, api_key=None))
    assert seen["auth"] is None


def test_fallback_moves_on_only_before_text():
    bad = _provider(lambda r: httpx.Response(429), name="free")
    good = _provider(lambda r: httpx.Response(200, content=_sse(_delta("from paid"))), name="paid")
    chain = cp.FallbackProvider([bad, good])
    assert "".join(_collect(chain)) == "from paid" and chain.name == "paid"

    partial = _provider(lambda r: httpx.Response(200, content=_sse(_delta("half"), {"error": {"m": 1}})), name="a")
    chain = cp.FallbackProvider([partial, good])
    with pytest.raises(cp.ChatProviderError):
        _collect(chain)  # text already streamed from "a": don't splice in another model

    chain = cp.FallbackProvider([bad, _provider(lambda r: httpx.Response(401), name="b")])
    with pytest.raises(cp.ChatProviderError, match="API key"):
        _collect(chain)  # last error surfaces


def test_config_chain(monkeypatch):
    monkeypatch.setattr(settings, "chat_provider", "openrouter, ollama")
    monkeypatch.setattr(settings, "openrouter_api_key", None)  # unconfigured -> skipped
    monkeypatch.setattr(settings, "chat_ollama_model", "qwen3:8b")
    p = cp.get_chat_provider()
    assert isinstance(p, cp.OpenAICompatibleProvider) and p.name == "ollama"
    assert p.extra_body["reasoning_effort"] == "none" and p.base_url == settings.chat_ollama_base_url

    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")
    monkeypatch.setattr(settings, "chat_openrouter_model", "qwen/some-model:free")
    p = cp.get_chat_provider()
    assert isinstance(p, cp.FallbackProvider) and [x.name for x in p.providers] == ["openrouter", "ollama"]
    assert p.providers[0].headers["X-Title"] == "Jobify"

    monkeypatch.setattr(settings, "chat_provider", "hf")
    monkeypatch.setattr(settings, "hf_token", None)
    with pytest.raises(cp.ChatProviderError, match="No AI model is configured"):
        cp.get_chat_provider()

    monkeypatch.setattr(settings, "chat_provider", "custom")
    monkeypatch.setattr(settings, "chat_custom_base_url", "https://dashscope-intl.example/compatible-mode/v1")
    monkeypatch.setattr(settings, "chat_custom_model", "qwen-plus")
    monkeypatch.setattr(settings, "chat_custom_api_key", "dk")
    p = cp.get_chat_provider()
    assert (p.name, p.model, p.api_key) == ("custom", "qwen-plus", "dk")

    monkeypatch.setattr(settings, "chat_provider", "")
    assert cp.get_chat_provider().name == "echo"
