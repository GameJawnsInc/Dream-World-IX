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


def test_the_donors_are_the_coast_rows_qualified_first():
    rows = TE.donors()
    assert [(r["donor"], r["size"]) for r in rows] == [
        ((7, 17), (1, 1)), ((20, 5), (1, 1)), ((18, 15), (1, 1)),                  # the qualified single blocks
        ((9, 5), (2, 3)), ((6, 4), (2, 2)), ((10, 17), (1, 2)), ((7, 17), (4, 2))]   # the carry units
    assert rows[0]["name"] == "beach-island" and rows[0]["rots"] == TE.ROTS
    assert {r["name"]: r["status"] for r in rows}["the-comma"] in ("candidate", "qualified")
    assert {r["name"]: r["rots"] for r in rows}["beach-chain"] == (0,)          # its object pins the turn


@pytest.mark.parametrize("size,rot", [((2, 3), 0), ((2, 3), 90), ((2, 3), 180), ((2, 3), 270), ((1, 2), 90)])
def test_a_unit_s_ghost_turns_by_the_region_map(size, rot):
    """placed() is transplant._rot_region_xz on the region-local frame, laid at the target rect's corner."""
    rng = np.random.default_rng(rot + size[1])
    ext = (64.0 * size[0], 64.0 * size[1])
    local = rng.uniform([0, 0, -ext[1]], [ext[0], 4, 0], (6, 3))
    donor, cell = (9, 5), (12, 2)
    world = local + (64.0 * donor[0], 0.0, -64.0 * donor[1])
    got = TE.placed(world.reshape(2, 3, 3), donor, cell, rot=rot, size=size).reshape(-1, 3)
    ts = TE.tsize(size, rot)
    ext_r = (64.0 * ts[0], 64.0 * ts[1])
    for (x, y, z), g in zip(local, got):
        rx, rz = TR._rot_region_xz(x, z, rot // 90, ext, ext_r)
        assert np.allclose(g, (64.0 * cell[0] + rx, y, -64.0 * cell[1] + rz))


def test_a_unit_s_target_fits_the_click_and_stays_on_the_grid():
    assert TE.tsize((2, 3), 90) == (3, 2) and TE.tsize((2, 3), 180) == (2, 3)
    assert TE.anchor_for(64 * 10 + 5.0, -(64 * 6 + 5.0), size=(2, 3)) == (9, 5)   # the rect's middle nearest it
    assert TE.anchor_for(5.0, -5.0, size=(2, 3)) == (23, 0)                        # C23: the column wraps, the row
    assert TE.cells((23, 0), (2, 3)) == [(23, 0), (0, 0), (23, 1), (0, 1), (23, 2), (0, 2)]   # is kept on the grid
    assert TE.anchor_for(64 * 23 + 40.0, -(64 * 19 + 40.0), size=(2, 3), rot=90) == (22, 18)
    assert TE.cells((22, 18), (2, 3), 90) == [(22, 18), (23, 18), (0, 18), (22, 19), (23, 19), (0, 19)]
    assert TE.anchor_for(64 * 3 + 10.0, -(64 * 5 + 10.0)) == (3, 5)               # one block: its own cell
    v = TE.preview((9, 5), land={(10, 6)}, occupied=lambda b: {}, size=(2, 3))
    assert not v["ok"] and "1 of its 6 blocks are real land or coast" in v["why"]
    v = TE.preview((9, 5), land=set(), occupied=lambda b: {(9, 5): ["W"], (10, 7): ["W"]}, size=(2, 3))
    assert "2 of its 6 blocks already hold an edit in W" in v["why"] and len(v["where"]) == 2
    assert TE.preview((9, 5), land=set(), occupied=lambda b: {}, size=(2, 3))["ok"]
    assert "runs off the map" in TE.preview((23, 18), land=set(), occupied=lambda b: {}, size=(2, 3))["why"]


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
    unit = TE.command("-", (20, 0), (9, 5), rot=90, size=(2, 3), dry_run=False)
    assert unit == ["world-transplant", "--mod-folder", "-", "--cell", "20,0", "--donor", "9,5", "--size", "2x3",
                    "--shift", "0,0", "--rot", "90"]
    row = RC.row_for(unit)
    assert row == {"table": "transplant", "cell": [20, 0], "donor": [9, 5], "size": [2, 3], "rot": 90}
    assert RC.label(row) == "carry blocks (9, 5) 2x3 to (20, 0), turned 90"
    with pytest.raises(ValueError, match="one plain carry"):              # a unit runs shift 0,0, never auto
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


def _stub_region(monkeypatch):
    import inspect
    sig = inspect.signature(TR.transplant_region)
    calls = []

    def carry(mod, **kw):
        b = sig.bind(mod, **kw)
        b.apply_defaults()
        calls.append((str(mod), {k: v for k, v in b.arguments.items() if k not in ("game", "mod_folder")}))
        return {"op": "transplant-region", "donor": list(kw["donor"]), "cell": list(kw["cell"]), "rot": kw["rot"],
                "size": list(kw["size"]), "tsize": [3, 2], "shift": [0, 0], "strips": [], "coverage_strips": [],
                "carried": {"terrain": 10}, "cells": {}, "gates": [{"gate": "land-fit", "ok": True}], "clean": True,
                "deployed": []}
    monkeypatch.setattr(TR, "transplant_region", carry)
    return calls


def test_a_unit_s_verdict_names_its_whole_turned_rect(monkeypatch, tmp_path):
    """The history snapshots the verdict's blocks before an Accept writes them: a unit's verdict must name every
    block of its (turned) rect, or Undo could not put the rest back."""
    calls = _stub_region(monkeypatch)
    game = _game(tmp_path)
    rep = tmp_path / "v.json"
    argv = TE.command("M", (20, 0), (9, 5), rot=90, size=(2, 3), report=rep)
    assert cli.main(["--game", str(game)] + argv) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] and v["size"] == [2, 3] and sorted(map(tuple, v["blocks"])) == sorted(TE.cells((20, 0), (2, 3), 90))
    assert calls[0][1]["size"] == (2, 3) and calls[0][1]["shift"] == (0, 0)


