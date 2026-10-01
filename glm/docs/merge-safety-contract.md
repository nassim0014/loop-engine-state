# GLM Merge-Safety Contract

Every rule is a hard gate. At merge time each one is re-checked literally; **any single failure
means no merge** — the PR is closed (or fixed first, within the fix-attempt budget).

## Scope & identity

1. **Allowlist.** GLM works only these 8 repos: kinz-competitor-intelligence,
   btc-llm-sentiment, kinz-margin-guardian-pipeline, kinz-secure-commerce-hub, Next.js-SaaS,
   kinz-price-bridge, analytics-service-toolkit, feed-quality-gate. Never
   kinz-accounting-analysis* (Claude owns it), Kinz-animations, kinz-fidelite, or any repo not
   listed. `loop-engine-state` is touchable only on the `glm/state` branch, inside `glm/`.
2. **Branch naming.** Every work branch is `glm/<loop-short>-<YYYYMMDD>-<repo-slug>-<topic>`,
   e.g. `glm/improve-20261002-price-bridge-sync-n-plus-1`. The `glm/` prefix is the structural
   identity marker (a PR cannot exist without its branch).
3. **No direct pushes to `main`** of any repo, ever. No pushes to `claude/*`, `loop/claude/*`,
   `exp/*` or `dependabot/*` branches — they belong to other actors.
4. **No force-push, ever.** Not to shared branches, not to GLM's own branches, not to
   `glm/state`. Fix forward with new commits; rebase only local unpushed commits.

## Diff budget & protected paths

5. **Diff <= 400 lines.** `git diff --shortstat origin/main...HEAD` — insertions + deletions
   combined must be <= 400. Bigger ideas go to `glm/findings/` for the owner, not into a PR.
6. **Protected paths — never modify, rename or delete:**
   - CI: anything under `.github/workflows/` (GLM also never *adds* a workflow file — that is an
     owner/Claude-maintenance decision);
   - lockfiles: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `uv.lock`,
     `Pipfile.lock`;
   - dependency manifests: `requirements*.txt`, `pyproject.toml` `[project]`/dependency
     sections, `package.json` dependency fields — no dependency additions, bumps or pins;
   - auth & secrets: `.env*` (except documented, non-secret additions to committed
     `.env.example` templates), `*.pem`, `*.key`, credentials, `secrets/`, tokens;
   - test-harness infrastructure: `conftest.py`, `pytest.ini`, `jest.config.*`,
     `vitest.config.*`, `playwright.config.*`, `tsconfig` test configs, fixture scaffolding.
     (Adding **new test files** is allowed and encouraged; see rule 7.)
7. **Tests only get stronger.** No test deleted, no assertion removed or relaxed, no new
   skip/xfail/`test.skip`/`it.skip`. Changes to existing test files must be strictly additive;
   prefer brand-new test files. Every bug fix ships with a regression test that fails without
   the fix.

## Merge mechanics

8. **CI green required.** Merge (squash) only when the PR head SHA has at least one check or
   status, all concluded, none failed/cancelled/timed-out/action-required. **No checks at all
   means no merge** — instead run the repo's CI commands locally, record the result in the PR
   body, and leave the merge to a later session once checks exist. Poll CI at most 20 minutes.
9. **Squash-merge only.** `PUT /repos/{owner}/{repo}/pulls/{n}/merge` with
   `{"merge_method": "squash"}`. Never merge-commit, never rebase-merge.
10. **Not a draft, no conflicts, no `hold`/`do-not-merge` label.**
11. **Rate caps.** Max 2 PRs per PR-loop session; max 1 open PR per repo at a time; max 2 merged
    PRs per repo per day.
12. **Zero open PRs at session end.** Every PR GLM opened this session is squash-merged or
    closed (with the reason recorded in `glm/backlog.json` and the run record) before the session
    ends. Exception: none — if CI is still running at session end, wait for it (within the
    20-minute budget) or close.

## Other actors

13. **Claude's PRs are untouchable.** Never merge, close, comment, review, rebase or edit any PR
    whose head branch starts with `claude/`, `loop/claude/`, `claude/auto-improve-`, `exp/`.
    They look human-authored to you; the branch prefix tells you otherwise. Default action:
    leave them entirely alone. (Only exception: Nassim explicitly names a PR in this session's
    instructions.)
14. **Dependabot PRs are untouchable** — they are Claude's maintenance-job territory and they
    modify manifests/lockfiles, which rule 6 forbids GLM from doing anyway.
15. **File-overlap avoidance.** Before working a repo, list its open PRs' changed files. If an
    open PR (claude/* or dependabot/*) already touches the files you would touch, pick a
    different repo or a different item this session.
16. **Claude timing.** No PR-writing work inside the blackout windows (01:15-03:30 and
    06:15-08:30 Tunis) or while any `claude/*` branch shows a push newer than 2 hours —
    downgrade that session to read-only analysis.

## Repo & platform behavior

17. **No visibility, settings or automation changes.** No visibility changes, no branch
    protection, no webhooks/collaborators, no `dependabot.yml` creation, no repo creation or
    deletion (Genesis is owner-only), no issue creation or comments anywhere (owner wants 0%
    issues).
18. **Zero secrets.** Never read, print, log or commit secret values (`.env`, tokens, keys,
    databases). If a secret value appears in a diff or a file by accident: abort the work,
    close any PR containing it, delete the branch, and report to the owner **without quoting the
    value**.

## Repo-specific hard rules (stricter rules always win)

19. The repo's own `CLAUDE.md` / `CONTEXT.md` / `context.md` rules beat this contract whenever
    they are stricter. Key per-repo rules baked into the loop prompt: never run the KINZ
    scrapers; never touch `data/competitors_seed.json` or `kinz-competitor-intelligence-BACKUP-*`;
    analytics-service-toolkit carries **no business logic and no domain data, ever**;
    feed-quality-gate checks stay pure with injected `now` and synthetic fixtures only;
    Next.js-SaaS uses **pnpm** (never npm) and forbids `any`.
