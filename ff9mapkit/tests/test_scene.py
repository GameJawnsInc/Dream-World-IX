"""Phase-2 validation: .bgx scene + .bgi walkmesh + camera-driven paint guide.

Golden masters: the GRGR reference camera, our HUT exterior walkmesh, and a real multi-floor
walkmesh (anms + normals + 3 floors) — the latter proving the .bgi serializer handles the full
format, not just the flat case. (All FF9-derived inputs are regenerated from the user's install by
``ff9mapkit extract-templates``; the scene-codec tests build kit-authored synthetic scenes.)
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit.scene import bgi, bgx, cam, guide

FIX = Path(__file__).parent / "fixtures"


# ----------------------------------------------------------------- .bgi walkmesh

def test_bgi_roundtrip_minimal_and_multifloor():
    for name in ("hut_ext.bgi.bytes", "multifloor.bgi.bytes"):
        raw = (FIX / name).read_bytes()
        assert bgi.BgiWalkmesh.from_bytes(raw).to_bytes() == raw, name


def test_build_flat_reproduces_hut_walkmesh_byte_exact():
    raw = (FIX / "hut_ext.bgi.bytes").read_bytes()
    m = bgi.BgiWalkmesh.from_bytes(raw)
    verts = [(v.x, v.y, v.z) for v in m.verts]
    faces = [tuple(t.vtx) for t in m.tris]
    assert bgi.build_flat(verts, faces).to_bytes() == raw


# --- the placement-query cache + bucket grid (a pure SPEED change: must stay bit-identical) ---

def _scan_on_walkmesh(m, x, z):
    """The pre-cache `point_on_walkmesh`: scan EVERY triangle, first match wins."""
    wv, fo = m.world_verts(), {ti: fi for fi, fl in enumerate(m.floors) for ti in fl.tri_ndx_list}
    for ti, t in enumerate(m.tris):
        if bgi._pt_in_tri_xz(x, z, wv[t.vtx[0]], wv[t.vtx[1]], wv[t.vtx[2]]):
            return fo.get(ti, t.floor_ndx)
    return None


def _scan_boundary(m, x, z):
    """The pre-cache `distance_to_boundary`: scan every triangle, min over the floor's wall edges."""
    floor = _scan_on_walkmesh(m, x, z)
    if floor is None:
        return None
    wv, fo = m.world_verts(), {ti: fi for fi, fl in enumerate(m.floors) for ti in fl.tri_ndx_list}
    best = None
    for ti, t in enumerate(m.tris):
        if fo.get(ti, t.floor_ndx) != floor:
            continue
        for k in range(3):
            if t.nbr[k] >= 0:
                continue
            i, j = bgi.SLOT_PAIRS[k]
            d = bgi._pt_seg_dist_xz(x, z, wv[t.vtx[i]], wv[t.vtx[j]])
            if best is None or d < best:
                best = d
    return best


def _probe_lattice(m, n=22):
    """A lattice over the mesh bbox grown 15% (so probes fall OFF the mesh and outside the grid
    entirely), plus every world vertex and triangle centroid -- the exact-boundary cases."""
    wv = m.world_verts()
    xs, zs = [v[0] for v in wv], [v[2] for v in wv]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    px, pz = (x1 - x0) * 0.15 + 1, (z1 - z0) * 0.15 + 1
    x0, x1, z0, z1 = x0 - px, x1 + px, z0 - pz, z1 + pz
    pts = [(round(x0 + (x1 - x0) * i / (n - 1)), round(z0 + (z1 - z0) * j / (n - 1)))
           for i in range(n) for j in range(n)]
    pts += [(v[0], v[2]) for v in wv]
    pts += [(round(sum(wv[i][0] for i in t.vtx) / 3), round(sum(wv[i][2] for i in t.vtx) / 3))
            for t in m.tris]
    return pts


