# CLAUDE.md: NEXUS / Job Finder + Jobify

Agent and contributor context. Auto-loaded by Claude Code every session, so keep it dense, current, and true. Human-facing overview and run steps are in `README.md`. **These two files are the only docs in this repo.** Don't create new `.md` docs. Update this file when architecture, rules, or the MVP state changes, and put per-module rationale in module docstrings.

---

## 1. Hard rules (apply to every task)

**NEVER**
- Auto-apply, auto-send email, or post to any social platform without explicit user approval. `AUTO_SEND_EMAILS=false` stays the default.
- Scrape LinkedIn, X, or Google result pages directly, or automate a social account. Lead search uses official key-based APIs only (Google CSE, Serper).
- Invent experience, metrics, company facts, or comp numbers. Everything traces to `data/resume.txt`, `config/profile.yml`, or `config/target_companies.yml`.
- Hardcode candidate data in code. Read it from config.
- Recommend applying to roles that score below 50%.
- Put a secret in a `VITE_*` variable, or commit `.env*`, keys, or personal data.
- Use free-form application statuses (see §3).

**ALWAYS**
- Read `config/profile.yml` + `data/resume.txt` before evaluating fit or writing outreach. Cite resume lines when justifying a score.
- Regenerate `data/applications.md` (`python -m src.tracker`) after any status change.
- New API routes: require auth by default and filter every query by the current user (§6).
- Validate with the smallest relevant check: `python -m compileall src main.py`, the targeted `pytest` file, and `npm run check` in `jobify/`.
- Keep diffs to one concern each. Don't refactor business logic unless asked.

---

## 2. `/nexus` command routing

| Command | Action |
|---|---|
| `/nexus` / `/nexus help` | Show this table |
| `/nexus tracker` | `python -m src.tracker`, then show `data/applications.md` |
| `/nexus status <id> <Status>` | `python -m src.tracker --update <id> <Status>`, then regenerate |
| `/nexus pipeline` | Process `data/pipeline.md` (§4) |
| `/nexus scan <query>` | `python -m src.cli scan "<query>"` |
| `/nexus verify` / `dedup` / `normalize` / `digest` | `python -m src.cli <same>` |
| `/nexus drafts` | `python -m src.cli drafts` (review queue; `send <id>` only after the user approves) |
| `/nexus deep <company>` | WebSearch the company's AI/eng strategy, open roles, and culture. Feed new signals via `SignalScoutAgent.ingest_signal()` |
| `/nexus agents [tier1]` | `python -m src.agents.orchestrator --stage daily [--tiers 1]`, then show `data/agent_run_report.md` |
| `/nexus leads` | `... --stage leads [--categories funding ats yc]` |
| `/nexus networker <co>` | `... --stage networker --company "<co>" [--jd "<text>"]` |
| `/nexus prep <co>` | `... --stage interview-prep --company "<co>" [--role "<title>"]` |
| `/nexus pitch <co>` | `... --stage pitch --company "<co>" [--jd "<text>"]` |
| `/nexus mock <co>` | `... --stage interview-questions --company "<co>" [--num-questions 5]` |
| `/nexus negotiate <co> <lpa>` | `... --stage negotiate-counter --company "<co>" --offer <lpa>` (benchmark only: `negotiate-benchmark`) |
| `/nexus learn` | `... --stage weekly-learning` |

`...` = `python -m src.agents.orchestrator`.

---

## 3. Domain model

**Tracker statuses (canonical, CLI + `data/applications.md`):** `Ready` · `Outreach` · `Applied` · `Replied` · `Interview` · `Offer` · `Rejected` · `Skip`

**Lifecycle state machine (`src/lifecycle.py`, API):** `saved → ready → applied → interview → offer → negotiation → accepted`. `rejected` can be reached from any active stage and is terminal.
- `applied` only after proof is logged (`POST /api/applications/{id}/proof`). External actions are never silently marked as done.
- `negotiation → accepted` requires explicit UI confirmation.
- "Do This Next" returns exactly one action per opportunity: `GET /api/action-queue`, `POST /api/opportunities/{job_id}/do-next`, `GET /api/opportunities/{job_id}/brief`, `POST /api/applications/{id}/transition`.

**Jobify Kanban stages:** `applied, interview, offer, rejected, ghosted`. These are not the same as the backend vocab, so the mapper must translate (§6).

**Fit rubric** (used by `/nexus pipeline` and `agent_03_fit_scorer.py`, deterministic):

| Role match | Career level | Tech stack | Remote/location | Company stage | Growth | Comp vs target |
|---|---|---|---|---|---|---|
| 25% | 15% | 20% | 10% | 10% | 10% | 10% |

