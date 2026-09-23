#!/usr/bin/env python3
"""Build the loop calendar (.ics) from schedule.json.

  python scripts/make_ics.py            # write calendar/loop-engine.ics
  python scripts/make_ics.py --check    # exit 3 if the committed calendar is stale

Idempotent: the output depends only on schedule.json, never on today's date, so re-running
with an unchanged schedule prints "already up to date" and writes nothing. DTSTART is the
first occurrence on or after schedule.json's `calendar_start`.

Replaces the laptop-only bin/make-calendar.py, which read systemd and the laptop's task
folders. The schedule is the source of truth now, and it lives in this repo.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / "schedule.json"
OUT = ROOT / "calendar" / "loop-engine.ics"

DAYS = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"]      # cron numbering: 0 = Sunday

# Africa/Tunis is UTC+1 all year (no DST since 2009), so one fixed rule is exact.
VTIMEZONE = [
    "BEGIN:VTIMEZONE",
    "TZID:Africa/Tunis",
    "BEGIN:STANDARD",
    "DTSTART:19700101T000000",
    "TZOFFSETFROM:+0100",
    "TZOFFSETTO:+0100",
    "TZNAME:CET",
    "END:STANDARD",
    "END:VTIMEZONE",
]


def expand(field: str, lo: int, hi: int) -> list[int] | None:
    """Cron field -> sorted values, or None for '*'. Supports N, a-b, a,b and */N."""
    if field == "*":
        return None
    vals: set[int] = set()
    for part in field.split(","):
        if part.startswith("*/"):
            vals.update(range(lo, hi + 1, int(part[2:])))
        elif "-" in part:
            a, b = part.split("-")
            vals.update(range(int(a), int(b) + 1))
        else:
            vals.add(int(part))
    bad = [v for v in vals if not lo <= v <= hi]
    if bad:
        raise ValueError(f"cron value(s) {bad} outside {lo}..{hi} in '{field}'")
    return sorted(vals)


def parse_cron(expr: str) -> dict:
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"expected 5 cron fields, got {len(parts)}: '{expr}'")
    minute, hour, dom, month, dow = parts
    if month != "*":
        raise ValueError(f"month field must be '*': '{expr}'")
    if dom != "*" and dow != "*":
        raise ValueError(f"cron ORs day-of-month with day-of-week; not supported: '{expr}'")
    days = expand(dow, 0, 7)
    if days is not None:
        days = sorted({d % 7 for d in days})          # 7 is also Sunday in cron
    return {"minute": int(minute), "hour": int(hour),
            "dom": expand(dom, 1, 31), "dow": days}


def rrule(c: dict) -> str:
    if c["dow"] is not None:
        return "FREQ=WEEKLY;BYDAY=" + ",".join(DAYS[d] for d in c["dow"])
    if c["dom"] is not None:
        return "FREQ=MONTHLY;BYMONTHDAY=" + ",".join(str(d) for d in c["dom"])
    return "FREQ=DAILY"


def matches(c: dict, d: date) -> bool:
    if c["dow"] is not None:
        return (d.isoweekday() % 7) in c["dow"]
    if c["dom"] is not None:
        return d.day in c["dom"]
    return True


def first_on_or_after(c: dict, start: date) -> date:
    for i in range(62):
        d = start + timedelta(days=i)
        if matches(c, d):
            return d
    raise ValueError("no occurrence within 62 days")


def esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def fold(line: str) -> list[str]:
    """RFC 5545: lines longer than 75 octets continue on the next line after a space."""
    out, cur = [], ""
    for ch in line:
        limit = 75 if not out else 74
        if len((cur + ch).encode("utf-8")) > limit:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    out.append(cur)
    return [out[0]] + [" " + s for s in out[1:]]


def events(sched: dict) -> list[list[str]]:
    start = date.fromisoformat(sched.get("calendar_start", "2026-01-01"))
    stamp = start.strftime("%Y%m%dT000000Z")
    evs = []
    for l in sched["loops"]:
        if not l.get("enabled") or l.get("schedule_kind") != "cron":
            continue
        if l.get("timezone", "Africa/Tunis") != "Africa/Tunis":
            raise ValueError(f"{l['name']}: only Africa/Tunis is supported")
        cal = l.get("calendar")
        if cal:
            dtstart = cal["dtstart"].replace("-", "").replace(":", "") + "00"
            rule = cal["rrule"]
        else:
            c = parse_cron(l["schedule"])
            d = first_on_or_after(c, start)
            dtstart = f"{d:%Y%m%d}T{c['hour']:02d}{c['minute']:02d}00"
            rule = rrule(c)
        where = {"claude-cloud": "claude.ai routine", "claude-laptop": "laptop",
                 "zai": "Z.ai"}.get(l["agent"], l["agent"])
        desc = [l.get("purpose", ""), f"Runs on: {where}.",
                f"Merges: {'yes' if l.get('merges') else 'no'}."]
        if l.get("prompt"):
            desc.append(f"Prompt: loop-engine-state/{l['prompt']}.")
        if cal and cal.get("note"):
            desc.append(cal["note"])
        evs.append([
            "BEGIN:VEVENT",
            f"UID:{l['name']}@loop-engine-state.nassim0014",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID=Africa/Tunis:{dtstart}",
            "DURATION:PT30M",
            f"RRULE:{rule}",
            f"SUMMARY:{esc(l.get('title', l['name']))}",
            f"DESCRIPTION:{esc(' '.join(x for x in desc if x))}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ])
    return evs


def build(sched: dict) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//nassim0014//loop-engine-state//EN",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:Loop engine",
             "X-WR-TIMEZONE:Africa/Tunis", *VTIMEZONE]
    for ev in events(sched):
        lines += ev
    lines.append("END:VCALENDAR")
    return "".join(f + "\r\n" for line in lines for f in fold(line))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 3 if the calendar is stale")
    args = ap.parse_args()

    text = build(json.loads(SCHEDULE.read_text(encoding="utf-8")))
    current = OUT.read_bytes().decode("utf-8") if OUT.exists() else None
    if current == text:
        print(f"already up to date: {OUT.relative_to(ROOT)}")
        return
    if args.check:
        print(f"STALE: {OUT.relative_to(ROOT)} does not match schedule.json; "
              "run python3 scripts/make_ics.py")
        sys.exit(3)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(text.encode("utf-8"))
    print(f"wrote {OUT.relative_to(ROOT)} ({text.count('BEGIN:VEVENT')} events)")


if __name__ == "__main__":
    main()
