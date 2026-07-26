import sys, json
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from ff9mapkit.world import locate as L
from ff9mapkit.world import navimap as NM
a2f = L.area_to_fields()
names = L.field_names()
print("field manifest entries:", len(names))
OBJ_AREAS = {0,2,6,7,9,10,14,15,22,24,27,28,32,34,41,44,45,48,49,54,56,57,60,63}
for a in sorted(a2f):
    d = a2f[a]
    star = "*" if a in OBJ_AREAS else " "
    print(f" {star}area {a:2d} marker={NM.MARKER_NAMES.get(a,'?'):28s} -> " +
          "; ".join(f"{c}:{f}({names.get(f,'?')})" for c,f in d))
miss = sorted(OBJ_AREAS - set(a2f))
print("object-mesh areas with NO .eb case:", miss)
