"""Render-and-diff contrast audit: every text-bearing control, every tab, every palette.

WHY THIS EXISTS
---------------
Four legibility defects shipped in this app while a test suite that greps QSS strings stayed green:
a malformed `:focus::indicator` selector that boxed every radio; `#accent` out-ranking `:focus` so the
primary button had no focus ring; `hover` byte-identical to `surface_btn` in four palettes; and a
container's bare `background: transparent` out-ranking the app sheet, so the newcomer's primary CTA was
unfilled in all 8 palettes and its label invisible in 5. Every one needed a RENDERED PIXEL to find.

THE METHOD
----------
For each visible text-bearing widget:

  * INK = w.palette().color(w.foregroundRole()). Qt's QStyleSheetStyle RESOLVES the QSS `color:` into the
    widget's QPalette at polish time -- verified: a plain QLabel reports $text, role="muted" reports
    $muted, QPushButton#accent reports $accent_fg. So the exact declared foreground is readable directly.
  * BG  = the modal colour of the widget's RENDERED crop, i.e. what is actually painted behind the glyphs
    after every cascade, override and specificity fight has resolved.
  * contrast(INK, BG), WCAG 2.1 relative luminance.

Reading the ink from QPalette instead of from pixels is what makes this trustworthy. Two earlier attempts
failed and are recorded so nobody rebuilds them:

  1. "count the ink" -- take the 2nd-most-common colour in the crop. That is an ANTIALIASING FRINGE, not
     the glyph core; it reported ~1.5:1 on text measuring a true 12.7:1.
  2. "blank the text and diff" -- grab twice, once with every text blanked; differing pixels are the
     glyphs. Correct in principle, fatal in practice: blanking makes labels shrink, THE LAYOUT REFLOWS,
     and the second grab has every widget somewhere else -- so the crop samples the wrong region and
     healthy text reads as INVISIBLE. Freezing sizes to stop the reflow perturbs the scroll areas'
     minimums and reflows them anyway. Do not revisit it.

INK-from-QPalette + BG-from-pixels catches the real bug class exactly: the ink says $accent_fg while the
background says $bg, because a container's bare `background: transparent` out-ranked the app sheet and the
button never got its fill.

Colour is font-independent, so the offscreen QPA cannot lie about it (it lies about ADVANCES) -- but this
still runs native, because a stubbed font DB perturbs layout and geometry.

KNOWN LIMIT -- READ BEFORE BELIEVING A FINDING
----------------------------------------------
The INK is exact. The BG is sampled from a render, and a widget that is shown DYNAMICALLY may not have
been laid out when the grab was taken, so its crop lands on the chrome behind it and the tool reports a
false low ratio. The breadcrumb doc-mode chip does exactly this: audited as "#ffffff on #f4f5f7 = 1.09
INVISIBLE", but probed directly it is correctly filled (#2f6feb, 847 px, with 27 px of white text). It is
FINE.

So: SPOT-CHECK before acting. A finding whose ink/bg pair is DERIVABLE FROM THE PALETTE (accent_fg on
accent; accent on surface_2; help on surface) needs no render and is trustworthy -- verify it with
arithmetic instead. A finding whose bg is a surface the widget has no business being on is the tool
lying, not the app.

Run:  py studies/gui-aesthetics/evidence/audit_contrast.py [--palette mist] [--verbose]
Exit: 0 clean, 1 if any FAIL survives.
"""
from __future__ import annotations

import collections
import os
import sys
import tempfile

os.environ["FF9MAPKIT_NO_THUMBS"] = "1"
os.environ.setdefault("LOCALAPPDATA", tempfile.mkdtemp())   # else a persisted geometry perturbs layout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ff9mapkit"))

from PySide6.QtCore import Qt                                                    # noqa: E402
from PySide6.QtGui import QColor                                                 # noqa: E402
from PySide6.QtWidgets import (                                                  # noqa: E402
    QApplication, QCheckBox, QLabel, QPushButton, QRadioButton, QToolButton, QWidget,
)

from ff9mapkit.editor import theme                                              # noqa: E402
from ff9mapkit.workspace.shell import Workspace, _apply_app_theme               # noqa: E402

TEXTY = (QLabel, QPushButton, QCheckBox, QRadioButton, QToolButton)

