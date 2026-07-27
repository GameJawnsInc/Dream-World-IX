"""Offline READ-side parser for FF9's ``ef###.bytes`` special-effect container -- the layer that reaches
a summon creature's skeleton, meshes and motion clips.

This is the committable, kit-side port of the study parser
``studies/custom-summons/thomas-swap/disasm/ef_container.py`` (validated 372/372 stock files). It reads a
caller-supplied blob -- a stock ``ef###.bytes`` the user extracted from their own install -- and returns
offsets, counts and typed structures. It **embeds no game bytes and writes nothing**; it is a parser only
(the writer lives elsewhere).

Provenance of every rule is the disassembly of the user's own ``FF9SpecialEffectPlugin.dll`` (x64,
``ImageBase 0x180000000``), recorded in the study's ``FORMAT.md`` / ``D3-container-validate.md``. Field
names below follow ``FORMAT.md``.

WHAT THIS REACHES (the transplant read path, FORMAT.md §2.1):

    parse_header(blob)              -> Container (chunk/resource table, native walker fn 0xd390)
    creature_package(blob)          -> ModelPackage (ids 4+5: the creature header + model-address map)
    creature_geom(blob, mp)         -> Geom (the skeleton parent+length tree + the mesh table)
    mp.motion_file_offsets          -> the N motion-clip payload offsets (decoded by summons.motion)

The GEOM block carries an indexed-pool, rigid-run-length-skinned model: a ``BoneLink`` parent/length tree,
a mesh table of eight ``POLY_*`` buckets, and per-mesh vertex/uv/colour pools. Every creature in the game
uses only ``FT4`` + ``FT3`` (flat-shaded textured quads/tris with inline neutral-grey RGB).

WHAT THE EDIT LANES ADD (the reskin / rescore read path -- same parser, wider reach):

    parse_directory(blob, base)     -> the id-2 sub-file directory (signed table-relative offsets)
    parse_op_stream(blob)           -> the sequence stream as ``Op(at, code, arg1, arg2)`` records
    scan_geom(blob, start, end)     -> every GEOM block in a span, not just the creature's own
    Geom.end                        -> a scanned block's REGION end (the chain-closure colour-pool end)

These four exist because a creature's own GEOM is reached directly by ``creature_geom`` while every
OTHER GEOM in a container -- and the camera sub-files the sequence names -- can only be found by
walking. They embed no game bytes either; the study's disassembly-provenance parser
(``studies/custom-summons/thomas-swap/disasm/ef_container.py``) remains the record of where each rule
came from.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

SECTOR = 0x800

__all__ = [
    "ContainerError", "SECTOR", "SEQ_OFFSET", "RESOURCE_IDS", "STREAMED_IDS",
    "PRIM_TYPES", "PRIM_FIELDS", "MAX_VERTS_PER_MESH",
    "Resource", "Chunk", "Container", "parse_header", "parse_directory",
    "Op", "parse_op_stream",
    "BoneLink", "Mesh", "Geom", "parse_geom", "geom_checks", "scan_geom",
    "iter_primitives", "vertices", "bone_of_vertex",
    "ModelPackage", "parse_model_package", "creature_geom", "creature_package", "vram_rect",
]


class ContainerError(RuntimeError):
    """Raised when the container / model bytes fail a structural law (parser drift or a bad blob)."""


# --------------------------------------------------------------------------- little-endian readers
def _s16(b: bytes, o: int) -> int: return struct.unpack_from("<h", b, o)[0]
def _u16(b: bytes, o: int) -> int: return struct.unpack_from("<H", b, o)[0]
def _u32(b: bytes, o: int) -> int: return struct.unpack_from("<I", b, o)[0]
def _s32(b: bytes, o: int) -> int: return struct.unpack_from("<i", b, o)[0]
def _a4(v: int) -> int: return (v + 3) & ~3


# --------------------------------------------------------------------------- resource ids
# The 10-entry dispatch table @0x3ed54 reached from the sector-feed state machine (fn 0x3de37). Only the
# ids the creature read path needs are documented here; ``kind`` names them for a summary listing. ids
# {0,1,4,9} are streamed one payload per tick (bitmask 0x213 @0x3e632).
RESOURCE_IDS = {
    0: "VRAM_IMAGE_LIST",
    1: "VRAM_IMAGE_CONT",
    2: "SUBFILE_ARCHIVE",     # sub-file directory + camera/sound blocks
    3: "CHUNK_IMAGE",         # the PS1 main-RAM image = MIPS effect program
    4: "VRAM_TEXPAGE",        # creature texture pages + CLUT; ALSO carries the model-package header
    5: "SUMMON_MODEL",        # the creature model image -> Hi_RegisterSummonModel
    6: "MARK_6",
    7: "MARK_7",
    8: "MARK_8",
    9: "VRAM_TEXPAGE_ALT",
}
STREAMED_IDS = {0, 1, 4, 9}


# --------------------------------------------------------------------------- container structures
@dataclass
class Resource:
    """One resource-table entry (fn 0xd390). ``offset``/``nbytes`` are the absolute file span of the
    0x800-aligned payload."""
    index: int
    id: int
    info: int
    size_sectors: int
    offset: int
    nbytes: int
    extra_sectors: Optional[int] = None   # present only when id==2 and info!=0 (the one conditional field)

    @property
    def kind(self) -> str:
        return RESOURCE_IDS.get(self.id, f"UNKNOWN_{self.id}")


@dataclass
class Chunk:
    slot: int             # table ordinal -- the psx-base double-buffer parity key
    chunk_index: int
    resources: List[Resource] = field(default_factory=list)

    @property
    def psx_base(self) -> int:
        """fn 0xd390@0xd431: 0x801E7700 + (slot & 1) * 0x5000."""
        return 0x801E7700 + (self.slot & 1) * 0x5000


@dataclass
class Container:
    size: int
    chunks: List[Chunk]
    table_end: int        # file offset just past the resource table
    cursor_end: int       # the walker's final resourcePosition -- MUST equal size on a clean blob


def parse_header(blob: bytes, strict: bool = True) -> Container:
    """Port of fn 0xd390 (the native resource-table walker). Every width/signedness matches the
    disassembly: chunkCount/chunkIndex/resourceCount/size read signed-16; id/info signed-8. The format's
    only self-check is that the running payload cursor lands exactly on the file length."""
    off = 0
    chunk_count = _s16(blob, off); off += 2
    pos = SECTOR                                        # r11d = 0x800 @0xd3ab
    chunks: List[Chunk] = []
    for i in range(chunk_count):
        ci = _s16(blob, off); rc = _s16(blob, off + 2); off += 4
        ch = Chunk(slot=i, chunk_index=ci)
        for j in range(rc):
            rid = struct.unpack_from("<b", blob, off)[0]
            info = struct.unpack_from("<b", blob, off + 1)[0]
            size = _s16(blob, off + 2)
            nbytes = size << 11
            r = Resource(index=j, id=rid, info=info, size_sectors=size, offset=pos, nbytes=nbytes)
            off += 4
            pos += nbytes                               # every path adds size<<11 (0xd409/0xd418/0xd4a4)
            if rid == 2 and info != 0:                  # 0xd49f: the ONLY conditional extra field
                r.extra_sectors = _s16(blob, off); off += 2
                pos += r.extra_sectors << 11
            ch.resources.append(r)
        chunks.append(ch)
    c = Container(size=len(blob), chunks=chunks, table_end=off, cursor_end=pos)
    if strict and pos != len(blob):
        raise ContainerError(
            f"resource table sums to {pos:#x} but the file is {len(blob):#x} -- parser drift")
    return c


def parse_directory(blob: bytes, base_off: int, count: Optional[int] = None) -> List[int]:
    """The id-2 sub-resource directory: a table of SIGNED 32-bit offsets RELATIVE TO THE TABLE.

    Port of fn 0x3d800's tail @0x3da87, which computes ``entry = base + (Int32)base[idx]``. The table
    is self-describing: entry[0] points just past the table itself, so ``count == entry[0] // 4``
    unless the caller states one.

    (``SFXBinaryFile.cs`` reads these same bytes as ``u16 offset + u16 flags`` pairs; a "flags ==
    0xFFFF external file" in that model is simply a NEGATIVE relative offset here. A negative entry
    is returned verbatim -- it points backwards out of the region into earlier-loaded data, and it is
    the CALLER's job to refuse it rather than this parser's to hide it.)
    """
    first = _s32(blob, base_off)
    n = count if count is not None else (first // 4 if first > 0 else 0)
    return [_s32(blob, base_off + 4 * i) for i in range(n)]


# --------------------------------------------------------------------------- the sequence op stream
#: the SEQUENCE STREAM's file offset -- inside sector 0, fn 0x31d31 @0x31edb sets
#: ``seqPtr(0x323198) = 0x320cd0 = headerSector + 0x400``.
SEQ_OFFSET = 0x400


@dataclass
class Op:
    """One 3-byte ``(code, arg1, arg2)`` record of the sequence stream, at file offset ``at``.

    Deliberately CODE ONLY -- no opcode name, no handler rva, no valid/illegal status. The native
    dispatch tables that would supply those live in the study's disassembly notes and are not needed
    by any kit consumer (the camera extractor reads ``code``/``arg1``/``arg2``/``at`` and nothing
    else), so shipping a half-populated status column here would be an authority claim this module
    does not carry.
    """
    at: int
    code: int
    arg1: int
    arg2: int


def parse_op_stream(blob: bytes, off: int = SEQ_OFFSET, limit: int = 200_000) -> List[Op]:
    """Walk the container's sequence stream: 3-byte ``(code, arg1, arg2)`` records from ``off``.

    Port of fn 0x315f1's fetch/dispatch head (@0x31647..0x3167e). The interpreter stops advancing on
    code 0x00 (END_HOLD rewinds the pointer and re-executes), so that record is included and the walk
    returns.

    NAMED ``parse_op_stream``, not ``parse_sequence``: ``ff9mapkit.battle.camera_codec`` already has a
    ``parse_sequence(b, off, end)`` that walks a camera CODE stream -- an entirely different format at
    an entirely different layer. Both are in scope inside :mod:`ff9mapkit.summons.camera`, so the two
    names had to differ or every future call site would have to be read twice to know which one it is.
    """
    ops: List[Op] = []
    for _ in range(limit):
        code, a1, a2 = blob[off], blob[off + 1], blob[off + 2]
        ops.append(Op(off, code, a1, a2))
        off += 3
        if code == 0x00:
            return ops
    raise ContainerError("sequence stream never reached END within the limit")


# --------------------------------------------------------------------------- geometry: bucket layout
#            name    code  stride  cnt_off  nvert  nuv  ncol  inline_rgb
PRIM_TYPES: Tuple[tuple, ...] = (
    ("FT4", 0x2C, 0x18, 0x02, 4, 4, 0, True),
    ("FT3", 0x24, 0x14, 0x04, 3, 3, 0, True),
    ("GT4", 0x3C, 0x20, 0x06, 4, 4, 4, False),
    ("GT3", 0x34, 0x18, 0x08, 3, 3, 3, False),
    ("G4",  0x38, 0x18, 0x0A, 4, 0, 4, False),
    ("G3",  0x30, 0x14, 0x0C, 3, 0, 3, False),
    ("F4",  0x28, 0x10, 0x0E, 4, 0, 0, True),
    ("F3",  0x20, 0x0C, 0x10, 3, 0, 0, True),
)
# per-type field offsets inside a face record (FORMAT.md §2.3, each cited to its native builder)
PRIM_FIELDS = {
    "FT4": dict(v=(0x00, 0x02, 0x04, 0x06), uv=(0x08, 0x0A, 0x0C, 0x0E), rgb=0x10, part=0x13, flg=0x15),
    "FT3": dict(v=(0x00, 0x02, 0x04), uv=(0x0C, 0x0E, 0x10), rgb=0x08, part=0x06, flg=0x12),
    "GT4": dict(v=(0x00, 0x02, 0x04, 0x06), uv=(0x08, 0x0A, 0x0C, 0x0E),
                col=(0x10, 0x12, 0x14, 0x16), part=0x1D, flg=0x1C),
    "GT3": dict(v=(0x00, 0x02, 0x04), uv=(0x06, 0x08, 0x0A),
                col=(0x10, 0x12, 0x14), part=0x16, flg=0x0F),
    "G4":  dict(v=(0x00, 0x02, 0x04, 0x06), col=(0x08, 0x0A, 0x0C, 0x0E), flg=0x14),
    "G3":  dict(v=(0x00, 0x02, 0x04), col=(0x08, 0x0A, 0x0C), flg=0x13),
    "F4":  dict(v=(0x00, 0x02, 0x04, 0x06), rgb=0x08, flg=0x0D),
    "F3":  dict(v=(0x00, 0x02, 0x04), rgb=0x08, flg=0x0B),
}
MAX_VERTS_PER_MESH = 0x1B58   # `cmp idx,0x1b58` @0x50b3 and in every emit loop


@dataclass
class BoneLink:
    """4 bytes: ``{u16 length; u8 zero; u8 parent}`` (fn 0x7de7 @0x81aa). ``length`` is a single scalar
    translation along the child's local Z; ``parent`` indexes the bone-world-matrix array. The BoneLink
    rows are nodes ``1..boneCount-1``; node 0 is the implicit root (it carries the clip's root translation,
    not a length). A parent index is always LOWER than its child (the hierarchy pass walks in order)."""
    length: int
    zero: int
    parent: int

    @property
    def signed_length(self) -> int:
        return struct.unpack("<h", struct.pack("<H", self.length))[0]


@dataclass
class Mesh:
    """One MeshDesc (stride 0x28). ``counts`` are the eight bucket face counts in emission order
    (``PRIM_TYPES``). ``verts_per_bone`` is the run-length skin: vertex n belongs to the bone whose run
    contains it."""
    index: int
    unknown0: int                 # MeshDesc+0x00 -- OPAQUE (NOT nVert; falsified corpus-wide)
    counts: List[int]
    zero: int                     # +0x12
    ot_bias: int                  # +0x13 (signed): OT base = otBase + (8 - otBias)*4
    p_verts_per_bone: int         # +0x14  (geom-relative on disk)
    p_positions: int              # +0x18
    p_primitives: int             # +0x1c
    p_uv: int                     # +0x20
    p_colors: int                 # +0x24
    verts_per_bone: List[int]
    col_count: Optional[int] = None   # derived by chain closure, not stored in the file

    @property
    def n_vert(self) -> int:
        """Sum of the per-bone runs (skinning is RIGID + RUN-LENGTH; fn 0x4eb0 @0x509d)."""
        return sum(self.verts_per_bone)

    @property
    def uv_count(self) -> int:
        """Only the four TEXTURED buckets carry UV indices (4/3/4/3 per face)."""
        return sum(self.counts[i] * PRIM_TYPES[i][5] for i in range(8))

    @property
    def prim_bytes(self) -> int:
        return sum(self.counts[i] * PRIM_TYPES[i][2] for i in range(8))

    @property
    def face_count(self) -> int:
        return sum(self.counts)


@dataclass
class Geom:
    """A decoded GEOM block (the creature's model image, offset 0 of the id-5 payload)."""
    base: int                     # absolute file offset of the block
    flags: int
    zero1: int
    bone_count: int
    mesh_count: int
    unknown_a: int                # +0x04 OPAQUE
    unknown_b: int                # +0x08 OPAQUE
    p_bone_table: int             # +0x0c (== 0x14 on disk; bone rows at +0x18)
    p_mesh_table: int             # +0x10 (== 0x18 + (boneCount-1)*4)
    list_head: int                # +0x14 (NOT an invariant)
    bones: List[BoneLink]
    meshes: List[Mesh]

    def parents(self) -> List[int]:
        """Parent index per node, 0..boneCount-1 (parents[0] is the implicit root, reported as 0)."""
        out = [0] * self.bone_count
        for r, bl in enumerate(self.bones):
            out[r + 1] = bl.parent
        return out

    def lengths(self) -> List[int]:
        """Signed local-Z length per node (lengths[0] == 0; the root has a translation track, not a
        length)."""
        out = [0] * self.bone_count
        for r, bl in enumerate(self.bones):
            out[r + 1] = bl.signed_length
        return out

    @property
    def end(self) -> int:
        """Absolute file offset just past the block = the LAST mesh's colour pool end (chain closure).

        The colour pool is the one sub-block whose size the file never states, so this is the only
        honest answer to "how long is this GEOM block": ``base + p_colors + 4*col_count`` of the last
        mesh in TABLE order. ``col_count`` is resolved by :func:`parse_geom`'s chain closure; a block
        parsed with no ``block_end`` may leave the final LAYOUT-order mesh's count unresolved, and
        this property then reports the header-relative pool START (``col_count or 0``) rather than
        inventing a length.

        Why it is a property and not a caller-side computation: every consumer that treats a scanned
        GEOM as a REGION (a byte-identical attribution gate, an overlap check) needs ``[base, end)``.
        Without it those callers fall back to ``base + 0x10`` -- the 16-byte header stub -- and a gate
        spanning the region goes green while gating essentially nothing.
        """
        m = self.meshes[-1]
        return self.base + m.p_colors + 4 * (m.col_count or 0)


def parse_geom(blob: bytes, base: int, block_end: Optional[int] = None) -> Geom:
    """Decode a GEOM block at absolute file offset ``base`` (pre-relocation, as on disk). ``block_end``
    bounds the last mesh's colour pool (the one length the file never states); when omitted the final
    mesh's ``col_count`` is left unresolved."""
    flags = blob[base]
    zero1 = blob[base + 1]
    bone_count = blob[base + 2]
    mesh_count = blob[base + 3]
    if bone_count == 0 or mesh_count == 0:
        raise ContainerError("geom: boneCount/meshCount == 0")
    unk_a = _u32(blob, base + 4)
    unk_b = _u32(blob, base + 8)
    p_bone = _u32(blob, base + 0x0C)
    p_mesh = _u32(blob, base + 0x10)
    list_head = _u32(blob, base + 0x14)
    bones = [BoneLink(_u16(blob, base + 0x18 + 4 * i), blob[base + 0x18 + 4 * i + 2],
                      blob[base + 0x18 + 4 * i + 3]) for i in range(bone_count - 1)]
    meshes: List[Mesh] = []
    for i in range(mesh_count):
        d = base + p_mesh + 0x28 * i          # `lea rcx,[rax+rax*4]; lea r8,[rdx+rcx*8]` @0x58fe
        counts = [_u16(blob, d + PRIM_TYPES[k][3]) for k in range(8)]
        vpb_off = _u32(blob, d + 0x14)
        vpb = [_u16(blob, base + vpb_off + 2 * b) for b in range(bone_count)]
        meshes.append(Mesh(
            index=i, unknown0=_u16(blob, d), counts=counts, zero=blob[d + 0x12],
            ot_bias=struct.unpack_from("<b", blob, d + 0x13)[0],
            p_verts_per_bone=vpb_off, p_positions=_u32(blob, d + 0x18),
            p_primitives=_u32(blob, d + 0x1C), p_uv=_u32(blob, d + 0x20),
            p_colors=_u32(blob, d + 0x24), verts_per_bone=vpb))
    # Chain closure fixes each colour pool's length -- the ONE sub-block whose size the file never states.
    # The pool runs to the next sub-block start anywhere in the model (table order need not be layout
    # order), or to ``block_end`` for the last one.
    layout = sorted(meshes, key=lambda m: m.p_verts_per_bone)
    for i, m in enumerate(layout):
        nxt = (layout[i + 1].p_verts_per_bone if i + 1 < len(layout)
               else (block_end - base if block_end is not None else None))
        if nxt is not None and nxt >= m.p_colors:
            m.col_count = (nxt - m.p_colors) // 4
    return Geom(base, flags, zero1, bone_count, mesh_count, unk_a, unk_b,
                p_bone, p_mesh, list_head, bones, meshes)


def geom_checks(blob: bytes, g: Geom, limit: Optional[int] = None) -> dict:
    """Every structural identity FORMAT.md asserts, evaluated on one block -- each a pass/fail boolean so a
    corpus sweep tells invariant from coincidence. ``limit`` = the enclosing payload's end offset."""
    r = {
        "flags_bit0_clear": (g.flags & 1) == 0,
        "byte1_zero": g.zero1 == 0,
        "pBoneTable_is_0x14": g.p_bone_table == 0x14,
        "pMeshTable_law": g.p_mesh_table == 0x18 + (g.bone_count - 1) * 4,
    }
    ok_uv = ok_vpb = ok_pos = ok_prim = ok_mz = True
    for m in g.meshes:
        ok_mz &= (m.zero == 0)
        # The five sub-blocks are contiguous, in order, each starting at the 4-BYTE-ALIGNED end of the
        # previous (D3 correction to the earlier "exact adjacency" claim).
        ok_vpb &= (_a4(m.p_verts_per_bone + 2 * g.bone_count) == m.p_positions)
        ok_pos &= (_a4(m.p_positions + 8 * m.n_vert) == m.p_primitives)
        ok_prim &= (_a4(m.p_primitives + m.prim_bytes) == m.p_uv)
        ok_uv &= (_a4(m.p_uv + 2 * m.uv_count) == m.p_colors)
    r["mesh_byte0x12_zero"] = ok_mz
    r["chain_vertsPerBone_to_positions"] = ok_vpb
    r["chain_positions_to_primitives"] = ok_pos      # proves the 8-byte vertex + Sum(vertsPerBone)
    r["chain_primitives_to_uv"] = ok_prim            # proves all 8 counts AND all 8 strides
    r["chain_uv_to_colors"] = ok_uv                  # proves u16 UV entries + the 4/3/4/3 UV-per-face
    if limit is not None:
        r["in_bounds"] = g.base + g.meshes[-1].p_colors <= limit
    return r


# GEOM blocks also exist OUTSIDE the summon lane (the whole Hi_Register*EffModel family shares fn
# 0x7120). In the stock corpus 1005 blocks live in resources id 2 (658), 6 (282), 5 (24 -- the
# creatures), 8 (20), 3 (12) and 10 (9); only the id-5 ones sit at their resource's offset 0, which is
# what ``creature_geom`` reaches directly. Every other block needs this scan to be FOUND at all.
_GEOM_NEEDLE = b"\x14\x00\x00\x00"          # geom+0x0c == 0x14, on disk, 1005/1005


def scan_geom(blob: bytes, start: int = 0, end: Optional[int] = None):
    """Yield every GEOM block in ``blob[start:end]``, located by header law + chain identity.

    Acceptance is the cheap header law (``pBoneTable == 0x14`` and ``pMeshTable == 0x18 +
    (boneCount-1)*4``) plus the four chain identities :func:`geom_checks` evaluates. In the stock
    corpus that pair is already 100% selective: zero candidates passed the header law and then failed
    a chain check.

    Two checks are excluded from the verdict on purpose. ``listHead_zero`` is NOT an invariant (7 of
    1005 stock blocks carry a non-zero listHead), and ``in_bounds`` needs an extent only the caller
    knows -- neither is evaluated here, and the name-keyed filter below stays correct whether or not
    this module's :func:`geom_checks` happens to emit them.
    """
    end = len(blob) if end is None else end
    pos = start
    while True:
        k = blob.find(_GEOM_NEEDLE, pos, end)
        if k < 0:
            return
        pos = k + 4
        base = k - 0x0C
        if base < start or blob[base] & 1 or blob[base + 1] != 0:
            continue
        bc, mc = blob[base + 2], blob[base + 3]
        if bc == 0 or mc == 0 or _u32(blob, base + 0x10) != 0x18 + (bc - 1) * 4:
            continue
        try:
            g = parse_geom(blob, base)
        except (ContainerError, struct.error, IndexError):
            continue
        chk = geom_checks(blob, g)
        if all(v for kk, v in chk.items() if kk not in ("listHead_zero", "in_bounds")):
            yield g


def iter_primitives(blob: bytes, g: Geom, mesh: Mesh):
    """Yield every face of one mesh as a dict. ``uv``/``col``/``rgb``/``part`` are present only for the
    types that carry them. Indices are into the mesh's own pools."""
    off = g.base + mesh.p_primitives
    for k, (name, code, stride, _c, nv, nuv, ncol, has_rgb) in enumerate(PRIM_TYPES):
        f = PRIM_FIELDS[name]
        for _ in range(mesh.counts[k]):
            rec = {"type": name, "code": code,
                   "v": [_u16(blob, off + o) for o in f["v"]],
                   "flag": blob[off + f["flg"]]}
            if nuv:
                rec["uv"] = [_u16(blob, off + o) for o in f["uv"]]
            if ncol:
                rec["col"] = [_u16(blob, off + o) for o in f["col"]]
            if has_rgb:
                rec["rgb"] = tuple(blob[off + f["rgb"] + i] for i in range(3))
            if "part" in f:
                rec["part"] = blob[off + f["part"]]
            # flag byte: bit0 = semi-transparent, bit1 = SKIP the backface test, bits5..7 = ABR mode
            rec["no_cull"] = bool(rec["flag"] & 2)
            rec["abr"] = (rec["flag"] >> 5) & 3
            yield rec
            off += stride


def vertices(blob: bytes, g: Geom, mesh: Mesh):
    """Yield (x, y, z, w) s16 quads. Skinning is implied by position: vertex n belongs to the bone whose
    run contains it (``verts_per_bone``); ``w`` is loaded into the GTE but never read."""
    o = g.base + mesh.p_positions
    for i in range(mesh.n_vert):
        yield struct.unpack_from("<4h", blob, o + 8 * i)


def bone_of_vertex(mesh: Mesh) -> List[int]:
    """Vertex index -> owning bone (the run-length rigid skin, expanded)."""
    out: List[int] = []
    for b, n in enumerate(mesh.verts_per_bone):
        out.extend([b] * n)
    return out


# --------------------------------------------------------------------------- id4+id5 model package
@dataclass
class ModelPackage:
    """THE CREATURE MODEL HEADER, at the START of the id-4 payload (read by the id-4 texture handler, the
    id-5 model/motion handler, then handed to ``Hi_RegisterSummonModel``). The header and the payloads
    stream into one arena: the header occupies ``arena[0 .. texOffset)``; ``header+texOffset`` is the
    texture blob at id-4 time and the GEOMETRY block afterwards. Consequence for an offline reader: every
    header field that addresses the model image is HEADER-relative, so
    ``file offset = id5.offset + headerRelative - texOffset``.

      +0x00  s16  texOffset   == 0x180 + 4*motionCount -- header size == model-image base
      +0x02  s16  motionCount N
      +0x04  s16  partCount   -- materials AND 64x128 texture pages (<= 6)
      +0x06  u16  clutRows
      +0x08  u32  texBytes    == partCount * 0x4000
      +0x0c  u32  clutBytes   == clutRows  * 0x200
      +0x10  u32  modelBytes  -- END of the model image, header-relative
      +0x14  u32  firstBlock  -- END of the GEOMETRY block == start of the texanim table
      +0x18  u16[partCount]  TPAGE
      +0x24  u16[partCount]  CLUT
      +0x30  u16[partCount]  texture V-offset
      +0x180 u32[N] MOTION TABLE, header-relative
    """
    tex_offset: int
    motion_count: int
    part_count: int
    clut_rows: int
    tex_bytes: int
    clut_bytes: int
    model_bytes: int
    first_block: int
    motion_offsets: List[int]        # header-relative, as stored
    tpage: List[int]
    clut: List[int]
    v_offset: List[int]
    header_offset: int               # = the id-4 payload offset
    tex_file_offset: int             # absolute file offset of the texture pages (id-4 time)
    model_file_offset: int           # absolute file offset of the model image = the id-5 payload
    model_bytes_total: int           # the model image's own size (modelBytes - texOffset)

    def to_file(self, header_rel: int) -> int:
        """Header-relative model-image address -> absolute file offset."""
        return self.model_file_offset + header_rel - self.tex_offset

    @property
    def geom_offset(self) -> int:
        return self.model_file_offset                      # geometry starts the model image

    @property
    def geom_end(self) -> int:
        return self.to_file(self.first_block)

    @property
    def model_image_end(self) -> int:
        return self.to_file(self.model_bytes)

    @property
    def motion_file_offsets(self) -> List[int]:
        """Absolute file offset of each of the N motion-clip payloads (decoded by summons.motion)."""
        return [self.to_file(m) for m in self.motion_offsets]


def parse_model_package(blob: bytes, chunk: Chunk) -> Optional[ModelPackage]:
    """Return the creature model package for a chunk carrying both an id-4 and an id-5 resource, else
    ``None``."""
    r4 = next((r for r in chunk.resources if r.id == 4), None)
    r5 = next((r for r in chunk.resources if r.id == 5), None)
    if r4 is None or r5 is None:
        return None
    a = r4.offset
    n = _s16(blob, a + 2)
    npart = _s16(blob, a + 4)
    tex_off = _s16(blob, a)
    return ModelPackage(
        tex_offset=tex_off, motion_count=n, part_count=npart, clut_rows=_u16(blob, a + 6),
        tex_bytes=_u32(blob, a + 8), clut_bytes=_u32(blob, a + 0xC),
        model_bytes=_u32(blob, a + 0x10), first_block=_u32(blob, a + 0x14),
        motion_offsets=[_u32(blob, a + 0x180 + 4 * i) for i in range(n)],
        tpage=[_u16(blob, a + 0x18 + 2 * i) for i in range(npart)],
        clut=[_u16(blob, a + 0x24 + 2 * i) for i in range(npart)],
        v_offset=[_u16(blob, a + 0x30 + 2 * i) for i in range(npart)],
        header_offset=a, tex_file_offset=a + tex_off, model_file_offset=r5.offset,
        model_bytes_total=_u32(blob, a + 0x10) - tex_off,
    )


def creature_package(blob: bytes) -> Optional[ModelPackage]:
    """Walk the chunks and return the first id-4 + id-5 model package (the creature), or ``None`` if this
    effect carries no creature."""
    for ch in parse_header(blob, strict=False).chunks:
        mp = parse_model_package(blob, ch)
        if mp is not None:
            return mp
    return None


def creature_geom(blob: bytes, mp: ModelPackage) -> Geom:
    """The creature's GEOM block: at offset 0 of the id-5 payload, ending at the header's ``firstBlock``
    (so the last mesh's colour pool -- the one length the block never stores -- is determined)."""
    return parse_geom(blob, mp.geom_offset, block_end=mp.geom_end)


def vram_rect(tpage: int, v_offset: int) -> Tuple[int, int, int, int]:
    """The 64x128 16bpp texture-page rect the id-4 handler uploads (@0x3e302-0x3e34b)."""
    return ((tpage & 0x0F) * 64, ((tpage & 0x10) << 4) + v_offset, 64, 128)


# --------------------------------------------------------------------------- read-only summary (CLI)
def summary(blob: bytes) -> str:
    """A one-blob, read-only listing: the container map, the creature package and its GEOM stats. Prints
    counts/offsets only (no payload bytes)."""
    c = parse_header(blob, strict=False)
    out = [f"size={c.size:#x} chunks={len(c.chunks)} tableEnd={c.table_end:#x} "
           f"cursorEnd={c.cursor_end:#x} lenMatch={c.cursor_end == c.size}"]
    for ch in c.chunks:
        out.append(f"  chunk[{ch.slot}] index={ch.chunk_index} resources={len(ch.resources)} "
                   f"ids={[r.id for r in ch.resources]}")
    mp = creature_package(blob)
    if mp is None:
        out.append("  (no creature package -- this effect carries no id-4+id-5 model)")
        return "\n".join(out)
    out.append(f"  MODEL @{mp.header_offset:#x}: parts={mp.part_count} motions={mp.motion_count} "
               f"clutRows={mp.clut_rows}")
    out.append(f"    motion clips @ {[hex(x) for x in mp.motion_file_offsets]}")
    g = creature_geom(blob, mp)
    out.append(f"  GEOM: bones={g.bone_count} meshes={g.mesh_count} "
               f"verts={sum(m.n_vert for m in g.meshes)} faces={sum(m.face_count for m in g.meshes)}")
    for m in g.meshes:
        used = {PRIM_TYPES[i][0]: m.counts[i] for i in range(8) if m.counts[i]}
        out.append(f"    mesh{m.index}: verts={m.n_vert} uv={m.uv_count} col={m.col_count} {used}")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        with open(p, "rb") as fh:
            blob = fh.read()
        print("=" * 72)
        print(p)
        print(summary(blob))
