"""SPEND -- every FILLED ground that carries text, and the ink actually painted on it.

WHAT THIS MEASURES, AND WHY IT NEEDS NO RENDER. A filled chip is two hexes: the fill and the ink. Both
come from the palette dict, so the contrast is computable from `theme.THEMES` alone -- no Qt, no font DB,
no screenshot. STATE.md's instrument rule: *"A finding derivable from the palette needs no render at all
-- prefer that."* This is that case, so this probe is pure arithmetic and cannot be lied to by the
offscreen platform (which has burned this study three times).

THE CENSUS IS THE HARD PART, NOT THE MATH. A filled ground is only a defect if text lands ON it, and
`grep '#ffffff'` finds one line while the real question is "which grounds carry ink". The sites below were
found by grepping `background:{` in inline `setStyleSheet` f-strings across `workspace/` and reading each
hit -- NOT by trusting any docstring's account of itself.

    shell.py:361      chip        fill = accent | warn        ink = '#ffffff'   HARDCODED
    forms_qt.py:603   help button fill = help                 ink = accent_fg   WRONG PARTNER

`accent_fg` is fenced at 4.5 against `accent` ONLY (test_editor_theme.py:135). Riding it on `help` is
unfenced by construction: nothing ever asserted those two hexes were compatible.

Run:  py studies/gui-aesthetics/evidence/probe_filled_ground_ink.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from ff9mapkit.editor import theme  # noqa: E402


def _lum(hexstr: str) -> float:
    """WCAG 2.x relative luminance. Written out rather than imported: this study's rule is not to trust a
    library it cannot check, and `theme._contrast` is the very module under test -- a probe that grades a
    module with that module's own arithmetic proves only self-consistency."""
    h = hexstr.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


AA = 4.5        # the chip is 12px 600-weight -- NORMAL text. 600 weight does not buy the large-text bar
                # (that needs 18.66px bold), so 4.5 is the correct floor. Growing text never loosens it.

# (label, fill-key, the ink ACTUALLY painted today, why)
SITES = [
    ("chip ACCENT  (7 of 8 modes)", "accent", lambda p: "#ffffff", "shell.py:361 hardcoded"),
    ("chip BATTLE  (warn ground)", "warn", lambda p: "#ffffff", "shell.py:361 hardcoded"),
    ("help button", "help", lambda p: p["accent_fg"], "forms_qt.py:603 wrong partner"),
]


def main() -> int:
    worst = {}
    for label, fill_key, ink_of, note in SITES:
        print(f"\n=== {label:<28} fill=${fill_key:<7} {note}")
        print(f"    {'palette':<16} {'fill':<9} {'ink':<9} {'ratio':>6}  {'verdict':<6}")
        fails = 0
        for name in theme.THEMES:
            pal = theme.derive(dict(theme.THEMES[name]))
            fill, ink = pal[fill_key], ink_of(pal)
            r = contrast(ink, fill)
            ok = r >= AA
            fails += (not ok)
            print(f"    {name:<16} {fill:<9} {ink:<9} {r:>6.2f}  {'ok' if ok else 'FAIL':<6}")
        worst[label] = fails
        print(f"    -> {fails}/8 FAIL AA {AA}")

    print("\n" + "=" * 62)
    for k, v in worst.items():
        print(f"  {v}/8 fail  {k}")

    # --- what the authored token would give, where one exists -----------------------------------------
    print("\n=== the ink the palette ALREADY authored for the accent ground (accent_fg)")
    print(f"    {'palette':<16} {'white':>7} {'accent_fg':>10}  {'delta':>7}")
    for name in theme.THEMES:
        pal = theme.derive(dict(theme.THEMES[name]))
        w = contrast("#ffffff", pal["accent"])
        a = contrast(pal["accent_fg"], pal["accent"])
        print(f"    {name:<16} {w:>7.2f} {a:>10.2f}  {a - w:>+7.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
