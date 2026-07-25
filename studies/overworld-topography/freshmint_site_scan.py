"""THE FRESH-SITE SCAN for THE GENERATOR FOLD-BACK proof (2026-07-25).

Finds an all-ocean site for an r132-class two-ground landmass that is clear of
  (a) every STOCK land vertex (wrap-aware clearance, the rung_f_fit_sweep2 kernel, lifted verbatim),
  (b) every LIVE-DEPLOYED block in <game>/FF9CustomMap-world  -- read-only, at BLOCK granularity
      (a deployed block that happens to be all-sea still counts as occupied: we must not overwrite it),
  (c) the x-wrap seam (the whole footprint stays inside [0,1536), build_landmass REFUSES col<0),
  (d) the north/south grid edges (z in (0,-1280)).

The site is scored on OFF-SEAM CLEARANCE RADIUS and, among ties, on distance from the rung-F
footprint.  Emits out/foldback/freshmint_site.json.  READ-ONLY: X.read_block + a filename scan of the
live tree.  NEVER writes the install.

    py -X utf8 freshmint_site_scan.py
"""
from __future__ import annotations

import glob
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import island as ISL         # noqa: E402
from ff9mapkit.world import mesh as M             # noqa: E402

LIVE = Path("C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world")
BLOCK = 64.0
NX, NZ = 24, 20                 # the grid: x wraps, z does not
WORLD_W = BLOCK * NX            # 1536
WORLD_H = BLOCK * NZ            # 1280
LAND_Y = 0.6
R_TARGET = 132.0                # the r132 class (MEC 71.4 + realized 50 + wander ~8)
R_ISLAND = 125.0                # what the mint actually asks build_landmass for (rung-F's own value)

# benches / footprints named in the study that must be avoided regardless of what is on disk today
NAMED_BENCH_BLOCKS = {
    # rung F (the accepted two-ground island) + its declared site rect
    *[(bx, by) for bx in range(0, 5) for by in range(15, 20)],
    # first-continent archipelago + waystation region, dunes/desert benches quoted in the study
    (6, 18), (6, 19), (7, 18), (7, 19), (8, 19),
    (9, 9), (10, 8), (10, 9), (10, 10), (11, 8), (11, 9),
    (11, 18), (11, 19), (12, 18), (12, 19),
    (18, 17), (18, 18), (18, 19), (19, 17), (19, 18), (19, 19),
    (20, 17), (20, 18), (20, 19),
    # the donor junction read window (Cleyra 13-15,11-12 + read margin) -- never mint on the donor
    *[(bx, by) for bx in range(12, 17) for by in range(10, 14)],
    # the stock dunes mass used as the envelope calibration reference
    (18, 3), (19, 3), (20, 3),
}


def live_blocks():
    """Every block the live FF9CustomMap-world tree writes, either disc, any part."""
    blocks = set()
    pat = re.compile(r"Block\[(\d+)\]\[(\d+)\]")
    for f in glob.glob(str(LIVE / "**" / "Block*"), recursive=True):
        m = pat.search(Path(f).name)
        if m:
            blocks.add((int(m.group(1)), int(m.group(2))))
    return blocks


def gather_stock(game):
    """ONE pass over the whole 24x20 grid: land verts (for the clearance kernel) AND per-block
    PREFAB OCCUPANCY (``island._real_block_parts``).  THE OPEN-OCEAN TARGET LAW is block-granular and
    strictly stronger than a land-vertex clearance -- a stock block can carry a submerged ``terrain``
    or a sea-only prefab with NO land vertex at all and still be un-overridable.  Caches to
    out/foldback/stock_grid.json (the install is shared mutable state; the cache is ours)."""
    cache = HERE / "out" / "foldback" / "stock_grid.json"
    if cache.exists():
        d = json.loads(cache.read_text())
        return ([tuple(p) for p in d["land"]],
                {tuple(map(int, k.split(","))): v for k, v in d["occ"].items()})
    land, occ = [], {}
    for by in range(NZ):
        for bx in range(NX):
            p = ISL._real_block_parts((bx, by), disc=1, lod="0_1", game=game)
            if p:
                occ[(bx, by)] = p
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except Exception:
                continue
            ox, oz = X.block_world_origin(bx, by)
            for v in bm.verts:
                if v[1] > LAND_Y:
                    land.append((v[0] + ox, v[2] + oz))
        print(f"  scanned row by={by}", flush=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dict(land=[list(p) for p in land],
                                     occ={f"{k[0]},{k[1]}": v for k, v in occ.items()})))
    return land, occ


