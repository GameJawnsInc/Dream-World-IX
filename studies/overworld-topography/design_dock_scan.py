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

So a MISS here is not a hole in deployed geometry -- it is ground the probe never
measured (an unmodded block; stock ocean, most likely, but the probe does not read
the stock map and cannot claim it). Two very different things wear the same "MISS",
and this probe now separates them:

  * UNCOVERED -- the sample lies outside every block that contributed a mesh.
    Out of measurement scope. Never water, never land, DOES NOT disqualify: the
    probe's own blindness is not evidence of a defect on the ground. Recorded, and
    every admitted candidate carries `uncovered_dist` so a reviewer can see which
    sites were sited next to a blind spot.
  * HOLE -- a MISS INSIDE a block that did load. That is a real hole in deployed
    geometry, and the placement census gate is a hard zero on it ("a miss ANYWHERE
    is a stranding spot (land) or a vehicle wall + void render (water)"). A dock is
    exactly where the boat hull and the landing apron meet, so a hole within the
    24u admission envelope DISQUALIFIES the candidate outright.

The deliberate choice, stated: MISS never counts as water (both classes), but only
the HOLE class disqualifies. Blanket disqualification on any MISS would have thrown
away every Tidefall and Larkspur candidate over an artifact of the bbox sweep, which
is a different wrong answer, not a safer one. In THIS island set every MISS is
UNCOVERED and the hole arm never fires -- `--selftest` exercises it on a synthetic
grid so the arm is not a check that cannot fail.

THE SOURCE SEAM: `--src DIR` points the loader at a snapshot directory instead of
the live install, so a result is reproducible after the shared install drifts (same
law as the deploy-target seam in the brief -- pin the path through a seam, never
read the real file). A snapshot dir holds the files flat; the install nests them
under r<by>/. `--legacy-water` reproduces the pre-fix classification, for A/B only.

--------------------------------------------------------------------------------
RE-RUN VERDICT (2026-08-27, A/B against ONE pinned snapshot of the live install)
--------------------------------------------------------------------------------
`--legacy-water` first, then the fix, same `--src` -- so the diff is the fix alone.
Legacy reproduced the 2026-07-25 archive exactly (Tidefall 561 land / 1056 water /
136 candidates; Larkspur 366 / 2035 / 141; Grimhorn 589 / 1812 / 210; Sandreach 116
/ 973 / 0), so the install had not drifted under these blocks.

THE DEFECT WAS REAL BUT INERT ON THIS DATA. Water drops by exactly the miss count
(Tidefall 1056 -> 800, Larkspur 2035 -> 1267) and NOT ONE candidate moved: 0 added,
0 dropped, 0 water_dist changed, on every island. Falsified directly rather than
inferred -- re-running the admission test against the UNCOVERED samples alone
admits 0 candidates on Tidefall and 0 on Larkspur, so nothing was ever holding a
hole up as its reason to exist. 14 candidates (5 Tidefall, 9 Larkspur) do have an
unmeasured block within 24u, but each also has real sea within 12u; they now carry
`uncovered_dist` so that is visible instead of invisible.

All four dock coordinates grafted into the composed-world design SURVIVE, each
backed by real sea at 12u: (272,-1168) Ashvale, (412,-1224) Tidefall, (1204,-1192)
Grimhorn, (700,-616) Larkspur (uncovered_dist 29.12u). Independently of this probe,
(412,-1224) was already found unbuildable in play -- the ring's R2 moved that
trigger to (420,-1232) because the beacon hull crossed the (6,19)/(6,18) seam
(southern-ring/DESIGN.md:44-45).

NOT FIXED HERE, and worth knowing before trusting a candidate COUNT: the scan sweeps
each island's bounding RECTANGLE, so it measures only what the mod folder overrides
and never reads the stock map. The uncovered blocks are almost certainly stock ocean
-- but "almost certainly" is not a measurement, which is the whole point of the
split above. `n_candidates` is now the true total; the `candidates` list is still
capped at 400 (Ashvale: 562 real, 400 listed -- the archived run recorded only the
capped list, with no total).
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


def load_world_meshlist(blocks, src=None):
    """(meshlist, covered) -- one world-frame meshlist: every part of every block, in
    registration order, verts translated into world coordinates. `covered` is the set of
    (bx, by) that contributed at least one part; anything outside it was never measured."""
    root, flat = mesh_root(src)
    out, covered = [], set()
    for part in PARTS:
        for (bx, by) in blocks:
            name = f"Block[{bx}][{by}] {part}.ff9mesh"
            p = root / name if flat else root / f"r{by}" / name
            if not p.exists():
                continue
            bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, lod="0_1",
                                          part=part.lower())
            for k in range(bm.vcount):
                v = bm.verts[k]
                bm.verts[k] = (v[0] + BLOCK * bx, v[1], v[2] - BLOCK * by)
            out.append((part, bm))
            covered.add((bx, by))
    return out, covered


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


def classify(grid, covered, legacy=False):
    """(land, water, holes, uncovered). THE FIX: MISS is excluded from `water` -- a hole is
    not sea -- and split by whether the sample fell inside a block that actually loaded.
    `legacy=True` restores the defect (water = complement of land) for A/B only."""
    land = {k: v for k, v in grid.items() if v[1] in LAND_MESH and v[0] > 0.25}
    if legacy:
        return land, {k for k in grid if k not in land}, set(), set()
    holes, uncovered = set(), set()
    for k, v in grid.items():
        if v[1] != "MISS":
            continue
        (holes if in_covered(covered, k[0], k[1]) else uncovered).add(k)
    water = {k for k, v in grid.items()
             if k not in land and k not in holes and k not in uncovered}
    return land, water, holes, uncovered


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


