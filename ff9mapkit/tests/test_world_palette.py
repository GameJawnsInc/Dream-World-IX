"""Learned UV palette (world/palette.py) -- stamp real atlas tiles onto UV-less new overworld geometry.

Hermetic: build_palette ranks donor tiles by frequency (over stubbed sample_donor_faces); pick_uvs picks the modal
tile + falls back (variant OOR -> modal, absent topograph -> global modal, empty -> None); apply_palette_uvs stamps
ONLY zero-UV faces, keyed per-triangle by topograph, and leaves already-textured faces byte-identical.
"""
from __future__ import annotations

from ff9mapkit.world import palette as P
from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_UV, CH_TAN


def _mesh(tris_spec):
    """A minimal flat/unindexed BlockMesh from [(topograph, [uv0,uv1,uv2]), ...] -- one triangle per spec."""
    pos, uv, tan, tris = [], [], [], []
    for ti, (topo, uvs) in enumerate(tris_spec):
        idall = float(encode_id(topograph=topo))
        for k in range(3):
            pos.append([float(ti), 0.0, float(k)])
            uv.append([float(uvs[k][0]), float(uvs[k][1])])
            tan.append([idall, 0.0, 0.0, 1.0])
        tris.append([ti * 3, ti * 3 + 1, ti * 3 + 2])
    chan = {CH_POS: pos, CH_UV: uv, CH_TAN: tan}
    channels = {CH_POS: (0, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}
    return BlockMesh(name="t", disc=1, x=0, y=0, lod="0_1", vcount=len(pos), stride=48, channels=channels,
                     chan_arrays=chan, flat_index=list(range(len(pos))), tris=tris, raw_vbuf=b"", raw_ibuf=b"",
                     use32=True, submeshes=[])


def test_build_palette_ranks_donor_tiles(monkeypatch):
    tileA = ((0.1, 0.2), (0.3, 0.4), (0.5, 0.6))
    tileB = ((0.7, 0.7), (0.8, 0.8), (0.9, 0.9))
    faces = [(10, tileA), (10, tileA), (10, tileA), (10, tileB), (37, tileB)]   # topo10: A x3 > B x1
    monkeypatch.setattr(P, "sample_donor_faces", lambda *a, **k: iter(faces))
    pal = P.build_palette(disc=1, part="terrain", cache=False)
    assert [uv for uv, _ in pal[10]] == [tileA, tileB]        # modal (A) first
    assert pal[10][0] == (tileA, 3) and pal[37] == [(tileB, 1)]


def test_pick_uvs_modal_variant_and_fallbacks():
    tileA = ((0.1, 0.2), (0.3, 0.4), (0.5, 0.6))
    tileB = ((0.7, 0.7), (0.8, 0.8), (0.9, 0.9))
    pal = {10: [(tileA, 3), (tileB, 1)], 37: [(tileB, 5)]}
    assert P.pick_uvs(pal, 10) == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]      # modal
    assert P.pick_uvs(pal, 10, variant=1) == [[0.7, 0.7], [0.8, 0.8], [0.9, 0.9]]
    assert P.pick_uvs(pal, 10, variant=9) == [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]  # OOR -> modal
    # absent topograph -> the GLOBAL modal (tileB, count 5 > tileA count 3)
    assert P.pick_uvs(pal, 99) == [[0.7, 0.7], [0.8, 0.8], [0.9, 0.9]]
    assert P.pick_uvs({}, 10) is None                          # empty palette


def test_apply_palette_uvs_stamps_only_zero_faces():
    zero = [(0.0, 0.0)] * 3
    real = [(0.5, 0.5)] * 3
    bm = _mesh([(10, zero), (10, real)])                       # tri0 zero-UV, tri1 already textured
    tileA = ((0.1, 0.2), (0.3, 0.4), (0.5, 0.6))
    pal = {10: [(tileA, 3)]}
    out = P.apply_palette_uvs(bm, pal, only_zero=True)
    uv = out.chan_arrays[CH_UV]
    assert uv[0] == [0.1, 0.2] and uv[1] == [0.3, 0.4] and uv[2] == [0.5, 0.6]   # tri0 stamped
    assert uv[3] == [0.5, 0.5] and uv[4] == [0.5, 0.5] and uv[5] == [0.5, 0.5]   # tri1 untouched
    # input mesh not mutated (returns a copy)
    assert bm.chan_arrays[CH_UV][0] == [0.0, 0.0]


def test_apply_palette_uvs_per_triangle_topograph_and_noop():
    zero = [(0.0, 0.0)] * 3
    bm = _mesh([(10, zero), (37, zero)])                       # two zero-UV tris, different topographs
    pal = {10: [(((0.1, 0.1), (0.1, 0.1), (0.1, 0.1)), 1)],
           37: [(((0.9, 0.9), (0.9, 0.9), (0.9, 0.9)), 1)]}
    uv = P.apply_palette_uvs(bm, pal).chan_arrays[CH_UV]
    assert uv[0] == [0.1, 0.1] and uv[3] == [0.9, 0.9]         # each tri keyed by its OWN topograph
    # a topograph override forces one tile for all faces
    uv2 = P.apply_palette_uvs(bm, pal, topograph=37).chan_arrays[CH_UV]
    assert uv2[0] == [0.9, 0.9] and uv2[3] == [0.9, 0.9]
    # empty palette -> unchanged object
    assert P.apply_palette_uvs(bm, {}) is bm


def test_stamp_uv_rect_stamps_a_custom_region():
    zero = [(0.0, 0.0)] * 3
    real = [(0.5, 0.5)] * 3
    bm = _mesh([(59, zero), (59, real)])                       # tri0 zero-UV, tri1 already textured
    rect = (0.95, 0.001, 0.999, 0.05)                          # a NEW tile's UV region (T3)
    # project="corner": the crude 3-rect-corners-per-tri
    uv = P.stamp_uv_rect(bm, rect, only_zero=True, project="corner").chan_arrays[CH_UV]
    assert uv[0] == [0.95, 0.001] and uv[1] == [0.999, 0.001] and uv[2] == [0.999, 0.05]
    assert uv[3] == uv[4] == uv[5] == [0.5, 0.5]               # textured tri untouched
    # project="box" (default): planar-projected UVs stay INSIDE the rect and vary (a real wrap, not a fixed triplet)
    uvb = P.stamp_uv_rect(bm, rect, only_zero=True).chan_arrays[CH_UV]
    for i in range(3):
        assert 0.95 <= uvb[i][0] <= 0.999 and 0.001 <= uvb[i][1] <= 0.05
    assert uvb[3] == [0.5, 0.5]                                # textured tri still untouched
    assert P.stamp_uv_rect(bm, rect, only_zero=False, project="corner").chan_arrays[CH_UV][3] == [0.95, 0.001]


def test_is_zero_uv():
    assert P._is_zero_uv([(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)])
    assert not P._is_zero_uv([(0.0, 0.0), (0.1, 0.0), (0.0, 0.0)])
