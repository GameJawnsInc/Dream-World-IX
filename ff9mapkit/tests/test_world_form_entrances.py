"""A CUSTOM FORM CELL'S ENTRANCE IN FORM 2 (engine patch s92; `world-forms --entrance2`).

An entrance is ground tiles with IDALL event bits; the form switch swaps the walked ground, event bits included (the
stock game closes Cleyra's entrance and opens the Water Shrine's that way). `off` clears them in the cell's Terrain2,
`only` in its form-1 Terrain (Terrain2 keeps them), `both` gives each form's ground the other's. Nothing but the event
bits changes.
"""
from __future__ import annotations

import warnings

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import extract as X, formentrance as FE, forms as F, mesh as M, terrain as T

CELL, PLAIN, STOCK = (23, 14), (23, 15), (22, 14)
COND = "(GetEventGlobalByte(1089) & 1) != 0"
DOOR = {(9, 9)}                                          # the 4u tile (local x 36..40, z -36..-40) with the event


def _mesh(tris, name, x, y, disc=1):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos, tan = [], []
    for t in tris:
        for (p, idall) in t:
            pos.append(list(p))
            tan.append([float(idall), 0.0, 0.0, 1.0])
    n = len(pos)
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * n, CH_UV: [[0.1, 0.6]] * n, CH_TAN: tan},
                     flat_index=list(range(n)), tris=[[i, i + 1, i + 2] for i in range(0, n, 3)],
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _ground(x, y, door=True, disc=1, split=False, half=False):
    """A 16x16 grid of 4u tiles; DOOR carries event 1 (``half``: on its first triangle only). ``split`` re-cuts the
    DOOR tile into three triangles, as a later form-2 edit might."""
    tris = []
    for i in range(16):
        for j in range(16):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            quads = [[(x0, z0), (x1, z0), (x0, z1)], [(x1, z0), (x1, z1), (x0, z1)]]
            if split and (i, j) in DOOR:                  # the form-2 ground re-cut there (e.g. a fill or a split)
                m = ((x0 + x1) / 2.0, z0)
                quads = [[(x0, z0), m, (x0, z1)], [m, (x1, z0), (x0, z1)], [(x1, z0), (x1, z1), (x0, z1)]]
            for k, corners in enumerate(quads):
                ev = 1 if door and (i, j) in DOOR and not (half and k > 0) else 0
                tris.append([((px, 3.0, pz), X.encode_id(topograph=20, area=14, event=ev)) for px, pz in corners])
    return _mesh(tris, f"Block[{x}][{y}] Terrain", x, y, disc)


