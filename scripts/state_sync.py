#!/usr/bin/env python3
"""Pull/push loop-engine state against the state repo — the single source of truth.

  python scripts/state_sync.py pull                     # fetch config into --work
  python scripts/state_sync.py push -m "closed-loop: advance cursor"
  python scripts/state_sync.py lease --loop repo-genesis-loop --acquire
  python scripts/state_sync.py lease --loop repo-genesis-loop --release --status done

Writes are SHA-conditional (read -> mutate -> update with base SHA). On 409 the
change is re-applied on top of the newer blob, up to 3 times, then it aborts.
Two agents write here and never coordinate in real time, so a blind write would
silently drop whichever one lost the race.

`push` merges three ways: base (what the remote said at pull time) vs local vs the
CURRENT remote. Only fields the local side actually changed are applied; everything
it merely held a stale copy of is left at whatever the remote now says.

This is not decoration. Until 2026-08-24 push did `d.clear(); d.update(local)` inside
the retry loop — it re-read the fresh blob and immediately threw it away. Detection
worked and resolution ignored it, so the retry loop turned a safe 409 into a guaranteed
overwrite. It ate a config commit that had landed 16 seconds earlier. Optimistic
concurrency needs BOTH halves; the base snapshot is what makes the second half possible,
because without it you cannot tell "I changed this field" from "my copy is old".
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = "nassim0014/loop-engine-state"
FILES = ["registry.json", "state.json", "schedule.json", "loop-settings.json"]
MAX_RETRIES = 3


def gh_json(*args: str):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {r.stderr.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def read_remote(path: str) -> tuple[dict, str]:
    """Return (parsed_json, blob_sha). The SHA is what makes the next write safe."""
    meta = gh_json("api", f"repos/{REPO}/contents/{path}")
    raw = base64.b64decode(meta["content"]).decode("utf-8")
    return json.loads(raw), meta["sha"]


def write_remote(path: str, data: dict, sha: str, message: str) -> bool:
    body = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    r = subprocess.run(
        ["gh", "api", "-X", "PUT", f"repos/{REPO}/contents/{path}",
         "-f", f"message={message}",
         "-f", f"content={base64.b64encode(body.encode()).decode()}",
         "-f", f"sha={sha}"],
        capture_output=True, text=True)
    if r.returncode == 0:
        return True
    if "409" in r.stderr or "does not match" in r.stderr.lower():
        return False          # conflict — caller re-reads and retries
    raise RuntimeError(f"write {path} failed: {r.stderr.strip()}")


def mutate(path: str, fn, message: str) -> dict:
    """Apply fn to the remote blob, SHA-conditionally, retrying on conflict."""
    for attempt in range(1, MAX_RETRIES + 1):
        data, sha = read_remote(path)
        fn(data)
        data["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        if write_remote(path, data, sha, message):
            if attempt > 1:
                print(f"  (succeeded on attempt {attempt} after conflict)")
            return data
        print(f"  409 conflict on {path}, re-reading (attempt {attempt}/{MAX_RETRIES})")
    raise SystemExit(
        f"ABORT: {MAX_RETRIES} consecutive conflicts on {path}. Two agents are "
        f"contending for the same field — a human should look before retrying.")


def three_way(base: dict, local: dict, remote: dict) -> dict:
    """Apply local's changes (measured against base) on top of remote.

    A field the local side never touched keeps the REMOTE value, however stale the
    local copy is. That single rule is what stops one loop's in-memory snapshot from
    reverting another agent's concurrent edit.

    Lists are atomic — schedule.json's `tasks` array is replaced only if the local
    side genuinely changed it. Element-wise list merging would need stable identity
    per element and is not worth the ambiguity here.
    """
    out = dict(remote)
    for k in set(base) | set(local):
        if k not in local:
            # Local deleted it. Honour that only if the remote still agrees with base;
            # if the remote changed it too, someone made it relevant again — keep theirs.
            if k in base and remote.get(k) == base[k]:
                out.pop(k, None)
            continue
        if k not in base:
            out[k] = local[k]                      # local added it
            continue
        if local[k] == base[k]:
            continue                                # untouched locally -> remote wins
        if isinstance(local[k], dict) and isinstance(base[k], dict) \
                and isinstance(out.get(k), dict):
            out[k] = three_way(base[k], local[k], out[k])
        else:
            out[k] = local[k]
    return out


def cmd_pull(a) -> None:
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    basedir = work / ".base"; basedir.mkdir(exist_ok=True)
    for f in FILES:
        data, _ = read_remote(f)
        blob = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        (work / f).write_text(blob)
        # The base snapshot is the record of what we were told. push diffs against it
        # to separate "I edited this" from "I am holding an old copy".
        (basedir / f).write_text(blob)
        print(f"  pulled {f}")


def cmd_push(a) -> None:
    work = Path(a.work)
    basedir = work / ".base"
    for f in FILES:
        local_p = work / f
        if not local_p.exists():
            continue
        new = json.loads(local_p.read_text())
        remote, _ = read_remote(f)
        if new == remote:
            print(f"  {f} unchanged")
            continue

        base_p = basedir / f
        if not base_p.exists():
            # No base means no way to tell an edit from a stale field. Refuse rather
            # than fall back to a wholesale write — that fallback is the original bug.
            raise SystemExit(
                f"ABORT: no base snapshot for {f} at {base_p}.\n"
                f"       push cannot tell which fields you actually changed, and "
                f"writing the whole file would clobber concurrent edits.\n"
                f"       Run `state_sync.py pull` first.")
        base = json.loads(base_p.read_text())

        touched = sorted(k for k in set(base) | set(new)
                         if base.get(k) != new.get(k))

        def apply(d, b=base, n=new):
            # Merge BEFORE clearing: d is the fresh remote blob and is the third input.
            merged = three_way(b, n, dict(d))
            d.clear()
            d.update(merged)

        mutate(f, apply, a.message)
        print(f"  pushed {f} (fields changed: {', '.join(touched) or 'none'})")


def cmd_lease(a) -> None:
    """Lease-first guard: claim BEFORE doing work, so a crash cannot double-run."""
    settings, _ = read_remote("loop-settings.json")
    stale_h = settings.get("genesis", {}).get("stale_lease_hours", 6)
    min_days = settings.get("genesis", {}).get("min_days_between_runs", 27)
    now = datetime.now(timezone.utc)

    if a.acquire:
        state, _ = read_remote("state.json")
        cur = state.get("loops", {}).get(a.loop, {})
        last, status = cur.get("last_run"), cur.get("status")

        if status == "running" and last:
            age_h = (now - datetime.fromisoformat(last)).total_seconds() / 3600
            if age_h <= stale_h:
                print(json.dumps({"acquired": False,
                                  "reason": f"lease ACTIVE since {last} ({age_h:.1f}h old)"}))
                sys.exit(1)
            print(f"  clearing STALE lease ({age_h:.0f}h > {stale_h}h)")

        if last and status != "running":
            days = (now - datetime.fromisoformat(last)).days
            if days < min_days:
                print(json.dumps({"acquired": False,
                                  "reason": f"last run {days}d ago, min {min_days}d"}))
                sys.exit(1)

        def claim(d):
            d.setdefault("loops", {}).setdefault(a.loop, {})
            d["loops"][a.loop].update({"last_run": now.replace(microsecond=0).isoformat(),
                                       "status": "running"})
        mutate("state.json", claim, f"{a.loop}: acquire lease")
        print(json.dumps({"acquired": True, "at": now.isoformat()}))

    elif a.release:
        def rel(d):
            d.setdefault("loops", {}).setdefault(a.loop, {})["status"] = a.status
        mutate("state.json", rel, f"{a.loop}: release lease ({a.status})")
        print(json.dumps({"released": True, "status": a.status}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pull", "push", "lease"])
    ap.add_argument("--work", default="/home/kiwif/loop-engine/state-cache")
    ap.add_argument("-m", "--message", default="loop: update state")
    ap.add_argument("--loop")
    ap.add_argument("--acquire", action="store_true")
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--status", default="done",
                    choices=["idle", "running", "done", "failed", "paused"])
    a = ap.parse_args()
    {"pull": cmd_pull, "push": cmd_push, "lease": cmd_lease}[a.cmd](a)


if __name__ == "__main__":
    main()
