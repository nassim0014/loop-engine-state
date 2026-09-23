#!/usr/bin/env python3
"""Tests for make_ics — cron to calendar conversion.

  python scripts/test_make_ics.py

No pytest dependency, same as the other tests here.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_ics import build, first_on_or_after, fold, parse_cron, rrule  # noqa: E402

FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}\n        got  {got}\n        want {want}")
        FAILURES.append(name)


def raises(name: str, fn) -> None:
    try:
        fn()
    except ValueError:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}: no ValueError")
        FAILURES.append(name)


check("daily", rrule(parse_cron("15 16 * * *")), "FREQ=DAILY")
check("weekdays list", rrule(parse_cron("15 10 * * 1,3,5")), "FREQ=WEEKLY;BYDAY=MO,WE,FR")
check("sunday as 7", rrule(parse_cron("30 18 * * 7")), "FREQ=WEEKLY;BYDAY=SU")
check("every 2nd day of month",
      rrule(parse_cron("0 3 */2 * *")),
      "FREQ=MONTHLY;BYMONTHDAY=" + ",".join(str(d) for d in range(1, 32, 2)))
check("time kept", parse_cron("40 11 * * 6")["hour"], 11)
raises("dom and dow together rejected", lambda: parse_cron("0 1 1 * 1"))
raises("out of range rejected", lambda: parse_cron("0 1 * * 9"))
raises("month field rejected", lambda: parse_cron("0 1 * 2 *"))

# 2026-09-24 is a Thursday: the next Saturday is the 26th, the next odd day is the 25th.
check("first Saturday", first_on_or_after(parse_cron("40 11 * * 6"), date(2026, 9, 24)),
      date(2026, 9, 26))
check("first odd day", first_on_or_after(parse_cron("0 3 */2 * *"), date(2026, 9, 24)),
      date(2026, 9, 25))

long = "DESCRIPTION:" + "x" * 200
folded = fold(long)
check("fold keeps content", "".join(s[1:] if i else s for i, s in enumerate(folded)), long)
check("fold line length", max(len(s.encode()) for s in folded) <= 75, True)

sched = {"calendar_start": "2026-09-24", "loops": [
    {"name": "a", "title": "A, b; c", "agent": "claude-cloud", "schedule": "15 16 * * *",
     "schedule_kind": "cron", "timezone": "Africa/Tunis", "enabled": True},
    {"name": "off", "agent": "zai", "schedule": "0 1 * * *", "schedule_kind": "cron",
     "timezone": "Africa/Tunis", "enabled": False},
    {"name": "g", "agent": "claude-laptop", "schedule": "0 14 * * 3", "schedule_kind": "cron",
     "timezone": "Africa/Tunis", "enabled": True,
     "calendar": {"dtstart": "2026-10-14T14:00", "rrule": "FREQ=DAILY;INTERVAL=28"}},
]}
ics = build(sched)
check("disabled loops left out", ics.count("BEGIN:VEVENT"), 2)
check("text escaped", "SUMMARY:A\\, b\\; c" in ics, True)
check("dtstart from cron", "DTSTART;TZID=Africa/Tunis:20260924T161500" in ics, True)
check("calendar override", "RRULE:FREQ=DAILY;INTERVAL=28" in ics
      and "DTSTART;TZID=Africa/Tunis:20261014T140000" in ics, True)
check("CRLF line ends", ics.endswith("END:VCALENDAR\r\n") and "\n" not in ics.replace("\r\n", ""), True)
check("deterministic", build(sched), ics)

print(f"\n{len(FAILURES)} failure(s)")
sys.exit(1 if FAILURES else 0)
