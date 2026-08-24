#!/usr/bin/env python3
"""KCI -> kpb schema drift check.

  python scripts/schema_drift.py --export <path-to-kci-checkout>   # write contracts/kci_schema.json
  python scripts/schema_drift.py --diff   <path-to-kpb-checkout>   # compare against kpb's fixture
  exit 0 = no drift - 3 = drift found - 2 = could not inspect

kinz-price-bridge consumes kinz-competitor-intelligence's schema. Nothing in either
repo's CI notices when KCI's tables change — kpb keeps parsing happily against a fixture
that no longer matches reality, and the failure surfaces much later as wrong data rather
than a broken build. This makes the contract explicit and diffable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CONTRACT = Path(__file__).resolve().parent.parent / "contracts" / "kci_schema.json"


def export(kci_root: Path) -> int:
    """Import KCI's SQLAlchemy metadata and dump table -> column types."""
    sys.path.insert(0, str(kci_root))
    try:
        from src.database import Base            # noqa: E402
    except Exception as e:                        # noqa: BLE001
        print(f"cannot import src.database from {kci_root}: {e}", file=sys.stderr)
        return 2

    schema = {
        t.name: {c.name: str(c.type) for c in sorted(t.columns, key=lambda c: c.name)}
        for t in sorted(Base.metadata.tables.values(), key=lambda t: t.name)
    }
    CONTRACT.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT.write_text(json.dumps(
        {"_comment": "Exported from kinz-competitor-intelligence SQLAlchemy metadata. "
                     "kinz-price-bridge parses against this shape; a diff here means kpb "
                     "may silently mis-parse.",
         "source": "kinz-competitor-intelligence/src/database.py",
         "tables": schema}, indent=2) + "\n")
    print(f"wrote {CONTRACT} ({len(schema)} tables)")
    return 0


def diff(kpb_root: Path) -> int:
    if not CONTRACT.exists():
        print("no contract yet — run --export first", file=sys.stderr)
        return 2
    live = json.loads(CONTRACT.read_text())["tables"]

    fixtures = list(kpb_root.rglob("kci_schema*.json")) + \
               list(kpb_root.rglob("fixtures/*schema*.json"))
    if not fixtures:
        print(json.dumps({"drift": None,
                          "note": "kpb has no committed schema fixture yet — nothing to "
                                  "compare. That is itself a backlog item."}, indent=2))
        return 0

    fixture = json.loads(fixtures[0].read_text())
    pinned = fixture.get("tables", fixture)

    added = sorted(set(live) - set(pinned))
    removed = sorted(set(pinned) - set(live))
    changed = {}
    for t in sorted(set(live) & set(pinned)):
        cols_new = sorted(set(live[t]) - set(pinned[t]))
        cols_gone = sorted(set(pinned[t]) - set(live[t]))
        retyped = {c: [pinned[t][c], live[t][c]]
                   for c in set(live[t]) & set(pinned[t]) if live[t][c] != pinned[t][c]}
        if cols_new or cols_gone or retyped:
            changed[t] = {"added": cols_new, "removed": cols_gone, "retyped": retyped}

    drift = bool(added or removed or changed)
    print(json.dumps({"fixture": str(fixtures[0]), "drift": drift,
                      "tables_added": added, "tables_removed": removed,
                      "columns_changed": changed}, indent=2))
    return 3 if drift else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", metavar="KCI_ROOT")
    ap.add_argument("--diff", metavar="KPB_ROOT")
    a = ap.parse_args()
    if a.export:
        sys.exit(export(Path(a.export).resolve()))
    if a.diff:
        sys.exit(diff(Path(a.diff).resolve()))
    ap.error("need --export or --diff")


if __name__ == "__main__":
    main()