AA_FLOOR = 4.5      # WCAG AA, normal text
AA_LARGE = 3.0      # WCAG AA, >=18.66px or >=14px bold -- and the non-text floor


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c.red()) + 0.7152 * f(c.green()) + 0.0722 * f(c.blue())


def _cr(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _crop(img, w, win):
    g = w.geometry()
    g.moveTopLeft(w.mapTo(win, w.rect().topLeft()))
    return img.copy(g)


def audit(mode, app, verbose=False):
    pal = theme.pick_palette(mode)
    _apply_app_theme(app, pal)
    win = Workspace(pal)
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    win.resize(1400, 950)
    win.show()
    app.processEvents()

    findings = []
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)
        app.processEvents()
        tab = win.tabs.tabText(i)

        targets = [w for w in win.findChildren(QWidget)          # findChildren takes ONE type, not a tuple
                   if isinstance(w, TEXTY) and w.isVisible() and (w.text() or "").strip()
                   and not w.objectName().startswith("qt_")
                   and w.width() > 8 and w.height() > 8]
        if not targets:
            continue

        shot = win.grab().toImage()
        vis = win.rect()
        for w in targets:
            g = w.geometry()
            g.moveTopLeft(w.mapTo(win, w.rect().topLeft()))
            if not vis.contains(g):
                continue                          # scrolled below the fold: nothing painted there
            crop = shot.copy(g)
            bg = collections.Counter(
                crop.pixelColor(x, y).name()
                for x in range(crop.width()) for y in range(crop.height())
            ).most_common(1)[0][0]                # modal colour = what is really painted behind the text
            ink = w.palette().color(w.foregroundRole())    # the QSS-resolved foreground (see the header)
            r = _cr(ink, QColor(bg))
            label = f"{type(w).__name__}#{w.objectName() or '-'}"
            text = w.text()
            short = text if len(text) <= 42 else text[:39] + "..."
            f = w.font()
            big = f.pixelSize() >= 19 or (f.pixelSize() >= 14 and f.bold())
            floor = AA_LARGE if big else AA_FLOOR
            verdict = "ok" if r >= floor else ("INVISIBLE" if r < 1.15 else f"< {floor}")
            if verdict != "ok" or verbose:
                findings.append((mode, tab, label, short, r, f"{ink.name()} on {bg}", verdict))
    win.deleteLater()
    app.processEvents()
    return findings


def main():
    verbose = "--verbose" in sys.argv
    only = None
    if "--palette" in sys.argv:
        only = sys.argv[sys.argv.index("--palette") + 1]
    app = QApplication.instance() or QApplication([])
    if app.platformName() == "offscreen":
        print("REFUSING to run offscreen: a stubbed font DB renders no glyphs, so every widget would "
              "report a false INVISIBLE. Run on the native platform.")
        return 2
    rows = []
    for mode in ([only] if only else list(theme.THEMES)):
        rows += audit(mode, app, verbose)
    # DEDUPE: persistent chrome (the toolbar, the breadcrumb, the Deploy button) is re-found on all 10
    # tabs, inflating a handful of real defects into hundreds of rows. Key on the DEFECT, not the sighting.
    seen, uniq = {}, []
    for r in rows:
        k = (r[0], r[2], r[3], r[6])              # palette, widget, text, verdict
        if k in seen:
            seen[k][0] += 1
            continue
        row = [1, r]
        seen[k] = row
        uniq.append(row)
    bad = [u for u in uniq if u[1][6] != "ok"]
    print(f"{'palette':16s} {'widget':21s} {'text':38s} {'ratio':>6s} {'ink on bg':22s} seen  verdict")
    for n, (mode, tab, label, text, r, colours, verdict) in sorted(uniq, key=lambda x: x[1][4]):
        if verdict == "ok" and not verbose:
            continue
        print(f"{mode:16s} {label[:21]:21s} {text[:38]:38s} {r:6.2f} {colours:22s} x{n:<3d} {verdict}")
    print(f"\n{len(bad)} DISTINCT finding(s) across {len(theme.THEMES) if not only else 1} palette(s) "
          f"({sum(u[0] for u in bad)} sightings -- persistent chrome repeats per tab).")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
