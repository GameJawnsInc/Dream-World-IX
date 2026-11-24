import sys
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
from ff9mapkit import floorplan as FP
out = Path(r"<SCRATCH>/review/place-code/room")
out.mkdir(exist_ok=True)
plan = {"name": "D", "mod_folder": "FF9CustomMap", "id_base": 30700, "entry": "A",
        "rooms": [{"name": "A", "poly": [[0, 0], [2400, 0], [2400, 1800], [0, 1800]]},
                  {"name": "B", "poly": [[2400, 0], [4800, 0], [4800, 1800], [2400, 1800]]}],
        "doors": [{"a":"A","b":"B"}]}
try:
    FP.compose_and_emit(plan, out, log=None)
except Exception as e:
    print("doors err", e); plan["doors"]=[]; FP.compose_and_emit(plan, out, log=None)
for p in sorted(out.rglob("*")): print(p.relative_to(out))
t = next((out/"A").glob("*.field.toml")); print(t.read_text(encoding="utf-8")[:3000])
