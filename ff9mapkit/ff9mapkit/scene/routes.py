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

THE FLOOR LAW (the HANGOUT playtests, 2026-07): a walker lives on ONE floor of a
multi-floor mesh and can only change floors across a SEAM edge. Point-in-mesh
tested in flattened 2D calls a raised terrace "on the mesh", so a target there
passed every offline gate while the ground-floor walker marched into the terrace
base and wedged. Every sweep here is therefore floor-aware: a leg is clean only
if it stays on its floor or crosses floors AT a seam
(:meth:`BgiWalkmesh.seam_edges_xz`); anywhere else two floors meet in 2D is a
wall. :func:`sweep_wander` additionally models the roll honestly: the engine
rolls a target ANYWHERE in the box — it never checks the mesh — so off-mesh and
off-floor box area jams the walker too.
"""
from __future__ import annotations

import math

# The player controller radius, IN-GAME MEASURED 2026-07-30 on calibration field 30510: walking into
# a wall clamps the centre at exactly 80u off it (the kit's player Init runs
# SetObjectLogicalSize(20,..) and Memoria's DoEventCode does radius = size * 4). Equal to
# cam.COLLISION_RADIUS_W but deliberately its OWN literal, fenced by an equality assert in
# tests/test_floorplan.py -- an alias cannot detect the drift the fence exists to catch.
# Was 48.0 until the measurement: that value was the OPTIMISTIC direction, so every sweep here
# certified patrols the engine physically cannot walk (a 130u corridor measures 1820 standable
# cells at 48 and ZERO at 80).
WALL_CLEARANCE_W = 80.0

# The RESOLUTION every sweep rasterises and samples at -- a length scale, NOT a clearance, and
# deliberately NOT `WALL_CLEARANCE_W`. It must resolve a walker-sized GAP, so it has to get FINER as
# geometry gets tighter, whereas a radius gets COARSER as the walker gets bigger: tying one to the
# other means correcting the radius upward silently blinds the sweep. That is exactly what the
# 2026-07-30 48 -> 80 correction did -- the demo field's 40u notch fell between cell centres
# (`(gi+0.5)*80` steps straight over `x in (640,680)`), `_raster_on_mesh` filled the hole in, and
# `sweep_pursuit` reported 0 blocked of 1358 pairs where every finer grain finds 130-260. A FALSE
# CLEAN, the one failure mode `sweep_pursuit`'s own contract calls out. Matches
# `sweep_polyline`'s step and `content.pathfind._MESH_STEP_W`, so every walkability check in the kit
# resolves the same detail. A gap narrower than this is still missed -- the sweeps err quiet by
# design, so their rate is a floor -- but the bound no longer moves when a radius is re-measured.
SWEEP_GRAIN_W = 40.0

MIN_RATE_PAIRS = 200           # below this, report COUNTS -- a rate off 20 pairs is noise


def _floors_fn(wmesh):
    """The mesh's floor-membership query, or a 1-floor shim over point_on_walkmesh
    for duck-typed meshes (tests) that don't carry floors."""
    fn = getattr(wmesh, "floors_at", None)
    if fn is not None:
        return fn
    on = getattr(wmesh, "point_on_walkmesh", None)
    if on is None:
        return None

    def shim(x, z):
        f = on(x, z)
        return [] if f is None else [f]
    return shim


def _seam_lut(wmesh) -> dict:
    """``{(fa, fb): [((ax,az),(bx,bz)), ...]}`` seam segments (fa < fb), or {} when the
    mesh carries none / can't say. A missing table means every floor change is a wall."""
    fn = getattr(wmesh, "seam_edges_xz", None)
    if fn is None:
        return {}
    try:
        return fn() or {}
    except Exception:
        return {}


