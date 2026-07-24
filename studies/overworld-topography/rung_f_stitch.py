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


def _count_once(out_by_block):
    """Count above-skirt once-edges across a {block: world-soup} composite (seam-integrity probe)."""
    ecnt = Counter()
    for soup in out_by_block.values():
        for tri in soup:
            pts = [tuple(round(c, 3) for c in v[0]) for v in tri]
            for q in range(3):
                if pts[q] == pts[(q + 1) % 3]:
                    continue
                ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    return sum(1 for (a, b), n in ecnt.items() if n == 1 and not (a[1] <= 1e-3 and b[1] <= 1e-3))


def _reblock_soup(tris):
    """Re-block a world soup into {block: soup}, clipping border-crossing tris to their centroid block
    frame (deterministic shared cuts -> watertight across borders)."""
    import ff9mapkit.world.transplant as TR2
    out = defaultdict(list)
    for tri in tris:
        cx = sum(v[0][0] for v in tri) / 3.0
        cz = sum(v[0][2] for v in tri) / 3.0
        bi = int(math.floor(cx / BLOCK))
        bj = int(math.floor(-cz / BLOCK))
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
        for k in range(1, len(q) - 1):
            t3 = [q[0], q[k], q[k + 1]]
            if _tri_area2_3d(t3) > 1e-7:
                out[(bi, bj)].append(t3)
    return dict(out)


def _count_once_flat(tris):
    ecnt = Counter()
    for tri in tris:
        pts = [tuple(round(c, 3) for c in v[0]) for v in tri]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    return sum(1 for (a, b), n in ecnt.items() if n == 1 and not (a[1] <= 1e-3 and b[1] <= 1e-3))


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
    # EXHAUSTIVE (build-fix round 4): snap EVERY grass boundary-loop vertex within reach of dC (the
    # window perimeter), not only those whose incident-edge MIDPOINT was near dC (that detection missed
    # the seam verts sitting at the grass-lattice/stock-vert mismatch, leaving the height-mismatch seam
    # open -> the perimeter-zipper once-edges). Each vertex is snapped to its own nearest dC point below.
    weld_src = set()
    for (a, b) in gbound:
        for v in (a, b):
            d, _ = idx.nearest_on_boundary(v[0][0], v[0][2], reach)
            if d is not None:
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
# THE CONFORMING PASS (build-fix round 3) -- close EVERY residual once-edge (block-border re-partition
# T-junctions + window-perimeter grass-seam T-junctions), not just the lowland-dC seam.
#
# The defect is always the same shape: a VERTEX of one tri lies strictly interior to another tri's EDGE
# (colinear XZ, matching Y), leaving that edge single-owner. The unmatched vertices ARE exactly the
# endpoints of the current once-edges. So: iterate -- (a) census the composite's once-edges above the
# y=0 skirt, (b) take their endpoints as the candidate T-vertices, (c) split every edge that carries one
# strictly interior (per block, so inserts stay in-frame -- a border/window-perimeter split point lies on
# a block-frame edge or interior line). Repeat until the once-edge set stops shrinking. Because the
# candidate set is the CURRENT defects only, interior 2-owner ecotone edges are never touched (their
# verts are not once-edge endpoints) -> byte-rigidity + the R2 body count are preserved.
# ============================================================================================
def _once_edge_endpoints(out_by_block, add_border_verts=False, btol=1e-2):
    ecnt = Counter()
    border_verts = set()
    for soup in out_by_block.values():
        for tri in soup:
            pts = [tuple(round(c, 3) for c in v[0]) for v in tri]
            for p in pts:
                if add_border_verts and (abs(p[0] - round(p[0] / BLOCK) * BLOCK) < btol
                                         or abs(p[2] - round(p[2] / BLOCK) * BLOCK) < btol):
                    border_verts.add(p)
            for q in range(3):
                a, b = pts[q], pts[(q + 1) % 3]
                if a == b:
                    continue
                ecnt[tuple(sorted((a, b)))] += 1
    cand = set()
    n_above = 0
    for (a, b), n in ecnt.items():
        if n == 1 and not (a[1] <= 1e-3 and b[1] <= 1e-3):
            n_above += 1
            cand.add(a)
            cand.add(b)
    # ADD every vertex on a block border (the perimeter zipper: the window-rect <-> grass seam lies on
    # block borders; a border vert of one side must split the other side's border edge). Restricted to
    # once-edge endpoints' presence so an already-watertight interior border is untouched.
    if add_border_verts:
        cand |= border_verts
    return [list(p) for p in cand], n_above


