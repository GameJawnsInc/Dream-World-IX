"""world-transplant: carry a complete real block (all sub-meshes) to a custom ocean cell with
0-mod-4 shift + 90-degree rotation, offline-gated (census + weld audit + land fit + tweak scope).

Hermetic: the geometry core (clip / rotate / weld audit), the orchestration (strip gathering,
coverage-feasible shift window, auto-fit, blanking, deploy/refuse) with ``world_tris`` stubbed,
and the two proven tweak classes (TileRetexture / PatchRecover exact-capture). One game-gated
test reproduces the in-game-proven donor (7,17) ROT-90 configuration ("it holds", 2026-07-08).
"""
from __future__ import annotations

import math

import pytest

from ff9mapkit.world import mesh as M, transplant as TR

NRM = (0.0, 1.0, 0.0)


def _v(x, y, z, uv=(0.5, 0.5), idall=12800.0, nrm=NRM):
    return ((float(x), float(y), float(z)), nrm, tuple(uv), (float(idall), 0.0, 0.0, 1.0))


def _quad(x0, x1, z0, z1, *, y=0.0, idall=12800.0, uv=(0.5, 0.5)):
    """Two UP-FACING tris covering [x0,x1] x [z0,z1] (world coords, z0 < z1 <= 0)."""
    a, b = _v(x0, y, z1, uv, idall), _v(x1, y, z1, uv, idall)
    c, d = _v(x1, y, z0, uv, idall), _v(x0, y, z0, uv, idall)
    return [[a, b, d], [b, c, d]]


def _soup(tris, name="Block[0][0] Terrain", cell=(0, 0)):
    return TR._soup_block_mesh(name, cell, tris, disc=1, lod="0_1")


# ---------------------------------------------------------------- weld audit

def test_weld_audit_zero_on_shared_and_far_verts():
    bm = _soup(_quad(0.0, 64.0, -64.0, 0.0))     # shared corners are IDENTICAL, others far
    assert M.weld_audit([bm]) == []
    assert M.weld_audit([("Terrain", bm)]) == []


def test_weld_audit_finds_near_miss_across_parts():
    t1 = [[_v(0, 0, 0), _v(10, 0, 0), _v(0, 0, -10)]]
    t2 = [[_v(0.01, 0, 0), _v(20, 0, 0), _v(0, 0, -20)]]          # 0.01u from t1's corner
    pairs = M.weld_audit([_soup(t1), _soup(t2, name="Block[0][0] Sea4")])
    assert pairs == [((0.0, 0.0, 0.0), (0.01, 0.0, 0.0))]


def test_weld_audit_tolerance_boundary():
    t1 = [[_v(0, 0, 0), _v(10, 0, 0), _v(0, 0, -10)]]
    t2 = [[_v(0.06, 0, 0), _v(20, 0, 0), _v(0, 0, -20)]]          # beyond the 0.05 tol
    assert M.weld_audit([_soup(t1), _soup(t2)]) == []
    assert len(M.weld_audit([_soup(t1), _soup(t2)], tol=0.1)) == 1


# ---------------------------------------------------------------- clip + rotation

def test_clip_poly_inside_passes_whole():
    poly = [_v(0, 0, 0), _v(4, 0, 0), _v(4, 0, -4), _v(0, 0, -4)]
    assert TR.clip_poly(poly, 0, 64.0, True) == poly


def test_clip_poly_lerps_cut_edge_exactly():
    poly = [_v(0, 0, 0, uv=(0.0, 0.0)), _v(8, 0, 0, uv=(1.0, 0.0)), _v(0, 0, -8, uv=(0.0, 1.0))]
    cut = TR.clip_poly(poly, 0, 4.0, True)
    assert [p[0] for p in cut] == [(0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (4.0, 0.0, -4.0), (0.0, 0.0, -8.0)]
    assert [p[2] for p in cut] == [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 1.0)]


def test_rot_xz_lattice_and_identity():
    assert TR._rot_xz(4.0, -8.0, 1) == (8.0, -60.0)
    corners = {(0.0, 0.0), (64.0, 0.0), (64.0, -64.0), (0.0, -64.0)}
    assert {TR._rot_xz(x, z, 1) for (x, z) in corners} == corners      # frame maps to itself
    x, z = 12.0, -40.0
    for n in range(4):
        x, z = TR._rot_xz(x, z, 1)
    assert (x, z) == (12.0, -40.0)                                     # 4 quarter-turns = identity
    rx, rz = TR._rot_xz(16.0, -4.0, 1)
    assert rx % 4.0 == 0.0 and rz % 4.0 == 0.0                         # lattice preserved


# ---------------------------------------------------------------- orchestration (stubbed blocks)

def _fake_world(blocks):
    """world_tris stub: blocks = {(bx, by, part): [tris]} in WORLD coords."""
    def fake(bx, by, part, **_k):
        return [list(t) for t in blocks.get((bx, by, part), [])]
    return fake


def _island_donor(land_x=(88.0, 104.0)):
    """Donor (1,1): a small terrain island + a full-cell sea4 (world frame x 64..128, z -128..-64)."""
    return {(1, 1, "terrain"): _quad(land_x[0], land_x[1], -104.0, -88.0),
            (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0)}


def test_transplant_basic_clean(monkeypatch):
    monkeypatch.setattr(TR, "world_tris", _fake_world(_island_donor()))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8)
    assert s["clean"] is True and s["dry_run"] is True and s["deployed"] == []
    assert s["shift"] == [0.0, 0.0] and s["strips"] == [] and s["blanked"] == []
    assert s["carried"]["terrain"] == 2 and s["carried"]["sea4"] == 2
    assert all(g["ok"] for g in s["gates"])


def test_transplant_census_inherited_misses_pass(monkeypatch):
    """A donor that misses IN SITU (e.g. under a cliff's wall shadow) may keep those misses --
    the transplant law is no INTRODUCED misses, not miss==0 (real donors carry legit misses)."""
    blocks = _island_donor()
    del blocks[(1, 1, "sea4")]                       # the donor itself misses on all its water
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8)
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["miss"] > 0 and census["introduced"] == 0
    assert census["inherited"] == census["miss"] and census["ok"] is True
    assert s["clean"] is True


def test_transplant_census_fails_on_introduced_hole(monkeypatch):
    """A shift that vacates an edge the strip only PARTIALLY refills = a hole the donor never
    had -> introduced misses -> refused."""
    blocks = _island_donor(land_x=(104.0, 128.0))                  # tongue at the E border
    blocks[(2, 1, "sea4")] = _quad(128.0, 192.0, -96.0, -64.0, idall=232.0)   # HALF-height strip
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(-8.0, 0.0), dry_run=True,
                      census_samples=8)
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["introduced"] > 0 and census["ok"] is False and s["clean"] is False


def test_transplant_shift_window_from_strip_data(monkeypatch):
    blocks = _island_donor(land_x=(104.0, 128.0))    # land at the donor's E edge
    blocks[(2, 1, "sea4")] = _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)   # E neighbour
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    # auto-fit: ideal centring shift -20 clamps to the E strip's -8; the strip refills the frame
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8)
    assert s["strips"] == ["E"] and s["window"]["x"] == [-8.0, 0.0] and s["window"]["z"] == [0.0, 0.0]
    assert s["shift"] == [-8.0, 0.0] and s["clean"] is True
    # explicit in-window shift works too
    s2 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(-8.0, 0.0), dry_run=True, census_samples=8)
    assert s2["clean"] is True
    # beyond the window / off-lattice / bad rot are refused up front
    with pytest.raises(ValueError, match="coverage-feasible"):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(-16.0, 0.0), dry_run=True)
    with pytest.raises(ValueError, match="multiples of 4"):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(-3.0, 0.0), dry_run=True)
    with pytest.raises(ValueError, match="rot"):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 1), rot=45, dry_run=True)


def test_transplant_no_strip_no_shift(monkeypatch):
    monkeypatch.setattr(TR, "world_tris", _fake_world(_island_donor()))
    with pytest.raises(ValueError, match="coverage-feasible"):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(-8.0, 0.0), dry_run=True)


def test_transplant_auto_strips_reject_foreign_neighbours(monkeypatch):
    """Neighbour blocks are real world blocks with their OWN content: a strip only comes along
    where the donor's own land reaches that border (the island-tongue rule)."""
    blocks = _island_donor()                                     # central island: touches NO border
    blocks[(2, 1, "terrain")] = _quad(128.0, 136.0, -128.0, -64.0, idall=12800.0)   # foreign landmass edge
    blocks[(2, 1, "sea4")] = _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8)
    assert s["strips"] == [] and s["window"]["x"] == [0.0, 0.0]      # foreign data NOT carried
    assert s["carried"]["terrain"] == 2                              # the donor island only
    # explicit opt-in still allows it (expert mode)
    s2 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), strips="all", shift=(-8.0, 0.0),
                       dry_run=True, census_samples=8, land_margin=0.0)
    assert s2["strips"] == ["E"] and s2["carried"]["terrain"] > 2
    with pytest.raises(ValueError, match="strips must be"):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 1), strips=("Q",), dry_run=True)


def test_transplant_rot90_rotates_window_and_land(monkeypatch):
    blocks = _island_donor(land_x=(104.0, 128.0))
    blocks[(2, 1, "sea4")] = _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), rot=90, dry_run=True, census_samples=8)
    # the donor-E strip's rotated image sits NORTH -> the window moves to the z axis
    assert s["window"]["x"] == [0.0, 0.0] and s["window"]["z"] == [-8.0, 0.0]
    assert s["shift"] == [0.0, -8.0] and s["clean"] is True


def test_transplant_rot_keeps_sea_normals_rotates_land(monkeypatch):
    blocks = _island_donor()
    tilted = (0.6, 0.8, 0.0)                          # a real slope on the land part
    blocks[(1, 1, "terrain")] = [[_v(*p[0], uv=p[2][:2], idall=12800.0, nrm=tilted) for p in t]
                                 for t in blocks[(1, 1, "terrain")]]
    captured = {}
    real_soup = TR._soup_block_mesh

    def spy(name, cell, tris, **kw):
        captured[name.split()[-1]] = tris
        return real_soup(name, cell, tris, **kw)

    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    monkeypatch.setattr(TR, "_soup_block_mesh", spy)
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), rot=90, dry_run=True, census_samples=8,
                      land_margin=0.0)
    assert s["carried"]["terrain"] == 2
    (tnx, tny, tnz) = captured["Terrain"][0][0][1]
    assert (tny == 0.8) and (round(tnx, 6), round(tnz, 6)) == (0.0, 0.6)   # (0.6,0)->(0,0.6)
    assert captured["Sea4"][0][0][1] == NRM                                # sea normal untouched


