"""The World tab's forest tool (overworld editor rung C1), offscreen: workspace.worldforest + its World tab wiring.

The tool never carves in the Workspace's process; every judgement is a ``world-forest`` job. Here the job runner is
scripted (it writes the verdict a real job would), except in THE C1 ACCEPTANCE at the bottom, where the runner runs
``cli.main`` on the tool's own argv in-process -- what its subprocess runs -- and the draft it writes is compared
byte for byte with the same forest typed by hand. The donor read is monkeypatched there (no game bytes).
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

from PySide6.QtWidgets import QApplication                                      # noqa: E402

from ff9mapkit.editor.theme import pick_palette                                 # noqa: E402
from ff9mapkit.world import draft as D                                          # noqa: E402
from ff9mapkit.world import forestedit as FE                                    # noqa: E402
from ff9mapkit.world import interior as IN                                      # noqa: E402
from ff9mapkit.world import mesh as M                                           # noqa: E402

from .test_world_interior import _canopy_dome, _mains_grid, _patch_donor        # noqa: E402
from .test_worldview3d import _mouse                                            # noqa: E402

PAL = pick_palette("dark")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _no_real_install(monkeypatch):
    """NEVER THE REAL INSTALL (see test_world_forestedit): a missing tmp game path raises, never auto-detects."""
    from ff9mapkit import config
    monkeypatch.delenv("FF9_GAME_PATH", raising=False)
    monkeypatch.setattr(config, "_read_user_config", lambda: {})
    for name in ("_registry_candidates", "_steam_library_candidates", "_fallback_candidates"):
        monkeypatch.setattr(config, name, lambda: [])


def _game(tmp_path) -> Path:
    """A tmp install holding FF9CustomMap-world: one block of mains grass (13x13 cells of 4u at y 3.2)."""
    g = tmp_path / "game"
    g.mkdir(parents=True, exist_ok=True)
    M.deploy_override(_mains_grid(), mod_folder="FF9CustomMap-world", game=g, part="Terrain", disc=1)
    return g


def _outline():
    """A 20 x 20 canopy outline: a square rim of 16 points on 0, a 1u-high plateau inside (invented geometry)."""
    rim = [(-10 + 5 * k, 0.0, 10.0) for k in range(4)] + [(10.0, 0.0, 10 - 5 * k) for k in range(4)] + \
          [(10 - 5 * k, 0.0, -10.0) for k in range(4)] + [(-10.0, 0.0, -10 + 5 * k) for k in range(4)]
    tris = np.array([[(-10, 1, -10), (10, 1, -10), (10, 1, 10)], [(-10, 1, -10), (10, 1, 10), (-10, 1, 10)]],
                    dtype=np.float64)
    return FE.Outline((15, 15), tris, np.array(rim, dtype=np.float64), (20.0, 20.0))


class Scripted:
    """A runner that answers each job with the verdict ``answer(kind, argv)`` returns (written where the real job
    writes it), synchronously, and records every argv."""

    def __init__(self, answer=None):
        self.argvs, self.killed = [], 0
        self.answer = answer or (lambda kind, argv: {"ok": True, "dry_run": kind == "check", "center": [26, -26],
                                                     "report": {"blob_tris": 50, "dropped": 96, "zip_tris": 46,
                                                                "wall_rise": 1.0},
                                                     "blocks": [[0, 0], [1, 0]], "refused": None,
                                                     "written": [] if kind == "check" else
                                                     ["d/FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"]})
        self.hold = False                                  # True: start() records but never finishes (a running job)
        self.pending = None

    def start(self, argv, cwd, done):
        self.argvs.append(argv)
        kind = "check" if "--dry-run" in argv else "accept"
        rep = Path(argv[argv.index("--report-json") + 1])
        verdict = self.answer(kind, argv)

        def finish():
            if verdict is not None:
                rep.write_text(json.dumps(verdict), encoding="utf-8")
            done(0 if verdict and verdict["ok"] else 2, "")
        if self.hold:
            self.pending = finish
        else:
            finish()

    def kill(self):
        self.killed += 1
        self.pending = None

    def busy(self):
        return self.pending is not None


def _tool(app, tmp_path, runner=None, **kw):
    from ff9mapkit.workspace.worldforest import ForestTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    game = _game(tmp_path)
    ix = FE.SoupIndex(IN.soup_from_blocks({(0, 0): _mains_grid()}))
    panel = WorldView3DPanel(PAL)
    changed = []
    tool = ForestTool(PAL, panel, game_fn=lambda: game, source_fn=lambda: game / "FF9CustomMap-world",
                      runner=runner or Scripted(), drafts_root=tmp_path / "drafts", sync=True,
                      outline_fn=lambda donor: _outline(), soup_fn=lambda folder: ix, on_changed=changed.append,
                      **kw)
    tool.open_tool()
    return tool, panel, changed


def _settle(tool):
    """Fire the check the handles' timer would (the debounce is a timer; the tests do not wait on it)."""
    tool._timer.stop()
    tool._check()


