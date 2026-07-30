"""FloorplanDoc + PlanCanvas — click-authoring Rung 6c's Workspace host.

Pins the host half of the floorplan composer: the chart is ISOTROPIC (RUNG6.md §2 — a camera
would have squashed a drawn square by 15/14), a gesture ends in exactly ONE host write, the
shared-wall candidates come from ``floorplan.shared_edges`` and a click on one declares the
door, the live gate feedback disables Compose and NAMES the offender, undo is doc-local and
atomic over a door pair, and Compose emits EXACTLY the one-argument ``floorplan`` argv over a
json ``floorplan.compose`` accepts.

The pure math is ``tests/test_floorplan.py``'s (85 fences); the CLI verb is the cli suite's.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication                              # noqa: E402

from ff9mapkit import floorplan as FP                                   # noqa: E402
from ff9mapkit.workspace.floorplandoc import (                          # noqa: E402
    FloorplanDoc, PlanCanvas, attribute_problems, candidate_doors,
)
from ff9mapkit.workspace.shell import pick_palette                      # noqa: E402

KIT = Path(__file__).resolve().parents[1]                               # the ff9mapkit checkout


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _deterministic_qt_teardown(qt_drain):
    """Widgets die HERE, not in a forced GC pass (THE GC-CHILD LAW's teardown half)."""
    yield
    qt_drain()


@pytest.fixture(autouse=True)
def _no_real_deploy_pin(monkeypatch, tmp_path):
    """★ NO TEST READS THE DEVELOPER'S REAL ``.ff9deploy.toml``.

    This repo's most-recurring test defect is a test that reads the developer's machine, and the
    pin is the sharpest case here: it is GITIGNORED, so its very existence differs per checkout and
    it carries a live id band. Left alone, ``_doc(kit=KIT)`` read the real worktree pin and handed
    every 'clean plan' assertion a 30500 that a fresh clone does not have — the suite was green on
    this machine and would have been red on a colleague's.

    Aimed at ``tmp_path/.ff9deploy.toml`` rather than at the reader, so ``_read_deploy_id_base``
    itself keeps its coverage; the two id-base tests write that exact file and are unchanged.
    """
    monkeypatch.setattr(FloorplanDoc, "deploy_pin_path",
                        lambda self: tmp_path / ".ff9deploy.toml")


class _Run:
    """The run_job seam: records the argv + kwargs, reports 'started'.

    ``finish(code)`` fires the recorded ``on_finished`` AFTER the launch returns, which is what
    the real ``run_job`` does (a QProcess signal). Firing it inline during ``__call__`` would let
    a test pass on an ordering production never has."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        return True

    def finish(self, code, i=-1):
        cb = self.calls[i][1].get("on_finished")
        assert cb is not None, "the compose job must carry an on_finished hook"
        cb(code)


def _doc(app, *, run=None, kit=KIT, on_composed=None, id_base="30500", theme="dark"):
    """``id_base`` defaults to a real scratch id because a plan WITHOUT one is genuinely
    incomplete (the id gate lists it and holds Compose off) — pass ``id_base=""`` to drive that
    path deliberately, never by omission."""
    run = run or _Run()
    doc = FloorplanDoc(pick_palette(theme), kit, run=run, on_composed=on_composed)
    if id_base:
        doc.id_box.setText(id_base)
    return doc, run


def _draw(canvas, pts):
    """Draw one room through the canvas's own click seam and CLOSE it on the first corner."""
    for p in pts:
        canvas.click_world(*p)
    canvas.click_world(*pts[0])


def _status(doc):
    """The status line's AUTHORITATIVE text. It is an ``ElideLabel``, so ``text()`` is whatever
    fits the current width — reading that would make every assert here a report on the pane."""
    return doc.status.fullText()


# a plain two-room plan that abuts on x = 0 -- the composer's happy path
_A = [(-1200, -800), (0, -800), (0, 800), (-1200, 800)]
_B = [(0, -800), (1200, -800), (1200, 800), (0, 800)]


def _two_rooms(app, **kw):
    doc, run = _doc(app, **kw)
    _draw(doc.canvas, _A)
    _draw(doc.canvas, _B)
    return doc, run


# --------------------------------------------------------------------- the frame (RUNG6.md §2)

def test_the_chart_is_isotropic_and_plus_z_is_up():
    """THE reason this is a chart and not a camera. A pitch-90 BackdropCanvas camera is exactly
    affine but anisotropic by ``1/K_VSCALE`` = 15/14, so a drawn SQUARE would arrive as a 15:14
    room. One conversion each way, one factor, and +z up-screen (scene y grows down)."""
    sq = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    pts = [PlanCanvas.world_to_scene(x, z) for x, z in sq]
    w = max(p[0] for p in pts) - min(p[0] for p in pts)
    h = max(p[1] for p in pts) - min(p[1] for p in pts)
    assert w == pytest.approx(h), f"the chart squashed a square {w} x {h} -- it is not isotropic"
    assert PlanCanvas.world_to_scene(0, 100)[1] < PlanCanvas.world_to_scene(0, 0)[1], "+z is UP"
    for x, z in ((0, 0), (-2500, 1750), (413, -9)):     # the pair is a real inverse, not a cousin
        sx, sy = PlanCanvas.world_to_scene(x, z)
        assert PlanCanvas.scene_to_world(sx, sy) == pytest.approx((x, z))


def test_the_canvas_matches_the_other_plan_view_chart():
    """The behavior STAGE and this chart are two plan views of the same world; if they disagree
    about how big 500u is, the author is reading two different rooms."""
    from ff9mapkit.workspace import behaviordoc, floorplandoc
    assert floorplandoc._WORLD == behaviordoc._WORLD


# --------------------------------------------------------------------- construction

def test_construction_touches_no_disk_and_gates_compose(app, monkeypatch):
    """The startup-spend law: the doc's only disk touches are the user's own Open / Compose.
    The ``.ff9deploy.toml`` id-base read is FIRST-USE, and construction must not trip it."""
    reads = []
    monkeypatch.setattr(FloorplanDoc, "_read_deploy_id_base",
                        lambda self: reads.append(1) or None)
    doc, run = _doc(app)
    assert not reads, "construction read .ff9deploy.toml -- that is a startup disk touch"
    assert not run.calls
    assert not doc.compose_btn.isEnabled()
    assert "at least one room" in doc.compose_btn.toolTip()
    assert doc._session == {"rooms": [], "doors": [], "entry": None}
    assert doc.canvas.mode() == "rooms"
    assert not doc.undo_btn.isEnabled() and not doc.clear_btn.isEnabled()


def test_the_minted_room_name_is_real_not_a_placeholder(app):
    """THE DEFAULT-VALUE LAW. A minted room name becomes an on-disk member dir AND the field's
    own name, so it must be legal and unique on arrival -- validated through campaign's own
    ``_validate_member_name``, the one owner, not a copy of the rule."""
    doc, _ = _two_rooms(app)
    names = [r["name"] for r in doc._session["rooms"]]
    assert names == ["ROOM1", "ROOM2"]
    for i, n in enumerate(names):
        assert FloorplanDoc.check_room_name(n, names[:i] + names[i + 1:]) is None
    assert "already called" in FloorplanDoc.check_room_name("ROOM1", ["ROOM1"])
    assert FloorplanDoc.check_room_name("a/b", []), "a path separator must be refused out loud"
    assert FloorplanDoc.check_room_name(" pad ", []), "a padded name must be refused out loud"


# --------------------------------------------------------------------- drawing a room

def test_drawing_a_room_appends_it_and_closing_emits_once(app):
    """Corners accumulate on the canvas (which writes NOTHING); closing on the first corner
    emits ``room_drawn`` exactly once and the HOST appends the room."""
    doc, _ = _doc(app)
    c = doc.canvas
    seen = []
    c.room_drawn.connect(lambda poly: seen.append(poly))
    for p in _A:
        c.click_world(*p)
    assert c.pending() == [tuple(p) for p in _A]
    assert doc._session["rooms"] == [], "the canvas must not write -- the host owns the document"
    assert not seen
    c.click_world(*_A[0])                            # click the first corner again -> close
    assert len(seen) == 1, "one closed outline is ONE emit"
    assert c.pending() == []
    assert doc._session["rooms"][0]["poly"] == [tuple(p) for p in _A]
    assert doc._session["entry"] == "ROOM1", "the first room drawn is the way in"
    assert doc.undo_btn.isEnabled() and doc.clear_btn.isEnabled()


def test_a_double_click_closes_the_outline(app):
    doc, _ = _doc(app)
    c = doc.canvas
    for p in _A[:3]:
        c.click_world(*p)
    assert c.double_click_world(*_A[2]) is True
    assert len(doc._session["rooms"]) == 1 and c.pending() == []
    for p in _A[:2]:                                 # under 3 corners there is no room to close
        c.click_world(*p)
    assert c.double_click_world(*_A[1]) is False
    assert len(doc._session["rooms"]) == 1


def test_a_duplicated_corner_is_refused_where_g1_would_refuse_it(app):
    """G1 refuses two corners under 8u apart. Saying so at the click is better than composing
    a room that cannot exist."""
    doc, _ = _doc(app)
    c = doc.canvas
    c.click_world(0, 0)
    c.click_world(0, 0)
    assert c.pending() == [(0, 0)]
    assert "duplicated corner" in _status(doc)


# --------------------------------------------------------------------- dragging

def test_a_vertex_drag_ends_in_one_host_write(app):
    """The StageCanvas contract: the drag never writes. Many move steps, ONE emit on the drop,
    ONE history step, and the host owns the document mutation."""
    doc, _ = _doc(app)
    _draw(doc.canvas, _A)
    c = doc.canvas
    emits = []
    c.room_reshaped.connect(lambda ri, poly: emits.append((ri, poly)))
    before = len(doc._history)
    assert c.press_world(-1200, -800) is True
    for step in range(1, 6):
        c.drag_world(-1200 - 10 * step, -800 - 4 * step)
    assert not emits, "a drag in flight has not written anything yet"
    assert doc._session["rooms"][0]["poly"][0] == (-1200, -800)
    c.end_drag()
    assert len(emits) == 1, "one drag is ONE callback"
    assert doc._session["rooms"][0]["poly"][0] == (-1250, -820)
    assert len(doc._history) == before + 1, "one drag is ONE undo step"
    doc.on_undo()
    assert doc._session["rooms"][0]["poly"][0] == (-1200, -800)


def test_a_drag_that_moves_nothing_writes_nothing(app):
    doc, _ = _doc(app)
    _draw(doc.canvas, _A)
    c = doc.canvas
    emits = []
    c.room_reshaped.connect(lambda ri, poly: emits.append(poly))
    before = len(doc._history)
    assert c.press_world(-1200, -800) is True
    c.drag_world(-1200, -800)
    c.end_drag()
    assert not emits and len(doc._history) == before


def test_dragging_a_rooms_interior_moves_the_whole_room(app):
    """Arranging rooms is the plan's most useful gesture, so the body drags too -- as ONE write,
    by the grabbed spot (never snapping a corner to the cursor)."""
    doc, _ = _doc(app)
    _draw(doc.canvas, _A)
    c = doc.canvas
    emits = []
    c.room_reshaped.connect(lambda ri, poly: emits.append(poly))
    assert c.press_world(-600, 0) is True             # inside the room, not on a corner
    c.drag_world(-600 + 300, 0 + 500)
    c.end_drag()
    assert len(emits) == 1
    assert doc._session["rooms"][0]["poly"] == [(x + 300, z + 500) for x, z in _A]


def test_a_press_that_never_moved_is_a_CLICK_not_a_swallowed_grab(app):
    """★ THE ABUTTING-ROOM GESTURE. A dungeon is rooms that SHARE walls, so a new room's first
    corner is by definition the neighbour's own corner (or its wall, or its body). ``press_world``
    grabs on all three, so before ``release_world`` existed that first click vanished: nothing
    drawn, nothing said, and no way to start an abutting room at all.

    This drives ``press_world`` + ``release_world`` — the pair Qt's handlers call. Every other
    fence here drives ``click_world`` directly, which SKIPS ``press_world``, which is exactly why
    none of them could see it (a probe that cannot reproduce the lifecycle cannot falsify a
    lifecycle bug). Verified against synthesised QMouseEvents natively as well.
    """
    doc, _ = _doc(app)
    _draw(doc.canvas, _A)
    c = doc.canvas
    before = list(doc._session["rooms"][0]["poly"])

    for tag, (x, z) in (("the neighbour's own CORNER", (0, -800)),
                        ("the neighbour's BODY", (-600, 0))):
        c.clear_pending()
        assert c.press_world(x, z) is True, f"{tag}: nothing was grabbable, so nothing to resolve"
        c.release_world(x, z, travel_px=0)
        assert c.pending() == [(int(x), int(z))], f"{tag}: a still press must place a corner"
        assert doc._session["rooms"][0]["poly"] == before, f"{tag}: and must not move the room"
    c.clear_pending()

    # ...and a press that DID travel is still a drag, not a stray corner.
    assert c.press_world(-1200, -800) is True
    c.drag_world(-1150, -760)
    c.release_world(-1150, -760, travel_px=60)
    assert c.pending() == [], "a real drag must not also drop a corner"
    assert doc._session["rooms"][0]["poly"][0] == (-1150, -760)


def test_the_real_qt_release_resolves_the_same_way(app):
    """The seam above is only worth something if Qt's own handler spends it. Synthesised press +
    release at one point, through ``mousePressEvent`` / ``mouseReleaseEvent``, with no travel."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    doc, _ = _doc(app)
    _draw(doc.canvas, _A)
    c = doc.canvas
    c.clear_pending()
    pos = QPointF(c.mapFromScene(QPointF(*PlanCanvas.world_to_scene(0, -800))))
    for typ, held in ((QMouseEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton),
                      (QMouseEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton)):
        ev = QMouseEvent(typ, pos, pos, Qt.MouseButton.LeftButton, held,
                         Qt.KeyboardModifier.NoModifier)
        (c.mousePressEvent if typ == QMouseEvent.Type.MouseButtonPress
         else c.mouseReleaseEvent)(ev)
    assert len(c.pending()) == 1, "a real still click on a neighbour's corner placed nothing"


def test_a_press_on_empty_ground_is_not_a_grab(app):
    """...so it falls through to the pan machinery, which is what makes drawing and panning
    share the left button with no mode."""
    doc, _ = _doc(app)
    _draw(doc.canvas, _A)
    assert doc.canvas.press_world(9000, 9000) is False


# --------------------------------------------------------------------- doors

def test_shared_walls_are_offered_and_a_click_declares_the_door(app):
    """``shared_edges`` OFFERS, the author DECLARES (THE DRAWN-MESH LAW). The offered segment is
    the abutting wall; clicking it writes one door at the depth the spin box shows."""
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    assert len(doc.canvas._cands) == 1, "two abutting rooms share exactly one wall here"
    cand = doc.canvas._cands[0]
    assert {cand["a"], cand["b"]} == {"ROOM1", "ROOM2"}
    assert cand["length"] == pytest.approx(1600.0)
    assert doc.canvas._pick_candidate(0, 0) == 0
    doc.canvas.click_world(0, 0)
    assert len(doc._session["doors"]) == 1
    d = doc._session["doors"][0]
    assert d["a"] == "ROOM1" and d["b"] == "ROOM2" and d["two_way"] is True
    assert d["depth"] == FP.DEPTH_DEFAULT
    assert sorted(d["seg"]) == [(0, -800), (0, 800)]
    assert doc._sel_door == 0


def test_a_declared_wall_is_no_longer_offered(app):
    """Otherwise the same wall could be declared twice, and two gateway strips on one wall are a
    G4 tread-region overlap -- one of them would silently never fire."""
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    assert candidate_doors(doc._session["rooms"], doc._session["doors"]) == []


def test_clicking_a_door_selects_it_and_the_depth_box_edits_that_door(app):
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    doc._on_door_selected(-1)
    assert doc._sel_door is None
    assert doc.canvas._pick_door(0, 200) == 0
    doc.canvas.click_world(0, 200)                    # on the declared door, not a candidate
    assert doc._sel_door == 0
    assert doc.depth.value() == int(FP.DEPTH_DEFAULT)
    steps = len(doc._history)
    doc.depth.setValue(300)
    doc.depth.setValue(320)                           # ...a BURST is one logical edit
    assert doc._session["doors"][0]["depth"] == 320.0
    assert len(doc._history) == steps + 1, "a spin-box burst is one undo step, not one per tick"
    doc.on_undo()
    assert doc._session["doors"][0]["depth"] == FP.DEPTH_DEFAULT


def test_deleting_a_door_and_a_room_walks_back_atomically(app):
    """THE reason undo is doc-local. A door is a gateway on one side and an arrival row on the
    other; ``shell._UndoRec`` is single-member, so a half-undone pair would be a gateway with no
    arrival -- which falls through to ``[player] spawn`` SILENTLY. The snapshot stack makes the
    pair atomic, including when a deleted ROOM takes its doors with it."""
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    assert len(doc._session["doors"]) == 1
    doc._on_door_deleted(0)
    assert doc._session["doors"] == []
    doc.on_undo()
    assert len(doc._session["doors"]) == 1
    doc._on_room_deleted(1)                           # delete ROOM2 -> its door cannot survive
    assert [r["name"] for r in doc._session["rooms"]] == ["ROOM1"]
    assert doc._session["doors"] == []
    doc.on_undo()                                     # ...and BOTH come back in one step
    assert [r["name"] for r in doc._session["rooms"]] == ["ROOM1", "ROOM2"]
    assert len(doc._session["doors"]) == 1


def test_the_door_menu_and_room_menu_are_seams_not_popups(app, monkeypatch):
    """A menu the fences would have to click is not a seam. Both live behind one method each."""
    doc, _ = _two_rooms(app)
    assert callable(doc.canvas._room_menu) and callable(doc.canvas._door_menu)
    fired = []
    doc.canvas.room_rename.connect(lambda i: fired.append(("rename", i)))
    doc.canvas.room_deleted.connect(lambda i: fired.append(("delete", i)))
    monkeypatch.setattr(doc, "_ask_room_name", lambda cur: "GREATHALL")
    doc._on_room_rename(0)
    assert doc._session["rooms"][0]["name"] == "GREATHALL"


def test_renaming_a_room_retargets_its_doors_and_refuses_an_illegal_name(app, monkeypatch):
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    monkeypatch.setattr(doc, "_ask_room_name", lambda cur: "GREAT HALL")
    doc._on_room_rename(0)
    assert doc._session["rooms"][0]["name"] == "GREAT HALL"       # a space is legal
    assert doc._session["doors"][0]["a"] == "GREAT HALL", "a door names its rooms -- retarget it"
    assert doc._session["entry"] == "GREAT HALL"
    monkeypatch.setattr(doc, "_ask_room_name", lambda cur: "ROOM2")
    doc._on_room_rename(0)
    assert doc._session["rooms"][0]["name"] == "GREAT HALL"       # refused, not applied
    assert "already called" in _status(doc)
    monkeypatch.setattr(doc, "_ask_room_name", lambda cur: "wing/east")
    doc._on_room_rename(0)
    assert doc._session["rooms"][0]["name"] == "GREAT HALL"
    assert "path separators" in _status(doc)


# --------------------------------------------------------------------- the live gate

def test_a_clean_plan_reports_its_composed_summary(app):
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    doc.id_box.setText("30500")
    doc.judge_now(sync=True)
    assert doc.compose_btn.isEnabled()
    assert doc.plist.count() == 0
    txt = _status(doc)
    assert "2 field(s)" in txt and "30500-30501" in txt
    assert "2 rooms" in txt and "1 door" in txt
    # the per-room fitted camera is TOOLTIP detail: on the line it took two more wrapped rows off
    # the chart at every scale (snap-measured), and the chart is the primary surface
    tip = doc.status.toolTip()
    assert "entry ROOM1" in tip
    assert "ROOM1 id 30500, distance 2241u, pitch 48, off_r (600, -122)" in tip
    assert "ROOM2 id 30501" in tip


def test_a_broken_room_disables_compose_lists_it_and_paints_it(app):
    """The tab's real value: ``compose`` raises with EVERY problem, so the offender is named,
    painted in the error colour, and Compose is off with a tooltip saying why."""
    doc, run = _doc(app)
    _draw(doc.canvas, [(0, 0), (1000, 1000), (1000, 0), (0, 1000)])     # a bowtie: G1
    _draw(doc.canvas, [(4000, 0), (5200, 0), (5200, 1200), (4000, 1200)])
    doc.judge_now(sync=True)
    errors = doc._verdict[1]
    assert errors and any("ROOM1" in e and "intersects itself" in e for e in errors)
    assert not doc.compose_btn.isEnabled()
    assert "problem(s)" in doc.compose_btn.toolTip()
    assert doc.canvas._bad_rooms == {"ROOM1"}, "the offender paints, its innocent neighbour does not"
    assert doc.plist.count() == len(errors)
    assert "ROOM1" in doc.plist.item(0).text()
    doc._ask_out = lambda: str(KIT)
    doc.on_compose()
    assert not run.calls, "Compose must never run on a plan with a standing error"


def test_a_too_shallow_door_is_refused_out_loud_never_clamped(app):
    """THE DEFAULT-VALUE LAW's second half. The core refuses a strip under ``2*R_WALK`` (its
    standable window would be a sliver), so the spin box must NOT clamp -- a silently corrected
    value is exactly the plausible-but-wrong default the law forbids."""
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    assert doc.depth.minimum() < FP.DEPTH_MIN, "clamping would hide the refusal"
    assert doc.depth.value() == int(FP.DEPTH_DEFAULT), "the default IS the core's own constant"
    doc.canvas.click_world(0, 0)
    doc.depth.setValue(100)
    doc.judge_now(sync=True)
    errors = doc._verdict[1]
    assert any("ROOM1-ROOM2" in e and "100u" in e for e in errors), errors
    assert doc._session["doors"][0]["depth"] == 100.0, "the value the author typed, unclamped"
    assert doc.canvas._bad_doors == {0}
    assert not doc.compose_btn.isEnabled()


def test_a_warning_is_listed_without_blocking_compose(app):
    """A warn is not an error: it is said, quietly, and the button stays live."""
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    doc.depth.setValue(int(FP.DEPTH_WARN) - 5)        # over DEPTH_MIN, under the proven floor
    doc.judge_now(sync=True)
    composed, errors, warnings = doc._verdict
    assert composed is not None and not errors
    assert any("in-game-proven floor" in w for w in warnings)
    assert doc.compose_btn.isEnabled()
    assert doc.plist.count() == len(warnings)
    assert "warning" in _status(doc)


def test_an_unattributable_problem_is_still_listed(app):
    """Never swallow one. A message that names no room paints nothing and is SAID anyway."""
    rooms = [{"name": "ROOM1", "poly": _A}]
    bad, badd, loose = attribute_problems(["the floorplan has no rooms"], ["ROOM1"], [])
    assert not bad and not badd and loose == ["the floorplan has no rooms"]
    assert rooms                                       # (the fixture exists to name the shape)


def test_attribution_matches_whole_names_not_substrings():
    """``ROOM1`` must not light up for every problem about ``ROOM10`` -- the messages are
    ``room <NAME>: ...`` / ``door <A>-<B>: ...`` and the match honours that."""
    names = ["ROOM1", "ROOM10"]
    doors = [{"a": "ROOM1", "b": "ROOM10"}]
    bad, badd, loose = attribute_problems(["room ROOM10: nowhere to stand"], names, doors)
    assert bad == {"ROOM10"} and not badd and not loose
    bad, badd, _ = attribute_problems(["door ROOM10-ROOM1: depth 9u leaves a sliver"], names, doors)
    assert badd == {0}
    assert bad == {"ROOM1", "ROOM10"}                  # the message names both, so both paint


def test_the_judge_drops_a_stale_verdict(app):
    """A verdict computed for a plan the author has since changed must never paint: it would
    claim a fixed problem is still there, or that a new one is not."""
    doc, _ = _two_rooms(app)
    doc.judge_now(sync=True)
    stale_gen = doc._gen
    doc._on_room_deleted(1)                            # the plan moved on
    doc._finish_judge((stale_gen, None, ["room ROOM2: a stale complaint"], []))
    assert doc.canvas._bad_rooms == set()
    assert all("stale complaint" not in doc.plist.item(i).text()
               for i in range(doc.plist.count()))


def test_the_judge_runs_off_the_gui_thread_by_default(app):
    """It is ~0.5s per room, so the default lane must not be the GUI thread -- and it must be
    safe there, which it is because ``compose`` is pure (no Qt, no disk, no install)."""
    import inspect
    src = inspect.getsource(FloorplanDoc.judge_now)
    assert "threading.Thread" in src and "sync=False" in inspect.signature(
        FloorplanDoc.judge_now).__str__().replace(" ", "")
    plan = {"name": "D", "rooms": [{"name": "ROOM1", "poly": _A}], "doors": [], "id_base": 30500}
    composed, errors, warnings = FloorplanDoc._judge_work(plan)
    assert composed is not None and not errors and isinstance(warnings, list)


def test_the_judge_never_lets_an_odd_plan_kill_the_tab(app):
    composed, errors, _w = FloorplanDoc._judge_work({"rooms": [{"name": "R", "poly": "nonsense"}]})
    assert composed is None and errors and len(errors) == 1


# --------------------------------------------------------------------- the id base

def test_the_id_base_comes_from_the_worktree_pin_on_first_use(app, tmp_path):
    """THE DEFAULT-VALUE LAW: never invent a plausible id (a collision in the GLOBAL EventDB is
    the classic null-.eb black screen). The real value is this worktree's own
    ``.ff9deploy.toml`` ``campaign_id_base``, read on FIRST USE, not at construction."""
    fake_kit = tmp_path / "ff9mapkit"
    fake_kit.mkdir()
    (tmp_path / ".ff9deploy.toml").write_text('mod_folder = "FF9CustomMap"\n'
                                              'campaign_id_base = 30500\n', encoding="utf-8")
    doc, _ = _doc(app, kit=fake_kit, id_base="")
    assert doc.id_box.text() == "", "an empty box, not a guessed number"
    assert doc._id_base_read is False
    assert doc.id_base() == 30500
    assert doc._id_base_read is True
    doc.id_box.setText("30700")                        # a typed value wins
    assert doc.id_base() == 30700


def test_no_id_base_anywhere_refuses_loudly(app, tmp_path):
    """Real, or LOUDLY INVALID. With no pin and an empty box there is no real id to mint, so
    Compose refuses and says where to get one -- it does not fall back to 4000."""
    fake_kit = tmp_path / "ff9mapkit"
    fake_kit.mkdir()
    doc, run = _doc(app, kit=fake_kit, id_base="")
    _draw(doc.canvas, _A)
    doc.judge_now(sync=True)
    assert doc.id_base() is None
    doc._ask_out = lambda: str(tmp_path)
    doc.on_compose()
    assert not run.calls
    assert "No first field id" in _status(doc) and "campaign_id_base" in _status(doc)


def test_the_id_box_spends_the_shared_band_validator(app, tmp_path):
    """The round-13 ``id_field`` lesson: one band voice, ``pack.check_custom_id`` -- never a
    private copy of 4000-32767. It rides the LIVE gate (a listed problem, Compose off) rather
    than raising out of ``plan()``: a half-typed id must not take the judge down."""
    doc, run = _doc(app, id_base="")
    _draw(doc.canvas, _A)
    doc.id_box.setText("100")                          # a REAL field id: locked
    doc.judge_now(sync=True)                           # ...and this must NOT raise
    assert not doc.compose_btn.isEnabled()
    assert any("custom band" in doc.plist.item(i).text() for i in range(doc.plist.count()))
    assert "id_base" not in doc.plan(), "a refused id never reaches the emitted plan"
    doc._ask_out = lambda: str(tmp_path)
    doc.on_compose()
    assert not run.calls
    assert "custom band" in _status(doc)
    doc.id_box.setText("30500")
    doc.judge_now(sync=True)
    assert doc.compose_btn.isEnabled() and doc.plan()["id_base"] == 30500


# --------------------------------------------------------------------- Compose

def test_compose_writes_a_json_compose_accepts_and_emits_the_exact_argv(app, tmp_path):
    """The verb reads name / ids / mod folder / rooms / doors FROM the json, so the GUI hands it
    ONE path and nothing else -- any flag here would be a second source of truth."""
    doc, run = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    doc.name_box.setText("SUNKEN")
    doc.mod_box.setText("FF9CustomMap")
    doc.id_box.setText("30500")
    doc._ask_out = lambda: str(tmp_path)
    doc.on_compose()
    assert len(run.calls) == 1
    argv, kw = run.calls[0]
    out = tmp_path / "sunken"
    plan_path = out / FP.SIDECAR
    assert argv == [sys.executable, "-m", "ff9mapkit", "floorplan", str(plan_path)]
    assert kw["cwd"] == str(KIT)
    assert plan_path.is_file()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["version"] == 1 and plan["name"] == "SUNKEN" and plan["id_base"] == 30500
    assert plan["mod_folder"] == "FF9CustomMap" and plan["entry"] == "ROOM1"
    assert [r["name"] for r in plan["rooms"]] == ["ROOM1", "ROOM2"]
    assert plan["doors"][0]["depth"] == FP.DEPTH_DEFAULT
    composed = FP.compose(plan)                        # the core accepts it verbatim
    assert [r.field_id for r in composed.rooms] == [30500, 30501]
    assert composed.entry == "ROOM1" and len(composed.edges) == 2


def test_compose_is_in_place_after_the_first_run(app, tmp_path):
    doc, run = _two_rooms(app)
    doc.id_box.setText("30500")
    doc._ask_out = lambda: str(tmp_path)
    doc.judge_now(sync=True)
    doc.on_compose()
    assert doc._project and doc._project["out"] == str(tmp_path / "dungeon")
    assert doc.compose_btn.text().startswith("Recompose")
    doc._ask_out = lambda: (_ for _ in ()).throw(AssertionError("asked again"))
    doc.canvas.press_world(-1200, -800)
    doc.canvas.drag_world(-1210, -810)
    doc.canvas.end_drag()
    assert "not composed yet" in _status(doc)
    doc.judge_now(sync=True)
    doc.on_compose()
    assert len(run.calls) == 2
    a1, a2 = run.calls[0][0], run.calls[1][0]
    assert a1[-1] == a2[-1], "the same plan file -- in place"


def test_a_cancelled_out_dialog_runs_nothing(app, tmp_path):
    doc, run = _two_rooms(app)
    doc.id_box.setText("30500")
    doc.judge_now(sync=True)
    doc._ask_out = lambda: None
    doc.on_compose()
    assert not run.calls and doc._project is None


def test_a_clean_run_hands_the_campaign_to_the_shell(app, tmp_path):
    """PLAN.md §5 call site 3: the composed dungeon lands as a live campaign through the
    shell's own ``open_campaign``, so its graph is visible at once."""
    opened = []
    run = _Run()
    doc, _ = _two_rooms(app, run=run, on_composed=lambda p: opened.append(p))
    doc.id_box.setText("30500")
    doc.judge_now(sync=True)
    doc._ask_out = lambda: str(tmp_path)
    camp = tmp_path / "dungeon" / "campaign.toml"
    camp.parent.mkdir(parents=True, exist_ok=True)
    camp.write_text('[campaign]\nname = "DUNGEON"\n', encoding="utf-8")
    doc.on_compose()
    assert opened == []                                # not yet -- the job is still running
    run.finish(0)
    assert opened == [camp]