def test_transplant_carries_vertical_wall_tris(monkeypatch):
    """THE WALL LAW (in-game 2026-07-09, the (9,5) forest island: 'the top renders, the
    vertical portion doesn't'): real VERTICAL faces -- forest sides, topo-38 -- have ZERO plan
    area, so the degenerate-sliver filter must test TRUE 3D area, never plan area. A clip
    sliver (collinear verts) still drops; a wall quad still carries."""
    wall = [[((100.0, 0.0, -96.0), (0.0, 0.0, 1.0), (0.1, 0.1), (9728.0, 0, 0, 1)),
             ((104.0, 0.0, -96.0), (0.0, 0.0, 1.0), (0.9, 0.1), (9728.0, 0, 0, 1)),
             ((104.0, 4.0, -96.0), (0.0, 0.0, 1.0), (0.9, 0.9), (9728.0, 0, 0, 1))],
            [((100.0, 0.0, -96.0), (0.0, 0.0, 1.0), (0.1, 0.1), (9728.0, 0, 0, 1)),
             ((104.0, 4.0, -96.0), (0.0, 0.0, 1.0), (0.9, 0.9), (9728.0, 0, 0, 1)),
             ((100.0, 4.0, -96.0), (0.0, 0.0, 1.0), (0.1, 0.9), (9728.0, 0, 0, 1))]]
    blocks = _island_donor()
    blocks[(1, 1, "terrain")] = blocks[(1, 1, "terrain")] + wall
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(0.0, 0.0), dry_run=True,
                      census_samples=8, land_margin=0.0)
    assert s["carried"]["terrain"] == 4                      # island quad + BOTH wall tris
    s2 = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(1, 1), shift=(0.0, 0.0),
                              dry_run=True, census_samples=8, land_margin=0.0)
    assert s2["carried"]["terrain"] == 4
    # a true LINE sliver (all verts collinear in 3D -- what clipping produces) still drops
    sliver = [[((10.0, 0.0, -50.0), NRM, (0.5, 0.5), (12800.0, 0, 0, 1)),
               ((20.0, 0.0, -50.0), NRM, (0.5, 0.5), (12800.0, 0, 0, 1)),
               ((15.0, 0.0, -50.0), NRM, (0.5, 0.5), (12800.0, 0, 0, 1))]]
    blocks2 = _island_donor()
    blocks2[(1, 1, "terrain")] = blocks2[(1, 1, "terrain")] + sliver
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks2))
    s3 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(0.0, 0.0), dry_run=True,
                       census_samples=8, land_margin=0.0)
    assert s3["carried"]["terrain"] == 2


def test_transplant_blanks_fully_clipped_donor_part(monkeypatch):
    blocks = _island_donor()
    # a TRULY degenerate beach1 (zero width -- collinear verts) dies at the degenerate-area
    # gate -> the whole donor part is gone and MUST be blanked (else the donor prefab's
    # original beach renders unshifted underneath). THE HAIRLINE LAW: a merely THIN quad is
    # real surface now and carries -- only true degenerates drop.
    blocks[(1, 1, "beach1")] = _quad(128.0, 128.0, -100.0, -96.0, idall=12920.0)
    deployed = []
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    monkeypatch.setattr(M, "deploy_override",
                        lambda bm, **k: deployed.append((k.get("part"), bm.x, bm.y, bm.vcount)) or "p")
    monkeypatch.setattr(M, "deploy_donor_sidecar",
                        lambda dx, dy, **k: deployed.append(("Donor", dx, dy, (k["x"], k["y"]))) or "d")
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), census_samples=8, land_margin=0.0)
    assert s["blanked"] == ["beach1"] and s["clean"] is True
    assert deployed == [("Terrain", 4, 2, 6), ("Beach1", 4, 2, 3),      # 3 verts = the hidden blank
                        ("Sea4", 4, 2, 6), ("Donor", 1, 1, (4, 2))]
    assert len(s["deployed"]) == 4


def test_transplant_refuses_deploy_when_not_clean(monkeypatch):
    blocks = _island_donor(land_x=(104.0, 128.0))
    blocks[(2, 1, "sea4")] = _quad(128.0, 192.0, -96.0, -64.0, idall=232.0)   # half-height strip
    deployed = []
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: deployed.append(1))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda *a, **k: deployed.append(1))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(-8.0, 0.0), census_samples=8)
    assert s["clean"] is False and s["deployed"] == [] and deployed == []


def test_transplant_refuses_real_target_cell(monkeypatch):
    """The target must be OPEN OCEAN: a cell with real block data is part of the game's world,
    and overriding it replaces real continent geometry (the (5,2)/(6,2) incident)."""
    blocks = _island_donor()
    blocks[(4, 2, "terrain")] = _quad(256.0, 320.0, -192.0, -128.0)   # the TARGET is real land
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    with pytest.raises(ValueError, match="REAL world block"):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True)
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8,
                      allow_real_target=True)
    assert s["clean"] is True                       # explicit expert override still works


def test_transplant_rejects_ocean_donor_and_bad_grid(monkeypatch):
    monkeypatch.setattr(TR, "world_tris", _fake_world({}))
    with pytest.raises(ValueError, match="no block mesh data"):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True)
    with pytest.raises(ValueError, match="out of the"):
        TR.transplant("MOD", cell=(24, 2), donor=(1, 1), dry_run=True)
    with pytest.raises(ValueError, match="out of the"):
        TR.transplant("MOD", cell=(4, 2), donor=(1, 20), dry_run=True)


# ---------------------------------------------------------------- the two proven tweak classes

def test_tile_retexture_rewrites_uv_and_idall():
    tw = TR.TileRetexture(cells={(22, -23): ((0, 0), 0)}, match_idall=12812, new_idall=12800,
                          uv_fn=lambda x, z, cell, quad, ori: (0.25, 0.75))
    cell_tris = _quad(88.0, 92.0, -92.0, -88.0, idall=12812.0)          # donor cell (22,-23)
    out = [tw.apply("terrain", t) for t in cell_tris]
    assert tw.applied == 2 and tw.gate()["ok"] is True
    for poly in out:
        for (pos, nrm, uv, tan) in poly:
            assert uv == (0.25, 0.75) and tan[0] == 12800.0 and tan[3] == 1.0   # tangent tail kept
    # geometry + normals stay verbatim
    assert [v[0] for v in out[0]] == [v[0] for v in cell_tris[0]]
    # wrong part / wrong idall / unlisted cell pass through untouched
    assert tw.apply("beach1", cell_tris[0]) == cell_tris[0]
    other = _quad(0.0, 4.0, -4.0, 0.0, idall=12812.0)[0]                # cell (0,-1) not listed
    assert tw.apply("terrain", other) == other
    grass = _quad(88.0, 92.0, -92.0, -88.0, idall=12800.0)[0]
    assert tw.apply("terrain", grass) == grass


def test_patch_recover_captures_exact_offlattice_floats():
    # real-donor-style OFF-LATTICE verts (the weld law: never hand-type geometry)
    A2 = (496.046875, 1.160156, -1125.0234375)
    A = (500.03125, 0.8203125, -1125.609375)
    C2 = (496.0078125, 0.201171875, -1129.0390625)
    C = (500.015625, 0.19921875, -1129.6015625)
    nA = (-0.179, 0.881, -0.438)
    t1 = [(A2, nA, (0.1, 0.1), (12920.0, 0, 0, 0)), (A, nA, (0.2, 0.1), (12920.0, 0, 0, 0)),
          (C2, nA, (0.1, 0.9), (12920.0, 0, 0, 0))]
    t2 = [(A, nA, (0.2, 0.1), (12920.0, 0, 0, 0)), (C, nA, (0.2, 0.9), (12920.0, 0, 0, 0)),
          (C2, nA, (0.1, 0.9), (12920.0, 0, 0, 0))]
    tw = TR.PatchRecover(part="beach1", drop=lambda poly: min(v[0][0] for v in poly) >= 495.9,
                         corners={"A2": (496.0, -1125.0), "A": (500.0, -1125.6),
                                  "C2": (496.0, -1129.0), "C": (500.0, -1129.6)},
                         fan=[("C2", "A2", "A"), ("C2", "A", "C")],
                         uv={"A2": (0.5, 0.5312), "A": (0.25, 0.5312),
                             "C2": (0.5, 0.9375), "C": (0.25, 0.9375)},
                         idall=12920.0, expected_drops=2)
    assert tw.apply("beach1", t1) is None and tw.apply("beach1", t2) is None
    assert tw.gate()["ok"] is True
    fan = tw.emit()
    assert len(fan) == 2
    # bit-exact capture: positions AND normals come from the dropped tris, never retyped
    assert fan[0][1][0] == A2 and fan[0][2][0] == A and fan[1][2][0] == C
    assert fan[0][0][1] == nA
    assert fan[0][0][2] == (0.5, 0.9375) and fan[0][0][3] == (12920.0, 0.0, 0.0, 0.0)
    # a tri outside the drop region passes through
    keep = [(tuple(v[0]), v[1], v[2], v[3]) for v in _quad(400.0, 404.0, -1104.0, -1100.0)[0]]
    assert tw.apply("beach1", keep) == keep


def test_vertex_displace_moves_all_instances_weld_preserving():
    wl = (488.0, 0.1953125, -1125.29296875)                 # off-lattice real-style float
    b1 = [[(wl, NRM, (0.1, 0.45), (12920.0, 0, 0, 0)),
           _v(492, 0.2, -1128), _v(488, 1.16, -1121.2)]]
    s2 = [[(wl, NRM, (0.5, 0.5), (212.0, 0, 0, 0)),
           _v(492, 0.2, -1128), _v(488, 0.0, -1129.3)]]
    tw = TR.VertexDisplace(moves={(488.0, 0.1953, -1125.293): (0.0, 0.0, -1.2)}, expected=2)
    ob1 = tw.apply("beach1", b1[0])
    os2 = tw.apply("sea2", s2[0])
    assert tw.gate()["ok"] is True and tw.applied == 2 and tw.folds == 0
    # both instances moved by the SAME delta from the exact float -> still coincident (weld kept)
    assert ob1[0][0] == os2[0][0] == (488.0, 0.1953125, -1125.29296875 - 1.2)
    # UV / tangent / normal untouched (the texture stretches, shading stays)
    assert ob1[0][2] == (0.1, 0.45) and ob1[0][3] == (12920.0, 0, 0, 0) and ob1[0][1] == NRM
    # untouched polys pass through as the same object
    other = [_v(0, 0, 0), _v(4, 0, 0), _v(0, 0, -4)]
    assert tw.apply("terrain", other) is other


def test_vertex_displace_fold_gate_and_scope():
    # a displacement that drives a vert across the tile = flipped winding -> gate fails
    tri = [_v(0, 0, 0), _v(4, 0, 0), _v(0, 0, -4)]
    tw = TR.VertexDisplace(moves={(0.0, 0.0, 0.0): (0.0, 0.0, -10.0)}, expected=1)
    tw.apply("sea2", tri)
    g = tw.gate()
    assert g["folds"] == 1 and g["ok"] is False
    # part-scoped displacement ignores other parts
    tw2 = TR.VertexDisplace(moves={(0.0, 0.0, 0.0): (0.0, 0.0, -1.0)}, expected=1, part="sea2")
    assert tw2.apply("terrain", tri) is tri
    tw2.apply("sea2", tri)
    assert tw2.gate()["ok"] is True
    # a missed key -> count gate fails loud
    tw3 = TR.VertexDisplace(moves={(99.0, 0.0, 0.0): (0.0, 0.0, -1.0)}, expected=1)
    tw3.apply("sea2", tri)
    assert tw3.gate()["ok"] is False


def test_patch_recover_raises_on_uncaptured_corner():
    tw = TR.PatchRecover(part="beach1", drop=lambda poly: False,
                         corners={"A": (0.0, 0.0)}, fan=[("A", "A", "A")],
                         uv={"A": (0.0, 0.0)}, idall=1.0, expected_drops=0)
    with pytest.raises(ValueError, match="not captured"):
        tw.emit()


