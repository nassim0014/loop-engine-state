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
| Maintenance: dependency updates, red CI, conflicts, merge what's green | daily 16:15 | claude.ai routine | yes |
| Improvements: top item on 2 repos, refills improvement lists | Mon, Wed, Fri 10:15 | claude.ai routine | yes |
| Creative idea, judged by a separate Opus agent | Sat 11:40 | claude.ai routine | if verified |
| Weekly summary | Sun 18:30 | claude.ai routine | no |
| Daily commit, only if nothing else landed | daily 22:00 | claude.ai routine | yes |
| Kinz accounting improvement | 03:00 every other day | claude.ai routine | no |
| New private repo (genesis), every 28 days | Wed 14:00, gated | laptop, systemd | no |
| KINZ competitor analyst, read-only, on the fresh weekly scrape | Mon 11:00 | claude.ai routine | no |
| Z.ai keep-going | paused | Z.ai | yes |

Genesis stays on the laptop because cloud sessions cannot create repositories. Its prompt
is `~/.claude/scheduled-tasks/repo-genesis-loop/SKILL.md` on the laptop, run by the
`loop-genesis` systemd timer. Everything else is a claude.ai routine.

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
