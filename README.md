# Job Finder

Job Finder is a job-search and career workflow platform. It combines a FastAPI
backend, a React dashboard, background workers, and integrations for job
discovery, candidate matching, outreach, application tracking, and venture
capital portfolio research.

## Features

- Search and evaluate job opportunities against candidate profiles.
- Discover target companies, contacts, and hiring signals.
- Track applications in a tenant-isolated Kanban board.
- Manage authentication, billing, and user credits.
- Browse startup and VC portfolio research, including founder data.
- Run background tasks with Celery and Redis.
- Use the target-company agent pipeline for research, fit scoring, interview
  preparation, and outreach drafts. The pipeline does not send outreach
  automatically.

## Run locally

### API

Use Python 3.11 or newer. From the repository root:

```bash
python -m venv .venv
# Activate the virtual environment, then:
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The API is available at `http://localhost:8000`; interactive API
documentation is at `http://localhost:8000/docs`. Configure optional
integrations and production settings with environment variables or a local
`.env` file. Never commit credentials.

### Full stack with Docker Compose

```bash
docker compose up --build
```

The Compose stack includes the API, frontend, PostgreSQL, Redis, Celery
workers/scheduler, and supporting services. See
[`docker-compose.yml`](./docker-compose.yml) and
[`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md) for deployment details.

## Target-company agents

The agent pipeline can run focused research and preparation stages from the
repository root:

```bash
python -m src.agents.orchestrator --stage daily
python -m src.agents.orchestrator --stage leads
python -m src.agents.orchestrator --stage interview-prep --company "Company"
```

See [`docs/AGENT_STRATEGIES.md`](./docs/AGENT_STRATEGIES.md) for the agent
strategies and [`CLAUDE.md`](./CLAUDE.md) for the available `/nexus` commands.
Review generated drafts before taking action; the agents do not auto-send
messages or apply to jobs.

## Tests

Install the Python dependencies, then run the test suite with:

```bash
python -m pytest
```
