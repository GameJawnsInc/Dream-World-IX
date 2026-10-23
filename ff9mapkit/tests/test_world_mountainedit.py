"""The overworld editor's mountain (rung C2), its kit half: the command the World tab runs, the massif picker, the
ghost (the carve's own map and rock-height stretch), the placement laws as a preview (fenced against the carve),
the island's ground, and the mountain's located refusals and ``--report-json``.

The Workspace half (the tool, its handles and jobs) is ``tests/test_worldmountain.py``."""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from ff9mapkit.world import interior as IN
from ff9mapkit.world import mesh as M
from ff9mapkit.world import mountainedit as ME
from ff9mapkit.world.extract import CH_POS, CH_TAN, encode_id

from .test_world_forestedit import _game, _no_real_install  # noqa: F401  (the autouse install guard)
from .test_world_interior import (GRASS, MASSIF, ROCK, _MAIN_U, _bm, _cone_donor_blocks, _grid_block,
                                  _mountain_bench, _patch_donor, _pyramid_donor)

QUIET = {"log": lambda *a: None}


# ---------------------------------------------------------------- the command
def test_command_spells_the_handles_the_way_a_hand_typed_command_does():
    assert ME.command("M", (190.0, -1228.0), "0,0", dry_run=False) == \
        ["world-mountain", "--mod-folder", "M", "--center", "190,-1228", "--donor", "0,0"]
    assert ME.command("M", (190.04, -1228.26), "10,5-6", spread=1.25, rot_deg=-90, rock_height=1.333,
                      ground="desert", reach=120.0, dry_run=True, report="r.json") == \
        ["world-mountain", "--mod-folder", "M", "--center", "190,-1228.3", "--donor", "10,5-6", "--rot", "270",
         "--spread", "1.25", "--rock-height", "1.33", "--ground", "desert", "--reach", "120", "--dry-run",
         "--report-json", "r.json"]
    for k, v in (("rot_deg", 360), ("spread", 1.0), ("rock_height", 1.0), ("ground", "grass"), ("reach", 96.0)):
        argv = ME.command("M", (0, 0), "0,0", **{k: v})
        assert not {"--rot", "--spread", "--rock-height", "--ground", "--reach"} & set(argv), k


def test_the_command_parses_as_world_mountain():
    from ff9mapkit import cli
    a = cli.build_parser().parse_args(ME.command("M", (12.3, -4.5), "5-6,15-16", spread=1.5, rot_deg=33,
                                                 rock_height=2.0, ground="snow", reach=128, report="r.json"))
    assert (a.mod_folder, a.center, a.donor, a.spread, a.rot, a.rock_height, a.ground, a.reach, a.dry_run,
            a.report_json) == ("M", "12.3,-4.5", "5-6,15-16", 1.5, 33.0, 2.0, "snow", 128.0, True, "r.json")
    assert cli._parse_block_rect(a.donor) == ME._blocks(a.donor)    # the outline reads the carve's block order


def test_massif_donors_are_the_qualified_massif_rows():
    from ff9mapkit.world.donors import load_donors
    rows = ME.massif_donors()
    want = [r["name"] for r in load_donors() if r.get("class") == "massif" and r.get("status") == "qualified"]
    assert [r["name"] for r in rows] == want and len(want) == 7
    assert all(r["donor"] == r["blocks"] and r.get("home_ground") for r in rows)


def test_reach_grows_only_past_the_default():
    assert ME.reach_for(20.0) == 96.0 and ME.reach_for(65.3) == 96.0
    assert ME.reach_for(98.0) == 112.0                   # the snow ridge at x1.5: 98 + 12 + 2 = 112
    assert ME.reach_for(99.0) == 120.0


# ---------------------------------------------------------------- the ghost is the carve's shape
def _carried_rock(res):
    """The carried rock's world positions (topo 49) in every changed block."""
    pts = []
    for (bx, by), bm in res["changed"].items():
        for p, t4 in zip(bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN]):
            if t4[0] == MASSIF:
                pts.append((p[0] + 64.0 * bx, p[1], p[2] - 64.0 * by))
    return np.array(pts)


@pytest.mark.parametrize("rot, spread", [(0, 1.0), (90, 1.0), (270, 1.25), (33, 1.0), (200, 1.2)])
def test_the_ghost_stands_where_the_carve_puts_the_rock(monkeypatch, tmp_path, rot, spread):
    """Turned, spread and seated, the ghost's rock is the carried rock: the same apex, the same plan points."""
    _patch_donor(monkeypatch, _pyramid_donor())
    ol = ME.outline("0,0", game=tmp_path)
    assert ol.tris.shape == (4, 3, 3) and math.isclose(ol.r_rim, 4.0 * math.sqrt(2))
    assert np.allclose(ol.rim[:, 1], 0.0) and ol.home_ground == "grass" and ol.height_ok
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res = IN.carve_mountain(soup, center=(26.0, -26.0), alcove=None, rot_deg=rot, spread=spread, game=tmp_path,
                            **QUIET)
    tris, rim = ME.placed(ol, (26.0, -26.0), spread=spread, rot_deg=rot, ground_y=3.2)
    got = _carried_rock(res)
    apex = tris.reshape(-1, 3)[tris.reshape(-1, 3)[:, 1].argmax()]
    assert np.allclose(got[got[:, 1].argmax()], apex, atol=1e-4)
    for p in tris.reshape(-1, 3):                        # every ghost corner is a carried rock position
        assert np.min(np.hypot(got[:, 0] - p[0], got[:, 2] - p[2])) < 1e-4


