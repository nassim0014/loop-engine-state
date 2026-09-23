# Cloud job prompts

Each cloud job is a claude.ai routine. The routine itself holds only the short bootstrap
below. The real instructions live here, so every change is a reviewed commit and not an
invisible edit in a settings page.

| Job | Routine name | Prompt |
|---|---|---|
| `cloud-maintenance` | Loop: maintenance | `maintenance.md` |
| `cloud-improvements` | Loop: improvements | `improvements.md` |
| `cloud-creative` | Loop: creative idea | `creative.md` |
| `cloud-weekly-summary` | Loop: weekly summary | `weekly-summary.md` |
| `cloud-daily-commit` | Loop: daily commit | `daily-commit.md` |

`_common.md` holds the rules every job shares: setup, branch names, the three merge
rules, the never-list, and how to finish.

Schedules and trigger ids are in `../schedule.json`. Changing a prompt here takes effect on
the next run. Changing a schedule means updating the routine and `schedule.json` together,
then regenerating the calendar with `python3 scripts/make_ics.py`.

## Bootstrap (the text stored in each routine)

```
You are the cloud-<job> job of Nassim's loop engine. Your instructions are in the private
repo nassim0014/loop-engine-state, branch main: read prompts/_common.md, then
prompts/<job>.md, and follow them. The repo should be at /home/user/loop-engine-state; if it
is not, attach it with add_repo (owner nassim0014, repo loop-engine-state, access push) and
clone it first. If you cannot read those two files, reply only
"FAILED: could not read my instructions" and stop.
```
