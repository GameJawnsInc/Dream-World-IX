"""Route geometry: walkability sweeps for scripted walk lines (rung 4 of the
behavior-tree study; promoted from ``tools/field_layout_probe.py``).

FF9 walkers move STRAIGHT at their target and slide on contact — there is NO
pathfinding. A walk leg that leaves the walkmesh means the walker jams against
the boundary (concave notches wedge; convex obstacles slide, ugly but alive —
the ``laying-out-ff9-fields`` skill's movement laws). These helpers sweep a
polyline against a :class:`~ff9mapkit.scene.bgi.BgiWalkmesh` so patrol rings,
marches, and flee lines are verified OFFLINE — both the layout probe and
``behavior lint`` run the same sweep.

:func:`sweep_pursuit` extends the same idea to the DYNAMIC feeds (``chase`` /
``wander``), whose target is only known at runtime: instead of one authored line
it sweeps the whole FAMILY of legs the engagement gate admits. Grounded in the
Path-B study (`studies/behavior-trees/pathb/`), which measured that straight-line
pursuit only jams above ~900u on a concave field — so the family, bounded by the
branch's own ``near`` radius, is the thing worth checking.
"""
from __future__ import annotations

import math

WALL_CLEARANCE_W = 48.0        # the player controller radius (cam.COLLISION_RADIUS_W)
MIN_RATE_PAIRS = 200           # below this, report COUNTS -- a rate off 20 pairs is noise


def boundary_edges_xz(verts, tris) -> list:
    """Walkmesh boundary edges (edges on exactly one triangle) as ((x,z),(x,z)) world pairs."""
    count: dict = {}
    for tri in tris:
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        for u, v in ((a, b), (b, c), (c, a)):
            if u == v:
                continue
            key = (v, u) if u > v else (u, v)
            count[key] = count.get(key, 0) + 1
    n = len(verts)
    return [((verts[a][0], verts[a][2]), (verts[b][0], verts[b][2]))
            for (a, b), c in count.items() if c == 1 and 0 <= a < n and 0 <= b < n]


def mesh_boundary_edges(wmesh) -> list:
    """Collision-WALL edges of a :class:`BgiWalkmesh` as ((x,z),(x,z)) world pairs.

    SEAM-AWARE: an edge with a triangle neighbor across it (``t.nbr[k] >= 0``) is
    an interior edge or a cross-floor SEAM the walker crosses freely -- the same
    authority :meth:`BgiWalkmesh.distance_to_boundary` uses. Multi-floor meshes
    keep DISJOINT per-floor vertex sets, so the raw exactly-one-triangle count
    (:func:`boundary_edges_xz`) calls every seam a wall and the sweep emits
    phantom near-edge warnings on clear routes. Falls back to the raw count for
    meshes that carry no neighbor data."""
    from .bgi import SLOT_PAIRS
    wv = wmesh.world_verts()
    tris = list(wmesh.tris)
    if not all(len(getattr(t, "nbr", ()) or ()) >= 3 for t in tris):
        return boundary_edges_xz(wv, [tuple(t.vtx) for t in tris])
    n = len(wv)
    edges = []
    for t in tris:
        for k in range(3):
            if t.nbr[k] >= 0:                    # neighbor across this edge -> not a wall
                continue
            i, j = SLOT_PAIRS[k]
            a, b = int(t.vtx[i]), int(t.vtx[j])
            if a == b or not (0 <= a < n and 0 <= b < n):
                continue
            edges.append(((wv[a][0], wv[a][2]), (wv[b][0], wv[b][2])))
    return edges


def seg_dist_xz(px, pz, a, b) -> float:
    """Distance from point (px, pz) to segment a->b in the XZ plane."""
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    cx, cz = ax + t * dx, az + t * dz
    return math.hypot(px - cx, pz - cz)


def sweep_polyline(points, wmesh, bedges=None, *, closed=False, step=40.0) -> list:
    """Sample every leg of a polyline ~every ``step`` units against the walkmesh.

    Returns per-leg dicts ``{a, b, len, spans, minwall}`` — ``spans`` is a list of
    ``(t0, t1)`` OFF-MESH parameter intervals (a walker on that leg jams);
    ``minwall`` is the minimum boundary distance over the on-mesh samples (None
    when the whole leg is off-mesh or ``bedges`` is empty). ``bedges`` defaults
    to :func:`mesh_boundary_edges`."""
    if bedges is None:
        bedges = mesh_boundary_edges(wmesh) if wmesh is not None else []
    pts = [tuple(p) for p in points]
    if closed and pts:
        pts = pts + [pts[0]]
    legs = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(2, int(L / step))
        spans, cur, minwall = [], None, None
        for k in range(n + 1):
            t = k / n
            x, z = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            on = wmesh is not None and wmesh.point_on_walkmesh(x, z) is not None
            if not on:
                cur = [t, t] if cur is None else [cur[0], t]
            else:
                if cur is not None:
                    spans.append(tuple(cur))
                    cur = None
                if bedges:
                    d = min(seg_dist_xz(x, z, e0, e1) for e0, e1 in bedges)
                    minwall = d if minwall is None else min(minwall, d)
        if cur is not None:
            spans.append(tuple(cur))
        legs.append({"a": a, "b": b, "len": L, "spans": spans, "minwall": minwall})
    return legs


