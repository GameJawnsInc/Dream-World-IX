"""INTAGLIO P2: the console, at 3x -- is it a hole in the app with a lit lip above it?

The open question the spec left thin: "kill the bottom radius ... a hole in a plate has no rounded floor."
The panes today FLOAT inside 8px margins above a QStatusBar that draws its own border-top. So squaring
their bottom corners only reads as a hole if they ALSO run flush -- and flush would butt the pane's 1px
bottom border against the status bar's 1px top border, making a 2px line. That is a render question.

Run:  py studies/gui-aesthetics/evidence/shot_console.py
Out:  evidence/console_{palette}.png
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtCore import Qt                                                  # noqa: E402
from PySide6.QtWidgets import QApplication                                     # noqa: E402

from ff9mapkit.editor import theme                                             # noqa: E402
from ff9mapkit.workspace import shell as shellmod                              # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen forces Fusion and stubs the font DB"

ZOOM = 3

for mode in ("dark", "light", "mist"):
    pal = theme.derive(dict(theme.THEMES[mode]))
    win = shellmod.Workspace(pal)
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    win.resize(1280, 800)
    win.show()
    app.processEvents()

    # the console panel + everything below it, so the lip, the wells and the status bar are all in frame
    head = win._console_head
    top = head.mapTo(win, head.rect().topLeft()).y() - 6
    img = win.grab().toImage().copy(0, top, 1280, 800 - top)
    big = img.scaled(img.width() * ZOOM, img.height() * ZOOM,
                     Qt.AspectRatioMode.IgnoreAspectRatio,
                     Qt.TransformationMode.FastTransformation)   # NEAREST: no invented gradients
    out = HERE / f"console_{mode}.png"
    big.save(str(out))
    print(f"  {out.name:20} {big.width()}x{big.height()}   (console top at y={top})")
    win.hide()
    app.processEvents()
    win.deleteLater()
    app.processEvents()

print("\nLook for: a LIT lip on the head strip, two CUT wells below it, and what happens where the")
print("wells' floor meets the status bar.")
