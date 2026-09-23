# Cloud job prompts

All cloud jobs run from **one** claude.ai routine, "Loop engine". It fires at 01:45 and 06:45
Tunis time and runs whichever jobs are due (`dispatch.md`, `../scripts/due_jobs.py`). The runs
happen at night because the loops share Nassim's usage limit. There is one routine because repos
have to be attached to a routine by hand in the claude.ai UI, and one routine means doing that once.

The routine holds only a short bootstrap. The real instructions live here, so every change
is a reviewed commit and not an invisible edit in a settings page.

| Job | When (Tunis) | Prompt |
|---|---|---|
| `cloud-maintenance` | daily 01:45, first | `maintenance.md` |
| `cloud-kinz-analyst` | Tue 01:45, the night after Monday's scrape | `kinz-analyst.md` |
| `cloud-improvements` | Mon, Wed, Fri 01:45 | `improvements.md` |
| `cloud-kinz-improvement` | Sun, Tue, Thu 01:45 | `kinz-accounting.md` |
| `cloud-creative` | Sat 01:45 | `creative.md` |
| `cloud-daily-commit` | daily 06:45, after the night jobs | `daily-commit.md` |
| `cloud-weekly-summary` | Mon 06:45 | `weekly-summary.md` |

`_common.md` holds the rules every job shares: setup, the GitHub API, branch names, the
three merge rules, the never-list, and how to finish.

Job times live in `../schedule.json`. A job must sit on one of the dispatcher's three times,
and `scripts/test_due_jobs.py` fails in CI if one doesn't. After changing a time, regenerate
the calendar with `python3 scripts/make_ics.py`.

To run a job by hand, fire the routine with the message `run: <job name>`.

A new repo (from genesis, say) is invisible to every job until it is attached to the
routine. The weekly summary reminds Nassim when a registry repo is missing.

## Bootstrap (the text stored in the routine)

```
You are the dispatcher of Nassim's loop engine. The repo nassim0014/loop-engine-state is
attached to this routine at /home/user/loop-engine-state. Update it to the latest main, then
read prompts/_common.md and prompts/dispatch.md and follow them. If the repo is not there,
reply only "NEEDS YOU: attach loop-engine-state and the work repos to the Loop engine
routine" and stop.
```
