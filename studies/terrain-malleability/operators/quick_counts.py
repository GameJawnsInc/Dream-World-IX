"""Operator inventory, step 5: cheap map-scale denominators the NOTES quote (block counts per kind), from the
kit's own reader.  READ-ONLY (container-name indexing; no mod folder is read or written).

  terrain blocks on Disc1/Disc4 ; blocks carrying an Object (town/structure) ; beach-bearing coastal donors
  (list_coastal_donors beach_only=True) ; all coastal donors.

These are the denominators for 'how much of the real map can operator X touch': e.g. 63 object blocks bound the
number of real blocks where a Terrain reshape leaves a rendering/collision Object behind.

Rerun:  py studies/terrain-malleability/operators/quick_counts.py
"""
import json, os, sys
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
res = {
    "terrain_blocks_disc1": len(X.list_blocks(disc=1)),
    "terrain_blocks_disc4": len(X.list_blocks(disc=4)),
    "object_blocks_disc1": len(X.list_object_blocks(disc=1)),
    "object_blocks_disc4": len(X.list_object_blocks(disc=4)),
    "beach_donors_disc1": sorted(X.list_coastal_donors(disc=1, beach_only=True)),
    "all_coastal_donors_disc1": len(X.list_coastal_donors(disc=1, beach_only=False)),
}
res["beach_donor_count"] = len(res["beach_donors_disc1"])
# ---- the mesh-contract ceiling (engine constants: WorldMeshOverride.cs:186 vcount <= 65535 [s34]; unindexed => 3 verts/tri,
#      WMBlock.cs:60-73 [stock]) and how much headroom the stock map leaves under it
import math, statistics
MAX_VERTS = 65535
res["max_tris_per_part_block"] = MAX_VERTS // 3
res["finest_uniform_lattice_u"] = round(64.0 / math.sqrt(res["max_tris_per_part_block"] / 2.0), 3)   # 2 tris per square cell
res["stock_lattice_u"] = 4.0
tri_counts = []
for (bx, by) in X.list_blocks(disc=1):
    tri_counts.append(len(X.read_block(bx, by, disc=1, part="terrain").tris))
res["stock_terrain_tris_per_block"] = {"min": min(tri_counts), "median": statistics.median(tri_counts), "max": max(tri_counts), "n": len(tri_counts)}
res["stock_max_headroom_x"] = round(res["max_tris_per_part_block"] / max(tri_counts), 1)
res["beach_donors_disc1"] = [list(b) for b in res["beach_donors_disc1"]]
json.dump(res, open(os.path.join(OUT, "quick_counts.json"), "w"), indent=1)
print({k: v for k, v in res.items() if k != "beach_donors_disc1"})
