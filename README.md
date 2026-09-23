# loop-engine-state

Control repo for Nassim's scheduled agent loops: what runs, when, with which instructions,
and a record of every run. Private. Nothing here is a work target for the loops.

## What the loops are for

In order of priority (owner, 2026-09-23):
1. Real improvements to the repos Nassim uses or shows people.
2. An active GitHub profile.
3. Learning how to build agent systems.

The agents work on their own, merges included. Nassim hears about it in two ways: a phone
alert when a run fails or needs him, and a weekly summary on Sunday evening.

## What runs where (times are Africa/Tunis)

| Job | When | Where | Merges |
|---|---|---|---|
| Maintenance: dependency updates, red CI, conflicts, merge what's green | daily 16:15 | Loop engine routine | yes |
| KINZ competitor analyst, read-only, on the fresh weekly scrape | Mon 16:15 | Loop engine routine | no |
| Improvements: top item on 2 repos, refills improvement lists | Mon, Wed, Fri 10:15 | Loop engine routine | yes |
| Creative idea, judged by a separate Opus agent | Sat 10:15 | Loop engine routine | if verified |
| Daily commit, only if nothing else landed | daily 22:15 | Loop engine routine | yes |
| Weekly summary | Sun 22:15 | Loop engine routine | no |
| Kinz accounting improvement: 1-3 tested fixes | Sun, Tue, Thu 10:15 | Loop engine routine | yes |
| New private repo (genesis), every 28 days | Wed 14:00, gated | laptop, systemd | no |
| Z.ai keep-going | paused | Z.ai | yes |

"Loop engine" is one claude.ai routine that fires at 10:15, 16:15 and 22:15 and runs the
jobs that are due (`prompts/dispatch.md`). The repos are attached to that routine, so a new
repo has to be attached there before any job can see it.

Genesis stays on the laptop because cloud sessions cannot create repositories. Its prompt
is `~/.claude/scheduled-tasks/repo-genesis-loop/SKILL.md` on the laptop, run by the
`loop-genesis` systemd timer.

## Files

| Path | What |
|---|---|
| `schedule.json` | Every job, its schedule and routine id. Source of the calendar. |
| `prompts/` | Instructions for the cloud jobs. Each routine only points here. |
| `registry.json` | The repos, which agent works each one, and notes for future runs. |
| `state.json` | Rotation position and each loop's last run. |
| `loop-settings.json` | Merge rules and genesis settings. |
| `runs/` | One record per run, with a link to the session that did it. |
| `experiments/` | Creative-job goals, written before the work, and the judge's verdict. |
| `reports/` | Weekly summaries. |
| `calendar/loop-engine.ics` | Calendar of all jobs. Regenerate with `python3 scripts/make_ics.py`. |
| `docs/STATE_PROTOCOL.md` | How writers share this repo without overwriting each other. |

## Checks

```
pip install jsonschema
python3 scripts/validate_config.py --runs
python3 scripts/test_make_ics.py && python3 scripts/make_ics.py --check
python3 scripts/test_three_way.py
```

CI runs all of these on every push.
