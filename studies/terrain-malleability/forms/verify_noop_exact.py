"""VERIFIER (forms lane, F10/F17) -- are the NO-OP cells REALLY identical, or only multiset-equal?

mesh_channel_diff.py compares parts as multisets of per-triangle records with SORTED corners, which is blind to
(1) triangle ORDER (the engine's raycast takes the first hit in array order), (2) WINDING (sorted corners erase it,
but the n.y > 0.1 walk filter and back-face culling depend on it) and (3) the NORMAL channel. A "free" switch
(BMV, F17) must be identical in all three. This compares the ORDERED arrays (verts, tris, uvs, tangents,
normals) of every form-1/form-2 pair on each disc-1/disc-4 NO-OP cell.
CALIBRATION: a part vs itself is IDENTICAL; a part vs a copy with two triangles' corners swapped (winding
flipped) must be reported as DIFFERENT by this checker while still multiset-equal by the lane's geo key.
Rerun:  py verify_noop_exact.py
"""
import sys, json
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X

census = json.loads((HERE / "out" / "prefab_census.json").read_text())
table = json.loads((HERE / "out" / "form_table.json").read_text())
PAIRS = [("TerrainForm1", "TerrainForm2"), ("ObjectForm1", "ObjectForm2"), ("VolcanoCrater1", "VolcanoCrater2"),
         ("VolcanoLava1", "VolcanoLava2")]


def arrays(mesh_path):
    import re
    m = re.match(r"worldmap/disc(\d)/(0_\d)/r(\d+)/block\[(\d+)\]\[(\d+)\] (\w+)\.asset", mesh_path)
    bm = X.read_block(int(m.group(4)), int(m.group(5)), disc=int(m.group(1)), lod=m.group(2), part=m.group(6))
    return (tuple(map(tuple, bm.verts)), tuple(map(tuple, bm.tris)), tuple(map(tuple, bm.uvs or [])),
            tuple(map(tuple, bm.tangents or [])), tuple(map(tuple, getattr(bm, "normals", None) or [])))


def same(a, b):
    names = ("verts", "tris", "uvs", "tangents", "normals")
    return [n for n, x, y in zip(names, a, b) if x != y]


# calibration
row = [r for r in census["1"] if (r["x"], r["y"]) == (22, 14)][0]
A = arrays(row["slots"]["TerrainForm1"]["mesh"])
assert same(A, A) == []
tris = list(A[1])
tris[0] = (tris[0][0], tris[0][2], tris[0][1])
tris[1] = (tris[1][0], tris[1][2], tris[1][1])
B = (A[0], tuple(tris), A[2], A[3], A[4])
assert same(A, B) == ["tris"], same(A, B)
print("CALIBRATION OK: self identical; winding flip of 2 tris detected as 'tris' differing; normals channel present:",
      len(A[4]) > 0)

for d in ("1", "4"):
    noop = [tuple(r["cell"]) for r in table["rows"] if r[f"disc{d}"]["class"] == "NO-OP"]
    rows = {(r["x"], r["y"]): r for r in census[d]}
    print(f"\ndisc {d}: NO-OP cells per label_forms = {noop}")
    for c in noop:
        s = rows[c]["slots"]
        res = []
        for a, b in PAIRS:
            if a in s or b in s:
                if (a in s) != (b in s):
                    res.append(f"{a}/{b}: PRESENCE DIFFERS")
                    continue
                diff = same(arrays(s[a]["mesh"]), arrays(s[b]["mesh"]))
                res.append(f"{a[:-1]}: {'IDENTICAL (ordered arrays)' if not diff else 'DIFF ' + ','.join(diff)}")
        print("   ", c, " | ".join(res))
