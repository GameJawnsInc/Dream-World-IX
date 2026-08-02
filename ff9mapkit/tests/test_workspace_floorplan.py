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

from PySide6.QtCore import QPointF, QRectF, Qt                          # noqa: E402
from PySide6.QtGui import QMouseEvent                                   # noqa: E402
from PySide6.QtWidgets import QApplication                              # noqa: E402

from ff9mapkit import floorplan as FP                                   # noqa: E402
from ff9mapkit.workspace.floorplandoc import (                          # noqa: E402
    FloorplanDoc, PlanCanvas, attribute_problems, candidate_doors, clear_of_chips, label_offsets,
)
from ff9mapkit.workspace.shell import pick_palette                      # noqa: E402

KIT = Path(__file__).resolve().parents[1]                               # the ff9mapkit checkout


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _deterministic_qt_teardown(qt_drain):
    """Widgets die HERE, not in a forced GC pass (THE GC-CHILD LAW's teardown half).

    ★ ...AND THE JUDGE DEBOUNCE IS DISARMED FIRST. ``qt_drain`` PARKS widgets alive on purpose and
    runs ``processEvents()`` after every test — so a doc whose last gesture armed the 140ms timer
    fires it inside somebody else's teardown and starts a judge WORKER THREAD, long after its own
    test ended. That is invisible until a thread is mid-import when the main thread touches the same
    module: it surfaced as ``pytest.approx`` raising ``partially initialized module 'numpy'`` in a
    test that touches neither Qt nor threads — a "circular import" that is really a data race. The
    judge has a deterministic sync lane and this module uses only that, so nothing here needs the
    timer; a probe that leaves a thread running is not a probe, it is the next test's flake.
    """
    yield
    for w in QApplication.topLevelWidgets():
        try:
            t = getattr(w, "_debounce", None)
            if t is not None:
                t.stop()
        except RuntimeError:                           # a wrapper whose C++ side already went
            pass
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


def test_the_round_trip_carries_the_art_fingerprint_a_recompose_needs(app, tmp_path):
    """★ THE MERGE'S ART RECORD RIDES THIS ROUND TRIP, so it is fenced here rather than assumed.
    `emit` records the sha256 of the placeholder pair it painted under each room's ``art`` key, and
    that is what tells the NEXT recompose whether a PNG on disk is the composer's own (repaint it)
    or the author's painting (keep it). The tab writes ``self.plan()`` to the sidecar and hands the
    CLI that path, so a room key this tab dropped would silently turn every painted room back into
    a checkerboard. `_carry` keeps it by EXCLUSION, which is exactly why it works -- but only while
    ``art`` stays out of ``_ROOM_OWNED``."""
    p = tmp_path / FP.SIDECAR
    fp = {"art/back.png": "a" * 64, "art/floor.png": "b" * 64}
    p.write_text(json.dumps({
        "version": 1, "name": "X", "id_base": 30500,
        "rooms": [{"name": "ROOM1", "poly": _A, "id": 30500, "art": fp}], "doors": []}),
        encoding="utf-8")
    doc, _ = _doc(app)
    doc.load_plan(p)
    out = doc.plan()["rooms"][0]
    assert out["art"] == fp, "the tab dropped the art fingerprint; every painted room repaints"
    assert out["id"] == 30500, "and the id pin rides the same carry"


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


# ------------------------------------------------- the chart/findings rail (the shared budget)

def _laid_out(app, doc, w=900, h=620):
    """Give ``doc`` a REAL layout pass without putting a window on anyone's desktop.

    ``resize()`` alone is not one: an unshown widget never lays out, so the rail's sizes stay
    ``[0, 0]`` and ``_fit_split`` correctly declines to divide nothing. ``WA_DontShowOnScreen`` +
    ``show()`` is the same pair ``tools/gui_snap.py`` renders with. Geometry read after this is
    still offscreen geometry — assert relations, not numbers.

    ★ AND IT MUST QUIESCE THE DEBOUNCE. Every gesture arms a 140ms timer whose default lane is a
    WORKER THREAD, and nothing in this module had ever run an event loop, so that timer had never
    once fired here. The first ``processEvents()`` let it — and a judge thread importing under the
    main thread's feet took down an unrelated later test with ``partially initialized module
    'numpy'``, a "circular import" that is really a data race. A probe that leaves a thread running
    is not a probe, it is the next test's flake; so the timer is stopped and the verdict is taken on
    the deterministic sync lane the rest of this module already uses.
    """
    doc._debounce.stop()
    doc.judge_now(sync=True)
    doc.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    doc.resize(w, h)
    doc.show()
    app.processEvents()
    doc._debounce.stop()
    doc._fit_plist()
    app.processEvents()
    doc._debounce.stop()
    return doc


def _refused(app, **kw):
    """The state the rail exists for: a plan whose door gate REFUSES, so the well has content."""
    doc, run = _two_rooms(app, **kw)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)
    doc.depth.setValue(100)                            # under DEPTH_MIN -> the long refusal
    doc.judge_now(sync=True)
    return doc, run


def test_the_chart_and_the_well_share_one_rail(app):
    """★ THE CHART IS THE PRIMARY SURFACE, and before the rail it lost to the well exactly when a
    gate refused. Measured natively at CALIBRE 150 in an 850px window: of a 556px document the well
    took 118px and the canvas was left **130** — 23% of the tab, showing a plan the author could not
    read, at the one moment the problem being reported was about that plan.

    The fixed rows ride in the UPPER pane on purpose: the chart and the well are not adjacent (the
    envelope, id and status rows sit between them), so this is what keeps the reading order — and
    the status line's "see the list below" — true while still making every pixel the rail takes from
    the well a pixel the canvas gets, the canvas being the only stretching member above it."""
    doc, _ = _refused(app)
    assert doc.split.count() == 2
    assert doc.split.widget(0) is doc._upper and doc.split.widget(1) is doc.plist
    assert doc.canvas.parent() is doc._upper, "the canvas stretches inside the upper pane"
    for w in (doc.status, doc.id_box, doc.mod_box, doc.name_box):
        assert doc._upper.isAncestorOf(w), f"{w} must ride with the chart, not below the rail"
    assert doc.split.isCollapsible(0) is False, "the chart never collapses to nothing"
    assert doc.split.isCollapsible(1) is True, "the well may be dragged shut -- that is a choice"

    # ...and every spare pixel goes to the CHART. Fenced as the effect, not as the setter (QSplitter
    # has no stretchFactor getter, and the effect is what the author sees): grow the document and
    # the canvas must take the whole increase while the content-sized well stays put.
    _laid_out(app, doc, 900, 560)
    chart, well = doc.canvas.height(), doc.plist.height()
    _laid_out(app, doc, 900, 760)
    assert doc.plist.height() == well, "the well grew on a taller window instead of the chart"
    assert doc.canvas.height() >= chart + 180, \
        f"the chart took only {doc.canvas.height() - chart} of a 200px increase"


