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
