import os, sys, tomllib, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from ff9mapkit.editor.theme import pick_palette
from ff9mapkit.workspace.cutscenedoc import CutsceneDoc
from ff9mapkit.content import text as _text
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp()); p = T.make_cutscene_field(tmp)
LINE = "We made it to the altar at last, all of us."
raw = tomllib.loads(T.FIELD_TOML)
raw["cutscene"][0]["steps"][2] = {"say": LINE, "speaker": "Cid"}
raw["cutscene"][0]["steps"].append({"say": "Quiet now.", "actor": "Mira"})
d = CutsceneDoc(pick_palette("dark")); d.show_field("GLEN", raw, p)
d.board_btn.setChecked(True)
for k in range(len(d._board["beats"])):
    d._show_beat(k); print(f"BOARD beat {k}:", repr(d.board_say.text()))
for s in raw["cutscene"][0]["steps"][2:]:
    print("GAME (build path):", repr(_text.wrap_text(_text.with_speaker(s.get("speaker"), s["say"]), 28)[0]))
