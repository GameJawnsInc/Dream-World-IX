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


def blockmesh_from_ff9mesh(path, *, disc: int, x: int, y: int, lod: str = "0_1", part: str = "terrain"):
    """Reconstruct a :class:`~ff9mapkit.world.extract.BlockMesh` from a loose ``.ff9mesh`` override (the inverse of
    :func:`deploy_override`). Lets a later edit STACK on an already-deployed override instead of re-reading the
    pristine p0data block -- e.g. a second entrance in the same block adds its event tiles / building onto the first
    one's terrain / object override rather than dropping it. The mesh is flat/unindexed, so ``tris`` regroups the
    stored index buffer in 3s; ``stride`` is nominal (the write path reads channels directly, never re-packs)."""
    from .extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    d = read_ff9mesh(path)
    chan = {CH_POS: [list(v) for v in d["verts"]]}
    channels = {CH_POS: (0, 3)}
    if d["normals"]:
        chan[CH_NRM] = [list(v) for v in d["normals"]]
        channels[CH_NRM] = (12, 3)
    if d["uvs"]:
        chan[CH_UV] = [list(v) for v in d["uvs"]]
        channels[CH_UV] = (24, 2)
    if d["tangents"]:
        chan[CH_TAN] = [list(v) for v in d["tangents"]]
        channels[CH_TAN] = (32, 4)
    idx = list(d["indices"])
    tris = [[idx[i], idx[i + 1], idx[i + 2]] for i in range(0, len(idx) - 2, 3)]
    return BlockMesh(name=f"Block[{x}][{y}] {part.capitalize()}", disc=disc, x=x, y=y, lod=lod, vcount=d["vcount"],
                     stride=48, channels=channels, chan_arrays=chan, flat_index=idx, tris=tris,
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def override_relpath(disc: int, x: int, y: int, lod: str = "0_1", part: str = "Terrain") -> str:
    """The mod-folder-relative path the engine's ``WorldMeshOverride`` searches for a block sub-mesh override (under
    ``FF9_Data``, mirroring ``WMWorldPrefabMaker``'s Resources path + the ``.ff9mesh`` extension). ``part`` matches
    the engine's ``transform.name`` (WMWorld.RegisterBlockComponent interpolates it into the lookup): ``"Terrain"``
    (ground + walkmesh + IDALL) or ``"Object"`` (baked buildings/structures). The s34 hook is generic over ``part``,
    so an ``Object`` override loads exactly like a ``Terrain`` one -- for a block that HAS a stock Object component."""
    return f"FF9_Data/WorldMap/Disc{disc}/{lod}/r{y}/Block[{x}][{y}] {part}.ff9mesh"


def donor_sidecar_relpath(disc: int, x: int, y: int, lod: str = "0_1") -> str:
    """The mod-folder-relative path of a cell's per-cell COASTAL DONOR sidecar (Path D faithful coast) -- mirrors
    :func:`override_relpath` but part ``Donor`` + ``.txt``. The engine (``WorldMeshOverride.TryReadDonorPath``) reads
    it to pick which REAL coastal block prefab (its Beach/Sea/foam) renders on this reclaimed cell."""
    return f"FF9_Data/WorldMap/Disc{disc}/{lod}/r{y}/Block[{x}][{y}] Donor.txt"


def deploy_donor_sidecar(donor_x: int, donor_y: int, *, mod_folder: str, disc: int, x: int, y: int,
                         lod: str = "0_1", game=None) -> Path:
    """Write the per-cell donor sidecar for reclaimed cell ``(x, y)``: a one-line ``"dx,dy"`` naming the real coastal
    donor block whose beach/sea/foam sub-meshes the engine should render on this cell. Deployed next to the cell's
    ``Terrain.ff9mesh`` override; the engine's ``TryReadDonorPath`` searches the stacked ``FolderNames`` for it."""
    dest = config.find_game_path(game) / mod_folder / donor_sidecar_relpath(disc, x, y, lod)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"{donor_x},{donor_y}", encoding="utf-8")
    return dest


