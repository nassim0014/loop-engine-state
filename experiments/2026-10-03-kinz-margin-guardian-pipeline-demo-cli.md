# Idea: offline demo CLI for kinz-margin-guardian-pipeline

`kinz-margin-guardian-pipeline` currently requires Docker + Postgres + Airflow (4GB+
RAM) just to see whether the margin-calculation and alerting logic actually works,
which is real friction for anyone evaluating the repo. Add `scripts/demo.py`: a
zero-dependency, zero-secret, zero-database CLI that seeds a handful of synthetic
products, simulates today's competitor prices, runs them through the existing
`src.margin_engine` + `src.alert_manager.format_alert_message` pipeline, and prints
a readable table (plus an optional `--json` machine-readable output) so the whole
pipeline's value is visible in one command, in one second, on a laptop with nothing
installed beyond the repo's lightweight test dependencies.

## Success checks

1. `python scripts/demo.py` exits 0 and prints a table with exactly 5 product rows
   (one line per synthetic product, each identifiable by name).
2. `python scripts/demo.py --json /tmp/demo_output.json` exits 0 and writes a JSON
   file containing exactly 5 entries, each with at least the keys `product_name`,
   `b2c_margin_pct`, `b2b_margin_pct`, `b2c_alert`, `b2b_alert`.
3. At least one of the 5 synthetic products is priced so its margin falls below the
   default 40% alert threshold, so the table shows at least one row flagged ALERT,
   and the script also prints a human-readable alert line for it (via
   `src.alert_manager.format_alert_message`) — demonstrating the alerting path
   without needing Slack, a webhook, or the private `astk` package.
4. Running `python scripts/demo.py --seed 42` twice in a row produces byte-identical
   stdout both times (deterministic given a fixed seed).
5. `pytest tests/test_demo.py -q` passes — new tests covering the synthetic product
   builder, the margin-engine wiring, and the `--json` output schema.
6. The demo runs with `DATABASE_URL` unset and no Docker daemon or network reachable
   (true in this very sandbox) — it must not import or touch anything that requires
   Postgres, Docker, or the private `astk` package to succeed.

## Verdict

PR: https://github.com/nassim0014/kinz-margin-guardian-pipeline/pull/27
Judge: fresh Opus subagent, given only the repo path, branch name, and this file's
text (no implementation opinion from the building agent).

1. PASS — `python scripts/demo.py` exits 0, prints exactly 5 named product rows.
2. PASS — `--json` output is a 5-entry JSON list, every entry has
   `product_name`/`b2c_margin_pct`/`b2b_margin_pct`/`b2c_alert`/`b2b_alert`.
3. PASS — Argan Oil 100ml (26.03% B2C / 12.97% B2B) is flagged ALERT in the table,
   and the real `format_alert_message` lines are printed for it, threshold read
   from the real `src/config.py` default (40%).
4. PASS — `--seed 42` run twice gave byte-identical stdout (same sha256 both
   times); `--seed 7` gave a different hash, confirming the seed actually drives
   the output.
5. PASS — `pytest tests/test_demo.py -q` → 11 passed in 0.20s.
6. PASS — ran with `DATABASE_URL` unset, `docker info` failing, sockets patched to
   raise, and a meta-path import hook forcing `ModuleNotFoundError` for astk,
   psycopg2, sqlalchemy, docker, airflow and requests — still exited 0 with full
   table + alerts + JSON, and none of those modules were actually imported. (One
   caveat noted: `src/alert_manager.py` only catches `ModuleNotFoundError`, not a
   generic `ImportError`, for the astk fallback — pre-existing on main, not
   touched by this PR, and irrelevant to a real missing-package environment.)

Sanity checks: full suite on the branch 61 passed/2 skipped vs. 50 passed/2
skipped on `origin/main` before this PR — exactly the 11 new tests, no existing
test broken, skip count unchanged. `ruff check` clean.

**VERDICT: VERIFIED**

CI on PR #27 and the standing merge rules (CI green, no workflow file touched, no
test weakened, not draft, no conflict, no hold label) decide whether this merges —
checked separately before the merge decision.
