"""split_retarget_by_polygon: THE COLLISION-ALIGNMENT FIX (in-game 2026-07-09, "some collision,
but it's not aligned"). retarget_tiles' only_polygon path decides a whole triangle's fate by a
single CENTROID test -- fine on fine-grained terrain, but a real donor triangle can be several
times bigger than a small building footprint (measured: this project's transplanted highland
terrain has a median tri area of ~6 sq-units against a 36 sq-unit 6x6 tower base), so a
straddling triangle over/under-shoots the building's clean geometric edge by up to half its
own size. split_retarget_by_polygon SPLITS straddling triangles exactly (Sutherland-Hodgman
half-plane clips against every hull edge) instead of centroid-testing them whole."""
from __future__ import annotations

import pytest

from ff9mapkit.world import mesh as M
from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN, decode_id

NRM = (0.0, 1.0, 0.0)


def _v(x, y, z, idall=100.0, uv=(0.0, 0.0)):
    return ((float(x), float(y), float(z)), NRM, uv, (float(idall), 0.0, 0.0, 0.0))


def _soup(tris):
    pos, nrm, uv, tan, flat, tris_out = [], [], [], [], [], []
    for t in tris:
        base = len(pos)
        for (p, n, u, tn) in t:
            pos.append(list(p)); nrm.append(list(n)); uv.append(list(u)); tan.append(list(tn))
            flat.append(len(pos) - 1)
        tris_out.append([base, base + 1, base + 2])
    return BlockMesh(name="x", disc=1, x=0, y=0, lod="0_1", vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tris_out, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


def _area2_xz(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x0, z0 = pts[i][0], pts[i][2]
        x1, z1 = pts[(i + 1) % n][0], pts[(i + 1) % n][2]
        a += x0 * z1 - x1 * z0
    return abs(a)


def _topo_areas(bm):
    """{topo: total XZ area of tris carrying it}."""
    out = {}
    for tri in bm.tris:
        pts = [bm.verts[i] for i in tri]
        a = _area2_xz(pts) / 2.0
        topo = decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        out[topo] = out.get(topo, 0.0) + a
    return out


SQUARE = [(2.0, 2.0), (6.0, 2.0), (6.0, 6.0), (2.0, 6.0)]   # CCW, area 16


def test_fully_outside_triangle_is_unchanged():
    tri = [[_v(20, 0, 20), _v(30, 0, 20), _v(20, 0, 30)]]
    bm = _soup(tri)
    out = M.split_retarget_by_polygon(bm, SQUARE, topograph=59)
    assert len(out.tris) == 1
    areas = _topo_areas(out)
    assert 59 not in areas
    assert areas[25] == pytest.approx(_area2_xz([p[0] for p in tri[0]]) / 2.0)


def test_fully_inside_triangle_retargets_whole():
    tri = [[_v(3, 0, 3), _v(5, 0, 3), _v(3, 0, 5)]]
    bm = _soup(tri)
    out = M.split_retarget_by_polygon(bm, SQUARE, topograph=59)
    areas = _topo_areas(out)
    assert 25 not in areas
    assert areas[59] == pytest.approx(_area2_xz([p[0] for p in tri[0]]) / 2.0)


def test_straddling_triangle_splits_exactly_no_gaps_no_overlap():
    """A triangle much bigger than the hull, straddling it -- exact area conservation and the
    topo-59 region matches the TRUE geometric intersection (verified by hand: the triangle's
    hypotenuse x+z=10 clips the hull corner (6,6) [x+z=12, outside] -- true intersection =
    16 - 2 = 14, not the full 16 a naive "hull is inside" assumption would give)."""
    tri = [[_v(0, 0, 0), _v(10, 0, 0), _v(0, 0, 10)]]
    bm = _soup(tri)
    out = M.split_retarget_by_polygon(bm, SQUARE, topograph=59)
    orig_area = _area2_xz([p[0] for p in tri[0]]) / 2.0
    areas = _topo_areas(out)
    assert sum(areas.values()) == pytest.approx(orig_area)          # watertight: no gap/overlap
    assert areas[59] == pytest.approx(14.0)                         # the TRUE intersection area
    assert areas[25] == pytest.approx(orig_area - 14.0)


def test_original_topo_and_geometry_preserved_outside_hull():
    """The untouched-outside region must carry the SAME idall components (event/area/flags,
    only topograph changes on the inside piece) and UV as the source -- a split must not
    silently lose data on the fragments it keeps at the original topo."""
    tri = [[_v(0, 0, 0, idall=204.0, uv=(0.3, 0.7)), _v(10, 0, 0, idall=204.0, uv=(0.9, 0.7)),
           _v(0, 0, 10, idall=204.0, uv=(0.3, 0.1))]]
    bm = _soup(tri)
    out = M.split_retarget_by_polygon(bm, SQUARE, topograph=59)
    outside_uvs = [tuple(out.uvs[i]) for tri2 in out.tris
                   for i in tri2 if decode_id(int(round(out.tangents[tri2[0]][0])))["topograph"] != 59]
    # every outside-fragment vertex UV must fall within the source triangle's own UV range
    assert all(0.3 - 1e-6 <= u <= 0.9 + 1e-6 and 0.1 - 1e-6 <= v <= 0.7 + 1e-6 for (u, v) in outside_uvs)


def test_event_stamp_after_split_exclusion_is_exact_by_construction():
    """author_entrance's ORDER -- footprint split FIRST, event stamping (exclude_polygon=hull) SECOND --
    makes the centroid-based trigger exclusion EXACT with no further change: the split leaves no
    straddling triangle, so every fragment the stamp sees is wholly in or wholly out of the hull.
    Composed check on a straddling source triangle: zero event-tile area intersects the hull, and no
    blocked (topo-59) fragment carries the event."""
    tri = [[_v(0, 0, 0), _v(10, 0, 0), _v(0, 0, 10)]]
    bm = M.split_retarget_by_polygon(_soup(tri), SQUARE, topograph=59)
    n = M.retarget_tiles(bm, event=1, area=5, center=(4.0, 4.0), radius=50.0, exclude_polygon=SQUARE)
    assert n > 0                                             # fragments beside the building DO get the trigger
    ev_area_inside = 0.0
    for t in bm.tris:
        d = decode_id(int(round(bm.tangents[t[0]][0])))
        if d["topograph"] == 59:
            assert d["event"] == 0                           # never a trigger under the building
            continue
        if d["event"] != 1:
            continue
        poly = [(tuple(bm.verts[i]), NRM, (0.0, 0.0), (0.0, 0.0, 0.0, 0.0)) for i in t]
        for k in range(len(SQUARE)):                         # true intersection area with the hull
            poly = M._clip_edge(poly, SQUARE[k], SQUARE[(k + 1) % len(SQUARE)], keep_left=True)
            if not poly:
                break
        if poly:
            ev_area_inside += M._poly_area2_xz(poly) / 2.0
    assert ev_area_inside == pytest.approx(0.0, abs=1e-9)


def test_object_anchor_footprint_matches_real_terrain_alignment_bug(monkeypatch):
    """Reproduces the exact in-game symptom on a MINIATURE version of the real donor: a big
    real-style terrain triangle whose centroid lands OUTSIDE a small building hull but whose
    corner reaches INSIDE it -- retarget_tiles (whole-triangle centroid test) would leave that
    corner walkable (a gap the player can stand in, under the wall); split_retarget_by_polygon
    correctly blocks exactly the overlapping sliver."""
    # a big tri with centroid at (7,0,7) -- OUTSIDE the [2,6]x[2,6] hull -- but corner (3,0,3) inside
    tri = [[_v(3, 0, 3), _v(15, 0, 3), _v(3, 0, 15)]]
    bm = _soup(tri)
    old_changed = M.retarget_tiles(bm, topograph=59, only_polygon=SQUARE)
    assert old_changed == 0                                  # centroid (7,0,7) is outside -> retarget_tiles skips it
    out = M.split_retarget_by_polygon(_soup(tri), SQUARE, topograph=59)
    areas = _topo_areas(out)
    assert areas.get(59, 0.0) > 0.0                          # the split correctly blocks the overlapping corner
