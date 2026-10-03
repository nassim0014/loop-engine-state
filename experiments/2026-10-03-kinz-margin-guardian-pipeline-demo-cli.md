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