def _seam_near(seams: dict, floors_a, floors_b, x, z, tol) -> bool:
    """Is a seam edge between SOME floor of ``floors_a`` and SOME floor of ``floors_b``
    within ``tol`` of (x, z)? The legality test for a floor change observed there."""
    for fa in floors_a:
        for fb in floors_b:
            for e0, e1 in seams.get((min(fa, fb), max(fa, fb)), ()):
                if seg_dist_xz(x, z, e0, e1) <= tol:
                    return True
    return False


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

    Returns per-leg dicts ``{a, b, len, spans, minwall, jumps}`` — ``spans`` is a
    list of ``(t0, t1)`` OFF-MESH parameter intervals (a walker on that leg jams);
    ``minwall`` is the minimum boundary distance over the on-mesh samples (None
    when the whole leg is off-mesh or ``bedges`` is empty); ``jumps`` records every
    FLOOR change with no seam edge at the crossing, as
    ``{"t", "x", "z", "from", "to"}`` — in flattened 2D such a leg looks on-mesh,
    but the walker WEDGES against the terrace base / balcony lip there (THE FLOOR
    LAW above). ``bedges`` defaults to :func:`mesh_boundary_edges`."""
    if bedges is None:
        bedges = mesh_boundary_edges(wmesh) if wmesh is not None else []
    floors = _floors_fn(wmesh) if wmesh is not None else None
    seams = _seam_lut(wmesh) if wmesh is not None else {}
    pts = [tuple(p) for p in points]
    if closed and pts:
        pts = pts + [pts[0]]
    legs = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(2, int(L / step))
        spans, cur, minwall, jumps = [], None, None, []
        walk = None                        # the floor set the walker is currently on
        for k in range(n + 1):
            t = k / n
            x, z = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            fl = floors(x, z) if floors is not None else []
            on = bool(fl) if floors is not None else (
                wmesh is not None and wmesh.point_on_walkmesh(x, z) is not None)
            if not on:
                cur = [t, t] if cur is None else [cur[0], t]
                walk = None                # after a gap the floor track restarts
            else:
                if cur is not None:
                    spans.append(tuple(cur))
                    cur = None
                if floors is not None:
                    fs = set(fl)
                    if walk is None:
                        walk = fs
                    elif walk & fs:
                        walk = walk & fs   # overlapping floors narrow; walker stays put
                    else:
                        # floor change: legal ONLY across a real seam edge near here
                        if not _seam_near(seams, walk, fs, x, z, step + 8.0):
                            jumps.append({"t": t, "x": x, "z": z,
                                          "from": sorted(walk), "to": sorted(fs)})
                        walk = fs
                if bedges:
                    d = min(seg_dist_xz(x, z, e0, e1) for e0, e1 in bedges)
                    minwall = d if minwall is None else min(minwall, d)
        if cur is not None:
            spans.append(tuple(cur))
        legs.append({"a": a, "b": b, "len": L, "spans": spans, "minwall": minwall,
                     "jumps": jumps})
    return legs


def _raster_on_mesh(wmesh, step: float) -> dict:
    """``{(gi, gj): frozenset(floor indices)}`` for every grid cell whose CENTRE lies on
    the walkmesh, at ``step`` resolution (treat as a set for pure on/off tests).

    Rasterises each triangle over its own bbox cells (O(area/step^2) total) instead of
    testing every cell against every triangle -- ``point_on_walkmesh`` is O(tris) per
    call, which a pair sweep cannot afford. Carries each cell's FLOOR membership so the
    pair sweeps can apply THE FLOOR LAW without a second pass."""
    from .bgi import _pt_in_tri_xz
    wv = wmesh.world_verts()
    tf = {}
    for fi, fl in enumerate(getattr(wmesh, "floors", ()) or ()):
        for ti in getattr(fl, "tri_ndx_list", ()) or ():
            tf[ti] = fi
    on: dict = {}
    for ti, t in enumerate(wmesh.tris):
        a, b, c = wv[t.vtx[0]], wv[t.vtx[1]], wv[t.vtx[2]]
        fi = tf.get(ti, getattr(t, "floor_ndx", 0))
        x0 = min(a[0], b[0], c[0]); x1 = max(a[0], b[0], c[0])
        z0 = min(a[2], b[2], c[2]); z1 = max(a[2], b[2], c[2])
        for gi in range(int(math.floor(x0 / step)), int(math.floor(x1 / step)) + 1):
            x = (gi + 0.5) * step
            for gj in range(int(math.floor(z0 / step)), int(math.floor(z1 / step)) + 1):
                have = on.get((gi, gj))
                if have is not None and fi in have:
                    continue
                if _pt_in_tri_xz(x, (gj + 0.5) * step, a, b, c):
                    on[(gi, gj)] = (have | {fi}) if have else frozenset((fi,))
    return on


def _seam_cells(wmesh, step: float) -> dict:
    """``{(gi, gj): {(fa, fb), ...}}`` — cells within one cell of a SEAM edge, tagged
    with the floor pair(s) that legally cross there. The pair sweeps' O(1) legality
    test: a floor change observed anywhere else is a wall (a terrace base)."""
    cells: dict = {}
    for pair, segs in _seam_lut(wmesh).items():
        for (ax, az), (bx, bz) in segs:
            L = math.hypot(bx - ax, bz - az)
            n = max(1, int(L / (step * 0.5)))
            for k in range(n + 1):
                t = k / n
                gi = int(math.floor((ax + (bx - ax) * t) / step))
                gj = int(math.floor((az + (bz - az) * t) / step))
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        cells.setdefault((gi + di, gj + dj), set()).add(pair)
    return cells


def _cross_ok(cur, new, pairs) -> bool:
    """May a walker on floors ``cur`` step onto floors ``new`` given the seam floor
    ``pairs`` present at this cell?"""
    if not pairs:
        return False
    for f0 in cur:
        for f1 in new:
            if (min(f0, f1), max(f0, f1)) in pairs:
                return True
    return False


def _erode_cells(on, step: float, bedges, clearance: float) -> set:
    """The subset of ``on`` cells whose centre is at least ``clearance`` from a
    collision WALL -- the positions a unit's CENTRE can actually hold."""
    if not bedges:
        return set(on)
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
    return occ


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
    return _erode_cells(on, step, bedges, clearance), set(on)