Score 0–100. **≥65% = worth applying**, <50% = never recommend.

---

## 4. `/nexus pipeline` procedure

1. Read `data/pipeline.md` and take the rows whose Status is empty or `pending`.
2. For each URL: fetch the JD (WebFetch, or Playwright if needed), then score it with §3 against the resume and profile.
3. Report company, role, match %, matched skills (with resume citations), gaps, and a recommendation.
4. Summarise the count processed and the top 3 by fit. **Don't apply or send anything.** Surface the results for the user.

---

## 5. Architecture map

```
Job sources (JobSpy, Adzuna, Careerjet, USAJobs, ATS boards, Firecrawl)
  → src/scrapers/            raw listings
  → src/job_processor.py     AI match scoring + content generation
  → src/email_engine/, src/email_discovery.py      contact email discovery
  → src/contact_intelligence/                      decision-maker graph ranking (PageRank)
  → src/personalization/     company research, HookGenerator, EmailComposer
  → src/outreach/            timing, A/B, follow-up scheduler (draft → approve → send)
  → src/feedback/            hook-type / send-hour learning
  → data/applications.md     human-readable tracker
```

| Concern | Where |
|---|---|
| App bootstrap, most routes | `main.py` (FastAPI, lifespan, CORS ~L920, router includes) |
| Routers | `src/api/routers/*.py`, `src/vc_intelligence/api.py`, crawler, sidekick, nextraise, workday, startups_gallery |
| Auth | `src/auth/dependencies.py` (Clerk RS256 via JWKS + auto-provision, HS256 legacy, `require_admin`, `is_public_path`), `jwt_handler.py`, `crypto.py` |
| Settings | `src/config.py`. `env`, `database_url` (default SQLite `jobs.db`), `cors_origins`, `frontend_url`, `clerk_*`, `default_signup_credits=50`, `auto_send_emails=False`; the default `jwt_secret_key` is blocked when `ENV=production` |
| Models / DB | `src/models.py` (`User.clerk_user_id` exists), `src/database.py`, `alembic/` (only `b4686927ddeb_initial_schema`) |
| Billing / credits | `billing_router.py` + `billing_service.py` (Stripe; webhook paths also reserved for Dodo), `credit_service.py` (`CREDIT_COSTS`, `SELECT … FOR UPDATE`) |
| AI providers | `src/ai/unified_ai_service.py`: cascade Ollama → Gemini → OpenAI/Anthropic/Groq. Ollama isn't available on PaaS |
| Background | `src/tasks.py`. Procfile: `api`, `worker` (concurrency 4), `beat` (exactly one), `flower` :5555 (internal only) |
| CLI | `src/cli.py`: tracker, verify, dedup, normalize, digest, pipeline, drafts, send, skip, status, scan, process-async, vc-seed-100, vc-scrape-*, vc-cron |
| Deploy | `Dockerfile`, `docker-compose{,.dev,.prod}.yml` (postgres, redis, api, celery_worker/beat/flower, telegram_daemon, frontend, ollama), `render.yaml`, `fly.toml` |
| CI | `.github/workflows/deploy-frontend.yml`, `security-scan.yml`. No backend test CI yet |

### Agent layer (`src/agents/`)

Contract: `AgentContext` in, `AgentResult{ok, summary, data, warnings}` out (`base.py`). Every agent falls back to a labelled result when keys or network are missing, and none raises. Each one can run standalone: `python -m src.agents.agent_NN_name`. HTTP: `/api/agents/*` (`agents_router.py` → `src/services/agents_service.py`). The orchestrator only writes `data/agent_run_report.md` and `data/agent_state.db`.

