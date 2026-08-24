#!/usr/bin/env python3
"""Derive a write-proof settings file for --dry-run from the live allowlist.

  python scripts/make_dry_settings.py            # writes /home/kiwif/loop-engine/loop-settings.dry.json
  python scripts/make_dry_settings.py --check    # exit 3 if the derived file is stale

The existing --dry-run only prepends "write nothing" to the prompt and trusts the model
to comply. That is a request, not a control. A dry run of the review loop — which holds
merge authority over six repos — needs a floor that holds even if the model ignores the
preamble, misreads it, or is steered by something it reads in a PR body.

Deny beats allow in Claude Code, so this is derived, never hand-maintained: it copies the
live settings and layers an unconditional deny list on top. Editing loop-settings.json
can widen the real run; it cannot widen the dry run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ENGINE = Path("/home/kiwif/loop-engine")
LIVE = ENGINE / "loop-settings.json"
DRY = ENGINE / "loop-settings.dry.json"

# Every path by which a loop can change the world. Bare tool names match all uses.
DENY = [
    # --- local writes ---
    "Write",
    "Edit",
    "NotebookEdit",
    # --- git writes ---
    "Bash(git push:*)",
    "Bash(git commit:*)",
    "Bash(git merge:*)",
    "Bash(git tag:*)",
    "Bash(git checkout -b:*)",
    "Bash(git switch -c:*)",
    "Bash(git branch:*)",
    "Bash(git reset:*)",
    "Bash(git rebase:*)",
    # --- GitHub writes ---
    "Bash(gh pr create:*)",
    "Bash(gh pr merge:*)",
    "Bash(gh pr close:*)",
    "Bash(gh pr edit:*)",
    "Bash(gh pr comment:*)",
    "Bash(gh pr review:*)",
    "Bash(gh pr ready:*)",
    "Bash(gh issue create:*)",
    "Bash(gh issue close:*)",
    "Bash(gh issue edit:*)",
    "Bash(gh issue comment:*)",
    "Bash(gh repo create:*)",
    "Bash(gh repo edit:*)",
    "Bash(gh workflow run:*)",
    "Bash(gh workflow enable:*)",
    "Bash(gh workflow disable:*)",
    "Bash(gh release:*)",
    "Bash(gh label:*)",
    # gh api defaults to GET; every mutating verb is spelled out.
    "Bash(gh api -X POST:*)",
    "Bash(gh api -X PUT:*)",
    "Bash(gh api -X PATCH:*)",
    "Bash(gh api -X DELETE:*)",
    "Bash(gh api --method POST:*)",
    "Bash(gh api --method PUT:*)",
    "Bash(gh api --method PATCH:*)",
    "Bash(gh api --method DELETE:*)",
    # --- state writes ---
    # state_sync.py push/lease mutate the coordination repo; pull is read-only but the
    # rule cannot see the subcommand, so the whole script is denied for a dry run.
    "Bash(/home/kiwif/loop-engine/.venv/bin/python:*state_sync.py*)",
    # --- shell escapes around the above ---
    "Bash(tee:*)",
    "Bash(dd:*)",
    "Bash(truncate:*)",
    "Bash(install:*)",
]


def build() -> dict:
    cfg = json.loads(LIVE.read_text())
    perms = cfg.setdefault("permissions", {})
    merged = list(dict.fromkeys(list(perms.get("deny", [])) + DENY))
    perms["deny"] = merged
    cfg["_generated"] = (
        "DERIVED FILE — do not edit. Regenerate with scripts/make_dry_settings.py. "
        "loop-settings.json plus an unconditional deny list, so --dry-run cannot write "
        "even if the model ignores the dry-run preamble."
    )
    return cfg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 3 if the derived file is missing or stale")
    a = ap.parse_args()

    want = build()
    if a.check:
        if not DRY.exists():
            print(f"{DRY} missing — run without --check", file=sys.stderr)
            sys.exit(3)
        if json.loads(DRY.read_text()) != want:
            print(f"{DRY} is stale (loop-settings.json changed since it was derived)",
                  file=sys.stderr)
            sys.exit(3)
        print(f"{DRY.name} current — {len(want['permissions']['deny'])} deny rules")
        sys.exit(0)

    DRY.write_text(json.dumps(want, indent=2) + "\n")
    print(f"wrote {DRY}")
    print(f"  allow: {len(want['permissions'].get('allow', []))}  "
          f"deny: {len(want['permissions']['deny'])} "
          f"(+{len(DENY)} dry-run rules)")


if __name__ == "__main__":
    main()
