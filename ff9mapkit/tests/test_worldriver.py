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


# ---------------------------------------------------------------- editing a placed river step (rung C12)
MOVE = {"table": "river", "at": [512.0, 192.0], "move_from": [512.0, 128.0]}


def test_the_river_card_opens_on_a_move_and_holds_where_it_moved_from(app, tmp_path):
    tool, _run, _panel, _reads = _card(tmp_path / "a")
    tool.open_tool()
    tool.load_row(MOVE)
    assert tool._shift == (8, -3) and tool.row() == MOVE and tool.to_lbl.text() == "To 512, 192"
    with pytest.raises(ValueError, match="its placement 0, 0 is not one the river fits on open ocean"):
        tool.load_row({"table": "river", "at": [0.0, 0.0]})
    tool, _run, _panel, _reads = _card(tmp_path / "b", at=(9, 0))      # the draft holds it somewhere else
    tool.open_tool()
    with pytest.raises(ValueError, match="the draft before it holds the river at 576, 0, not where the step moved it"):
        tool.edit_row(MOVE, label="move", on_accepted=lambda: None, on_cancel=lambda note=None: None)
    tool, _run, _panel, _reads = _card(tmp_path / "c", at=None)        # a plain carry: no river before it
    tool.open_tool()
    tool.load_row({"table": "river", "at": [576.0, 0.0]})
    assert tool.row() == {"table": "river", "at": [576.0, 0.0]}