def test_transplant_runs_tweaks_and_gates_their_scope(monkeypatch):
    blocks = _island_donor()
    # the island's 4 land tris get a "quest" id on one lattice cell (world 88..92 x -92..-88)
    blocks[(1, 1, "terrain")] = (_quad(88.0, 92.0, -92.0, -88.0, idall=12812.0)
                                 + _quad(92.0, 104.0, -104.0, -88.0, idall=12800.0)
                                 + _quad(88.0, 104.0, -104.0, -92.0, idall=12800.0))
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    tw = TR.TileRetexture(cells={(22, -23): ((0, 0), 0)}, match_idall=12812, new_idall=12800,
                          uv_fn=lambda *a: (0.1, 0.2))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), tweaks=[tw], dry_run=True,
                      census_samples=8, land_margin=0.0)
    assert next(g for g in s["gates"] if g["gate"] == "retile[terrain]")["ok"] is True
    # scope gate FAILS the build when the tweak matched nothing (wrong cell)
    tw2 = TR.TileRetexture(cells={(0, 0): ((0, 0), 0)}, match_idall=12812, new_idall=12800,
                           uv_fn=lambda *a: (0.1, 0.2))
    s2 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), tweaks=[tw2], dry_run=True,
                       census_samples=8, land_margin=0.0)
    assert s2["clean"] is False
    assert next(g for g in s2["gates"] if g["gate"] == "retile[terrain]")["ok"] is False


def test_row_insert_grows_island_with_bitexact_welds(monkeypatch):
    """The growth seed (in-game proven 2026-07-08): split-shift at a lattice line + seam-profile
    extrusion -- welds bit-exact by identity, per-class UV fill, the island grows by delta."""
    LINE = 92.0
    blocks = {
        # two grass tiles astride the cut line (topo 0 -> mains fill + relief center)
        (1, 1, "terrain"): (_quad(88.0, 92.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.03, 0.78))
                            + _quad(92.0, 96.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.09, 0.81))),
        # sea4 as two lattice slabs meeting exactly ON the line (mirror-affine fill)
        (1, 1, "sea4"): (_quad(64.0, 92.0, -128.0, -64.0, idall=232.0)
                         + _quad(92.0, 128.0, -128.0, -64.0, idall=232.0)),
    }
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    tweaks = [TR.RowInsert(p, line=LINE) for p in TR.PARTS]
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(0.0, 0.0), land_margin=0.0,
                      tweaks=tweaks, dry_run=True, census_samples=8)
    assert s["clean"] is True, s["gates"]
    tw = {t.part: t for t in tweaks}
    # terrain: 2 tris kept, 2 shifted, grass fill = a 4-tri relief fan
    assert tw["terrain"].kept == 2 and tw["terrain"].shifted == 2 and tw["terrain"].emitted == 4
    assert tw["sea4"].emitted == 2                          # flat mirror fill
    assert s["carried"]["terrain"] == 8
    # the island grew by exactly delta: the east grass tile now ends at 96+4 -> local 36
    lf = next(g for g in s["gates"] if g["gate"] == "land-fit")
    assert lf["bbox"][1] == pytest.approx(36.0)
    # weld audit already gated inside transplant (bit-exact-by-identity) -- assert it explicitly
    assert next(g for g in s["gates"] if g["gate"] == "weld-audit")["pairs"] == 0


def test_row_insert_grass_fill_speaks_the_mains_language(monkeypatch):
    LINE = 92.0
    blocks = {
        (1, 1, "terrain"): (_quad(88.0, 92.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.03, 0.78))
                            + _quad(92.0, 96.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.09, 0.81))),
        (1, 1, "sea4"): (_quad(64.0, 92.0, -128.0, -64.0, idall=232.0)
                         + _quad(92.0, 128.0, -128.0, -64.0, idall=232.0)),
    }
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    tw = TR.RowInsert("terrain", line=LINE)
    for t in blocks[(1, 1, "terrain")]:
        tw.apply("terrain", [tuple(v) for v in t])
    fill = tw.emit()
    assert len(fill) == 4                                   # the relief fan
    from ff9mapkit.world.grassland import GRASS_U_HALF, GRASS_V_HALF
    u_all = [v[2][0] for t in fill for v in t]
    v_all = [v[2][1] for t in fill for v in t]
    assert min(u_all) >= GRASS_U_HALF[0][0] - 0.16 and max(u_all) <= GRASS_U_HALF[1][1] + 0.16
    assert min(v_all) >= GRASS_V_HALF[0][0] - 0.16 and max(v_all) <= GRASS_V_HALF[1][1] + 0.16
    # the chosen quadrant avoids BOTH real neighbours ((0,0) west, (1,1) east)
    picked = {_uv_quad(v[2]) for t in fill for v in t if abs(v[0][0] - 94.0) > 1.5}
    # boundary verts may bleed; probe the fan centre vert instead
    centre = [v for t in fill for v in t if abs(v[0][0] - 94.0) < 0.5]
    assert centre and _uv_quad(centre[0][2]) not in {(0, 0), (1, 1)}
    # every fill tri is up-facing (winding enforced at emit)
    for t in fill:
        ux, uz = t[1][0][0] - t[0][0][0], t[1][0][2] - t[0][0][2]
        vx, vz = t[2][0][0] - t[0][0][0], t[2][0][2] - t[0][0][2]
        assert uz * vx - ux * vz > 0


def _uv_quad(uv):
    return (0 if uv[0] < 0.0654 else 1, 0 if uv[1] < 0.7993 else 1)


def test_object_anchor_gate(monkeypatch):
    """A donor Object (cave/town) renders from the PREFAB at its original pose -- the kit
    doesn't carry it. Any rot/shift/RowInsert displacing the ground under its footprint must
    be refused (the (9,17) cave tear, 2026-07-09) unless explicitly overridden."""
    blocks = _island_donor()
    blocks[(1, 1, "object")] = _quad(90.0, 96.0, -100.0, -94.0, y=2.0)
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    # untransformed carry: object region untouched -> ok
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(0.0, 0.0), dry_run=True,
                      census_samples=8)
    oa = next(g for g in s["gates"] if g["gate"] == "object-anchor")
    assert oa["ok"] is True and oa["moved"] is False and oa["x"] == [90.0, 96.0]
    # a rotation (like a shift) moves the ground under the static object -> refused
    s2 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), rot=90, shift=(0.0, 0.0),
                       dry_run=True, census_samples=8)
    oa2 = next(g for g in s2["gates"] if g["gate"] == "object-anchor")
    assert oa2["ok"] is False and s2["clean"] is False
    # a RowInsert west of the footprint's east edge displaces ground under it -> refused;
    # east of the footprint leaves it verbatim -> ok
    s3 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(0.0, 0.0), land_margin=0.0,
                       tweaks=TR.chain_row_inserts([92.0]), dry_run=True, census_samples=8)
    assert next(g for g in s3["gates"] if g["gate"] == "object-anchor")["ok"] is False
    s4 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(0.0, 0.0), land_margin=0.0,
                       tweaks=TR.chain_row_inserts([96.0]), dry_run=True, census_samples=8)
    assert next(g for g in s4["gates"] if g["gate"] == "object-anchor")["ok"] is True
    # expert override
    s5 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), rot=90, shift=(0.0, 0.0),
                       allow_object_misalign=True, dry_run=True, census_samples=8)
    assert next(g for g in s5["gates"] if g["gate"] == "object-anchor")["ok"] is True


def test_row_insert_clones_non_grass_family_owner(monkeypatch):
    """A topo-0 owner OUTSIDE the grass rect (the (9,17) u~0.39 scrub band) is a PAINTED-WASH
    family, not an interchangeable variant set -- the fill must CONTINUE the local material by
    cloning the west owner's field (a variant-avoid pick maximizes contrast = the hard-edged
    'meadow marks', in-game 2026-07-09). Never grass quadrants either."""
    LINE = 92.0
    U0, U1 = 0.394, 0.454
    STRIPS = [(0.369, 0.399), (0.399, 0.431), (0.431, 0.462), (0.462, 0.493)]
    def scrub(x0, x1, z0, z1, strip):
        v0, v1 = STRIPS[strip]
        # linear-in-position field: u west->east across [U0,U1], v north->south across strip
        return [[((x0, 1.0, z0), (0, 1, 0), (U0, v0), (12544.0, 0, 0, 1)),
                 ((x1, 1.0, z0), (0, 1, 0), (U1, v0), (12544.0, 0, 0, 1)),
                 ((x1, 1.0, z1), (0, 1, 0), (U1, v1), (12544.0, 0, 0, 1))],
                [((x0, 1.0, z0), (0, 1, 0), (U0, v0), (12544.0, 0, 0, 1)),
                 ((x1, 1.0, z1), (0, 1, 0), (U1, v1), (12544.0, 0, 0, 1)),
                 ((x0, 1.0, z1), (0, 1, 0), (U0, v1), (12544.0, 0, 0, 1))]]
    tw = TR.RowInsert("terrain", line=LINE)
    tiles = (scrub(84.0, 88.0, -100.0, -96.0, 0) + scrub(88.0, 92.0, -100.0, -96.0, 1)
             + scrub(92.0, 96.0, -100.0, -96.0, 2) + scrub(96.0, 100.0, -100.0, -96.0, 3))
    for t in tiles:
        tw.apply("terrain", [tuple(v) for v in t])
    fill = tw.emit()
    assert len(fill) == 4                                    # relief fan (topo-0 ground family)
    us = [v[2][0] for t in fill for v in t]
    vs = [v[2][1] for t in fill for v in t]
    # the STRETCH of the owner (strip 1): inside the owner's rect, never grass, no sibling
    assert min(us) >= U0 - 1e-6 and max(us) <= U1 + 1e-6
    assert min(vs) >= STRIPS[1][0] - 1e-6 and max(vs) <= STRIPS[1][1] + 1e-6
    # the fill maps the owner's EAST HALF at 2x width: west edge = the owner's mid-tile u,
    # east edge = the owner's east-edge u -- the original owner->east seam is RESTORED
    umid = (U0 + U1) / 2.0
    west = [v[2] for t in fill for v in t if abs(v[0][0] - LINE) < 1e-6]
    assert all(abs(uv[0] - umid) < 1e-6 for uv in west)
    east = [v[2] for t in fill for v in t if abs(v[0][0] - (LINE + 4.0)) < 1e-6]
    assert all(abs(uv[0] - U1) < 1e-6 for uv in east)
    # orientation/handedness unchanged (no flip): u still ramps west->east, v untouched by x
    assert min(uv[0] for uv in east) > max(uv[0] for uv in west) - 1e-9


def test_row_insert_wash_stretch_switches_to_east_at_family_boundary():
    """The side rule: when the owner is the wash family's BOUNDARY tile (gradient) and the
    east tile is wash interior, the fill stretches from the EAST tile's west half instead --
    the restored seam lands on the gradient side, the self-tear hides in the uniform core
    (in-game 2026-07-09: the west fill's gradient stutter vs the clean east fill)."""
    LINE = 92.0
    U0, U1 = 0.394, 0.454
    STRIPS = [(0.369, 0.399), (0.399, 0.431), (0.431, 0.462), (0.462, 0.493)]
    def tile(x0, x1, z0, z1, u0, u1, v0, v1):
        return [[((x0, 1.0, z0), (0, 1, 0), (u0, v0), (12544.0, 0, 0, 1)),
                 ((x1, 1.0, z0), (0, 1, 0), (u1, v0), (12544.0, 0, 0, 1)),
                 ((x1, 1.0, z1), (0, 1, 0), (u1, v1), (12544.0, 0, 0, 1))],
                [((x0, 1.0, z0), (0, 1, 0), (u0, v0), (12544.0, 0, 0, 1)),
                 ((x1, 1.0, z1), (0, 1, 0), (u1, v1), (12544.0, 0, 0, 1)),
                 ((x0, 1.0, z1), (0, 1, 0), (u0, v1), (12544.0, 0, 0, 1))]]
    def scrub(x0, x1, strip):
        v0, v1 = STRIPS[strip]
        return tile(x0, x1, -100.0, -96.0, U0, U1, v0, v1)
    tw = TR.RowInsert("terrain", line=LINE)
    tiles = (tile(84.0, 88.0, -100.0, -96.0, 0.004, 0.064, 0.77, 0.80)   # GRASS west of owner
             + scrub(88.0, 92.0, 1) + scrub(92.0, 96.0, 2) + scrub(96.0, 100.0, 3))
    for t in tiles:
        tw.apply("terrain", [tuple(v) for v in t])
    fill = tw.emit()
    assert len(fill) == 4
    # stretched from the EAST tile (strip 2): west edge = its west-edge u (the restored seam
    # against the gradient owner), east edge = its mid u (the tear inside the uniform core)
    vs = [v[2][1] for t in fill for v in t]
    assert min(vs) >= STRIPS[2][0] - 1e-6 and max(vs) <= STRIPS[2][1] + 1e-6
    west = [v[2][0] for t in fill for v in t if abs(v[0][0] - LINE) < 1e-6]
    east = [v[2][0] for t in fill for v in t if abs(v[0][0] - (LINE + 4.0)) < 1e-6]
    assert all(abs(u - U0) < 1e-6 for u in west)
    assert all(abs(u - (U0 + U1) / 2.0) < 1e-6 for u in east)


