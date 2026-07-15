"""Render the action row + page frame after Phase 2a (the button ladder) and Phase 5 (the grid).

Two questions this answers that no fence can:
  1. Does the ladder READ -- is there one obvious entry point in the action row?
  2. Is the 24px page frame right, or is it now loose?

The A/B is honest about what it isolates. The button ORDER and the page frame are Python (a layout
reorder + page_margins), so they cannot be un-done from a stylesheet -- both shots therefore share the
new layout. What the A/B varies is the QSS half only: the `[role="quiet"]` block is stripped in "flat",
so every button renders in the default fill, which is what the row looked like before the tier existed.

Harness recipe (studies/gui-makeover/README.md): NEVER QT_QPA_PLATFORM=offscreen here -- it stubs the
font DB, gives tofu boxes and inflates advances 2-3x. Native platform + WA_DontShowOnScreen + grab().

Run:  py studies/gui-aesthetics/evidence/shot_ladder.py
Out:  studies/gui-aesthetics/evidence/ladder_{flat,ranked}.png  (Build & Deploy, full page)
      studies/gui-aesthetics/evidence/coop_ranked.png           (Co-op, full page)
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtCore import Qt                                                  # noqa: E402
from PySide6.QtWidgets import QApplication                                     # noqa: E402

from ff9mapkit.editor.theme import DARK, derive                                # noqa: E402
from ff9mapkit.workspace.builddoc import BuildDoc                              # noqa: E402
from ff9mapkit.workspace.coopdoc import CoopDoc                                # noqa: E402
from ff9mapkit.workspace.style import qss                                      # noqa: E402

app = QApplication.instance() or QApplication([])
pal = derive(DARK)

def rules_only(css: str) -> str:
    """Drop QSS comments. style.py EXPLAINS the quiet tier in prose next to it, so a substring check
    over the raw sheet reads the comment and concludes the rules are still there."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


ranked_css = qss(DARK)
assert 'QPushButton[role="quiet"]' in rules_only(ranked_css), \
    "the quiet tier is gone -- has Phase 2a been reverted?"
# strip the whole quiet block -> every button falls back to the default filled rule
flat_css = re.sub(r'\n\s*QPushButton\[role="quiet"\][^\n]*\{[^}]*\}', "", ranked_css)
assert 'QPushButton[role="quiet"]' not in rules_only(flat_css), "the quiet rules survived the strip"


def shot(make, sheet, name, size=(1180, 620)):
    doc = make()
    doc.setStyleSheet(sheet)
    doc.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    doc.resize(*size)
    doc.show()
    app.processEvents()
    pm = doc.grab()
    out = HERE / f"{name}.png"
    pm.save(str(out))
    print(f"  {out.name:24s} {pm.width()}x{pm.height()}")
    doc.deleteLater()
    app.processEvents()


def build():
    return BuildDoc(pal, REPO, run=lambda *a, **k: None, problems=lambda *a, **k: None)


def coop():
    return CoopDoc(pal, REPO, run=lambda *a, **k: None)


print(f"platform={app.platformName()}  (must NOT be 'offscreen' -- see the harness note)\n")
shot(build, flat_css, "ladder_flat")
shot(build, ranked_css, "ladder_ranked")
try:
    shot(coop, ranked_css, "coop_ranked")
except TypeError as e:                       # CoopDoc's ctor differs; not worth guessing
    print(f"  coop skipped: {e}")

print("\nlook for: ONE obvious entry point per row; Package/Disable across the stretch, unfilled but not")
print("greyed; and a 24px page frame that outranks each card's own 16px interior.")
