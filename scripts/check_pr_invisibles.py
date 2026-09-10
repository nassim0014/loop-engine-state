#!/usr/bin/env python3
"""Reject invisible/deceptive characters in a PR's body, title, and commits.

  python scripts/check_pr_invisibles.py --repo nassim0014/btc-llm-sentiment --pr 45
  python scripts/check_pr_invisibles.py --stdin < message.txt
  echo "text" | python scripts/check_pr_invisibles.py --stdin

  exit 0 = clean   exit 1 = invisible characters found   exit 2 = tool error

Why this exists (and why it's not the same as validate.yml's check):
`validate.yml` greps this repo's committed *source files* for two zero-width
codepoints. But the real incident (btc-llm-sentiment PR #45, 2026-08-29) was an
invisible marker in a **PR body** — text that never lands in a file, so no
file-scanning CI can see it. A PR body is where a loop or a second agent can
smuggle a coordination marker past review; a human reviewer can't see a
zero-width character, and editors/formatters silently strip them, so the marker
scheme fails invisibly. The review-loop runs this against each candidate PR
before merging.

Markers must be BUILT in code from named constants, never pasted as literals —
so any literal invisible character in author-supplied text is, by policy, a
defect regardless of intent.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unicodedata

# Codepoints that are invisible, zero-width, or alter text direction — none of
# which belong in a hand-written PR body / title / commit message. Ordinary
# whitespace (space, tab, newline, carriage return) is deliberately NOT here.
_DISALLOWED: dict[int, str] = {
    0x00AD: "SOFT HYPHEN",
    0x061C: "ARABIC LETTER MARK",
    0x115F: "HANGUL CHOSEONG FILLER",
    0x1160: "HANGUL JUNGSEONG FILLER",
    0x180E: "MONGOLIAN VOWEL SEPARATOR",
    0x200B: "ZERO WIDTH SPACE",
    0x200C: "ZERO WIDTH NON-JOINER",
    0x200D: "ZERO WIDTH JOINER",
    0x200E: "LEFT-TO-RIGHT MARK",
    0x200F: "RIGHT-TO-LEFT MARK",
    0x2028: "LINE SEPARATOR",
    0x2029: "PARAGRAPH SEPARATOR",
    0x202A: "LEFT-TO-RIGHT EMBEDDING",
    0x202B: "RIGHT-TO-LEFT EMBEDDING",
    0x202C: "POP DIRECTIONAL FORMATTING",
    0x202D: "LEFT-TO-RIGHT OVERRIDE",
    0x202E: "RIGHT-TO-LEFT OVERRIDE",
    0x2060: "WORD JOINER",
    0x2061: "FUNCTION APPLICATION",
    0x2062: "INVISIBLE TIMES",
    0x2063: "INVISIBLE SEPARATOR",
    0x2064: "INVISIBLE PLUS",
    0x2066: "LEFT-TO-RIGHT ISOLATE",
    0x2067: "RIGHT-TO-LEFT ISOLATE",
    0x2068: "FIRST STRONG ISOLATE",
    0x2069: "POP DIRECTIONAL ISOLATE",
    0x3164: "HANGUL FILLER",
    0xFEFF: "ZERO WIDTH NO-BREAK SPACE (BOM)",
    0xFFA0: "HALFWIDTH HANGUL FILLER",
}


def _is_disallowed(cp: int) -> bool:
    # Named set above, plus the Unicode Tag block (U+E0000–U+E007F), which can
    # smuggle ASCII invisibly, and any other format/unassigned control we didn't
    # name individually.
    if cp in _DISALLOWED:
        return True
    if 0xE0000 <= cp <= 0xE007F:
        return True
    return False


def _name(cp: int) -> str:
    if cp in _DISALLOWED:
        return _DISALLOWED[cp]
    if 0xE0000 <= cp <= 0xE007F:
        return "UNICODE TAG CHARACTER"
    try:
        return unicodedata.name(chr(cp))
    except ValueError:
        return "UNNAMED"


def scan_text(text: str, *, label: str = "") -> list[dict]:
    """Return one finding dict per disallowed character in ``text``.

    Pure and dependency-free so it is trivially unit-testable. Each finding:
    ``{label, line, col, offset, codepoint ('U+200B'), name}``.
    """
    findings: list[dict] = []
    line = 1
    col = 1
    for offset, ch in enumerate(text):
        cp = ord(ch)
        if _is_disallowed(cp):
            findings.append({
                "label": label,
                "line": line,
                "col": col,
                "offset": offset,
                "codepoint": f"U+{cp:04X}",
                "name": _name(cp),
            })
        # Advance line/col using only *real* newlines (LF); the exotic line
        # separators are themselves flagged above, not treated as newlines.
        if ch == "\n":
            line += 1
            col = 1
        else:
            col += 1
    return findings


def _fetch_pr_parts(repo: str, pr: str) -> dict[str, str]:
    """Fetch title, body, and commit messages for a PR via the gh CLI."""
    result = subprocess.run(
        ["gh", "pr", "view", pr, "--repo", repo, "--json", "title,body,commits"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh pr view failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    parts = {"title": data.get("title") or "", "body": data.get("body") or ""}
    for i, commit in enumerate(data.get("commits") or []):
        parts[f"commit[{i}]"] = commit.get("messageHeadline", "") + "\n" + commit.get(
            "messageBody", ""
        )
    return parts


def _report(findings: list[dict]) -> None:
    for f in findings:
        loc = f"{f['label']} {f['line']}:{f['col']}" if f["label"] else f"{f['line']}:{f['col']}"
        print(f"  {f['codepoint']} {f['name']}  at {loc} (offset {f['offset']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", help="owner/name; required with --pr")
    parser.add_argument("--pr", help="PR number to scan (title + body + commit messages)")
    parser.add_argument("--stdin", action="store_true", help="scan text from stdin instead")
    args = parser.parse_args(argv)

    try:
        if args.stdin:
            parts = {"stdin": sys.stdin.read()}
        elif args.pr:
            if not args.repo:
                print("error: --pr requires --repo", file=sys.stderr)
                return 2
            parts = _fetch_pr_parts(args.repo, args.pr)
        else:
            print("error: pass --pr (with --repo) or --stdin", file=sys.stderr)
            return 2
    except Exception as exc:  # gh failure, bad JSON, etc.
        print(f"error: {exc}", file=sys.stderr)
        return 2

    all_findings: list[dict] = []
    for label, text in parts.items():
        all_findings.extend(scan_text(text, label=label))

    if all_findings:
        where = f"{args.repo}#{args.pr}" if args.pr else "input"
        print(f"::error::{len(all_findings)} invisible character(s) in {where} — reject this PR")
        _report(all_findings)
        return 1

    print("clean — no invisible characters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
