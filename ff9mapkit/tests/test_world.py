#!/usr/bin/env python3
"""World-map block-mesh extractor (Path C foundation).

Offline: the IDALL bit-field decode, the lossless vertex round-trip, surgical in-place edit, and the OBJ
writer -- all against a hand-built synthetic block. Install-gated: read REAL disc-1 blocks out of p0data and
assert the decode is byte-lossless on every one (the property a later geometry edit relies on).
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.world import extract as W


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _synthetic_block(tan0_x=32512, tan3_x=232):
    """A 2-triangle flat block: pos (ch0 @0 dim3) + tangent (ch7 @12 dim4), stride 28, 6 verts. Triangle 0's
    first corner (vert 0) carries IDALL ``tan0_x``; triangle 1's (vert 3) carries ``tan3_x``."""
    stride = 28
    channels = {W.CH_POS: (0, 3), W.CH_TAN: (12, 4)}
    pos = [[float(i), float(i) * 0.5, -float(i)] for i in range(6)]
    tan = [[float(tan0_x), 0.0, 0.0, 1.0], [1.0, 0, 0, 1], [2.0, 0, 0, 1],
           [float(tan3_x), 0.0, 0.0, 1.0], [4.0, 0, 0, 1], [5.0, 0, 0, 1]]
    bm = W.BlockMesh(name="Block[0][0] Terrain", disc=1, x=0, y=0, lod="0_1", vcount=6, stride=stride,
                     channels=channels, chan_arrays={W.CH_POS: pos, W.CH_TAN: tan},
                     flat_index=[0, 1, 2, 3, 4, 5], tris=[[0, 1, 2], [3, 4, 5]],
                     raw_vbuf=bytes(6 * stride), raw_ibuf=b"", use32=False,
                     submeshes=[(0, 6)])
    bm.raw_vbuf = W.pack_vbuf(bm)             # the canonical packed bytes for this mesh
    return bm


# ---- IDALL decode (mirrors ff9.cs m_GetIDEvent/Area/Topograph) -------------------------------
def test_decode_id_bitfields():
    assert W.decode_id(232) == {"event": 0, "area": 0, "topograph": 58, "flags": 0}      # plain land
    assert W.decode_id(27724) == {"event": 1, "area": 44, "topograph": 19, "flags": 0}   # a place entrance
    assert W.decode_id(32512) == {"event": 1, "area": 63, "topograph": 0, "flags": 0}
    # event lives in bits 14-15, area 8-13, topograph 2-7, flags 0-1
    packed = (2 << 14) | (37 << 8) | (19 << 2) | 1
    assert W.decode_id(packed) == {"event": 2, "area": 37, "topograph": 19, "flags": 1}


# ---- lossless round-trip + surgical edit -----------------------------------------------------
def test_roundtrip_lossless():
    bm = _synthetic_block()
    assert W.roundtrip_ok(bm)                                  # pack-from-zeros reproduces raw exactly


def test_inplace_edit_is_surgical():
    bm = _synthetic_block()
    orig = bm.raw_vbuf
    bm.chan_arrays[W.CH_TAN][0][0] = 12345.0                   # retarget triangle 0's IDALL
    patched = W.pack_vbuf(bm, base=orig)
    diff = [i for i in range(len(orig)) if orig[i] != patched[i]]
    # every changed byte lies within vert 0's tangent.x 4-byte slot (offset 12-15); nothing else moves
    # (some of the 4 bytes may coincide between the two float encodings, so assert a subset, not equality)
    assert diff and set(diff) <= {12, 13, 14, 15}
    assert struct.unpack_from("<f", patched, 12)[0] == 12345.0


def test_block_mapids_and_summary():
    bm = _synthetic_block(tan0_x=27724, tan3_x=232)
    assert W.block_mapids(bm) == [27724, 232]                  # one IDALL per triangle, first-corner rule
    summ = W.block_summary(bm)
    assert summ["triangles"] == 2
    assert summ["place_areas"] == [44]                         # 27724 -> event1/area44 ; 232 -> plain land
    assert summ["place_entrances"] == [{"area": 44, "event": 1, "idall": 27724, "tris": 1}]
    assert 58 in summ["topographs"] and 19 in summ["topographs"]


def test_to_obj_writes_geometry(tmp_path):
    bm = _synthetic_block()
    p = W.to_obj(bm, tmp_path / "b.obj")
    text = p.read_text(encoding="utf-8")
    assert text.count("\nv ") == 6 and text.count("\nf ") == 2


# ---- install-gated: real disc-1 geometry ------------------------------------------------------
@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_block_0_0_roundtrips(tmp_path):
    bm = W.read_block(0, 0, disc=1)
    assert bm.vcount > 0 and bm.tangents is not None and len(bm.tris) > 0
    assert W.roundtrip_ok(bm), "real block decode must be byte-lossless (a geometry edit depends on it)"
    summ = W.block_summary(bm)
    assert 63 in summ["place_areas"]                           # block[0][0] has the area-63 entrance (vanilla data)


# ---- the .ff9mesh loose-override format (engine WorldMeshOverride reads this) ----------------
def test_ff9mesh_format_roundtrip(tmp_path):
    from ff9mapkit.world import mesh as M
    bm = _synthetic_block(tan0_x=27724, tan3_x=232)
    p = M.write_ff9mesh(bm, tmp_path / "b.ff9mesh")
    assert p.read_bytes()[:4] == b"F9WM"
    d = M.read_ff9mesh(p)
    assert d["version"] == 1 and d["vcount"] == bm.vcount
    assert d["verts"] == bm.verts                          # geometry preserved
    assert d["tangents"] == bm.tangents                    # tangent.x ids preserved (collision/entry fidelity)
    assert d["normals"] is None and d["uvs"] is None        # synthetic block carries only pos + tangent channels
    assert d["indices"] == bm.flat_index


def test_override_relpath_matches_engine_search():
    from ff9mapkit.world import mesh as M
    # mirrors WMWorldPrefabMaker's Resources path + FF9_Data base the engine's WorldMeshOverride searches
    assert M.override_relpath(1, 3, 7) == "FF9_Data/WorldMap/Disc1/0_1/r7/Block[3][7] Terrain.ff9mesh"


def test_raise_vertex_edits_one_vertex():
    from ff9mapkit.world import mesh as M
    bm = _synthetic_block()
    before = [list(v) for v in bm.verts]
    bi = M.raise_vertex_near_center(bm, 8.0)
    moved = [i for i in range(bm.vcount) if bm.verts[i] != before[i]]
    assert moved == [bi] and bm.verts[bi][1] == before[bi][1] + 8.0


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_real_block_ff9mesh_roundtrip(tmp_path):
    from ff9mapkit.world import mesh as M
    bm = W.read_block(0, 0, disc=1)
    d = M.read_ff9mesh(M.write_ff9mesh(bm, tmp_path / "r.ff9mesh"))
    assert d["verts"] == bm.verts and d["tangents"] == bm.tangents and d["indices"] == bm.flat_index


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_list_blocks_and_sample_roundtrip():
    blocks = W.list_blocks(disc=1)
    assert (0, 0) in blocks and len(blocks) > 100             # disc 1 has hundreds of terrain blocks
    sample = blocks[::max(1, len(blocks) // 12)]              # ~12 spread across the grid
    for (x, y) in sample:
        assert W.roundtrip_ok(W.read_block(x, y, disc=1)), f"block[{x}][{y}] not lossless"
