"""Read FF9 WORLD-MAP block meshes out of the install's p0data, OFFLINE -- the Path-C (geometry-edit) foundation.

The overworld's per-block TERRAIN mesh is the authoritative source for RENDER **and** COLLISION/height **and**
the per-tile world-map/event id: Memoria's ``w_nwpHit`` (ff9.cs:7141) does NOT parse the legacy ``model_hm.nwp``
PSX packs -- it raycasts this Unity mesh (``WMBlock.Raycast`` -> ``WMPhysics.Raycast``) and reads the hit
triangle's id from ``tangent.x`` (``mapid = (Int32)tangents[triangles[t*3]].x``, WMBlock.cs:231). That id feeds
``m_GetIDEvent`` -> the world ``.eb`` -> ``Field()``. So extracting (and later editing) this mesh is how Path C
reshapes terrain and re-points which (forked) place a world tile reaches.

Mesh location (container, lower-cased): ``assets/resources/worldmap/disc{D}/0_1/r{Y}/block[{X}][{Y}] terrain``.
``0_1`` is the LOD that becomes the Form-1 walkmesh (``0_2`` is a far LOD). The mesh is FLAT/unindexed -- vertex
count == index count == 3*triangleCount -- so triangle ``t``'s corners are the index-buffer entries ``3t,3t+1,3t+2``
and its id is ``int(tangent.x)`` of the first corner.

Read-only on the install (everything is written to the caller's out dir). Reuses the field/battle UnityPy bundle
cache + the packed Unity-5 ``m_VertexData`` decode approach (cf. :func:`ff9mapkit.battle.extract._decode_mesh`).
"""
from __future__ import annotations

import json
import struct
from collections import Counter, OrderedDict
from dataclasses import dataclass, field as _dcfield, replace as _dc_replace
from pathlib import Path

from .. import config

# Unity-5 vertex channel indices used by these meshes.
CH_POS, CH_NRM, CH_UV, CH_TAN = 0, 1, 3, 7
_WM_BUNDLE_HINT = ".ff9mapkit-worldmap-bundle.json"

# World-map block grid frame (verified in Memoria WMWorld.cs:454-458 + the GetAbsolutePositionOf variants, and
# corroborated empirically -- every disc-1 block's local verts span x[0,64] z[-64,0], only Y differs per block):
# a block is 64x64 Unity units; its LOCAL verts are translated to world by the engine, worldVert = block_world_origin
# + localVert, with Z NEGATED (grid row y advances toward -Z). This is THE frame for cross-block (seam-continuous)
# geometry edits -- a deform must be evaluated in world XZ so coincident seam verts get the identical delta.
BLOCK_SIZE = 64


def block_world_origin(x: int, y: int) -> tuple:
    """The ``(worldX, worldZ)`` origin the engine translates block ``[x][y]``'s LOCAL verts by:
    ``worldVert = (x*64 + localX, localY, -y*64 + localZ)``. Z is negated. (Memoria ``WMWorld.cs``:
    ``transform.position.x = x*64``, ``.z = -y*64``; the mesh copy sits at ``localPosition = 0``.)"""
    return (x * BLOCK_SIZE, -y * BLOCK_SIZE)


def footprint_nearest_dist(x: int, y: int, cx: float, cz: float) -> float:
    """World-XZ distance from point ``(cx, cz)`` to the NEAREST point of block ``[x][y]``'s 64x64 world footprint
    (``x*64..x*64+64`` by ``-y*64-64..-y*64``); 0 if the point is inside. The crack-free deploy test: a reshape of
    radius ``r`` about ``(cx, cz)`` touches block ``[x][y]`` iff this <= ``r`` -- and any block it does NOT touch has
    its whole footprint (incl. shared edges) beyond ``r``, so those seams stay at zero delta on both sides."""
    fx0, fx1 = x * BLOCK_SIZE, x * BLOCK_SIZE + BLOCK_SIZE
    fz1, fz0 = -y * BLOCK_SIZE, -y * BLOCK_SIZE - BLOCK_SIZE
    ddx = max(fx0 - cx, 0.0, cx - fx1)
    ddz = max(fz0 - cz, 0.0, cz - fz1)
    return (ddx * ddx + ddz * ddz) ** 0.5