def test_a_failed_run_hands_nothing_to_the_shell(app, tmp_path):
    opened = []
    run = _Run()
    doc, _ = _two_rooms(app, run=run, on_composed=lambda p: opened.append(p))
    doc.id_box.setText("30500")
    doc.judge_now(sync=True)
    doc._ask_out = lambda: str(tmp_path)
    doc.on_compose()
    run.finish(2)
    assert opened == []
    assert "Compose failed" in _status(doc)


def test_a_clean_run_with_no_campaign_on_disk_hands_nothing(app, tmp_path):
    """A zero exit code the emitter cannot back up with a file is not a success to forward -- the
    shell would open nothing and report a failure the user never caused."""
    opened = []
    run = _Run()
    doc, _ = _two_rooms(app, run=run, on_composed=lambda p: opened.append(p))
    doc.id_box.setText("30500")
    doc.judge_now(sync=True)
    doc._ask_out = lambda: str(tmp_path)
    doc.on_compose()
    run.finish(0)                                      # exit 0, but nothing was written
    assert opened == []


def test_the_gate_findings_reach_the_shared_problems_panel(app, tmp_path):
    """``problems`` is a real seam, not decoration: a refusal belongs in the app's one Problems
    panel too, not only in this tab's list."""
    posted = []
    run = _Run()
    doc = FloorplanDoc(pick_palette("dark"), KIT, run=run,
                       problems=lambda verdict, probs: posted.append((verdict, probs)))
    doc.id_box.setText("30500")
    _draw(doc.canvas, [(0, 0), (1000, 1000), (1000, 0), (0, 1000)])
    doc.judge_now(sync=True)
    doc._ask_out = lambda: str(tmp_path)
    doc.on_compose()
    assert posted and posted[0][1], "the refusal must reach the shell's Problems panel"


