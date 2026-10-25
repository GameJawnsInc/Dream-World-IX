"""A multi-block carry across the world's x seam (overworld editor C23).

The world is an x-torus: a target rect at column 23 two blocks wide fills columns 23 and 0. ``transplant_region`` keeps
its target keys UNWRAPPED inside (column 24 is column 0's east neighbour, so the region's own adjacency holds) and gives
a column its wrapped label only where it meets a file. These pin each of those points, and that the seam moves no byte:
the same carry off the seam deploys the same meshes. Hermetic: the stock reads are faked, the install is a tmp dir.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ff9mapkit.world import mesh as M, transplant as TR, transplantedit as TE
from tests.test_world_texgates import _fake_world, _lawful_donor_terrain, _quad_tris

#: donor (1,1)+2x1: land in BOTH cells (so the carried land straddles the seam), a full sea sheet under each
DONOR = {(1, 1, "terrain"): _lawful_donor_terrain(104.0, 124.0, -104.0, -88.0),
         (1, 1, "sea4"): _quad_tris(64.0, 128.0, -128.0, -64.0, idall=232.0),
         (2, 1, "terrain"): _lawful_donor_terrain(128.0, 148.0, -104.0, -88.0),
         (2, 1, "sea4"): _quad_tris(128.0, 192.0, -128.0, -64.0, idall=232.0)}


def _carry(monkeypatch, tmp_path, cell, *, world=None, asked=None):
    """Carry the donor onto ``cell`` (2x1) for real into a tmp install, the writers recording what they were given."""
    fake = _fake_world(world or DONOR)

    def world_tris(bx, by, part, **k):
        if asked is not None:
            asked.append((bx, by))
        return fake(bx, by, part, **k)
    monkeypatch.setattr(TR, "world_tris", world_tris)
    wrote = {"meshes": [], "sidecars": []}

    def deploy_override(bm, **k):
        wrote["meshes"].append((bm.x, bm.y, k.get("part"), bm.name, bm))
        return f"{bm.name}.ff9mesh"

    def deploy_donor_sidecar(dx, dy, **k):
        wrote["sidecars"].append((k["x"], k["y"], dx, dy))
        return f"Block[{k['x']}][{k['y']}] Donor.txt"
    monkeypatch.setattr(M, "deploy_override", deploy_override)
    monkeypatch.setattr(M, "deploy_donor_sidecar", deploy_donor_sidecar)
    (tmp_path / "MOD").mkdir(exist_ok=True)
    s = TR.transplant_region("MOD", cell=cell, donor=(1, 1), size=(2, 1), shift=(0.0, 0.0), land_margin=0.0,
                             census_samples=8, skip_mirror=True, game=tmp_path)
    return s, wrote


def test_a_rect_carries_across_the_seam_under_wrapped_labels(monkeypatch, tmp_path):
    s, wrote = _carry(monkeypatch, tmp_path, (23, 2))
    assert s["clean"], [g for g in s["gates"] if not g["ok"]]
    assert {(x, y) for x, y, *_ in wrote["meshes"]} == {(23, 2), (0, 2)}        # column 24 is written as column 0
    assert all(name.startswith(f"Block[{x}][{y}] ") for x, y, _p, name, _bm in wrote["meshes"])
    assert {(x, y) for x, y, *_ in wrote["sidecars"]} == {(23, 2), (0, 2)}
    assert set(s["cells"]) == {"23,2", "0,2"}                                    # the report names the labels
    assert all(not g["gate"].startswith("effective-prefab[24") for g in s["gates"])


def test_the_seam_moves_no_byte(monkeypatch, tmp_path):
    """Block-local verts: the carry onto (23, 2) writes what the same carry onto (4, 2) writes, block for block."""
    seam = _carry(monkeypatch, tmp_path, (23, 2))[1]["meshes"]
    off = _carry(monkeypatch, tmp_path, (4, 2))[1]["meshes"]
    pairs = {(23, 2): (4, 2), (0, 2): (5, 2)}
    by = {(x, y, p): bm for x, y, p, _n, bm in off}
    assert len(seam) == len(off) and seam
    for x, y, p, _n, bm in seam:
        o = by[(*pairs[(x, y)], p)]
        assert bm.chan_arrays == o.chan_arrays and bm.tris == o.tris and bm.flat_index == o.flat_index, (x, y, p)


def test_the_target_is_read_at_its_labels_and_refused_there(monkeypatch, tmp_path):
    asked = []
    _carry(monkeypatch, tmp_path, (23, 2), asked=asked)
    assert (0, 2) in asked and not any(bx >= 24 for bx, _by in asked)         # the occupancy read asks the label
    real = {**DONOR, (0, 2, "terrain"): _quad_tris(0.0, 64.0, -192.0, -128.0)}  # stock land at the wrapped column
    with pytest.raises(ValueError, match=r"target cell \(0,2\) is a REAL world block"):
        _carry(monkeypatch, tmp_path, (23, 2), world=real)


def test_a_mod_deploy_at_the_wrapped_column_refuses(monkeypatch, tmp_path):
    d = tmp_path / "MOD" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r2"
    d.mkdir(parents=True)
    (d / "Block[0][2] Terrain.ff9mesh").write_bytes(b"ANOTHER DEPLOY")
    s, wrote = _carry(monkeypatch, tmp_path, (23, 2))
    g = next(g for g in s["gates"] if g["gate"] == "mod-overwrite")
    assert not g["ok"] and "(0,2)" in g["existing"] and not wrote["meshes"]


def test_rows_stay_edged_and_a_rect_cannot_lap_the_world(monkeypatch, tmp_path):
    monkeypatch.setattr(TR, "world_tris", _fake_world(DONOR))
    with pytest.raises(ValueError, match="out of the 24x20 overworld grid"):
        TR.transplant_region("MOD", cell=(23, 19), donor=(1, 1), size=(2, 2), dry_run=True, game=tmp_path)
    with pytest.raises(ValueError, match="out of the 24x20 overworld grid"):
        TR.transplant_region("MOD", cell=(24, 2), donor=(1, 1), size=(2, 1), dry_run=True, game=tmp_path)


def test_the_report_and_the_card_name_the_labels(tmp_path):
    from ff9mapkit.cli import _morph_report_json
    out = tmp_path / "v.json"
    args = SimpleNamespace(report_json=str(out), cell="23,1", size="2x3", rot=0, dry_run=True, disc=1)
    _morph_report_json(args, summary={"gates": [], "clean": True, "deployed": [], "shift": [0, 0], "rot": 0,
                                      "op": "transplant-region"})
    blocks = json.loads(out.read_text(encoding="utf-8"))["blocks"]
    assert blocks == [list(c) for c in TE.cells((23, 1), (2, 3))] == [[23, 1], [0, 1], [23, 2], [0, 2], [23, 3], [0, 3]]
    assert TE.anchor_for(3.0, -160.0, size=(2, 3)) == (23, 1)                   # a click just east of x = 0
    assert TE.anchor_for(1533.0, -160.0, size=(2, 3)) == (23, 1)                # ... and just west of it
    asked = []
    v = TE.preview((23, 1), land={(0, 2)}, occupied=lambda bs: asked.extend(bs) or {}, size=(2, 3))
    assert not v["ok"] and "1 of its 6 blocks are real land" in v["why"] and v["where"] == [(32.0, -160.0)]
    v = TE.preview((23, 1), land=set(), occupied=lambda bs: asked.extend(bs) or {(0, 3): ["W"]}, size=(2, 3))
    assert not v["ok"] and "already hold an edit in W" in v["why"] and (0, 1) in asked and (24, 1) not in asked
    assert TE.preview((23, 1), land=set(), occupied=lambda bs: {}, size=(2, 3))["ok"]
