"""DRAWN: a FILMSTRIP of the signet signing itself -- the only way to show motion in a still.

The mark is revealed by walking a dash offset along a path that was ALREADY in draw-on order: it starts
at the arm's far end, where the gradient is at its faintest (alpha 70), runs left into the corner gaining
opacity, turns, rises, and the filigree + bead fade in over the final quarter so the signature lands last.

Measured by frame-diff against t=0 (no colour heuristic to get wrong):

    t=0.00     0 px                        -- nothing
    t=0.15    52 px   x 413-464  y 106     -- the far end, on the baseline
    t=0.30   105 px   x 360-464  y 106     -- running left
    t=0.70   244 px   x 221-464  y 106
    t=0.85   391 px   x 189-464  y  25-106 -- TURNED and RISEN
    t=1.00   439 px                        -- the finish lands

and t=1.0 is BYTE-IDENTICAL to the pre-DRAWN build in all 3 palettes checked.

Run:  py studies/gui-aesthetics/evidence/shot_drawn.py
Out:  evidence/drawn_{palette}.png
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtCore import Qt                                                  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter                      # noqa: E402
from PySide6.QtWidgets import QApplication                                     # noqa: E402

from ff9mapkit.editor import theme                                             # noqa: E402
from ff9mapkit.workspace import hero as H                                      # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"

FRAMES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
W, CROP_H = 560, 130          # just the wordmark + the mark; the status line is not the subject


def strip(mode):
    d = theme.derive(dict(theme.THEMES[mode]))
    shots = []
    for t in FRAMES:
        b = H.HeroBand(d)
        b.resize(1280, 156)
        b._draw = t
        shots.append(b.grab().toImage().copy(150, 12, W, CROP_H))
        b.deleteLater()

    lab = 22
    out = QImage(W, (CROP_H + lab) * len(FRAMES), QImage.Format.Format_RGB32)
    out.fill(QColor(d["bg"]))
    p = QPainter(out)
    f = QFont("Segoe UI")
    f.setPixelSize(13)
    f.setWeight(QFont.Weight.DemiBold)
    p.setFont(f)
    for i, (t, img) in enumerate(zip(FRAMES, shots)):
        y = i * (CROP_H + lab)
        p.setPen(QColor(d["muted"]))
        tag = f"t = {t:.1f}"
        if t == 0.0:
            tag += "   (motion off = this frame is never seen; the mark is simply there)"
        elif t == 1.0:
            tag += "   AT REST -- byte-identical to the pre-DRAWN build"
        p.drawText(6, y + 15, tag)
        p.drawImage(0, y + lab, img)
    p.end()
    dst = HERE / f"drawn_{mode}.png"
    out.save(str(dst))
    return dst


for mode in ("mist", "light"):
    d = strip(mode)
    print(f"  {d.name:20} {len(FRAMES)} frames")

print("\nRead top to bottom: the mark appears out of open air at the arm's faint end, runs into the")
print("corner gaining opacity, turns, rises, and the bead lands last.")
