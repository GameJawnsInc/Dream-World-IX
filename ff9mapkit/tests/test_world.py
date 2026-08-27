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


def test_encode_decode_id_roundtrip():
    for (e, a, t, f) in [(0, 0, 58, 0), (1, 44, 19, 0), (2, 14, 0, 0), (3, 63, 63, 3)]:
        assert W.decode_id(W.encode_id(e, a, t, f)) == {"event": e, "area": a, "topograph": t, "flags": f}


def test_retarget_tiles_make_and_move_entrance():
    from ff9mapkit.world import mesh as M
    # LEVER B: two plain tiles (topograph 58) -> make them an entrance to area 5, topograph preserved
    bm = _synthetic_block(tan0_x=232, tan3_x=232)
    assert M.retarget_tiles(bm, event=1, area=5) == 2
    summ = W.block_summary(bm)
    assert summ["place_areas"] == [5] and all(e["event"] == 1 for e in summ["place_entrances"])
    assert W.decode_id(int(round(bm.tangents[0][0])))["topograph"] == 58          # topograph kept
    # only_entrances: re-point the entrance tile only, leave plain land alone
    bm2 = _synthetic_block(tan0_x=27724, tan3_x=232)                              # tri0 = area44 entrance ; tri1 = plain
    assert M.retarget_tiles(bm2, area=9, only_entrances=True) == 1
    assert W.block_summary(bm2)["place_areas"] == [9]                             # area 44 -> area 9
    assert W.decode_id(int(round(bm2.tangents[3][0])))["event"] == 0             # the plain tile is untouched


def test_retarget_tiles_exclude_box_skips_under_building():
    from ff9mapkit.world import mesh as M
    # two plain tiles: tri0 centroid ~(1,-1), tri1 ~(4,-4). A box over tri1 (an impassable building) skips it, so an
    # entrance-trigger tile is never placed under the structure (the soft-lock the castle caused).
    bm = _synthetic_block(tan0_x=232, tan3_x=232)
    n = M.retarget_tiles(bm, event=1, area=5, exclude_box=(3.0, 5.0, -5.0, -3.0))
    assert n == 1
    ev = [W.decode_id(int(round(bm.tangents[t[0]][0])))["event"] for t in bm.tris]
    assert ev == [1, 0]                                       # tri0 set; tri1 (under the building box) left plain