# --------------------------------------------------------------------- the sidecar round trip

def test_the_sidecar_round_trips_the_session(app, tmp_path):
    """Compose writes ``<out>/floorplan.json``; Open reads it back into an EDITABLE session --
    rooms, doors, depths, entry, name, mod folder, id base -- and arms in-place recompose."""
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    doc.depth.setValue(300)
    doc._on_room_entry(1)                              # ROOM2 is the way in
    doc.name_box.setText("SUNKEN")
    doc.mod_box.setText("FF9CustomMap-world")
    doc.id_box.setText("30520")
    doc._ask_out = lambda: str(tmp_path)
    doc.judge_now(sync=True)
    doc.on_compose()
    side = tmp_path / "sunken" / FP.SIDECAR
    assert side.is_file()

    doc2, run2 = _doc(app)
    doc2.load_plan(side)
    assert [r["name"] for r in doc2._session["rooms"]] == ["ROOM1", "ROOM2"]
    assert doc2._session["rooms"][0]["poly"] == [tuple(p) for p in _A]
    assert doc2._session["doors"][0]["depth"] == 300.0
    assert doc2._session["entry"] == "ROOM2"
    assert doc2.name_box.text() == "SUNKEN"
    assert doc2.mod_box.text() == "FF9CustomMap-world"
    assert doc2.id_box.text() == "30520"
    assert doc2.compose_btn.text().startswith("Recompose")
    doc2._ask_out = lambda: (_ for _ in ()).throw(AssertionError("asked on a reopen"))
    doc2.judge_now(sync=True)
    doc2.on_compose()
    assert run2.calls[0][0][-1] == str(side), "a reopen recomposes IN PLACE"


