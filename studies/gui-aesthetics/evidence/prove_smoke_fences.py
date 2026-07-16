"""THE SMOKE -- prove the SUITE now sees every breakage that was live at master.

WHY THIS IS THE MOST IMPORTANT PROOF IN ROUND 6. The workspace smoke is the ONLY thing that drives the
live Qt shell; the other 3644 tests are pure functions and rendered strings. It was RED at master, and had
been for an entire round, while five commit messages of mine reported it green -- because NOTHING RAN IT.
Three test modules' docstrings claimed the shell was "exercised by --smoke"; only a human typing it by
hand ever did.

Four independent breakages had accumulated:
  1. `_GUIDED is True` + `_density == "comfortable"` -- read the DEVELOPER'S PREFS. On the machine where
     this was found (`"guided": false`) the smoke failed on its owner's settings, and took two more
     asserts with it: the Battle "Advanced drawer" only EXISTS in Guided, so its correct absence was
     reported as a defect.
  2. `maximumHeight() == 16` on the wrap-preview note -- QUARTO P1 re-pinned it to 18, so the filter
     matched nothing. It asserted the NUMBER while its own comment stated the LAW ("fixed-height, no
     reflow").
  3. `"Fork a real field" in _g_empty` -- a later round made the spine deliberately SILENT on EMPTY. The
     assert AND its comment both still taught the reversed design.
  4. a lone U+2192 in the summary -- UnicodeEncodeError on a default Windows console, i.e. exactly where
     the documented dev-loop command runs. Masked until the asserts above stopped failing first.

AND THE FENCE THAT DID NOT WORK, which is worth more than the ones that did. The obvious guard --
run the smoke with LOCALAPPDATA pointed at an EMPTY tmp dir -- CANNOT see #1: an empty dir means factory
defaults, `guided: True`, so the pin is redundant there and removing it stays green.

    AN ISOLATED TEST PROVES YOUR CODE WORKS IN ISOLATION. IT SAYS NOTHING ABOUT THE USER'S MACHINE.

So the real fence BUILDS the machine that broke (a hostile prefs file) rather than a clean one.

Run:  py studies/gui-aesthetics/evidence/prove_smoke_fences.py
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
KIT = ROOT / "ff9mapkit"
SHELL = KIT / "ff9mapkit" / "workspace" / "shell.py"
F = "tests/test_workspace_smoke.py"

HOSTILE = F + "::test_the_smoke_survives_a_hostile_prefs_file"
LIVE = F + "::test_the_workspace_shell_smoke_passes"
ASCII_ = F + "::test_the_smoke_summary_is_ascii_safe"

ARROW = "→"

CASES = [
    ("#1  un-pin beginner-mode (inherit the developer's prefs again)",
     "    from . import forms_qt as _fq_smoke\n    _fq_smoke.set_guided(True)\n", "", HOSTILE),
    ("#1b assert the DEFAULT density instead of a round-trip",
     "    _d0, _qss0 = win._density, win.styleSheet()",
     '    _d0, _qss0 = "comfortable", win.styleSheet()\n    assert win._density == "comfortable"',
     HOSTILE),
    ("#2  assert the note's NUMBER instead of its law",
     "    note = [lb for lb in prev_box[0].parent().findChildren(QLabel)\n"
     "            if lb.minimumHeight() == lb.maximumHeight() > 0]",
     "    note = [lb for lb in prev_box[0].parent().findChildren(QLabel) if lb.maximumHeight() == 16]",
     LIVE),
    ("#3  assert the OLD spine behaviour on EMPTY",
     '    assert (_g_empty, _a_empty) == ("", []), \\',
     '    assert "Fork a real field" in _g_empty, \\',
     LIVE),
    ("#4  put the U+2192 back in the summary",
     'f"loose-field->parent-campaign upward jump',
     'f"loose-field' + ARROW + 'parent-campaign upward jump',
     ASCII_),
]


def run(node: str) -> int:
    p = subprocess.run([sys.executable, "-m", "pytest", node, "-q", "--no-header"],
                       cwd=KIT, capture_output=True, text=True, timeout=400)
    return p.returncode


def main() -> int:
    src = SHELL.read_text(encoding="utf-8")
    ok = True
    print("Every breakage that was live at master -- does the SUITE see it now?\n")
    for label, old, new, node in CASES:
        if old not in src:
            print(f"  STALE  {label}  <- anchor not found; this probe is lying, fix it first")
            ok = False
            continue
        if run(node) != 0:
            print(f"  BASE-RED  {label}  <- proves nothing")
            ok = False
            continue
        SHELL.write_text(src.replace(old, new, 1), encoding="utf-8")
        try:
            red = run(node) != 0
            print(f"  {'CAUGHT ' if red else 'MISSED '}  {label}")
            ok &= red
        finally:
            SHELL.write_text(src, encoding="utf-8")
    print("\n" + "=" * 70)
    print("  ALL FIVE ARE NOW CAUGHT BY THE SUITE" if ok else "  SOMETHING STILL SLIPS THROUGH")
    assert "_fq_smoke.set_guided(True)" in SHELL.read_text(encoding="utf-8"), "shell.py NOT restored"
    print("  shell.py restored")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
