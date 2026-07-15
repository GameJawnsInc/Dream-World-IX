"""THE PRODUCTIZATION ACCEPTANCE -- zero-byte-diff proof for world-forest / world-hill.

Rebuilds island E's whole pipeline through the NEW ``ff9mapkit.world.interior`` module --
clean seed-55 mint -> module forest-carve (exact recovered center) -> f32 write/read-back
-> module hill (exact center from the memory) -- and byte-compares the result against the
DEPLOYED, in-game-proven island E files. Identity = the productized path is proven by
identity with the playtested deploy (the declarative-shore-tweaks pattern).

Run from the repo root:  py studies/overworld-topography/interior_productize_check.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world import extract as X                   # noqa: E402
from ff9mapkit.world import interior as IN                 # noqa: E402
from ff9mapkit.world import mesh as M                      # noqa: E402
from ff9mapkit.world.island import build_landmass          # noqa: E402

GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
BLOCKS = [(4, 17), (5, 17), (4, 18), (5, 18), (6, 18)]
HILL_CENTER = (348, -1184)                                 # memory: project-ff9-...-topography

# ---- 0. recover the forest center from the DEPLOYED bytes -------------------------------
xs, zs = [], []
for blk in BLOCKS:
    p = MODW / f"r{blk[1]}" / f"Block[{blk[0]}][{blk[1]}] Terrain.ff9mesh"
    bm = M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1], part="terrain")
    ts = bm.chan_arrays[X.CH_TAN]
    ps = bm.chan_arrays[X.CH_POS]
    for tri in bm.tris:
        if X.decode_id(int(round(ts[tri[0]][0])))["topograph"] == 37:
            for i in tri:
                xs.append(ps[i][0] + 64.0 * blk[0])
                zs.append(ps[i][2] - 64.0 * blk[1])
assert xs, "no deployed canopy found on island E"
fx = (min(xs) + max(xs)) / 2
fz = (min(zs) + max(zs)) / 2
FOREST_CENTER = (round(fx), round(fz))
print(f"recovered forest center: ({fx:.3f},{fz:.3f}) -> {FOREST_CENTER}", flush=True)

# ---- 1. clean mint -> module forest carve -------------------------------------------------
print("rebuilding island E (seed 55) ...", flush=True)
built = build_landmass(center=(344, -1152), base_radius=46, seed=55, lobes=3,
                       stamps="auto")
soup = IN.soup_from_blocks(built["blocks"])
res_f = IN.carve_forest(soup, center=FOREST_CENTER, donor=(15, 15))
IN.census_gate(res_f["changed"], probe=(FOREST_CENTER, 37))

# ---- 2. f32 write / read-back (the deployed representation) -------------------------------
tmp = Path(tempfile.mkdtemp(prefix="ff9_accept_"))
paths = {}
for blk, bm in res_f["changed"].items():
    paths[blk] = M.write_ff9mesh(bm, tmp / f"f_{blk[0]}_{blk[1]}.ff9mesh")
blocks2 = {blk: M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1], part="terrain")
           for blk, p in paths.items()}

# ---- 3. module hill on the read-back state -------------------------------------------------
soup2 = IN.soup_from_blocks(blocks2)
res_h = IN.build_hill(soup2, center=HILL_CENTER)
IN.census_gate(res_h["changed"])

# ---- 4. byte-compare vs the deployed island ------------------------------------------------
fails = []
for blk in BLOCKS:
    if blk in res_h["changed"]:
        got = M.write_ff9mesh(res_h["changed"][blk], tmp / f"h_{blk[0]}_{blk[1]}.ff9mesh").read_bytes()
        src = "mint->forest->hill"
    else:
        got = paths[blk].read_bytes()
        src = "mint->forest"
    dep = (MODW / f"r{blk[1]}" / f"Block[{blk[0]}][{blk[1]}] Terrain.ff9mesh").read_bytes()
    ok = got == dep
    print(f"  block {blk} [{src}]: {'IDENTICAL' if ok else f'DIFFERS ({len(got)} vs {len(dep)} bytes)'}",
          flush=True)
    if not ok:
        fails.append(blk)
print("hill changed blocks:", sorted(res_h["changed"]), flush=True)
if fails:
    print(f"ACCEPTANCE FAILED: {fails}")
    sys.exit(1)
print("ACCEPTANCE PASSED: the module reproduces the in-game-proven island E byte-for-byte")
