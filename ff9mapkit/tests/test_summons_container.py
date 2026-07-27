"""``summons.container`` -- the ef###.bytes container / creature-package / geometry parser.

Two lanes (the suite's game-gated pattern, cf. test_battle_locate.py):
  * OFFLINE -- the bucket/field tables' internal consistency, the small pure helpers, and a synthetic
    header walk. No install, no stock bytes -- always runs.
  * GAME-GATED -- the decode of the user's own locally-extracted stock creatures (Bahamut ef227 @ 93
    nodes / 2 meshes; Odin ef261 @ 97 nodes as a generalisation check). Skips cleanly when the local
    ``C:/gd/SCRATCH/summon-format/`` blobs are absent.
"""
from __future__ import annotations

import os
import struct

import pytest

from ff9mapkit.summons import container as C

_SCRATCH = r"C:/gd/SCRATCH/summon-format"


def _ef(effid: int) -> str:
    return os.path.join(_SCRATCH, f"ef{effid:03d}.bytes")


def _have(effid: int) -> bool:
    return os.path.exists(_ef(effid))


def _blob(effid: int) -> bytes:
    with open(_ef(effid), "rb") as fh:
        return fh.read()


# ------------------------------------------------------------------ OFFLINE (always run)
def test_prim_tables_are_internally_consistent():
    # PRIM_FIELDS must be keyed by the eight PRIM_TYPES names, and each type's v/uv/col field tuples must
    # have exactly the per-face vertex/uv/colour counts the type advertises.
    names = [t[0] for t in C.PRIM_TYPES]
    assert set(C.PRIM_FIELDS) == set(names)
    for name, code, stride, cnt_off, nv, nuv, ncol, has_rgb in C.PRIM_TYPES:
        f = C.PRIM_FIELDS[name]
        assert len(f["v"]) == nv
        assert ("uv" in f) == bool(nuv) and (len(f.get("uv", ())) == nuv)
        assert ("col" in f) == bool(ncol) and (len(f.get("col", ())) == ncol)
        assert ("rgb" in f) == bool(has_rgb)
        assert "flg" in f
        # every referenced field byte sits inside the record stride
        for off in list(f["v"]) + list(f.get("uv", ())) + list(f.get("col", ())) + [f["flg"]]:
            assert off < stride


def test_vram_rect():
    assert C.vram_rect(0, 0) == (0, 0, 64, 128)
    # tpage low nibble -> x*64 ; bit4 -> +256 in y ; v_offset adds to y
    assert C.vram_rect(0x03, 0) == (192, 0, 64, 128)
    assert C.vram_rect(0x11, 5) == (64, 261, 64, 128)


def test_bonelink_signed_length():
    assert C.BoneLink(0xFFC0, 0, 7).signed_length == -64
    assert C.BoneLink(145, 0, 1).signed_length == 145


def test_parse_header_synthetic_walk_and_strict():
    # chunkCount=1; one chunk (index 0, 1 resource); one id-4 resource of 1 sector.
    header = struct.pack("<H", 1) + struct.pack("<HH", 0, 1) + struct.pack("<bbH", 4, 0, 1)
    blob = header + b"\x00" * (0x1000 - len(header))          # payload runs 0x800..0x1000
    c = C.parse_header(blob)                                   # strict: cursor 0x1000 == len 0x1000
    assert len(c.chunks) == 1 and len(c.chunks[0].resources) == 1
    r = c.chunks[0].resources[0]
    assert r.id == 4 and r.offset == 0x800 and r.nbytes == 0x800 and r.kind == "VRAM_TEXPAGE"
    assert c.chunks[0].psx_base == 0x801E7700
    # a short blob fails the cursor==length self-check in strict mode, passes when strict is off
    with pytest.raises(C.ContainerError):
        C.parse_header(blob[:-1], strict=True)
    assert C.parse_header(blob[:-1], strict=False).cursor_end == 0x1000


def test_no_creature_package_returns_none():
    header = struct.pack("<H", 1) + struct.pack("<HH", 0, 1) + struct.pack("<bbH", 3, 0, 1)
    blob = header + b"\x00" * (0x1000 - len(header))
    assert C.creature_package(blob) is None                    # id-3 only, no id-4+id-5 pair


# ================================================================== THE EDIT-LANE READ PATH
# ``parse_directory`` / ``parse_op_stream`` / ``scan_geom`` / ``Geom.end`` are what the reskin and
# rescore lanes need on top of the transplant read path. All four are exercised here on containers
# and blocks this file COMPUTES -- every offset below is derived from the format's own laws, and no
# byte run is copied from any stock file.

