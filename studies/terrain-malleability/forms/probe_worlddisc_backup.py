"""forms lane: inspect 'worlddisc-incasethatitneedstocreateagain.prefab' (p0data3) -- is it the WMBlock (runtime
tier) hierarchy whose IsSwitchable SetForm actually reads (WMBlock.cs:99), or a WMBlockPrefab tier copy?
Rerun:  py probe_worlddisc_backup.py"""
import sys, collections
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X
env = X._worldmap_env(1)
by_pid, by_cont = {}, {}
for o in env.objects:
    by_pid[o.path_id] = o
    c = (getattr(o, "container", None) or "").lower()
    if c:
        by_cont[c] = o
root = by_cont["assets/resources/worldmap/prefabs/worlddisc-incasethatitneedstocreateagain.prefab"].read()
print("root:", root.m_Name, [(cid) for cid, pp in root.m_Component])
tr = [by_pid[pp.path_id] for cid, pp in root.m_Component if cid == 4][0].read()
print("children:", len(tr.m_Children))
keys = None; sw = []; cnt = collections.Counter()
for ch in tr.m_Children:
    ctr = by_pid[ch.path_id].read()
    g = by_pid[ctr.m_GameObject.path_id].read()
    mbs = [by_pid[pp.path_id] for cid, pp in g.m_Component if cid == 114]
    for mb in mbs:
        tt = mb.read_typetree()
        if keys is None:
            keys = list(tt.keys()); print("fields:", keys)
        cnt[(tt.get("IsSwitchable"), tt.get("IsSea"))] += 1
        if tt.get("IsSwitchable"):
            sw.append((tt["InitialX"], tt["InitialY"]))
    cnt["grandchildren>0"] += 1 if len(ctr.m_Children) else 0
print("(IsSwitchable, IsSea) counts:", dict(cnt))
print("switchable:", sorted(sw))
