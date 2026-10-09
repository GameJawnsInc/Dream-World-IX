"""A CUSTOM FORM CELL'S BUILDING IN FORM 2 (engine patches s92 + s93; `world-forms --building2`).

`--building2 X Y none` removes an armed cell's stock building in form 2: a blank `Object2`, and a `Terrain2` whose hole
under the building is filled from the tiles around it (every stock building plugs a hole in its ground). `PATH.obj`
shows another building there (render only; topograph 59 under its footprint), also on a cell with no building (s93).
`keep` removes the `Object2` again. Refused before any write: an unarmed cell, a stock switchable cell, a hole open to
the cell's edge, a kit building (its footprint's topograph 59 is baked into both forms' ground).
"""
from __future__ import annotations

import copy
import warnings

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, extract as X, forms as F, formobject as FO, mesh as M, terrain as T

CELL, BARE, EDGE, STOCK, MIXED, ISLAND = (23, 14), (23, 15), (23, 16), (22, 14), (23, 17), (22, 15)
COND = "(GetEventGlobalByte(1089) & 1) != 0"
HOLE = {(8, 8), (9, 8), (8, 9), (9, 9)}                 # 4u cells (i, j): local x 32..40, z -32..-40
EDGE_HOLE = {(0, 8), (1, 8), (0, 9), (1, 9)}            # touches the cell's west border
GROUND = X.encode_id(topograph=20)
DOOR = X.encode_id(topograph=20, event=1)
RIM = {(i, j) for i in range(7, 11) for j in range(7, 11)} - HOLE   # the ring of tiles round CELL's hole
ISLE = {(i, j) for i in range(6, 10) for j in range(6, 10)}


def _mesh(tris, name, x, y, disc=1):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos, uv, tan = [], [], []
    for t in tris:
        for (p, u, idall) in t:
            pos.append(list(p))
            uv.append(list(u))
            tan.append([float(idall), 0.0, 0.0, 1.0])
    n = len(pos)
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * n, CH_UV: uv, CH_TAN: tan},
                     flat_index=list(range(n)), tris=[[i, i + 1, i + 2] for i in range(0, n, 3)],
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _cells_tris(cells, h=3.0, idall=GROUND):
    """Two tris per 4u cell, each cell's uv an exact tile rect (u = +x, v = -z)."""
    tris = []
    for (i, j) in sorted(cells):
        x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0

        def v(px, pz):
            return ((px, h, pz), (0.10 + 0.05 * (px - x0) / 4.0, 0.60 + 0.05 * (z0 - pz) / 4.0), idall)
        tris.append([v(x0, z0), v(x1, z0), v(x0, z1)])         # up-facing to the engine's ground query
        tris.append([v(x1, z0), v(x1, z1), v(x0, z1)])
    return tris


ALL = {(i, j) for i in range(16) for j in range(16)}