def test_cut_census_component_laws(monkeypatch):
    """cut_census bakes the full cut-line law: zero straddlers, grows land, and no component
    crossings -- beach both-sides, beach end-cap ON the line, painted-wash patch crossing,
    object-ground displacement ((9,17) measured ZERO usable lines; (7,17) exactly one)."""
    blocks = {
        # land tiles astride x=88 and x=96 (both lattice-clean)
        (1, 1, "terrain"): (_quad(84.0, 88.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.03, 0.78))
                            + _quad(88.0, 92.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.09, 0.81))
                            + _quad(92.0, 96.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.03, 0.81))
                            + _quad(96.0, 100.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.09, 0.78))),
        (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0),
        # a foam ribbon ending exactly ON x=96 (end-cap) and entirely west of x=100
        (1, 1, "beach1"): _quad(92.0, 96.0, -110.0, -106.0, y=1.2, idall=7680.0),
        # an object whose ground lies east of x=88
        (1, 1, "object"): _quad(90.0, 94.0, -104.0, -100.0, y=2.0),
    }
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    cen = {c["line"]: c for c in TR.cut_census((1, 1))}
    # sea4 spans the whole cell -> every lattice line except tile edges straddles... the
    # full-cell quad's fan triangulation straddles interior lines; assert the law fields
    c88 = cen[88.0]
    assert c88["grows_land"] is True
    assert "displaces-object-ground" in c88["risks"]
    c96 = cen[96.0]
    assert "beach-end-on-line" in c96["risks"]


def test_row_insert_wang_strip_fill_preserves_orientation():
    """A Wang transition strip (sea5/sea1) is DIRECTIONAL: the fill must translate-clone the
    owner (same u-direction, inside the strip rect) -- the old mirror reversed the tile's
    orientation ('the sea isn't properly tiled', in-game 2026-07-09)."""
    from ff9mapkit.world.water import UFULL, VSTRIP
    LINE = 92.0
    (v0, v1) = VSTRIP[1]
    def strip_tile(x0, x1):
        # full-u strip tile, u increasing with x, v spanning strip 1
        return [[((x0, 0.0, -100.0), (0, 1, 0), (UFULL[0], v0), (228.0, 0, 0, 1)),
                 ((x1, 0.0, -100.0), (0, 1, 0), (UFULL[1], v0), (228.0, 0, 0, 1)),
                 ((x1, 0.0, -96.0), (0, 1, 0), (UFULL[1], v1), (228.0, 0, 0, 1))],
                [((x0, 0.0, -100.0), (0, 1, 0), (UFULL[0], v0), (228.0, 0, 0, 1)),
                 ((x1, 0.0, -96.0), (0, 1, 0), (UFULL[1], v1), (228.0, 0, 0, 1)),
                 ((x0, 0.0, -96.0), (0, 1, 0), (UFULL[0], v1), (228.0, 0, 0, 1))]]
    tw = TR.RowInsert("sea5", line=LINE)
    for t in strip_tile(88.0, 92.0) + strip_tile(92.0, 96.0):
        tw.apply("sea5", [tuple(v) for v in t])
    fill = tw.emit()
    assert len(fill) == 2
    for t in fill:
        vs = [v[2][1] for v in t]
        assert min(vs) >= v0 - 1e-6 and max(vs) <= v1 + 1e-6      # stays in the strip
        for a in range(3):
            for b in range(3):
                dx = t[b][0][0] - t[a][0][0]
                if abs(dx) > 1.0:
                    assert (t[b][2][0] - t[a][2][0]) / dx > 0     # u INCREASES with x, unmirrored


def test_chain_row_inserts_cumulative_lines():
    """Callers give donor-frame lines; the helper sorts west-to-east and shifts each later
    cut by every earlier cut's delta (a later tweak sees already-shifted geometry)."""
    tweaks = TR.chain_row_inserts([92.0, 88.0], parts=("terrain",))
    assert [tw.line for tw in tweaks] == [88.0, 96.0]
    assert tweaks[0].seed != tweaks[1].seed                 # each cut rolls its own grass
    # per-part fan-out preserves cut order (all of cut 1 before any of cut 2)
    tweaks3 = TR.chain_row_inserts([100.0], parts=("terrain", "sea4"))
    assert [(tw.part, tw.line) for tw in tweaks3] == [("terrain", 100.0), ("sea4", 100.0)]


def test_chained_row_inserts_grow_island_twice(monkeypatch):
    """Two chained cuts (adjacent clean lines, the (9,17) 604+608 pattern): both fills emitted,
    everything east of both nets +2*delta, welds bit-exact by identity throughout."""
    blocks = {
        (1, 1, "terrain"): (_quad(84.0, 88.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.03, 0.78))
                            + _quad(88.0, 92.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.09, 0.81))
                            + _quad(92.0, 96.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.03, 0.81))),
        (1, 1, "sea4"): (_quad(64.0, 88.0, -128.0, -64.0, idall=232.0)
                         + _quad(88.0, 92.0, -128.0, -64.0, idall=232.0)
                         + _quad(92.0, 128.0, -128.0, -64.0, idall=232.0)),
    }
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    tweaks = TR.chain_row_inserts([88.0, 92.0])
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(0.0, 0.0), land_margin=0.0,
                      tweaks=tweaks, dry_run=True, census_samples=8)
    assert s["clean"] is True, s["gates"]
    cut1 = {tw.part: tw for tw in tweaks if tw.line == 88.0}
    cut2 = {tw.part: tw for tw in tweaks if tw.line == 96.0}
    # cut 1 splits [84,88] | [88,96]; cut 2 then splits at 96: keeps [84,88]+[92,96](orig 88-92),
    # shifts [96,100](orig 92-96) -- each cut fills one grass cell (a 4-tri relief fan)
    assert cut1["terrain"].kept == 2 and cut1["terrain"].shifted == 4
    assert cut2["terrain"].kept == 4 and cut2["terrain"].shifted == 2
    assert cut1["terrain"].emitted == 4 and cut2["terrain"].emitted == 4
    # the island grew by exactly 2*delta: orig land [84,96] -> [84,104] = local [20,40]
    lf = next(g for g in s["gates"] if g["gate"] == "land-fit")
    assert lf["bbox"][0] == pytest.approx(20.0) and lf["bbox"][1] == pytest.approx(40.0)
    # both fills + all shifted geometry weld bit-exact (the identity law survives chaining)
    assert next(g for g in s["gates"] if g["gate"] == "weld-audit")["pairs"] == 0
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["introduced"] == 0


# ---------------------------------------------------------------- transplant_region (multi-cell)

def _capture_deploys(monkeypatch):
    """Patch the two deploy writers to capture (kind, part, cell, mesh-bytes) tuples."""
    import json
    deployed = []
    monkeypatch.setattr(M, "deploy_override",
                        lambda bm, **k: deployed.append(("override", k.get("part"), bm.x, bm.y,
                                                         json.dumps(bm.chan_arrays, sort_keys=True),
                                                         tuple(bm.flat_index))) or "p")
    monkeypatch.setattr(M, "deploy_donor_sidecar",
                        lambda dx, dy, **k: deployed.append(("sidecar", dx, dy, k["x"], k["y"])) or "d")
    return deployed


def _tongue_donor():
    """Donor (1,1): land reaching the E border + its (2,1) tongue -- the proven island shape."""
    return {(1, 1, "terrain"): _quad(100.0, 128.0, -104.0, -88.0, y=1.0),
            (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0),
            (2, 1, "terrain"): _quad(128.0, 134.0, -104.0, -88.0, y=1.0),
            (2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)}


def test_region_1x1_byte_identical_to_transplant(monkeypatch):
    """THE IDENTITY LAW: a 1x1 region is the single-cell transplant -- deployed mesh bytes and
    the sidecar must be bit-identical to the in-game-proven transplant() across plain, rotated,
    shifted and strip-refilled configurations (the island_morph byte-identity discipline)."""
    blocks = _tongue_donor()
    blocks[(1, 1, "beach1")] = _quad(98.0, 100.0, -104.0, -88.0, y=0.2, idall=7680.0)
    for kw in (dict(), dict(rot=90), dict(shift=(-8.0, 0.0)), dict(rot=180)):
        monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
        d1 = _capture_deploys(monkeypatch)
        s1 = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), census_samples=8,
                           land_margin=0.0, **kw)
        got1 = list(d1)
        d1.clear()
        s2 = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(1, 1),
                                  census_samples=8, land_margin=0.0, **kw)
        assert s1["clean"] is True and s2["clean"] is True, (kw, s1["gates"], s2["gates"])
        assert s1["shift"] == s2["shift"] and got1 == list(d1), kw


