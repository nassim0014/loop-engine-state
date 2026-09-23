#!/usr/bin/env python3
"""Tests for due_jobs, including a check that the real schedule.json is consistent.

  python scripts/test_due_jobs.py

Every dispatched job must fall inside a dispatcher fire's window, or it would never run.
That check runs against the committed schedule.json, so CI catches a job moved to a time
the dispatcher doesn't fire.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from due_jobs import TUNIS, cron_matches, dispatched, due  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}\n        got  {got}\n        want {want}")
        FAILURES.append(name)


def t(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=TUNIS)


# 2026-09-28 is a Monday, 2026-09-27 a Sunday.
check("daily match", cron_matches("15 16 * * *", t("2026-09-28T16:15")), True)
check("wrong minute", cron_matches("15 16 * * *", t("2026-09-28T16:16")), False)
check("weekday list", cron_matches("15 10 * * 1,3,5", t("2026-09-28T10:15")), True)
check("weekday list miss", cron_matches("15 10 * * 1,3,5", t("2026-09-29T10:15")), False)
check("sunday as 0", cron_matches("15 22 * * 0", t("2026-09-27T22:15")), True)
check("hour list", cron_matches("15 10,16,22 * * *", t("2026-09-28T22:15")), True)

sched = {"loops": [
    {"name": "maint", "dispatched": True, "enabled": True, "schedule_kind": "cron",
     "schedule": "15 16 * * *"},
    {"name": "analyst", "dispatched": True, "enabled": True, "schedule_kind": "cron",
     "schedule": "15 16 * * 1"},
    {"name": "off", "dispatched": True, "enabled": False, "schedule_kind": "cron",
     "schedule": "15 16 * * *"},
    {"name": "laptop", "enabled": True, "schedule_kind": "cron", "schedule": "15 16 * * *"},
]}
empty = {"loops": {}}
check("on time, in list order", due(sched, empty, t("2026-09-28T16:15")), ["maint", "analyst"])
check("late start still due", due(sched, empty, t("2026-09-28T17:10")), ["maint", "analyst"])
check("early fire still due", due(sched, empty, t("2026-09-28T15:58")), ["maint", "analyst"])
check("too late", due(sched, empty, t("2026-09-28T17:20")), [])
check("weekday gate", due(sched, empty, t("2026-09-29T16:15")), ["maint"])
recent = {"loops": {"maint": {"last_run": "2026-09-28T14:30:00+00:00"}}}   # 15:30 Tunis
check("ran 45 min ago, not again", due(sched, recent, t("2026-09-28T16:15")), ["analyst"])
old = {"loops": {"maint": {"last_run": "2026-09-27T15:30:00Z"}}}
check("ran yesterday, due", due(sched, old, t("2026-09-28T16:15")), ["maint", "analyst"])

# The real schedule: every dispatched job occurrence in a sample week must be covered
# by a dispatcher fire, or that job would silently never run.
real = json.loads((ROOT / "schedule.json").read_text(encoding="utf-8"))
disp = [l for l in real["loops"] if l.get("prompt") == "prompts/dispatch.md"]
check("exactly one dispatcher", len(disp), 1)
if disp:
    fire = disp[0]["schedule"]
    start = t("2026-09-28T00:00")
    fires = [start + timedelta(minutes=i) for i in range(7 * 24 * 60)
             if cron_matches(fire, start + timedelta(minutes=i))]
    for job in dispatched(real):
        missed = []
        for i in range(7 * 24 * 60):
            when = start + timedelta(minutes=i)
            if cron_matches(job["schedule"], when) and not any(
                    job["name"] in due({"loops": [job]}, empty, f) for f in fires):
                missed.append(when.strftime("%a %H:%M"))
        check(f"{job['name']} covered by the dispatcher", missed, [])
    check("dispatcher has jobs", len(dispatched(real)) > 0, True)

print(f"\n{len(FAILURES)} failure(s)")
sys.exit(1 if FAILURES else 0)
