"""A new island from the World tab (overworld editor rung C5): the ghost is the mint's own coastline, the mint's first
laws as a preview, the command, ``world-island --report-json``, the ``[[island]]`` recipe row (the same call as the
command), the island card, and THE ACCEPTANCE on real bytes (install-gated): the card's call, the same call typed by
hand, and the recipe composed into a draft write the same bytes."""
from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import numpy as np
import pytest

from ff9mapkit import cli
from ff9mapkit.world import draft as D
from ff9mapkit.world import fuse as FU
from ff9mapkit.world import island as I
from ff9mapkit.world import islandedit as IE
from ff9mapkit.world import recipe as RC

from .test_world_forestedit import _game, _mod
from .test_worldcoast import REAL_GAME, _pin  # noqa: F401  (the autouse install guard; the install resolved first)


# ---------------------------------------------------------------- the ghost is the mint's coast
@pytest.mark.parametrize("kw", [dict(radius=24.0, seed=5.0, lobes=1), dict(radius=30.0, seed=17.0, lobes=2),
                                dict(radius=72.0, seed=5.0, lobes=1), dict(radius=40.0, seed=900.0, lobes=3)])
def test_the_ghost_is_the_coast_the_mint_builds(kw):
    center = (800.0, -640.0)
    built = I.build_landmass(center=center, base_radius=kw["radius"], seed=kw["seed"], lobes=kw["lobes"], stamps=None)
    ring = IE.outline(center, **kw)
    assert np.allclose(np.asarray(built["outline"]), ring)
    blocks = IE.footprint(ring)
    assert {tuple(b) for b in built["blocks"]} <= set(blocks)          # every block the mint fills, at least


def test_the_mint_s_first_laws_preview():
    ring = IE.outline((96.0, -160.0), radius=24.0, seed=5.0)
    (b,) = IE.footprint(ring)
    assert b == (1, 2)
    free = IE.preview(ring, land=set(), occupied=lambda blocks: {})
    assert free["ok"] and free["blocks"] == [(1, 2)]
    land = IE.preview(ring, land={(1, 2)}, occupied=lambda blocks: {})
    assert not land["ok"] and "real land or coast at block (1, 2)" in land["why"] and land["where"] == [(96.0, -160.0)]
    taken = IE.preview(ring, land=set(), occupied=lambda blocks: {(1, 2): ["FF9CustomMap-world"]})
    assert not taken["ok"] and "already holds an edit in FF9CustomMap-world" in taken["why"]
    edge = IE.preview(IE.outline((96.0, -20.0), radius=24.0, seed=5.0), land=set(), occupied=lambda b: {})
    assert not edge["ok"] and "off the top or bottom" in edge["why"]


def test_the_command_and_its_row():
    argv = IE.command("M", (96.04, -160.0), seed=17, radius=30, lobes=2, height=3.6, ground="snow", report="r.json")
    assert argv == ["world-island", "--mod-folder", "M", "--center", "96,-160", "--seed", "17", "--radius", "30",
                    "--lobes", "2", "--height", "3.6", "--ground", "snow", "--dry-run", "--report-json", "r.json"]
    a = cli.build_parser().parse_args(argv)
    assert (a.center, a.seed, a.radius, a.lobes, a.height, a.ground) == ("96,-160", 17.0, 30.0, 2, 3.6, "snow")
    row = RC.row_for(IE.command("-", (96.0, -160.0), seed=5, dry_run=False))
    assert row == {"table": "island", "center": [96.0, -160.0], "seed": 5.0}
    assert RC.label(row) == "island r24 seed 5 at 96, -160"
    with pytest.raises(ValueError, match="names its --seed"):
        RC.row_for(["world-island", "--mod-folder", "-", "--center", "1,2"])
    assert IE.grounds() == ["grass", "desert", "snow"]


# ---------------------------------------------------------------- the CLI's verdict and the [[island]] row
def _stub_mint(monkeypatch):
    """The mint stubbed, every call recorded as its BOUND arguments (defaults applied): the CLI passes each default
    explicitly, a recipe row only what it names, and the two must mean the same call."""
    import inspect
    sig = inspect.signature(I.landmass)
    calls = []

    def landmass(mod, **kw):
        bound = sig.bind(mod, **kw)
        bound.apply_defaults()
        calls.append((str(mod), {k: v for k, v in bound.arguments.items() if k not in ("game", "mod_folder")}))
        return {"op": "landmass", "center": list(kw.get("center") or (0, 0)), "seed": kw["seed"], "radius":
                kw["base_radius"], "blocks": [{"block": [1, 2], "verts": 3, "tris": 1}], "report": {"clean": True},
                "area": None}
    monkeypatch.setattr(I, "landmass", landmass)
    return calls


