# glm/ — GLM loop engine state

This directory is the control plane of **GLM's** autonomous improvement loops for
nassim0014's 8 code repos. It is completely independent of Claude's loop engine (the root
files of this repo). GLM is a chat-triggered agent; this branch (`glm/state`) is its only
writable surface.

## Who may write here

Only GLM sessions, and only inside `glm/`. Claude's jobs, the laptop loops and humans: read
this freely, but never edit it. GLM likewise never touches the root files, `runs/`,
`prompts/`, `reports/`, `experiments/`, `findings/` (root), `main`, or any `claude/*` branch.

## Layout

| Path | What |
|---|---|
| `schedule.json` | GLM's loops and times (Africa/Tunis), blackout windows, conflict guard |
| `state.json` | Runtime state: loop last-runs, session lock, PR ledger, counters |
| `backlog.json` | GLM's working queue (claims + GLM-found items) and owner-attention list |
| `findings/` | Dated read-only analyst outputs (append-only) |
| `runs/` | One JSON run record per session (append-only) |
| `session-log.md` | Append-only human-readable session log |
| `docs/` | The merge-safety contract, state protocol, backlog strategy |
| `prompts/` | The canonical trigger prompt (PAT replaced by `{{GLM_PAT}}`) and the Claude handoff notice |
| `schemas/` | glm-schedule.schema.json (root schedule schema + agent "glm" + `glm/prompts/` paths) |

## Rules in one paragraph

GLM works only the 8 allowlisted repos, on `glm/*` branches, squash-merges only when CI ran
and passed, never touches workflows/lockfiles/manifests/secrets/test-harness files, keeps
diffs <= 400 lines, never weakens tests, leaves `claude/*` and `dependabot/*` PRs entirely
alone, ends every session with zero open PRs, and pushes state only to this branch (never
`main`, never force). Full contract: `docs/merge-safety-contract.md`.

Bootstrap: 2026-10-01, commissioned by Nassim (owner). Loop definitions in `schedule.json`.
