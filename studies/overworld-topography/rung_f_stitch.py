"""RUNG F STITCH -- THE T-JUNCTION SEAM WELD (2026-07-24, build-fix round 1).

Round 1 root cause (rung_f_build.json known_residuals.weld_integrity): the carry welds a FINE-CONFORM
donor mesh (irregular triangulation -- variable-size tris, verts off the 4u grid by up to ~2u, boundary
edges spanning multiple cells e.g. an 8u edge x=56->64 with no vertex at 60) into a COARSE minted grass
lattice (a vertex at EVERY 4u grid corner). The carried mesh boundary loop dC never coincides with the
grass hole boundary (which was defined by CELL membership, a different curve than the actual conform
mesh boundary), so ~250 seam grid-corners become T-junctions: a grass vertex lies strictly inside a
carried boundary edge (or vice versa), leaving the edge single-owner -> 243 once-edges above the skirt
-> R1's land-perimeter silhouette reads the un-welded seam as internal COAST (~2u standoff, an artifact).

THE FIX (the two proven mechanisms named in the task):
  (1) THE APRON WELD -- snap every grass hole-boundary vertex ONTO dC (project to the nearest carried
      boundary edge in XZ, take the carried edge's LERPED position incl. Y). Deformation goes to the
      GRASS (the massif-carry apron law); the carried ensemble stays byte-RIGID. Closes the XZ+Y gap
      between the cell-aligned grass hole and the conform mesh boundary.
  (2) THE T-JUNCTION ELIMINATION -- with the grass boundary now lying on dC, iteratively split every
      triangle edge that has another mesh vertex strictly interior to it (colinear in XZ within tol,
      Y matching the edge within ytol): a welded grass vert splits the carried edge it sits on; a
      carried boundary vert splits the grass edge it sits on. Inserted verts carry EDGE-LERPED
      attributes (the DEFORMED-TILE / clip-insert law, _lerp_vert convention: tangent/IDALL inherited
      from endpoint A so topo+flags are preserved). After convergence no vertex lies inside any edge ->
      every seam edge is shared by exactly two triangles -> watertight (the only once-edges left are the
      true island coast at the y=0 skirt).

BYTE-RIGIDITY: the pure-INTERIOR carried tris are never touched (only carried tris whose edge carries a
seam T-vertex are split, and those are the boundary ring -- rung_f_build STAGE2 asserts rigidity only on
whole donor-matching interior tris, counting a split boundary piece as a clipped_piece, not a violation).

READ-ONLY vs the game install. Pure in-memory geometry. Imported by rung_f_layout.carry().
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

BLOCK = 64.0
CELL = 4.0


def _lerp_vert(a, b, t):
    """transplant._lerp_vert convention: pos/nrm/uv lerped, tangent (IDALL topo+flags) inherited from A."""
    p = tuple(a[0][k] + t * (b[0][k] - a[0][k]) for k in range(3))
    nr = tuple(a[1][k] + t * (b[1][k] - a[1][k]) for k in range(3))
    uv = (a[2][0] + t * (b[2][0] - a[2][0]), a[2][1] + t * (b[2][1] - a[2][1]))
    return (p, nr, uv, a[3])


def _tri_area2_3d(t3):
    (ax, ay, az) = t3[0][0]
    ux, uy, uz = (t3[1][0][0] - ax, t3[1][0][1] - ay, t3[1][0][2] - az)
    vx, vy, vz = (t3[2][0][0] - ax, t3[2][0][1] - ay, t3[2][0][2] - az)
    cx, cy, cz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    return math.sqrt(cx * cx + cy * cy + cz * cz)


# ============================================================================================
# dC -- the carried submesh boundary (once-edges), and a spatial index of its 3D segments
# ============================================================================================
def boundary_edges(tris):
    """Return the list of boundary (once-owned) edges of a triangle soup, each as a (vertA, vertB)
    pair of FULL verts (pos, nrm, uv, tan). An edge is keyed by rounded endpoint XYZ."""
    ecnt = Counter()
    esample = {}
    for tri in tris:
        for q in range(3):
            a, b = tri[q], tri[(q + 1) % 3]
            ka = tuple(round(c, 3) for c in a[0])
            kb = tuple(round(c, 3) for c in b[0])
            if ka == kb:
                continue
            ek = tuple(sorted((ka, kb)))
            ecnt[ek] += 1
            esample[ek] = (a, b)
    return [esample[ek] for ek, n in ecnt.items() if n == 1]


class SegIndex:
    """Bucket 3D segments (XZ) into a coarse grid for near-segment queries."""

    def __init__(self, edges, bucket=BLOCK):
        self.bucket = bucket
        self.grid = defaultdict(list)
        for (a, b) in edges:
            ax, az = a[0][0], a[0][2]
            bx, bz = b[0][0], b[0][2]
            i0, i1 = sorted((math.floor(ax / bucket), math.floor(bx / bucket)))
            j0, j1 = sorted((math.floor(az / bucket), math.floor(bz / bucket)))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.grid[(i, j)].append((a, b))

    def nearest_on_boundary(self, px, pz, reach):
        """Nearest point on any boundary edge to (px,pz) within XZ `reach`. Returns
        (dist_xz, projected_full_vert) or (None, None). The projected vert takes the edge's LERPED
        pos/nrm/uv and inherits tangent from the edge's A endpoint."""
        b = self.bucket
        best_d = reach
        best_v = None
        ci, cj = math.floor(px / b), math.floor(pz / b)
        seen = set()
        for i in (ci - 1, ci, ci + 1):
            for j in (cj - 1, cj, cj + 1):
                for (A, B) in self.grid.get((i, j), ()):
                    kid = (id(A), id(B))
                    if kid in seen:
                        continue
                    seen.add(kid)
                    ax, az = A[0][0], A[0][2]
                    bx, bz = B[0][0], B[0][2]
                    abx, abz = bx - ax, bz - az
                    L2 = abx * abx + abz * abz
                    if L2 < 1e-12:
                        continue
                    t = ((px - ax) * abx + (pz - az) * abz) / L2
                    t = max(0.0, min(1.0, t))
                    cx, cz = ax + t * abx, az + t * abz
                    d = math.hypot(px - cx, pz - cz)
                    if d < best_d:
                        best_d = d
                        best_v = _lerp_vert(A, B, t)
        if best_v is None:
            return None, None
        return best_d, best_v


