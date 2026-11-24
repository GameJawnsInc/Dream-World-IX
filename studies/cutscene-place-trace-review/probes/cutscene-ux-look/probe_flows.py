import os, sys, tomllib, importlib.util, pathlib, tempfile
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
app = QApplication(sys.argv)
REPO = pathlib.Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9")
spec = importlib.util.spec_from_file_location("fx", REPO/"ff9mapkit/tests/test_cutscenedoc.py")
fx = importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
from ff9mapkit.workspace import style
tmp = pathlib.Path(tempfile.mkdtemp(dir=os.environ["SCR"]))
p = fx.make_cutscene_field(tmp)
pal = pick_palette("dark")
try:
    app.setStyleSheet(style.qss(pal))
except Exception as e: print("qss", e)
d = CutsceneDoc(pal)
d.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
d.resize(820, 640); d.show()
raw = tomllib.loads(p.read_text(encoding="utf-8"))
d.show_field("GLEN", raw, p); app.processEvents()

# 1. settings typed but not applied, then the shell re-feeds (tab show) the same field
d.settings_btn.setChecked(True); app.processEvents()
g = d._settings_getters
g["requires_scenario"].__self__.setText("777")
print("1. typed gate before refeed:", g["requires_scenario"]())
d.show_field("GLEN", raw, p); app.processEvents()
print("1. gate field after same-field refeed:", d._settings_getters["requires_scenario"](), "| raw:", raw["cutscene"][0].get("requires_scenario"))
d.settings_btn.setChecked(False); app.processEvents()

# 2. step editor reveal: is the header (Apply) inside the ladder viewport?
d._edit_step(2); app.processEvents(); app.processEvents()
vp = d._lscroll.viewport()
top = d.editor.apply_btn.mapTo(vp, d.editor.apply_btn.rect().topLeft()).y()
row_top = None
print("2. viewport h", vp.height(), "editor h", d.editor.height(), "apply_btn y in viewport", top,
      "scroll", d._lscroll.verticalScrollBar().value())
# 3. stage pick armed, then switch kind to say
d._close_editor(); d._render(); app.processEvents()
d._edit_step(0); app.processEvents()
d.editor.pick_btn.click()
print("3. armed:", d.canvas.on_sim_click is not None)
d.editor.kind.setCurrentIndex(0)   # say
print("3. after kind->say still armed:", d.canvas.on_sim_click is not None, "pick visible:", d.editor.pick_btn.isVisibleTo(d.editor))
d._close_editor()
# 4. delete scene: one call, no confirm
n0 = len(raw["cutscene"])
d.del_scene_btn.click(); app.processEvents()
print("4. scenes before/after one click on - Scene:", n0, len(raw["cutscene"]))
# 5. selection visual: does a selected row differ from others other than the chip text?
d.show_field("GLEN", raw, p); app.processEvents()
d._on_step_select(1); app.processEvents()
rows = [d.ladder._lay.itemAt(i).widget() for i in range(d.ladder._lay.count())]
rows = [r for r in rows if r is not None and r.__class__.__name__ == "_StepRow"]
print("5. row props:", [(r.property("role"), r.property("selected"), r.styleSheet()) for r in rows], [c.text() for c in d.ladder._idx_chips])
