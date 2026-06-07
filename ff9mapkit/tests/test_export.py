"""Exporter: write a .bgi from WORLD-space geometry, faithfully, for ANY floor count.

The exporter (`bgi.build`) is the inverse of the importer (`BgiWalkmesh.world_verts`): emit verts in
world coords with orgPos=0 and every floor.org=0, so the engine renders `world = vert + 0 + 0`
(WalkMesh.cs:53,141,227). These tests prove the round trip preserves world positions, triangle
topology, and the floor partition — across single-floor (hut) and multi-floor (a real 3-floor
walkmesh, which stores nonzero per-floor org tiling disjoint corner-origin vertex sets).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit.scene import bgi

FIX = Path(__file__).parent / "fixtures"


def _partition(wm):
    """The floor partition as a set of frozensets of triangle indices (order-independent)."""
    return frozenset(frozenset(fl.tri_ndx_list) for fl in wm.floors)


def test_build_flat_delegates_byte_identical_to_legacy():
    """build(org=header_vec) with one floor == the historical build_flat output, byte for byte."""
    raw = (FIX / "hut_ext.bgi.bytes").read_bytes()
    src = bgi.BgiWalkmesh.from_bytes(raw)
    verts = [(v.x, v.y, v.z) for v in src.verts]
    faces = [tuple(t.vtx) for t in src.tris]
    assert bgi.build_flat(verts, faces).to_bytes() == raw
    assert bgi.build(verts, faces, org=(0, 0, 300), header_min=(0, 0, 300),
                     header_max=(0, 0, 300), char=(0, 0, 300)).to_bytes() == raw


def test_export_roundtrips_world_positions_and_floors():
    """import (corner-origin + floor.org -> world) -> export (world, org=0) -> re-import: identical
    world vertex positions, identical triangle topology, identical floor partition. 1 and 3 floors."""
    for name in ("hut_ext.bgi.bytes", "multifloor.bgi.bytes"):
        src = bgi.BgiWalkmesh.from_bytes((FIX / name).read_bytes())
        wv = src.world_verts()                                   # importer
        faces = [tuple(t.vtx) for t in src.tris]
        floor_ids = [t.floor_ndx for t in src.tris]              # per-face floor
        out = bgi.build(wv, faces, floor_ids=floor_ids)          # exporter (org=0, floor.org=0)

        # the exporter emits a clean world frame, regardless of the source's tiling convention
        assert tuple(out.orgPos.__dict__.values()) == (0, 0, 0)
        assert all((fl.org.x, fl.org.y, fl.org.z) == (0, 0, 0) for fl in out.floors)

        rt = bgi.BgiWalkmesh.from_bytes(out.to_bytes())          # round-trips through bytes cleanly
        assert rt.to_bytes() == out.to_bytes()
        rwv = rt.world_verts()
        assert len(rwv) == len(wv)
        assert all(tuple(a) == tuple(b) for a, b in zip(rwv, wv))   # EXACT: org=0 => world == stored
        assert [tuple(t.vtx) for t in rt.tris] == faces            # topology preserved
        assert len(rt.floors) == len(src.floors)                   # same floor count
        assert _partition(rt) == _partition(src)                   # same triangle grouping


def test_build_multifloor_sets_per_tri_floor_and_groups():
    """Distinct face floor_ids -> one BGI floor each, tris grouped, floor_ndx set per triangle."""
    verts = [(0, 0, 0), (100, 0, 0), (100, 0, 100), (0, 0, 100),    # floor 0 (low)
             (0, 500, 200), (100, 500, 200), (50, 500, 300)]        # floor 1 (raised)
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6)]
    m = bgi.build(verts, faces, floor_ids=[0, 0, 1])
    assert len(m.floors) == 2
    assert [t.floor_ndx for t in m.tris] == [0, 0, 1]
    assert set(m.floors[0].tri_ndx_list) == {0, 1}
    assert set(m.floors[1].tri_ndx_list) == {2}
    # header bbox spans both floors; charPos is the bbox centre
    assert (m.minPos.y, m.maxPos.y) == (0, 500)


def test_build_remaps_noncontiguous_floor_ids():
    """Arbitrary floor ids (e.g. 5, 9) collapse to contiguous 0..N-1 in first-seen order."""
    verts = [(0, 0, 0), (10, 0, 0), (10, 0, 10), (0, 0, 10)]
    m = bgi.build(verts, [(0, 1, 2), (0, 2, 3)], floor_ids=[9, 5])
    assert [f.ndx for f in m.floors] == [0, 1]
    assert [t.floor_ndx for t in m.tris] == [0, 1]


def test_build_rejects_floor_ids_length_mismatch():
    verts = [(0, 0, 0), (10, 0, 0), (10, 0, 10)]
    try:
        bgi.build(verts, [(0, 1, 2)], floor_ids=[0, 0])
    except ValueError as e:
        assert "floor_ids" in str(e)
    else:
        raise AssertionError("expected ValueError on floor_ids length mismatch")


def test_load_obj_floors_groups_by_object():
    """Each `o`/`g` object in the .obj becomes a floor; a repeated name reuses its floor."""
    obj = (
        "o ground\n"
        "v 0 0 0\nv 100 0 0\nv 100 0 100\nv 0 0 100\n"
        "f 1 2 3\nf 1 3 4\n"
        "o ledge\n"
        "v 0 500 200\nv 100 500 200\nv 50 500 300\n"
        "f 5 6 7\n"
    )
    import tempfile
    import os
    fd, path = tempfile.mkstemp(suffix=".obj")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(obj)
        verts, faces, floor_ids = bgi.load_obj_floors(path)
        assert len(verts) == 7
        assert faces == [(0, 1, 2), (0, 2, 3), (4, 5, 6)]
        assert floor_ids == [0, 0, 1]
        # obj_to_bgi picks the multi-floor world builder when there's >1 object
        m = bgi.BgiWalkmesh.from_bytes(bgi.obj_to_bgi(path))
        assert len(m.floors) == 2
        assert (m.orgPos.x, m.orgPos.y, m.orgPos.z) == (0, 0, 0)
    finally:
        os.unlink(path)


def test_obj_reexport_loses_cross_floor_connectivity(tmp_path):
    """KNOWN LIMITATION (guarded here so it can't silently regress): the .bgi CODEC is lossless, but
    the obj INTERMEDIATE is not -- it carries geometry, not the navmesh ADJACENCY graph. obj->build
    rebuilds neighbor links by shared vertex INDEX, so a multi-floor mesh (disjoint vertex sets per
    floor) loses cross-floor links and floors strand. Forks must ship the original via [walkmesh] bgi;
    authoring/reshaping multi-floor geometry needs the seam sidecar (docs/WALKMESH_EDITING.md)."""
    from ff9mapkit import extract
    src = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    assert src.reachable_floors() == src.all_floors()              # codec lossless: every floor connected
    obj = tmp_path / "wm.obj"
    obj.write_text(extract._world_walkmesh_obj_text(src), encoding="utf-8")
    verts, faces, fids = bgi.load_obj_floors(str(obj))
    rex = bgi.build(verts, faces, floor_ids=fids)
    assert rex.all_floors() == src.all_floors()                   # geometry + partition survive
    assert rex.reachable_floors() < src.all_floors()              # but cross-floor connectivity is LOST


def _multifloor_scene_toml(tmp_path, walkmesh_block):
    from ff9mapkit import extract
    src = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    (tmp_path / "wm.obj").write_text(extract._world_walkmesh_obj_text(src), encoding="utf-8")
    v, f, fid = bgi.load_obj_floors(str(tmp_path / "wm.obj"))
    (tmp_path / "wm.bgi").write_bytes(bgi.build(v, f, floor_ids=fid).to_bytes())   # stranded re-export
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "X"\narea = 21\n\n[camera]\nborrow = "camera.bgx"\n\n'
        + walkmesh_block, encoding="utf-8")
    from ff9mapkit.build import FieldProject, build_mod
    return build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")


def test_build_warns_on_stranded_floors_for_obj(tmp_path):
    """build() warns when a (re)BUILT multi-floor walkmesh strands floors -- the obj-reexport footgun
    (the in-game GRGR symptom), surfaced at build time."""
    info = _multifloor_scene_toml(tmp_path, '[walkmesh]\nobj = "wm.obj"\nframe = "world"\n')
    assert any("not walk-reachable" in w for w in info["warnings"])


def test_build_skips_reachability_for_verbatim_bgi(tmp_path):
    """A verbatim [walkmesh] bgi is authoritative and SKIPPED -- avoids crying wolf on the real fields
    that legitimately reach some floors by script, not on foot (e.g. UDFT: 9 of 23 walk-reachable)."""
    info = _multifloor_scene_toml(tmp_path, '[walkmesh]\nbgi = "wm.bgi"\n')
    assert not any("not walk-reachable" in w for w in info["warnings"])


# ---- v2: seam sidecar (reshape a multi-floor walkmesh while keeping connectivity) ----

def test_seam_extract_apply_reconciles_multifloor():
    """v2 reconcile: extract_seams (from the original) + apply_seams (onto a geometry-only obj round-
    trip) reproduces the original cross-floor link set + full reachability. The smoke test, as a unit."""
    src = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    seams = src.extract_seams()
    assert seams                                                   # multi-floor has cross-floor seams
    wv = src.world_verts()
    geom = bgi.build([(int(x), int(y), int(z)) for (x, y, z) in wv],
                     [tuple(t.vtx) for t in src.tris], floor_ids=[t.floor_ndx for t in src.tris])
    assert geom.reachable_floors() < src.all_floors()             # geometry-only: floors stranded
    linked, missing, _ = geom.apply_seams(seams)
    assert missing == 0 and linked == len(seams)
    assert geom.reachable_floors() == src.all_floors()            # reconciled: connectivity restored


def test_build_obj_with_links_reconciles(tmp_path):
    """[walkmesh] obj + links rebuilds geometry AND reconciles cross-floor seams -> no stranded-floor
    warning, fully-connected built .bgi."""
    from ff9mapkit import extract
    from ff9mapkit.build import FieldProject, build_mod
    from ff9mapkit.config import ModLayout
    src = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    (tmp_path / "wm.obj").write_text(extract._world_walkmesh_obj_text(src), encoding="utf-8")
    extract._write_links_toml(src, tmp_path / "wm.links.toml")
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "X"\narea = 21\n\n[camera]\nborrow = "camera.bgx"\n\n'
        '[walkmesh]\nobj = "wm.obj"\nlinks = "wm.links.toml"\nframe = "world"\n', encoding="utf-8")
    info = build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")
    assert not any("not walk-reachable" in w for w in info["warnings"])
    fm = ModLayout(tmp_path / "mod").fieldmap_dir(info["fields"][0])
    built = bgi.BgiWalkmesh.from_bytes((fm / f"{info['fields'][0]}.bgi.bytes").read_bytes())
    assert built.reachable_floors() == built.all_floors()         # fully connected after reconcile


def test_build_obj_links_warns_on_broken_seam(tmp_path):
    """A seam whose connecting edge was moved/deleted warns (no silent mis-link)."""
    from ff9mapkit import extract
    from ff9mapkit.build import FieldProject, build_mod
    src = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    (tmp_path / "wm.obj").write_text(extract._world_walkmesh_obj_text(src), encoding="utf-8")
    extract._write_links_toml(src, tmp_path / "wm.links.toml")
    with open(tmp_path / "wm.links.toml", "a", encoding="utf-8") as fh:   # an unmatchable seam
        fh.write("\n[[seam]]\na_floor = 0\na_edge = [[99999, 0, 0], [99998, 0, 0]]\n"
                 "b_floor = 1\nb_edge = [[99999, 0, 0], [99998, 0, 0]]\n")
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "X"\narea = 21\n\n[camera]\nborrow = "camera.bgx"\n\n'
        '[walkmesh]\nobj = "wm.obj"\nlinks = "wm.links.toml"\nframe = "world"\n', encoding="utf-8")
    info = build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")
    assert any("could" in w and "seam" in w for w in info["warnings"])


def test_walkmesh_bgi_mode_ships_verbatim(tmp_path):
    """[walkmesh] bgi = "<file>" ships the .bgi byte-for-byte (preserves real-field connectivity),
    unlike obj->build which rebuilds neighbor links."""
    from ff9mapkit.build import FieldProject, resolve_camera, resolve_walkmesh
    raw = (FIX / "multifloor.bgi.bytes").read_bytes()
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "walkmesh.bgi").write_bytes(raw)
    (tmp_path / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "X"\narea = 21\n\n[camera]\nborrow = "camera.bgx"\n\n'
        '[walkmesh]\nbgi = "walkmesh.bgi"\n', encoding="utf-8")
    proj = FieldProject.load(tmp_path / "f.field.toml")
    assert resolve_walkmesh(proj, resolve_camera(proj)) == raw    # verbatim, multi-floor + links intact


def test_editable_world_obj_roundtrips_multifloor(tmp_path):
    """write_editable_project's walkmesh re-export (.bgi -> world .obj -> build) preserves world
    positions + floor partition. Covers the offline core of `import --editable` (no game data)."""
    from ff9mapkit import extract
    src = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    obj = tmp_path / "wm.obj"
    obj.write_text(extract._world_walkmesh_obj_text(src), encoding="utf-8")
    verts, faces, floor_ids = bgi.load_obj_floors(str(obj))
    out = bgi.build(verts, faces, floor_ids=floor_ids)
    assert len(out.floors) == len(src.floors)                 # floors preserved
    assert (out.orgPos.x, out.orgPos.y, out.orgPos.z) == (0, 0, 0)
    rt = bgi.BgiWalkmesh.from_bytes(out.to_bytes())
    assert all(tuple(a) == tuple(b) for a, b in zip(rt.world_verts(), src.world_verts()))
    assert _partition(rt) == _partition(src)


def test_walkmesh_always_world_frame_org0(tmp_path):
    """All authored walkmeshes build in TRUE world coords (org=0): the honest model (measured
    Session 18 -- no character offset, no +300). `frame`/`character_offset` are ignored for
    back-compat, so an obj with or without them resolves identically (org=0, verts verbatim)."""
    from ff9mapkit.build import FieldProject, resolve_camera, resolve_walkmesh
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "wm.obj").write_text("v 0 0 0\nv 100 0 0\nv 100 0 100\nv 0 0 100\nf 1 2 3\nf 1 3 4\n")
    base = ('[field]\nid = 4003\nname = "X"\narea = 21\n\n'
            '[camera]\nborrow = "camera.bgx"\n\n[walkmesh]\nobj = "wm.obj"\n')

    (tmp_path / "a.field.toml").write_text(base, encoding="utf-8")
    pa = FieldProject.load(tmp_path / "a.field.toml")
    wa = bgi.BgiWalkmesh.from_bytes(resolve_walkmesh(pa, resolve_camera(pa)))
    assert (wa.orgPos.x, wa.orgPos.y, wa.orgPos.z) == (0, 0, 0)
    assert sorted(round(v[2]) for v in wa.world_verts()) == [0, 0, 100, 100]   # verts verbatim

    # legacy keys (frame="world", character_offset) are accepted but change nothing
    (tmp_path / "b.field.toml").write_text(base + 'frame = "world"\ncharacter_offset = 298\n', encoding="utf-8")
    pb = FieldProject.load(tmp_path / "b.field.toml")
    wb = bgi.BgiWalkmesh.from_bytes(resolve_walkmesh(pb, resolve_camera(pb)))
    assert wb.to_bytes() == wa.to_bytes()


def test_load_obj_single_object_unchanged():
    """A single-object (or object-less) .obj still goes through the legacy flat path (header 300)."""
    import tempfile
    import os
    fd, path = tempfile.mkstemp(suffix=".obj")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write("v 0 0 0\nv 100 0 0\nv 100 0 100\nv 0 0 100\nf 1 2 3\nf 1 3 4\n")
        m = bgi.BgiWalkmesh.from_bytes(bgi.obj_to_bgi(path))
        assert len(m.floors) == 1
        assert (m.orgPos.x, m.orgPos.y, m.orgPos.z) == (0, 0, 300)   # legacy uniform header
    finally:
        os.unlink(path)


# ---- robustness: validation for user-edited / altered exports ----

def test_build_rejects_bad_geometry():
    """A mis-edited .obj fails LOUDLY at build (clear error), not with a cryptic crash."""
    with pytest.raises(ValueError, match="no geometry"):
        bgi.build([], [])
    with pytest.raises(ValueError, match="out of range"):
        bgi.build([(0, 0, 0), (10, 0, 0), (0, 0, 10)], [(0, 1, 5)])   # vertex 5 doesn't exist


def test_point_on_walkmesh_and_degenerate():
    wm = bgi.build([(-100, 0, -100), (100, 0, -100), (100, 0, 100), (-100, 0, 100)],
                   [(0, 1, 2), (0, 2, 3)])
    assert wm.point_on_walkmesh(0, 0) is not None        # inside the square
    assert wm.point_on_walkmesh(9999, 9999) is None      # far outside
    assert wm.degenerate_tris() == []
    deg = bgi.build([(0, 0, 0), (10, 0, 0), (20, 0, 0), (0, 0, 50)],   # tri 0 collinear in XZ
                    [(0, 1, 2), (0, 2, 3)])
    assert 0 in deg.degenerate_tris()


def _quad_scene_toml(npc_pos=None, spawn=None, extra=""):
    t = ('[field]\nid = 4003\nname = "X"\narea = 21\n\n[camera]\nborrow = "camera.bgx"\n\n'
         '[walkmesh]\nquad = [[-500, -500], [500, -500], [500, 500], [-500, 500]]\nframe = "world"\n\n')
    if spawn:
        t += f'[player]\nspawn = [{spawn[0]}, {spawn[1]}]\n\n'
    if npc_pos:
        t += f'[[npc]]\nname = "N"\npreset = "vivi"\npos = [{npc_pos[0]}, {npc_pos[1]}]\n\n'
    return t + extra


def test_build_warns_content_off_walkmesh(tmp_path):
    """The recurring in-game mistake (NPC/spawn off the walkable area) is now a build-time warning."""
    from ff9mapkit.build import FieldProject, build_mod
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(
        _quad_scene_toml(npc_pos=(9000, 9000), spawn=(0, 0)), encoding="utf-8")
    info = build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")
    assert any("off the walkmesh" in w for w in info["warnings"])       # NPC at (9000,9000) flagged
    assert not any("player spawn" in w for w in info["warnings"])       # spawn (0,0) is ON the mesh


def test_build_no_content_warning_when_on_walkmesh(tmp_path):
    from ff9mapkit.build import FieldProject, build_mod
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(_quad_scene_toml(npc_pos=(100, 100)), encoding="utf-8")
    info = build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")
    assert not any("off the walkmesh" in w for w in info["warnings"])


# ---- borrow-fork content validation (the off-walkmesh guard, now universal) ----

def _borrow_toml(tmp_path, npc_pos, *, ref_line='[walkmesh]\nreference = "wm.bgi"\n\n', wm_name="wm.bgi"):
    (tmp_path / wm_name).write_bytes(bgi.build(
        [(-500, 0, -500), (500, 0, -500), (500, 0, 500), (-500, 0, 500)],
        [(0, 1, 2), (0, 2, 3)]).to_bytes())                      # square reference walkmesh
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "X"\narea = 21\nborrow_bg = "GRGR_MAP420_GR_CEN_0"\n\n'
        '[camera]\nborrow = "camera.bgx"\n\n' + ref_line +
        f'[[npc]]\nname = "N"\npreset = "vivi"\npos = [{npc_pos[0]}, {npc_pos[1]}]\n', encoding="utf-8")
    from ff9mapkit.build import FieldProject, build_mod
    return build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")


def test_borrow_fork_warns_content_off_walkmesh(tmp_path):
    """BG-borrow forks (the common case) now also get the off-walkmesh warning, via [walkmesh] reference."""
    assert any("off the walkmesh" in w for w in _borrow_toml(tmp_path, (9000, 9000))["warnings"])


def test_borrow_fork_no_warning_on_walkmesh(tmp_path):
    assert not any("off the walkmesh" in w for w in _borrow_toml(tmp_path, (0, 0))["warnings"])


def test_borrow_fork_validates_via_sibling_walkmesh(tmp_path):
    """Without [walkmesh] reference, a borrow fork still validates against the sibling walkmesh.bgi the
    importer writes next to the field.toml (zero-config convention)."""
    info = _borrow_toml(tmp_path, (9000, 9000), ref_line="", wm_name="walkmesh.bgi")
    assert any("off the walkmesh" in w for w in info["warnings"])


# ---- art/layer sanity (a repaint at the wrong aspect would stretch in-game) ----

def _fake_png(path, w, h):
    import struct as _s
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + _s.pack(">I", 13) + b"IHDR" + _s.pack(">II", w, h)
                     + b"\x08\x06\x00\x00\x00" + b"\x00" * 8)   # valid 24-byte IHDR header is enough


def _layer_scene(tmp_path, png_w, png_h):
    _fake_png(tmp_path / "back.png", png_w, png_h)
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "X"\narea = 21\n\n[camera]\nborrow = "camera.bgx"\n\n'
        '[walkmesh]\nquad = [[-100, -100], [100, -100], [100, 100], [-100, 100]]\nframe = "world"\n\n'
        '[[layers]]\nimage = "back.png"\nz = 4000\n', encoding="utf-8")
    from ff9mapkit.build import FieldProject, build_mod
    return build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")


def test_build_warns_layer_aspect_mismatch(tmp_path):
    """A repainted layer whose PNG aspect != its size quad is flagged (it'd stretch in-game)."""
    assert any("stretched" in w for w in _layer_scene(tmp_path, 1000, 200)["warnings"])


def test_build_no_layer_warning_correct_aspect(tmp_path):
    """A layer at size x4 (the convention) matches the canvas aspect -> no warning."""
    from ff9mapkit.scene import cam
    rw, rh = cam.parse_bgx_cameras(str(FIX / "grgr.bgx"))[0].range
    assert not any("stretched" in w for w in _layer_scene(tmp_path, rw * 4, rh * 4)["warnings"])


# ---- collision-radius edge proximity (content on-mesh but too close to a wall to reach) ----

def test_distance_to_boundary():
    wm = bgi.build([(-500, 0, -500), (500, 0, -500), (500, 0, 500), (-500, 0, 500)],
                   [(0, 1, 2), (0, 2, 3)])
    assert abs(wm.distance_to_boundary(0, 0) - 500) < 1e-6      # centre: 500u to each wall
    assert abs(wm.distance_to_boundary(470, 0) - 30) < 1e-6     # near the +x wall
    assert wm.distance_to_boundary(9999, 9999) is None          # off the walkmesh


def test_build_warns_npc_within_collision_radius_of_edge(tmp_path):
    """An NPC on the mesh but within the ~48u player collision radius of a wall is flagged advisory --
    the player's centre can't reach it. (470,0) is 30u from the +x edge of the 1000u quad."""
    from ff9mapkit.build import FieldProject, build_mod
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(_quad_scene_toml(npc_pos=(470, 0)), encoding="utf-8")
    info = build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")
    assert any("collision radius" in w for w in info["warnings"])
    assert not any("off the walkmesh" in w for w in info["warnings"])    # it IS on the mesh


def test_build_no_near_edge_warning_well_inside(tmp_path):
    from ff9mapkit.build import FieldProject, build_mod
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(_quad_scene_toml(npc_pos=(100, 100)), encoding="utf-8")
    info = build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")
    assert not any("collision radius" in w for w in info["warnings"])


def test_build_gateway_zone_exempt_from_near_edge(tmp_path):
    """An exit zone is edge-placed BY DESIGN (a door), so the near-edge advisory must NOT fire on it."""
    from ff9mapkit.build import FieldProject, build_mod
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    gw = ('[[gateway]]\nto = 100\nentrance = 0\n'
          'zone = [[440, -30], [500, -30], [500, 30], [440, 30]]\n')   # centre ~ (470,0), 30u from wall
    (tmp_path / "f.field.toml").write_text(_quad_scene_toml(extra=gw), encoding="utf-8")
    info = build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")
    assert not any("collision radius" in w for w in info["warnings"])   # gateways exempt


# ---- walkmesh verify (the standalone check, no build) ----

def test_verify_walkmesh_clean_custom_scene(tmp_path):
    from ff9mapkit.build import FieldProject, verify_walkmesh
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(
        _quad_scene_toml(npc_pos=(100, 100), spawn=(0, 0)), encoding="utf-8")
    rep = verify_walkmesh(FieldProject.load(tmp_path / "f.field.toml"))
    assert rep["source"] == "custom scene"
    assert rep["floors"] == [0] and rep["stranded"] == [] and rep["warnings"] == []


def test_verify_walkmesh_flags_off_mesh(tmp_path):
    from ff9mapkit.build import FieldProject, verify_walkmesh
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(_quad_scene_toml(npc_pos=(9000, 9000)), encoding="utf-8")
    rep = verify_walkmesh(FieldProject.load(tmp_path / "f.field.toml"))
    assert any("off the walkmesh" in w for w in rep["warnings"])
