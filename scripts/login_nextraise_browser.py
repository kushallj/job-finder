"""
scripts/login_nextraise_browser.py — Interactive Live NextRaise.ai OAuth Login & Token Extractor.

Launches a visible browser window, navigates to https://nextraise.ai,
allows you to sign in with Google (canaby007@gmail.com), and automatically
extracts the real session token, cookies, and headers into the database.
"""
import asyncio
import json
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from playwright.async_api import async_playwright
from src.database import db_session
from src.nextraise.models import NextRaiseConfigRecord, NextRaiseQuota


async def interactive_login():
    print("================================================================")
    print("🌐 NEXTRAISE.AI LIVE OAUTH INTERACTIVE LOGIN")
    print("================================================================")
    print("Launching visible browser window...")
    print("1. A browser window will open on your Mac screen at https://nextraise.ai")
    print("2. Click 'Sign In' / 'Sign In with Google' and log in with canaby007@gmail.com")
    print("3. The script will automatically capture your live auth session and save it.\n")

    async with async_playwright() as p:
        # Launch browser with anti-detection flags for Google OAuth
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
            "--no-sandbox",
        ]
        
        try:
            # Try launching with installed Chrome first for highest Google OAuth compatibility
            browser = await p.chromium.launch(headless=False, channel="chrome", args=launch_args)
        except Exception:
            # Fall back to default bundled Chromium
            browser = await p.chromium.launch(headless=False, args=launch_args)

        context = await browser.new_context(viewport=None)
        
        # Mask webdriver flag to prevent Google "browser not secure" blockage
        await context.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
        
        page = await context.new_page()

        captured = {
            "bearer_token": None,
            "session_cookies": {},
            "auth_user": None,
        }

        # Intercept live API requests
        async def on_request(request):
            headers = request.headers
            auth = headers.get("authorization") or headers.get("x-auth-token")
            if auth and ("nextraise" in request.url or "supabase" in request.url or "firebase" in request.url or "api" in request.url):
                if not auth.startswith("Basic") and len(auth) > 20:
                    captured["bearer_token"] = auth
                    print(f"🔑 [Live Intercept] Captured Authorization Token ({auth[:25]}...)")

        page.on("request", on_request)

        print("Navigating to https://nextraise.ai ...")
        try:
            await page.goto("https://nextraise.ai", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Navigation info: {e}")

        print("\n👉 Please sign in with your Google account (canaby007@gmail.com) in the browser window.")
        print("Waiting for login completion (listening for up to 300 seconds)...\n")

        login_successful = False

        for second in range(1, 301):
            await asyncio.sleep(1)
            
            # Check URL for logged-in indicators
            current_url = page.url
            is_in_app = any(path in current_url for path in ["/dashboard", "/app", "/jobs", "/tracker", "/profile", "/settings"])

            # Check cookies
            cookies = await context.cookies()
            auth_cookies = [
                c for c in cookies
                if any(k in c.get("name", "").lower() for k in ["auth", "token", "session", "sb-", "nextraise", "jwt"])
                and len(c.get("value", "")) > 15
            ]

            # Check LocalStorage
            try:
                storage_str = await page.evaluate("() => JSON.stringify(window.localStorage)")
                storage = json.loads(storage_str) if storage_str else {}
            except Exception:
                storage = {}

            # Detect auth token from storage
            token = captured["bearer_token"]
            if not token:
                for k, v in storage.items():
                    if any(term in k.lower() for term in ["sb-", "token", "auth", "session"]) and len(str(v)) > 20:
                        token = str(v)
                        break

            if (token or len(auth_cookies) > 0) and (is_in_app or second > 15 and (token or len(auth_cookies) >= 2)):
                cookie_dict = {c["name"]: c["value"] for c in auth_cookies}
                print(f"\n🎉 LIVE NEXTRAISE LOGIN DETECTED at {current_url}!")
                if token:
                    print(f"✅ Bearer Token: {token[:35]}...")
                print(f"✅ Captured {len(cookie_dict)} authentication session cookies.")

                # Store live credentials in database
                with db_session() as db:
                    cfg = db.query(NextRaiseConfigRecord).first()
                    if not cfg:
                        cfg = NextRaiseConfigRecord()
                        db.add(cfg)

                    cfg.account_email = "canaby007@gmail.com"
                    cfg.oauth_access_token = token or json.dumps(cookie_dict)
                    cfg.session_token = json.dumps(cookie_dict)
                    cfg.oauth_connected = True
                    cfg.daily_target = 300
                    cfg.mode = "instant_auto"

                    quota = db.query(NextRaiseQuota).first()
                    if not quota:
                        quota = NextRaiseQuota()
                        db.add(quota)
                    quota.daily_limit = 300
                    quota.active_tier = "nextraise_pro_unlimited"

                    db.commit()
                    db.refresh(cfg)
                    print(f"💾 NextRaise credentials for {cfg.account_email} saved to database!")

                login_successful = True
                print("\n================================================================")
                print("✅ NEXTRAISE OAUTH AUTHENTICATION COMPLETED SUCCESSFULLY!")
                print("================================================================")
                print("You can now close the browser window or continue using the dashboard.")
                await asyncio.sleep(4)
                await browser.close()
                return

        if not login_successful:
            print("⚠️ Login wait timeout reached. Closing browser.")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(interactive_login())