def blocks_touched(cx: float, cz: float, radius: float, blocks) -> list:
    """The subset of existing ``blocks`` (``(x, y)`` pairs, e.g. from :func:`list_blocks`) whose world footprint comes
    within ``radius`` of ``(cx, cz)`` -- the exact, crack-free set to redeploy for a radius-``radius`` reshape,
    IN THE GRID INTERIOR ONLY. THE SEAM EXCEPTION (audit rec 12): footprints are unwrapped, so within ``radius``
    of the world seam (x=0/1536 or z=0/-1280) the toroidal neighbour across the seam is NOT in this set -- a
    cross-seam edit must handle the far side itself (``terrain.reshape`` reports the drop as ``off_grid``)."""
    return sorted((x, y) for (x, y) in blocks if footprint_nearest_dist(x, y, cx, cz) <= radius)


def decode_id(idall: int) -> dict:
    """Unpack a per-triangle ``tangent.x`` value (the engine's ``IDALL``) into its bit-fields, mirroring
    ff9.cs ``m_GetIDEvent``/``m_GetIDArea``/``m_GetIDTopograph``:

      * ``event``     (bits 14-15) -- 0 = plain terrain; 1-3 = a PLACE/field ENTRANCE tile (fires the world
        ``.eb`` via ``m_GetIDEvent`` -> ``WorldEvent``; the event id is packed into the cell tag, so it must
        match the dispatcher trigger's tag low bits).
      * ``area``      (bits 8-13)  -- a coarse REGIONAL tag (0-63) shared across whole neighbourhoods; NOT read
        by entrance dispatch (``WorldEvent`` packs the walked CELL, not these bits -- see ``world/locate.py``).
      * ``topograph`` (bits 2-7)   -- terrain type (0-63): drives encounters / movement / footstep sfx.
      * ``flags``     (bits 0-1).
    """
    return {"event": (idall & 0xC000) >> 14, "area": (idall & 0x3F00) >> 8,
            "topograph": (idall & 0xFC) >> 2, "flags": idall & 3}


def encode_id(event: int = 0, area: int = 0, topograph: int = 0, flags: int = 0) -> int:
    """Pack ``{event, area, topograph, flags}`` back into an IDALL (the inverse of :func:`decode_id`) -- the
    per-triangle ``tangent.x`` value. ``event`` 0=plain land, 1-3=fires the cell's dispatcher trigger (the id is
    part of the matched tag); ``area`` 0-63 = the cosmetic regional tag (NOT the dispatch case -- the destination
    comes from the world ``.eb`` object-0 trigger GetIP-keyed to the CELL); ``topograph`` 0-63 = terrain type
    (movement/encounters). Used to arm/disarm a tile's trigger bits or retype terrain (``world-retarget``)."""
    return ((event & 3) << 14) | ((area & 0x3F) << 8) | ((topograph & 0x3F) << 2) | (flags & 3)


def _unitypy():
    from ..extract import _unitypy as _u           # reuse the field extractor's lazy import + error message
    return _u()


_CLASS_ID_MESH = None


def _class_id_mesh():
    """Lazily-cached ``UnityPy.enums.ClassIDType.Mesh`` member. ``o.type`` (every object in ``env.objects``)
    is already a genuine ``ClassIDType`` (UnityPy ``ObjectReader.type``), so comparing it directly against
    this member -- instead of stringifying via ``o.type.name`` -- selects the identical object set (the
    enum's ``.name`` IS the literal string ``"Mesh"`` by construction) while skipping the ``DynamicClassAttribute``
    descriptor dispatch that dominated read_block's hot-loop profile. Import stays lazy (not at module top)
    to match :func:`_unitypy`'s deferred-install-error contract."""
    global _CLASS_ID_MESH
    if _CLASS_ID_MESH is None:
        from UnityPy.enums import ClassIDType      # noqa: PLC0415
        _CLASS_ID_MESH = ClassIDType.Mesh
    return _CLASS_ID_MESH