def test_add_solid_base_fills_hollow_footprint():
    from ff9mapkit.world import mesh as M
    # a "building" = two separate clusters with a GAP between (like the castle's split towers). The solid base
    # fills the convex hull, so the gap becomes impassable and can't box a player who walks in.
    ch = {W.CH_POS: [[0, 5, 0], [2, 5, 0], [0, 5, 2], [20, 5, 0], [22, 5, 0], [20, 5, 2]],
          W.CH_NRM: [[0, 1, 0]] * 6, W.CH_UV: [[0, 0]] * 6,
          W.CH_TAN: [[float(W.encode_id(0, 0, 59)), 0, 0, 1]] * 6}
    bm = W.BlockMesh(name="Block[0][0] Object", disc=1, x=0, y=0, lod="0_1", vcount=6, stride=48,
                     channels={W.CH_POS: (0, 3), W.CH_NRM: (12, 3), W.CH_UV: (24, 2), W.CH_TAN: (32, 4)},
                     chan_arrays=ch, flat_index=[0, 1, 2, 3, 4, 5], tris=[[0, 1, 2], [3, 4, 5]],
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    base = M.add_solid_base(bm, topograph=59, lift=0.5)
    assert base.vcount > bm.vcount and len(base.tris) > len(bm.tris)

    def pip(px, pz, t):
        (ax, az), (bx, bz), (cx, cz) = t
        d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(d) < 1e-9:
            return False
        a = ((bz - cz) * (px - cx) + (cx - bx) * (pz - cz)) / d
        b = ((cz - az) * (px - cx) + (ax - cx) * (pz - cz)) / d
        return a >= -0.01 and b >= -0.01 and (1 - a - b) >= -0.01

    fill = [[(base.verts[t[i]][0], base.verts[t[i]][2]) for i in range(3)] for t in base.tris[len(bm.tris):]]
    assert any(pip(10.0, 1.0, t) for t in fill)                  # the gap (10,1) is now covered -> no walk-in
    assert all(W.decode_id(int(round(base.tangents[i][0])))["topograph"] == 59
               for i in range(bm.vcount, base.vcount))           # fill is impassable
    assert abs(base.verts[bm.vcount][1] - 5.5) < 1e-6            # sits at min-Y (5) + lift (0.5)


def test_cell_openness_note_flags_bad_spots():
    from ff9mapkit.world import entrance as EN
    # 2-tile cell: tri0 walkable (topo10), tri1 blocked (topo49 river/cliff) -> >20% blocked -> POOR SPOT note
    ter = _synthetic_block(tan0_x=W.encode_id(0, 0, 10), tan3_x=W.encode_id(0, 0, 49))
    summ = {}
    EN._cell_openness_note(ter, 2.0, -2.0, 0.0, 0.0, summ)
    assert summ.get("notes") and any("BLOCKED" in n for n in summ["notes"])
    # all-walkable cell (topo 10 + 36) -> no note
    ter2 = _synthetic_block(tan0_x=W.encode_id(0, 0, 10), tan3_x=W.encode_id(0, 0, 36))
    summ2 = {}
    EN._cell_openness_note(ter2, 2.0, -2.0, 0.0, 0.0, summ2)
    assert not summ2.get("notes")
    # an adjacent town (stock object carrying topo-59 collision) -> trap-pocket warning
    town = _synthetic_block(tan0_x=W.encode_id(0, 0, 59), tan3_x=W.encode_id(0, 0, 59))
    summ3 = {}
    EN._cell_openness_note(ter2, 2.0, -2.0, 0.0, 0.0, summ3, stock_obj=town)
    assert summ3.get("notes") and any("town" in n.lower() for n in summ3["notes"])


def test_retarget_tiles_only_box_blocks_footprint():
    from ff9mapkit.world import mesh as M
    # two plain tiles: tri0 centroid ~(1,-1), tri1 ~(4,-4). only_box over tri0 blocks JUST the footprint tile 59.
    bm = _synthetic_block(tan0_x=W.encode_id(0, 0, 10), tan3_x=W.encode_id(0, 0, 10))
    n = M.retarget_tiles(bm, topograph=59, only_box=(0.0, 2.0, -2.0, 0.0))
    assert n == 1
    topos = [W.decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] for t in bm.tris]
    assert topos == [59, 10]                                  # tri0 (in box) blocked; tri1 (outside) untouched


def test_retarget_tiles_polygon_matches_outline():
    from ff9mapkit.world import mesh as M
    poly = [(0.0, 0.0), (3.0, 0.0), (0.0, -3.0)]              # a triangle containing tri0 ~(1,-1) but not tri1 ~(4,-4)
    assert M._point_in_polygon(1.0, -1.0, poly) and not M._point_in_polygon(4.0, -4.0, poly)
    bm = _synthetic_block(tan0_x=W.encode_id(0, 0, 10), tan3_x=W.encode_id(0, 0, 10))
    assert M.retarget_tiles(bm, topograph=59, only_polygon=poly) == 1        # only the tile inside the outline
    assert [W.decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] for t in bm.tris] == [59, 10]
    bm2 = _synthetic_block(tan0_x=232, tan3_x=232)
    assert M.retarget_tiles(bm2, event=1, exclude_polygon=poly) == 1         # skip the tile inside the outline
    assert [W.decode_id(int(round(bm2.tangents[t[0]][0])))["event"] for t in bm2.tris] == [0, 1]


def test_entrance_building_world_hull(tmp_path):
    from ff9mapkit.world import entrance as EN, mesh as M
    obj = tmp_path / "b.obj"
    obj.write_text("v -10 0 -3\nv 10 0 -3\nv 10 0 3\nv -10 0 3\nf 1 2 3 4\n")   # 20x6 rect, centroid (0,0)
    hull = EN._building_world_hull({"obj": str(obj), "at": (100.0, -200.0)}, (0.0, 0.0))
    assert M._point_in_polygon(100.0, -200.0, hull)                          # centre blocked
    assert not M._point_in_polygon(115.0, -200.0, hull)                      # 5u past the 10u half-width -> walkable