| # | Agent | Key behaviour |
|---|---|---|
| 1 | SignalScout | Funding/IPO/leadership signals from `target_companies.yml`; hot <45d, stale >180d; `ingest_signal()`; no web scraping |
| 2 | ATSHunter | Probes public Greenhouse/Lever/Ashby JSON boards by slug; 403/404 is silent |
| 3 | FitScorer | The §3 rubric, deterministic, no LLM |
| 4 | ResumeTailor | Re-ranks profile differentiators by JD overlap; LLM polishes wording only and never adds facts |
| 5 | ContactMapper | Wraps `contact_intelligence`; skips Tier 3 by default; 7-day cache |
| 6 | OutreachComposer | Feeds the exact signal into `HookGenerator`/`EmailComposer`; falls back to a template |
| 7 | PriorityScheduler | fit + signal decay (30d half-life) + tier boost + learned multiplier; **daily cap 8** |
| 8 | InterviewPrep | Manual, on `Interview` status; dossier from signals + `CompanyResearcher` (7d cache) + industry heuristics |
| 9 | FeedbackStrategist | Tests whether Tier 1 really out-converts Tier 2/3; `MIN_SAMPLE_SIZE=5`, `DAMPENING=0.5`; writes `tier:N` multipliers |
| 10 | ChallengeSolver | Only publicly evidenced challenges (JD pain points via `jd_analyzer`, else signal type); proof points traceable to the resume |
| 11 | QueryHunter | 30 queries from `boolean_queries.yml` via CSE/Serper → `boolean_leads` table (`new→reviewed→converted`); with no key it just prints the queries |
| 12 | Influencer | LinkedIn/X drafts only, never posts |
| 13 | Pitcher | WIN one-pager composed from #10/#4 output; warns when generic |
| 14 | Interviewer | Stateless `generate_questions()` / `score_answer()` (STAR regex + specificity, optional LLM) |
| 15 | Negotiator | Uses only `comp_benchmark_inr_lpa` + profile comp; anchor between your floor and the company max; with no benchmark it uses a labelled +12% fallback |
| 16–26 | Interviewer profiler, proof-of-work "fabricator", anti-ghosting SLA, frontier-AI radar, reverse headhunter, geo-arbitrage, web3 bounties, exec decision memo, system-design whiteboard, exec outreach drip, architecture sandbox | **Experimental.** Not wired into orchestrator stages or `/api/agents/*`; only `tests/test_sprint{1..6}_features.py` exercise them. Audit each against §1 before using or shipping. #17 and #25 (and #16's interviewer profiling) carry the highest risk of fabrication or spam |

Orchestrator stages: `daily`, `interview-prep`, `weekly-learning`, `leads`, `networker`, `pitch`, `interview-questions`, `negotiate-benchmark`, `negotiate-counter`.

### Sources of truth (read before generating content)

`data/resume.txt` · `config/profile.yml` · `config/target_companies.yml` · `config/boolean_queries.yml` · `data/applications.md` · `data/pipeline.md`. All of these are personal data: never paste them into public artifacts, logs, or commits.

---

## Production MVP (Jobify)

Goal: ship **Jobify** (`jobify/`, copied from `devnoid1/Jobify` @ `89b2570` on 2026-11-05, without history) as the only UI on this FastAPI backend. `frontend/` and `extension/` are being retired (§9).

### 6. Jobify frontend rules

- Stack: React 19, Vite 8, Tailwind 4, React Router 7, `@clerk/react`, Motion, Lucide. TypeScript entry `src/main.tsx`; the rest is mostly `.jsx`. Node 22. Deploys to Vercel (`vercel.json`: SPA rewrite, security headers, report-only CSP).
- Routes: `/` marketing · `/signin` (Clerk) · `/plans` → `/checkout` · `/demo/{chat,jobs,applications,founders,portfolio}` (no auth, fixtures) · `/app/{…}` (Clerk session).
- **Integration seam = `jobify/src/services/*.js`** (application, auth, chat, founder, job, newsletter, portfolio). Pages import services only, never `mocks/` or `fetch`.
- `import.meta.env` is read **only** in `src/config/env.js`. `hasApi` is true when `VITE_API_BASE_URL` is set.
- Server calls go through `src/lib/apiClient.js` (sends `Authorization: Bearer <Clerk JWT>`, throws `ApiError{status, code, message}`). Call `getToken()` on every request and never cache it. 401 → sign-in; 402 → `CREDITS_REQUIRED` → "Choose a plan".
- Wiring a service: keep its exported names and return shapes. Swap the mock body for `api(...)`, but keep `mode === "demo" || !hasApi ? mock : api(...)` (**`/demo` must never call the API**). Put backend↔UI field mapping in `src/services/mappers/*.js`, then delete the matching `src/mocks/*.js` once it's unused.
- Env: `VITE_CLERK_PUBLISHABLE_KEY`, `VITE_API_BASE_URL`, `VITE_NEWSLETTER_ENDPOINT`, `VITE_SUPPORT_EMAIL`. Vite bakes these in at build time, so a change needs a redeploy.

### 7. Backend state (verified in code, 2026-11-05)