def test_the_rail_default_never_leaves_a_void_over_the_chart(app):
    """★ A SPLITTER SEEDS FROM sizeHint AND NEVER RECLAIMS WHAT maximumHeight REFUSES — the rail's
    own regression, caught by the snap the day it went in. A ``QListWidget``'s sizeHint is ~256x192
    whatever it holds, so Qt placed the handle at the well's 192px HINT while ``maximumHeight``
    clamped the widget to 72: 120px of dead splitter void, and the chart fell from 313 to 184 at
    CALIBRE 100. Stretch factors cannot fix it (they divide a surplus, and there was none), so
    ``_fit_split`` sets the default explicitly from the ceiling ``_fit_plist`` just measured."""
    doc, _ = _refused(app)
    _laid_out(app, doc)
    upper, well = doc.split.sizes()
    assert well <= doc.plist.maximumHeight(), \
        f"the rail gave the well {well} for a box that can only be {doc.plist.maximumHeight()}"
    assert upper + well == sum(doc.split.sizes()), "no pane may be left holding a void"
    assert upper >= doc.pane_floor(0), "the chart column never opens below its own floor"


def test_the_charts_floor_hears_the_dial(app):
    """A px constant cannot hear the CALIBRE dial, and the chart's floor is two overlay CHIPS —
    the compass and the zoom hint, both pinned to the viewport corners, both text. So the floor is
    read from the live labels and MUST grow with the dial.

    Asserted as a relation, never as a number: this module runs offscreen, whose stub font DB has
    manufactured whole defects in this repo (it reports 65/71/82 here against a real 85/100/112)."""
    floors = []
    for scale in (100, 125, 150):
        doc, _ = _doc(app)
        doc.set_scale(scale)
        floors.append(doc.canvas.chart_floor())
        assert doc.canvas.minimumHeight() == doc.canvas.chart_floor(), \
            "the floor is only a floor if the widget carries it"
    assert floors == sorted(floors) and floors[0] < floors[-1], \
        f"a floor that does not move with the dial is a px constant in disguise: {floors}"


def test_an_untouched_rail_is_never_persisted(app):
    """★ A VALUE THE APP COMPUTED UNDER DURESS IS NOT A VALUE THE USER CHOSE (the round-7 law).
    The cheapest way to honour it on a new rail is to never record the app's own arithmetic at all:
    until the handle moves there is no preference here, so the save path has nothing to write and
    the next launch re-derives the default from the live font and window."""
    doc, _ = _refused(app)
    _laid_out(app, doc)
    assert doc.split_sizes() is None, "the app sizing its own rail is not the author choosing"
    doc._on_split_moved(0, 1)                          # what splitterMoved delivers on a real drag
    assert doc.split_sizes() == [int(x) for x in doc.split.sizes()]


def test_a_squeezed_rail_is_not_a_preference(app):
    """The round-7 law spent on this rail — the same tell, the same boundary, and the floors READ
    at runtime because they are font-dependent (``chart_floor`` moves with the dial; the well's is
    Qt's list default, a flat 74 native / 70 offscreen — which is precisely why it is taken from the
    live widget rather than copied here as a literal that would be wrong on one of them)."""
    doc, _ = _refused(app)
    up, well = doc.pane_floor(0), doc.pane_floor(1)

    # PINNED AT A MINIMUM == forced by a short window (or a bigger dial than the one that saved).
    assert doc.repair_split([up, 300]) is None
    assert doc.repair_split([up + 2, 300]) is None
    assert doc.repair_split([600, well]) is None
    assert doc.repair_split([600, well + 2]) is None

    # COLLAPSED TO ZERO == chosen: setCollapsible(1, True), so a shut well is a deliberate drag.
    assert doc.repair_split([600, 0]) == [600, 0]
    # ...and pane 0 is NOT collapsible, so a zero chart is not something a drag can produce.
    assert doc.repair_split([0, 400]) is None

    # Comfortably clear of both floors == a real drag. Keep it.
    assert doc.repair_split([600, 200]) == [600, 200]
    # Arity / type / sign — prefs.layout() fences these too; belt and braces.
    assert doc.repair_split([600]) is None
    assert doc.repair_split([600, 200, 40]) is None
    assert doc.repair_split([-1, 400]) is None
    assert doc.repair_split("nonsense") is None


def test_restore_split_spends_the_repair(app):
    """The mechanism is worth nothing if the call site does not spend it — this arc's oldest lesson.
    A saved squeeze must not become the author's balance just because it was on disk."""
    doc, _ = _refused(app)
    assert doc.restore_split([600, 200]) is True and doc.split_sizes() == [600, 200]
    doc._split_choice = None
    assert doc.restore_split([600, doc.pane_floor(1)]) is False, "a squeeze fossil is refused"
    assert doc.split_sizes() is None, "...and the live default is left to re-derive itself"


def test_the_status_stops_promising_a_list_that_is_shut(app):
    """A refusal must always say where to read it. The well is collapsible on purpose, which makes
    "see the list below" a lie in exactly the state where a refusal most needs somewhere to point —
    and the replacement is kept to one word longer because this is an ElideLabel that drops its
    TAIL: the first cut ("open the findings rail below to read them") rendered as "…below to rea…"
    at CALIBRE 150, eliding away the very words it was added to say."""
    doc, _ = _refused(app)
    assert "see the list below" in _status(doc)
    doc._split_choice = [500, 0]                       # the author dragged it shut
    doc._paint_verdict()
    assert doc._well_shut() is True
    assert "see the list below" not in _status(doc)
    assert "open the list below" in _status(doc)
    doc._split_choice = [400, 100]                     # ...and opened it again
    doc._paint_verdict()
    assert "see the list below" in _status(doc)


def test_the_rail_is_visible_and_grabbable(app):
    """★ THE RAIL IS A CONTROL, NOT A DIVIDER, so it does not get divider ink. The app-wide
    ``QSplitter::handle`` is ``$border`` at 1px, and both halves fail this one surface: 1px is a
    grab target the author cannot hit, and ``$border`` measures **1.25-1.49:1** against ``$surface``
    across the 8 palettes — the 6x-magnified strip showed a flat band with no rail in it, which is
    what sub-3.0 looks like. ``$muted`` is 5.08-6.99:1 in every palette, clearing the 3.0 NON-TEXT
    floor (WCAG 1.4.11).

    :hover goes to ``$text``, not ``$accent``: accent is only 2.47:1 on nord, so hovering would have
    made the rail HARDER to see there. Monotone by measurement, asserted per palette."""
    from ff9mapkit.editor import theme as T
    from ff9mapkit.workspace import style

    doc, _ = _doc(app)
    assert doc.split.objectName() == "floorplanSplit", "the scoped rule needs its id on the widget"
    for name in T.THEME_CHOICES:
        pal = pick_palette(name)
        sheet = style.qss(pal)
        assert "QSplitter#floorplanSplit::handle:vertical" in sheet
        assert "QSplitter#floorplanSplit::handle:vertical:hover" in sheet
        base = _contrast(_srgb(pal["muted"]), _srgb(pal["surface"]))
        hover = _contrast(_srgb(pal["text"]), _srgb(pal["surface"]))
        assert base >= 3.0, f"{name}: the rail is {base:.2f}:1 -- under the non-text floor"
        assert hover >= base, (f"{name}: hover {hover:.2f} is fainter than the resting rail "
                               f"{base:.2f} -- the affordance would go backwards")


