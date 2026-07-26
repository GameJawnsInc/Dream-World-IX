"""Fences for the Behavior tab (:mod:`ff9mapkit.workspace.behaviordoc`) -- rung A, read-only.

This file OWNS the synthetic demo field (kit-authored TOML, zero Square-Enix bytes):
``FIELD_TOML`` / :func:`demo_raw` / :func:`make_behavior_field` -- ``tools/gui_snap.py``'s
``behavior:*`` surfaces load them by path (the script-tree fixture pattern), so the surface
renders in a template-less worktree.

Laws fenced here: construction and the shell feed touch NO files (the startup-spend law --
the one disk lane is the user's own Compile click, tripwired); the doc renders an INVALID
document rather than refusing (lenient projections + the compiler's own words in Problems);
a field switch drops the previous field's compile report (a stale instrument is worse than
none); the shell call sites SPEND retheme/set_scale/_feed_behavior (the call-site law, fenced
at source level). Widths are never asserted -- offscreen lies about width."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="GUI extra not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton        # noqa: E402

from ff9mapkit.editor.theme import pick_palette                                # noqa: E402
from ff9mapkit.workspace import behaviorscan                                   # noqa: E402
from ff9mapkit.workspace.behaviordoc import BehaviorDoc, LadderView, StageCanvas   # noqa: E402

# --------------------------------------------------------------------------- the demo field
# A synthetic novel field exercising most of the [behavior] vocabulary rung A renders: a
# 6-branch watchman (announce+once+raise / swing / chase / patrol-marker fallback), a wander
# raider with a die-counter, a POOLED porter (+ its priced [[behavior.pool]] row), timer,
# counters, a table + schedule, a scan, and a public flag. Kit-authored; compiles through the
# real compiler (test_the_demo_field_dry_compiles pins that, so every consumer can trust it).
FIELD_TOML = """\
[field]
name = "BGLADE"
id = 30991

[player]
spawn = [500, -200]

[walkmesh]
bgi = "walkmesh.bgi"

[[npc]]
name = "watchman"
pos = [620, 170]

[[npc]]
name = "raider"
pos = [80, 80]

[[npc]]
name = "porter"
pos = [300, 420]

[[marker]]
name = "ring"
path = [[500, 140], [690, 115], [710, 215], [520, 230]]
closed = true

[[marker]]
name = "market"
pos = [150, 120]

[[marker]]
name = "east_nook"
pos = [820, 230]

[behavior]
timer = 180
counters = ["wave", "kills", "at_shrine"]
public_flags = ["hire"]

[[behavior.table]]
name = "sched"
values = [170, 90, 60]

[[behavior.schedule]]
counter = "wave"
table = "sched"

[[behavior.scan]]
name = "shrine"
units = ["watchman", "raider"]
point = [155, 190]
radius = 300
count = "at_shrine"

[[behavior.pool]]
name = "recruits"
price = 300

[[behavior.unit]]
npc = "watchman"
hp = 4

  [[behavior.unit.branch]]
  when = [{ hp_le = 0 }]
  do = { die = true }

  [[behavior.unit.branch]]
  when = [{ hp_le = 1 }]
  do = { flee = "raider", to = ["market", "east_nook"], speed = 75 }

  [[behavior.unit.branch]]
  when = [{ active = "raider" }, { near = ["raider", 450] }]
  do = { announce = "Raiders at the gate!" }
  once = "cry"
  raise_flags = ["alarm"]

  [[behavior.unit.branch]]
  when = [{ active = "raider" }, { near = ["raider", 300] }]
  do = { swing_at = "raider", damage = 1, interval = 25 }

  [[behavior.unit.branch]]
  when = [{ active = "raider" }, { near = ["raider", 900] }]
  do = { chase = "raider", standoff = 180, speed = 65 }

  [[behavior.unit.branch]]
  do = { patrol = "ring" }

[[behavior.unit]]
npc = "raider"
hp = 5

  [[behavior.unit.branch]]
  when = [{ hp_le = 0 }]
  do = { die = "kills" }

  [[behavior.unit.branch]]
  do = { wander = [80, 80], radius = 250 }

[[behavior.unit]]
npc = "porter"
hp = 3
pooled = true
pool = "recruits"

  [[behavior.unit.branch]]
  when = [{ hp_le = 0 }]
  do = { die = true }

  [[behavior.unit.branch]]
  do = { hold_post = true }