def _raster_on_mesh(wmesh, step: float) -> set:
    """Grid cells (gi, gj) whose CENTRE lies on the walkmesh, at ``step`` resolution.

    Rasterises each triangle over its own bbox cells (O(area/step^2) total) instead of
    testing every cell against every triangle -- ``point_on_walkmesh`` is O(tris) per
    call, which a pair sweep cannot afford."""
    from .bgi import _pt_in_tri_xz
    wv = wmesh.world_verts()
    on = set()
    for t in wmesh.tris:
        a, b, c = wv[t.vtx[0]], wv[t.vtx[1]], wv[t.vtx[2]]
        x0 = min(a[0], b[0], c[0]); x1 = max(a[0], b[0], c[0])
        z0 = min(a[2], b[2], c[2]); z1 = max(a[2], b[2], c[2])
        for gi in range(int(math.floor(x0 / step)), int(math.floor(x1 / step)) + 1):
            x = (gi + 0.5) * step
            for gj in range(int(math.floor(z0 / step)), int(math.floor(z1 / step)) + 1):
                if (gi, gj) in on:
                    continue
                if _pt_in_tri_xz(x, (gj + 0.5) * step, a, b, c):
                    on.add((gi, gj))
    return on


def occupiable_cells(wmesh, step: float, bedges=None,
                     clearance: float = WALL_CLEARANCE_W) -> tuple:
    """``(occupiable, on_mesh)`` cell sets at ``step`` resolution.

    ``on_mesh`` is every cell on the walkmesh; ``occupiable`` is the subset at least
    ``clearance`` from a collision WALL -- the positions a unit's CENTRE can actually
    hold. The Path-B study's lesson: testing un-standable corner slivers as if a unit
    could stand in them manufactures warnings nobody can act on."""
    if bedges is None:
        bedges = mesh_boundary_edges(wmesh)
    on = _raster_on_mesh(wmesh, step)
    if not bedges:
        return set(on), on
    buckets: dict = {}                          # wall edges bucketed by cell, padded
    span = max(step, clearance)
    for e in bedges:
        (ax, az), (bx, bz) = e
        for gi in range(int(math.floor((min(ax, bx) - clearance) / span)),
                        int(math.floor((max(ax, bx) + clearance) / span)) + 1):
            for gj in range(int(math.floor((min(az, bz) - clearance) / span)),
                            int(math.floor((max(az, bz) + clearance) / span)) + 1):
                buckets.setdefault((gi, gj), []).append(e)
    occ = set()
    for (gi, gj) in on:
        x, z = (gi + 0.5) * step, (gj + 0.5) * step
        key = (int(math.floor(x / span)), int(math.floor(z / span)))
        near_edges = buckets.get(key)
        if near_edges and any(seg_dist_xz(x, z, e0, e1) < clearance for e0, e1 in near_edges):
            continue
        occ.add((gi, gj))
    return occ, on


def _in_box(x, z, box) -> bool:
    return box is None or (box[0] <= x <= box[1] and box[2] <= z <= box[3])