| Area | State | Gap |
|---|---|---|
| Clerk auth | Session token has no email by default → users stored as `user_…@clerk.user`. Add `{"email": "{{user.primary_email_address}}", "name": "{{user.full_name}}"}` under Clerk → Sessions → Customize session token. ✅ `get_current_user` verifies RS256 via JWKS (`CLERK_ISSUER` / `CLERK_JWKS_URL`), auto-provisions `User` with signup credits; **fails closed when JWKS isn't configured**; `azp` checked against `CLERK_AUTHORIZED_PARTIES`; `dev_token_admin` needs `ALLOW_DEV_AUTH_TOKENS=true`. ✅ Svix-verified webhook `POST /api/auth/webhook/clerk` | Webhook skips verification when `CLERK_WEBHOOK_SECRET` is unset outside production. Test helper: `clerk_auth` fixture in `tests/conftest.py` |
| Route protection | ✅ `enforce_auth_unless_public` is an **app-level dependency**: every route needs a token unless `is_public_path()` allows it | New public routes (e.g. Gmail OAuth callback) must be added to `is_public_path`. Admin-only actions still need `require_admin` |
| Default admin | ✅ Fixed 2026-11-05: `init_db` used to seed `admin@jobfinder.ai` / `admin123` superuser on every startup, and `/api/auth/login` is public. Now opt-in (`SEED_DEV_ADMIN` + `DEV_ADMIN_PASSWORD`, never production); login refuses `admin123`; `require_admin` = `is_superuser` only | Any DB started before this fix contains that user: delete it or set a new password | `multi_tenant_enabled=True` by default. Only with `MULTI_TENANT_ENABLED=false` and `ENV≠production` do anonymous requests act as the first/admin user | Never deploy with `MULTI_TENANT_ENABLED=false` |
| Credits top-up | ✅ `/api/auth/credits/topup` now `require_admin` | It credits the **caller** (`user.id`), not a target user. Fix it before admins rely on it |
| CORS | ✅ Production: only `CORS_ORIGINS` + `FRONTEND_URL`. Elsewhere: those plus any `localhost`/`127.0.0.1` port (the old any-origin regex with credentials is gone; regression test in `test_groundwork_contract_auth.py`) | Staging must list its exact frontend origin in `CORS_ORIGINS` |
| Tenant isolation | `user_id` column on Application, Contact, CreditTransaction, MailboxAccount, OutreachRecord, Resume, TelegramConnector (checked via `__table__.c`). `scoped()` in `src/api/contract.py` raises on models without it | No `user_id`: CandidateProfile/Experience/Project, InboundRecruiterMessage, XOAuthToken, OutreachFunnelEvent, TargetCompanyRecord, PortfolioChatLog. Add it before exposing these per-user. Job/VC tables are shared catalogs: per-user state goes in join tables |
| Migrations | ✅ `b4686927ddeb` regenerated as a full baseline (26 tables, `alembic check` clean); compose runs `alembic upgrade head` | Existing create_all DBs: run `alembic stamp head` once. One new revision per phase |
| Mailbox / Gmail | **Simulated**: hard-coded `candidate@gmail.com`, `/simulate-inbound` | Real Google OAuth (`gmail.readonly`, encrypted refresh token, Celery sync); remove simulate in production |
| Chat | ✅ Phase 6: conversations CRUD + SSE send; `CHAT_PROVIDER` chain (echo · ollama · openrouter · hf · custom) via one OpenAI-compatible adapter. Verified live with local Ollama qwen3:8b | Production provider/key not chosen; replies not grounded in the user's profile yet; agent tools; side effects need a second confirm call |
| Portfolio | ✅ Phase 5: draft/publish/regenerate; public `GET /api/portfolio/{username}` serves the publish-time snapshot only | No hosted public page yet (the API returns JSON; Jobify has no `/p/:username` route). Legacy RAG `portfolio_router` unmounted |
| Billing | Stripe only; backend plans free/$29/$59/$99 vs Jobify $5/$8 | One plan catalog served by `GET /api/billing/plans`; idempotent webhooks; webhook-only entitlement |
| Response shape | ✅ All errors → `{error:{code,message,…}, detail}` (402 → `CREDITS_REQUIRED`); `paginate()` → `{items,total,page,pageSize}`; `scoped()` tenant filter (all in `src/api/contract.py`) | Per-feature mappers to the Jobify field names |
| Legal/risk surface | Anti-bot scraping (stealth/camoufox/nodriver), email permutation, Common Crawl email mining, Workday/NextRaise auto-apply, founder email harvesting, `sidekick-desktop` "screen-share invisible" interview HUD | Keep out of the SaaS image/product until reviewed (ToS, GDPR/DPDP, anti-spam) |

### 8. Screen → endpoint map

