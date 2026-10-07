"""SEA4F vs SEA4 at Block[12][0] -- what the runtime open ocean actually renders, vs what the kit copies.

Runtime: every IsSea cell (205 per disc) renders SeaBlockPrefab = WorldMap/Prefabs/WorldDisc1/r0/Block[12][0]f
(WMWorld.cs:1198-1200, STOCK -- note the hard-coded disc 1), whose single child 'Sea4' references the mesh
'Block[12][0] Sea4f' (census.py: prefab d1/12,0f child Sea4 -> d1/0_1/12,0/sea4f). The kit's island sea plane
(ff9mapkit/world/island.py SEA_PLANE_SOURCE=(12,0), part 'sea4') reads the NON-f mesh and patches its one missing
quad with mesh.fill_missing_grid_quads (a cloned neighbour quad).

Measures:
  * is sea4 a strict subset of sea4f (same tris: positions, uvs, tangent.x)?  which tris does sea4f add?
  * does Block[12][0]'s Sea6 sit exactly on that quad (landdonor_water.py proves plan-coverage equality)?
  * does the kit's fill (fill_missing_grid_quads) reproduce sea4f's two extra tris byte-for-byte?

Calibration: the subset test is first run on sea4f against ITSELF (must be 512/512 shared, 0 extra).
Rerun:  py studies/terrain-malleability/consumption/sea4f_vs_sea4.py   -> out/sea4f_vs_sea4.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X              # noqa: E402
from ff9mapkit.world import mesh as M                 # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def tri_keys(bm, nd=5):
    keys = []
    for t in bm.tris:
        corners = tuple((tuple(round(c, nd) for c in bm.verts[i]), tuple(round(c, nd) for c in bm.uvs[i])) for i in t)
        tx = int(bm.tangents[t[0]][0])
        keys.append((frozenset(corners), tx))
    return keys


def compare(a, b):
    ka, kb = tri_keys(a), tri_keys(b)
    sa, sb = set(ka), set(kb)
    return {"a_tris": len(ka), "b_tris": len(kb), "shared": len(sa & sb), "only_a": len(sa - sb), "only_b": len(sb - sa),
            "same_order_prefix": sum(1 for x, y in zip(ka, kb) if x == y)}, sb - sa


def main():
    OUT.mkdir(exist_ok=True)
    s4f = X.read_block(12, 0, part="sea4f")
    s4 = X.read_block(12, 0, part="sea4")
    s6 = X.read_block(12, 0, part="sea6")
    self_cmp, _ = compare(s4f, s4f)
    c0 = self_cmp["shared"] == 512 and self_cmp["only_a"] == 0
    print(f"CALIB sea4f vs itself: {self_cmp} -> {'OK' if c0 else 'FAIL'}")
    cmp, extra = compare(s4, s4f)
    print(f"sea4 (cell's own) vs sea4f (SeaBlockPrefab): {cmp}")
    ex = []
    for corners, tx in extra:
        ps = sorted(p for p, _ in corners)
        ex.append({"plan_x": [min(p[0] for p in ps), max(p[0] for p in ps)], "plan_z": [min(p[2] for p in ps), max(p[2] for p in ps)],
                   "y": sorted({p[1] for p in ps}), "idall": tx, "topo": (tx & 0xFC) >> 2})
    print(f"sea4f-only tris: {ex}")
    s6p = sorted({tuple(round(c, 5) for c in v) for v in s6.verts})
    print(f"Block[12][0] Sea6 verts: {s6p}, idall {[int(t[0]) for t in s6.tangents][:3]}")
    filled = M.fill_missing_grid_quads(X.read_block(12, 0, part="sea4"))
    fcmp, fextra = compare(filled, s4f)
    print(f"kit fill_missing_grid_quads(sea4) vs sea4f: {fcmp}")
    res = {"calib_ok": c0, "sea4_vs_sea4f": cmp, "sea4f_extra_tris": ex, "sea6_verts": s6p, "kit_fill_vs_sea4f": fcmp}
    (OUT / "sea4f_vs_sea4.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"wrote {OUT / 'sea4f_vs_sea4.json'}")
    return 0 if c0 else 1


if __name__ == "__main__":
    sys.exit(main())
