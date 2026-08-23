#!/usr/bin/env python3
"""Migrate laptop-local loop-engine config into state-repo target formats.

Idempotent: re-running produces the same output (only `updated_at` moves).
Reads from --src (default /home/kiwif/loop-engine), writes into --dest (default .).

  python scripts/install_migrate_config.py --dry-run   # print, write nothing
  python scripts/install_migrate_config.py             # write
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

# Repos deliberately outside the rotation, with the reason. Anything not listed
# and not opted-out becomes a normal rotation repo.
SPECIAL_ROLES = {
    "kinz-price-bridge": (
        "bridge",
        False,
        "Created by genesis 2026-08-19 then orphaned empty when that run hit the usage "
        "limit mid-scaffold. Held out of rotation until it has code — the closed loop "
        "cannot work a repo with no content. Genesis adopts and finishes it on its next run.",
    ),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def migrate_registry(old: dict) -> dict:
    repos, order = [], []
    for r in sorted(old["repos"], key=lambda x: x["name"].lower()):
        name = r["name"]
        if r.get("opt_out"):
            role, in_rot, extra = "cloud-owned", False, r.get("opt_out_reason", "")
        elif name in SPECIAL_ROLES:
            role, in_rot, extra = SPECIAL_ROLES[name]
        else:
            role, in_rot, extra = "rotation", True, ""

        notes = r.get("notes") or []
        if isinstance(notes, list):
            notes = " | ".join(notes)
        if extra:
            notes = f"{extra} || {notes}" if notes else extra

        entry = {
            "name": name,
            "owner": "nassim0014",
            "visibility": (r.get("visibility") or "private").lower(),
            "in_rotation": in_rot,
            "role": role,
            "created_by": "genesis-loop" if name in
                          ("kinz-price-bridge", "analytics-service-toolkit") else "manual",
        }
        if notes:
            entry["notes"] = notes
        repos.append(entry)
        if in_rot:
            order.append(name)

    return {"version": 1, "updated_at": now_iso(),
            "repos": repos, "rotation": {"order": order}}


def migrate_state(old: dict, order: list[str]) -> dict:
    """Old flat state -> per-loop structure. Cursor is clamped into the new order."""
    cursor = old.get("rotation_cursor", 0)
    if order:
        cursor = cursor % len(order)

    def loop(last, status="idle"):
        return {"last_run": f"{last}T00:00:00+00:00" if last else None, "status": status,
                "consecutive_failures": 0}

    week = datetime.now(timezone.utc).isocalendar()
    return {
        "version": 1,
        "updated_at": now_iso(),
        "rotation_cursor": cursor,
        "loops": {
            "repo-closed-loop":   loop(old.get("last_closed_run")),
            "repo-review-loop":   loop(None),
            "repo-open-loop":     loop(old.get("last_open_run")),
            "repo-genesis-loop":  {**loop(old.get("last_genesis_run")), "status": "paused",
                                   "notes": "Paused by owner until the 2d crash test passes."},
            "loop-engine-digest": loop(None),
            "repo-backlog-refresh": loop(None),
            # Non-rotation loops still need entries: validate_config warns on any
            # enabled loop in schedule.json with no state, and a loop nobody tracks
            # is one nobody notices has stopped.
            "kinz-competitor-analyst": loop(None),
            "cloud-kinz-improvement": loop(None),
            "cloud-daily-commit": loop(None),
            "cloud-weekly-status": loop(None),
        },
        # Cache only. Every merging loop recomputes this from GitHub truth.
        "merge_budget": {"week_iso": f"{week[0]}-W{week[1]:02d}",
                         "merges_this_week": 0, "opened_this_week": 0},
    }


def migrate_schedule(old: dict) -> dict:
    """Calendar-shaped entries -> loop-shaped schedule. Cloud routines keep their agent."""
    AGENT = {"local": "claude-laptop", "cloud": "zai-cloud"}
    PURPOSE = {
        "repo-closed-loop": "Work the top backlog item on N repos by rotation; open PRs.",
        "repo-review-loop": "Daily sweep + janitor: merge green PRs, triage conflicts, report red CI.",
        "repo-open-loop": "Weekly experiment; pushes a branch and opens an ISSUE, never a PR.",
        "repo-genesis-loop": "Every 28 days, create one new private repo coherent with the portfolio.",
        "loop-engine-digest": "Weekly read-only report across all loops and repos.",
        "kinz-competitor-analyst": "Read-only KINZ data-quality analysis; writes findings only.",
        "repo-backlog-refresh": "Weekly backlog top-up: one docs-only PR per repo.",
    }
    MERGES = {"repo-closed-loop", "repo-review-loop"}
    WRITES_PRS = {"repo-closed-loop", "repo-review-loop", "repo-backlog-refresh"}

    loops = []
    for t in old.get("tasks", []):
        tid = t["id"]
        if tid == "loop-engine-day1-review":
            continue  # one-time, already fired
        loops.append({
            "name": tid,
            "agent": AGENT.get(t.get("where"), "claude-laptop"),
            "schedule": t.get("cron") or "",
            "schedule_kind": "cron",
            "timezone": "Africa/Tunis",
            "enabled": True,
            "paused_until": None,
            "writes_prs": tid in WRITES_PRS,
            "merges": tid in MERGES,
            "purpose": PURPOSE.get(tid, t.get("summary", "")),
        })
    return {"version": 1, "timezone_default": "Africa/Tunis", "loops": loops}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/home/kiwif/loop-engine")
    ap.add_argument("--dest", default=".")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src, dest = Path(a.src), Path(a.dest)

    reg = migrate_registry(json.loads((src / "registry.json").read_text()))
    st = migrate_state(json.loads((src / "state.json").read_text()),
                       reg["rotation"]["order"])
    sch = migrate_schedule(json.loads((src / "schedule.json").read_text()))
    pol = json.loads((src / "merge-policy.json").read_text())
    pol.pop("_comment", None)

    out = {"registry.json": reg, "state.json": st,
           "schedule.json": sch, "loop-settings.json": pol}

    for fname, data in out.items():
        blob = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if a.dry_run:
            print(f"--- {fname} ({len(blob)} bytes) ---")
        else:
            (dest / fname).write_text(blob, encoding="utf-8")
            print(f"wrote {fname}")

    if not a.dry_run:
        print(f"\nrotation ({len(reg['rotation']['order'])}): "
              f"{', '.join(reg['rotation']['order'])}")
        print(f"cursor: {st['rotation_cursor']} -> "
              f"{reg['rotation']['order'][st['rotation_cursor']]}")


if __name__ == "__main__":
    main()
