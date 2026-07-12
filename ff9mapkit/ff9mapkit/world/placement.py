"""OFFLINE ENGINE-PLACEMENT SIMULATOR -- the overworld ground-query, byte-exact to Memoria source.

RE'd 2026-07-07 from ``ff9.cs w_nwpHit`` (~7221), ``WMBlock.Raycast``/``AddWalkMesh`` and
``WMPhysics.Raycast`` (see project memory ``project-ff9-overworld-placement-rules``); it reproduced the
synth-blob's triple in-game stranding offline (its walkable top was wound down-facing). The rules:

1. Ground = a DOWN ray. Walking: origin ``y + 2.34375``, INFINITE reach downward -- ``ff9.rayDistance``
   (2.8) is passed to ``WMBlock.Raycast`` but the parameter is DEAD (never read; verified in source
   2026-07-12), so a step DOWN of any height is legal and only the climb ceiling exists. Sky (spawn /
   arrival / the F6 teleport re-ground / flying actors): origin ``y + 400``, infinite.
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
WALK_RAY_START = 2.34375
WALK_RAY_DIST = 2.8                                      # ff9.rayDistance -- DEAD in WMBlock.Raycast
SKY_RAY_START = 400.0


def _decode_topo(idall: int):
    from .extract import decode_id
    return decode_id(idall)["topograph"]


def place(meshlist, x: float, z: float, y: float = 0.0, *, sky: bool = True):
    """The engine ground query at ``(x, z)`` from height ``y``. ``meshlist`` = ``[(name, BlockMesh)]`` in
    the block's REGISTRATION order (Object, Terrain, ..., Sea1..6), all in the same (block-local or world)
    frame as ``x, z``. Returns ``(ground_y, mesh_name, idall, topograph)``; a miss returns
    ``(0.0, "MISS", 0, None)`` -- the engine's defaultHeight fallback."""
    origin_y = y + (SKY_RAY_START if sky else WALK_RAY_START)
    # NO max drop in either mode: the engine passes ff9.rayDistance (2.8) into WMBlock.Raycast
    # but that parameter is never read -- descent of any height is legal, only the climb gates.
    for name, bm in meshlist:
        V, T, fi = bm.verts, bm.tangents, bm.flat_index
        for t in range(len(fi) // 3):
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
            return hy, name, idall, _decode_topo(idall)
    return 0.0, "MISS", 0, None


def census(meshlist, *, span=(2.0, 62.0, -62.0, -2.0), samples: int = 24, y: float = 0.0):
    """Sky-cast a grid over the block and report where the player would ground. Returns
    ``{"counts": {(mesh, topo): n}, "miss": [(x, z), ...], "points": [(x, z, ground_y, mesh, topo)]}``.
    Gate: ``len(miss) == 0`` -- a miss ANYWHERE is a stranding spot (land) or a vehicle wall + void
    render (water)."""
    x0, x1, z0, z1 = span
    counts = collections.Counter()
    miss = []
    points = []
    for i in range(samples):
        for j in range(samples):
            px = x0 + (x1 - x0) * i / (samples - 1)
            pz = z0 + (z1 - z0) * j / (samples - 1)
            gy, name, idall, topo = place(meshlist, px, pz, y, sky=True)
            counts[(name, topo)] += 1
            points.append((px, pz, gy, name, topo))
            if name == "MISS":
                miss.append((px, pz))
    return {"counts": dict(counts), "miss": miss, "points": points}
