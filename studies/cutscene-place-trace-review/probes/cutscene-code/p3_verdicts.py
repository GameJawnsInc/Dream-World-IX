import os, sys, copy, tomllib, pathlib, tempfile, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace import cutscenescan
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
import test_cutscenedoc as T
from collections import Counter
def tags(c): return Counter(it.data(0) for it in c._scene.items() if it.data(0))
tmp = pathlib.Path(tempfile.mkdtemp())
TOML = T.FIELD_TOML.replace('''[[cutscene]]
requires_scenario = 300
steps = [
  { say = "Dusk falls over the glen." },''', '''[[cutscene]]
requires_scenario = 300
actors = ["Mira"]
steps = [
  { walk = [2000, 2000] },
  { say = "Dusk falls over the glen." },''')
p = tmp / "GLEN.field.toml"; p.write_text(TOML, encoding="utf-8")
(tmp / "walkmesh.bgi").write_bytes(T._mesh_bytes())
raw = tomllib.loads(TOML)
d = CutsceneDoc(pick_palette("dark"))
d.show_field("GLEN", raw, p)
d.rail.setCurrentRow(0)
d.stage_now(sync=True)
print("summary:", d.stage_note.text())
print("scene#0 selected; verdict rows:", [(v['scene'], v['step']) for v in d.canvas._verdict_rows])
print("scene#0 canvas tags:", dict(tags(d.canvas)))
labels = [it.text() for it in d.canvas._scene.items() if hasattr(it, "text") and "stalls" in str(getattr(it, "text", lambda: "")())]
print("stall labels on scene #0 stage:", labels)
# storyboard timing on GUI thread with warm mesh
d.board_btn.setChecked(True)
t = time.perf_counter()
for _ in range(5): d._render()
print("5 renders with board on (warm mesh): %.3fs" % (time.perf_counter() - t))
# verdict staleness: edit scene 1 to fix its walk, verdict still painted until restage
d.board_btn.setChecked(False)
d.rail.setCurrentRow(1)
d._edit_step(0); d.editor.value_line.setText("0, 0"); d._apply_step()
print("after fix (before restage fires): verdict rows", len(d.canvas._verdict_rows), "timer active", d._restage_timer.isActive())