@pytest.fixture
def world(tmp_path, monkeypatch):
    """CELL: ground with a 2x2-tile hole its stock building plugs; BARE: ground, no building; EDGE: a building over a
    hole open to the cell's west border; STOCK: a switchable stock cell."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    (tmp_path / "MOD").mkdir()
    monkeypatch.setattr(T, "_mod_root", lambda mod_folder, game=None: tmp_path / "MOD")

    holes = {CELL: HOLE, EDGE: EDGE_HOLE, MIXED: HOLE | EDGE_HOLE, ISLAND: ALL - ISLE}

    def stock(bx, by, disc=1, lod="0_1", part="terrain", **k):
        if part == "terrain" and (bx, by) in (CELL, BARE, EDGE, STOCK, MIXED, ISLAND):
            hole = holes.get((bx, by), set())
            tris = _cells_tris(ALL - hole - (RIM if (bx, by) == CELL else set()))
            if (bx, by) == CELL:                              # an entrance round the hole: never a fill source
                tris += _cells_tris(RIM, idall=DOOR)
            return _mesh(tris, f"Block[{bx}][{by}] Terrain", bx, by, disc)
        if part == "object" and (bx, by) in holes:
            plug = _cells_tris(holes[(bx, by)], idall=X.encode_id(topograph=59))
            roof = [[((34.0, 9.0, -34.0), (0.2, 0.2), 0), ((38.0, 9.0, -34.0), (0.3, 0.2), 0),
                     ((34.0, 9.0, -38.0), (0.2, 0.3), 0)]]
            return _mesh(plug + roof, f"Block[{bx}][{by}] Object", bx, by, disc)
        raise ValueError("mesh not found")
    monkeypatch.setattr(X, "read_block", stock)
    written = []
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: written.append((copy.deepcopy(bm), k))
                        or tmp_path / f"{bm.name}.ff9mesh")

    def no_copy(paths, **k):
        assert k.get("skip_mirror") == DM.REPLAY, "a form-2 building is planned per disc, never copied"
    monkeypatch.setattr(DM, "auto_mirror", no_copy)
    return tmp_path / "MOD", written


def _arm(root, cell, disc=1):
    F.write_condition(root, disc, *cell, COND)


def _obj(tmp_path, w=2.0, h=6.0):
    p = tmp_path / "tower.obj"
    vs = [(-w, 0, -w), (w, 0, -w), (w, 0, w), (-w, 0, w), (-w, h, -w), (w, h, -w), (w, h, w), (-w, h, w)]
    faces = [(1, 2, 3), (1, 3, 4), (5, 7, 6), (5, 8, 7), (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 8),
             (3, 8, 4), (4, 8, 5), (4, 5, 1)]
    p.write_text("".join(f"v {a} {b} {c}\n" for a, b, c in vs) + "".join(f"f {a} {b} {c}\n" for a, b, c in faces))
    return p


def _soup(bm, cell):
    from ff9mapkit.world.transplant import _soup
    return _soup(bm, *cell)


def _topo(bm, tri):
    return X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]


# ---- removal


def test_remove_blanks_the_building_and_fills_the_hole_under_it(world):
    root, written = world
    _arm(root, CELL)
    res = FO.apply("MOD", *CELL, "none")
    (t2, kt), (o2, ko) = written
    assert kt["part"] == "Terrain2" and ko["part"] == "Object2" and kt["disc"] == ko["disc"] == 1
    assert o2.vcount == 3                                    # the blank: one hidden triangle
    p, = res["plans"]
    assert p["kind"] == "remove" and p["fill"]["hole_u2"] == pytest.approx(64.0, abs=1.0)
    assert p["fill"]["uncovered_u2"] == 0 and p["fill"]["topographs"] == {20: p["fill"]["fill_tris"]}
    def centre(tr):
        return sum(t2.verts[i][0] for i in tr) / 3.0, sum(t2.verts[i][2] for i in tr) / 3.0
    fill = [tr for tr in t2.tris if 32.0 < centre(tr)[0] < 40.0 and -40.0 < centre(tr)[1] < -32.0]
    assert len(fill) >= p["fill"]["fill_tris"] and all(
        X.decode_id(int(round(t2.tangents[tr[0]][0])))["event"] == 0 for tr in fill)   # an entrance is never copied
    # the form-2 ground answers the whole old footprint, and keeps every vertex of the ground it started from
    foot = FO.footprint_points(_soup(X.read_block(*CELL, part="object"), CELL), CELL)
    assert FO._covers(_soup(t2, CELL), foot).all()
    assert p["keep_gate"]["lost"] == 0 and p["keep_gate"]["new_on_border"] == 0
    base = {FO._pk(v) for v in M.world_positions(X.read_block(*CELL), (64.0 * 23, -64.0 * 14))}
    assert base <= {FO._pk(v) for v in M.world_positions(t2, (64.0 * 23, -64.0 * 14))}
    # without the fill the old footprint has no ground at all (what removing the building alone would leave)
    assert not FO._covers(_soup(X.read_block(*CELL), CELL), foot).any()


def test_refusals_come_before_any_write(world, tmp_path):
    root, written = world
    with pytest.raises(ValueError, match="not armed"):
        FO.apply("MOD", *CELL, "none")
    with pytest.raises(ValueError, match="BlackMageVillage"):
        FO.apply("MOD", *STOCK, "none")
    _arm(root, EDGE)
    with pytest.raises(ValueError, match="open to the cell's edge"):
        FO.apply("MOD", *EDGE, "none")
    _arm(root, MIXED)
    with pytest.raises(ValueError, match="still has no ground"):
        FO.apply("MOD", *MIXED, "none")
    _arm(root, ISLAND)                                        # the patch's outer edge is not a hole to fill
    with pytest.raises(ValueError, match="open to the cell's edge"):
        FO.apply("MOD", *ISLAND, "none")
    _arm(root, BARE)
    with pytest.raises(ValueError, match="no building to remove"):
        FO.apply("MOD", *BARE, "none")
    with pytest.raises(ValueError, match="no such OBJ"):
        FO.apply("MOD", *BARE, str(tmp_path / "missing.obj"))
    with pytest.raises(ValueError, match="outside Block"):
        FO.apply("MOD", *BARE, str(_obj(tmp_path)), at=(64.0 * 23 + 63.0, -64.0 * 15 - 32.0))
    # a kit building on a bare cell: its footprint's topograph 59 is in the ground both forms start from
    kit = tmp_path / "MOD" / M.override_relpath(1, *BARE, "0_1", "Object")
    kit.parent.mkdir(parents=True, exist_ok=True)
    M.write_ff9mesh(_mesh(_cells_tris({(3, 3)}), "Block[23][15] Object", *BARE), kit)
    with pytest.raises(ValueError, match="kit Object"):
        FO.apply("MOD", *BARE, "none")
    assert written == []


def test_the_keep_gate_refuses_a_new_vertex_on_the_border(world, monkeypatch):
    from ff9mapkit.world import coastmorph as CM
    root, written = world
    _arm(root, CELL)
    real = CM._tiled_fill_region

    def stray(ring, gnrm, srcs):
        out = real(ring, gnrm, srcs)
        v = out[0][0]
        return out + [[((64.0 * 23, 3.0, -64.0 * 14 - 30.0), v[1], v[2], v[3]), out[0][1], out[0][2]]]
    monkeypatch.setattr(CM, "_tiled_fill_region", stray)
    with pytest.raises(ValueError, match="KEEP GATE"):
        FO.apply("MOD", *CELL, "none")
    assert written == []


def test_a_rerun_on_a_filled_terrain2_adds_nothing(world, tmp_path):
    root, written = world
    _arm(root, CELL)
    FO.apply("MOD", *CELL, "none")
    t2 = written[0][0]
    dest = tmp_path / "MOD" / M.override_relpath(1, *CELL, "0_1", "Terrain2")
    dest.parent.mkdir(parents=True, exist_ok=True)
    M.write_ff9mesh(t2, dest)
    written.clear()
    p, = FO.apply("MOD", *CELL, "none")["plans"]
    assert p["fill"]["fill_tris"] == 0 and len(written[0][0].tris) == len(t2.tris)


# ---- another building


def test_a_building_appears_on_a_bare_cell_render_only_with_a_blocked_footprint(world, tmp_path):
    root, written = world
    _arm(root, BARE)
    at = (64.0 * 23 + 20.0, -64.0 * 15 - 20.0)
    p, = FO.apply("MOD", *BARE, str(_obj(tmp_path)), at=at)["plans"]
    (t2, kt), (o2, ko) = written
    assert p["kind"] == "add" and ko["part"] == "Object2" and kt["part"] == "Terrain2"
    assert {int(round(t[0])) for t in o2.tangents} == {FO.RENDER_ONLY_IDALL}   # the ground query skips it
    blocked = [t for t in t2.tris if _topo(t2, t) == FO.BLOCKED_TOPO]
    assert p["footprint_blocked"] == len(blocked) > 0
    for t in blocked:                                          # every blocked tri lies under the 4x4 footprint
        cx = sum(t2.verts[i][0] for i in t) / 3.0
        cz = sum(t2.verts[i][2] for i in t) / 3.0
        assert 18.0 - 1e-6 <= cx <= 22.0 + 1e-6 and -22.0 - 1e-6 <= cz <= -18.0 + 1e-6
    xs = [v[0] for v in o2.verts]
    assert min(xs) == pytest.approx(18.0) and max(xs) == pytest.approx(22.0)


def test_a_new_building_on_a_stock_building_cell_fills_the_old_hole_too(world, tmp_path):
    root, written = world
    _arm(root, CELL)
    p, = FO.apply("MOD", *CELL, str(_obj(tmp_path)), at=(64.0 * 23 + 12.0, -64.0 * 14 - 12.0))["plans"]
    assert p["kind"] == "replace" and p["fill"]["fill_tris"] > 0 and p["footprint_blocked"] > 0


def test_keep_removes_the_object2_and_nothing_else(world, tmp_path):
    root, written = world
    _arm(root, CELL)
    o2 = tmp_path / "MOD" / M.override_relpath(1, *CELL, "0_1", "Object2")
    o2.parent.mkdir(parents=True, exist_ok=True)
    M.write_ff9mesh(M.hidden_block_mesh(name="Block[23][14] Object2", x=23, y=14), o2)
    assert F.custom_cells(root)[0]["object2"] == "blank"
    FO.apply("MOD", *CELL, "keep")
    assert not o2.exists() and written == [] and F.custom_cells(root)[0]["object2"] is None


# ---- disc 4, the listing, the form check, the CLI


def test_disc4_is_planned_on_its_own_ground_only_where_armed(world, tmp_path):
    root, written = world
    _arm(root, CELL)
    res = FO.apply("MOD", *CELL, "none")
    assert [k["disc"] for _bm, k in written] == [1, 1] and "not armed on disc 4" in res["plans"][0]["disc4"]
    written.clear()
    _arm(root, CELL, disc=4)
    res = FO.apply("MOD", *CELL, "none")
    assert [p["disc"] for p in res["plans"]] == [1, 4]
    assert sorted(k["disc"] for _bm, k in written) == [1, 1, 4, 4]


def test_the_form_check_and_listing_know_object2(tmp_path):
    root = tmp_path
    _arm(root, CELL)
    d = root / "FF9_Data/WorldMap/Disc1/0_1/r14"
    M.write_ff9mesh(_mesh(_cells_tris({(1, 1)}), "Block[23][14] Object", *CELL), d / "Block[23][14] Object.ff9mesh")
    assert F.form_hits([d / "Block[23][14] Object.ff9mesh"]) == []      # no Object2: the building shows in both
    M.write_ff9mesh(_mesh(_cells_tris({(2, 2), (3, 3)}), "Block[23][14] Object2", *CELL),
                    d / "Block[23][14] Object2.ff9mesh")
    h, = F.form_hits([d / "Block[23][14] Object.ff9mesh"])
    assert h["form"] == 1 and h["counterpart"] == "Object2" and h["covered"]
    assert F.custom_cells(root)[0]["object2"] == "mesh"


def test_cli_building2(world, capsys, tmp_path):
    root, written = world
    _arm(root, CELL)
    args = cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD", "--building2", "23", "14", "none",
                                          "--dry-run"])
    assert cli._cmd_world_forms(args) == 0 and written == []
    out = capsys.readouterr().out
    assert "REMOVED in form 2" in out and "dry run" in out
    args = cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD", "--building2", "23", "15", "none"])
    assert cli._cmd_world_forms(args) == 2 and "not armed" in capsys.readouterr().err
    args = cli.build_parser().parse_args(["world-forms", "--building2", "23", "14", "none"])
    assert cli._cmd_world_forms(args) == 2


# ---- the hole's edge, split at the tile lines


def test_split_ring_keeps_every_tile_and_ends_on_the_lines():
    # one tri whose boundary edge crosses x = 4 deep inside the tile: the split puts a vertex on the line
    a = ((1.0, 2.0, -1.0), (0.0, 1.0, 0.0), (0.1, 0.1), (float(GROUND), 0.0, 0.0, 1.0))
    b = ((7.0, 4.0, -1.5), (0.0, 1.0, 0.0), (0.4, 0.1), (float(GROUND), 0.0, 0.0, 1.0))
    c = ((4.0, 3.0, -3.0), (0.0, 1.0, 0.0), (0.2, 0.3), (float(GROUND), 0.0, 0.0, 1.0))
    ter, ring = FO.split_ring([[a, b, c]], [a[0], b[0], c[0]], max_edge=100.0)   # b-c and c-a END on x = 4
    assert len(ter) == 2 and len(ring) == 4 and ring[1][0] == pytest.approx(4.0)
    mid = ring[1]
    assert mid[1] == pytest.approx(2.0 + 0.5 * 2.0)                     # lerped exactly on the old edge
    area = sum(abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                   - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2])) for t in ter)
    assert area == pytest.approx(abs((7.0 - 1.0) * (-3.0 + 1.0) - (4.0 - 1.0) * (-1.5 + 1.0)))


# ---- real data


def _need_install() -> None:
    try:
        import UnityPy  # noqa: F401
        ok = (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        ok = False
    if not ok:
        warnings.warn("--building2 went unchecked on real data in this run: no FF9 install + UnityPy. Re-run in the "
                      "MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy (see the warnings summary)")


@pytest.mark.parametrize("disc", [1, 4])
def test_real_6_12_building_removal_fills_its_whole_footprint_with_walkable_ground(disc, tmp_path, monkeypatch):
    """Cell (6,12)'s building (a walkable Object over an 11-point hole on disc 1, two holes on disc 4): the fill
    covers the footprint, with walkable topographs carried from the ground around it, losing no vertex."""
    _need_install()
    from ff9mapkit.world.placement import WALK_OK
    from ff9mapkit.world.transplant import world_tris
    F.write_condition(tmp_path, disc, 6, 12, COND)
    monkeypatch.setattr(T, "_mod_root", lambda mod_folder, game=None: tmp_path)
    p = FO.plan("FF9CustomMap_test_nonexistent", 6, 12, "none", disc=disc)
    assert p["kind"] == "remove" and p["fill"]["uncovered_u2"] == 0 and p["fill"]["fill_tris"] > 0
    assert set(p["fill"]["topographs"]) <= WALK_OK
    assert p["keep_gate"]["lost"] == 0 and p["keep_gate"]["new_on_border"] == 0
    foot = FO.footprint_points(world_tris(6, 12, "object", disc=disc), (6, 12))
    assert FO._covers(_soup(p["writes"]["Terrain2"], (6, 12)), foot).all()


def test_real_open_holes_are_refused(tmp_path, monkeypatch):
    """(5,4)'s building stands over ground open to the cell's edge: no closed hole to fill, so it is refused."""
    _need_install()
    F.write_condition(tmp_path, 1, 5, 4, COND)
    monkeypatch.setattr(T, "_mod_root", lambda mod_folder, game=None: tmp_path)
    with pytest.raises(ValueError, match="open to the cell's edge"):
        FO.plan("FF9CustomMap_test_nonexistent", 5, 4, "none")
