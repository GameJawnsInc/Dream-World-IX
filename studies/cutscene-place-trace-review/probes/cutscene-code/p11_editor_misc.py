import os, sys, tomllib, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp()); p = T.make_cutscene_field(tmp)
raw = tomllib.loads(T.FIELD_TOML)
d = CutsceneDoc(pick_palette("dark")); d.show_field("GLEN", raw, p)
# 1) add at row 0, switch to walk, then Apply -> next row (1): is with_prev usable?
d._selected_step = None
d.editor.open_step(0, None, {"say": ""}, d._cast(), insert_at=0); d._sync_insets()
d.editor.kind.setCurrentIndex(list(__import__("ff9mapkit.editor.forms", fromlist=["x"]).STEP_KIND).index("turn"))
d.editor.value_line.setText("64"); d.editor.actor.setEditText("Mira")
d._apply_step()
print("add lane now at row", d.editor.insert_at, "| with_prev enabled:", d.editor.with_prev.isEnabled())
d._close_editor()
# 2) unapplied text lost by a rowtool click on another row
d._edit_step(2); d.editor.value_text.setPlainText("A long line I was halfway through typing")
d._move_step(0, +1)
print("editor open after ↓ on another row:", d.editor.scene is not None, "| typed text survives in doc:",
      any("halfway" in str(s.get("say", "")) for s in raw["cutscene"][0]["steps"]))
# 3) delete a row ABOVE the selection: selection drifts to a different step
d._selected_step = 3; sel_before = raw["cutscene"][0]["steps"][3]
d._del_step(0)
print("selected idx", d._selected_step, "was", sel_before, "now points at", raw["cutscene"][0]["steps"][d._selected_step] if d._selected_step is not None and d._selected_step < len(raw["cutscene"][0]["steps"]) else None)
