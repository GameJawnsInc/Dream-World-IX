"""OFFLINE ENGINE-PLACEMENT SIMULATOR -- the overworld ground-query, byte-exact to Memoria source.

RE'd 2026-07-07 from ``ff9.cs w_nwpHit`` (~7221), ``WMBlock.Raycast``/``AddWalkMesh`` and
``WMPhysics.Raycast`` (see project memory ``project-ff9-overworld-placement-rules``); it reproduced the
synth-blob's triple in-game stranding offline (its walkable top was wound down-facing). The rules:

1. Ground = a DOWN ray. Walking: origin ``y + 2.34375``, INFINITE reach downward -- ``ff9.rayDistance``
   (2.8) is passed to ``WMBlock.Raycast`` but the parameter is DEAD (never read; verified in source
   2026-07-12), so a step DOWN of any height is legal and only the climb ceiling exists. Sky (spawn /
   arrival / the debug-menu teleport re-ground / flying actors): origin ``y + 400``, infinite.
2. **Every miss resolves to ground = 0** (ocean level): block missing/not-ready, or no triangle hit.
   An interior miss strands the player at Y=0 under the land; a WATER-area miss is ALSO an invisible
   VEHICLE WALL (movement into a no-walkmesh region is rejected -- airship-proven in-game) and a void
   render hole.
3. A block's form-1 walkmeshes are scanned in REGISTRATION order -- Object, Terrain, Beach1, Beach2,
   Stream, River, RiverJoint, Falls, Sea1..Sea6 -- and the FIRST MESH with any passing hit wins (not the
   geometrically closest). An up-facing submerged tri in Terrain therefore SHADOWS the Sea surface above
   it; real blocks keep water areas Terrain-free.
4. Within a mesh, the FIRST TRIANGLE IN BUFFER ORDER wins (not the nearest hit) among tris that pass:
   ``idall.x`` not in {4078, 4088, 2040}; up-facing by the GEOMETRIC WINDING normal (``ny > 0.1`` of
   normalized ``Cross(v1-v0, v2-v0)`` -- NOT the stored vertex normals); ray intersects at t >= 0.
5. mapid = the hit tri's ``tangent.x`` IDALL; movement legality reads its topograph.

Use :func:`census` as a build gate: **MISS must be 0 everywhere in the cell** (land AND water), and the
warp target must ground on walkable topo.
"""
from __future__ import annotations

import collections
import math

#: idall values the engine's triangle filter skips outright
IDALL_SKIP = {4078, 4088, 2040}
#: flight-only marker: a passing hit with this idall makes the engine abandon the WHOLE mesh
VETO = 0x31EE
WALK_RAY_START = 2.34375
WALK_RAY_DIST = 2.8                                      # ff9.rayDistance -- DEAD in WMBlock.Raycast
SKY_RAY_START = 400.0
INDEX_GRID = 8.0  #: spatial-index bucket size (same frame/units as the meshes)
#: sheets closer than this in y are ONE surface (walk_sim's DEDUP_EPS)
SHEET_DEDUP_EPS = 0.02
#: a stack only COUNTS when the top two walkable sheets are at least this far apart --
#: walk_sim's SUNKEN_EPS, the bench-calibrated "visibly under the surface" threshold.
#: CALIBRATED 2026-08-04 against the owner-accepted V-shore bench: without the floor, 5
#: micro-overlap samples (relief-seam tris 0.024-0.066u apart) score the ACCEPTED island
#: as defective -- the exact judge-before-calibrating trap texgates.py:56 names.
STACK_GAP_MIN = 0.3
#: the on-foot topograph limit mask {0x0010667F, 0xD8FF3CFF} bit-decoded (walk_sim.py:44-45,
#: FC-3, double-confirmed) -- a "walkable sheet" means its topograph is in this set
WALK_OK = frozenset(list(range(0, 8)) + list(range(10, 14)) + list(range(16, 24))
                    + [27, 28, 30, 31] + list(range(32, 39)) + [41, 42, 45, 46, 52])
#: engine block number (WMWorldPrefabMaker.cs: Number = row*24 + col) with a HARDCODED
#: registration-order exception: 219 = Water Shrine (WMWorld.cs early-returns after
#: Object/Terrain/Sea3/Sea4/Sea5 -- no Beach/Stream/River/Falls scan happens there)
WATER_SHRINE_BLOCK = 219


def check_order_exceptions(meshlist):
    """REFUSE the two engine registration-order exceptions this simulator does not model
    (project-ff9-overworld-placement-rules, WMWorld.cs 2026-07-18): the Water Shrine block
    (Number 219 early-returns after a short part list) and volcano blocks (the prefab
    splices VolcanoCrater/VolcanoLava in BEFORE Beach1 -- prefab-part-driven, so the check
    keys on the part NAME). Refusal is cheaper than modelling and cannot go quietly wrong.
    Called once per meshlist by :func:`census` and :func:`build_meshlist_index` -- NOT by
    the hot :func:`place` loop (the perf ledger owns that refusal)."""
    from .mesh import GRID_COLS
    for name, bm in meshlist:
        if "volcano" in str(name).lower():
            raise ValueError(f"registration-order exception: {name!r} -- the engine splices "
                             "Volcano* parts BEFORE Beach1; this simulator does not model it")
        bx, by = getattr(bm, "x", None), getattr(bm, "y", None)
        if bx is not None and by is not None and by * GRID_COLS + bx == WATER_SHRINE_BLOCK:
            raise ValueError(f"registration-order exception: block ({bx},{by}) is the Water "
                             "Shrine (Number 219) -- the engine scans only Object/Terrain/"
                             "Sea3/Sea4/Sea5 there; this simulator does not model it")