def test_candidate_doors_is_pure_and_survives_a_sick_outline():
    """A bowtie offers nothing and must not raise -- G1 is what reports it, not a traceback."""
    rooms = [{"name": "A", "poly": [(0, 0), (1000, 1000), (1000, 0), (0, 1000)]},
             {"name": "B", "poly": _B}]
    assert candidate_doors(rooms, []) is not None
    rooms = [{"name": "A", "poly": _A}, {"name": "B", "poly": _B}]
    got = candidate_doors(rooms, [])
    assert len(got) == 1 and got[0]["length"] == pytest.approx(1600.0)
    assert candidate_doors([{"name": "A", "poly": [(0, 0), (1, 1)]}], []) == []


# ------------------------------------------------- the SCREEN-FIXED chips (viewport-space ink)
# Every other de-collision on this chart argues in SCENE space against other chart ink. ``_hint``
# and ``_compass`` are QLabel CHILDREN OF THE VIEWPORT: they live in viewport px, paint above the
# scene, and nothing in scene space can see them. Measured (native, dark, the refused plan) the
# door caption printed 186x16px INSIDE the zoom hint across a band of chart heights. The reasoning
# and the numbers live in floorplandoc's note above ``label_offsets``.

def _chart_labels(canvas):
    """``[(text, ink rect in viewport px)]`` for every label on the chart.

    ★ NEVER ``parentItem()``. On these items it flips C++ ownership to the Python wrapper and
    SEGFAULTS the run (memory project-ff9-pyside-parentitem-ownership). ``deviceTransform`` over
    the view's ``viewportTransform`` composes the whole ItemIgnoresTransformations subtree with no
    parent walk — and it measures INK, not the boundingRect, because a box carries the font's
    leading and descent: an intersection is not a collision.
    """
    from PySide6.QtCore import QRectF
    from PySide6.QtWidgets import QGraphicsSimpleTextItem
    vt = canvas.viewportTransform()
    out = []
    for it in canvas._scene.items():
        if isinstance(it, QGraphicsSimpleTextItem):
            x, y, w, h = canvas._ink_box(it.text(), it.font(), it.boundingRect())
            out.append((it.text(), it.deviceTransform(vt).mapRect(QRectF(x, y, w, h))))
    return out


def _bites(canvas, chips=None):
    """``[(text, depth px)]`` — every label whose INK is under a screen-fixed chip."""
    from ff9mapkit.workspace.floorplandoc import _overlap
    chips = canvas._chip_rects() if chips is None else chips
    out = []
    for text, r in _chart_labels(canvas):
        for c in chips:
            ow, oh = _overlap(r.x(), r.y(), r.width(), r.height(), *c)
            if ow > 0 and oh > 0:
                out.append((text, min(ow, oh)))
    return out


def _charted(app, *, w=880, h=230):
    """A two-room plan with a DECLARED door, on a canvas sized like the real one and fitted.

    The size is passed, never asserted in px: offscreen stubs the font DB, so every WIDTH it
    reports is fiction. Everything below asserts a RELATION between measured rects instead.
    """
    doc, _ = _two_rooms(app)
    doc.tools.set_current("doors")
    doc.judge_now(sync=True)
    doc.canvas.click_world(0, 0)                   # declare the ROOM1-ROOM2 wall
    doc.judge_now(sync=True)
    doc.canvas.resize(w, h)
    doc.canvas.fit()
    return doc


def test_a_label_mirror_is_about_the_ANCHOR_and_x_comes_first():
    """The mirror is behaviordoc's own (``dx = -dx - width``): the same distance from the anchor
    on the OTHER side, so the point the label names is still the point it points at. x BEFORE y
    because a chip is a ~31px corner band and a y mirror moves a label by little more than its own
    height — the door caption straddles its anchor, so its y mirror is a 6px step back into it."""
    offs = label_offsets(10, -14, 300, 22)
    assert offs[0] == (10, -14), "the AUTHORED offset must be the first candidate"
    assert len(offs) == 4 and len(set(offs)) == 4
    assert offs[1] == (-310, -14), "x mirror: left edge 10 right of anchor -> right edge 10 left"
    assert offs[2] == (10, -8), "y mirror: top 14 above the anchor -> bottom 14 below it"
    assert offs[3] == (-310, -8)
    assert offs[1][1] == offs[0][1] and offs[2][0] == offs[0][0], "one axis at a time, x first"
    centred = label_offsets(10, -14, 300, 22, centre=True)
    assert [o[0] for o in centred] == [-150.0, -150.0], \
        "a centred label's offset IS -w/2 -- its x mirror is itself and must drop out"
    assert len(centred) == 2


def test_the_chip_clearance_moves_NOTHING_when_no_chip_is_under_the_label():
    """The safety of the whole pass. It is a chip clearance and nothing else: with no chip under
    the label the geometry every other comment in floorplandoc was measured against must come back
    byte for byte, or a mirror appears for a reason nobody can see."""
    offs = label_offsets(10, -14, 300, 22)
    ink = (0.0, 5.0, 300.0, 12.0)
    assert clear_of_chips(offs, (437.0, 180.0), ink, []) == offs[0]
    far = [(0.0, 400.0, 260.0, 28.0), (10.0, 8.0, 446.0, 28.0)]
    assert clear_of_chips(offs, (437.0, 180.0), ink, far, viewport=(875.0, 226.0)) == offs[0]


def test_a_label_whose_INK_lands_on_a_chip_flips_to_the_other_side():
    """The measured case as numbers: the caption's anchor on the shared wall, the hint chip in the
    viewport's bottom-right corner, the authored offset printing the caption into it."""
    offs = label_offsets(10, -14, 300, 22)
    ink = (0.0, 5.0, 300.0, 12.0)
    # at the AUTHORED offset the caption's ink spans x 447..747, y 171..183; the chip's top edge
    # cuts 3px into it, which is the shallow end of the measured band (7px at chart height 228).
    hint = [(560.0, 180.0, 300.0, 28.0)]
    got = clear_of_chips(offs, (437.0, 180.0), ink, hint, viewport=(875.0, 226.0))
    assert got == offs[1], "the x mirror is the step that clears a corner band"
    left = 437.0 + got[0] + ink[0]
    assert left + ink[2] <= hint[0][0], "the pick must actually be CLEAR, not merely different"


def test_an_INTERSECTION_IS_NOT_A_COLLISION():
    """A text item's boundingRect carries the font's leading and descent — measured at CALIBRE 150
    the door caption's box is 22.0px around 15.7px of ink, 5.4 slack above and 0.9 below. A rule
    that flipped on BOX intersection would move labels that are visibly clear; one that ignored a
    real bite would leave glyphs buried. Both halves, on one ink box."""
    offs = label_offsets(10, -14, 300, 22)
    ink = (0.0, 5.0, 300.0, 12.0)                  # box spans 0..22 local, ink only 5..17
    # placed, the caption's BOX spans y 166..188 and its INK only 171..183.
    box_only = [(560.0, 184.0, 300.0, 28.0)]       # 4px of box under the chip, 0px of glyph
    assert clear_of_chips(offs, (437.0, 180.0), ink, box_only,
                          viewport=(875.0, 226.0)) == offs[0]
    into_the_ink = [(560.0, 180.0, 300.0, 28.0)]   # 3px of real glyph under the chip
    assert clear_of_chips(offs, (437.0, 180.0), ink, into_the_ink,
                          viewport=(875.0, 226.0)) != offs[0]


