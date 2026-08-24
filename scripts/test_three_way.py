#!/usr/bin/env python3
"""Regression tests for state_sync.three_way — replays the 2026-08-24 clobber.

  python scripts/test_three_way.py

No pytest dependency: this runs in CI and from run-loop.sh preflight, and the
coordination repo should not need a test framework installed to prove its own
merge is sound.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_sync import three_way  # noqa: E402

FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}\n        got  {got}\n        want {want}")
        FAILURES.append(name)


# --- the actual incident -----------------------------------------------------------
# The closed loop pulled schedule.json at 10:17, Phase 3 added repo-backlog-refresh at
# 10:21:36, the loop pushed its stale copy at 10:21:52 and the entry vanished.
base = {"tasks": ["closed", "review"], "version": 1}
local = {"tasks": ["closed", "review"], "version": 1}          # loop changed nothing
remote = {"tasks": ["closed", "review", "backlog"], "version": 1}  # Phase 3 landed
check("stale holder does not revert a concurrent add",
      three_way(base, local, remote), remote)

# The same run rolled merge_budget.week_iso W35 -> W34 by writing back a stale value.
base = {"merge_budget": {"week_iso": "2026-W34", "merges_this_week": 0}}
local = {"merge_budget": {"week_iso": "2026-W34", "merges_this_week": 0}}
remote = {"merge_budget": {"week_iso": "2026-W35", "merges_this_week": 0}}
check("stale nested field does not roll back",
      three_way(base, local, remote), remote)

# --- the merge must still let real edits through ------------------------------------
base = {"rotation_cursor": 2, "tasks": ["a"]}
local = {"rotation_cursor": 3, "tasks": ["a"]}                 # loop advanced the cursor
remote = {"rotation_cursor": 2, "tasks": ["a", "b"]}           # someone else added a task
check("real local edit applies over an untouched remote field",
      three_way(base, local, remote), {"rotation_cursor": 3, "tasks": ["a", "b"]})

# Two agents touching different sub-keys of the same nested object must both survive.
base = {"loops": {"closed": {"runs": 1}, "open": {"runs": 5}}}
local = {"loops": {"closed": {"runs": 2}, "open": {"runs": 5}}}
remote = {"loops": {"closed": {"runs": 1}, "open": {"runs": 6}}}
check("disjoint nested edits both survive",
      three_way(base, local, remote),
      {"loops": {"closed": {"runs": 2}, "open": {"runs": 6}}})

# --- adds and deletes ---------------------------------------------------------------
check("local add is applied",
      three_way({"a": 1}, {"a": 1, "b": 2}, {"a": 1}), {"a": 1, "b": 2})

check("local delete is honoured when remote agrees with base",
      three_way({"a": 1, "b": 2}, {"a": 1}, {"a": 1, "b": 2}), {"a": 1})

# A delete racing an edit: the other agent made the field relevant again, so keep theirs.
check("local delete yields to a concurrent remote edit",
      three_way({"a": 1, "b": 2}, {"a": 1}, {"a": 1, "b": 99}), {"a": 1, "b": 99})

# --- true conflict: both changed the same scalar. Local wins, deliberately. ----------
# The loser here is visible in git history; a silent revert is not. Documented, not ideal.
check("same-field conflict resolves to local (last writer wins)",
      three_way({"a": 1}, {"a": 2}, {"a": 3}), {"a": 2})

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("all three-way merge tests passed")