def gather_live_land(blocks):
    land = []
    for (bx, by) in sorted(blocks):
        try:
            rel = M.override_relpath(1, bx, by, part="Terrain")
            bm = M.blockmesh_from_ff9mesh(LIVE / rel, disc=1, x=bx, y=by, part="terrain")
        except Exception:
            continue
        ox, oz = X.block_world_origin(bx, by)
        for v in bm.verts:
            if v[1] > LAND_Y:
                land.append((v[0] + ox, v[2] + oz))
    return land


def footprint_blocks(cx, cz, r):
    """Blocks a disc of radius r at (cx,cz) can touch (x wraps, z does not)."""
    out = set()
    for bx in range(NX):
        for by in range(NZ):
            x0, x1 = BLOCK * bx, BLOCK * (bx + 1)
            z1, z0 = -BLOCK * by, -BLOCK * (by + 1)      # z0 < z1
            dx = 0.0
            if cx < x0 or cx > x1:
                d = min(abs(cx - x0), abs(cx - x1),
                        abs(cx - x0 + WORLD_W), abs(cx - x1 + WORLD_W),
                        abs(cx - x0 - WORLD_W), abs(cx - x1 - WORLD_W))
                dx = d
            dz = 0.0 if z0 <= cz <= z1 else min(abs(cz - z0), abs(cz - z1))
            if math.hypot(dx, dz) <= r:
                out.add((bx, by))
    return out


