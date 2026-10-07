"""VERIFIER (adversarial) -- D4-03: prefab_census.py resolves a child's MeshFilter by m_PathID alone
(mesh_by_pid) and compares materials by m_PathID alone (m_FileID ignored). That is only sound if every
referenced PathID is unique across the serialized files in the env and the refs are file-local (FileID 0)
or point to one shared file. Check: (1) PathID uniqueness among worldmap meshes; (2) the serialized file each
disc's prefabs / meshes live in; (3) every child's m_Mesh / m_Materials FileID, resolved to a real file;
(4) material identity across discs resolved through FileID (file name + PathID). Read-only.
Run: py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/verify_prefab_refs.py
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X          # noqa: E402

env = X._worldmap_env(1)
idx = X._mesh_index(env)
pid_count = Counter(o.path_id for o in idx.values())
dups = {p: n for p, n in pid_count.items() if n > 1}
print(f"(1) worldmap meshes: {len(idx)}; PathIDs shared by >1 mesh: {len(dups)}")
mesh_files = Counter((re.search(r"worldmap/(disc\d)/", c).group(1) if re.search(r"worldmap/(disc\d)/", c) else "?",
                      o.assets_file.name) for c, o in idx.items())
print("(2) mesh (disc, serialized file):", dict(mesh_files))
PRE = re.compile(r"worldmap/prefabs/worlddisc(\d)/r(\d+)/block\[(\d+)\]\[(\d+)\](f?)\.prefab$")
pref = {}
for k, o in env.container.items():
    m = PRE.search((k or "").lower())
    if m:
        d, _r, x, y, f = m.groups()
        pref[(int(d), int(x), int(y), f)] = o
print("    prefab (disc, serialized file):", dict(Counter((k[0], o.assetsfile.name) for k, o in pref.items())))


pid2c = {oo.path_id: c for c, oo in idx.items()}
mesh_file = next(iter(idx.values())).assets_file.name


def comps(go):
    return [c[1] if isinstance(c, tuple) else getattr(c, "component", c) for c in go.m_Component]


def resolve_file(af, fid):
    if fid == 0:
        return af.name
    ext = af.externals[fid - 1]
    return getattr(ext, "path", None) or getattr(ext, "pathName", None) or str(ext)


fids = Counter()
mat_by_disc = defaultdict(Counter)
mesh_own = Counter()
for key, o in sorted(pref.items()):
    d = key[0]
    go = o.read()
    tr = next(p.read() for p in comps(go) if type(p.read()).__name__ == "Transform")
    for ch in tr.m_Children:
        cgo = ch.read().m_GameObject.read()
        for p in comps(cgo):
            obj = p.read()
            tn = type(obj).__name__
            if tn == "MeshFilter":
                ref = obj.m_Mesh
                fids[("mesh", d, ref.m_FileID)] += 1
                tf = resolve_file(o.assetsfile, ref.m_FileID)
                c = pid2c.get(ref.m_PathID) if tf == mesh_file else None
                if c:
                    mm = re.search(r"worldmap/disc(\d)/", c.lower())
                    mesh_own[(d, int(mm.group(1)) if mm else None)] += 1
                else:
                    mesh_own[(d, "unresolved")] += 1
            elif tn == "MeshRenderer":
                for m in obj.m_Materials:
                    fids[("mat", d, m.m_FileID)] += 1
                    mat_by_disc[d][(cgo.m_Name, resolve_file(o.assetsfile, m.m_FileID), m.m_PathID)] += 1
print("(3) ref FileIDs (kind, disc, FileID):", dict(fids))
print("    MeshFilter deref -> owning mesh tree (prefab disc, mesh disc):", dict(mesh_own))
# (4) material identity through the resolved file
def mat_set(d, name):
    return {(f, p) for (n, f, p) in mat_by_disc[d] if n == name}
for name in ("Terrain", "Object", "Sea4", "Terrain2"):
    print(f"(4) {name}: disc1 {sorted(mat_set(1, name))[:3]}  disc4 {sorted(mat_set(4, name))[:3]}  "
          f"same={mat_set(1, name) == mat_set(4, name)}")

# (5) which disc-4 prefab children read a DISC-1 mesh? (prefab_census normalises the disc segment, so it cannot see this)
x41 = Counter()
x41_land = Counter()
same_cell = Counter()
for key, o in sorted(pref.items()):
    if key[0] != 4:
        continue
    go = o.read()
    tr = next(p.read() for p in comps(go) if type(p.read()).__name__ == "Transform")
    for ch in tr.m_Children:
        cgo = ch.read().m_GameObject.read()
        for p in comps(cgo):
            obj = p.read()
            if type(obj).__name__ == "MeshFilter":
                c = pid2c.get(obj.m_Mesh.m_PathID, "")
                mm = re.search(r"worldmap/disc(\d)/(0_\d)/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)", c)
                if mm and mm.group(1) == "1":
                    own = (int(mm.group(4)), int(mm.group(5))) == (key[1], key[2])
                    x41[(cgo.m_Name, mm.group(2), "own-cell" if own else f"cell({mm.group(4)},{mm.group(5)})")] += 1
print("(5) disc-4 prefab children whose mesh is a DISC-1 asset (child, tree, which cell's mesh):")
for k, v in sorted(x41.items(), key=lambda kv: -kv[1])[:20]:
    print("     ", k, v)
