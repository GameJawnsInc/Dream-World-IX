"""The ``.ff9mesh`` loose-override format (custom-overworld Path C): emit a world block mesh the custom engine
loads from a mod folder (``Memoria.World.WorldMeshOverride``), bypassing the AssetBundle pipeline.

The format is a verbatim dump of a :class:`ff9mapkit.world.extract.BlockMesh`'s channels::

    b"F9WM" | version i32 | vertexCount i32 | indexCount i32 | flags i32
    vertices v*3 f32 ; normals v*3 f32 (flags&1) ; uv v*2 f32 (flags&2) ; tangents v*4 f32 (flags&4) ; indices i*i32

The engine override search is the Resources loose-asset path: a block's file lives at
``<game>/<mod_folder>/FF9_Data/WorldMap/Disc{D}/{lod}/r{Y}/Block[{X}][{Y}] Terrain.ff9mesh`` -- the same place
``AssetManager`` looks for a Resources override (``GetResourcesAssetsPath(true)`` = ``FF9_Data``). Editing a block
= read it (``world.extract``), mutate ``chan_arrays`` (verts / tangent.x), :func:`write_ff9mesh`, :func:`deploy_override`.
"""
from __future__ import annotations

import math
import struct
from pathlib import Path

from .. import config

MAGIC = b"F9WM"
VERSION = 1


def write_ff9mesh(bm, path) -> Path:
    """Serialize a :class:`~ff9mapkit.world.extract.BlockMesh` to the ``.ff9mesh`` format the engine reads."""
    verts, normals, uvs, tangents = bm.verts, bm.normals, bm.uvs, bm.tangents
    flags = (1 if normals else 0) | (2 if uvs else 0) | (4 if tangents else 0)
    idx = bm.flat_index
    out = bytearray(MAGIC)
    out += struct.pack("<iiii", VERSION, bm.vcount, len(idx), flags)
    for v in verts:
        out += struct.pack("<3f", v[0], v[1], v[2])
    if normals:
        for n in normals:
            out += struct.pack("<3f", n[0], n[1], n[2])
    if uvs:
        for u in uvs:
            out += struct.pack("<2f", u[0], u[1])
    if tangents:
        for t in tangents:
            out += struct.pack("<4f", t[0], t[1], t[2], t[3])
    out += struct.pack("<%di" % len(idx), *idx)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path


def read_ff9mesh(path) -> dict:
    """Parse a ``.ff9mesh`` back into ``{version, vcount, verts, normals, uvs, tangents, indices}`` (round-trip
    check / re-import). The inverse of :func:`write_ff9mesh`."""
    data = Path(path).read_bytes()
    if data[:4] != MAGIC:
        raise ValueError("not a .ff9mesh (bad magic)")
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off = 20

    def take(n, dim):
        nonlocal off
        arr = [list(struct.unpack_from("<%df" % dim, data, off + j * dim * 4)) for j in range(n)]
        off += n * dim * 4
        return arr

    verts = take(vcount, 3)
    normals = take(vcount, 3) if flags & 1 else None
    uvs = take(vcount, 2) if flags & 2 else None
    tangents = take(vcount, 4) if flags & 4 else None
    indices = list(struct.unpack_from("<%di" % icount, data, off))
    return {"version": version, "vcount": vcount, "verts": verts, "normals": normals,
            "uvs": uvs, "tangents": tangents, "indices": indices}


def override_relpath(disc: int, x: int, y: int, lod: str = "0_1") -> str:
    """The mod-folder-relative path the engine's ``WorldMeshOverride`` searches for a block's override (under
    ``FF9_Data``, mirroring ``WMWorldPrefabMaker``'s Resources path + the ``.ff9mesh`` extension)."""
    return f"FF9_Data/WorldMap/Disc{disc}/{lod}/r{y}/Block[{x}][{y}] Terrain.ff9mesh"


def deploy_override(bm, *, mod_folder: str, game=None, lod: str = "0_1") -> Path:
    """Write ``bm`` as a loose ``.ff9mesh`` override into ``<game>/<mod_folder>/<override_relpath>`` -- where the
    custom engine (WorldMeshOverride) picks it up at world load. The mod_folder must be a stacked ``FolderNames``
    entry (e.g. ``FF9CustomMap``). Returns the written path."""
    dest = config.find_game_path(game) / mod_folder / override_relpath(bm.disc, bm.x, bm.y, lod)
    return write_ff9mesh(bm, dest)