| Jobify screen / service | Backend today | Needed |
|---|---|---|
| Sign in · `authService` | Clerk verification ✅, `/api/auth/me` (credits_balance) | `/me` returns user + plan + credits; retire password register/login for customers |
| Jobs · `jobService` (`workModes, types, countries, skills, minSalaryUsd, maxYears, matchOnly, sort`) | `GET /api/jobs` (page, limit, search, region, experience_level, years_of_experience, date_posted, tech_stack, source, has_remote, sort_by/order), `GET /api/jobs/{id}` | Param mapper; per-user match % from CandidateProfile; `user_jobs` saved/applied. "Mark applied" only records it and never submits to the employer |
| Applications · `applicationService` | `/api/kanban/board`, `/cards`, `PATCH /cards/{id}/stage`, `/next-action`, `/email-provenance` | Card CRUD, notes, interview events, offer fields, stage-vocab mapping; "ghosted" after 30 days of silence via Celery beat |
| Founders · `founderService` | `/api/vc/*` | search/country/industry/hiringOnly filters; per-user **unlock** that debits credits; emails returned only after unlock |
| Chat · `chatService` | ✅ `/api/conversations` (Phase 6, echo stub) | Real model; outreach returns a draft for approval |
| Portfolio · `portfolioService` | ✅ `/api/portfolio` (Phase 5) | Public page renderer |
| Plans/Checkout | `/api/billing/plans`, `create-checkout-session`, `create-portal-session`, `webhook` | Real redirect, webhook-driven plan, subscription UI |
| Credits counter | `/api/auth/me`, `/credits/history`, `CREDIT_COSTS` | The server decides cost; the UI refetches after a spend and never decrements locally |

### 9. MVP plan: backend conforms to Jobify (decided 2026-11-05)

**Principle:** the frontend is the spec. `jobify/docs/INTEGRATION.md` and the return shapes in `jobify/src/services/*.js` define the API, and the backend changes to match. Frontend changes are limited to swapping service bodies to `api(...)` (keeping the `/demo` mock branch) and removing "simulated" labels once a feature is real.

**Decisions:** existing `/api/*` routes are **replaced** in place (`VITE_API_BASE_URL=https://<host>/api`) · `frontend/` and `extension/` are **retired**, so their routes can be reshaped or deleted freely · payments via **Dodo** (merchant of record, which handles GST/tax) at **Jobify `plans.js` prices** (Basic $5/500 credits, Pro $8/1,500) · Jobs/Founders data = **everything currently in the DB** (legal review is the user's accepted risk, so flag it, don't block) · **real Gmail OAuth in the MVP** · Chat LLM provider **deferred**.

**Cross-cutting: ✅ done 2026-11-05** (global auth, fail-closed Clerk + `azp`, contract envelope/`paginate`/`scoped`, credit costs, Alembic baseline, `clerk_auth` test fixture, `.env.example`). Tests: legacy endpoint tests run single-tenant via an autouse fixture in `tests/conftest.py`; Jobify-phase tests must use `clerk_auth`. 22 tests were failing before this work and still fail (not caused by it). Original checklist for reference:
- Global auth: wire `enforce_auth_unless_public` as an app-level dependency and keep `is_public_path` as the allow-list. Add an `azp` check. Add `CLERK_*`, `DODO_*`, `GOOGLE_OAUTH_*`, `TOKEN_ENCRYPTION_KEY` to `.env.example`.
- Contract helpers in `src/api/contract.py`: `paginate()` → `{items,total,page,pageSize}`, plus an exception handler mapping every `HTTPException`/validation error to `{error:{code,message}}` (402 → `CREDITS_REQUIRED`).
- Tenant helper `scoped(query, Model, user)`. Every new route uses it, and pytest asserts user A can't read or write user B's rows.
- One credit table in `credit_service.CREDIT_COSTS`: `chat_message=5`, `founder_unlock=5` (matching `ChatPage.CREDIT_COST` and `mocks/founders.UNLOCK_COST`). The server debits; the UI refetches `/me/subscription`.
- Alembic: baseline the current models, then one migration per phase. Remove `migrate_database.py || true`.
- Test auth: inject a fake JWKS via `set_clerk_jwks_client()` in a pytest fixture.

