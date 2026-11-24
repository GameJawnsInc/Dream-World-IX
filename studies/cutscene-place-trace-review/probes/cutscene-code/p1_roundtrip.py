import os, sys, copy, tomllib, json, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit"); sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
from ff9mapkit.workspace import cutscenescan
import test_cutscenedoc as T

tmp = pathlib.Path(tempfile.mkdtemp())
STEPS = [
    {"say": "Hi", "style": 128},
    {"say": "Hi", "signal": "+"},
    {"say": "Hi", "signal": True},
    {"say": "Hi", "window_pos": [10, 20], "box": [100, 2], "dim": True},
    {"walk": "@altar", "actor": "Cid", "speed": 12},
    {"path": ["altar", [100, 200]], "actor": "Cid"},
    {"animation": "12", "actor": "Cid"},
    {"wait_signal": 3, "timeout": 99},
    {"walk": [10, 20], "actor": "Cid", "follow": "Mira"},
    {"turn": 64, "actor": "Mira", "with_prev": True},
    {"set_flag": [8712, 1]},
    {"say": "line", "actor": "Cid", "speaker": "Cid", "speed": 4},
]
raw = tomllib.loads(T.FIELD_TOML)
raw["cutscene"][0]["steps"] = copy.deepcopy(STEPS)
p = T.make_cutscene_field(tmp)
d = CutsceneDoc(pick_palette("dark"))
d.show_field("GLEN", raw, p)
for i, before in enumerate(STEPS):
    d._edit_step(i)
    try:
        d._apply_step()
    except Exception as e:
        print(i, "EXC", type(e).__name__, e); continue
    after = raw["cutscene"][0]["steps"][i]
    note = d.editor.note.text()
    if after != before or note:
        print(i, "BEFORE", before, "\n   AFTER ", after, "\n   NOTE", repr(note))
    else:
        print(i, "same")
    d._close_editor()
# build validation of the style one
from ff9mapkit.content import text as _t
try:
    _t.resolve_style(raw["cutscene"][0]["steps"][0].get("style"))
    print("style ok")
except Exception as e:
    print("style after apply ->", e)
