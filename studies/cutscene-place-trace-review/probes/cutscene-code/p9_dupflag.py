import sys, copy, tomllib, pathlib, tempfile
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from ff9mapkit import build
from ff9mapkit.workspace import cutscenescan as cs
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp()); T.make_cutscene_field(tmp)
raw = tomllib.loads(T.FIELD_TOML)
raw["cutscene"][0]["flag"] = 8712
print(cs.duplicate_scene(raw, 0))
raw["cutscene"][1]["requires_scenario"] = 150        # author fixes the gate as the tooltip tells them
print("shared once-flag:", raw["cutscene"][0].get("flag"), raw["cutscene"][1].get("flag"))
print("TAB:", cs.scene_problems(raw) + cs.dispatch_problems(raw))
print("BUILD:", [p for p in build.validate(build.FieldProject(copy.deepcopy(raw), tmp)) if "flag" in p.lower() or "cutscene" in p])