def lift_block(bm, amount: float) -> int:
    """EDIT: raise EVERY vertex of the block by ``amount`` units -- an unmistakable whole-block lift (a floating
    plateau with a sharp cliff at the block edges) to confirm the override renders. Mutates ``bm`` in place;
    tangents/ids untouched. Returns the vertex count changed."""
    for v in bm.verts:
        v[1] += amount
    return bm.vcount


def raise_vertex_near_center(bm, amount: float) -> int:
    """EDIT (first-experiment helper): raise the vertex nearest the block's XZ centre by ``amount`` units -- an
    unmistakable spike to confirm the loose override is loaded + drives render/collision. Returns the vertex index.
    Mutates ``bm`` in place (tangents/ids untouched, so collision ids stay faithful)."""
    verts = bm.verts
    cx = sum(v[0] for v in verts) / len(verts)
    cz = sum(v[2] for v in verts) / len(verts)
    bi, best = 0, None
    for i, v in enumerate(verts):
        d = (v[0] - cx) ** 2 + (v[2] - cz) ** 2
        if best is None or d < best:
            best, bi = d, i
    verts[bi][1] += amount
    return bi


# --------------------------------------------------------------------------------------------------
# Purposeful terrain reshaping (Path C step 3).
#
# The world block mesh is FLAT/UNINDEXED: coincident triangle corners are *separate* vertices, so moving
# a single vertex (like ``raise_vertex_near_center``) TEARS the surface. Every reshape below applies a Y
# delta that is a pure function of a vertex's WORLD-XZ position -- so coincident corners always get the
# identical delta and the mesh stays watertight (no seam cracks), including across block boundaries.
#
# ``world_origin=(ox, oz)`` is the block's world origin (``extract.block_world_origin``): pass it so a hill
# / ridge can span several blocks continuously (the deform reasons in world XZ). For a self-contained
# block-local edit leave it (0, 0) and the default centre is the block's own XZ centroid.
#
# AUTHORING GOTCHAS (in-game 2026-07-01 -- the render/collision mechanism is solid; these are the real traps
# when reshaping the LIVE overworld):
#   * WALKABILITY IS TOPOGRAPH, NOT SLOPE. The overworld move gate (ff9.w_movementRoundCheck ->
#     w_movementCheckTopographID) only checks the target tile's TOPOGRAPH against the control's allowed set
#     (`limit`) -- there is NO slope/step-height gate. A reshape leaves tangent.x (topograph) untouched, so a
#     raised slope stays walkable at ANY grade. (Earlier "slope compounds" theory was WRONG.)
#   * PLACEMENT / EMBED is the real trap. What froze the player at Dali: a spawn / field-exit drops the actor
#     at the tile's STALE (pre-raise) Y, BELOW the new surface, and foot movement raycasts DOWN from the actor,
#     so it never reaches the raised tiles -> stuck in every direction (field re-entry did NOT fix it, because
#     the entry Y is effectively fixed). RULE: do NOT reshape terrain under a spawn / field-entry tile; reshape
#     AWAY from entries and the player walking in from adjacent unraised ground lands on top and moves fine.
#   * FIELD-ENTRANCE PITS. Raising a block lifts the entrance *tiles* but NOT the entrance *prop models*
#     (they stay at their old Y), leaving the props sunk in a visible pit. Another reason to avoid reshaping
#     blocks that carry a place entrance (``extract.block_summary(...)['place_entrances']``).
#   * COORDINATES. A block's edit key is its InitialX/InitialY == the mesh-file coord == the extraction coord
#     (the wrap's CurrentX/CurrentY is only screen position). To find which blocks a place occupies, trust the
#     runtime (F6 / a ground raycast), NOT the offline area->place decoder -- its area labels are unreliable.
# --------------------------------------------------------------------------------------------------

def _falloff(t: float, kind: str = "smooth") -> float:
    """Deform weight in ``[0, 1]``: 1 at the centre (``t=0``), 0 at/after the rim (``t>=1``), where
    ``t = distance / radius``. ``smooth`` (default) is a smoothstep dome -- C1 at the rim (zero slope), so the
    edit blends creaselessly into the untouched terrain; ``gauss`` is a rim-windowed bell (rounder peak); ``cone``
    is linear (a sharp-tipped cone)."""
    if t <= 0.0:
        return 1.0
    if t >= 1.0:
        return 0.0
    if kind == "cone":
        return 1.0 - t
    if kind == "gauss":                                  # windowed so it hits exactly 0 at the rim (no step)
        k = 2.5
        g = math.exp(-(k * t) ** 2)
        g0 = math.exp(-(k) ** 2)
        return (g - g0) / (1.0 - g0)
    s = t * t * (3.0 - 2.0 * t)                          # smoothstep 0->1
    return 1.0 - s                                       # dome: 1 at centre -> 0 at rim, flat slope both ends


