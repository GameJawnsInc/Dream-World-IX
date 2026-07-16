"""BREATHE -- does the space around the text grow with the text? And what does growing it cost?

THE DEFECT, as round 6's survey measured it: `qss()` merges {**_SCALES, **grid, **typ, **dens, ...} and
only `typ` is passed through `type_px(k, scale)`. `grid` and `dens` never see the scale. So at 200% a
card's TEXT grows 95% and its WHITESPACE grows 1px -- the card goes from 58% whitespace to 42%, and a
button's padding-to-text ratio halves. `prefs.text_scale()` seeds from the Windows slider, so users land
at 125/150% without ever opening Preferences: the dial degrades exactly the people it exists to help.

MUST RUN NATIVE. Every number here is text-derived, and offscreen's stub font DB renders ~14px/char --
this study's 4th offscreen burn INVENTED a whole defect out of exactly that. Asserted below.

THE TOOLBAR IS THE TRAP, AND IT IS MEASURED, NOT REASONED. style.py's budget comment is load-bearing:
    "The 14px body costs exactly one button at 1280 (15/15 -> 14/15) and this rung buys it back... If a
     future round grows the body again: 15px loses two items and tightening does NOT recover them --
     the budget is spent."
So this probe counts VISIBLE toolbar actions at each scale, with the toolbar metrics scaled and exempt,
and lets the count decide rather than the argument.

Run:  py studies/gui-aesthetics/evidence/probe_breathe.py      (NO offscreen)
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="ff9probe_")
os.environ.pop("QT_QPA_PLATFORM", None)
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from PySide6.QtGui import QFont, QFontInfo                                   # noqa: E402
from PySide6.QtWidgets import (QApplication, QLabel, QLineEdit, QToolButton,  # noqa: E402
                               QVBoxLayout, QWidget)

from ff9mapkit import prefs                                                  # noqa: E402
from ff9mapkit.editor.theme import pick_palette                              # noqa: E402
from ff9mapkit.workspace import style, widgets                               # noqa: E402

# THE DIAL'S REAL RANGE, read from the dial -- not a range I picked. My first cut ran 100..200 and the
# toolbar count came back NON-MONOTONIC: 15/14/13/11 and then 15/15 again at 200%. The tell was right.
# `_apply_text_scale` is `pct if pct in prefs.TEXT_SCALES else 100`, so 200 silently FELL BACK TO 100 and
# that row was measuring the baseline while claiming to measure the extreme.
#   A PROBE THAT INVENTS ITS OWN INPUT RANGE IS MEASURING A PRODUCT THAT DOES NOT EXIST.
SCALES = prefs.TEXT_SCALES


def card_metrics(app, pal, scale):
    """A real widgets.section() card: how much of it is ink, and how much is air?"""
    host = QWidget()
    host.setStyleSheet(style.qss(pal, "comfortable", scale))
    lay = QVBoxLayout(host)
    box = widgets.section("Build to (field)")     # returns the CARD; its rows go in .content_layout
    for _ in range(3):
        box.content_layout.addWidget(QLineEdit())
    lay.addWidget(box)
    host.resize(420, 600)
    host.show()
    app.processEvents()
    assert host.isVisible(), "never shown"
    h = box.sizeHint().height()
    # ink = the text rows' own line boxes; air = everything else in the card
    f = QFont("Segoe UI")
    f.setPixelSize(style.type_px("type_body", scale))
    from PySide6.QtGui import QFontMetricsF
    line = QFontMetricsF(f).height()
    ft = QFont("Segoe UI")
    ft.setPixelSize(style.type_px("type_head", scale))
    ink = QFontMetricsF(ft).height() + 3 * line
    host.close()
    return h, ink, h - ink


def toolbar_items(app, pal, scale):
    """How many toolbar actions are still VISIBLE at 1280 -- the rest are in Qt's hidden chevron."""
    from ff9mapkit.workspace.shell import Workspace, _apply_app_theme
    _apply_app_theme(app, pal)
    w = Workspace(pal)
    w._apply_text_scale(scale)
    w.resize(1280, 820)
    w.show()
    app.processEvents()
    assert w.width() == 1280, f"asked 1280 got {w.width()} -- a resize is a request, not a fact"
    tb = w._toolbar if hasattr(w, "_toolbar") else None
    if tb is None:
        from PySide6.QtWidgets import QToolBar
        tbs = w.findChildren(QToolBar)
        tb = tbs[0] if tbs else None
    assert tb is not None, "no toolbar found -- this probe is measuring nothing"
    acts = [a for a in tb.actions() if not a.isSeparator()]
    vis = sum(1 for a in acts
              if tb.widgetForAction(a) is not None and tb.widgetForAction(a).isVisible())
    w.close()
    return vis, len(acts)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    assert app.platformName() != "offscreen", "offscreen stubs the font DB -- every number would be fiction"
    _f = QFont("Segoe UI")
    _f.setPixelSize(14)
    assert QFontInfo(_f).pixelSize() == 14, "font DB not resolving"
    app.setStyle("fusion")
    pal = pick_palette("dark")

    print("=== A CARD: does the air grow with the ink?\n")
    print(f"  {'scale':>5} {'body':>5} | {'card h':>7} {'ink':>6} {'air':>6} {'air %':>6}")
    base = None
    for s in SCALES:
        h, ink, air = card_metrics(app, pal, s)
        if base is None:
            base = air
        print(f"  {s:>4}% {style.type_px('type_body', s):>5} | {h:>7.0f} {ink:>6.0f} {air:>6.0f} "
              f"{100 * air / h:>5.1f}%")
    print(f"\n  air at {SCALES[0]}% -> {SCALES[-1]}%: {base:.0f} -> "
          f"{card_metrics(app, pal, SCALES[-1])[2]:.0f}   (the ink grows; the air is asked not to)")

    print("\n=== THE QSS SPACING DECLARATIONS: how many move with the dial?\n")
    import re
    a = style.qss(pal, "comfortable", 100)
    b = style.qss(pal, "comfortable", SCALES[-1])
    pads_a = re.findall(r"(?:padding|spacing|margin)\s*:\s*[^;]+;", a)
    pads_b = re.findall(r"(?:padding|spacing|margin)\s*:\s*[^;]+;", b)
    moved = sum(1 for x, y in zip(pads_a, pads_b) if x != y)
    print(f"  {moved} of {len(pads_a)} padding/spacing/margin declarations move between 100% and {SCALES[-1]}%")

    print("\n=== THE TOOLBAR BUDGET (the trap style.py documents)\n")
    print(f"  {'scale':>5} | {'visible':>7} / total   verdict")
    for s in SCALES:
        vis, tot = toolbar_items(app, pal, s)
        print(f"  {s:>4}% | {vis:>7} / {tot:<5}  {'all reachable' if vis == tot else 'OVERFLOW -> chevron'}")
    print("\n  (overflowed items are still reachable via Qt's chevron -- the cost is DISCOVERABILITY,")
    print("   which style.py records as how Ctrl-K and Preferences went invisible.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