def test_the_clearance_is_total_so_a_redraw_never_oscillates():
    """Every candidate scores and ties break on the authored order, so the same geometry always
    picks the same offset — feeding the choice back in must be a fixed point. And when NOTHING is
    clear it still answers with a real candidate rather than giving up on the first."""
    ink = (0.0, 5.0, 300.0, 12.0)
    offs = label_offsets(10, -14, 300, 22)
    hint = [(560.0, 180.0, 300.0, 28.0)]
    got = clear_of_chips(offs, (437.0, 180.0), ink, hint, viewport=(875.0, 226.0))
    assert got != offs[0], "this fence is only a fixed-point test if the pass actually MOVED it"
    again = clear_of_chips([got] + [o for o in offs if o != got], (437.0, 180.0), ink, hint,
                           viewport=(875.0, 226.0))
    assert again == got, "the pick must be a fixed point, or a redraw can chatter between two"
    swamped = [(-4000.0, -4000.0, 8000.0, 8000.0)]        # a chip over the whole chart
    assert clear_of_chips(offs, (437.0, 180.0), ink, swamped) in offs


def test_the_door_caption_clears_the_zoom_hint_on_the_REAL_paint(app):
    """The fence with teeth: the genuine ``_label`` path, the genuine chip rect, ink measured off
    the painted items. The chip is PARKED on the caption so the collision is produced rather than
    waited for — what produces it in the wild is a band of chart HEIGHTS, and offscreen cannot be
    trusted to reproduce a px band (it stubs the font DB)."""
    doc = _charted(app)
    caption = [(t, r) for t, r in _chart_labels(doc.canvas) if "deep" in t]
    assert caption, "no door caption on the chart -- this fence would be vacuous"
    text, rect = caption[0]
    doc.canvas._hint.setGeometry(int(rect.x()), int(rect.y()),
                                 max(1, int(rect.width())), max(1, int(rect.height())))
    parked = doc.canvas._chip_rects()
    assert parked, "_chip_rects saw nothing -- isVisibleTo is what keeps this from going vacuous"

    doc.canvas._chip_rects = lambda: []            # the control: the clearance switched OFF
    doc.canvas._draw()
    assert _bites(doc.canvas, parked), "red-first: without the clearance the caption must BITE"

    del doc.canvas._chip_rects                     # ...and back to production
    doc.canvas._draw()
    assert not _bites(doc.canvas), f"a chart label is still under a chip: {_bites(doc.canvas)}"
    moved = [r for t, r in _chart_labels(doc.canvas) if t == text]
    assert moved and moved[0].x() != rect.x(), "the caption must have FLIPPED, not merely redrawn"


def test_every_chart_label_is_judged_against_the_chips():
    """THE BLAST RADIUS. ``_label`` serves the room name / metrics / entry tiers, the shared-wall
    caption, the door caption and the pending-corner caption — so the clearance belongs at that ONE
    seam and no tier may reach the scene around it. Asserted on the SOURCE, because a tier that
    called ``addSimpleText`` itself would be invisible to every state this suite can reach."""
    import ast
    import inspect
    from ff9mapkit.workspace import floorplandoc
    owners = set()
    for fn in ast.walk(ast.parse(inspect.getsource(floorplandoc))):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Attribute) and node.attr == "addSimpleText":
                owners.add(fn.name)
    assert owners == {"_label"}, \
        f"a label tier reaches the scene around the chip clearance: {sorted(owners)}"


def test_the_clearance_re_runs_when_the_chips_MOVE(app):
    """The chips are pinned to the viewport's CORNERS, so a resize moves them under labels that did
    not move — and the height band this fixes is REACHED by a resize. behaviordoc's own rule: the
    pass re-runs per draw, fit and zoom."""
    doc = _charted(app)
    for h in (200, 230, 260, 300, 340):
        doc.canvas.resize(880, h)
        doc.canvas.fit()
        assert not _bites(doc.canvas), f"chart height {h}: {_bites(doc.canvas)}"


def test_a_canvas_with_no_real_viewport_leaves_every_label_where_it_was(app):
    """``_place_hint`` has not run against a real viewport yet, so the chip rects are fiction —
    judging against them would move labels to dodge a chip that is not there."""
    from PySide6.QtCore import QRectF
    doc, _ = _two_rooms(app)
    doc.canvas.resize(20, 20)
    for text, dx, dy, centre in (("shared wall", 6, -16, False), ("100u deep", 10, -14, False),
                                 ("ROOM1", 0, -9, True)):
        got = doc.canvas._chip_clear(0, 0, text, doc.canvas._font(8), QRectF(0, 0, 300, 22),
                                     dx, dy, centre)
        assert got == label_offsets(dx, dy, 300, 22, centre=centre)[0]


# ============================================================ the live gate: fast, and still live
# `compose` re-ran WHOLE on every gesture: ~17s per drag on an eight-room plan -- the same as
# drawing it -- and one worker per
# keystroke stacking under the GIL. The tab now carries one `GeomCache` across judges and hands the
# composer a `cancel` hook. These pin the three things that buys, and the one thing it must not
# cost -- a verdict that differs from the one a cold judge would have painted.


def test_the_doc_carries_one_cache_across_judges(app):
    """★ THE CALL-SITE LAW. `GeomCache` existing in `floorplan.py` is worth nothing; SPENDING it
    here is the whole optimization. A gesture changes one room, so a second judge of a plan whose
    geometry did not move must be almost entirely hits.

    Measured before this: ~17s per gesture on eight rooms, the same as a cold judge, because there
    was no cache to carry. After: ~0.6s, and FLAT in room count.
    """
    doc, _ = _two_rooms(app)
    doc.judge_now(sync=True)
    before = (doc._cache.hits, doc._cache.misses)
    doc.judge_now(sync=True)                            # the same geometry, judged again
    after = (doc._cache.hits, doc._cache.misses)
    assert after[0] > before[0], "the second judge recomputed everything -- the cache is not spent"
    assert after[1] == before[1], f"a re-judge of unchanged geometry missed {after[1] - before[1]}"


def test_a_cached_judge_paints_the_same_verdict_as_a_cold_one(app):
    """The cache may cost time and may never cost truth. Two docs, one warm and one cold, must
    agree on every visible piece of the verdict -- which rooms are refused, which are warned, the
    findings text, and whether Compose is enabled."""
    warm, _ = _two_rooms(app)
    warm.judge_now(sync=True)
    warm.judge_now(sync=True)
    cold, _ = _two_rooms(app)
    cold._cache = FP.GeomCache()                        # a cache that has never seen this plan
    cold.judge_now(sync=True)

    def seen(d):
        return (d.canvas._bad_rooms, d.canvas._warn_rooms, d.canvas._bad_doors,
                [d.plist.item(i).text() for i in range(d.plist.count())],
                d.compose_btn.isEnabled(), _status(d))

    assert seen(warm) == seen(cold)


