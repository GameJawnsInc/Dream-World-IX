"""Route geometry: walkability sweeps for scripted walk lines (rung 4 of the
behavior-tree study; promoted from ``tools/field_layout_probe.py``).

FF9 walkers move STRAIGHT at their target and slide on contact — there is NO
pathfinding. A walk leg that leaves the walkmesh means the walker jams against
the boundary (concave notches wedge; convex obstacles slide, ugly but alive —
the ``laying-out-ff9-fields`` skill's movement laws). These helpers sweep a
polyline against a :class:`~ff9mapkit.scene.bgi.BgiWalkmesh` so patrol rings,
marches, and flee lines are verified OFFLINE — both the layout probe and
``behavior lint`` run the same sweep.
"""
from __future__ import annotations

import math

WALL_CLEARANCE_W = 48.0        # the player controller radius (cam.COLLISION_RADIUS_W)


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
    """``boundary_edges_xz`` straight from a :class:`BgiWalkmesh`."""
    wv = wmesh.world_verts()
    return boundary_edges_xz(wv, [tuple(t.vtx) for t in wmesh.tris])


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
