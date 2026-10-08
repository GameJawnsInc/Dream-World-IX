"""Operator inventory, step 6: FREE-RIDE EXPOSURE -- for each operator that deploys a Donor.txt sidecar, which
sub-meshes of the donor PREFAB does the operator NOT override or blank (so the engine renders them from the
donor prefab, unrotated / un-edited / un-mirrored-by-intent)?

Engine fact (read in WMWorld.cs, stock+s34): a cell diverted by HasLandOverride loads the donor prefab and then
registers EVERY transform the prefab has (WMWorld.cs:588-807, LoadBlock); RegisterBlockComponent swaps in a
loose override only for the parts that have one (WMWorld.cs:823-831).  Any part the writer neither overrides nor
blanks renders verbatim from the donor.  For Object that is by design (THE OBJECT POSE LAW); for Beach2 / Sea6 /
Stream / Volcano* / River / Falls it is a silent free-rider.

For each lane we take the part set the lane's own code deploys (constants copied from the module, with their
file:line in LANES below) and subtract it from the donor block's real part set (asset container names, both
discs).  READ-ONLY (container-name index; no mesh decode, no mod folder touched).

CALIBRATION: the world-island non-beach lane must show Uaho (0,0)'s free-riders as {} or explain each; the
control is the (7,17) transplant lane, where the module docstring itself documents Object as the free-rider.

Rerun:  py studies/terrain-malleability/operators/donor_part_exposure.py
"""
import json, os, re, sys
from collections import defaultdict

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X, island as I, transplant as T, interior as IN, water as W, terrain as TR

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def parts_by_block(disc):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    out = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            out[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return out


P = {1: parts_by_block(1), 4: parts_by_block(4)}
low = lambda it: {s.lower() for s in it}

# lane -> (deployed part set (lowercase), donor block, source of the set)
LANES = {
    "world-island (cliff block)": (low({"Terrain", "Sea4"}) | low(I.HIDDEN_PARTS), I.DEFAULT_DONOR,
                                   "island.py HIDDEN_PARTS + Terrain + Sea4 (landmass(), else-branch)"),
    "world-island (beach block, grass pins)": (low({"Terrain", "Sea4", "Sea1", "Sea2", "Sea5", "Beach1", "Object", "Sea3"}),
                                               I.BEACH_PINS["grass"], "island.py landmass() is_bch branch"),
    "world-island (beach block, desert pins)": (low({"Terrain", "Sea4", "Sea1", "Sea2", "Sea5", "Beach1", "Object", "Sea3"}),
                                                I.BEACH_PINS["desert"], "island.py landmass() is_bch branch"),
    "world-water": (low({"Terrain"}) | low(W.LADDER) | low(W.BLANK), (15, 4), "water.py _deploy_ocean_cell (donor default 15,4)"),
    # defect 18: before the fix the set was {"Terrain"} alone, and Sea1/3/4/5 free-rode (H1, in-game RESULTS section 9)
    "world-reclaim (no sidecar -> LandDonorPrefab 12,10)": (low({"Terrain"}) | low(TR.LAND_DONOR_WATER), TR.LAND_DONOR,
                                                            "terrain.reclaim Terrain + LAND_DONOR_WATER + WMWorld.cs:1210"),
    "world-coast (donor 18,15)": (low({"Terrain"}), (18, 15), "terrain.coast: Terrain only + Donor.txt"),
    "world-transplant (donor 7,17)": (low(T.PARTS), (7, 17), "transplant.PARTS"),
    "world-transplant (donor 20,5)": (low(T.PARTS), (20, 5), "transplant.PARTS"),
    # the ensemble carry runs on an ALREADY-deployed island: its files (Terrain, Sea4, the blanked HIDDEN_PARTS) stay, and
    # deploy_mountain_parts adds ENSEMBLE_PARTS + re-points Donor.txt at the part-carrying donor (interior.py:3265-3315)
    "world-mountain ensemble (horseshoe 5,15)": (low({"Terrain", "Sea4"}) | low(I.HIDDEN_PARTS) | low(IN.ENSEMBLE_PARTS), (5, 15),
                                                 "island files already on disk + interior.ENSEMBLE_PARTS"),
}

rows = {}
print(f"{'lane':52s} {'donor':8s} {'disc':4s} donor-prefab parts -> FREE-RIDERS (parts the lane neither overrides nor blanks)")
for lane, (dep, donor, src) in LANES.items():
    for d in (1, 4):
        have = P[d].get(tuple(donor), set())
        free = sorted(have - dep)
        rows[f"{lane} | disc{d}"] = {"donor": list(donor), "donor_parts": sorted(have), "deployed": sorted(dep), "free_riders": free, "src": src}
        print(f"{lane:52s} {str(tuple(donor)):8s} {d:<4d} {sorted(have)} -> {free}")

# the global blind-spot set: part names that NO lane in the kit can write or blank
KIT_WRITABLE = low(T.PARTS) | low(I.HIDDEN_PARTS) | low(IN.ENSEMBLE_PARTS) | low(W.LADDER) | low(W.BLANK) | {"terrain", "sea4", "object"}
allparts = set()
for d in (1, 4):
    for b, s in P[d].items():
        allparts |= s
blind = sorted(allparts - KIT_WRITABLE)
carriers = {p: sorted(b for b, s in P[1].items() if p in s) for p in blind}
print("\nreal part names on disc1/4:", sorted(allparts))
print("kit-writable (union of PARTS / HIDDEN_PARTS / ENSEMBLE_PARTS / water LADDER+BLANK + terrain/sea4/object):", sorted(KIT_WRITABLE))
print("NO kit writer can override or blank:", blind)
for p, bl in carriers.items():
    print(f"   {p:14s} carried by {len(bl)} disc-1 block(s): {bl}")
json.dump({"lanes": rows, "blind_parts": blind, "blind_carriers": {k: [list(x) for x in v] for k, v in carriers.items()}},
          open(os.path.join(OUT, "donor_part_exposure.json"), "w"), indent=1)
