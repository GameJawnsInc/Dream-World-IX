"""PROBE: does the app obey the OS TEXT-SIZE accessibility slider? (WCAG 1.4.4 Resize Text)

The first cut of this probe LIED: it mutated the app font and re-measured labels built BEFORE the
change -- and reported that even the app-font label "ignores the slider", which is impossible. A
probe whose control fails is measuring nothing. Widgets cache a resolved font; the propagation is
event-driven and does not reach an unparented, unshown label on demand.

So: build each label AFTER the font change, in a real shown window.

Windows 11 "Accessibility > Text size" scales the SYSTEM FONT's point size (it does NOT touch
logical DPI -- that's the separate "Scale" setting). Qt picks the system font up as
QApplication.font(). So the question is exactly: which of our sizing strategies tracks
QApplication.font(), and which is deaf to it?

Run:  py studies/gui-aesthetics/evidence/probe_os_text_scale.py
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtGui import QFont, QFontMetricsF                      # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget   # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"

BASE = QFont(app.font())
print(f"system font: {BASE.family()!r} {BASE.pointSizeF()}pt\n")


def measure(scale):
    """Build a fresh window under a scaled app font; report each strategy's rendered height."""
    f = QFont(BASE)
    f.setPointSizeF(BASE.pointSizeF() * scale)
    app.setFont(f)

    win = QWidget()
    lay = QVBoxLayout(win)
    inherit = QLabel("Deploy the field")               # strategy A: inherit the app font
    qss_px = QLabel("Deploy the field")                # strategy B: hard-coded QSS px  <- what we ship
    qss_pt = QLabel("Deploy the field")                # strategy C: QSS pt
    em = QLabel("Deploy the field")                    # strategy D: QSS em (relative)
    for w in (inherit, qss_px, qss_pt, em):
        lay.addWidget(w)
    qss_px.setStyleSheet("font-size: 13px;")
    qss_pt.setStyleSheet("font-size: 10pt;")
    em.setStyleSheet("font-size: 1.1em;")
    win.show()
    app.processEvents()
    out = {nm: QFontMetricsF(w.font()).height()
           for nm, w in (("inherit", inherit), ("qss_px", qss_px), ("qss_pt", qss_pt), ("qss_em", em))}
    win.close()
    win.deleteLater()
    app.processEvents()
    return out


a = measure(1.0)
b = measure(1.5)                                       # the slider dragged to 150%
app.setFont(BASE)

print(f"  {'strategy':10} {'100%':>7} {'150%':>7}   verdict")
print("  " + "-" * 52)
for nm in ("inherit", "qss_px", "qss_pt", "qss_em"):
    grew = b[nm] / a[nm]
    verdict = f"TRACKS  (x{grew:.2f})" if grew > 1.05 else "*** DEAF to the slider ***"
    print(f"  {nm:10} {a[nm]:>7.2f} {b[nm]:>7.2f}   {verdict}")

print()
print("  A control that fails invalidates the run: 'inherit' MUST track. If it does not,")
print("  this probe is measuring nothing and its verdicts are void.")
