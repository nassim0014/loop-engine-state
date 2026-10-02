# KINZ Competitor Intelligence — Project Context

> **Purpose**: persistent context for AI assistants across sessions. Read this
> first to understand the architecture and the decisions that are load-bearing,
> without re-reading the whole codebase.
>
> **For humans**: [README.md](README.md) is the user-facing guide — setup,
> workflows, troubleshooting. This file is the technical companion to it.

---

## Project Overview

**Repository**: `nassim0014/kinz-competitor-intelligence` (private)
**Owner**: Nassim K. (KINZ — Tunisian natural cosmetics brand)

The system answers three questions:

1. What are competitors selling, and at what price?
2. How visible are they on social media vs KINZ?
3. Which retail outlets could stock KINZ, and who hasn't been approached?

Two distinct entity types, and conflating them is the most common conceptual
error:

- **Competitors** (`competitors`) — rival brands, benchmarked on price and reach.
- **Outlets** (`parapharmacies`) — shops that could *sell* KINZ. Sales prospects.

They are separate tables deliberately. Putting outlets in `competitors` would
corrupt price matrices, market share and rankings, and `Competitor` has no
columns for GPS / rating / reviews / opening hours.

---

## Current State

Re-verified 2026-08-07 against `data/competitors.db` in
`~/Desktop/Github Projects/kinz-competitor-intelligence` — the machine's actual
working copy. (A previous version of this table was mistakenly re-verified
against a stale, unrelated second clone at `~/Github Projects/...` and reported
a "missing outlets table" that doesn't exist in this, the real, database —
corrected here.)

| Metric | Value |
|--------|-------|
| Competitors | 78 (54 active, 26 active *with* a live website) |
| Products | 1,905 (1,783 priced) |
| Price history rows | 1,789 |
| Retail outlets | 3,578 (2,752 with phone, all 3,578 with GPS, 2,961 with a rating) |
| Tests | 498, all passing |
| Dashboard tabs | 9 (8 wrapped in `st.fragment`; Market is the one exception, by design — it has no interactive widgets to isolate) |
| Scripts | 22 |

Outlet mix: 1,362 pharmacies, 974 parapharmacies, 759 cosmétique shops, 483
herboristeries. Top governorates: Tunis (1,267), Sfax (319), Sousse (281),
Médenine (211), Nabeul (205).

The "23 of the original ~70-competitor PDF seed are dead sites" note that used
to live here is also unverifiable against this DB (413 competitors, all
`is_active = 1`) and has been dropped rather than left stale — see flag above.

---

## Architecture

```
kinz-competitor-intelligence/
├── src/
│   ├── database.py          # SQLAlchemy models + engine (SQLite WAL / Postgres)
│   ├── config.py            # env configuration — see "Configuration precedence"
│   ├── pdf_parser.py        # parses the industry PDF (77 competitors)
│   ├── scheduler.py         # APScheduler; runs as the `scheduler` Docker service
│   ├── scrapers/
│   │   ├── web_scraper.py           # Playwright product/price scraper (2700+ lines)
│   │   ├── instagram_scraper.py     # instaloader metrics
│   │   ├── instagram_discoverer.py  # finds IG handles on competitor sites
│   │   ├── social_discoverer.py     # FB / TikTok / YouTube / LinkedIn handles
│   │   └── youtube_scraper.py       # YouTube Data API v3
│   ├── analyzers/           # market + price analysis
│   └── reporters/           # ReportLab PDF reports + email
├── scripts/                 # 14 CLIs — full catalog in README § Script reference
├── api/                     # FastAPI (routes: competitors, products, analytics)
├── dashboard/app.py         # Streamlit, 9 tabs, full CRUD on every table
├── tests/                   # 311 tests
│   ├── test_web_scraper.py
│   ├── test_pdf_parser.py
│   └── test_api.py          # route smoke tests — catches import/schema regressions
├── .github/workflows/
│   ├── scrape.yml           # weekly Monday 3 AM Tunis
│   └── tests.yml            # pytest on every push/PR
├── Dockerfile.{api,dashboard,scheduler}
└── data/
    ├── competitors_seed.example.json  # committed; placeholder contacts
    ├── competitors_seed.json  # GITIGNORED — real contact data, local only
    └── competitors.db         # gitignored — never committed
```

---

## ⚠️ Load-bearing decisions (do not regress)

These caused real production bugs. Each has a regression test or guard.

### 1. WooCommerce Store API must paginate

`_try_woocommerce_store_api()` **must** page through `&page=N`. The API caps
`per_page` at 100 and returns **no error** when truncating, so a single-page
request silently loses everything beyond 100 products.

This cost ~1,000 products — 888 from one competitor alone — and went unnoticed
because the numbers looked plausible. Tells: several competitors landing on
*exactly* 100.