def _decode_topo(idall: int):
    from .extract import decode_id
    return decode_id(idall)["topograph"]


def build_index(bm):
    """Uniform-grid index over triangle 2D AABBs, (x, z) -> ascending tri indices (promoted from
    ``coastnav._build_grid``, the proven emitter-default accelerator).

    Buckets hold ascending triangle indices, and any triangle covering a point is in that point's
    bucket (AABB overlap), so a bucket scan returns exactly the file-order first hit the full scan
    returns -- the index is a pure accelerator, never a semantic change. ``extract.py`` guarantees
    ``bm.tris[t] == flat_index[3t:3t+3]``, so tri indices map 1:1 between the two topology views.
    A dense census over a stacked meshlist is O(all tris) per sample without it -- minutes per gate
    run at region scale, which is what made "sample finer" unaffordable."""
    grid = {}
    for t, tri in enumerate(bm.tris):
        xs = [bm.verts[k][0] for k in tri]
        zs = [bm.verts[k][2] for k in tri]
        for gx in range(math.floor((min(xs) - 1e-6) / INDEX_GRID),
                        math.floor((max(xs) + 1e-6) / INDEX_GRID) + 1):
            for gz in range(math.floor((min(zs) - 1e-6) / INDEX_GRID),
                            math.floor((max(zs) + 1e-6) / INDEX_GRID) + 1):
                grid.setdefault((gx, gz), []).append(t)
    return grid


def build_meshlist_index(meshlist):
    """Per-mesh :func:`build_index` grids aligned with ``meshlist``'s order -- hand the result to
    ``place(index=...)``. Build once per meshlist, never per sample. Refuses the two
    registration-order exception blocks (:func:`check_order_exceptions`)."""
    check_order_exceptions(meshlist)
    return [build_index(bm) for _, bm in meshlist]


def all_sheets(meshlist, x: float, z: float, *, strict: bool = True, index=None):
    """Every filter-passing intersection on the vertical line at ``(x, z)``, in SCAN order
    (mesh registration order, buffer order within a mesh), deduped by y
    (:data:`SHEET_DEDUP_EPS`). Returns ``[(y, mesh_name, idall, topograph), ...]``.

    Ported from ``studies/path-d-new-world/walk_sim.py:227-248`` -- the ~60 lines that
    reproduced the owner's lawn-under-hill pin at 0.00u with a clean pristine control
    (BENCH-WALK-SIM.md). :func:`place` is first-hit-or-MISS, so it is structurally blind
    to a walkable sheet UNDER a walkable sheet -- the one defect class in the Path-D arc
    with a playtest receipt, and a STATIC one. ``strict=True`` demands interior hits (a
    shared boundary LINE is not a stack). VETO (flight-only) tris are invisible here,
    matching the walk instrument."""
    eps = 1e-5 if strict else -1e-9
    out = []
    for mi, (name, bm) in enumerate(meshlist):
        V, T, fi = bm.verts, bm.tangents, bm.flat_index
        if index is None:
            cand = range(len(fi) // 3)
        else:
            cand = index[mi].get((math.floor(x / INDEX_GRID), math.floor(z / INDEX_GRID)), ())
        for t in cand:
            idx = fi[3 * t:3 * t + 3]
            idall = int(round(T[idx[0]][0]))
            if idall in IDALL_SKIP or idall == VETO:
                continue
            a, b, c = V[idx[0]], V[idx[1]], V[idx[2]]
            ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
            ny = uz * vx - ux * vz
            L = math.sqrt((uy*vz-uz*vy)**2 + ny*ny + (ux*vy-uy*vx)**2) or 1.0
            if ny / L <= 0.1:
                continue
            d = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[2]-c[2])*(x-c[0]) + (c[0]-b[0])*(z-c[2])) / d
            w1 = ((c[2]-a[2])*(x-c[0]) + (a[0]-c[0])*(z-c[2])) / d
            w2 = 1 - w0 - w1
            if w0 < eps or w1 < eps or w2 < eps:
                continue
            hy = w0*a[1] + w1*b[1] + w2*c[1]
            if any(abs(hy - y0) <= SHEET_DEDUP_EPS for (y0, _, _, _) in out):
                continue
            out.append((hy, name, idall, _decode_topo(idall)))
    return out