def test_a_cancelled_judge_is_not_painted_as_a_refusal(app):
    """★ `ComposeCancelled` is deliberately NOT a `ComposeError`, so `_judge_work`'s catch-all would
    render a superseded judge as a red finding reading "the composer could not judge this plan:
    ComposeCancelled:" -- a refusal the author never earned. Today `_finish_judge`'s generation
    check happens to drop that payload before it paints, which makes it latent rather than visible:
    exactly the kind that surfaces the day somebody judges synchronously on a stale generation.

    A cancelled judge found NOTHING. It says so."""
    plan = {"name": "D", "rooms": [{"name": "ROOM1", "poly": _A}], "doors": [], "id_base": 30500}
    composed, errors, warnings = FloorplanDoc._judge_work(plan, cancel=lambda: True)
    assert composed is None
    assert errors == [], f"a cancelled judge painted {errors}"
    assert warnings == []


def test_judge_work_is_still_callable_unbound_with_one_positional_arg(app):
    """The cache and cancel arrive as keyword-only extras with `None` defaults precisely so this
    stays true -- several fences (and any future one) call it as a plain function."""
    plan = {"name": "D", "rooms": [{"name": "ROOM1", "poly": _A}], "doors": [], "id_base": 30500}
    composed, errors, _w = FloorplanDoc._judge_work(plan)
    assert composed is not None and not errors