def test_report_json_carries_the_mint_s_verdict(monkeypatch, tmp_path):
    _stub_mint(monkeypatch)
    game = _game(tmp_path)
    rep = tmp_path / "v.json"
    assert cli.main(["--game", str(game)] + IE.command("M", (96.0, -160.0), seed=5, report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] and v["blocks"] == [[1, 2]] and v["seed"] == 5.0 and v["center"] == [96.0, -160.0]

    def refuse(mod, **kw):
        raise ValueError("landmass footprint touches REAL world block(s) {(1, 2): {'sea4': 8}} -- the island cannot "
                         "deploy there")
    monkeypatch.setattr(I, "landmass", refuse)
    assert cli.main(["--game", str(game)] + IE.command("M", (96.0, -160.0), seed=5, report=rep)) == 2
    v = json.loads(rep.read_text())
    assert not v["ok"] and v["refused"]["where"] == [[96.0, -160.0]] and "REAL world block" in v["refused"]["message"]


def test_the_island_row_is_the_command(monkeypatch, tmp_path):
    calls = _stub_mint(monkeypatch)
    game = _game(tmp_path)
    argv = IE.command("Src", (96.0, -160.0), seed=17, radius=30, lobes=2, height=3.6, ground="snow", dry_run=False)
    assert cli.main(["--game", str(game)] + argv) == 0
    by_hand = list(calls)
    calls.clear()
    row = RC.row_for(argv)
    FU.compose_layout("Src", {"island": [{k: v for k, v in row.items() if k != "table"}]}, game=game)
    assert calls == by_hand


# ---------------------------------------------------------------- the island card
@pytest.fixture(scope="module")
def app():
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _card(app, tmp_path, runner, land=frozenset(), stack=()):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldisland import IslandTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    panel = WorldView3DPanel(pick_palette("dark"))
    tool = IslandTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=runner,
                      drafts_root=tmp_path / "drafts", sync=True, stack_fn=lambda: list(stack),
                      outline_fn=lambda d: set(land))
    tool.open_tool()
    return tool, panel


def test_the_card_draws_the_coast_judges_it_and_mints_into_the_draft(app, tmp_path):
    from .test_worldforest import Scripted

    def answer(kind, argv):
        return {"ok": True, "dry_run": kind == "check", "center": [96.0, -160.0], "seed": 5.0, "blocks": [[1, 2]],
                "written": [], "report": {"clean": True}, "refused": None}
    run = Scripted(answer)
    tool, panel = _card(app, tmp_path, run)
    assert (tool.radius.minimum(), tool.radius.maximum()) == IE.RADIUS_RANGE
    assert (tool.lobes.minimum(), tool.lobes.maximum()) == IE.LOBES_RANGE
    tool.seed.setValue(5)
    tool.place(96.0, -160.0, 0.0)
    tris = panel._overlays[0][0]
    assert np.allclose(tris[:, 1], 3.2)                  # the land at its height
    ring = IE.outline((96.0, -160.0), radius=24.0, seed=5.0)
    assert np.allclose(panel._ghost["poly"], ring)       # the coast the mint will build
    tool._timer.stop()
    tool._check()
    (argv,) = run.argvs
    assert argv[5:] == IE.command(tool.draft(), (96.0, -160.0), seed=5, dry_run=True, report=argv[-1])
    assert "Passes every gate" in tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert D.recipe_rows(tool.draft()) == [{"table": "island", "center": [96.0, -160.0], "seed": 5.0}]
    assert tool._last_center == (96.0, -160.0)
    tool.seed.setValue(6)                                # a new seed is a new shape: the ghost follows
    tool.place(96.0, -160.0)
    assert np.allclose(panel._ghost["poly"], IE.outline((96.0, -160.0), radius=24.0, seed=6.0))


def test_the_card_refuses_real_land_and_a_block_already_edited(app, tmp_path):
    from ff9mapkit.world import mesh as M
    from .test_world_interior import GRASS, _MAIN_U, _bm
    from .test_worldforest import Scripted
    run = Scripted()
    tool, _p = _card(app, tmp_path, run, land={(1, 2)})
    tool.seed.setValue(5)
    tool.place(96.0, -160.0)
    tool._timer.stop()
    tool._check()
    assert not run.argvs and "real land or coast at block (1, 2)" in tool.verdict_lbl.text()
    game = _game(tmp_path / "two")
    M.deploy_override(_bm([(((0, 3.0, 0), (4, 3.0, 0), (0, 3.0, -4)), GRASS, _MAIN_U)], name="Block[1][2] Terrain",
                          x=1, y=2), mod_folder="Other", game=game, part="Terrain", disc=1)
    tool2, _p2 = _card(app, tmp_path / "three", run, stack=[str(game / "Other")])
    tool2.seed.setValue(5)
    tool2.place(96.0, -160.0)
    assert "already holds an edit in Other" in tool2.verdict_lbl.text()


# ---------------------------------------------------------------- THE ACCEPTANCE, on real bytes
def _bytes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name}


def test_the_card_s_call_the_hand_typed_call_and_the_recipe_mint_the_same_island(tmp_path):
    if REAL_GAME is None:
        warnings.warn("the island card's identity went unchecked on real bytes: no FF9 install + UnityPy. Re-run in "
                      "the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy")
    scratch = _game(tmp_path)                            # made first: a missing folder must never resolve elsewhere
    src = _mod(scratch, "Src", ((0, 0),))
    assert src.is_relative_to(tmp_path)
    land = IE.stock_land(game=REAL_GAME)
    center = next((64.0 * bx + 32.0, -(64.0 * by + 32.0)) for by in range(2, 18) for bx in range(1, 23)
                  if not {(bx + i, by + j) for i in (-1, 0, 1) for j in (-1, 0, 1)} & land)
    argv = IE.command("X", center, seed=5, dry_run=False)
    drafts = []
    for name in ("editor", "hand"):
        d = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / name)
        drafts.append(d)
        assert cli.main(["--game", str(REAL_GAME)] + [str(d) if a == "X" else a for a in argv]) == 0
    composed = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / "composed")
    recipe = tmp_path / "r.toml"
    recipe.write_text(RC.dumps([RC.row_for(argv)]), encoding="utf-8")
    assert cli.main(["--game", str(REAL_GAME), "world-fuse", str(recipe), "--mod-folder", str(composed)]) == 0
    ed = _bytes(drafts[0])
    assert ed == _bytes(drafts[1]) == _bytes(composed) and ed != _bytes(src)
