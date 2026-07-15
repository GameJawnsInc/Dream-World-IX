"""REGISTER P1: does the quiet selection still out-read HOVER? Render it; do not argue it.

THE DEDUCTION this answers. By contrast ratio, hover BEATS the new selection in four palettes
(nord 1.327 vs 1.161, gruvbox 1.488 vs 1.294, dracula 1.451 vs 1.329, sol-dark 1.326 vs 1.230). That
looks fatal and is not, because contrast is LUMINANCE-ONLY and blind to the axis the selection uses:

    hover     = a pure lightness step   (dHue 0.2-2.5 deg, dSat -0.05..+0.08)
    selection = a hue/chroma event      (dHue up to 93.8 deg, dSat up to +0.42) + a 3px saturated rail

But this arc's record is that the eye failed six times and the pixels did not -- so the argument does not
get to settle it. This renders the REAL rows, from the REAL sheet, at 4x, and lets an eye decide.

Run:  py studies/gui-aesthetics/evidence/shot_selection.py
Out:  evidence/selection_{palette}.png
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtCore import QPoint, Qt                                          # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter                      # noqa: E402
from PySide6.QtWidgets import (                                                # noqa: E402
    QApplication, QListWidget, QVBoxLayout, QWidget,
)

from ff9mapkit.editor import theme                                             # noqa: E402
from ff9mapkit.workspace.style import qss                                      # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB and forces Fusion"

ZOOM = 4
ROWS = ["alexandria_gate", "evil_forest_1", "prima_vista_deck", "ice_cavern_302"]


def shot(mode):
    pal = theme.THEMES[mode]
    host = QWidget()
    v = QVBoxLayout(host)
    v.setContentsMargins(10, 10, 10, 10)
    lst = QListWidget()
    for r in ROWS:
        lst.addItem(r)
    v.addWidget(lst)
    host.setStyleSheet(qss(pal))
    host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    host.resize(360, 150)
    host.show()
    app.processEvents()

    lst.setCurrentRow(1)                       # row 1 = SELECTED
    # row 2 = HOVERED. A grab cannot carry a real mouse, so post a synthetic move to the row's centre --
    # Qt's :hover is driven by the widget's own under-mouse tracking, which this sets for real.
    r2 = lst.visualItemRect(lst.item(2))
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QEvent, QPointF
    lst.setMouseTracking(True)
    ev = QMouseEvent(QEvent.Type.MouseMove, QPointF(r2.center()), QPointF(r2.center()),
                     Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    app.sendEvent(lst.viewport(), ev)
    app.processEvents()

    img = host.grab().toImage()
    big = img.scaled(img.width() * ZOOM, img.height() * ZOOM,
                     Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
    out = HERE / f"selection_{mode}.png"
    big.save(str(out))
    host.hide()
    app.processEvents()
    return out


for mode in ("gruvbox-dark", "nord", "solarized-light"):    # the palettes where hover out-CONTRASTS selection
    p = shot(mode)
    print(f"  {p.name:28} row1 = SELECTED, row2 = hovered")

print("\nLook at row 1 vs row 2. If the ratio were the right instrument, row 2 would win.")
