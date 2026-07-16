"""PROBE: PUNCH's claims, checked before anything is built.

The direction says three things worth acting on and one that corrects my own briefing:

  1. Segoe is optically LINEAR -- x-height/px is exactly 0.500 at every rung. One master, scaled; nothing
     about the small end drawn for the small end. That is what optical sizing exists to fix.
  2. The app OWNS a real six-cut optical family (Sitka Small/Text/Subheading/Heading/Display/Banner) and
     spends only its display cuts.
  3. QSS letter-spacing works, and the app spends it on almost nothing.
  4. MY BRIEF WAS WRONG: its "name 26px -> x-height 13.00" row is SEGOE 26, the fallback -- not the face
     the nameplate actually wears. Sitka Display is installed, so the crown is already OFF the 0.500 axis.

Every number here is measured on the SHIPPED face chain, natively. Nothing is taken from the menu.

NATIVE ONLY -- offscreen stubs the font DB and every metric under it is fiction.

Run:  py studies/gui-aesthetics/evidence/probe_optical.py
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QFontMetricsF     # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel                           # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")

from ff9mapkit.editor import theme                                           # noqa: E402
from ff9mapkit.workspace import hero, style                                  # noqa: E402

print("=" * 82)
print("1  IS THE OPTICAL FAMILY REALLY INSTALLED?  (QFontInfo resolves the FALLBACK, so ask the DB)")
print("=" * 82)
fams = set(QFontDatabase.families())
SITKA = ["Sitka Small", "Sitka Text", "Sitka Subheading", "Sitka Heading", "Sitka Display", "Sitka Banner"]
for f in SITKA:
    print(f"  {f:20} {'INSTALLED' if f in fams else '-- MISSING --'}")
print(f"\n  the nameplate's chain: {style._QSS.template.split('font-family: ')[1].split(';')[0] if False else ''}")
import re
chain = re.search(r'QLabel\[role="name"\]\s*\{\s*font-family:\s*([^;]+);', style._QSS.template)
print(f"  role=\"name\" asks for: {chain.group(1) if chain else '??'}")
print(f"  hero wordmark_face() -> {hero.wordmark_face()!r}")

print()
print("=" * 82)
print("2  THE OPTICAL AXIS -- x-height / px. A REAL optical family MOVES; one master does not.")
print("=" * 82)
print(f"  {'face':20} {'@11':>7} {'@13':>7} {'@26':>7} {'@40':>7}   scale-invariant?")
for fam in ["Segoe UI"] + [f for f in SITKA if f in fams]:
    row, vals = [], []
    for px in (11, 13, 26, 40):
        fo = QFont(fam)
        fo.setPixelSize(px)
        if QFontInfo(fo).family() != fam:                 # Qt silently fell back -- the number would be a lie
            row.append("  (fb)")
            continue
        r = QFontMetricsF(fo).xHeight() / px
        vals.append(r)
        row.append(f"{r:>7.3f}")
    inv = "yes" if vals and max(vals) - min(vals) < 0.005 else "NO -- it varies with size"
    print(f"  {fam:20} {''.join(row)}   {inv}")
print()
print("  Segoe flat at 0.500 = ONE MASTER, linearly scaled. The Sitka cuts stepping DOWN across the")
print("  family = a real optical axis: the display cuts have proportionally smaller x-heights, which is")
print("  exactly what you want big and exactly what you do not want small.")

print()
print("=" * 82)
print("3  WHAT THE CROWN ACTUALLY WEARS  (my brief's ground-truth table got this wrong)")
print("=" * 82)
for fam in ("Segoe UI", "Sitka Display"):
    fo = QFont(fam)
    fo.setPixelSize(26)
    got = QFontInfo(fo).family()
    m = QFontMetricsF(fo)
    print(f"  {fam:14} -> resolves {got!r:16} h {m.height():>6.2f}  cap {m.capHeight():>5.2f}  "
          f"x {m.xHeight():>5.2f}  x/px {m.xHeight() / 26:.3f}")
body = QFont("Segoe UI"); body.setPixelSize(14)
name = QFont("Sitka Display"); name.setPixelSize(26)
bx, nx = QFontMetricsF(body).xHeight(), QFontMetricsF(name).xHeight()
print(f"\n  nominal size ratio  26/14 = {26 / 14:.2f}x")
print(f"  OPTICAL ratio       x {nx:.2f} / x {bx:.2f} = {nx / bx:.2f}x   <- what the eye actually gets")
print("  The crown is ALREADY off the 0.500 axis because Sitka Display is a display cut. The brief's")
print("  'FACT 2: x-height scales exactly linearly' is true WITHIN Segoe and false across the shipped ramp.")

print()
print("=" * 82)
print("4  DOES QSS letter-spacing WORK, AND WHAT DOES THE APP SPEND?")
print("=" * 82)
S = "Build to (field)"
base = QLabel(S)
base.setStyleSheet("font-family: 'Segoe UI'; font-size: 14px;")
base.ensurePolished()
w0 = QFontMetricsF(base.font()).horizontalAdvance(S)
for track in (-0.5, 0, 0.3, 0.5, 1.0):
    lab = QLabel(S)
    lab.setStyleSheet(f"font-family: 'Segoe UI'; font-size: 14px; letter-spacing: {track}px;")
    lab.ensurePolished()
    w = QFontMetricsF(lab.font()).horizontalAdvance(S)
    print(f"  letter-spacing {track:>4}px -> advance {w:>7.2f}  ({w - w0:+6.2f} over {len(S)} chars "
          f"= {(w - w0) / len(S):+.3f}/char)")
print()
tracked = re.findall(r"([^{}]*)\{[^}]*letter-spacing[^}]*\}", style._QSS.template)
print(f"  QSS rules that track: {len(tracked)} -> {[t.strip()[:34] for t in tracked]}")
print(f"  and in PYTHON (QPainter, invisible to the sheet): hero._WORD_TRACK = {hero._WORD_TRACK} "
      f"at {hero._WORD_PX}px, plus the overline's 1.0 at 11px")
print("\n  So tracking IS spent -- on the two SMALL/uppercase things. The 26px crown tracks at 0, which")
print("  is the one rung where a display face most wants tightening.")
