import sys, copy, tomllib, pathlib, tempfile
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit/tests")
import os; os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from ff9mapkit import build
from ff9mapkit.workspace import cutscenescan as cs
import test_cutscenedoc as T
tmp = pathlib.Path(tempfile.mkdtemp()); p = T.make_cutscene_field(tmp)
base = tomllib.loads(T.FIELD_TOML)
def case(name, steps, actors=("Cid", "Mira")):
    raw = copy.deepcopy(base)
    raw["cutscene"][0]["steps"] = steps
    raw["cutscene"][0]["actors"] = list(actors)
    tab = cs.scene_problems(raw) + cs.dispatch_problems(raw)
    bp = [x for x in build._validate_conductor.__globals__["validate"](build.FieldProject(copy.deepcopy(raw), tmp)) if "cutscene" in x]
    print(f"== {name}\n  TAB  : {tab}\n  BUILD: {bp}")
case("say leads a with_prev turn (after a move)", [{"walk": "altar", "actor": "Cid"}, {"say": "hi"}, {"turn": 64, "actor": "Mira", "with_prev": True}])
case("same actor twice in a parallel group", [{"walk": "altar", "actor": "Cid"}, {"turn": 64, "actor": "Cid", "with_prev": True}])
case("actor step untagged in a 2-cast scene", [{"walk": "altar"}])
case("bad tail code", [{"say": "hi", "tail": "XYZ"}])
case("empty steps", [])
case("bad style string", [{"say": "hi", "style": "fancy"}])
