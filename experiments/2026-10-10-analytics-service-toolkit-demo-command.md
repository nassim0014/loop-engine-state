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

PR: https://github.com/nassim0014/analytics-service-toolkit/pull/11
Judge: fresh Opus subagent, given only the repo path, the branch name, and this
file's text (no implementation opinion from the building agent).

1. PASS — `astk demo` (no env vars, no network via `unshare -rn`) exited 0.
2. PASS — output shows `slack_webhook_url='***'`, the real demo webhook string
   never appears unredacted. Caveat raised: `_DemoSettings` redeclared the field
   as plain `str` instead of inheriting `SecretStr`, so the repr-redaction (which
   keys off field *name*) still worked but the type protection was silently
   dropped.
3. PASS — "wrote 3 rows" / "read 3 rows" / "healthcheck: ok", via real
   `make_engine` + `session_scope` + `fetch_df` calls, no mocks.
4. PASS — `should_send('demo:margin-alert')` → `True` then `False` on the same
   `Deduplicator` instance within one run.
5. PASS — `astk demo --json /tmp/astk_demo.json` exit 0; file has non-empty
   `settings`/`database`/`dedup`/`alert` keys.
6. PASS — `pytest tests/test_cli.py -k demo -q` → 6 passed.

**Overall: VERIFIED**, with the SecretStr caveat on check 2 flagged as real
(not a check failure, but a correctness bug).

### Post-verification fix

Fixed the SecretStr caveat before merging: `_DemoSettings.slack_webhook_url` now
keeps the inherited `SecretStr | None` type instead of widening it to `str | None`,
and the demo additionally exercises `settings.slack_webhook()` (the real
unwrap-for-use path, previously never called) via a dry-run `SlackNotifier` check.
Re-ran all 6 success checks myself after the fix — all still pass, plus:
- new test asserting `_DemoSettings.model_fields["slack_webhook_url"].annotation
  == SecretStr | None` (would have caught the original bug)
- full suite: 84 passed, 2 skipped (was 83/2 before this fix, +1 new test) on
  both Python 3.11 and 3.12
- `ruff check .` clean

No second judge round run for this fix: the original verdict was VERIFIED (not
NOT VERIFIED), the fix only narrows a type back to what the base class already
declared and adds a call to an existing, already-tested method — it doesn't
change any success-check's observable behavior, which I re-confirmed directly
rather than re-delegating.

CI on PR #11 and the standing merge rules (CI green, no workflow file touched,
no test weakened, not draft, no conflict, no hold label) decide whether this
merges — checked separately before the merge decision.
