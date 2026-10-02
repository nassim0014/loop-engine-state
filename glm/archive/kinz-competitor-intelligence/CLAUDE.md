# Working on this repository

Competitor-monitoring platform for KINZ (Tunisian cosmetics). FastAPI + Streamlit
dashboard + SQLAlchemy/SQLite + Playwright scrapers.

## Ground rules

**Never push to `main`.** Branch, open a PR, let CI pass, then merge. This holds
even when asked to "just fix it" — the branch costs nothing and the PR body is
where the reasoning lives.

**Never commit credentials.** The GitHub PAT lives outside the repo. It must not
appear in any file, git config, commit message, log, or report. `.env` is
gitignored; `.env.example` is the documented template.

**The database is not reproducible.** `data/competitors.db` holds ~3,600 outlets
that took 8–12 hours of Google Maps scraping, plus sales-pipeline fields
(`is_stockist`, `contacted`, `notes`) that were entered by hand and no scraper can
regenerate. Treat any change to write paths as high-risk and cover it with tests
first. This is not hypothetical: see PR #23, where a stringified float silently
nulled `reviews_count` on every save of the Outlets tab.

**Measure before optimising, and say the number.** The dashboard work in PR #17
started from a profile showing 4,417 ms in one `px.line` call and 1,324 ms in one
loop. Caching, which was the obvious guess, would have saved 65 ms. If you have no
measurement, say so plainly rather than implying one.

## Commands

```bash
./venv/bin/pytest -q                 # full suite (~365 tests)
./venv/bin/ruff check .              # lint (errors only: E9, F, B)
./venv/bin/streamlit run dashboard/app.py
```

CI runs exactly these two: `.github/workflows/ci.yml`, jobs `Lint` and `Tests`.

## Layout

| Path | What it is |
|---|---|
| `dashboard/app.py` | The Streamlit app. ~2,400 lines, nine tabs. |
| `dashboard/analysis.py` | Pure pandas logic, no Streamlit import — so it's testable. |
| `dashboard/saves.py` | Database writes for the editable tables. Same reason. |
| `src/database.py` | Models, engine, PRAGMA hook, and the `new_columns` migration map. |
| `src/scrapers/` | Playwright + HTTP scrapers. |
| `scripts/` | Operational entry points (scraping, enrichment, seeding). |
| `api/` | FastAPI service. |

## Things that have bitten before

**`st.tabs` executes every tab body on every rerun.** A keystroke in one tab's
search box re-runs all nine. This is the root cause of the dashboard feeling slow.
The fix is `st.fragment` around self-contained blocks. As of PR #32, 8 of the 9
tabs are fragmented — Market is the one exception, by design (it's read-only
charts, nothing interactive to isolate). (Corrected 2026-08-07 — this used to
say "two done, seven not," which was stale.)

**`st.rerun()` defaults to `scope="app"`** and reruns the whole app even from
inside a fragment. Only the explicit `scope="fragment"` is fragment-local. An
earlier comment in this repo claimed the opposite and shaped a PR around it.

**`st.cache_data` is process-global**, and `AppTest` runs the app in the test
process. Tests must clear it or they silently assert against another test's stale
frames — which is exactly what four smoke tests did until PR #24.

**`create_all()` creates tables, not columns.** A new column on an existing model
needs an entry in `new_columns` in `src/database.py`, or every existing database
is silently missing it. `test_no_schema_drift_warning_on_current_schema` guards
this.

**`_coalesce` in `app.py` returns `str(value).strip()`**, so it turns numbers into
strings. `blank_to_none` in `dashboard/saves.py` does not. Don't merge them
without checking every caller; the difference caused a data-loss bug.

**SQLite locking.** The dashboard used to call `init_db()` inside save helpers,
which takes an exclusive lock and blocked concurrent scrapers. Loaders and savers
must not run migrations.

## Style

Match the surrounding code. Comments explain *why*, and specifically why a
non-obvious choice was made — most comments in this repo record a measurement or a
bug, not a restatement of the line below.

Commit messages and PR bodies are written for a reader who wasn't there. State
what broke, how it was verified, and what was *not* covered.

## Reporting

Say what actually happened. If tests fail, show the output. If something was
skipped, say so. Don't claim a PR, a passing run, or a measurement that didn't
happen — this has gone wrong before and is the fastest way to become useless.