def test_region_2x1_verbatim_carry(monkeypatch):
    """The multi-cell unlock: a real 2-block landmass (each block carrying its own half of the
    land, meeting at the shared border -- real block meshes never straddle their own frame)
    carried whole to 2 adjacent ocean cells. Each target cell deploys its own overrides + its
    NATURAL donor sidecar; the census covers both cells; the shared-border weld is exact."""
    blocks = {(1, 1, "terrain"): _quad(100.0, 128.0, -104.0, -88.0, y=1.0),
              (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0),
              (2, 1, "terrain"): _quad(128.0, 150.0, -104.0, -88.0, y=1.0),
              (2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    deployed = _capture_deploys(monkeypatch)
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                             census_samples=8, land_margin=2.0)
    assert s["clean"] is True, s["gates"]
    assert s["tsize"] == [2, 1] and sorted(s["cells"]) == ["4,2", "5,2"]
    assert s["cells"]["4,2"]["donor"] == [1, 1] and s["cells"]["5,2"]["donor"] == [2, 1]
    assert s["cells"]["4,2"]["carried"]["terrain"] == 2 and s["cells"]["5,2"]["carried"]["terrain"] == 2
    assert next(g for g in s["gates"] if g["gate"] == "weld-audit")["pairs"] == 0
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["introduced"] == 0 and census["samples"] > 0
    kinds = {(d[0], d[3], d[4]) for d in deployed if d[0] == "sidecar"}
    assert ("sidecar", 4, 2) in kinds and ("sidecar", 5, 2) in kinds


def test_region_shift_splits_straddlers_watertight(monkeypatch):
    """An in-region shift carries tris ACROSS the interior border; the re-partition splits them
    with bit-identical cut points on both sides (the _split_at_borders law) -- weld audit 0."""
    blocks = {(1, 1, "terrain"): _quad(100.0, 128.0, -104.0, -88.0, y=1.0),
              (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0),
              (2, 1, "terrain"): _quad(128.0, 150.0, -104.0, -88.0, y=1.0),
              (2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=232.0),
              # W neighbour strip data: opens the +x window so shift +4 refills the W edge...
              # (tongue law: the window opens where the REGION's own land reaches the border --
              # it doesn't here, so use explicit strips to keep the fixture small)
              (0, 1, "sea4"): _quad(0.0, 64.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(4.0, 0.0),
                             strips=("W",), census_samples=8, dry_run=True, land_margin=0.0)
    assert s["clean"] is True, s["gates"]
    # the (2,1) terrain quad now spans x 68..90 region-local: still one cell -- but the (1,1)
    # sea4 + terrain shifted across x=64? terrain [100,128]+4 -> local [40,68]: STRADDLES.
    assert s["cells"]["4,2"]["carried"]["terrain"] > 0 and s["cells"]["5,2"]["carried"]["terrain"] > 0
    assert next(g for g in s["gates"] if g["gate"] == "weld-audit")["pairs"] == 0
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["introduced"] == 0


def test_region_prefab_parts_gate_and_fallback(monkeypatch):
    """A target cell carrying a part its natural donor prefab LACKS (RegisterBlockComponent
    binds by transform name -- the part would silently not render) must fall back to a donor
    cell with a SUPERSET of parts, or fail the prefab-parts gate."""
    # (1,1)'s terrain reaches x=150 (a hermetic straddle; real per-block meshes stay in-frame,
    # but a shift/strip produces the same shape) -- cell (5,2) then carries terrain whose
    # natural donor (2,1) is sea4-only
    blocks = {(1, 1, "terrain"): _quad(100.0, 150.0, -104.0, -88.0, y=1.0),
              (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0),
              (2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                             census_samples=8, dry_run=True, land_margin=0.0)
    # fallback: (1,1) = {terrain, sea4} hosts cell (5,2)'s {terrain, sea4}; sea4 carried -> no blanks
    assert next(g for g in s["gates"] if g["gate"] == "prefab-parts")["ok"] is True
    assert s["cells"]["5,2"]["donor"] == [1, 1] and s["cells"]["5,2"]["blanked"] == []
    # orphan the need: cell (5,2) now also carries sea3, which only (2,1) has -- so it needs
    # {terrain, sea3, sea4}: (1,1) lacks sea3, (2,1) lacks terrain -> NO superset -> gate fails
    blocks[(2, 1, "sea3")] = _quad(128.0, 192.0, -112.0, -64.0, idall=228.0)
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s2 = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                              census_samples=8, dry_run=True, land_margin=0.0)
    g = next(g for g in s2["gates"] if g["gate"] == "prefab-parts")
    assert g["ok"] is False and s2["clean"] is False
    assert g["bad"][0]["cell"] == [5, 2] and "terrain" in g["bad"][0]["need"]
    assert g["bad"][0]["natural"] == [2, 1]


def test_region_skips_empty_target_cells(monkeypatch):
    """A donor rect cell that is pure ocean carries nothing -- its target cell deploys NOTHING
    (no override, no sidecar) and stays true SeaBlockPrefab ocean; census skips it."""
    blocks = {(1, 1, "terrain"): _quad(88.0, 104.0, -104.0, -88.0, y=1.0),
              (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    deployed = _capture_deploys(monkeypatch)
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                             census_samples=8)
    assert s["clean"] is True, s["gates"]
    assert sorted(s["cells"]) == ["4,2"]                      # (5,2) skipped whole
    assert all(d[2] != 5 for d in deployed if d[0] == "override")
    assert all(d[3] != 5 for d in deployed if d[0] == "sidecar")


def test_region_rot90_swaps_rect_and_maps_sidecars(monkeypatch):
    """rot 90 turns a 2x1 donor rect into a 1x2 target rect; each target cell's sidecar is the
    donor cell it maps BACK to through the inverse region transform."""
    blocks = _tongue_donor()
    blocks[(2, 1, "terrain")] = _quad(128.0, 140.0, -104.0, -88.0, y=1.0)
    blocks[(2, 1, "sea4")] = _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), rot=90,
                             shift=(0.0, 0.0), census_samples=8, dry_run=True, land_margin=0.0,
                             strips="none")
    assert s["clean"] is True, s["gates"]
    assert s["tsize"] == [1, 2] and sorted(s["cells"]) == ["4,2", "4,3"]
    # under one CCW quarter-turn the region's west donor cell lands in the SOUTH target cell
    assert s["cells"]["4,3"]["donor"] == [1, 1] and s["cells"]["4,2"]["donor"] == [2, 1]
    assert next(g for g in s["gates"] if g["gate"] == "weld-audit")["pairs"] == 0


def test_region_object_cell_never_hosts_foreign_target(monkeypatch):
    """An OBJECT-bearing donor cell must not be picked as the sidecar for a foreign target cell
    (its prefab Object would ghost-render there); its own natural cell at identity transform is
    legitimate (the verbatim carry brings the object along)."""
    blocks = {(1, 1, "terrain"): _quad(100.0, 150.0, -104.0, -88.0, y=1.0),
              (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0),
              (1, 1, "object"): _quad(104.0, 112.0, -100.0, -92.0, y=2.0),
              (2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                             census_samples=8, dry_run=True)
    # cell (5,2) needs terrain (the straddle): natural (2,1) lacks it; the only superset donor
    # is (1,1) but it bears an Object -> excluded -> prefab-parts FAILS (no silent ghost)
    g = next(g for g in s["gates"] if g["gate"] == "prefab-parts")
    assert g["ok"] is False and g["bad"][0]["cell"] == [5, 2]
    # identity transform keeps the object cell's own target legitimate: object-anchor ok
    oa = next(g for g in s["gates"] if g["gate"].startswith("object-anchor"))
    assert oa["ok"] is True and oa["moved"] is False
    # a shift moves the ground under the prefab-anchored object -> anchor gate refuses
    blocks2 = dict(blocks)
    blocks2[(2, 1, "terrain")] = _quad(128.0, 136.0, -104.0, -88.0, y=1.0)   # E tongue for window
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks2))
    s2 = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                              rot=90, census_samples=8, dry_run=True)
    oa2 = next(g for g in s2["gates"] if g["gate"].startswith("object-anchor"))
    assert oa2["ok"] is False and oa2["moved"] is True


def test_region_census_backmaps_through_the_region_transform(monkeypatch):
    """Misses backmap through the inverse region transform to the DONOR's per-cell meshes:
    in-situ donor misses are inherited (clean); a hole the donor never had is introduced."""
    blocks = {(1, 1, "terrain"): _quad(88.0, 104.0, -104.0, -88.0, y=1.0),
              (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0),
              # donor (2,1) covers only its WEST half -- the east half misses IN SITU
              (2, 1, "sea4"): _quad(128.0, 160.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                             census_samples=8, dry_run=True)
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["miss"] > 0 and census["introduced"] == 0
    assert census["inherited"] == census["miss"] and s["clean"] is True, s["gates"]


def test_region_refusals(monkeypatch):
    blocks = _tongue_donor()
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    with pytest.raises(ValueError, match="size must be"):
        TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(0, 1), dry_run=True)
    with pytest.raises(ValueError, match="donor rect"):
        TR.transplant_region("MOD", cell=(4, 2), donor=(23, 1), size=(2, 1), dry_run=True)
    with pytest.raises(ValueError, match="target rect"):
        TR.transplant_region("MOD", cell=(23, 2), donor=(1, 1), size=(2, 1), dry_run=True)
    # rot 90 swaps the target rect: 1x2 must fit vertically
    with pytest.raises(ValueError, match="target rect"):
        TR.transplant_region("MOD", cell=(4, 19), donor=(1, 1), size=(2, 1), rot=90, dry_run=True)
    # a real block anywhere in the target rect refuses (unless expert-overridden)
    blocks2 = dict(blocks)
    blocks2[(5, 2, "terrain")] = _quad(320.0, 384.0, -192.0, -128.0)
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks2))
    with pytest.raises(ValueError, match="REAL world block"):
        TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), dry_run=True)
    # an all-ocean donor rect refuses
    monkeypatch.setattr(TR, "world_tris", _fake_world({}))
    with pytest.raises(ValueError, match="no block mesh data"):
        TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), dry_run=True)


# ------------------------------------------------- region growth (cut laws on a multi-cell base)

def test_cut_census_region_empty_cell_laws(monkeypatch):
    """A REGION cut's shift is global, but the seam extrusion fills only at its planes -- so an
    empty donor cell creates discontinuities (the (9,5)+2x3 row-0 hole, 2026-07-09): east-
    neighbour data slides off a shared border, west-neighbour data slides INTO the empty cell
    (`spills-into-empty`, always disqualifying). A vacated border whose on-plane content is pure
    OPEN WATER is FILLABLE (reported in `boundary_fills`, the multi-boundary extrusion); any
    other language on it keeps `gap-vacation`. Lines east of the empty cell stay clean."""
    blocks = {  # donor rect (1,1)+3x1: EMPTY | data | data
        (2, 1, "terrain"): _quad(140.0, 156.0, -104.0, -88.0, y=1.0),
        (2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=232.0),
        (3, 1, "terrain"): _quad(192.0, 204.0, -104.0, -88.0, y=1.0),
        (3, 1, "sea4"): _quad(192.0, 256.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    cen = {c["line"]: c for c in TR.cut_census((1, 1), size=(3, 1))}
    assert len(cen) == 47                                      # every interior 4u line of 3 cells
    # cell (1,1) is empty, (2,1) east of it has data: lines <= their border x=128 vacate a gap
    # -- the border is pure sea4, so the gap is FILLABLE, not a risk
    assert cen[80.0]["risks"] == [] and cen[80.0]["boundary_fills"] == [[128.0, -128.0, -64.0]]
    assert cen[128.0]["boundary_fills"] == [[128.0, -128.0, -64.0]]
    assert cen[80.0]["clean"] is True and cen[80.0]["ok"] is False     # water: a SLIDE line
    assert cen[132.0]["boundary_fills"] == []                  # east of the border: no gap
    # an UNFILLABLE border -- land ends exactly ON it -- keeps the gap-vacation risk
    blocks_land = dict(blocks)
    blocks_land[(2, 1, "terrain")] = _quad(128.0, 156.0, -104.0, -88.0, y=1.0)
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks_land))
    cen_l = {c["line"]: c for c in TR.cut_census((1, 1), size=(3, 1))}
    assert "gap-vacation" in cen_l[80.0]["risks"] and cen_l[80.0]["boundary_fills"] == []
    assert cen_l[80.0]["clean"] is False
    # the mirror law needs data WEST of an empty cell: rect (2,1)+2x1 = data | empty... reuse
    blocks2 = {(2, 1, "terrain"): _quad(140.0, 156.0, -104.0, -88.0, y=1.0),
               (2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks2))
    cen2 = {c["line"]: c for c in TR.cut_census((2, 1), size=(2, 1))}
    assert "spills-into-empty" in cen2[160.0]["risks"]         # west-of-the-empty-cell border
    assert "spills-into-empty" in cen2[192.0]["risks"]         # exactly at it
    assert all("gap-vacation" not in c["risks"] for c in cen2.values())


