# Bootstrap scan — 2026-10-01 (GLM read-only analyst output)

Full read of all 8 allowlisted repos + loop-engine-state + the GitHub API landscape.
Purpose: seed `glm/backlog.json`, map Claude's coverage, and record what needs the owner.

## 1. Landscape

- 12 repos total. 8 code repos are GLM's allowlist; `kinz-accounting-analysis-20260623-102129`
  is Claude's (never touch); `Kinz-animations` and `kinz-fidelite` are not code; this state repo
  is infra.
- Claude's cloud engine fires 01:45 & 06:45 Tunis (dispatch + maintenance daily; improvements
  Mon/Wed/Fri on 2 repos by `rotation_cursor`; kinz-accounting Sun/Tue/Thu; creative Sat;
  analyst Tue; daily-commit; weekly summary Mon). GLM's slots (10:30 / 15:30 / 21:00 + weekend)
  sit entirely outside those windows.
- **Open PR census at scan time: 13, all dependabot, zero agent PRs.**
  - btc-llm-sentiment: #55, #60, #61, #62, #63 (all fail the same pre-existing Docker check —
    shap==0.52.0 needs Python>=3.12 while the Dockerfile builds on 3.11; the full
    requirements set is ResolutionImpossible as pinned).
  - kinz-secure-commerce-hub: #37, #64, #65, #69, #70, #71 (coupled frontend peer-dep cluster;
    #64 httpx pip).
  - Next.js-SaaS: #95 (react-select, conflicted), #99 (@ai-sdk/react 3-major jump, red).
  All are Claude-maintenance / owner territory. GLM never touches them.
- No `glm/*` branches exist anywhere yet — the namespace is clean.

## 2. Per-repo snapshot (CI runs on PRs in all 8)

| Repo | Tests (measured) | CI on PR | Open in-repo backlog | GLM note |
|---|---|---|---|---|
| kinz-price-bridge | 36 | ruff + pytest | **0 items — all done** | Claude's rotation skips it → GLM primary repo. GLM found: sync.py unbounded read + N+1, silent exit in run_sync.py, stale CLAUDE.md test count |
| feed-quality-gate | 58 | ruff + pytest + CLI smoke (must fail on broken example) | #2 stuck_value_cluster, #3 value_range, #4 non_product_row, #5 zero_yield_source, #11 cli branches, #12 gate fallback | checks pure / synthetic data only |
| analytics-service-toolkit | 61 | ruff + pytest --cov | #5 Postgres dedup (needs CI container), #8 alerts retry test, #9 cli branches, #4b tag v0.1.0 (owner), #7 hygiene | no business logic, no domain data, ever |
| kinz-margin-guardian-pipeline | 81 (24 skip in CI w/o astk) | pytest --cov + docker | #8 ASTK_PAT (owner), #11 misleading skip reason, #13 .env.example knobs, #14 no dependabot.yml | item 11 fixable source-side (config.py pattern) |
| kinz-secure-commerce-hub | 103 backend + 6 frontend jest | 7 checks (backend/frontend/security/docker) | item 6: scheduler.py 0%, run_etl.py ~57%, auth/jwt/passwords/audit gaps | item 4 next-bump = owner sign-off |
| btc-llm-sentiment | 90 | test + ml-smoke + security + docker + CodeQL | #13 safe_load_pickle test (items 10/12 owner-blocked) | light CI env only; 1 pre-existing ruff F401 on main |
| kinz-competitor-intelligence | 414 | lint + pytest --cov | 8a-follow-up (owner), 12 social.py coverage, 13 database.py error branch, 8c (deprioritized) | private; venv; scrapers/seed data off-limits |
| Next.js-SaaS | 81 (vitest+playwright) | build + test + security | metering.ts, dispatcher.ts, getOrgMembership, exportUserData, CSP nonce, backoff-ladder tests, coverage tooling | pnpm only; TS strict; cursor=6 lands here Friday |

Code-signal sweep: 0 real TODO/FIXME across all 8 (4 hits in KCI are Tunisian phone-format
strings); 0 bare `except:`; silent `except Exception` hotspots: btc (26 silent), KCI (62
without log/raise), kmg 1, hub 1, price-bridge 1. Longest functions: KCI 55 >75-line
functions (worst 1106), btc 15, Next.js-SaaS 19. These are future backlog candidates only
when they pair with a concrete failure mode — not queued speculatively.

## 3. What GLM deliberately does NOT duplicate

- Dependabot handling, red-main repair, green-PR sweeping → Claude's daily maintenance.
- Backlog refills of the repos' own `docs/IMPROVEMENTS.md` → Claude's improvements job does
  this when a list drops under 3; GLM reads those files as input and ticks items only inside
  PRs that do the work.
- Anything requiring owner decisions (§4 below).
- kinz-accounting-analysis entirely.

## 4. Needs the owner (recorded, not acted on)

1. **btc-llm-sentiment dependency cluster**: coordinated re-pin across numpy/shap/
   tensorflow-cpu/pandas/scikit-learn/optuna/torch/yfinance + Dockerfile Python version.
   Verified by Claude's runs to be ResolutionImpossible as pinned; blocks 5 dependabot PRs and
   makes "Docker build" permanently red on PRs.
2. **kinz-secure-commerce-hub frontend cluster**: next 14→16 + eslint 8→10 + react-dom +
   tailwindcss 4 must land together (peer-dep coupled); dependabot cannot be @-mentioned from
   agent sessions (mangled mention characters — Claude hit this 3×).
3. **Next.js-SaaS**: #99 @ai-sdk/react 1.2.12→4.0.x (3 majors, red), #95 (conflicted).
4. **analytics-service-toolkit**: tag v0.1.0 + release + pinned install line (a real consumer
   already floats on `@main`); Postgres Deduplicator needs a CI service container (workflow
   change — owner-only).
5. **kinz-margin-guardian-pipeline**: ASTK_PAT secret for the docker job; requirements pinning
   policy; no dependabot.yml.
6. **kinz-competitor-intelligence**: 8a-follow-up phantom `avg_likes`/`avg_comments`
   (add-vs-drop decision); dep-ceiling policy (item 14).
7. **Registry visibility drift**: analytics-service-toolkit, feed-quality-gate,
   kinz-margin-guardian-pipeline, kinz-price-bridge are PUBLIC on GitHub while the registry
   recorded them private (flagged by Claude's loops since 2026-09-13, never resolved).
   Visibility is owner-only — confirm intent.
8. **GLM identity**: everything GLM does displays as nassim0014. Structural markers are in
   place (glm/ branches, [glm] titles, signature blocks, this ledger). The durable fix is a
   dedicated machine account or GitHub App (owner action, when convenient).

## 5. Seed queue

19 actionable items queued in `glm/backlog.json` (priority = impact × confidence). Top of the
queue: price-bridge N+1 fix (20), fqg stuck_value_cluster (20), fqg value_range (20),
astk alerts-retry test (20), Next.js getOrgMembership tests (20 — after Claude's Friday run
clears that repo), hub scheduler.py tests (16), kci database.py error branch (16).

Next GLM sessions should start with kinz-price-bridge (Claude never works it) and
feed-quality-gate, then hub/kci/margin/btc/astk, holding Next.js-SaaS until after Claude's
Fri 2026-10-02 improvements run (rotation_cursor=6 points there).