# ------------------------------------------------------------------ the id-2 directory
def test_parse_directory_is_self_describing():
    """entry[0] points just past the table, so the table states its own length."""
    entries = [16, 32, 32, 64]
    blob = b"\x00" * 0x100 + b"".join(struct.pack("<i", e) for e in entries) + b"\x00" * 0x40
    assert C.parse_directory(blob, 0x100) == entries           # 16 // 4 == 4 entries


def test_parse_directory_honours_an_explicit_count():
    entries = [16, 32, 32, 64]
    blob = b"".join(struct.pack("<i", e) for e in entries) + b"\x00" * 0x40
    assert C.parse_directory(blob, 0, 2) == [16, 32]
    assert C.parse_directory(blob, 0, 6) == entries + [0, 0]   # reads what the caller asked for


def test_parse_directory_returns_a_negative_entry_verbatim():
    """A negative relative offset is an EXTERNAL sub-file -- it points backwards out of the region.
    Hiding or clamping it here would turn a refusable condition into silently wrong bytes; refusing
    it is the CALLER's job (``camera.Id2Archive.bounds`` does exactly that)."""
    entries = [12, -40244, 64]
    blob = b"".join(struct.pack("<i", e) for e in entries) + b"\x00" * 0x40
    assert C.parse_directory(blob, 0) == entries


def test_a_non_positive_first_entry_yields_no_entries():
    blob = struct.pack("<i", -4) + b"\x00" * 0x20
    assert C.parse_directory(blob, 0) == []


# ------------------------------------------------------------------ the sequence op stream
def _seq(ops, off=C.SEQ_OFFSET, size=0x800):
    b = bytearray(size)
    b[off:off + 3 * len(ops)] = b"".join(bytes(o) for o in ops)
    return bytes(b)


def test_parse_op_stream_walks_three_byte_records_and_stops_at_end():
    blob = _seq([(0x01, 0, 10), (0x29, 2, 0), (0x00, 0, 0), (0x23, 9, 9)])
    ops = C.parse_op_stream(blob)
    assert [(o.code, o.arg1, o.arg2) for o in ops] == [(0x01, 0, 10), (0x29, 2, 0), (0x00, 0, 0)]
    assert [o.at for o in ops] == [C.SEQ_OFFSET, C.SEQ_OFFSET + 3, C.SEQ_OFFSET + 6]
    assert C.SEQ_OFFSET == 0x400


def test_parse_op_stream_honours_an_explicit_offset():
    blob = _seq([(0x05, 1, 0), (0x00, 0, 0)], off=0x40)
    assert [(o.code, o.arg1) for o in C.parse_op_stream(blob, 0x40)] == [(0x05, 1), (0x00, 0)]


def test_a_stream_that_never_ends_is_refused_not_truncated():
    """Walking off the end of a stream that carries no END is a REFUSAL: a silently truncated op list
    would report a container as having fewer camera ops than it really runs."""
    blob = b"\x01" * 0x1000
    with pytest.raises(C.ContainerError, match="never reached END"):
        C.parse_op_stream(blob, 0, limit=64)


def test_an_op_carries_the_code_and_nothing_it_cannot_vouch_for():
    """Deliberately CODE ONLY. The native dispatch tables that would supply an opcode NAME, handler
    or valid/illegal status live in the study's disassembly notes; a half-populated status column
    here would be an authority claim this module does not carry."""
    (op, _end) = C.parse_op_stream(_seq([(0x29, 1, 0), (0x00, 0, 0)]))
    assert (op.code, op.arg1, op.arg2, op.at) == (0x29, 1, 0, 0x400)
    for absent in ("status", "name", "handler", "valid"):
        assert not hasattr(op, absent), absent


