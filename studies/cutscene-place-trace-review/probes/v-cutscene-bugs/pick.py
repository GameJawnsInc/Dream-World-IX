import os, sys, tomllib, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.editor import forms
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp()); p = T.make_cutscene_field(tmp)
raw = tomllib.loads(T.FIELD_TOML)
d = CutsceneDoc(pick_palette("dark")); d.show_field("GLEN", raw, p)
d._add_step()
d.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("walk"))
d.editor.pick_btn.click()
print("armed:", d.canvas.on_sim_click is not None)
d.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("say"))
print("after ->say armed:", d.canvas.on_sim_click is not None, "pick visible-flag:", not d.editor.pick_btn.isHidden())
d.canvas.on_sim_click(123.4, 456.7)   # what the canvas does on a click in sim mode
print("hidden value_line now:", repr(d.editor.value_line.text()), "| say text:", repr(d.editor.value_text.toPlainText()))
d.editor.kind.setCurrentIndex(list(forms.STEP_KIND).index("wait"))
print("->wait value_line:", repr(d.editor.value_line.text()))
