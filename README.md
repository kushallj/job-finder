# Job Finder + Jobify

Job-search intelligence platform. **Job Finder** (this repo root) is the FastAPI backend: job discovery and scoring, application tracking, outreach drafting, startup/VC research, and a target-company agent layer. **Jobify** (`jobify/`) is the new customer-facing React frontend being taken to an MVP on top of it.

Human-in-the-loop by design: the system drafts, scores, and tracks. It never auto-applies, auto-sends email, or posts to social platforms without explicit approval.

> **Docs policy:** this repo has exactly two docs, this `README.md` (humans: what it is, how to run it) and [`CLAUDE.md`](./CLAUDE.md) (agents and contributors: rules, architecture, current state, MVP plan). Don't add more Markdown docs; extend one of these or put rationale in module docstrings.

## Layout

```text
job-finder/
├── main.py              FastAPI app (≈6.6k lines, ≈170 routes) + router composition
├── src/                 Backend: models, auth, routers, services, scrapers, agents
│   ├── jobify/          the product API: routers/ (one per screen) + services/ (business logic)
│   ├── api/             contract.py (envelope, paginate, scoped) + routers/ (ops, agents, auth, billing, legacy)
│   ├── services/        shared services (credits, billing, catalog runs, email classifier) + legacy
│   ├── agents/          core agents 1-15 + orchestrator.py
│   ├── experimental/    agents 16-26 + their services (unwired; audit before use)
│   ├── auth/            Clerk RS256 + legacy HS256 JWT verification
│   ├── company_sources/ registries/ (curated company lists) + miners/ (careers/contact miners)
│   ├── models.py        SQLAlchemy models    database.py  engine/session
│   ├── tasks.py         Celery tasks         cli.py       NEXUS CLI
│   └── config.py        Pydantic settings (reads .env)
├── jobify/              Product frontend: React 19, Vite 8, Tailwind 4, Clerk
├── frontend/            Legacy internal dashboard (being retired)
├── config/              profile.yml (personal, git-ignored), target_companies.yml, boolean_queries.yml
├── data/                resume.txt (personal, git-ignored), tracker, pipeline.md, agent_state.db
├── alembic/             migrations: baseline + one revision per Jobify phase
├── tests/               pytest suite (≈130 test files)
├── scripts/             one-off and ops scripts; dev/ has start.sh (API + Celery + Flower)
├── infra/               cloudflare/ (inbox worker), n8n/ (workflows), synology/ (NAS deploy)
├── docker/              per-service Dockerfiles used by docker-compose
├── extension/  sidekick-desktop/   non-core surfaces
├── docker-compose*.yml  Dockerfile  Procfile  render.yaml  fly.toml
└── README.md  CLAUDE.md
```

## Run locally

**Backend** (Python 3.11+)

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                 # SQLite + mock providers work with zero keys
python -m alembic upgrade head         # existing create_all DB: run `alembic stamp head` once first
python -m uvicorn main:app --reload --port 8000
```

API docs at http://localhost:8000/docs, health check at `/api/health`.

The full stack (Postgres, Redis, API, Celery worker/beat/flower, Ollama) runs with `docker compose up --build`.

**Jobify frontend** (Node 22)

```bash
cd jobify
npm install
copy .env.example .env.local           # set VITE_CLERK_PUBLISHABLE_KEY
npm run dev                            # http://localhost:3000
npm run check                          # typecheck + build
```

`/demo/*` works with no login and mock data. `/app/*` needs a Clerk session. To point Jobify at the local API, set `VITE_API_BASE_URL=http://localhost:8000/api` (the backend CORS default already allows `:3000`). Leave it empty to stay on mocks.

**Background jobs** (need Redis)

```bash
celery -A src.tasks worker --loglevel=info
celery -A src.tasks beat --loglevel=info      # exactly one beat, anywhere
python -m src.tasks catalog                   # trigger a job-catalog refresh now
```

Beat refreshes the shared job catalog twice a day (`CATALOG_REFRESH_HOURS_UTC`, default 08:00 and 20:00 IST; searches from `CATALOG_QUERIES`), syncs Gmail hourly, and marks stale applications ghosted daily. No scheduled task sends email. Admins can see refresh history and a `stale` flag at `GET /api/admin/catalog-runs`.

## Use it for your own job search

1. Put your resume in `data/resume.txt` and your profile (target roles, stack, comp, location) in `config/profile.yml`. Both are git-ignored personal data.
2. Add job URLs or descriptions to `data/pipeline.md` (or paste them to Claude Code) and run `/nexus pipeline`. Each job gets a 0–100 fit score with the matching resume lines and gaps; 65+ is worth applying, below 50 is never recommended.
3. Tailored resumes reorder and reword only what is already in your resume. Nothing is invented, and nothing is submitted or sent for you.

Agents and CLI for the same flow:

```bash
python -m src.agents.orchestrator --stage daily          # signal → ATS → fit → schedule → tailor → contacts → drafts
python -m src.agents.orchestrator --stage interview-prep --company "Company"
python -m src.agents.orchestrator --stage negotiate-counter --company "Company" --offer 22
python -m src.cli tracker | verify | drafts | scan "<query>"
```

Output is written to `data/` (for example `data/agent_run_report.md`) for review. The full `/nexus` command list is in [`CLAUDE.md` §2](./CLAUDE.md).

## Checks

```bash
python -m pytest
python -m compileall src main.py
cd jobify && npm run check
```

## Status

**Not production-ready yet.** Every API route requires a Clerk token unless it is on an explicit public allow-list, and every Jobify query is filtered to the signed-in user.

| Jobify feature | State |
|---|---|
| Jobs, Applications, Founders, Portfolio | Live on the API |
| Jobify inbox (per-user forwarding address) | Live; needs Cloudflare Email Routing set up |
| Gmail sync | Code done; needs a Google OAuth client (restricted scope, verification cost) |
| Chat | Live with streaming; LLM provider not chosen yet (echo stub by default; OpenRouter, Ollama and HF supported) |
| Payments (Dodo) | Not started; checkout page is still a simulation |
| Deploy | `render.yaml`, `fly.toml` and `docker-compose.prod.yml` run the API, a Celery worker and one beat |

The gap list and the MVP plan are in [`CLAUDE.md` → Production MVP](./CLAUDE.md#production-mvp-jobify).

## Security

- Never commit secrets. `.env*` is git-ignored; use platform secret stores in deployment.
- Treat `config/`, `data/`, and logs as personal data. `config/profile.yml` and `data/resume*.txt` are git-ignored; keep them that way.
- `AUTO_SEND_EMAILS=false` is the default and must stay that way. Nothing on the beat schedule may send email (enforced by `tests/test_catalog_refresh.py`).
- Only `VITE_*` variables reach the browser. Never put a secret in one.