# ---------------------------------------------------------------- the handles are the laws
def test_the_handles_stop_where_the_laws_do(app, tmp_path):
    """THE CALL-SITE LAW for the handles: the spread spin stops at the interior's own ceiling constant, the angle
    wraps a whole turn, and the donor picker offers exactly the catalogue's qualified canopies."""
    tool, _p, _c = _tool(app, tmp_path)
    assert tool.spread.minimum() == 1.0 and tool.spread.maximum() == IN.FOREST_SPREAD_MAX
    assert (tool.angle.minimum(), tool.angle.maximum(), tool.angle.wrapping()) == (0, 359, True)
    assert [tool.donor_box.itemData(i) for i in range(tool.donor_box.count())] == \
        ["{},{}".format(*r["donor"]) for r in FE.canopy_donors()]


# ---------------------------------------------------------------- the flow
def test_a_click_places_a_ghost_the_check_judges_and_accept_writes_the_draft(app, tmp_path):
    run = Scripted()
    tool, panel, changed = _tool(app, tmp_path, run)
    assert not tool.accept_btn.isEnabled() and "Click the map" in tool.verdict_lbl.text()
    tool.place(26.04, -25.97, 3.2)
    assert tool.center == (26.0, -26.0)                    # the editor's grid: commands stay short and exact
    assert len(panel._overlays) == 2 and panel._ghost["center"] == (26.0, -26.0)
    assert np.isclose(panel._ghost["y"], 3.2)              # the rim sits on the island's own ground
    assert "Footprint lawful" in tool.verdict_lbl.text() and not run.argvs
    _settle(tool)
    (argv,) = run.argvs
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    assert argv[1:5] == ["-m", "ff9mapkit", "--game", str(tmp_path / "game")]
    assert argv[5:] == FE.command(draft, (26.0, -26.0), tool.donor(), dry_run=True,
                                  report=argv[-1])
    assert D.read_meta(draft) is not None                  # the first check made the draft, outside the install
    assert tool.verdict_lbl.property("state") == "ok" and "Passes every gate" in tool.verdict_lbl.text()
    assert tool.accept_btn.isEnabled()
    tool.accept_btn.click()
    assert "--dry-run" not in run.argvs[1] and run.argvs[1][5:9] == ["world-forest", "--mod-folder", str(draft),
                                                                     "--center"]
    assert changed == [draft] and tool.center is None and panel._overlays == [] and panel._ghost is None
    assert "In the draft: 1 block written" in tool.verdict_lbl.text()


