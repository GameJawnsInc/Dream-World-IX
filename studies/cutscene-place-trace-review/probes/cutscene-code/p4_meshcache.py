import os, sys, pathlib, tempfile, tomllib
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit import prefs
from ff9mapkit.workspace import shell
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
from ff9mapkit.scene import bgi
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp())
prefs._path = lambda: tmp / "prefs.json"
def small_mesh():   # floor only x[-300,300] z[-300,600]: the altar (900,400) is OFF it
    verts = [(-300,0,600),(300,0,600),(-300,0,-300),(300,0,-300)]
    return bgi.build(verts, [(0,1,3),(0,3,2)]).to_bytes()
# 1) same doc, walkmesh file replaced on disk, explicit re-check
p = T.make_cutscene_field(tmp / "a")
d = CutsceneDoc(pick_palette("dark"))
d.show_field("GLEN", tomllib.loads(T.FIELD_TOML), p)
d.stage_now(sync=True); print("1st check:", d.stage_note.text())
(tmp / "a" / "walkmesh.bgi").write_bytes(small_mesh())
d.stage_now(sync=True); print("explicit re-check after the mesh changed on disk:", d.stage_note.text())
d2 = CutsceneDoc(pick_palette("dark"))
d2.show_field("GLEN", tomllib.loads(T.FIELD_TOML), p)
d2.stage_now(sync=True); print("fresh doc on the same file:", d2.stage_note.text())
# 2) shell: open GLEN from dir a, check; open another GLEN from dir b (small mesh)
w = shell.Workspace(pick_palette("dark"))
pa = T.make_cutscene_field(tmp / "sa")
w.open_field(pa); w.tabs.setCurrentWidget(w.cutscene_doc)
w.cutscene_doc.stage_now(sync=True); print("shell A:", w.cutscene_doc.stage_note.text(), id(w.cutscene_doc._wmesh))
pb = T.make_cutscene_field(tmp / "sb"); (tmp / "sb" / "walkmesh.bgi").write_bytes(small_mesh())
w.open_field(pb); w.tabs.setCurrentWidget(w.cutscene_doc)
print("shell B member", w.cutscene_doc._member, "path", w.cutscene_doc._path, "armed", w.cutscene_doc._stage_armed, "mesh id", id(w.cutscene_doc._wmesh))
w.cutscene_doc.stage_now(sync=True); print("shell B check:", w.cutscene_doc.stage_note.text())
