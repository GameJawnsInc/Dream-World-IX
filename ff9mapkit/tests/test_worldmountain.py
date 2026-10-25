"""The World tab's mountain tool (overworld editor rung C2), offscreen: workspace.worldmountain + its World tab wiring.

As for the forest (``tests/test_worldforest.py``): the job runner is scripted, except in THE C2 ACCEPTANCE at the
bottom, where it runs ``cli.main`` on the tool's own argv in-process and the draft it writes is compared byte for
byte with the same mountain typed by hand. The donor read is monkeypatched (no game bytes): the rock pyramid of
``tests/test_world_interior.py``.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="GUI extra not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ff9mapkit.world import draft as D                                          # noqa: E402
from ff9mapkit.world import interior as IN                                      # noqa: E402
from ff9mapkit.world import mesh as M                                           # noqa: E402
from ff9mapkit.world import mountainedit as ME                                  # noqa: E402
from ff9mapkit.world.extract import encode_id                                   # noqa: E402

from .test_world_interior import _MAIN_U, _bm, _mountain_bench, _patch_donor, _pyramid_donor   # noqa: E402
from .test_worldforest import PAL, Scripted, _no_real_install, _outline, _settle, app  # noqa: E402,F401

UAHO = "0,0"


def _game(tmp_path, bench=None) -> Path:
    """A tmp install whose FF9CustomMap-world holds one block of mains grass with a coast tri in its far corner."""
    g = tmp_path / "game"
    g.mkdir(parents=True, exist_ok=True)
    M.deploy_override(bench or _mountain_bench(), mod_folder="FF9CustomMap-world", game=g, part="Terrain", disc=1)
    return g


def _desert_bench():
    DESERT, DES_U = float(encode_id(topograph=17)), _MAIN_U + 0.65332
    tris = []
    for i in range(13):
        for j in range(13):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            tris.append((((x0, 3.2, z0), (x1, 3.2, z0), (x0, 3.2, z1)), DESERT, DES_U))
            tris.append((((x1, 3.2, z0), (x1, 3.2, z1), (x0, 3.2, z1)), DESERT, DES_U))
    return _bm(tris)


def _passes(kind, argv):
    return {"ok": True, "dry_run": kind == "check", "center": [26, -26], "ground": "grass", "note": None,
            "report": {"blob_tris": 4, "plugs": 0, "dropped": 30, "zip_tris": 24, "peak_y": 7.2, "rock_rigid": 0.0,
                       "teleport": [8.5, -26.0]},
            "blocks": [[0, 0]], "refused": None,
            "written": [] if kind == "check" else ["d/FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"]}


def _tool(app, monkeypatch, tmp_path, runner=None, bench=None, **kw):
    from ff9mapkit.workspace.worldmountain import MountainTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    _patch_donor(monkeypatch, _pyramid_donor())
    game = _game(tmp_path, bench)
    ol = ME.outline(UAHO, game=game)
    ix = ME.SoupIndex(IN.soup_from_blocks({(0, 0): bench or _mountain_bench()}))
    panel = WorldView3DPanel(PAL)
    changed = []
    seams = {"outline_fn": lambda donor: ol, "soup_fn": lambda folder: ix, **kw}
    tool = MountainTool(PAL, panel, game_fn=lambda: game, source_fn=lambda: game / "FF9CustomMap-world",
                        runner=runner or Scripted(_passes), drafts_root=tmp_path / "drafts", sync=True,
                        on_changed=changed.append, **seams)
    tool.open_tool()
    return tool, panel, changed


# ---------------------------------------------------------------- the handles are the laws
def test_the_handles_stop_where_the_laws_do(app, monkeypatch, tmp_path):
    """THE CALL-SITE LAW for the handles: spread and height stop at the interior's own ceilings, the angle wraps,
    and the picker offers exactly the catalogue's qualified massifs."""
    tool, _p, _c = _tool(app, monkeypatch, tmp_path)
    assert (tool.spread.minimum(), tool.spread.maximum()) == (1.0, IN.MTN_SPREAD_MAX)
    assert (tool.rock_height.minimum(), tool.rock_height.maximum()) == (1.0, IN.MTN_ROCK_HEIGHT_MAX)
    assert (tool.angle.minimum(), tool.angle.maximum(), tool.angle.wrapping()) == (0, 359, True)
    assert [tool.donor_box.itemData(i) for i in range(tool.donor_box.count())] == \
        [r["donor"] for r in ME.massif_donors()]
    assert tool.donor() == UAHO and tool.rock_height.isEnabled()


