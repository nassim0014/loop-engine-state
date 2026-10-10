# Idea: `astk demo` — a zero-config, zero-secret end-to-end walkthrough

`analytics-service-toolkit` already has `astk doctor` (checks a *real* DB/Slack
you point it at) and `examples/demo_app.py` (a Streamlit app, needs `pip install
.[streamlit]` and a browser). Neither lets someone evaluating the library see all
four pieces — settings, db, alerts, logging — actually working together in one
command with nothing configured. Add `astk demo`: a new Typer command that spins
up an in-memory SQLite engine, loads settings with every secret-redaction path
exercised, round-trips real rows through `session_scope`/`fetch_df`, fires the
`Deduplicator` twice on the same key to show suppression, sends a console alert,
and emits one structured log line — then prints a readable step-by-step summary
(plus an optional `--json` machine-readable report), all in under a second with
no database, webhook, or network reachable.

## Success checks

1. `astk demo` exits 0 with no environment variables or flags set, and needs no
   network access or running database.
2. The output's settings section shows `slack_webhook_url` as redacted (`***`),
   not the literal configured value — demonstrating the `SecretStr` redaction
   `repr()` path from `astk.settings` actually fires, not just that it exists.
3. The output's database section reports writing and reading back the same
   number of rows (e.g. "wrote 3 rows" / "read 3 rows") via real
   `make_engine` + `session_scope` + `fetch_df` calls against the in-memory
   SQLite engine — not a hardcoded or mocked result.
4. The output's dedup section shows the *same* alert key accepted the first
   time and suppressed the second time within one run, proving
   `Deduplicator.should_send` (via `InMemoryDedupBackend`) actually ran twice
   rather than being asserted once.
5. `astk demo --json /tmp/astk_demo.json` exits 0 and writes a JSON file with at
   least the keys `settings`, `database`, `dedup`, `alert`, each a non-empty
   object/value — a machine-readable version of the same run.
6. `pytest tests/test_cli.py -k demo -q` passes — new tests covering the command
   via Typer's `CliRunner`, including that the second `should_send` call on the
   same key returns `False` within the run.

## Verdict

(filled in after a fresh judge subagent checks each item by actually running it)
