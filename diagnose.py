#!/usr/bin/env python3
"""
diagnose.py — Run this to identify the exact cause of health check failures.

Usage (from your project root):
    cd /Users/kushalljain/Desktop/job-finder
    python diagnose.py
"""

import asyncio
import importlib
import inspect as _inspect
import os
import sys
import traceback

try:
    import httpx
except ImportError:
    httpx = None

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env loaded")
except ImportError:
    print("⚠️  python-dotenv not installed — reading OS environment directly")


# =============================================================================
# 1. Environment variable audit
# =============================================================================

def check_env():
    print("\n" + "═"*62)
    print("  1. ENVIRONMENT VARIABLES")
    print("═"*62)

    keys = {
        "GEMINI_API_KEY":  ("Gemini AI",              "https://aistudio.google.com/apikey"),
        "GMAIL_ADDRESS":   ("SMTP sender email",       None),
        "GMAIL_PASSWORD":  ("Gmail App Password",      "https://myaccount.google.com/apppasswords"),
        "GOOGLE_SHEET_ID": ("Google Sheets (optional)","https://sheets.google.com → copy ID from URL"),
    }

    for key, (label, url) in keys.items():
        val = os.getenv(key, "")
        if val:
            masked = val[:5] + "..." + val[-2:] if len(val) > 7 else "***"
            print(f"  ✅  {key:<22}  {masked}  ({len(val)} chars) [{label}]")
        else:
            print(f"  ❌  {key:<22}  NOT SET  [{label}]")
            if url:
                print(f"       → {url}")


# =============================================================================
# 2. Package versions
# =============================================================================

def check_packages():
    print("\n" + "═"*62)
    print("  2. INSTALLED PACKAGES")
    print("═"*62)

    for pkg in ["google.genai", "google.generativeai", "google.api_core", "google.auth", "httpx"]:
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, "__version__", "?")
            if pkg == "google.generativeai":
                print(f"  ⚠️  {pkg:<35} {ver}  ← DEPRECATED, uninstall:")
                print(f"       pip uninstall google-generativeai -y && pip install google-genai")
            else:
                print(f"  ✅  {pkg:<35} {ver}")
        except ImportError:
            if pkg == "google.generativeai":
                print(f"  ✅  {pkg:<35} not installed (correct)")
            else:
                print(f"  ❌  {pkg:<35} NOT INSTALLED")
                if pkg == "google.genai":
                    print("       → pip install google-genai")


# =============================================================================
# 3. Inspect ALL exception classes in google.genai.errors
# =============================================================================

def inspect_genai_errors():
    print("\n" + "═"*62)
    print("  3. google.genai EXCEPTION CLASS NAMES")
    print("     (used to fix the error atlas in email_outreach.py)")
    print("═"*62)

    try:
        from google.genai import errors as _e
        classes = [(n, c) for n, c in _inspect.getmembers(_e, _inspect.isclass)
                   if issubclass(c, BaseException) and c is not BaseException]
        if classes:
            print("  Available exception classes:")
            for name, cls in sorted(classes):
                print(f"    {name}")
        else:
            print("  ❌ No exception classes found in google.genai.errors")
    except ImportError as exc:
        print(f"  ❌ Cannot import google.genai.errors: {exc}")
        print("     → pip install google-genai")


# =============================================================================
# 4. Live Gemini test — shows EXACT exception type
# =============================================================================

async def test_ollama_mistral():
    """Test Ollama + Mistral — the primary AI path for this project."""
    print("\n" + "═"*62)
    print("  4. LOCAL LLM TEST (Ollama + Mistral)")
    print("═"*62)

    if httpx is None:
        print("  ❌ httpx not installed")
        print("  → Install: pip install httpx")
        return

    base_url = "http://localhost:11434"
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            resp = await c.get(f"{base_url}/api/tags")
    except Exception as exc:
        print(f"  ❌ Ollama not running: {exc}")
        print("  → Install: curl -fsSL https://ollama.com/install.sh | sh")
        print("  → Then:    ollama pull mistral")
        return

    if resp.status_code != 200:
        print(f"  ❌ Ollama returned HTTP {resp.status_code}")
        return

    models_raw = resp.json().get("models", [])
    full_names = {m["name"] for m in models_raw}
    by_base    = {}
    for m in models_raw:
        base = m["name"].split(":")[0]
        if base not in by_base or "latest" in m["name"]:
            by_base[base] = m["name"]

    print(f"  ✅ Ollama running at {base_url}")
    print(f"  Installed models: {sorted(full_names) or '(none)'}")

    # Resolve which model will be used (mirrors local_llm_service.py logic exactly)
    _PRIORITY = ["mistral:latest", "mistral:7b", "mistral", "llama3.2:3b", "llama3.2:1b"]
    env_pref  = os.getenv("OLLAMA_MODEL", "")
    candidates = ([env_pref] if env_pref else []) + _PRIORITY

    resolved = None
    for candidate in candidates:
        if candidate in full_names:
            resolved = candidate; break
        base = candidate.split(":")[0]
        if base in by_base:
            resolved = by_base[base]; break

    if not resolved:
        print(f"  ❌ No supported model installed")
        print(f"  → Run: ollama pull mistral")
        return

    print(f"  ✅ Will use model: {resolved}")
    if "mistral" in resolved:
        print("  ✅ Mistral — best quality for job extraction and cover letters")

    # Live generation test — asks Mistral to extract a job as JSON
    print(f"  Testing structured extraction (JSON output)...")
    prompt = ('Extract job info as JSON only: '
              '"Python Developer at TechCorp in Bangalore. Apply at https://techcorp.com/jobs/123" '
              'Return: {"title":"...","company":"...","location":"...","url":"..."}')
    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(f"{base_url}/api/generate", json={
                "model":  resolved,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 150, "temperature": 0.2},
            })
        if r.status_code == 200:
            response_text = r.json().get("response", "")
            print(f"  ✅ Generation OK | response: {response_text[:200]}")
            import re as _re, json as _json
            m = _re.search(r"\{.*?\}", response_text, _re.DOTALL)
            if m:
                try:
                    parsed = _json.loads(m.group())
                    print(f"  ✅ JSON valid — keys: {list(parsed.keys())}")
                except Exception:
                    print("  ⚠️  JSON parse failed — model warming up, run again")
            else:
                print("  ⚠️  No JSON in response — try: ollama run mistral \'hello\'")
        else:
            print(f"  ❌ HTTP {r.status_code}: {r.text[:200]}")
    except Exception as exc:
        print(f"  ❌ Request failed: {exc}")


