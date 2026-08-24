#!/usr/bin/env python3
"""Genesis truth guard — ask GitHub whether a repo was recently created.

  python scripts/genesis_guard.py            # {"guard_days":21,"blocking":[...]}
  exit 0 = clear to proceed - exit 3 = blocked

The lease in state_sync.py protects against a crash WITHIN a cycle. This protects
against state being wrong BETWEEN cycles — a restored backup, a hand-edit, a botched
merge. GitHub cannot lie about which repos exist; state.json can.

Only repos genesis itself could have produced count as evidence. A naive
"any repo created in the last N days" check treats infrastructure and hand-made repos
as a double-run — loop-engine-state, created by the owner, would have blocked genesis
for three weeks for no reason.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

STATE_REPO = "nassim0014/loop-engine-state"
# Never genesis output: engine infrastructure.
INFRA = {"loop-engine-state"}


def remote(path: str) -> dict:
    r = subprocess.run(["gh", "api", f"repos/{STATE_REPO}/contents/{path}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"cannot read {path}: {r.stderr.strip()}")
    return json.loads(base64.b64decode(json.loads(r.stdout)["content"]))


def main() -> None:
    reg = remote("registry.json")
    settings = remote("loop-settings.json")
    guard_days = settings["genesis"]["duplicate_guard_days"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=guard_days)

    manual = {r["name"] for r in reg["repos"] if r.get("created_by") == "manual"}
    excluded = INFRA | manual

    r = subprocess.run(["gh", "repo", "list", "nassim0014", "--limit", "100",
                        "--json", "name,createdAt"], capture_output=True, text=True)
    repos = json.loads(r.stdout or "[]")

    blocking = [
        {"name": x["name"], "created": x["createdAt"][:10]}
        for x in repos
        if datetime.fromisoformat(x["createdAt"].replace("Z", "+00:00")) > cutoff
        and x["name"] not in excluded
    ]

    print(json.dumps({
        "guard_days": guard_days,
        "cutoff": cutoff.date().isoformat(),
        "excluded_as_not_genesis_output": sorted(excluded),
        "blocking": blocking,
        "clear_to_proceed": not blocking,
    }, indent=2))
    sys.exit(3 if blocking else 0)


if __name__ == "__main__":
    main()
