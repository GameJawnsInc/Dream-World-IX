"""PRESS -- prove the state fences go RED on the real defects, and CANNOT go vacuous.

WHY THE SECOND HALF MATTERS AS MUCH AS THE FIRST. The press fences' first cut took the bare `app` fixture.
`_apply_app_theme` only sets the Fusion style + the QPalette -- THE QSS IS A WIDGET STYLESHEET, set on the
Workspace itself and reaching controls by inheritance. So the fences ran against NO SHEET and measured
Fusion's own native chrome. Fusion draws its own pressed state, so all 7 press fences went GREEN while
testing nothing: they would have passed with the bug fully present.

The focus half failed loudly, and that is the only reason it surfaced.

    A FENCE THAT IS WRONG IN THE SAFE DIRECTION IS THE ONE THAT SHIPS.

So this proves both directions: the fence goes red on each ORIGINAL defect, AND an unthemed host is
rejected rather than silently measured.

Run:  py studies/gui-aesthetics/evidence/prove_press_fences.py
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
KIT = ROOT / "ff9mapkit"
STYLE = KIT / "ff9mapkit" / "workspace" / "style.py"
A11Y = KIT / "tests" / "test_workspace_a11y.py"


def run(node: str) -> tuple:
    p = subprocess.run([sys.executable, "-m", "pytest", node, "-q", "--no-header"],
                       cwd=KIT, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# (label, the shipped line, what to replace it with, the fence that must notice)
CASES = [
    ("revert #railSeg:pressed -- THE CASCADE SHADOW",
     "    QToolButton#railSeg:pressed { color: $text; background: $pressed; }\n", "",
     "tests/test_workspace_a11y.py::test_an_id_scoped_button_still_reacts_to_a_click[railSeg]"),
    ("revert #search:pressed -- the Ctrl-K pill",
     "    QPushButton#search:pressed { background: $pressed; border-color: $accent; color: $text; }\n", "",
     "tests/test_workspace_a11y.py::test_an_id_scoped_button_still_reacts_to_a_click[search]"),
    ("revert #consoleToggle:focus -- the WCAG 2.4.7 hole",
     "    QToolButton#consoleToggle:focus { border: 1px solid $focus; color: $text; }\n", "",
     "tests/test_workspace_a11y.py::test_an_id_scoped_button_shows_where_the_keyboard_is[consoleToggle]"),
]


def main() -> int:
    src = STYLE.read_text(encoding="utf-8")
    ok = True
    print("Re-introduce each ORIGINAL defect; the fence must go RED.\n")
    for label, old, new, node in CASES:
        assert old in src, f"anchor stale -- fix this probe before trusting it: {label}"
        base, _ = run(node)
        if base != 0:
            print(f"  [{label}] BASELINE ALREADY RED -- proves nothing")
            ok = False
            continue
        STYLE.write_text(src.replace(old, new, 1), encoding="utf-8")
        try:
            code, out = run(node)
            red, named = code != 0, ("pressed" in out.lower() or "focus" in out.lower())
            print(f"  [{label}]")
            print(f"      baseline green : yes")
            print(f"      goes red       : {'yes' if red else 'NO  <-- VACUOUS FENCE'}")
            print(f"      names the bug  : {'yes' if named else 'NO  <-- red for another reason'}")
            ok &= red and named
        finally:
            STYLE.write_text(src, encoding="utf-8")

    print("\n=== THE VACUITY CHECK -- the failure mode that actually happened")
    print("    Strip the sheet off the host. The fence must REFUSE, not quietly measure Fusion.")
    asrc = A11Y.read_text(encoding="utf-8")
    assert "host.setStyleSheet(qss(pal))" in asrc, "anchor stale"
    A11Y.write_text(asrc.replace("host.setStyleSheet(qss(pal))", "host.setStyleSheet('')", 1),
                    encoding="utf-8")
    try:
        code, _ = run("tests/test_workspace_a11y.py::test_an_id_scoped_button_still_reacts_to_a_click")
        caught = code != 0
        print(f"    unthemed host REJECTED: "
              f"{'yes' if caught else 'NO  <-- the fence would measure Fusion again'}")
        ok &= caught
    finally:
        A11Y.write_text(asrc, encoding="utf-8")

    print("\n" + "=" * 68)
    print("  ALL DEMONSTRATIONS BEHAVED AS CLAIMED" if ok else "  A FENCE IS NOT DOING ITS JOB")
    assert "$pressed" in STYLE.read_text(encoding="utf-8"), "style.py NOT restored"
    assert "qss(pal)" in A11Y.read_text(encoding="utf-8"), "test file NOT restored"
    print("  files restored")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