async def test_gemini():

    print("\n" + "═"*62)
    print("  5. GEMINI API TEST (optional — Mistral is your primary AI)")
    print("═"*62)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        print("  ❌ GEMINI_API_KEY not set — cannot test")
        return

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    print(f"  Key: {api_key[:8]}... ({len(api_key)} chars)")
    print(f"  Model: {model}")
    print("  Sending: 'Say: ok'")

    try:
        from google import genai
        from google.genai import types as genai_types

        client = genai.Client(api_key=api_key)

        def _call():
            return client.models.generate_content(
                model=model,
                contents="Say: ok",
                config=genai_types.GenerateContentConfig(max_output_tokens=5),
            )

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, _call)
        print(f"  ✅ SUCCESS — response: {repr(resp.text)}")

    except Exception as exc:
        # ── THIS IS THE KEY OUTPUT ─────────────────────────────────────────────
        # Copy the class name shown here and add it to _build_error_atlas()
        full_class = f"{type(exc).__module__}.{type(exc).__name__}"
        print(f"\n  ❌ FAILED")
        print(f"  ┌─ Exception class (add this to error atlas): ────────────")
        print(f"  │  {full_class}")
        print(f"  └─────────────────────────────────────────────────────────")
        print(f"  Message: {exc}")
        print()
        print("  Full traceback:")
        print("  " + "─"*58)
        # Indent the traceback
        tb_lines = traceback.format_exc().splitlines()
        for line in tb_lines:
            print(f"  {line}")
        print("  " + "─"*58)

        # Known fixes by exception name
        name = type(exc).__name__
        fixes = {
            "AuthenticationError":   "GEMINI_API_KEY is invalid.\n  → https://aistudio.google.com/apikey → create new key → update .env",
            "PermissionDeniedError": "Key lacks permission.\n  → Enable API: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com",
            "NotFoundError":         f"Model '{model}' not found.\n  → Use: gemini-2.0-flash or gemini-1.5-flash\n  → Set GEMINI_MODEL=gemini-2.0-flash in .env",
            "ResourceExhaustedError":"Rate limit hit (free: 15 req/min).\n  → Wait 60s and retry.",
            "ClientError":           "4xx error — bad request or invalid key format.\n  → Check GEMINI_API_KEY has no quotes or spaces in .env",
            "APIError":              "Generic API error.\n  → Check message above for HTTP status code.",
            "ValueError":            "Bad config value.\n  → GEMINI_API_KEY may be empty. Check .env: GEMINI_API_KEY=AIza... (no quotes)",
        }
        if name in fixes:
            print(f"\n  FIX for {name}:")
            print(f"  {fixes[name]}")
        else:
            print(f"\n  ⚠️  '{name}' is not in the fix database.")
            print(f"  Copy the class name above and share it so we can add the right fix.")


# =============================================================================
# 5. Google Sheets guide
# =============================================================================

def check_sheets():
    print("\n" + "═"*62)
    print("  6. GOOGLE SHEETS")
    print("═"*62)

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    if sheet_id:
        print(f"  ✅ GOOGLE_SHEET_ID set: {sheet_id[:24]}...")
        print("  If sheets still fail, share the sheet with your service account email.")
    else:
        print("  ℹ️  GOOGLE_SHEET_ID not set — this is OPTIONAL.")
        print("  All data falls back to logs/dead_letter.json (no data loss).")
        print()
        print("  To enable Sheets:")
        print("  1. https://console.cloud.google.com/iam-admin/serviceaccounts → Create")
        print("  2. Download JSON key → save as credentials/sheets.json")
        print("  3. https://console.cloud.google.com/apis/library/sheets.googleapis.com → Enable")
        print("  4. Create a sheet at https://sheets.google.com")
        print("  5. Share it (Editor) with the service account email")
        print("  6. Add to .env:")
        print("       GOOGLE_SHEET_ID=<id-from-url>")
        print("       GOOGLE_CREDENTIALS_PATH=credentials/sheets.json")


# =============================================================================
# Main
# =============================================================================

async def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  JOB FINDER DIAGNOSTIC — finds the exact cause of failures  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    check_env()
    check_packages()
    inspect_genai_errors()
    await test_ollama_mistral()
    await test_gemini()
    check_sheets()

    print("\n" + "═"*62)
    print("  NEXT STEP")
    print("═"*62)
    print("  Copy the exception class name from section 4 above.")
    print("  • If Mistral passed: your AI stack is working — no Gemini key needed.")
    print("  • Share any error class names here for exact fixes.")
    print()


if __name__ == "__main__":
    asyncio.run(main())