Guard: `tests/test_web_scraper.py::TestStoreApiPagination`.

### 2. `.env` must not override real environment variables

`src/config.py` loads `.env` with **`override=False`**. Precedence is
**env var > `.env` > code default**.

With `override=True` (the old behaviour), `tests/conftest.py`'s isolation was
silently defeated and **the entire test suite ran against the production
database**, mutating real rows. It also meant container/CI-injected variables
could be clobbered by a mounted `.env`.

Guard: `tests/conftest.py` raises at import time if the resolved engine URL
looks like the production database.

### 3. `is_active` must be honoured when selecting scrape targets

`manual_scrape.py`, `social_discoverer.py` and `instagram_discoverer.py` all
filter `Competitor.is_active.is_(True)`. They previously did **not**, despite
docstrings claiming otherwise — so deactivating a competitor did nothing and
dead domains were re-scraped every run.

### 4. Report/endpoint code that reads model fields which don't exist

`ScrapingLog.scrape_type` / `.status` are plain Strings, not Enums —
calling `.value` on them raises `AttributeError`, and there is **no
`items_scraped` field**. This mistake was made twice and 500'd both
`/analytics/market-overview` and weekly PDF report generation.

Same class, 2026-08-29: `_add_instagram_leaderboard` read
`InstagramMetric.avg_likes` — no such column — fixed in PR (item 8a).
`api/routes/analytics.py:257-258` still reads `m.avg_likes` /
`m.avg_comments` on `InstagramMetric` (backlog item 8a-follow-up).

Every one of these only looked healthy because the relevant table
(`scraping_logs`, `instagram_metrics`) was empty until a real scrape ran.
The guard is a test that seeds a row and renders the output —
`tests/test_pdf_generator.py` does this for the PDF path.

### 5. SQLite-only setup must be conditional

`src/database.py` branches on the `DATABASE_URL` scheme. SQLite gets
`check_same_thread` + WAL PRAGMAs; Postgres gets a plain engine with
`pool_pre_ping=True`. The SQLite-specific setup previously ran
unconditionally, which would crash every Docker container on startup.

### 6. Parapharmacy scrapes must persist incrementally

A national run takes 8–12 hours. Holding results in memory until the end meant
an interruption lost everything — which happened three times.

Now: `on_batch` saves every `--batch-size` places (default 10), flushed from a
`finally:` block so Ctrl-C / SIGKILL still keeps work. Batch-handler exceptions
are **caught and logged, never raised** — a locked database must not abort a
multi-hour scrape.

`--resume` skips **individual places**, not just governorates:
`_persisted_place_urls()` seeds the seen-URL set from the database, so known
places aren't re-visited (~20s saved each). The DB is the record of what's
done; the checkpoint is a coarse index.

---

## Database Schema

### Competitor
id, company_name (unique), contact_person, phone, email, location, governorate,
website, instagram_handle, facebook_page, tiktok_handle, youtube_channel,
linkedin_url, products_offered (JSON), certifications (JSON), business_type,
year_established, **is_active**, created_at, last_scraped_at

### Product
id, competitor_id (FK), product_name, category, price_tnd, currency,
description, image_url, product_url, volume, is_available, first_seen_at,
scraped_at — UniqueConstraint(competitor_id, product_name)

### PriceHistory
id, product_id (FK), price_tnd, recorded_at, source ('scraper'/'api'/'manual')

### InstagramMetric / FacebookMetric / YoutubeMetric / LinkedinMetric
Per-platform follower/engagement counts, each FK to competitor, with recorded_at.

### ScrapingLog
id, competitor_id (FK), scrape_type, status, error_message, scraped_at
— see load-bearing decision #4.

### Parapharmacy (retail outlets — NOT competitors)
- id, name, outlet_type ('Parapharmacie'/'Pharmacie'/'Herboristerie'/'Cosmétique')
- phone, email, website, facebook_page, instagram_handle
- address, governorate, latitude, longitude, google_maps_url
- rating, reviews_count, opening_hours
- **is_stockist, contacted, notes** — human-owned pipeline fields, editable in
  the dashboard, **never overwritten by a re-scrape**
- source, scraped_at
- UniqueConstraint(google_maps_url)

`init_db()` auto-adds missing columns via `ALTER TABLE ADD COLUMN`. Idempotent.

---

## Key Technical Details

