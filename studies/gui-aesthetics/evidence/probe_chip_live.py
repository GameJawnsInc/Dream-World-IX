"""SPEND -- drive the REAL chip in the REAL Workspace and read the pixels it actually paints.

WHY, WHEN THE SUITE IS GREEN AND THE MATH IS PROVEN. Because this round's own subject is the gap between
"the token exists" and "the token reaches a pixel", and this arc has been on the wrong side of it twice:
round 5 shipped a NameError past 3621 green tests because nothing DROVE the live dial, and round 4 audited
the contrast of an icon tier that had never once been drawn. `derive()` returning a good hex proves
`derive()`. It does not prove the chip asks for it.

So: construct the real Workspace, call the real `_set_chip`, grab the real widget, count the real ink.

WHAT WOULD MAKE THIS PROBE A LIAR, stated up front:
  * offscreen stubs the font DB -- so this probe asserts nothing about SIZE or geometry, only colour.
    Colour is font-independent and is the one thing this harness is trustworthy about (STATE.md's
    instrument rule).
  * a widget that was never shown reports nothing and prints an empty list -- which this study nearly
    concluded from once. So `show()` + `isVisible()` are ASSERTED, not assumed.

Run:  py studies/gui-aesthetics/evidence/probe_chip_live.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from PySide6.QtWidgets import QApplication          # noqa: E402

from ff9mapkit.editor import theme                  # noqa: E402


def _lum(rgb) -> float:
    ch = [c / 255.0 for c in rgb]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b) -> float:
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setStyle("fusion")                       # the app really runs Fusion (shell.py `_apply_app_theme`)
    from ff9mapkit.workspace.shell import Workspace

    print(f"{'palette':<16} {'mode':<8} {'fill px':<9} {'ink px':<9} {'ratio':>6}  {'white?':<7} verdict")
    bad = 0
    for name in theme.THEMES:
        pal = theme.THEMES[name]                 # RAW -- exactly what main() hands Workspace
        w = Workspace(dict(pal))
        w.resize(1280, 820)
        w.show()
        app.processEvents()
        assert w.isVisible(), "the window never showed -- every number below would be a fiction"
        for mode in ("field", "battle"):
            w._set_chip(mode)
            app.processEvents()
            chip = w.crumb._chip
            assert chip.isVisible(), f"{name}/{mode}: the chip is hidden; nothing was measured"
            img = chip.grab().toImage()
            # the fill = the most common pixel; the ink = the pixel furthest from it in luminance
            counts = {}
            for y in range(img.height()):
                for x in range(img.width()):
                    c = img.pixelColor(x, y)
                    counts[(c.red(), c.green(), c.blue())] = counts.get((c.red(), c.green(), c.blue()), 0) + 1
            fill = max(counts, key=counts.get)
            ink = max(counts, key=lambda p: (contrast(p, fill), counts[p]))
            r = contrast(ink, fill)
            is_white = ink == (255, 255, 255)
            ok = r >= 4.5
            bad += not ok
            print(f"{name:<16} {mode:<8} #{fill[0]:02x}{fill[1]:02x}{fill[2]:02x}   "
                  f"#{ink[0]:02x}{ink[1]:02x}{ink[2]:02x}   {r:>6.2f}  "
                  f"{'YES' if is_white else 'no':<7} {'ok' if ok else 'FAIL'}")
        w.close()
    print(f"\n  sub-AA chips: {bad}/16")
    print("  NOTE: the ink is the extreme ANTIALIASED pixel, so the ratio is a LOWER BOUND on the")
    print("  glyph core -- an edge pixel is a blend of ink and fill. It cannot flatter the result.")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