def sweep_pursuit(wmesh, radius: float, *, standoff: float = 0.0, spacing: float | None = None,
                  grain: float = WALL_CLEARANCE_W, bedges=None, source_box=None,
                  target_box=None, worst: int = 3, max_samples: int = 3_000_000) -> dict:
    """Sweep the FAMILY of straight legs a dynamic feed (chase / wander) can walk.

    A ``chase`` feeds the target's LIVE position, so there is no single authored line
    to sweep -- what it walks is any leg between two positions its branch admits. This
    tests that family: for every pair of occupiable positions whose CHEBYSHEV
    separation is <= ``radius`` (the compiler's own ``_box`` engagement test, so a pair
    can be up to ``radius * sqrt(2)`` apart) and whose Euclidean separation exceeds
    ``standoff`` (inside it the pursuer holds ground), the leg is swept from the pursuer
    up to the standoff ring. A leg that leaves the walkmesh is a position pair at which
    the pursuer walks into a wall.

    TWO resolutions, deliberately decoupled: ``grain`` (default the collision radius) is
    what the walkmesh raster and the leg sampling use -- it must resolve a walker-sized
    gap, so it NEVER scales with ``radius``; ``spacing`` is only how far apart the
    sampled ENDPOINTS sit. Both the default spacing (a fifth of the family, or of the
    floor, whichever is smaller) and the ``max_samples`` widening are clamped to the
    OCCUPIABLE EXTENT: a family can never be wider than the field, and sizing off
    ``radius`` alone made an ungated (field-sized) chase rasterise at thousands of units
    per cell and report a false clean.

    ``source_box``/``target_box`` are optional ``(x0, x1, z0, z1)`` restrictions (a
    ``near_point``-gated chaser; a ``wander`` box). A gap narrower than ``grain`` can be
    missed -- the check errs quiet, so the reported rate is a floor. Returns
    ``{"tested", "blocked", "radius", "standoff", "grain", "spacing", "sources",
    "worst": [{"a","b","dist","span","mid"}]}``; ``spacing`` is the endpoint step
    actually used, so a widened sweep is always reportable, never silent."""
    if bedges is None:
        bedges = mesh_boundary_edges(wmesh)
    occ, on = occupiable_cells(wmesh, grain, bedges)
    reach = max(1, int(radius / grain))          # Chebyshev reach in FINE cells
    # the family can never be wider than the FIELD: clamp every sizing decision to the
    # occupiable extent. Sizing off `radius` alone drove a 20000u family to a ~4000u
    # endpoint grid on an 1600u floor -- 0 pairs tested, reported as clean.
    if occ:
        span_cells = max(max(c[0] for c in occ) - min(c[0] for c in occ),
                         max(c[1] for c in occ) - min(c[1] for c in occ)) + 1
    else:
        span_cells = 1
    eff = min(reach, span_cells)
    if spacing is None:
        spacing = max(grain, min(radius, span_cells * grain) / 5.0)
    k = max(1, min(int(round(spacing / grain)), max(1, eff // 5)))

    def sources_for(stride):
        """One representative occupiable cell per ``stride``-sized bucket. BUCKETING,
        not ``gi % stride == 0``: a modulus on ABSOLUTE grid indices can select nothing
        at all on a field whose cells never hit the residue (measured: a 20000u family
        picked 0 sources and reported a false clean)."""
        pick: dict = {}
        for c in occ:
            if not _in_box((c[0] + 0.5) * grain, (c[1] + 0.5) * grain, source_box):
                continue
            key = (c[0] // stride, c[1] // stride)
            if key not in pick or c < pick[key]:
                pick[key] = c
        return sorted(pick.values())

    srcs = sources_for(k)
    while srcs and k < eff and \
            len(srcs) * (2 * eff // k + 1) ** 2 * (eff / 2 + 1) > max_samples:
        k *= 2                                   # widen the ENDPOINT grid only
        srcs = sources_for(k)
    spacing = k * grain

    def leg_gap(a, b, cut):
        """Longest OFF-MESH run (world units) along a->b truncated at ``cut``, or 0."""
        dx, dz = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dz)
        if d <= 0:
            return 0.0, a
        f = max(0.0, min(1.0, cut / d))
        n = max(2, int(d * f / grain))
        run, best, bmid = 0.0, 0.0, a
        for i in range(n + 1):
            t = (i / n) * f
            x, z = a[0] + dx * t, a[1] + dz * t
            if (int(math.floor(x / grain)), int(math.floor(z / grain))) in on:
                run = 0.0
            else:
                run += d * f / n
                if run > best:
                    best, bmid = run, (x, z)
        return best, bmid

    tested = blocked = 0
    hits: list = []
    lim = max(1, eff // k) * k                   # target lattice, source-aligned
    for (gi, gj) in srcs:
        ax, az = (gi + 0.5) * grain, (gj + 0.5) * grain
        for di in range(-lim, lim + 1, k):
            for dj in range(-lim, lim + 1, k):
                c = (gi + di, gj + dj)
                if c not in occ:
                    continue
                bx, bz = (c[0] + 0.5) * grain, (c[1] + 0.5) * grain
                if not _in_box(bx, bz, target_box):
                    continue
                if max(abs(bx - ax), abs(bz - az)) > radius:
                    continue
                d = math.hypot(bx - ax, bz - az)
                if d <= standoff:
                    continue                    # inside the standoff: holds ground
                tested += 1
                span, mid = leg_gap((ax, az), (bx, bz), d - standoff)
                if span > 0:
                    blocked += 1
                    hits.append({"a": (ax, az), "b": (bx, bz), "dist": d,
                                 "span": span, "mid": mid})
    hits.sort(key=lambda h: (-h["span"], h["a"], h["b"]))
    picked, spots = [], set()               # spatially DISTINCT exemplars: three near-
    sep = max(grain * 4, radius / 8.0)      # identical pairs around one wall teach once
    for h in hits:
        cell = (int(h["mid"][0] // sep), int(h["mid"][1] // sep))
        if cell in spots:
            continue
        spots.add(cell)
        picked.append(h)
        if len(picked) >= worst:
            break
    return {"tested": tested, "blocked": blocked, "radius": radius, "standoff": standoff,
            "grain": grain, "spacing": spacing, "sources": len(srcs), "worst": picked}


def pursuit_extent(wmesh) -> float:
    """The walkmesh's larger XZ extent — the radius an UNGATED chase's pursuit family
    spans (its quarry can be anywhere on the field). Shared by ``behavior lint`` and
    the Workspace's stage sweep so both size the family the same way."""
    wv = wmesh.world_verts()
    if not wv:
        return 0.0
    return float(max(max(v[0] for v in wv) - min(v[0] for v in wv),
                     max(v[2] for v in wv) - min(v[2] for v in wv)))


def describe_pursuit_problems(name: str, res: dict) -> list:
    """Human-readable warnings for a :func:`sweep_pursuit` result — the pursuit-line
    analogue of :func:`describe_leg_problems`, phrased the same way."""
    if not res["tested"]:
        return [f"pursuit {name}: no position pair to test (nothing occupiable within the "
                f"{res['radius']:.0f}u box, or the whole family sits inside the standoff)"]
    if not res["blocked"]:
        return []
    tail = (f"-- a walker moves STRAIGHT at its live target and slides/stalls on the "
            f"boundary (no pathfinding), so the pursuer wedges whenever its quarry "
            f"stands on one of those spots")
    box = (f"inside the {res['radius']:.0f}u CHEBYSHEV box the compiler tests, so up to "
           f"{res['radius'] * 1.414:.0f}u apart")
    if res["tested"] < MIN_RATE_PAIRS:
        # too few pairs for a rate to mean anything: state the finding, not a statistic
        out = [f"pursuit {name}: {res['blocked']} of only {res['tested']} sampled position "
               f"pairs ({box}) have a straight pursuit line that leaves the walkmesh {tail}"]
    else:
        out = [f"pursuit {name}: {100.0 * res['blocked'] / res['tested']:.1f}% of the "
               f"position pairs its engagement gate admits ({res['blocked']}/"
               f"{res['tested']} {box}) have a straight pursuit line that leaves the "
               f"walkmesh {tail}"]
    for h in res["worst"]:
        (ax, az), (bx, bz) = h["a"], h["b"]
        out.append(f"pursuit {name}: e.g. pursuer at ({ax:.0f},{az:.0f}), target at "
                   f"({bx:.0f},{bz:.0f}) ({h['dist']:.0f}u apart): OFF-MESH for "
                   f"~{h['span']:.0f}u around ({h['mid'][0]:.0f},{h['mid'][1]:.0f})")
    out.append(f"pursuit {name}: sampled {res['sources']} pursuer positions "
               f"{res['spacing']:.0f}u apart, legs tested at {res['grain']:.0f}u -- a "
               f"blocking gap narrower than that can be missed, so this is a floor on "
               f"the real rate, not a ceiling")
    return out


def describe_leg_problems(name: str, legs: list, *, wall_clearance: float = WALL_CLEARANCE_W) -> list:
    """Human-readable warnings for a swept polyline — the probe's exact phrasing,
    shared so ``behavior lint`` and the layout probe agree word for word."""
    warns = []
    for i, leg in enumerate(legs):
        ax, az = leg["a"]
        bx, bz = leg["b"]
        for t0, t1 in leg["spans"]:
            mid_t = (t0 + t1) / 2
            mx = ax + (bx - ax) * mid_t
            mz = az + (bz - az) * mid_t
            span = max((t1 - t0) * leg["len"], 40.0)
            warns.append(
                f"route '{name}' leg {i + 1} ({ax:.0f},{az:.0f})->({bx:.0f},{bz:.0f}): "
                f"OFF-MESH for ~{span:.0f}u around ({mx:.0f},{mz:.0f}) -- a walker moves "
                f"STRAIGHT and slides/stalls on the boundary (no pathfinding); reroute this leg")
        if not leg["spans"] and leg["minwall"] is not None and leg["minwall"] < wall_clearance:
            warns.append(
                f"route '{name}' leg {i + 1} ({ax:.0f},{az:.0f})->({bx:.0f},{bz:.0f}): "
                f"passes {leg['minwall']:.0f}u from a walkmesh edge -- collision radius "
                f"(~{wall_clearance:.0f}u) shoves walkers off this line")
    return warns
