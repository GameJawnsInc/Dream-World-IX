"""Moving the river from the World tab (overworld editor rung C5): the placements a river fits and the cells each
writes, the ghost, the laws (the river's own files do not hold a placement), the command and its recipe row, the
card, and the World tab's menu entry. The move itself (``world-river --move-from``, the draft's deletions, the
ledger) is ``tests/test_world_river_move.py``."""
from __future__ import annotations

import os

import numpy as np
import pytest

from ff9mapkit.world import draft as D
from ff9mapkit.world import recipe as RC
from ff9mapkit.world import riveredit as RE

from .test_world_forestedit import _game, _mod


def _shape():
    """A small river: its island's blocks (15..16, 13..14) and its three cells at shift (8, -2) wrap the seam."""
    tris = np.array([[[1000.0, 3.0, -900.0], [1010.0, 3.0, -900.0], [1000.0, 3.0, -910.0]]])
    ring = np.array([[970.0, -860.0], [1060.0, -860.0], [1060.0, -950.0], [970.0, -950.0]])
    return RE.RiverShape(tris=tris, ring=ring, blocks=[(15, 13), (16, 13), (15, 14), (16, 14)],
                         cells=[(23, 12), (0, 11), (0, 12)], cells_shift=(8, -2),
                         shifts=[(8, -2), (8, -3), (9, 0), (10, 1)])


def test_cells_move_with_the_shift_round_the_seam():
    rs = _shape()
    assert rs.cells_at((8, -2)) == [(0, 11), (0, 12), (23, 12)]
    assert rs.cells_at((8, -3)) == [(0, 10), (0, 11), (23, 11)]
    assert rs.cells_at((9, 0)) == [(0, 14), (1, 13), (1, 14)]
    assert rs.cells_at((-16, -2)) == rs.cells_at((8, -2))               # 24 columns is no shift
    assert RE.same_shift((8, -2), (-16, -2)) and not RE.same_shift((8, -2), (8, -3)) and not RE.same_shift(None, (0, 0))
    assert RE.offset_of((8, -3)) == (512.0, 192.0) and RE.shift_of((512.0, 192.0)) == (8, -3)


def test_the_ghost_is_the_river_moved_by_the_shift():
    rs = _shape()
    tris, rim = RE.placed(rs, (8, -3))
    assert np.allclose(tris[0, 0], (1000.0 + 512.0, 3.0, -900.0 + 192.0))
    assert np.allclose(rim[:, [0, 2]], rs.ring + (512.0, 192.0)) and np.allclose(rim[:, 1], 0.4)
    tris, rim = RE.placed(rs, (9, 0))                                  # past the seam: wrapped onto the map once
    assert np.allclose(tris[0, 0], (1000.0 + 576.0 - 1536.0, 3.0, -900.0))
    assert 0.0 <= rim[:, 0].mean() < 1536.0


def test_a_click_picks_the_nearest_placement():
    rs = _shape()
    for s in rs.shifts:
        assert RE.nearest(rs, *RE.centre(rs, s)) == s
    x, z = RE.centre(rs, (8, -3))
    assert RE.nearest(rs, x + 1536.0 * 0 + 10.0, z - 5.0) == (8, -3)


def test_the_laws_of_a_placement():
    rs = _shape()
    held = {(0, 11): ["FF9CustomMap-world"], (1, 14): ["OTHER"]}

    def occ(cells):
        return {c: held[c] for c in cells if c in held}
    v = RE.preview(rs, (8, -2), river_at=(8, -2), occupied=occ)
    assert not v["ok"] and v["why"] == "the river is here now"
    v = RE.preview(rs, (8, -3), river_at=(8, -2), occupied=occ)
    assert not v["ok"] and "1 of its 3 blocks already hold an edit in FF9CustomMap-world" in v["why"]
    assert v["where"] == [(32.0, -(64.0 * 11 + 32.0))]
    held.pop((0, 11))                                                  # the river's own files never hold it
    assert RE.preview(rs, (8, -3), river_at=(8, -2), occupied=occ)["ok"]
    assert RE.free_shifts(rs, river_at=(8, -2), occupied=occ) == [(8, -3), (10, 1)]
    assert RE.cell_of_path("x/r11/Block[0][11] Sea4.ff9mesh") == (0, 11) and RE.cell_of_path("x/y.txt") is None