def deploy_override(bm, *, mod_folder: str, game=None, lod: str = "0_1", part: str = "Terrain") -> Path:
    """Write ``bm`` as a loose ``.ff9mesh`` override into ``<game>/<mod_folder>/<override_relpath>`` -- where the
    custom engine (WorldMeshOverride) picks it up at world load. ``part`` = the block layer (``"Terrain"`` default,
    or ``"Object"`` for the building mesh). The mod_folder must be a stacked ``FolderNames`` entry (e.g.
    ``FF9CustomMap``). Returns the written path."""
    dest = config.find_game_path(game) / mod_folder / override_relpath(bm.disc, bm.x, bm.y, lod, part)
    return write_ff9mesh(bm, dest)


def sample_ground_y(terrain_bm, lx: float, lz: float) -> float:
    """The terrain surface Y at block-LOCAL ``(lx, lz)`` -- the nearest terrain vertex's Y. Used to seat a placed
    building on the ground (both the Terrain and Object meshes live in the block's local frame at ``localPosition=0``,
    so their Y are directly comparable)."""
    best, by = None, 0.0
    for v in terrain_bm.verts:
        d = (v[0] - lx) ** 2 + (v[2] - lz) ** 2
        if best is None or d < best:
            best, by = d, v[1]
    return by


