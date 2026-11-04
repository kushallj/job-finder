# Contributing

This repository is a multi-service job-intelligence platform. Contributions should preserve the current architecture, increase clarity, and avoid unnecessary churn.

## Before you start

1. Read the root overview in [README.md](./README.md).
2. Read the architecture and operations guide in [agent.md](./agent.md).
3. Review the target docs in [docs/architecture/README.md](./docs/architecture/README.md).
4. Keep production logic stable unless the task explicitly requires changes.

## Scope and expectations

- Prefer documentation and structure improvements before logic changes.
- Keep backend logic under `src/` and keep operational scripts under `scripts/`.
- Keep config, generated outputs, and secrets outside production code.
- Add or update docs when workflows, env settings, or toolchains change.

## Local validation

Use the smallest command that checks the changed behavior:

```bash
python -m compileall src main.py
python -m pytest
```

## Standards

- Follow existing naming patterns and module boundaries.
- Keep docs precise and current.
- Avoid duplicating sources of truth.
- Preserve compatibility with the repo's current stack.

## PR expectations

- Explain the problem and the reasoning for the change.
- Document any new environment variables or operational steps.
- Keep diffs focused on one concern at a time.
- Note any migration or archive actions when reorganizing the repo.