def snap_to_borders(out_by_block, tol=0.25, log=print):
    """Snap every vertex within ``tol`` of a 64u block border ONTO it (the border-axis coord only,
    deterministic per world position). A phase-shifted carry lands stock verts just off the target
    borders; a vert snapped from row A and the same vert from row B agree exactly -> the two sides
    share the border profile, so the remaining border T-junctions become splittable by conform_composite
    (and a snapped vert sits ON the block frame edge -> in-frame, so frame-bounds holds). Returns
    (new_out, n_snapped, n_dropped)."""
    n_snap = n_drop = 0
    out = {}
    for blk, soup in out_by_block.items():
        ns = []
        for tri in soup:
            nt = []
            for v in tri:
                x, y, z = v[0]
                bx = round(x / BLOCK) * BLOCK
                bz = round(z / BLOCK) * BLOCK
                nx = bx if 1e-6 < abs(x - bx) <= tol else x
                nz = bz if 1e-6 < abs(z - bz) <= tol else z
                if nx != x or nz != z:
                    n_snap += 1
                    nt.append(((nx, y, nz), v[1], v[2], v[3]))
                else:
                    nt.append(v)
            if _tri_area2_3d(nt) > 1e-7:
                ns.append(nt)
            else:
                n_drop += 1
        out[blk] = ns
    log(f"  [snap-borders] {n_snap} verts snapped onto a block border (<= {tol}u); {n_drop} degenerate dropped")
    return out, n_snap, n_drop


def zipper_perimeter(out_by_block, lines, log=print, eps=0.03):
    """THE PROFILE-RAMP PERIMETER ZIPPER (build-fix round 4b). The window-rect <-> grass seam lies on
    clean block-border lines (whole-block shift). The residual once-edges are a HEIGHT MISMATCH: flat
    grass (y~3) meets the carried ecotone boundary (y~1). For each perimeter line, build the CARRIED
    (window-side) boundary Y-profile and RAMP every GRASS-side vertex on the line onto it (exact Y at its
    position; deformation to the grass, the apron law). After the ramp both sides lie on the SAME profile
    curve, so the later merge+conform coincide/split them watertight. ``lines`` = [(axis,val,win_gt)] where
    axis in {'x','z'}, val = the border coord, win_gt = the window is on the coord>val side.
    Returns (new_out, n_ramped)."""
    import bisect
    # mutable copy: each vertex = [ [x,y,z], nrm, uv, tan ] so the position can be ramped in place
    out = {blk: [[[list(v[0]), v[1], v[2], v[3]] for v in tri] for tri in soup]
           for blk, soup in out_by_block.items()}
    n_ramp = 0
    for (axis, val, win_gt) in lines:
        ai = 0 if axis == "x" else 2
        oi = 2 if axis == "x" else 0
        prof = []
        for soup in out.values():
            for tri in soup:
                cax = sum(v[0][ai] for v in tri) / 3.0
                onside = (cax > val) if win_gt else (cax < val)
                if not onside:
                    continue
                for v in tri:
                    if abs(v[0][ai] - val) < eps:
                        prof.append((round(v[0][oi], 4), v[0][1]))
        if not prof:
            continue
        prof.sort()
        os = [p[0] for p in prof]
        ys = [p[1] for p in prof]

        def py(o):
            if o <= os[0]:
                return ys[0]
            if o >= os[-1]:
                return ys[-1]
            i = bisect.bisect_left(os, o)
            if i < len(os) and os[i] == o:
                return ys[i]
            o0, o1, y0, y1 = os[i - 1], os[i], ys[i - 1], ys[i]
            return y0 + (y1 - y0) * (o - o0) / (o1 - o0) if o1 != o0 else y0

        for soup in out.values():
            for tri in soup:
                cax = sum(v[0][ai] for v in tri) / 3.0
                grass = (cax < val) if win_gt else (cax > val)
                if not grass:
                    continue
                for v in tri:
                    if abs(v[0][ai] - val) < eps:
                        ny = py(round(v[0][oi], 4))
                        if abs(v[0][1] - ny) > 1e-4 or abs(v[0][ai] - val) > 1e-9:
                            v[0][1] = ny
                            v[0][ai] = val
                            n_ramp += 1
    res = {}
    for blk, soup in out.items():
        ns = []
        for tri in soup:
            t = [(tuple(v[0]), v[1], v[2], v[3]) for v in tri]
            if _tri_area2_3d(t) > 1e-7:
                ns.append(t)
        res[blk] = ns
    log(f"  [zipper] ramped {n_ramp} grass perimeter verts onto the carried boundary Y-profile")
    return res, n_ramp


