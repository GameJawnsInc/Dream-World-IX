"""CAPACITY lane, step 2 -- what the RUNTIME block prefabs actually bind: child GameObject NAMES (the s34
override key is `transform.name`, WMWorld.cs:823-825) and which mesh each child's MeshFilter references,
for every block prefab on disc 1 + disc 4. Answers: is "0_2" a far LOD or the Form-2 (story-state) mesh set,
and what override filename would a Form-2 child look up?

Calibration: a known plain land block (12,10) must show exactly one child "Terrain" -> its 0_1 terrain mesh;
the Water Shrine (3,9) must show the Sea3_2/4_2/5_2 children (README.md:1222 / WMWorldPrefabMaker.cs:159).

Writes out/prefab_children.json (names + mesh names only).
Run:  py studies/terrain-malleability/capacity/prefab_children.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
_PIDS = {}
_CTYPES = Counter()          # component-type histogram over prefab roots + children (LODGroup present?)
PAT = re.compile(r"worldmap/prefabs/worlddisc(\d+)/r(\d+)/block\[(\d+)\]\[(\d+)\](f?)(?:\.prefab)?$")


def children_of(go):
    """[(child_name, mesh_name or None, slot)] for a prefab root GameObject's direct children."""
    out = []
    tr = None
    for comp in go.m_Component:
        ptr = comp.component if hasattr(comp, "component") else comp[1] if isinstance(comp, tuple) else comp
        try:
            obj = ptr.read()
        except Exception:
            continue
        _CTYPES[type(obj).__name__] += 1
        if type(obj).__name__ == "Transform":
            tr = obj
    if tr is None:
        return out
    for ch in tr.m_Children:
        t = ch.read()
        cgo = t.m_GameObject.read()
        mesh_name = None
        mesh_pid = None
        for comp in cgo.m_Component:
            ptr = comp.component if hasattr(comp, "component") else comp[1] if isinstance(comp, tuple) else comp
            try:
                o = ptr.read()
            except Exception:
                continue
            _CTYPES[type(o).__name__] += 1
            if type(o).__name__ == "MeshFilter":
                try:
                    mesh_name = o.m_Mesh.read().m_Name
                    mesh_pid = o.m_Mesh.path_id
                except Exception:
                    mesh_name = "<unreadable>"
        out.append((cgo.m_Name, mesh_name))
        _PIDS[(go.m_Name, cgo.m_Name)] = mesh_pid
    return out


def main():
    env = X._worldmap_env(1)
    res = defaultdict(dict)
    name_hist = Counter()
    for k, ptr in env.container.items():
        m = PAT.search((k or "").lower())
        if not m:
            continue
        disc, y, x, f = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(5)
        try:
            go = ptr.read()
        except Exception as e:
            continue
        if type(go).__name__ != "GameObject":
            continue
        ch = children_of(go)
        res[f"disc{disc}"][f"{x},{y}{f}"] = ch
        for n, _ in ch:
            name_hist[n] += 1
    # BINDING CHECK: does every Form-2 child (Terrain2/Object2) bind the 0_2 container mesh, and every
    # Form-1 Terrain/Object child the 0_1 one? (path_id equality; both discs share this env)
    cont = {}
    for c, o in X._mesh_index(env).items():
        mm = re.search(r"worldmap/disc(\d+)/(0_[12])/r(\d+)/block\[(\d+)\]\[(\d+)\] (terrain|object)(?:\.asset)?$", c)
        if mm:
            cont[o.path_id] = (int(mm.group(1)), mm.group(2), mm.group(6))
    bind = Counter()
    for (root, child), pid in _PIDS.items():
        if child in ("Terrain", "Object", "Terrain2", "Object2") and pid in cont:
            bind[(child, cont[pid][1])] += 1
        elif child in ("Terrain2", "Object2"):
            bind[(child, "UNMATCHED")] += 1
    print("component types over all block prefabs (roots+children):", dict(_CTYPES))
    print("child -> bound mesh dir (prefab count, both discs):", dict(bind))
    (OUT / "prefab_children.json").write_text(json.dumps(res, indent=0), encoding="utf-8")
    print("child-name histogram (both discs):", dict(name_hist.most_common()))
    for disc in ("disc1", "disc4"):
        d = res[disc]
        print(f"== {disc}: {len(d)} prefabs")
        for key in ("12,10", "3,9", "19,10", "14,6", "0,0", "12,0f", "13,4"):
            print(f"   {key}: {d.get(key)}")
        # every child whose mesh lives in the 0_2 set -> what is it NAMED?
        f2 = Counter()
        for key, ch in d.items():
            for n, mn in ch:
                if mn is not None:
                    f2[(n, "0_2?" if False else "")] += 0
        # name -> set of mesh-name suffixes
        by_name = defaultdict(Counter)
        for key, ch in d.items():
            for n, mn in ch:
                by_name[n][(mn or "None").split(" ")[-1]] += 1
        print("   child name -> mesh-name tail:", {n: dict(c) for n, c in sorted(by_name.items())})


if __name__ == "__main__":
    main()
