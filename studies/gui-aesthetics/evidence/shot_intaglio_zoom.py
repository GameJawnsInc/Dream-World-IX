"""INTAGLIO at 6x: the only way to actually SEE a 1px material.

The full-panel render is useless for this judgement -- a 1px edge in a 1180px screenshot is invisible to
review, exactly as the quiet tier's fill was (measured 1.215 and looked identical). The edge IS painting:
probed at t=0.18, a dark button's top border row is #5d626b and its foot is #30343d, as specified.

So: crop the action row + an input, scale 6x NEAREST (never smooth -- interpolation invents the very
gradient we are trying to judge), and stack the candidates for one comparison.

THE CALL: at 0.18 the carrier is d33-d43 but the NON-carrier is d13-d17 in the six dark palettes -- a lit
top AND a visible foot, which is a bevel, which is Windows 95. At 0.14 the carrier drops to d26-d34 and
the foot quiets. 0.00 is what ships today. No ratio can separate "lit" from "Win95"; only this can.

Run:  py studies/gui-aesthetics/evidence/shot_intaglio_zoom.py
Out:  evidence/intaglio_zoom_{palette}.png
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
from PySide6.QtWidgets import (                                                # noqa: E402
    QApplication, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from ff9mapkit.editor import theme                                             # noqa: E402
from ff9mapkit.workspace.style import qss                                      # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen forces Fusion and stubs the font DB"

ZOOM = 6
TS = [0.00, 0.14, 0.18]


def strip(mode, t):
    """The real widgets, from the real sheet, at one t."""
    theme.EDGE_T = t
    pal = theme.THEMES[mode]
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(14, 12, 14, 12)
    v.setSpacing(10)

    row = QHBoxLayout()
    row.setSpacing(8)
    a = QPushButton("Build / Deploy")
    a.setObjectName("accent")                 # the primary: lit from its own hue
    b = QPushButton("Check logic")            # the default: raised
    c = QPushButton("Package (zip)…")
    c.setProperty("role", "quiet")            # the quiet rung: flush, no edge
    for w in (a, b, c):
        row.addWidget(w)
    row.addStretch(1)
    v.addLayout(row)

    e = QLineEdit()
    e.setPlaceholderText("a .field.toml — an input is CUT, not raised")
    v.addWidget(e)

    host.setStyleSheet(qss(pal))
    host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    host.resize(520, 92)
    host.show()
    app.processEvents()
    img = host.grab().toImage()
    host.hide()
    app.processEvents()
    return img


for mode in ("dark", "light", "mist"):
    imgs = [(t, strip(mode, t)) for t in TS]
    w, h = imgs[0][1].width(), imgs[0][1].height()
    lab = 26
    out = QImage(w * ZOOM, (h * ZOOM + lab) * len(TS), QImage.Format.Format_RGB32)
    d = theme.derive(dict(theme.THEMES[mode]))
    out.fill(QColor(d["bg"]))
    p = QPainter(out)
    f = QFont("Segoe UI")
    f.setPixelSize(15)
    f.setWeight(QFont.Weight.DemiBold)
    p.setFont(f)
    for i, (t, img) in enumerate(imgs):
        y = i * (h * ZOOM + lab)
        p.setPen(QColor(d["text"]))
        tag = "t = 0.00  — SHIPS TODAY (no edge)" if t == 0 else f"t = {t:.2f}"
        p.drawText(6, y + 18, tag)
        # NEAREST: smooth scaling would invent the gradient we are here to judge
        p.drawImage(0, y + lab, img.scaled(w * ZOOM, h * ZOOM, Qt.AspectRatioMode.IgnoreAspectRatio,
                                           Qt.TransformationMode.FastTransformation))
    p.end()
    dst = HERE / f"intaglio_zoom_{mode}.png"
    out.save(str(dst))
    print(f"  {dst.name:28} {out.width()}x{out.height()}")

theme.EDGE_T = 0.18
print("\nLook at the button's TOP edge vs its FOOT. Raised object, or Win95 chip?")