def merge_verts_global(out_by_block, tol=0.08, y_min=None, log=print):
    """Merge coincident-but-offset vertices (weld/clip float slop, 0.001..tol apart) to ONE canonical
    position so their edges are recognised as shared -> the precision micro-cracks close. A single
    canonical per spatial cluster (first-seen wins, so an already-placed vert never moves -- carried
    interior verts, seen as exact shares, cluster to themselves and do NOT move; only a seam vert that
    is <tol from an existing canonical snaps onto it). Degenerate tris (a merge collapsed two verts) are
    dropped. ``y_min`` (optional): only verts with y >= y_min participate -- a coast-safe merge that
    never touches the y~0 waterline (whose near-miss pairs are build_landmass's own, not weld defects).
    Returns (new_out, n_moved, n_dropped)."""
    grid = {}                              # coarse bucket key -> list of canonical positions

    def canon(p):
        if y_min is not None and p[1] < y_min:
            return p
        gk = (math.floor(p[0] / tol), math.floor(p[1] / tol), math.floor(p[2] / tol))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for c in grid.get((gk[0] + dx, gk[1] + dy, gk[2] + dz), ()):
                        if abs(c[0] - p[0]) <= tol and abs(c[1] - p[1]) <= tol and abs(c[2] - p[2]) <= tol:
                            return c
        grid.setdefault(gk, []).append(p)
        return p

    out = {}
    n_moved = n_drop = 0
    for blk, soup in out_by_block.items():
        ns = []
        for tri in soup:
            nt = []
            for v in tri:
                c = canon(v[0])
                if c is not v[0] and c != v[0]:
                    n_moved += 1
                    nt.append((c, v[1], v[2], v[3]))
                else:
                    nt.append((v[0] if c is v[0] else c, v[1], v[2], v[3]))
            if _tri_area2_3d(nt) > 1e-7:
                ns.append(nt)
            else:
                n_drop += 1
        out[blk] = ns
    log(f"  [merge] {n_moved} verts snapped to a canonical within {tol}u; {n_drop} degenerate tris dropped")
    return out, n_moved, n_drop


