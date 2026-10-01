# GLM session log (append-only)

## 2026-10-01 — glm-bootstrap (design session, chat-triggered)

- Read all 8 allowlisted repos, loop-engine-state (Claude's schedule/state/registry/settings/
  prompts/handoff docs), and the GitHub API landscape (13 open dependabot PRs, 0 agent PRs,
  clean glm/ namespace).
- Designed the loop system: 5 loops (improvement-am daily 10:30, improvement-pm Tue/Thu/Sat
  15:30, analyst daily 21:00 read-only, backlog-refresh Sun 12:00, state-hygiene Sat 20:00 —
  all Africa/Tunis, all outside Claude's 01:45/06:45 windows with 2 h live-activity guards).
- State mechanism: this branch (glm/state), this directory (glm/), session lock with 3 h stale
  override, append-only runs/ and findings/, PR ledger in state.json.
- Merge-safety contract: 19 numbered gates (squash-only, CI-green-or-no-merge, <=400 lines,
  protected paths incl. workflows/lockfiles/manifests/secrets/test-harness, tests only
  stronger, zero open PRs at session end, Claude/dependabot PRs untouchable).
- Identity: structural markers (glm/ branch prefix, [glm] PR title prefix surviving the
  squash, signature block, glm(...) commit prefix, PR ledger). Machine-account recommendation
  recorded for the owner.
- Backlog seeded with 19 items; owner-attention list recorded (8 items incl. the btc
  dependency cluster and the registry visibility drift).
- Deliverables for the owner saved outside git (chat + download dir): schedule, protocols,
  trigger prompt, Claude handoff notice. No work PRs opened (by design).