def _streaming_assets(game=None) -> Path:
    return config.find_game_path(game) / "StreamingAssets"


def _bundles(game=None):
    from ..extract import _bundles as _b
    return _b(game)


def _load_env(path):
    from ..extract import _load_env as _l           # bounded-LRU cache of static base-game bundles
    return _l(path)


#: per-process memo of ``_worldmap_env`` outcomes, keyed (StreamingAssets path, disc) -- POSITIVE and
#: NEGATIVE. The hint file below caches only WINNERS, so a disc with no bundle (a synthetic namespace,
#: e.g. 9) used to trigger the full ~50-bundle rescan on EVERY call: profiled at 97% of a coast-nav
#: stamp's runtime (928 UnityPy loads for one cell). A miss is now paid once per process.
_WM_ENV_MEMO: dict = {}


def _worldmap_env(disc: int = 1, game=None):
    """The loaded p0data bundle that holds the worldmap terrain meshes for ``disc``. Caches the winning bundle
    basename next to StreamingAssets so we don't rescan ~50 bundles every call (p0data3 first -- where they live).
    A disc with NO winning bundle is memoized too (see ``_WM_ENV_MEMO``) and re-raises without rescanning."""
    _unitypy()                                       # surface the install/UnityPy error early
    sa = _streaming_assets(game)
    memo_key = (str(sa), int(disc))
    if memo_key in _WM_ENV_MEMO:
        env, err = _WM_ENV_MEMO[memo_key]
        if err is not None:
            raise ValueError(err)
        return env
    needle = f"worldmap/disc{disc}/0_1/"
    hint = sa / _WM_BUNDLE_HINT

    def _has(env) -> bool:
        return any(needle in (k or "").lower() and "terrain" in (k or "").lower() for k in env.container)

    if hint.is_file():
        try:
            bn = json.loads(hint.read_text(encoding="utf-8")).get(str(disc))
            if bn and (sa / bn).is_file():
                env = _load_env(str(sa / bn))
                if _has(env):
                    _WM_ENV_MEMO[memo_key] = (env, None)
                    return env
        except (OSError, ValueError, KeyError):
            pass
    ordered = sorted(_bundles(game), key=lambda p: (0 if "p0data3." in Path(p).name else 1, p))
    for path in ordered:
        try:
            env = _load_env(path)
        except Exception:                            # noqa: BLE001 -- a non-bundle/odd file -> skip, keep scanning
            continue
        if _has(env):
            try:
                cur = json.loads(hint.read_text(encoding="utf-8")) if hint.is_file() else {}
                cur[str(disc)] = Path(path).name
                hint.write_text(json.dumps(cur), encoding="utf-8")
            except OSError:
                pass
            _WM_ENV_MEMO[memo_key] = (env, None)
            return env
    msg = (f"no worldmap terrain meshes (container {needle!r}) found in StreamingAssets/p0data*.bin "
           f"-- is this a full FF9 install?")
    _WM_ENV_MEMO[memo_key] = (None, msg)
    raise ValueError(msg)


