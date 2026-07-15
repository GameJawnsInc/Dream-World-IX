"""Render the REAL 'Build to (field)' panel before/after the `style.py:126` selector fix.

This answers the question the whole plan is gated on and that nobody in the research dossier ever asked:
*what does the panel actually look like without the phantom rects?* The user's own screenshot is the
"before"; this produces the "after" WITHOUT editing style.py (the fix is injected into the rendered QSS).

Harness recipe (from studies/gui-makeover/README.md -- do NOT use QT_QPA_PLATFORM=offscreen here; it
stubs the font DB, gives tofu boxes, and inflates text advances 2-3x):
    native platform + WA_DontShowOnScreen + show() + processEvents() + grab().

Run:  py studies/gui-aesthetics/evidence/shot_builddeploy.py
Out:  studies/gui-aesthetics/evidence/builddeploy_{before,after}.png
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

from ff9mapkit.editor.theme import DARK, derive                                # noqa: E402
from ff9mapkit.workspace.builddoc import BuildDoc                              # noqa: E402
from ff9mapkit.workspace.style import qss                                      # noqa: E402

BROKEN_T = "QCheckBox:focus::indicator, QRadioButton:focus::indicator { border: 1px solid %s; }"
FIXED_T = "QCheckBox::indicator:focus, QRadioButton::indicator:focus { border: 1px solid %s; }"

# The fix LANDED (Phase 0, style.py:126), so the shipped QSS is now the "after". The "before" is
# reconstructed by RE-INJECTING the malformed selector, so this stays runnable rather than bit-rotting.

app = QApplication.instance() or QApplication([])
pal = derive(DARK)
focus = pal.get("focus", pal["accent"])
fixed_css = qss(DARK)
broken, fixed = BROKEN_T % focus, FIXED_T % focus
assert fixed in fixed_css, "style.py lacks the correct `::indicator:focus` -- has Phase 0 been reverted?"
broken_css = fixed_css.replace(fixed, broken)


def shot(sheet, name):
    doc = BuildDoc(pal, REPO, run=lambda *a, **k: None, problems=lambda *a, **k: None)
    doc.setStyleSheet(sheet)
    doc.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    doc.resize(1180, 460)
    doc.show()
    app.processEvents()

    box = doc.field_box                      # just the 'Build to (field)' group -- the exact card complained about
    pm = box.grab()
    out = HERE / f"builddeploy_{name}.png"
    pm.save(str(out))
    print(f"  {out.name:26s} {pm.width()}x{pm.height()}")
    doc.deleteLater()
    app.processEvents()
    return out


print(f"platform={app.platformName()}  (must NOT be 'offscreen' -- see the harness note)")
print(f"DARK focus={focus}\n")
shot(broken_css, "before")
shot(fixed_css, "after")
print("\nOpen both. The 'before' should show a blue rect around every radio row; the 'after' none.")
