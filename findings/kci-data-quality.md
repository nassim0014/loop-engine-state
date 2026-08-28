# KCI data quality — analyst findings

Updated by the `kinz-competitor-analyst` scheduled task. Same headings every
run so diffs are meaningful; counts first, then the specific rows that changed.

## Run: 2026-08-28

### State
- Competitors: 78 total, 54 active, 26 active+website  *(unchanged since 08-24)*
- Products: 1,905 (1,783 priced)  *(unchanged)*
- Price history rows: 1,789  *(unchanged)*
- Outlets: 3,923 — `is_stockist` 0, `contacted` 0, `notes` empty on all 3,923.
  *(unchanged — 4th run running; still needs a one-line owner confirmation that
  the sales-pipeline fields are simply not entered yet, not lost.)*
- Local DB last scrape: **2026-07-30 17:07 UTC — 29 days old, stale.** No local
  scrape since. Approaching the point where the dashboard's July snapshot is
  misleading for any week-over-week read.

### Data quality (qa_validate.py, read-only)
- missing_price: 122 (6.4%) · missing_category: 161 (8.5%) ·
  missing_description: 93 (4.9%) · short_description: 25  *(all identical to
  08-24 and 08-26 — same frozen July data.)*
- ECOVILLAGE missing_price concentration unchanged (67/85 = 79% of its own
  catalog; batch-2 site so cloud release never carries it).
- **NEW — wrong-price cluster on FLORAISON natural beauty (batch-1 site, so
  this one IS in the cloud release too).** 13 of ~70 FLORAISON products are
  pinned to exactly **350.0 TND** — far outside its real range (12–180 TND).
  `qa_validate.py` does not flag it because 350 is a "plausible" number and the
  check only looks for nulls, not identical-value clusters.
  - Confirmed artefact, not real prices: in the same 2026-07-30 scrape, the
    detail-page enrichment pass corrected 6 of these from 350 → real
    (Routine Éclat 350→137, Routine Anti-âge 350→145, Crème Exfoliante
    Comfort 350→48, Sérum Hair Pro 350→34, Lavender & Sage 350→24, Sérum
    Déo Roll-On Aquarelle 350→29). The other 13 never got corrected.
  - One of the 13, *"Parlons de Sunguard SPF50+"*, is a **blog article
    ingested as a product**.
  - **Root cause (two interacting caps in `src/scrapers/web_scraper.py`):**
    (a) detail-page enrichment — the reliable price source — is hard-capped
    at the first 15 products (`products_to_enrich = list(result.products[:15])`,
    line 1217; also `[:15]` at line 1066). FLORAISON has ~70, so ~55 keep
    whatever the listing card matched. (b) The Stage-8 "all identical price →
    banner match, clear them" guard only fires when **every** priced product
    shares one value (`len(unique_prices) == 1`, line 1313); FLORAISON has
    plenty of real prices, so the partial 350 cluster slips straight through.
    350 is almost certainly a "livraison gratuite à partir de 350 DT"
    free-shipping threshold on the listing page.
  - **Proposed fix (reported only, no PR per task scope):** raise or remove
    the 15-item enrichment cap (or prioritise enriching products whose price
    equals the modal value), and widen the Stage-8 guard to clear a *cluster*
    of ≥N identical prices that are statistical outliers vs the rest of the
    catalogue, not only the all-identical case. Add a fixture test with a
    mixed real/banner price list. Separately, exclude `/blog/` and article
    URLs from product discovery so "Parlons de…" stops being a product.

### Website health (check_websites.py, read-only)
- 25/26 alive (HTTP 200). Same single recoverable timeout: **HERBES DE
  TUNISIE** (no response in 20s — 3rd run in a row). Still likely transient;
  websearch still turns up no clear replacement URL. Not worth acting on.
- NAKAWA still reported "alive HTTP 200" by the health check (parked-domain,
  confirmed 08-26 by page title *"Nom de domaine à vendre"* — not re-fetched
  this run). Still active in the DB; still needs a manual retire. `--mark-inactive`
  will not catch it.

