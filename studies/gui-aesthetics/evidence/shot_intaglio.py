"""INTAGLIO: render the edge at several `t` and let an eye decide.

THE question this direction turns on, and the one no measurement can answer. At t=0.18 the CARRIER lands
d33-d43 in all 8 palettes -- but the NON-CARRIER lands d13-d17 in the six dark ones, so dark gets a lit
top AND a visible shaded foot. Two edges on a raised rectangle is a BEVEL, and a bevel is Windows 95.
Light does not have the problem: its non-carrier is d8, genuinely invisible, so light gets one clean foot.

"Materially lit" and "Win95" have identical contrast ratios. Only looking can separate them.

Run:  py studies/gui-aesthetics/evidence/shot_intaglio.py
Out:  evidence/intaglio_{palette}_t{NN}.png  -- the real Build & Deploy action row + inputs

NATIVE platform only: offscreen stubs the font DB AND forces the Fusion style, so it lies about both text
advances and what Qt paints.
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
from ff9mapkit.workspace.builddoc import BuildDoc                              # noqa: E402
from ff9mapkit.workspace.style import qss                                      # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "run me on the native platform -- see the module docstring"


def shot(mode, t):
    theme.EDGE_T = t                       # the lever, re-derived per render
    pal = theme.derive(dict(theme.THEMES[mode]))
    doc = BuildDoc(pal, REPO, run=lambda *a, **k: None, problems=lambda *a, **k: None)
    doc.setStyleSheet(qss(theme.THEMES[mode]))
    doc.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    doc.resize(1180, 480)
    doc.show()
    app.processEvents()
    pm = doc.grab()
    out = HERE / f"intaglio_{mode}_t{int(t * 100):02d}.png"
    pm.save(str(out))
    doc.deleteLater()
    app.processEvents()
    return out


ORIG = theme.EDGE_T
try:
    print(f"platform={app.platformName()}  style={app.style().objectName()}\n")
    for mode in ("dark", "light", "mist"):
        for t in (0.18, 0.14, 0.00):
            p = shot(mode, t)
            d = theme.derive(dict(theme.THEMES[mode]))
            carrier = max(
                max(abs(a - b) for a, b in zip(*[[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in pair]))
                for pair in ((d["border"], d["border_lit"]), (d["border"], d["border_shade"]))
            )
            print(f"  {p.name:28} carrier d{carrier}")
finally:
    theme.EDGE_T = ORIG

print("\nt=0.00 is the CONTROL: no edge at all, i.e. exactly what ships today.")
print("Look for: does the button read as a raised object, or as a bevelled Win95 chip?")
