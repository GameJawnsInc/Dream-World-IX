"""SPEND -- prove each new fence GOES RED on the exact bug it claims to catch.

WHY THIS EXISTS AS A SCRIPT AND NOT A BELIEF. This round's whole subject is mechanisms that were built,
documented, fenced -- and never actually spent. A fence that passes is indistinguishable from a fence that
cannot fail; the suite reports green either way. Round 5 shipped a NameError past 3621 green tests because
nothing drove the live dial, and round 4 shipped a colour tier that had never once been drawn. So: re-break
each defect, watch the fence go red WITH THE RIGHT MESSAGE, restore, watch it pass.

    A FENCE YOU HAVE NOT SEEN FAIL IS A FENCE YOU HAVE NOT WRITTEN.

Run:  py studies/gui-aesthetics/evidence/prove_spend_fences.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KIT = ROOT / "ff9mapkit"


def run(nodeid: str) -> tuple:
    p = subprocess.run([sys.executable, "-m", "pytest", nodeid, "-q", "--no-header", "-x"],
                       cwd=KIT, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def bite(label: str, path: Path, old: str, new: str, nodeid: str, expect: str) -> bool:
    """Break one thing, demand the named fence goes red and SAYS the right thing, then restore."""
    src = path.read_text(encoding="utf-8")
    assert old in src, f"{label}: anchor not found -- this probe is stale, fix it before trusting it"
    ok0, out0 = run(nodeid)
    if ok0 != 0:
        print(f"  [{label}] BASELINE ALREADY RED -- aborting, the probe would prove nothing")
        return False
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    try:
        code, out = run(nodeid)
        red = code != 0
        said = expect.lower() in out.lower()
        print(f"  [{label}]")
        print(f"      baseline green : yes")
        print(f"      goes red       : {'yes' if red else 'NO  <-- THE FENCE CANNOT SEE THIS BUG'}")
        print(f"      names the bug  : {'yes' if said else 'NO  <-- red for the wrong reason'}"
              f"   (looked for {expect!r})")
        if red and not said:
            print("      ---- what it actually said ----")
            for ln in out.splitlines():
                if ln.strip().startswith("E "):
                    print("      " + ln.strip()[:150])
        return red and said
    finally:
        path.write_text(src, encoding="utf-8")


def main() -> int:
    shell = KIT / "ff9mapkit" / "workspace" / "shell.py"
    theme = KIT / "ff9mapkit" / "editor" / "theme.py"
    widgets = KIT / "ff9mapkit" / "workspace" / "widgets.py"
    results = []

    print("\n=== 1. the ORIGINAL defect: the chip hardcodes white")
    results.append(bite(
        "chip #ffffff", shell,
        'f"background:{fill};color:{ink};border-radius:3px;padding:1px 7px;font-weight:600;")',
        'f"background:{fill};color:#ffffff;border-radius:3px;padding:1px 7px;font-weight:600;")',
        "../ff9mapkit/tests/test_workspace_style.py::test_no_widget_paints_a_colour_the_palette_never_chose",
        "#ffffff"))

    print("\n=== 2. a sub-AA ink on a fill (warn_fg -> the raw warn hue)")
    results.append(bite(
        "warn_fg sub-AA", theme,
        'out[f"{_k}_fg"] = _fg_token(pal[_k], pal)',
        'out[f"{_k}_fg"] = pal["text"]',
        "../ff9mapkit/tests/test_editor_theme.py::test_a_filled_ground_carries_its_ink",
        "sub-AA"))

    print("\n=== 3. the BORROWED ink (help wearing accent_fg -- the real shipped bug)")
    results.append(bite(
        "borrowed ink", theme,
        'for _k in ("warn", "help"):\n        out[f"{_k}_fg"] = _fg_token(pal[_k], pal)',
        'for _k in ("warn", "help"):\n        out[f"{_k}_fg"] = _fg_token(pal[_k], pal)\n'
        '    out["help_fg"] = pal["accent_fg"]',
        "../ff9mapkit/tests/test_editor_theme.py::test_a_filled_ground_carries_its_ink",
        "sub-AA"))

    print("\n=== 4. a palette-blind default creeping back in")
    results.append(bite(
        "blind default", widgets,
        "def __init__(self, placeholder, color, parent=None):",
        'def __init__(self, placeholder, color="#808080", parent=None):',
        "../ff9mapkit/tests/test_workspace_style.py::test_no_widget_paints_a_colour_the_palette_never_chose",
        "#808080"))

    print("\n=== 5. THE CONTROL -- a hex inside a CSS COMMENT must NOT trip it")
    style = KIT / "ff9mapkit" / "workspace" / "style.py"
    src = style.read_text(encoding="utf-8")
    anchor = "* { outline: 0; }"
    assert anchor in src, "control anchor stale"
    style.write_text(src.replace(anchor, "/* a note about #4c8dff */\n    " + anchor, 1), encoding="utf-8")
    try:
        code, _ = run("../ff9mapkit/tests/test_workspace_style.py::"
                      "test_no_widget_paints_a_colour_the_palette_never_chose")
        ok = code == 0
        print(f"  [css-comment control] stays green: "
              f"{'yes' if ok else 'NO  <-- it is flagging PROSE, not code'}")
        results.append(ok)
    finally:
        style.write_text(src, encoding="utf-8")

    print("\n" + "=" * 74)
    print(f"  {sum(results)}/{len(results)} demonstrations behaved as claimed")
    if not all(results):
        print("  ^ a fence that cannot fail is not protecting anything. Fix it before shipping.")
    # restored?
    for p in (shell, theme, widgets, style):
        assert "<<<<<<<" not in p.read_text(encoding="utf-8"), f"{p.name} not restored cleanly"
    print("  all files restored")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