def test_a_massif_with_falls_on_its_face_keeps_its_height(app, monkeypatch, tmp_path):
    """The horseshoe class: --rock-height refuses a massif carrying geometry the stretch would leave behind, so the
    handle holds at x1 and says why (and comes back for a massif it can stretch)."""
    tool, _p, _c = _tool(app, monkeypatch, tmp_path)
    tool.rock_height.setValue(1.5)
    fixed = SimpleNamespace(**{**vars(tool._outlines[UAHO]), "height_ok": False})
    tool._outlines["5-6,15-16"] = fixed
    tool.donor_box.setCurrentIndex(tool.donor_box.findData("5-6,15-16"))
    assert not tool.rock_height.isEnabled() and tool.rock_height.value() == 1.0
    assert "falls or a river mouth" in tool.rock_height.toolTip()
    tool.donor_box.setCurrentIndex(tool.donor_box.findData(UAHO))
    assert tool.rock_height.isEnabled()


# ---------------------------------------------------------------- the flow
def test_a_click_places_a_ghost_the_check_judges_and_accept_writes_the_draft(app, monkeypatch, tmp_path):
    run = Scripted(_passes)
    tool, panel, changed = _tool(app, monkeypatch, tmp_path, run)
    assert "Click the map where the mountain goes" in tool.verdict_lbl.text()
    assert tool.ground_chip.text() == "grass at home" and tool.ground_chip.property("kind") == "info"
    tool.place(26.04, -25.97, 3.2)
    assert tool.center == (26.0, -26.0) and panel._ghost["center"] == (26.0, -26.0)
    assert np.isclose(panel._ghost["y"], 3.2)
    ghost = panel._overlays[0][0]
    assert np.isclose(ghost[:, 1].max(), 3.2 + 4.0)        # the pyramid's apex above the seated rim
    assert tool.ground_chip.text() == "grass at home and here" and tool.ground_chip.property("kind") == "good"
    assert "Footprint lawful" in tool.verdict_lbl.text() and not run.argvs
    _settle(tool)
    (argv,) = run.argvs
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    assert argv[5:] == ME.command(draft, (26.0, -26.0), UAHO, dry_run=True, report=argv[-1])
    assert tool.verdict_lbl.property("state") == "ok" and "Passes every gate" in tool.verdict_lbl.text()
    assert "rock rigidity 0.0%" in tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert run.argvs[1][5:9] == ["world-mountain", "--mod-folder", str(draft), "--center"]
    assert "--dry-run" not in run.argvs[1]
    assert changed == [draft] and tool.center is None and panel._ghost is None
    assert "In the draft: 1 block written" in tool.verdict_lbl.text() and "another mountain" in tool.verdict_lbl.text()
    assert tool._last_center == (8.5, -26.0)               # Show in game goes to the carve's own teleport point


def test_the_handles_reach_the_command(app, monkeypatch, tmp_path):
    run = Scripted(_passes)
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, run)
    tool.place(26.0, -26.0, 3.2)
    tool.angle.setValue(90)
    tool.spread.setValue(1.25)
    tool.rock_height.setValue(1.5)
    _settle(tool)
    argv = run.argvs[-1]
    assert argv[argv.index("--rot") + 1] == "90" and argv[argv.index("--spread") + 1] == "1.25"
    assert argv[argv.index("--rock-height") + 1] == "1.5" and "--ground" not in argv and "--reach" not in argv
    ghost = tool._ghost[0]
    assert np.isclose(ghost[..., 1].max(), 3.2 + 6.0)       # the ghost stretched as the carve stretches


def test_on_another_ground_the_command_speaks_it_and_the_chip_warns(app, monkeypatch, tmp_path):
    """The island's ground is the carve's --ground, and a massif off its home ground is flagged (THE HOME-GROUND
    WARNING: lawful, no gate sees it, the owner's call): the chip warns before the check, the verdict after."""
    def warned(kind, argv):
        v = _passes(kind, argv)
        v.update(ground="desert", note="!! WARNING home ground: the uaho massif stands on grass at home")
        return v
    run = Scripted(warned)
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, run, bench=_desert_bench())
    tool.place(26.0, -26.0, 3.2)
    assert tool.ground_chip.text() == "grass at home, desert here" and tool.ground_chip.property("kind") == "warn"
    assert tool.ground_chip.accessibleName() == "warn: grass at home, desert here"
    _settle(tool)
    argv = run.argvs[-1]
    assert argv[argv.index("--ground") + 1] == "desert"
    assert tool.verdict_lbl.property("state") == "warn" and "never meets in stock" in tool.verdict_lbl.text()
    assert tool.accept_btn.isEnabled()                     # a warning, not a refusal