| Phase | Jobify contract (paths under `/api`) | Backend work (reuse → new) | Size |
|---|---|---|---|
| **1. Me + Jobs** ✅ 2026-11-05 (`src/api/routers/jobify_router.py`, `src/services/jobify_jobs.py`, `tests/test_jobify_phase1.py`; frontend: `jobService.js`, `JobsPage.jsx`, `AppProvider.jsx`, `apiClient.isLive()`). Extra routes the UI needs: `GET /me/jobs/state`, `GET/PUT /me/profile` (matching profile on `CandidateProfile`, edited from the Jobs page; `profileService.js`). `/applied` only flags the job; the card comes from `POST /applications` (Phase 2), as `JobsPage.apply()` does. Match % is 0 until the user saves a profile (the Jobs page prompts for it). **Known gap:** list scoring scans the newest `MAX_SCAN_ROWS=2000` rows | `GET /me`, `GET /me/subscription`; `GET /jobs?q&workModes&types&countries&skills&matchOnly&minSalaryUsd&maxYears&sort&page&pageSize`, `GET /jobs/:id`, `PUT /me/jobs/:id/saved`, `POST /me/jobs/:id/applied` | `User`/`get_current_user` → `Subscription` mapper (`subscription_tier`→`basic\|pro\|null`, status, `credits_balance`, `renewsAt`). `Job` → `toJob` mapper (`workMode`, `type`, `postedDaysAgo`, `skills[]`, `responsibilities[]`). Per-user `match` from `CandidateProfile` vs job, deterministic, in one function. **New** `user_jobs(user_id, job_id, saved_at, applied_at)`. `applied` also creates an `Application(stage=applied, source="jobs")`. Delete the old `/api/jobs*` handlers in `main.py` | M |
| **2. Applications** ✅ 2026-11-05 (`src/api/routers/jobify_applications_router.py`, `src/services/jobify_applications.py`, `tests/test_jobify_phase2.py`, migration `f9feca078a08`; frontend `applicationService.js` live/mock + error handling in `ApplicationsPage.jsx`). Events/offer stored as JSON (the UI replaces them wholesale), not a separate table. Ghosted: Celery beat `sweep_ghosted_applications` daily 03:15. `kanban_router` left in place (legacy, not used by Jobify). Gmail methods still simulated → Phase 3 | `GET/POST /applications`, `PATCH/DELETE /applications/:id` | `Application` (has `kanban_stage`, `email_subject`, `recruiter_*`). **Add** `company`, `position`, `notes`, `offer_salary`, `offer_deadline`, `source`, and make `job_id` nullable. **New** `application_events(id, application_id, title, at)`. Map stages to `applied\|interview\|offer\|rejected\|ghosted`. Celery beat marks `ghosted` after 30 days with no inbound mail. Retire `kanban_router` | M |
| **3. Gmail (real)** ✅ code 2026-11-05, live OAuth pending Google client (`src/services/gmail_sync.py`, `src/api/routers/jobify_gmail_router.py`, `tests/test_jobify_phase3.py`, migration `2d3379e61ccd`; hourly beat `sync_gmail_mailboxes`). Only messages matching the user's own applications are stored; email moves cards forward only. Legacy `/api/mailbox` unmounted (unscoped matcher let one user move another's cards) | `GET /gmail`, `POST /gmail/connect` → `{url}`, `POST /gmail/sync`, `DELETE /gmail` | Google OAuth web flow, scope `gmail.readonly`; public `GET /api/gmail/callback` with a signed `state`. Fernet-encrypt the refresh token in `MailboxAccount`. `sync` = Celery task → `InboundRecruiterMessage` → classify → advance cards (record provenance). `DELETE` revokes the token and purges bodies. Delete `/simulate-inbound` and the hard-coded `candidate@gmail.com`. **External:** Google Cloud project, consent screen in *Testing* mode (≤100 test users) until verification/CASA | L |
| **4. Founders** ✅ 2026-11-06 (`src/api/routers/jobify_founders_router.py`, `src/services/jobify_founders.py`, `tests/test_jobify_phase4.py`, migration `bd61bb92804c`; frontend `founderService.js` live/mock, `FoundersPage.jsx` facets/async state). Extra routes: `GET /founders/facets`, `GET /me/founders/state`. Country derived from ccTLD/VC focus (else "Unknown"); hiring = open job in catalog with the same company name. Emails only for unlocked companies; unlock charges `CREDIT_COSTS["founder_unlock"]` once, concurrent duplicates refunded. **Data:** `python -m src.cli founders-import` (idempotent, `src/vc_intelligence/import_founder_data.py`) loads every repo dataset: VC batch catalog + enrich_50 (344 cos / 681 founders, 102 VCs), startups.gallery founders (64 real; 314 placeholders skipped) and companies (1,369 with location/funding/jobs), registries (~415) → ~1,980 companies, ~741 founders, deduped by domain. **All scraped emails are pattern guesses** (`first.last@domain`): `email_verified=False` (API still returns `emailVerified:false`; the card shows the email without a label, per product decision 2026-11-06); companies without founders show "Founders not on file yet" and can't be unlocked (409 `NO_FOUNDERS`) | `GET /founders?q&country&industry&hiringOnly&page&pageSize`, `PUT /me/founders/:id/saved`, `POST /founders/:id/unlock` | `PortfolioCompany` + `CompanyFounder` → `Company{…, hiring, founders[{id,name,initials,role,linkedin,x}]}`. **The list never includes emails.** **New** `founder_unlocks(user_id, company_id)` (unique) and `user_saved_founders`. Unlock = one transaction: `deduct_credits(founder_unlock)` with `FOR UPDATE` → insert unlock → return contact fields. Unlocking again is free and idempotent | M |
| **5. Portfolio** ✅ 2026-11-07 (`src/api/routers/jobify_portfolio_router.py`, `src/services/jobify_portfolio.py`, `tests/test_jobify_phase5.py`, migration `7c1e5a9d2b40`; frontend `portfolioService.js` live/mock, async load + errors in `PortfolioPage.jsx`). Drafts are lenient (limits only) so autosave never drops edits; publish is strict (name required, http(s) links only) and snapshots into `published_content`. Unpublish keeps the username claimed. No leading/trailing hyphen (subdomain). Regenerate only fills empty fields / appends missing items from `CandidateProfile` + experiences/projects. Legacy `portfolio_router` (RAG chat auto-seeded a personal profile publicly) is unmounted; `tests/test_portfolio_rag.py` mounts it on a standalone app | `GET/PUT /portfolio`, `POST /portfolio/publish {username}`, `DELETE /portfolio/publish`, `GET /portfolio/username-available?name=`, `POST /portfolio/regenerate` | **New** `portfolios(user_id unique, username unique nullable, status draft\|published, content JSON, updated_at)`. Username `^[a-z0-9-]{3,24}$` plus reserved words. Declare the static paths before `/{username}`. Public `GET /portfolio/{username}` serves published content only. `regenerate` builds deterministically from `CandidateProfile`/`CandidateProject` until the LLM is chosen | S–M |
| **6. Chat** ✅ 2026-11-07, echo stub (`src/api/routers/jobify_chat_router.py`, `src/services/jobify_chat.py`, `src/services/chat_providers.py`, `tests/test_jobify_phase6.py`, migration `7f9a78797b89`; frontend `chatService.js` live/mock, `apiClient.apiStream`, streaming render in `ChatPage.jsx`). SSE events: `user` · `delta {text}` · `done {message, creditsCharged}` · `error {code, message, refunded}`; pre-stream errors (402/404/422/503) are JSON. Charged on accept; refunded only if the provider fails before any text; Stop keeps the charge and stores the partial as `status=stopped`. Streaming writes use a fresh session (`get_session_factory`), not the request session. Provider = `ChatProvider` protocol; `CHAT_PROVIDER` is a fallback chain (moves on only before any text). `OpenAICompatibleProvider` covers Ollama/OpenRouter/HF/Qwen/Kimi/MiniMax/NIM; reasoning deltas and `<think>` blocks are never shown; Ollama gets `reasoning_effort=none` (reasoning tokens otherwise eat `max_tokens` → empty replies). System prompts forbid invented experience/metrics (placeholders instead) | `GET/POST /conversations`, `PATCH/DELETE /conversations/:id`, `POST /conversations/:id/messages {content, mode: ask\|agent}` (streamed, abortable) | **New** `conversations(id, user_id, title, mode, updated_at)` and `messages(id, conversation_id, role, content, usage, created_at)`. SSE response that stops on client disconnect. Debit `chat_message` per send. A `ChatProvider` protocol with an **echo/stub provider until the LLM decision**. Agent mode may only return drafts (never sends). First match the stream format `chatService.send` expects | M |
| **7. Payments (Dodo)** | `POST /checkout/session` (name, email, phone, country, address, business/GSTIN, plan, interval, currency, discount) → `{url}`; plans catalog | Extend the existing Dodo code in `billing_service.py`. Server-side plan catalog = `plans.js` values (confirm yearly prices). Hosted checkout URL. Verify the signature on `POST /api/billing/webhook/dodo`. **New** `payment_events(provider_event_id unique)` for idempotency. Webhook alone sets `subscription_tier/status/renewsAt` and grants credits (`CreditTransaction`). Handle `past_due`/`cancelled`. Remove the unused Stripe path once Dodo is live | M |
| **3b. Jobify inbox** ✅ 2026-11-06 (free; primary tracking path) | `GET /inbox`, `GET /inbox/messages[?applicationId]`, `GET /inbox/messages/:id`, `POST /inbox/messages/:id/reply`; public `POST /api/inbound/email` | Every user gets `name.xxxx@INBOX_DOMAIN` (`src/services/jobify_inbox.py`, `src/api/routers/jobify_inbox_router.py`, `tests/test_jobify_inbox.py`, migration `20fe69d7d131`). Shared ingest with Gmail in `src/services/mail_ingest.py`. All inbox mail is stored (job-only address); unauthenticated senders never move cards; reply-only, user-clicked, `INBOX_DAILY_SEND_LIMIT`. Frontend: `inboxService.js`, `InboxPanel.jsx`, address + Inbox button on Applications | S–M |

