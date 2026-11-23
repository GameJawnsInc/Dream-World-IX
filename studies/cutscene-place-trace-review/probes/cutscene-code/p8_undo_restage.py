import os, sys, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit import prefs
from ff9mapkit.workspace import shell
import test_cutscenedoc as T
from collections import Counter
def tags(c): return Counter(it.data(0) for it in c._scene.items() if it.data(0))
tmp = pathlib.Path(tempfile.mkdtemp()); prefs._path = lambda: tmp / "prefs.json"
(tmp / "f").mkdir()
p = tmp / "f" / "GLEN.field.toml"
p.write_text(T.FIELD_TOML.replace('walk = "altar"', "walk = [2000, 2000]"), encoding="utf-8")
(tmp / "f" / "walkmesh.bgi").write_bytes(T._mesh_bytes())
w = shell.Workspace(pick_palette("dark")); w.open_field(p); w.tabs.setCurrentWidget(w.cutscene_doc)
d = w.cutscene_doc
d.stage_now(sync=True); print("1 stall:", d.stage_note.text(), "verdicts", tags(d.canvas)["verdict"])
d._edit_step(0); d.editor.value_line.setText("altar"); d._apply_step(); d._close_editor()
d._restage_timer.stop(); d.stage_now(sync=True); print("2 fixed:", d.stage_note.text(), "verdicts", tags(d.canvas)["verdict"])
w._undo(); d = w.cutscene_doc
print("3 after undo: doc walk =", w._doc("GLEN").data["cutscene"][0]["steps"][0].get("walk"),
      "| restage timer armed:", d._restage_timer.isActive(), "| note:", d.stage_note.text(), "| verdicts", tags(d.canvas)["verdict"])