def test_placement_queries_match_the_full_scan_bit_for_bit():
    """The bucket grid + derived-geometry cache are an optimisation ONLY: every placement query must
    return exactly what scanning every triangle returned (same floor, same float, same None)."""
    for name in ("hut_ext.bgi.bytes", "multifloor.bgi.bytes"):
        m = bgi.BgiWalkmesh.from_bytes((FIX / name).read_bytes())
        for (x, z) in _probe_lattice(m):
            assert m.point_on_walkmesh(x, z) == _scan_on_walkmesh(m, x, z), (name, x, z)
            d, ref = m.distance_to_boundary(x, z), _scan_boundary(m, x, z)
            assert d == ref or (d is None and ref is None), (name, x, z, d, ref)


def test_cached_geometry_survives_a_neighbor_rebuild():
    """`rebuild_neighbors`/`apply_seams` move nbr+edgeClone -- which the WALL cache is derived from
    and the structural signature cannot see -- so both must drop the cache."""
    m = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    pts = _probe_lattice(m, n=8)
    for (x, z) in pts:                                    # warm every cache
        m.distance_to_boundary(x, z)
    seams = m.extract_seams()
    m.rebuild_neighbors()                                 # drops the cross-floor seams -> more walls
    for (x, z) in pts:
        assert m.distance_to_boundary(x, z) == _scan_boundary(m, x, z), (x, z)
    m.apply_seams(seams)                                  # links them back -> fewer walls again
    for (x, z) in pts:
        assert m.distance_to_boundary(x, z) == _scan_boundary(m, x, z), (x, z)


def test_world_verts_and_vert_floor_map_stay_caller_owned():
    """Both are cached internally but must still hand back a FRESH object each call -- callers have
    always been free to keep/mutate the result, and sharing the cache would corrupt the mesh."""
    m = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    a, b = m.world_verts(), m.world_verts()
    assert a == b and a is not b
    a[0] = (12345, 6789, 1011)
    assert m.world_verts()[0] == b[0]                     # the mesh is unharmed
    va, vb = m.vert_floor_map(), m.vert_floor_map()
    assert va == vb and va is not vb
    va[0] = 999
    assert m.vert_floor_map()[0] == vb[0]


def test_invalidate_cache_picks_up_an_in_place_vertex_edit():
    """The signature only sees section COUNTS + orgPos; editing a vertex in place is the documented
    `invalidate_cache()` case."""
    m = bgi.BgiWalkmesh.from_bytes((FIX / "hut_ext.bgi.bytes").read_bytes())
    before = m.world_verts()[0]
    m.verts[0].x += 500
    m.invalidate_cache()
    assert m.world_verts()[0][0] == before[0] + 500
    assert m.point_on_walkmesh(0, 0) == _scan_on_walkmesh(m, 0, 0)


def test_quad_reproduces_hut_walkmesh_and_links():
    raw = (FIX / "hut_ext.bgi.bytes").read_bytes()
    q = bgi.quad([(-1069, -85), (1069, -85), (1069, -2267), (-1069, -2267)])
    assert q.to_bytes() == raw
    # neighbor + edgeClone links match the known-good values
    assert q.tris[0].nbr == [1, -1, -1]
    assert q.tris[1].nbr == [-1, 0, -1]
    assert [e.clone for e in q.edges] == [1, -1, -1, -1, 0, -1]


# ----------------------------------------------------------------- .bgx scene

def _semantic(scene: bgx.BgxScene):
    ov = [(o.image, o.position, o.size, o.shader, o.camera_id, o.viewport_id) for o in scene.overlays]
    cams = [(c.proj, tuple(c.centerOffset), tuple(c.t), tuple(c.range), c.depthOffset,
             tuple(c.viewport), tuple(tuple(r) for r in c.r)) for c in scene.cameras]
    return ov, cams