### Scrape-failure triage
- Local `scraping_logs` unchanged — all rows dated 2026-07-30. Same 7
  active+website/0-product competitors as 08-26; classifications from that run
  stand (NAKAWA parked, BIO GATRANA React SPA, NOPAL TUNISIE B2B-no-cart,
  AGROLINE/MED EXOIL/NOPALISSE/HERBES DE TUNISIE transient connectivity —
  AGROLINE scraped 29 products fine in the 08-24 cloud run).
- No WooCommerce pagination regression (no competitor at exactly 100 products).

### Price movements
- Still nothing. Most recent price_history row is 2026-07-30; no movement
  window exists. The only "changes" the query surfaces are the within-run
  350→real enrichment corrections described above, not market moves.

### GitHub Actions cloud scrape (`scrape.yml`)
- Last 5 runs **unchanged since 08-24** (no new run has fired; next schedule
  ~2026-08-31): 08-24 ✅ · 08-21 dispatch ✅ · 08-21 cancelled · 08-17 ❌ ·
  08-10 ❌. Seed secret still set. 08-10/08-17 = resolved secret-unset pattern.
- **STILL CRITICAL — batch 2 persists nothing.** Full evidence in the 08-26
  section below; nothing has changed. Every weekly release still carries only
  batch-1 competitors (~10 of 77, ~1,300 products), silently dropping KARINA,
  ORGANICA, PERFECT BIO, ECOVILLAGE, STÉ KINZ, MELIORA, PUNICA, TVH, RIVILIA,
  NURESSENCE (~600 products, ~40% of catalogue). Fix is the
  `manual_scrape.py --offset` change described 08-26. Highest priority.
- **Still open — seed-resurrection bug** (`seed_from_json.py` hardcodes
  `is_active=True`): unchanged.

### Needing owner decision
1. **CRITICAL — cloud scrape batch 2 saves nothing** (unchanged from 08-26).
   `manual_scrape.py --offset` fix. Highest priority.
2. **NEW — FLORAISON 350 TND wrong-price cluster** (13 products, incl. a blog
   post as a product). Batch-1 site so it also pollutes the cloud release.
   Scraper fix proposed above; no data mutation done.
3. NAKAWA — parked domain, health check won't catch it; needs a manual
   `edit_competitor.py` deactivate (unchanged from 08-26).
4. ECOVILLAGE price-parsing bug — 79% of its catalogue unpriced locally;
   batch-2 so invisible in cloud until #1 is fixed (unchanged).
5. BIO GATRANA / NOPAL TUNISIE — unsupported site types, not scraper bugs;
   decide keep-tracking vs mark "no catalogue" (unchanged).
6. Seed-resurrection bug in `seed_from_json.py` — still unfixed (unchanged).
7. Local DB now 29 days stale — a local scrape is still the only way to get
   batch-2 competitors' data at all until #1 lands (unchanged).
8. Outlets pipeline fields all empty across 3,923 rows — confirm expected,
   not lost (unchanged; 4th run flagging this).

---

## Run: 2026-08-26

### State
- Competitors: 78 total, 54 active, 26 active+website  *(unchanged since 08-24)*
- Products: 1,905 (1,783 priced)  *(unchanged)*
- Price history rows: 1,789  *(unchanged)*
- Outlets: 3,923 — `is_stockist` 0, `contacted` 0, `notes` empty on all 3,923.
  Unchanged for at least two runs. CLAUDE.md says these are hand-entered and
  no scraper can regenerate them, so if the owner expects pipeline data here
  it is either not yet entered or was lost before 2026-07-30. Worth a one-line
  confirmation from the owner; not actionable from here.
- Local DB last scrape: **2026-07-30 17:07 UTC — 27 days old, stale.** No local
  scrape has run since the last two analyst runs. Dashboard figures are from
  that July snapshot; the cloud runs below never write this local DB.

