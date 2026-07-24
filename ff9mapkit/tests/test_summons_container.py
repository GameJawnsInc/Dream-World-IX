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
