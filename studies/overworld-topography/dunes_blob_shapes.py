"""DUNES BLOB SHAPES -- shape census of stock's real topo-41 (dunes) regions at 4u cell
granularity, run to explain WHY dunes_patch_mint.py v2's 3x3-core + two-concentric-shell design
renders as a rectilinear SQUARE FRAME while stock dunes boundaries read as organic blobs, and to
extract 2-4 stampable-footprint templates (SHAPE ONLY, no UV/texture bytes) for the next mint
round.

Cell-classification machinery (FAM_OF topo->family map, the per-cell dominant-family vote,
the desert|dunes STRIP-vs-MAINS UV classifier) is a verbatim re-derivation of
``dunes_strip_emitter.py`` / ``dunes_patch_mint.py``'s own copies -- not imported (LAW 5: every
script independently rerunnable) -- so any drift in those constants would show up as a diff
against this file, not a silent shared-state assumption.

STEPS:
  1. Map-wide per-cell family census (all 24x20 disc-1 blocks, continuous world coords so cell
     adjacency is naturally cross-block-aware) -> the set of cells whose dominant family is
     "dunes" (topo 41, MAINS-textured or STRIP-textured -- both are walkable-as-dunes cells and
     both belong to the region's true footprint).
  2. Connected components (4-neighbour) over that cell set: count, size histogram, bboxes.
  3. Per-component boundary trace (directed-edge cancellation + chain-walk, the same technique
     the codebase already uses for mesh boundary-edge extraction in ``once_edges_from_bm``,
     applied here to the CELL grid instead of triangle verts) -> straight-run length
     distribution, corner count, convex-hull-area ratio, aspect ratio.
  4. Freckle census: components of 1-2 cells within a few cells of a bigger component.
  5. Stampability: does any component (+ 1-cell ring) fit an ~80-regular-cell host budget? If
     not, extract a closed LOBE via erosion-core + multi-source-BFS (Voronoi) partition, cut at
     the component's narrowest waist -- report the cut exactly.
  6. Emit 2-4 normalized footprint templates (cell-set + boundary list + freckle suggestions,
     SHAPE ONLY) to out/dunes_blob_templates.json.
  7. Score dunes_patch_mint.py v2's own core+shell footprint (read from its own committed
     out/dunes_patch_mint.json if present, else recomputed from its known construction) against
     the same trace metrics -- the number that explains the square-frame failure.

Run from the repo root:  py studies/overworld-topography/dunes_blob_shapes.py
Artifacts -> out/dunes_blob_shapes.json, out/dunes_blob_templates.json
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                      # noqa: E402

HERE = Path(__file__).parent
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)

BLOCK = 64.0
CELL_U = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

# ---- FAM_OF -- verbatim re-derivation of dunes_strip_emitter.py's topo->family map (LAW 5) ----
FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    FAM_OF[t] = "grass"
for t in (4, 5, 6):
    FAM_OF[t] = "scrub"
for t in (17, 16, 19, 20):
    FAM_OF[t] = "desert"
for t in (27, 28):
    FAM_OF[t] = "snow"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"
FAM_OF[45] = FAM_OF[46] = "canyon"

DUNES_TOPO = 41

print("=== STEP 1: map-wide per-cell family census (all 24x20 disc-1 blocks) ===")

fams_at: dict = defaultdict(Counter)   # cell -> Counter(family -> tri count)
n_blocks_read = 0
for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        n_blocks_read += 1
        V = bm.verts
        TAN = bm.tangents
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(TAN[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            if fam is None:
                continue
            cx = sum(V[j][0] for j in tri) / 3.0 + BLOCK * bx
            cz = sum(V[j][2] for j in tri) / 3.0 - BLOCK * by
            cell = (math.floor(cx / CELL_U), math.floor(cz / CELL_U))
            fams_at[cell][fam] += 1

print(f"blocks read: {n_blocks_read}/480; cells classified: {len(fams_at)}")

cell_fam = {c: fc.most_common(1)[0][0] for c, fc in fams_at.items()}
dunes_cells = {c for c, f in cell_fam.items() if f == "dunes"}
print(f"dunes cells (dominant family == dunes, MAINS+STRIP-textured both included): {len(dunes_cells)}")

fam_tally = Counter(cell_fam.values())
print(f"map-wide family tally (all classified cells): {dict(fam_tally)}")


# ============================================================================================
# STEP 2 -- connected components (4-neighbour, cross-block already folded into cell coords)
# ============================================================================================
print("\n=== STEP 2: connected components over the dunes cell set ===")


def connected_components(cellset):
    visited = set()
    comps = []
    for start in cellset:
        if start in visited:
            continue
        comp = set()
        q = deque([start])
        visited.add(start)
        while q:
            c = q.popleft()
            comp.add(c)
            for di, dj in NEI4:
                n = (c[0] + di, c[1] + dj)
                if n in cellset and n not in visited:
                    visited.add(n)
                    q.append(n)
        comps.append(comp)
    return comps


components = connected_components(dunes_cells)
components.sort(key=len, reverse=True)


def bbox(cells):
    xs = [c[0] for c in cells]
    zs = [c[1] for c in cells]
    return (min(xs), min(zs), max(xs), max(zs))


comp_info = []
for idx, comp in enumerate(components):
    bx0, bz0, bx1, bz1 = bbox(comp)
    comp_info.append(dict(idx=idx, size=len(comp), bbox=(bx0, bz0, bx1, bz1),
                           w=bx1 - bx0 + 1, h=bz1 - bz0 + 1, cells=comp))

print(f"components: {len(components)}; size histogram: "
      f"{dict(sorted(Counter(len(c) for c in components).items()))}")
def to_block(cell):
    """cell (i,j) -> (bx,by) block index, inverting cell=(floor(x/4),floor(z/4)) with
    x=64*bx+local_x (local_x in [0,64)) and z=local_z-64*by (local_z in (-64,0]) -- i.e.
    bx=floor(cell_x*4/64), by=floor(-(cell_z*4)/64)."""
    return (math.floor(cell[0] * CELL_U / BLOCK), math.floor(-(cell[1] * CELL_U) / BLOCK))


for ci in comp_info:
    print(f"  comp[{ci['idx']}] size={ci['size']:4d} bbox={ci['bbox']} "
          f"({ci['w']}x{ci['h']} cells) blocks touched="
          f"{sorted({to_block(c) for c in ci['cells']})}")


# ============================================================================================
# STEP 3 -- boundary trace: directed-edge cancellation + chain-walk (cell-grid analogue of the
# codebase's mesh once-edge technique)
# ============================================================================================
print("\n=== STEP 3: boundary trace per component (straight-run / corner / convexity / aspect) ===")


def boundary_trace(cellset):
    """Directed CCW cell-boundary edges; edges shared by two cells in cellset cancel (interior
    edges), the survivors chain start->end into one or more closed loops. Returns the list of
    loops, each a list of (corner_start, corner_end, owning_cell) in walk order, plus the raw
    corner-adjacency used, for diagnostics."""
    directed = {}     # (start_corner, end_corner) -> owning cell (last writer wins; used only
    #                    for cancellation bookkeeping below)
    for (i, j) in cellset:
        bl, br, tr, tl = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
        sides = [(bl, br, (i, j - 1)), (br, tr, (i + 1, j)),
                 (tr, tl, (i, j + 1)), (tl, bl, (i - 1, j))]
        for (a, b, nb) in sides:
            if nb in cellset:
                continue   # interior edge, no boundary contribution from this side
            directed[(a, b)] = (i, j)

    # sanity: an edge and its reverse both present would mean a degenerate 1-cell-thin sliver
    # touching itself -- doesn't happen for a raster region with no duplicate cells, kept as an
    # assertion-free note (not fatal): reverse-edge collisions would show as two DIFFERENT owning
    # cells emitting (a,b) and (b,a) simultaneously, which cancels correctly under the outgoing
    # dict-by-start lookup used in the walk below regardless.
    out_from = defaultdict(list)
    for (a, b), cell in directed.items():
        out_from[a].append((b, cell))

    def turn_priority(prev_dir, cand_dir):
        """Right-hand-first tie-break at pinch corners (>1 candidate leaving the same corner):
        prefer the candidate that turns most CLOCKWISE relative to the incoming direction, the
        standard rule for extracting a simple (non-self-crossing) polygon from cell-boundary
        edges at a diagonal-touch pinch point. Returns a sortable key (lower = more preferred)."""
        # cross product z-component prev x cand; more negative = more clockwise turn
        cross = prev_dir[0] * cand_dir[1] - prev_dir[1] * cand_dir[0]
        dot = prev_dir[0] * cand_dir[0] + prev_dir[1] * cand_dir[1]
        # order: hard-right(cross<0,dot~0-ish) < straight(cross==0,dot==1) < hard-left(cross>0)
        # encode as angle-like scalar via atan2 for a total order
        return -math.atan2(cross, dot)

    remaining = dict(directed)
    loops = []
    while remaining:
        (a0, b0) = next(iter(remaining))
        loop = []
        a, b = a0, b0
        cell0 = remaining.pop((a0, b0))
        loop.append((a, b, cell0))
        cur = b
        prev_dir = (b[0] - a[0], b[1] - a[1])
        guard = 0
        while cur != a0 and guard < 100000:
            guard += 1
            cands = [(end, cell) for (end, cell) in out_from[cur] if (cur, end) in remaining]
            if not cands:
                break   # dangling (shouldn't happen for a closed raster boundary); stop loop
            if len(cands) == 1:
                end, cell = cands[0]
            else:
                end, cell = min(cands, key=lambda ec: turn_priority(prev_dir, (ec[0][0] - cur[0], ec[0][1] - cur[1])))
            remaining.pop((cur, end))
            loop.append((cur, end, cell))
            prev_dir = (end[0] - cur[0], end[1] - cur[1])
            cur = end
        loops.append(loop)
    return loops


def loop_area(loop):
    """Shoelace area (signed) of the corner polygon -- positive = CCW (outer boundary by our
    CCW-cell convention), negative = CW (a hole)."""
    a = 0.0
    for (p, q, _cell) in loop:
        a += p[0] * q[1] - q[0] * p[1]
    return a / 2.0


def run_lengths_and_corners(loop):
    dirs = [(q[0] - p[0], q[1] - p[1]) for (p, q, _c) in loop]
    if not dirs:
        return [], 0
    runs = []
    cur_dir = dirs[0]
    run_len = 1
    for d in dirs[1:]:
        if d == cur_dir:
            run_len += 1
        else:
            runs.append(run_len)
            cur_dir = d
            run_len = 1
    runs.append(run_len)
    # merge wraparound run with the first run if same direction (closed polygon)
    if len(runs) > 1 and dirs[-1] == dirs[0]:
        runs[0] += runs[-1]
        runs.pop()
    return runs, len(runs)


def convex_hull_area(points):
    """Andrew monotone-chain convex hull, shoelace area. points: list of (x,y) ints/floats."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return 0.0

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    a = 0.0
    for i in range(len(hull)):
        x1, y1 = hull[i]
        x2, y2 = hull[(i + 1) % len(hull)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def analyze_shape(cellset, label=""):
    loops = boundary_trace(cellset)
    outer_loops = [lp for lp in loops if loop_area(lp) > 0]
    hole_loops = [lp for lp in loops if loop_area(lp) < 0]
    outer = max(outer_loops, key=lambda lp: abs(loop_area(lp))) if outer_loops else (max(loops, key=len) if loops else [])
    runs, n_corners = run_lengths_and_corners(outer)
    outline_cells = []
    for (_p, _q, cell) in outer:
        if not outline_cells or outline_cells[-1] != cell:
            outline_cells.append(cell)
    corners_pts = set()
    for (p, q, _c) in outer:
        corners_pts.add(p)
        corners_pts.add(q)
    hull_area = convex_hull_area(list(corners_pts))
    convexity = (len(cellset) / hull_area) if hull_area > 0 else None
    bx0, bz0, bx1, bz1 = bbox(cellset)
    w, h = bx1 - bx0 + 1, bz1 - bz0 + 1
    aspect = max(w, h) / max(1, min(w, h))
    return dict(
        label=label, size=len(cellset), n_loops=len(loops), n_holes=len(hole_loops),
        n_outer_boundary_cells=len(outline_cells), n_corners=n_corners,
        max_run=max(runs) if runs else 0, mean_run=round(float(np.mean(runs)), 3) if runs else 0.0,
        median_run=float(np.median(runs)) if runs else 0.0,
        run_hist=dict(sorted(Counter(runs).items())),
        hull_area=round(hull_area, 2), convexity=round(convexity, 4) if convexity else None,
        bbox=(bx0, bz0, bx1, bz1), w=w, h=h, aspect=round(aspect, 3),
        outline_cells=outline_cells, runs=runs,
    )


shape_reports = []
for ci in comp_info:
    rep = analyze_shape(ci["cells"], label=f"comp[{ci['idx']}]")
    shape_reports.append(rep)
    print(f"  {rep['label']}: size={rep['size']:4d} bbox={rep['bbox']} loops={rep['n_loops']} "
          f"holes={rep['n_holes']} boundary_cells={rep['n_outer_boundary_cells']} "
          f"corners={rep['n_corners']} max_run={rep['max_run']} mean_run={rep['mean_run']} "
          f"convexity={rep['convexity']} aspect={rep['aspect']}")
    print(f"      run_hist={rep['run_hist']}")


# ---- neighbour-family breakdown per component boundary (which family(ies) does the blob touch) ----
print("\nboundary neighbour-family census (which real family each component's edge touches):")
comp_neighbour_fam = []
for ci in comp_info:
    touch = Counter()
    for c in ci["cells"]:
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n in ci["cells"]:
                continue
            f = cell_fam.get(n)
            if f is not None:
                touch[f] += 1
            else:
                touch["<unclassified/off-census>"] += 1
    comp_neighbour_fam.append(dict(touch))
    print(f"  comp[{ci['idx']}] (size {ci['size']}): {dict(touch)}")


# ============================================================================================
# STEP 4 -- freckle census: 1-2 cell components near a bigger component
# ============================================================================================
print("\n=== STEP 4: freckle census (1-2 cell satellite components) ===")

BIG_THRESH = 6          # a component >= this size counts as "a bigger component" for proximity
FRECKLE_MAX = 2          # <=2 cells = freckle
NEAR_RADIUS = 4          # cells (Chebyshev) considered "near"

big_comps = [ci for ci in comp_info if ci["size"] >= BIG_THRESH]
freckles = [ci for ci in comp_info if ci["size"] <= FRECKLE_MAX]


def cheb_dist(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def min_dist_to_comp(freckle_cells, comp_cells):
    return min(cheb_dist(f, c) for f in freckle_cells for c in comp_cells)


freckle_reports = []
for fr in freckles:
    dists = [(bc["idx"], min_dist_to_comp(fr["cells"], bc["cells"])) for bc in big_comps]
    dists.sort(key=lambda t: t[1])
    nearest_idx, nearest_d = dists[0] if dists else (None, None)
    near = nearest_d is not None and nearest_d <= NEAR_RADIUS
    # does this freckle carry the desert|dunes strip UV rather than mains UV? We don't have UV
    # bytes here (topology-only census); flag it structurally instead -- a freckle whose cells
    # are ALL boundary cells (no interior cell) is topologically indistinguishable from a
    # strip-only sliver; report that structural fact plainly rather than re-deriving the UV
    # classifier a third time in this file.
    all_boundary = True   # a 1-2 cell freckle has no interior cell by construction (every cell
    #                        touches a non-dunes neighbour) -- always true, stated explicitly
    freckle_reports.append(dict(size=fr["size"], bbox=fr["bbox"], cells=sorted(fr["cells"]),
                                 nearest_big_comp=nearest_idx, nearest_dist_cells=nearest_d,
                                 near_a_big_component=near, all_cells_are_boundary_cells=all_boundary))
    print(f"  freckle size={fr['size']} bbox={fr['bbox']} nearest big comp={nearest_idx} "
          f"dist={nearest_d} near={near}")

print(f"total freckles (<= {FRECKLE_MAX} cells): {len(freckles)}; "
      f"near a big component (<= {NEAR_RADIUS} cells away): "
      f"{sum(1 for f in freckle_reports if f['near_a_big_component'])}")


# ============================================================================================
# STEP 5 -- stampability: fits an ~80-regular-cell host budget? else extract a closed LOBE
# ============================================================================================
print("\n=== STEP 5: stampability against an ~80-regular-cell host budget ===")

HOST_BUDGET = 80


def with_ring(cellset):
    ring = set(cellset)
    for c in cellset:
        for di, dj in NEI4:
            ring.add((c[0] + di, c[1] + dj))
    return ring


stampable = []
for ci in comp_info:
    footprint = with_ring(ci["cells"])
    fits = len(footprint) <= HOST_BUDGET
    stampable.append(dict(idx=ci["idx"], size=ci["size"], footprint_with_ring=len(footprint), fits=fits))
    print(f"  comp[{ci['idx']}] size={ci['size']:4d} size+1-cell-ring={len(footprint):4d} "
          f"fits<= {HOST_BUDGET}: {fits}")

any_fits = any(s["fits"] for s in stampable)
smallest_sorted = sorted(comp_info, key=lambda c: c["size"])[:5]
print(f"\nany component small enough to stamp whole: {any_fits}")
print("smallest 5 components (exact footprints below, emitted to templates JSON where they fit):")
for ci in smallest_sorted:
    print(f"  comp[{ci['idx']}] size={ci['size']} bbox={ci['bbox']}")


# ---- lobe extraction (erosion-core + multi-source BFS/Voronoi partition), applied to the
# largest component if nothing stamps whole ----
def erode(cellset):
    return {c for c in cellset if all((c[0] + di, c[1] + dj) in cellset for di, dj in NEI4)}


def lobe_partition(cellset):
    """Erode to find interior 'cores' (lobe seeds); connected-component those; multi-source BFS
    (Voronoi, 4-neighbour, FIFO ties broken by insertion/lexicographic order for determinism)
    assigns every cell in cellset to its nearest core -- the boundary between two lobes' basins
    IS the saddle cut. Returns list of lobe cellsets (each a subset of cellset)."""
    core = erode(cellset)
    core_comps = connected_components(core)
    core_comps.sort(key=len, reverse=True)
    if len(core_comps) < 2:
        return [cellset]   # single-lobe blob, nothing to cut
    owner = {}
    q = deque()
    for lobe_id, comp in enumerate(core_comps):
        for c in comp:
            owner[c] = lobe_id
            q.append(c)
    while q:
        c = q.popleft()
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n in cellset and n not in owner:
                owner[n] = owner[c]
                q.append(n)
    lobes = defaultdict(set)
    for c, lobe_id in owner.items():
        lobes[lobe_id].add(c)
    return [lobes[k] for k in sorted(lobes)]


lobe_report = None
chosen_lobe_cells = None
chosen_lobe_source_comp = None
if not any_fits:
    biggest = comp_info[0]
    lobes = lobe_partition(biggest["cells"])
    print(f"\nlobe partition of the biggest component (comp[{biggest['idx']}], size {biggest['size']}): "
          f"{len(lobes)} lobe(s), sizes {sorted((len(l) for l in lobes), reverse=True)}")
    if len(lobes) >= 2:
        # identify cut edges: cell-adjacent pairs (a in lobe X, b in lobe Y, X!=Y) both inside
        # the original component -- these edges are the SYNTHETIC cut, everything else on each
        # lobe's outline is verbatim-real component boundary.
        lobe_of = {}
        for li, l in enumerate(lobes):
            for c in l:
                lobe_of[c] = li
        cut_pairs = []
        for c in biggest["cells"]:
            for di, dj in NEI4:
                n = (c[0] + di, c[1] + dj)
                if n in biggest["cells"] and lobe_of.get(n) != lobe_of.get(c) and (n, c) not in cut_pairs:
                    cut_pairs.append((c, n))
        print(f"cut edges (saddle boundary between lobes): {len(cut_pairs)} cell-adjacent pairs")
        # pick the LARGEST lobe that still fits the host budget (a bigger, more representative
        # closed sub-blob is more useful than the smallest trivial appendage that happens to
        # fit); fall back to the smallest lobe overall if none fit at all
        lobes_by_size_desc = sorted(lobes, key=len, reverse=True)
        fit_candidates = [l for l in lobes_by_size_desc if len(with_ring(l)) <= HOST_BUDGET]
        chosen_lobe_cells = fit_candidates[0] if fit_candidates else min(lobes, key=len)
        chosen_lobe_source_comp = biggest["idx"]
        cut_cells_in_chosen = {c for (c, n) in cut_pairs if c in chosen_lobe_cells} | \
                               {n for (c, n) in cut_pairs if n in chosen_lobe_cells}
        rep = analyze_shape(chosen_lobe_cells, label=f"lobe-of-comp[{biggest['idx']}]")
        lobe_report = dict(source_comp=biggest["idx"], source_size=biggest["size"],
                            n_lobes=len(lobes), lobe_sizes=sorted((len(l) for l in lobes), reverse=True),
                            n_cut_edges=len(cut_pairs), chosen_lobe_size=len(chosen_lobe_cells),
                            chosen_lobe_fits_budget=len(with_ring(chosen_lobe_cells)) <= HOST_BUDGET,
                            cut_cells_in_chosen_lobe=sorted(cut_cells_in_chosen),
                            shape=rep)
        print(f"chosen lobe: size={len(chosen_lobe_cells)} bbox={rep['bbox']} "
              f"fits budget={lobe_report['chosen_lobe_fits_budget']} "
              f"cells-touching-the-cut={len(cut_cells_in_chosen)}/{len(chosen_lobe_cells)}")
    else:
        print("erosion found a single interior core (no natural two-lobe waist) -- the biggest "
              "component does not have a clean saddle to cut; would need a different split "
              "heuristic (not implemented, not needed this run).")


# ============================================================================================
# STEP 6 -- emit 2-4 normalized footprint templates (SHAPE ONLY) -> out/dunes_blob_templates.json
# ============================================================================================
print("\n=== STEP 6: emit footprint templates (shape only, no UV/texture bytes) ===")


def normalize(cellset):
    bx0, bz0, _bx1, _bz1 = bbox(cellset)
    return sorted((c[0] - bx0, c[1] - bz0) for c in cellset), (bx0, bz0)


def boundary_cells_of(cellset):
    out = []
    for c in cellset:
        if any((c[0] + di, c[1] + dj) not in cellset for di, dj in NEI4):
            out.append(c)
    return sorted(out)


templates = []

# template A/B: the two smallest REAL components, whole, verbatim (if any exist at all -- always
# true here since every stock family has some small satellite blobs)
for ci in smallest_sorted[:2]:
    norm_cells, origin = normalize(ci["cells"])
    bcells, _ = normalize(set(boundary_cells_of(ci["cells"])))
    # nearby freckles (relative to this template's own origin, world cell units)
    nearby_freckles = []
    for fr in freckle_reports:
        if fr["nearest_big_comp"] == ci["idx"] or (ci["size"] <= FRECKLE_MAX):
            for fc in fr["cells"]:
                nearby_freckles.append([fc[0] - origin[0], fc[1] - origin[1]])
    templates.append(dict(
        name=f"real_component_{ci['idx']}_verbatim", kind="whole_component",
        source="stock dunes component, whole, unmodified",
        size=ci["size"], bbox_wh=(ci["w"], ci["h"]),
        cell_offsets=norm_cells, boundary_cell_offsets=bcells,
        suggested_freckle_offsets=nearby_freckles,
        fits_80_cell_host_with_ring=(len(with_ring(ci["cells"])) <= HOST_BUDGET),
    ))

# template C: the extracted lobe (if a lobe cut was needed)
if lobe_report is not None and chosen_lobe_cells is not None:
    norm_cells, origin = normalize(chosen_lobe_cells)
    bcells, _ = normalize(set(boundary_cells_of(chosen_lobe_cells)))
    cut_norm = sorted((c[0] - origin[0], c[1] - origin[1]) for c in lobe_report["cut_cells_in_chosen_lobe"])
    templates.append(dict(
        name=f"lobe_of_comp_{lobe_report['source_comp']}_cut_at_saddle", kind="closed_sub_blob_lobe",
        source=f"one lobe of real dunes component[{lobe_report['source_comp']}] "
                f"(size {lobe_report['source_size']}, {lobe_report['n_lobes']} lobes total), "
                f"cut where erosion-core Voronoi basins meet (the narrowest waist)",
        size=len(chosen_lobe_cells), bbox_wh=(bbox(chosen_lobe_cells)[2] - bbox(chosen_lobe_cells)[0] + 1,
                                               bbox(chosen_lobe_cells)[3] - bbox(chosen_lobe_cells)[1] + 1),
        cell_offsets=norm_cells, boundary_cell_offsets=bcells,
        cut_boundary_cell_offsets=cut_norm,
        cut_boundary_note="cells in cut_boundary_cell_offsets sit on the SYNTHETIC cut (the "
                           "saddle line between this lobe and its sibling lobe(s) of the same "
                           "real component) -- every OTHER boundary_cell_offsets entry is "
                           "verbatim-real stock component boundary.",
        suggested_freckle_offsets=[],
        fits_80_cell_host_with_ring=(len(with_ring(chosen_lobe_cells)) <= HOST_BUDGET),
    ))

# template D: v2's own square core+shell footprint, for direct side-by-side comparison (this is
# NOT a new proposal -- it is the falsified design, included so the templates file carries its
# own comparison baseline)
CORE_SIZE = 3
v2_core = {(di, dj) for di in range(CORE_SIZE) for dj in range(CORE_SIZE)}


def dilate(seed_cells, exclude):
    nxt = set()
    for c in seed_cells:
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if n not in exclude:
                nxt.add(n)
    return nxt


v2_inner = dilate(v2_core, v2_core)
v2_outer = dilate(v2_inner, v2_core | v2_inner)
v2_full = v2_core | v2_inner | v2_outer
v2_shape = analyze_shape(v2_full, label="v2_square_core_plus_2_shells (FALSIFIED design)")
templates.append(dict(
    name="v2_square_core_plus_shells_REFERENCE_ONLY", kind="falsified_reference",
    source="dunes_patch_mint.py v2's 3x3 core + inner shell (dilate x1) + outer shell "
           "(dilate x2) -- included ONLY as the comparison baseline this study falsifies, "
           "NOT a usable template",
    size=v2_shape["size"], bbox_wh=(v2_shape["w"], v2_shape["h"]),
    cell_offsets=sorted(v2_full), boundary_cell_offsets=sorted(boundary_cells_of(v2_full)),
    suggested_freckle_offsets=[],
    fits_80_cell_host_with_ring=(len(with_ring(v2_full)) <= HOST_BUDGET),
    shape_stats=v2_shape,
))

templates_out = dict(
    generated_by="dunes_blob_shapes.py", cell_unit_u=CELL_U,
    note="SHAPE ONLY: cell_offsets are (i,j) integer grid offsets from each template's own "
         "bbox-min-corner origin, one unit == one 4u world cell. No UV/texture/topo-index "
         "bytes are carried here -- a consumer stamps this cell-set (mark cells dunes-mains, "
         "ring cells desert|dunes strip per the existing STRIPS/emit_strip_rows machinery) "
         "onto its own host, at its own chosen world position.",
    host_budget_cells=HOST_BUDGET,
    templates=templates,
)
(OUTD / "dunes_blob_templates.json").write_text(json.dumps(templates_out, indent=1, default=str))
print(f"-> {OUTD / 'dunes_blob_templates.json'} ({len(templates)} templates)")


# ============================================================================================
# STEP 7 -- v2 vs measured envelope: the number that says why it failed
# ============================================================================================
print("\n=== STEP 7: v2's square-frame footprint vs the measured real-component envelope ===")

real_max_runs = [r["max_run"] for r in shape_reports if r["size"] >= BIG_THRESH]
real_mean_runs = [r["mean_run"] for r in shape_reports if r["size"] >= BIG_THRESH]
real_corners = [r["n_corners"] for r in shape_reports if r["size"] >= BIG_THRESH]
real_convexity = [r["convexity"] for r in shape_reports if r["size"] >= BIG_THRESH and r["convexity"]]

env = dict(
    n_real_components_ge_thresh=len(real_max_runs),
    real_max_run_range=(min(real_max_runs), max(real_max_runs)) if real_max_runs else None,
    real_mean_run_range=(round(min(real_mean_runs), 3), round(max(real_mean_runs), 3)) if real_mean_runs else None,
    real_corners_range=(min(real_corners), max(real_corners)) if real_corners else None,
    real_convexity_range=(round(min(real_convexity), 3), round(max(real_convexity), 3)) if real_convexity else None,
    v2_max_run=v2_shape["max_run"], v2_mean_run=v2_shape["mean_run"],
    v2_corners=v2_shape["n_corners"], v2_convexity=v2_shape["convexity"],
    v2_run_hist=v2_shape["run_hist"],
)
print(f"REAL components (size>={BIG_THRESH}) envelope: max_run in {env['real_max_run_range']}, "
      f"mean_run in {env['real_mean_run_range']}, corners in {env['real_corners_range']}, "
      f"convexity in {env['real_convexity_range']}")
print(f"v2 square (core+2 shells, {v2_shape['size']} cells): max_run={env['v2_max_run']} "
      f"mean_run={env['v2_mean_run']} corners={env['v2_corners']} convexity={env['v2_convexity']} "
      f"run_hist={env['v2_run_hist']}")
if real_max_runs:
    v2_pctile_note = (f"v2's max_run={env['v2_max_run']} is "
                       f"{'INSIDE' if min(real_max_runs) <= env['v2_max_run'] <= max(real_max_runs) else 'OUTSIDE'} "
                       f"the real range {env['real_max_run_range']}")
    print(v2_pctile_note)
else:
    v2_pctile_note = "no real component reached the size threshold for comparison"


# ============================================================================================
# summary dump
# ============================================================================================
out = dict(
    n_blocks_read=n_blocks_read, n_cells_classified=len(fams_at),
    map_wide_family_tally=dict(fam_tally),
    n_dunes_cells=len(dunes_cells), n_components=len(components),
    component_size_histogram=dict(sorted(Counter(len(c) for c in components).items())),
    components=[dict(idx=ci["idx"], size=ci["size"], bbox=ci["bbox"], w=ci["w"], h=ci["h"])
                for ci in comp_info],
    shape_reports=[{k: v for k, v in r.items() if k not in ("outline_cells", "runs")} for r in shape_reports],
    boundary_neighbour_family_by_component=comp_neighbour_fam,
    freckle_census=freckle_reports,
    stampability=stampable,
    host_budget_cells=HOST_BUDGET,
    any_component_fits_whole=any_fits,
    lobe_extraction=lobe_report,
    v2_reference_shape=v2_shape,
    envelope_vs_v2=env,
    envelope_note=v2_pctile_note,
    templates_file=str(OUTD / "dunes_blob_templates.json"),
)
(OUTD / "dunes_blob_shapes.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'dunes_blob_shapes.json'}")
print("\nDONE.")