def main():
    from ff9mapkit import config as _cfg
    game = _cfg.find_game_path(None)
    stock, stock_occ = gather_stock(game)
    # THE OPEN-OCEAN TARGET LAW, block-granular: a stock block that loads its OWN prefab can never be
    # a mint target (a sea-only prefab has no Terrain transform for the loose override to bind to --
    # the (6,17) canvas incident).  This is the gate compose() re-checks at ACTION time as S0.
    forbidden = live_blocks() | NAMED_BENCH_BLOCKS | set(stock_occ)
    print(f"stock prefab-occupied blocks {len(stock_occ)}")
    live = gather_live_land(live_blocks())
    print(f"live-occupied blocks {len(live_blocks())}; forbidden (live + named benches) {len(forbidden)}")
    print(f"stock land verts {len(stock)}  live land verts {len(live)}")
    land = stock + live
    uniq = {(round(lx / 2.0) * 2.0, round(lz / 2.0) * 2.0) for (lx, lz) in land}
    LX = np.array([p[0] for p in uniq])
    LZ = np.array([p[1] for p in uniq])
    print(f"unique 2u land points {len(uniq)}")

    # forbidden-block clearance: distance from a candidate centre to the nearest forbidden block RECT
    fb = sorted(forbidden)
    soft_fb = sorted(live_blocks() | NAMED_BENCH_BLOCKS)     # deployed/bench -- want REAL separation

    def fb_clear(cx, cz, which=None):
        best = 1e9
        for (bx, by) in (which if which is not None else fb):
            x0, x1 = BLOCK * bx, BLOCK * (bx + 1)
            z1, z0 = -BLOCK * by, -BLOCK * (by + 1)
            if x0 <= cx <= x1:
                dx = 0.0
            else:
                dx = min(abs(cx - x0), abs(cx - x1),
                         abs(cx - x0 + WORLD_W), abs(cx - x1 + WORLD_W),
                         abs(cx - x0 - WORLD_W), abs(cx - x1 - WORLD_W))
            dz = 0.0 if z0 <= cz <= z1 else min(abs(cz - z0), abs(cz - z1))
            best = min(best, math.hypot(dx, dz))
            if best <= 0.0:
                return 0.0
        return best

    # THE ACHIEVABLE-CENTRE LATTICE.  rung_f_layout:113 -- "SHIFT_CELLS=(-192,-96) = the WHOLE-BLOCK
    # shift ... THE ROOT-CAUSE FIX (build-fix round 4): a whole-block shift on BOTH axes maps the 6
    # donor blocks onto 6 target blocks with ZERO re-partition ... a phase shift instead re-partitions
    # every border tri, minting hundreds of un-weldable T-junctions -> the cascade."  So the shift is
    # constrained to a multiple of BLOCK=64u, NOT merely of CELL=4u.  The donor blob's own pre-shift
    # centre is (928, -768) (kept region 192x128u), and the rung-F build seated the island centre ON
    # the blob centre, so shift_world = (cx-928, cz+768) and a legal centre satisfies
    #     cx == 928 (mod 64) == 32 (mod 64)      and      cz == -768 (mod 64) == 0 (mod 64).
    # rung-F's own (160,-1152) is on this lattice (160%64=32, -1152%64=0) -- the check that it is the
    # right lattice and not an invented one.
    cxs = np.arange(32.0, WORLD_W, 64.0)
    czs = np.arange(-64.0, -WORLD_H, -64.0)
    # THE MAX-RADIUS SWEEP.  For every lattice centre compute the LARGEST island radius that keeps
    # (a) the written-block footprint disjoint from every forbidden block, (b) the land clearance,
    # (c) the off-seam cap, (d) the grid-edge cap.  A whole-block-lattice centre is coarse (64u), so
    # the radius -- not the position -- is what has to give once rung-F occupies the world's single
    # largest true-ocean circle.
    FP_PAD = 8.0                     # the coast wanders +-undulation; 8u covers it at r<=132

    def max_radius(cx, cz, clr, edge, cap):
        r = min(clr, edge, cap)
        while r >= 40.0:
            if not (footprint_blocks(cx, cz, r + FP_PAD) & forbidden):
                return r
            r -= 4.0
        return 0.0

    rows = []
    for cx in cxs:
        dx = cx - LX
        dx = dx - WORLD_W * np.round(dx / WORLD_W)
        dx2 = dx * dx
        offseam_cap = min(cx, WORLD_W - cx)
        for cz in czs:
            edge = min(abs(cz), abs(-WORLD_H - cz))
            clr = math.sqrt(float(np.min(dx2 + (cz - LZ) ** 2)))
            rmax = max_radius(float(cx), float(cz), clr, edge, offseam_cap)
            if rmax < 40.0:
                continue
            fc = fb_clear(float(cx), float(cz), soft_fb)      # separation from DEPLOYED/bench content
            rows.append((float(cx), float(cz), clr, edge, offseam_cap, fc, rmax))

    rows.sort(key=lambda r: (-r[6], -r[5]))
    print(f"whole-block-lattice centres with a legal island radius >= 40u: {len(rows)}")
    for r in rows[:15]:
        print(f"  cx={r[0]:7.1f} cz={r[1]:8.1f} Rmax={r[6]:6.1f} stock_clr={r[2]:7.2f} "
              f"edge={r[3]:6.1f} offseam={r[4]:6.1f} deployed_clr={r[5]:7.1f}")
    if not rows:
        print("NO CANDIDATE")
        return 1
    # commit to the largest legal radius on the winning centre
    globals()["R_ISLAND"] = rows[0][6]
    rows = [r[:6] for r in rows if r[6] >= rows[0][6] - 1e-9]

    # score: maximise min(stock clearance, bench clearance, edge, offseam cap); tie-break on
    # distance from the rung-F island centre (want a genuinely DIFFERENT part of the ocean)
    RFX, RFZ = 160.0, -1152.0

    def score(r):
        cx, cz, clr, edge, cap, fc = r
        m = min(clr, edge, cap, fc)
        d = math.hypot(min(abs(cx - RFX), WORLD_W - abs(cx - RFX)), cz - RFZ)
        return (round(m, 1), round(d, 1))

    rows.sort(key=score, reverse=True)
    top = rows[:25]
    for r in top[:12]:
        cx, cz, clr, edge, cap, fc = r
        print(f"  cx={cx:7.1f} cz={cz:8.1f} stock_clr={clr:7.2f} edge={edge:7.1f} "
              f"offseam_cap={cap:7.1f} bench_clr={fc:7.1f}  min={min(clr, edge, cap, fc):7.2f}")

    # pick the winner, prefer a BLOCK-ALIGNED-centre-of-a-block-boundary style centre if one is
    # within 0.5u of the best score (cosmetic: keeps the site rect tidy)
    best = top[0]
    bs = score(best)
    tidy = [r for r in top if score(r)[0] >= bs[0] - 0.001
            and abs(r[0] % 32.0) < 1e-6 and abs(r[1] % 32.0) < 1e-6]
    chosen = tidy[0] if tidy else best
    cx, cz, clr, edge, cap, fc = chosen
    fp = footprint_blocks(cx, cz, R_ISLAND + 8.0)
    site_rect = sorted(fp)
    bxs = sorted({b[0] for b in fp})
    bys = sorted({b[1] for b in fp})
    rect = {(bx, by) for bx in range(min(bxs), max(bxs) + 1) for by in range(min(bys), max(bys) + 1)}
    collide = sorted(rect & forbidden)

    # THE SHIFT: place the donor window's centre on the island centre.  The rung-F build seated the
    # donor blob at (island_center + (0,-2)); shift_world = (cx-928, cz+768) reproduces that offset
    # exactly, and both components are integer multiples of CELL=4 for a 4u-aligned centre.
    shift_world = (cx - 928.0, cz + 768.0)
    shift_cells = (int(round(shift_world[0] / 4.0)), int(round(shift_world[1] / 4.0)))
    assert abs(shift_cells[0] * 4.0 - shift_world[0]) < 1e-6, shift_world
    assert abs(shift_cells[1] * 4.0 - shift_world[1]) < 1e-6, shift_world
    # THE WHOLE-BLOCK SHIFT LAW (rung_f_layout:113): both components must be whole blocks.
    assert shift_cells[0] % 16 == 0 and shift_cells[1] % 16 == 0, shift_cells

    out = dict(
        method=("4u-aligned continuous sweep (rung_f_fit_sweep2 kernel); wrap-aware clearance to "
                "stock+live LAND verts; BLOCK-granular clearance to every live-deployed block and "
                "every bench named in the study; off-seam cap min(cx,1536-cx); grid edges z in "
                "(0,-1280)."),
        r_target=R_TARGET, r_island=R_ISLAND,
        n_stock_land=len(stock), n_live_land=len(live), n_unique_land_2u=len(uniq),
        live_blocks=[list(b) for b in sorted(live_blocks())],
        forbidden_blocks=[list(b) for b in sorted(forbidden)],
        n_candidates=len(rows),
        top=[dict(cx=r[0], cz=r[1], stock_clearance=round(r[2], 2), edge=round(r[3], 1),
                  offseam_cap=round(r[4], 1), bench_clearance=round(r[5], 1),
                  min_clearance=round(min(r[2], r[3], r[4], r[5]), 2)) for r in top],
        chosen=dict(cx=cx, cz=cz, stock_clearance=round(clr, 2), edge=round(edge, 1),
                    offseam_cap=round(cap, 1), bench_clearance=round(fc, 1),
                    min_clearance=round(min(clr, edge, cap, fc), 2)),
        footprint_blocks=[list(b) for b in site_rect],
        site_rect=[list(b) for b in sorted(rect)],
        site_rect_bx=[min(bxs), max(bxs)], site_rect_by=[min(bys), max(bys)],
        collisions_with_forbidden=[list(b) for b in collide],
        shift_world=list(shift_world), shift_cells=list(shift_cells),
        rung_f_center=[RFX, RFZ],
        distance_from_rung_f=round(math.hypot(min(abs(cx - RFX), WORLD_W - abs(cx - RFX)), cz - RFZ), 1),
    )
    d = HERE / "out" / "foldback"
    d.mkdir(parents=True, exist_ok=True)
    (d / "freshmint_site.json").write_text(json.dumps(out, indent=1))
    print("\nCHOSEN SITE:", out["chosen"])
    print("site rect blocks:", out["site_rect_bx"], out["site_rect_by"], f"({len(rect)} blocks)")
    print("touched footprint blocks:", len(site_rect))
    print("collisions with forbidden:", collide)
    print("shift_cells:", shift_cells)
    print("wrote out/foldback/freshmint_site.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