def test_the_dungeon_name_does_not_re_judge_the_geometry(app, monkeypatch):
    """★ Typing a nine-character name spawned NINE full composes -- the 140ms debounce only
    coalesces keystrokes faster than that, and compose is pure Python under the GIL, so they
    stacked: 2.7s of asked-for work took 13.2s with Compose disabled throughout.

    `compose` reads `name` in exactly one place (the composed campaign's own name) and it reaches
    no grid sample. The gate the old comment invoked, `_name_problem`, lives in
    `_envelope_problems`, which `_paint_verdict` spends on EVERY repaint whether or not a judge
    ran -- so the name box needs a repaint, not a re-judge."""
    doc, _ = _two_rooms(app)
    doc.judge_now(sync=True)
    calls = []
    real = FP.compose
    monkeypatch.setattr(FP, "compose", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    for ch in "GREATHALL":
        doc.name_box.setText(doc.name_box.text() + ch)
    assert calls == [], f"{len(calls)} composes for nine keystrokes"

    # ...and the name gate still fires, because it never depended on the judge
    doc.name_box.setText("bad name/with slash")
    assert any("name" in doc.plist.item(i).text().lower() for i in range(doc.plist.count())) or \
        not doc.compose_btn.isEnabled(), "the name gate stopped being enforced"


def test_a_verdict_landing_mid_drag_does_not_eat_the_drag(app):
    """★ THE SNAP-BACK, fenced. `PlanCanvas.set_plan` used to do `self._drag = None` on every feed
    -- and the live gate feeds it from a worker. A verdict landing mid-drag discarded the gesture
    silently: `mouseReleaseEvent` tests `if self._drag`, so the release committed nothing, no
    `room_reshaped` was emitted, no undo entry was pushed, and `_draw` repainted the room at its
    PRE-DRAG outline. The generation guard could not save it, because a drag never bumps `_gen`.

    Second-order, on the same line: a release that had barely travelled was then re-read as a
    CLICK, which in Rooms mode silently starts a new outline under the author's cursor.

    Making the gate fast shrinks this window. It does not close it. The drag outranks the feed."""
    doc, _ = _two_rooms(app)
    doc.judge_now(sync=True)
    canvas = doc.canvas
    before = list(canvas._rooms[0]["poly"])

    assert canvas.press_world(*_A[0]) is True, "the corner handle was not grabbable"
    canvas.drag_world(_A[0][0] - 300, _A[0][1] - 300)
    assert canvas._drag is not None

    doc._paint_verdict()                                # what a worker's verdict does, exactly

    assert canvas._drag is not None, "the verdict ate the drag"
    assert canvas._poly(0) != before, "the drag's live outline was reverted under the author"
    canvas.release_world(_A[0][0] - 300, _A[0][1] - 300)
    assert canvas._drag is None
    assert doc._session["rooms"][0]["poly"] != before, "the release did not commit the drag"


def test_a_feed_that_no_longer_shows_the_dragged_room_clears_the_drag(app):
    """The other half, and it is why the guard is not an index-range check. The drag record is an
    INDEX into the fed rooms plus the outline that was under the cursor when the press landed. A
    feed that no longer shows THAT room unchanged at THAT index must drop the gesture -- deleting an
    earlier room keeps every index in range while sliding a different room under it, and a release
    would then write this drag onto somebody else's outline.

    ``_B[1]``, not ``_B[0]``: the rooms abut, so their shared corner picks ROOM1's handle and the
    test would silently be dragging the wrong room."""
    doc, _ = _two_rooms(app)
    canvas = doc.canvas
    assert canvas.press_world(*_B[1]) is True
    assert canvas._drag["ri"] == 1, "grab a corner ROOM1 does not also own"
    canvas.drag_world(_B[1][0] + 100, _B[1][1] + 100)

    canvas.set_plan([{"name": "ROOM1", "poly": _A}], [])       # ROOM2 is gone: index out of range
    assert canvas._drag is None

    assert canvas.press_world(*_A[0]) is True                  # now index 0, still in range...
    canvas.drag_world(_A[0][0] - 50, _A[0][1] - 50)
    assert canvas._drag is not None
    canvas.set_plan([{"name": "ROOM2", "poly": _B}], [])       # ...but a DIFFERENT room sits there
    assert canvas._drag is None, "an index-range check alone would have kept this drag"


# ==================================================== first contact, 2026-07-30: the drawing gesture
# The first human to use this tab reported, in order: "it's hard to click the same spot twice", "the
# view shifts when adding new points", "the first point is always put at the origin", and "is getting
# the edges close together for a door supposed to be so hard?".
#
# The first three are ONE defect and the fourth is a missing affordance. Neither was reachable by any
# fence here, because every fence drove `click_world` -- the world-space seam -- and the defect lived
# entirely in what the VIEW did between one click and the next.


def _click(canvas, px, py):
    """A real press/release pair at a viewport pixel -- the path a mouse takes, not the seam."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    p = QPointF(px, py)
    for typ, handler in ((QMouseEvent.Type.MouseButtonPress, canvas.mousePressEvent),
                         (QMouseEvent.Type.MouseButtonRelease, canvas.mouseReleaseEvent)):
        handler(QMouseEvent(typ, p, canvas.viewport().mapToGlobal(p), Qt.MouseButton.LeftButton,
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))


def _origin_on_screen(canvas):
    """Where world (0,0) currently sits in viewport pixels -- i.e. where the chart IS."""
    from PySide6.QtCore import QPointF
    o = canvas.world_to_scene(0.0, 0.0)
    p = canvas.mapFromScene(QPointF(*o))
    return (p.x(), p.y())


def _laid_out_canvas(app, doc, w=880, h=420, *, viewport_w=None):
    """★ ``viewport_w`` FORCES THE VIEWPORT'S WIDTH, AND ITS PARITY IS LOAD-BEARING.

    ``doc.canvas.resize(w, h)`` is silently overridden by the layout -- the real viewport is 1250,
    an EVEN number, every single time. That matters more than it sounds: the chart-drift defect
    class lives in Qt's re-centring branch, whose `leftIndent` is an INTEGER division, so it can
    only bias on an ODD extent. Every canvas fence in this file therefore ran under the one
    condition that makes the whole class invisible, and a fence written against it passed happily
    on the broken code. Pass an odd width to actually exercise it."""
    doc.resize(1280, 900)
    doc.show()
    app.processEvents()
    doc.canvas.resize(w, h)
    app.processEvents()
    if viewport_w is not None:
        c = doc.canvas
        c.setFixedWidth(viewport_w + (c.width() - c.viewport().width()))
        app.processEvents()
        assert c.viewport().width() == viewport_w, (
            f"could not force the viewport to {viewport_w}; got {c.viewport().width()}")
    doc.canvas.fit()
    app.processEvents()
    return doc.canvas


def test_the_chart_does_not_move_while_a_room_is_being_drawn(app):
    """★ THE DEFECT FIRST CONTACT HIT, and the reason its three reports are one bug.

    `_scene_bounds` follows the geometry and the geometry includes the outline IN PROGRESS, so the
    first corner collapsed the scene rect from 480 world units to 58 -- one point plus its pad. Qt
    then centred a rect far smaller than the viewport and the whole chart jumped: measured, world
    (0,0) moved 375px right and 253px down on the FIRST click.

    That is why "the first point is always put at the origin": the point does not move, the chart
    does, until the point sits dead centre where the origin crosshair used to be. And it is why
    clicking the same spot twice was hard -- every click after the first landed in a new frame.

    Four clicks at a screen RECTANGLE must produce a world RECTANGLE. Before the fix they produced
    a garbage quadrilateral."""
    doc, _ = _doc(app)
    c = _laid_out_canvas(app, doc)
    before = _origin_on_screen(c)

    for px, py in [(250, 120), (600, 120), (600, 320), (250, 320)]:
        _click(c, px, py)
        app.processEvents()
        now = _origin_on_screen(c)
        assert now == pytest.approx(before, abs=1.0), (
            f"the chart moved {now[0] - before[0]:+.0f},{now[1] - before[1]:+.0f}px under the "
            f"author while they were drawing")

    pts = c.pending()
    assert len(pts) == 4
    xs = sorted({round(x) for x, _z in pts})
    zs = sorted({round(z) for _x, z in pts})
    assert len(xs) == 2 and len(zs) == 2, (
        f"four clicks on a screen rectangle produced {pts} -- not a rectangle in world space")


def test_ctrl_zero_still_frames_the_geometry_after_the_view_has_wandered(app):
    """The scene rect is now allowed to grow past the geometry so the view is never re-anchored
    (see `_stable_rect`). That slack accumulates as the author pans -- so `fit()` has to re-derive
    from `_scene_bounds()` and not from `sceneRect()`, or Ctrl+0 would frame wherever they had
    wandered to instead of framing the rooms.

    Asserted on the visible result, not on the rect: after Ctrl+0 the geometry is fully on screen
    AND fills a fair share of it."""
    doc, _ = _two_rooms(app)
    c = _laid_out_canvas(app, doc)
    doc.judge_now(sync=True)
    c.fit()
    app.processEvents()
    fit_zoom = c._zoom

    for _ in range(8):                    # zoom OUT, which is what actually grows the union:
        f = 1 / 1.15                      # panning cannot, since the view is clamped to the rect
        c.scale(f, f)
        c._zoom *= f
        c._draw()
    app.processEvents()
    geom = c._scene_bounds()
    assert c._scene.sceneRect().width() > geom.width() * 2, (
        "the view never actually took on slack, so this fence is asserting nothing")

    c.fit()
    app.processEvents()
    vis = c.mapToScene(c.viewport().rect()).boundingRect()
    assert vis.contains(geom), "Ctrl+0 left the rooms off screen"
    assert c._zoom == pytest.approx(fit_zoom, rel=0.05), (
        f"Ctrl+0 framed the accumulated slack, not the rooms (zoom {c._zoom} vs {fit_zoom})")


def test_a_corner_snaps_onto_a_neighbours_corner_and_wall(app):
    """★ "is getting the edges close together for a door supposed to be so hard?" -- no.

    `shared_edges` admits two rooms as sharing a wall only within 8 WORLD units, and at the chart's
    opening zoom one screen pixel is already ~9. A pixel-perfect click is therefore OUT of tolerance
    before the mouse even moves, and the author gets "No shared wall here" with nothing to correct.

    Measured A/B on identical clicks 3-5px off a shared wall: snapping off -> shared_edges offers
    ZERO candidates; snapping on -> one candidate spanning the whole 1049u wall."""
    doc, _ = _doc(app)
    c = _laid_out_canvas(app, doc)
    for p in [(300, 150), (600, 150), (600, 330), (300, 330)]:
        _click(c, *p)
    _click(c, 300, 150)
    app.processEvents()
    doc.judge_now(sync=True)
    r1 = doc._session["rooms"][0]["poly"]

    for p in [(604, 153), (880, 147), (877, 334), (603, 327)]:      # sloppy, 3-5px off the wall
        _click(c, *p)
    _click(c, 604, 153)
    app.processEvents()
    doc.judge_now(sync=True)
    r2 = doc._session["rooms"][1]["poly"]

    shared = FP.shared_edges([(float(a), float(b)) for a, b in r1],
                             [(float(a), float(b)) for a, b in r2])
    assert shared, (f"no shared wall from clicks 3-5px off it: ROOM1 {r1} ROOM2 {r2} -- snapping "
                    f"is what makes the 8u tolerance reachable by hand")
    assert shared[0]["length"] > 900, f"only {shared[0]['length']:.0f}u of the wall was shared"


def test_snapping_prefers_a_corner_over_a_wall_and_never_eats_its_own_room(app):
    """A corner lies ON two walls, so it has to win, or starting a room on a neighbour's corner
    would slide along the wall instead. And a dragged vertex must not capture onto its OWN room --
    that collapses the outline into a duplicated corner, which G1 refuses."""
    doc, _ = _two_rooms(app)
    c = _laid_out_canvas(app, doc)
    doc.judge_now(sync=True)

    corner = c._poly(0)[1]
    got, what = c.snap(corner[0] + c.world_tol(2), corner[1] + c.world_tol(2))
    assert what == "corner" and got == pytest.approx(corner, abs=0.01)

    (ax, az), (bx, bz) = c._poly(0)[0], c._poly(0)[1]
    mid = ((ax + bx) / 2.0, (az + bz) / 2.0)
    got, what = c.snap(mid[0], mid[1] + c.world_tol(3))
    assert what == "wall", f"a point beside a wall snapped as {what}"
    assert got == pytest.approx(mid, abs=max(1.0, c.world_tol(1)))

    own = c._poly(0)[0]
    _got, what = c.snap(own[0] + c.world_tol(2), own[1] + c.world_tol(2), skip_room=0)
    assert what != "corner" or _got != pytest.approx(own, abs=0.01), (
        "a dragged vertex captured onto its own room")


def test_the_rubber_band_previews_the_snapped_point(app):
    """The band is the ONLY preview of where the corner lands, so it must show the snapped point --
    a band that says one thing while the click does another is worse than no snapping at all."""
    doc, _ = _two_rooms(app)
    c = _laid_out_canvas(app, doc)
    doc.judge_now(sync=True)
    c.click_world(-5000, -5000)                    # an outline in progress, far from everything
    corner = c._poly(0)[1]
    near = (corner[0] + c.world_tol(2), corner[1] + c.world_tol(2))
    from PySide6.QtCore import QPointF
    p = QPointF(*c.world_to_widget(*near)) if hasattr(c, "world_to_widget") else None
    if p is None:                                  # no widget-space forward map: drive the seam
        c._hover = c.snap(*near)[0]
    else:
        from PySide6.QtGui import QMouseEvent
        c.mouseMoveEvent(QMouseEvent(QMouseEvent.Type.MouseMove, p, c.viewport().mapToGlobal(p),
                                     Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                                     Qt.KeyboardModifier.NoModifier))
    assert c._hover == pytest.approx(corner, abs=0.01), (
        f"the rubber band previewed {c._hover}, not the corner the click would snap to")


# ------------------------------------------------------- the ratchet, and the two ways to miss it

@pytest.mark.parametrize("viewport_w", [1207, 1208], ids=["odd", "even"])
def test_hovering_never_moves_the_chart_at_either_viewport_parity(app, viewport_w):
    """★ THE SLIDE FIRST CONTACT FILMED, and the fence that can actually see it.

    The scene rect used to be `geometry UNIONED WITH mapToScene(viewport().rect())` -- a view input
    computed from a view output. `mapToScene(QRect)` maps `rect.adjusted(0,0,1,1)`, so that union
    always strictly contains the viewport, which forces Qt's "whole scene fits, centre it" branch,
    whose `leftIndent = maxSize.width()/2 - (viewRect.left()+viewRect.right())/2` is an INTEGER
    division. On an ODD extent the re-centre lands half a pixel off, the view moves, the visible
    rect moves with it, the next redraw computes a different union, and it biases the same way
    again -- one pixel per redraw, and the rubber band redraws once per mouse move.

    ⚠ PARITY IS THE WHOLE POINT OF THE PARAMETRIZE. The suite's natural viewport is 1250, EVEN, the
    one width at which this defect cannot occur: the union comes out value-identical every frame,
    `QGraphicsScene::setSceneRect` early-outs, and a fence written at that width passes on the
    broken code. Measured on the unfixed source: even -> (0, 0), odd -> -40px and climbing.

    ⚠ IT IS NOT THE TRANSFORMATION ANCHOR -- `setSceneRect` cannot re-anchor, and the drift is
    identical under `NoAnchor`. Do not "fix" this by touching the anchor: that line is also the only
    thing enabling mouse tracking (see PlanCanvas.__init__), and turning it off silences hover
    entirely while leaving this whole suite green."""
    doc, _ = _doc(app)
    c = _laid_out_canvas(app, doc, viewport_w=viewport_w)
    _click(c, 400, 220)
    app.processEvents()

    before = _origin_on_screen(c)
    rect0 = QRectF(c._scene.sceneRect())
    for px, py in [(420, 230), (470, 250), (520, 240), (560, 210), (600, 200), (640, 230),
                   (600, 280), (540, 300), (480, 280), (430, 240)] * 6:
        p = QPointF(px, py)
        c.mouseMoveEvent(QMouseEvent(QMouseEvent.Type.MouseMove, p, c.viewport().mapToGlobal(p),
                                     Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                                     Qt.KeyboardModifier.NoModifier))
    app.processEvents()

    after = _origin_on_screen(c)
    assert after == pytest.approx(before, abs=1.0), (
        f"viewport {viewport_w} ({'odd' if viewport_w % 2 else 'even'}): 60 hover redraws slid the "
        f"chart by {after[0] - before[0]:+.0f},{after[1] - before[1]:+.0f}px")
    assert c._scene.sceneRect() == rect0, (
        "a hover changed the scene rect -- that is the ratchet's first turn")


def test_the_scene_rect_is_never_derived_from_where_the_view_is_looking(app):
    """The invariant behind the fence above, asserted directly: scroll the view, redraw, and the
    rect must not care. A rect that follows the viewport is a feedback loop whatever the arithmetic
    happens to do this Qt version."""
    doc, _ = _two_rooms(app)
    c = _laid_out_canvas(app, doc, viewport_w=1207)
    doc.judge_now(sync=True)
    rect0 = QRectF(c._scene.sceneRect())
    c.horizontalScrollBar().setValue(c.horizontalScrollBar().value() + 40)
    c.verticalScrollBar().setValue(c.verticalScrollBar().value() + 25)
    c._draw()
    app.processEvents()
    assert c._scene.sceneRect() == rect0, (
        f"scrolling the view changed the scene rect {rect0} -> {c._scene.sceneRect()}")


def test_the_viewport_still_receives_button_less_hover(app):
    """★ THE REGRESSION THAT ALMOST SHIPPED, and it needed Qt's real delivery path to see.

    `setTransformationAnchor(AnchorUnderMouse)` is the ONLY thing in this package that enables
    `setMouseTracking` on the chart's viewport, and Qt delivers button-less `MouseMove` only to
    tracking widgets. Switching the anchor to `NoAnchor` -- which looks like pure hygiene, and which
    fixes nothing here -- silences the rubber band, the snap preview and the coordinate chip
    completely. Measured: 0 hover events of 300.

    Every other mouse fence in this file calls `c.mouseMoveEvent(...)` as a plain method, which
    bypasses delivery entirely, so all of them stayed green with hover dead. This one posts through
    `QApplication.sendEvent` to the viewport, which is the only way the gate is in the blast
    radius."""
    from PySide6.QtWidgets import QApplication as _QApp

    doc, _ = _doc(app)
    c = _laid_out_canvas(app, doc)
    assert c.viewport().hasMouseTracking(), (
        "the chart's viewport is not tracking the mouse -- Qt will not deliver a button-less move, "
        "so the rubber band and the snap preview are dead")

    _click(c, 400, 220)
    app.processEvents()
    seen = []
    for px in range(420, 480, 6):
        p = QPointF(px, 240)
        _QApp.sendEvent(c.viewport(),
                        QMouseEvent(QMouseEvent.Type.MouseMove, p, c.viewport().mapToGlobal(p),
                                    Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                                    Qt.KeyboardModifier.NoModifier))
        seen.append(c._hover)
    app.processEvents()
    assert any(h is not None for h in seen), "no hover reached the canvas through Qt's own delivery"
    assert len({h for h in seen if h is not None}) > 1, (
        "the rubber band's target never moved across six delivered hovers")


# ========================================================= first contact, step 3: stacked handles
# "I can't drag a corner handle of ROOM2 when it's stacked onto a ROOM1 corner. might need some way
# to settle stacked handle selection, I can't think of a good one."
#
# The answer was not to settle the selection. Coincident corners exist for exactly one reason --
# the author snapped them into a shared wall -- so they move together and there is nothing to
# disambiguate.


def _two_abutting(app):
    """Two rooms sharing the x=0 wall, their corners EXACTLY coincident."""
    doc, _ = _two_rooms(app)
    doc.judge_now(sync=True)
    return doc, doc.canvas


def test_a_stacked_corner_can_be_grabbed_at_all(app):
    """★ The defect: `_pick_vertex` broke the tie by room order with a STRICT `<`, so the room
    drawn second could never win, and its corner was simply unreachable."""
    doc, c = _two_abutting(app)
    stacked = (0, -800)
    assert any(tuple(v) == stacked for v in c._poly(0)), "fixture: ROOM1 should own this corner"
    assert any(tuple(v) == stacked for v in c._poly(1)), "fixture: ROOM2 should own it too"

    assert c.press_world(*stacked) is True
    d = c._drag
    welded = {(w["ri"], w["vi"]) for w in (d.get("also") or ())}
    assert welded, "the stacked corner was grabbed alone -- the other room's corner is unreachable"
    assert {d["ri"]} | {ri for ri, _vi in welded} == {0, 1}, "both rooms must be in the weld"
    c.end_drag()


def test_a_welded_corner_drag_keeps_the_abutment(app):
    """★ WHY WELDING BEATS SETTLING THE SELECTION. Moving one of two coincident corners tears the
    shared wall apart, and re-making it means landing the other corner inside `shared_edges`' 8u
    tolerance by hand -- the exact thing snapping exists because nobody can do. So the whole weld
    moves and the abutment survives being edited."""
    doc, c = _two_abutting(app)

    def shared():
        r = doc._session["rooms"]
        return FP.shared_edges([(float(a), float(b)) for a, b in r[0]["poly"]],
                               [(float(a), float(b)) for a, b in r[1]["poly"]])

    assert shared(), "fixture: the rooms should start out sharing a wall"
    c.press_world(0, -800)
    c.drag_world(-200, -1100)
    assert c._poly(0)[1] == c._poly(1)[0], "the weld came apart DURING the drag"
    c.release_world(-200, -1100, travel_px=99)
    doc.judge_now(sync=True)

    r = doc._session["rooms"]
    assert tuple(r[0]["poly"][1]) == (-200, -1100)
    assert tuple(r[1]["poly"][0]) == (-200, -1100), "only one side of the weld was committed"
    assert shared(), "the shared wall did not survive the drag"


def test_a_weld_is_one_undo_step(app):
    """★ A weld that undoes by halves is worse than no weld. Emitting the singular `room_reshaped`
    once per moved room pushed one history entry EACH, so a single undo restored one room and left
    the other moved -- half an abutment, which is a shared wall that no longer exists on one side.
    The batched signal exists for exactly this."""
    doc, c = _two_abutting(app)
    before = ([tuple(p) for p in doc._session["rooms"][0]["poly"]],
              [tuple(p) for p in doc._session["rooms"][1]["poly"]])
    depth = len(doc._history)

    c.press_world(0, -800)
    c.drag_world(-200, -1100)
    c.release_world(-200, -1100, travel_px=99)
    doc.judge_now(sync=True)
    assert len(doc._history) == depth + 1, (
        f"a welded drag pushed {len(doc._history) - depth} undo entries, not 1")

    doc.on_undo()
    doc.judge_now(sync=True)
    after = ([tuple(p) for p in doc._session["rooms"][0]["poly"]],
             [tuple(p) for p in doc._session["rooms"][1]["poly"]])
    assert after == before, "one undo did not restore BOTH sides of the weld"


def test_a_lone_corner_still_emits_the_singular_signal(app):
    """The batched signal is additive: an ordinary un-welded corner drag must be unchanged, because
    every other fence and the whole snap-back guard ride `room_reshaped`."""
    doc, c = _two_abutting(app)
    single, batched = [], []
    c.room_reshaped.connect(lambda ri, poly: single.append(ri))
    c.rooms_reshaped.connect(lambda pairs: batched.append(pairs))

    c.press_world(-1200, -800)               # ROOM1's far corner: nothing is stacked on it
    assert not (c._drag.get("also") or []), "fixture: this corner should not be welded"
    c.drag_world(-1400, -900)
    c.release_world(-1400, -900, travel_px=99)
    assert single == [0] and not batched


def test_dragging_a_room_bodily_still_separates_a_weld(app):
    """The escape hatch, and the honest limit of welding: corners snapped together can no longer be
    pulled apart one at a time, so the way out has to be a whole-room drag. If this stops working
    an author can weld two rooms and never un-weld them."""
    doc, c = _two_abutting(app)
    ri = c._pick_room(600, 0)                       # inside ROOM2, away from any handle
    assert ri == 1, f"fixture: expected to grab ROOM2, got {ri}"
    c.press_world(600, 0)
    assert c._drag["kind"] == "room"
    c.drag_world(1400, 0)
    c.release_world(1400, 0, travel_px=99)
    doc.judge_now(sync=True)
    r = doc._session["rooms"]
    assert tuple(r[0]["poly"][1]) != tuple(r[1]["poly"][0]), "the rooms did not come apart"


# ---------------------------------------------------------- step 4: the band warning's reach

def test_the_band_warning_does_not_fire_on_an_ordinary_dungeon(app):
    """★ "on Step 4, i got this warning when placing the door between 2 aligned edges."

    The gap this warning measures is (the room's extent perpendicular to the door wall) / 2 minus
    the strip depth -- so the old 4*R_WALK = 320u reach warned about EVERY room under ~1140u
    across. The first real two-room dungeon anyone drew got two of them, at 183u and 244u, with
    nothing whatever wrong with it. A warning that fires on the ordinary case hides the one that
    matters. The reach is now the player's own DIAMETER: inside it, one body-length of involuntary
    displacement bridges the gap, which is what the message claims."""
    plan = {"name": "T", "id_base": 30500,
            "rooms": [{"name": "A", "poly": [[0, 0], [1000, 0], [1000, 900], [0, 900]]},
                      {"name": "B", "poly": [[1000, 0], [2000, 0], [2000, 900], [1000, 900]]}],
            "doors": [{"a": "A", "b": "B", "seg": [[1000, 200], [1000, 700]]}]}
    c = FP.compose(plan)
    band = [w for w in c.warnings if "band" in w]
    assert not band, f"an ordinary two-room dungeon warned: {band}"


def test_the_band_warning_still_catches_a_spawn_a_step_from_a_trigger(app):
    """...and it must still fire when the claim is TRUE. Never widen the reach to silence a real
    finding: if a spawn really is a step from a trigger, the answer is to move the spawn."""
    zone = [(0, 0), (400, 0), (400, 200), (0, 200)]
    for gap, want in ((10.0, True), (100.0, True), (400.0, False)):
        out = FP.band_warnings((200.0, 200.0 + gap), [{"zone": zone, "label": "a door"}])
        assert bool(out) is want, f"gap {gap}u: expected warn={want}, got {out}"


def test_the_band_reach_is_the_players_own_diameter(app):
    """A tripwire on the number itself. It is 2 * R_WALK for a stated reason -- one body-length of
    displacement -- not a value tuned until the noise stopped. If someone re-tunes it, this says so
    out loud and points at why 320 was wrong."""
    assert FP.BAND_REACH == 2 * FP.R_WALK, (
        f"BAND_REACH is {FP.BAND_REACH}, not 2*R_WALK={2 * FP.R_WALK}. The old 4*R_WALK warned "
        f"about every room under ~1140u across; widen it again and the gate goes back to noise.")