def test_the_ghost_stretches_as_rock_height_does(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    ol = ME.outline("0,0", game=tmp_path)
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res = IN.carve_mountain(soup, center=(26.0, -26.0), alcove=None, rock_height=1.5, game=tmp_path, **QUIET)
    tris, _rim = ME.placed(ol, (26.0, -26.0), rock_height=1.5, ground_y=3.2)
    assert math.isclose(tris[..., 1].max(), res["report"]["peak_y"], abs_tol=1e-4)
    assert math.isclose(tris[..., 1].max(), 3.2 + 6.0, abs_tol=1e-6)     # the apex 4 -> 6 about the pinned base
    assert ol.tris_at(1.5) is ol.tris_at(1.5)                             # cached


# ---------------------------------------------------------------- the placement laws, vectorised
def _patchy_blocks(seed, size=3, odd=0.012):
    """A size x size block field of mains grass with coast rock and stamped tiles scattered through it."""
    rng = np.random.default_rng(seed)
    blocks = {}
    for bx in range(size):
        for by in range(size):
            tris = []
            for i in range(16):
                for j in range(16):
                    x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
                    roll = rng.random()
                    idall, u = (ROCK, 0.9) if roll < odd / 2 else (GRASS, 0.4) if roll < odd else (GRASS, _MAIN_U)
                    tris.append((((x0, 3.2, z0), (x1, 3.2, z0), (x0, 3.2, z1)), idall, u))
                    tris.append((((x1, 3.2, z0), (x1, 3.2, z1), (x0, 3.2, z1)), GRASS, _MAIN_U))
            blocks[(bx, by)] = _bm(tris, name=f"Block[{bx}][{by}] Terrain", x=bx, y=by)
    return blocks


def _carve_gate(soup, center, donor, rot, spread, tmp_path):
    try:
        IN.carve_mountain(soup, center=center, donor=donor, alcove=None, rot_deg=rot, spread=spread, game=tmp_path,
                          **QUIET)
    except IN.CarveRefused as e:
        return e.gate if e.gate in ("blocks", "span", "footprint") else None
    except ValueError:
        return None
    return None


@pytest.mark.parametrize("which", ["pyramid", "cone"])
def test_footprint_preview_is_the_carve_s_own_law(monkeypatch, tmp_path, which):
    """THE PREVIEW IS THE LAW: at random centres, turns and spreads over a patchy field (some of it beyond the
    island), the preview names the first placement gate the carve refuses with, or none when the carve gets past
    all three -- for a single-block massif and for one that takes a multi-block span."""
    if which == "pyramid":
        _patch_donor(monkeypatch, _pyramid_donor())
        donor, n = "0,0", 40
    else:
        _patch_donor(monkeypatch, _cone_donor_blocks())
        donor, n = "0-1,0", 24
    ol = ME.outline(donor, game=tmp_path)
    blocks = _patchy_blocks(5)
    ix = ME.SoupIndex(IN.soup_from_blocks(blocks))
    rng = np.random.default_rng(11)
    seen = set()
    for _ in range(n):
        c = (round(float(rng.uniform(-10, 202)), 1), round(float(rng.uniform(-202, 10)), 1))
        rot, spread = float(rng.choice([0, 90, 180, 33, 301])), float(rng.choice([1.0, 1.0, 1.3]))
        _t, rim = ME.placed(ol, c, spread=spread, rot_deg=rot)
        pv = ME.footprint_preview(ix, c, rim[:, [0, 2]], ol.r_rim * spread)
        window = {b: m for b, m in blocks.items() if ME._window(c, ME.reach_for(ol.r_rim * spread))(b)}
        if not window:
            assert pv["gate"] == "blocks"
            continue
        want = _carve_gate(IN.soup_from_blocks(window), c, ME._blocks(donor), rot, spread, tmp_path)
        assert pv["gate"] == want, (c, rot, spread, pv)
        seen.add(pv["gate"])
    assert {"blocks", "span", "footprint"} <= seen or which == "cone" and {"blocks", "footprint"} <= seen


def test_footprint_preview_says_what_it_reached(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    ol = ME.outline("0,0", game=tmp_path)
    ix = ME.SoupIndex(IN.soup_from_blocks({(0, 0): _mountain_bench()}))
    _t, rim = ME.placed(ol, (46.0, -46.0))
    pv = ME.footprint_preview(ix, (46.0, -46.0), rim[:, [0, 2]], ol.r_rim)
    assert pv["gate"] == "footprint" and pv["why"] == "coast rock (topograph 58)"
    (x, z), = pv["where"]
    assert 54 <= x <= 58 and -58 <= z <= -54
    _t, rim = ME.placed(ol, (26.0, -26.0))
    assert ME.footprint_preview(ix, (26.0, -26.0), rim[:, [0, 2]], ol.r_rim)["ok"]
    assert ME.footprint_preview(ix, (600.0, -600.0), rim[:, [0, 2]] + (574, -574), ol.r_rim)["why"] == \
        "no island here"


def test_island_ground_reads_the_family_under_the_point():
    DESERT, DES_U = float(encode_id(topograph=17)), _MAIN_U + 0.65332
    des = []
    for i in range(16):
        for j in range(16):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            des.append((((x0, 3.2, z0), (x1, 3.2, z0), (x0, 3.2, z1)), DESERT, DES_U))
            des.append((((x1, 3.2, z0), (x1, 3.2, z1), (x0, 3.2, z1)), DESERT, DES_U))
    ix = ME.SoupIndex(IN.soup_from_blocks({(0, 0): _grid_block(0, 0), (1, 0): _bm(des, name="Block[1][0] Terrain",
                                                                                  x=1, y=0)}))
    assert ME.island_ground(ix, 30.0, -30.0) == "grass"
    assert ME.island_ground(ix, 94.0, -30.0) == "desert"
    assert ME.island_ground(ix, 500.0, -30.0) == "grass"           # off the island: the default


# ---------------------------------------------------------------- B1 for the mountain
def test_mountain_refusals_say_where_and_keep_their_text(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    with pytest.raises(IN.CarveRefused) as e:
        IN.carve_mountain(soup, center=(46.0, -46.0), alcove=None, game=tmp_path, **QUIET)
    assert e.value.gate == "footprint" and e.value.detail == "it reaches coast rock (topograph 58)"
    assert str(e.value) == "massif footprint at (46,-46) is not clear plain-grass mains (band 6.5u)"
    (x, z), = e.value.where
    assert 54 <= x <= 58 and -58 <= z <= -54
    with pytest.raises(IN.CarveRefused) as e:
        IN.carve_mountain(soup, center=(60.0, -26.0), alcove=None, game=tmp_path, **QUIET)
    assert e.value.gate == "span" and str(e.value).startswith("massif at (60,-26) leaves block span [(0, 0)]")
    assert e.value.where and all(x > 64 - 8.5 for x, _z in e.value.where)
    _patch_donor(monkeypatch, _cone_donor_blocks())
    two = IN.soup_from_blocks({(0, 1): _grid_block(0, 1), (1, 1): _grid_block(1, 1), (0, 2): _grid_block(0, 2)})
    with pytest.raises(IN.CarveRefused) as e:
        IN.carve_mountain(two, center=(64.0, -128.0), donor=[(0, 0), (1, 0)], alcove=None, game=tmp_path, **QUIET)
    assert e.value.gate == "blocks" and "needs deployed Terrain overrides" in str(e.value)
    assert e.value.where == [(96.0, -160.0)]                       # block (1, 2), the one with no island
    assert isinstance(e.value, ValueError)


def test_mountain_report_json_carries_the_verdict_and_the_home_ground_note(monkeypatch, tmp_path, capsys):
    from ff9mapkit import cli
    game = _game(tmp_path)
    _patch_donor(monkeypatch, _pyramid_donor())
    M.deploy_override(_mountain_bench(), mod_folder="Src", game=game, part="Terrain", disc=1)
    rep = tmp_path / "v.json"
    assert cli.main(["--game", str(game)] + ME.command("Src", (26.0, -26.0), "0,0", report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] is True and v["dry_run"] is True and v["center"] == [26.0, -26.0] and v["note"] is None
    assert v["report"]["blob_tris"] == 4 and v["blocks"] == [[0, 0]] and v["written"] == [] and v["ground"] == "grass"
    assert cli.main(["--game", str(game)] + ME.command("Src", (46.0, -46.0), "0,0", ground="desert",
                                                       report=rep)) == 2
    err = capsys.readouterr().err
    v = json.loads(rep.read_text())
    assert v["ok"] is False and v["refused"]["gate"] == "footprint" and v["refused"]["message"] in err
    assert v["note"].startswith("!! WARNING home ground: the uaho massif stands on grass")
    assert cli.main(["--game", str(game)] + ME.command("Src", (26.0, -26.0), "0,0", dry_run=False,
                                                       report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] and not v["dry_run"] and any(p.endswith("Block[0][0] Terrain.ff9mesh") for p in v["written"])
