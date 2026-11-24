import os, sys, tomllib, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
import test_cutscenedoc as T
from collections import Counter
def tags(c): return Counter(it.data(0) for it in c._scene.items() if it.data(0))
tmp = pathlib.Path(tempfile.mkdtemp()); p = T.make_cutscene_field(tmp)
raw = tomllib.loads(T.FIELD_TOML)
d = CutsceneDoc(pick_palette("dark")); d.show_field("GLEN", raw, p)
d.board_btn.setChecked(True); d._show_beat(1)
print("scene0 beat:", d.board_pos.text(), "| say:", repr(d.board_say.text()), dict(tags(d.canvas)))
for _ in range(3): d._del_step(0)
print("steps now:", raw["cutscene"][0]["steps"])
print("after deleting every step:", d.board_pos.text(), "| say:", repr(d.board_say.text()),
      "| canvas beatpos items:", tags(d.canvas)["beatpos"], "| slider enabled", d.board_slider.isEnabled())
print("canvas board beats:", len((d.canvas._board or {}).get("beats", [])), "doc board beats:", len(d._board.get("beats", [])))
