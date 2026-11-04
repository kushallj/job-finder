# Job Finder

Job Finder is a job-intelligence and workflow platform focused on job discovery, candidate profiling, application tracking, outreach preparation, and startup/VC research. The repository mixes a Python FastAPI backend, a React frontend, automation tasks, and domain-specific data pipelines.

## Repository goals

- Keep the application understandable and modular
- Keep operational logic separate from generated data and research artifacts
- Keep deployment and environment configuration explicit
- Keep onboarding friction low for contributors and operators
- Preserve compatibility with the existing stack while improving documentation and structure

## Repository overview

```text
job-finder/
├── main.py                     # FastAPI app entrypoint
├── src/                       # Python backend: app logic, models, routers, services
├── frontend/                  # Vite/React frontend and UI logic
├── sidekick-desktop/          # desktop integration shell
├── extension/                 # browser extension helpers
├── config/                    # candidate and sourcing profiles
├── data/                      # resumes, generated outputs, pipeline and tracker data
├── docs/                      # canonical docs + legacy archive
├── docker/                    # containerized service definitions
├── scripts/                   # operational scripts
├── tests/                     # repository-level test documentation and additions
├── .github/                   # CI/workflow definitions
├── alembic/                   # migration support
├── .env.example               # example environment variables
├── .pre-commit-config.yaml    # basic repository checks
├── pytest.ini                 # pytest defaults
├── pyproject.toml             # minimal Python project metadata/tooling config
├── package.json               # repo-level npm scripts
├── README.md                  # canonical user-facing entry point
├── agent.md                   # architecture, operations, and contributor guide
├── docker-compose.yml         # local runtime stack
├── Dockerfile                 # app image
└── requirements.txt           # Python dependency lockfile
```

## What is in the codebase

The platform currently includes:

- FastAPI backend for jobs, contacts, outreach, profile data, and startup signals
- SQLAlchemy + PostgreSQL support with optional SQLite compatibility
- Celery + Redis task workers for background jobs
- React frontend and a Vite-based dashboard
- startup/VC research, networking, and lead-sourcing workflows
- recruiter/outreach and candidate match pipelines
- target-company agents for interviews, fit scoring, and outreach prep

## Runtime stack

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy / Alembic
- PostgreSQL (current desired local DB)
- Redis + Celery
- React + Vite
- Docker Compose for orchestration

## Quick start

### 1. Create a local environment

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Use the repo root `.env` file (or copy from `.env.example`). Keep secrets out of version control.

```bash
copy .env.example .env
```

The repo already supports PostgreSQL via the env variable configuration used by the application and Compose files.

### 4. Start the backend

```bash
python -m uvicorn main:app --reload
```

API docs: `http://localhost:8000/docs`

### 5. Start the stack with Docker (optional)

```bash
docker compose up --build
```

## Database and operations

This repo expects a PostgreSQL-backed runtime for production-style usage, with Redis and Celery for async work. The authoritative local configuration is described in:

- `.env`
- `docker-compose.yml`
- `src/config.py`
- `src/database.py`

## Key directories

- `src/`: backend implementation. Most business logic lives here.
- `frontend/`: UI and frontend API layer.
- `docs/`: operational reference documentation and archive of older design notes.
- `config/`: profiles, search configs, target company definitions.
- `data/`: persisted job data, resumes, generated artifacts, and research state.
- `scripts/`: one-off automation and environment setup helpers.

## Documentation hierarchy

This repo is intentionally consolidating its documentation. The canonical order is:

1. `README.md`
2. `agent.md`
3. `docs/architecture/README.md`
4. `docs/repository-structure.md`
5. `docs/legacy/README.md`
6. deeper domain docs under `docs/`

## Repository structure optimization

The repository is in a safe first pass of folder structure optimization. The current plan and migration checklist live in [docs/repository-structure.md](./docs/repository-structure.md). This pass keeps production logic intact while clarifying ownership, archives, and documentation boundaries.

## Target-company agents

The project contains an agent-oriented workflow for research, fit scoring, interview prep, and outreach. Review drafts before action; the system is designed to support human approval rather than autonomous sending.

```bash
python -m src.agents.orchestrator --stage daily
python -m src.agents.orchestrator --stage leads
python -m src.agents.orchestrator --stage interview-prep --company "Company"
```

See [`docs/AGENT_STRATEGIES.md`](./docs/AGENT_STRATEGIES.md) for the agent rationale and [`agent.md`](./agent.md) for repo operations.

## Testing and quality checks

```bash
python -m pytest
python -m compileall src main.py
```

The repo also includes basic pre-commit and CI conventions to catch common issues early.

## Security and production readiness

- Never commit secrets or API keys.
- Keep all production-sensitive values in `.env` or platform secrets.
- Prefer environment-based config over hardcoded credentials.
- Review generated outreach and job automation output before sending or applying.
- Treat `config/`, `data/`, and logs as operationally sensitive assets.

## Contributing

Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for the contributor workflow and expectations.

- Keep production logic stable unless specifically requested.
- Prefer documentation and structure changes before behavior changes.
- Use consistent naming, keep module boundaries clear, and avoid duplicate source-of-truth files.
- Add or update docs when adding new workflows or significant tooling changes.

## Maintainer notes

This repository has grown into a monorepo-like structure with multiple workloads. The top-level docs and the repo-level conventions are intentionally more opinionated than the older scattered Markdown. The goal is to make onboarding and architecture review simpler without freezing the technical direction.
