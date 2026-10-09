"""CUSTOM FORM CELLS: story terrain on ANY cell (terrain study P1; engine patch s92).

The custom engine arms a cell stock never switches when it has a loose `Terrain2`, keeps its form-1 Object in form 2
(unless a loose `Object2` replaces it), and switches it once per world load when its `Block[x][y] Form.txt` NCalc
condition holds. The kit side: `world-forms --arm X Y --when COND` writes the Form.txt, `--form 2` edits the cell's
alternate ground starting from its own form-1 ground (there is no stock form 2), the form check warns about a form-1
edit there, and cells switch -- and may be edited -- together only when their conditions are the same.
"""
from __future__ import annotations

import argparse
import copy

import pytest

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, extract as X, forms as F, mesh as M, terrain as T

CELL, CELL2, STOCK = (23, 14), (23, 15), (22, 14)          # (23,14),(23,15) plain cells; (22,14) Black Mage Village
COND, COND2 = "(GetEventGlobalByte(1089) & 1) != 0", "ScenarioCounter >= 6000"


def _mesh(tris, name, x, y, disc=1):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos = [list(c) for t in tris for c in t]
    n = len(pos)
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: [[0.0, 1.0, 0.0]] * n, CH_UV: [[0.5, 0.5]] * n,
                                  CH_TAN: [[0.0, 0.0, 0.0, 1.0]] * n},
                     flat_index=list(range(n)), tris=[[i, i + 1, i + 2] for i in range(0, n, 3)],
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _terrain(x, y, h=3.0, part="Terrain", disc=1):
    tris = []
    for i in range(16):
        for j in range(16):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            for corners in ([(x0, z0), (x0, z1), (x1, z0)], [(x1, z0), (x0, z1), (x1, z1)]):
                tris.append([(px, h, pz) for px, pz in corners])
    return _mesh(tris, f"Block[{x}][{y}] {part}", x, y, disc)


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Plain cells around (23,14); its form-1 Object touches the ground at local (36,-32). No stock 0_2 anywhere but
    the stock cell (22,14)."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)

    def stock(bx, by, disc=1, lod="0_1", part="terrain", **k):
        if lod == "0_2" and (bx, by) != STOCK:
            raise ValueError("mesh not found")
        if part == "terrain" and 20 <= bx <= 24 and 12 <= by <= 17:
            return _terrain(bx, by, disc=disc)
        if (bx, by) == CELL and part == "object":
            return _mesh([[(36.0, 3.0, -32.0), (37.0, 5.0, -32.0), (36.0, 5.0, -33.0)]], "Block[23][14] Object", 23, 14)
        raise ValueError("mesh not found")
    monkeypatch.setattr(X, "read_block", stock)
    written = []
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: written.append((copy.deepcopy(bm), k))
                        or tmp_path / f"{bm.name}.ff9mesh")
    monkeypatch.setattr(DM, "auto_mirror", lambda *a, **k: (_ for _ in ()).throw(AssertionError("copy path")))
    return tmp_path / "MOD", written


def _y(bm, lx, lz):
    return sorted({round(v[1], 4) for v in bm.verts if abs(v[0] - lx) < 1e-9 and abs(v[2] - lz) < 1e-9})


def _at(cell, lx=32.0, lz=-32.0):
    return (cell[0] * 64.0 + lx, -cell[1] * 64.0 + lz)


# ---- the Form.txt


def test_write_and_read_a_condition(tmp_path):
    p = F.write_condition(tmp_path, 1, *CELL, f"  {COND}  ")
    assert p == tmp_path / F.form_sidecar_relpath(1, *CELL)
    assert p.read_text(encoding="utf-8").startswith("# ff9mapkit:") and F.read_condition(p) == COND
    assert F.custom_condition(tmp_path, 1, *CELL) == COND and F.custom_condition(tmp_path, 4, *CELL) is None
    with pytest.raises(ValueError, match="already switches with BlackMageVillage"):
        F.write_condition(tmp_path, 1, *STOCK, COND)
    with pytest.raises(ValueError, match="one line"):
        F.write_condition(tmp_path, 1, *CELL, "true\nfalse")
    with pytest.raises(ValueError, match="off the"):
        F.write_condition(tmp_path, 1, 24, 0, COND)
    F.write_condition(tmp_path, 1, *CELL, None)
    assert not p.exists()


def test_custom_cells_and_the_form_check(tmp_path):
    F.write_condition(tmp_path, 1, *CELL, COND)
    d = tmp_path / "FF9_Data/WorldMap/Disc1/0_1/r14"
    ter = d / "Block[23][14] Terrain.ff9mesh"
    ter.write_bytes(b"x")
    (d / "Block[23][14] Object.ff9mesh").write_bytes(b"x")
    assert F.custom_cells(tmp_path) == [{"disc": 1, "cell": CELL, "condition": COND, "armed": False, "object2": None}]
    hits = F.form_hits(sorted(d.glob("*.ff9mesh")))
    assert [(h["part"], h["form"], h["place"]) for h in hits] == [("Terrain", 1, None)]   # the Object is in both forms
    (line,) = F.note_lines(hits)
    assert "replaces FORM 1 ONLY" in line and f"when its Form.txt holds ({COND}" in line and "--form 2" in line
    (d / "Block[23][14] Terrain2.ff9mesh").write_bytes(b"x")
    assert F.custom_cells(tmp_path)[0]["armed"] is True
    assert {h["part"]: h["form"] for h in F.form_hits(sorted(d.glob("*.ff9mesh")))} == {"Terrain": 1, "Terrain2": 2}
    other = tmp_path / "FF9_Data/WorldMap/Disc1/0_1/r10/Block[5][10] Terrain.ff9mesh"
    other.parent.mkdir(parents=True)
    other.write_bytes(b"x")
    assert F.form_hits([other]) == []                                   # a plain cell, not armed: nothing


