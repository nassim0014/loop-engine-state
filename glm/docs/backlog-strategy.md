# GLM Backlog Auto-Generation Strategy

The queue lives in `glm/backlog.json` on the `glm/state` branch. It is GLM's working queue —
repos' own `docs/IMPROVEMENTS.md` files remain the canonical in-repo backlogs (Claude refills
them); GLM reads them as an input, not a competitor.

## 1. When the backlog regenerates

| Trigger | What runs |
|---|---|
| `glm-analyst-scan` (daily 21:00 Tunis) | light refresh: verify queued items still apply, add obvious new candidates, drop done/stale ones |
| any repo drops below **3 actionable GLM-suitable items** | full scan of that repo before it can be picked again |
| `glm-backlog-refresh` (Sun 12:00 Tunis) | full regeneration of all 8 repos, re-score everything |
| a PR closes unmerged / CI fails twice | the item returns to `proposed` with the failure reason attached |

## 2. What gets scanned (per repo)

1. **`docs/IMPROVEMENTS.md`** — every open item, re-verified against the code first
   (backlog bookkeeping rots: the btc repo has shipped-but-unticked items and a stale "Now"
   entry; always grep for the described symptom before trusting it).
2. **Claude's registry notes** (root `registry.json`, read-only) — what Claude already did,
   plans, or flagged owner-blocked, so GLM does not duplicate or step on a known mine.
3. **Coverage gaps** — modules with no/low test coverage vs. the repo's coverage report
   (`pytest --cov ... --cov-report=term-missing` locally, using the repo's CI env recipe);
   priority to write paths, auth primitives, money/billing math, error branches.
4. **Code signals** — silent `except Exception` handlers, functions > 75 lines on hot paths,
   missing docstrings on public APIs, stale docs claims (README/CLAUDE.md vs. reality — e.g.
   kinz-price-bridge's CLAUDE.md still says "4 smoke tests" while the suite is 36).
5. **Open-PR landscape** — items whose files are already touched by an open PR are excluded
   until that PR resolves.
6. **Back-compat seams** — deprecations the repo itself documents (e.g. pandas 3 ragged-CSV
   reinterpretation risk flagged in the accounting repo's notes).

## 3. What disqualifies an item from GLM's queue (goes to `findings/` instead)

- needs an owner decision (marked "OWNER DECISION" / "NEEDS YOU" anywhere in its history);
- requires touching protected paths (workflows, lockfiles, manifests, secrets, test harness);
- plausibly exceeds the 400-line diff budget;
- needs a new dependency, a CI service container, a release/publish step, or live-network
  verification (e.g. scraper behavior in KINZ — those PRs must stay open by that repo's rule,
  which conflicts with GLM's zero-open-PRs rule, so GLM never takes them);
- changes how money, tax or reported figures are calculated (accounting-domain hard line);
- duplicates something Claude's rotation is about to do (check `rotation_cursor` in root
  `state.json`, read-only) or a currently-open PR already does.

## 4. Scoring

```
priority = impact (1-5) x confidence (1-5)     # tie-break: smaller est_lines first
impact     = user-visible robustness/correctness/test-value of the fix
confidence = odds it lands green within budget without judgement calls
```

Preference order by type: **additive tests on untested write/auth/billing paths > small
correctness/robustness fixes with regression tests > stale-docs corrections**. Cosmetic-only
changes are not queued.

## 5. Item schema (`glm/backlog.json`)

```json
{
  "id": "GLM-PB-001",
  "repo": "kinz-price-bridge",
  "title": "Fix unbounded read + N+1 in sync_latest_prices",
  "type": "performance | robustness | test | docs | feature",
  "source": "glm-scan 2026-10-01 | repo docs/IMPROVEMENTS.md item 12",
  "files": ["src/sync.py"],
  "est_lines": 140,
  "impact": 5, "confidence": 4, "priority": 20,
  "status": "proposed | in_progress | done | dropped",
  "claimed_at": null, "pr": null, "notes": "verify approach against current query shape first"
}
```

## 6. Claim discipline (the anti-race rules)

1. Claim an item (`status: in_progress`, `claimed_at`, loop name) **in `glm/backlog.json`
   before writing code**, and push the claim.
2. Only one in-progress item per repo at a time.
3. When both agents shipped the same idea anyway (race lost): if Claude's landed first, rebase
   only if the change is still needed; otherwise close GLM's PR with a one-line reason and mark
   the item `dropped (done by claude, PR #N)`.
4. Never edit a repo's `docs/IMPROVEMENTS.md` from outside a PR that actually does the work
   (ticking the item belongs in the same PR that fixes it — Claude's convention, kept).