def _in_box(x, z, box) -> bool:
    return box is None or (box[0] <= x <= box[1] and box[2] <= z <= box[3])


def sweep_pursuit(wmesh, radius: float, *, standoff: float = 0.0, spacing: float | None = None,
                  grain: float = SWEEP_GRAIN_W, bedges=None, source_box=None,
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

    TWO resolutions, deliberately decoupled: ``grain`` (default :data:`SWEEP_GRAIN_W`) is
    what the walkmesh raster and the leg sampling use -- it must resolve a walker-sized
    gap, so it scales with NEITHER ``radius`` NOR the wall clearance (it was the clearance
    until 2026-07-30, and correcting that radius 48 -> 80 silently blinded this sweep to a
    40u notch: 0 blocked of 1358 pairs, a false clean); ``spacing`` is only how far apart the
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
    on = _raster_on_mesh(wmesh, grain)           # cell -> its floor set (THE FLOOR LAW)
    occ = _erode_cells(on, grain, bedges, WALL_CLEARANCE_W)
    scells = _seam_cells(wmesh, grain)
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
        """Longest BLOCKED run (world units) along a->b truncated at ``cut``, or 0.

        Blocked = off-mesh, OR past a floor change with no seam at the crossing: in
        flattened 2D a terrace base reads as mesh, but the walker never gets onto it
        -- everything beyond an unseamed crossing counts as blocked (THE FLOOR LAW)."""
        dx, dz = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dz)
        if d <= 0:
            return 0.0, a
        f = max(0.0, min(1.0, cut / d))
        n = max(2, int(d * f / grain))
        run, best, bmid = 0.0, 0.0, a
        walk = None                              # the walker's current floor set
        wedged = False
        for i in range(n + 1):
            t = (i / n) * f
            x, z = a[0] + dx * t, a[1] + dz * t
            cell = (int(math.floor(x / grain)), int(math.floor(z / grain)))
            fl = None if wedged else on.get(cell)
            if fl is not None and walk is not None and not (walk & fl) \
                    and not _cross_ok(walk, fl, scells.get(cell)):
                wedged, bmid = True, (x, z)      # a wall in 2D-clothes: the terrace base
                fl = None
            if fl is not None:
                walk = (walk & fl) if (walk is not None and walk & fl) else fl
                run = 0.0
            else:
                run += d * f / n
                if run > best:
                    best = run
                    if not wedged:
                        bmid = (x, z)
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
               f"pairs ({box}) have a straight pursuit line that leaves the walkmesh or "
               f"crosses an unseamed floor break {tail}"]
    else:
        out = [f"pursuit {name}: {100.0 * res['blocked'] / res['tested']:.1f}% of the "
               f"position pairs its engagement gate admits ({res['blocked']}/"
               f"{res['tested']} {box}) have a straight pursuit line that leaves the "
               f"walkmesh or crosses an unseamed floor break {tail}"]
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