def test_a_unit_s_row_runs_the_unit_s_command(monkeypatch, tmp_path):
    calls = _stub_region(monkeypatch)
    game = _game(tmp_path)
    argv = TE.command("Src", (20, 0), (9, 5), rot=90, size=(2, 3), dry_run=False)
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


def test_the_card_carries_a_unit_onto_a_rect_that_turns_with_it(app, tmp_path):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldtransplant import TransplantTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted

    def answer(kind, argv):
        c = [int(v) for v in argv[argv.index("--cell") + 1].split(",")]
        return {"ok": True, "dry_run": kind == "check", "cell": c, "blocks": [list(b) for b in TE.cells(c, (2, 3), 90)],
                "shift": [0, 0], "gates": [{"gate": "land-fit", "ok": True}], "written": [], "refused": None}
    run = Scripted(answer)
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    panel = WorldView3DPanel(pick_palette("dark"))
    land = np.array([[[64 * 9 + 30.0, 3.0, -64 * 5 - 30.0], [64 * 10 + 34.0, 3.0, -64 * 6 - 30.0],
                      [64 * 9 + 30.0, 3.0, -64 * 7 - 34.0]]])
    seen = []
    tool = TransplantTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=run,
                          drafts_root=tmp_path / "drafts", sync=True, stack_fn=lambda: [],
                          land_fn=lambda d, size=(1, 1): seen.append((d, size)) or land, ocean_fn=lambda: set())
    tool.open_tool()
    tool.donor_box.setCurrentIndex(tool.donor_box.findData("9,5@2x3"))
    comma = next(r for r in TE.donors() if r["name"] == "the-comma")
    assert tool.donor_box.currentText() == "the-comma 2x3" + ("" if comma["status"] == "qualified" else " · new")
    tip = tool.donor_box.itemData(tool.donor_box.currentIndex(), 3)
    assert ("Not yet walked in game." in tip) == (comma["status"] != "qualified")
    assert [tool.rot_box.itemData(i) for i in range(tool.rot_box.count())] == [0, 90, 180, 270]
    tool.rot_box.setCurrentIndex(tool.rot_box.findData(90))
    tool.place(64 * 21.5, -64 * 1.0, 0.0)                # the turned 3x2 rect whose middle is nearest
    assert tool.cell() == (20, 0) and tool.size() == (2, 3) and seen[-1] == ((9, 5), (2, 3))
    assert tool.cell_lbl.text() == "Onto (20, 0), 3x2"
    ghost = panel._overlays[0][0].reshape(-1, 3)
    assert np.allclose(ghost, TE.placed(land, (9, 5), (20, 0), rot=90, size=(2, 3)).reshape(-1, 3))
    tool._timer.stop()
    tool._check()
    (argv,) = run.argvs
    assert argv[5:] == TE.command(tool.draft(), (20, 0), (9, 5), rot=90, size=(2, 3), dry_run=True, report=argv[-1])
    assert tool._step_cells(tool._current_verdict()) == TE.cells((20, 0), (2, 3), 90)
    tool.accept_btn.click()
    assert D.recipe_rows(tool.draft()) == [{"table": "transplant", "cell": [20, 0], "donor": [9, 5], "size": [2, 3],
                                            "rot": 90}]
    tool.donor_box.setCurrentIndex(tool.donor_box.findData("7,17@4x2"))
    assert [tool.rot_box.itemData(i) for i in range(tool.rot_box.count())] == [0]   # the chain: its object's turn


