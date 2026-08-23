# State Protocol

This repo is the **single source of truth**. Laptop and sandbox copies are cache.
Every loop session pulls before acting and writes back before ending.

---

## 1. Write protocol — read → mutate → update with base SHA

Two agents write here (Claude on the laptop, Z.ai in the sandbox) and they do not
coordinate in real time. A blind write loses whatever the other one just did, so every
mutation is conditional on the blob you actually read.

```bash
# 1. read, keeping the SHA you read at
OUT=$(gh api repos/nassim0014/loop-engine-state/contents/state.json)
SHA=$(jq -r .sha <<<"$OUT")
jq -r .content <<<"$OUT" | base64 -d > state.json

# 2. mutate locally
python3 - <<'PY'
import json; s=json.load(open('state.json'))
s['rotation_cursor'] = (s['rotation_cursor'] + 2) % 6
json.dump(s, open('state.json','w'), indent=2)
PY

# 3. update, passing the SHA you read at
gh api -X PUT repos/nassim0014/loop-engine-state/contents/state.json \
  -f message="state: advance cursor (closed-loop)" \
  -f content="$(base64 -w0 state.json)" \
  -f sha="$SHA"
```

**On HTTP 409 (SHA mismatch)** someone else wrote between your read and your write.
Do **not** force. Re-read, re-apply your change on top of the new content, retry.
**Maximum 3 retries**, then abort the session and record the failure in your run
record — three consecutive conflicts means two agents are fighting over the same
field and a human should look.

Never `git push --force` to this repo. Never edit another agent's run record.

---

## 2. Branch naming — all agents

```
loop/<agent>/<YYYY-MM-DD>/<item-slug>
```

- `<agent>` — `claude` or `zai`
- `<item-slug>` — kebab-case, from the backlog item
- If the name is taken, append `-2`, then `-3`, …

Examples:

```
loop/claude/2026-08-22/fix-walk-forward-error-branches
loop/zai/2026-08-22/cover-kpis-routes
loop/zai/2026-08-22/cover-kpis-routes-2
```

Experiment branches from `repo-open-loop` are the one exception — they use
`exp/<date>/<idea>` and never become PRs.

---

## 3. Run records — every session, no exceptions

Each loop session ends by writing `runs/<UTC-timestamp>-<loop>.json`, valid against
`schemas/run-record.schema.json`:

```json
{
  "loop": "repo-closed-loop",
  "agent": "claude-laptop",
  "started": "2026-08-22T10:17:00+00:00",
  "ended":   "2026-08-22T10:51:00+00:00",
  "status":  "success",
  "prs_opened": 2, "prs_merged": 1, "prs_closed": 0, "tests_added": 5,
  "repos_touched": ["btc-llm-sentiment", "Next.js-SaaS"],
  "errors": []
}
```

Timestamp format: `20260822T101700Z`. Validate before committing:

```bash
python scripts/validate_config.py --runs
```

A session with no run record is indistinguishable from a session that never ran —
which is precisely the ambiguity this file exists to remove. `status: "skipped"` is a
valid, useful outcome; write it rather than writing nothing.

---

## 4. Merge budget — GitHub is truth, `state.json` is cache

`merge_budget.merges_this_week` is a **reporting cache only**. Both merging loops
recompute the real number from GitHub at the start of every run:

> agent-marker PRs merged since Monday 00:00 Africa/Tunis, summed across
> `registry.rotation.order`.

The budget is **global and shared** between Claude and Z.ai. A local counter cannot
see the other agent's merges, so it is structurally incapable of being right — that is
why the cap is enforced from GitHub and never from the number in this file.

Dependabot merges and stale-closes do not count against it.

---

## 5. Ownership — who may write what

| Field | Owner | Others |
|---|---|---|
| `rotation_cursor` | `repo-closed-loop` (Claude) | read only |
| `loops.<name>.*` | the named loop | read only |
| `merge_budget` | any merging loop (cache) | recompute, don't trust |
| `registry.json` | `repo-closed-loop` refresh | read only |
| `loop-settings.json` | owner (human) | read only |
| `runs/*.json` | the loop that wrote it | append only, never edit |

Z.ai may work any repo, but **never moves the cursor** — otherwise two agents advance
it independently and the rotation silently skips repos.
