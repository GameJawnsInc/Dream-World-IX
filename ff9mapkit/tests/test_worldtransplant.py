"""Carrying a real coastal block from the World tab (overworld editor rung C5): the donors, the ghost (the carry's own
quarter-turn map), the target's laws, the command, ``world-transplant --report-json`` for a carry, the
``[[transplant]]`` recipe row (the command itself, not ``[[placement]]``), the card, and THE ACCEPTANCE on real bytes
(install-gated): the command typed by hand and the recipe row composed into a draft carry the same bytes."""
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
from ff9mapkit.world import recipe as RC
from ff9mapkit.world import transplant as TR
from ff9mapkit.world import transplantedit as TE

from .test_world_forestedit import _game, _mod
from .test_worldcoast import REAL_GAME, _pin  # noqa: F401  (the autouse install guard; the install resolved first)


def test_the_donors_are_the_qualified_coast_rows():
    rows = TE.donors()
    assert [r["donor"] for r in rows] == [(7, 17), (20, 5), (18, 15)]
    assert rows[0]["name"] == "beach-island"


@pytest.mark.parametrize("rot", [0, 90, 180, 270])
def test_the_ghost_turns_by_the_carry_s_own_map(rot):
    """placed() is transplant._rot_xz about the cell centre, then the move to the target cell and the shift."""
    rng = np.random.default_rng(rot)
    local = rng.uniform([0, 0, -64], [64, 4, 0], (6, 3))
    donor, cell = (7, 17), (3, 5)
    world = local + (64.0 * donor[0], 0.0, -64.0 * donor[1])
    got = TE.placed(world.reshape(2, 3, 3), donor, cell, rot=rot, shift=(4.0, -8.0)).reshape(-1, 3)
    for (x, y, z), g in zip(local, got):
        rx, rz = TR._rot_xz(x, z, rot // 90)
        assert np.allclose(g, (64.0 * cell[0] + rx + 4.0, y, -64.0 * cell[1] + rz - 8.0))


def test_the_target_s_laws():
    assert TE.preview((3, 5), land=set(), occupied=lambda b: {})["ok"]
    v = TE.preview((3, 5), land={(3, 5)}, occupied=lambda b: {})
    assert not v["ok"] and "real land or coast" in v["why"] and v["where"] == [(224.0, -352.0)]
    v = TE.preview((3, 5), land=set(), occupied=lambda b: {(3, 5): ["FF9CustomMap-world"]})
    assert "already holds an edit in FF9CustomMap-world" in v["why"]
    assert TE.preview((26, 5), land=set(), occupied=lambda b: {})["blocks"] == [(2, 5)]   # the seam wraps


def test_the_command_and_its_row():
    argv = TE.command("M", (3, 5), (7, 17), rot=450, report="r.json")
    assert argv == ["world-transplant", "--mod-folder", "M", "--cell", "3,5", "--donor", "7,17", "--rot", "90",
                    "--dry-run", "--report-json", "r.json"]
    row = RC.row_for(TE.command("-", (3, 5), (7, 17), rot=90, dry_run=False))
    assert row == {"table": "transplant", "cell": [3, 5], "donor": [7, 17], "rot": 90}
    assert RC.label(row) == "carry block (7, 17) to (3, 5), turned 90"
    with pytest.raises(ValueError, match="plain single-cell carry"):
        RC.row_for(TE.command("-", (3, 5), (7, 17), dry_run=False) + ["--size", "2x1"])


def _stub_carry(monkeypatch):
    import inspect
    sig = inspect.signature(TR.transplant)
    calls = []

    def carry(mod, **kw):
        b = sig.bind(mod, **kw)
        b.apply_defaults()
        calls.append((str(mod), {k: v for k, v in b.arguments.items() if k not in ("game", "mod_folder")}))
        return {"op": "transplant", "donor": list(kw["donor"]), "cell": list(kw["cell"]), "rot": kw["rot"],
                "shift": [4.0, -8.0], "strips": [], "coverage_strips": [], "carried": {"terrain": 10}, "cells": {},
                "gates": [{"gate": "land-fit", "ok": True}], "clean": True, "deployed": []}
    monkeypatch.setattr(TR, "transplant", carry)
    return calls


def test_report_json_carries_the_carry_s_verdict(monkeypatch, tmp_path):
    _stub_carry(monkeypatch)
    game = _game(tmp_path)
    rep = tmp_path / "v.json"
    assert cli.main(["--game", str(game)] + TE.command("M", (3, 5), (7, 17), rot=90, report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] and v["op"] == "transplant" and v["shift"] == [4.0, -8.0] and v["cell"] == [3, 5]


def test_the_transplant_row_is_the_command(monkeypatch, tmp_path):
    calls = _stub_carry(monkeypatch)
    game = _game(tmp_path)
    argv = TE.command("Src", (3, 5), (7, 17), rot=90, dry_run=False)
    assert cli.main(["--game", str(game)] + argv) == 0
    by_hand = list(calls)
    calls.clear()
    row = RC.row_for(argv)
    out = FU.compose_layout("Src", {"transplant": [{k: v for k, v in row.items() if k != "table"}]}, game=game)
    assert out["clean"] and calls == by_hand


# ---------------------------------------------------------------- the card
@pytest.fixture(scope="module")
def app():
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_the_card_picks_a_cell_draws_the_donor_there_and_carries_it(app, tmp_path):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldtransplant import TransplantTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted

    def answer(kind, argv):
        return {"ok": True, "dry_run": kind == "check", "cell": [3, 5], "blocks": [[3, 5]], "shift": [4.0, -8.0],
                "gates": [{"gate": "land-fit", "ok": True}], "written": [], "refused": None}
    run = Scripted(answer)
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    panel = WorldView3DPanel(pick_palette("dark"))
    land = np.array([[[64 * 7 + 30.0, 3.0, -64 * 17 - 30.0], [64 * 7 + 34.0, 3.0, -64 * 17 - 30.0],
                      [64 * 7 + 30.0, 3.0, -64 * 17 - 34.0]]])
    tool = TransplantTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=run,
                          drafts_root=tmp_path / "drafts", sync=True, stack_fn=lambda: [],
                          land_fn=lambda d: land, ocean_fn=lambda: {(4, 5)})
    tool.open_tool()
    tool.rot_box.setCurrentIndex(tool.rot_box.findData(90))
    tool.place(230.0, -350.0, 0.0)                      # anywhere in (3,5): the cell is the target
    assert tool.cell() == (3, 5) and tool.center == (224.0, -352.0)
    ghost = panel._overlays[0][0].reshape(-1, 3)
    assert np.allclose(ghost, TE.placed(land, (7, 17), (3, 5), rot=90).reshape(-1, 3))
    tool._timer.stop()
    tool._check()
    (argv,) = run.argvs
    assert argv[5:] == TE.command(tool.draft(), (3, 5), (7, 17), rot=90, dry_run=True, report=argv[-1])
    ghost = panel._overlays[0][0].reshape(-1, 3)        # the check's shift moved it
    assert np.allclose(ghost, TE.placed(land, (7, 17), (3, 5), rot=90, shift=(4.0, -8.0)).reshape(-1, 3))
    tool.accept_btn.click()
    assert D.recipe_rows(tool.draft()) == [{"table": "transplant", "cell": [3, 5], "donor": [7, 17], "rot": 90}]
    tool.place(290.0, -350.0)                           # (4,5) is real land: refused before any job
    assert "real land or coast" in tool.verdict_lbl.text() and len(run.argvs) == 2


# ---------------------------------------------------------------- THE ACCEPTANCE, on real bytes
def _bytes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name}


def test_the_command_and_the_recipe_row_carry_the_same_bytes(tmp_path):
    if REAL_GAME is None:
        warnings.warn("the transplant row's identity went unchecked on real bytes: no FF9 install + UnityPy. Re-run "
                      "in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy")
    scratch = _game(tmp_path)                            # made first: a missing folder must never resolve elsewhere
    src = _mod(scratch, "Src", ((0, 0),))
    hand = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / "hand")
    argv = TE.command(hand, (3, 5), (7, 17), rot=90, dry_run=False)
    assert cli.main(["--game", str(REAL_GAME)] + argv) == 0
    composed = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / "composed")
    recipe = tmp_path / "r.toml"
    recipe.write_text(RC.dumps([RC.row_for(argv)]), encoding="utf-8")
    assert cli.main(["--game", str(REAL_GAME), "world-fuse", str(recipe), "--mod-folder", str(composed)]) == 0
    assert _bytes(hand) == _bytes(composed) != _bytes(src)
