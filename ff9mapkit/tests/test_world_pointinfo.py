"""world.pointinfo -- the facts the World tab's 3D pick shows (editor rung A1).

Hermetic: the block's parts are synthetic BlockMeshes handed in through ``render.cell_meshes`` (monkeypatched),
the mod stack is a tmp tree, and ``stack=`` pins FolderNames, so nothing reads an install. Each fact is an existing
kit answer joined at one point; these fence the join: the triple and its wrap, the engine's ground (first part in
registration order, not the highest), the census's stacked-sheet rule and its inversion, the canopy sink, who the
game takes each file from, and the ledger's last writer.
"""
from __future__ import annotations

import json

import pytest

from ff9mapkit.world import pointinfo as PI
from ff9mapkit.world import render as R
from ff9mapkit.world.extract import CH_NRM, CH_POS, CH_TAN, CH_UV, BlockMesh, encode_id

SHOWN = "FF9CustomMap-world"


def _grid(idall, y, name="Block[1][1] Terrain"):
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    for i in range(16):
        for j in range(16):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            for corners in (((x0, y, z0), (x1, y, z0), (x0, y, z1)), ((x1, y, z0), (x1, y, z1), (x0, y, z1))):
                base = len(pos)
                for c in corners:
                    pos.append(list(c)); nrm.append([0.0, 1.0, 0.0]); uv.append([0.0, 0.0])
                    tan.append([float(idall), 0.0, 0.0, 1.0]); flat.append(len(pos) - 1)
                tris.append([base, base + 1, base + 2])
    return BlockMesh(name=name, disc=1, x=1, y=1, lod="0_1", vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=tris, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


GRASS, CANOPY, SEA = encode_id(topograph=0, area=14), encode_id(topograph=37, area=3), encode_id(topograph=57)


@pytest.fixture
def site(tmp_path):
    (tmp_path / SHOWN).mkdir()
    return R.RenderSite(cells=(), disc=1, game=tmp_path, mod_root=tmp_path / SHOWN)


def _parts(monkeypatch, parts):
    monkeypatch.setattr(R, "cell_meshes", lambda site, bx, by, part_src=None, stock=False: list(parts))


def _put(game, folder, part, bx=1, by=1):
    p = PI._part_file(game, folder, 1, bx, by, part)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"F9WM")
    return p


def test_the_triple_wraps_and_names_block_and_cell(site, monkeypatch):
    _parts(monkeypatch, [("Terrain", _grid(GRASS, 5.0))])
    info = PI.point_info(site, 1536.0 + 100.5, -70.25, stack=[SHOWN])
    assert info["world"] == (100.5, -70.25) and info["block"] == (1, 1) and info["cell"] == (3, 2)
    assert info["local"] == pytest.approx((36.5, -6.25))


def test_ground_is_the_engines_first_hit_and_sea_under_land_is_not_a_stack(site, monkeypatch):
    _parts(monkeypatch, [("Terrain", _grid(GRASS, 5.0)), ("Sea4", _grid(SEA, 0.0, "Block[1][1] Sea4"))])
    info = PI.point_info(site, 100.5, -70.25, stack=[SHOWN])
    g = info["ground"]
    assert (g["y"], g["part"], g["topograph"], g["area"]) == (5.0, "Terrain", 0, 14) and g["walkable"]
    assert not g["stacked"] and not g["shadowed"]           # Sea4 is not a walkable sheet
    lines = PI.describe(info)
    assert any("Also on this vertical: Sea4 at y 0" in ln for ln in lines)
    assert not any("⚠" in ln for ln in lines)


def test_a_walkable_sheet_over_one_the_engine_prefers_is_an_inversion(site, monkeypatch):
    """Object registers before Terrain, so a low Object lawn under a higher Terrain grounds you on the LOWER one:
    the lawn-under-hill class the census calls an inversion."""
    _parts(monkeypatch, [("Object", _grid(GRASS, 2.0, "Block[1][1] Object")), ("Terrain", _grid(GRASS, 5.0))])
    g = PI.point_info(site, 100.5, -70.25, stack=[SHOWN])["ground"]
    assert g["part"] == "Object" and g["y"] == 2.0 and g["stacked"] and g["shadowed"]
    assert any("LOWER" in ln for ln in PI.describe(PI.point_info(site, 100.5, -70.25, stack=[SHOWN])))


def test_a_canopy_tile_reports_where_the_party_stands(site, monkeypatch):
    _parts(monkeypatch, [("Terrain", _grid(CANOPY, 8.0))])
    g = PI.point_info(site, 100.5, -70.25, stack=[SHOWN])["ground"]
    assert g["canopy"] and g["stand_y"] == pytest.approx(8.0 - 1.171875)


def test_no_parts_is_the_engines_miss(site, monkeypatch):
    _parts(monkeypatch, [])
    info = PI.point_info(site, 100.5, -70.25, stack=[SHOWN])
    assert info["ground"]["part"] == "MISS"
    assert any("drops you to y 0" in ln for ln in PI.describe(info))


def test_a_higher_folder_hides_the_shown_folders_part(site, tmp_path, monkeypatch):
    _parts(monkeypatch, [("Terrain", _grid(GRASS, 5.0))])
    _put(tmp_path, SHOWN, "Terrain")
    _put(tmp_path, "FF9CustomMap", "Terrain")              # higher priority, same part
    info = PI.point_info(site, 100.5, -70.25, stack=["FF9CustomMap", SHOWN])
    assert info["owners"]["hidden"] == [("Terrain", "FF9CustomMap")]
    assert any("Terrain comes from FF9CustomMap" in ln for ln in PI.describe(info))
    info = PI.point_info(site, 100.5, -70.25, stack=[SHOWN, "FF9CustomMap"])
    assert info["owners"]["hidden"] == [] and info["owners"]["parts"]["Terrain"] == SHOWN


def test_a_folder_missing_from_foldernames_is_named(site, monkeypatch):
    _parts(monkeypatch, [("Terrain", _grid(GRASS, 5.0))])
    info = PI.point_info(site, 100.5, -70.25, stack=["FF9CustomMap"])
    assert info["owners"]["in_stack"] is False
    assert any("not in Memoria.ini's FolderNames" in ln for ln in PI.describe(info))


def test_the_ledgers_last_row_for_the_block_names_its_verb(site, tmp_path, monkeypatch):
    _parts(monkeypatch, [("Terrain", _grid(GRASS, 5.0))])
    rows = [{"cell": [1, 1], "part": "Terrain", "write_disc": 1, "utc": "2026-10-01T00:00:00+00:00",
             "argv": ["world-island", "--mod-folder", SHOWN]},
            {"cell": [1, 1], "part": "Sea4", "write_disc": 4, "utc": "2026-10-02T00:00:00+00:00",
             "argv": ["world-mirror"]},                         # disc 4: not this view's
            {"cell": [2, 1], "part": "Terrain", "write_disc": 1, "utc": "2026-10-03T00:00:00+00:00",
             "argv": ["world-forest"]}]                         # another block
    (tmp_path / SHOWN / ".ff9world.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                                                       encoding="utf-8")
    led = PI.point_info(site, 100.5, -70.25, stack=[SHOWN])["ledger"]
    assert led["verb"] == "world-island" and led["utc"].startswith("2026-10-01")