# ------------------------------------------------------------------ scan_geom + Geom.end
def _synth_geom() -> bytes:
    """A COMPUTED two-mesh GEOM block: every offset below satisfies the header law and all four
    chain identities, so ``scan_geom`` must accept it. Nothing here is a copied byte run -- the
    layout is derived from the format's own rules (see ``parse_geom``)."""
    bc, mc = 2, 2
    p_mesh = 0x18 + (bc - 1) * 4                               # the pMeshTable law
    b = bytearray(0xFC)
    b[0], b[1], b[2], b[3] = 0x00, 0x00, bc, mc                # flags bit0 clear, byte1 zero
    struct.pack_into("<I", b, 0x04, 0xDEADBEEF)                # +0x04 / +0x08 are OPAQUE
    struct.pack_into("<I", b, 0x08, 0xFEEDFACE)
    struct.pack_into("<I", b, 0x0C, 0x14)                      # pBoneTable -- and the scan needle
    struct.pack_into("<I", b, 0x10, p_mesh)
    struct.pack_into("<I", b, 0x14, 0)                         # listHead (NOT an invariant)
    struct.pack_into("<HBB", b, 0x18, 100, 0, 0)               # node 1: length 100, parent 0

    def mesh(i, counts, vpb, p_vpb, p_pos, p_prim, p_uv, p_col):
        d = p_mesh + 0x28 * i
        struct.pack_into("<H", b, d, 0x1234)                   # +0x00 OPAQUE (NOT nVert)
        for name, _code, _stride, cnt_off, *_rest in C.PRIM_TYPES:
            struct.pack_into("<H", b, d + cnt_off, counts.get(name, 0))
        b[d + 0x12] = 0                                        # the mesh zero byte
        b[d + 0x13] = 0                                        # otBias
        struct.pack_into("<IIIII", b, d + 0x14, p_vpb, p_pos, p_prim, p_uv, p_col)
        for j, n in enumerate(vpb):
            struct.pack_into("<H", b, p_vpb + 2 * j, n)

    #      counts       verts/bone   vpb    pos    prim   uv     colors
    mesh(0, {"FT4": 1}, [2, 2], 0x6C, 0x70, 0x90, 0xA8, 0xB0)  # 4 verts, 1 quad, 4 uv, 2 colours
    mesh(1, {"FT3": 1}, [1, 2], 0xB8, 0xBC, 0xD4, 0xE8, 0xF0)  # 3 verts, 1 tri,  3 uv, 3 colours
    return bytes(b)


GEOM_AT = 0x40


def _geom_blob() -> bytes:
    blk = _synth_geom()
    return b"\x77" * GEOM_AT + blk + b"\x00" * 0x30            # filler either side


def test_the_synthetic_geom_satisfies_every_check_the_scanner_gates_on():
    blob, blk = _geom_blob(), _synth_geom()
    g = C.parse_geom(blob, GEOM_AT, GEOM_AT + len(blk))
    chk = C.geom_checks(blob, g, limit=len(blob))
    assert all(chk.values()), chk
    assert g.bone_count == 2 and g.mesh_count == 2
    assert [m.n_vert for m in g.meshes] == [4, 3]


def test_geom_end_is_the_colour_pool_end_not_a_header_stub():
    """THE REGION LAW. A consumer that treats a scanned GEOM as a region needs ``[base, end)``. The
    colour pool is the one sub-block whose size the file never states, so ``end`` is
    ``base + p_colors + 4*col_count`` of the last mesh -- resolved by chain closure.

    This test FAILS LOUDLY if ``Geom.end`` is ever dropped: without it every caller falls back to
    ``base + 0x10``, the 16-byte header stub, and a gate spanning "the block" then spans 6 % of it
    while still reporting green.
    """
    assert isinstance(getattr(C.Geom, "end", None), property), \
        "Geom.end vanished -- every region consumer silently collapses to a 16-byte header stub"
    blob, blk = _geom_blob(), _synth_geom()
    g = C.parse_geom(blob, GEOM_AT, GEOM_AT + len(blk))
    assert g.end == GEOM_AT + len(blk)                          # the WHOLE block, exactly
    assert g.end - g.base == 0xFC
    assert g.end > g.base + 0x10 + 0x80                         # ...and nothing like the stub


def test_geom_end_reports_the_pool_start_rather_than_inventing_a_length():
    """Parsed with no ``block_end`` the final layout-order mesh's colour count is UNRESOLVED. ``end``
    then reports the pool START -- an honest under-report, never a guessed length."""
    blob = _geom_blob()
    g = C.parse_geom(blob, GEOM_AT)                             # no block_end
    assert g.meshes[-1].col_count is None
    assert g.end == GEOM_AT + 0xF0                              # p_colors of the last mesh
    assert g.end < GEOM_AT + len(_synth_geom())


def test_scan_geom_finds_a_block_creature_geom_cannot_reach():
    """``creature_geom`` reaches only the id-5 block at its resource's offset 0. Every other GEOM in
    a container -- and this one sits at an arbitrary offset behind filler -- needs the scan to be
    FOUND at all."""
    blob = _geom_blob()
    found = list(C.scan_geom(blob))
    assert [g.base for g in found] == [GEOM_AT]
    assert found[0].end - found[0].base >= 0xF0                 # a real region, not a stub


def test_scan_geom_respects_the_span_it_was_given():
    blob = _geom_blob()
    assert list(C.scan_geom(blob, GEOM_AT + 1)) == []            # base would fall before ``start``
    assert [g.base for g in C.scan_geom(blob, 0, GEOM_AT + 0x10)] == [GEOM_AT]
    assert list(C.scan_geom(blob, 0, GEOM_AT + 0x0C)) == []      # the needle itself is outside