**Why 3b exists:** Gmail read access (`gmail.readonly`) is a Google *restricted* scope. Without paid annual CASA verification ($675–$5,400/yr, 4–12 wks) the OAuth app stays in Testing: 100 manually-added users, refresh tokens expire every 7 days. Phase 3 code is kept for when verification is affordable; the Jobify inbox needs no Google approval.

**Jobify inbox setup (one-time, developer):**
1. Add the domain to Cloudflare (free plan) → Email → Email Routing → enable for a subdomain such as `mail.yourdomain.com` (Cloudflare adds the MX/SPF records).
2. `cd infra/cloudflare/inbox-worker`, set `INBOUND_URL` in `wrangler.toml` to `https://<api host>/api/inbound/email`, then `npx wrangler deploy` and `npx wrangler secret put INBOUND_WEBHOOK_SECRET` (same value as the API `.env`).
3. Email Routing → Routes → **Catch-all** → action *Send to a Worker* → `jobify-inbox`.
4. API `.env`: `INBOX_DOMAIN=mail.yourdomain.com`, `INBOUND_WEBHOOK_SECRET=...`. Replies: `INBOX_SMTP_HOST/PORT/USERNAME/PASSWORD` from any SMTP provider (Brevo/Resend free tiers); verify `INBOX_DOMAIN` with that provider (SPF/DKIM) so replies aren't spam-foldered.
5. On the first live delivery, check the stored message's `sender_verified`: it depends on Cloudflare passing `Authentication-Results`/`ARC-Authentication-Results` headers. If they're absent, verification falls back to `None` (cards still move) — revisit before launch.

