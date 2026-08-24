# KCI data quality — analyst findings

Updated by the `kinz-competitor-analyst` scheduled task. Same headings every
run so diffs are meaningful; counts first, then the specific rows that changed.

## Run: 2026-08-24

### State
- Competitors: 78 total, 54 active, 26 active+website
- Products: 1,905 (1,783 priced)
- Price history rows: 1,789
- Outlets: 3,923 (0 flagged `is_stockist`)
- Local DB last scrape: **2026-07-30 17:07 UTC — 25 days old, stale.** Local
  dashboard figures above are from that scrape; the cloud runs below do not
  write to this local DB.

### Data quality (qa_validate.py, read-only)
- missing_price: 122 products (6.4%)
- missing_category: 161 products (8.5%)
- missing_description: 93 products (4.9%)
- short_description: 25 products (<20 chars)
- **Concentration check:** missing_price is NOT evenly spread — ECOVILLAGE
  NATURAL BEAUTY alone accounts for 67/122 (55% of all missing prices), which
  is 67/85 (79%) of that competitor's own catalog. Looks like a parsing bug on
  that site's price field, not incidental gaps. missing_category concentrates
  159/161 on BIO TUNISIA MAHDIA, but that's only 16% of its 984-product
  catalog (the largest in the DB) — proportionally unremarkable.

### Website health (check_websites.py, read-only)
- 25/26 alive (HTTP 200), 1 recoverable timeout: HERBES DE TUNISIE (no
  response in 20s). No dead/parked sites found. Websearch for a replacement
  URL turned up nothing specific to this company — likely transient, not
  worth acting on yet.

### Scrape-failure triage (local DB, last local scrape 2026-07-30)
- 7 active+website competitors have zero products. Two categories:
  - **Real scraper bug (status=success, 0 products):** BIO GATRANA, NAKAWA,
    NOPAL TUNISIE — all three sites are alive today. Scraper logged success
    but captured nothing; likely a layout change or selector break on these
    three sites specifically. Worth a look at the scraper config for these.
  - **Connectivity errors at scrape time (not necessarily dead):** AGROLINE
    (DERMAFIG) — timeout; HERBES DE TUNISIE — timeout; MED EXOIL —
    SSL_ERROR_BAD_CERT_DOMAIN; NOPALISSE NATURE — SSL_ERROR_BAD_CERT_DOMAIN.
    All four are alive (HTTP 200) as of today's website-health check, so
    these look transient/recoverable, not dead sites.
- No WooCommerce pagination regression found (zero competitors with exactly
  100 products).

### Price movements
- No price_history rows in the last 14 days to compare — the most recent
  price_history record is also 2026-07-30 (same stale local scrape). This is
  an absence-of-data result, not a "nothing moved" result.

### GitHub Actions cloud scrape (`scrape.yml`)
- Last 5 runs: 2026-08-24 schedule ✅ (42m40s) · 2026-08-21 dispatch ✅
  (44m55s) · 2026-08-21 dispatch cancelled (1m14s, manual) · 2026-08-17
  schedule ❌ (4m32s) · 2026-08-10 schedule ❌ (4m40s).
- The two 2026-08-17/08-10 failures both show the known
  `COMPETITORS_SEED_JSON`-secret-unset pattern (seeds 3 fake competitors →
  Batch 2 gets 0 products → `export_csv.py` writes nothing → release-upload
  step glob-fails → job marked failed).
- **Confirmed resolved and holding unattended:** the secret was set
  2026-08-21T08:10:11Z (`gh secret list`). The 2026-08-21 dispatch run and,
  more importantly, the first *scheduled* run since the fix (2026-08-24
  03:05 UTC) both completed clean — no seed-warning annotation, both batches
  succeeded, no release-upload failure. Batch 1 took 28m26s (vs ~1m30s when
  scraping the 3-fake-competitor placeholder), consistent with a real
  77-competitor scrape.
- **Still open — seed-resurrection bug:** the 2026-08-24 run's
  `scrape-summary` artifact reports "Total competitors: 77", i.e. every
  cloud run still seeds all 77 competitors as active (`is_active=True` is
  hardcoded in `seed_from_json.py`), including the 24 that are `is_active=0`
  locally (retired dead/parked sites). Cloud runs are wasting time
  re-attempting known-dead sites and their per-batch population doesn't
  match the true 54-active set. Not yet fixed; no PR opened (report-only
  per task scope).

### Needing owner decision (unchanged across runs unless noted)
1. HERBES DE TUNISIE — one recoverable timeout today, no action needed yet.
2. ECOVILLAGE price-parsing bug — 79% of its own products missing price;
   worth a scraper look.
3. BIO GATRANA / NAKAWA / NOPAL TUNISIE — scraper reports success but 0
   products; likely layout/selector break, worth investigating.
4. Seed-resurrection bug in `seed_from_json.py` (is_active hardcoded True) —
   still unfixed, confirmed live again this run.
5. Local DB is 25 days stale — run a local scrape when convenient; cloud
   scrape does not update it.
