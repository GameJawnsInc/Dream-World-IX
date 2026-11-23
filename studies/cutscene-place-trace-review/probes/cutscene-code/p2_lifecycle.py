import os, sys, copy, tomllib, pathlib, tempfile, traceback
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit import prefs, provision
from ff9mapkit.workspace import cutscenescan, shell
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp())
prefs._path = lambda: tmp / "prefs.json"
try:
    provision._user_dir = lambda: tmp / "user"
except Exception: pass
sys.excepthook = lambda *a: print("EXCEPTHOOK:", "".join(traceback.format_exception(*a))[-600:])

# ---- A: undo under an open editor (shell)
w = shell.Workspace(pick_palette("dark"))
p = T.make_cutscene_field(tmp / "a")
w.open_field(p)
w.tabs.setCurrentWidget(w.cutscene_doc)
d = w.cutscene_doc
d.rail.setCurrentRow(0)
d._add_step()                       # add at end (row 3)
d.editor.value_text.setPlainText("added line")
d._apply_step()
d._close_editor(); d._render()
print("A steps after add:", [list(s)[0] for s in w._doc("GLEN").data["cutscene"][0]["steps"]])
d._edit_step(3)
print("A editor on", d.editor.scene, d.editor.step_i)
w._undo()
d = w.cutscene_doc
print("A after undo: editor target", d.editor.scene, d.editor.step_i, "steps",
      len(w._doc("GLEN").data["cutscene"][0]["steps"]), "same raw obj?", d._raw is w._doc("GLEN").data)
d.editor.value_text.setPlainText("edited after undo")
try:
    d._apply_step()
    print("A apply ok; steps:", w._doc("GLEN").data["cutscene"][0]["steps"])
except Exception as e:
    print("A APPLY RAISED", type(e).__name__, e)

# ---- A2: editor open on step 0, undo restores a doc where step 0 is something else (move)
w2 = shell.Workspace(pick_palette("dark"))
p2 = T.make_cutscene_field(tmp / "a2")
w2.open_field(p2); w2.tabs.setCurrentWidget(w2.cutscene_doc)
d2 = w2.cutscene_doc
d2._move_step(2, -1)       # say <-> turn ; undo record
d2._edit_step(1)           # now step1 = say "Made it"
print("A2 editor kind", d2.editor.current_kind(), d2.editor.value_text.toPlainText())
w2._undo()                 # step1 is turn again
d2 = w2.cutscene_doc
print("A2 after undo editor target", d2.editor.step_i, "doc step1 =", w2._doc("GLEN").data["cutscene"][0]["steps"][1])
d2._apply_step()
print("A2 after apply step1 =", w2._doc("GLEN").data["cutscene"][0]["steps"][1])
print("A2 step2 =", w2._doc("GLEN").data["cutscene"][0]["steps"][2])