def test_a_door_naming_a_missing_room_is_dropped_on_open(app, tmp_path):
    """A gateway with no destination room is a Field(0) black screen. It never survives a load."""
    p = tmp_path / FP.SIDECAR
    p.write_text(json.dumps({
        "version": 1, "name": "X", "rooms": [{"name": "ROOM1", "poly": _A}],
        "doors": [{"a": "ROOM1", "b": "GHOST", "seg": [[0, -800], [0, 800]]}]}), encoding="utf-8")
    doc, _ = _doc(app)
    doc.load_plan(p)
    assert doc._session["doors"] == []
    assert [r["name"] for r in doc._session["rooms"]] == ["ROOM1"]


def test_a_bad_file_does_not_kill_the_tab(app, tmp_path, monkeypatch):
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    doc, _ = _doc(app)
    monkeypatch.setattr(doc, "_ask_open", lambda: str(p))
    doc.on_open()
    assert "Could not open" in _status(doc)
    assert doc._session["rooms"] == []


# --------------------------------------------------------------------- undo / clear / plumbing

def test_undo_restores_the_previous_session(app):
    doc, _ = _two_rooms(app)
    assert len(doc._session["rooms"]) == 2
    doc.on_undo()
    assert [r["name"] for r in doc._session["rooms"]] == ["ROOM1"]
    doc.on_undo()
    assert doc._session["rooms"] == []
    doc.on_undo()                                      # empty stack: a no-op, never a crash
    assert doc._session["rooms"] == []