def test_world_forms_arm_disarm_and_list(world, capsys):
    mod, _w = world
    ns = cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD", "--arm", "23", "14", "--when", COND])
    assert cli._cmd_world_forms(ns) == 0 and "armed Block[23][14] (Disc1)" in capsys.readouterr().out
    assert F.custom_condition(mod, 1, *CELL) == COND
    assert cli._cmd_world_forms(cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD"])) == 0
    assert f"custom cell Block[23][14] (Disc1, engine s92): switches when {COND} -- NOT ARMED" in capsys.readouterr().out
    bad = cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD", "--arm", "22", "14", "--when", COND])
    assert cli._cmd_world_forms(bad) == 2 and "already switches" in capsys.readouterr().err
    nowhen = cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD", "--arm", "23", "14"])
    assert cli._cmd_world_forms(nowhen) == 2 and "--arm needs --when" in capsys.readouterr().err
    dis = cli.build_parser().parse_args(["world-forms", "--mod-folder", "MOD", "--disarm", "23", "14"])
    assert cli._cmd_world_forms(dis) == 0 and F.custom_condition(mod, 1, *CELL) is None


# ---- --form 2 on a custom cell


def test_form2_on_a_custom_cell_starts_from_its_form1_ground_and_keeps_its_object(world):
    mod, written = world
    F.write_condition(mod, 1, *CELL, COND)
    s = T.reshape("MOD", at=_at(CELL), radius=12.0, amount=3.0, form=2, seam_taper=0.0, skip_mirror=True)
    assert s["custom"] and s["place"].startswith("custom cell(s) [(23, 14)]") and COND in s["place"]
    (bm, k), = written
    assert k["part"] == "Terrain2" and bm.name.endswith("Terrain2")
    assert _y(bm, 32.0, -32.0) == [6.0]                          # its form-1 ground (3.0) + 3: no stock form 2
    assert _y(bm, 36.0, -32.0) == [3.0]                          # held: the form-1 Object stays in form 2 here


def test_a_deployed_object2_replaces_the_object_as_partner(world, monkeypatch, tmp_path):
    mod, written = world
    F.write_condition(mod, 1, *CELL, COND)
    dep = tmp_path / "Block[23][14] Object2.ff9mesh"
    monkeypatch.setattr(M, "deployed_override", lambda m, x, y, *, part="Terrain", **k:
                        dep if ((x, y), part) == (CELL, "Object2") else None)
    monkeypatch.setattr(M, "blockmesh_from_ff9mesh", lambda p, **k: _mesh(
        [[(28.0, 3.0, -32.0), (29.0, 5.0, -32.0), (28.0, 5.0, -33.0)]], "Block[23][14] Object2", 23, 14))
    T.reshape("MOD", at=_at(CELL), radius=12.0, amount=3.0, form=2, seam_taper=0.0, skip_mirror=True)
    (bm, _k), = written
    assert _y(bm, 28.0, -32.0) == [3.0] and _y(bm, 36.0, -32.0)[0] > 4.0


def test_custom_groups_switch_together_or_refuse(world):
    mod, written = world
    border = (CELL[0] * 64.0 + 32.0, -15 * 64.0)                  # on the (23,14)|(23,15) border
    with pytest.raises(ValueError, match="world-forms --arm X Y"):                 # nothing armed yet
        T.reshape("MOD", at=border, radius=12.0, amount=1.0, form=2)
    F.write_condition(mod, 1, *CELL, COND)
    F.write_condition(mod, 1, *CELL2, COND2)
    with pytest.raises(ValueError, match="switch independently"):                  # different conditions
        T.reshape("MOD", at=border, radius=12.0, amount=1.0, form=2)
    F.write_condition(mod, 1, *CELL2, COND)
    s = T.reshape("MOD", at=border, radius=12.0, amount=1.0, form=2, skip_mirror=True)
    assert sorted(tuple(b["block"]) for b in s["blocks"]) == [CELL, CELL2] and s["stitch"]["torn"] == 0
    with pytest.raises(ValueError, match="switch independently"):                  # a custom cell beside a place
        T.reshape("MOD", at=(23 * 64.0, -14 * 64.0 - 32.0), radius=12.0, amount=1.0, form=2)
    assert all(k["part"] == "Terrain2" for _bm, k in written)


def test_disc4_replays_a_custom_cell_only_where_it_is_armed(world, capsys):
    mod, written = world
    F.write_condition(mod, 1, *CELL, COND)
    T.reshape("MOD", at=_at(CELL), radius=12.0, amount=1.0, form=2)
    assert [k["disc"] for _bm, k in written] == [1] and "not armed on disc 4" in capsys.readouterr().out
    written.clear()
    F.write_condition(mod, 4, *CELL, COND)
    T.reshape("MOD", at=_at(CELL), radius=12.0, amount=1.0, form=2)
    assert [k["disc"] for _bm, k in written] == [1, 4] and "REPLAYING" in capsys.readouterr().out