def test_a_verdict_for_handles_that_moved_is_never_shown(app, tmp_path):
    """The stale guard: a check answers the handles it was asked about; turning the forest after it makes the
    verdict moot (Accept stays off) and a running check is killed rather than left to answer late."""
    run = Scripted()
    tool, _p, _c = _tool(app, tmp_path, run)
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    assert tool.accept_btn.isEnabled()
    tool.angle.setValue(90)
    assert not tool.accept_btn.isEnabled() and "Footprint lawful" in tool.verdict_lbl.text()
    run.hold = True
    _settle(tool)
    assert run.pending is not None and "Checking every gate" in tool.verdict_lbl.text()
    late = run.pending
    tool.spread.setValue(1.25)                             # moved while the check ran
    assert run.killed >= 1
    late()                                                 # the killed job's answer arriving anyway
    assert not tool.accept_btn.isEnabled() and tool._current_verdict() is None


def test_a_refusal_is_drawn_where_the_gate_says(app, tmp_path):
    def refuse(kind, argv):
        return {"ok": False, "dry_run": True, "center": None, "report": None, "blocks": [], "written": [],
                "refused": {"gate": "walk-in", "message": "a rim segment climbs 2.61 > 2.3 at (31.0, -17.5)",
                            "detail": "", "where": [[31.0, -17.5]]}}
    tool, panel, _c = _tool(app, tmp_path, Scripted(refuse))
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    assert tool.verdict_lbl.property("state") == "error"
    assert "Refused by the walk-in simulation" in tool.verdict_lbl.text() and "2.61" in tool.verdict_lbl.text()
    assert not tool.accept_btn.isEnabled()
    marks = panel._overlays[2:]
    assert len(marks) == 1
    pin = marks[0][0]
    assert np.allclose(pin[:, 0].mean(), 31.0) and np.allclose(pin[:, 2].mean(), -17.5)
    assert marks[0][1] == tuple(int(PAL["error"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def test_the_preview_refuses_before_any_job_runs(app, tmp_path):
    """Off the island the cheap law answers at once, and no job is started for a forest that cannot pass."""
    run = Scripted()
    tool, panel, _c = _tool(app, tmp_path, run)
    tool.place(200.0, -200.0, 0.0)
    _settle(tool)
    assert not run.argvs and tool.verdict_lbl.property("state") == "warn"
    assert "open grass" in tool.verdict_lbl.text() or "Not on an island" in tool.verdict_lbl.text()
    assert len(panel._overlays) >= 3                       # the ghost, its rim, and where it fails


def test_a_click_before_the_reads_land_is_judged_when_they_do(app, tmp_path):
    """A click that lands while the canopy is still being read fires its check into nothing; the read landing
    must start it (it once never ran)."""
    run = Scripted()
    tool, _p, _c = _tool(app, tmp_path, run)
    tool._outlines.clear()
    tool._bg = lambda what, fn: None                       # hold the outline read: nothing to judge yet
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    assert not run.argvs and "Reading" in tool.verdict_lbl.text()
    del tool._bg                                           # the reads work again (the instance stub goes)
    tool._on_bg("outline", 0, (tool.donor(), _outline()), None)
    assert tool._timer.isActive()
    tool._timer.stop()                                     # the read restarted the check at once; fire it
    tool._check()
    assert len(run.argvs) == 1 and tool.accept_btn.isEnabled()


def test_copy_command_targets_the_draft_never_the_live_folder(app, tmp_path):
    tool, _p, _c = _tool(app, tmp_path)
    tool.place(26.0, -26.0, 3.2)
    tool.spread.setValue(1.33)
    tool.copy_btn.click()
    text = QApplication.clipboard().text()
    assert "FF9CustomMap-world.draft" in text and "--spread 1.33" in text and "--dry-run" not in text
    assert str(tmp_path / "game" / "FF9CustomMap-world") + " " not in text + " "


def test_a_job_that_dies_without_a_verdict_says_so(app, tmp_path):
    tool, _p, _c = _tool(app, tmp_path, Scripted(lambda kind, argv: None))
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    assert tool.verdict_lbl.property("state") == "error" and "without a verdict" in tool.verdict_lbl.text()


def test_discard_asks_and_then_removes_only_the_draft(app, tmp_path):
    asked = []
    tool, _p, changed = _tool(app, tmp_path, ask=lambda title, text: asked.append(text) or True)
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    draft = tool.draft()
    assert draft is not None and not tool.discard_btn.isHidden()
    tool.discard_btn.click()
    assert asked and "The install is not touched" in asked[0]
    assert not draft.exists() and (tmp_path / "game" / "FF9CustomMap-world").is_dir()
    assert changed[-1] is None and tool.discard_btn.isHidden()


# ---------------------------------------------------------------- the ghost drag (real event delivery)
def test_dragging_the_ghost_moves_the_forest_and_a_drag_elsewhere_still_orbits(app):
    """Through QApplication.sendEvent: a press inside the ghost's plan drags it on its own level (ghost_moved per
    move, ghost_dropped on release) and the camera holds still; a press outside it orbits as before."""
    from ff9mapkit.workspace import worldview3d as V
    w = V.WorldView3D()
    w.resize(320, 200)
    w.camera = V.OrbitCamera(target=(30.0, 0.0, -30.0), yaw=0.0, pitch=60.0, dist=80.0)
    cx, cz = 30.0, -30.0
    w.set_ghost({"center": (cx, cz), "y": 0.0, "poly": np.array([(cx - 8, cz - 8), (cx + 8, cz - 8),
                                                                (cx + 8, cz + 8), (cx - 8, cz + 8)])})
    moved, dropped = [], []
    w.ghost_moved.connect(lambda x, z: moved.append((x, z)))
    w.ghost_dropped.connect(lambda x, z: dropped.append((x, z)))
    yaw0 = w.camera.yaw
    _mouse(w, "press", (160, 100))
    _mouse(w, "move", (180, 100))
    _mouse(w, "move", (200, 100))
    _mouse(w, "release", (200, 100))
    assert moved and dropped and w.camera.yaw == yaw0
    x1, z1 = dropped[0]
    assert abs(z1 - cz) < 1.0 and abs(x1 - cx) > 5.0       # slid sideways on the ground, not up the screen
    _mouse(w, "press", (10, 10))                           # outside the ghost: the camera's, as ever
    _mouse(w, "move", (60, 10))
    _mouse(w, "release", (60, 10))
    assert len(dropped) == 1 and w.camera.yaw != yaw0


def test_a_ribbon_stands_on_its_ring_and_the_plane_hit_inverts_the_ray():
    from ff9mapkit.workspace import worldview3d as V
    ring = np.array([(0, 2.0, 0), (4, 2.0, 0), (4, 2.0, -4)], dtype=np.float64)
    rib = V.ribbon_tris(ring, 1.5)
    assert rib.shape == (18, 3) and set(np.round(rib[:, 1], 6)) == {2.0, 3.5}
    view = V.OrbitCamera(target=(10.0, 0.0, -10.0), yaw=20.0, pitch=50.0, dist=60.0).view()
    x, z = V.plane_hit(view, (400, 300), 200.5, 150.5, 0.0)
    assert abs(x - 10.0) < 0.05 and abs(z + 10.0) < 0.05


# ---------------------------------------------------------------- the World tab
def _doc(app, tmp_path, **kw):
    from ff9mapkit.workspace.worlddoc import WorldDoc
    game = _game(tmp_path)
    (game / "Memoria.ini").write_text('[Mod]\nFolderNames = "FF9CustomMap", "FF9CustomMap-world", "MoguriMain"\n',
                                      encoding="utf-8")
    ix = FE.SoupIndex(IN.soup_from_blocks({(0, 0): _mains_grid()}))
    doc = WorldDoc(PAL, game_path_fn=lambda: game, drafts_root=tmp_path / "drafts", forest_runner=Scripted(),
                   forest_seams={"outline_fn": lambda d: _outline(), "soup_fn": lambda f: ix, "sync": True}, **kw)
    doc._census, doc._game = SimpleNamespace(root=game / "FF9CustomMap-world"), game
    return doc, game


def test_the_forest_button_is_a_3d_page_control_and_opens_the_tool_there(app, tmp_path):
    doc, _g = _doc(app, tmp_path)
    assert doc.tools_btn.isHidden() and doc._forest is None
    doc.set_view_mode("3d", sync=True)
    assert not doc.tools_btn.isHidden()
    doc.tool_actions["forest"].trigger()
    assert doc._forest is not None and not doc._forest.isHidden()
    doc._on_pick(((26.0, 3.2, -26.0), "Terrain"), sync=True)
    assert doc._forest.center == (26.0, -26.0)             # a click on the map places the forest
    doc.set_view_mode("chart")
    assert doc._forest.isHidden() and doc.tools_btn.isHidden() and doc._forest.center is None


def test_an_open_card_takes_the_strip_s_room_and_the_view_gives_way_first(app, tmp_path):
    """THE 931px FLOOR: card, block strip and view together floored the page at 931px tall at 150% (984 with the
    mountain's second row), so in a 1280x850 window the card's verdict and draft line were clipped. While a card is
    open the strip goes, the view's floor drops to CARD_VIEW_FLOOR -- on the host too, and with the status page
    out of the stack, whose wrapped teach line otherwise sets the host's height for width and outranks it -- and a
    PLAIN caption folds (room for C3's recipe bar too). A caption carrying a warning never folds."""
    from ff9mapkit.workspace.worlddoc import CARD_VIEW_FLOOR
    from ff9mapkit.workspace.worldview3d import MIN_VIEW_H
    doc, _g = _doc(app, tmp_path)
    doc.set_view_mode("3d", sync=True)
    panel = doc._view3d
    assert not doc._strip.isHidden() and panel._host.minimumHeight() == 0
    assert not panel.caption.isHidden() and "as the game loads it" in panel.caption.text()
    doc.open_forest(sync=True)
    assert doc._strip.isHidden() and panel._host.minimumHeight() == CARD_VIEW_FLOOR < MIN_VIEW_H
    assert panel.caption.isHidden() and "as the game loads it" in panel.caption.text()   # folded, text kept
    doc.draw_box.setCurrentIndex(doc.draw_box.findData("folder"))     # a caption that warns: it stays on the face
    doc._load_view3d(sync=True)
    assert not panel.caption.isHidden() and "looks different in game" in panel.caption.text()
    doc.draw_box.setCurrentIndex(doc.draw_box.findData("stack"))
    doc._load_view3d(sync=True)
    assert panel.caption.isHidden()
    if panel.view is not None:                             # the GL view exists once the map loaded
        assert panel.view.minimumHeight() == CARD_VIEW_FLOOR
        assert panel._stack.indexOf(panel._status) < 0 and panel._stack.currentWidget() is panel.view
    doc._forest.close_btn.click()
    assert not doc._strip.isHidden() and panel._host.minimumHeight() == 0 and not panel.caption.isHidden()
    if panel.view is not None:
        assert panel.view.minimumHeight() == MIN_VIEW_H
    doc.open_forest(sync=True)
    doc.set_view_mode("chart")                             # leaving the 3D page puts the card away: the strip is back
    assert not doc._strip.isHidden()


def test_after_accept_the_view_draws_the_draft_in_place_of_its_folder(app, tmp_path):
    doc, game = _doc(app, tmp_path)
    doc.open_forest(sync=True)
    assert doc.draw_box.findData("draft") < 0              # no draft yet: nothing to offer
    doc._forest.place(26.0, -26.0, 3.2)
    _settle(doc._forest)
    doc._forest.accept_btn.click()
    assert doc.draw_box.currentData() == "draft"
    site, cap = doc._render_site()
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    assert [p.name for p in site.stack] == ["FF9CustomMap", draft.name, "MoguriMain"]
    assert cap.startswith("Drawn with your draft in place of FF9CustomMap-world")
    assert "the draft of FF9CustomMap-world › MoguriMain › stock" in cap and "does not load the draft" in cap


# ---------------------------------------------------------------- rung C4: promote, revert, and the game follows
class PromoteToo(Scripted):
    """Scripted world-forest jobs; world-promote jobs run the real ``cli.main`` in-process (what the subprocess runs)."""

    def start(self, argv, cwd, done):
        if "world-promote" in argv:
            from ff9mapkit import cli
            self.argvs.append(argv)
            done(cli.main([str(a) for a in argv[3:]]), "")
            return
        super().start(argv, cwd, done)


def test_promote_asks_writes_the_live_folder_and_the_game_can_follow(app, monkeypatch, tmp_path):
    from .test_world_forestedit import _fake_mirror
    _fake_mirror(monkeypatch)
    asked, reloads = [], []
    run = PromoteToo()
    tool, panel, changed = _tool(app, tmp_path, run, ask=lambda t, text: asked.append(t) or True,
                                 on_reload=lambda x, z: reloads.append((x, z)))
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    tool.accept_btn.click()                                # scripted: the draft itself is edited by hand below
    draft = tool.draft()
    rel = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
    (draft / rel).write_bytes(b"the forest")
    tool._refresh_draft_label()
    assert not tool.promote_btn.isHidden() and tool.revert_btn.isHidden()
    assert not tool.show_btn.isHidden()                    # the accepted forest is where Show in game goes
    tool.promote_btn.click()
    assert asked == ["Promote the draft?"]
    (argv,) = [a for a in run.argvs if "world-promote" in a]
    assert argv[5:7] == ["world-promote", str(draft)] and "--revert" not in argv
    live = tmp_path / "game" / "FF9CustomMap-world" / rel
    assert live.read_bytes() == b"the forest"
    assert tool.verdict_lbl.property("state") == "ok" and "Promoted into FF9CustomMap-world" in tool.verdict_lbl.text()
    assert changed[-1] is None                             # the view goes back to the game's own stack
    assert tool.promote_btn.isHidden() and not tool.revert_btn.isHidden()
    tool.show_btn.click()
    assert reloads == [(26.0, -26.0)]
    tool.revert_btn.click()
    assert asked[-1] == "Revert the promote?" and live.read_bytes() != b"the forest"
    assert "Reverted" in tool.verdict_lbl.text() and changed[-1] == draft
    assert not tool.promote_btn.isHidden() and tool.revert_btn.isHidden()


def test_the_promote_actions_ride_the_draft_line_and_never_widen_the_card(app, tmp_path):
    """THE 1348px FLOOR: Promote, Revert promote and Show in game shared one row with Accept, Copy, the draft line and
    Discard, so the promoted card floored the window at 1348px at 150% (1152 in every other state). They ride the
    draft line's row now, and showing them leaves the card's floor where it was. Relative widths only: offscreen
    fonts invent the absolute ones."""
    tool, _panel, _changed = _tool(app, tmp_path, on_reload=lambda x, z: None)
    acts = (tool.promote_btn, tool.revert_btn, tool.show_btn)
    assert all(tool.draft_row.indexOf(b) >= 0 for b in acts + (tool.draft_lbl,))
    assert all(tool.accept_row.indexOf(b) >= 0 for b in (tool.accept_btn, tool.copy_btn, tool.discard_btn))

    def floor():
        app.processEvents()                                 # the layouts' LayoutRequest: a hint is cached until then
        return tool.minimumSizeHint().width()
    for b in acts + (tool.discard_btn,):
        b.hide()
    bare = floor()
    for b in acts + (tool.discard_btn,):
        b.show()
    assert floor() == bare                                  # every action showing: the floor has not moved
    for b in acts:                                          # anti-vacuity: on the Accept row they DO move it
        tool.accept_row.addWidget(b)
    assert floor() > bare


def test_a_refused_promote_says_why_and_writes_nothing(app, monkeypatch, tmp_path):
    from .test_world_forestedit import _fake_mirror
    _fake_mirror(monkeypatch)
    run = PromoteToo()
    tool, _p, changed = _tool(app, tmp_path, run, ask=lambda t, text: True)
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    draft = tool.draft()
    rel = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
    (draft / rel).write_bytes(b"the forest")
    live = tmp_path / "game" / "FF9CustomMap-world" / rel
    live.write_bytes(b"another session")                   # someone deployed there after the draft was made
    tool._refresh_draft_label()
    tool.promote_btn.click()
    assert tool.verdict_lbl.property("state") == "error" and "another deploy wrote them" in tool.verdict_lbl.text()
    assert live.read_bytes() == b"another session" and changed == []


def test_without_the_dev_reload_show_in_game_never_shows(app, tmp_path):
    tool, _p, _c = _tool(app, tmp_path)
    tool._last_center = (26.0, -26.0)
    tool._sync_buttons()
    assert tool.show_btn.isHidden()


# ---------------------------------------------------------------- THE C1 ACCEPTANCE: the editor's bytes
def test_the_editor_writes_the_bytes_the_hand_typed_command_writes(monkeypatch, tmp_path, app):
    """The forest tool accepts into a draft through its own job argv; the same forest typed by hand against a
    copy of the same island writes the same bytes. Every world mesh file is compared, and the source folder is
    never written."""
    from ff9mapkit import cli
    from ff9mapkit.workspace.worldforest import ForestTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    game = _game(tmp_path)
    shutil.copytree(game / "FF9CustomMap-world", game / "Hand")
    before = {p: p.read_bytes() for p in (game / "FF9CustomMap-world").rglob("*") if p.is_file()}
    _patch_donor(monkeypatch, _canopy_dome())

    class InProcess:                                       # what the subprocess runs, run here (same argv)
        def __init__(self):
            self.argvs = []

        def start(self, argv, cwd, done):
            assert argv[1:3] == ["-m", "ff9mapkit"] and Path(cwd) == Path(FE.__file__).resolve().parents[2]
            self.argvs.append(argv)
            done(cli.main([str(a) for a in argv[3:]]), "")

        def kill(self):
            pass

        def busy(self):
            return False
    run = InProcess()
    tool = ForestTool(PAL, WorldView3DPanel(PAL), game_fn=lambda: game,
                      source_fn=lambda: game / "FF9CustomMap-world", runner=run, drafts_root=tmp_path / "drafts",
                      sync=True, outline_fn=lambda donor: FE.outline(donor, game=game))
    tool.donor_box.setCurrentIndex(tool.donor_box.findData("15,15"))
    assert tool.donor() == (15, 15)
    tool.open_tool()
    tool.place(26.0, -26.0, 3.2)
    _settle(tool)
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert [a[a.index("--center") + 1] for a in run.argvs] == ["26,-26", "26,-26"]
    assert "--dry-run" in run.argvs[0] and "--dry-run" not in run.argvs[1]
    draft = tmp_path / "drafts" / "FF9CustomMap-world.draft"
    assert (1, 0, 0) in D.edited_blocks(draft) and tool.draft() == draft

    assert cli.main(["--game", str(game), "world-forest", "--mod-folder", "Hand", "--center", "26,-26",
                     "--donor", "15,15"]) == 0

    def world(root):
        return {p.relative_to(root).as_posix(): p.read_bytes()
                for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh")}
    hand, ed = world(game / "Hand"), world(draft)
    assert hand == ed and len(hand) >= 1                   # (no stock Disc4 here, so no mirror file to compare)
    assert ed != world(game / "FF9CustomMap-world")        # and the forest is really in it
    assert {p: p.read_bytes() for p in (game / "FF9CustomMap-world").rglob("*") if p.is_file()} == before
