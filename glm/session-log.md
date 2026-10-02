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

## 2026-10-02 - owner-cleanup session (chat-triggered, owner-directed)

- Directive: remove every AI-writing trace from the 8 code repos, "even em dashes".
- Scanned all repos (attribution strings, agent-file mentions, em/en dashes, smart quotes,
  invisible chars, emoji headings, AI-voice phrases), then cleaned in 8 squash-merged PRs
  (glm/docs-cleanup, one per repo, all green or pre-existing-red only; zero open PRs after).
- Removed AI-assistant files repo-wide: CLAUDE.md x7, CONTEXT.md, context.md, .claude/,
  docs/IMPROVEMENTS.md x8. Everything archived under glm/archive/ (never to be recreated;
  backlogs now live only in glm/backlog.json).
- 354 historical PR bodies scrubbed (footers, Loop-Agent lines, claude.ai links, dashes,
  zero-width chars). Backup: glm/archive/pr-body-backup-20261002.json. Dependabot PR bodies
  left as-is (bot-owned, package-fact content).
- Deliverables updated for the new policy: trigger prompt (new section 1b house style, plain
  squash-commit titles on main, backlog now canonical in glm/backlog.json), Claude handoff
  notice (do-not-recreate list, stop attribution trailers), backlog strategy, merge contract
  (rules 19-20), state protocol, schedule.
- Open for the owner: git history still carries 86 old commit trailers + 4 Claude-authored
  commits; removing them needs a history rewrite + force-push, which the standing rules forbid.