### Web scraper (`web_scraper.py`)
- Playwright (Firefox default) for JS-rendered pages
- **WooCommerce Store API tried first** — bypasses HTML entirely, ~100x faster
  (see load-bearing decision #1 about pagination)
- Pagination: infinite scroll, "Load More" buttons, next-page links
- Product-page fallback when a listing yields <3 products
- Detail-page enrichment scoped to `.summary` to avoid banner price matches
- Domain-parked detection ("domain for sale" / "hugedomains")

### Price extraction
- Returns `(price, currency)`; TND, EUR, USD, GBP + 15 Arabic currencies
- Arabic numeral conversion (٠-٩ → 0-9)
- Tunisian fix: integers >1000 divided by 1000 (97.000 = 97 TND)
- Price 0 → None; years 1900–2100 rejected as prices

### Product name validation (`is_valid_product_name`)
11 rules: blocklist, pure numbers, too short, all-caps single word, benefit
labels, category labels, punctuation-only, junk regex, emoji, colon-ending.
Multi-word all-caps names are **allowed** ("SOFT KISSES" is brand styling).

### Deduplication
Stage 1 by `product_url` (normalised); stage 2 by `normalize_product_name()`
(strips accents/punctuation, lowercases). Keeps the most complete entry.

### Parapharmacy scraper
- Google Maps via Playwright; 5 query types × 24 governorates × sub-locations
- Sub-location search matters: "herboristerie Tunis" returns 1 result,
  "herboristerie Le Bardo" returns 7
- GPS often missing from the detail panel — **extracted from the Maps URL**
  (`!3d<lat>!4d<lng>`) as a fallback, otherwise the dashboard map is empty
- Browser restarts periodically to avoid memory crashes

### Data quality
`qa_validate.py` runs 8 checks (impossible prices, missing fields, duplicates,
zero prices); `--fix` clears bad values. Runs automatically after each scrape.
DB backed up to `data/backups/` before each run.

### CI/CD
- **scrape.yml** — weekly Monday 02:00 UTC, two sequential batches. Batch 1
  hands its DB to batch 2 via a 1-day artifact (**not** a git commit — an
  earlier version committed the binary DB to `main` every week). Final results
  publish to a rolling `weekly-scrape-data` release. Nothing is committed to
  `main`.
- **tests.yml** — pytest on every push/PR.

---

## Dashboard (`dashboard/app.py`)

9 tabs, all with inline CRUD: Competitors, Products, Prices, Instagram,
Social Media, Market, Alerts, **Outlets**, **Distribution**.

Tabs 8–9 read `parapharmacies` and show a guided empty state until
`scrape_parapharmacies.py --import-to-db` has been run.

Save helpers: `save_competitor_changes`, `save_product_changes`,
`save_parapharmacy_changes` (matches by `id`, leaves `is_stockist`/`contacted`/
`notes` alone), `save_metric_changes` (generic for the four social tables),
`save_price_history_changes`, `save_social_handles`.

**Why manual entry is first-class**: Instagram/social discovery frequently
times out on Tunisian sites. The dashboard never requires a scraper to have
succeeded — every metric can be added, edited or deleted by hand.

---

## Common Commands

```bash
source venv/bin/activate        # required before everything below

# Competitor scraping
python scripts/manual_scrape.py --type web
python scripts/manual_scrape.py --type web --limit 5 --debug
python scripts/manual_scrape.py --type all

# Retail outlets (interruptible; rerun the same command to continue)
python scripts/scrape_parapharmacies.py --import-to-db --resume
python scripts/scrape_parapharmacies.py --import-to-db --resume --batch-size 5
python scripts/scrape_parapharmacies.py --import-to-db --resume \
    --governorates "Tunis,Sousse" --no-sub-locations

# Health + quality
python scripts/check_websites.py
python scripts/check_websites.py --mark-inactive
python scripts/qa_validate.py --fix

# Export / view
python scripts/export_csv.py --excel data/analyse_concurrentielle.xlsx
streamlit run dashboard/app.py
uvicorn api.main:app --reload --port 8000

# Tests
python -m pytest tests/
```

---

## GitHub Access

Private repo; a PAT with `repo` scope is required.

**Never write a token into a file, git config, commit or log.** The snippet
that used to live here embedded the PAT in plaintext in `~/.gitconfig` — the
exact thing it warned against. Use instead:

- `gh auth login` — stores via the OS keychain
- `git config --global credential.helper 'cache --timeout=3600'` — memory only
- An OS keychain helper (`osxkeychain`, `manager`, `libsecret`)

If a token leaks, revoke it immediately at
https://github.com/settings/tokens and rotate.

---

## How AI Assistants Should Use This File

1. **Read this first**, then README.md for user-facing behaviour.
2. **Check "Load-bearing decisions" before changing** config loading, the
   Store API path, `is_active` filtering, `ScrapingLog` access, database engine
   setup, or parapharmacy persistence. Each entry documents a bug that already
   happened.
3. **Update this file** when adding models, tabs, scripts, or making
   architectural decisions — and record *why*, not just *what*.
4. **Verify before documenting.** Numbers here come from the live database;
   re-query rather than copying stale figures forward.