def test_the_command_and_its_row():
    argv = RE.command("M", (8, -3), move_from=(8, -2), report="r.json")
    assert argv == ["world-river", "--mod-folder", "M", "--at=512,192", "--move-from=512,128", "--dry-run",
                    "--report-json", "r.json"]
    assert RE.command("M", (-16, 0), dry_run=False) == ["world-river", "--mod-folder", "M", "--at=-1024,0"]
    row = RC.row_for(RE.command("-", (8, -3), move_from=(8, -2), dry_run=False))
    assert row == {"table": "river", "at": [512.0, 192.0], "move_from": [512.0, 128.0]}
    assert RC.row_for(RE.command("-", (9, 0), dry_run=False)) == {"table": "river", "at": [576.0, 0.0]}


# ---------------------------------------------------------------- the card
@pytest.fixture(scope="module")
def app():
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _card(tmp_path, *, at=(8, -2), held=None, answer=None):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldriver import RiverTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    reads = []

    def river_fn(target, rs):
        reads.append(target)
        return at, dict(held or {})
    run = Scripted(answer or (lambda kind, argv: {
        "ok": True, "dry_run": kind == "check", "at": [512.0, 192.0], "shift": [8, -3], "move_from": [512.0, 128.0],
        "blocks": [[0, 10], [0, 11], [23, 11], [0, 12], [23, 12]], "gates": [{"gate": "B1 stack", "verdict": "green"}],
        "files": 132, "written": [], "bridge": [8.0, -765.0], "refused": None}))
    panel = WorldView3DPanel(pick_palette("dark"))
    tool = RiverTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=run,
                     drafts_root=tmp_path / "drafts", sync=True, outline_fn=lambda key: _shape(),
                     river_fn=river_fn)
    return tool, run, panel, reads


def test_the_card_reads_the_river_picks_a_placement_and_moves_it(app, tmp_path):
    tool, run, panel, reads = _card(tmp_path)
    tool.open_tool()
    assert "The river is at 512, 128 now." in tool.from_lbl.text() and reads == [tool.source()]
    tool.place(*RE.centre(_shape(), (8, -2)))                           # where it is: no job, the way out named
    assert "The river is here now. It can move to 512, 192" in tool.verdict_lbl.text() and run.argvs == []
    tool.place(*RE.centre(_shape(), (8, -3)), 0.0)
    assert tool._shift == (8, -3) and tool.to_lbl.text() == "To 512, 192"
    ghost = panel._overlays[0][0].reshape(-1, 3)
    assert np.allclose(ghost, RE.placed(_shape(), (8, -3))[0].reshape(-1, 3))
    tool._timer.stop()
    tool._check()
    (argv,) = run.argvs
    assert argv[5:] == RE.command(tool.draft(), (8, -3), move_from=(8, -2), dry_run=True, report=argv[-1])
    assert "Passes every gate (1): the river moved from 512, 128 to 512, 192, 132 files" in tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert D.recipe_rows(tool.draft()) == [{"table": "river", "at": [512.0, 192.0], "move_from": [512.0, 128.0]}]
    assert tool._last_center == (8.0, -765.0)                           # Show in game goes to the bridge
    assert reads[-1] == tool.draft()                                    # where the river is, read again (the draft)


def test_a_held_placement_refuses_before_any_job(app, tmp_path):
    tool, run, _panel, _reads = _card(tmp_path, held={(0, 10): {"OTHER"}})
    tool.open_tool()
    tool.place(*RE.centre(_shape(), (8, -3)))
    assert "Not here: 1 of its 3 blocks already hold an edit in OTHER." in tool.verdict_lbl.text()
    tool._timer.stop()
    tool._check()
    assert run.argvs == []


def test_no_river_in_the_folder_places_a_new_one(app, tmp_path):
    tool, run, _panel, _reads = _card(tmp_path, at=None)
    tool.open_tool()
    assert "No river in FF9CustomMap-world: a click places a new one." in tool.from_lbl.text()
    tool.place(*RE.centre(_shape(), (9, 0)))
    tool._timer.stop()
    tool._check()
    (argv,) = run.argvs
    assert "--move-from=512,128" not in " ".join(argv) and "--at=576,0" in argv


def test_the_menu_opens_the_river_card(app, tmp_path):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worlddoc import WorldDoc
    doc = WorldDoc(pick_palette("dark"))
    assert doc.tool_actions["river"].text() == "Move the river"
    assert "world-river --move-from" in doc.tool_actions["river"].toolTip()
