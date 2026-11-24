import os, sys, copy, tomllib, pathlib, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
from ff9mapkit import build, flags
from ff9mapkit.editor import forms
from ff9mapkit.workspace import cutscenescan as cs
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp()); p = T.make_cutscene_field(tmp)
raw = tomllib.loads(T.FIELD_TOML)
raw["cutscene"][0]["steps"].append({"set_flag": [8600, 1]})
proj = build.FieldProject(copy.deepcopy(raw), tmp)
print("validate:", [x for x in build.validate(proj) if "8600" in x or "flag" in x.lower()])
print("lint_logic:", [x for x in build.lint_logic(build.FieldProject(copy.deepcopy(raw), tmp)) if "8600" in x])
print("lint_flag_bands:", build.lint_flag_bands(build.FieldProject(copy.deepcopy(raw), tmp)))
print("tab:", cs.scene_problems(raw)+cs.dispatch_problems(raw))
print("is_reserved 8600", flags.is_reserved(8600))
try: print(forms.make_step("set_flag", "chest_potion, 1"))
except Exception as e: print("make_step name:", e)
raw2 = tomllib.loads(T.FIELD_TOML + '\n[[flag]]\nname = "chest_potion"\nindex = 8720\n')
raw2["cutscene"][0]["steps"].append({"set_flag": ["chest_potion", 1]})
print("validate named:", [x for x in build.validate(build.FieldProject(raw2, tmp)) if "flag" in x.lower()])