def test_region_boundary_fill_covers_empty_cell_gap(monkeypatch):
    """THE MULTI-BOUNDARY SEAM EXTRUSION (the gap-vacation kill, 2026-07-09): a cut west of an
    empty cell's east border slides the east cell's content off it; the boundary fill extrudes
    the east side's seam profile ``+delta`` into the vacated band -- west edge = the bit-exact
    pre-shift boundary profile (the original SeaBlockPrefab join), east edge welding to the
    shifted content BY IDENTITY -- and the placement census stays hole-free."""
    blocks = {(2, 1, "terrain"): _quad(152.0, 168.0, -104.0, -88.0, y=1.0),
              (2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=228.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    cen = {c["line"]: c for c in TR.cut_census((1, 1), size=(2, 1))}
    assert cen[100.0]["clean"] is True and cen[100.0]["risks"] == []
    assert cen[100.0]["boundary_fills"] == [[128.0, -128.0, -64.0]]
    tweaks = TR.chain_row_inserts([100.0], boundaries=cen[100.0]["boundary_fills"])
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                             tweaks=tweaks, land_margin=0.0, census_samples=8, dry_run=True)
    assert s["clean"] is True, s["gates"]
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["introduced"] == 0
    ri = next(g for g in s["gates"] if g["gate"] == "rowinsert[sea4]")
    assert ri["boundary_fills"] == {"128": 2}          # one full-height band = two tris
    rt = next(g for g in s["gates"] if g["gate"] == "rowinsert[terrain]")
    assert rt["ok"] is True and rt["boundary_fills"] == {"128": 0}   # owes nothing at water
    # the fill band's verts: west edge bit-exact ON the plane, east edge = the same profile
    # +delta (identity with the shifted content)
    fill = [t for t in tweaks[[tw.part for tw in tweaks].index("sea4")].emit()]
    xs = sorted({round(v[0][0], 6) for t in fill for v in t})
    assert xs == [128.0, 132.0]


def test_region_boundary_fill_windowed_to_empty_rows(monkeypatch):
    """The fill's z-window law: only the EMPTY cell's row gets boundary bands -- a data row
    crossing the same border shifts contiguously and must NOT be double-covered (the line
    fill owns its gap there instead)."""
    blocks = {(2, 1, "sea4"): _quad(128.0, 192.0, -128.0, -64.0, idall=228.0),
              (1, 2, "sea4"): (_quad(64.0, 100.0, -192.0, -128.0, idall=228.0)
                               + _quad(100.0, 128.0, -192.0, -128.0, idall=228.0)),
              (2, 2, "sea4"): _quad(128.0, 192.0, -192.0, -128.0, idall=228.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    cen = {c["line"]: c for c in TR.cut_census((1, 1), size=(2, 2))}
    assert cen[100.0]["clean"] is True
    assert cen[100.0]["boundary_fills"] == [[128.0, -128.0, -64.0]]   # row 0's window only
    tweaks = TR.chain_row_inserts([100.0], boundaries=cen[100.0]["boundary_fills"])
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 2), shift=(0.0, 0.0),
                             tweaks=tweaks, land_margin=0.0, census_samples=8, dry_run=True)
    assert s["clean"] is True, s["gates"]
    ri = next(g for g in s["gates"] if g["gate"] == "rowinsert[sea4]")
    assert ri["boundary_fills"] == {"128": 2}          # the empty row's band only
    assert ri["emitted"] == 4                          # + the row-1 LINE fill (2 tris)
    # every boundary-band tri sits inside the empty row's z-window
    fill = tweaks[[tw.part for tw in tweaks].index("sea4")].emit()
    band = [t for t in fill if all(v[0][0] >= 128.0 - 1e-6 for v in t)]
    assert band and all(-128.0 - 1e-6 <= v[0][2] <= -64.0 + 1e-6 for t in band for v in t)


def test_chain_row_inserts_boundary_composition():
    """Boundary planes ride the same cumulative +i*delta correction as the lines (each cut's
    band tiles against the one before), and a cut east of a plane never owes it a fill."""
    tws = TR.chain_row_inserts([100.0, 108.0], parts=("sea4",),
                               boundaries=[(128.0, -128.0, -64.0), (104.0, -128.0, -64.0)])
    assert [tw.line for tw in tws] == [100.0, 112.0]
    assert [st["plane"] for st in tws[0]._bnd] == [104.0, 128.0]
    assert [st["plane"] for st in tws[1]._bnd] == [132.0]      # 104 < 108: not owed
    with pytest.raises(ValueError):
        TR.RowInsert("sea4", line=100.0, boundaries=[(96.0, -128.0, -64.0)])


def test_split_border_pairs():
    """Interior-border weld classification (the non-easternmost-cut law): an off-lattice float
    next to a bit-exact clip vert on the border plane is a benign clip T-junction (the 592
    build's two undiagnosed x=64 pairs); an all-on-plane CLUSTER with no off-plane witness =
    the cells disagree about the shared profile = a crack; pairs away from any border stay
    cracks. Clusters judge together: a float so close to the border that both its edges' cut
    verts pair with each other (the (9,5) z-cut's A-C-B corner sliver) is still ONE benign
    T-junction -- the off-plane witness vindicates the whole cluster."""
    t_pair = ((63.976562, 2.0, -100.35), (64.0, 2.0, -100.351563))
    crack = ((64.0, 2.0, -80.0), (64.0, 2.04, -80.01))
    off = ((30.0, 0.0, -20.0), (30.01, 0.0, -20.0))
    cracks, ts = TR._split_border_pairs([t_pair, crack, off], (64.0,), ())
    assert ts == [t_pair] and sorted(cracks) == sorted([crack, off])
    # the corner-sliver cluster: A, B exact on-plane, C the off-plane witness (real values
    # from the (9,5)+2x3 z=-352 build's row border)
    A, B = (87.266514, 10.256452, -64.0), (87.286678, 10.269531, -64.0)
    C = (87.28125, 10.269531, -64.019531)
    cracks2, ts2 = TR._split_border_pairs([(A, B), (A, C), (B, C)], (), (-64.0,))
    assert cracks2 == [] and sorted(ts2) == sorted([(A, B), (A, C), (B, C)])
    # the same A-B pair WITHOUT its witness stays a crack (profile disagreement)
    cracks3, ts3 = TR._split_border_pairs([(A, B)], (), (-64.0,))
    assert cracks3 == [(A, B)] and ts3 == []


def test_z_frame_roundtrip_exact():
    """The z-adapter frame map is a swap + sign flip + power-of-two shift -- BIT-EXACT both
    ways on off-lattice donor floats (the weld-by-identity laws depend on it)."""
    poly = [_v(496.046875, 3.2109375, -1120.828125), _v(0.0, 0.0, -0.015625),
            _v(1535.984375, 26.5, -64.0)]
    back = TR._z_out_poly(TR._z_in_poly(poly))
    assert [v[0] for v in back] == [v[0] for v in poly]
    assert TR._z_in_poly(poly)[0][0] == (1120.828125, 3.2109375, 496.046875 - 2048.0)


def test_row_insert_z_grows_island_south(monkeypatch):
    """The z-axis growth seed (the exact-rotation adapter over the proven x-cut): a whole
    lattice ROW inserted at a z plane -- everything south shifts -delta, the vacated row is
    seam-extruded, welds bit-exact, and the island grows southward by delta."""
    LINE = -96.0
    blocks = {
        # two grass tiles astride the z cut line (topo 0 -> mains fill + relief center)
        (1, 1, "terrain"): (_quad(88.0, 92.0, -96.0, -92.0, y=1.0, idall=12544.0, uv=(0.03, 0.78))
                            + _quad(88.0, 92.0, -100.0, -96.0, y=1.0, idall=12544.0, uv=(0.09, 0.81))),
        # sea4 as two slabs meeting exactly ON the line (mirror-affine fill)
        (1, 1, "sea4"): (_quad(64.0, 128.0, -96.0, -64.0, idall=228.0)
                         + _quad(64.0, 128.0, -128.0, -96.0, idall=228.0)),
    }
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    tweaks = [TR.RowInsertZ(p, line=LINE) for p in TR.PARTS]
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), shift=(0.0, 0.0), land_margin=0.0,
                      tweaks=tweaks, dry_run=True, census_samples=8)
    assert s["clean"] is True, s["gates"]
    gt = next(g for g in s["gates"] if g["gate"] == "rowinsertz[terrain]")
    gs = next(g for g in s["gates"] if g["gate"] == "rowinsertz[sea4]")
    assert gt["shifted"] == 2 and gt["emitted"] == 4          # grass relief fan
    assert gs["shifted"] == 2 and gs["emitted"] == 2          # flat mirror fill
    # the island grew south by exactly delta: the south grass tile now ends at -104 -> local -40
    lf = next(g for g in s["gates"] if g["gate"] == "land-fit")
    assert lf["bbox"][2] == pytest.approx(-40.0)
    assert next(g for g in s["gates"] if g["gate"] == "weld-audit")["pairs"] == 0
    # every fill tri is up-facing in WORLD frame (winding survives the rotation round trip)
    for t in tweaks[[tw.part for tw in tweaks].index("sea4")].emit():
        ux, uz = t[1][0][0] - t[0][0][0], t[1][0][2] - t[0][0][2]
        vx, vz = t[2][0][0] - t[0][0][0], t[2][0][2] - t[0][0][2]
        assert uz * vx - ux * vz > 0


def test_row_insert_z_inverse_and_chain():
    """inverse_z mirrors inverse_x southward; chain_row_inserts_z applies north-to-south
    with the -i*delta correction, and a cut south of a boundary plane never owes it."""
    tw = TR.RowInsertZ("terrain", line=-96.0)
    assert tw.inverse_z(-90.0) == -90.0                        # north of the cut: identity
    assert tw.inverse_z(-104.0) == -100.0                      # shifted content maps back +4
    assert tw.inverse_z(-98.0) == -96.0                        # the fill row maps to the seam
    tws = TR.chain_row_inserts_z([-96.0, -88.0], parts=("sea4",),
                                 boundaries=[(-128.0, 64.0, 128.0), (-92.0, 64.0, 128.0)])
    assert [t.line for t in tws] == [-88.0, -100.0]
    assert sorted(tws[0].gate()["boundary_fills"]) == ["-128", "-92"]
    assert sorted(tws[1].gate()["boundary_fills"]) == ["-132"]   # -92 not owed; -128 rides -4
    inv = TR._tweak_inverse_z(tws)
    assert inv(-112.0) == -104.0                               # both cuts undone, south-to-north
    with pytest.raises(ValueError):
        TR.RowInsertZ("sea4", line=-96.0, boundaries=[(-90.0, 64.0, 128.0)])  # north of the cut


def test_cut_census_axis_z(monkeypatch):
    """axis='z' sweeps the region's interior z planes via the exact-rotation adapter; the
    component + empty-cell laws transpose (a data-south-neighbour border is fillable when
    pure water; a land z-line grows southward; spills fires south of a data cell)."""
    blocks = {(1, 2, "terrain"): _quad(88.0, 104.0, -168.0, -152.0, y=1.0),
              (1, 2, "sea4"): (_quad(64.0, 128.0, -152.0, -128.0, idall=228.0)
                               + _quad(64.0, 128.0, -192.0, -152.0, idall=228.0))}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    # rect (1,1)+1x2: EMPTY north cell over the data south cell
    cen = {c["line"]: c for c in TR.cut_census((1, 1), size=(1, 2), axis="z")}
    assert len(cen) == 31 and all(c["axis"] == "z" for c in cen.values())
    assert cen[-100.0]["clean"] is True and cen[-100.0]["risks"] == []
    assert cen[-100.0]["boundary_fills"] == [[-128.0, 64.0, 128.0]]
    assert cen[-100.0]["ok"] is False                          # water: a slide line
    assert cen[-152.0]["ok"] is True and cen[-152.0]["grows_land"] is True   # a land z-line
    assert cen[-152.0]["boundary_fills"] == []                 # south of the empty border
    # spills transposed: rect (1,2)+1x2 = data north | empty south
    cen2 = {c["line"]: c for c in TR.cut_census((1, 2), size=(1, 2), axis="z")}
    assert "spills-into-empty" in cen2[-160.0]["risks"]