def test_clear_is_one_undoable_gesture(app):
    doc, _ = _two_rooms(app)
    doc.on_clear()
    assert doc._session == {"rooms": [], "doors": [], "entry": None}
    doc.on_undo()
    assert len(doc._session["rooms"]) == 2


def test_the_mode_strip_owns_the_click_semantics(app):
    doc, _ = _two_rooms(app)
    assert doc.tools.current() == "rooms" and doc.canvas.mode() == "rooms"
    assert not doc.depth.isVisible() or not doc.isVisible()
    doc.tools.set_current("doors")
    assert doc.canvas.mode() == "doors"
    doc.judge_now(sync=True)
    assert doc.canvas._cands, "candidates are only computed for the Doors tool"
    doc.tools.set_current("rooms")
    doc.judge_now(sync=True)
    assert doc.canvas._cands == []


def test_switching_mode_abandons_a_half_drawn_outline(app):
    doc, _ = _doc(app)
    doc.canvas.click_world(0, 0)
    doc.canvas.click_world(500, 0)
    doc.tools.set_current("doors")
    assert doc.canvas.pending() == []


def test_retheme_and_scale_reach_the_canvas(app):
    doc, _ = _doc(app)
    doc.retheme(pick_palette("light"))
    assert doc.canvas.pal is doc.pal
    assert doc.plist.placeholder_color == doc.pal["muted"]
    doc.set_scale(150)
    assert doc.canvas._scale == 150