# ============================================================================================
# (1) THE APRON WELD -- snap LOWLAND grass hole-boundary verts onto the LOWLAND part of dC
#
# SURGICAL (build-fix round 1): weld only where dC is LOWLAND (nearest carried boundary height <
# apron_max). The carried valley's TALL mountain-wall boundary (>=6u, 199 of 251 boundary edges,
# measured 2.8u from the ecotone) is a MOUNTAIN-LOCKED-VALLEY exposure -- a flat grass island cannot
# weld to a 40u vertical wall foot+top, and the massif-carry apron law needs a LOWLAND window
# perimeter (which THIS window lacks). So we weld the lowland seam (correct + bounded) and leave the
# tall walls as intrinsic once-edges, isolating the true R1 blocker instead of exploding the mesh.
# ============================================================================================
def corner_snap(grass_tris, carried_tris, placed_R):
    """Round-1's base weld: snap every grass vertex sitting on a placed_R BOUNDARY grid-corner to the
    nearest carried vertex at that corner (the full seam-corner weld, ~243-once-edge floor). Applied
    BEFORE the projection weld + T-junction pass so the seam starts from its most-welded state."""
    pr = set(placed_R)
    bcorners = set()
    for (ci, cj) in pr:
        for (gi, gj) in ((ci, cj), (ci + 1, cj), (ci, cj + 1), (ci + 1, cj + 1)):
            incident = {(gi - 1, gj - 1), (gi - 1, gj), (gi, gj - 1), (gi, gj)}
            if any(ic not in pr for ic in incident):
                bcorners.add((gi, gj))
    cb = {}
    for tri in carried_tris:
        for v in tri:
            p = v[0]
            gi, gj = round(p[0] / CELL), round(p[2] / CELL)
            if (gi, gj) not in bcorners:
                continue
            d = abs(p[0] - CELL * gi) + abs(p[2] - CELL * gj)
            prev = cb.get((gi, gj))
            if prev is None or d < prev[1]:
                cb[(gi, gj)] = (p, d)
    cb = {k: v[0] for k, v in cb.items()}
    out = []
    n = 0
    for tri in grass_tris:
        nt = []
        for v in tri:
            gi, gj = round(v[0][0] / CELL), round(v[0][2] / CELL)
            tgt = cb.get((gi, gj))
            if tgt is not None and math.dist(v[0], tgt) > 1e-6:
                nt.append((tgt, v[1], v[2], v[3]))
                n += 1
            else:
                nt.append(v)
        if _tri_area2_3d(nt) > 1e-7:
            out.append(nt)
    return out, n