@pytest.fixture
def world(tmp_path, monkeypatch):
    """CELL has an entrance tile; PLAIN has none; STOCK is a switchable cell. Deploys land in tmp_path/MOD."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    (tmp_path / "MOD").mkdir()
    monkeypatch.setattr(T, "_mod_root", lambda mod_folder, game=None: tmp_path / "MOD")

    def stock(bx, by, disc=1, lod="0_1", part="terrain", **k):
        if part == "terrain" and (bx, by) in (CELL, PLAIN, STOCK):
            return _ground(bx, by, door=(bx, by) != PLAIN, disc=disc)
        raise ValueError("mesh not found")
    monkeypatch.setattr(X, "read_block", stock)
    return tmp_path / "MOD"


def _deployed(root, part, cell=CELL, disc=1):
    p = root / M.override_relpath(disc, *cell, "0_1", part)
    return M.blockmesh_from_ff9mesh(p, disc=disc, x=cell[0], y=cell[1], part=part) if p.is_file() else None


def _events(bm):
    return sorted({ev for _t, ev in FE.event_tris(bm)}), len(FE.event_tris(bm))


def test_off_closes_the_entrance_in_form_2_only(world):
    F.write_condition(world, 1, *CELL, COND)
    p, = FE.apply("MOD", *CELL, "off")["plans"]
    t2 = _deployed(world, "Terrain2")
    assert _events(t2) == ([], 0) and _deployed(world, "Terrain") is None      # form 1 keeps its stock entrance
    assert p["tags"] == {"form1": [(47, 29, 1)], "form2": []} and p["changed"] == {"Terrain": 0, "Terrain2": 2}
    # nothing but the event bits moved: positions, topograph and area are the form-1 ground's
    t1 = X.read_block(*CELL)
    assert t2.verts == t1.verts
    for a, b in zip(t1.tangents, t2.tangents):
        da, db = X.decode_id(int(a[0])), X.decode_id(int(b[0]))
        assert (da["topograph"], da["area"]) == (db["topograph"], db["area"]) and db["event"] == 0


def test_only_moves_the_entrance_into_form_2_and_both_undoes_it(world):
    F.write_condition(world, 1, *CELL, COND)
    FE.apply("MOD", *CELL, "only")
    assert _events(_deployed(world, "Terrain")) == ([], 0)                     # form 1: no entrance
    assert _events(_deployed(world, "Terrain2")) == ([1], 2)                   # form 2: the entrance
    p, = FE.apply("MOD", *CELL, "both")["plans"]
    assert p["changed"] == {"Terrain": 2, "Terrain2": 0}
    assert _events(_deployed(world, "Terrain")) == ([1], 2) and _events(_deployed(world, "Terrain2")) == ([1], 2)
    FE.apply("MOD", *CELL, "off")
    p, = FE.apply("MOD", *CELL, "both")["plans"]                               # and after off: form 2 regains it
    assert p["changed"] == {"Terrain": 0, "Terrain2": 2} and _events(_deployed(world, "Terrain2")) == ([1], 2)


def test_events_follow_the_plan_onto_a_recut_form2_ground(world):
    """Terrain2 need not match Terrain triangle for triangle (a --building2 fill, a split): the event goes to every
    form-2 triangle whose centroid lies on a form-1 entrance triangle."""
    F.write_condition(world, 1, *CELL, COND)
    recut = _ground(*CELL, door=False, split=True)
    recut = M.blockmesh_from_ff9mesh(M.write_ff9mesh(recut, world / M.override_relpath(1, *CELL, "0_1", "Terrain2")),
                                     disc=1, x=CELL[0], y=CELL[1], part="Terrain2")
    assert FE.copy_events(recut, X.read_block(*CELL)) == 3
    # an entrance on HALF a tile: only the re-cut triangles whose centroid lies on that half take it (the other half
    # shares the tile's bounding box, not the triangle)
    half = _ground(*CELL, half=True)
    recut = _ground(*CELL, door=False, split=True)
    assert FE.copy_events(recut, half) == 2
    got = sorted(round(sum(recut.verts[i][0] for i in t) / 3.0, 3) for t, _ev in FE.event_tris(recut))
    assert got == [pytest.approx(36.667, abs=1e-3), pytest.approx(38.0, abs=1e-3)]   # not the 38.667 one


def test_only_after_off_gives_form_2_its_entrance_back(world):
    F.write_condition(world, 1, *CELL, COND)
    FE.apply("MOD", *CELL, "off")
    assert _events(_deployed(world, "Terrain2")) == ([], 0)
    p, = FE.apply("MOD", *CELL, "only")["plans"]
    assert p["changed"] == {"Terrain": 2, "Terrain2": 2}
    assert _events(_deployed(world, "Terrain2")) == ([1], 2) and _events(_deployed(world, "Terrain")) == ([], 0)


def test_refusals(world):
    with pytest.raises(ValueError, match="not armed"):
        FE.apply("MOD", *CELL, "off")
    with pytest.raises(ValueError, match="BlackMageVillage"):
        FE.apply("MOD", *STOCK, "off")
    F.write_condition(world, 1, *PLAIN, COND)
    with pytest.raises(ValueError, match="no entrance tiles"):
        FE.apply("MOD", *PLAIN, "off")
    F.write_condition(world, 1, *CELL, COND)
    with pytest.raises(ValueError, match="takes one of"):
        FE.apply("MOD", *CELL, "close")
    assert not list((world / "FF9_Data").rglob("*.ff9mesh"))


def test_disc4_is_replayed_only_where_armed(world):
    F.write_condition(world, 1, *CELL, COND)
    res = FE.apply("MOD", *CELL, "off")
    assert [p["disc"] for p in res["plans"]] == [1] and "not armed on disc 4" in res["plans"][0]["disc4"]
    F.write_condition(world, 4, *CELL, COND)
    res = FE.apply("MOD", *CELL, "off")
    assert [p["disc"] for p in res["plans"]] == [1, 4] and _events(_deployed(world, "Terrain2", disc=4)) == ([], 0)


def test_a_disc4_cell_without_the_entrance_is_noted_not_refused(world, monkeypatch):
    """Disc 4's own ground can lack the entrance (the real (18,12) has none there): the disc-1 edit still lands."""
    real = X.read_block
    monkeypatch.setattr(X, "read_block", lambda bx, by, disc=1, **k: _ground(bx, by, door=False, disc=4) if disc == 4
                        else real(bx, by, disc=disc, **k))
    F.write_condition(world, 1, *CELL, COND)
    F.write_condition(world, 4, *CELL, COND)
    res = FE.apply("MOD", *CELL, "off")
    assert [p["disc"] for p in res["plans"]] == [1] and "no entrance tiles on disc 4" in res["plans"][0]["disc4"]
    assert _events(_deployed(world, "Terrain2")) == ([], 0) and _deployed(world, "Terrain2", disc=4) is None
    with pytest.raises(ValueError, match="no entrance tiles"):           # asked for disc 4 directly: refused
        FE.apply("MOD", *CELL, "off", disc=4)


def test_cli_entrance2(world, capsys):
    F.write_condition(world, 1, *CELL, COND)
    args = cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD", "--entrance2", "23", "14", "only",
                                          "--dry-run"])
    assert cli._cmd_world_forms(args) == 0 and not list((world / "FF9_Data").rglob("*.ff9mesh"))
    assert "OPENS only when the cell switches" in capsys.readouterr().out
    args = cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD", "--entrance2", "23", "15", "off"])
    assert cli._cmd_world_forms(args) == 2 and "not armed" in capsys.readouterr().err


def _need_install() -> None:
    try:
        import UnityPy  # noqa: F401
        ok = (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        ok = False
    if not ok:
        warnings.warn("--entrance2 went unchecked on real data in this run: no FF9 install + UnityPy. Re-run in the "
                      "MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy (see the warnings summary)")


@pytest.mark.parametrize("mode,form1,form2", [("off", [(37, 24, 1)], []), ("only", [], [(37, 24, 1)])])
def test_real_ice_cavern_entrance(mode, form1, form2, tmp_path, monkeypatch):
    """(18,12)'s Ice Cavern entrance (case 4, field 300): two tiles; off/only move exactly that tag between forms."""
    _need_install()
    F.write_condition(tmp_path, 1, 18, 12, COND)
    monkeypatch.setattr(T, "_mod_root", lambda mod_folder, game=None: tmp_path)
    p = FE.plan("FF9CustomMap_test_nonexistent", 18, 12, mode)
    assert p["tags_before"]["form1"] == [(37, 24, 1)]
    assert p["tags"] == {"form1": form1, "form2": form2} and sum(p["changed"].values()) == 2
