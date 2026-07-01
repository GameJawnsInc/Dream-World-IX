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