def weld_grass_to_boundary(grass_tris, carried_tris, reach, apron_max=6.0):
    cedges = [e for e in boundary_edges(carried_tris) if max(e[0][0][1], e[1][0][1]) < apron_max]
    idx = SegIndex(cedges)
    gbound = boundary_edges(grass_tris)
    weld_src = set()
    for (a, b) in gbound:
        mx, mz = (a[0][0] + b[0][0]) / 2.0, (a[0][2] + b[0][2]) / 2.0
        d, _ = idx.nearest_on_boundary(mx, mz, reach)
        if d is not None:
            for v in (a, b):
                weld_src.add((round(v[0][0], 3), round(v[0][1], 3), round(v[0][2], 3)))
    weld_map = {}
    welded_targets = []
    max_lift = 0.0
    for (kx, ky, kz) in weld_src:
        d, pv = idx.nearest_on_boundary(kx, kz, reach)
        if pv is None:
            continue
        weld_map[(kx, ky, kz)] = pv
        welded_targets.append(pv[0])
        max_lift = max(max_lift, abs(pv[0][1] - ky))
    out = []
    for tri in grass_tris:
        nt = []
        for v in tri:
            k = (round(v[0][0], 3), round(v[0][1], 3), round(v[0][2], 3))
            tgt = weld_map.get(k)
            if tgt is not None:
                nt.append((tgt[0], v[1], v[2], v[3]))     # move POSITION onto dC; keep grass tile attrs
            else:
                nt.append(v)
        if _tri_area2_3d(nt) > 1e-7:
            out.append(nt)
    return out, len(weld_map), max_lift, welded_targets


# ============================================================================================
# (2) THE T-JUNCTION ELIMINATION -- SEAM-ONLY, single-pass, multi-insert (bounded, no cascade)
#
# cand_points = ONLY the seam vertices (the welded grass-rim targets + the lowland dC boundary verts).
# For each triangle edge, insert EVERY cand point that lies strictly on it (colinear XZ within tol_xz,
# edge-Y within ytol), sorted by param, in ONE fan re-triangulation. Because the candidate set is FIXED
# and seam-local, interior edges (whose neighbours are not seam verts) are never touched and no split
# can cascade (an inserted vert is not itself a candidate). Bounded by |cand| * |seam edges|.
# ============================================================================================
def eliminate_tjunctions(tris, cand_points, tol_xz=0.05, ytol=0.75):
    cand_buckets = defaultdict(list)
    for P in cand_points:
        cand_buckets[(math.floor(P[0] / CELL), math.floor(P[2] / CELL))].append(P)
    n_splits = 0
    out = []
    for tri in tris:
        # find, per edge, the sorted interior cand points; split the edge with the MOST inserts (one
        # edge per tri per call keeps the fan simple; a rare 2-edge tri is caught on the extra iters
        # the caller runs). We iterate here until this tri has no splittable edge.
        work = [tri]
        done = []
        guard = 0
        while work and guard < 64:
            guard += 1
            cur = work.pop()
            best = None
            for e in range(3):
                A, B = cur[e], cur[(e + 1) % 3]
                ax, az = A[0][0], A[0][2]
                bx, bz = B[0][0], B[0][2]
                abx, abz = bx - ax, bz - az
                L2 = abx * abx + abz * abz
                if L2 < 1e-12:
                    continue
                i0, i1 = sorted((math.floor(ax / CELL), math.floor(bx / CELL)))
                j0, j1 = sorted((math.floor(az / CELL), math.floor(bz / CELL)))
                hits = []
                seen = set()
                for i in range(i0, i1 + 1):
                    for j in range(j0, j1 + 1):
                        for P in cand_buckets.get((i, j), ()):
                            kp = (round(P[0], 3), round(P[1], 3), round(P[2], 3))
                            if kp in seen:
                                continue
                            seen.add(kp)
                            t = ((P[0] - ax) * abx + (P[2] - az) * abz) / L2
                            if t <= 3e-3 or t >= 1 - 3e-3:
                                continue
                            cx, cz = ax + t * abx, az + t * abz
                            if (P[0] - cx) ** 2 + (P[2] - cz) ** 2 > tol_xz * tol_xz:
                                continue
                            ey = A[0][1] + t * (B[0][1] - A[0][1])
                            if abs(ey - P[1]) > ytol:
                                continue
                            hits.append(t)
                if hits and (best is None or len(hits) > len(best[1])):
                    best = (e, sorted(hits))
            if best is None:
                done.append(cur)
                continue
            e, ts = best
            A, B, C = cur[e], cur[(e + 1) % 3], cur[(e + 2) % 3]
            # fan the split edge: A -> M1 -> M2 -> ... -> B, each with apex C
            pts = [A] + [_lerp_vert(A, B, t) for t in ts] + [B]
            for q in range(len(pts) - 1):
                nt = [pts[q], pts[q + 1], C]
                if _tri_area2_3d(nt) > 1e-9:
                    done.append(nt)
                    if q > 0:
                        n_splits += 1
        out.extend(done)
    return out, n_splits


