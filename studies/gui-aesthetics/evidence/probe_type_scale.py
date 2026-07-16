"""PROBE: what the type scale actually IS at runtime -- and whether it obeys the OS.

Three questions, none of which prose can answer:

  Q1  What is the OS/Qt default app font? (Windows ships Segoe UI 9pt; the app hard-codes 13px.)
  Q2  Does a QSS `font-size: 13px` scale with the OS TEXT-SIZE accessibility slider? (WCAG 1.4.4)
  Q3  What is the real rendered pixel height + cap-height of each tier, natively?

NATIVE ONLY -- offscreen stubs the font DB (advances inflate 2-3x) and forces Fusion.

Run:  py studies/gui-aesthetics/evidence/probe_type_scale.py
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtGui import QFont, QFontInfo, QFontMetricsF          # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel                 # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"

scr = app.primaryScreen()
print("=" * 78)
print("Q1  THE OS BASELINE")
print("=" * 78)
f = app.font()
fi = QFontInfo(f)
print(f"  QApplication.font()   family={f.family()!r} resolved={fi.family()!r}")
print(f"                        pointSizeF={f.pointSizeF()}  pixelSize={f.pixelSize()}")
print(f"                        -> RESOLVED pointSize={fi.pointSize()} pixelSize={fi.pixelSize()}")
print(f"  screen  logicalDotsPerInch={scr.logicalDotsPerInch()}  devicePixelRatio={scr.devicePixelRatio()}")
print(f"          physicalDotsPerInch={scr.physicalDotsPerInch():.1f}")
print()
print("  The OS default in PIXELS is the number the app should be RELATIVE to.")
print(f"  App hard-codes 13px body. OS default renders at {QFontInfo(app.font()).pixelSize()}px.")

print()
print("=" * 78)
print("Q2  DOES QSS px OBEY THE OS TEXT-SIZE SLIDER?  (WCAG 1.4.4 Resize Text)")
print("=" * 78)
# The Windows 11 "Accessibility > Text size" slider changes the SYSTEM FONT's point size.
# It does NOT change logical DPI. So: a widget whose size comes from the app font tracks it;
# a widget with a hard-coded QSS px does not. Prove it by simulating: bump the app font and
# see which label moves.
probe_app_font = QLabel("Deploy the field")           # inherits app font -> should track
probe_qss_px = QLabel("Deploy the field")             # hard px -> should NOT track
probe_qss_px.setStyleSheet("font-size: 13px;")
probe_qss_pt = QLabel("Deploy the field")             # pt -> tracks DPI but not the slider
probe_qss_pt.setStyleSheet("font-size: 10pt;")

def heights():
    return tuple(QFontMetricsF(w.font()).height() for w in (probe_app_font, probe_qss_px, probe_qss_pt))

for w in (probe_app_font, probe_qss_px, probe_qss_pt):
    w.ensurePolished()
before = heights()
print(f"  baseline           app-font={before[0]:.2f}  qss-13px={before[1]:.2f}  qss-10pt={before[2]:.2f}")

base = app.font()
bigger = QFont(base)
bigger.setPointSizeF(base.pointSizeF() * 1.5)          # the slider at 150%
app.setFont(bigger)
for w in (probe_app_font, probe_qss_px, probe_qss_pt):
    w.setStyleSheet(w.styleSheet())                    # force re-polish
    w.ensurePolished()
after = heights()
print(f"  OS slider @ 150%   app-font={after[0]:.2f}  qss-13px={after[1]:.2f}  qss-10pt={after[2]:.2f}")
app.setFont(base)

for nm, b, a in zip(("app-font", "qss-13px", "qss-10pt"), before, after):
    verdict = "TRACKS the slider" if abs(a - b) > 0.5 else "*** IGNORES the slider ***"
    print(f"    {nm:10} {b:6.2f} -> {a:6.2f}   {verdict}")

print()
print("=" * 78)
print("Q3  EVERY TIER, RENDERED NATIVELY")
print("=" * 78)
from ff9mapkit.workspace import style                                 # noqa: E402

TIERS = [
    ("name", 26, 400), ("h2", 16, 600), ("h3", 15, 600),
    ("body", 13, 400), ("mono", 12, 400), ("caption/overline", 11, 400),
]
print(f"  {'tier':18} {'px':>4} {'wt':>4} {'height':>7} {'cap-h':>6} {'x-h':>6} {'avg-adv':>8}")
for nm, px, wt in TIERS:
    fo = QFont("Consolas" if nm == "mono" else "Segoe UI")
    fo.setPixelSize(px)
    fo.setWeight(QFont.Weight(wt))
    m = QFontMetricsF(fo)
    print(f"  {nm:18} {px:>4} {wt:>4} {m.height():>7.2f} {m.capHeight():>6.2f} "
          f"{m.xHeight():>6.2f} {m.averageCharWidth():>8.2f}")

print()
print("  x-height is what the eye actually reads. Segoe UI x-height ~= 0.50 em.")
m11 = QFontMetricsF(QFont("Segoe UI")); m11.__class__  # noqa
f11 = QFont("Segoe UI"); f11.setPixelSize(11)
f13 = QFont("Segoe UI"); f13.setPixelSize(13)
x11, x13 = QFontMetricsF(f11).xHeight(), QFontMetricsF(f13).xHeight()
print(f"  caption x-height {x11:.2f}px vs body {x13:.2f}px -> the hint tier reads "
      f"{100 * (1 - x11 / x13):.0f}% SMALLER than body, not the 15% the px numbers imply.")

print()
print("=" * 78)
print("Q4  THE MEASURE (chars per line) AT EACH WIDTH TOKEN")
print("=" * 78)
from ff9mapkit.workspace import widgets                              # noqa: E402
ALPHA = "abcdefghijklmnopqrstuvwxyz "
for nm, w_px, px in (("PROSE_W", widgets.PROSE_W, 13), ("CAPTION_W", widgets.CAPTION_W, 11)):
    fo = QFont("Segoe UI"); fo.setPixelSize(px)
    adv = QFontMetricsF(fo).horizontalAdvance(ALPHA) / len(ALPHA)
    print(f"  {nm:10} = {w_px:>4}px at {px}px  -> ~{w_px / adv:5.1f} chars/line  (ideal 45-75)")
    for bump in (1, 2, 3):
        fo2 = QFont("Segoe UI"); fo2.setPixelSize(px + bump)
        adv2 = QFontMetricsF(fo2).horizontalAdvance(ALPHA) / len(ALPHA)
        print(f"             at {px + bump}px -> ~{w_px / adv2:5.1f} chars/line")
