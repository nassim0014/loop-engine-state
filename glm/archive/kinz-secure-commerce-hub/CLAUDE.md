# kinz-secure-commerce-hub — Agent Guidance

## What this is

Security-first e-commerce intelligence platform. FastAPI backend + React/TypeScript
frontend. Public repo under `nassim0014` — no private `astk` dependency may be
imported here.

## Rules (inherited from the loop engine)

1. **Never push directly to `main`** — open a PR, squash-merge.
2. **Squash-merge only** — so a revert is one command.
3. **Never create GitHub issues** — owner wants 0%.
4. **Never change repository visibility.**
5. **Never rewrite git history or force-push.**
6. **Never delete a branch other than one created this run.**

## Architecture

```
src/
  api/              FastAPI backend
    routes/         API route handlers (kpis, sales, products, auth, health)
    models/         SQLAlchemy ORM models
    security/        JWT auth, RBAC, rate limiting
    utils.py         Shared utilities
  pipeline/         ETL jobs (run_etl.py)
  frontend/         React/TypeScript frontend (Jest tests)
tests/
  backend/           pytest suite (95 tests)
  frontend/          Jest suite
docker-compose.yml   Full stack: API + frontend + PostgreSQL
```

## Development workflow

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r src/api/requirements.txt

# Tests (95 tests, ~8s)
pytest tests/ -v

# Lint
cd src/api && ruff check .

# Frontend
cd src/frontend && npm install && npx jest

# Full stack via Docker
docker compose up --build -d
```

## CI

`.github/workflows/ci.yml` — runs on push + pull_request to main.
Lint (ruff) + tests (pytest) + frontend tests (Jest).

## Known traps

- **Dependabot next 14→16**: PR #18 was closed with conflicts. The bump is a
  major runtime change — needs manual verification that the frontend still
  renders correctly. Wait for owner sign-off.
- **SettingWithCopyWarning**: fixed in PR #26 in `run_etl.py`. Use `.copy()`
  when slicing DataFrames before modifying.
- **Security headers**: the API includes CORP/COEP/COOP headers — don't remove
  them, they're tested in `test_security_hardening.py`.

## Loop-engine integration

In the closed-loop rotation (position 4 in the cursor). The loop engine works
this repo every 2 days, opening small PR-based improvements. See
`docs/IMPROVEMENTS.md` for the current backlog.