def conform_composite(out_by_block, iters=6, tol_xz=0.06, ytol=2.6, cascade_cap=1200,
                      add_border_verts=True, log=print):
    """Drive the composite's above-skirt once-edges toward 0 by T-junction elimination against the
    current once-edge endpoints. Per-block (inserts stay in-frame). CASCADE GUARD: if an iteration
    would split more than ``cascade_cap`` edges OR the once-edge count grows, ABORT and return the
    PRE-conform state (a whole-soup T-junction pass cascades on a non-conforming seam -- rung_f_build.json
    records the 77865-split dead end; with the whole-block shift there is little to do, so a runaway means
    the seam is structurally non-weldable, which the caller must see as the residual, not paper over)."""
    base = {blk: list(soup) for blk, soup in out_by_block.items()}
    out = {blk: list(soup) for blk, soup in out_by_block.items()}
    hist = []
    total_split = 0
    aborted = False
    for it in range(iters):
        cand, n_above = _once_edge_endpoints(out, add_border_verts=add_border_verts)
        hist.append(n_above)
        if n_above == 0:
            break
        if not cand:
            break
        if it > 0 and n_above > hist[0]:                # growing -> cascade; abort to pre-conform state
            log(f"  [conform] iter {it}: once-edges GREW to {n_above} (>{hist[0]}) -> ABORT (cascade), revert")
            aborted = True
            break
        made = 0
        trial = {}
        for blk, soup in out.items():
            new, ns = eliminate_tjunctions(soup, cand, tol_xz=tol_xz, ytol=ytol)
            trial[blk] = new
            made += ns
        if made > cascade_cap:
            log(f"  [conform] iter {it}: {n_above} once-edges -> {made} splits > cap {cascade_cap} -> "
                f"ABORT (cascade), revert to pre-conform")
            aborted = True
            break
        out = trial
        total_split += made
        log(f"  [conform] iter {it}: {n_above} once-edges above skirt -> {made} splits")
        if made == 0:
            break
    if aborted:
        out = base
    _, n_final = _once_edge_endpoints(out)
    log(f"  [conform] {total_split} total splits; once-edges above skirt {hist[0] if hist else 0} -> "
        f"{n_final}{' (ABORTED-cascade, reverted)' if aborted else ''}")
    return out, dict(iters=len(hist), splits=total_split, once_before=(hist[0] if hist else 0),
                     once_after=n_final, aborted=aborted, history=hist)