def _xz_centroid(bm, ox: float = 0.0, oz: float = 0.0):
    verts = bm.verts
    cx = sum(v[0] for v in verts) / len(verts) + ox
    cz = sum(v[2] for v in verts) / len(verts) + oz
    return cx, cz


def _dist_point_segment(px, pz, ax, az, bx, bz) -> float:
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    if L2 <= 1e-9:
        return math.hypot(px - ax, pz - az)
    t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz))


def deform_radial(bm, *, amount: float, radius: float, center=None, falloff: str = "smooth",
                  world_origin=(0.0, 0.0)) -> int:
    """RESHAPE: raise a smooth HILL (``amount > 0``) or sink a CRATER (``amount < 0``) within ``radius`` world
    units of ``center`` (world XZ; default = the block's centroid). Tear-free (see module note). ``+Y`` is up in
    these meshes (proven by the whole-block lift). Mutates ``bm`` in place (tangents/ids untouched). Returns the
    number of vertices moved."""
    ox, oz = world_origin
    cx, cz = center if center is not None else _xz_centroid(bm, ox, oz)
    moved = 0
    for v in bm.verts:
        w = _falloff(math.hypot(v[0] + ox - cx, v[2] + oz - cz) / radius, falloff)
        if w > 0.0:
            v[1] += amount * w
            moved += 1
    return moved


def deform_ridge(bm, *, p0, p1, amount: float, radius: float, falloff: str = "smooth",
                 world_origin=(0.0, 0.0)) -> int:
    """RESHAPE: raise a RIDGE (``amount > 0``) or carve a VALLEY (``amount < 0``) of half-width ``radius`` along the
    world-XZ segment ``p0 -> p1`` (each an ``(x, z)`` pair). Tear-free. Returns the number of vertices moved."""
    ox, oz = world_origin
    (ax, az), (bx, bz) = p0, p1
    moved = 0
    for v in bm.verts:
        w = _falloff(_dist_point_segment(v[0] + ox, v[2] + oz, ax, az, bx, bz) / radius, falloff)
        if w > 0.0:
            v[1] += amount * w
            moved += 1
    return moved


def flatten_region(bm, *, radius: float, center=None, height=None, falloff: str = "smooth",
                   world_origin=(0.0, 0.0)) -> int:
    """RESHAPE: flatten toward ``height`` (default = the mean Y under the disc) within ``radius`` -- a plateau /
    clearing. Each vertex Y is blended toward ``height`` by the falloff weight (fully flat at the centre, untouched
    at the rim), so the surrounding terrain stitches in smoothly. Tear-free. Returns the number of vertices moved."""
    ox, oz = world_origin
    cx, cz = center if center is not None else _xz_centroid(bm, ox, oz)
    if height is None:
        ys = [v[1] for v in bm.verts if math.hypot(v[0] + ox - cx, v[2] + oz - cz) < radius]
        height = sum(ys) / len(ys) if ys else 0.0
    moved = 0
    for v in bm.verts:
        w = _falloff(math.hypot(v[0] + ox - cx, v[2] + oz - cz) / radius, falloff)
        if w > 0.0:
            v[1] += (height - v[1]) * w
            moved += 1
    return moved