def scan(name, blocks, src=None, legacy=False):
    ml, covered = load_world_meshlist(blocks, src)
    xs = [bx for bx, _ in blocks]
    zs = [by for _, by in blocks]
    x0, x1 = BLOCK * min(xs), BLOCK * (max(xs) + 1)
    z1, z0 = -BLOCK * min(zs), -BLOCK * (max(zs) + 1)
    grid = {}
    x = x0
    while x <= x1:
        z = z0
        while z <= z1:
            gy, mesh, idall, topo = P.place(ml, x, z, 0.0, sky=True)
            grid[(round(x), round(z))] = (gy, mesh, topo)
            z += STEP
        x += STEP
    land, water, holes, uncovered = classify(grid, covered, legacy)

    cands, n_hole_rejected = [], 0
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
        # a real hole in deployed geometry inside the admission envelope disqualifies;
        # an unmeasured block does not -- it is only recorded.
        hole_d = nearest(px, pz, holes)
        if hole_d is not None and hole_d <= WATER_MAX:
            n_hole_rejected += 1
            continue
        cands.append((round(relief, 2), best, px, pz, round(gy, 2), topo, mesh,
                      nearest(px, pz, uncovered)))
    # rank: closest to water, then flattest
    cands.sort(key=lambda c: (c[1], c[0]))
    bbox_blocks = set((bx, by) for bx in range(min(xs), max(xs) + 1)
                      for by in range(min(zs), max(zs) + 1))
    return dict(
        blocks=sorted(blocks),
        blocks_covered=sorted(covered),
        blocks_uncovered=sorted(bbox_blocks - covered),
        n_samples=len(grid), n_land=len(land), n_water=len(water),
        n_miss=len(holes) + len(uncovered), n_hole=len(holes), n_uncovered=len(uncovered),
        n_hole_rejected=n_hole_rejected,
        # coordinates, not just counts -- the archived run cannot be audited after the fact
        hole_xz=sorted(holes), uncovered_xz=sorted(uncovered),
        n_candidates=len(cands),                       # true total; the list below is capped
        candidates=[dict(x=c[2], z=c[3], y=c[4], water_dist=c[1], relief=c[0],
                         topo=c[5], mesh=c[6], uncovered_dist=c[7]) for c in cands[:400]])


def selftest():
    """Exercise the HOLE arm, which never fires on the real island set (every MISS there is
    UNCOVERED). Break-it-to-prove-it: a synthetic MISS inside a covered block must classify
    as a hole, the same sample outside every covered block must classify as uncovered, and
    neither may reach `water`."""
    covered = {(0, 0)}
    inside, outside = (32, -32), (96, -32)             # block (0,0) spans x[0,64] z[-64,0]
    grid = {inside: (0.0, "MISS", None), outside: (0.0, "MISS", None),
            (16, -16): (3.0, "Terrain", 0), (48, -48): (0.0, "Sea4", None)}
    land, water, holes, uncovered = classify(grid, covered)
    assert holes == {inside}, holes
    assert uncovered == {outside}, uncovered
    assert water == {(48, -48)}, water                 # and NOT either MISS -- the fix
    assert set(land) == {(16, -16)}, land
    assert nearest(28, -32, holes) == 4.0              # the disc scan sees a hole
    assert nearest(28, -32, water) == 25.61            # hypot(20, 16), the only sea sample
    lg_land, lg_water, lg_h, lg_u = classify(grid, covered, legacy=True)
    assert lg_water == {inside, outside, (48, -48)}, lg_water   # the defect, reproduced
    assert (lg_h, lg_u) == (set(), set())
    print("selftest OK -- hole/uncovered split live; legacy water reproduces the defect")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=None,
                    help="snapshot dir of .ff9mesh files (default: the live install)")
    ap.add_argument("--legacy-water", action="store_true",
                    help="reproduce the pre-2026-08-27 defect (MISS counted as water); A/B only")
    ap.add_argument("--out", default=None, help="output json path (default: the standard one)")
    ap.add_argument("--selftest", action="store_true",
                    help="run the classifier self-test and exit")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return

    source = ("snapshot:" + str(args.src)) if args.src else "live install"
    print("source: " + source
          + ("   [LEGACY WATER -- MISS counted as water]" if args.legacy_water else ""))
    report = {"_source": source, "_legacy_water": bool(args.legacy_water)}
    for name, blocks in ISLANDS.items():
        r = scan(name, blocks, args.src, args.legacy_water)
        report[name] = r
        print(f"\n=== {name}: land={r['n_land']} water={r['n_water']} miss={r['n_miss']} "
              f"(hole={r['n_hole']} uncovered={r['n_uncovered']}) "
              f"apron-candidates={r['n_candidates']}"
              + (f" [{r['n_hole_rejected']} rejected on a hole]" if r["n_hole_rejected"] else ""))
        if r["blocks_uncovered"]:
            print("    !! bbox blocks with NO mesh loaded (never measured): "
                  f"{r['blocks_uncovered']}")
        seen = []
        for c in r["candidates"]:
            if all(math.hypot(c["x"] - s["x"], c["z"] - s["z"]) > 40 for s in seen):
                seen.append(c)
                ud = "" if c["uncovered_dist"] is None else f" unmeasured@{c['uncovered_dist']}u"
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
