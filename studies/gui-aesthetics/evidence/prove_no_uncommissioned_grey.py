"""Where did the workflow's '603 px of #787878' come from?

It does not reproduce in the real shell (0 px) or in a stylesheet'd QTabWidget (0 px). Hypothesis: the
agent probed a QTabBar with NO app stylesheet applied -- i.e. Qt's default Fusion/Windows base line --
and reported a harness artifact as a live application defect.

Test: the SAME widget, with and without the app sheet.
"""
import collections
import os
import sys
from pathlib import Path

REPO = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\gui-card-readability-eb5d9f")
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt                                          # noqa: E402
from PySide6.QtGui import QImage                                       # noqa: E402
from PySide6.QtWidgets import (                                        # noqa: E402
    QApplication, QTabWidget, QVBoxLayout, QWidget,
)

from ff9mapkit.editor import theme                                     # noqa: E402
from ff9mapkit.workspace.style import qss                              # noqa: E402

app = QApplication.instance() or QApplication([])


def count(sheet, label, draw_base=True):
    host = QWidget()
    lay = QVBoxLayout(host)
    tw = QTabWidget()
    tw.setDocumentMode(True)
    tw.tabBar().setDrawBase(draw_base)
    for n in ("Content", "Battle", "Save"):
        tw.addTab(QWidget(), n)
    lay.addWidget(tw)
    if sheet:
        host.setStyleSheet(sheet)
    host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    host.resize(700, 200)
    host.show()
    app.processEvents()
    img = host.grab().toImage()
    c = collections.Counter()
    for y in range(img.height()):
        for x in range(img.width()):
            c[QImage.pixelColor(img, x, y).name()] += 1
    host.hide()
    app.processEvents()
    greys = {k: v for k, v in c.items() if k in ("#787878", "#adadad", "#f0f0f0", "#d4d0c8")}
    print(f"  {label:52} #787878={c.get('#787878', 0):5}  other Qt-default greys={greys}")
    return c.get("#787878", 0)


print(f"Qt style in play: {app.style().objectName()}\n")
print("THE SAME QTabWidget, with and without the app stylesheet:\n")
bare = count(None, "NO stylesheet (raw Qt default)")
styled = count(qss(theme.DARK), "WITH the app sheet (what the app actually ships)")
nobase = count(qss(theme.DARK), "WITH the app sheet + setDrawBase(False)", draw_base=False)

print()
if bare and not styled:
    print("VERDICT: the grey is a HARNESS ARTIFACT.")
    print("  It appears only when the app stylesheet is absent. The app always applies its sheet, so this")
    print("  grey is never on the user's screen. The QSS pane/tab rules already override Qt's base.")
elif styled:
    print("VERDICT: the grey is REAL -- it survives the app sheet. The claim stands.")
else:
    print("VERDICT: no #787878 anywhere in this configuration -- the claim does not reproduce at all.")
