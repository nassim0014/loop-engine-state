#!/usr/bin/env python3
"""Retire the cloud `weekly-status` routine — loop-engine-digest absorbed it.

  python scripts/retire_cloud_weekly_status.py --dry-run
  python scripts/retire_cloud_weekly_status.py

Idempotent: if the routine is already disabled, this reports and exits 0.

DISABLE, NOT DELETE. The claude.ai remote-trigger API exposes list/get/create/update/run
but no delete, and disabling is the reversible option regardless — a one-field flip to
restore if the merged digest turns out to miss something the standalone report covered.
The schedule.json entry is removed either way so the calendar stops advertising it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TRIGGER_ID = "trig_01XPrcRnF5nLUdt1ZT5wAg9j"     # "Weekly status update", Fri 15:00 UTC
SCHEDULE = Path("/home/kiwif/loop-engine/schedule.json")


def api(method: str, path: str, body: dict | None = None) -> dict:
    cmd = ["gh", "api", "-X", method, f"https://api.claude.ai/api{path}"]
    if body:
        cmd += ["--input", "-"]
    r = subprocess.run(cmd, input=json.dumps(body) if body else None,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout) if r.stdout.strip() else {}


def drop_from_schedule(dry: bool) -> bool:
    """Remove the calendar entry so the .ics stops advertising a retired routine."""
    d = json.loads(SCHEDULE.read_text())
    before = len(d["tasks"])
    d["tasks"] = [t for t in d["tasks"] if t["id"] != "cloud-weekly-status"]
    if len(d["tasks"]) == before:
        print("  schedule.json: no cloud-weekly-status entry (already removed)")
        return False
    if dry:
        print("  schedule.json: WOULD remove cloud-weekly-status")
    else:
        SCHEDULE.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        print("  schedule.json: removed cloud-weekly-status")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    print(f"retire cloud-weekly-status ({TRIGGER_ID})")
    print("  reason: loop-engine-digest now produces the single weekly report;")
    print("          two reports for one week was the thing being fixed.\n")

    drop_from_schedule(a.dry_run)

    print("\n  NOTE: the remote trigger itself must be disabled via the RemoteTrigger")
    print("        tool or the claude.ai routines UI — this script cannot reach the")
    print("        claude.ai API through `gh`. It handles the local half only.")
    print("        Target state: enabled = false.")
    sys.exit(0)


if __name__ == "__main__":
    main()
