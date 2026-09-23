# State Protocol

This repo is the **single source of truth**. Laptop and sandbox copies are cache.
Every loop session pulls before acting and writes back before ending.

What runs where is in `README.md`; the cloud jobs' instructions are in `prompts/`.

---

## 1. Write protocol — read → mutate → update with base SHA

Several writers share this repo: the Claude cloud jobs, the laptop's genesis and analyst,
and Z.ai. They do not coordinate in real time. A blind write loses whatever the other one
just did, so every mutation must be conditional on what you actually read.

**Cloud jobs** use git itself as the condition: commit, then
`git pull --rebase origin main && git push origin HEAD:main`, and retry up to 3 times.
A push onto a moved `main` is refused, never silently applied. Run records are new files,
so they never conflict. Each job edits only its own `loops.<name>` entry in `state.json`.

**Laptop and Z.ai** use the contents API with the blob SHA, below, or `scripts/state_sync.py`,
which does it with a three-way merge.

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

## 2. Branch naming — who made a PR is read from its branch

| Prefix | Who |
|---|---|
| `claude/loop-<job>-<YYYYMMDD>-<slug>` | Claude cloud jobs (current) |
| `claude/auto-improve-<YYYY-MM-DD>` | the Kinz accounting routine |
| `loop/zai/<YYYY-MM-DD>/<slug>` | Z.ai |
| `loop/claude/…`, `exp/…` | retired laptop loops (older PRs only) |

The branch is structural: a PR cannot exist without the branch it was pushed from. The
hidden zero-width marker in PR bodies is retired. It was a convention the writing agent had
to remember, and it caused a budget miscount on 2026-08-24.

Once Z.ai has its own GitHub account, its PRs are also told apart by author. Until then its
commits show as `nassim0014` like everything else, so the branch prefix is the only signal.

---

## 3. Run records — every session, no exceptions

Each loop session ends by writing `runs/<UTC-timestamp>-<loop>.json`, valid against
`schemas/run-record.schema.json`:

```json
{
  "loop": "cloud-improvements",
  "run_url": "https://claude.ai/code/session_01AbC...",
  "started": "2026-09-24T09:15:02Z",
  "ended":   "2026-09-24T09:41:40Z",
  "status":  "success",
  "prs_opened": 2, "prs_merged": 1, "prs_closed": 0, "tests_added": 5,
  "repos_touched": ["btc-llm-sentiment", "Next.js-SaaS"],
  "pr_urls": ["https://github.com/nassim0014/btc-llm-sentiment/pull/61"],
  "summary": "Fixed the empty-input crash in walk_forward; Next.js-SaaS PR waiting on CI.",
  "errors": []
}
```

`run_url` replaces the old `agent` field. Every laptop record said `claude-laptop` whoever
actually wrote it, so the field could not answer "who did this". A session link can be
opened and checked. Z.ai records use a link to its own job or commit instead. Old records
with `agent` still validate.

Timestamp format: `20260822T101700Z`. Validate before committing:

```bash
python scripts/validate_config.py --runs
```

A session with no run record is indistinguishable from a session that never ran —
which is precisely the ambiguity this file exists to remove. `status: "skipped"` is a
valid, useful outcome; write it rather than writing nothing.

---

## 4. Merge rules — no caps, but CI must mean something

Owner decision, 2026-09-23: agents merge with no weekly or per-run cap. The merge budget,
its cache in `state.json` and `merge_budget.py` are gone. What stays, in
`loop-settings.json`, is what keeps CI worth trusting once merging is automatic:

1. Merge only when CI ran on the PR head and every check passed. No checks means no merge.
2. Never modify, delete or rename an existing file under `.github/workflows/`. Adding a new
   workflow is allowed only when no existing workflow runs on pull requests.
3. Never delete, skip or weaken a test.

The full wording the jobs follow is in `prompts/_common.md` §3.

---

## 5. Ownership — who may write what

| Field | Owner | Others |
|---|---|---|
| `rotation_cursor` | `cloud-improvements` | read only |
| `loops.<name>.*` | the named loop | read only |
| `registry.json` repo `notes` | the job working that repo | read only |
| `registry.json` `worked_by`, `in_rotation` | owner (human) | read only |
| `loop-settings.json`, `schedule.json`, `prompts/` | owner (human) | read only |
| `experiments/*.md` | `cloud-creative` | append only |
| `reports/*.md` | `cloud-weekly-summary` | read only |
| `runs/*.json` | the loop that wrote it | append only, never edit |

Each repo has one `worked_by` agent. Only that agent starts new work there, so Claude and
Z.ai never race on the same repo. That replaces the old "Z.ai may work any repo" rule, which
relied on both agents checking each other's open PRs.
