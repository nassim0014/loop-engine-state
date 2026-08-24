#!/usr/bin/env python3
"""Compute the shared weekly merge budget from GitHub truth.

  python scripts/merge_budget.py            # human summary
  python scripts/merge_budget.py --json     # {"used":N,"cap":M,"remaining":K,"can_merge":bool}

The budget is GLOBAL: Claude (laptop) and Z.ai (sandbox) draw from one pool. A
counter in state.json cannot see the other agent's merges, so it is structurally
incapable of being correct — the number is always recomputed from GitHub here and
state.json's copy is a reporting cache only.

Counts agent PRs merged since Monday 00:00 Africa/Tunis.
Dependabot merges and stale-closes are exempt.

WHAT COUNTS, and why it is not the marker alone. Until 2026-08-24 this matched the
literal substring "loop-agent:" in the PR body. On that day a closed-loop cycle merged
kinz-secure-commerce-hub#46 with the body line "Loop-Agent: closed-loop / claude / laptop"
— different case, different layout, no zero-width prefix. The substring did not match, so
the merge was invisible and the budget reported 0/20 while at least one merge had landed.

A marker is a convention the writing agent has to remember to apply; a budget is a control.
Resting a control on a convention lets the controlled party opt out of it by reformatting a
string. The branch prefix is structural instead — a loop PR cannot exist without the branch
it was pushed to — so `loop/` and `exp/` heads are the primary signal, with a
case-insensitive marker match kept as a fallback for anything pushed from another layout.
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

REPO = "nassim0014/loop-engine-state"
TZ = timezone(timedelta(hours=1))          # Africa/Tunis, fixed +01:00, no DST
MARKER = "loop-agent:"                      # visible substring, matched case-insensitively
AGENT_HEADS = ("loop/", "exp/")             # structural signal; see module docstring
BOT_AUTHORS = {"dependabot", "app/dependabot", "github-actions", "app/github-actions"}


def is_agent_merge(pr: dict) -> bool:
    """A merged PR counts against the shared budget if an agent authored the branch.

    Branch prefix first: it cannot be omitted the way a body marker can. The marker
    check is a case-insensitive fallback so a PR pushed from some other layout still
    counts rather than silently slipping the cap.
    """
    if (pr.get("author") or {}).get("login", "").lower() in BOT_AUTHORS:
        return False
    head = pr.get("headRefName") or ""
    if head.startswith(AGENT_HEADS):
        return True
    return MARKER in (pr.get("body") or "").lower()


def gh_json(*args: str):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def remote(path: str):
    meta = gh_json("api", f"repos/{REPO}/contents/{path}")
    return json.loads(base64.b64decode(meta["content"]).decode())


def week_start() -> datetime:
    now = datetime.now(TZ)
    monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    return monday


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    reg = remote("registry.json")
    settings = remote("loop-settings.json")
    cap = settings["merge_policy"]["auto_merge_weekly_cap"]
    since = week_start()
    since_utc = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    per_repo, used = {}, 0
    for name in reg["rotation"]["order"]:
        try:
            prs = gh_json("pr", "list", "-R", f"nassim0014/{name}", "--state", "merged",
                          "--limit", "100", "--json",
                          "number,body,mergedAt,headRefName,author") or []
        except RuntimeError as e:
            print(f"WARN could not read {name}: {e}", file=sys.stderr)
            continue
        n = sum(1 for p in prs
                if p.get("mergedAt", "") >= since_utc and is_agent_merge(p))
        per_repo[name] = n
        used += n

    remaining = max(0, cap - used)
    out = {"week_start_local": since.isoformat(), "cap": cap, "used": used,
           "remaining": remaining, "can_merge": remaining > 0, "per_repo": per_repo}

    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"week from {since:%Y-%m-%d %H:%M %Z}")
        for k, v in per_repo.items():
            if v:
                print(f"  {k:<34}{v}")
        print(f"\n  used {used} / cap {cap}  ->  remaining {remaining}"
              f"  ({'MERGING ALLOWED' if remaining else 'BUDGET EXHAUSTED — open/close only'})")
    sys.exit(0 if remaining > 0 else 3)


if __name__ == "__main__":
    main()