def _worker_lane(tool):
    """The Workspace's lane for ``tool``: each read goes to a worker; here it is held until :func:`_land`."""
    held = []
    tool._sync = False
    tool._bg = lambda what, fn: held.append((what, fn))
    return held


def _land(tool, held):
    while held:
        what, fn = held.pop(0)
        tool._on_bg(what, 0, fn(), None)


def test_a_placed_mountain_on_another_ground_opens_once_the_island_is_read(app, monkeypatch, tmp_path):
    """THE SAID-BACK LAW waits for the reads a mountain row rests on: its --ground follows the island under it and its
    --reach the massif's outline, both read on a worker in the Workspace, and open_tool has just dropped the island.
    Said back at once, a mountain placed on desert read as grass and its edit refused (review of C12). A row the
    handles truly cannot say still refuses, once the reads are in."""
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, bench=_desert_bench())
    tool.place(26.0, -26.0, 3.2)
    row = tool.row()
    assert row["ground"] == "desert"
    tool.close_tool()
    held = _worker_lane(tool)
    tool._outlines.clear()                                 # a massif this card has not read yet either
    tool.open_tool()
    notes = []
    tool.edit_row(row, label="mountain", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    assert tool.editing()
    _land(tool, held)
    assert tool.editing() and notes == [] and tool.row() == row
    tool.close_tool()                                      # (its cancel)
    tool.open_tool()
    notes = []
    tool.edit_row({**row, "ground": "snow"}, label="mountain", on_accepted=lambda: None,
                  on_cancel=lambda note=None: notes.append(note))
    _land(tool, held)
    assert not tool.editing() and len(notes) == 1 and "would not say its ground back" in notes[0], notes


def test_a_mountain_row_held_for_its_reads_freezes_its_handles_and_checks_once_seated(app, monkeypatch, tmp_path):
    """While a mountain row waits for its reads, a retune was said back against the step and cancelled the edit
    (review of the C12 fixes); letting a retune skip the law instead let a row the card cannot say open on whether a
    sub-second read had landed, and a check armed at open ran on the wrong ground and stalled the card (review of its
    fix). Now the handles wait with the row: frozen, a click on the map kept for after, no check until it is seated;
    then the whole row is said back and the check runs at once, on the step's own ground."""
    run = Scripted(_passes)
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, run, bench=_desert_bench())
    tool.place(26.0, -26.0, 3.2)
    row = tool.row()
    tool.close_tool()
    held = _worker_lane(tool)
    tool._outlines.clear()
    tool.open_tool()
    notes = []
    tool.edit_row(row, label="mountain", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    assert all(not w.isEnabled() for w in (tool.donor_box, tool.angle, tool.spread, tool.rock_height))
    tool.place(40.0, -40.0, 3.2)                           # a click while it reads: not taken
    n = len(run.argvs)
    tool._check()                                          # the timer open armed: nothing runs yet
    assert run.argvs[n:] == [] and tool.center == (26.0, -26.0)
    _land(tool, held)
    assert tool.editing() and notes == [] and tool.row() == row
    assert all(w.isEnabled() for w in (tool.donor_box, tool.angle, tool.spread, tool.rock_height))
    assert tool._timer.isActive()                          # seated: judged at once
    tool._timer.stop()
    tool._check()
    _land(tool, held)                                      # (its draft is made first, on a worker)
    argv = run.argvs[-1]
    assert argv[argv.index("--ground") + 1] == "desert"
    tool.close_tool()
    tool.open_tool()
    with pytest.raises(ValueError, match="would not say its center back"):   # off the grid: refused at open
        tool.edit_row({**row, "center": [26.04, -26.0]}, label="mountain", on_accepted=lambda: None,
                      on_cancel=lambda note=None: None)


def test_a_falls_massif_row_with_a_height_still_refuses_once_its_outline_is_read(app, monkeypatch, tmp_path):
    """A massif with falls on its face keeps its height (world-mountain refuses --rock-height for it): a row that
    stretches one is not one the card can say, and it refuses -- it opened, rewritten, while a retune skipped the law
    (review of the C12 fixes, third round)."""
    import dataclasses
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, bench=_desert_bench())
    falls = dataclasses.replace(tool._outline_fn(UAHO), height_ok=False)
    tool._outline_fn = lambda donor: falls
    tool.place(26.0, -26.0, 3.2)
    row = {**tool.row(), "rock_height": 1.5}
    tool.close_tool()
    held = _worker_lane(tool)
    tool._outlines.clear()
    tool.open_tool()
    notes = []
    tool.edit_row(row, label="mountain", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    _land(tool, held)
    assert not tool.editing() and len(notes) == 1 and "rock_height" in notes[0], notes


def test_an_island_read_begun_before_the_edit_does_not_decide_it(app, monkeypatch, tmp_path):
    """An island (soup) read begun while the card was open lands after the bar's Edit lifted the step out of the draft
    (same path, new bytes): the card took any read whose path matched, so the held row's ground was read off the
    island as it was before the lift and a valid edit refused -- or, landing last, the ghost judged a stale island
    (review of the C12 fixes). A read begun before the island changed is dropped."""
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, bench=_desert_bench())
    tool.place(26.0, -26.0, 3.2)
    row = tool.row()
    assert row["ground"] == "desert"
    tool.close_tool()
    desert = tool._soup_fn(None)
    grass = ME.SoupIndex(IN.soup_from_blocks({(0, 0): _mountain_bench()}))
    state = {"ix": grass}                                  # the draft as it was, with the step in it
    tool._soup_fn = lambda folder: state["ix"]
    tool._sync = False
    held = []
    tool._bg = lambda what, fn: held.append((what, fn()))  # a worker reads at once; its result comes later
    tool.open_tool()                                       # a read begins: the island before the lift
    state["ix"] = desert                                   # the bar's Edit lifts the step...
    tool.island_changed()                                  # ...and the tab says so
    tool.open_tool()
    notes = []
    tool.edit_row(row, label="mountain", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    while held:
        what, result = held.pop(0)                         # the read from before the lift lands first
        tool._on_bg(what, 0, result, None)
    assert tool.editing() and notes == [] and tool.row() == row


def test_an_island_read_that_fails_after_the_island_changed_is_dropped(app, monkeypatch, tmp_path):
    """5519e76d dropped a stale island read's result, but its error came back with no generation and wiped the live
    island and said "The island could not be read" whichever read it was -- a read racing a quick second Undo
    (review of the C12 fixes, third round). A read's error carries its generation and its frame too."""
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, bench=_desert_bench())
    good = tool._soup_fn(None)
    calls = {"n": 0}

    def soup_fn(folder):
        calls["n"] += 1
        if calls["n"] == 1:
            raise FileNotFoundError("Block[0][0] Terrain.ff9mesh: the undo is rewriting it")
        return good
    tool._soup_fn = soup_fn
    tool._sync = False
    held = []
    tool._bg = lambda what, fn: held.append((what, fn))

    def deliver_all():
        while held:
            what, fn = held.pop(0)
            try:
                tool._on_bg(what, 0, fn(), None)
            except Exception as e:                       # noqa: BLE001 -- as the worker hands it over
                tool._on_bg(what, 0, None, e)
    tool.island_changed()                                # read 1: the undo rewriting the island under it
    tool.island_changed()                                # the second undo: read 2
    deliver_all()
    assert tool._ix is good and "could not be read" not in tool.verdict_lbl.text()


