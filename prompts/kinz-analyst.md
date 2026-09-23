# Job: KINZ competitor analyst (Tuesday night)

Loop name: `cloud-kinz-analyst`. Read `prompts/_common.md` first; everything there applies.

**Goal:** a weekly, read-only check of the KINZ competitor data, so bad data is caught before
anyone relies on it. It replaces the laptop task, which kept re-reading a local database
frozen on 2026-07-30. This job reads the fresh data the weekly GitHub Actions scrape publishes
every Monday morning, so it runs the night after (Tuesday 01:45).

This job changes nothing in `kinz-competitor-intelligence`. It writes only
`findings/kci-data-quality.md` and its run record in the state repo.

## Privacy, before anything else

The database holds real people's names, phone numbers and emails (`competitors.contact_person`,
`phone`, `email`, and the same fields in `parapharmacies`). Never select, print, log or copy
these columns anywhere: not in findings, not in your messages, not in commands whose output you
read. Company names, websites, products and prices are fine. Delete the downloaded database at
the end of the run.

## Get the data

1. The repo is at `/home/user/kinz-competitor-intelligence`. Use it read-only.
2. Read the release with
   `curl -sS https://api.github.com/repos/nassim0014/kinz-competitor-intelligence/releases/tags/weekly-scrape-data`.
   Its body says when it was last updated. Find the asset named `competitors.db` and download
   it by its API `url` with the header `Accept: application/octet-stream` to
   `/tmp/kci/competitors.db`. The browser download link returns 404 for this private repo.
   Do the same for `analyse_concurrentielle.csv` if you need it.
3. Open the database read-only (`sqlite3.connect("file:/tmp/kci/competitors.db?mode=ro", uri=True)`).
4. If the release is more than 8 days old, the weekly scrape did not publish. Find out why from
   the "Weekly Competitor Scrape" workflow runs and their logs (Actions API).

## Check

Start by reading the latest `## Run:` section of `findings/kci-data-quality.md`, so you report
what changed rather than repeating it.

- **State:** competitors (total, active, active with website), products (total, priced), price
  history rows, newest `products.scraped_at`, and how many competitors have products at all.
- **Scrape coverage:** which active competitors with a website have no products or no
  `scraping_logs` row this week. The known critical bug is that batch 2 of `scrape.yml` saves
  nothing, because its inline `python -c` step never writes to the database. Check the latest
  workflow run's batch-2 log and say whether it is still happening.
- **Data quality:** missing price, category or description counts. Clusters of identical prices
  inside one competitor (the known FLORAISON 350 TND case), prices of 0 or far outside that
  competitor's range, and non-products such as blog posts.
- **Pagination regression:** several competitors with exactly 100 products means WooCommerce
  pagination has broken. Flag it loudly.
- **Price movements:** from `price_history`, products whose price changed by more than 30% since
  the previous recorded price, grouped by competitor. A few examples are enough.
- **Workflow health:** result of the last 5 `scrape.yml` runs.

You may clone the repo and run `scripts/qa_validate.py` **without** `--fix` against a copy of
the database (`DATABASE_URL=sqlite:////tmp/kci/copy.db`). Never run any scraper, never run
anything with `--fix` or `--mark-inactive` against real data, and never contact competitor
websites.

## Write

1. Add a new `## Run: <YYYY-MM-DD>` section at the top of `findings/kci-data-quality.md`, under
   the file's intro. Use the same headings every run: State, Scrape coverage, Data quality,
   Price movements, Workflow health, Needing owner decision. Numbers first, and mark what changed
   since last run. Keep the 6 most recent run sections and delete older ones; git keeps history.
2. The improvements job reads your latest section when it works on this repo, so describe each
   code problem precisely: the file, the cause, and the proposed fix.
3. Run record and state, as in the shared rules.

## Final message

`NEEDS YOU:` if something only Nassim can fix is still open. The batch-2 bug is one: the fix is
in `.github/workflows/scrape.yml`, which agents may not edit. Name the single most important
item. Otherwise `OK:` with the headline numbers.
