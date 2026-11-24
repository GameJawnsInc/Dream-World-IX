import os, sys, tomllib, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication, QLineEdit
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
from ff9mapkit.workspace import forms_qt
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp()); p = T.make_cutscene_field(tmp)
raw = tomllib.loads(T.FIELD_TOML)
d = CutsceneDoc(pick_palette("dark")); d.show_field("GLEN", raw, p)
d.settings_btn.setChecked(True)
vals = forms_qt.read(d._settings_getters); print("before:", vals.get("requires_scenario"), vals.get("then_warp"))
# type into then_warp (unapplied)
les = [w for w in d._settings_host.itemAt(0).widget().findChildren(QLineEdit)]
# find the then_warp field via getters: set by brute force each line edit whose text == '' later; simpler: locate getter's widget
g = d._settings_getters
print("getter keys:", list(g)[:12])
# set requires_scenario text by locating the QLineEdit currently holding '100'
for le in les:
    if le.text() == "100": le.setText("150")
print("typed (unapplied):", forms_qt.read(d._settings_getters).get("requires_scenario"))
d._on_step_select(0)                       # select the walk step (settings stays open)
print("after step select:", forms_qt.read(d._settings_getters).get("requires_scenario"))
hs = d._stage_handles(); print("handles", hs)
d._on_stage_move(hs[0]["id"], 880, 380)    # a stage drag of the selected step's target
print("after a stage drag:", forms_qt.read(d._settings_getters).get("requires_scenario"), "settings open:", d.settings_btn.isChecked())
print("doc gate still:", raw["cutscene"][0].get("requires_scenario"))
