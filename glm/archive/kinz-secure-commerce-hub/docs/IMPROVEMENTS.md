# Improvement backlog

The queue the closed-loop improvement cycle works from. One item per run,
highest value first.

**Verify a symptom is still present before trusting this file's headings.**
Items 1 and 2 below sat marked "Now" for four cycles after PRs #27 and #28
had already resolved both (`routes/kpis.py` and `routes/sales.py` were
already at 99%/97% coverage when checked) — the backlog was simply never
ticked off. `pytest --cov` is the source of truth, not this file.

**How to run the workflows locally**

```bash
# Backend tests (95 tests, ~8s)
cd src/api && pip install -r requirements.txt
cd ../.. && pytest tests/ -v --cov=src --cov-report=term-missing

# Backend lint + SAST
cd src/api && ruff check . && bandit -r . -ll -ii -x tests/

# Frontend tests
cd src/frontend && npm install && npx jest

# Full stack via Docker
docker compose up --build -d

# CI: .github/workflows/ci.yml — backend (Python 3.11+3.12) + frontend (Node)
```

---

## Now

### 6. Remaining coverage gaps — pick the highest-value one next
**Re-verify before trusting the numbers below** — a fresh `pytest --cov` run
on 2026-09-18 (while fixing item 7) already found `src/api/security/rbac.py`
at **100%**, not the 68% recorded here. Don't trust this list without
re-running coverage first.

