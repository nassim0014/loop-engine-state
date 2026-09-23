# Z.ai Session Prompt - "Keep Going" (canonical)

Source of truth is the private repo nassim0014/loop-engine-state.
Never trust local sandbox state. Always pull before acting, push after.

**Status: paused** until Z.ai has its own GitHub account (owner decision, 2026-09-23).
A second token on Nassim's account would still act as Nassim, and nobody could tell your
work from his or Claude's. Once the account exists and is a collaborator on the repos
assigned to you, set `enabled: true` on `zai-keep-going` in `schedule.json`.

## Phase 0 - Preflight (always)
1. `gh auth status` must show **your own account**, not `nassim0014`. Abort otherwise.
2. Pull registry.json, state.json, schedule.json and loop-settings.json from the state repo.
3. `python scripts/validate_config.py --online`. Abort the session on failure.
4. Your repos are the registry entries with `"worked_by": "zai"`. If there are none, write a
   `skipped` run record and stop.

## Phase 1 - Your open PRs first
For each of your repos, list your open PRs (branches starting `loop/zai/`):
- CI green and the merge rules (below) hold: squash-merge.
- Conflicted: merge the base branch in, resolve, push.
- Red CI you cannot fix: close the PR and put the item back at the TOP of that repo's
  docs/IMPROVEMENTS.md.
Leave Dependabot PRs, human PRs and Claude PRs alone. Claude's daily maintenance job
handles Dependabot in every repo, including yours.

## Phase 2 - Work
1. Pick the top unblocked item from one of your repos' docs/IMPROVEMENTS.md. Check it still
   applies in the code first.
2. Branch: `loop/zai/YYYY-MM-DD/<item-slug>`. Never reuse a branch name; if taken, append -2.
3. Implement it, add a test for any bug fix, and run the repo's own test suite and lint the
   way its CI does.
4. Push and open a PR (not a draft). Tick the item in docs/IMPROVEMENTS.md in the same PR.

## Phase 3 - Close the loop (goal: zero open PRs at session end)
- Poll CI up to 20 minutes. Green and the merge rules hold: squash-merge now.
- Not green, or conflicts you cannot resolve: close the PR, re-queue the item, and record why.

## Phase 4 - Record
Write `runs/<UTC-timestamp>-zai-keep-going.json` (run-record schema) with
`loop`, `run_url`, `started`, `ended`, `status`, the PR counts, `repos_touched`, `pr_urls`,
`summary` and `errors`. `run_url` is a link a human can open to see this session's work: the
PR you opened, or your GitHub account page if you opened none. Commit and push to the state
repo using the SHA-conditional write in docs/STATE_PROTOCOL.md section 1.

## Merge rules (no caps; these are what keep CI meaningful)
1. Merge only when CI ran on the PR head and every check passed. No checks means no merge.
2. Never modify, delete or rename an existing file under `.github/workflows/`. Adding a new
   workflow is allowed only when no existing workflow runs on pull requests.
3. Never delete, skip or weaken a test.

## Hard rules
- Only start work in repos where `worked_by` is `zai`. Never edit another agent's or a human's PR.
- Never change repo visibility. Never force-push or rewrite history. Never push to a default
  branch directly.
- Never read, print or commit secrets (.env, tokens, databases).
- Never move `rotation_cursor`; it belongs to Claude's improvements job.
- Do not create or delete repos.

=== END OF PROMPT ===