### Data quality (qa_validate.py, read-only)
- missing_price: 122 products (6.4%)  *(unchanged)*
- missing_category: 161 products (8.5%)  *(unchanged)*
- missing_description: 93 products (4.9%)  *(unchanged)*
- short_description: 25 products (<20 chars)  *(unchanged)*
- **Concentration check (unchanged):** missing_price concentrates on ECOVILLAGE
  NATURAL BEAUTY — 67/122 of all missing prices, = 67/85 (79%) of that
  competitor's own catalog. Consistent with a price-field parsing bug on that
  one site. missing_category concentrates 159/161 on BIO TUNISIA MAHDIA, but
  that is 16% of its 984-product catalog — proportionally unremarkable.
  NB: ECOVILLAGE is a *batch-2* competitor, so the cloud release never carries
  it at all (see cloud-scrape finding below) — the parsing bug only shows in
  local data.

### Website health (check_websites.py, read-only)
- 25/26 alive (HTTP 200), 1 recoverable timeout: HERBES DE TUNISIE (no
  response in 20s — same as 08-24). Websearch for a replacement URL again
  found nothing specific to this company. Likely transient; not worth acting
  on yet.
- **check_websites.py missed a parked domain this run:** it reported NAKAWA
  (`nakawabio.com`) as "alive HTTP 200", but the page title is *"Nom de
  domaine à vendre"* — the domain is parked / for sale. The parked-page
  heuristic caught PHYTOESSENTIA but not this one (different parking
  template). NAKAWA should be retired (see decisions).

### Scrape-failure triage
Re-classified the three "status=success, 0 products" competitors from the
08-24 run by fetching each homepage directly (read-only, not the scraper):
- **NAKAWA** — domain parked / for sale ("Nom de domaine à vendre"). Genuinely
  dead. Not a scraper bug. → retire.
- **BIO GATRANA** (`biogatrana.com`) — a client-rendered React/Vite SPA
  (`<div id="root">`, 1.1 KB static HTML) for a food-supplements brand; no
  WooCommerce/Shopify store markers. The scraper correctly finds no products
  because there is no product catalog to scrape. Low priority — arguably not
  a cosmetics competitor at all.
- **NOPAL TUNISIE** (`nopaltunisie.com`) — a real 26 KB English-language B2B
  prickly-pear-oil export site, no standard e-commerce cart / Store API. The
  scraper only handles WooCommerce/Shopify-style catalogs, so it captures
  nothing here. Unsupported-platform case, not a regression.
- Connectivity-error competitors from 08-24 (AGROLINE/DERMAFIG, MED EXOIL,
  NOPALISSE NATURE, HERBES DE TUNISIE) — AGROLINE actually scraped fine in
  the 2026-08-24 cloud run (29 products), confirming those were transient.
- No WooCommerce pagination regression (no competitor at exactly 100
  products, cloud or local).

### Price movements
- Still no price_history rows in the last 14 days — most recent record is
  2026-07-30. Absence of data, not "nothing moved". Will stay this way until
  a local scrape runs.

### GitHub Actions cloud scrape (`scrape.yml`)
- Last 5 runs unchanged since 08-24 (next scheduled run ~2026-08-31):
  2026-08-24 schedule ✅ (42m40s) · 2026-08-21 dispatch ✅ · 2026-08-21
  dispatch cancelled · 2026-08-17 schedule ❌ · 2026-08-10 schedule ❌.
- Seed secret `COMPETITORS_SEED_JSON` still set (2026-08-21T08:10:11Z). The
  08-10 / 08-17 failures were the known secret-unset pattern, resolved.
