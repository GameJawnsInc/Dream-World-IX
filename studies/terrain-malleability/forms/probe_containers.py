"""forms lane, step 0: what does p0data3 hold for the form switch?  Lists container paths for
(a) worldmap/disc{1,4}/0_2/* (the Form-2 mesh SOURCE per WMWorldPrefabMaker.cs:36,119-133) and
(b) worldmap/prefabs/worlddisc{1,4}/* (the baked WMBlockPrefab per-block prefabs), and reports whether
MonoBehaviours carry a TypeTree. Read-only on the install.  Rerun:  py probe_containers.py"""
import sys, re, collections
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X
env = X._worldmap_env(1)
cont = {}
for o in env.objects:
    c = (getattr(o, "container", None) or "")
    if c:
        cont.setdefault(c.lower(), []).append((o.type.name, o.path_id))
print("total container entries:", len(cont))
for d in (1, 4):
    f2 = sorted(c for c in cont if f"worldmap/disc{d}/0_2/" in c)
    print(f"disc{d} 0_2 entries: {len(f2)}")
    parts = collections.Counter(re.sub(r".*\] ", "", c).replace(".asset", "") for c in f2)
    print("   parts:", dict(parts))
    pf = sorted(c for c in cont if f"worldmap/prefabs/worlddisc{d}/" in c)
    print(f"disc{d} prefab entries: {len(pf)}  e.g. {pf[:2]}  types={collections.Counter(t for c in pf for t,_ in cont[c])}")
other = sorted({re.sub(r"/r\d+/.*", "/r*/...", c) for c in cont if "worldmap/prefabs" in c})
print("prefab path families:", other[:30])
# typetree presence
mb = [o for o in env.objects if o.type.name == "MonoBehaviour"]
print("MonoBehaviours in env:", len(mb))
if mb:
    o = mb[0]
    try:
        print("serialized_type has nodes:", bool(getattr(o.serialized_type, "nodes", None) or getattr(o.serialized_type, "node", None)))
    except Exception as e:
        print("typetree probe err", e)
