"""SHOT: the Import doc's hint tier at a 1920 window -- one state per run.

The before/after is produced by stashing (see shot_quarto.py's header for why a faked "before" is not
acceptable here: COLUMN's change is in PYTHON -- 35 call sites moved from a hand-rolled QLabel to
widgets.caption() -- and no stylesheet patch can reproduce the old widget).

The numbers are already conclusive (103.6 / 140.8 / 198.5 / 313.7 ch/line before, flat 74.1 after). This
is for the thing the numbers cannot answer: whether a 380px column of 12px grey text READS, or whether it
now looks like a narrow ribbon stranded in a wide pane.

NATIVE ONLY. Fusion, because the app forces Fusion (shell.py:129). The text scale is PINNED to 100 --
the user's real prefs are at 110% and a probe must not inherit them.

Run:  py studies/gui-aesthetics/evidence/shot_column.py <out-stem>
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtWidgets import QApplication                                   # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")

from ff9mapkit.editor import theme                                           # noqa: E402
from ff9mapkit.workspace import shell as S                                   # noqa: E402

stem = sys.argv[1] if len(sys.argv) > 1 else "column"
pal = theme.derive(dict(theme.THEMES["mist"]))
win = S.Workspace(pal)
win.show()
win._apply_text_scale(100)                              # never inherit the user's real dial
win.setFixedWidth(1920)
for _ in range(4):
    app.processEvents()
assert win.width() == 1920, f"asked 1920, got {win.width()} -- shot void"
win.tabs.setCurrentWidget(win.import_field)
for _ in range(4):
    app.processEvents()

img = win.import_field.grab().toImage()
dst = HERE / f"{stem}_import.png"
img.copy(0, 0, min(1500, img.width()), min(560, img.height())).save(str(dst))
print(f"  {dst.name}  ({img.width()}x{img.height()} grabbed)")
win.close()
app.processEvents()
