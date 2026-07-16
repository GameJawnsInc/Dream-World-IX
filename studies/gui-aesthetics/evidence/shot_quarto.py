"""SHOT: the real Build & Deploy card, before and after QUARTO P1 + RUBRIC.

Renders ONE state -- whatever is in the working tree -- to a named PNG. The before/after is produced by
`shot_quarto_ab.py`, which stashes and re-runs this in a FRESH PROCESS.

That indirection is not ceremony. The first cut of this shot patched the stylesheet to fake the "before",
and that was already dishonest for QUARTO (an anchor on `font-size: 13px` that the token change had
retired -- the guard caught it) and *structurally impossible* for RUBRIC, whose change is in PYTHON:
widgets.section() chooses role="cardtitle" and drops the .upper(). No amount of QSS patching reproduces
the old widget. The only faithful "before" is the old code, run as the old code.

NATIVE ONLY -- offscreen stubs the font DB and every advance it reports is fiction. Style is forced to
Fusion because THE APP FORCES FUSION (shell.py:129 _apply_app_theme); the platform default would render
chrome the app never ships.

Run:  py studies/gui-aesthetics/evidence/shot_quarto.py <out-stem>
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtWidgets import QApplication                                  # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")                                  # what the app really runs

from ff9mapkit.editor import theme                                          # noqa: E402
from ff9mapkit.workspace import style                                       # noqa: E402
from ff9mapkit.workspace.builddoc import BuildDoc                           # noqa: E402

stem = sys.argv[1] if len(sys.argv) > 1 else "quarto"
W, H = 720, 560

for mode in ("mist", "light"):
    pal = theme.derive(dict(theme.THEMES[mode]))
    doc = BuildDoc(pal, REPO, run=lambda *a, **k: None, problems=lambda *a, **k: None)
    doc.setStyleSheet(style.qss(pal))
    doc.resize(W, H)
    doc.ensurePolished()
    app.processEvents()
    dst = HERE / f"{stem}_{mode}.png"
    doc.grab().toImage().save(str(dst))
    doc.deleteLater()
    app.processEvents()
    print(f"  {dst.name}")
