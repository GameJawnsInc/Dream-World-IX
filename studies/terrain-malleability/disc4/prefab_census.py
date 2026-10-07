"""STEP 2 -- THE PREFAB-LAYER CENSUS: did Square edit anything ABOVE the mesh between WorldDisc1 and WorldDisc4?

For each of the 481 baked block prefabs (`worldmap/prefabs/worlddisc{1,4}/r{y}/block[x][y](f)`), read the
WMBlockPrefab MonoBehaviour (flags: IsSea/IsSwitchable/HasSpecialObject/Has*/Number; which Form1/Form2/part
slots are non-null) and every child GameObject (name, mesh container [disc segment normalized], material
PathIDs, local transform). Compare disc1 vs disc4. Also proves which mesh tree each slot reads -- in
particular that the `0_2` mesh tree feeds the FORM-2 slots (Terrain2/Object2/Sea*_2), not a far LOD.

Writes out/prefab_census.json. Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/prefab_census.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X          # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
env = X._worldmap_env(1)
PRE = re.compile(r"worldmap/prefabs/worlddisc(\d)/r(\d+)/block\[(\d+)\]\[(\d+)\](f?)\.prefab$")
pref = {}
for k, o in env.container.items():
    m = PRE.search((k or "").lower())
    if m:
        d, _r, x, y, f = m.groups()
        pref[(int(d), int(x), int(y), f)] = o
mesh_by_pid = {o.path_id: c for c, o in X._mesh_index(env).items()}


def _comps(go):
    return [c[1] if isinstance(c, tuple) else getattr(c, "component", c) for c in go.m_Component]


def describe(o):
    go = o.read()
    mb, kids, tr = None, [], None
    for p in _comps(go):
        obj = p.read()
        tn = type(obj).__name__
        if tn == "Transform":
            tr = obj
        elif tn == "MonoBehaviour":
            mb = p.read_typetree()
    slots = {k: (v["m_PathID"] != 0) for k, v in mb.items() if isinstance(v, dict) and "m_PathID" in v
             and k not in ("m_GameObject", "m_Script")}
    flags = {k: v for k, v in mb.items() if not isinstance(v, dict) and k not in ("m_Enabled", "m_Name")}
    for ch in tr.m_Children:
        ctr = ch.read()
        cgo = ctr.m_GameObject.read()
        mesh, mats = None, None
        for p in _comps(cgo):
            obj = p.read()
            tn = type(obj).__name__
            if tn == "MeshFilter":
                c = mesh_by_pid.get(obj.m_Mesh.m_PathID, f"pid:{obj.m_Mesh.m_PathID}")
                mesh = re.sub(r"worldmap/disc\d/", "worldmap/discN/", c)
            elif tn == "MeshRenderer":
                mats = [m.m_PathID for m in obj.m_Materials]
        lp, lr, ls = ctr.m_LocalPosition, ctr.m_LocalRotation, ctr.m_LocalScale
        kids.append({"name": cgo.m_Name, "mesh": mesh, "mats": mats,
                     "xf": [round(lp.x, 4), round(lp.y, 4), round(lp.z, 4), round(lr.x, 4), round(lr.y, 4),
                            round(lr.z, 4), round(lr.w, 4), round(ls.x, 4), round(ls.y, 4), round(ls.z, 4)]})
    rp = tr.m_LocalPosition
    return {"slots": slots, "flags": flags, "kids": kids, "root_pos": [round(rp.x, 3), round(rp.y, 3), round(rp.z, 3)]}


rows, diffs = [], Counter()
slot_tree = Counter()
for key in sorted(k for k in pref if k[0] == 1):
    _, x, y, f = key
    a = describe(pref[key])
    b = describe(pref[(4, x, y, f)])
    for kid in a["kids"]:
        m = re.search(r"/(0_\d)/", kid["mesh"] or "")
        slot_tree[(kid["name"], m.group(1) if m else None)] += 1
    rec = {"x": x, "y": y, "f": f, "diff": []}
    if a["flags"] != b["flags"]:
        rec["diff"].append(["flags", {k: (a["flags"][k], b["flags"].get(k)) for k in a["flags"]
                                      if a["flags"][k] != b["flags"].get(k)}])
    if a["slots"] != b["slots"]:
        rec["diff"].append(["slots", {k: (a["slots"][k], b["slots"].get(k)) for k in a["slots"]
                                      if a["slots"][k] != b["slots"].get(k)}])
    ka = [(k["name"], k["mesh"], k["mats"], k["xf"]) for k in a["kids"]]
    kb = [(k["name"], k["mesh"], k["mats"], k["xf"]) for k in b["kids"]]
    if [k[0] for k in ka] != [k[0] for k in kb]:
        rec["diff"].append(["children", [k[0] for k in ka], [k[0] for k in kb]])
    else:
        for p, q in zip(ka, kb):
            if p[1] != q[1]:
                rec["diff"].append(["mesh-ref", p[0], p[1], q[1]])
            if p[2] != q[2]:
                rec["diff"].append(["materials", p[0], p[2], q[2]])
            if p[3] != q[3]:
                rec["diff"].append(["transform", p[0], p[3], q[3]])
    if a["root_pos"] != b["root_pos"]:
        rec["diff"].append(["root_pos", a["root_pos"], b["root_pos"]])
    for d in rec["diff"]:
        diffs[d[0]] += 1
    rec["children1"] = [k["name"] for k in a["kids"]]
    rows.append(rec)

print(f"{len(rows)} prefab pairs compared")
print("difference kinds (count of prefab pairs x kind):", dict(diffs))
for r in rows:
    if r["diff"]:
        print(f"  ({r['x']},{r['y']}){r['f']}: {r['diff']}")
print("\nchild-slot name x mesh tree it reads (disc1 prefabs):")
for (n, t), v in sorted(slot_tree.items(), key=lambda kv: (str(kv[0][1]), kv[0][0])):
    print(f"   {n:16s} <- {t}  x{v}")
(OUT / "prefab_census.json").write_text(json.dumps({"rows": rows, "slot_tree": [[*k, v] for k, v in slot_tree.items()]},
                                                   indent=0), encoding="utf-8")
print("->", OUT / "prefab_census.json")