**Order and parallelism:** cross-cutting → 1 → 2 → {3, 4, 5} in any order → 7 → 6 once the LLM is decided. (Phase 8 cleanup/launch dropped from the MVP plan on 2026-11-05.) Gmail (3) has external lead time (Google project + consent screen), so start that setup on day one.

**Still open (ask, don't assume):** Chat LLM provider (user prefers free Hugging Face / Qwen / Kimi / MiniMax; Ollama available locally) · Jobify yearly prices and currency handling (USD only vs INR display) · owner of the Google Cloud and Dodo accounts (need test keys).

**Production target:** Jobify on Vercel (Clerk *production* instance on an owned domain) · slim API image without Playwright (scrapers in a separate worker image) · Celery worker + one beat · managed Postgres (backups/PITR) + Redis · Sentry + PostHog · secrets in the platform store · Flower and `/metrics` kept private.

---

## 10. Gotchas

- `401 Invalid Clerk token`: wrong `CLERK_ISSUER`/JWKS, or a dev/prod Clerk instance mismatch between Jobify and the API.
- 401 after about a minute: the client cached the Clerk token. Call `getToken()` on every request.
- `/signin` blank on Vercel: `VITE_CLERK_PUBLISHABLE_KEY` wasn't set at build time. Set it and redeploy.
- Works on SQLite but fails on Postgres: develop against compose Postgres; SQLite is lax about types and JSON.
- Celery tasks never run: worker/beat not started, or wrong `REDIS_URL`.
- Chat replies empty with a qwen3/thinking model: reasoning consumed `max_tokens`. Disable thinking for that provider (`reasoning_effort: none` on Ollama).
- Local Ollama on CPU is slow (qwen3:8b ≈ 10–30 s to first token here). Use `qwen3:1.7b` for quick dev loops.
- LLM calls fail in production: there's no Ollama on PaaS, so set `GEMINI_API_KEY` plus a fallback.
- Root `.gitignore` has Python `lib/`; `!jobify/src/lib/` re-includes Jobify's lib. Check `git status --ignored jobify` after adding Jobify folders.
- Importing `main` runs a `startups_gallery` seed insert against `DATABASE_URL` (noisy SQL errors on import). Pre-existing; isolate tests with `dependency_overrides[get_db]`.
- PowerShell 5.1 `Get-Content` misreads UTF-8 (em-dashes print as `â€”`). Pass `-Encoding utf8`; the files themselves are fine.
- `main.py` is 6.6k lines. Search it with `Grep`; don't read it whole. Splitting it into routers is a planned refactor, so don't do it ad hoc.