def place(meshlist, x: float, z: float, y: float = 0.0, *, sky: bool = True, index=None):
    """The engine ground query at ``(x, z)`` from height ``y``. ``meshlist`` = ``[(name, BlockMesh)]`` in
    the block's REGISTRATION order (Object, Terrain, ..., Sea1..6), all in the same (block-local or world)
    frame as ``x, z``. Returns ``(ground_y, mesh_name, idall, topograph)``; a miss returns
    ``(0.0, "MISS", 0, None)`` -- the engine's defaultHeight fallback. ``index`` (optional) = the
    :func:`build_meshlist_index` of THIS meshlist; a pure accelerator, byte-identical verdicts."""
    origin_y = y + (SKY_RAY_START if sky else WALK_RAY_START)
    # NO max drop in either mode: the engine passes ff9.rayDistance (2.8) into WMBlock.Raycast
    # but that parameter is never read -- descent of any height is legal, only the climb gates.
    for mi, (name, bm) in enumerate(meshlist):
        V, T, fi = bm.verts, bm.tangents, bm.flat_index
        if index is None:
            cand = range(len(fi) // 3)
        else:
            cand = index[mi].get((math.floor(x / INDEX_GRID), math.floor(z / INDEX_GRID)), ())
        hit = None
        for t in cand:
            idx = fi[3 * t:3 * t + 3]
            idall = int(round(T[idx[0]][0]))
            if idall in IDALL_SKIP:
                continue
            a, b, c = V[idx[0]], V[idx[1]], V[idx[2]]
            ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
            ny = uz * vx - ux * vz
            L = math.sqrt((uy*vz-uz*vy)**2 + ny*ny + (ux*vy-uy*vx)**2) or 1.0
            if ny / L <= 0.1:
                continue
            d = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
            if abs(d) < 1e-12:
                continue
            w0 = ((b[2]-c[2])*(x-c[0]) + (c[0]-b[0])*(z-c[2])) / d
            w1 = ((c[2]-a[2])*(x-c[0]) + (a[0]-c[0])*(z-c[2])) / d
            w2 = 1 - w0 - w1
            if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                continue
            hy = w0*a[1] + w1*b[1] + w2*c[1]
            if hy > origin_y:
                continue
            hit = (hy, idall)
            break
        if hit is not None:
            if hit[1] == VETO:
                continue                                 # flight-only: abandon the WHOLE mesh
            return hit[0], name, hit[1], _decode_topo(hit[1])
    return 0.0, "MISS", 0, None


def census(meshlist, *, span=(2.0, 62.0, -62.0, -2.0), samples: int = 24, y: float = 0.0):
    """Sky-cast a grid over the block and report where the player would ground. Returns
    ``{"counts": {(mesh, topo): n}, "miss": [(x, z), ...], "points": [(x, z, ground_y, mesh, topo)],
    "stacked": [...], "inversions": [...]}``. Gates: ``len(miss) == 0`` -- a miss ANYWHERE is a
    stranding spot (land) or a vehicle wall + void render (water) -- and ``len(stacked) == 0``.

    THE STACKED-SHEET CENSUS (audit rec 3). ``stacked`` lists samples where >= 2 WALKABLE
    sheets (:data:`WALK_OK`) share the vertical line with the top two at least
    :data:`STACK_GAP_MIN` apart: ``{"at", "sheets", "gap", "shadowed"}``,
    ``shadowed`` = the engine's first-in-scan-order pick grounds BELOW the top walkable sheet
    -- the player walks UNDER the surface (the lawn-under-hill class, pinned at 0.00u by the
    bench walk instrument on a real playtest defect). ``inversions`` is the shadowed subset.
    NOTE: a one-tri-hole MISS is still missed ~25% of the time at the default 24-sample pitch
    (the measured detection floor) -- this census gates what it samples, not what it doesn't."""
    x0, x1, z0, z1 = span
    counts = collections.Counter()
    miss = []
    points = []
    stacked = []
    inversions = []
    index = build_meshlist_index(meshlist)               # once per census -- pure accelerator
    for i in range(samples):
        for j in range(samples):
            px = x0 + (x1 - x0) * i / (samples - 1)
            pz = z0 + (z1 - z0) * j / (samples - 1)
            gy, name, idall, topo = place(meshlist, px, pz, y, sky=True, index=index)
            counts[(name, topo)] += 1
            points.append((px, pz, gy, name, topo))
            if name == "MISS":
                miss.append((px, pz))
            walk = [s for s in all_sheets(meshlist, px, pz, strict=True, index=index)
                    if s[3] in WALK_OK]
            if len(walk) >= 2:
                ys = sorted((s[0] for s in walk), reverse=True)
                if ys[0] - ys[1] < STACK_GAP_MIN:
                    continue                             # relief-seam micro-overlap, not a stack
                rec = {"at": (px, pz), "gap": round(ys[0] - ys[1], 3),
                       "sheets": [(round(s[0], 3), s[1], s[3]) for s in walk],
                       "shadowed": name != "MISS" and ys[0] - gy > SHEET_DEDUP_EPS}
                stacked.append(rec)
                if rec["shadowed"]:
                    inversions.append(rec)
    return {"counts": dict(counts), "miss": miss, "points": points,
            "stacked": stacked, "inversions": inversions}
