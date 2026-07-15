"""THE PRODUCTIZATION ACCEPTANCE -- zero-byte-diff proof for world-mountain.

Rebuilds the Uaho bench carry through the NEW ``ff9mapkit.world.interior.carve_mountain``
module and byte-compares against the DEPLOYED, in-game-approved bench (2026-07-13,
"the cliff is great -- walkable, seams against the grass great"). Two tracks:

TRACK A (strict identity, the proof): the PRISTINE bench mint the study actually
transformed (its ``.pristine-r31s42`` sibling beside the deployed file, else the study
worktree's timestamped ``.bak``) -> module carve (scan seed (160,-1246), the study's own
seed) -> byte-identical to the deployed Block[2][19]. This input still carries the
pre-fix mint's one-tri hole, so it also exercises the module's mint-hole patch.

TRACK B (the go-forward path): a FRESH ``world-island`` mint (r31 seed-42, hole-free
since the island.py ring-conformity fix) -> f32 write/read-back -> module carve. The
result legally differs from the deployed bytes ONLY at the two concave-dent
re-triangulations the fix changed in the MINT itself (world ~(142,-1220) and
~(144,-1264), both far outside the carve band); the carve must pick the identical
placement, patch zero holes, and block (2,18) must stay byte-identical.

Run from the repo root:  py studies/overworld-topography/mountain_productize_check.py
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
BLK = (2, 19)
SEED_PT = (160.0, -1246.0)                                 # the study's own scan seed
MINT = dict(center=SEED_PT, base_radius=31.0, seed=42.0, lobes=1, n_patches=0)
DENTS = ((141.9, -1219.5), (143.6, -1263.8))               # the island.py fix's two spots
DEP_P = MODW / f"r{BLK[1]}" / f"Block[{BLK[0]}][{BLK[1]}] Terrain.ff9mesh"
tmp = Path(tempfile.mkdtemp(prefix="ff9_mtn_accept_"))


def bm_of(path):
    return M.blockmesh_from_ff9mesh(path, disc=1, x=BLK[0], y=BLK[1], part="terrain")


def carve(source_bm, label):
    soup = IN.soup_from_blocks({BLK: source_bm})
    res = IN.carve_mountain(soup, near=SEED_PT, log=lambda *a: None)
    got = M.write_ff9mesh(res["changed"][BLK], tmp / f"{label}.ff9mesh").read_bytes()
    return res, got


def tri_set(raw, label):
    p = tmp / f"ts_{label}.ff9mesh"
    p.write_bytes(raw)
    bm = bm_of(p)
    ps, us = bm.chan_arrays[X.CH_POS], bm.chan_arrays[X.CH_UV]
    ns, ts = bm.chan_arrays[X.CH_NRM], bm.chan_arrays[X.CH_TAN]
    out = set()
    for tri in bm.tris:
        out.add(tuple(tuple((*ps[i], *us[i], *ns[i], ts[i][0])) for i in tri))
    return out


# ---- 0. recover the expected placement from the DEPLOYED bytes ---------------------------
dep = DEP_P.read_bytes()
dep_bm = bm_of(DEP_P)
rx, rz = [], []
ts_ = dep_bm.chan_arrays[X.CH_TAN]
ps_ = dep_bm.chan_arrays[X.CH_POS]
for tri in dep_bm.tris:
    if X.decode_id(int(round(ts_[tri[0]][0])))["topograph"] in IN.MOUNTAIN_ROCK_TOPOS:
        for i in tri:
            rx.append(ps_[i][0] + 64.0 * BLK[0])
            rz.append(ps_[i][2] - 64.0 * BLK[1])
assert rx, "no deployed massif rock found on the bench"
RECOVERED = (round((min(rx) + max(rx)) / 2), round((min(rz) + max(rz)) / 2))
print(f"recovered massif centre from the deployed bytes: ~{RECOVERED}", flush=True)

# ---- TRACK A: the pristine study input -> module carve -> IDENTITY ------------------------
pris = DEP_P.with_name(DEP_P.name + ".pristine-r31s42")
if not pris.exists():
    cands = sorted(Path(__file__).resolve().parents[2].glob(
        "**/backups/Block[[]2[]][[]19[]] Terrain.ff9mesh.20260713-151059"))
    assert cands, ("no pristine bench input found -- expected the .pristine-r31s42 "
                   "sibling beside the deployed file (or the study worktree .bak)")
    pris = cands[0]
print(f"TRACK A input: {pris}", flush=True)
res_a, got_a = carve(bm_of(pris), "a")
print(f"  module placement: {res_a['center']} rot {res_a['rot'] * 90}deg, "
      f"mint holes patched: {res_a['report']['patched_holes']}", flush=True)
ok_a = got_a == dep
print(f"  TRACK A [pristine -> carve vs deployed]: "
      f"{'IDENTICAL' if ok_a else f'DIFFERS ({len(got_a)} vs {len(dep)} bytes)'}", flush=True)

# ---- TRACK B: fresh mint -> f32 round-trip -> module carve --------------------------------
print("TRACK B: fresh world-island mint (r31 seed-42) ...", flush=True)
built = build_landmass(**MINT)
paths = {blk: M.write_ff9mesh(bm, tmp / f"mint_{blk[0]}_{blk[1]}.ff9mesh")
         for blk, bm in built["blocks"].items()}
fresh = {blk: M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1], part="terrain")
         for blk, p in paths.items()}
res_b, got_b = carve(fresh[BLK], "b")
print(f"  module placement: {res_b['center']} rot {res_b['rot'] * 90}deg, "
      f"mint holes patched: {res_b['report']['patched_holes']}", flush=True)
fails = []
if res_b["center"] != res_a["center"] or res_b["rot"] != res_a["rot"]:
    fails.append(f"track B placement {res_b['center']}/{res_b['rot']} != track A")
if res_b["report"]["patched_holes"] != 0:
    fails.append("the fresh mint should be hole-free (island.py ring-conformity fix)")
# the only byte differences must be the mint's own dent re-triangulations
sA = tri_set(dep, "dep")
sB = tri_set(got_b, "b")
diff = sA ^ sB
far = []
for t in diff:
    cx = sum(p[0] for p in t) / 3 + 64.0 * BLK[0]
    cz = sum(p[2] for p in t) / 3 - 64.0 * BLK[1]
    if not any((cx - dx) ** 2 + (cz - dz) ** 2 < 6.0 ** 2 for dx, dz in DENTS):
        far.append((round(cx, 1), round(cz, 1)))
print(f"  TRACK B diff vs deployed: {len(diff)} tris, all at the two mint dents: "
      f"{'YES' if not far else f'NO -- strays at {far[:5]}'}", flush=True)
if far:
    fails.append(f"track B differs outside the mint dents: {far[:5]}")
if len(diff) > 32:
    # the flips re-triangulate ~6 tris and re-smooth their corner normals, which the
    # neighboring tris' coincident entries share -- measured 24 tris total (2026-07-15)
    fails.append(f"track B dent diff too large ({len(diff)} tris)")
# the neighbor block the mint spills into is untouched by the carve
dep18 = (MODW / "r18" / "Block[2][18] Terrain.ff9mesh").read_bytes()
got18 = paths[(2, 18)].read_bytes()
ok18 = got18 == dep18
print(f"  block (2,18) [mint-only]: {'IDENTICAL' if ok18 else 'DIFFERS'}", flush=True)
if not ok18:
    fails.append("fresh mint block (2,18) differs from the deployed one")

if not ok_a:
    fails.insert(0, "TRACK A identity failed")
if fails:
    print("ACCEPTANCE FAILED:")
    for f in fails:
        print(f"  - {f}")
    sys.exit(1)
print("ACCEPTANCE PASSED: carve_mountain reproduces the in-game-approved Uaho bench "
      "byte-for-byte (track A), and the go-forward fresh-mint path differs only by the "
      "mint's own dent fix (track B)")