def recompute_normals(bm, *, tol: float = 1e-3) -> int:
    """Recompute smooth vertex normals after a geometry edit (a Y-only deform leaves the stored normals stale ->
    wrong terrain shading). Position-welds coincident corners (the mesh is unindexed) so a shared grid node gets ONE
    averaged normal (smooth shading, no faceting at triangle seams), and sign-aligns each welded normal to the
    group's ORIGINAL stored normal so the winding/orientation is preserved (no inside-out darkening). No-op if the
    mesh has no normal channel. Mutates ``bm.normals`` in place. Returns the vertex count updated."""
    norms = bm.normals
    if norms is None:
        return 0
    verts = bm.tris and bm.verts
    acc = [[0.0, 0.0, 0.0] for _ in range(bm.vcount)]
    for a, b, c in bm.tris:                               # area-weighted face normals -> each corner
        va, vb, vc = verts[a], verts[b], verts[c]
        ux, uy, uz = vb[0] - va[0], vb[1] - va[1], vb[2] - va[2]
        wx, wy, wz = vc[0] - va[0], vc[1] - va[1], vc[2] - va[2]
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        for i in (a, b, c):
            acc[i][0] += nx
            acc[i][1] += ny
            acc[i][2] += nz
    groups = {}
    for i, v in enumerate(verts):
        groups.setdefault((round(v[0] / tol), round(v[1] / tol), round(v[2] / tol)), []).append(i)
    for idxs in groups.values():
        sx = sum(acc[i][0] for i in idxs)
        sy = sum(acc[i][1] for i in idxs)
        sz = sum(acc[i][2] for i in idxs)
        L = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
        nx, ny, nz = sx / L, sy / L, sz / L
        ox = sum(norms[i][0] for i in idxs)              # original orientation of this welded node
        oy = sum(norms[i][1] for i in idxs)
        oz = sum(norms[i][2] for i in idxs)
        if nx * ox + ny * oy + nz * oz < 0.0:            # keep the artist's facing (flip if inverted)
            nx, ny, nz = -nx, -ny, -nz
        for i in idxs:
            norms[i][0], norms[i][1], norms[i][2] = nx, ny, nz
    return bm.vcount


def retarget_tiles(bm, *, event=None, area=None, topograph=None, center=None, radius=None,
                   world_origin=(0.0, 0.0), only_entrances: bool = False) -> int:
    """Rewrite the per-triangle IDALL (stored in ``tangent.x``) for tiles in a region. ``event`` (0=land, 1-3=
    entrance-trigger bits), ``area`` (0-63), ``topograph`` (0-63 = terrain type) each default to KEEP the tile's
    current value. Sets tangent.x on all 3 corner verts of each affected triangle (the engine reads the HIT
    triangle's first-corner tangent.x as the mapid, WMBlock.cs). ``center``+``radius`` (world XZ) limit the region;
    ``only_entrances`` restricts to tiles already carrying event bits. Geometry (verts/normals/uv) is UNTOUCHED.
    Returns the triangle count changed. Deploy via :func:`deploy_override` (same loose ``.ff9mesh`` path).

    WHAT THIS CONTROLS (in-game verified 2026-07-01):
      * ``topograph`` -> WALKABILITY + terrain type. The overworld move gate (``ff9.w_movementRoundCheck`` ->
        ``w_movementCheckTopographID``) reads the tile topograph from this tangent.x, so this genuinely changes
        where the player can walk / encounter rates. This is the reliable use of tile retargeting.
      * ``event``/``area`` do NOT create a working ENTRANCE on their own. An overworld entrance is a world ``.eb``
        ENTRY keyed to the CELL POSITION: walking on an event tile fires ``ff9.WorldEvent`` which packs a cell tag
        ``0x8000|(cellZ<<8)|(cellX<<2)|event`` and ``GetIP``-matches it against the world ``.eb`` entry table; NO
        matching entry -> silent no-op (PROVEN: setting event+area on a plain block warped nowhere). So the entry,
        not the tile, defines the destination. Creating/moving an entrance needs a world ``.eb`` entry for that
        cell (Lever A+ = world-.eb authoring); the tile's ``event``/``area`` are only the trigger flag + cosmetic."""
    from .extract import decode_id, encode_id
    tan = bm.tangents
    if tan is None:
        raise ValueError("block mesh has no tangent channel -- no IDALL to edit")
    ox, oz = world_origin
    verts, changed = bm.verts, 0
    for tri in bm.tris:
        d = decode_id(int(round(tan[tri[0]][0])))
        if only_entrances and not d["event"]:
            continue
        if center is not None and radius is not None:
            cx = (verts[tri[0]][0] + verts[tri[1]][0] + verts[tri[2]][0]) / 3.0 + ox
            cz = (verts[tri[0]][2] + verts[tri[1]][2] + verts[tri[2]][2]) / 3.0 + oz
            if math.hypot(cx - center[0], cz - center[1]) > radius:
                continue
        idall = encode_id(d["event"] if event is None else event,
                          d["area"] if area is None else area,
                          d["topograph"] if topograph is None else topograph, d["flags"])
        for vi in tri:
            tan[vi][0] = float(idall)
        changed += 1
    return changed
