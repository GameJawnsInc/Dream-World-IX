"""Exporter: write a .bgi from WORLD-space geometry, faithfully, for ANY floor count.

The exporter (`bgi.build`) is the inverse of the importer (`BgiWalkmesh.world_verts`): emit verts in
world coords with orgPos=0 and every floor.org=0, so the engine renders `world = vert + 0 + 0`
(WalkMesh.cs:53,141,227). These tests prove the round trip preserves world positions, triangle
topology, and the floor partition — across single-floor (hut) and multi-floor (the editor's 3-floor
walkmesh, which stores nonzero per-floor org tiling disjoint corner-origin vertex sets).
"""
from __future__ import annotations

from pathlib import Path

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
    for name in ("hut_ext.bgi.bytes", "editor_multifloor.bgi.bytes"):
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


def test_walkmesh_frame_world_emits_org0_vs_legacy_300(tmp_path):
    """[walkmesh] frame = "world" -> bgi.build (org=0); default -> legacy build_flat (org=300)."""
    from ff9mapkit.build import FieldProject, resolve_camera, resolve_walkmesh
    (tmp_path / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())
    (tmp_path / "wm.obj").write_text("v 0 0 0\nv 100 0 0\nv 100 0 100\nv 0 0 100\nf 1 2 3\nf 1 3 4\n")
    base = ('[field]\nid = 4003\nname = "X"\narea = 21\n\n'
            '[camera]\nborrow = "camera.bgx"\n\n[walkmesh]\nobj = "wm.obj"\n')

    (tmp_path / "world.field.toml").write_text(base + 'frame = "world"\n', encoding="utf-8")
    pw = FieldProject.load(tmp_path / "world.field.toml")
    ww = bgi.BgiWalkmesh.from_bytes(resolve_walkmesh(pw, resolve_camera(pw)))
    assert (ww.orgPos.x, ww.orgPos.y, ww.orgPos.z) == (0, 0, 0)

    (tmp_path / "legacy.field.toml").write_text(base, encoding="utf-8")
    pl = FieldProject.load(tmp_path / "legacy.field.toml")
    wl = bgi.BgiWalkmesh.from_bytes(resolve_walkmesh(pl, resolve_camera(pl)))
    assert (wl.orgPos.x, wl.orgPos.y, wl.orgPos.z) == (0, 0, 300)


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