def test_show_in_game_goes_onto_the_grid_for_a_carry_across_the_seam(app, tmp_path):
    """A carry anchored at column 23 runs past x = 1536, and its middle is 1536 or more; the engine's teleport refuses
    x/64 >= 24, so Show in game failed for every carry across the seam (review of C23). The point the card hands the
    game is folded onto the grid, as the mountain card's already was."""
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldtransplant import TransplantTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted

    def answer(kind, argv):
        c = [int(v) for v in argv[argv.index("--cell") + 1].split(",")]
        return {"ok": True, "dry_run": kind == "check", "cell": c, "blocks": [list(b) for b in TE.cells(c, (2, 3))],
                "shift": [0, 0], "gates": [{"gate": "land-fit", "ok": True}], "written": [], "refused": None}
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    land = np.array([[[64 * 9 + 30.0, 3.0, -64 * 5 - 30.0], [64 * 10 + 34.0, 3.0, -64 * 6 - 30.0],
                      [64 * 9 + 30.0, 3.0, -64 * 7 - 34.0]]])
    reloads = []
    tool = TransplantTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: game,
                          source_fn=lambda: src, runner=Scripted(answer), drafts_root=tmp_path / "drafts", sync=True,
                          stack_fn=lambda: [], land_fn=lambda d, size=(1, 1): land, ocean_fn=lambda: set(),
                          on_reload=lambda x, z: reloads.append((x, z)))
    tool.open_tool()
    tool.donor_box.setCurrentIndex(tool.donor_box.findData("9,5@2x3"))
    tool.place(3.0, -160.0, 0.0)                          # just east of x = 0: anchored at column 23
    assert tool.cell() == (23, 1)
    tool._timer.stop()
    tool._check()
    tool.accept_btn.click()
    tool._show_in_game()
    (x, z), = reloads
    assert 0.0 <= x < 1536.0 and (x, z) == (0.0, -160.0)


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


def test_on_real_bytes_a_unit_by_hand_and_by_its_row_carry_the_same_bytes(tmp_path):
    """The comma (9,5) 2x3, turned 90, onto the first free rect of the real folder: the command typed by hand into one
    draft of the real FF9CustomMap-world and the [[transplant]] row composed into another carry the same bytes (read
    only: every write lands in the tmp drafts)."""
    if REAL_GAME is None or not (REAL_GAME / "FF9CustomMap-world").is_dir():
        warnings.warn("the multi-block carry went unchecked on real bytes: no FF9 install + UnityPy + "
                      "FF9CustomMap-world. Re-run in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy + FF9CustomMap-world")
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import river as RV
    src = REAL_GAME / "FF9CustomMap-world"
    hand = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / "hand")
    land = TE.stock_land(game=REAL_GAME)
    stack = [str(hand)] + [str(REAL_GAME / f) for f in RV.stack_folders(REAL_GAME) if f != src.name]

    def free(c):
        cs = TE.cells(c, (2, 3), 90)
        return all(0 <= x < 24 and 0 <= y < 20 for x, y in cs) and not set(cs) & land and not any(
            M.existing_overrides([b], fo, disc=d, game=REAL_GAME) for b in cs for fo in stack for d in (1, 4))
    target = next((c for c in ((x, y) for y in range(20) for x in range(22)) if free(c)), None)
    if target is None:
        pytest.skip("no free 3x2 rect of open ocean on the real folder")
    argv = TE.command(hand, target, (9, 5), rot=90, size=(2, 3), dry_run=False)
    assert cli.main(["--game", str(REAL_GAME)] + argv) == 0
    composed = D.ensure_draft(src, game=REAL_GAME, root=tmp_path / "composed")
    recipe = tmp_path / "r.toml"
    recipe.write_text(RC.dumps([RC.row_for(TE.command("-", target, (9, 5), rot=90, size=(2, 3), dry_run=False))]),
                      encoding="utf-8")
    assert cli.main(["--game", str(REAL_GAME), "world-fuse", str(recipe), "--mod-folder", str(composed)]) == 0
    assert _bytes(hand) == _bytes(composed) != _bytes(src)
    edited = {tuple(b[1:]) for b in D.edited_blocks(hand)}
    assert edited and edited <= set(TE.cells(target, (2, 3), 90))