def test_entrance_hull_anchors_by_bbox_center_not_centroid(tmp_path):
    from ff9mapkit.world import entrance as EN
    # asymmetric OBJ: 3 verts clustered near x=0, one far at x=20 -> centroid x=5.25 but bbox-centre x=10.
    # bbox-centre anchoring must seat the FOOTPRINT symmetrically on the target (span [90,110], not the
    # centroid-pulled [94.75,114.75]) so the model doesn't bulge to one side of the cell.
    obj = tmp_path / "asym.obj"
    obj.write_text("v 0 0 0\nv 0 0 4\nv 1 0 2\nv 20 0 2\nf 1 2 3\nf 1 3 4\n")
    hull = EN._building_world_hull({"obj": str(obj), "at": (100.0, -200.0)}, (0.0, 0.0))
    xs = [p[0] for p in hull]
    assert abs(min(xs) - 90.0) < 1e-6 and abs(max(xs) - 110.0) < 1e-6   # centred on 100 (bbox), not 94.75 (centroid)


def test_building_world_box(tmp_path):
    from ff9mapkit.world import entrance as EN
    obj = tmp_path / "b.obj"
    obj.write_text("v -10 0 -3\nv 10 0 -3\nv 10 0 3\nv -10 0 3\nf 1 2 3 4\n")   # 20x6, centroid (0,0)
    box = EN._building_world_box({"obj": str(obj), "at": (100.0, -200.0)}, (0.0, 0.0), margin=2.0)
    assert box == (88.0, 112.0, -205.0, -195.0)               # centroid -> (100,-200), padded 2u


def test_entrance_block_detection_predicate():
    # the predicate world-deploy uses to REFUSE reshaping a place-entrance block (softlock + prop-pit trap)
    entr = _synthetic_block(tan0_x=27724, tan3_x=232)          # tri0 = event1/area44 entrance ; tri1 = plain land
    hits = sorted({W.decode_id(i)["area"] for i in W.block_mapids(entr) if W.decode_id(i)["event"]})
    assert hits == [44]                                        # flagged as an entrance block (area 44)
    plain = _synthetic_block(tan0_x=232, tan3_x=232)           # both plain terrain -> not an entrance block
    assert not [i for i in W.block_mapids(plain) if W.decode_id(i)["event"]]


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


# ---- overworld entrance dispatch decode (world-locate) ---------------------------------------
def test_sc_condition_parse():
    from ff9mapkit.world import locate as L
    assert L._sc_condition("opDC(0) op7D(96,34) op18 op7F") == "SC < 8800"     # 96+34*256=8800, op18=<
    assert L._sc_condition("opDC(0) op7D(236,9) op1A op7F") == "SC <= 2540"    # 236+9*256=2540, op1A=<=
    assert L._sc_condition("opD5(29) op7F") is None                            # not a ScenarioCounter gate


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_case_to_fields_matches_dispatch():
    from ff9mapkit.world import locate as L
    a = L.case_to_fields()
    assert a[2] == [("SC < 8800", 1856), ("default", 2450)]      # case 2 = Alexandria Main Street
    assert a[14] == [("SC <= 2540", 359), ("default", 350)]      # case 14 = Dali
    assert a[4] == [("default", 300)]                            # case 4 = Ice Cavern
    assert a[24][0][1] == 2152 and a[24][-1] == ("default", 602)  # 3-way ScenarioCounter branch (Dragon's Gate)
    assert L.area_to_fields is L.case_to_fields                  # compat alias for the pre-census name