def test_the_shell_registers_the_tab_on_the_author_rail(app):
    """All THREE registration sites, plus the two theme/CALIBRE hooks -- a mechanism the call
    site never spends is this package's most-repeated defect."""
    from ff9mapkit.editor.theme import pick_palette as pp
    from ff9mapkit.workspace.shell import Workspace
    win = Workspace(pp("dark"))
    try:
        assert isinstance(win.floorplan_doc, FloorplanDoc)
        assert win.tabs.indexOf(win.floorplan_doc) >= 0
        assert win.tabs.tabText(win.tabs.indexOf(win.floorplan_doc)) == "Floorplan"
        author = next(members for name, members in win._rail_groups if name == "Author")
        assert win.floorplan_doc in author, "Floorplan authors the topology; the Map renders it"
        win.tabs.setCurrentWidget(win.floorplan_doc)     # the identity branch must not raise
        app.processEvents()
        assert win.tabs.currentWidget() is win.floorplan_doc
        assert win._chip_mode is None, "the doc owns its own undo -- it takes no edit chip"
        assert win.floorplan_doc.on_composed == win.open_campaign
        win.retheme(pp("light"))
        assert win.floorplan_doc.canvas.pal is win.pal
        win._apply_text_scale(150)
        assert win.floorplan_doc.canvas._scale == 150
    finally:
        win.hide()


