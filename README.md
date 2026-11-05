# Job Finder + Jobify

Job-search intelligence platform. **Job Finder** (this repo root) is the FastAPI backend: job discovery and scoring, application tracking, outreach drafting, startup/VC research, and a target-company agent layer. **Jobify** (`jobify/`) is the new customer-facing React frontend being taken to an MVP on top of it.

Human-in-the-loop by design: the system drafts, scores, and tracks. It never auto-applies, auto-sends email, or posts to social platforms without explicit approval.

> **Docs policy:** this repo has exactly two docs, this `README.md` (humans: what it is, how to run it) and [`CLAUDE.md`](./CLAUDE.md) (agents and contributors: rules, architecture, current state, MVP plan). Don't add more Markdown docs; extend one of these or put rationale in module docstrings.

## Layout

```text
job-finder/
├── main.py              FastAPI app (≈6.6k lines, ≈170 routes) + router composition
├── src/                 Backend: models, auth, routers, services, scrapers, agents
│   ├── api/routers/     agents, auth, billing, kanban, mailbox, portfolio, telegram
│   ├── agents/          26 target-company agents + orchestrator.py
│   ├── auth/            Clerk RS256 + legacy HS256 JWT verification
│   ├── models.py        SQLAlchemy models    database.py  engine/session
│   ├── tasks.py         Celery tasks         cli.py       NEXUS CLI
│   └── config.py        Pydantic settings (reads .env)
├── jobify/              NEW product frontend: React 19, Vite 8, Tailwind 4, Clerk
├── frontend/            Legacy internal dashboard: React 19, MUI, react-query
├── config/              profile.yml, target_companies.yml, boolean_queries.yml
├── data/                resume.txt, tracker, pipeline.md, agent_state.db (sensitive)
├── alembic/             migrations (only the initial schema so far)
├── tests/               pytest suite (≈120 test files)
├── extension/  sidekick-desktop/  n8n_workflows/  dsm_deploy/   non-core surfaces
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

`/demo/*` works with no login and mock data. `/app/*` needs a Clerk session. To point Jobify at the local API, set `VITE_API_BASE_URL=http://localhost:8000` (the backend CORS default already allows `:3000`). Leave it empty to stay on mocks.

**Agents and CLI**

```bash
python -m src.agents.orchestrator --stage daily          # signal → ATS → fit → schedule → tailor → contacts → drafts
python -m src.agents.orchestrator --stage leads
python -m src.agents.orchestrator --stage interview-prep --company "Company"
python -m src.cli tracker | verify | drafts | scan "<query>"
```

Output is written to `data/` (for example `data/agent_run_report.md`) for review.

## Checks

```bash
python -m pytest
python -m compileall src main.py
cd jobify && npm run check
```

## Status

Jobify UI is built but still reads mock services (`jobify/src/services/*`). The backend now verifies Clerk tokens, but most routes are still unauthenticated. **It is not production-ready.** The verified gap list and the MVP plan are in [`CLAUDE.md` → Production MVP](./CLAUDE.md#production-mvp-jobify).

## Security

- Never commit secrets. `.env*` is git-ignored; use platform secret stores in deployment.
- Treat `config/`, `data/`, and logs as personal data.
- `AUTO_SEND_EMAILS=false` is the default and must stay that way.
- Only `VITE_*` variables reach the browser. Never put a secret in one.