def test_navipos_landmark_pins():
    """Offline regression pins for the navipos naming layer (the engine's landmark table; the census verified the
    markers land inside their Object-mesh structure bboxes to <2u)."""
    from ff9mapkit.world import locate as L
    lm = {m["name"]: m for m in L.landmarks()}
    assert lm["Alexandria Harbour"]["block"] == (21, 10)
    assert lm["Lindblum Dragon's Gate"]["block"] == (14, 15)
    near = L.nearest_landmark(1349.8, -678.0)
    assert near["name"] == "Alexandria Harbour" and near["dist"] < 2.0


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_case_to_cells_geography_is_the_cell_tag_join():
    """THE CELL-TAG JOIN (census refit): entrance geography comes from object-0's GetIP cell tags, NOT from the
    tiles' IDALL area bits (which the pre-census join used -- it filed Alexandria under Marsh 650 and Qu's Marsh
    under Treno 908 because case numbers coincide with unrelated area numbers)."""
    from ff9mapkit.world import locate as L
    c = L.case_to_cells()
    assert (39, 21, 1) in c[2]                                   # Alexandria's gate cell -> case 2 (1856/2450)
    assert (34, 25, 1) in c[14]                                  # Dali -> case 14 (NOT the area-2 conflation)
    assert (29, 29, 1) in c[22]                                  # Qu's Marsh -> case 22 -> Marsh/Entrance 650
    assert set(c[25]) == {(27, 33, 2), (27, 34, 2), (28, 33, 2), (28, 34, 2)}  # Lindblum: 4 alias tags, ONE body
    b = L.case_to_blocks()
    assert b[24] == [(14, 15)]                                   # Lindblum Dragon's Gate block
    assert (19, 10) in b[2]                                      # Alexandria's gate block


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_locate_rows_name_the_right_places():
    from ff9mapkit.world import locate as L
    rows = {r["case"]: r for r in L.locate()}
    r24 = rows[24]
    assert r24["blocks"] == [(14, 15)] and r24["landmark"]["name"] == "Lindblum Dragon's Gate"
    assert r24["destinations"][-1]["field"] == 602
    r2 = rows[2]
    assert r2["landmark"]["name"] == "Alexandria" and r2["landmark"]["dist"] < 16
    assert rows[22]["landmark"]["name"] == "Qu's Marsh" and rows[22]["destinations"][0]["field"] == 650


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_list_blocks_and_sample_roundtrip():
    blocks = W.list_blocks(disc=1)
    assert (0, 0) in blocks and len(blocks) > 100             # disc 1 has hundreds of terrain blocks
    sample = blocks[::max(1, len(blocks) // 12)]              # ~12 spread across the grid
    for (x, y) in sample:
        assert W.roundtrip_ok(W.read_block(x, y, disc=1)), f"block[{x}][{y}] not lossless"


def test_blendio_obj_to_blockmesh(tmp_path):
    """Offline: OBJ -> BlockMesh does world->target-local frame conversion, unindexes, preserves UV, stamps IDALL."""
    from ff9mapkit.world import blendio as BIO, mesh as M
    from ff9mapkit.world.extract import decode_id, block_world_origin
    ox, oz = block_world_origin(2, 3)                         # target block origin
    obj_text = "\n".join([
        "o Block_2_3_object",
        f"v {ox + 10:.3f} 5.0 {oz - 4:.3f}",
        f"v {ox + 20:.3f} 6.0 {oz - 8:.3f}",
        f"v {ox + 30:.3f} 7.0 {oz - 2:.3f}",
        "vt 0.1 0.2", "vt 0.3 0.4", "vt 0.5 0.6",
        "vn 0 1 0", "vn 0 1 0", "vn 0 1 0",
        "f 1/1/1 2/2/2 3/3/3",
    ]) + "\n"
    p = tmp_path / "b.obj"
    p.write_text(obj_text)
    obj = BIO.read_obj(p)
    assert len(obj["V"]) == 3 and len(obj["faces"]) == 1
    bm = BIO.obj_to_blockmesh(obj, into_block=(2, 3), part="object", topograph=59)
    assert bm.vcount == 3 and len(bm.tris) == 1 and (bm.x, bm.y) == (2, 3)
    assert abs(bm.verts[0][0] - 10.0) < 1e-4 and abs(bm.verts[0][2] + 4.0) < 1e-4   # world -> local
    assert abs(bm.uvs[1][0] - 0.3) < 1e-4                                            # UV preserved
    assert all(decode_id(int(round(bm.tangents[t[0]][0])))["topograph"] == 59 for t in bm.tris)
    M.write_ff9mesh(bm, tmp_path / "b.ff9mesh")               # writes the loose override format
    rt = M.read_ff9mesh(tmp_path / "b.ff9mesh")
    assert rt["vcount"] == 3 and len(rt["indices"]) == 3


def test_blendio_trim_floor(tmp_path):
    """trim_floor drops LOW up-facing faces (base floor/apron) while keeping walls + high roofs; round-trips via OBJ."""
    from ff9mapkit.world import blendio as BIO
    obj = {"V": [[0, 0, 0], [0, 0, 4], [4, 0, 0],        # 1-3: low flat FLOOR (up-facing, Y0) -> drop
                 [0, 0, 0], [4, 0, 0], [0, 10, 0],       # 4-6: vertical WALL -> keep
                 [0, 20, 0], [0, 20, 4], [4, 20, 0]],    # 7-9: high flat ROOF (up-facing, Y20) -> keep
           "VT": [], "VN": [],
           "faces": [((1, 0, 0), (2, 0, 0), (3, 0, 0)),
                     ((4, 0, 0), (5, 0, 0), (6, 0, 0)),
                     ((7, 0, 0), (8, 0, 0), (9, 0, 0))]}
    t = BIO.trim_floor(obj, base_height=6.0, up_threshold=0.5)
    assert t["dropped"] == 1 and t["kept"] == 2 and len(t["faces"]) == 2   # only the base floor removed
    p = BIO.write_obj(t, tmp_path / "trimmed.obj")
    rt = BIO.read_obj(p)
    assert len(rt["faces"]) == 2 and len(rt["V"]) == 9                       # faces filtered, vert pool preserved


def test_blendio_quad_triangulates(tmp_path):
    """A quad face fan-triangulates to two triangles (Blender may export n-gons)."""
    from ff9mapkit.world import blendio as BIO
    p = tmp_path / "q.obj"
    p.write_text("\n".join(["v 0 0 0", "v 1 0 0", "v 1 0 -1", "v 0 0 -1", "f 1 2 3 4"]) + "\n")
    obj = BIO.read_obj(p)
    assert len(obj["faces"]) == 2
    bm = BIO.obj_to_blockmesh(obj, into_block=(0, 0))
    assert len(bm.tris) == 2 and bm.vcount == 6


# ---- overworld ENTRANCE authoring (world-entrance) --------------------------------------------
def test_entrance_pack_unpack_cell_tag():
    from ff9mapkit.world import entrance as EN
    # the WorldEvent GetIP key: 0x8000 | (cellZ<<8 & 0x3F00) | (cellX<<2 & 0xFC) | (id&3)  (ff9.cs WorldEvent;
    # verified vs real object-0 tags). z is a 6-BIT field -- the engine aliases z mod 64, so the kit REFUSES
    # z >= 64 (a 7-bit-packed tag would set bit 14, which no WorldEvent request carries -> a never-firing trigger).
    assert EN.pack_cell_tag(35, 25, 1) == 0x998D
    assert EN.pack_cell_tag(37, 24, 1) == 0x9895            # WORLD00's real Ice-Cavern func tag
    assert EN.unpack_cell_tag(0x998D) == (35, 25, 1)
    assert EN.unpack_cell_tag(0x9895) == (37, 24, 1)
    assert EN.unpack_cell_tag(0x0004) is None               # top bit unset -> an ordinary object func, not a cell
    assert EN.unpack_cell_tag(0xD895) is None               # bit 14 set -> WorldEvent's formula never emits this
    # round-trip across the valid ranges
    for cx, cz, ev in [(0, 0, 1), (63, 63, 3), (35, 25, 2)]:
        assert EN.unpack_cell_tag(EN.pack_cell_tag(cx, cz, ev)) == (cx, cz, ev)
    for bad in [(64, 0, 1), (0, 64, 1), (0, 128, 1), (0, 0, 0), (0, 0, 4)]:
        with pytest.raises(ValueError):
            EN.pack_cell_tag(*bad)


def test_entrance_cell_geometry():
    from ff9mapkit.world import entrance as EN
    assert EN.cell_to_block(35, 25) == (17, 12)             # 32u cells, 64u blocks (proven in-game placement)
    assert EN.cell_to_block(37, 24) == (18, 12)
    assert EN.cell_to_block(0, 0) == (0, 0)
    assert EN.cell_world_center(35, 25) == (1136, -816)     # matches the debug-menu World-tab cell readout (Z negated)
    assert EN.cell_world_center(0, 0) == (16, -16)


def test_entrance_patch_byte39_synthetic():
    from ff9mapkit.world import entrance as EN
    # a SYNTHETIC entrance-func body (our own opcode bytes -- op_05{ Byte[39]=4 } ; op_04), NOT game data
    body = bytes([0x05, 0xD5, 0x27, 0x7D, 0x04, 0x00, 0x2C, 0x7F, 0x04])
    assert EN.byte39_value(body) == 4
    patched = EN.patch_byte39(body, 13)
    assert EN.byte39_value(patched) == 13
    assert patched[4] == 13 and patched[:4] == body[:4] and patched[5:] == body[5:]   # only the literal moved
    with pytest.raises(ValueError):                         # a body with no Byte[39] assignment is rejected
        EN.patch_byte39(bytes([0x05, 0x7F, 0x04]), 4)


def test_entrance_blockmesh_from_ff9mesh_reconstructs():
    """A deployed .ff9mesh reconstructs into an editable BlockMesh (so a 2nd entrance STACKS on the 1st)."""
    from ff9mapkit.world import mesh as M
    import tempfile
    bm = _synthetic_block(tan0_x=27724, tan3_x=232)
    with tempfile.TemporaryDirectory() as d:
        p = M.write_ff9mesh(bm, f"{d}/b.ff9mesh")
        rt = M.blockmesh_from_ff9mesh(p, disc=1, x=0, y=0, part="terrain")
    assert rt.vcount == bm.vcount and len(rt.tris) == len(bm.tris)
    assert rt.verts == bm.verts and rt.tangents == bm.tangents
    # and the reconstruction is itself editable: retarget still works on it
    assert M.retarget_tiles(rt, area=9, only_entrances=True) == 1


def test_entrance_read_block_stacked_prefers_override(tmp_path):
    """read_block_stacked returns the mod-folder override when present (offline, no install needed)."""
    from ff9mapkit.world import entrance as EN, mesh as M
    bm = _synthetic_block(tan0_x=27724, tan3_x=232)
    dest = tmp_path / "FF9CustomMap" / M.override_relpath(1, 0, 0, "0_1", "Terrain")
    M.write_ff9mesh(bm, dest)
    got = EN.read_block_stacked("FF9CustomMap", 0, 0, disc=1, part="terrain", game=tmp_path)
    assert got.vcount == bm.vcount and got.tangents == bm.tangents     # read the override, not p0data
    # a block with no override + no install returns None under missing_ok (never raising into p0data)
    assert EN.read_block_stacked("FF9CustomMap", 9, 9, part="object", game=tmp_path, missing_ok=True) is None
    # fresh=True IGNORES the override -> falls through to p0data (missing here) instead of returning it
    assert EN.read_block_stacked("FF9CustomMap", 0, 0, disc=1, part="terrain", game=tmp_path,
                                 fresh=True, missing_ok=True) is None


# --- install-gated: real dispatchers + destination table ---
@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_entrance_func_body_real_template():
    from ff9mapkit.world import entrance as EN
    body = EN.entrance_func_body(4)                         # the proven Ice-Cavern case, from the real 0x9895
    assert EN.byte39_value(body) == 4 and len(body) == 29
    assert EN.byte39_value(EN.entrance_func_body(13)) == 13  # redirect the destination via the literal patch


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_entrance_resolve_destination():
    from ff9mapkit.world import entrance as EN
    assert EN.resolve_destination(field=300)["case"] == 4          # Ice Cavern <- case 4
    assert EN.resolve_destination(case=4)["field"] == 300
    with pytest.raises(ValueError, match="no overworld dispatch case leads to field 999999"):
        EN.resolve_destination(field=999999)                       # unreachable -> actionable error
    with pytest.raises(ValueError, match="EITHER field=<id> OR case=<n>, not both"):
        EN.resolve_destination(field=300, case=4)                  # not both


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_entrance_dispatcher_cases():
    from ff9mapkit.world import entrance as EN
    disp = EN.load_world_dispatchers()
    assert len(disp) == 13                                          # WORLD00..12
    assert 4 in EN.dispatcher_cases(disp["evt_world_world00"])      # WORLD00 routes case 4
    assert EN.dispatcher_cases(disp["evt_world_world01"]) is None   # a cutscene state has no area switch


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_entrance_add_function_e2e():
    """Author the trigger func into a real dispatcher; it disassembles correctly and corrupts nothing."""
    from ff9mapkit.world import entrance as EN
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.eb import edit as E, disasm as D
    disp = EN.load_world_dispatchers()
    base = disp["evt_world_world00"]
    s0 = EbScript.from_bytes(base)
    tag = EN.pack_cell_tag(50, 40, 1)                              # a fresh cell not already in WORLD00
    out = E.add_function(base, 0, tag, EN.entrance_func_body(13, dispatchers=disp))
    s1 = EbScript.from_bytes(out)
    nf = s1.entry(0).func_by_tag(tag)
    assert nf is not None
    ins = list(D.iter_code(s1.data, nf.abs_start, nf.abs_end))
    assert any(i.op == 0x10 and i.imm(0) == 6 for i in ins)         # RunScriptAsync(6, 1, 11)
    assert EN.byte39_value(out[nf.abs_start:nf.abs_end]) == 13
    for f in s0.entry(0).funcs:                                     # every prior func byte-identical
        g = s1.entry(0).func_by_tag(f.tag)
        assert base[f.abs_start:f.abs_end] == out[g.abs_start:g.abs_end]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_entrance_author_dry_run():
    from ff9mapkit.world import entrance as EN
    # cell (35,25) -> the proven Dali-adjacent block [17][12]; field 300 = Ice Cavern (case 4). A nonexistent mod
    # folder means the base is pristine p0data (no prior deploy to stack on).
    info = EN.author_entrance(cell=(35, 25), mod_folder="FF9CustomMap_test_nonexistent", field=300, dry_run=True)
    assert info["dry_run"] and info["tag_hex"] == "0x998D"
    assert info["block"] == [17, 12] and info["case"] == 4 and info["field"] == 300
    # case 4 lives in all 9 area-switch dispatchers; each is either written or (if it already had the cell) skipped
    assert len(info["dispatchers_written"]) + len(info["dispatchers_skipped"]) == 9
    assert info["dispatchers_written"] and info["tiles_set"] > 0    # the cell's terrain tiles were matched


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_entrance_patches_each_language_own_base():
    """The world dispatchers are NOT language-identical (JP carries localized dialogue + a distinct layout), so the
    entrance func must be patched into EACH language's own base -- cloning US to jp/ would clobber JP dialogue."""
    from ff9mapkit.world import entrance as EN
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.eb import edit as E
    alld = EN.load_all_dispatchers()
    assert len(alld) == 13 and {"us", "jp", "uk", "fr"} <= set(alld["evt_world_world00"])
    langs = alld["evt_world_world00"]
    assert langs["jp"] != langs["us"]                              # JP is a distinct dispatcher (16 B shorter)
    tag = EN.pack_cell_tag(50, 40, 1)
    body = EN.entrance_func_body(4, dispatchers={n: L["us"] for n, L in alld.items()})
    out_us = E.add_function(langs["us"], 0, tag, body)
    out_jp = E.add_function(langs["jp"], 0, tag, body)
    assert out_jp != out_us                                        # patched separately -> JP layout preserved
    # every pre-existing dispatcher func (entry 1 = where the localized dialogue lives) is byte-identical in JP
    s0, s1 = EbScript.from_bytes(langs["jp"]), EbScript.from_bytes(out_jp)
    for f in s0.entry(1).funcs:
        g = s1.entry(1).func_by_tag(f.tag)
        assert g is not None and langs["jp"][f.abs_start:f.abs_end] == out_jp[g.abs_start:g.abs_end]


def test_entrance_missing_building_rejected_before_write(tmp_path):
    """A bad --building path fails FAST (before any .eb write) so it can't leave a half-deploy. Offline: the guard
    raises before load_world_dispatchers is reached."""
    from ff9mapkit.world import entrance as EN
    with pytest.raises(ValueError, match=r"--building OBJ not found"):
        EN.author_entrance(cell=(35, 25), mod_folder="X", case=4, game=tmp_path,
                           building={"obj": str(tmp_path / "nope.obj")}, dry_run=True)


def test_entrance_cli_texture_passthrough(tmp_path, capsys, monkeypatch):
    """world-entrance forwards --texture/--tile/--tile-uv into the building dict (2026-07-09: texturing a
    building on a transplanted cell needed TWO manual build_from_obj bypasses because the flags simply
    weren't plumbed through the CLI); texture flags without --building are rejected up front."""
    from ff9mapkit import cli
    from ff9mapkit.world import entrance as EN
    # the spec parsers (shared with world-mesh-build)
    assert cli._parse_tile_spec("52:0") == (52, 0)
    with pytest.raises(ValueError, match="TOPOGRAPH:VARIANT"):
        cli._parse_tile_spec("52")
    assert cli._parse_tile_uv_spec("0.1,0.2,0.3,0.4") == (0.1, 0.2, 0.3, 0.4)
    with pytest.raises(ValueError, match="umin,vmin"):
        cli._parse_tile_uv_spec("0.1,0.2")
    # texture flags without --building = a hard arg error, not a silent no-op
    rc = cli.main(["world-entrance", "--cell", "19", "21", "--field", "300", "--mod-folder", "X", "--texture"])
    assert rc == 2 and "--building" in capsys.readouterr().err
    # the parsed flags land in the building dict author_entrance receives
    captured = {}

    def fake_author(**kw):
        captured.update(kw)
        return {"tag_hex": "0x0000", "field": 300, "dry_run": True, "cell": (19, 21), "case": 4,
                "dest_note": "", "dispatchers_written": [], "dispatchers_skipped": [], "langs": [],
                "tiles_set": 1, "block": (9, 10), "event": 1, "backups": []}

    monkeypatch.setattr(EN, "author_entrance", fake_author)
    rc = cli.main(["world-entrance", "--cell", "19", "21", "--field", "300", "--mod-folder", "X",
                   "--building", str(tmp_path / "t.obj"), "--tile", "52:0", "--dry-run"])
    assert rc == 0
    b = captured["building"]
    assert b["tile"] == (52, 0) and b["tile_uv"] is None and b["texture"] is False   # --tile implies texture downstream


def test_entrance_flatten_pad_capped_to_building(tmp_path):
    """A --flatten-pad wider than the building is capped to the footprint, so the flat (step-prone) ground stays
    under the impassable structure instead of leaving a walkable edge-step you get stuck on."""
    from ff9mapkit.world import entrance as EN
    # a 20(X) x 6(Z) base: inscribed radius from the centroid = min half-extent = 3 (the shallow Z side), NOT the
    # 10.4 corner -- so a wide circular pad is capped to keep it under the narrow side too (the real castle bug).
    obj = tmp_path / "b.obj"
    obj.write_text("v -10 0 -3\nv 10 0 -3\nv 10 0 3\nv -10 0 3\nf 1 2 3 4\n")
    summ = {}
    r = EN._capped_flatten_radius(14.0, {"obj": str(obj)}, summ)
    assert abs(r - 3.0) < 1e-6 and summ["notes"] and "capped" in summ["notes"][0]   # inscribed (min extent), not corner
    summ2 = {}                                                              # requested < footprint -> unchanged, no note
    assert EN._capped_flatten_radius(2.0, {"obj": str(obj)}, summ2) == 2.0 and not summ2.get("notes")
    summ3 = {}                                                              # no building -> not capped but warns
    assert EN._capped_flatten_radius(14.0, None, summ3) == 14.0 and summ3["notes"]


def test_world_deploy_rejects_lift_with_reshape(capsys):
    """--hill/--crater/--flatten and --lift/--spike are mutually exclusive: --lift/--spike is a flat diagnostic
    bump, and the elif dispatch picks exactly one branch -- composing them must refuse, not pick a winner."""
    from ff9mapkit import cli
    ns = cli.build_parser().parse_args(["world-deploy", "--mod-folder", "FF9CustomMap",
                                        "--block", "3", "7", "--hill", "24", "--lift", "5"])
    rc = cli._cmd_world_deploy(ns)
    assert rc == 2
    assert "not both" in capsys.readouterr().err

    ns2 = cli.build_parser().parse_args(["world-deploy", "--mod-folder", "FF9CustomMap",
                                         "--block", "3", "7", "--crater", "8", "--spike", "2"])
    rc2 = cli._cmd_world_deploy(ns2)
    assert rc2 == 2
    assert "not both" in capsys.readouterr().err
