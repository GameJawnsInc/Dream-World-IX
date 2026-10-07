"""forms lane CENSUS 1 -- every WorldDisc1/WorldDisc4 block PREFAB's WMBlockPrefab MonoBehaviour (typetree-read via
UnityPy from the user's own install, read-only), recording IsSwitchable/IsSea/Number/Is3_9 and which form-1/form-2
slots are populated + the mesh container each child resolves to.  Output: out/prefab_census.json (derived
metadata only -- names, flags, counts; no mesh bytes).
Rerun:  py census_prefabs.py          (~1-2 min, UnityPy over p0data3.bin)"""
import sys, json, re, collections
from pathlib import Path
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X

SLOTS = ["TerrainForm1", "ObjectForm1", "TerrainForm2", "ObjectForm2", "Beach1", "Beach2", "Stream", "River",
         "RiverJoint", "Falls", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6", "VolcanoCrater1", "VolcanoLava1",
         "VolcanoCrater2", "VolcanoLava2", "Sea3_2", "Sea4_2", "Sea5_2"]
FLAGS = ["Is3_9", "IsSea", "HasSpecialObject", "IsSwitchable", "InitialX", "InitialY", "Number", "Form"]
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

def census(d):
    env = X._worldmap_env(d)
    by_pid, by_cont = {}, {}
    for o in env.objects:
        by_pid[o.path_id] = o
        c = (getattr(o, "container", None) or "").lower()
        if c:
            by_cont[c] = o
    rows = []
    pat = re.compile(rf"assets/resources/worldmap/prefabs/worlddisc{d}/r(\d+)/block\[(\d+)\]\[(\d+)\]\.prefab$")
    for c, o in sorted(by_cont.items()):
        m = pat.match(c)
        if not m:
            continue
        x, y = int(m.group(2)), int(m.group(3))
        go = o.read()
        mb = [by_pid[pp.path_id] for cid, pp in go.m_Component if cid == 114]
        if len(mb) != 1:
            rows.append({"x": x, "y": y, "error": f"{len(mb)} MonoBehaviours"}); continue
        tt = mb[0].read_typetree()
        row = {"x": x, "y": y}
        for f in FLAGS:
            row[f] = int(tt[f])
        slots = {}
        for s in SLOTS:
            pid = tt[s]["m_PathID"]
            if not pid:
                continue
            tr = by_pid[pid].read()
            cgo = by_pid[tr.m_GameObject.path_id].read()
            mid = None
            for ccid, cpp in cgo.m_Component:
                if ccid == 33:
                    mid = by_pid[cpp.path_id].read().m_Mesh.path_id
            mc = (getattr(by_pid.get(mid), "container", None) or "").lower() if mid else ""
            slots[s] = {"name": cgo.m_Name, "active": bool(cgo.m_IsActive),
                        "mesh": re.sub(r"^assets/resources/", "", mc)}
        row["slots"] = slots
        # children not referenced by any slot (would never be registered by LoadBlock)
        tr0 = [by_pid[pp.path_id] for cid, pp in go.m_Component if cid == 4][0].read()
        refd = {tt[s]["m_PathID"] for s in SLOTS if tt[s]["m_PathID"]}
        row["unreferenced_children"] = []
        for ch in tr0.m_Children:
            if ch.path_id not in refd:
                ctr = by_pid[ch.path_id].read()
                row["unreferenced_children"].append(by_pid[ctr.m_GameObject.path_id].read().m_Name)
        rows.append(row)
    return rows

res = {}
for d in (1, 4):
    rows = census(d)
    res[str(d)] = rows
    sw = [r for r in rows if r.get("IsSwitchable")]
    f2 = [r for r in rows if any(s in r.get("slots", {}) for s in ("TerrainForm2", "ObjectForm2", "VolcanoCrater2", "VolcanoLava2", "Sea3_2", "Sea4_2", "Sea5_2"))]
    print(f"disc{d}: prefabs={len(rows)} IsSwitchable={len(sw)} has-any-form2-slot={len(f2)} "
          f"errors={sum(1 for r in rows if 'error' in r)}")
    print("   switchable cells:", sorted((r['x'], r['y']) for r in sw))
    mism = [(r['x'], r['y']) for r in rows if bool(r.get('IsSwitchable')) != (r in f2)]
    print("   IsSwitchable != has-form2-slot:", mism)
    cnt = collections.Counter(s for r in f2 for s in r["slots"] if s in ("TerrainForm2","ObjectForm2","VolcanoCrater2","VolcanoLava2","Sea3_2","Sea4_2","Sea5_2"))
    print("   form2 slot counts:", dict(cnt))
    unref = [(r['x'], r['y'], r['unreferenced_children']) for r in rows if r.get('unreferenced_children')]
    print("   prefabs with unreferenced children:", unref[:10], "count", len(unref))
    # does every form2 slot resolve to a 0_2 mesh, every form1 slot to 0_1?
    bad = []
    for r in rows:
        for s, v in r.get("slots", {}).items():
            want = "0_2" if (s.endswith("Form2") or s.endswith("2") and s.startswith("Volcano") or s.endswith("_2")) else "0_1"
            if f"/{want}/" not in v["mesh"]:
                bad.append((r['x'], r['y'], s, v["mesh"]))
    print("   slot->LOD-dir mismatches:", bad[:12], "count", len(bad))
(OUT / "prefab_census.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("wrote", OUT / "prefab_census.json")
