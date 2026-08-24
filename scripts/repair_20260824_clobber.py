#!/usr/bin/env python3
"""Repair the 2026-08-24 lost update, and apply Phase 4 to state-repo config.

  python scripts/repair_20260824_clobber.py --dry-run
  python scripts/repair_20260824_clobber.py

Idempotent: re-running against repaired config reports "already correct" and exits 0.

WHAT HAPPENED. The closed loop pulled config at ~10:17, Phase 3 committed
repo-backlog-refresh at 10:21:36, and the loop pushed its stale in-memory copy at
10:21:52. Three fields regressed:

  schedule.json  repo-backlog-refresh entry deleted (it never existed in the stale copy)
  state.json     merge_budget.week_iso 2026-W35 -> 2026-W34 (2026-08-24 is a Monday,
                 so W35 is correct; the loop wrote back a value from before the rollover)
  registry.json  refreshed — inspected, no regression, left alone

Root cause was in state_sync.cmd_push, now fixed: it re-read the fresh blob inside the
SHA-conditional retry loop and then discarded it (`d.clear(); d.update(local)`). Detection
worked; resolution ignored it. See scripts/test_three_way.py, which replays both
regressions above as tests.

This script repairs the data. The code fix is what stops it recurring.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BACKLOG_ENTRY = {
    "name": "repo-backlog-refresh",
    "agent": "claude-laptop",
    "schedule": "0 9 * * 6",
    "schedule_kind": "cron",
    "timezone": "Africa/Tunis",
    "enabled": True,
    "paused_until": None,
    "writes_prs": True,
    "merges": False,
    "purpose": "Weekly backlog top-up: one docs-only PR per repo.",
}
CORRECT_WEEK = "2026-W35"          # 2026-08-24 is a Monday; ISO week 35.
RETIRED = "cloud-weekly-status"    # Phase 4: absorbed by loop-engine-digest.

changes: list[str] = []


def fix_schedule(d: dict) -> None:
    names = [t["name"] for t in d["loops"]]

    if BACKLOG_ENTRY["name"] not in names:
        # Restore in schedule order: after kinz-competitor-analyst, where Phase 3 put it.
        idx = next((i for i, t in enumerate(d["loops"])
                    if t["name"] == "kinz-competitor-analyst"), len(d["loops"]) - 1) + 1
        d["loops"].insert(idx, dict(BACKLOG_ENTRY))
        changes.append("schedule.json: restored repo-backlog-refresh (clobbered)")
    else:
        print("  schedule.json: repo-backlog-refresh already present")

    if RETIRED in names:
        d["loops"] = [t for t in d["loops"] if t["name"] != RETIRED]
        changes.append(f"schedule.json: removed {RETIRED} (Phase 4 retirement)")
    else:
        print(f"  schedule.json: {RETIRED} already removed")


def fix_state(d: dict) -> None:
    wk = d.get("merge_budget", {}).get("week_iso")
    if wk != CORRECT_WEEK:
        d["merge_budget"]["week_iso"] = CORRECT_WEEK
        changes.append(f"state.json: week_iso {wk} -> {CORRECT_WEEK} (rolled backwards)")
    else:
        print(f"  state.json: week_iso already {CORRECT_WEEK}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    targets = [("schedule.json", fix_schedule), ("state.json", fix_state)]
    blobs = {}
    for name, fn in targets:
        d = json.loads((ROOT / name).read_text())
        fn(d)
        blobs[name] = d

    if not changes:
        print("\nalready correct — nothing to repair")
        sys.exit(0)

    print()
    for c in changes:
        print(f"  {'WOULD ' if a.dry_run else ''}{c}")

    if not a.dry_run:
        for name, d in blobs.items():
            (ROOT / name).write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        print("\nwritten. Run scripts/validate_config.py next.")
    sys.exit(0)


if __name__ == "__main__":
    main()
