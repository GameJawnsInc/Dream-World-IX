"""Phase-2 validation: .bgx scene + .bgi walkmesh + camera-driven paint guide.

Golden masters: the GRGR reference scene, our HUT exterior scene/walkmesh, and the editor's
multi-floor walkmesh (anms + normals + 3 floors) — the latter proving the .bgi serializer
handles the full format, not just the flat case.
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit.scene import bgi, bgx, cam, guide

FIX = Path(__file__).parent / "fixtures"


# ----------------------------------------------------------------- .bgi walkmesh

def test_bgi_roundtrip_minimal_and_multifloor():
    for name in ("hut_ext.bgi.bytes", "editor_multifloor.bgi.bytes"):
        raw = (FIX / name).read_bytes()
        assert bgi.BgiWalkmesh.from_bytes(raw).to_bytes() == raw, name


def test_build_flat_reproduces_hut_walkmesh_byte_exact():
    raw = (FIX / "hut_ext.bgi.bytes").read_bytes()
    m = bgi.BgiWalkmesh.from_bytes(raw)
    verts = [(v.x, v.y, v.z) for v in m.verts]
    faces = [tuple(t.vtx) for t in m.tris]
    assert bgi.build_flat(verts, faces).to_bytes() == raw


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


def test_bgx_parse_grgr():
    s = bgx.BgxScene.from_file(FIX / "grgr.bgx")
    assert len(s.overlays) == 7
    assert len(s.cameras) == 1
    assert s.overlays[0].image == "FBG_N21_GRGR_MAP420_GR_CEN_0_0.png"
    assert s.cameras[0].proj == 497
    assert s.cameras[0].t == [0, -248, 5018]


def test_bgx_semantic_roundtrip():
    for name in ("grgr.bgx", "hut_ext.bgx"):
        orig = (FIX / name).read_text(encoding="utf-8", errors="replace")
        s = bgx.BgxScene.parse(orig)
        rt = bgx.BgxScene.parse(s.to_text())
        assert _semantic(s) == _semantic(rt), name


def test_bgx_build_reproduces_hut_scene():
    s = bgx.BgxScene.from_file(FIX / "hut_ext.bgx")
    built = bgx.build(s.cameras[0], s.overlays, header_comment="Vivi's Return (exterior)")
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
