#!/usr/bin/env python3
"""Validate loop-engine config: JSON Schemas + cross-file invariants.

Usage:
  python scripts/validate_config.py                    # offline checks
  python scripts/validate_config.py --online           # + gh reachability/CI checks
  python scripts/validate_config.py --runs             # also validate runs/*.json
  python scripts/validate_config.py --json             # machine-readable output

Exit codes: 0 valid - 1 invalid - 2 environment error
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    sys.exit("Missing dependency: pip install jsonschema")

SCHEMA_FOR = {
    "registry.json": "registry.schema.json",
    "state.json": "state.schema.json",
    "schedule.json": "schedule.schema.json",
    "loop-settings.json": "settings.schema.json",
}
RUN_SCHEMA = "run-record.schema.json"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None: self.errors.append(msg)
    def warn(self, msg: str) -> None: self.warnings.append(msg)

    @property
    def ok(self) -> bool: return not self.errors


def load(path: Path, rep: Report):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        rep.error(f"missing file: {path}")
    except json.JSONDecodeError as e:
        rep.error(f"{path.name}: invalid JSON ({e})")
    return None


def schema_check(label: str, data, schema_file: str, sdir: Path, rep: Report) -> None:
    spath = sdir / schema_file
    if not spath.exists():
        rep.error(f"missing schema: {spath}")
        return
    schema = json.loads(spath.read_text(encoding="utf-8"))
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    for e in sorted(v.iter_errors(data), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "<root>"
        rep.error(f"{label}: {loc}: {e.message}")


def parse_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def cross_checks(cfg: dict, rep: Report, root: Path) -> None:
    reg, state = cfg["registry.json"], cfg["state.json"]
    sched, settings = cfg["schedule.json"], cfg["loop-settings.json"]

    # schedule <-> state consistency
    loops = sched.get("loops", [])
    names = [l["name"] for l in loops]
    if len(names) != len(set(names)):
        rep.error("schedule.json: duplicate loop names")
    for l in loops:
        if l.get("enabled") and l["name"] not in state.get("loops", {}):
            rep.warn(f"state.json: no entry for enabled loop '{l['name']}'")
        if l.get("enabled") and l.get("paused_until"):
            try:
                if parse_dt(l["paused_until"]) < datetime.now(timezone.utc):
                    rep.warn(f"schedule.json: '{l['name']}' paused_until is in the past")
            except (TypeError, ValueError):
                rep.error(f"schedule.json: bad paused_until for '{l['name']}'")

    # rotation consistency
    order = reg.get("rotation", {}).get("order", [])
    by_name = {r["name"]: r for r in reg.get("repos", [])}
    for n in order:
        r = by_name.get(n)
        if r is None:
            rep.error(f"registry.json: rotation.order names '{n}' but no such repo entry")
        elif not r.get("in_rotation"):
            rep.error(f"registry.json: '{n}' in rotation.order but in_rotation=false")
    rot_repos = sorted(r["name"] for r in reg.get("repos", []) if r.get("in_rotation"))
    if rot_repos != sorted(order):
        rep.warn("registry.json: in_rotation repos don't exactly match rotation.order")

    # cursor bounds
    cursor = state.get("rotation_cursor")
    if cursor is not None and order and not (0 <= cursor < len(order)):
        rep.error(f"state.json: rotation_cursor={cursor} out of bounds (0..{len(order) - 1})")

    # one worker per rotation repo, so two agents never start work in the same repo
    for n in order:
        r = by_name.get(n)
        if r is not None and r.get("worked_by") not in ("claude", "zai"):
            rep.error(f"registry.json: rotation repo '{n}' needs worked_by claude or zai")
    zai_on = any(l.get("agent") == "zai" and l.get("enabled") for l in loops)
    for r in reg.get("repos", []):
        if r.get("worked_by") == "zai" and not zai_on:
            rep.warn(f"registry.json: '{r['name']}' is worked_by zai but no zai loop is enabled")

    # cloud jobs: the prompt they bootstrap from must exist in this repo
    for l in loops:
        if l.get("prompt") and not (root / l["prompt"]).is_file():
            rep.error(f"schedule.json: '{l['name']}' prompt {l['prompt']} does not exist")
        if l.get("agent") == "claude-cloud" and l.get("enabled") and not l.get("trigger_id"):
            rep.warn(f"schedule.json: '{l['name']}' has no trigger_id yet (routine not created)")

    # genesis lease (the double-run guard)
    g = state.get("loops", {}).get("repo-genesis-loop")
    if g and g.get("status") == "running":
        stale_h = settings.get("genesis", {}).get("stale_lease_hours", 6)
        try:
            age = (datetime.now(timezone.utc) - parse_dt(g["last_run"])).total_seconds() / 3600
            if age > stale_h:
                rep.error(f"genesis lease STALE ({age:.0f}h > {stale_h}h) - clear before genesis runs")
            else:
                rep.warn(f"genesis lease ACTIVE since {g['last_run']}")
        except (TypeError, ValueError):
            rep.error("genesis lease: unreadable last_run")


def gh(*args: str):
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def online_checks(cfg: dict, rep: Report) -> None:
    if gh("auth", "status").returncode != 0:
        rep.error("online: gh not authenticated")
        return
    for r in cfg["registry.json"].get("repos", []):
        full = f"{r['owner']}/{r['name']}"
        if gh("repo", "view", full).returncode != 0:
            rep.error(f"online: cannot view {full}")
            continue
        if r.get("in_rotation"):
            w = gh("api", f"repos/{full}/contents/.github/workflows")
            ok = w.returncode == 0 and json.loads(w.stdout or "[]")
            if not ok:
                rep.error(f"online: {full} has no CI workflows (rotation repos must have CI)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="dir containing the 4 config files")
    ap.add_argument("--schemas", default=None,
                    help="schemas dir (default: the schemas/ shipped next to this script, "
                         "falling back to <dir>/schemas)")
    ap.add_argument("--runs", action="store_true", help="also validate runs/*.json")
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = Path(args.dir).resolve()

    # Schemas ship WITH this script, so resolve them from the script's location, not from
    # wherever the config being validated happens to live. The old default was
    # <dir>/schemas, which worked only when run from inside state-repo: the 2026-08-24
    # backlog-refresh dry run pointed --dir at /home/kiwif/loop-engine (the config cache)
    # and got 4 "missing schema" errors. Since the runbook says abort the session when
    # validate_config fails, that mismatch would have blocked every run of that loop.
    # <dir>/schemas is kept as a fallback so a self-contained config dir still validates.
    if args.schemas:
        sdir = Path(args.schemas).resolve()
    else:
        shipped = Path(__file__).resolve().parent.parent / "schemas"
        sdir = shipped if shipped.is_dir() else d / "schemas"

    rep = Report()
    cfg: dict = {}
    for f, s in SCHEMA_FOR.items():
        data = load(d / f, rep)
        if data is not None:
            cfg[f] = data
            schema_check(f, data, s, sdir, rep)

    if args.runs:
        for rf in sorted((d / "runs").glob("*.json")):
            data = load(rf, rep)
            if data is not None:
                schema_check(rf.name, data, RUN_SCHEMA, sdir, rep)

    if len(cfg) == len(SCHEMA_FOR):
        cross_checks(cfg, rep, d)
        if args.online:
            online_checks(cfg, rep)

    out = {"ok": rep.ok, "errors": rep.errors, "warnings": rep.warnings,
           "checked_at": datetime.now(timezone.utc).isoformat()}
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        for w in rep.warnings: print(f"WARN  {w}")
        for e in rep.errors:   print(f"FAIL  {e}")
        print(f"\n{'VALID' if rep.ok else 'INVALID'} - "
              f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    sys.exit(0 if rep.ok else 1)


if __name__ == "__main__":
    main()