def test_a_read_of_the_river_from_before_the_edit_is_not_taken_for_the_draft_before_the_step(app, tmp_path):
    """A read of where the river stands, begun while the card was open, lands after the bar's Edit lifted the step out
    of the draft (same path, new bytes): it said where the river was BEFORE the edit, and the move's held move_from
    refused against it and cancelled the edit (review of C12). A read begun before the draft moved is dropped; the
    one begun after it decides."""
    tool, _run, _panel, _reads = _card(tmp_path)
    state = {"at": (8, -3)}                                 # the draft after the step: the river moved (8,-2) -> (8,-3)
    tool._river_fn = lambda target, rs: (state["at"], {})
    tool._sync = False
    held = []
    tool._bg = lambda what, fn: held.append((what, fn()))   # a worker reads at once; its result comes later

    def deliver(kind):
        k = next((i for i, (w, _r) in enumerate(held) if w == kind), None)
        if k is not None:
            what, result = held.pop(k)
            tool._on_bg(what, 0, result, None)
        return k is not None
    tool.open_tool()
    deliver("outline")                                      # the river's shape in; where it stands is being read
    assert any(w == "river" for w, _r in held)
    state["at"] = (8, -2)                                   # the bar's Edit: the draft back to before the step...
    tool.island_changed()                                   # ...the tab's _draft_changed, then _open_carry
    tool.open_tool()
    notes = []
    tool.edit_row(MOVE, label="move", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    while deliver("river") or deliver("outline"):
        pass
    assert tool.editing() and notes == [] and tool.river_at() == (8, -2)


def test_a_stale_read_that_fails_does_not_take_the_live_read_s_place(app, tmp_path):
    """A read of the river begun before the draft moved fails (plausibly: the draft is being rewritten under it) and
    its error came with no number, so it freed the slot of the read begun after: that one was dropped when it landed,
    the river never read, the stale error on screen (review of the C12 fixes). A read's error carries its number."""
    tool, _run, _panel, _reads = _card(tmp_path)
    calls = {"n": 0}

    def river_fn(target, rs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("the draft was being rewritten")
        return (8, -2), {}
    tool._river_fn = river_fn
    tool._sync = False
    held = []
    tool._bg = lambda what, fn: held.append((what, fn))

    def deliver(kind):                                       # as the worker does: its result, or its exception
        k = next((i for i, (w, _f) in enumerate(held) if w == kind), None)
        if k is None:
            return False
        what, fn = held.pop(k)
        try:
            tool._on_bg(what, 0, fn(), None)
        except Exception as e:                               # noqa: BLE001
            tool._on_bg(what, 0, None, e)
        return True
    tool.open_tool()
    deliver("outline")                                       # the shape in: read 1 asked
    tool.island_changed()                                    # the draft moved: read 2 asked
    while deliver("river") or deliver("outline"):
        pass
    assert tool.river_at() == (8, -2) and "could not be read" not in tool.verdict_lbl.text()


def test_a_river_edit_whose_move_from_is_not_where_the_river_stands_is_cancelled_when_that_read_comes(app, tmp_path):
    """Where the river stands is read on a worker: the edit opens on the placement at once, and the row's move_from
    is held to that read when it comes (a different one cancels the edit with the reason)."""
    notes = []
    tool, _run, _panel, _reads = _card(tmp_path, at=(9, 0))
    tool.open_tool()                                    # the shape in (once per card)
    tool._river = None                                  # an undo moved the draft: where it stands is read again
    held = []
    tool._bg = lambda what, fn: held.append((what, fn))
    tool.edit_row(MOVE, label="move", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    assert tool.editing() and tool._shift == (8, -3) and notes == []
    (what, fn), = [h for h in held if h[0] == "river"]
    tool._on_bg(what, 0, fn(), None)
    assert notes == ["Not opened in its card: the draft before it holds the river at 576, 0, not where the step moved "
                     "it from. Delete still works."] and not tool.editing() and tool.isHidden()


def test_the_river_s_shape_is_read_once_per_install_and_kit(tmp_path, monkeypatch):
    """The river card read the river's shape on its first open of every session: 17-24 s on a worker, every time
    (PERF.md 7, c5). It is a function of the install's stock bytes and of the kit's code alone, so it is kept in the
    kit's cache per install, stamped with the world code it was computed by: the same shape back, exactly, and a
    different kit computes it again."""
    import json
    calls = []

    def read(game=None):
        calls.append(game)
        return _shape()
    monkeypatch.setattr(RE, "_cache_dir", lambda: tmp_path / "cache")
    game = tmp_path / "game"
    first = RE.cached_shape(game, read=read)
    again = RE.cached_shape(game, read=read)
    assert len(calls) == 1
    for a, b in ((first, _shape()), (again, _shape())):
        assert np.array_equal(a.tris, b.tris) and a.tris.dtype == b.tris.dtype == np.float64
        assert np.array_equal(a.ring, b.ring) and a.ring.dtype == b.ring.dtype
        assert (a.blocks, a.cells, a.cells_shift, a.shifts) == (b.blocks, b.cells, b.cells_shift, b.shifts)
        assert all(type(x) is tuple for x in a.blocks + a.cells + a.shifts) and type(a.cells_shift) is tuple
    monkeypatch.setattr(RE, "_code_stamp", lambda: "another kit")
    RE.cached_shape(game, read=read)
    assert len(calls) == 2                                               # a new kit reads it again
    (doc,) = [json.loads(p.read_text()) for p in (tmp_path / "cache" / "world-river").glob("*.json")]
    assert doc["stamp"].startswith("another kit-") and doc["game"] == str(game)


def test_the_river_card_reads_the_cached_shape(tmp_path, monkeypatch):
    """THE CALL SITE: the card's default shape read is the cached one."""
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldriver import RiverTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    asked = []
    monkeypatch.setattr(RE, "cached_shape", lambda game, **k: asked.append(game) or _shape())
    monkeypatch.setattr(RE, "shape", lambda **k: pytest.fail("the uncached read"))
    tool = RiverTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: tmp_path,
                     source_fn=lambda: tmp_path / "F", drafts_root=tmp_path / "d", sync=True)
    assert tool._outline_fn(None).cells == _shape().cells and asked == [tmp_path]


def test_a_cache_that_cannot_be_written_still_hands_back_the_shape(tmp_path, monkeypatch):
    """A cache write that fails -- the JSON held open by another reader, a read-only shared cache, two reads racing
    one tmp name -- threw the finished 17-24 s shape away and the card said "The river could not be read" (review
    of the perf commits, K1). The shape comes back; only the cache is skipped, and each writer has its own tmp."""
    cache = tmp_path / "cache"
    (cache).write_text("a file where the cache folder should be")      # mkdir under it fails
    monkeypatch.setattr(RE, "_cache_dir", lambda: cache)
    got = RE.cached_shape(tmp_path / "game", read=lambda game=None: _shape())
    assert got.cells == _shape().cells
    monkeypatch.setattr(RE, "_cache_dir", lambda: tmp_path / "ok")
    real = type(tmp_path).replace
    monkeypatch.setattr(type(tmp_path), "replace", lambda self, dst: (_ for _ in ()).throw(PermissionError(5, "held")))
    got = RE.cached_shape(tmp_path / "game", read=lambda game=None: _shape())
    monkeypatch.setattr(type(tmp_path), "replace", real)
    assert got.cells == _shape().cells
    assert not list((tmp_path / "ok" / "world-river").glob("*.tmp*"))   # no tmp left behind


def test_the_river_cache_reads_again_when_the_install_s_bundles_change(tmp_path, monkeypatch):
    """The cache keyed the install's PATH only: a Steam update or a verify-integrity repair at the same path kept
    handing back the river read from the old bundles (review of the perf commits, K3). The stamp holds each stock
    bundle's name, size and time too."""
    import os
    monkeypatch.setattr(RE, "_cache_dir", lambda: tmp_path / "cache")
    game = tmp_path / "game"
    (game / "StreamingAssets").mkdir(parents=True)
    bundle = game / "StreamingAssets" / "p0data3.bin"
    bundle.write_bytes(b"stock")
    calls = []
    read = (lambda game=None: calls.append(1) or _shape())
    RE.cached_shape(game, read=read)
    RE.cached_shape(game, read=read)
    assert len(calls) == 1
    st = bundle.stat()
    os.utime(bundle, ns=(st.st_atime_ns, st.st_mtime_ns + 10 ** 9))       # the bundle was replaced
    RE.cached_shape(game, read=read)
    assert len(calls) == 2
