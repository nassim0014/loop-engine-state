#!/usr/bin/env python3
"""Print the final schedule table — declared config vs what systemd will actually do.

  python scripts/schedule_table.py

The `enabled` column is deliberately NOT read from schedule.json. That field is an
intention; `systemctl is-enabled` is the fact. When they disagree the table says so,
because "enabled: true" in a config file next to a disabled timer is exactly the kind
of quiet mismatch that makes a loop look scheduled when nothing will ever fire it.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / "schedule.json"

# schedule.json name -> systemd timer unit. Loops with no unit run elsewhere.
UNITS = {
    "repo-closed-loop": "loop-closed.timer",
    "repo-review-loop": "loop-review.timer",
    "repo-open-loop": "loop-open.timer",
    "repo-genesis-loop": "loop-genesis.timer",
    "repo-backlog-refresh": "loop-backlog.timer",
}


def unit_state(unit: str) -> str:
    r = subprocess.run(["systemctl", "--user", "is-enabled", unit],
                       capture_output=True, text=True)
    return (r.stdout or r.stderr).strip() or "unknown"


def main() -> None:
    loops = json.loads(SCHEDULE.read_text())["loops"]

    rows, notes = [], []
    for t in loops:
        name = t["name"]
        unit = UNITS.get(name)
        if unit:
            actual = unit_state(unit)
            enabled = {"enabled": "yes", "disabled": "NO"}.get(actual, actual)
            if t.get("enabled") and actual != "enabled":
                notes.append(f"{name}: config says enabled, timer is {actual}")
        else:
            # Cloud routines and in-app tasks have no local timer to inspect.
            enabled = "yes (cloud)" if t["agent"].endswith("cloud") else "yes (in-app)"

        rows.append([
            name,
            t["agent"],
            t["schedule"] or "one-time",
            t["timezone"],
            "yes" if t.get("writes_prs") else "no",
            "YES" if t.get("merges") else "no",
            enabled,
        ])

    head = ["loop", "agent", "schedule", "timezone", "writes_prs", "merges", "enabled"]
    w = [max(len(str(r[i])) for r in [head, *rows]) for i in range(len(head))]
    line = "  ".join("-" * n for n in w)

    print("  ".join(h.ljust(w[i]) for i, h in enumerate(head)))
    print(line)
    for r in rows:
        print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))
    print(line)
    print(f"{len(rows)} loops - "
          f"{sum(1 for r in rows if r[5] == 'YES')} with merge authority - "
          f"{sum(1 for r in rows if r[6] == 'NO')} awaiting enable")

    if notes:
        print("\nCONFIG/SYSTEMD MISMATCH — intention vs fact:")
        for n in notes:
            print(f"  - {n}")


if __name__ == "__main__":
    main()
