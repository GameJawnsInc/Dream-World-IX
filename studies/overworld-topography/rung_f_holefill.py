"""RUNG F HOLE-FILL (2026-07-24, rebuild attempt 2).

THE ROOT-CAUSE FIX for attempt 1's 64 residual once-edges. The seam diagnostic (rung_f_diag_seam2 /
rung_f_diag_holes) proved the round-4 "perimeter zipper" story WRONG: only 6 of 64 once-edges are on
block borders; 51 are GRASS-side (y>2.5) edges with NO opposing vertex -- the rims of 14 STRANDED grass
patches at "missing" cells (cells the donor mesh never triangulated) ENCLOSED by the carried blob.

The carried blob = the kept verbatim ecotone tris + the dropped-feature grass-fill tris. It is watertight
INTERNALLY (kept and dropped share exact donor edges), so its ONLY boundary loops are (a) the OUTER donor
land outline and (b) the small INTERIOR HOLES around those enclosed missing cells. Attempt 1 left the
interior holes open (a 4u grass patch stranded inside the blob whose rim never welds to the off-grid donor
boundary) and tried to weld the stranded grass -- it plateaued at 64.

THE FIX (watertight BY CONSTRUCTION): EAR-CLIP each interior hole loop using the blob's OWN exact boundary
verts (same transformed donor positions the carried tris already carry -> the fill shares every boundary
vertex bit-for-bit -> zero new once-edges), clothe the fill flat grass keeping each boundary vert's own Y,
and REMOVE the stranded grass at the enclosed cells. This dissolves 56 of the 64 once-edges by
construction, leaving only the single clean OUTER blob<->grass-frame seam for the stitch to weld.

READ-ONLY vs the game install. Pure in-memory geometry.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict, deque

CELL = 4.0
NEI4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _key(v):
    return (round(v[0][0], 3), round(v[0][1], 3), round(v[0][2], 3))


def boundary_edges(tris):
    """The once-owned (boundary) edges of a triangle soup, each as (vertA, vertB) full verts."""
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


def _signed_area_xz(poly_pts):
    a = 0.0
    n = len(poly_pts)
    for i in range(n):
        x1, _, z1 = poly_pts[i]
        x2, _, z2 = poly_pts[(i + 1) % n]
        a += x1 * z2 - x2 * z1
    return 0.5 * a


def _key3(v):
    return (round(v[0][0], 3), round(v[0][1], 3), round(v[0][2], 3))


def directed_boundary_halfedges(tris):
    """Extract DIRECTED boundary half-edges from the triangle winding: an interior edge appears once in
    each direction (net 0); a boundary edge has a net direction (the way it winds in its owning tri). A
    directed representation is robust at junction vertices (two loops sharing a vertex keep their own
    orientation) where an undirected walk would cross loops. Returns (outgoing, vert_of):
      outgoing : {tail_key: [head_key, ...]}   (net boundary half-edges, with multiplicity)
      vert_of  : {key: full vert}"""
    cnt = Counter()
    vert_of = {}
    for tri in tris:
        for q in range(3):
            a, b = tri[q], tri[(q + 1) % 3]
            ka, kb = _key3(a), _key3(b)
            if ka == kb:
                continue
            cnt[(ka, kb)] += 1
            vert_of[ka] = a
            vert_of[kb] = b
    outgoing = defaultdict(list)
    for (ka, kb), n in cnt.items():
        net = n - cnt.get((kb, ka), 0)
        for _ in range(net):
            outgoing[ka].append(kb)
    return outgoing, vert_of


def _link_loops(outgoing, vert_of):
    """Walk directed half-edges tail->head into closed loops. Consumes each half-edge once; at a junction
    (multiple outgoing) pops the last (the specific choice is immaterial -- every half-edge is consumed
    into SOME loop, and the caller keys on area/height, not identity). Returns list of full-vert loops."""
    og = {k: list(v) for k, v in outgoing.items()}
    loops = []
    starts = [k for k, v in og.items() if v]
    for s in starts:
        while og.get(s):
            loop = [s]
            cur = og[s].pop()
            guard = 0
            while cur != s and guard < 1000000:
                guard += 1
                loop.append(cur)
                nxts = og.get(cur)
                if not nxts:
                    break
                cur = nxts.pop()
            if cur == s and len(loop) >= 3:
                loops.append([vert_of[k] for k in loop])
    return loops


def boundary_loops(tris):
    """Robust boundary-loop extraction via directed half-edges (junction-safe)."""
    outgoing, vert_of = directed_boundary_halfedges(tris)
    return _link_loops(outgoing, vert_of)


def _pt_in_tri_xz(p, a, b, c, eps=1e-9):
    def sgn(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[2] - p3[2]) - (p2[0] - p3[0]) * (p1[2] - p3[2])
    d1 = sgn(p, a, b)
    d2 = sgn(p, b, c)
    d3 = sgn(p, c, a)
    has_neg = (d1 < -eps) or (d2 < -eps) or (d3 < -eps)
    has_pos = (d1 > eps) or (d2 > eps) or (d3 > eps)
    return not (has_neg and has_pos)


def earclip_xz(loop):
    """Ear-clip a simple polygon (list of full verts) in the XZ plane. Returns a list of triangles
    (each a triple of the ORIGINAL full verts -> the fill shares every boundary vertex bit-for-bit).
    Emits up-facing tris (ny2>0). Robust to a stalled remainder (bails, leaving that sliver unfilled --
    reported by the caller's once-edge measurement, never silently)."""
    verts = list(loop)
    # de-dup consecutive identical (a loop walk can repeat the closing vertex)
    dd = []
    for v in verts:
        if not dd or _key(v) != _key(dd[-1]):
            dd.append(v)
    verts = dd
    if len(verts) < 3:
        return []
    pts = [v[0] for v in verts]
    if _signed_area_xz(pts) < 0:
        verts.reverse()
    idx = list(range(len(verts)))
    out = []
    guard = 0
    while len(idx) > 3 and guard < 20000:
        guard += 1
        n = len(idx)
        ear = False
        for k in range(n):
            i0, i1, i2 = idx[(k - 1) % n], idx[k], idx[(k + 1) % n]
            a, b, c = verts[i0][0], verts[i1][0], verts[i2][0]
            # convex vertex (CCW loop): cross of (b-a)x(c-b) z-component > 0
            cross = (b[0] - a[0]) * (c[2] - b[2]) - (b[2] - a[2]) * (c[0] - b[0])
            if cross <= 1e-12:
                continue
            clean = True
            for m in idx:
                if m in (i0, i1, i2):
                    continue
                if _pt_in_tri_xz(verts[m][0], a, b, c):
                    clean = False
                    break
            if clean:
                out.append(_upface(verts[i0], verts[i1], verts[i2]))
                idx.pop(k)
                ear = True
                break
        if not ear:
            break
    if len(idx) == 3:
        out.append(_upface(verts[idx[0]], verts[idx[1]], verts[idx[2]]))
    return out


def _clothe(v, grass_id, grass_uv):
    return (v[0], (0.0, 1.0, 0.0), grass_uv, (grass_id, 1.0, 0.0, 0.0))


def fill_loop(loop, grass_id, grass_uv):
    """Triangulate an interior hole loop, clothed flat grass, sharing every loop edge -> watertight to
    the blob by construction. Tries ear-clip; if it stalls on a thin/degenerate sliver (returns fewer
    than len-2 tris), falls back to a CENTROID FAN (a new interior vertex + one tri per loop edge -- the
    loop edges are still each used once here and once by the blob boundary tri opposite -> 2-owned).
    Every emitted tri is up-faced."""
    dd = []
    for v in loop:
        if not dd or _key3(v) != _key3(dd[-1]):
            dd.append(v)
    if len(dd) < 3:
        return []
    tris = earclip_xz(dd)
    if len(tris) >= len(dd) - 2:
        return [[_clothe(v, grass_id, grass_uv) for v in t] for t in tris]
    # fallback: centroid fan
    n = len(dd)
    cx = sum(v[0][0] for v in dd) / n
    cy = sum(v[0][1] for v in dd) / n
    cz = sum(v[0][2] for v in dd) / n
    cvert = ((cx, cy, cz), (0.0, 1.0, 0.0), grass_uv, (grass_id, 1.0, 0.0, 0.0))
    out = []
    for i in range(n):
        a = _clothe(dd[i], grass_id, grass_uv)
        b = _clothe(dd[(i + 1) % n], grass_id, grass_uv)
        t = _upface(cvert, a, b)
        if _tri_area2(t) > 1e-9:
            out.append(t)
    return out


def _tri_area2(t3):
    (ax, ay, az) = t3[0][0]
    ux, uy, uz = (t3[1][0][0] - ax, t3[1][0][1] - ay, t3[1][0][2] - az)
    vx, vy, vz = (t3[2][0][0] - ax, t3[2][0][1] - ay, t3[2][0][2] - az)
    cx, cy, cz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    return math.sqrt(cx * cx + cy * cy + cz * cz)


def _upface(a, b, c):
    ny2 = (b[0][2] - a[0][2]) * (c[0][0] - a[0][0]) - (b[0][0] - a[0][0]) * (c[0][2] - a[0][2])
    return [a, c, b] if ny2 <= 0 else [a, b, c]


def enclosed_missing_cells(placed_R):
    """Given the set of TARGET cells the carry occupies, flood the 'outside' from the bbox padding ring
    through non-placed cells; a non-placed cell not reached is ENCLOSED (a stranded grass hole). Returns
    the set of enclosed cells (to be removed from the grass frame + filled by the ear-clip)."""
    pr = set(placed_R)
    cxs = [c[0] for c in pr]
    czs = [c[1] for c in pr]
    x0, x1, z0, z1 = min(cxs) - 1, max(cxs) + 1, min(czs) - 1, max(czs) + 1
    outside = set()
    dq = deque()
    for cx in range(x0, x1 + 1):
        for cz in (z0, z1):
            if (cx, cz) not in outside:
                outside.add((cx, cz)); dq.append((cx, cz))
    for cz in range(z0, z1 + 1):
        for cx in (x0, x1):
            if (cx, cz) not in outside:
                outside.add((cx, cz)); dq.append((cx, cz))
    while dq:
        c = dq.popleft()
        for di, dj in NEI4:
            n = (c[0] + di, c[1] + dj)
            if x0 <= n[0] <= x1 and z0 <= n[1] <= z1 and n not in outside and n not in pr:
                outside.add(n); dq.append(n)
    enclosed = set()
    for cx in range(x0 + 1, x1):
        for cz in range(z0 + 1, z1):
            if (cx, cz) not in pr and (cx, cz) not in outside:
                enclosed.add((cx, cz))
    return enclosed


def _once_edges_above(tris, y_skirt=1e-3):
    ecnt = Counter()
    for tri in tris:
        pts = [_key3(v) for v in tri]
        for q in range(3):
            if pts[q] == pts[(q + 1) % 3]:
                continue
            ecnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    return {e for e, n in ecnt.items() if n == 1 and not (e[0][1] <= y_skirt and e[1][1] <= y_skirt)}


def _near_miss_verts(tris, near_tol=0.02, y_min=0.5):
    """Above-skirt vertex positions that have a DISTINCT neighbour within near_tol (a weld-audit hairline
    crack: stock-donor near-duplicate verts). Spatial-hashed. Coast (y<y_min) excluded."""
    grid = defaultdict(list)
    allp = set()
    for tri in tris:
        for v in tri:
            p = _key3(v)
            if p[1] >= y_min:
                allp.add(p)
    for p in allp:
        grid[(math.floor(p[0] / near_tol), math.floor(p[1] / near_tol), math.floor(p[2] / near_tol))].append(p)
    bad = set()
    for p in allp:
        gk = (math.floor(p[0] / near_tol), math.floor(p[1] / near_tol), math.floor(p[2] / near_tol))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in grid.get((gk[0] + dx, gk[1] + dy, gk[2] + dz), ()):
                        if q != p and (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 < near_tol * near_tol:
                            bad.add(p)
                            bad.add(q)
    return bad


def excise_and_refill(tris, grass_id, grass_uv, rounds=4, max_span=32.0, near_tol=0.02, log=print):
    """Heal messy LOCAL defects (a missing donor tri / stock near-duplicate verts in the flat-grass fill
    region -- an un-splittable T-junction cluster OR a weld-audit hairline crack) by EXCISING the tris
    that own an above-skirt once-edge OR touch a near-miss vertex pair, then EAR-CLIP re-filling the small
    clean holes that exposes (from the remaining mesh's own boundary verts -> watertight + no near-
    duplicates by construction). Iterated a few rounds. Only SMALL interior holes (bbox span <= max_span)
    are refilled, so the outer coast / blob outline is never touched. Returns (new_tris, n_excised,
    n_fill)."""
    cur = list(tris)
    n_excised_tot = n_fill_tot = 0
    for _r in range(rounds):
        once = _once_edges_above(cur)
        nm = _near_miss_verts(cur, near_tol=near_tol) if near_tol else set()
        if not once and not nm:
            break
        keep = []
        n_ex = 0
        for tri in cur:
            pts = [_key3(v) for v in tri]
            owns = any(tuple(sorted((pts[q], pts[(q + 1) % 3]))) in once for q in range(3))
            touches_nm = any(p in nm for p in pts)
            if owns or touches_nm:
                n_ex += 1
            else:
                keep.append(tri)
        # the holes exposed by excision = the small above-skirt boundary loops of `keep`
        loops = above_skirt_loops(keep)
        fill = []
        n_f = 0
        for lp in loops:
            xs = [v[0][0] for v in lp]
            zs = [v[0][2] for v in lp]
            if (max(xs) - min(xs)) <= max_span and (max(zs) - min(zs)) <= max_span:
                ft = fill_loop(lp, grass_id, grass_uv)
                fill.extend(ft)
                if ft:
                    n_f += 1
        cur = keep + fill
        n_excised_tot += n_ex
        n_fill_tot += len(fill)
        log(f"  [excise] round {_r}: {len(once)} once-edges + {len(nm)} near-miss verts -> excised {n_ex} "
            f"tris, refilled {n_f} holes ({len(fill)} tris); once now {len(_once_edges_above(cur))}, "
            f"near-miss now {len(_near_miss_verts(cur, near_tol=near_tol)) if near_tol else 0}")
        if n_ex == 0:
            break
    return cur, n_excised_tot, n_fill_tot


def dilate(cells, n=1):
    """Grow a cell set by n 4-connected rings."""
    cur = set(cells)
    for _ in range(n):
        add = set()
        for c in cur:
            for di, dj in NEI4:
                add.add((c[0] + di, c[1] + dj))
        cur |= add
    return cur


def above_skirt_loops(tris, y_skirt=1e-3):
    """Boundary loops whose verts are ALL above the y=0 sea skirt (the land-interior seams, i.e. the
    grass hole rim or the blob outline -- NOT the true coast at y=0). Returns loops sorted by |XZ area|
    descending."""
    loops = boundary_loops(tris)
    out = []
    for lp in loops:
        if all(v[0][1] > y_skirt for v in lp):
            out.append(lp)
    out.sort(key=lambda lp: -abs(_signed_area_xz([v[0] for v in lp])))
    return out


def contour_tile(A, B, grass_id, grass_uv, log=print):
    """Tile the ANNULUS between an OUTER loop A (the grass hole rim, ~4u lattice, y~land_height) and an
    INNER loop B (the blob outline dC, off-grid, y~lowland) with a triangle strip that uses EXACTLY the
    verts of A and B -> watertight to BOTH the grass frame (shares every A vert) and the blob (shares
    every B vert) BY CONSTRUCTION. Greedy min-diagonal advance (the classic contour-tiling method);
    both loops oriented CCW so the strip does not twist. Emits up-facing grass tris (the apron ramp from
    y~3 down to y~1). Returns the fill tris."""
    A = list(A); B = list(B)
    if len(A) < 3 or len(B) < 3:
        return []
    if _signed_area_xz([v[0] for v in A]) < 0:
        A = A[::-1]
    if _signed_area_xz([v[0] for v in B]) < 0:
        B = B[::-1]
    na, nb = len(A), len(B)

    def d2(p, q):
        return (p[0] - q[0]) ** 2 + (p[2] - q[2]) ** 2

    # anchor: A[0] to its nearest B vertex
    j0 = min(range(nb), key=lambda j: d2(A[0][0], B[j][0]))
    i = j = 0
    tris = []
    while i < na or j < nb:
        ai = A[i % na]
        an = A[(i + 1) % na]
        bj = B[(j0 + j) % nb]
        bn = B[(j0 + j + 1) % nb]
        adv_a = i < na
        adv_b = j < nb
        cost_a = d2(an[0], bj[0]) if adv_a else float("inf")   # advance A: new tri (ai,an,bj)
        cost_b = d2(ai[0], bn[0]) if adv_b else float("inf")   # advance B: new tri (ai,bj,bn)
        if cost_a <= cost_b:
            tris.append(_mk_grass(ai, an, bj, grass_id, grass_uv))
            i += 1
        else:
            tris.append(_mk_grass(ai, bj, bn, grass_id, grass_uv))
            j += 1
    log(f"  contour-tile: annulus A({na}) <-> B({nb}) -> {len(tris)} apron fill tris")
    return tris


def _mk_grass(a, b, c, grass_id, grass_uv):
    """Up-facing tri from three full verts, clothed flat grass (position/Y kept from the loop verts so
    the tri welds to A and B). Grass tile attributes on all three."""
    va = (a[0], (0.0, 1.0, 0.0), grass_uv, (grass_id, 1.0, 0.0, 0.0))
    vb = (b[0], (0.0, 1.0, 0.0), grass_uv, (grass_id, 1.0, 0.0, 0.0))
    vc = (c[0], (0.0, 1.0, 0.0), grass_uv, (grass_id, 1.0, 0.0, 0.0))
    return _upface(va, vb, vc)


def fill_interior_holes(carried_world, fill_world, placed_R, grass_id, grass_uv, log=print):
    """Ear-clip every INTERIOR hole loop of the blob (carried ecotone + dropped-cell fill) and return the
    new fill tris (flat-grass clothed, boundary-vert Y kept -> welds to the blob boundary by construction)
    plus the set of enclosed cells to remove from the grass frame. The OUTER loop (max |XZ area|) is left
    for the grass-frame stitch."""
    blob = list(carried_world) + list(fill_world)
    loops = boundary_loops(blob)
    if not loops:
        return [], set()
    areas = [abs(_signed_area_xz([v[0] for v in lp])) for lp in loops]
    outer_i = max(range(len(loops)), key=lambda i: areas[i])
    holes = [lp for i, lp in enumerate(loops) if i != outer_i]
    earfill = []
    n_holes_filled = 0
    for lp in holes:
        tris = earclip_xz(lp)
        for t in tris:
            new = []
            for v in t:
                # flat-grass clothing; KEEP the boundary vertex's exact position (incl Y) -> shares
                new.append((v[0], (0.0, 1.0, 0.0), grass_uv, (grass_id, 1.0, 0.0, 0.0)))
            earfill.append(new)
        if tris:
            n_holes_filled += 1
    enclosed = enclosed_missing_cells(placed_R)
    log(f"  hole-fill: {len(loops)} boundary loops (outer + {len(holes)} interior holes); "
        f"ear-clipped {n_holes_filled} holes -> {len(earfill)} fill tris; {len(enclosed)} enclosed cells "
        f"to un-grass")
    return earfill, enclosed
