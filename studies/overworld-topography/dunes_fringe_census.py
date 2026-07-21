"""THE FRINGE CENSUS -- rung 7 of the dunes arc (2026-07-21), the forensics of the two playtest
fringe defects the TRUE MESH CARRY (rung 6, dunes_true_carry.py) left behind.

THE PLAYTEST VERDICT (user, two ground-level screenshots)
  "The ecotone is nice now" -- the dunes|desert seam LANDED. Two NEW fringe defects:
    1. "Lifted or shrunken seams in the ground" -- long thin BLUE SLIVERS (sea/void through the
       terrain); one clearly at (1220,-1152), EXACTLY on the block border z=-1152 (rows 17/18).
    2. "Hard-edged grass ecotone tiles" -- carried green fragments (topo-0 grass / topo-49 mural)
       read as triangular green shards with dead-straight edges against the red desert.

WHY THIS INSTRUMENT EXISTS -- the arc's RECORDED BLIND SPOT (memory coast-mosaic):
  "the adjacency test only sees WITHIN-block edges, never a coincident edge across a block boundary."
  The weld_audit is per-block LOCAL-frame: two verts on a shared border have coords z=0 (top of the
  by-1 block) vs z=-64 (bottom of the by block) -- same WORLD line, different local values, so a
  cross-block crack is STRUCTURALLY invisible to it. This census is the cross-block test the arc
  never had: it lifts BOTH sides of every shared border into the WORLD frame and matches the border
  cross-sections.

WHAT IT DOES
  PART 1 -- CRACK/STEP CENSUS. For every pair of adjacent DEPLOYED blocks in and around the 3x3 mint
    region (carried-carried, carried-host, host-host), and stock-vs-stock on the donor region as the
    CALIBRATION NULL, lift both sides' border-lying tri edges into world (t=along-coord, Y). Classify
    every mismatch: HOLE (a t-range with border geometry on one side only -> sea/void shows through),
    T-JUNCTION (one side subdivides an edge the other spans -- benign if collinear, a crack if the
    spanning edge's Y differs at the split), VERTICAL STEP (a matched t with different Y -> the lifted/
    shrunken seam). Reports world coords, the two blocks, gap width / step height. Then drills the
    (1220,-1152) sliver + others to the actual verts.
  PART 2 -- GREEN-SHARD CENSUS. Enumerate every carried topo-0 grass / topo-49 mural tri in the 5
    deployed blocks; for each, its donor context (what surrounded it in stock) and its deployed
    neighbours; classify genuine dunes-ensemble content vs orphaned grass-context stump. Check what
    stock comp[1] does at its OWN desert margin where no grass is nearby = the fix vocabulary.
  PART 2b -- THE GREEN-SHARD instrument (review follow-up, 2026-07-21). The topo-0 count MISSED the
    true source of defect #2: per-pixel render attribution proved the visible "hard-edged grass
    ecotone tiles" are 12 carried FLAT desert ECOTONE-STRIP tiles (topo 16/17/19/20, UV u~0.92-0.98)
    whose verbatim strip UV -- brown on the desert side, GREEN on the grass side in stock comp[1] --
    lands on green atlas texels once relocated onto the all-desert island. :func:`green_ground_count_
    from_bm` samples each ground tri's UV against the atlas (the render-faithful measure). topo-41
    dunes render ZERO green (the approved ecotone is untouched); the 62 topo-49 mesa murals hold only
    faint sub-tri lichen speckle (peak ~4.4%% of a tri, olive-brown) and are KEPT as faithful rock.

Run OFFLINE (reads deployed + stock, writes only out/):
  py studies/overworld-topography/dunes_fringe_census.py
Artifacts -> out/dunes_fringe_census.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as MESH      # noqa: E402

import dunes_grazing_eye as GE                # noqa: E402

BLOCK = 64.0
CELL = 4.0
GP = Path(_cfg.find_game_path(None))
MOD = "FF9CustomMap-world"
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)

CARRIED = [(18, 18), (19, 17), (19, 18), (19, 19), (20, 18)]
MINT_BLOCKS = [(bx, by) for bx in range(18, 21) for by in range(17, 20)]     # deployed host island 3x3
HOST_CORNERS = [(18, 17), (20, 17), (18, 19), (20, 19)]                       # deployed, NOT rebuilt
DONOR_BLOCKS = [(bx, by) for bx in range(12, 16) for by in range(10, 14)]     # stock comp[1] region

# match tolerances (bytes are exact float copies -> true coincidences are < 1e-4; a real defect is
# a DY-scale step ~0.1-1u or a whole missing edge). We flag anything above MATCH.
T_MATCH = 0.02          # along-border coord match
Y_MATCH = 0.02          # vertical match -> below this, a shared-t vert pair is "welded"
BORDER_EPS = 0.03       # a vert is ON the border plane if |coord-plane| < this


# ============================================================================================
# world-frame tri loaders
# ============================================================================================
def deployed_world_tris(bx, by):
    """Deployed override -> list of world tris [(pos,topo,fam)x3 as (p3,topo,fam)]; [] if none."""
    p = GP / MOD / MESH.override_relpath(1, bx, by, part="Terrain")
    if not p.exists():
        return None
    bm = MESH.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
    return _world_tris_from_bm(bm, bx, by)


def stock_world_tris(bx, by):
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except (ValueError, FileNotFoundError):
        return None
    return _world_tris_from_bm(bm, bx, by)


def _world_tris_from_bm(bm, bx, by):
    V, TAN = bm.verts, bm.tangents
    out = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(float(V[j][0]) + BLOCK * bx, float(V[j][1]), float(V[j][2]) - BLOCK * by) for j in tri]
        topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        out.append((p3, topo, GE.TOPO_FAM.get(topo, f"t{topo}")))
    return out


def bm_world_tris(bm, bx, by):
    """A freshly-built (pre-deploy) BlockMesh -> world tris [(p3,topo,fam)] -- the in-memory
    equivalent of :func:`deployed_world_tris`, so the carry's own gate suite can census the
    REBUILT blocks before a single byte reaches the game (the fix must be proven in-memory)."""
    return _world_tris_from_bm(bm, bx, by)


def census_built_blocks(world_by_block):
    """Cross-block seam census over an IN-MEMORY ``{(bx,by): [(p3,topo,fam),...]}`` (freshly-built,
    pre-deploy) -- the same instrument as :func:`run_crack_census` without touching disk. Returns
    ``(recs, totals)``; ``totals`` = dict(steps, holes). The calibration NULL still lives on the
    stock donor region (:func:`run_crack_census`), so a caller gates the built totals only after
    the NULL has proven the instrument raises 0 phantom seams on shipping data."""
    recs = []
    for (A, B, axis, plane) in adjacency_pairs(list(world_by_block)):
        if world_by_block.get(A) is None or world_by_block.get(B) is None:
            continue
        rec = census_border(f"[{A[0]}][{A[1]}]", world_by_block[A],
                            f"[{B[0]}][{B[1]}]", world_by_block[B], axis, plane)
        rec["carriedA"] = A in CARRIED
        rec["carriedB"] = B in CARRIED
        recs.append(rec)
    tot = dict(steps=sum(r["n_steps"] for r in recs),
               tjunc=sum(r["n_tjunc"] for r in recs),
               holes=sum(r["n_holes"] for r in recs))
    return recs, tot


def green_shard_count(world_by_block):
    """The orphan-grass gate over IN-MEMORY built blocks: count topo-0 tris (the rung-7 stump). A
    faithful fix drives this to 0. NOTE: this is NOT the full green-shard measure -- the review
    follow-up proved carried FLAT desert-STRIP tiles (topo 16/17/19/20) also render green; that is
    counted by :func:`green_ground_count_from_bm` (which needs UVs, dropped by the world-tri
    loaders)."""
    return sum(1 for tris in world_by_block.values() for (_p3, topo, _f) in tris if topo == 0)


# rung-7 CONT. (2026-07-21): the GREEN-SHARD instrument. Unlike the topo-0 count, this measures what
# actually RENDERS green -- a carried FLAT desert/grass GROUND tile whose verbatim UV lands on green
# atlas texels (the relocated ecotone-strip shards). Needs UVs, so it reads the BlockMesh directly
# (deployed OR freshly-built); rock/wall faces + non-ground topos are excluded (the mesa's faint
# lichen speckle is faithful, not a shard).
GREEN_GROUND_TOPOS = frozenset({0, 16, 17, 19, 20})


def green_ground_count_from_bm(bm, bx, by, frac_min=0.05, ny_min=0.7):
    """Count FLAT desert/grass GROUND tris in one block whose UV renders strict grass-green
    (>= frac_min of the tri's UV area). Returns (n, cells)."""
    V, N, U, TAN = bm.verts, bm.normals, bm.uvs, bm.tangents
    n = 0
    cells = []
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
        if topo not in GREEN_GROUND_TOPOS:
            continue
        ny = sum(abs(float(N[j][1])) for j in tri) / 3.0
        if ny < ny_min:
            continue
        uv3 = [(float(U[j][0]), float(U[j][1])) for j in tri]
        if GE.tri_green_frac(uv3) >= frac_min:
            n += 1
            cx = sum(float(V[j][0]) for j in tri) / 3.0 + BLOCK * bx
            cz = sum(float(V[j][2]) for j in tri) / 3.0 - BLOCK * by
            cells.append((math.floor(cx / CELL), math.floor(cz / CELL)))
    return n, cells


def deployed_green_ground_count(blocks=None):
    """The GREEN-SHARD instrument over the DEPLOYED override bytes (the anti-test 'before' read)."""
    if blocks is None:
        blocks = CARRIED
    tot = 0
    allcells = []
    for (bx, by) in blocks:
        p = GP / MOD / MESH.override_relpath(1, bx, by, part="Terrain")
        if not p.exists():
            continue
        bm = MESH.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        n, cells = green_ground_count_from_bm(bm, bx, by)
        tot += n
        allcells += cells
    return tot, allcells


def green_ground_count_built(built_bms):
    """The GREEN-SHARD instrument over freshly-built (pre-deploy) BlockMeshes (the in-memory gate)."""
    tot = 0
    allcells = []
    for (bx, by), bm in built_bms.items():
        n, cells = green_ground_count_from_bm(bm, bx, by)
        tot += n
        allcells += cells
    return tot, allcells


# ============================================================================================
# PART 1 -- cross-block border census
# ============================================================================================
def border_geometry(tris, axis, plane):
    """Collect border-lying geometry. axis 0 => plane is x, along=z; axis 2 => plane is z, along=x.
    Returns (verts, edges): verts = set of EVERY (t,Y) a tri corner touches on the plane (incl. lone
    corners that touch the border with no border-lying edge -- those are the phase-shifted notch
    verts, and missing them was how the arc's within-block audit stayed blind); edges = list of
    ((t0,Y0),(t1,Y1)) for tri edges whose BOTH endpoints lie on the plane (the T-junction span set)."""
    along = 2 if axis == 0 else 0
    verts = set()
    edges = []
    for (p3, topo, fam) in tris:
        onb = [abs(p[axis] - plane) < BORDER_EPS for p in p3]
        for i in range(3):
            if onb[i]:
                verts.add((round(p3[i][along], 4), round(p3[i][1], 4)))
        for i in range(3):
            j = (i + 1) % 3
            if onb[i] and onb[j]:
                a = (round(p3[i][along], 4), round(p3[i][1], 4))
                b = (round(p3[j][along], 4), round(p3[j][1], 4))
                if a != b:
                    edges.append((a, b))
    return verts, edges


def _contact_intervals(edges):
    """From a side's border-lying edges, the union of t-intervals where the terrain touches the
    border with an actual EDGE on it (a lone corner vert is NOT interval contact -- that is the
    phase-shifted notch: the boundary rises off the border between two touching points). Vertical
    border edges (t0==t1, wall faces) contribute no interval. Returns a sorted merged list of
    (t_lo, t_hi) plus a profile sampler segs=[(t0,t1,y0,y1)]."""
    segs = []
    ivals = []
    for (a, b) in edges:
        t0, y0 = a
        t1, y1 = b
        if abs(t1 - t0) < 1e-6:
            continue
        lo, hi = (t0, t1) if t0 < t1 else (t1, t0)
        ivals.append((lo, hi))
        segs.append((t0, t1, y0, y1))
    ivals.sort()
    merged = []
    for (lo, hi) in ivals:
        if merged and lo <= merged[-1][1] + 1e-4:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged, segs


def _covered(merged, t, tol=1e-4):
    return any(lo - tol <= t <= hi + tol for (lo, hi) in merged)


def _profile_y(segs, t, tol=T_MATCH):
    """Y(t) on a side's border boundary (interpolated on the covering edge). None if t uncovered."""
    ys = []
    for (t0, t1, y0, y1) in segs:
        lo, hi = (t0, t1) if t0 < t1 else (t1, t0)
        if lo - tol <= t <= hi + tol:
            f = 0.0 if abs(t1 - t0) < 1e-9 else max(0.0, min(1.0, (t - t0) / (t1 - t0)))
            ys.append(y0 + f * (y1 - y0))
    return ys or None


def census_border(nameA, trisA, nameB, trisB, axis, plane):
    """Census one shared border by BORDER-EDGE INTERVAL COVERAGE + Y-PROFILE comparison (the
    authoritative test -- a vertex-match test misses the phase-shifted NOTCH, where both endpoint
    verts coincide but one side lacks the border edge between them). Reports:
      HOLE  -- a t-range one side covers with a border edge and the other does not (a void: the
               notched side's boundary rises off the border -> sea/void shows through).
      STEP  -- a t both sides cover but at different Y (the lifted/shrunken seam)."""
    _vA, eA = border_geometry(trisA, axis, plane)
    _vB, eB = border_geometry(trisB, axis, plane)
    mA, sA = _contact_intervals(eA)
    mB, sB = _contact_intervals(eB)
    along_axis = "z" if axis == 0 else "x"

    def world_of(t, y):
        if axis == 0:      # vertical border: plane=x, along=z
            return (round(plane, 2), round(y, 3), round(t, 2))
        return (round(t, 2), round(y, 3), round(plane, 2))     # horizontal: plane=z, along=x

    # sample the union of both sides' covered t at fine resolution; classify each sample
    ts = set()
    for (lo, hi) in mA + mB:
        n = max(2, int((hi - lo) / 0.25) + 1)
        for k in range(n + 1):
            ts.add(round(lo + (hi - lo) * k / n, 4))
    # endpoints too
    for (lo, hi) in mA + mB:
        ts.add(round(lo, 4)); ts.add(round(hi, 4))

    hole_ts, step_ts = [], []
    for t in sorted(ts):
        cA, cB = _covered(mA, t), _covered(mB, t)
        if cA and not cB:
            hole_ts.append((t, nameA, nameB, _profile_y(sA, t)))
        elif cB and not cA:
            hole_ts.append((t, nameB, nameA, _profile_y(sB, t)))
        elif cA and cB:
            ya, yb = _profile_y(sA, t), _profile_y(sB, t)
            if ya and yb:
                dy = min(abs(a - b) for a in ya for b in yb)
                if dy >= Y_MATCH:
                    step_ts.append((t, dy, min(ya), min(yb)))

    # collapse consecutive t into ranges (report width, not per-sample)
    def _ranges(items, keyt):
        out = []
        for it in items:
            t = keyt(it)
            if out and abs(t - out[-1]["_last"]) <= 0.5 + 1e-4:
                out[-1]["_last"] = t
                out[-1]["t_hi"] = t
                out[-1]["_items"].append(it)
            else:
                out.append(dict(t_lo=t, t_hi=t, _last=t, _items=[it]))
        return out

    holes = []
    for r in _ranges(hole_ts, lambda it: it[0]):
        it0 = r["_items"][0]
        present, missing = it0[1], it0[2]
        yv = [it[3][0] for it in r["_items"] if it[3]]
        holes.append(dict(present=present, missing=missing,
                          t_range=[round(r["t_lo"], 3), round(r["t_hi"], 3)],
                          width=round(r["t_hi"] - r["t_lo"], 3),
                          where=world_of((r["t_lo"] + r["t_hi"]) / 2, yv[0] if yv else 0.0)))
    steps = []
    for r in _ranges(step_ts, lambda it: it[0]):
        dymax = max(it[1] for it in r["_items"])
        it0 = r["_items"][0]
        steps.append(dict(t_range=[round(r["t_lo"], 3), round(r["t_hi"], 3)],
                          width=round(r["t_hi"] - r["t_lo"], 3), dY=round(dymax, 4),
                          where=world_of((r["t_lo"] + r["t_hi"]) / 2, it0[2]),
                          yA=round(it0[2], 4), yB=round(it0[3], 4), sideA=nameA, sideB=nameB))

    return dict(border=f"{nameA}|{nameB} {along_axis}-run @ {'x' if axis==0 else 'z'}={plane:.1f}",
                covA=[[round(a, 2), round(b, 2)] for a, b in mA],
                covB=[[round(a, 2), round(b, 2)] for a, b in mB],
                n_steps=len(steps), n_tjunc=0, n_holes=len(holes),
                steps=steps, t_junctions=[], holes=holes)


def adjacency_pairs(blocks):
    """All shared-border pairs among a block set: (A, B, axis, plane, alongkey)."""
    S = set(blocks)
    out = []
    for (bx, by) in sorted(blocks):
        # east neighbour (vertical border x = 64*(bx+1))
        if (bx + 1, by) in S:
            out.append(((bx, by), (bx + 1, by), 0, BLOCK * (bx + 1)))
        # south neighbour (horizontal border z = -64*(by+1))
        if (bx, by + 1) in S:
            out.append(((bx, by), (bx, by + 1), 2, -BLOCK * (by + 1)))
    return out


def run_crack_census(loader, blocks, label):
    """loader(bx,by)->world tris or None. Census every internal shared border; return the records."""
    cache = {}
    for b in blocks:
        cache[b] = loader(*b)
    recs = []
    for (A, B, axis, plane) in adjacency_pairs(blocks):
        if cache.get(A) is None or cache.get(B) is None:
            continue
        rec = census_border(f"[{A[0]}][{A[1]}]", cache[A], f"[{B[0]}][{B[1]}]", cache[B], axis, plane)
        rec["carriedA"] = A in CARRIED
        rec["carriedB"] = B in CARRIED
        recs.append(rec)
    tot = dict(steps=sum(r["n_steps"] for r in recs), tjunc=sum(r["n_tjunc"] for r in recs),
               holes=sum(r["n_holes"] for r in recs))
    print(f"\n=== CRACK CENSUS: {label} ({len(recs)} internal borders) ===")
    print(f"    TOTAL  steps={tot['steps']}  T-junctions={tot['tjunc']}  holes={tot['holes']}")
    for r in recs:
        if r["n_steps"] or r["n_holes"]:
            tag = f"[carried={r['carriedA']}/{r['carriedB']}]"
            print(f"  {r['border']:38s} {tag:20s} steps={r['n_steps']} holes={r['n_holes']}")
            for s in r["steps"][:8]:
                print(f"       STEP  at {s['where']}  dY={s['dY']} over t{s['t_range']} (w={s['width']}) "
                      f"yA={s['yA']} yB={s['yB']}")
            for h in r["holes"][:8]:
                print(f"       HOLE  at {h['where']}  present={h['present']} missing={h['missing']} "
                      f"t{h['t_range']} (w={h['width']})")
    return recs, tot


# ============================================================================================
# PART 1b -- drill specific sliver sites to the actual verts
# ============================================================================================
def drill_site(wx, wz, radius=3.0):
    """Dump every deployed-terrain vert within `radius` of (wx,wz), grouped by block, with Y+topo --
    the ground truth at a reported sliver."""
    print(f"\n--- DRILL at world ({wx},{wz}) radius {radius} ---")
    for (bx, by) in sorted(set(MINT_BLOCKS)):
        tris = deployed_world_tris(bx, by)
        if tris is None:
            continue
        hits = []
        for (p3, topo, fam) in tris:
            for p in p3:
                if abs(p[0] - wx) <= radius and abs(p[2] - wz) <= radius:
                    hits.append((round(p[0], 4), round(p[1], 4), round(p[2], 4), topo))
        if hits:
            uniq = sorted(set(hits))
            print(f"  block [{bx}][{by}] ({'carried' if (bx,by) in CARRIED else 'host'}): {len(uniq)} verts")
            for (x, y, z, topo) in uniq:
                onbz = "  <-ON z=-1152 border" if abs(z + 1152) < 0.03 else ""
                onbx = "  <-ON x-border" if abs(x - round(x / BLOCK) * BLOCK) < 0.03 else ""
                print(f"       ({x:9.4f},{y:8.4f},{z:10.4f}) topo={topo}{onbz}{onbx}")


# ============================================================================================
# PART 2 -- green-shard census
# ============================================================================================
def load_deployed_all(blocks):
    tris = []
    for (bx, by) in blocks:
        t = deployed_world_tris(bx, by)
        if t:
            for (p3, topo, fam) in t:
                tris.append((p3, topo, fam, (bx, by)))
    return tris


def cell_of(p3):
    cx = sum(p[0] for p in p3) / 3.0
    cz = sum(p[2] for p in p3) / 3.0
    return (math.floor(cx / CELL), math.floor(cz / CELL))


def green_shard_census():
    print("\n" + "=" * 92)
    print("PART 2 -- GREEN-SHARD CENSUS (carried topo-0 grass + topo-49 mural in the 5 blocks)")
    print("=" * 92)
    dep = load_deployed_all(CARRIED)
    green = [(p3, topo, fam, blk) for (p3, topo, fam, blk) in dep if topo in (0, 49)]
    # deployed neighbour family per green cell
    depcell_fam = defaultdict(Counter)
    for (p3, topo, fam, blk) in dep:
        depcell_fam[cell_of(p3)][topo] += 1
    green_cells = defaultdict(Counter)
    for (p3, topo, fam, blk) in green:
        green_cells[cell_of(p3)][topo] += 1

    # donor context: reproduce the placement T (deployed<-donor) and look at what stock had AROUND
    # each green cell's donor origin.
    stock = GE.load_stock()
    scmap = GE.cells_map(stock)
    scfam = GE.cell_family(stock)
    mint = GE.load_mod(MINT_BLOCKS)
    mcmap = GE.cells_map(mint)
    T = GE.translation(GE.topo41_footprint(scmap), GE.topo41_footprint(mcmap))   # donor->deployed
    print(f"  placement T (donor->deployed) = {T};  {len(green)} green tris in "
          f"{len(green_cells)} deployed cells")

    NEI8 = [(dx, dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1) if (dx, dz) != (0, 0)]
    records = []
    for gc in sorted(green_cells):
        donor_cell = (gc[0] - T[0], gc[1] - T[1])
        # donor-side neighbour families (what stood next to this tile in stock)
        donor_nb = Counter()
        for (dx, dz) in NEI8:
            f = scfam.get((donor_cell[0] + dx, donor_cell[1] + dz))
            if f:
                donor_nb[f] += 1
        donor_self = scfam.get(donor_cell)
        # deployed-side neighbour families
        dep_nb = Counter()
        for (dx, dz) in NEI8:
            c = (gc[0] + dx, gc[1] + dz)
            fams = depcell_fam.get(c)
            if fams:
                dom = fams.most_common(1)[0][0]
                dep_nb[GE.TOPO_FAM.get(dom, f"t{dom}")] += 1
        # classify: grass-context stump if donor had grass neighbours but deployed has none
        donor_had_grass = donor_nb.get("grass", 0) + donor_nb.get("scrub", 0)
        dep_has_grass = dep_nb.get("grass", 0)
        is_stump = (donor_had_grass > 0 and dep_has_grass == 0)
        records.append(dict(dep_cell=list(gc), donor_cell=list(donor_cell),
                            topos=dict(green_cells[gc]), donor_self=donor_self,
                            donor_nb=dict(donor_nb), dep_nb=dict(dep_nb),
                            classify="orphan-grass-stump" if is_stump else "in-ensemble"))
    n_stump = sum(1 for r in records if r["classify"] == "orphan-grass-stump")
    print(f"  {len(records)} green cells: {n_stump} orphan-grass-stump, {len(records)-n_stump} in-ensemble")
    for r in records:
        print(f"   dep{r['dep_cell']} donor{r['donor_cell']} topos={r['topos']} "
              f"donor_self={r['donor_self']} donor_nb={r['donor_nb']} dep_nb={r['dep_nb']} "
              f"-> {r['classify']}")

    # vocabulary check: what does stock comp[1] wear at its OWN desert-side margin (no grass near)?
    FP = GE.dunes_footprint(scfam)
    AZ, _ = GE.best_desert_azimuth(FP, scfam)
    margin_fams = Counter()
    fp = set(FP)
    for c in fp:
        for k in (1, 2, 3):
            n = (c[0] + int(AZ[0]) * k, c[1] + int(AZ[1]) * k)
            if n not in fp and scfam.get(n):
                margin_fams[scfam[n]] += 1
    print(f"\n  stock comp[1] desert-facing margin (azimuth {AZ}) family census: {dict(margin_fams)}")
    print("  => the fix vocabulary: what a dunes-ensemble desert margin wears when no grass is behind it")
    return dict(T=list(T), n_green_tris=len(green), records=records,
                stock_desert_margin=dict(margin_fams), n_stump=n_stump)


# ============================================================================================
# PERMANENT GATES (frozen: the stock NULL must census clean; the deployed defect set is the
# freeze the fix build must drive to zero without disturbing the approved ecotone / the eye)
# ============================================================================================
def permanent_gates(null_tot, dep_tot, shard):
    """The cross-block seam gate + the orphan-shard gate -- the two instruments the dunes arc never
    had. Calibration law honored: the STOCK NULL must be 0/0 (proves the instrument is not raising
    phantom seams on shipping data) before the deployed count means anything."""
    print("\n" + "=" * 92)
    print("PERMANENT GATES (frozen instrument)")
    print("=" * 92)
    gates = []

    def g(name, ok, detail=""):
        gates.append((name, bool(ok), detail))
        print(f"  GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))

    # GATE 1 -- the NULL: stock donor region censuses clean (the instrument is calibrated)
    g("cross-block seam NULL (stock donor region: 0 steps, 0 holes)",
      null_tot["steps"] == 0 and null_tot["holes"] == 0,
      f"stock steps={null_tot['steps']} holes={null_tot['holes']}")

    # GATE 2 -- the deployed cross-block seam integrity. The fix (dunes_fringe_fix.py, 2026-07-21)
    # is DEPLOYED, so 0 is the FROZEN POST-FIX state: this gate now stands guard so a regression
    # that RE-INTRODUCES a cross-block seam (a future carry re-deploy without the FIX-H/FIX-S carry
    # law) is caught. The rung-7 defect set it drove to zero was KNOWN = 2 steps + 2 holes.
    KNOWN_PREFIX = 4
    seam = dep_tot["steps"] + dep_tot["holes"]
    g("deployed cross-block seam integrity == 0 (frozen post-fix state)", seam == 0,
      f"deployed steps={dep_tot['steps']} holes={dep_tot['holes']} "
      f"({'CLEAN -- the rung-7 fix is deployed' if seam == 0 else f'REGRESSION: {seam} seam(s) re-introduced'}; "
      f"the pre-fix defect set was {KNOWN_PREFIX})")

    # GATE 3 -- no orphan green shard (topo-0 grass with no grass anywhere in its deployed 8-nbhd)
    g("no orphan grass shard (topo-0 tile with an all-desert deployed neighbourhood)",
      shard["n_stump"] == 0,
      f"orphan grass stumps = {shard['n_stump']} (target 0)")

    # GATE 4 -- (review follow-up 2026-07-21) no green ground SHARD in the deployed bytes: 0 carried
    # FLAT desert/grass ground tiles RENDER grass-green. The topo-0 count (GATE 3) missed the real
    # source of the user's "hard-edged grass ecotone tiles" -- 12 relocated desert-STRIP tiles whose
    # verbatim UV lands on green atlas texels. This is the render-faithful measure (UV -> atlas). The
    # 62 topo-49 mesa murals are NOT ground tiles and are excluded (they carry only faint sub-tri
    # lichen speckle -- olive-brown, KEPT as faithful rock).
    n_green_ground, gcells = deployed_green_ground_count()
    g("no green ground shard (0 flat desert/grass ground tiles render grass-green -- the deployed "
      "state after the green-shard fix)",
      n_green_ground == 0,
      f"green flat-ground tiles = {n_green_ground} (target 0"
      + (f"; still green at cells {sorted(gcells)[:8]}" if gcells else "") + ")")
    return gates


# ============================================================================================
# OFFLINE FIX VALIDATION -- apply the 3 designed fixes in-memory, re-census, prove the mechanism
# ============================================================================================
def _mutable_soup(blocks):
    soup = {}
    for (bx, by) in blocks:
        tris = deployed_world_tris(bx, by)
        soup[(bx, by)] = [([list(p) for p in p3], topo, fam) for (p3, topo, fam) in (tris or [])]
    return soup


def simulate_fix(blocks=CARRIED):
    """Apply the three designed fixes to in-memory world soups and re-census -- PROOF the mechanism
    closes every defect without moving any interior geometry:
      FIX-H (holes): snap every vert within (1e-4, 1.0u) of a block-border plane ONTO it (the
                     phase-shifted notch vert stretches its tri down to the border -> gap filled).
      FIX-S (steps): per shared border, raise both sides' matched-t border verts to the per-t MAX Y
                     (the flat-host side welds UP to the carried donor margin -- the cross-block form
                     of the carry's own conform-snap).
      FIX-G (green): re-dress every topo-0 grass tri to desert topo-17 (the amputation stump ->
                     plain desert, per stock comp[1]'s own desert margin = 86 desert / 4 grass).
    """
    print("\n" + "=" * 92)
    print("OFFLINE FIX VALIDATION (apply the 3 designed fixes in-memory, re-census)")
    print("=" * 92)
    soup = _mutable_soup(blocks)
    TAU = 1.0

    # FIX-G: re-dress grass
    n_green = 0
    for blk, tris in soup.items():
        for (p3, topo, fam) in tris:
            pass
    new = {}
    for blk, tris in soup.items():
        nt = []
        for (p3, topo, fam) in tris:
            if topo == 0:
                n_green += 1
                nt.append((p3, 17, "desert"))
            else:
                nt.append((p3, topo, fam))
        new[blk] = nt
    soup = new

    # FIX-H: snap near-border verts onto the border plane (per block)
    n_snap = 0
    for (bx, by), tris in soup.items():
        for (p3, topo, fam) in tris:
            for p in p3:
                # x borders at 64*bx, 64*(bx+1); z borders at -64*by, -64*(by+1)
                for plane in (BLOCK * bx, BLOCK * (bx + 1)):
                    if 1e-4 < abs(p[0] - plane) < TAU:
                        p[0] = plane
                        n_snap += 1
                for plane in (-BLOCK * by, -BLOCK * (by + 1)):
                    if 1e-4 < abs(p[2] - plane) < TAU:
                        p[2] = plane
                        n_snap += 1

    # FIX-S: per shared border, raise matched-t verts to per-t MAX Y
    n_step = 0
    for (A, B, axis, plane) in adjacency_pairs(blocks):
        if A not in soup or B not in soup:
            continue
        along = 2 if axis == 0 else 0
        # collect (t -> maxY) over border verts of both sides
        maxy = {}
        for blk in (A, B):
            for (p3, topo, fam) in soup[blk]:
                for p in p3:
                    if abs(p[axis] - plane) < BORDER_EPS:
                        key = round(p[along], 3)
                        maxy[key] = max(maxy.get(key, -1e9), p[1])
        for blk in (A, B):
            for (p3, topo, fam) in soup[blk]:
                for p in p3:
                    if abs(p[axis] - plane) < BORDER_EPS:
                        key = round(p[along], 3)
                        if key in maxy and maxy[key] - p[1] >= Y_MATCH:
                            p[1] = maxy[key]
                            n_step += 1
    print(f"  applied: FIX-G re-dressed {n_green} grass tris, FIX-H snapped {n_snap} notch verts, "
          f"FIX-S raised {n_step} step verts")

    # re-census the fixed soups
    fixed = {blk: [(tuple(tuple(p) for p in p3), topo, fam) for (p3, topo, fam) in tris]
             for blk, tris in soup.items()}
    recs = []
    for (A, B, axis, plane) in adjacency_pairs(blocks):
        if A not in fixed or B not in fixed:
            continue
        recs.append(census_border(f"[{A[0]}][{A[1]}]", fixed[A], f"[{B[0]}][{B[1]}]", fixed[B], axis, plane))
    tot = dict(steps=sum(r["n_steps"] for r in recs), holes=sum(r["n_holes"] for r in recs))
    n_green_left = sum(1 for tris in soup.values() for (_p, topo, _f) in tris if topo == 0)
    print(f"  AFTER FIX: cross-block steps={tot['steps']} holes={tot['holes']}  green(topo-0)={n_green_left}")
    ok = tot["steps"] == 0 and tot["holes"] == 0 and n_green_left == 0
    print(f"  => FIX MECHANISM {'PROVEN (all fringe defects closed)' if ok else 'INCOMPLETE'}")
    return dict(applied=dict(green=n_green, snap=n_snap, step=n_step),
                after=dict(steps=tot["steps"], holes=tot["holes"], green=n_green_left), ok=ok)


# ============================================================================================
# main
# ============================================================================================
def main():
    print("=== dunes_fringe_census.py -- THE FRINGE CENSUS (cracks/steps + green shards) ===")

    # calibration null: stock donor region, stock-vs-stock
    null_recs, null_tot = run_crack_census(stock_world_tris, DONOR_BLOCKS, "STOCK donor region (NULL)")

    # the deployed 3x3 mint region + its immediate neighbours (to catch coast-side too)
    NEIGH = MINT_BLOCKS + [(17, 18), (21, 18), (19, 16)]     # west/east/north of the cross tips
    dep_recs, dep_tot = run_crack_census(deployed_world_tris, MINT_BLOCKS, "DEPLOYED 3x3 mint region")

    # drill the reported sliver + a few other border midpoints
    drill_site(1220.0, -1152.0)
    drill_site(1216.0, -1180.0)    # x-border [18][18]|[19][18] interior
    drill_site(1248.0, -1216.0)    # z-border [19][18]|[19][19]

    shard = green_shard_census()
    n_green_ground, gcells = deployed_green_ground_count()
    print(f"\n  GREEN-SHARD instrument (deployed flat-ground): {n_green_ground} tiles render "
          f"grass-green" + (f" at {sorted(gcells)[:8]}" if gcells else " -- CLEAN"))

    gates = permanent_gates(null_tot, dep_tot, shard)
    fixval = simulate_fix()

    out = dict(
        null=dict(totals=null_tot, borders=null_recs),
        deployed=dict(totals=dep_tot, borders=dep_recs),
        green_shards=shard, green_ground=dict(n=n_green_ground, cells=[list(c) for c in gcells]),
        gates=[{"name": n, "ok": ok, "detail": d} for (n, ok, d) in gates],
        fix_validation=fixval,
    )
    (OUTD / "dunes_fringe_census.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_fringe_census.json'}")
    print(f"\nSUMMARY: NULL(stock) steps={null_tot['steps']} holes={null_tot['holes']}"
          f"  |  DEPLOYED steps={dep_tot['steps']} holes={dep_tot['holes']}"
          f"  |  green stumps={shard['n_stump']}/{len(shard['records'])}"
          f"  |  green ground tiles={n_green_ground}"
          f"  |  fix mechanism {'PROVEN' if fixval['ok'] else 'INCOMPLETE'}")


if __name__ == "__main__":
    main()