def sweep_wander(wmesh, cx, cz, radius, *, grain: float = SWEEP_GRAIN_W, bedges=None,
                 clearance: float = WALL_CLEARANCE_W, worst: int = 3,
                 max_samples: int = 1_500_000) -> dict:
    """Sweep a ``wander`` box the way the ENGINE actually plays it.

    The wander roll (``B_SYSVAR[0]`` random) lands ANYWHERE in the ``centre +- radius``
    box -- it never checks the walkmesh -- and the walker marches STRAIGHT at the rolled
    point. So the family to test is walker position (a walkable spot on the CENTRE'S
    floor inside the box) x roll target (EVERY box cell, walkable or not): a leg that
    exits the mesh or crosses floors away from a seam jams the walker at that boundary
    -- the in-game "glitchy waypoints" look (the HANGOUT playtests: a box overhanging a
    terrace base or the mesh edge passed the occupiable-pair sweep clean).

    Returns ``{"centre", "radius", "centre_floors", "tested", "jammed", "cells",
    "off_cells", "alien_cells", "alien_floors", "grain", "spacing", "sources",
    "worst"}`` -- ``worst`` entries are ``{"a", "b", "dist", "span", "mid", "why"}``
    (``span`` = how far short of the roll the walker wedges)."""
    floors = _floors_fn(wmesh)
    seams = _seam_lut(wmesh)
    if bedges is None:
        bedges = mesh_boundary_edges(wmesh)
    centre_floors = list(floors(cx, cz)) if floors is not None else []
    res = {"centre": (float(cx), float(cz)), "radius": float(radius),
           "centre_floors": centre_floors, "tested": 0, "jammed": 0, "cells": 0,
           "off_cells": 0, "alien_cells": 0, "alien_floors": [], "grain": grain,
           "spacing": grain, "sources": 0, "worst": []}
    if floors is None or not centre_floors:
        return res                               # centre off-mesh: nothing to walk from
    cset = set(centre_floors)

    n = max(2, int(2 * radius / grain))
    lattice = [cx - radius + 2 * radius * i / n for i in range(n + 1)]
    zlattice = [cz - radius + 2 * radius * j / n for j in range(n + 1)]
    cells, home = [], []
    alien_floors: set = set()
    for x in lattice:
        for z in zlattice:
            fs = set(floors(x, z))
            cells.append((x, z, fs))
            if not fs:
                res["off_cells"] += 1
            elif not (fs & cset):
                res["alien_cells"] += 1
                alien_floors |= fs
            else:
                home.append((x, z, fs))
    res["cells"] = len(cells)
    res["alien_floors"] = sorted(alien_floors)

    srcs = [(x, z, fs) for (x, z, fs) in home
            if not bedges or min(seg_dist_xz(x, z, e0, e1) for e0, e1 in bedges) >= clearance]
    k = 1                                        # thin the WALKER positions, never the rolls
    est = lambda s: len(s) * len(cells) * max(2.0, radius / grain)  # noqa: E731
    while len(srcs[::k]) > 1 and est(srcs[::k]) > max_samples:
        k += 1
    srcs = srcs[::k]
    res["sources"] = len(srcs)
    res["spacing"] = k * grain

    def march(a, b, start_floors):
        """First jam event on the straight leg a->b, or None if the walker arrives."""
        dx, dz = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dz)
        if d <= 0:
            return None
        m = max(2, int(d / grain))
        walk = set(start_floors)
        for i in range(1, m + 1):
            t = i / m
            x, z = a[0] + dx * t, a[1] + dz * t
            fs = set(floors(x, z))
            if not fs:
                return {"t": t, "x": x, "z": z, "why": "walks OFF-MESH"}
            if walk & fs:
                walk = walk & fs
                continue
            if _seam_near(seams, walk, fs, x, z, grain + 8.0):
                walk = fs                        # a real seam: the legal floor change
                continue
            return {"t": t, "x": x, "z": z,
                    "why": (f"crosses floor {_floors_label(sorted(walk))} -> floor "
                            f"{_floors_label(sorted(fs))} with NO SEAM")}
        return None

    hits = []
    for (ax, az, afs) in srcs:
        for (bx, bz, _fs) in cells:
            if (bx, bz) == (ax, az):
                continue
            res["tested"] += 1
            ev = march((ax, az), (bx, bz), afs)
            if ev is not None:
                res["jammed"] += 1
                d = math.hypot(bx - ax, bz - az)
                hits.append({"a": (ax, az), "b": (bx, bz), "dist": d,
                             "span": d * (1.0 - ev["t"]), "mid": (ev["x"], ev["z"]),
                             "why": ev["why"]})
    hits.sort(key=lambda h: (-h["span"], h["a"], h["b"]))
    picked, spots = [], set()                    # spatially DISTINCT exemplars, like
    sep = max(grain * 4, radius / 8.0)           # sweep_pursuit's: one wall teaches once
    for h in hits:
        cell = (int(h["mid"][0] // sep), int(h["mid"][1] // sep))
        if cell in spots:
            continue
        spots.add(cell)
        picked.append(h)
        if len(picked) >= worst:
            break
    res["worst"] = picked
    return res


def describe_wander_problems(name: str, res: dict) -> list:
    """Human-readable warnings for a :func:`sweep_wander` result — phrased like
    :func:`describe_pursuit_problems`, shared by ``behavior lint`` and the Workspace
    sweep lane. Quiet when every roll is reachable (floor changes AT seams are fine)."""
    cx, cz = res["centre"]
    if not res["centre_floors"]:
        return [f"wander {name}: the wander CENTRE ({cx:.0f},{cz:.0f}) is OFF the "
                f"walkmesh -- the walker has no home to roll around; move it onto the floor"]
    if not res["tested"]:
        return [f"wander {name}: no walkable position on the centre's floor inside the "
                f"box to test from (the box may be smaller than the wall clearance)"]
    if not res["jammed"]:
        return []
    tail = ("-- the roll lands ANYWHERE in the box and never checks the mesh; the walker "
            "marches STRAIGHT at the rolled point (no pathfinding) and wedges where the "
            "line leaves its floor")
    if res["tested"] < MIN_RATE_PAIRS:
        out = [f"wander {name}: {res['jammed']} of only {res['tested']} sampled "
               f"walker->roll legs jam {tail}"]
    else:
        out = [f"wander {name}: {100.0 * res['jammed'] / res['tested']:.1f}% of its rolls "
               f"jam the walker ({res['jammed']}/{res['tested']} walker->roll legs) {tail}"]
    if res["off_cells"] or res["alien_cells"]:
        bits = []
        if res["off_cells"]:
            bits.append(f"{res['off_cells']} sit OFF the walkmesh")
        if res["alien_cells"]:
            bits.append(f"{res['alien_cells']} sit on floor "
                        f"{_floors_label(res['alien_floors'])} (reachable only across a seam)")
        out.append(f"wander {name}: of the box's {res['cells']} roll cells, "
                   + " and ".join(bits)
                   + " -- shrink the radius or recentre until the box hugs the walker's floor")
    for h in res["worst"]:
        (ax, az), (bx, bz) = h["a"], h["b"]
        out.append(f"wander {name}: e.g. walker at ({ax:.0f},{az:.0f}), roll at "
                   f"({bx:.0f},{bz:.0f}): {h['why']} at "
                   f"({h['mid'][0]:.0f},{h['mid'][1]:.0f})")
    out.append(f"wander {name}: sampled {res['sources']} walker positions "
               f"{res['spacing']:.0f}u apart against every {res['grain']:.0f}u roll cell "
               f"-- a floor on the real rate, not a ceiling")
    return out


def _floors_label(floors) -> str:
    return "+".join(str(f) for f in floors)


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
        for j in leg.get("jumps") or ():
            warns.append(
                f"route '{name}' leg {i + 1} ({ax:.0f},{az:.0f})->({bx:.0f},{bz:.0f}): "
                f"crosses floor {_floors_label(j['from'])} -> floor {_floors_label(j['to'])} "
                f"at ({j['x']:.0f},{j['z']:.0f}) with NO SEAM there -- the floors only meet "
                f"in flattened 2D (a terrace base / balcony lip is a WALL); the walker wedges "
                f"against it every pass. Route through a real seam or keep the leg on one floor")
        if not leg["spans"] and not leg.get("jumps") and leg["minwall"] is not None \
                and leg["minwall"] < wall_clearance:
            # a jump leg necessarily grazes the base wall: the crossing IS the finding
            warns.append(
                f"route '{name}' leg {i + 1} ({ax:.0f},{az:.0f})->({bx:.0f},{bz:.0f}): "
                f"passes {leg['minwall']:.0f}u from a walkmesh edge -- collision radius "
                f"(~{wall_clearance:.0f}u) shoves walkers off this line")
    return warns
