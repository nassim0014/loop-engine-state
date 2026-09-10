#!/usr/bin/env python3
"""Tests for check_pr_invisibles.scan_text — the PR-body invisible-char guard.

  python scripts/test_check_pr_invisibles.py

No pytest dependency, by the same rule as test_three_way.py: CI and the
run-loop preflight must be able to prove this guard works without installing a
test framework.

Every invisible character used as a fixture is BUILT with ``chr(0x…)``, never
pasted as a literal — otherwise this very file would trip validate.yml's
"no literal zero-width characters in source" gate. That the guard's own tests
must follow the guard's own rule is the point.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_pr_invisibles import main, scan_text  # noqa: E402

FAILURES: list[str] = []

ZWSP = chr(0x200B)
ZWNJ = chr(0x200C)
ZWJ = chr(0x200D)
WORD_JOINER = chr(0x2060)
BOM = chr(0xFEFF)
RTL_OVERRIDE = chr(0x202E)
POP_ISOLATE = chr(0x2069)
TAG_A = chr(0xE0041)  # UNICODE TAG "A"


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok    {name}")
    else:
        FAILURES.append(name)
        print(f"  FAIL  {name}\n        got  {got!r}\n        want {want!r}")


# --- scan_text ---------------------------------------------------------------

def test_clean_text_has_no_findings() -> None:
    text = "Normal PR body.\n\nTabs\tand punctuation — em dash, é, 中文, 🎉."
    check("clean text passes", scan_text(text), [])


def test_ordinary_whitespace_is_allowed() -> None:
    # Space, tab, newline, CR must never be flagged.
    check("whitespace allowed", scan_text(" \t\n\r"), [])


def test_detects_zero_width_space() -> None:
    findings = scan_text("hi" + ZWSP + "there")
    check("one ZWSP found", len(findings), 1)
    check("ZWSP codepoint", findings[0]["codepoint"], "U+200B")
    check("ZWSP offset", findings[0]["offset"], 2)


def test_detects_word_joiner_and_bom() -> None:
    # The two codepoints from the real btc PR #45 incident, plus a BOM.
    findings = scan_text("a" + WORD_JOINER + "b" + BOM + "c")
    cps = sorted(f["codepoint"] for f in findings)
    check("word joiner + BOM found", cps, ["U+2060", "U+FEFF"])


def test_detects_rtl_override_and_isolate() -> None:
    findings = scan_text("safe" + RTL_OVERRIDE + "gnirts" + POP_ISOLATE)
    cps = sorted(f["codepoint"] for f in findings)
    check("bidi controls found", cps, ["U+202E", "U+2069"])


def test_detects_unicode_tag_smuggling() -> None:
    findings = scan_text("x" + TAG_A + "y")
    check("tag char found", len(findings), 1)
    check("tag char named", findings[0]["name"], "UNICODE TAG CHARACTER")


def test_line_and_column_tracking() -> None:
    findings = scan_text("line1\nli" + ZWSP + "ne2")
    check("finding on line 2", findings[0]["line"], 2)
    check("finding at col 3", findings[0]["col"], 3)


def test_multiple_findings_reported_in_order() -> None:
    findings = scan_text(ZWSP + "_" + ZWNJ + "_" + ZWJ)
    check("three findings in order", [f["codepoint"] for f in findings],
          ["U+200B", "U+200C", "U+200D"])


# --- CLI via --stdin (exit codes) --------------------------------------------

def _run_stdin(text: str) -> int:
    proc = subprocess.run(
        [sys.executable,
         str(Path(__file__).resolve().parent / "check_pr_invisibles.py"), "--stdin"],
        input=text, capture_output=True, text=True,
    )
    return proc.returncode


def test_cli_exit_0_on_clean() -> None:
    check("clean -> exit 0", _run_stdin("all good\n"), 0)


def test_cli_exit_1_on_invisible() -> None:
    check("dirty -> exit 1", _run_stdin("bad" + ZWSP + "marker\n"), 1)


def main_tests() -> None:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    # Smoke: the module's own main() returns 2 with no args (usage error).
    check("no-args -> exit 2", main([]), 2)

    if FAILURES:
        print(f"\n{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
        sys.exit(1)
    print("\nall passed")


if __name__ == "__main__":
    main_tests()
