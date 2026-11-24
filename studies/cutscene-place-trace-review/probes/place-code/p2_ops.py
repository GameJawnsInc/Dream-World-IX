import sys, tempfile
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
from ff9mapkit.workspace import placedoc as P
from ff9mapkit.editor.model import FieldDoc
from ff9mapkit import build
# 1) prop naming after a delete
d = {"prop":[{"name":"prop0","prop":"barrel","pos":[0,0]},{"name":"prop1","prop":"barrel","pos":[0,0]}]}
del d["prop"][0]; P.place_prop(d, 5, 5); print("prop names:", [p["name"] for p in d["prop"]])
# 2) gateway/event index drift
d = {"gateway":[{"name":"a","to":100,"zone":[[0,0],[10,0],[10,10],[0,10]]},
                {"name":"b","to":101,"zone":[[0,0],[10,0]]},   # malformed 2pt -> skipped
                {"name":"c","to":102,"zone":[[50,0],[60,0],[60,10],[50,10]]}]}
rows = P.region_rows(d); print("rows:", [(r["i"], r["index"], r["label"]) for r in rows])
# 3) gw to 0 and to in reserved hole / out of band
d = {}
print(P.place_gateway(d, [(0,0),(1,0),(1,1),(0,1)], 0), d["gateway"][0])
for to in (9005, 3500, 20000, 32767):
    dd={"gateway":[{"name":"x","to":to,"zone":[[0,0],[100,0],[100,100],[0,100]]}]}
    print(to, "warn:", P.region_rows(dd)[0]["warn"])
# 4) scene.toml overlay
tmp = Path(tempfile.mkdtemp(dir=r"<SCRATCH>/review/place-code"))
(tmp/"room.field.toml").write_text('[field]\nid=30999\nname="R"\narea=11\n[camera]\nborrow="camera.bgx"\n[player]\nspawn=[0,0]\n', encoding="utf-8")
(tmp/"room.scene.toml").write_text('[player]\nspawn=[111,222]\n[[gateway]]\nname="door0"\nzone=[[500,500],[600,500],[600,600],[500,600]]\n', encoding="utf-8")
fd = FieldDoc.load(tmp/"room.field.toml")
print("scene loaded:", fd.scene_path is not None)
P.set_spawn(fd.data, -40, 80)
P.place_gateway(fd.data, [(0,0),(100,0),(100,100),(0,100)], 70)
print("region_rows sees:", [r["label"] for r in P.region_rows(fd.data)])
fd.save()
proj = build.FieldProject.load(str(tmp/"room.field.toml"))
print("BUILD spawn:", proj.raw["player"]["spawn"], " gateways:", [(g["name"], g.get("to"), g["zone"]) for g in proj.raw["gateway"]])
