# GLM State-Tracking Protocol

GLM's state is completely independent of Claude's. Claude's state (root `schedule.json`,
`state.json`, `registry.json`, `loop-settings.json`, `prompts/`, `runs/`) is **read-only** for
GLM. GLM never pushes to `main` of `loop-engine-state`.

## 1. Where it lives

| What | Where |
|---|---|
| State repo | `nassim0014/loop-engine-state` (private) |
| GLM's branch | `glm/state` (never merged to main; a living branch) |
| GLM's directory | `glm/` on that branch only |

```
glm/
  schedule.json     GLM's loop definitions (this system's times)
  state.json        runtime state: loop last-runs, session lock, PR ledger, counters
  backlog.json      GLM's prioritized queue of improvement items (with claims)
  findings/         dated read-only analyst outputs (YYYY-MM-DD-<slug>.md, never rewritten)
  runs/             one JSON run record per session (<UTC-ts>-<loop>.json, append-only)
  session-log.md    append-only human-readable log, one block per session
  docs/             merge-safety-contract.md, state-protocol.md, backlog-strategy.md
  prompts/          glm-loop.md (the trigger prompt; PAT replaced by {{GLM_PAT}})
  schemas/          glm-schedule.schema.json (root schema + "glm" agent + glm/prompts path)
  README.md         what this namespace is, so Claude or a human stumbling on it understands
```

## 2. Session start (read protocol)

1. `git fetch origin` and check out the tip of `origin/glm/state`
   (`git checkout -B glm/state origin/glm/state`). If the branch does not exist, bootstrap it
   (§5).
2. Read `glm/state.json`. Check `session_lock`:
   - lock fresh (< 3 h old) → another GLM session may be live: **abort**, report to owner.
   - lock stale (>= 3 h) → override it, set your own lock, note the override in `session-log.md`.
   - no lock → set yours: `{"id": "<UTC-ts>", "started_at": "...", "loop": "<name>"}` and push
     the lock immediately, before any work (lease before work, not after).
3. Read `glm/backlog.json`, `glm/schedule.json`, and — read-only, for context only — the root
   `registry.json` (repo notes from Claude's runs) and `state.json` (`rotation_cursor` tells you
   where Claude's improvements job will land next; never move it).

## 3. Session end (write protocol)

1. Resolve every PR opened this session (merge or close) — zero open GLM PRs.
2. Update `glm/state.json`: loop `last_run`/`status`, counters, PR ledger entries, clear
   `session_lock`.
3. Update `glm/backlog.json` item statuses (`proposed → in_progress → done | back-to-proposed
   with reason`).
4. Write `glm/runs/<UTC-ts>-<loop>.json` (append-only; never edit a past record) and append one
   block to `session-log.md`.
5. Commit `glm(<loop>): run <UTC-ts>` and `git push origin glm/state`.
   - Push rejected (branch moved — another session or a retry): `git fetch origin &&
     git rebase origin/glm/state` and retry, **max 3 times**. Never force-push.
   - Still failing → paste the run record into the final chat message and report
     `NEEDS YOU: state push refused`.

## 4. Isolation rules

- Write only inside `glm/`. Never touch root config, `runs/`, `prompts/`, `reports/`,
  `experiments/`, `findings/` (root), or anything under Claude's ownership.
- Run records and findings files are append-only; a file written once is never rewritten.
- The PAT never appears in any committed file. The in-repo copy of the prompt uses
  `{{GLM_PAT}}`; the real token exists only in the pasted chat prompt.
- CI on the state repo runs `validate_config.py` on every push; it validates only root files,
  so `glm/` additions are safe — but keep every `glm/` file valid JSON/Markdown with no
  zero-width or bidi characters (the repo's CI greps for them).

## 5. First-run genesis (if `glm/state` is missing)

Create the branch from `origin/main`, add the `glm/` skeleton above (schedule, empty state with
`session_lock: null`, backlog from a fresh scan, README), commit `glm: bootstrap`, push
`git push -u origin glm/state`. No PR, no merge to main, no root changes.

## 6. Recovery

- Session crashed mid-work → next session sees open `glm/*` PRs via the ledger + GitHub API:
  resolve them first (merge if green and contract-clean, else close + requeue the item with the
  failure reason), then continue.
- Ledger vs GitHub drift → `glm-state-hygiene` loop reconciles from GitHub truth (GitHub is the
  truth; the ledger is a cache).
