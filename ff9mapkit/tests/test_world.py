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


# ---- world-grid frame (block world placement; Memoria WMWorld.cs) ----------------------------
def test_block_world_origin_negates_z():
    assert W.block_world_origin(0, 0) == (0, 0)
    assert W.block_world_origin(13, 16) == (832, -1024)     # x*64 ; -y*64 (Z negated)
    assert W.block_world_origin(14, 17) == (896, -1088)


def test_footprint_nearest_dist():
    # block[13][16] world footprint: x[832,896] z[-1088,-1024]
    assert W.footprint_nearest_dist(13, 16, 864, -1056) == 0.0      # a point inside -> 0
    assert abs(W.footprint_nearest_dist(13, 16, 822, -1056) - 10.0) < 1e-9   # 10u left of the x edge
    assert abs(W.footprint_nearest_dist(13, 16, 832, -1014) - 10.0) < 1e-9   # 10u above the z edge


def test_blocks_touched_is_the_crack_free_set():
    blocks = {(12, 16), (13, 16), (14, 16), (15, 16), (20, 20)}
    # centre on the 13/14 seam (world x=896), radius 40 reaches only 13 & 14 (12/15 edges are 64u away)
    assert W.blocks_touched(896.0, -1056.0, 40.0, blocks) == [(13, 16), (14, 16)]
    assert (20, 20) not in W.blocks_touched(896.0, -1056.0, 40.0, blocks)


# ---- purposeful terrain reshaping (tear-free deforms) ----------------------------------------
def _flat_block(positions, normals=None):
    """A minimal BlockMesh from explicit vertex positions (+ optional normals) -- for the deform unit tests
    (no packed bytes needed; the deforms operate on chan_arrays)."""
    n = len(positions)
    channels = {W.CH_POS: (0, 3)}
    chan = {W.CH_POS: [list(p) for p in positions]}
    stride = 12
    if normals is not None:
        channels[W.CH_NRM] = (12, 3)
        chan[W.CH_NRM] = [list(v) for v in normals]
        stride = 24
    tris = [[i, i + 1, i + 2] for i in range(0, n - 2, 3)] or [[0, 0, 0]]
    return W.BlockMesh(name="Block[0][0] Terrain", disc=1, x=0, y=0, lod="0_1", vcount=n, stride=stride,
                       channels=channels, chan_arrays=chan, flat_index=list(range(n)), tris=tris,
                       raw_vbuf=b"", raw_ibuf=b"", use32=False, submeshes=[(0, n)])


def test_deform_radial_hill_and_watertight():
    from ff9mapkit.world import mesh as M
    # two COINCIDENT centre corners (0,0) + a mid-radius vert + one past the rim
    bm = _flat_block([[0, 0, 0], [0, 0, 0], [5, 0, 0], [20, 0, 0]])
    n = M.deform_radial(bm, amount=10.0, radius=10.0, center=(0.0, 0.0), falloff="smooth")
    ys = [v[1] for v in bm.verts]
    assert ys[0] == ys[1]                       # coincident corners move IDENTICALLY -> no tear
    assert abs(ys[0] - 10.0) < 1e-9             # peak == amount at the centre
    assert 0 < ys[2] < ys[0]                    # partial at mid-radius
    assert ys[3] == 0.0                         # past the rim: untouched
    assert n == 3                               # rim vert not counted


def test_deform_radial_crater_lowers():
    from ff9mapkit.world import mesh as M
    bm = _flat_block([[0, 0, 0]])
    M.deform_radial(bm, amount=-8.0, radius=10.0, center=(0.0, 0.0))
    assert abs(bm.verts[0][1] + 8.0) < 1e-9     # centre sinks by the depth (crater)


def test_deform_radial_seam_continuous_across_blocks():
    from ff9mapkit.world import mesh as M
    # the SAME world point on the 13|14 seam: block13 local x=64 (origin 832) and block14 local x=0 (origin 896)
    # both map to world x=896 -> a world-XZ deform must give them the identical delta (else the seam cracks).
    b13 = _flat_block([[64.0, 0.0, -32.0]])
    b14 = _flat_block([[0.0, 0.0, -32.0]])
    ctr = (896.0, -1056.0)
    M.deform_radial(b13, amount=8.0, radius=200.0, center=ctr, world_origin=W.block_world_origin(13, 16))
    M.deform_radial(b14, amount=8.0, radius=200.0, center=ctr, world_origin=W.block_world_origin(14, 16))
    assert abs(b13.verts[0][1] - b14.verts[0][1]) < 1e-9     # identical -> watertight seam


def test_deform_ridge_raises_along_segment():
    from ff9mapkit.world import mesh as M
    bm = _flat_block([[0, 0, 0], [5, 0, 0], [0, 0, 20]])     # on-line, off-to-side, on-line
    M.deform_ridge(bm, p0=(0.0, 0.0), p1=(0.0, 100.0), amount=6.0, radius=10.0)
    ys = [v[1] for v in bm.verts]
    assert abs(ys[0] - 6.0) < 1e-9 and abs(ys[2] - 6.0) < 1e-9   # on the ridge line -> full height
    assert 0 < ys[1] < 6.0                                        # off to the side -> partial


def test_flatten_region_pulls_to_height():
    from ff9mapkit.world import mesh as M
    bm = _flat_block([[0, 10, 0], [3, 20, 0], [100, 50, 0]])
    M.flatten_region(bm, radius=10.0, center=(0.0, 0.0), height=0.0)
    ys = [v[1] for v in bm.verts]
    assert abs(ys[0]) < 1e-9                     # centre fully flattened to the target
    assert 0 < ys[1] < 20.0                      # partially pulled toward it
    assert ys[2] == 50.0                         # outside the radius: untouched


def test_falloff_endpoints_and_monotonic():
    from ff9mapkit.world import mesh as M
    for kind in ("smooth", "gauss", "cone"):
        assert M._falloff(0.0, kind) == 1.0      # full weight at the centre
        assert M._falloff(1.0, kind) == 0.0      # zero at/after the rim (no step -> no crease)
        assert M._falloff(1.5, kind) == 0.0
        prev = 1.0
        for i in range(1, 10):
            w = M._falloff(i / 10.0, kind)
            assert w <= prev + 1e-9              # monotonically non-increasing
            prev = w


def test_recompute_normals_unit_and_oriented():
    from ff9mapkit.world import mesh as M
    bm = _flat_block([[0, 0, 0], [10, 0, 0], [0, 0, 10]], normals=[[0, 1, 0]] * 3)
    bm.verts[0][1] = 5.0                         # tilt the triangle (stale normals now point straight up)
    M.recompute_normals(bm)
    for nrm in bm.normals:
        assert abs(sum(c * c for c in nrm) ** 0.5 - 1.0) < 1e-6   # unit length
        assert nrm[1] > 0                        # sign-aligned to the original +Y facing (not inside-out)


def test_ff9mesh_roundtrip_with_normals(tmp_path):
    from ff9mapkit.world import mesh as M
    bm = _flat_block([[0, 0, 0], [1, 2, 3], [4, 5, 6]], normals=[[0, 1, 0], [0, 1, 0], [0, 1, 0]])
    d = M.read_ff9mesh(M.write_ff9mesh(bm, tmp_path / "n.ff9mesh"))
    assert d["verts"] == bm.verts and d["normals"] == bm.normals
    assert d["tangents"] is None and d["uvs"] is None


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