def _convex_hull_xz(pts):
    """2D convex hull (monotone chain) of ``(x, z)`` points, counter-clockwise, no repeated endpoint."""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def add_solid_base(bm, *, topograph: int = 59, lift: float = 0.5):
    """Append a SOLID collision footprint (the XZ convex hull of ``bm``, fan-triangulated at its lowest Y + ``lift``,
    stamped ``topograph``) so a hollow 3D building blocks like a real town instead of leaving walk-in courtyard
    pockets you get boxed in. The hull FILLS interior gaps (a courtyard, a split between towers), so the whole
    footprint is impassable and the player stops at its edge (they trigger the entrance from OUTSIDE it). The fill
    sits just above the seated base so the engine's down-raycast hits it before the ground. Returns a new merged
    :class:`~ff9mapkit.world.extract.BlockMesh` (same channels as ``bm``)."""
    from .extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    verts = bm.verts
    hull = _convex_hull_xz([(v[0], v[2]) for v in verts])
    if len(hull) < 3:
        return bm
    y = min(v[1] for v in verts) + lift
    idall = float(encode_id(event=0, area=0, topograph=topograph))
    fan_pos, fan_nrm, fan_uv, fan_tan, fan_tris, fan_flat = [], [], [], [], [], []
    vi = 0
    for k in range(1, len(hull) - 1):                     # fan: (hull0, hull_k, hull_{k+1})
        for (hx, hz) in (hull[0], hull[k], hull[k + 1]):
            fan_pos.append([hx, y, hz])
            fan_nrm.append([0.0, 1.0, 0.0])
            fan_uv.append([0.0, 0.0])
            fan_tan.append([idall, 0.0, 0.0, 1.0])
            fan_flat.append(vi); vi += 1
        fan_tris.append([vi - 3, vi - 2, vi - 1])
    off = bm.vcount
    add = {CH_POS: fan_pos, CH_NRM: fan_nrm, CH_UV: fan_uv, CH_TAN: fan_tan}
    chan = {ci: [list(v) for v in bm.chan_arrays[ci]] + [list(v) for v in add.get(ci, [])] for ci in bm.channels}
    flat = list(bm.flat_index) + [i + off for i in fan_flat]
    tris = [list(t) for t in bm.tris] + [[a + off, b + off, c + off] for (a, b, c) in fan_tris]
    return BlockMesh(name=bm.name, disc=bm.disc, x=bm.x, y=bm.y, lod=bm.lod, vcount=off + vi, stride=bm.stride,
                     channels=dict(bm.channels), chan_arrays=chan, flat_index=flat, tris=tris,
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def flat_block_mesh(*, disc: int = 1, x: int = 0, y: int = 0, seg: int = 8, topograph: int = 0,
                    height: float = 0.0, lod: str = "0_1"):
    """Build a fresh FLAT, WALKABLE terrain :class:`~ff9mapkit.world.extract.BlockMesh` filling one 64x64 block in
    LOCAL space (verts x[0,64] z[-64,0], Y=``height``) -- the primitive for RECLAIMING an OCEAN cell as land, where
    there is no stock terrain mesh to :func:`deform_radial`. (The ``s34`` engine Path-D divert routes a designated sea
    cell onto a land donor prefab so ``RegisterBlockComponent`` swaps THIS override in as its Terrain render+walkmesh.)

    ``seg`` x ``seg`` quads, two triangles each, emitted as FRESH verts per triangle (the stock world blocks are
    flat/unindexed: ``vcount == indexCount``; sharing verts would desync the index buffer -> garbage cross-cell faces).
    Every triangle's ``tangent.x`` = ``encode_id(topograph=topograph)`` so the whole cell is one walkable topograph
    (default **0** = plains, the most-common on-foot-walkable real-land face; the mask 0x0010667F/0xD8FF3CFF admits it,
    topo 49/58/59 do NOT). Stored normals are (0,1,0); UVs are [0,0] -> stamp real atlas UVs with
    :func:`ff9mapkit.world.palette.apply_palette_uvs` before deploy.

    WINDING is what makes it walkable, NOT the stored normal: the engine's up-facing walkmesh filter tests the
    GEOMETRIC triangle normal ``Cross(v1-v0, v2-v0)`` (``WMBlock.cs:70`` builds it, ``WMPhysics.cs:22`` rejects any
    tri with ``Dot(up, n) <= 0.1``). These two tris per quad wind so that geometric normal is **+Y** (verified: for a
    flat tri the normal Y = ``e1.z*e2.x - e1.x*e2.z``; both windings below give ``+step^2``)."""
    from .extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    idall = float(encode_id(event=0, area=0, topograph=topograph))
    step = 64.0 / seg                                       # fixed 64u overworld block (extract.BLOCK_SIZE)
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    vi = 0

    def emit(px, pz):
        nonlocal vi
        pos.append([px, height, pz]); nrm.append([0.0, 1.0, 0.0])
        uv.append([0.0, 0.0]); tan.append([idall, 0.0, 0.0, 1.0])
        flat.append(vi); vi += 1

    for i in range(seg):
        for j in range(seg):
            x0, x1 = i * step, (i + 1) * step
            z0, z1 = -j * step, -(j + 1) * step                 # z0 nearer 0, z1 more negative (grid marches -Z)
            c00, c10, c11, c01 = (x0, z0), (x1, z0), (x1, z1), (x0, z1)
            for (a, b, c) in ((c00, c11, c01), (c00, c10, c11)):   # both UP-wound (+Y geometric normal)
                base = vi
                emit(*a); emit(*b); emit(*c)
                tris.append([base, base + 1, base + 2])
    chan = {CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan}
    channels = {CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}
    return BlockMesh(name=f"Block[{x}][{y}] Terrain", disc=disc, x=x, y=y, lod=lod, vcount=vi, stride=48,
                     channels=channels, chan_arrays=chan, flat_index=flat, tris=tris,
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def island_block_mesh(*, disc: int = 1, x: int = 0, y: int = 0, water_dirs, seg: int = 10, height: float = 6.0,
                       beach: float = 22.0, grass_topo: int = 0, shore_topo: int = 20, shore_frac: float = 0.30,
                       shore_dip: float = 0.0, lod: str = "0_1"):
    """Synthesize ONE block of a NATURAL island (vs :func:`flat_block_mesh`'s bare slab): a walkable GRASS plateau at
    ``Y=height`` that ramps DOWN to the waterline on each WATER-facing edge, textured GREEN GRASS (``grass_topo`` 0 --
    the atlas green tile, verified by sampling atlas pixel colors) on the flat top and TAN SAND (``shore_topo`` 20) on
    the low ring, so it reads as a grassy island with a sandy beach. Both topographs are WALKABLE (the player can walk
    the whole island down to the waterline; the surrounding stock sea is the wall). NOTE the atlas has no bright-white
    sand tile (real FF9 white beaches are a sea-side foam effect); topo 20 is the sandiest walkable land tile.

    ``water_dirs`` = the grid dirs (subset of ``{(-1,0),(1,0),(0,1),(0,-1)}``) whose neighbour is OPEN WATER for this
    cell; an INTERIOR island cell passes an EMPTY set -> a flat plateau (no beach). A vertex's Y ramps from ``shore_dip``
    (just under the sea, at a water edge) up to ``height`` over ``beach`` units inland -- so edges DIP under the water
    for a seamless blend and the top is a walkable plateau. ``shore_frac`` = the fraction of ``height`` below which a
    face is textured shore/sand (the beach band width). WINDING gives the +Y geometric normal regardless of the height
    profile (normal.y = e1.z*e2.x - e1.x*e2.z depends only on XZ), so every ramp face stays walkable + up-facing; a gentle
    ramp keeps ``Dot(up, n) > 0.1``. Call :func:`recompute_normals` after for correct slope shading."""
    from .extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    wd = set(tuple(d) for d in water_dirs)
    idg, ids = float(encode_id(topograph=grass_topo)), float(encode_id(topograph=shore_topo))
    step = 64.0 / seg

    def edge_dist(lx, lz, d):                                # world-XZ distance from (lx,lz) to this cell edge
        if d == (-1, 0):
            return lx                                        # west edge local x=0
        if d == (1, 0):
            return 64.0 - lx                                 # east edge local x=64
        if d == (0, -1):
            return -lz                                       # north edge local z=0 (lz in [-64,0])
        return lz + 64.0                                     # south edge local z=-64

    def hgt(lx, lz):
        if not wd:
            return height                                    # interior cell -> flat plateau
        m = min(edge_dist(lx, lz, d) for d in wd)
        return shore_dip + (height - shore_dip) * max(0.0, min(1.0, m / beach))

    shore_y = height * shore_frac
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    vi = 0

    def emit(px, pz, idall):
        nonlocal vi
        pos.append([px, hgt(px, pz), pz]); nrm.append([0.0, 1.0, 0.0])
        uv.append([0.0, 0.0]); tan.append([idall, 0.0, 0.0, 1.0])
        flat.append(vi); vi += 1

    for i in range(seg):
        for j in range(seg):
            x0, x1 = i * step, (i + 1) * step
            z0, z1 = -j * step, -(j + 1) * step
            c00, c10, c11, c01 = (x0, z0), (x1, z0), (x1, z1), (x0, z1)
            cy = 0.25 * (hgt(*c00) + hgt(*c10) + hgt(*c11) + hgt(*c01))    # quad mean height -> shore vs grass
            idall = ids if cy < shore_y else idg
            for (a, b, c) in ((c00, c11, c01), (c00, c10, c11)):           # both UP-wound (+Y geometric normal)
                base = vi
                emit(*a, idall); emit(*b, idall); emit(*c, idall)
                tris.append([base, base + 1, base + 2])
    chan = {CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan}
    channels = {CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}
    bm = BlockMesh(name=f"Block[{x}][{y}] Terrain", disc=disc, x=x, y=y, lod=lod, vcount=vi, stride=48,
                   channels=channels, chan_arrays=chan, flat_index=flat, tris=tris,
                   raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    recompute_normals(bm)                                    # slope shading (winding already gives up-facing geom normal)
    return bm


def cliff_block_mesh(*, disc: int = 1, x: int = 0, y: int = 0, cliff_dirs, seg: int = 10, land_height: float = 4.0,
                     rim_run: float = 1.2, roll_amp: float = 0.6, land_topo: int = 0, cliff_topo: int = 58,
                     profile_pow: float = 1.0, lod: str = "0_1"):
    """Synthesize ONE block of a CLIFF-walled island: a walkable rolling land top at ~``land_height`` that drops to the
    waterline (``Y=0``) via a STEEP near-vertical ROCK WALL on each cliff-facing edge -- the FAITHFUL (7,17) cliff
    profile (measured 2026-07-06: 100% of real cliff-face tris are >45deg, median **72deg**, ~4u drop over ~**1.2u**
    run), NOT :func:`island_block_mesh`'s gentle grid-smeared apron (24deg over 9u -- the wrong shape).

    THE KEY: the wall is SHARP because a vertex ROW is placed EXACTLY ``rim_run`` inside each cliff border (a
    NON-UNIFORM grid), so the full drop lands in one ~1.2u band instead of smearing across a uniform 6.4u grid quad.
    ``cliff_dirs`` = the grid dirs whose neighbour is open water (subset of ``{(-1,0),(1,0),(0,1),(0,-1)}``); an EMPTY
    set = a flat-topped interior cell (no wall). The wall tris carry ``cliff_topo`` (58, on-foot BLOCKED -- the player
    stops at the rim) for :func:`ff9mapkit.world.terrain._apply_cliff_rock_uvs` to texture grey rock; the top carries
    ``land_topo`` (0 = plains). A 74deg wall's geometric normal still has ``n.y = cos(74) ~ 0.28 > 0.1`` so it survives
    the engine's up-facing walkmesh filter (renders + collides); topo 58 is what blocks foot traffic, not the slope.

    CORNERS ARE TEAR-FREE: with a grid line at ``rim_run`` on BOTH cliff axes, the corner quad has three ``Y=0`` corners
    + one raised inner corner, so its two triangles share the low->high diagonal -- no mid-quad crease to split
    inconsistently (the exact failure mode of ``island_block_mesh``'s ``min()``-sampled ramp, which put the diagonal
    crease INSIDE a quad -> the triangular gaps). ``roll_amp`` undulation fades in PAST the rim (0 at the wall top) so
    the wall top stays a clean uniform line while the interior rolls like real land. Heights are a pure function of
    world XZ (coincident corners get identical Y) -> watertight. Call sequence mirrors island_block_mesh (winding gives
    the +Y geometric normal; :func:`recompute_normals` runs at the end for slope shading)."""
    from .extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    cd = set(tuple(d) for d in cliff_dirs)
    idL, idC = float(encode_id(topograph=land_topo)), float(encode_id(topograph=cliff_topo))

    def axis(lo, hi, cliff_lo, cliff_hi):                    # grid lines + a rim inset line on each cliff border
        lines = {lo + (hi - lo) * f / seg for f in range(seg + 1)}
        if cliff_lo:
            lines.add(lo + rim_run)
        if cliff_hi:
            lines.add(hi - rim_run)
        return sorted(lines)

    xs = axis(0.0, 64.0, (-1, 0) in cd, (1, 0) in cd)        # west border x=0, east x=64
    zs = axis(-64.0, 0.0, (0, 1) in cd, (0, -1) in cd)       # south border z=-64, north z=0

    def inset(lx, lz):                                       # world-XZ distance INWARD from the nearest cliff border
        ds = []
        if (-1, 0) in cd:
            ds.append(lx)                                    # from west (x=0)
        if (1, 0) in cd:
            ds.append(64.0 - lx)                             # from east (x=64)
        if (0, -1) in cd:
            ds.append(-lz)                                   # from north (z=0)
        if (0, 1) in cd:
            ds.append(lz + 64.0)                             # from south (z=-64)
        return min(ds) if ds else rim_run + 10.0

    def hgt(lx, lz):
        ins = inset(lx, lz)
        t = max(0.0, min(1.0, ins / rim_run))
        base = land_height * (t ** profile_pow)              # 0 at the border -> land_height at the rim (steep wall)
        rw = max(0.0, min(1.0, (ins - rim_run) / 6.0))       # fade the roll in past the rim (0 at the wall top)
        return base + roll_amp * math.sin(lx * 0.19 + 0.7) * math.cos(lz * 0.17 + 0.3) * rw

    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    vi = 0

    def emit(px, pz, idall):
        nonlocal vi
        pos.append([px, hgt(px, pz), pz]); nrm.append([0.0, 1.0, 0.0])
        uv.append([0.0, 0.0]); tan.append([idall, 0.0, 0.0, 1.0])
        flat.append(vi); vi += 1

    for ix in range(len(xs) - 1):
        for iz in range(len(zs) - 1):
            x0, x1 = xs[ix], xs[ix + 1]
            z0, z1 = zs[iz + 1], zs[iz]                       # z0 nearer 0, z1 more negative (island_block_mesh winding)
            c00, c10, c11, c01 = (x0, z0), (x1, z0), (x1, z1), (x0, z1)
            is_wall = any(inset(cx, cz) < rim_run - 1e-6 for (cx, cz) in (c00, c10, c11, c01))
            idall = idC if is_wall else idL
            for (a, b, c) in ((c00, c11, c01), (c00, c10, c11)):   # both UP-wound (+Y geometric normal)
                base = vi
                emit(*a, idall); emit(*b, idall); emit(*c, idall)
                tris.append([base, base + 1, base + 2])
    chan = {CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan}
    channels = {CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}
    bm = BlockMesh(name=f"Block[{x}][{y}] Terrain", disc=disc, x=x, y=y, lod=lod, vcount=vi, stride=48,
                   channels=channels, chan_arrays=chan, flat_index=flat, tris=tris,
                   raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    recompute_normals(bm)
    return bm


def tri_soup_block_mesh(triangles, *, name, disc: int = 1, x: int = 0, y: int = 0, lod: str = "0_1",
                        normal=(0.0, 1.0, 0.0)):
    """Build a :class:`~ff9mapkit.world.extract.BlockMesh` from a triangle SOUP -- ``triangles`` is a list of triangles,
    each a 3-list of ``((px, py, pz), (u, v))`` (position, uv) vertex pairs in the block's LOCAL frame. Verts are
    emitted FRESH per triangle (unindexed: ``vcount == indexCount``, matching the stock world blocks -- sharing verts
    would desync the flat index buffer). Every vertex gets the fixed ``normal`` and a trivial tangent ``[1,0,0,1]`` (no
    IDALL): this is a RENDER sub-mesh (a water / decor layer), NOT the collision Terrain (whose walkability comes from
    :func:`flat_block_mesh`'s winding + topograph). The overworld water synthesizer (:mod:`ff9mapkit.world.water`) emits
    its Sea3/Sea5/Sea4 layers through this."""
    from .extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    nx, ny, nz = normal
    pos, nrm, uv, tan = [], [], [], []
    for tri in triangles:
        for (p, t) in tri:
            pos.append([float(p[0]), float(p[1]), float(p[2])]); nrm.append([nx, ny, nz])
            uv.append([float(t[0]), float(t[1])]); tan.append([1.0, 0.0, 0.0, 1.0])
    n = len(pos)
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod=lod, vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=list(range(n)), tris=[[3 * k, 3 * k + 1, 3 * k + 2] for k in range(n // 3)],
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def hidden_block_mesh(*, name, disc: int = 1, x: int = 0, y: int = 0, lod: str = "0_1", y_depth: float = -80.0,
                      normal=(0.0, 1.0, 0.0)):
    """A single degenerate (near-zero-area) triangle far below the world at ``y_depth`` -- deploys as a sub-mesh override
    that renders NOTHING. Used to BLANK a donor block's sub-mesh part (e.g. the coast-only Sea1/Sea2 water a deep-ocean
    donor carries) so it does not draw on a synthesized-water cell."""
    from .extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    nx, ny, nz = normal
    pos = [[0.0, y_depth, 0.0], [0.1, y_depth, 0.0], [0.0, y_depth, 0.1]]
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod=lod, vcount=3, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[nx, ny, nz]] * 3, CH_UV: [[0.0, 0.0]] * 3,
                                  CH_TAN: [[1.0, 0.0, 0.0, 1.0]] * 3},
                     flat_index=[0, 1, 2], tris=[[0, 1, 2]], raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def place_building(dst_object_bm, src_object_bm, *, translate=(0.0, 0.0, 0.0), set_idall=None):
    """Append ``src_object_bm``'s geometry (a copied building/structure) onto ``dst_object_bm`` (a block's existing
    Object mesh), shifted by ``translate`` (dst block-LOCAL units). Returns a NEW merged
    :class:`~ff9mapkit.world.extract.BlockMesh` (deploy it with ``deploy_override(..., part="Object")``). The mesh is
    FLAT/unindexed, so appending = concatenate every channel + offset the index buffer; UVs/normals/tangent carry over
    so the copy renders with the shared world Object atlas. ``set_idall`` (optional) forces the appended tiles'
    ``tangent.x`` IDALL (the Object mesh is added to the WALKMESH form-1, so the building is collision -- keep the
    source's solid topograph, or pass e.g. ``encode_id(0, 0, <solid topo>)`` to normalize). Requires the two meshes to
    share channels (both are stock Object meshes → they do)."""
    from .extract import BlockMesh, CH_POS, CH_TAN
    if set(dst_object_bm.channels) != set(src_object_bm.channels):
        raise ValueError(f"channel mismatch dst{sorted(dst_object_bm.channels)} vs src{sorted(src_object_bm.channels)}")
    dx, dy, dz = translate
    off = dst_object_bm.vcount
    chan = {}
    for ci in dst_object_bm.channels:
        d = [list(v) for v in dst_object_bm.chan_arrays[ci]]
        s = [list(v) for v in src_object_bm.chan_arrays[ci]]
        if ci == CH_POS:
            s = [[v[0] + dx, v[1] + dy, v[2] + dz] for v in s]
        elif ci == CH_TAN and set_idall is not None:
            s = [[float(set_idall)] + v[1:] for v in s]
        chan[ci] = d + s
    flat = list(dst_object_bm.flat_index) + [i + off for i in src_object_bm.flat_index]
    tris = [list(t) for t in dst_object_bm.tris] + [[a + off, b + off, c + off] for (a, b, c) in src_object_bm.tris]
    return BlockMesh(name=dst_object_bm.name, disc=dst_object_bm.disc, x=dst_object_bm.x, y=dst_object_bm.y,
                     lod=dst_object_bm.lod, vcount=dst_object_bm.vcount + src_object_bm.vcount,
                     stride=dst_object_bm.stride, channels=dict(dst_object_bm.channels), chan_arrays=chan,
                     flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


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


def _point_in_polygon(px, pz, poly) -> bool:
    """Ray-cast point-in-polygon test for a world-XZ ``(x, z)`` polygon (ordered vertices)."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if (zi > pz) != (zj > pz) and px < (xj - xi) * (pz - zi) / (zj - zi) + xi:
            inside = not inside
        j = i
    return inside


def retarget_tiles(bm, *, event=None, area=None, topograph=None, center=None, radius=None,
                   world_origin=(0.0, 0.0), only_entrances: bool = False, exclude_box=None, only_box=None,
                   exclude_polygon=None, only_polygon=None) -> int:
    """Rewrite the per-triangle IDALL (stored in ``tangent.x``) for tiles in a region. ``event`` (0=land, 1-3=
    entrance-trigger bits), ``area`` (0-63), ``topograph`` (0-63 = terrain type) each default to KEEP the tile's
    current value. Sets tangent.x on all 3 corner verts of each affected triangle (the engine reads the HIT
    triangle's first-corner tangent.x as the mapid, WMBlock.cs). ``center``+``radius`` (world XZ) limit the region;
    ``only_entrances`` restricts to tiles already carrying event bits. ``exclude_box`` (world XZ
    ``(xmin, xmax, zmin, zmax)``) SKIPS tiles whose centroid falls inside it -- used to keep entrance-trigger tiles
    OUT from under a building footprint (a tile under an impassable structure boxes the player who triggers there).
    ``only_box`` (same form) is the INVERSE -- restrict to tiles INSIDE it; with ``topograph=59`` it makes the terrain
    UNDER a building impassable so the whole footprint blocks and the player stops at its EDGE (the terrain conforms to
    the ground, so it blocks reliably where a flat floating prop base would bury/float). Geometry (verts/normals/uv) is
    UNTOUCHED. Returns the triangle count changed.

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
        if any(r is not None for r in (radius if center is not None else None,
                                       exclude_box, only_box, exclude_polygon, only_polygon)):
            cx = (verts[tri[0]][0] + verts[tri[1]][0] + verts[tri[2]][0]) / 3.0 + ox
            cz = (verts[tri[0]][2] + verts[tri[1]][2] + verts[tri[2]][2]) / 3.0 + oz
            if center is not None and radius is not None and math.hypot(cx - center[0], cz - center[1]) > radius:
                continue
            if exclude_box is not None:
                xmn, xmx, zmn, zmx = exclude_box
                if xmn <= cx <= xmx and zmn <= cz <= zmx:
                    continue                                  # tile under the building -> skip (would box the player)
            if only_box is not None:
                xmn, xmx, zmn, zmx = only_box
                if not (xmn <= cx <= xmx and zmn <= cz <= zmx):
                    continue                                  # only tiles INSIDE the box (the footprint block)
            if exclude_polygon is not None and _point_in_polygon(cx, cz, exclude_polygon):
                continue                                      # tile inside the building outline -> skip (trigger)
            if only_polygon is not None and not _point_in_polygon(cx, cz, only_polygon):
                continue                                      # only tiles inside the building OUTLINE (tight block)
        idall = encode_id(d["event"] if event is None else event,
                          d["area"] if area is None else area,
                          d["topograph"] if topograph is None else topograph, d["flags"])
        for vi in tri:
            tan[vi][0] = float(idall)
        changed += 1
    return changed
