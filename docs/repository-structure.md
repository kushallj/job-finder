# Repository Structure Optimization Plan

This document defines the first safe optimization pass for the repository without changing production behavior.

## Guiding principles

- Keep domain logic under `src/`.
- Keep operational code under `scripts/` and `docker/`.
- Keep generated artifacts in `data/` and `logs/`.
- Keep historical or legacy material in `docs/legacy/` and `docs/archive/`.
- Treat `README.md`, `agent.md`, and `docs/architecture/README.md` as the canonical documentation stack.

## Target structure (proposed)

```text
job-finder/
├── README.md                        # user-facing overview
├── agent.md                         # architecture + contributor guide
├── CONTRIBUTING.md                  # contribution rules and validation
├── .env.example                     # environment template
├── .editorconfig                    # formatting rules
├── pyproject.toml                   # tool config
├── pytest.ini
├── requirements.txt
├── package.json
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── src/
│   ├── __init__.py
│   ├── api/
│   ├── agents/
│   ├── application/
│   ├── auth/
│   ├── async_pipeline/
│   ├── core/
│   ├── domain/
│   ├── infrastructure/
│   ├── presentation/
│   ├── services/
│   ├── ...
│   ├── database.py
│   ├── models.py
│   ├── tasks.py
│   └── config.py
├── frontend/
├── sidekick-desktop/
├── extension/
├── config/
├── data/
├── docs/
│   ├── architecture/
│   ├── legacy/
│   ├── repository-structure.md
│   └── ...
├── scripts/
├── tests/
├── logs/
├── archive/
│   └── legacy-notes/
├── .github/
├── .kiro/
└── .claude/
```

## What this pass changes

This pass is intentionally documentation-first and non-invasive.

- Clarifies ownership of files by category.
- Keeps the repo navigable for new contributors.
- Splits canonical documentation from historical archives.
- Creates a migration path before any file moves are attempted.

## Safe migration rules

1. Do not move production logic in the same patch as documentation cleanup.
2. Keep directories stable if they already map cleanly to a domain or runtime area.
3. Move only when a grouping is clearly redundant, ambiguous, or historically stale.
4. Update references after any move.
5. Keep a transition checklist for owners of legacy directories.

## Transition checklist

- [ ] Review top-level directories and their purpose
- [ ] Confirm `src/` remains the core implementation home
- [ ] Confirm `docs/` is the canonical documentation home
- [ ] Confirm `config/` and `data/` contain only runtime inputs and generated outputs
- [ ] Archive stale or experimental folders under `archive/` or `docs/legacy/`
- [ ] Keep README and agent docs aligned with actual structure

## Next optimization phase

The next phase would move only clearly redundant files or folders into a more canonical grouping, and would be paired with a follow-up validation pass to ensure imports, references, scripts, and docs still point to the right paths.
