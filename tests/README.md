# Test Strategy

This folder acts as the repo-level test entry point for future additions and focused validation work.

## Current state

- Frontend tests live under `frontend/src/**/__tests__`.
- Repo-level Python validation is driven by `pytest.ini` and `python -m pytest`.
- Runtime verification should keep to the smallest relevant command before broader suites.

## Guidance

- Prefer test files near the implementation they cover.
- Keep repo-level tests focused on integration and smoke checks.
- Add new tests when behavior changes or new workflows are introduced.
