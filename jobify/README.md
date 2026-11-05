# Jobify

Job search and application management SaaS. This repo is the **frontend**: a React app with a public marketing site and a signed-in product (Chat, Jobs, Applications, Founders, Portfolio, Plans, Checkout).

This README is the **merge and launch guide** for combining this frontend with the backend repo (`kushallj/job-finder`).
It lists what is done, what clashes, what is missing on each side, how to fix common problems, and what must happen before real users and real money touch the product.

> Backend analysed: `github.com/kushallj/job-finder`, latest commit `cc0a1ac5` (2026-11-02, "VC Portfolio Founder Intelligence Engine & Production Hardening (#14)"), 107 commits, 889 tracked files.
> Method: static reading of the code (routes, models, auth, billing, config, Docker, CI) plus `grep` counts. **I did not run the backend or its tests.** Anything marked *(verify)* is an inference that someone should confirm by running it.

Contents: [1 TL;DR](#1-tldr) · [2 Architecture](#2-architecture) · [3 Stack: claimed vs found](#3-stack-claimed-vs-actually-in-the-repo) · [4 P0 blockers](#4-p0-blockers-fix-before-anything-is-public) · [5 Integration map](#5-integration-map-frontend-screen--backend-endpoint) · [6 Auth (Clerk + FastAPI)](#6-authentication-clerk--fastapi) · [7 Billing and credits](#7-billing-plans-and-credits) · [8 Feature logic](#8-feature-logic-how-each-feature-should-behave) · [9 Missing: frontend](#9-whats-missing-frontend) · [10 Missing: backend](#10-whats-missing-backend) · [11 Troubleshooting](#11-troubleshooting-playbook) · [12 Merge plan](#12-how-to-merge-the-two-repos) · [13 Production setup](#13-production-architecture) · [14 Market-ready checklist](#14-market-ready-checklist) · [15 Roadmap](#15-roadmap) · [16 Run locally](#16-run-it-locally)

---

## 1. TL;DR

| Question | Answer |
|---|---|
| Is the frontend finished? | The UI is built and works against **local mock services** (`src/services/*`). No real API calls exist yet. |
| Is the backend finished? | It is large (about 170 routes in `main.py` plus routers) but **mostly unauthenticated**, partly simulated, and its auth/billing don't match this frontend. |
| What is the single biggest risk? | Public, unauthenticated routes that can send email, start crawlers and spend AI credits. See [§4](#4-p0-blockers-fix-before-anything-is-public). |
| What is the merge strategy? | Keep this frontend as the product UI. Keep Clerk for login. Make FastAPI verify Clerk tokens. Replace each file in `src/services/` with a real API call. One service at a time. |
| Can we launch now? | No. See [§14](#14-market-ready-checklist). |

**Decisions the team must make first** (everything else depends on them):

1. **Auth:** Clerk (recommended, already wired in this frontend) or the backend's own JWT? → [§6](#6-authentication-clerk--fastapi)
2. **Payments:** Stripe (what is coded) or Dodo / Razorpay / Cashfree (what was planned)? → [§7](#7-billing-plans-and-credits)
3. **Pricing:** frontend shows $5 / $8, backend has $29 / $59 / $99. Which is real? → [§7](#7-billing-plans-and-credits)
4. **Legal posture of scraping and auto-apply:** keep, cut, or replace with licensed data. → [§4](#4-p0-blockers-fix-before-anything-is-public), [§14](#14-market-ready-checklist)
5. **Which UI wins:** the backend repo ships its own React/MUI dashboard. → [§12](#12-how-to-merge-the-two-repos)

---

## 2. Architecture

```
                       ┌───────────────────────────────────────────────┐
  Browser              │  Frontend (this repo) · React 19 + Vite 8     │
  ──────────────────►  │  Marketing site + /app (signed in) + /demo    │
                       │  Auth UI: Clerk (@clerk/react)                │
                       └───────────────┬───────────────────────────────┘
                                       │ HTTPS · Authorization: Bearer <Clerk session JWT>
                                       ▼
                       ┌───────────────────────────────────────────────┐
                       │  API (kushallj/job-finder) · FastAPI          │
                       │  verifies Clerk JWT → maps to users row       │
                       │  routers: jobs, applications, founders(vc),   │
                       │  chat/agents, portfolio, billing, credits     │
                       └───┬───────────────┬──────────────┬────────────┘
                           │               │              │
                  PostgreSQL         Redis + Celery    External: Stripe (or Dodo/
                  (SQLAlchemy +      worker/beat       Razorpay), Gmail API, LLMs
                   Alembic)          (scrapers, sync)  (Ollama/Gemini/OpenAI…), email
```

Today the arrows from the browser to the API **do not exist yet**: the frontend reads `localStorage` fixtures through `src/services/*`.

### Frontend routes (this repo)

| Route | What | Auth |
|---|---|---|
| `/` | Marketing site (11 sections) | public |
| `/signin` (`/login` redirects here) | Clerk Sign in / Sign up tabs, `?redirect_to=` supported | public |
| `/signup` | redirects to `/plans` | public |
| `/plans` → `/checkout` | Plan choice and checkout **preview** | checkout needs login |
| `/demo/{chat,jobs,applications,founders,portfolio}` | Demo workspace, fixed demo user, sample data | none |
| `/app/{chat,jobs,applications,founders,portfolio}` | Real workspace, same components | Clerk session (UX guard only) |

### Repository layout

```
Jobify/
├── src/
│   ├── main.tsx            Entry: ErrorBoundary > ClerkProvider > App
│   ├── App.jsx             Route table (public site, /demo, /app, account flow)
│   ├── app/                Signed-in product: AppProvider (user, mode, plan, credits, toasts),
│   │                       DashboardLayout, ErrorBoundary, ui.jsx, pages/*
│   ├── components/         Marketing site sections + shared bits (ui/ = small primitives)
│   ├── services/           <- INTEGRATION SEAM. One file per domain; pages never touch storage or fetch
│   ├── mocks/              Demo fixtures used by services today. Delete a file when its service goes live
│   ├── data/               Static content/config: plans.js, siteContent.js, routes.js, images.js
│   ├── config/env.js       The only place that reads import.meta.env
│   ├── lib/                apiClient.js (fetch + Clerk JWT + ApiError), storage.js (demo-only), utils.js
│   ├── hooks/              Reusable React hooks
│   ├── styles/, index.css  Global styles / Tailwind entry
│   └── assets/images/      Image slot specs
├── public/                 Static files served as-is (robots.txt, assets/)
├── docs/INTEGRATION.md     Per-endpoint API contracts for the backend developer
├── .github/workflows/      CI: typecheck, build, npm audit
├── vercel.json             SPA rewrite, cache headers, security headers (CSP in report-only)
├── .env.example            Documented env vars (copy to .env.local)
├── .agents/, skills-lock.json   Clerk agent-skill docs (dev tooling only; not shipped)
└── SECURITY.md             Security rules and how to report issues
```

Conventions: pages import from `services/`, never from `mocks/`; secrets never go in `VITE_*` vars; `import.meta.env` is read only in `config/env.js`; new server calls go through `lib/apiClient.js`.

### How the backend developer plugs in (per service)

1. Set `VITE_API_BASE_URL`. `hasApi` in `src/config/env.js` becomes true.
2. Open a service (e.g. `src/services/jobService.js`) and keep its exported method names and return shapes (contract: `docs/INTEGRATION.md`).
3. Replace the mock body with `api("/jobs", { query })` from `src/lib/apiClient.js`. It already sends `Authorization: Bearer <Clerk JWT>` and throws `ApiError { status, code, message }`.
4. Keep the mock path for `/demo` (it must never call the real API), e.g. `mode === "demo" || !hasApi ? mock : api(...)`.
5. Delete the matching `src/mocks/*.js` fixtures and `localStorage` keys once nothing uses them.

Contracts for each service are in [docs/INTEGRATION.md](docs/INTEGRATION.md) and in the header comment of each service file.

---

## 3. Stack: claimed vs actually in the repo

The stack summary you shared does not fully match the code at `cc0a1ac5`. Wrong assumptions here cause wasted work, so fix the docs or the code.

| Area | Claimed | Found in code | Action |
|---|---|---|---|
| Framework | FastAPI 0.104.1, Uvicorn 0.24.0, Pydantic 2.5 | ✅ matches `requirements.txt` | Plan upgrades (these are late-2023 versions; check CVEs). |
| DB | SQLite dev, Postgres prod | ✅ SQLAlchemy 2.0.23, Alembic 1.13, asyncpg, psycopg2. **Only one Alembic migration** (`b4686927ddeb_initial_schema`) | Generate migrations for all later models. See [§11](#11-troubleshooting-playbook). |
| Queue | Celery + Redis + Flower | ✅ `Procfile`: api, worker (4), beat, flower :5555 | Protect Flower (it is an admin UI). |
| AI cascade | Ollama → Gemini → OpenAI/Anthropic/Groq | ✅ `src/ai/unified_ai_service.py` plus local/standalone services | Ollama cannot run on typical PaaS; in production the cascade effectively starts at Gemini. |
| **Auth** | not stated | **Custom HS256 JWT** (`src/auth/jwt_handler.py`), `/api/auth/register`, `/login`, bcrypt-style hashing in `crypto.py` | Frontend uses **Clerk**. Must reconcile. [§6](#6-authentication-clerk--fastapi) |
| **Payments** | "Dodopayment or Razorpay or Cashfree" | **Stripe only** (`billing_router.py`, `billing_service.py`, 52 files mention stripe). Razorpay/Cashfree matches are *company names in scrapers*, not payment code | Pick a provider. [§7](#7-billing-plans-and-credits) |
| **Email** | Mailjet | **No Mailjet code.** Providers are SMTP (Gmail), SendGrid, AWS SES | Add a Mailjet provider or change the plan. |
| **Metrics** | PostHog | **No PostHog integration.** 3 files match the word (scraped company names). `/metrics` is Prometheus | Add PostHog in the frontend and server events. |
| Scraping | Playwright, Selenium, BS4 | ✅ plus `playwright-stealth`, `camoufox`, `nodriver`, `curl-cffi` (anti-detection) and a "Common Crawl stealth miner" | Legal risk. [§4](#4-p0-blockers-fix-before-anything-is-public) |
| Frontend | not stated | The backend repo contains **its own** React 19 + MUI + zustand + react-query dashboard (175 files, 40+ endpoint modules, pages: Dashboard, Jobs, Contacts, Outreach, AgentsHub, Copilot…) | Two UIs now exist. [§12](#12-how-to-merge-the-two-repos) |
| Extras | not stated | Electron app (`sidekick-desktop`), browser extension, Telegram bot, Workday/NextRaise auto-apply, voice interviewer, n8n workflows, `.kiro`, `.idea`, `.claude` folders | Scope decision: ship, park, or delete. |

---

## 4. P0 blockers (fix before anything is public)

These are real findings from reading the code. Order is by danger.

### P0-1. Almost no endpoint requires login

Counts at `cc0a1ac5`:

| File | Routes | Auth dependency used |
|---|---|---|
| `main.py` | **169** | **0** |
| `agents_router.py` | 16 | 0 |
| `kanban_router.py` | 6 | 0 |
| `mailbox_router.py` | 5 | 0 |
| `portfolio_router.py` | 4 | 0 |
| `telegram_connector_router.py` | 7 | 0 |
| `crawler_router.py` (+ duplicate in main.py) | 5 | 0 |
| `jobs_router.py`, `stats_router.py` | 3 | 0 |
| `auth_router.py` | 5 | 4 |
| `billing_router.py` | 4 | 4 |
| `vc_intelligence/api.py` | 13 | 10 |

Only auth, billing and most VC routes are protected. `get_optional_current_user` returns `None` in production, so routes that use it still serve anonymous users.

**Dangerous examples (all anonymous):** `POST /api/outreach/send` (sends email from your SMTP account), `POST /api/fintech/auto-outreach`, `POST /api/crawler/start|stop`, `POST /api/providers/sync`, `POST /run-query`, `POST /api/resume/generate-ats` (spends LLM tokens), `POST /api/signalhire/callback`.

**Fix:** add a router-level dependency so new routes are secure by default:

```python
# main.py: protect everything, then explicitly allow-list public routes
from fastapi import Depends
from src.auth.dependencies import get_current_user   # now Clerk-backed, see §6

protected = dict(dependencies=[Depends(get_current_user)])
app.include_router(agents_router, **protected)
app.include_router(kanban_router, **protected)
app.include_router(mailbox_router, **protected)
# …every router. Public only: /health, /api/billing/webhook (signature-verified),
# GET /api/portfolio/{username} (public page), /api/billing/plans (catalog).
```

`main.py` itself needs its 169 routes moved into routers (it is 6,532 lines) so this can be applied once. Admin-only actions (crawler, provider sync, seed, outreach bulk) need `Depends(require_admin)`, not just login.

### P0-2. Anyone logged in can mint free credits

`POST /api/auth/credits/topup` adds up to 1000 credits per call, per its own docstring a *"Simulated credit top-up"*, behind only `get_current_user`. Call it in a loop and the credit meter and billing are meaningless.

**Fix:** delete the route (or gate it to `is_superuser`). Credits must only be added by (a) signup grant, (b) a verified payment webhook, (c) an admin action, each logged in `CreditTransaction`.

### P0-3. No per-user data isolation

Only these tables have a `user_id`: `Application`, `CandidateProfile`, `CreditTransaction`, `MailboxAccount`, `OutreachFunnelEvent`, `Resume`, `TargetCompanyRecord`, `TelegramConnector`, `XOAuthToken`. Tables such as `Contact` and `OutreachRecord` have none *(verify)*, and the unauthenticated routes don't filter by user anyway. Once login is enforced, every query must filter by the current user, otherwise user A reads user B's contacts and applications.

**Fix:** add `user_id` (indexed, non-null) to every per-user table, a migration to backfill, and a repository helper that *always* applies `.filter(Model.user_id == user.id)`. Add a test that logs in as user A and asserts user B's rows are invisible on every list/get/update/delete route.

### P0-4. Secrets and defaults

- `config.py` ships a default `jwt_secret_key = "job-finder-super-secret-production-key-2026-change-in-env"`. A startup validator blocks it when `env == production` (good), but anything running with `ENV=development` on the public internet is forgeable. Never run a public deployment with `ENV` unset.
- CORS: outside production it allows `allow_origin_regex = https?://.*` **with** `allow_credentials=True`. Staging environments exposed to the internet inherit that. Use an explicit allow-list in every deployed environment.
- Tracked `.claude/settings.json`, `.idea/`, `.kiro/` should not be in a product repo.
- Good: no key-shaped strings (`AIza…`, `sk_live_…`, private keys) were found in tracked files, and `.env*` is ignored. Run `gitleaks` over the **full git history** before going public (the history is 220 MB and 107 commits; old commits may differ).

### P0-5. Personal data in the repo

`config/profile.yml`, `config/profile_samta_jain.yml`, `data/resume.pdf`, `data/resume.txt`, `data_examples/*.csv` and commit history (for example "calibrate pipeline for 54yo homemaker Samta Jain") reference real-looking personal profiles. The latest commit says PII was sanitised, but the file names and history remain. Treat as a data-protection problem: remove from history (`git filter-repo`), confirm consent, and keep demo data obviously fake.

### P0-6. Legal and platform risk of the data pipeline

The repo includes anti-bot tooling (`playwright-stealth`, `camoufox`, `nodriver`), a "Common Crawl stealth miner" for email discovery, LinkedIn scraping (Proxycurl), email-guessing "permutations", a Workday / NextRaise auto-apply bot, and "Founders / decision makers" harvesting with emails. Selling this exposes the business to: job-board and LinkedIn terms-of-service breaches, GDPR / India DPDP Act violations (collecting and emailing personal data without a lawful basis), CAN-SPAM / anti-spam law, and account bans. **Decide before launch** which of these ship. Safer substitutes: licensed job APIs and partner feeds, user-supplied contacts, official Gmail OAuth, opt-in only.

Keep the existing safeguard `auto_send_emails = False` (human-in-the-loop). Do not remove it.

---

## 5. Integration map (frontend screen → backend endpoint)

"Gap" is what must change. Frontend service files are in `src/services/`.

| Screen | Frontend service | Backend today | Gap / action |
|---|---|---|---|
| **Sign in / up** | Clerk (`SignInPage.jsx`) | `/api/auth/register`, `/login`, `/me` (own JWT) | Backend must accept Clerk tokens; retire register/login. [§6](#6-authentication-clerk--fastapi) |
| **Plans / Checkout** | `data/plans.js` (static), `CheckoutPage` (simulated) | `GET /api/billing/plans`, `POST /create-checkout-session`, `/create-portal-session`, `POST /webhook` (Stripe) | Plans must come from the API; real checkout redirect; webhook-driven entitlement. [§7](#7-billing-plans-and-credits) |
| **Jobs** | `jobService` | `GET /api/jobs` (page, limit, search, region, experience_level, years_of_experience, date_posted, tech_stack, source, has_remote, sort_by/order), `GET /api/jobs/{id}` | Filter vocab differs. Frontend sends `workModes, types, countries, skills, minSalaryUsd, maxYears, matchOnly, sort`. Needs a mapper or new params. **Match %** and per-user **saved/applied** state don't exist on the backend. Response shape differs from `{items,total,page,pageSize}` *(verify)*. |
| **Mark applied / save** | `jobService.markApplied/toggleSaved` | `PUT /api/jobs/{id}/application`, `POST /api/applications/{id}/transition` | Add saved-jobs endpoint; align semantics. |
| **Applications board** | `applicationService` | `GET /api/kanban/board`, `/cards`, `PATCH /cards/{id}/stage`, `POST /cards/{id}/next-action`, `/email-provenance` | Create / update / delete / notes / interview events / offer fields are not exposed. Stage enum must match: frontend `applied, interview, offer, rejected, ghosted` *(confirm backend stage names)*. |
| **Gmail connect + sync** | `applicationService.connect/sync/disconnect` | `POST /api/mailbox/connect`, `GET /status`, `POST /sync`, `POST /simulate-inbound`, `GET /messages` | **Backend is simulated too**: `connect` is hard-coded to `candidate@gmail.com`. Real Google OAuth + Gmail API (read-only scope) is missing on both sides. [§8](#8-feature-logic-how-each-feature-should-behave) |
| **Founders** | `founderService` | `/api/vc/*` (VC firms, portfolio companies, founders, CSV export, regional filters, continuous scraper) | Closest match. Needs: search/country/industry/hiringOnly params, a **per-user unlock** endpoint that debits credits, saved companies. Founder emails must stay server-side until unlocked. |
| **Chat (assistant)** | `chatService` | `/api/agents/*` (daily, leads, networker, pitch, interview, negotiate, outreach-draft), `/api/portfolio/{username}/chat` | There is **no general chat endpoint** with conversations and messages. Needs `conversations` + `messages` tables and a streaming endpoint (SSE). Outreach must return a **draft** for approval, never send. |
| **Portfolio** | `portfolioService` | `GET /api/portfolio/{username}`, `/github-activity`, `POST /{username}/chat`, `POST /seed` | **Read-only public view.** Missing: edit/save draft, publish/unpublish, username availability, regenerate, resume parse. |
| **Credits counter** | `AppProvider.credits` (local) | `GET /api/auth/me` (`credits_balance`), `GET /credits/history`, `CREDIT_COSTS` in `credit_service.py` | Read credits from the API; frontend costs (chat 5, unlock 5) differ from backend `CREDIT_COSTS`. Server decides cost. |

### One rule for all integration work

Each frontend service keeps its **current function signatures**. Only the body changes:

```js
// before (src/services/jobService.js)  → reads fixtures
// after: calls the API and maps the response into the shape the UI already uses
import { api } from "../lib/api.js";
export const jobService = {
  async list(q) {
    const { data } = await api.get("/api/jobs", { params: toBackendParams(q) });
    return { items: data.jobs.map(toUiJob), total: data.total, page: q.page, pageSize: q.pageSize };
  },
};
```

Put request/response mapping in `src/services/mappers/*.js` so UI components never learn backend field names.

Suggested `src/lib/api.js` (attaches the Clerk session token):

```js
import axios from "axios";
export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL, timeout: 30000 });
api.interceptors.request.use(async (cfg) => {
  const token = await window.Clerk?.session?.getToken();   // short-lived; do not cache in localStorage
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});
api.interceptors.response.use(undefined, (err) => {
  if (err.response?.status === 401) window.Clerk?.redirectToSignIn();
  if (err.response?.status === 402) err.code = "CREDITS_REQUIRED";   // UI shows "Choose a plan / top up"
  return Promise.reject(err);
});
```

(Add `axios` to this repo's dependencies. The backend's frontend already uses it.)

---

## 6. Authentication: Clerk + FastAPI

### The clash

| | This frontend | Backend |
|---|---|---|
| Login | Clerk (Google + email) | `POST /api/auth/login` email + password, own hashing |
| Token | Clerk session JWT, **RS256**, short-lived | Own JWT, **HS256**, 7-day default (`jwt_access_token_expire_minutes = 10080`) |
| User id | `user_xxx` string | integer `users.id` |
| Verification | Clerk JWKS (public key) | shared secret `jwt_secret_key` |

`decode_access_token` hard-rejects anything that isn't HS256, so **a Clerk token will always fail with "Unsupported JWT algorithm: RS256"**. This is the first error you will see.

### Recommended: keep Clerk, verify its tokens in FastAPI

1. Add dependency: `PyJWT[crypto]`.
2. Env vars (server-only): `CLERK_ISSUER=https://<your-instance>.clerk.accounts.dev` (production: your own domain), `CLERK_AUTHORIZED_PARTIES=https://app.yourdomain.com,http://localhost:3000`.
3. Replace `get_current_user`:

```python
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from src.config import settings
from src.database import get_db
from src.models import User

bearer = HTTPBearer(auto_error=False)
_jwks = PyJWKClient(f"{settings.clerk_issuer}/.well-known/jwks.json", cache_keys=True)

def get_current_user(cred: HTTPAuthorizationCredentials = Security(bearer),
                     db: Session = Depends(get_db)) -> User:
    if not cred:
        raise HTTPException(401, "Authentication required")
    try:
        key = _jwks.get_signing_key_from_jwt(cred.credentials).key
        claims = jwt.decode(cred.credentials, key, algorithms=["RS256"],
                            issuer=settings.clerk_issuer, leeway=5,
                            options={"require": ["exp", "iat", "sub"]})
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"Invalid token: {e}")
    azp = claims.get("azp")
    if azp and azp not in settings.clerk_authorized_parties:      # blocks tokens minted for other origins
        raise HTTPException(401, "Token not issued for this app")
    user = db.query(User).filter(User.clerk_user_id == claims["sub"]).first()
    if not user:                                                   # first request after signup: auto-provision
        user = User(clerk_user_id=claims["sub"], email=claims.get("email", ""),
                    subscription_tier="free", credits_balance=settings.default_signup_credits)
        db.add(user); db.commit(); db.refresh(user)
    if not user.is_active:
        raise HTTPException(403, "Account deactivated")
    return user
```

4. Migration: add `users.clerk_user_id` (unique, indexed); make `hashed_password` nullable.
5. Better than auto-provision on first call: a **Clerk webhook** (`user.created`, `user.updated`, `user.deleted`, verified with Svix) to create, sync and delete users. Needed for account deletion (GDPR).
6. Remove or admin-gate `/api/auth/register` and `/login`.
7. Email is not in Clerk's default session token. Either add a custom claim in Clerk (Sessions → Customize session token) or fetch the user from Clerk's Backend API in the webhook. Don't trust an email sent by the client.

### Alternative: drop Clerk and use the backend's JWT
Possible, but you would then rebuild: Google login, password reset, email verification, rate limiting, bot protection. The backend's `register` has `min_length=6` passwords and no email verification. Not recommended for a product launch.

---

## 7. Billing, plans and credits

### Conflict: three different price lists

| Source | Plans |
|---|---|
| Frontend `src/data/plans.js` (demo) | Basic $5 (500 credits), Pro $8 (1,500 credits). Placeholder values, not confirmed pricing |
| Backend `billing_service.py` | free $0 (50 credits), starter $29 (300), pro $59 (1,000), unlimited $99 (9,999), credit packs 100 and 300 |
| Marketing site (`siteContent.js`) | Free and Pro, monthly/annual (Save 20%) |

**Decide one price list.** Then make the backend the **single source of truth**: `GET /api/billing/plans` returns it, and `PlansPage`, `CheckoutPage` and the marketing pricing section read from it (or from one shared config generated at build time). Frontend flags never grant access.

### Provider decision

The only coded provider is **Stripe**. For an India-first product that bills in INR with GST, consider Razorpay, Cashfree or Dodo Payments. Whatever you pick, build it behind an interface so the rest of the app doesn't care:

```python
class PaymentProvider(Protocol):
    def create_checkout(self, user, plan_id, interval, success_url, cancel_url) -> str: ...  # hosted URL
    def create_portal(self, user, return_url) -> str: ...
    def verify_webhook(self, payload: bytes, headers: dict) -> dict: ...
```

### Rules that make billing safe

1. **Webhook is the only thing that grants access.** Never trust the success redirect. On `checkout.completed` / `subscription.updated` / `subscription.deleted`, update `subscription_tier`, `subscription_status`, `current_period_end`, grant credits.
2. **Idempotent webhooks:** store the provider event id in a table with a unique constraint; ignore repeats. *(verify: `process_webhook_event` was not checked for idempotency.)*
3. **Server computes the price.** The frontend sends `plan_id` + `interval` + `currency` only.
4. **Server decides credit cost** (`CREDIT_COSTS`) and uses `SELECT … FOR UPDATE` (already done in `deduct_credits`). Frontend only displays the number.
5. **HTTP 402** from the API means "no credits / no plan". The frontend already shows a "Choose a plan" prompt; wire `err.code === "CREDITS_REQUIRED"` to it.
6. The `unlimited` tier currently bypasses deduction and writes `max(balance, 9999)`. Add fair-use limits and per-minute rate limits; "unlimited" with paid LLM calls is a cost risk.
7. India: GST invoices (18%), INR pricing, GSTIN capture for business purchases (the checkout screen has a "purchasing as a business" box that is not wired to anything).
8. Subscriptions need: cancel, upgrade/downgrade proration, failed-payment handling (`past_due` grace period), refunds policy, receipts by email.

---

## 8. Feature logic: how each feature should behave

Write these into the API contract so both sides build the same thing.

### Credits
- Signup grant (`DEFAULT_SIGNUP_CREDITS=50`), monthly refill by plan, optional packs.
- Every credit change writes a `CreditTransaction` (amount, balance_after, action, reference_id).
- Spend is atomic and server-side. If balance < cost → `402 {error:{code:"CREDITS_REQUIRED"}}`.
- Frontend shows `credits_balance` from `/me`; after a spend, refetch (don't decrement locally).

### Jobs
- List: server-side filter, sort, pagination, one response shape `{ items, total, page, pageSize }`.
- **Match %** is computed per user from `CandidateProfile` (skills, years, location) vs job (tech_stack, level). Define the formula in one place and document it; show it as "estimated match".
- Saved and Applied are per-user rows (`user_jobs`: user_id, job_id, saved_at, applied_at).
- "Mark as applied" **only records** the application in Jobify. It must not submit anything to the employer. Auto-apply (Workday / NextRaise) is a separate, opt-in, per-action-confirmed feature, if kept at all.
- Label demo or seed jobs as demo. Do not present scraped listings as verified.

### Applications (Kanban)
- Stages: `applied → interview → offer → rejected | ghosted`. A card moves by user drag or by an inbound-email rule. Ghosted = no reply for 30 days (a scheduled Celery beat task, not a frontend guess).
- Each stage change is stored with `actor` (user / email_rule), timestamp, and source message id (the backend's `email-provenance` field covers this).
- Frontend needs notes, interview events, offer details: add these fields or sub-resources.

### Gmail connection (does not exist for real yet)
1. Frontend button → `POST /api/mailbox/connect` returns a Google OAuth URL.
2. User consents with **read-only** Gmail scope (`gmail.readonly`); Google may require a security assessment (CASA) for restricted scopes before public launch. Plan time for this.
3. Callback stores an encrypted refresh token per user.
4. Celery task syncs recent messages, classifies them (applied / interview / offer / rejected), and advances Kanban cards.
5. States the UI already handles: `not_connected, pending, connected, syncing, failed, disconnected`. "Disconnect" must revoke the token and delete synced message bodies.
6. Remove `simulate-inbound` and the hard-coded address from production builds.

### Founders / outreach
- Browsing companies and founder names is free; **contact details are gated** behind "Unlock" (cost in credits, per user, recorded once).
- Server returns email only for unlocked founders. The frontend never has emails in the list payload.
- Outreach flow: *draft → user reviews and edits → explicit Send*. Server enforces it (`auto_send_emails=False`). Add per-user daily send caps, suppression list, unsubscribe link, and bounce handling. Without these, your sending domain will be blacklisted.
- Only use data you have a lawful basis to hold. See [P0-6](#p0-6-legal-and-platform-risk-of-the-data-pipeline).

### Chat
- Tables: `conversations(id, user_id, title, mode, updated_at)`, `messages(id, conversation_id, role, content, created_at, usage)`.
- Endpoints: list / create / rename / delete conversation; `POST /conversations/{id}/messages` streaming via SSE; client abort stops generation (the UI already has a Stop button using `AbortSignal`).
- "Agent" mode may *propose* actions (e.g. an email draft); executing any side effect needs a second confirm call.
- Cost: debit credits per message by tokens or flat; log model, tokens, latency.

### Portfolio
- `portfolios(user_id, username unique, status draft|published, content jsonb, updated_at)`.
- Endpoints: `GET/PUT /portfolio` (draft), `GET /portfolio/username-available?name=`, `POST /portfolio/publish`, `DELETE /portfolio/publish`, `POST /portfolio/regenerate`.
- Public page `GET /api/portfolio/{username}` returns only published content.
- Username rule used by the UI: 3 to 24 chars `[a-z0-9-]`; reserve words (`admin`, `jobify`, `www`, `api`…). Enforce uniqueness at the DB.
- Actually serving `username.yourdomain.com` needs wildcard DNS + a public renderer. Today the UI only simulates "published".

---

## 9. What's missing: frontend

| # | Item | Why it matters |
|---|---|---|
| F1 | Real API layer (`src/lib/api.js`) and service rewrites | Nothing talks to the backend yet |
| F2 | Error boundary and a consistent error/empty/offline UI for network failures | Services currently never fail |
| F3 | Auth edge cases: token refresh, expired session, sign-out everywhere | |
| F4 | Real subscription UI: current plan, renewal date, cancel, portal link, invoices | Checkout is a preview only |
| F5 | Onboarding: upload resume, set target roles/skills/location (feeds Match %) | Without a profile, match scores are meaningless |
| F6 | Outreach draft review and approve screen | Required by the "no auto-send" rule |
| F7 | Settings page (profile, email connection, notifications, delete account, export data) | Legal requirement (GDPR/DPDP) |
| F8 | Terms, Privacy, Cookie pages and consent banner (`/terms` is a stub) | Legal |
| F9 | Contact form backend (currently local only) and newsletter | |
| F10 | Analytics (PostHog) and error monitoring (Sentry) | Blind without them |
| F11 | Tests: unit (Vitest), component, and Playwright end-to-end for sign-in → plan → app | None exist in this repo |
| F12 | Accessibility audit (keyboard drag and drop alternative for Kanban, focus order, contrast) | Only spot-checked |
| F13 | Bundle size: main chunk about 640 kB; split Clerk and marketing sections | Speed |
| F14 | SEO and sharing: per-route titles, OG images, `sitemap.xml`, `robots.txt`, favicon (the favicon currently 404s) | Acquisition |
| F15 | Remove or clearly label demo data everywhere in the real `/app` | Trust |
| F16 | Real testimonials and logos (placeholders must not ship) | Claims must be true |
| F17 | i18n and currency handling beyond INR/USD | If targeting multiple markets |
| F18 | Responsive pass at 768, 1024 and 1280 widths | Only 1910 and 390 were visually checked |

## 10. What's missing: backend

| # | Item | Why it matters |
|---|---|---|
| B1 | Clerk token verification and `users.clerk_user_id` | [§6](#6-authentication-clerk--fastapi) |
| B2 | Auth on every route; admin guard on admin routes | [P0-1](#p0-1-almost-no-endpoint-requires-login) |
| B3 | Remove `/credits/topup` | [P0-2](#p0-2-anyone-logged-in-can-mint-free-credits) |
| B4 | Tenant isolation and tests | [P0-3](#p0-3-no-per-user-data-isolation) |
| B5 | Chat tables and streaming endpoint | None today |
| B6 | Portfolio write/publish/availability/regenerate | Only read exists |
| B7 | Real Gmail OAuth and sync | Mailbox is simulated |
| B8 | Job match scoring, saved/applied endpoints | |
| B9 | Founder unlock endpoint with credit debit | |
| B10 | Provider-agnostic payments, idempotent webhooks, one plan catalog | [§7](#7-billing-plans-and-credits) |
| B11 | Mailjet (or chosen) email provider, SPF/DKIM/DMARC, suppression and unsubscribe | Deliverability |
| B12 | Standard response/error envelope (`{items,total,page,pageSize}`, `{error:{code,message}}`); FastAPI default is `{detail}` | Lets the frontend handle errors uniformly |
| B13 | Rate limiting (per user and per IP), request size limits, abuse controls | |
| B14 | Alembic migrations for **all** models; stop using `migrate_database.py \|\| true` | [§11](#11-troubleshooting-playbook) |
| B15 | Split `main.py` (6.5k lines, 169 routes) into routers/services | Maintainability and B2 |
| B16 | Background jobs for sync, ghosted detection, credit refills (Celery beat) | |
| B17 | OpenAPI → typed client generation for the frontend | Removes contract drift |
| B18 | Observability: structured logs with request id (exists), Sentry, protected `/metrics`, uptime checks | |
| B19 | Account deletion and data export endpoints | GDPR / DPDP |
| B20 | Backups and restore drill for Postgres | |
| B21 | Dependency upgrades (FastAPI 0.104, aiohttp 3.9.1, etc. are old) and `pip-audit` in CI | Security |
| B22 | CI that runs backend tests, lint, type-check and the existing secret scan | Only a frontend deploy workflow and a security scan exist |
| B23 | Cut or isolate non-core modules (Electron, extension, Telegram, voice, Workday) from the SaaS API image | Smaller attack surface and image |

---

## 11. Troubleshooting playbook

| Symptom | Likely cause | Fix |
|---|---|---|
| `/signin` shows an empty panel on Vercel but works locally | `VITE_CLERK_PUBLISHABLE_KEY` not set at build (the `.env.local` file is git-ignored) | Vercel → Settings → Environment Variables → add it for Production + Preview → **Redeploy** (Vite bakes it at build). The page now shows an explicit warning when the key is missing. |
| API returns `401 Unsupported JWT algorithm: RS256` | Backend still using the HS256 decoder on Clerk tokens | Implement [§6](#6-authentication-clerk--fastapi). |
| `401` only after ~1 minute | Clerk tokens are short-lived; token cached in the client | Call `getToken()` per request (see `api.js`); never store it. |
| `401 Token not issued for this app` | `azp` claim not in `CLERK_AUTHORIZED_PARTIES` | Add the exact frontend origin (scheme + host + port). |
| Browser CORS error | Origin not in `CORS_ORIGINS` / `FRONTEND_URL`; or wildcard + credentials | Add exact origin. In production the regex fallback is off by design. Don't use `*` with credentials. |
| CORS error but only on errors | A 500 returned before CORS middleware headers | Fix the 500; check API logs. |
| `402 Payment Required` | No credits or no plan | Expected. Show "Choose a plan". Don't retry. |
| Webhook `Invalid signature` | Wrong `STRIPE_WEBHOOK_SECRET`; body parsed before verifying; proxy altering the body | Use the endpoint's own secret; verify raw bytes (the code does `await request.body()`). Test with the provider's CLI. |
| User paid but plan not updated | Webhook not reaching the API (firewall, wrong URL, not idempotent retry loop) | Check provider webhook delivery log; make handler idempotent. |
| `relation "x" does not exist` on Postgres | Only one Alembic migration exists; later models were created by ad-hoc scripts on SQLite | `alembic revision --autogenerate` against a clean Postgres, review, commit. Stop swallowing failures (`migrate_database.py \|\| true` in `docker-compose.yml` hides them). |
| Works on SQLite, fails on Postgres | SQLite is loose about types/booleans/`datetime`; JSON columns differ | Develop against Postgres (docker compose already provides it). |
| Celery tasks never run | Worker/beat not started; wrong `REDIS_URL`; Procfile has 4 processes | Run all four (`api`, `worker`, `beat`, `flower`) or equivalent services. |
| API image huge / slow cold start | Playwright + Chromium in the API image | Move scraping workers to a separate image; keep the API image slim. |
| LLM calls fail in production | Ollama is local-only; no Gemini key | Set `GEMINI_API_KEY` (and a fallback provider); set timeouts and retries; track spend. |
| Playwright fails on PaaS | Missing browser deps / sandbox | Use the Playwright base image; run scrapers as workers. |
| Frontend 404 on refresh at `/app/jobs` | SPA fallback missing | `vercel.json` rewrite exists (`/(.*)` → `/index.html`). If hosting elsewhere, add the same. |
| `/app` redirects to sign-in forever | Clerk session not loaded or key mismatch between frontend and backend instance | Both must use the same Clerk instance (dev with dev, prod with prod). |
| Dev keys on a live domain | Using `pk_test_` in production | Create a Clerk **production** instance on a domain you own (`*.vercel.app` is not eligible), then swap both keys. |
| Credits go negative or double-spend | Two concurrent requests | Keep `SELECT … FOR UPDATE`; add a DB check constraint `credits_balance >= 0`. |
| Emails land in spam | No SPF/DKIM/DMARC; sending from a personal Gmail | Use a transactional provider with a verified domain; warm up; add unsubscribe. |
| `Gmail connect` always shows the same address | Mailbox router is simulated | Implement [real OAuth](#gmail-connection-does-not-exist-for-real-yet). |

---

## 12. How to merge the two repos

Two repos, two frontends. Recommended layout (monorepo):

```
jobify/
├── apps/
│   ├── web/        ← this repo (Jobify product UI + marketing)
│   ├── api/        ← kushallj/job-finder backend (FastAPI)
│   └── admin/      ← optional: the backend repo's existing React/MUI dashboard, internal only
├── docker-compose.yml        # postgres, redis, api, worker, beat (flower optional, internal)
├── .github/workflows/        # web: build+test, api: test+lint+pip-audit+image, security scan
└── docs/                     # API contract (OpenAPI export), this README
```

Steps:
1. Create the monorepo; import both histories (`git subtree add --prefix=apps/web …`, `… apps/api …`) so blame is preserved.
2. Decide the fate of the backend's UI: **keep as `apps/admin`** for internal ops (crawler control, VC harvester), not customer-facing. Customers use `apps/web`.
3. Delete from `apps/api`: `.idea/`, `.claude/`, `.kiro/`, personal data files (see [P0-5](#p0-5-personal-data-in-the-repo)), and move Electron/extension/Telegram/n8n into `extras/` or their own repos.
4. Export the OpenAPI schema from FastAPI on each CI run; generate a typed client for `apps/web` (e.g. `openapi-typescript`). Contract drift then fails CI.
5. Integrate **one vertical slice at a time**, in this order (each ends with an end-to-end test):
   1. Auth (Clerk → `/api/me`) → shows real user + credits in the sidebar.
   2. Jobs list/detail.
   3. Applications board (+ Gmail later).
   4. Founders + unlock.
   5. Portfolio.
   6. Billing (plans, checkout, webhook, portal).
   7. Chat.
6. For each slice: write the endpoint → add auth + tenant filter + tests → rewrite the matching `src/services/*.js` → delete its fixtures → add a Playwright test.
7. Keep `/demo` working throughout (it uses fixtures and a fixed demo user; it is also your marketing "try it" page). Make sure the demo never calls the real API.

### Environment variables

| Variable | Where | Notes |
|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | web (build time) | Public. Must be set in Vercel. |
| `VITE_API_BASE_URL` | web (build time) | e.g. `https://api.yourdomain.com`. Empty = mock services |
| `CLERK_SECRET_KEY` | **server only** | Only if the API calls Clerk's Backend API. Never in a `VITE_` var. |
| `CLERK_ISSUER`, `CLERK_AUTHORIZED_PARTIES` | api | For JWT verification |
| `DATABASE_URL`, `REDIS_URL` | api, worker | Postgres + Redis |
| `JWT_SECRET_KEY` | api | Only needed if the old HS256 path is kept |
| `ENV=production`, `CORS_ORIGINS`, `FRONTEND_URL` | api | Exact origins only |
| `STRIPE_*` or chosen provider's keys | api | Plus webhook secret |
| `GEMINI_API_KEY` (+ fallbacks) | api, worker | |
| `SENTRY_DSN`, `POSTHOG_KEY` | web, api | Monitoring |

**Security note:** the Clerk secret key and a publishable key were shared in chat during development. Rotate the secret key in the Clerk dashboard before launch.

---

## 13. Production architecture

Suggested, cost-sensible layout for a first launch:

| Piece | Option | Notes |
|---|---|---|
| Frontend | Vercel (already configured) | Custom domain, preview deployments |
| API | Fly.io / Render / Railway / AWS ECS | Slim image (no Playwright). 2+ instances behind HTTPS, health check `/api/health` |
| Workers | Same platform, separate service | `celery worker` (+ `beat` as exactly **one** instance) |
| Postgres | Managed (Neon / Supabase / RDS) | Daily backups, PITR, tested restore |
| Redis | Managed (Upstash / Redis Cloud / Elasticache) | Broker + cache |
| Files | S3-compatible bucket | Resumes, generated PDFs; private, signed URLs |
| Email | Mailjet / SES / SendGrid | Verified sending domain, SPF/DKIM/DMARC |
| Auth | Clerk **production** instance | Needs your own domain; run `npx clerk@latest deploy --mode agent --domain <domain>` |
| Payments | Stripe or Razorpay/Dodo/Cashfree | Webhook URL on the API domain |
| Monitoring | Sentry + PostHog + uptime check + Prometheus/Grafana (optional) | Alerts to a real channel |
| Secrets | Platform secret store | Never in the repo or the image |

Container hygiene: pin Python 3.11, multi-stage build, non-root user, `pip install --require-hashes` or a lockfile, `pip-audit`, scan the image. Flower and `/metrics` must not be public.

---

## 14. Market-ready checklist

Check each box before taking real money.

### Product
- [ ] Every screen reads real data from the API; no demo or fixture data in `/app`.
- [ ] Onboarding collects the profile needed for matching.
- [ ] Job data comes from sources you are allowed to use (licensed APIs, partner feeds, or user-added). Listings link to the original posting.
- [ ] Core loops work end to end: sign up → pick plan → pay → add jobs → track applications → get an email-driven update.
- [ ] Empty states, errors, loading, offline handled everywhere.
- [ ] Support channel (email/chat), status page, in-app feedback.

### Security
- [ ] Every route authenticated; admin routes role-checked ([P0-1](#p0-1-almost-no-endpoint-requires-login)).
- [ ] Tenant isolation tests pass ([P0-3](#p0-3-no-per-user-data-isolation)).
- [ ] No free-credit endpoint ([P0-2](#p0-2-anyone-logged-in-can-mint-free-credits)).
- [ ] Secrets rotated; git history scanned (gitleaks/trufflehog); `.env*` never committed.
- [ ] Rate limiting, request size limits, bot protection on signup.
- [ ] Encrypted storage for OAuth refresh tokens; least-privilege Gmail scope.
- [ ] Dependency audit clean; images scanned; Dependabot on.
- [ ] Penetration test or at least an OWASP ASVS L1 review.

### Legal and compliance
- [ ] Terms of Service, Privacy Policy, Cookie policy, Refund policy published.
- [ ] GDPR + India DPDP Act: lawful basis, consent, data processing agreements, data export and deletion working.
- [ ] Anti-spam compliance for outreach (CAN-SPAM / CASL / PECR / India rules): sender identity, unsubscribe, suppression list.
- [ ] Scraping and auto-apply reviewed by counsel; third-party platform terms respected.
- [ ] Google OAuth app verification (restricted Gmail scope needs a security assessment).
- [ ] Payments: tax (GST) invoicing, correct entity and bank setup with the provider.
- [ ] Marketing claims and testimonials are true and attributable.

### Reliability
- [ ] Staging environment that mirrors production; CI deploys to it first.
- [ ] Automated tests in CI: backend unit/integration, frontend unit, Playwright end-to-end.
- [ ] Load test the hot paths (jobs list, chat, webhook).
- [ ] Backups and a tested restore; migration rollback plan.
- [ ] Alerting on error rate, latency, queue depth, failed webhooks, LLM spend.
- [ ] Runbook for incidents; on-call owner.
- [ ] Cost controls: per-user LLM budgets, rate limits, provider spend alerts.

### Growth
- [ ] Analytics events: signup, plan view, checkout start/success, first job tracked, Gmail connected, outreach approved.
- [ ] SEO basics, OG images, sitemap, blog or content plan.
- [ ] Email lifecycle: welcome, onboarding nudges, receipts, win-back.
- [ ] Pricing tested with real users; referral/waitlist before broad launch.
- [ ] Beta with a small group; measure activation and retention before paid acquisition.

---

## 15. Roadmap

Sizes: S = a few days, M = 1 to 2 weeks, L = 3+ weeks (one developer; adjust for your team). Owner: **FE** frontend, **BE** backend, **BOTH**.

| Phase | Goal | Work | Owner | Size |
|---|---|---|---|---|
| **0. Safety** | Nothing dangerous is public | P0-1 to P0-6; remove topup; lock admin routes; rotate secrets; clean repo | BE | M |
| **1. Foundation** | Frontend talks to backend | Monorepo; Clerk JWT verify; `users.clerk_user_id`; `api.js`; OpenAPI client; standard envelopes; Alembic for all models; CI | BOTH | M |
| **2. Core slices** | Real data in the app | Jobs, Applications (manual CRUD), Founders (+ unlock + credits), tenant isolation tests | BOTH | L |
| **3. Money** | Get paid safely | One plan catalog; provider choice; checkout redirect; idempotent webhooks; portal; GST invoices; settings/subscription UI | BOTH | M–L |
| **4. Differentiators** | Why users pay | Real Gmail OAuth + sync; chat with streaming; portfolio publish + public renderer; outreach approve-then-send | BOTH | L |
| **5. Hardening** | Trust and scale | Rate limits, Sentry/PostHog, load tests, backups, accessibility, SEO, legal pages, Google verification | BOTH | M |
| **6. Beta → launch** | Real users | Closed beta, fix top issues, pricing test, support, status page, then public launch | BOTH | M |

Parallelism: while BE does Phase 0 and 1, FE can finish F2, F5, F6, F7, F8, F11 and F13 (they don't depend on the API).

---

## 16. Run it locally

**Frontend (this repo)**
```bash
npm install
cp .env.example .env.local      # then set VITE_CLERK_PUBLISHABLE_KEY (+ VITE_API_BASE_URL later)
npm run dev                     # http://localhost:3000
npm run typecheck               # tsc --noEmit (CI runs this + build)
npm run check                   # typecheck + build
npm run build
```
- `/demo/*` works with no login. `/app/*` needs a Clerk session (create a test user in the Clerk dashboard; in development, the verification code for `+clerk_test` emails is `424242`).

**Backend (kushallj/job-finder)**
```bash
cp .env.example .env            # SQLite + mock providers run with zero keys
docker compose up               # postgres, redis, api (:8000), worker, beat
# or: pip install -r requirements.txt && uvicorn main:app --port 8000
```
Check `http://localhost:8000/api/health` and `http://localhost:8000/docs` (OpenAPI).

**Both together:** set `VITE_API_BASE_URL=http://localhost:8000` in the frontend and add `http://localhost:3000` to the backend `CORS_ORIGINS` (it already allows `:3000` and `:5173`).

### Frontend quality gates (current state)
- `tsc --noEmit` and `vite build`: passing.
- Visually checked at 1910 px and 390 px; signed-in flows exercised with a Clerk test user (sign-in with device verification, plan → checkout → simulated success, chat, jobs search/detail/mark applied, Gmail simulated connect/sync, publish).
- Not yet done: automated tests, accessibility audit, mid-width checks, Kanban drag-and-drop test, real API.

---

### Appendix: marketing site (original scope of this repo)

The public site follows this 11-section order: Header, Hero + product demo, Job Categories, How Jobify Works, Everything You Need, Pricing, Testimonials, FAQ, Contact, Final CTA, Footer. Stack: React 19, Vite 8, Tailwind CSS 4, React Router 7, Lucide, Motion, Bricolage Grotesque + DM Sans. Content lives in `src/data/siteContent.js` (fixtures in `src/mocks/`); testimonial and pricing copy there is placeholder and must be replaced with verified content before launch.