def test_region_z_boundary_fill_covers_gap(monkeypatch):
    """The multi-boundary extrusion transposed: a z-cut through the empty north cell slides
    the south cell's content off their border; the boundary fill extrudes the border profile
    southward and the region census stays hole-free."""
    blocks = {(1, 2, "terrain"): _quad(88.0, 104.0, -168.0, -152.0, y=1.0),
              (1, 2, "sea4"): (_quad(64.0, 128.0, -152.0, -128.0, idall=228.0)
                               + _quad(64.0, 128.0, -192.0, -152.0, idall=228.0))}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    cen = {c["line"]: c for c in TR.cut_census((1, 1), size=(1, 2), axis="z")}
    tweaks = TR.chain_row_inserts_z([-100.0], boundaries=cen[-100.0]["boundary_fills"])
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(1, 2), shift=(0.0, 0.0),
                             tweaks=tweaks, land_margin=0.0, census_samples=8, dry_run=True)
    assert s["clean"] is True, s["gates"]
    ri = next(g for g in s["gates"] if g["gate"] == "rowinsertz[sea4]")
    assert ri["boundary_fills"] == {"-128": 2}                 # one band, two tris
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["introduced"] == 0
    # the band sits exactly in the vacated row [-132, -128], inside the empty cell's x-window
    fill = tweaks[[tw.part for tw in tweaks].index("sea4")].emit()
    band = [t for t in fill if all(v[0][2] <= -128.0 + 1e-6 for v in t)]
    assert band and all(-132.0 - 1e-6 <= v[0][2] for t in band for v in t)


def test_hairline_fragment_carries_and_ledger_gates(monkeypatch):
    """THE HAIRLINE LAW (in-game 2026-07-09, "a seam in the cliff"): a thin-but-real clip
    fragment is surface and must CARRY -- only true collinear degenerates drop. The clip-drop
    ledger gate accounts every dropped area2 (real dropped area = a hole in the making)."""
    blocks = _island_donor()
    # a 0.005u-wide sliver at the frame edge: REAL surface under the hairline law
    blocks[(1, 1, "beach1")] = _quad(127.995, 128.0, -100.0, -96.0, idall=12920.0)
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), census_samples=8, land_margin=0.0,
                      dry_run=True)
    assert s["blanked"] == [] and s["carried"]["beach1"] >= 1        # carried, not blanked
    cd = next(g for g in s["gates"] if g["gate"] == "clip-drop")
    assert cd["ok"] is True and cd["area2"] < 1e-3


def test_cut_census_lattice_seam_law(monkeypatch):
    """THE LATTICE-SEAM LAW: an off-lattice on-line vert in an OPEN-WATER part flags
    `conforming-on-line` (the unclamped mirror fill wraps the atlas between off-lattice
    seam verts -- the "stretched" tiles, in-game 2026-07-09); TERRAIN off-lattice verts
    stay legal (grass/rock/wash fills are position-generated or clamped)."""
    base = {(1, 1, "sea4"): (_quad(64.0, 92.0, -128.0, -64.0, idall=228.0)
                             + _quad(92.0, 128.0, -128.0, -64.0, idall=228.0))}
    # a shore-conforming water tri touching the line at an off-lattice z
    conform = [[_v(92.0, 0.0, -90.35, idall=228.0), _v(92.0, 0.0, -94.0, idall=228.0),
                _v(96.0, 0.0, -94.0, idall=228.0)]]
    blocks = dict(base)
    blocks[(1, 1, "sea4")] = base[(1, 1, "sea4")] + conform
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    cen = {c["line"]: c for c in TR.cut_census((1, 1))}
    assert "conforming-on-line" in cen[92.0]["risks"]
    # the same off-lattice vert as TERRAIN does not flag
    blocks2 = dict(base)
    blocks2[(1, 1, "terrain")] = [[_v(92.0, 1.0, -90.35), _v(92.0, 1.0, -94.0),
                                   _v(96.0, 1.0, -94.0)]]
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks2))
    cen2 = {c["line"]: c for c in TR.cut_census((1, 1))}
    assert "conforming-on-line" not in cen2[92.0]["risks"]
    # a boundary with an off-lattice on-plane water vert is UNFILLABLE (gap-vacation)
    blocks3 = {(2, 1, "sea4"): (_quad(128.0, 192.0, -128.0, -90.35, idall=228.0)
                                + _quad(128.0, 192.0, -90.35, -64.0, idall=228.0))}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks3))
    cen3 = {c["line"]: c for c in TR.cut_census((1, 1), size=(2, 1))}
    assert "gap-vacation" in cen3[100.0]["risks"] and cen3[100.0]["boundary_fills"] == []


def _painted(x0, x1, z0, z1, *, y, idall, uv_fn):
    """A terrain quad whose UV comes from a per-vertex generator (real affine field,
    unlike `_quad`'s single uniform uv) -- the shape `_cell_rect` needs to fingerprint a
    tile's family."""
    a = (x0, y, z1); b = (x1, y, z1); c = (x1, y, z0); d = (x0, y, z0)
    corners = [a, b, c, d]
    verts = [(p, NRM, uv_fn(p[0], p[2]), (idall, 0.0, 0.0, 1.0)) for p in corners]
    return [[verts[0], verts[1], verts[3]], [verts[1], verts[2], verts[3]]]


def test_cut_census_baked_terrain_law(monkeypatch):
    """THE BAKED-TERRAIN LAW (the highland-vocabulary decode, 2026-07-09): a terrain
    family RowInsert has no dedicated fill for (not grass/sand/cliff) whose UV rect has NO
    sibling elsewhere in the scanned donor+strip area is a hand-painted mural -- same class
    as a topo-0 wash, detected generically by UV-rect uniqueness rather than a hardcoded
    topo id, so a genuinely REPEATING rock patch stays fair game while a one-off painted
    tile flags."""
    from ff9mapkit.world.extract import encode_id
    BAKED_ID = float(encode_id(event=0, area=0, topograph=40))     # a singleton mural tile
    TILED_ID = float(encode_id(event=0, area=0, topograph=41))     # a repeating rock tile

    # a REPEATING family: the SAME local (u,v) pattern (position MOD 4) reused at two
    # ADJACENT 4u cells -- two real siblings, so the shared line between them stays clean
    # even though this topo has no dedicated RowInsert fill either
    def tiled_uv(x, z):
        return ((x % 4.0) / 4.0 * 0.1 + 0.2, (z % 4.0) / -4.0 * 0.1 + 0.5)
    tiled_a = _painted(80.0, 84.0, -100.0, -96.0, y=1.0, idall=TILED_ID, uv_fn=tiled_uv)
    tiled_b = _painted(84.0, 88.0, -100.0, -96.0, y=1.0, idall=TILED_ID, uv_fn=tiled_uv)

    # a BAKED singleton, isolated (not touching the tiled pair): uv is a function of
    # ABSOLUTE position -- no other cell shares this exact rect (a one-off painted mural
    # tile, like the real topo 17/38/49); BOTH its edges (92 and 96) touch only itself
    def baked_uv(x, z):
        return (x / 2000.0, z / -2000.0)
    baked = _painted(92.0, 96.0, -100.0, -96.0, y=1.0, idall=BAKED_ID, uv_fn=baked_uv)

    blocks = {(1, 1, "terrain"): tiled_a + tiled_b + baked}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    cen = {c["line"]: c for c in TR.cut_census((1, 1))}
    assert "crosses-baked-terrain" not in cen[84.0]["risks"]  # the repeating rock: clean
    assert "crosses-baked-terrain" in cen[92.0]["risks"]      # the singleton mural: flags
    assert "crosses-baked-terrain" in cen[96.0]["risks"]      # its OTHER edge: flags too

    # the SAME baked tile, now with a real sibling elsewhere in the donor+strip scan (its
    # neighbour E of the donor happens to reuse the identical mural rect -- an artist
    # copy-paste, shifted 40u so the rect matches exactly) -- no longer a singleton
    sibling_uv = lambda x, z: baked_uv(x - 40.0, z)
    blocks2 = {(1, 1, "terrain"): tiled_a + tiled_b + baked,
              (2, 1, "terrain"): _painted(132.0, 136.0, -100.0, -96.0, y=1.0, idall=BAKED_ID,
                                          uv_fn=sibling_uv)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks2))
    cen2 = {c["line"]: c for c in TR.cut_census((1, 1))}
    assert "crosses-baked-terrain" not in cen2[92.0]["risks"]


def test_census_backmap_inverts_row_insert(monkeypatch):
    """The miss-backmap must UNDO RowInsert cuts before querying the donor -- else the donor's
    own in-situ misses shift out from under it and misread as introduced (the x=107/115
    misclassification, 2026-07-09). Donor (2,1) misses on its east half in situ; after a cut
    the same holes sit +4 east and must still classify INHERITED."""
    blocks = {(1, 1, "terrain"): (_quad(88.0, 92.0, -100.0, -96.0, y=1.0, idall=12544.0,
                                        uv=(0.03, 0.78))
                                  + _quad(92.0, 96.0, -100.0, -96.0, y=1.0, idall=12544.0,
                                          uv=(0.09, 0.81))),
              (1, 1, "sea4"): (_quad(64.0, 92.0, -128.0, -64.0, idall=232.0)
                               + _quad(92.0, 128.0, -128.0, -64.0, idall=232.0)),
              (2, 1, "sea4"): _quad(128.0, 160.0, -128.0, -64.0, idall=232.0)}  # east half MISSES
    monkeypatch.setattr(TR, "world_tris", _fake_world(blocks))
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), shift=(0.0, 0.0),
                             tweaks=TR.chain_row_inserts([92.0]), land_margin=0.0,
                             census_samples=8, dry_run=True)
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["miss"] > 0 and census["introduced"] == 0
    assert census["inherited"] == census["miss"] and s["clean"] is True, s["gates"]


def test_row_insert_inverse_x():
    tw = TR.RowInsert("terrain", line=92.0)
    assert tw.inverse_x(88.0) == 88.0                          # west of the cut: identity
    assert tw.inverse_x(100.0) == 96.0                         # shifted content maps back -4
    assert tw.inverse_x(94.0) == 92.0                          # the fill column maps to the seam
    inv = TR._tweak_inverse_x(TR.chain_row_inserts([88.0, 92.0], parts=("terrain",)))
    assert inv(104.0) == 96.0                                  # both cuts undone, east-to-west


def test_split_frame_pairs():
    """A near-miss pair with BOTH verts on the same frame plane is a clip-boundary T-junction
    (benign -- the surface is continuous up to the frame); interior pairs remain cracks."""
    at_frame = ((127.976562, 0.0, -75.824219), (128.0, 0.0, -75.825243))
    interior = ((64.0, 9.28, -108.35), (64.042969, 9.30, -108.355469))
    inn, fr = TR._split_frame_pairs([at_frame, interior], (0.0, 128.0), (0.0, -192.0))
    assert fr == [at_frame] and inn == [interior]
    # BOTH verts must sit in the band -- one on the plane, one just outside stays interior
    half = ((60.0, 0.0, -0.02), (60.01, 0.0, -0.06))
    inn2, fr2 = TR._split_frame_pairs([half], (0.0, 128.0), (0.0, -192.0))
    assert inn2 == [half] and fr2 == []


# ---------------------------------------------------------------- game-data-gated

