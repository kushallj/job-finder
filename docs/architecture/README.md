# Architecture Overview

This repository is organized as a multi-service job-intelligence platform with a Python backend, a Vite/React frontend, supporting data services, and automation scripts.

## Runtime model

- Python API: `main.py` and `src/`
- Background jobs: Celery + Redis
- Database: PostgreSQL with SQLAlchemy + Alembic
- Frontend: `frontend/`
- Desktop shell: `sidekick-desktop/`
- Browser extension: `extension/`
- Deployment: Docker Compose and platform YAML files

## Main modules

```text
repo/
├── main.py                       # FastAPI app entrypoint
├── src/
│   ├── api/                     # API route modules and schemas
│   ├── auth/                    # auth and identity
│   ├── agents/                  # target-company orchestration and agents
│   ├── async_pipeline/          # async job pipeline pieces
│   ├── core/                    # shared reusable primitives
│   ├── infrastructure/          # infra adapters, providers, services
│   ├── services/                # service-layer logic
│   ├── models.py                # SQLAlchemy models
│   ├── database.py              # DB engine/session factory
│   └── tasks.py                 # Celery task hooks
├── frontend/                    # React app, API contracts, tests
├── docs/                        # canonical repo docs and archives
├── config/                      # candidate profiles and sourcing config
├── data/                        # data files, job data, resume, stored pipeline outputs
├── scripts/                     # shell automation and ops scripts
├── tests/                       # repo-level tests (additive, minimal)
├── docker-compose*.yml          # local/prod environments
├── Dockerfile, render.yaml, fly.toml
└── README.md, agent.md         # canonical entry points
```

## Design goals

- Keep app startup simple and readable via `main.py`
- Keep `src/` as the authoritative implementation area
- Keep operational and generated data outside core logic
- Keep docs and configs consistent and discoverable
- Keep production-sensitive values in environment variables, not source files

## Legacy note

Older and specialist docs remain in `docs/` and adjacent root files for reference. This repo’s primary documentation should be read in this order:

1. `README.md`
2. `agent.md`
3. `docs/architecture/README.md`
4. domain-specific references under `docs/`
