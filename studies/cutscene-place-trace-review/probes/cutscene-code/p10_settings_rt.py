import os, sys, copy, tomllib, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp()); p = T.make_cutscene_field(tmp)
VARIANTS = [
  {"requires_flag": "chapel_open", "set_flags": [{"flag": "chapel_open", "value": 0}], "once": False, "ate": True, "ate_mode": 6},
  {"requires_scenario": "Dali", "set_scenario": 2000},
  {"set_flags": [{"flag": 8712, "value": 1}, {"flag": 8713}], "then_warp": 4005, "warmup": 0},
  {"requires_flag": 8712, "requires_flag_clear": 8713, "flag": 8800},
]
for v in VARIANTS:
    raw = tomllib.loads(T.FIELD_TOML)
    raw["cutscene"][0].update(copy.deepcopy(v))
    before = copy.deepcopy(raw["cutscene"][0])
    d = CutsceneDoc(pick_palette("dark")); d.show_field("GLEN", raw, p)
    d.settings_btn.setChecked(True); d._apply_settings()
    after = raw["cutscene"][0]
    diff = {k: (before.get(k), after.get(k)) for k in set(before) | set(after) if before.get(k) != after.get(k)}
    print(v, "->", diff or "same", "| note:", repr(d.settings_note.text()))