**2026-09-25 (PR #62):** looking at `run_etl.py`'s gap for this item found a
real bug, not just a coverage hole — `transform_products()`'s `margin_pct`
divided by `price_tnd` unguarded, so a zero-priced product (valid data, not
dropped by the NaN check above it) silently produced `-inf`/`inf` in
`products_enriched.csv` instead of a sane value. Fixed (now `NaN` when
`price_tnd == 0`, matching how `kpis.py` already treats a zero denominator)
with a regression test. `run_etl.py` is still only at ~57% — `extract_*`,
`load()`, `run()`, and the missing-columns `ValueError` branch remain
untested — so it stays the top pick below, now for the remaining coverage
rather than a known bug.

Roughly ranked by real risk, not just missing-line count:

- `src/pipeline/jobs/scheduler.py` — 0% (24/24 missed). APScheduler
  wrapper; untested but also never exercised by anything except the live
  container, so a test would need to mock APScheduler's `BlockingScheduler`
  rather than actually run jobs on a timer.
- `src/pipeline/jobs/run_etl.py` — ~57% (untested: `extract_products`/
  `extract_sales`'s `FileNotFoundError` branches, `transform_products`'s
  missing-columns `ValueError`, `transform_sales`'s dropped-rows warning
  branch, `load()`, and `run()`). The margin_pct divide-by-zero bug in this
  file was fixed in PR #62; what's left here is coverage, not a known bug.
- `src/api/main.py` — 85% (11/72 missed, lines 67-73, 146-153, 181-183) —
  likely startup/shutdown lifecycle and error-handler branches, lower
  value than the above since they're exercised indirectly by every other
  test importing `app`.
- `src/api/routes/auth.py`, `security/jwt_handler.py`,
  `security/passwords.py`, `security/audit.py`, `api/utils/__init__.py` —
  smaller gaps (2-11 lines each), mostly exception-handling branches.

## Next

### 4. Open dependabot PR #18 — next 14→16 (major runtime bump)
50+ days old as of the last check. Next.js 14→16 is a major runtime bump —
per the review-loop rules, major runtime bumps always wait for the owner.
The repo also has a frontend with its own Dockerfile and tailwind config —
the bump needs manual verification that the frontend still renders
correctly.

---

## Done

- **PR #62 (item 6, partial)** — Found while chasing `run_etl.py`'s coverage
  gap: `transform_products()`'s `margin_pct = (price - cost) / price` divided
  by zero for any product priced at `0.0` (valid, non-NaN data), silently
  writing `-inf`/`inf` into `products_enriched.csv` — not valid JSON, would
  break any future consumer that serializes the row. Fixed with `np.where` so
  `margin_pct` is `NaN` (undefined) instead, matching the zero-denominator
  convention `kpis.py` already uses. Added
  `test_transform_products_zero_price_margin_pct_is_not_infinite`; verified it
  fails on the pre-fix code (`math.isnan(-inf)` is `False`) and passes after.
  103 tests pass (was 102), ruff clean. Item 6 itself is **not** fully done —
  `run_etl.py`'s `extract_*`/`load`/`run` functions and the other files listed
  under it are still uncovered; see the 2026-09-25 note above.
- **PR #60 (item 7)** — ~~CI broken on main — frontend `npm install`
  fails (ERESOLVE)~~ ✅ Fixed two lockstep dependency gaps in
  `src/frontend/package.json`, both introduced 2026-09-02: (1) `eslint` had
  been bumped to `10.9.1` (PR #43) without bumping `eslint-config-next`,
  which peer-requires `eslint@"^7.23.0 || ^8.0.0"` — reverted eslint to
  `8.57.0`. (2) `react` had been bumped to `19.2.8` (PR #44) while
  `react-dom` stayed at `18.3.1` and `next@14.2.3` peer-requires
  `react@^18.2.0` — reverted `react`/`@types/react` to `18.3.1`/`18.3.2` to
  match `react-dom`. Regenerated `package-lock.json`. Verified: reproduced
  the original `npm ci` ERESOLVE failure on main first, then confirmed
  `npm ci --no-audit --no-fund`, `npm run lint`, `npm test -- --ci
  --coverage` (6 tests), and `npm run build` all pass after the fix.
  Backend suite (102 tests), ruff, and bandit also re-verified unaffected.
  NOT covered: this only restores the pre-2026-09-02 working versions: it
  does not address the eslint 9+/flat-config migration or the react 19
  upgrade that dependabot will likely re-propose — the two dependabot PRs
  that reintroduce these bumps should land together with their peer deps
  next time, not separately.
- **PR #36** — Backlog bookkeeping correction (items 1 and 2
  were already resolved in PRs #27/#28 but never ticked off — moved to
  *Done* below with the real history). Same-PR code contribution: added
  `tests/backend/test_products.py` (previously had no test file at all),
  closing `routes/products.py` from 72%→100% coverage — the entire
  single-product `GET /{product_id}` route, the category-filter branch,
  the case-insensitive-filter branch, the no-match-returns-empty branch,
  and `_load_products()`'s missing-file fallback were all untested before
  this PR. 95 tests pass (was 80), ruff and bandit clean. Verified each
  new assertion actually catches a regression by temporarily breaking the
  corresponding code path (disabled the category filter, changed the 404
  to a 200) and confirming the relevant tests failed, then restored.
- **PR #35** — Added a bug-report issue template.
- **PR #34** — Added `SECURITY.md` with a reporting policy.
- **PR #33** — Added `.pre-commit-config.yaml` for ruff.
- **PR #32** — Added `CONTRIBUTING.md` with dev setup + PR workflow.
- **PR #31** — Added a `Makefile` with ruff + check targets.
- **PR #30 (item 5)** — ~~No CLAUDE.md~~ ✅ Added `CLAUDE.md` with ground
  rules, architecture, test commands, known traps (dependabot, the
  `SettingWithCopyWarning` fix, security headers), and loop-engine
  integration.
- **PR #29 (item 3)** — ~~`models/db.py` coverage — 0%~~ ✅ 13 new tests
  in `tests/backend/test_models.py`: CRUD on all three ORM models
  (ProductORM, CustomerORM, SaleORM) + defaults + nullability + metadata
  inspection.
- **PR #28 (item 2)** — ~~`routes/sales.py` coverage — 36% → target
  100%~~ ✅ Covered every filter branch (channel, category, start_date,
  end_date), pagination, the order lookup, and the 404 path. Landed at
  97% (one line remaining, an edge case not worth chasing at the time).
- **PR #27 (item 1)** — ~~`routes/kpis.py` coverage — 18% → target
  100%~~ ✅ Landed at 99%. Neither this PR nor #28 got ticked off here at
  the time — see the note at the top of this file.
- **PR #26** — Created `docs/IMPROVEMENTS.md` as the first-cycle
  deliverable, AND fixed the `SettingWithCopyWarning` in
  `src/pipeline/jobs/run_etl.py`. `transform_products()` did
  `df = df.dropna(...)` (returning a view) then assigned a new column to
  it, which pandas warns may not propagate to the original. Same issue in
  `transform_sales()`. Fixed with `.copy()` after `dropna` in both
  functions.

## Dropped

(none yet)