# --------------------------------------------------------------------- colour (the NINTH GROUND)

def _srgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(c):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def _contrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _over(fg, bg, alpha):
    a = alpha / 255.0
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3))


def test_every_chart_ink_clears_its_ground():
    """★ THE NINTH-GROUND LAW. A room's wash is a THIRD colour under chart text, so no existing
    fg/bg fence covers it — and the first cut of this canvas drew each room's NAME in the very
    token its own fill was made of: accent on accent@38, warn on warn@44, error on error@60. That
    measures **2.16:1 on nord** and 2.7-2.9 on solarized-dark / solarized-light / gruvbox — sub-AA
    text in most of the eight palettes, under even the 3.0 non-text floor in six of them.

    So the rule this pins is not 'the numbers happen to pass', it is **THE COLOUR LIVES IN THE
    STROKES; CHART TEXT IS ONLY ``text`` OR ``muted``** — and it is pinned over every palette, on
    the plain canvas AND on all three washes, because a floor calibrated on one ground does not
    transfer. Colour is font-independent, so this holds offscreen.
    """
    from ff9mapkit.editor import theme as T
    from ff9mapkit.workspace.floorplandoc import _FILL_ALPHA
    worst = (99.0, "")
    for name in T.THEMES:
        pal = T.pick_palette(name)
        surface = _srgb(pal["surface"])
        grounds = {"surface": surface}
        for tok in ("accent", "warn", "error"):
            grounds[f"{tok}@{_FILL_ALPHA}"] = _over(_srgb(pal[tok]), surface, _FILL_ALPHA)
        for ink in ("text", "muted"):               # the ONLY two inks the chart writes text in
            for gname, ground in grounds.items():
                r = _contrast(_srgb(pal[ink]), ground)
                if r < worst[0]:
                    worst = (r, f"{name}: {ink} on {gname}")
                assert r >= 4.5, (f"{name}: chart text {ink} on {gname} is {r:.2f}:1 -- the floor "
                                  f"for text is 4.5")
    assert worst[0] >= 4.5, worst


def test_a_room_label_is_suppressed_by_MEASUREMENT_not_a_magic_threshold(app):
    """The tiers used to gate on 60 / 96 / 100 screen px. The moment the state glyph was prepended
    (`✕ ROOM1` is ~14px wider than `ROOM1`) a 68px-wide room at CALIBRE 125 overprinted its
    neighbour again — snap-caught. A threshold that has to be re-tuned whenever the string changes
    is a coincidence, not a fence, so the tier asks the LIVE font whether ITS OWN string fits."""
    doc, _ = _two_rooms(app)
    c = doc.canvas
    from PySide6.QtGui import QFontMetricsF
    adv = QFontMetricsF(c._font(9, True)).horizontalAdvance("✕ ROOM1")
    # (the exact px are offscreen fiction -- the RELATIONS are not, and they are the law)
    assert c._fits("✕ ROOM1", adv + 40) is True
    assert c._fits("✕ ROOM1", adv - 20) is False, "a label wider than its room must be suppressed"
    # the GLYPH counts against the budget: prefixing one must be able to tip a room over
    span = next(w for w in range(int(adv) - 30, int(adv) + 40)
                if c._fits("ROOM1", w) and not c._fits("✕ ROOM1", w))
    assert span, "the state glyph is not measured, so it can overflow its room unnoticed"
    # a longer name is refused at a width the short one clears -- the whole point
    assert c._fits("✕ THEGREATSUNKENHALL", adv + 40) is False
    # ...and it hears the dial: the same room fits less text at 150
    c.set_scale(150)
    assert c._fits("✕ ROOM1", adv + 8) is False


def test_the_chart_says_a_rooms_state_without_using_colour(app):
    """...and because the ink is now neutral, the state has to be said some other way. Three ways:
    the stroke colour, the stroke WIDTH, and a glyph on the name — the last of which is the only
    one a colour-blind author gets for free."""
    doc, _ = _two_rooms(app)
    c = doc.canvas
    assert c._room_ink("ROOM1") == (doc.pal["accent"], "")
    c._bad_rooms = {"ROOM1"}
    assert c._room_ink("ROOM1") == (doc.pal["error"], "✕ ")
    c._bad_rooms, c._warn_rooms = set(), {"ROOM1"}
    assert c._room_ink("ROOM1") == (doc.pal["warn"], "! ")


# --------------------------------------------------------------------- sizing (CALIBRE)

