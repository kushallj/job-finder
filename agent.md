# Agent Guide

This document is the canonical repo guide for maintainers, contributors, and automation agents. It complements the root `README.md` and captures the practical operating model for the project.

## 1. Purpose and scope

Job Finder is a platform for:

- job discovery and scoring
- application tracking and lifecycle workflows
- outreach preparation and contact research
- startup and VC portfolio intelligence
- target-company research and interview preparation

The project spans backend services, UI, automation, and operational configuration. This guide documents the repo structure, conventions, and how to operate it safely.

## 2. Architecture at a glance

```text
job-finder/
├── main.py                     # FastAPI app startup and router composition
├── src/                       # Python implementation and service modules
│   ├── api/                   # route setup, request models, and API concerns
│   ├── agents/                # company and recruiting workflow agents
│   ├── auth/                  # auth dependencies and security helpers
│   ├── async_pipeline/        # asynchronous processing and pipeline utilities
│   ├── infrastructure/        # provider wrappers, interfaces, and infra glue
│   ├── services/              # business-layer service orchestration
│   ├── models.py              # SQLAlchemy models
│   ├── database.py            # DB engine, session factory, init logic
│   ├── tasks.py               # Celery task definitions
│   └── ...                    # domain modules for jobs, scraping, outreach, etc.
├── frontend/                  # React app and UI-specific API code
├── sidekick-desktop/          # desktop-layer shell for local workflows
├── extension/                 # browser extension assets and side tools
├── config/                    # profiles, target lists, search config
├── data/                      # resumes, generated artifacts, state, logs
├── docs/                      # canonical docs + archived historical docs
├── scripts/                   # deployment/ops automation
├── tests/                     # repository-level test documentation and new tests
├── .github/                   # CI and deployment workflows
├── docker-compose*.yml        # local and deployment compose files
├── Dockerfile                 # backend app container
├── requirements.txt           # Python dependency set
├── pytest.ini                 # test defaults
├── pyproject.toml             # minimal Python project configuration
├── README.md                  # high-level entry point
├── agent.md                   # this file
├── .env.example               # env configuration template
└── .pre-commit-config.yaml    # repository quality gates
```

## 3. System layers

### Application layer

- `main.py` is the runtime bootstrap and app assembly point.
- `src/api/` contains API routing and endpoint organization.
- `src/services/` contains orchestrating workflows focused on business behavior.

### Domain layer

- `src/` contains domain modules for jobs, outreach, referral data, contact intelligence, scraping, and finance/startup research.
- Domain logic is intentionally separated from UI and deployment concerns.

### Data layer

- `src/database.py` centralizes DB creation and session management.
- `src/models.py` is the SQLAlchemy model registry.
- Postgres is the intended production-style database; SQLite compatibility remains accepted for lightweight local work.

### Automation layer

- Celery workers and Redis support background task execution.
- `src/tasks.py` and related task modules should remain the task entry points.

### Frontend and tooling layer

- `frontend/` provides the dashboard and UI interactions.
- `sidekick-desktop/` and `extension/` are auxiliary product surfaces that should not be confused with core backend logic.

## 4. Setup and local development

### Python environment

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Start the backend

```bash
python -m uvicorn main:app --reload
```

### Start the stack via Docker

```bash
docker compose up --build
```

### Environment variables

Use `.env` at the repo root. Keep production-sensitive values out of source control. The repo includes `.env.example` as a safe starting template.

Required usage pattern:

- use `.env` for local runtime secrets
- use platform or CI secret stores for deployment
- never commit credentials, tokens, or signed export files

## 5. Repo conventions

### Documentation conventions

- `README.md` is the repo-level entry point.
- `agent.md` is the architecture and operations companion.
- `docs/` contains deeper domain guides and archived history.
- Prefer a single source of truth for architecture and onboarding material.

### Code organization conventions

- Keep backend code under `src/` unless it is explicitly a UI, deployment, or tooling surface.
- Keep config and profile data in `config/` or environment variables, not embedded in business logic.
- Keep generated outputs in `data/` and logs in a dedicated log directory.
- Keep scripts in `scripts/` for operational automation.

### Contribution conventions

- Prefer documentation-first changes for structural changes.
- Do not change business logic unless explicitly requested.
- Preserve backward compatibility during refactors.
- Add docs when new workflows, env vars, or service integrations are introduced.

## 6. Common commands

```bash
# backend startup
python -m uvicorn main:app --reload

# backend checks
python -m pytest
python -m compileall src main.py

# docker stack
docker compose up --build

# targeted agent flow
python -m src.agents.orchestrator --stage daily
python -m src.agents.orchestrator --stage leads
```

## 7. Security and production readiness

- Treat `.env`, `config/`, and `data/` as sensitive operational inputs.
- Use environment variables or platform secret management rather than plain source files.
- Do not auto-send emails, apply to jobs, or post outreach without explicit approval.
- Review generated candidate, job, and outreach drafts before external action.
- Keep dependencies updated and review security-sensitive changes with explicit checks.

## 8. Maintenance checklist

- Review the root README after structural changes.
- Update `agent.md` when architecture or workflows change.
- Archive outdated docs rather than leaving conflicting copies as primary references.
- Keep the env template aligned with current runtime expectations.
- Keep `src/` and `docs/` tidy and not overloaded with duplicated reference material.
- Revisit [docs/repository-structure.md](./docs/repository-structure.md) whenever top-level ownership or migration boundaries change.

## 9. Contributing workflow

For the contributor checklist and review expectations, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## 10. Contributor onboarding excerpt

New contributors should begin here:

1. Read `README.md` for an overview.
2. Read `agent.md` for architecture and conventions.
3. Review `docs/architecture/README.md` for the module layout.
4. Check `.env.example` before running locally.
5. Run a minimal validation command such as `python -m compileall src main.py`.
6. Only then add or modify deeper domain logic.

## 11. Migration and transition notes

This repository already contains a large amount of domain documentation and generated assets. The current reorganization aims to make the project easier to navigate without dropping historical context. The layered docs model is intentionally:

- readable for new contributors
- stable for existing operators
- explicit about the source of truth
- tolerant of legacy references that remain useful
