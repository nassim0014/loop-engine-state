#!/usr/bin/env python3
"""Which cloud jobs are due now? The dispatcher routine fires a few times a day; this decides.

  python scripts/due_jobs.py                          # due now (Africa/Tunis time)
  python scripts/due_jobs.py --at 2026-09-28T16:20    # due at a given Tunis time

Prints one job name per line, in schedule.json order, and exits 0. Nothing printed means
nothing is due, which is a correct outcome, not a failure.

A job is due when its cron matches a minute in [at - 60 min, at + 20 min]. The routine
scheduler adds some minutes of jitter, and a slow start must not skip a job. A job whose
state.json last_run is under 3 hours old is not due again, so a manual fire on top of a
scheduled one cannot run a job twice.

Only one claude.ai routine exists for all these jobs because repos have to be attached to
a routine by hand in the claude.ai UI. One routine means doing that once.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_ics import expand  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TUNIS = timezone(timedelta(hours=1))          # Africa/Tunis: UTC+1 all year, no DST
WINDOW_BEFORE = timedelta(minutes=60)
WINDOW_AFTER = timedelta(minutes=20)
RECENT = timedelta(hours=3)


def cron_matches(expr: str, dt: datetime) -> bool:
    minute, hour, dom, month, dow = expr.split()
    m, h, mo = expand(minute, 0, 59), expand(hour, 0, 23), expand(month, 1, 12)
    d, w = expand(dom, 1, 31), expand(dow, 0, 7)
    if w is not None:
        w = sorted({x % 7 for x in w})
    if m is not None and dt.minute not in m:
        return False
    if h is not None and dt.hour not in h:
        return False
    if mo is not None and dt.month not in mo:
        return False
    day_ok = dt.day in d if d is not None else None
    wday_ok = (dt.isoweekday() % 7) in w if w is not None else None
    if day_ok is None and wday_ok is None:
        return True
    if day_ok is None or wday_ok is None:
        return bool(day_ok or wday_ok)
    return day_ok or wday_ok                   # cron ORs the two day fields when both are set


def dispatched(sched: dict) -> list[dict]:
    return [l for l in sched["loops"]
            if l.get("dispatched") and l.get("enabled") and l.get("schedule_kind") == "cron"]


def due(sched: dict, state: dict, at: datetime) -> list[str]:
    at = at.astimezone(TUNIS).replace(second=0, microsecond=0)
    out = []
    for l in dispatched(sched):
        span = int((WINDOW_BEFORE + WINDOW_AFTER).total_seconds() // 60)
        start = at - WINDOW_BEFORE
        if not any(cron_matches(l["schedule"], start + timedelta(minutes=i)) for i in range(span + 1)):
            continue
        last = state.get("loops", {}).get(l["name"], {}).get("last_run")
        if last:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            if at - last_dt < RECENT:
                print(f"{l['name']}: ran at {last}, not due again", file=sys.stderr)
                continue
        out.append(l["name"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", help="Tunis local time, YYYY-MM-DDTHH:MM (default: now)")
    args = ap.parse_args()
    at = (datetime.fromisoformat(args.at).replace(tzinfo=TUNIS) if args.at
          else datetime.now(TUNIS))
    sched = json.loads((ROOT / "schedule.json").read_text(encoding="utf-8"))
    state = json.loads((ROOT / "state.json").read_text(encoding="utf-8"))
    for name in due(sched, state, at):
        print(name)


if __name__ == "__main__":
    main()