# ---------------------------------------------------------------- refusals that say where (rung C16)
def _slab(bx, by, x0, x1, z0, z1):
    """A donor block's land as two tris spanning x0..x1, z0..z1 (block-local; z negative)."""
    o = np.array([64.0 * bx, 0.0, -64.0 * by])
    a, b, c, d = ([x0, 3.0, z0], [x1, 3.0, z0], [x1, 3.0, z1], [x0, 3.0, z1])
    return np.array([[a, b, c], [a, c, d]]) + o


def test_the_land_fit_law_from_the_donor_alone():
    """A carry's land keeps 2u of sea to its rect's frame on every side (the land-fit gate), so a donor whose land is
    wider than the rect less 4u can never be carried, wherever it goes and however it is shifted: a block cut from a
    continent's coast. The law says which way, and marks the two edges it runs to on the target."""
    assert TE.too_wide(_slab(7, 17, 10, 54, -10, -54)) is None                   # an island: 44u each way
    assert TE.too_wide(_slab(7, 17, 0, 64, -20, -40), cell=(3, 5)) == {
        "why": "its land runs to its block's edge (64u east to west); a carry needs 2u of sea all round "
               "it, so this block cannot be carried alone",
        "where": [(192.0, -352.0), (256.0, -352.0)]}                            # (3,5)'s west and east edges
    assert "north to south" in TE.too_wide(_slab(7, 17, 0, 64, -20, -40), rot=90)["why"]   # a turn swaps the sides
    assert TE.too_wide(_slab(7, 17, 0, 61, -20, -40)) and TE.too_wide(_slab(7, 17, 2, 62, -20, -40)) is None
    assert TE.too_wide(_slab(7, 17, 0, 100, -20, -40), size=(2, 1)) is None     # a 2-block rect has room for 100u
    pv = TE.preview((3, 5), land=set(), occupied=lambda b: {}, donor_tris=_slab(7, 17, 0, 64, -20, -40))
    assert not pv["ok"] and pv["donor"] and pv["where"] == [(192.0, -352.0), (256.0, -352.0)]


def test_the_land_fit_gate_marks_the_sides_too_near_the_frame():
    g = TR._land_fit_gate([0.0, 40.0, -50.0, -10.0], 2.0, (64.0, 64.0), (3, 5))
    assert not g["ok"] and g["where"] == [[192.0, -350.0]]                      # its west side, on block (3,5)
    g = TR._land_fit_gate([10.0, 127.0, -191.0, -1.0], 2.0, (128.0, 192.0), (20, 0))
    assert not g["ok"] and g["where"] == [[1407.0, -96.0], [1348.5, -191.0], [1348.5, -1.0]]   # east, south, north
    assert "where" not in TR._land_fit_gate([10.0, 50.0, -50.0, -10.0], 2.0, (64.0, 64.0), (3, 5))


def test_a_refusal_marks_where_its_gates_say_not_the_block_s_middle(monkeypatch, tmp_path):
    """The carry's report marks a failing gate's own points (rung C16); a gate that names none keeps the middle."""
    def carry(mod, **kw):
        return {"op": "transplant", "donor": list(kw["donor"]), "cell": list(kw["cell"]), "rot": kw["rot"],
                "shift": [0.0, 0.0], "strips": [], "coverage_strips": [], "carried": {"terrain": 10}, "cells": {},
                "gates": [TR._land_fit_gate([0.0, 40.0, -50.0, -10.0], 2.0, (64.0, 64.0), tuple(kw["cell"])),
                          {"gate": "census", "introduced": 1, "ok": False}], "clean": False, "deployed": []}
    monkeypatch.setattr(TR, "transplant", carry)
    game = _game(tmp_path)
    rep = tmp_path / "v.json"
    assert cli.main(["--game", str(game)] + TE.command("M", (3, 5), (7, 17), report=rep)) == 2
    v = json.loads(rep.read_text())
    assert v["refused"]["gate"] == "land-fit" and v["refused"]["where"] == [[192.0, -350.0]]


def test_the_card_says_a_donor_that_fills_its_frame_cannot_be_carried(app, tmp_path):
    """No dry run for a donor no target can take: the card says so at once and marks the edges its land runs to."""
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldtransplant import TransplantTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted
    run = Scripted()
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    panel = WorldView3DPanel(pick_palette("dark"))
    tool = TransplantTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=run,
                          drafts_root=tmp_path / "drafts", sync=True, stack_fn=lambda: [],
                          land_fn=lambda d: _slab(7, 17, 0, 64, -20, -40), ocean_fn=lambda: set())
    tool.open_tool()
    tool.place(230.0, -350.0, 0.0)
    tool._timer.stop()
    tool._check()
    assert run.argvs == [] and tool.verdict_lbl.text().startswith("Not this donor: its land runs to")
    assert len(panel._overlays) == 2 + 2                # the ghost, its rim, and a mark on each edge
