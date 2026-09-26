# 2026-09-26 — feed-quality-gate: self-contained HTML report

Add `feed_quality_gate.report.to_html()` and a `fqg check --html PATH` CLI
flag that render a single, dependency-free HTML page for a `FeedReport` — a
score gauge, a colour-coded PASS/FAIL/WARN table per check, and a sample of
quarantined row ids — so a person (or a CI artifact viewer) can see a feed's
verdict without piping the JSON report through `jq` or reading a terminal
transcript.

## Success checks

1. `python3 -c "from feed_quality_gate.report import to_html; from feed_quality_gate import evaluate, load_rules; import pandas as pd; r = evaluate(pd.read_csv('examples/sample_feed.csv'), load_rules('rules.example.yaml')); h = to_html(r); assert h.startswith('<!doctype html'); assert str(r.score) in h; assert 'freshness' in h; print('OK')"` prints `OK`.
2. `fqg check -i examples/sample_feed.csv -r rules.example.yaml --html /tmp/fqg-report.html --quiet` exits `1` (the shipped example feed is intentionally broken) and `/tmp/fqg-report.html` contains both `<!doctype html` and `example-competitor-prices`.
3. A `CheckResult.message` containing `<script>alert(1)</script>` is HTML-escaped in `to_html()`'s output — the literal substring `<script>` does not appear in the rendered page.
4. `pytest tests/ -q` passes, including new tests covering `to_html()` and the CLI's `--html` flag.
5. `ruff check .` is clean.

## Verdict

PR: https://github.com/nassim0014/feed-quality-gate/pull/4 (branch
`claude/loop-creative-20260926-html-report`, head `1b52ca0`)

Judged by a fresh Opus subagent, given only the repo path, the branch name,
and this file's text — no opinion from the implementing session.

1. **PASS** — ran the exact command in a fresh venv (`/tmp/judge-venv`,
   `pip install -e ".[dev]"`); printed `OK`, exit 0.
2. **PASS** — deleted `/tmp/fqg-report.html` first, then ran the exact
   command; exited 1. The regenerated file (3209 bytes) contains
   `<!doctype html` (1 match) and `example-competitor-prices` (2 matches).
3. **PASS** — independently scripted a report with `results[0].message`
   replaced by `<script>alert(1)</script>` (via `dataclasses.replace`, not
   the repo's own test): literal `<script>` absent from the page, escaped
   `&lt;script&gt;alert(1)&lt;/script&gt;` present. Also notes the branch's
   own regression test at `tests/test_gate.py` covers the same case.
4. **PASS** — `pytest tests/ -q` → `59 passed in 0.29s`, exit 0. Confirmed
   the new `to_html()` tests in `tests/test_gate.py` and the CLI test
   `tests/test_rules_and_cli.py::TestCli::test_writes_html_report`.
5. **PASS** — `ruff check .` → `All checks passed!`, exit 0.

**VERIFIED**

CI on PR #4 (`test (3.11)`, `test (3.12)`) finished green
(https://github.com/nassim0014/feed-quality-gate/actions/runs/36206848239)
and the PR merged (squash) shortly after — merge rules pass (no
`.github/workflows/**` touched, no test removed/skipped, not a draft, no
conflict).