def _synthetic_scene():
    """A kit-authored scene: a real camera (regenerated from the user's install, never shipped) plus
    OUR overlays. Exercises the overlay codec without redistributing a ripped game scene."""
    camera = bgx.BgxScene.from_file(FIX / "grgr.bgx").cameras[0]
    overlays = [
        bgx.Overlay(image="back.png", position=(0, 0, 4000), size=(384, 314)),
        bgx.Overlay(image="floor.png", position=(0, 165, 3000), size=(384, 283)),
        bgx.Overlay(image="front.png", position=(0, 385, 8), size=(384, 63),
                    shader="PSX/FieldMap_Abr_1"),
    ]
    return camera, overlays


def test_bgx_parse_camera():
    s = bgx.BgxScene.from_file(FIX / "grgr.bgx")
    assert len(s.cameras) == 1
    assert s.cameras[0].proj == 497
    assert s.cameras[0].t == [0, -248, 5018]


def test_bgx_overlay_codec_roundtrip():
    camera, overlays = _synthetic_scene()
    s = bgx.BgxScene.parse(bgx.build(camera, overlays, header_comment="synthetic"))
    assert len(s.overlays) == 3 and len(s.cameras) == 1
    assert s.overlays[0].image == "back.png" and s.overlays[0].position == (0, 0, 4000)
    assert s.overlays[2].shader == "PSX/FieldMap_Abr_1"          # blend overlay preserved
    assert _semantic(s) == _semantic(bgx.BgxScene.parse(s.to_text()))   # semantic round-trip


def test_bgx_build_reproduces_scene():
    camera, overlays = _synthetic_scene()
    s = bgx.BgxScene.parse(bgx.build(camera, overlays))
    built = bgx.build(s.cameras[0], s.overlays, header_comment="rebuild")
    assert _semantic(bgx.BgxScene.parse(built)) == _semantic(s)


# ----------------------------------------------------------------- camera + guide

def test_camera_regen_faithful():
    c = bgx.BgxScene.from_file(FIX / "grgr.bgx").cameras[0]
    d = cam.decompose(c)
    r2, t2 = cam.synth_r_t(d["C"], d["R_ortho"], c.proj, k=d["k"])
    dr = max(abs(r2[i][j] - c.r[i][j]) for i in range(3) for j in range(3))
    dt = max(abs(t2[i] - c.t[i]) for i in range(3))
    assert dr <= 1 and dt <= 1


def test_guide_floor_lands_on_requested_canvas_rows():
    g = guide.make_camera(48.0, 4500, fov_x_deg=42.2)
    fr = guide.frame_floor(g, back_canvas_y=205, front_canvas_y=432)
    # back corners ~ y=205, front corners ~ y=432 (calibrated map)
    assert abs(fr.corners_canvas[0][1] - 205) < 1.0
    assert abs(fr.corners_canvas[2][1] - 432) < 1.0
    # the framed corners build a valid 2-triangle quad walkmesh
    wm = bgi.quad(guide.walkmesh_corners(fr))
    assert len(wm.tris) == 2
    assert wm.to_bytes()[:4] == bytes.fromhex("addedcac")  # magic 0xACDCDEAD


def test_bgx_build_multi_camera():
    """bgx.build accepts N cameras (multi-camera field) -> N CAMERA blocks; single Cam unchanged."""
    from ff9mapkit.scene import bgx, guide
    c0 = guide.make_camera(48, 4500, fov_x_deg=42.2)
    c1 = guide.make_camera(30, 4500, fov_x_deg=42.2)
    ov = [bgx.Overlay(image="a.png", position=(0, 0, 4000), size=(384, 448), camera_id=0),
          bgx.Overlay(image="b.png", position=(0, 0, 4000), size=(384, 448), camera_id=1)]
    assert bgx.build(c0, ov) == bgx.build([c0], ov)              # single == list-of-one (back-compat)
    sc = bgx.BgxScene.parse(bgx.build([c0, c1], ov))
    assert len(sc.cameras) == 2
    assert [o.camera_id for o in sc.overlays] == [0, 1]          # overlays keep their camera
