# Notice for Claude: a second agent (GLM) now works the repos

Nassim has stood up GLM — a separate, chat-triggered autonomous agent — as an independent
improvement loop system alongside your cloud jobs. It runs on a PAT on Nassim's account, so
its commits and PRs will show `nassim0014` as the author, exactly like yours. Here is what you
need to know; nothing about your own jobs changes.

**How to recognize GLM's work**

- Branches: `glm/*` (e.g. `glm/improve-20261002-price-bridge-sync-n-plus-1`).
- PR titles: `[glm] <repo>: <what>` — the prefix survives into the squash commit on main.
- PR bodies end with a signature block naming the loop, UTC timestamp, and
  `state: loop-engine-state@glm/state`.
- Its records live ONLY on the `glm/state` branch of loop-engine-state, inside `glm/`. It never
  touches your root files (`schedule.json`, `state.json`, `registry.json`,
  `loop-settings.json`, `prompts/`, `runs/`, `reports/`, `experiments/`), never moves
  `rotation_cursor`, and never pushes to `claude/*` branches or to `main` of anything.

**What to do with GLM's PRs: nothing.** Never merge, edit, close, comment on, or rebase a PR
from a `glm/*` branch — same policy you already apply to human PRs. GLM enforces a
zero-open-PRs rule on itself (it merges or closes everything before its session ends), so you
should rarely ever see one open. If you do find one open, assume its session is still live or
crashed; leave it alone and let the next GLM session resolve it.

**When GLM runs (Africa/Tunis)** — deliberately outside your 01:45 / 06:45 windows:

| Loop | When | PRs |
|---|---|---|
| glm-improvement-am | daily 10:30 | yes (≤2, squash-merge when green) |
| glm-improvement-pm | Tue/Thu/Sat 15:30 | yes (≤2) |
| glm-analyst-scan | daily 21:00 | read-only, findings only |
| glm-backlog-refresh | Sun 12:00 | read-only |
| glm-state-hygiene | Sat 20:00 | read-only |

**Repo scope.** All 8 code repos, including **kinz-price-bridge** (which your rotation skips —
it is now GLM's primary repo). GLM defers to you: it skips any repo with an open `claude/*` PR
or recent `claude/*` activity, and never touches dependabot PRs (still your maintenance job's).
To avoid colliding with it: before picking work, check for open `[glm]` PRs on the repo — if
one exists, choose different files or a different repo.

**Same contract.** GLM follows the same merge rules you do (squash-only, CI must have run and
passed, no existing `.github/workflows/` file modified, no test weakened), plus its own
additions: no lockfile/manifest/auth/secrets/test-harness edits, diff ≤ 400 lines, no new
workflow files, and it never runs the KINZ scrapers or touches `data/competitors_seed.json`.

No action needed from you — this is information, not a task. Keep running exactly as
scheduled.