def test_scan_geom_rejects_a_header_law_violation():
    b = bytearray(_geom_blob())
    struct.pack_into("<I", b, GEOM_AT + 0x10, 0x99)             # pMeshTable != 0x18 + (bc-1)*4
    assert list(C.scan_geom(bytes(b))) == []


def test_scan_geom_rejects_a_broken_chain_even_when_the_header_law_holds():
    """The header law alone is cheap and would admit coincidences; the four chain identities are what
    make acceptance selective. Nudge ONE pointer and the block must stop being yielded."""
    b = bytearray(_geom_blob())
    d = GEOM_AT + 0x1C + 0x28                                   # mesh 1's descriptor
    struct.pack_into("<I", b, d + 0x20, 0xEC)                   # p_uv 0xE8 -> 0xEC, chain broken
    g = C.parse_geom(bytes(b), GEOM_AT)
    assert g.p_mesh_table == 0x1C                               # header law still holds...
    assert not C.geom_checks(bytes(b), g)["chain_primitives_to_uv"]      # ...but the chain does not
    assert list(C.scan_geom(bytes(b))) == []


def test_scan_geom_does_not_gate_on_listhead_which_is_not_an_invariant():
    """7 of the 1005 stock blocks carry a non-zero listHead, so gating on it would drop real blocks."""
    b = bytearray(_geom_blob())
    struct.pack_into("<I", b, GEOM_AT + 0x14, 0x0BADF00D)
    assert [g.base for g in C.scan_geom(bytes(b))] == [GEOM_AT]


# ------------------------------------------------------------------ GAME-GATED (local stock blobs)
@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_container_and_creature():
    blob = _blob(227)
    c = C.parse_header(blob)                                   # strict cursor==length holds
    assert c.cursor_end == c.size == len(blob)
    mp = C.creature_package(blob)
    assert mp is not None
    assert mp.motion_count == 8
    assert len(mp.motion_file_offsets) == 8
    # header size law: texOffset == 0x180 + 4*motionCount
    assert mp.tex_offset == 0x180 + 4 * mp.motion_count
    assert mp.part_count == 6


@pytest.mark.skipif(not _have(227), reason="needs local C:/gd/SCRATCH/summon-format/ef227.bytes")
def test_ef227_geometry_skeleton_and_skinning():
    blob = _blob(227)
    mp = C.creature_package(blob)
    g = C.creature_geom(blob, mp)
    assert g.bone_count == 93 and g.mesh_count == 2
    assert len(g.bones) == g.bone_count - 1                    # BoneLink rows are nodes 1..N-1

    # forward-referencing hierarchy: every parent index is LOWER than its child (the pass walks in order)
    parents = g.parents()
    assert all(parents[k] < k for k in range(1, g.bone_count))
    assert all(bl.zero == 0 for bl in g.bones)                 # BoneLink middle byte all zero

    # header structural laws + the four chain identities (the format's own self-validating linter)
    chk = C.geom_checks(blob, g, limit=mp.geom_end)
    assert chk["pBoneTable_is_0x14"]
    assert chk["pMeshTable_law"]
    for key in ("chain_vertsPerBone_to_positions", "chain_positions_to_primitives",
                "chain_primitives_to_uv", "chain_uv_to_colors", "in_bounds"):
        assert chk[key], key

    # run-length RIGID skinning: exactly one bone per vertex, and the pool closes (maxVtxIdx == nVert-1)
    total_verts = 0
    for m in g.meshes:
        bov = C.bone_of_vertex(m)
        assert len(bov) == m.n_vert                            # one owning bone per vertex
        max_vidx = max(max(p["v"]) for p in C.iter_primitives(blob, g, m))
        assert max_vidx == m.n_vert - 1                        # chain closure
        # every creature in the game uses only FT4 + FT3
        used = {C.PRIM_TYPES[i][0] for i in range(8) if m.counts[i]}
        assert used <= {"FT4", "FT3"}
        total_verts += m.n_vert
    assert total_verts == 1439                                 # 797 + 642


@pytest.mark.skipif(not _have(261), reason="needs local C:/gd/SCRATCH/summon-format/ef261.bytes")
def test_ef261_odin_generalises():
    blob = _blob(261)
    c = C.parse_header(blob)
    assert c.cursor_end == c.size
    mp = C.creature_package(blob)
    g = C.creature_geom(blob, mp)
    assert g.bone_count == 97                                  # Odin -- the generalisation check
    parents = g.parents()
    assert all(parents[k] < k for k in range(1, g.bone_count))
    chk = C.geom_checks(blob, g, limit=mp.geom_end)
    assert all(chk[k] for k in ("pMeshTable_law", "chain_positions_to_primitives",
                                "chain_primitives_to_uv", "chain_uv_to_colors"))
