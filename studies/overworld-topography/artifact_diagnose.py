"""ARTIFACT DIAGNOSIS -- the hatched gray patch at the (8,17)+2x2 -> desert retile's NW coastal
notch (out/_zoom_graypatch_row1.png).

Pins the exact donor triangles under the artifact by the render's own coordinate math (row 1's
panel window, TARGET=(19,17), rot=0/shift=(0,0) so target-frame == donor-frame + (704,0)), reads
their ORIGINAL topo+uv straight from the donor's bytes, and re-runs the SAME GroundRetile.apply()
classification the real carry uses to show exactly which bucket (mains/wall/sand/recovered/
refused) each one lands in and why.

Offline only. Run from the repo root: py studies/overworld-topography/artifact_diagnose.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world.transplant import world_tris, decode_id, GroundRetile   # noqa: E402
from ff9mapkit.world import grassland as G                                   # noqa: E402
from ff9mapkit.world import island as I                                      # noqa: E402

# ---- row-1 panel window math (donor_8_17_retile_render.py, unchanged) ----------------------------
BLOCK = 64.0
SC = 8
CX, CZ, WINX, WINZ = 1280.0, -1152.0, 128.0, 128.0          # OUR CARRY row, TARGET=(19,17)
X0, X1 = CX - WINX / 2, CX + WINX / 2
Z0, Z1 = CZ - WINZ / 2, CZ + WINZ / 2

# the reported artifact pixel bbox (panel-local, matches the zoom crop) -> world bbox (target frame)
PX0, PX1, PY0, PY1 = 640, 940, 280, 480
wx0, wx1 = X0 + PX0 / SC, X0 + PX1 / SC
wz0, wz1 = Z1 - PY1 / SC, Z1 - PY0 / SC
print(f"artifact px bbox ({PX0},{PY0})-({PX1},{PY1})  ->  TARGET world x[{wx0:.1f},{wx1:.1f}] "
      f"z[{wz0:.1f},{wz1:.1f}]")

DONOR = (8, 17)
TARGET = (19, 17)
OFFX = 64.0 * (TARGET[0] - DONOR[0])                          # rot=0, shift=(0,0), same by -> pure +x
OFFZ = -64.0 * (TARGET[1] - DONOR[1])
dx0, dx1 = wx0 - OFFX, wx1 - OFFX
dz0, dz1 = wz0 - OFFZ, wz1 - OFFZ
print(f"  -> DONOR world x[{dx0:.1f},{dx1:.1f}] z[{dz0:.1f},{dz1:.1f}]  (offset {OFFX:+.1f},{OFFZ:+.1f})")

dbx, dby = 9, 17
print(f"  -> falls in donor block ({dbx},{dby}), local x[{dx0 - 64 * dbx:.1f},{dx1 - 64 * dbx:.1f}] "
      f"z[{dz0 + 64 * dby:.1f},{dz1 + 64 * dby:.1f}]")

# ---- rebuild the exact same retile the carry used -------------------------------------------------
gt = GroundRetile.for_donor(DONOR, "desert", size=(2, 2), strips="auto", extra=8.0, disc=1)
print(f"\nretile grass->desert: sand anchors {gt.sand_anchors}")
print(f"recover budget {gt.recover_budget} over cells {sorted(gt.recover_cells)}")
print(f"wall_rect(desert) = {gt.wall_rect}")
print(f"mains_rect(desert) = {gt.mains_rect}")

grass_wall_rect = (min(I.ROCK_U), min(I.ROCK_V), max(I.ROCK_U), max(I.ROCK_V))
grass_mains_rect = G.FAM_REGION["main"]
print(f"wall_rect(grass, i.e. donor-native) = {grass_wall_rect}")
print(f"mains_rect(grass, i.e. donor-native) = {grass_mains_rect}")

# ---- find donor tris under the artifact window, classify each ------------------------------------
hits = []
for part in ("terrain", "beach1"):
    for tri in world_tris(dbx, dby, part, disc=1, lod="0_1", game=None):
        cx = sum(v[0][0] for v in tri) / 3
        cz = sum(v[0][2] for v in tri) / 3
        if not (dx0 - 4 <= cx <= dx1 + 4 and dz0 - 4 <= cz <= dz1 + 4):
            continue
        topo = decode_id(int(round(tri[0][3][0])))["topograph"]
        us = [v[2][0] for v in tri]
        vs = [v[2][1] for v in tri]
        uvbox = (min(us), min(vs), max(us), max(vs))
        in_wall = all(gt._in(v[2], grass_wall_rect) for v in tri)
        in_mains = all(gt._in(v[2], grass_mains_rect) for v in tri)
        # run the SAME apply() the real carry ran (on a throwaway list-copy)
        n_before = dict(gt.n)
        u_before = len(gt.unclassified)
        gt.apply(part, [list(v) for v in tri])
        n_after = dict(gt.n)
        bucket = next((k for k in n_after if n_after.get(k, 0) > n_before.get(k, 0)), None)
        refused = len(gt.unclassified) > u_before
        hits.append(dict(part=part, cx=round(cx, 2), cz=round(cz, 2), topo=topo, uv=uvbox,
                         donor_in_wall_rect=in_wall, donor_in_mains_rect=in_mains,
                         bucket=("REFUSED" if refused else bucket)))

print(f"\n{len(hits)} donor tris under the artifact window:")
for h in hits:
    print(f"  {h}")

buckets = {}
for h in hits:
    buckets[h["bucket"]] = buckets.get(h["bucket"], 0) + 1
print(f"\nbucket tally: {buckets}")