@pytest.mark.parametrize("fails", ["island", "massif"])
def test_a_held_mountain_row_whose_read_fails_is_cancelled_saying_why(app, monkeypatch, tmp_path, fails):
    """A held row waits for the island and the massif with its handles frozen; when one of those reads failed, nothing
    read it again and the card sat frozen saying "Reading the massif and the island..." with nothing in flight, Cancel
    the only way out (review of the C12 fixes, fourth round). A failed read the held row waits on cancels the edit,
    saying which read failed."""
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, bench=_desert_bench())
    tool.place(26.0, -26.0, 3.2)
    row = tool.row()
    tool.close_tool()

    def broken(*_a):
        raise OSError("a block of the draft could not be read")
    if fails == "island":
        tool._soup_fn = broken
    else:
        tool._outline_fn = broken
    tool._sync = False
    held = []
    tool._bg = lambda what, fn: held.append((what, fn))
    tool._outlines.clear()
    tool.open_tool()
    notes = []
    tool.edit_row(row, label="mountain", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    while held:
        what, fn = held.pop(0)
        try:
            tool._on_bg(what, 0, fn(), None)
        except Exception as e:                           # noqa: BLE001 -- as the worker hands it over
            tool._on_bg(what, 0, None, e)
    assert not tool.editing() and len(notes) == 1 and "could not be read" in notes[0], notes


def test_the_preview_refuses_before_any_job_runs(app, monkeypatch, tmp_path):
    run = Scripted(_passes)
    tool, panel, _c = _tool(app, monkeypatch, tmp_path, run)
    tool.place(46.0, -46.0, 3.2)                           # its band reaches the coast tri in the corner
    _settle(tool)
    assert not run.argvs and tool.verdict_lbl.property("state") == "warn"
    assert "the footprint reaches coast rock (topograph 58)" in tool.verdict_lbl.text()
    assert len(panel._overlays) == 3                       # the ghost, its rim, and where it fails
    tool.place(60.0, -26.0, 3.2)
    assert "too near the edge of the deployed blocks" in tool.verdict_lbl.text()
    tool.place(300.0, -300.0, 0.0)
    assert "Not on an island" in tool.verdict_lbl.text()


def test_the_peak_cap_refuses_a_ghost_stretched_past_stock_s_tallest_terrain(app, monkeypatch, tmp_path):
    run = Scripted(_passes)
    from ff9mapkit.workspace.worldmountain import MountainTool  # noqa: F401
    tool, _p, _c = _tool(app, monkeypatch, tmp_path, run)
    _patch_donor(monkeypatch, _pyramid_donor(apex=22.0))
    tall = ME.outline(UAHO, game=tmp_path / "game")
    tool._outlines[UAHO] = tall
    tool.place(26.0, -26.0, 3.2)
    assert "Footprint lawful" in tool.verdict_lbl.text()   # x1: 3.2 + 22 stands under 42.68
    tool.rock_height.setValue(2.0)                          # x2: 3.2 + 44
    _settle(tool)
    assert not run.argvs and "Too tall" in tool.verdict_lbl.text() and "y 47.2" in tool.verdict_lbl.text()


def test_a_refusal_is_drawn_where_the_gate_says(app, monkeypatch, tmp_path):
    def refuse(kind, argv):
        return {"ok": False, "dry_run": True, "center": None, "report": None, "blocks": [], "written": [],
                "ground": "grass", "note": None,
                "refused": {"gate": "apron", "message": "the ground apron exceeds the grass slope envelope",
                            "detail": "31.2 deg > 29.5", "where": [[20.0, -30.0]]}}
    tool, panel, _c = _tool(app, monkeypatch, tmp_path, Scripted(refuse))
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    assert tool.verdict_lbl.property("state") == "error"
    assert "Refused by the apron slope (31.2 deg > 29.5)" in tool.verdict_lbl.text()
    (mark,) = panel._overlays[2:]
    assert np.allclose(mark[0][:, 0].mean(), 20.0) and np.allclose(mark[0][:, 2].mean(), -30.0)


# ---------------------------------------------------------------- the World tab
def _doc(app, monkeypatch, tmp_path):
    from ff9mapkit.workspace.worlddoc import WorldDoc
    _patch_donor(monkeypatch, _pyramid_donor())
    game = _game(tmp_path)
    (game / "Memoria.ini").write_text('[Mod]\nFolderNames = "FF9CustomMap", "FF9CustomMap-world", "MoguriMain"\n',
                                      encoding="utf-8")
    ix = ME.SoupIndex(IN.soup_from_blocks({(0, 0): _mountain_bench()}))
    ol = ME.outline(UAHO, game=game)
    doc = WorldDoc(PAL, game_path_fn=lambda: game, drafts_root=tmp_path / "drafts", forest_runner=Scripted(),
                   forest_seams={"outline_fn": lambda d: _outline(), "soup_fn": lambda f: ix, "sync": True},
                   mountain_runner=Scripted(_passes),
                   mountain_seams={"outline_fn": lambda d: ol, "soup_fn": lambda f: ix, "sync": True})
    doc._census, doc._game = SimpleNamespace(root=game / "FF9CustomMap-world"), game
    return doc, game


def test_the_mountain_button_opens_its_card_and_one_card_is_open_at_a_time(app, monkeypatch, tmp_path):
    doc, _g = _doc(app, monkeypatch, tmp_path)
    assert doc.tools_btn.isHidden() and doc._mountain is None
    doc.set_view_mode("3d", sync=True)
    assert not doc.tools_btn.isHidden()
    assert [a.text() for a in doc.tools_btn.menu().actions()] == ["Add forest", "Add mountain", "Add a hill", "Add an island",
                                                                   "Shape a coast", "Carry a coast", "Move the river",
                                                                   "Sink an island"]
    doc.tool_actions["forest"].trigger()
    doc.tool_actions["mountain"].trigger()
    assert not doc._mountain.isHidden() and doc._forest.isHidden()
    doc._on_pick(((26.0, 3.2, -26.0), "Terrain"), sync=True)
    assert doc._mountain.center == (26.0, -26.0) and doc._forest.center is None
    doc._view3d.ghost_dropped.emit(30.0, -30.0)            # the drag goes to the open card only
    assert doc._mountain.center == (30.0, -30.0) and doc._forest.center is None
    doc.set_view_mode("chart")
    assert doc._mountain.isHidden() and doc.tools_btn.isHidden()


def test_a_forest_accepted_meanwhile_is_read_when_the_mountain_opens_again(app, monkeypatch, tmp_path):
    """Both tools write the one draft: a card that opens re-reads the island, never a soup from before the other
    tool's Accept."""
    doc, _g = _doc(app, monkeypatch, tmp_path)
    reads = []
    doc._mountain_seams["soup_fn"] = (lambda f, real=doc._mountain_seams["soup_fn"]: reads.append(f) or real(f))
    doc.open_mountain(sync=True)
    doc.open_forest(sync=True)
    doc.open_mountain(sync=True)
    assert len(reads) == 2


# ---------------------------------------------------------------- THE C2 ACCEPTANCE: the editor's bytes
def test_the_editor_writes_the_bytes_the_hand_typed_command_writes(monkeypatch, tmp_path, app):
    """The mountain tool accepts into a draft through its own job argv; the same mountain typed by hand against a
    copy of the same island writes the same bytes. Every world mesh file is compared, and the source folder is
    never written. Turned, spread and heightened, so every handle is on the line."""
    from ff9mapkit import cli
    from ff9mapkit.workspace.worldforest import kit_cwd
    from ff9mapkit.workspace.worldmountain import MountainTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    _patch_donor(monkeypatch, _pyramid_donor())
    game = _game(tmp_path)
    shutil.copytree(game / "FF9CustomMap-world", game / "Hand")
    before = {p: p.read_bytes() for p in (game / "FF9CustomMap-world").rglob("*") if p.is_file()}

    class InProcess:                                       # what the subprocess runs, run here (same argv)
        def __init__(self):
            self.argvs = []

        def start(self, argv, cwd, done):
            assert argv[1:3] == ["-m", "ff9mapkit"] and Path(cwd) == kit_cwd()
            self.argvs.append(argv)
            done(cli.main([str(a) for a in argv[3:]]), "")

        def kill(self):
            pass

        def busy(self):
            return False
    run = InProcess()
    tool = MountainTool(PAL, WorldView3DPanel(PAL), game_fn=lambda: game,
                        source_fn=lambda: game / "FF9CustomMap-world", runner=run, drafts_root=tmp_path / "drafts",
                        sync=True)
    tool.open_tool()
    tool.place(26.0, -26.0, 3.2)
    tool.angle.setValue(30)
    tool.spread.setValue(1.2)
    tool.rock_height.setValue(1.5)
    _settle(tool)
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert len(run.argvs) == 2 and "--dry-run" in run.argvs[0] and "--dry-run" not in run.argvs[1]
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    assert (1, 0, 0) in D.edited_blocks(draft) and tool.draft() == draft

    assert cli.main(["--game", str(game), "world-mountain", "--mod-folder", "Hand", "--center", "26,-26",
                     "--donor", "0,0", "--rot", "30", "--spread", "1.2", "--rock-height", "1.5"]) == 0

    def world(root):
        return {p.relative_to(root).as_posix(): p.read_bytes()
                for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh")}
    hand, ed = world(game / "Hand"), world(draft)
    assert hand == ed and len(hand) >= 1                   # (no stock Disc4 here, so no mirror file to compare)
    assert ed != world(game / "FF9CustomMap-world")        # and the massif is really in it
    assert {p: p.read_bytes() for p in (game / "FF9CustomMap-world").rglob("*") if p.is_file()} == before
    v = json.loads(Path(run.argvs[1][-1]).read_text())
    assert v["ok"] and v["report"]["rock_height"]["scale"] == 1.5 and v["report"]["spread"] == 1.2