# ============================================================================================
# THE TILING STITCH (rebuild attempt 2) -- watertight BY CONSTRUCTION
#
# Root cause of attempt 1's plateau (rung_f_diag_seam2): the heuristic apron-weld + T-junction +
# conform leaves ~30 once-edges because it tries to reconcile a 4u grass staircase rim with an off-grid
# blob outline in-place. THE FIX: (a) ear-clip the blob's interior holes (rung_f_holefill, done in
# layout.carry), and (b) DILATE the grass removal by 1 cell so the grass rim recedes off the blob (and
# off the block borders -> no zero-width degenerate seam), then TILE the annulus between the grass rim
# loop A and the blob outline loop B with a triangle strip that uses EXACTLY the A and B verts. The
# result shares every seam vertex bit-for-bit -> ZERO once-edges above the skirt by construction. No
# corner-snap, no projection weld, no merge that drops tris, no capped conform.
# ============================================================================================
def stitch_tile(carried_by_block, host_bms, placed_R, grass_remove, land_height, grass_id, grass_uv,
                *, log=print):
    import rung_f_holefill as HF
    import ff9mapkit.world.transplant as TR2

    def tri_cell(tri):
        cx = sum(v[0][0] for v in tri) / 3.0
        cz = sum(v[0][2] for v in tri) / 3.0
        return (math.floor(cx / CELL), math.floor(cz / CELL))

    carried_world = [tri for tris in carried_by_block.values() for tri in tris]
    grass_world = []
    for blk, soup in host_bms.items():
        for tri in soup:
            if tri_cell(tri) not in grass_remove:
                grass_world.append(tri)
    log(f"  [tile-stitch] carried={len(carried_world)} grass_kept={len(grass_world)} tris "
        f"(grass_remove={len(grass_remove)} cells)")

    # EAR-CLIP the blob's INTERIOR holes (the extra above-skirt loops beyond the outer outline) using
    # the blob's OWN exact boundary verts -> watertight to the blob by construction. Done here (post-
    # re-partition, same directed-half-edge extraction as the tile) so the hole count is exact.
    bloops = HF.above_skirt_loops(carried_world)
    n_holes = 0
    if len(bloops) > 1:
        for h in bloops[1:]:
            ft = HF.fill_loop(h, grass_id, grass_uv)
            carried_world.extend(ft)
            n_holes += 1
        log(f"  [tile-stitch] filled {n_holes} interior blob holes -> {len(carried_world)} blob tris")
        bloops = HF.above_skirt_loops(carried_world)
        if len(bloops) > 1:
            log(f"  [tile-stitch] WARN {len(bloops)-1} interior blob loops REMAIN after fill")

    # A = the grass hole rim (largest above-skirt boundary loop of the grass frame)
    gloops = HF.above_skirt_loops(grass_world)
    if not gloops or not bloops:
        log(f"  [tile-stitch] MISSING LOOP: grass_loops={len(gloops)} blob_loops={len(bloops)} -- abort tile")
        combined = carried_world + grass_world
        tiling = []
        n_extra_g = n_extra_b = 0
    else:
        A = gloops[0]
        B = bloops[0]
        n_extra_g = len(gloops) - 1
        n_extra_b = len(bloops) - 1
        if n_extra_g or n_extra_b:
            log(f"  [tile-stitch] NOTE extra above-skirt loops: grass +{n_extra_g}, blob +{n_extra_b} "
                f"(should be 0 after hole-fill + dilation)")
        tiling = HF.contour_tile(A, B, grass_id, grass_uv, log=log)
        combined = carried_world + grass_world + tiling

    # EXCISE + REFILL local defects (missing donor tris / stock near-duplicate verts in the flat-grass
    # fill -- an un-splittable T-junction cluster) on the WORLD soup (before block-splitting, so the
    # geometric once-edges are true). Watertight refill from the exposed hole's own boundary verts.
    combined, n_excised, n_refill = HF.excise_and_refill(combined, grass_id, grass_uv, log=log)
    log(f"  [tile-stitch] excise+refill: excised {n_excised} defect tris, refilled {n_refill} tris; "
        f"world once-edges now {_count_once_flat(combined)}")

    # re-block by centroid, clipping each tri to its centroid block frame (deterministic shared cuts ->
    # a tri crossing a block border is split identically on both sides -> watertight across borders).
    out = defaultdict(list)
    n_clip = 0
    for tri in combined:
        cx = sum(v[0][0] for v in tri) / 3.0
        cz = sum(v[0][2] for v in tri) / 3.0
        bi = int(math.floor(cx / BLOCK))
        bj = int(math.floor(-cz / BLOCK))
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
    log(f"  [tile-stitch] frame clip: {n_clip} border-crossing tris re-partitioned; once-edges="
        f"{_count_once(out)}")

    # DROP DEGENERATE (zero XZ-area, collinear) tris FIRST. The re-block fast-path admits in-frame slivers
    # without an area check; some are DEGENERATE T-JUNCTION CAPS on the block borders (a zero-area tri
    # capping a grass-frame border edge against an off-grid tiling vert) -- they keep the mesh watertight
    # but read as "down-facing" (ny2==0). Dropping them EXPOSES the underlying T-junction as a once-edge,
    # which the conform below then splits into REAL geometry (the grass edge split at the tiling vert).
    n_deg = 0
    for blk in out:
        ns = []
        for tri in out[blk]:
            a, b, c = tri[0][0], tri[1][0], tri[2][0]
            ny2 = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
            # drop only INLAND degenerates (all verts >= 0.5u above the skirt) -- a coast-ramp degenerate
            # is left to build_landmass's own coast (dropping it minted hairline coast near-miss pairs).
            if abs(ny2) < 1e-6 and min(a[1], b[1], c[1]) >= 0.5:
                n_deg += 1
                continue
            ns.append(tri)
        out[blk] = ns
    log(f"  [tile-stitch] dropped {n_deg} inland degenerate slivers; once-edges now {_count_once(out)}")

    # T-JUNCTION CLOSURE: split every grass/border edge carrying an above-skirt once-edge endpoint (the
    # exposed T-junctions + any fan/grid seam). Bounded (candidate set = current defects); if it cannot
    # close a border T-junction cleanly, EXCISE+REFILL the local spot.
    n0 = _count_once(out)
    if n0 > 0:
        out, cdiag = conform_composite(out, iters=8, tol_xz=0.06, ytol=0.75, cascade_cap=400,
                                       add_border_verts=False, log=log)
        if _count_once(out) > 0:
            flat = [t for s in out.values() for t in s]
            flat, _ne, _nf = HF.excise_and_refill(flat, grass_id, grass_uv, log=log)
            out = _reblock_soup(flat)
        log(f"  [tile-stitch] once-edges after T-junction closure: {_count_once(out)}")
    else:
        cdiag = dict(iters=0, splits=0, once_before=0, once_after=0, aborted=False, history=[])

    # UP-FACE the grass frame / tiling apron / fill (the build's down_grass population = cells NOT in
    # placed_R); the carried ecotone's faithful stock down-facing is left verbatim.
    n_flip = n_deg2 = 0
    for blk in out:
        ns = []
        for tri in out[blk]:
            a, b, c = tri[0][0], tri[1][0], tri[2][0]
            ny2 = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
            if abs(ny2) < 1e-6 and min(a[1], b[1], c[1]) >= 0.5:
                n_deg2 += 1
                continue
            cx = sum(v[0][0] for v in tri) / 3.0
            cz = sum(v[0][2] for v in tri) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            if ny2 < 0 and cell not in placed_R:
                ns.append([tri[0], tri[2], tri[1]])
                n_flip += 1
            else:
                ns.append(tri)
        out[blk] = ns
    log(f"  [tile-stitch] apron up-face: {n_flip} re-wound, {n_deg2} degenerate dropped; once-edges "
        f"{_count_once(out)}")

    diag = dict(n_weld=len(tiling), max_lift=0.0, n_split=cdiag.get("splits", 0), tj_iters=0, n_flip=n_flip,
                n_carried=len(carried_world), n_grass=len(grass_world), n_stitched=len(combined),
                apron_verts=len(tiling), frame_clips=n_clip, merge_moved=0, merge_dropped=0,
                conform=cdiag,
                tiling_tris=len(tiling), extra_grass_loops=n_extra_g, extra_blob_loops=n_extra_b)
    return dict(out), diag


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

    # 6) WATERTIGHT CLOSURE (whole-block shift -> internal borders already watertight; only the outer
    #    3x2 perimeter seam needs it): PROFILE-RAMP ZIPPER (ramp grass perimeter verts onto the carried
    #    boundary Y-profile so the height mismatch vanishes) -> gentle merge of precision slop -> conform
    #    residual T-junctions (cascade-guarded) -> final merge.
    pr = set(placed_R)
    cxs = [c[0] for c in pr]
    czs = [c[1] for c in pr]
    lines = [("x", min(cxs) * CELL, True), ("x", (max(cxs) + 1) * CELL, False),
             ("z", (min(czs)) * CELL, True), ("z", (max(czs) + 1) * CELL, False)]
    log(f"  [stitch] once-edges after frame-clip: {_count_once(out)}")
    out, n_zip = zipper_perimeter(dict(out), lines, log=log)
    log(f"  [stitch] once-edges after zipper: {_count_once(out)}")
    out, n_moved, n_dropm = merge_verts_global(out, tol=0.05, log=log)
    log(f"  [stitch] once-edges after merge1: {_count_once(out)}")
    out, cdiag = conform_composite(out, log=log)
    log(f"  [stitch] once-edges after conform: {_count_once(out)}")
    out, n_moved2, n_dropm2 = merge_verts_global(out, tol=0.05, log=log)   # close lerp slop the splits mint
    log(f"  [stitch] once-edges after merge2: {_count_once(out)}")

    diag = dict(n_weld=n_weld, max_lift=round(max_lift, 3), n_split=n_split_total, tj_iters=0,
                n_flip=n_flip, n_carried=len(carried_world), n_grass=len(grass_world),
                n_stitched=len(stitched), apron_verts=len(apron_xz), frame_clips=n_clip,
                merge_moved=n_moved + n_moved2, merge_dropped=n_dropm + n_dropm2, conform=cdiag)
    return dict(out), diag