# ============================================================================================
# up-face enforcement for the welded apron ring (re-wind any grass tri that the apron lift turned
# downward -- worldmap terrain is up-facing; a down-wound apron tri is a shading/normal defect)
# ============================================================================================
def enforce_upface(tris, only_positions=None):
    """Re-wind (swap two verts) any triangle whose signed XZ area is <= 0 (downward). If
    `only_positions` is given (a set of XZ keys), only re-wind tris touching one of them (the apron
    ring) so genuine carried vertical faces are left verbatim. Returns (new_tris, n_flipped)."""
    out = []
    n = 0
    for tri in tris:
        a, b, c = tri[0][0], tri[1][0], tri[2][0]
        ny2 = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        touch = True
        if only_positions is not None:
            touch = any((round(v[0][0], 2), round(v[0][2], 2)) in only_positions for v in tri)
        if ny2 <= 0 and touch:
            out.append([tri[0], tri[2], tri[1]])
            n += 1
        else:
            out.append(tri)
    return out, n


# ============================================================================================
# orchestration
# ============================================================================================
def stitch(carried_by_block, host_bms, placed_R, land_height, *, weld_reach=4.6,
           tol_xz=0.05, ytol=0.75, apron_max=6.0, log=print):
    """Stitch the re-partitioned carried tris to the minted grass frame watertight.

      carried_by_block : {block: [world_tri, ...]}  (already re-partitioned at 64u borders)
      host_bms         : {block: [world grass tri, ...]}  (the full minted grass frame)
      placed_R         : set of TARGET cells the carry occupies
      land_height      : the grass flat height

    Returns (out_soup_by_block, diag). out_soup keys every touched block (carried + grass-hole ring)
    plus every untouched frame block is left to the caller (this returns ONLY touched blocks; the
    caller merges the untouched frame blocks verbatim)."""
    # 1) gather world soups
    carried_world = [tri for tris in carried_by_block.values() for tri in tris]

    def tri_cell(tri):
        cx = sum(v[0][0] for v in tri) / 3.0
        cz = sum(v[0][2] for v in tri) / 3.0
        return (math.floor(cx / CELL), math.floor(cz / CELL))

    # grass = every host tri whose cell is NOT carried (the hole is cut by CELL here; the weld then
    # pulls the hole rim onto the true conform mesh boundary dC, dissolving the cell-vs-mesh mismatch)
    grass_world = []
    for blk, soup in host_bms.items():
        for tri in soup:
            if tri_cell(tri) not in placed_R:
                grass_world.append(tri)
    log(f"  [stitch] carried={len(carried_world)} grass_kept={len(grass_world)} tris")

    # 2a) BASE CORNER WELD (round-1's full seam-corner snap: the ~243-once-edge floor)
    grass_world, n_corner = corner_snap(grass_world, carried_world, placed_R)
    log(f"  [stitch] base corner weld: {n_corner} grass boundary-corner verts snapped to dC")

    # 2b) THE APRON WELD (lowland seam only) + T-junction elimination on top
    grass_welded, n_weld, max_lift, welded_tgts = weld_grass_to_boundary(
        grass_world, carried_world, weld_reach, apron_max=apron_max)
    log(f"  [stitch] apron weld (lowland dC only): {n_weld} grass hole-rim verts snapped onto dC "
        f"(max_lift={max_lift:.3f})")

    # 3) THE T-JUNCTION ELIMINATION -- seam-only candidate set = the welded grass-rim targets + the
    #    LOWLAND dC boundary verts (the only verts that can create a seam T-junction). A fixed, seam-
    #    local candidate set cannot cascade. Split carried edges (at welded grass verts) AND grass
    #    edges (at lowland dC verts) in one bounded pass, repeated a few times for rare 2-edge tris.
    cand = list(welded_tgts)
    for (a, b) in boundary_edges(carried_world):
        if max(a[0][1], b[0][1]) < apron_max:
            cand.append(a[0]); cand.append(b[0])
    combined = carried_world + grass_welded
    n_split_total = 0
    for _ in range(4):
        combined, ns = eliminate_tjunctions(combined, cand, tol_xz=tol_xz, ytol=ytol)
        n_split_total += ns
        if ns == 0:
            break
    stitched = combined
    log(f"  [stitch] t-junction elimination (seam-only): {n_split_total} edge splits "
        f"({len(carried_world) + len(grass_welded)} -> {len(stitched)} tris)")

    # 4) up-face enforcement on the lifted apron ring only (carried vertical faces left verbatim)
    apron_xz = set()
    for pv in welded_tgts:
        apron_xz.add((round(pv[0], 2), round(pv[2], 2)))
    stitched, n_flip = enforce_upface(stitched, only_positions=apron_xz)
    log(f"  [stitch] apron up-face: {n_flip} down-wound apron tris re-wound")

    # 5) re-block by centroid, CLIPPING each tri to its centroid-block frame so a weld that pulled a
    #    grass vert a few u across a 64u border cannot poke past the block frame (the frame-bounds law).
    #    Carried tris are already in-frame (their earlier re-partition), so the clip is a no-op on them;
    #    only a poking welded-grass tri is trimmed at the border. A border clip mints a border-seam
    #    once-edge, but the block-border seam is already the tall-wall carry seam (weld-integrity is
    #    gated separately), so frame-bounds is honoured without hiding the true blocker.
    import ff9mapkit.world.transplant as TR2
    out = defaultdict(list)
    n_clip = 0
    for tri in stitched:
        cx = sum(v[0][0] for v in tri) / 3.0
        cz = sum(v[0][2] for v in tri) / 3.0
        bi = int(math.floor(cx / BLOCK))
        bj = int(math.floor(-cz / BLOCK))
        # in-frame fast path
        if all(BLOCK * bi - 0.05 <= v[0][0] <= BLOCK * (bi + 1) + 0.05
               and -BLOCK * (bj + 1) - 0.05 <= v[0][2] <= -BLOCK * bj + 0.05 for v in tri):
            out[(bi, bj)].append(tri)
            continue
        q = tri
        for (axis, plane, below) in ((0, BLOCK * bi, False), (0, BLOCK * (bi + 1), True),
                                     (2, -BLOCK * (bj + 1), False), (2, -BLOCK * bj, True)):
            q = TR2.clip_poly(q, axis, plane, below)
            if len(q) < 3:
                break
        if len(q) < 3:
            continue
        n_clip += 1
        for k in range(1, len(q) - 1):
            t3 = [q[0], q[k], q[k + 1]]
            if _tri_area2_3d(t3) > 1e-7:
                out[(bi, bj)].append(t3)
    if n_clip:
        log(f"  [stitch] frame clip: {n_clip} welded-grass tris trimmed to their block frame")

    diag = dict(n_weld=n_weld, max_lift=round(max_lift, 3), n_split=n_split_total, tj_iters=0,
                n_flip=n_flip, n_carried=len(carried_world), n_grass=len(grass_world),
                n_stitched=len(stitched), apron_verts=len(apron_xz), frame_clips=n_clip)
    return dict(out), diag