def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_transplant_proven_island_rot90():
    """The in-game-proven configuration (island_morph v4, "it holds" 2026-07-08): donor (7,17) +
    its (8,17) tongue, ROT 90, auto-shift (0,-8) -- every gate clean, all 7 parts carried."""
    s = TR.transplant("UNUSED", cell=(4, 2), donor=TR.PROVEN_DONOR, rot=90, dry_run=True)
    assert s["clean"] is True, s["gates"]
    assert s["strips"] == ["E"] and s["shift"] == [0.0, -8.0]
    assert all(s["carried"][p] > 0 for p in TR.PARTS)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_transplant_region_2x3_island():
    """The multi-cell carry configuration (first deployed 2026-07-09): the (9,5)+2x3 cliff
    island -- the game's ONLY fully-clean multi-block landmass (zero foreign land in its rect,
    no objects, 4u margin; screened by land-component flood fill over all 260 data blocks) --
    carried verbatim (identity transform) to the (9,9)+2x3 ocean rect. 5 data cells deploy
    with natural per-cell donor sidecars, the rect's empty corner cell is skipped, the
    cross-cell weld audit is 0 and the census introduces no misses."""
    s = TR.transplant_region("UNUSED", cell=(9, 9), donor=(9, 5), size=(2, 3),
                             shift=(0.0, 0.0), dry_run=True)
    assert s["clean"] is True, s["gates"]
    assert sorted(s["cells"]) == ["10,10", "10,11", "10,9", "9,10", "9,11"]   # (9,9) skipped
    for key, meta in s["cells"].items():
        (cx, cy) = (int(v) for v in key.split(","))
        assert meta["donor"] == [cx, cy - 4]              # natural sidecar, 4 rows north
        assert meta["carried"]["terrain"] > 0 and meta["carried"]["sea4"] > 0
    # 917 = 879 flat/sloped + the 38 vertical topo-38 forest-wall tris (the wall law)
    assert s["carried"]["terrain"] == 917 and s["carried"]["sea4"] == 1993
    assert next(g for g in s["gates"] if g["gate"] == "weld-audit")["pairs"] == 0
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["introduced"] == 0 and census["samples"] == 2880


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_region_growth_cut_config():
    """The first REGION growth cut attempt (2026-07-09, in-game FAILED and reverted): the one
    structurally-clean line -- 672 -- crosses the 26.5u MOUNTAIN, which the fill extrusion
    cannot faithfully cross ("seaming errors on both sides of the mountain") -- now the
    `crosses-relief` law, so this rect has ZERO usable land-GROWTH lines even after the
    multi-boundary unlock (640/672 are the only land lines and both cross the relief). The
    mechanics gates themselves stay green on the 672 config (fills across the region,
    tweak-inverted backmap, the single weld pair a benign frame T-junction) -- kept as the
    region-cut mechanics regression; the LAW is what rejects it."""
    cen = {c["line"]: c for c in TR.cut_census((9, 5), size=(2, 3))}
    assert [l for l, c in cen.items() if c["ok"]] == []
    assert "crosses-relief" in cen[672.0]["risks"] and "crosses-relief" in cen[640.0]["risks"]
    s = TR.transplant_region("UNUSED", cell=(11, 1), donor=(9, 5), size=(2, 3),
                             shift=(0.0, 0.0), tweaks=TR.chain_row_inserts([672.0]),
                             land_margin=0.0, dry_run=True)
    assert s["clean"] is True, s["gates"]
    ri = next(g for g in s["gates"] if g["gate"] == "rowinsert[terrain]")
    assert ri["shifted"] == 310 and ri["emitted"] == 50
    weld = next(g for g in s["gates"] if g["gate"] == "weld-audit")
    assert weld["pairs"] == 0 and weld["frame_pairs"] == 1 and weld["border_t_pairs"] == 0
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["inherited"] == 2 and census["introduced"] == 0


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_region_water_slide_cut_config():
    """THE MULTI-BOUNDARY UNLOCK on the real (9,5)+2x3 island (deployed 2026-07-09): the flat
    pure-sea4 lines 580-608 -- previously ALL disqualified by gap-vacation from the empty
    corner cell -- are now census-CLEAN slide cuts, each requiring one boundary fill at the
    empty cell's east border x=640 (window = the empty row z[-384,-320], certified pure open
    water). The 592 cut slides the whole island +4u east in proven water language; its two
    interior weld pairs at the x=64 border (the rejected build's undiagnosed signature)
    classify as benign clip T-junctions."""
    cen = {c["line"]: c for c in TR.cut_census((9, 5), size=(2, 3))}
    for line in (580.0, 592.0, 604.0):
        assert cen[line]["clean"] is True and cen[line]["risks"] == []
        assert cen[line]["boundary_fills"] == [[640.0, -384.0, -320.0]]
        assert cen[line]["ok"] is False                    # pure water: a slide, not growth
    # 608 hugs the west shore: an off-lattice water vert sits ON it (the lattice-seam law)
    assert cen[608.0]["risks"] == ["conforming-on-line"]
    tweaks = TR.chain_row_inserts([592.0], boundaries=cen[592.0]["boundary_fills"])
    s = TR.transplant_region("UNUSED", cell=(11, 1), donor=(9, 5), size=(2, 3),
                             shift=(0.0, 0.0), tweaks=tweaks, land_margin=0.0, dry_run=True)
    assert s["clean"] is True, s["gates"]
    ri = next(g for g in s["gates"] if g["gate"] == "rowinsert[sea4]")
    assert ri["shifted"] == 1829 and ri["emitted"] == 96   # 64 line + 32 boundary tris
    assert ri["boundary_fills"] == {"640": 32}
    rt = next(g for g in s["gates"] if g["gate"] == "rowinsert[terrain]")
    assert rt["shifted"] == 917 and rt["emitted"] == 0     # the island slides whole
    assert rt["ok"] is True and rt["boundary_fills"] == {"640": 0}
    weld = next(g for g in s["gates"] if g["gate"] == "weld-audit")
    assert weld["pairs"] == 0 and weld["border_t_pairs"] == 2
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["inherited"] == 2 and census["introduced"] == 0
    assert sorted(s["cells"]) == ["11,2", "11,3", "12,1", "12,2", "12,3"]   # (11,1) skipped


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_region_z_slide_cut_config():
    """THE Z-AXIS VARIANT on the real (9,5)+2x3 island (redeployed 2026-07-09 at line -332
    after the -352 build's two in-game defects): every land z-line is ALSO crosses-relief --
    the mountain blocks both axes, so this donor's land is un-growable on any axis (a
    component fact, not a mechanics gap). The first z-line tried, -352, hugged the north
    shore: shore-conforming water verts ON it made the mirror fill wrap the atlas
    ("stretched" tiles in-game) -- now the LATTICE-SEAM law flags it `conforming-on-line`.
    The legal -332 slide exercises the TRANSPOSED multi-boundary fill at the empty corner
    cell's SOUTH border z=-384 (window x[576,640], lattice-certified). The island slides 4u
    SOUTH whole; the A-C-B corner-sliver weld cluster at the row border classifies benign;
    the clip-drop ledger and border micro-census (the hairline law's gates) run clean."""
    cen = {c["line"]: c for c in TR.cut_census((9, 5), size=(2, 3), axis="z")}
    assert [l for l, c in cen.items() if c["ok"]] == []        # no land z-growth either
    for line in (-384.0, -416.0, -448.0):
        assert "crosses-relief" in cen[line]["risks"]
    assert cen[-352.0]["risks"] == ["conforming-on-line"]      # the in-game-failed line
    assert cen[-332.0]["clean"] is True and cen[-332.0]["risks"] == []
    assert cen[-332.0]["boundary_fills"] == [[-384.0, 576.0, 640.0]]
    tweaks = TR.chain_row_inserts_z([-332.0], boundaries=cen[-332.0]["boundary_fills"])
    s = TR.transplant_region("UNUSED", cell=(0, 4), donor=(9, 5), size=(2, 3),
                             shift=(0.0, 0.0), tweaks=tweaks, land_margin=0.0, dry_run=True)
    assert s["clean"] is True, s["gates"]
    ri = next(g for g in s["gates"] if g["gate"] == "rowinsertz[sea4]")
    assert ri["shifted"] == 2066 and ri["emitted"] == 68       # 36 line + 32 boundary tris
    assert ri["boundary_fills"] == {"-384": 32}
    rt = next(g for g in s["gates"] if g["gate"] == "rowinsertz[terrain]")
    assert rt["shifted"] == 917 and rt["emitted"] == 0         # the island slides whole
    weld = next(g for g in s["gates"] if g["gate"] == "weld-audit")
    assert weld["pairs"] == 0 and weld["border_t_pairs"] == 5
    census = next(g for g in s["gates"] if g["gate"] == "census")
    assert census["inherited"] == 2 and census["introduced"] == 0
    assert next(g for g in s["gates"] if g["gate"] == "clip-drop")["ok"] is True
    bc = next(g for g in s["gates"] if g["gate"] == "border-census")
    assert bc["holes"] == 0 and bc["probed"] == 640
    assert sorted(s["cells"]) == ["0,5", "0,6", "1,4", "1,5", "1,6"]      # (0,4) skipped


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_cut_census_relief_law_spares_proven_lines():
    """The relief threshold must NOT disqualify the in-game-proven single-cell cuts (their
    on-line land y-spans measured <= 3.5u vs the mountain's 26.5u). It DOES flag this donor's
    never-cut 7u headland line 1028 -- conservative, never falsified there."""
    cen = {c["line"]: c for c in TR.cut_census((16, 17))}
    assert cen[1060.0]["ok"] is True
    assert "crosses-relief" not in cen[1056.0]["risks"]
    assert "crosses-relief" not in cen[1060.0]["risks"]
    assert "crosses-relief" in cen[1028.0]["risks"]
    # the lattice-seam law conservatively flags 1056's shore-contact water (off-lattice
    # verts ON the line) -- proven in-game there, but the law can't tell mild from severe;
    # the build stays deployed as proven (the 508/touches-shallows precedent)
    assert cen[1056.0]["risks"] == ["conforming-on-line"]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_second_donor_screen_10_17_carryable_not_growable():
    """SECOND-DONOR SCREEN (2026-07-09): a slide-window scan (margin>=2u, sizes 2x2..4x4)
    over every data-bearing block found (10,17)+2x2 the best non-(9,5) candidate -- 2 real
    data cells, 22.7u margin, 5.5u relief (under the 6.0u cap), zero objects -- but it is
    CARRYABLE, not GROWABLE: every land line on either axis is blocked, and NOT by relief.
    x-lines: `conforming-on-line` (this donor has a real sea1 shore system, unlike (9,5)'s
    bare cliff+deep-water) + `spills-into-empty` (2 of its 4 rect cells are ocean -- the
    OTHER empty-cell risk, never given an extrusion fix the way `gap-vacation` was).
    z-lines: nonzero straddlers on BOTH candidates -- this donor's mesh isn't 4u-lattice-
    aligned in z at all (real coastal terrain, unlike (9,5)'s clean grid). Net: the (9,5)
    family's small-clean-multi-block-landmass property does NOT generalize; deployed
    (identity carry, no tweaks) at (9,3)+2x2 as the second real multi-cell reference."""
    s = TR.transplant_region("UNUSED", cell=(9, 3), donor=(10, 17), size=(2, 2),
                             shift=(0.0, 0.0), land_margin=2.0, dry_run=True)
    assert s["clean"] is True, s["gates"]
    assert s["carried"]["terrain"] == 63 and s["carried"]["sea1"] == 4

    censuses = {axis: {c["line"]: c for c in TR.cut_census((10, 17), size=(2, 2), axis=axis)}
                for axis in ("x", "z")}
    x_land = {l: c for l, c in censuses["x"].items() if c["grows_land"]}
    assert len(x_land) == 4 and all(not c["ok"] for c in x_land.values())
    assert all("conforming-on-line" in c["risks"] and "spills-into-empty" in c["risks"]
              for l, c in x_land.items() if c["straddlers"] == 0)
    z_land = {l: c for l, c in censuses["z"].items() if c["grows_land"]}
    assert len(z_land) == 2 and all(c["straddlers"] > 0 for c in z_land.values())
