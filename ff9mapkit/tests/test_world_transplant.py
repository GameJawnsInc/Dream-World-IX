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


def test_transplant_blanks_fully_clipped_donor_part(monkeypatch):
    blocks = _island_donor()
    # a beach1 sliver hugging the frame edge: survives the plane clips but dies at the
    # degenerate-area gate -> the whole donor part is gone and MUST be blanked (else the donor
    # prefab's original beach renders unshifted underneath)
    blocks[(1, 1, "beach1")] = _quad(127.999, 128.0, -100.0, -96.0, idall=12920.0)
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
