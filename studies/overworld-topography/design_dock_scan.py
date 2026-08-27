"""ANGLE A design probe -- DOCK-SITE scan on the ACCEPTED (immovable) islands.

Read-only. For each accepted cluster, sky-casts the engine ground query
(world.placement.place, byte-exact simulator) over the deployed blocks and reports
LANDABLE APRON candidates: a land sample with a walkable 8u pad around it, low local
relief, and open water within ~16u on the ring-facing side -- i.e. where a dock
entrance trigger + its `arrive` apron can lawfully sit.

Prints the best few per island; writes out/world-design/design_dock_scan.json.

--------------------------------------------------------------------------------
THE MEASUREMENT DEFECT (found + fixed 2026-08-27)
--------------------------------------------------------------------------------
The original classifier was two lines:

    land  = {k: v for k, v in grid.items() if v[1] in LAND_MESH and v[0] > 0.25}
    water = {k for k, v in grid.items() if k not in land}

`water` was the COMPLEMENT of land, so every MISS -- a sample where the ground
query found no mesh at all -- was counted AS WATER. The admission test then asks
"is there open water within 24u?", so a candidate could be admitted because a HOLE
IN THE MEASUREMENT sat nearby, not because real sea did. In the 2026-07-25 archived
run the holes were material: Tidefall n_miss=256 / n_land=561, Larkspur n_miss=768
/ n_land=366 (~24% of that island's grid). Ashvale / Sandreach / Grimhorn: 0.

WHAT THE MISSES ACTUALLY WERE. Every one was an UNLOADED BLOCK. `ISLANDS` lists an
island's blocks, but `scan` sweeps their bounding RECTANGLE -- and these block lists
are not rectangles. Tidefall's bbox holds 6 blocks and the list names 5; the odd one
out, (8,18), has no override in the mod folder, so nothing loads there and all 16x16
= 256 of its samples MISS. Larkspur: 3 such blocks x 256 = 768. The arithmetic
reproduces both archived counts exactly.

So a MISS here was not a hole in deployed geometry -- it was ground the probe never
measured (an unmodded block; stock ocean, most likely, but the probe does not read
the stock map and cannot claim it). Two very different things wore the same "MISS".

THE FIX IS IN THREE PARTS, and the last one removes the blind spot entirely:

  1. THE SWEEP IS SCOPED TO THE ISLAND'S OWN BLOCKS (`sweep_domain`). The lattice is
     still laid over the bounding box, but only points inside the CLOSED span of a
     block that loaded are queried -- closed, because a block's mesh reaches its own
     edge verts, so the rim is measured by the block behind it. The probe never asks
     a question it cannot answer, and MISS recovers its census meaning: a MISS is a
     REAL hole, and `n_miss` is a hard-zero gate ("a miss ANYWHERE is a stranding
     spot (land) or a vehicle wall + void render (water)"). Prints GATE FAIL if one
     ever appears.
  2. MISS IS EXCLUDED FROM `water`, and because a dock is exactly where the boat hull
     and the landing apron meet, a MISS within the 24u admission envelope
     DISQUALIFIES the candidate outright.
  3. THE STOCK MAP IS COMPOSED UNDERNEATH (`load_world_meshlist`, on by default; see
     its docstring for the layering). The mod folder holds only OVERRIDES, so reading
     it alone left every un-overridden block blank. Layered the way the engine layers
     a cell -- override if present, else the game's own asset for that block, else the
     shared `SeaBlockPrefab` for a cell with no assets at all -- there is nothing left
     for the probe to be blind to: `n_unmeasured` is 0 on all five islands.

`unmeasured` remains as a class for `--no-stock` runs: never queried, never water,
never land, never disqualifying -- the probe's own blindness is not evidence of a
defect on the ground. It is recorded as `unmeasured_xz` with `unmeasured_dist` on each
admitted candidate. Treating it as a defect would have thrown away every Tidefall and
Larkspur candidate over an artifact of the old sweep -- a different wrong answer, not
a safer one.

WHAT PROVES THE LAYERING IS RIGHT WAY UP, two ways. Composing stock underneath leaves
`n_land` byte-identical on all five islands (3064 / 561 / 116 / 589 / 366) -- if a
stock sea part were winning over a mod Terrain override anywhere, the land count would
collapse. And run against an EMPTY mod folder with only the stock layer, all five
footprints read 0 land / 100% water / 0 candidates: every one of these islands is
deployed onto true open ocean, so every square of island land in a real run comes from
the override layer and stock never wins over it.

Parts 1 and 2 are silent on the real island set (`n_miss` is 0 everywhere), so
`--selftest` exercises the re-scope and the disqualify path on synthetic input --
neither is a check that cannot fail. Part 3 fires on real data (4 blocks) and is
checked by the land-count identity above.

THE SOURCE SEAM: `--src DIR` points the loader at a snapshot directory instead of
the live install, so a result is reproducible after the shared install drifts (same
law as the deploy-target seam in the brief -- pin the path through a seam, never
read the real file). A snapshot dir holds the files flat; the install nests them
under r<by>/. It pins the MOD bytes only; the stock layer comes from the game's own
assets, which no kit path writes, so it does not drift. `--no-stock` reads the mod
folder alone (the un-overridden ground goes back to UNMEASURED), and `--legacy-water`
restores the WHOLE pre-fix probe -- mod folder only, bbox sweep, MISS counted as
water, no disqualify test -- so it reproduces the archived run; A/B only.

--------------------------------------------------------------------------------
RE-RUN VERDICT (2026-08-27, A/B against ONE pinned snapshot of the live install)
--------------------------------------------------------------------------------
`--legacy-water` first, then the fix, same `--src` -- so the diff is the fix alone.
Legacy reproduces the 2026-07-25 archive on every count (Tidefall 561 land / 1056
water / 256 miss / 136 candidates; Larkspur 366 / 2035 / 768 / 141; Grimhorn 589 /
1812 / 0 / 210; Sandreach 116 / 973 / 0 / 0) and on every candidate's identity,
order, water_dist, relief and y.

ONE REAL DRIFT, fully explained: four samples read `topo` 59 where the archive read
0/17 -- (48,-1160) Ashvale, (420,-1224) Tidefall, (1204,-1184) Grimhorn, (700,-608)
Larkspur. Those are exactly the four R2 QUAY BEACON anchors (REVERT.md:1211, 1307,
1373), deployed 2026-07-26, the day AFTER the archive; topo 59 is their terrain-hull
collision class. None of them is one of the four grafted dock coords. This is the
drift `--src` exists to pin.

THE DEFECT WAS REAL BUT INERT ON THIS DATA. At the mod-only stage water drops by
exactly the miss count (Tidefall 1056 -> 800, Larkspur 2035 -> 1267) and NOT ONE
candidate moved: 0 added, 0 dropped, 0 water_dist changed, on every island -- true of
the classifier fix alone, of the re-scoped sweep, and of the composed stock layer that
puts those counts back. Falsified directly rather than inferred: re-running the
admission test against the unmeasured samples ALONE admits 0 candidates on Tidefall
and 0 on Larkspur, so nothing was ever holding a hole up as its reason to exist.
A handful of candidates (5 Tidefall, 8 Larkspur) do sit within 24u of unmeasured
ground, but each also has real sea within 12u; they now carry `unmeasured_dist`.

THE RE-SCOPE + THE STOCK LAYER. Scoping the sweep to each island's own blocks left
the candidate list on all five islands IDENTICAL; composing the stock map underneath
then left it IDENTICAL again, and restored the full bbox as measured ground. Both are
fixes to how the measurement is CONSTRUCTED, not to what it concludes. Their payoff
is the two gates: `n_miss` is 0 on all five islands and means what the census means
by it, and `n_unmeasured` is 0 -- there is no longer any ground the probe declines to
look at.

AND THE MEASURED ANSWER TO WHAT THE HOLES WERE: all 1024 of them ARE ocean. With the
stock layer composed, Tidefall's water returns to exactly 1056 and Larkspur's to
exactly 2035 -- the archive's own numbers. The pre-fix probe's ASSUMPTION was right;
it was still an assumption, and it could just as easily have sat over stock LAND, in
which case the dock candidates it admitted would have been fictional. It is now a
measurement, and the probe can no longer be right by luck.

All four dock coordinates grafted into the composed-world design SURVIVE, each
backed by real sea at 12u: (272,-1168) Ashvale, (412,-1224) Tidefall, (1204,-1192)
Grimhorn, (700,-616) Larkspur (unmeasured_dist 29.12u). Independently of this probe,
(412,-1224) was already found unbuildable in play -- the ring's R2 moved that
trigger to (420,-1232) because the beacon hull crossed the (6,19)/(6,18) seam
(southern-ring/DESIGN.md:44-45).

THE ONE LAYERING CASE NOT MODELLED, because it does not arise on this island set: a
cell carrying a `Donor.txt` divert takes its un-overridden parts from the DONOR's
prefab, not its own. Measured here, every stock part under every mod-overridden block
IS overridden, so nothing free-rides and the question never comes up -- but it would
on an island that leaves parts un-overridden. `load_world_meshlist` says so at the
call site.

Remaining, and worth knowing before trusting a candidate COUNT: `n_candidates` is the
true total, but the `candidates` list is still capped at 400 (Ashvale: 562 real, 400
listed -- the archived run recorded only the capped list, with no total).
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg
from ff9mapkit.world import mesh as M
from ff9mapkit.world import placement as P

BLOCK = 64.0
STEP = 4.0
WATER_MAX = 24.0        # admission ceiling: real sea must be this close
SEARCH_MAX = 40.0       # how far out the water ring / hole disc looks
OUT = Path(__file__).resolve().parent / "out" / "world-design"

# registration order (placement.py rule 3)
PARTS = ["Object", "Terrain", "Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls",
         "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"]
LAND_MESH = {"Object", "Terrain", "Beach1", "Beach2"}

ISLANDS = {
    "Ashvale (junction, accepted)": [(bx, by) for bx in range(0, 5) for by in range(16, 20)],
    "Tidefall (first-continent remnant)": [(6, 18), (6, 19), (7, 18), (7, 19), (8, 19)],
    "Sandreach (desert-fidelity isle)": [(11, 18), (11, 19), (12, 18), (12, 19)],
    "Grimhorn (horseshoe/crag bench)": [(bx, by) for bx in range(18, 21) for by in range(17, 20)],
    "Larkspur (relief-demo isle)": [(9, 9), (10, 8), (10, 9), (10, 10), (11, 8), (11, 9)],
}


def mesh_root(src=None):
    """(root, flat) -- a snapshot dir is flat, the live install nests under r<by>/."""
    if src is not None:
        return Path(src), True
    gp = Path(_cfg.find_game_path(None))
    return gp / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1", False


def sea_block_prefab():
    """A fresh block-local copy of the shared `SeaBlockPrefab` stand-in: the game's only full-cell
    deep Sea4 plane, hole-filled (`island._sea_plane`). Fresh per call because the caller
    translates its verts into world coordinates in place."""
    from ff9mapkit.world.island import _sea_plane
    return _sea_plane(1)


def stock_part(bx, by, part):
    """Block (bx, by)'s STOCK `part` sub-mesh, or None if the real game ships no such asset --
    the same missing-mesh idiom `transplant.world_tris` uses. `extract.read_block` hands back a
    COPY off its memo, so the world-frame translation below may mutate it safely."""
    from ff9mapkit.world import extract as X
    try:
        bm = X.read_block(bx, by, disc=1, lod="0_1", part=part.lower())
    except ValueError as e:
        if "mesh not found" in str(e):
            return None
        raise
    return bm if bm.verts else None


def load_world_meshlist(blocks, src=None, stock=True):
    """(meshlist, covered, provenance) -- one world-frame meshlist: every part of every block in
    the island's bounding box, in registration order, verts translated into world coordinates.

    THE STOCK FALLBACK (`stock`, on by default). The mod folder holds only OVERRIDES, so reading
    it alone leaves every un-overridden block blank and the probe called that MISS. Composed the
    way the engine composes a cell, a part is the loose override if one exists, else the real
    game's own asset for that block -- and a cell with NO per-block assets at all is true open
    ocean, which renders from the shared `SeaBlockPrefab` whose only transform is `Sea4`
    (`island._real_block_parts`, `transplant.effective_prefab_arm`). That last case is stood up
    with the game's one full-cell deep Sea4 plane, hole-filled, exactly as `island._sea_plane`
    does -- the plane is itself missing a quad at home, and an unfilled hole is a void render AND
    an invisible vehicle wall.

    NOT MODELLED, because it does not arise here: a cell carrying a `Donor.txt` divert takes its
    un-overridden parts from the DONOR's prefab, not its own. Measured on this island set, every
    stock part under every mod-overridden block IS overridden, so no part free-rides and the
    question never comes up. It WOULD matter on an island whose blocks leave parts un-overridden.
    """
    root, flat = mesh_root(src)
    xs = [bx for bx, _ in blocks]
    zs = [by for _, by in blocks]
    bbox = [(bx, by) for bx in range(min(xs), max(xs) + 1)
            for by in range(min(zs), max(zs) + 1)]
    per_part = {p: [] for p in PARTS}
    from_mod, from_stock, open_ocean = set(), set(), set()
    for (bx, by) in bbox:
        for part in PARTS:
            name = f"Block[{bx}][{by}] {part}.ff9mesh"
            p = root / name if flat else root / f"r{by}" / name
            if p.exists():
                bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, lod="0_1",
                                              part=part.lower())
                from_mod.add((bx, by))
            elif stock:
                bm = stock_part(bx, by, part)
                if bm is None:
                    continue
                from_stock.add((bx, by))
            else:
                continue
            per_part[part].append((bx, by, bm))
        if stock and (bx, by) not in from_mod and (bx, by) not in from_stock:
            per_part["Sea4"].append((bx, by, sea_block_prefab()))   # true open ocean
            open_ocean.add((bx, by))
    out = []
    for part in PARTS:
        for (bx, by, bm) in per_part[part]:
            for k in range(bm.vcount):
                v = bm.verts[k]
                bm.verts[k] = (v[0] + BLOCK * bx, v[1], v[2] - BLOCK * by)
            out.append((part, bm))
    covered = from_mod | from_stock | open_ocean
    return out, covered, dict(mod=sorted(from_mod), stock=sorted(from_stock),
                              open_ocean=sorted(open_ocean))


def in_covered(covered, x, z, eps=1e-6):
    """Is (x, z) inside the CLOSED world span of some block that loaded? Closed, because a
    block's mesh reaches its own edge verts -- an edge sample is measured by the block behind
    it, which is why the archived Ashvale/Grimhorn sweeps show 0 miss on their rims."""
    bx0, by0 = math.floor(x / BLOCK), math.floor(-z / BLOCK)
    for bx in (bx0, bx0 - 1):
        for by in (by0, by0 - 1):
            if (bx, by) not in covered:
                continue
            if (BLOCK * bx - eps <= x <= BLOCK * (bx + 1) + eps
                    and -BLOCK * (by + 1) - eps <= z <= -BLOCK * by + eps):
                return True
    return False


def classify(grid, legacy=False):
    """(land, water, miss). THE FIX: MISS is excluded from `water` -- a hole is not sea.
    With the sweep scoped to the island's own blocks (see `sweep_domain`) every MISS the
    ground query returns is a REAL hole in deployed geometry, so `miss` is the census gate:
    it must be 0. `legacy=True` restores the defect (water = complement of land) for A/B."""
    land = {k: v for k, v in grid.items() if v[1] in LAND_MESH and v[0] > 0.25}
    miss = {k for k, v in grid.items() if v[1] == "MISS"}
    if legacy:
        return land, {k for k in grid if k not in land}, miss
    return land, {k for k in grid if k not in land and k not in miss}, miss


def disc_offsets(radius):
    """Lattice offsets within `radius`, nearest first -- so a scan can stop on first hit."""
    n = int(radius // STEP)
    out = [(i * STEP, j * STEP, math.hypot(i * STEP, j * STEP))
           for i in range(-n, n + 1) for j in range(-n, n + 1)]
    out = [t for t in out if 0 < t[2] <= radius]
    out.sort(key=lambda t: t[2])
    return out


DISC = disc_offsets(SEARCH_MAX)


def nearest(px, pz, pts):
    """Distance to the nearest lattice sample of `pts` within SEARCH_MAX, else None."""
    if not pts:
        return None
    for dx, dz, d in DISC:
        if (round(px + dx), round(pz + dz)) in pts:
            return round(d, 2)
    return None


def sweep_domain(blocks, covered, legacy=False):
    """(probe, unmeasured) -- the 4u lattice over the island's bounding box, split into the
    points this probe can actually measure and the ones it cannot.

    THE RE-SCOPE: `probe` is only the lattice inside the CLOSED span of a block that loaded,
    because an island's block list is not a rectangle -- Tidefall's bbox holds 6 blocks
    against a 5-block list, Larkspur's 9 against 6. Sweeping the bbox queried ground no mesh
    was ever loaded for and called the result MISS, which is what let a measurement hole pose
    as sea. Scoped this way the probe never asks a question it cannot answer, and a MISS
    recovers its census meaning. `legacy=True` restores the whole pre-fix bbox sweep."""
    xs = [bx for bx, _ in blocks]
    zs = [by for _, by in blocks]
    x0, x1 = BLOCK * min(xs), BLOCK * (max(xs) + 1)
    z1, z0 = -BLOCK * min(zs), -BLOCK * (max(zs) + 1)
    probe, unmeasured = [], set()
    x = x0
    while x <= x1:
        z = z0
        while z <= z1:
            if legacy or in_covered(covered, x, z):
                probe.append((x, z))
            else:
                unmeasured.add((round(x), round(z)))
            z += STEP
        x += STEP
    return probe, unmeasured


def scan(name, blocks, src=None, legacy=False, stock=True):
    ml, covered, prov = load_world_meshlist(blocks, src, stock)
    xs = [bx for bx, _ in blocks]
    zs = [by for _, by in blocks]
    probe, unmeasured = sweep_domain(blocks, covered, legacy)
    grid = {}
    for (x, z) in probe:
        gy, mesh, idall, topo = P.place(ml, x, z, 0.0, sky=True)
        grid[(round(x), round(z))] = (gy, mesh, topo)
    land, water, miss = classify(grid, legacy)

    cands, n_miss_rejected = [], 0
    for (px, pz), (gy, mesh, topo) in land.items():
        pad = [(px + dx, pz + dz) for dx in (-8, -4, 0, 4, 8) for dz in (-8, -4, 0, 4, 8)]
        padvals = [land.get((round(a), round(b))) for a, b in pad]
        if any(v is None for v in padvals):
            continue                                   # pad not fully land -> not an 8u apron
        ys = [v[0] for v in padvals]
        relief = max(ys) - min(ys)
        if relief > 2.0:
            continue                                   # want a flat apron
        # nearest open water (MISS no longer qualifies -- that was the defect)
        best = 1e9
        for r in range(4, int(SEARCH_MAX), 4):
            ring = [(px + r * math.cos(a * math.pi / 8), pz + r * math.sin(a * math.pi / 8))
                    for a in range(16)]
            if any((round(a / 4) * 4, round(b / 4) * 4) in water for a, b in ring):
                best = r
                break
        if best > WATER_MAX:
            continue
        # a MISS inside the island's own blocks is a real hole in deployed geometry -- one
        # inside the admission envelope disqualifies. UNMEASURED ground does not: it was
        # never queried, and the probe's own blindness is not evidence of a defect.
        # Skipped under `legacy`, which restores the pre-fix probe whole (it had no such test).
        if not legacy:
            miss_d = nearest(px, pz, miss)
            if miss_d is not None and miss_d <= WATER_MAX:
                n_miss_rejected += 1
                continue
        cands.append((round(relief, 2), best, px, pz, round(gy, 2), topo, mesh,
                      nearest(px, pz, unmeasured)))
    # rank: closest to water, then flattest
    cands.sort(key=lambda c: (c[1], c[0]))
    bbox_blocks = set((bx, by) for bx in range(min(xs), max(xs) + 1)
                      for by in range(min(zs), max(zs) + 1))
    return dict(
        sweep="bbox (legacy)" if legacy else "island blocks",
        source_layers="mod overrides over stock" if stock else "mod overrides only",
        blocks=sorted(blocks),
        blocks_covered=sorted(covered),
        blocks_mod=prov["mod"], blocks_stock=prov["stock"],
        blocks_open_ocean=prov["open_ocean"],           # no assets at all -> shared SeaBlockPrefab
        # a DECLARED island block with no override of its own is a data defect, stock or not
        blocks_no_mod_override=sorted(set(blocks) - set(map(tuple, prov["mod"]))),
        blocks_outside_list=sorted(bbox_blocks - set(blocks)),   # in the bbox, not on the list
        n_samples=len(grid), n_land=len(land), n_water=len(water),
        # in "island blocks" scope every MISS is a real hole -- the census gate is n_miss == 0
        n_miss=len(miss), n_miss_rejected=n_miss_rejected,
        n_unmeasured=len(unmeasured),
        # coordinates, not just counts -- the archived run cannot be audited after the fact
        miss_xz=sorted(miss), unmeasured_xz=sorted(unmeasured),
        n_candidates=len(cands),                       # true total; the list below is capped
        candidates=[dict(x=c[2], z=c[3], y=c[4], water_dist=c[1], relief=c[0],
                         topo=c[5], mesh=c[6], unmeasured_dist=c[7]) for c in cands[:400]])


def selftest():
    """Break-it-to-prove-it. Both arms below are silent on the real island set -- there, every
    MISS was an artifact of the bbox sweep and the re-scope removes them all, so `n_miss` is 0
    everywhere and the disqualify path never fires. Exercise them on synthetic input instead."""
    # 1. THE RE-SCOPE. Block (0,0) alone loads; the sweep must query its closed span and
    #    nothing else, so the bbox lattice splits into measured vs never-queried.
    probe, unmeasured = sweep_domain([(0, 0), (1, 0)], {(0, 0)})
    assert (64, -32) in probe, "the shared edge is measured by the block behind it"
    assert (68, -32) not in probe and (68, -32) in unmeasured, "block (1,0) loaded nothing"
    assert not (set(probe) & unmeasured), "a point is measured or not, never both"
    lg_probe, lg_unmeasured = sweep_domain([(0, 0), (1, 0)], {(0, 0)}, legacy=True)
    assert lg_unmeasured == set() and len(lg_probe) == 33 * 17, "legacy sweeps the whole bbox"

    # 2. THE CLASSIFIER. A MISS is a hole, never sea -- and it disqualifies within 24u.
    hole = (32, -32)
    grid = {hole: (0.0, "MISS", None), (16, -16): (3.0, "Terrain", 0),
            (48, -48): (0.0, "Sea4", None)}
    land, water, miss = classify(grid)
    assert miss == {hole} and water == {(48, -48)}, (miss, water)   # NOT the MISS -- the fix
    assert set(land) == {(16, -16)}, land
    assert nearest(28, -32, miss) == 4.0 <= WATER_MAX, "a hole 4u away disqualifies"
    assert nearest(28, -32, water) == 25.61            # hypot(20, 16), the only sea sample
    lg_land, lg_water, lg_miss = classify(grid, legacy=True)
    assert lg_water == {hole, (48, -48)}, lg_water     # the defect, reproduced
    assert lg_miss == {hole}, lg_miss                  # legacy still REPORTS it, as it did
    print("selftest OK -- sweep re-scope + miss-is-not-sea live; legacy reproduces the defect")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=None,
                    help="snapshot dir of .ff9mesh files (default: the live install)")
    ap.add_argument("--legacy-water", action="store_true",
                    help="restore the WHOLE pre-2026-08-27 probe -- mod folder only, bbox sweep, "
                         "MISS counted as water -- so it reproduces the archived run; A/B only")
    ap.add_argument("--no-stock", action="store_true",
                    help="read only the mod folder; do not compose the real game's own block "
                         "assets underneath. Leaves un-overridden ground UNMEASURED.")
    ap.add_argument("--out", default=None, help="output json path (default: the standard one)")
    ap.add_argument("--selftest", action="store_true",
                    help="run the classifier self-test and exit")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return

    stock = not (args.no_stock or args.legacy_water)
    source = ("snapshot:" + str(args.src)) if args.src else "live install"
    print(f"source: {source} + {'stock game assets' if stock else 'NO stock (mod folder only)'}"
          + ("   [LEGACY -- the whole pre-fix probe]" if args.legacy_water else ""))
    report = {"_source": source, "_legacy_water": bool(args.legacy_water), "_stock": stock}
    for name, blocks in ISLANDS.items():
        r = scan(name, blocks, args.src, args.legacy_water, stock)
        report[name] = r
        print(f"\n=== {name}: sweep={r['sweep']} samples={r['n_samples']} "
              f"land={r['n_land']} water={r['n_water']} miss={r['n_miss']} "
              f"unmeasured={r['n_unmeasured']} apron-candidates={r['n_candidates']}"
              + (f" [{r['n_miss_rejected']} rejected on a hole]" if r["n_miss_rejected"] else ""))
        if r["blocks_no_mod_override"]:
            print("    DECLARED island blocks with no override of their own: "
                  f"{r['blocks_no_mod_override']}")
        if r["blocks_stock"] or r["blocks_open_ocean"]:
            print(f"    filled from stock: {r['blocks_stock']}   open ocean (shared "
                  f"SeaBlockPrefab): {r['blocks_open_ocean']}")
        if not args.legacy_water and r["n_miss"]:
            print(f"    !! GATE FAIL -- {r['n_miss']} MISS in measured ground; a miss is a "
                  f"stranding spot / void render. First few: {r['miss_xz'][:6]}")
        if r["n_unmeasured"]:
            print(f"    !! {r['n_unmeasured']} samples UNMEASURED "
                  f"(blocks {r['blocks_outside_list']}) -- run without --no-stock")
        seen = []
        for c in r["candidates"]:
            if all(math.hypot(c["x"] - s["x"], c["z"] - s["z"]) > 40 for s in seen):
                seen.append(c)
                ud = "" if c["unmeasured_dist"] is None else f" unmeasured@{c['unmeasured_dist']}u"
                print(f"   apron ({c['x']:.0f},{c['z']:.0f}) y={c['y']:.2f} topo={c['topo']} "
                      f"mesh={c['mesh']} water@{c['water_dist']}u relief={c['relief']}{ud}")
            if len(seen) >= 6:
                break

    dest = Path(args.out) if args.out else OUT / "design_dock_scan.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("\nwrote", dest)


if __name__ == "__main__":
    main()