def test_every_box_is_wide_enough_for_its_own_widest_string(app):
    """A px width cannot hear the dial — and neither can ``averageCharWidth() * n``, which is what
    the first cut used: 10px average at CALIBRE 150 against ``FF9CustomMap``'s real 145px advance
    bought 160px for a string needing 185, and the snap showed the trailing ``p`` cut in half. The
    advance of the REAL string cannot be wrong about the real string, and the chrome comes from the
    widget's own sizeHint rather than a guess."""
    for scale in (100, 125, 150):
        doc, _ = _doc(app)
        doc.set_scale(scale)
        for attr, widest, _slack in FloorplanDoc._BOX_WIDEST:
            box = getattr(doc, attr)
            fm = box.fontMetrics()
            chrome = max(0, box.sizeHint().width() - fm.horizontalAdvance("x" * 17))
            assert box.minimumWidth() >= fm.horizontalAdvance(widest) + chrome, (
                f"scale {scale}: {attr} floors at {box.minimumWidth()} but {widest!r} needs "
                f"{fm.horizontalAdvance(widest)} + {chrome} of frame")
            assert box.maximumWidth() >= box.minimumWidth()


def test_a_long_finding_is_never_clipped_out_of_reach(app):
    """★ A CLIPPED GATE MESSAGE IS HALF A MESSAGE. Measured natively at CALIBRE 150 on the real
    refusal, ``sizeHintForRow`` reported **46px** for a row that wraps to **84** at that width, so
    the well's scroll range stayed **0..0** and the last third of the sentence was unreachable —
    no scrollbar, no ellipsis, nothing. The row's height is therefore computed from the live font
    over the live width and STAMPED on the item, which is what gives the view a truthful range."""
    from PySide6.QtCore import QRect, Qt
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    doc.depth.setValue(100)                        # under DEPTH_MIN: the long refusal
    doc.judge_now(sync=True)
    pl = doc.plist
    assert pl.count() >= 1
    fm = pl.fontMetrics()
    bar = pl.verticalScrollBar().sizeHint().width()
    text_w = max(60, pl.viewport().width() - bar - FloorplanDoc._PLIST_PAD_W)
    for i in range(pl.count()):
        text = pl.item(i).text()
        need = fm.boundingRect(QRect(0, 0, text_w, 1 << 20),
                               int(Qt.TextFlag.TextWordWrap), text).height()
        assert pl.item(i).sizeHint().height() >= need + FloorplanDoc._PLIST_PAD_H, (
            f"row {i} is stamped {pl.item(i).sizeHint().height()}px for text that wraps to {need} "
            f"inside {FloorplanDoc._PLIST_PAD_H}px of the sheet's own row padding")
    assert pl.verticalScrollMode() == pl.ScrollMode.ScrollPerPixel, (
        "a row taller than the cap must be scrollable to its end, not cut")
    assert pl.maximumHeight() >= min(
        pl.item(0).sizeHint().height(),
        FloorplanDoc._PLIST_LINE_CAP * fm.height() + FloorplanDoc._PLIST_PAD_H), \
        "the well must show its first finding to the cap, not less"


# --------------------------------------------------------------------- the id gate

def test_an_unresolved_id_base_holds_compose_off_BEFORE_the_click(app, tmp_path):
    """★ THE DEFAULT-VALUE LAW, and a button that was live then dead. ``.ff9deploy.toml`` is
    gitignored, so 'no pin' is every fresh checkout's first run — and there, ``plan()`` omitted
    ``id_base``, ``floorplan.compose`` fell back to its OWN default of 30000, and the tab reported
    '✓ composes: 1 field(s), ids 30000-30000' with Compose ENABLED. The click then refused and did
    nothing. A live verb that promises ids the tab will not mint is wrong twice."""
    fake_kit = tmp_path / "ff9mapkit"
    fake_kit.mkdir()
    doc, run = _doc(app, kit=fake_kit, id_base="")
    _draw(doc.canvas, _A)
    doc.judge_now(sync=True)
    assert doc.id_base() is None
    assert not doc.compose_btn.isEnabled(), "Compose was live with no real id to mint"
    listed = [doc.plist.item(i).text() for i in range(doc.plist.count())]
    assert any("No first field id" in t for t in listed), listed
    assert "30000" not in _status(doc), f"a made-up id reached the verdict: {_status(doc)}"
    doc._ask_out = lambda: str(tmp_path)
    doc.on_compose()
    assert not run.calls
    # ...and typing a real one clears it, same gate, no relaunch
    doc.id_box.setText("30500")
    doc.judge_now(sync=True)
    assert doc.compose_btn.isEnabled() and doc.plan()["id_base"] == 30500


def test_the_dungeon_name_is_gated_because_it_becomes_a_FOLDER(app, tmp_path):
    """``on_compose`` writes the sidecar to ``<chosen parent>/<name>.lower()``, so the name is a
    directory name and nothing was checking it: a typed ``../old`` put the plan OUTSIDE the folder
    the author picked, silently. Same validator as the room names — ``campaign``'s own."""
    doc, run = _two_rooms(app)
    doc.name_box.setText("../old")
    doc.judge_now(sync=True)
    assert not doc.compose_btn.isEnabled()
    assert any("cannot be a folder" in doc.plist.item(i).text()
               for i in range(doc.plist.count())), \
        [doc.plist.item(i).text() for i in range(doc.plist.count())]
    doc._ask_out = lambda: str(tmp_path)
    doc.on_compose()
    assert not run.calls, "a name that escapes the chosen folder must never reach save_plan"
    doc.name_box.setText("SUNKEN HALL")             # a space is fine; a separator is not
    doc.judge_now(sync=True)
    assert doc.compose_btn.isEnabled()


def test_the_canvas_feed_is_pure_of_the_hosts_dict(app):
    """The canvas holds its own copies: a fed row it mutated would be a back-channel write."""
    doc, _ = _two_rooms(app)
    doc.judge_now(sync=True)
    fed = doc.canvas._rooms[0]
    fed["poly"][0] = (9999, 9999)
    assert doc._session["rooms"][0]["poly"][0] == tuple(_A[0])


def test_candidate_doors_is_pure_and_survives_a_sick_outline():
    """A bowtie offers nothing and must not raise -- G1 is what reports it, not a traceback."""
    rooms = [{"name": "A", "poly": [(0, 0), (1000, 1000), (1000, 0), (0, 1000)]},
             {"name": "B", "poly": _B}]
    assert candidate_doors(rooms, []) is not None
    rooms = [{"name": "A", "poly": _A}, {"name": "B", "poly": _B}]
    got = candidate_doors(rooms, [])
    assert len(got) == 1 and got[0]["length"] == pytest.approx(1600.0)
    assert candidate_doors([{"name": "A", "poly": [(0, 0), (1, 1)]}], []) == []