"""


def demo_raw() -> dict:
    return tomllib.loads(FIELD_TOML)


def stage_mesh_bytes() -> bytes:
    """The demo field's synthetic walkmesh (kit-built, zero SE bytes): the BGLADE floor
    x[-300,1000] · z[-300,600] with a notch x(640,680) reaching down from the back edge
    to z=60 — it cuts the patrol ring's legs, so the rung-C sweep lane has REAL jams to
    name (the pursuit suite's u_mesh pattern, resized to this field)."""
    from ff9mapkit.scene import bgi
    xs = (-300, 640, 680, 1000)
    verts = [(x, 0, z) for z in (600, 60, -300) for x in xs]
    tris = [(0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
            (4, 5, 9), (4, 9, 8), (5, 6, 10), (5, 10, 9), (6, 7, 11), (6, 11, 10)]
    return bgi.build(verts, tris).to_bytes()


def make_behavior_field(root: Path) -> Path:
    """Write the demo field.toml (+ its walkmesh sidecar) under ``root`` and return its
    path (gui_snap's builder). The sidecar makes the sweep lane real end-to-end."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "walkmesh.bgi").write_bytes(stage_mesh_bytes())
    p = root / "field.toml"
    p.write_text(FIELD_TOML, encoding="utf-8")
    return p


# --------------------------------------------------------------------------- harness
@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def doc(app):
    d = BehaviorDoc(pick_palette("mist"))
    yield d
    d.deleteLater()


def _labels(widget):
    return [w.text() for w in widget.findChildren(QLabel)]


def _ladder_rows(ladder: LadderView):
    """The ladder's row frames (widgets.card() => QFrame with role='card'), top to bottom."""
    return [w for w in ladder.findChildren(QFrame)
            if w.property("role") == "card" and w.parent() is ladder]


def _scene_tags(canvas: StageCanvas):
    return [it.data(0) for it in canvas._scene.items() if it.data(0)]


# --------------------------------------------------------------------------- the fixture itself
def test_the_demo_field_dry_compiles(tmp_path):
    """The fixture must stay REAL: every consumer (doc tests, gui_snap) trusts that this field
    goes through the actual compiler. A vocabulary change that breaks it should fail HERE."""
    res = behaviorscan.dry_compile(make_behavior_field(tmp_path))
    assert res.ok, res.problems
    assert "blackboard" in res.report
    assert res.new_bytes and res.new_bytes > 0
    assert len(res.stable_hash) == 16
    assert ("hire", res.public_flags[0][1]) in res.public_flags
    assert any(name == "recruits" for name, _idx in res.pool_flags)
    assert res.size_rows and all(n > 0 for _nm, n in res.size_rows)


def test_dry_compile_without_behavior_is_a_problem_not_a_crash(tmp_path):
    p = tmp_path / "field.toml"
    p.write_text('[field]\nname = "EMPTY"\nid = 30992\n', encoding="utf-8")
    res = behaviorscan.dry_compile(p)
    assert not res.ok
    assert any("no [behavior] table" in x for x in res.problems)


# --------------------------------------------------------------------------- construction laws
def test_construction_and_feed_touch_no_files(doc, monkeypatch):
    """The startup-spend law: building the doc and feeding it the OPEN dict must never reach
    a disk lane (dry_compile / load_walkmesh). The tripwires fail the test if anything
    spends one uninvited."""
    def boom(_p):                                  # pragma: no cover - the fence itself
        raise AssertionError("a disk lane spent outside the user's own click")
    monkeypatch.setattr(behaviorscan, "dry_compile", boom)
    monkeypatch.setattr(behaviorscan, "load_walkmesh", boom)
    doc.show_field("BGLADE", demo_raw(), Path("unused.toml"))
    doc.edit_btn.setChecked(True)                  # stage-edit handles are pure projections too
    assert doc._stack.currentWidget() is doc._content


def test_no_field_and_no_behavior_show_teaching_guides(doc):
    doc.show_none()
    assert doc._stack.currentWidget() is doc._guide_page
    assert any("[behavior]" in t for t in _labels(doc._guide_page))
    doc.show_field("PLAIN", {"field": {"name": "PLAIN"}}, None)
    assert doc._stack.currentWidget() is doc._guide_page
    assert any("no [behavior] block" in t for t in _labels(doc._guide_page))


# --------------------------------------------------------------------------- the projections
def test_the_ladder_renders_every_branch_with_the_fallback_labeled(doc):
    doc.show_field("BGLADE", demo_raw(), None)
    rows = _ladder_rows(doc.ladder)
    assert len(rows) == 6                          # the watchman is the first unit -> selected
    texts = _labels(doc.ladder)
    assert "chase" in texts and "patrol" in texts
    assert any(t.startswith("near raider 900") for t in texts)
    assert any("once cry" in t for t in texts)     # decorator chips render
    assert any("raise alarm" in t for t in texts)
    assert any("fallback" in t for t in texts)     # the pinned last row says what it is
    assert any(t == "always" for t in texts)       # an unconditional guard reads as such
    # the row speaks to a screen reader as a sentence, not a soup
    assert any("then chase" in (r.accessibleName() or "") for r in rows)


def test_the_cast_lists_units_groups_pools_and_data(doc):
    doc.show_field("BGLADE", demo_raw(), None)
    tops = [doc.cast.topLevelItem(i).text(0) for i in range(doc.cast.topLevelItemCount())]
    assert tops[0] == "UNITS" and "POOLS" in tops and "DATA" in tops
    units_it = doc.cast.topLevelItem(0)
    names = [units_it.child(i).text(0) for i in range(units_it.childCount())]
    assert len(names) == 3
    assert any("porter" in n and "pooled" in n for n in names)
    sel = doc.cast.selectedItems()
    assert sel and sel[0].data(0, 0x0100) == ("unit", "watchman")   # Qt.UserRole


def test_selecting_a_unit_switches_the_ladder_and_the_stage(doc):
    doc.show_field("BGLADE", demo_raw(), None)
    units_it = doc.cast.topLevelItem(0)
    raider_item = next(units_it.child(i) for i in range(units_it.childCount())
                       if units_it.child(i).text(0).startswith("raider"))
    doc.cast.setCurrentItem(raider_item)
    assert doc._selected_unit == "raider"
    assert doc.canvas._selected == "raider"
    assert len(_ladder_rows(doc.ladder)) == 2


def test_the_stage_draws_posts_routes_refuges_and_only_the_selected_rings(doc):
    doc.show_field("BGLADE", demo_raw(), None)
    tags = _scene_tags(doc.canvas)
    assert tags.count("post") == 3                 # every unit has a positioned npc
    assert tags.count("route") >= 4                # the patrol ring's legs (closed -> wrap leg)
    assert tags.count("refuge") == 2               # both flee refuges, priority-numbered
    assert tags.count("player") == 1
    assert tags.count("wander") == 1 and tags.count("scan") == 1
    # rings belong to the SELECTION: the watchman holds 3 near radii (450/300/900)
    assert tags.count("ring") == 3
    doc.canvas.select_unit("porter")
    assert _scene_tags(doc.canvas).count("ring") == 0


def test_an_invalid_document_still_renders_with_the_compilers_words(doc):
    raw = demo_raw()
    raw["behavior"]["scan"][0]["count"] = "nope"   # not a declared counter
    doc.show_field("BGLADE", raw, None)
    assert doc._stack.currentWidget() is doc._content   # lenient: the view never refuses
    assert "not in [behavior] counters" in doc.problems_lbl.text()
    assert doc.problems_lbl.property("state") == "error"
    assert len(_ladder_rows(doc.ladder)) == 6      # the ladder still shows every branch


# --------------------------------------------------------------------------- the compile lane
def test_compile_now_sync_fills_the_instruments(doc, tmp_path):
    p = make_behavior_field(tmp_path)
    doc.show_field("BGLADE", demo_raw(), p)
    doc.compile_now(sync=True)
    # judged against the INSTRUMENTS column (the shell docks it into its inspector; it is
    # deliberately NOT a child of the doc) -- bare isVisible lies under a hidden ancestor
    assert doc.report_box.isVisibleTo(doc.instruments)
    text = doc.report_box.toPlainText()
    assert "blackboard" in text and "byte histogram" in text
    assert "Compiles" in doc.compile_note.text()
    flag_rows = _labels(doc.flags_host)
    assert any(t.startswith("hire →") for t in flag_rows)
    assert any(t.startswith("recruits →") for t in flag_rows)
    assert doc.flags_host.findChildren(QPushButton)   # the copy affordance exists per row


def test_compile_without_a_saved_path_teaches_instead_of_failing(doc):
    doc.show_field("BGLADE", demo_raw(), None)
    doc.compile_now(sync=True)
    assert "save it first" in doc.compile_note.text()
    assert not doc.report_box.isVisibleTo(doc.instruments)


def test_a_field_switch_drops_the_stale_report(doc, tmp_path):
    p = make_behavior_field(tmp_path)
    doc.show_field("BGLADE", demo_raw(), p)
    doc.compile_now(sync=True)
    assert doc.report_box.isVisibleTo(doc.instruments) and doc._has_result()
    doc.show_field("OTHER", demo_raw(), None)      # a different member, same shape
    assert not doc.report_box.isVisibleTo(doc.instruments)   # no lingering numbers
    assert not doc._has_result()
    assert "Nothing compiled yet" in doc.compile_note.text()


def test_a_dirty_doc_names_which_truth_the_compile_read(doc, tmp_path):
    p = make_behavior_field(tmp_path)
    doc.show_field("BGLADE", demo_raw(), p, dirty=True)
    assert "unsaved edits" in doc.compile_note.text().lower() or \
           "unsaved" in doc.compile_note.text()
    doc.compile_now(sync=True)
    assert "SAVED file" in doc.compile_note.text()


# --------------------------------------------------------------------------- rung B: the edits
@pytest.fixture()
def edoc(app):
    """An editable doc + its on_edit spy (the shell seam): [(member, label), ...]."""
    edits = []
    d = BehaviorDoc(pick_palette("mist"), on_edit=lambda m, lab: edits.append((m, lab)))
    d._edits = edits
    yield d
    d.deleteLater()


def test_edit_apply_writes_the_open_dict_and_hands_the_shell_one_step(edoc):
    raw = demo_raw()
    edoc.show_field("BGLADE", raw, None)
    edoc._edit_branch(4)                           # the watchman's chase row
    assert edoc.editor.isVisibleTo(edoc) and "chase" in edoc.editor.box.toPlainText()
    edoc.editor.box.setPlainText(
        'when = [{ active = "raider" }, { near = ["raider", 700] }]\n'
        'do = { chase = "raider", standoff = 200, speed = 65 }\n')
    edoc._apply_branch()
    br = raw["behavior"]["unit"][0]["branch"][4]
    assert br["do"]["standoff"] == 200 and br["when"][1] == {"near": ["raider", 700]}
    assert edoc._edits == [("BGLADE", "edit watchman branch 5")]
    texts = _labels(edoc.ladder)
    assert any("standoff 200" in t for t in texts)  # the ladder re-rendered the committed edit


def test_apply_refuses_bad_toml_with_the_reason(edoc):
    raw = demo_raw()
    edoc.show_field("BGLADE", raw, None)
    edoc._edit_branch(0)
    edoc.editor.box.setPlainText("when = [")
    edoc._apply_branch()
    assert "not valid TOML" in edoc.editor.note.text()
    assert edoc._edits == []                       # a refused apply is not an undo step
    assert raw["behavior"]["unit"][0]["branch"][0]["do"] == {"die": True}


def test_live_check_speaks_parse_then_validate_then_ok(edoc):
    edoc.show_field("BGLADE", demo_raw(), None)
    edoc._edit_branch(0)
    _b, note, state = edoc._check_branch("do = {")
    assert state == "error" and "not valid TOML" in note
    _b, note, state = edoc._check_branch('do = { patrol = "ghost" }')
    assert state == "warn" and "ghost" in note     # validate's own words on the applied copy
    _b, note, state = edoc._check_branch('when = [{ hp_le = 0 }]\ndo = { die = true }')
    assert state == "" and "Apply" in note


def test_move_delete_add_branch_go_through_the_shell_contract(edoc):
    raw = demo_raw()
    edoc.show_field("BGLADE", raw, None)
    edoc._move_row(0, +1)
    br = raw["behavior"]["unit"][0]["branch"]
    assert br[1]["do"] == {"die": True}
    edoc._delete_row(1)
    assert len(br) == 5 and not any(b["do"] == {"die": True} for b in br)
    edoc._add_branch()                             # lands above the fallback + opens the editor
    assert br[-2]["when"] == [{"flag": "never"}]
    assert edoc.editor.isVisibleTo(edoc)
    assert [lab for _m, lab in edoc._edits] == [
        "reorder watchman branches", "delete watchman branch 2", "add watchman branch"]


def test_add_unit_through_the_seam_and_remove_back_to_guide(edoc):
    raw = {"field": {"name": "PLAIN"},
           "npc": [{"name": "lone", "pos": [10, 20]}]}
    edoc.show_field("PLAIN", raw, None)
    assert edoc._stack.currentWidget() is edoc._guide_page   # no [behavior] yet
    edoc._ask_unit = lambda names: names[0]        # the modal seam -- never the real dialog
    edoc._add_unit()                               # the guide's own action button calls this
    assert edoc._stack.currentWidget() is edoc._content
    assert raw["behavior"]["unit"][0]["npc"] == "lone"
    assert behaviorscan.validate_problems(raw) == []   # the seeded unit is legal
    edoc._remove_unit()
    assert not behaviorscan.has_behavior(raw)
    assert edoc._stack.currentWidget() is edoc._guide_page   # back to the teaching guide
    assert [lab for _m, lab in edoc._edits] == [
        "add behavior unit lone", "remove behavior unit lone"]


def test_row_clears_hide_before_reparenting(app, edoc):
    """The phantom-window class (playtest-caught): clearing ladder rows reparented VISIBLE
    widgets to None, and each flashed as its own native OS window before deleteLater -- a
    reorder sprayed 'pythonw' windows across the screen. The checkable contract is the ORDER
    (hide, THEN reparent): ``isVisible`` is blind to the native flash -- probed offscreen,
    Qt reports False after setParent(None) in the buggy order too -- so this fence records
    the calls per row instead of trusting the property."""
    edoc.show_field("BGLADE", demo_raw(), None)
    edoc.show()                                    # rows must be genuinely visible to regress
    old_rows = _ladder_rows(edoc.ladder)
    calls = []

    def tap(w):
        oh, osp = w.hide, w.setParent
        w.hide = lambda: (calls.append((id(w), "hide")), oh())
        w.setParent = lambda p: (calls.append((id(w), "setParent")), osp(p))

    for w in old_rows:
        tap(w)
    edoc._move_row(0, +1)
    for w in old_rows:
        seq = [k for i, k in calls if i == id(w)]
        assert seq[:1] == ["hide"] and "setParent" in seq, seq
    edoc.hide()


def test_structural_ops_close_the_editor_first(edoc):
    edoc.show_field("BGLADE", demo_raw(), None)
    edoc._edit_branch(2)
    assert edoc.editor.isVisibleTo(edoc)
    edoc._move_row(2, +1)                          # indices shift -> a stale editor would write
    assert not edoc.editor.isVisibleTo(edoc)       # into the wrong row


# --------------------------------------------------------------------------- rung C: the stage authors
def test_stage_edit_toggle_grows_handles_grips_and_the_compass(edoc):
    raw = demo_raw()
    edoc.show_field("BGLADE", raw, None)
    assert _scene_tags(edoc.canvas).count("handle") == 0
    edoc.edit_btn.setChecked(True)
    tags = _scene_tags(edoc.canvas)
    assert tags.count("handle") == len(behaviorscan.stage_handles(raw))
    assert tags.count("ringgrip") == 3             # the selected watchman's three near rings
    assert edoc.canvas._compass.isVisibleTo(edoc.canvas)
    edoc.edit_btn.setChecked(False)
    assert _scene_tags(edoc.canvas).count("handle") == 0
    assert not edoc.canvas._compass.isVisibleTo(edoc.canvas)


def _handle_index(canvas, hid):
    return next(i for i, r in enumerate(canvas._move_items) if r["handle"]["id"] == hid)


def test_a_post_drag_commits_one_step_and_shows_the_guides(edoc):
    raw = demo_raw()
    edoc.show_field("BGLADE", raw, None)
    edoc.edit_btn.setChecked(True)
    i = _handle_index(edoc.canvas, ("pos", "watchman"))
    assert edoc.canvas._begin_drag(("handle", i))
    assert edoc.canvas._drag["spacing"] is not None    # the ~192u jam-spacing ring rides along
    assert edoc.canvas._coords.isVisibleTo(edoc.canvas)
    edoc.canvas._drag_world(640, 210)
    assert "640" in edoc.canvas._coords.text()
    edoc.canvas._end_drag()
    assert raw["npc"][0]["pos"] == [640, 210]
    assert edoc._edits == [("BGLADE", "move watchman")]
    assert not edoc.canvas._coords.isVisibleTo(edoc.canvas)


def test_a_drag_dropped_in_place_commits_nothing(edoc):
    raw = demo_raw()
    edoc.show_field("BGLADE", raw, None)
    edoc.edit_btn.setChecked(True)
    edoc.canvas._begin_drag(("handle", _handle_index(edoc.canvas, ("pos", "watchman"))))
    edoc.canvas._end_drag()                        # no movement -> no write, no undo step
    assert edoc._edits == [] and raw["npc"][0]["pos"] == [620, 170]


def test_a_ring_grip_drag_writes_that_conds_radius(edoc):
    raw = demo_raw()
    edoc.show_field("BGLADE", raw, None)
    edoc.edit_btn.setChecked(True)
    g = edoc.canvas._grip_items[0]
    assert edoc.canvas._begin_drag(("grip", 0))
    edoc.canvas._drag_world(g["cx"] + 512, g["cz"])
    assert "512" in edoc.canvas._coords.text()
    edoc.canvas._end_drag()
    _r, ui, bi, ci, verb = g["rid"]
    assert raw["behavior"]["unit"][ui]["branch"][bi]["when"][ci][verb][1] == 512
    assert edoc._edits and "512" in edoc._edits[0][1]


def test_route_point_ops_ride_the_undo_contract_and_the_floor_refuses(edoc):
    raw = demo_raw()
    edoc.show_field("BGLADE", raw, None)
    edoc._on_stage_insert(("path", "ring", 0))     # midpoint of the first leg, ready to drag
    assert len(raw["marker"][0]["path"]) == 5
    for _ in range(3):
        edoc._on_stage_delete(("path", "ring", 0))
    assert len(raw["marker"][0]["path"]) == 2
    steps = len(edoc._edits)
    edoc._on_stage_delete(("path", "ring", 0))     # the 2-point floor
    assert len(raw["marker"][0]["path"]) == 2
    assert len(edoc._edits) == steps               # a refusal is not an undo step
    assert "at least 2 points" in edoc.problems_lbl.text()
    assert edoc.problems_lbl.property("state") == "warn"


# --------------------------------------------------------------------------- rung D: archetype stamps
def test_stamp_flow_rides_both_seams_and_the_undo_contract(edoc):
    raw = {"field": {"name": "PLAIN"}, "player": {"spawn": [0, 0]},
           "npc": [{"name": "lone", "pos": [10, 20]}]}
    edoc.show_field("PLAIN", raw, None)
    assert edoc._stack.currentWidget() is edoc._guide_page   # no [behavior] yet
    edoc._ask_archetype = lambda: "sentry"         # both modal seams injected, never a dialog
    edoc._ask_unit = lambda names: names[0]
    edoc._stamp_archetype()                        # the guide's own action button calls this
    assert edoc._stack.currentWidget() is edoc._content
    assert edoc._selected_unit == "lone"
    assert raw["behavior"]["unit"][0]["npc"] == "lone"
    assert any(m["name"] == "lone_beat" for m in raw["marker"])   # the minted beat
    assert behaviorscan.validate_problems(raw) == []
    assert edoc._edits == [("PLAIN", "stamp sentry archetype on lone")]


def test_stamp_with_no_free_npc_teaches(edoc):
    edoc.show_field("BGLADE", demo_raw(), None)    # every demo npc already has a unit
    edoc._ask_archetype = lambda: "sentry"
    edoc._stamp_archetype()
    assert "add\nan [[npc]] first" in edoc.problems_lbl.text() or \
           "add an [[npc]] first" in edoc.problems_lbl.text()
    assert edoc._edits == []


def test_a_cancelled_picker_stamps_nothing(edoc):
    raw = {"field": {"name": "PLAIN"}, "npc": [{"name": "lone", "pos": [1, 2]}]}
    edoc.show_field("PLAIN", raw, None)
    edoc._ask_archetype = lambda: None             # user pressed Escape
    edoc._ask_unit = lambda names: names[0]
    edoc._stamp_archetype()
    assert "behavior" not in raw and edoc._edits == []


def test_guard_stamp_flow_binds_a_target_through_the_third_seam(edoc):
    raw = {"field": {"name": "PLAIN"}, "player": {"spawn": [0, 0]},
           "npc": [{"name": "brute", "pos": [10, 20]}, {"name": "hero", "pos": [90, 20]}]}
    edoc.show_field("PLAIN", raw, None)
    edoc._ask_archetype = lambda: "guard"
    edoc._ask_unit = lambda names: "hero"
    asked = []
    edoc._ask_target = lambda units: (asked.append(list(units)), "brute")[1]
    edoc._ask_archetype2 = None
    # no unit exists yet -> the guard needs its enemy seated first
    edoc._stamp_archetype()
    assert "seat its enemy first" in edoc.problems_lbl.text()
    behaviorscan.add_unit(raw, "brute")
    edoc.show_field("PLAIN", raw, None)
    edoc._stamp_archetype()
    assert asked == [["brute"]]
    assert raw["behavior"]["unit"][1]["npc"] == "hero"
    assert behaviorscan.validate_problems(raw) == []
    assert edoc._edits[-1] == ("PLAIN", "stamp guard archetype on hero vs brute")


def test_a_siege_field_renders_its_generated_behavior_read_only(edoc):
    import importlib.util
    from ff9mapkit.workspace import behaviorscan as BS
    p = (Path(__file__).resolve().parents[1] / "ff9mapkit" / "tests" / "test_siege.py")
    spec = importlib.util.spec_from_file_location("_siege_fixture", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    import copy
    raw = {"field": {"name": "REDOUBT", "id": 30991}, "player": {"spawn": [0, -600]},
           "siege": copy.deepcopy(mod.RAW)}
    edoc.show_field("REDOUBT", raw, None)
    assert edoc._stack.currentWidget() is edoc._content      # NOT the no-behavior guide
    assert edoc._readonly and edoc._view is not raw
    assert "read-only" in edoc.head_sum.text()
    assert not edoc.add_unit_btn.isEnabled() and not edoc.edit_btn.isEnabled()
    rows = _ladder_rows(edoc.ladder)
    assert rows and not any(w for r in rows for w in r.findChildren(QPushButton))
    assert "behavior" not in raw                             # rendering wrote NOTHING
    edoc._stamp_archetype()                                  # the programmatic doors refuse
    edoc._add_unit()
    assert "behavior" not in raw and edoc._edits == []
    edoc.show_field("BGLADE", demo_raw(), None)              # a normal field re-arms editing
    assert not edoc._readonly and edoc.add_unit_btn.isEnabled()
    assert BS.has_behavior(edoc._view)


# --------------------------------------------------------------------------- rung C: the sweep lane
def test_sweep_sync_paints_verdicts_and_arms_the_resweep(edoc, tmp_path):
    p = make_behavior_field(tmp_path)
    edoc.show_field("BGLADE", demo_raw(), p)
    edoc.sweep_now(sync=True)
    assert edoc._sweep_armed and edoc._wmesh is not None
    tags = _scene_tags(edoc.canvas)
    assert tags.count("jam") >= 2                  # the notch cuts the ring: line + marker each
    assert tags.count("pursuit") >= 2              # the chase family's worst pairs
    assert "jam" in edoc.sweep_note.text()
    assert edoc.sweep_note.property("state") == "error"
    edoc._move_row(2, +1)                          # an armed edit re-judges, debounced
    assert edoc._resweep_timer.isActive()


def test_sweep_without_a_saved_path_teaches(edoc):
    edoc.show_field("BGLADE", demo_raw(), None)
    edoc.sweep_now(sync=True)
    assert "save first" in edoc.sweep_note.text()
    assert not edoc._sweep_armed
    edoc._move_row(0, +1)                          # unarmed edits must NOT start the timer
    assert not edoc._resweep_timer.isActive()


def test_a_field_switch_drops_the_mesh_and_the_painted_verdicts(edoc, tmp_path):
    p = make_behavior_field(tmp_path)
    edoc.show_field("BGLADE", demo_raw(), p)
    edoc.sweep_now(sync=True)
    assert _scene_tags(edoc.canvas).count("jam")
    edoc.show_field("OTHER", demo_raw(), None)
    assert edoc._wmesh is None and not edoc._sweep_armed
    assert _scene_tags(edoc.canvas).count("jam") == 0
    assert edoc.sweep_note.text() == ""


def test_a_stale_sweep_never_paints(edoc, tmp_path):
    """The generation guard: a worker still in flight for the OLD field lands after a
    switch and must be dropped, not painted onto the new one."""
    p = make_behavior_field(tmp_path)
    edoc.show_field("BGLADE", demo_raw(), p)
    stale = behaviorscan.SweepResult(ok=True)
    stale.jams = [{"a": (0, 0), "b": (10, 0), "t0": 0.1, "t1": 0.4,
                   "mid": (2, 0), "span": 40.0, "name": "ghost"}]
    stale.lines = [("error", "ghost jam")]
    edoc._finish_sweep((edoc._sweep_gen - 1, stale, None))
    assert _scene_tags(edoc.canvas).count("jam") == 0
    assert "ghost" not in edoc.sweep_note.text()


def test_the_doc_spends_every_stage_mechanism(doc):
    """The call-site law for the new surface: the canvas callbacks must be the doc's own
    committers, and the toggle/sweep buttons must reach their spenders."""
    assert doc.canvas.on_move == doc._on_stage_move
    assert doc.canvas.on_radius == doc._on_stage_radius
    assert doc.canvas.on_insert == doc._on_stage_insert
    assert doc.canvas.on_delete == doc._on_stage_delete
    src = (Path(__file__).resolve().parents[1] / "ff9mapkit" / "workspace"
           / "behaviordoc.py").read_text(encoding="utf-8")
    for needle in ("edit_btn.toggled.connect(self._toggle_stage_edit)",
                   "self.sweep_btn.clicked.connect(lambda: self.sweep_now())",
                   "self._resweep_timer.start()",
                   "self._reset_sweep()"):
        assert needle in src, f"behaviordoc.py no longer spends {needle!r}"
    assert src.count("self._reset_sweep()") >= 2   # field switch AND project close


# --------------------------------------------------------------------------- dial + theme + call sites
def test_retheme_and_the_text_dial_reach_the_painted_canvas(doc):
    doc.show_field("BGLADE", demo_raw(), None)
    pal = pick_palette("dark")
    doc.retheme(pal)
    assert doc.canvas.pal is pal
    doc.set_scale(150)
    assert doc.canvas._scale == 150


def test_the_shell_spends_every_mechanism_this_doc_exposes():
    """The call-site law, fenced at the source: a BehaviorDoc whose retheme/set_scale/feed
    nobody calls is the study's most-repeated defect class."""
    src = (Path(__file__).resolve().parents[1] / "ff9mapkit" / "workspace" / "shell.py") \
        .read_text(encoding="utf-8")
    for needle in ("behavior_doc.retheme", "behavior_doc.set_scale",
                   "self._feed_behavior()", 'addTab(self.behavior_doc, "Behavior")',
                   "Go to Behavior", "_mount_behavior_instruments(",
                   "on_edit=self._on_behavior_edit",           # rung B: the edit contract...
                   '_checkpoint(member, label, "behavior")',   # ...records ONE undo step
                   'if key == "behavior":'):                   # ...whose undo lands on this tab
        assert needle in src, f"shell.py no longer spends {needle!r}"
    assert src.count("self._feed_behavior()") >= 2   # tab show AND tree select
    assert src.count("_mount_behavior_instruments(") >= 2   # the def AND the tab-change call


def test_the_instruments_column_is_standalone_for_the_inspector_dock(doc):
    """The shell docks doc.instruments into ITS inspector -- so the column must exist, hold
    the compile widgets, and not be seated inside the doc's own splitter."""
    assert doc.instruments.parent() is None
    assert doc.report_box in doc.instruments.findChildren(type(doc.report_box))
    doc.show_none()                                # a closed project resets the docked column
    assert not doc._has_result() and doc.problems_lbl.text() == ""
