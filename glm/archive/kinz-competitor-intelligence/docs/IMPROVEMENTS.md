# Improvement backlog

The queue the `/improve` routine works from. One item per run, highest value
first. Items are added whenever something is noticed but is too far out of scope
to fix on the spot.

**Rules**

- Work the top unblocked item. Don't cherry-pick easy ones.
- One PR per item. If an item turns out to be three things, split it and re-rank.
- Move finished items to *Done* with the PR number. Don't delete them — the
  history is how the next session learns what has already been tried.
- If an item turns out to be wrong or no longer applies, move it to *Dropped*
  with the reason. That is a legitimate outcome.

---

## Now

### 1. ~~Decide whether to pin the dependency floors~~ ✅ — merged as PR #56
**Decision: pin majors only (owner decision #1).** `requirements.txt`
now uses `>=X.Y,<X+1.0` for every package — the floor stays where it was,
the ceiling is the next major. Minor + patch updates flow (security
fixes) without pulling in a major that may break the API surface. The
streamlit 1.60→1.61 `AppTest.from_file` surprise (#32) would have been
caught by the `<2.0` ceiling (1.61 is a minor, still under 2.0 — so the
ceiling wouldn't have prevented it, but the policy is sound for true
major bumps like streamlit 1.x→2.0).

### 2. ~~Split `dashboard/app.py` — extract the Market tab (3a)~~ ✅ — merged as PR #45
First piece of the original "split `dashboard/app.py`" item, broken out per
the backlog rules because the whole job (nine tabs, ~2,400 lines) is too big
for a single reviewable PR. The pattern: extract one tab per cycle to
`dashboard/tabs/<name>.py` as a `render_<name>_tab(...)` function, leave the
`with tabN:` block in `app.py` as a one-line call.

Market is first because it is the smallest tab (~54 lines), has no interactive
widgets (no `data_editor`, no save paths) and no `@st.fragment` wrapper —
lowest-risk place to establish the extraction pattern. Pre-work: pure UI
helpers (`kpi_card`, `empty_state`, `status_pill`, `cap_rows_for_editor`,
`df_to_csv`, `MAX_*` constants) move to `dashboard/ui.py` so tab modules can
import them without triggering a full dashboard rebuild at import time.

### 3. ~~Split `dashboard/app.py` — extract the Alerts tab (3b)~~ ✅ — merged as PR #46
~137 lines, has a price-drop slider (interactive, fragment-wrapped) and the
scraping-logs section. Same pattern as 3a, but exercises the fragment +
slider case. Next after Market to keep the simple-pattern PRs close together.

### 4. ~~Split `dashboard/app.py` — extract the Distribution tab (3c)~~ ✅ — merged as PR #47
~238 lines. Includes the outlets map (`MAX_MAP_MARKERS`). Same pattern.

### 5. ~~Split `dashboard/app.py` — extract the Outlets tab (3d)~~ ✅ — merged as PR #48
~254 lines. Has an editable dataframe with save paths — the first extraction
that touches a write path. Comes after the read-only extractions so the
pattern is established.

### 6. ~~Split `dashboard/app.py` — extract the Social Media tab (3e)~~ ✅ — merged as PR #49
~335 lines, the largest. Multiple sub-sections (YT, FB, LinkedIn metrics +
handle editor). Same pattern; may want a further split-first pass.

### 7. ~~Split `dashboard/app.py` — extract Prices, Instagram, Products, Competitors tabs (3f–3i)~~ ✅ — merged as PR #50 (Prices), #51 (Instagram), #52 (Products), #53 (Competitors)
The remaining four tabs, each with save paths. Order by size: Products (129),
Prices (170), Instagram (172), Competitors (226).

### 8a. ~~Coverage — `src/reporters/pdf_generator.py` (16% coverage)~~ ✅ — PR (2026-08-29)
`tests/test_pdf_generator.py` builds a report end-to-end against in-memory
SQLite: the empty-database path (every "No data available" branch) and a
seeded path (every table branch). Coverage 16% → 98%.

The seeded path surfaced a **live crash**: `_add_instagram_leaderboard`
read `m.avg_likes`, but `InstagramMetric` has no such column — so weekly
report generation raised `AttributeError` the moment any Instagram metric
row existed. Same phantom-field class as CONTEXT.md load-bearing decision
#4. Fixed in the same PR: the leaderboard now shows `following_count`
(a real column) in that slot. Regression proven by reverting the fix.

### 8a-follow-up. `api/routes/analytics.py` has the same `avg_likes` / `avg_comments` phantom fields — crash fixed, drop-vs-add still NEEDS OWNER DECISION
`/analytics/instagram-leaderboard` (not `/competitor-positioning` — that
name was wrong; `api/routes/analytics.py:257-258` at the time this item was
written is the leaderboard's field-building dict, confirmed by reading the
current file rather than trusting the old citation) builds its leaderboard
dict from `m.avg_likes` and `m.avg_comments` on `InstagramMetric`. Neither
column exists, so the endpoint 500s as soon as a metric row is present —
was masked only by `instagram_metrics` being empty in the existing smoke
test (exactly the CONTEXT.md #4 pattern, and the same shape as 8a's PDF
crash). Confirmed live by reverting the fix below and watching the new test
fail with exactly `AttributeError: 'InstagramMetric' object has no
attribute 'avg_likes'`, then restoring it.

**Crash fixed** (same immediate, non-presumptuous move as the `price_unit`
bug's first fix in `api/routes/products.py`, PR #44): both fields now go
through `getattr(m, "avg_likes", None)` / `getattr(m, "avg_comments", None)`
instead of a raw attribute access, matching the None-when-absent contract
every other consumer already gets. Added
`tests/test_api_analytics.py::TestInstagramLeaderboardPhantomFields` (a
real endpoint-level test seeding a metric row against the app's actual
database, not this file's own private in-memory `db_session` fixture used
by the analyzer-function tests above it — those are a different database
the endpoint never sees).

**Still open, still the owner's call** (precedent: item 9 was the same
shape and the owner chose "drop"):
- **Drop** the two keys from the response dict entirely (matches what 8a
  did for the PDF, and item 9's decision), or
- **Add** `avg_likes` / `avg_comments` columns to `InstagramMetric` —
  needs a `new_columns` entry in `src/database.py` (CLAUDE.md), and a
  scraper actually populating them, which today nothing does.

### 8c. Coverage — `src/scrapers/*` (9-25% coverage)
Third and lowest-priority piece of the former item 8. Per this repo's
automation rules the scrapers are never run by this loop, and meaningfully
testing them needs mocked HTTP/Playwright fixtures — a bigger investment
than 8a/8b. Leave ranked last rather than picked next.

### 11. ~~`dashboard/tabs/prices.py` — price-write path is 0% covered, same bug shape as 3 prior data-loss PRs~~ ✅ — PR #69
`save_price_history_changes()` coverage 40% → 77% (`tests/test_dashboard_tabs_prices.py`, 18 tests). Both bugs named below were real, and fixed by switching to `dashboard.saves.to_price`/a new `_changed()` helper — the exact fix already applied once for the identical bug in the Products editor (`dashboard.saves.to_price`/`_differs`):

  * **Add guard** (`if pd.isna(price) or not price`): confirmed exactly as described — a price of 0.00 was silently skipped, no row added, no error.
  * **Edit coercion** (`float(v) if pd.notna(v) and v else None`): NOT what was described. `price_tnd` is `nullable=False` at the DB level, so coercing 0.00 to `None` does not silently null it — it raises `IntegrityError` on `db.commit()`, and because every edited row in the data_editor is saved under one commit, that rolled back **every other edit in the same save**, not just the zero-priced row. Proven in `test_regression_unfixed_coercion_corrupts_the_whole_batch` by reverting the fix and watching a sibling row's genuine edit vanish too.
  * Found while testing: the change-detection line right after it, `str(new_val or "") != str(old_val or "")`, has the same 0.0-collapses-to-"" bug independently — fixed alongside (`_changed()`), since leaving it would silently no-op a price set to exactly 0.00 even with the cast fixed.
  * The manual "Add a price record" form had the identical truthy guard (`pr_price:`) — fixed the same way (`pr_price is not None`). **Not covered by a test**: that form is Streamlit UI code and this PR did not drive it through `AppTest`; the fix is exercised only by inspection and by the same `_changed`/`to_price` unit tests.

Remaining uncovered in `prices.py` (77% → some ceiling below 100%): the chart-rendering branches and the manual-add-form body itself — UI code, not write-path logic.

### 12. `dashboard/tabs/social.py` — `save_social_handles()` (creates competitors on the fly) is 0% covered   `source: coverage`

`social.py` is the least-covered dashboard tab at 32% (168 of 247 statements missed). Lines 52-116 are the whole body of `save_social_handles()`, the only dashboard path that creates a `Competitor` row from free-text input (`db.add(Competitor(...))` + `flush`), dedupes it by exact `company_name` match, renames existing competitors, and blanks handles for removed rows — a write against the table the rest of the schema keys off, where a duplicate-creation or mis-resolved-competitor bug corrupts shared state rather than one row. Lines 216-226, 310-320 and 394-403 (the YouTube/Facebook/LinkedIn manual metric-add forms) are also uncovered but are insert-only count writes with a `if comp:` guard — lower priority; test `save_social_handles()` first.

### 13. `src/database.py`'s migration error-branch (duplicate-column vs. database-locked) is untested   `source: coverage`

Lines 372-388 of `init_db()` — the exception branch of the `ALTER TABLE ADD COLUMN` migration loop — are uncovered. The branch distinguishes "duplicate column" (harmless, a concurrent call won) from every other failure such as "database is locked" (migration did not happen), a distinction added after both were previously swallowed identically, per the comment at that location. Two tests against a temp SQLite engine — one raising a duplicate-column error, one raising a locked-database error — would pin the behavior. Note: the non-duplicate path currently only warns and continues rather than raising, so callers proceed on an unmigrated schema either way; that's existing, intentional-looking behavior, not something to silently change while adding the test.

### 14. Four 0.x dependencies still have a same-minor-version ceiling, narrower than the pin-majors-only policy (item 1) intended   `source: deps`

`pip list --outdated` shows `aiosqlite` 0.19.0 (latest 0.22.1, 3 minor releases behind) and `asyncpg` 0.29.0 (latest 0.31.0). `requirements.txt` pins `aiosqlite>=0.19,<0.20`, `asyncpg>=0.29,<0.30`, `python-multipart>=0.0.6,<0.1`, and `secure-smtplib>=0.1,<0.2` — each ceiling is "next minor," not "next major." Item 1's own fastapi entry already reasoned through this exact 0.x-versioning ambiguity ("the 'major' boundary is the 0.minor line... widening to <1.0 lets fastapi float") but applied it only to fastapi, not these four. There's also no `.github/dependabot.yml` in the repo, so nothing surfaces this automatically.

Loop-Agent: backlog-refresh / claude / laptop

## Next

### 9. ~~`ProductBase` has five fields with no backing `Product` column~~ ✅ — merged as PR #54
**Decision: drop fields (owner decision #2).** Removed `subcategory`,
`price_unit`, `ingredients`, `volume_ml`, and `product_page_url` from
`ProductBase` in `api/routes/products.py`. Also removed the
`getattr(p, "price_unit", None)` workaround in the price-comparison
matrix (the field no longer exists at all). The `Product` model in
`src/database.py` never had these columns — the schema fields were dead
API surface that always returned `None`.

### 10. ~~`src/analyzers/price_analyzer.py` is dead code~~ ✅ — merged as PR #55
**Decision: wire up + dedupe (owner decision #3).** `api/routes/analytics.py`
now imports and calls all five `price_analyzer` functions:
- `/price-changes` delegates to `detect_price_changes()` (was an inline
  duplicate — deleted ~25 lines of reimplemented logic)
- `/price-statistics` (new endpoint) → `get_price_statistics()`
- `/category-price-comparison` (new endpoint) → `get_category_price_comparison()`
- `/competitor-positioning` (new endpoint) → `get_competitor_price_positioning()`
- `/price-trend/{product_id}` (new endpoint) → `calculate_price_trend()`

17 new tests in `tests/test_api_analytics.py`: 12 direct analyzer-function
tests (in-memory SQLite) + 5 endpoint wiring tests. Coverage of
`price_analyzer.py` lifted from 26% (import-only) to ~90%+.


## Done

- **PR (2026-09-13)** — Item 8b: coverage for `src/reporters/email_sender.py`
  (19% → 100%) via `tests/test_email_sender.py` (15 tests, `smtplib.SMTP`
  mocked throughout — no real network). Covers the recipients-required
  guard on both `send_notification` and `send_report`, the TLS handshake
  order (`ehlo` → `starttls` → `ehlo` → `login`, and that `login` is
  skipped without credentials), the PDF-attach failure path, generated
  vs. caller-supplied subject/body, and `test_connection`. No production
  code changed. First pass at the recipients-guard test used a bare
  `EmailSender` with no mock, which passed even with the guard code
  deleted — the real `smtplib.SMTP` call just failed on DNS in the
  sandbox and returned `False` for an unrelated reason, proving nothing.
  Fixed to mock SMTP and assert it is never even instantiated when the
  guard fires; re-tested against the deleted guard and it now fails as
  expected. pytest 611 → 626, `ruff` clean.

- **PR (2026-08-29)** — Item 8a: coverage for `src/reporters/pdf_generator.py`
  (16% → 98%) via `tests/test_pdf_generator.py` (7 tests, empty-DB and
  seeded-DB report builds against in-memory SQLite). Fixed a live
  `AttributeError` crash in `_add_instagram_leaderboard` (`m.avg_likes` —
  no such column on `InstagramMetric`); regression proven by reverting.
  Filed 8a-follow-up for the identical bug in `api/routes/analytics.py`
  (needs owner decision, separate file). `pytest` 603 → 610, `ruff` clean.

- **PR #45** — Extracted the Market tab to `dashboard/tabs/market.py` as the
  first piece of the original "split `dashboard/app.py`" item (now broken
  into 3a–3i, see "Now" above). The whole job is too big for one reviewable
  PR (~2,400 lines, nine tabs), so this PR establishes the pattern with the
  smallest, lowest-risk tab: Market is read-only, has no interactive widgets,
  no save paths, no `@st.fragment` wrapper. ~54 lines extracted.

  Pre-work that enabled the extraction: pure UI helpers (`kpi_card`,
  `empty_state`, `status_pill`, `cap_rows_for_editor`, `df_to_csv`,
  `MAX_EDITOR_ROWS`, `MAX_DISPLAY_ROWS`, `MAX_MAP_MARKERS`) moved from
  `dashboard/app.py` to a new `dashboard/ui.py`. Without that move, the
  Market tab module would have had to `from dashboard.app import kpi_card,
  empty_state`, which triggers a full dashboard rebuild at import time —
  `tests/test_module_imports.py` would have run the entire dashboard once
  per parametrised module, and the new `dashboard.tabs.market` import would
  have been circular.

  Verified the extraction actually works end-to-end: forcing
  `render_market_tab` to `raise RuntimeError(...)` makes
  `test_app_runs_with_data` fail with that exact RuntimeError; restoring it
  makes the test pass again. The 578-test suite (575 baseline + 3 new
  parametrised cases on the three new modules — `dashboard.ui`,
  `dashboard.tabs`, `dashboard.tabs.market` — picked up automatically by
  `tests/test_module_imports.py`) is green. `ruff check .` is clean.

  Three imports that were only used inside the now-extracted tab body
  (`get_market_overview`, `get_competitor_rankings` from
  `src.analyzers.market_analyzer`, plus the never-called `status_pill`)
  were dropped from `dashboard/app.py`. `status_pill` was dead code in
  app.py before this PR — defined but never called anywhere in the file.
  It is kept in `dashboard/ui.py` because it is a public UI helper other
  tabs may want.

  Item 2 in the previous backlog revision ("Replace the deprecated
  starlette TestClient/httpx pairing") was already closed by PR #40 but
  had not been moved to Done. Fixed here.

- **PR #44** — Coverage gap for `api/routes/products.py` (item 4), 56% ->
  100%. `test_api.py`'s smoke test hit `/products/` once with no query
  parameters — proves the router imports, nothing else. Every filter branch
  (`category`, `competitor_id`, `has_price`, `search`), the single-product
  GET, price history, the price-comparison matrix, `/stats/overview`, and the
  `record-price` write had zero coverage. Added `tests/test_api_products.py`,
  one test per branch/route, driving the real FastAPI app through
  `TestClient` against the isolated test database (never production — see
  conftest.py's guard).

  The backlog description for this item was half wrong: it said the gap
  included "single-product/create/update/delete routes," but this router has
  no POST/PUT/DELETE for a product — those go through `dashboard/saves.py`,
  not the API. Corrected here.

  Writing the price-matrix tests surfaced a real bug, not just a coverage
  gap: `price_comparison_matrix()` did a raw `p.price_unit` attribute access
  on the `Product` ORM object, but `Product` has no `price_unit` column — it
  exists only in the Pydantic `ProductBase` schema, alongside four other
  schema fields with no backing column (`subcategory`, `ingredients`,
  `volume_ml`, `product_page_url`). Every other consumer of `price_unit`
  goes through Pydantic's `from_attributes`, which silently resolves a
  missing attribute to the field's `None` default; this raw access doesn't
  get that fallback, so the endpoint had always raised `AttributeError` and
  500'd whenever called with at least one priced product. Fixed with
  `getattr(p, "price_unit", None)`, matching the same None-when-absent
  contract the field already has everywhere else. Verified the fix is what
  the new tests actually catch: reverted it, confirmed exactly the two
  price-matrix tests failed and the rest stayed green, then restored.

  The other four schema/model mismatches (`subcategory`, `ingredients`,
  `volume_ml`, `product_page_url`) are the same shape of latent bug — they
  just don't crash, since they're only ever read through `ProductResponse`'s
  `from_attributes` fallback rather than raw ORM access. Not fixed: resolving
  it needs an owner decision (add the missing columns via migration +
  backfill, or drop the dead schema fields).
- **PR #43** — Coverage gap for `api/routes/competitors.py` (item 4), 61% ->
  100%. `test_api.py`'s smoke test hit `/competitors/` once with no query
  parameters — that proves the router imports, nothing else. Every filter
  branch (`governorate`, `has_website`, `is_active`, `search`), the
  single-competitor GET, all three writes (POST/PUT/DELETE), the nested
  `/products` endpoint and `/stats/overview` had zero coverage; a coverage
  run's missing-line report confirmed each was a fully-unexecuted function,
  not a partial branch gap. Added `tests/test_api_competitors.py`, one test
  per branch/route, driving the real FastAPI app through `TestClient` against
  the isolated test database (never production — see conftest.py's guard).
  No route behaviour changed. Verified two of the fourteen new tests actually
  catch a regression, not just pass vacuously: temporarily neutered the
  `governorate` filter and removed the 404 check from `delete_competitor`,
  confirmed exactly the two matching tests failed and the rest stayed green,
  then reverted (diff on `api/routes/competitors.py` is empty).
  `api/routes/products.py` (56%) is the same shape of gap and is next.
- **PR #41** — Coverage gap analysis (item 4). Ran `pytest --cov
  --cov-report=term-missing` against `main` (52% overall).
  The scraper and reporter modules are predictably low (9–25%: Instagram/
  LinkedIn/YouTube scrapers, `pdf_generator`, `email_sender`) and expected —
  CLAUDE.md already rules out running scrapers in this loop, and they need a
  live network or a rendered PDF/email to exercise meaningfully. Two findings
  worth carrying forward instead of a blanket "write more tests": item 5
  (`price_analyzer.py` is dead code, not just undertested) and item 6 (API
  route filter/error branches). Declined to add a coverage gate, per the
  item's own instruction — a percentage floor pressures whoever fills it into
  writing tests that execute lines without asserting anything.

- **PR #40** — Replaced `httpx>=0.27.0` with `httpx2>=2.0.0` in
  `requirements.txt`, clearing the last deprecation warning. Evaluated
  `httpx2` first, as the item asked: it's the httpx project's own successor
  (Pydantic Services Inc. / the original httpx author), and nothing else in
  the dependency tree requires `httpx` directly. Verifying it surfaced a real
  bug: `tests/test_api.py` gated its 13 tests on
  `pytest.importorskip("httpx")`, which — once only `httpx2` is installed,
  exactly what a fresh CI install now produces — makes the whole module skip
  silently (exit code 5, 0 collected, no failure). Fixed the guard to accept
  either backend and pinned it with unit tests. Demonstrated in a from-scratch
  venv (not a copy of the tracked one — an earlier attempt to copy `venv/`
  turned out not to be isolated, since the copied `pip`/`pytest` scripts kept
  absolute shebangs pointing at the original; caught and reverted before
  anything shipped): old guard + httpx2-only = 0 tests collected; new guard +
  httpx2-only = the same 528 tests the tracked venv collects, all passing.
- **PR #39** — Coverage gap analysis (item 4) turned up that the
  except/rollback/raise wrapper in all four `dashboard/saves.py` write
  functions had never run under any test — every existing test exercises the
  success path only, so nothing pinned down that a failed commit actually
  rolls back rather than partially applying. Added one test per function that
  forces `db.commit()` to raise and asserts `db.rollback()` ran and no row
  persisted. Also covered the blank-`product_name` skip in
  `apply_product_changes` (saves.py's own docstring flags it as protecting
  against one bad cell rolling back an entire batch) — untested despite being
  exactly the kind of edge case that class of bug hides in. `dashboard/saves.py`
  coverage: 91% -> 97%. Verified each new test actually catches its bug:
  temporarily reintroduced the old behavior (dropped the `product_name` skip;
  removed `db.rollback()` from `apply_metric_changes` specifically, leaving
  the other three intact) and confirmed only the matching test failed, then
  restored — no behavior change shipped, `dashboard/saves.py` diff is empty.
  Also evaluated item 2 (`httpx2`) without applying it — later resolved by
  PR #40 above.
- **PR #33** — Cleared two of the three deprecation warnings. The
  `datetime.utcnow()` one had a trap: the replacement the warning suggests,
  `datetime.now(timezone.utc)`, returns an AWARE datetime, while all 13
  DateTime columns hold naive UTC and ~7,350 rows are already stored that way.
  Mixing them makes Python raise `TypeError` on exactly the comparisons the
  analyzers and API do. A `utcnow()` helper keeps the naive semantics; tests
  pin the contract and an AST scan stops `datetime.utcnow` returning. Pydantic
  `class Config` became `ConfigDict`. The starlette/httpx one is resolved by
  PR #40 below.
- **PR #32** — Fragmented all six remaining interactive tabs: Competitors and
  Products (by the scheduled improve cycle), then Prices, Instagram, Social
  Media and Distribution, finishing the work started in #22/#24.

  Measured first, against the real database: a full rerun costs 1,121 ms of
  tab bodies and **Prices alone was 545 ms of it (48.6%)**. That tab, not an
  even split across six, was where the win was.

  Market is deliberately left unfragmented and now asserted to stay that way —
  it has zero rerun-triggering widgets, so nothing inside it can start a
  fragment rerun and wrapping it would buy nothing.

  Added `test_every_interactive_tab_is_a_fragment`, which reads the source
  rather than the rendered output: widget keys exist whether or not a tab is
  wrapped, so the older key-presence test could never have told the difference.
  Also seeded an `InstagramMetric` in the smoke fixture — without one, the
  Instagram tab rendered neither its editor nor its leaderboard, so half that
  tab had never been executed by any test.
- **PR #31** — (Same PR as the import smoke test below, two commits.) Extracted `save_product_changes`, the last inline save helper.
  Confirmed the zero-price suspicion and found it was **two** independent bugs,
  either of which alone erases a 0.00 TND price: the cast (`and v` is falsy for
  0) and the change detection (`str(x or "")` maps None, "" and 0.0 all to ""),
  so fixing one would have hidden the other. Also stopped a blank
  `product_name` from raising on commit and rolling back every other edit in
  the same save. No live data was affected — the database has 0 products
  priced at 0 and 122 priced NULL, and both call sites are manual-entry paths,
  not scrapers.
- **PR #31** — Import smoke test over all 51 modules. **The reason this item
  gave for itself was wrong**, and the correction is the useful part: the
  `pdf_generator` `NameError` it cited was a *runtime* failure inside a method,
  so the broken module imported perfectly fine and an import test would have
  passed. `ruff --select F821` reports it (4 hits on the pre-fix file) and `F`
  is already in this repo's ruff config, so that bug class was already covered
  by the lint job added in the same commit that fixed it. The test was still
  worth adding for a different class ruff cannot see — a dependency used but
  missing from `requirements.txt`, a circular import, module-level code that
  raises. Demonstrated: on a module importing a nonexistent package, ruff
  reports "All checks passed" and this test fails.
- **PR #30** — Two things. (a) Extracted `save_competitor_changes`, closing the
  save-helper work. No data-loss bug this time (all-string columns, no foreign
  key), but it did fix an `AttributeError` on saving a blank new row. (b) Made
  the test session start from an empty database: local runs inherited
  `data/test_competitors.db` from the previous run, so tests asserting on
  counts could pass or fail depending on history, and CI — where the file does
  not exist — never saw it. Caveat recorded in the PR: the original failures
  could not be reproduced after cleaning, so the causal chain is inferred
  rather than demonstrated.
- **PR #29** — Extracted `save_metric_changes` (Instagram/YouTube/Facebook/
  LinkedIn) into `dashboard/saves.py` as `apply_metric_changes`. Found and
  fixed a second FK-corruption bug in the same family as #23's: the update
  path treated `company_name` as an assignable field, so saving any existing
  metric row overwrote its `competitor_id` with the company name string.
- **PR #26** — Untracked the 77 real contacts; committed a placeholder example
  instead. Owner chose this over leaving it or scrubbing. Note the caveat: git
  history still contains the file, and clearing that needs a force-push rewrite
  that would break every existing clone.
- **PR #24** — Fragmented the Outlets browser. Found four smoke tests that had
  been asserting against another test's stale cached empty frames.
- **PR #23** — Extracted `dashboard/saves.py`; fixed a bug where every save of
  the Outlets tab nulled `reviews_count` for every row on screen.
- **PR #22** — Alerts slider as a fragment.
- **PR #20** — `dashboard/analysis.py` plus 19 unit tests and 4 perf budgets.
- **PR #17** — Cut ~5.7 s per rerun: the price chart was drawing 1,768
  single-point traces; the alerts loop was O(products).
- **PR #19** — Recovered the outlet classifier, which was pushed but never
  reached `main`.
- CI foundations: `pyproject.toml`, ruff, the `Lint` + `Tests` workflow.
- The four founding issues: Dockerfiles added; the plaintext-PAT snippet in
  `CONTEXT.md` replaced with a memory-only credential helper; `scrape.yml` no
  longer commits the binary database to `main`; seeded contacts documented.

## Dropped

- **`black` formatting** — would rewrite 42 of 54 files, burying real diffs under
  reformatting for no correctness gain. Ruff's error-only rules do the work that
  matters.
- **Running Claude inside GitHub Actions** — needs an API key in repository
  secrets and has no natural spend ceiling. The scheduled local routine gets the
  same result without either problem.
- **Targeted cache invalidation instead of `st.cache_data.clear()`** — measured
  at ~60 ms of benefit across 21 separate edits to write paths. Bad trade.