- **NEW — CRITICAL: batch 2 of the weekly scrape persists nothing. Every run
  silently discards ~half the catalogue.** Evidence from the 2026-08-24 run
  (its `scrape-final-data` artifact + job logs):
  - The published release DB has products for only **10 of 77 competitors**,
    and **25 `scraping_logs` rows total** — all from batch 1 (companies A–L
    by seed order). Batch 2 wrote **zero** log rows and **zero** products.
  - Batch 2's own job log shows it *did* scrape 24 competitors and *did* find
    products — "WooCommerce Store API: found 128 products" for ORGANICA, 126
    for PERFECT BIO, plus KARINA TUNISIE, PUNICA (13), TVH (11), NURESSENCE
    (5), MELIORA, RIVILIA, STÉ KINZ, ECOVILLAGE… — then logged
    "Done: 24 results" and "Exported **1302** products", the *exact same*
    1302 batch 1 had already exported. Nothing batch 2 scraped reached the DB.
  - **Root cause:** `manual_scrape.py` has no `--offset`, so the workflow's
    "Run scraper (Batch 2)" step is an inline `python -c` one-liner that calls
    `scrape_multiple_competitors(targets)` directly. That function
    (`src/scrapers/web_scraper.py:2933`) is pure — it returns
    `List[ScrapingResult]` and never touches the database. All DB writes live
    in `manual_scrape.py` (`_run_web_scrape`, lines ~178-300), which batch 2
    bypasses. So batch 2 has been a database no-op since the batch-split
    workflow was introduced; it was just invisible while the seed secret was
    unset and everything was fake.
  - The inline script also filters only `website != ''` — it does **not**
    filter `is_active` (CONTEXT.md load-bearing decision #3), unlike
    `manual_scrape.py`.
  - **Products lost from every cloud release:** KARINA TUNISIE (177 locally),
    ORGANICA (127), PERFECT BIO (126), ECOVILLAGE (85), STÉ KINZ (52),
    MELIORA (17), PUNICA (13), TVH (11), RIVILIA (7), NURESSENCE (5) and
    other batch-2 sites — on the order of 600 products, ~40% of the catalog.
  - **Proposed fix (code change — reported only, no PR per task scope):** add
    an `--offset N` arg to `manual_scrape.py` (mirror of the existing
    `--limit`, applied on the same `is_active`-filtered, ordered query), then
    change the batch-2 workflow step to
    `python scripts/manual_scrape.py --type web --offset 25`. This reuses the
    tested persistence + `is_active` path and deletes the fragile one-liner.
    Add a regression test that batch-2 target selection persists rows.
    Also add an explicit `.order_by(Competitor.id)` so `--limit` / `--offset`
    can't overlap or gap.
- **Still open — seed-resurrection bug** (unchanged from 08-24):
  `seed_from_json.py` hardcodes `is_active=True`, so every cloud run seeds all
  77 competitors active, including the 24 retired locally. Cloud wastes time
  re-hitting known-dead domains and its active set never matches the real 54.

### Needing owner decision
1. **CRITICAL — cloud scrape batch 2 saves nothing.** Every weekly release is
   missing ~half the competitors / ~600 products (KARINA, ORGANICA, PERFECT
   BIO, ECOVILLAGE, STÉ KINZ, …). Silent: run is green, summary says 1302.
   Needs the `manual_scrape.py --offset` fix above. Highest priority in this
   report.
2. NAKAWA — domain now parked/for-sale; retire it. `check_websites.py
   --mark-inactive` will NOT catch it (health check says "alive"); needs a
   manual `edit_competitor.py` deactivate, or improve the parked heuristic.
3. ECOVILLAGE price-parsing bug — 79% of its own products have no price
   locally. Worth a scraper look (also a batch-2 site, so invisible in cloud
   data until #1 is fixed).
4. BIO GATRANA / NOPAL TUNISIE — not scraper bugs; unsupported site types
   (React SPA with no shop / B2B export site). Decide whether to keep
   tracking them or mark them "no catalog".
5. Seed-resurrection bug in `seed_from_json.py` (`is_active` hardcoded True) —
   still unfixed.
6. Local DB is 27 days stale — run a local scrape when convenient; the cloud
   job never updates it. (And until #1 is fixed, a local scrape is the only
   way to get batch-2 competitors' data at all.)
7. Outlets pipeline fields (`is_stockist` / `contacted` / `notes`) are all
   empty across 3,923 rows — confirm that's expected, not lost.

---

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
    [2026-08-26 update: re-classified — NAKAWA is a parked domain, BIO GATRANA
    is a React SPA with no shop, NOPAL TUNISIE is a B2B site with no cart.
    None is a scraper regression.]
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
  [2026-08-26 correction: "both batches succeeded" is true only at the job
  level — batch 2 exits 0 but persists nothing to the DB. See 08-26 run.]
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
