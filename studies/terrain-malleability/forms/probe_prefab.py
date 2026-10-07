"""forms lane, step 1: dump ONE block prefab's component tree + its WMBlockPrefab typetree (calibration on
block (3,9) = Water Shrine, the one block source code special-cases: WMWorldPrefabMaker.cs:159, WMWorld.cs:602).
Rerun:  py probe_prefab.py [x y disc]"""
import sys
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X
x, y, d = (int(a) for a in sys.argv[1:4]) if len(sys.argv) >= 4 else (3, 9, 1)
env = X._worldmap_env(d)
by_cont, by_pid = {}, {}
for o in env.objects:
    by_pid[o.path_id] = o
    c = (getattr(o, "container", None) or "").lower()
    if c:
        by_cont[c] = o
pf = by_cont[f"assets/resources/worldmap/prefabs/worlddisc{d}/r{y}/block[{x}][{y}].prefab"]
go = pf.read()
comps = [(cid, pp) for cid, pp in go.m_Component]
print("root GO:", go.m_Name, "components:", [(cid, pp.path_id) for cid, pp in comps])
for cid, pp in comps:
    ob = by_pid[pp.path_id]
    if cid == 114:
        tt = ob.read_typetree()
        for k, v in tt.items():
            print("     ", k, "=", v)
    if cid == 4:
        tr = ob.read()
        for ch in tr.m_Children:
            ctr = by_pid[ch.path_id].read()
            cgo = by_pid[ctr.m_GameObject.path_id].read()
            mid = None
            for ccid, cpp in cgo.m_Component:
                if ccid == 33:   # MeshFilter
                    mid = by_pid[cpp.path_id].read().m_Mesh.path_id
            mcont = (getattr(by_pid.get(mid), "container", None) or "") if mid else ""
            print("     child", repr(cgo.m_Name), "active", cgo.m_IsActive, "transform pid", ch.path_id, "mesh pid", mid, "->", mcont)
