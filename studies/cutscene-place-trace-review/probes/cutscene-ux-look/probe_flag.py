import os, sys, tomllib, importlib.util, pathlib, tempfile
os.environ["QT_QPA_PLATFORM"]="offscreen"; os.environ.setdefault("FF9MAPKIT_NO_THUMBS","1")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
REPO = pathlib.Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9")
spec = importlib.util.spec_from_file_location("fx", REPO/"ff9mapkit/tests/test_cutscenedoc.py")
fx = importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
tmp = pathlib.Path(tempfile.mkdtemp(dir=os.environ["SCR"]))
p = fx.make_cutscene_field(tmp)
raw = tomllib.loads(p.read_text(encoding="utf-8"))
d = CutsceneDoc(pick_palette("dark")); d.show_field("GLEN", raw, p)
d._add_step()
d.editor.kind.setCurrentIndex(list(__import__("ff9mapkit.editor.forms",fromlist=["x"]).STEP_KIND).index("set_flag"))
d.editor.value_line.setText("8600, 1")
d._apply_step()
print("steps:", raw["cutscene"][0]["steps"][-1])
print("PROBLEMS:", repr(d.problems_lbl.text()), "| editor note:", repr(d.editor.note.text()))