@dataclass
class BlockMesh:
    """One decoded world block terrain mesh + everything needed to re-encode it losslessly (the edit foundation).

    ``chan_arrays`` holds EVERY non-empty vertex channel (``ci -> [[float, ...], ...]``); ``channels`` is its
    ``ci -> (byte_offset, dimension)`` layout within the interleaved ``stride``-byte vertex. ``flat_index`` is the
    raw index buffer; ``tris`` is it grouped into triangles. ``raw_vbuf``/``raw_ibuf`` are the original bytes."""
    name: str
    disc: int
    x: int
    y: int
    lod: str
    vcount: int
    stride: int
    channels: dict
    chan_arrays: dict
    flat_index: list
    tris: list
    raw_vbuf: bytes
    raw_ibuf: bytes
    use32: bool
    submeshes: list = _dcfield(default_factory=list)

    @property
    def verts(self):
        return self.chan_arrays.get(CH_POS)

    @property
    def normals(self):
        return self.chan_arrays.get(CH_NRM)

    @property
    def uvs(self):
        return self.chan_arrays.get(CH_UV)

    @property
    def tangents(self):
        return self.chan_arrays.get(CH_TAN)


def _decode_world_mesh(mesh_pptr, *, disc: int, x: int, y: int, lod: str) -> BlockMesh:
    md = mesh_pptr.read()
    vd = md.m_VertexData
    raw = bytes(vd.m_DataSize)
    vcount = int(vd.m_VertexCount)
    if not raw:
        raise ValueError(f"block[{x}][{y}] terrain: vertex data is streamed (m_DataSize empty) -- "
                         f"streamed-mesh decode not implemented yet")
    chans = vd.m_Channels
    channels, stride = {}, 0
    for ci, c in enumerate(chans):
        if c.dimension:
            channels[ci] = (int(c.offset), int(c.dimension))   # format 0 == float32
            stride = max(stride, int(c.offset) + int(c.dimension) * 4)
    if vcount * stride != len(raw):
        raise ValueError(f"block[{x}][{y}] vertex stride mismatch (v{vcount} * s{stride} != {len(raw)})")

    def rd(ci, vi):
        off, dim = channels[ci]
        return list(struct.unpack_from("<%df" % dim, raw, vi * stride + off))

    chan_arrays = {ci: [rd(ci, i) for i in range(vcount)] for ci in channels}

    ib = bytes(md.m_IndexBuffer)
    use32 = getattr(md, "m_IndexFormat", None) == 1 or getattr(md, "m_Use16BitIndices", 1) in (0, False)
    ent = 4 if use32 else 2
    flat = list(struct.unpack("<%d%s" % (len(ib) // ent, "I" if use32 else "H"), ib))
    submeshes = [(int(s.firstByte), int(s.indexCount)) for s in md.m_SubMeshes]
    tris = [[flat[i], flat[i + 1], flat[i + 2]] for i in range(0, len(flat) - 2, 3)]
    return BlockMesh(name=md.m_Name, disc=disc, x=x, y=y, lod=lod, vcount=vcount, stride=stride,
                     channels=channels, chan_arrays=chan_arrays, flat_index=flat, tris=tris,
                     raw_vbuf=raw, raw_ibuf=ib, use32=use32, submeshes=submeshes)


# read_block() is the hot path of every worldmap sweep (world-morphs/transplant/coastmorph/island/...):
# a naive call re-scans ALL of env.objects (~18.6k) for the matching container string AND re-decodes the
# vertex buffer, even when the SAME block was just read for a neighbor/donor lookup moments ago. Both costs
# are memoized here, per env (an env is process-lifetime-cached by extract._load_env's bounded LRU, so tying
# these to it needs no separate invalidation: the source p0data*.bin bytes are static for the process, and an
# evicted+GC'd env simply takes its index/memo with it). UnityPy's Environment has no __slots__, so they're
# stashed as plain attributes rather than an external id(env)-keyed dict (which would risk id-reuse aliasing
# after an eviction). Neither ever sees a DEPLOYED mod-folder override -- those are a wholly separate,
# already-uncached loose-.ff9mesh path (mesh.blockmesh_from_ff9mesh, via entrance.read_block_stacked /
# interior.read_deployed_blocks) that never calls into read_block/_worldmap_env at all.
def _mesh_index(env) -> dict:
    """Once per env: ``{container_lower: mesh_pptr}`` over every Mesh-typed object, ``setdefault`` so a
    hypothetical duplicate container resolves to the FIRST one in ``env.objects`` order -- exactly matching
    the original per-call linear scan's semantics (no duplicates found on disc 1: 2199/2199 distinct)."""
    idx = getattr(env, "_ff9mapkit_mesh_index", None)
    if idx is None:
        idx = {}
        mesh_type = _class_id_mesh()               # enum-member compare -- no .name descriptor dispatch
        for o in env.objects:
            if o.type != mesh_type:
                continue
            c = (getattr(o, "container", None) or "").lower()
            if c:
                idx.setdefault(c, o)
        env._ff9mapkit_mesh_index = idx
    return idx


_BLOCK_MEMO_MAX = 512          # masters are ~0.4 MB avg; unbounded, a host that read every key would retain ~800 MB


def _block_memo(env) -> OrderedDict:
    """Once per env: ``{(disc, lod, x, y, part): BlockMesh}`` decode memo (bounded LRU, ``_BLOCK_MEMO_MAX``).
    Holds the MASTER decode only -- every :func:`read_block` call still returns its own independent copy
    (:func:`_copy_blockmesh`), so a caller that mutates its result in place (``mesh.lift_block`` and friends)
    can never corrupt a later, unrelated read of the "same" block. Bounded so a long-lived host (the Workspace,
    the test suite) stays flat; sweep locality keeps the hit rate."""
    memo = getattr(env, "_ff9mapkit_block_memo", None)
    if memo is None:
        memo = OrderedDict()
        env._ff9mapkit_block_memo = memo
    return memo


def _copy_blockmesh(master: BlockMesh) -> BlockMesh:
    """A fresh, independently-mutable ``BlockMesh`` built from the memoized ``master``. Every in-place
    mutator in ``mesh.py`` (``lift_block``, ``raise_vertex_near_center``, ``deform_radial``, ``deform_ridge``,
    ``flatten_region``, ``recompute_normals``, ``retarget_tiles``) writes into a ROW element (``v[1] +=
    amount``, ``tan[vi][0] = x``), never replaces a whole ``chan_arrays[ci]`` list -- so one level of
    row-copy fully isolates the copy. ``tris``/``flat_index``/``channels``/``submeshes`` are copied one
    level too (cheap -- their elements are immutable ints/tuples -- and it keeps the invariant uniform
    rather than a fragile per-field allowlist a future mutator could silently violate). Only the truly
    immutable fields are shared: ``raw_vbuf``/``raw_ibuf`` (``bytes``) and ``use32``."""
    return _dc_replace(master,
                       chan_arrays={ci: [row[:] for row in arr] for ci, arr in master.chan_arrays.items()},
                       tris=[t[:] for t in master.tris],
                       flat_index=master.flat_index[:],
                       channels=dict(master.channels),
                       submeshes=list(master.submeshes))


def read_block(x: int, y: int, *, disc: int = 1, lod: str = "0_1", part: str = "terrain", game=None) -> BlockMesh:
    """Decode disc ``disc`` block ``(x, y)``'s sub-mesh. ``x`` in 0..23, ``y`` in 0..19. ``part`` selects the block
    layer: ``"terrain"`` (ground + walkmesh + the tangent.x entrance IDALL) or ``"object"`` (the baked buildings /
    towns / trees + decorative geometry). Only ~63 blocks carry an ``object`` mesh (those with a structure);
    :func:`list_object_blocks` enumerates them."""
    env = _worldmap_env(disc, game)
    key = (disc, lod, x, y, part)
    from ..extract import env_lock                   # decode/index seek the env's SHARED stateful reader, and a
    with env_lock:                                   # memoized race would poison the cache PERMANENTLY (extract.py:89)
        memo = _block_memo(env)
        master = memo.get(key)
        if master is None:
            target = f"worldmap/disc{disc}/{lod}/r{y}/block[{x}][{y}] {part.lower()}"
            o = None
            for c, oo in _mesh_index(env).items():   # insertion order == env.objects order: first match wins,
                if c.endswith(target) or (target in c):   # exactly the original linear scan's semantics
                    o = oo
                    break
            if o is None:
                raise ValueError(f"disc{disc} block[{x}][{y}] {part} mesh not found (looked for container {target!r})")
            master = _decode_world_mesh(o, disc=disc, x=x, y=y, lod=lod)
            memo[key] = master
            while len(memo) > _BLOCK_MEMO_MAX:
                memo.popitem(last=False)
        else:
            memo.move_to_end(key)
        return _copy_blockmesh(master)


def list_object_blocks(*, disc: int = 1, lod: str = "0_1", game=None) -> list:
    """Every ``(x, y)`` that carries an ``object`` (building/structure) sub-mesh -- the blocks with a town/dungeon/
    landmark you can copy from or augment. (~63 of the ~260 terrain blocks on disc 1.)"""
    import re
    env = _worldmap_env(disc, game)
    pat = re.compile(rf"worldmap/disc{disc}/{lod}/r\d+/block\[(\d+)\]\[(\d+)\] object(?:\.asset)?$")
    found = set()
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            found.add((int(m.group(1)), int(m.group(2))))
    return sorted(found)


def list_coastal_donors(*, disc: int = 1, lod: str = "0_1", game=None, beach_only: bool = True) -> dict:
    """``{(x, y): [sub-meshes]}`` for every LAND block that carries a coastal water sub-mesh -- the real COAST pieces
    a faithful reclaim (``terrain.coast`` / ``world-coast``) can copy so the reclaimed cell renders that block's
    animated beach + sea + foam (Path D). ``beach_only`` (default) keeps only blocks with a dedicated ``beach1`` mesh
    (a proper sandy beach, e.g. (18,15) -- the proven donor); set False to also include plain ``sea``-fringed coasts.
    The white sand + foam is the ``beach1``/``sea`` sub-mesh (animated ``WMRenderTextureBank``), NOT a terrain tile,
    which is why these must be CARRIED, not textured. Detected by the block's bundle sub-mesh containers."""
    import re
    env = _worldmap_env(disc, game)
    land = set(list_blocks(disc=disc, lod=lod, game=game))
    pat = re.compile(rf"worldmap/disc{disc}/{lod}/r\d+/block\[(\d+)\]\[(\d+)\] (beach1|beach2|sea\d)")
    found: dict = {}
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            xy = (int(m.group(1)), int(m.group(2)))
            if xy in land:
                found.setdefault(xy, set()).add(m.group(3))
    out = {xy: sorted(subs) for xy, subs in sorted(found.items())
           if (not beach_only or any(s.startswith("beach") for s in subs))}
    return out


def list_blocks(*, disc: int = 1, lod: str = "0_1", game=None) -> list:
    """Every ``(x, y)`` whose terrain mesh exists for ``disc`` (sorted) -- the real grid the engine streams."""
    import re
    env = _worldmap_env(disc, game)
    pat = re.compile(rf"worldmap/disc{disc}/{lod}/r\d+/block\[(\d+)\]\[(\d+)\] terrain(?:\.asset)?$")
    found = set()
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            found.add((int(m.group(1)), int(m.group(2))))
    return sorted(found)


def block_mapids(bm: BlockMesh) -> list:
    """Per-triangle raw ``IDALL`` (= ``int(tangent.x of index-buffer[3t])``, the engine's exact rule). Decode
    each with :func:`decode_id` for {event, area, topograph}."""
    tan = bm.tangents
    if tan is None:
        return []
    return [int(round(tan[bm.flat_index[t * 3]][0])) for t in range(len(bm.tris))]


def block_summary(bm: BlockMesh) -> dict:
    """A human read of a block: triangle count, the PLACE ENTRANCES it carries (tiles whose event bits are set
    -- these fire the world ``.eb``), the terrain TOPOGRAPHS present, and the raw id histogram."""
    ids = block_mapids(bm)
    counts = Counter(ids)
    entrances = [{"area": d["area"], "event": d["event"], "idall": i, "tris": counts[i]}
                 for i in sorted(counts) for d in (decode_id(i),) if d["event"]]
    topographs = sorted({decode_id(i)["topograph"] for i in counts})
    xs = [v[0] for v in bm.verts]
    ys = [v[1] for v in bm.verts]
    zs = [v[2] for v in bm.verts]
    return {
        "name": bm.name, "disc": bm.disc, "block": [bm.x, bm.y], "lod": bm.lod,
        "vertices": bm.vcount, "triangles": len(bm.tris),
        "place_entrances": entrances,                 # tiles with event!=0 -> a world-.eb place handler
        "place_areas": sorted({e["area"] for e in entrances}),
        "topographs": topographs,                     # terrain types present in this block
        "distinct_ids": sorted(counts),
        "id_counts": {str(k): v for k, v in sorted(counts.items())},
        "bounds": {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)], "z": [min(zs), max(zs)]},
    }


def pack_vbuf(bm: BlockMesh, *, base: bytes | None = None) -> bytes:
    """Re-encode the interleaved vertex buffer from ``chan_arrays``. ``base=None`` -> from zeros (a STRICT
    round-trip: equals ``raw_vbuf`` iff every byte lives in a channel); ``base=raw_vbuf`` -> patch-in-place
    (preserves any inter-channel padding -- the safe path for editing a few values)."""
    out = bytearray(base if base is not None else bytes(len(bm.raw_vbuf)))
    for ci, (off, dim) in bm.channels.items():
        for vi, vals in enumerate(bm.chan_arrays[ci]):
            struct.pack_into("<%df" % dim, out, vi * bm.stride + off, *vals)
    return bytes(out)


def roundtrip_ok(bm: BlockMesh) -> bool:
    """True iff re-encoding the vertex buffer from the decoded channels reproduces the original bytes exactly --
    proves the decode is lossless (so a later edit can write back faithfully)."""
    return pack_vbuf(bm) == bm.raw_vbuf


def to_obj(bm: BlockMesh, path) -> Path:
    """Write the block mesh as a plain OBJ (positions + normals + faces) for visual inspection / Blender import.
    Block-local coordinates (no world placement). 1-based OBJ indices."""
    path = Path(path)
    verts, normals = bm.verts, bm.normals
    lines = [f"# ff9mapkit world block disc{bm.disc} [{bm.x}][{bm.y}] -- {bm.name}",
             f"# {bm.vcount} verts, {len(bm.tris)} tris"]
    for v in verts:
        lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
    if normals:
        for n in normals:
            lines.append(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}")
    for a, b, c in bm.tris:
        if normals:
            lines.append(f"f {a + 1}//{a + 1} {b + 1}//{b + 1} {c + 1}//{c + 1}")
        else:
            lines.append(f"f {a + 1} {b + 1} {c + 1}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def extract_block(x: int, y: int, *, disc: int = 1, lod: str = "0_1", out_dir, game=None) -> dict:
    """Extract one block to ``out_dir``: ``block_{x}_{y}.obj`` (geometry) + ``block_{x}_{y}.mapids.json``
    (per-triangle ids + summary). Returns the summary dict (with a ``roundtrip`` flag + written paths)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    bm = read_block(x, y, disc=disc, lod=lod, game=game)
    summ = block_summary(bm)
    summ["roundtrip"] = roundtrip_ok(bm)
    obj = out_dir / f"block_{x}_{y}.obj"
    to_obj(bm, obj)
    j = out_dir / f"block_{x}_{y}.mapids.json"
    j.write_text(json.dumps({"summary": summ, "tri_mapids": block_mapids(bm)}, indent=1), encoding="utf-8")
    summ["files"] = {"obj": str(obj), "mapids": str(j)}
    return summ
