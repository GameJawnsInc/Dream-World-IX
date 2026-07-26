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


def make_behavior_field(root: Path) -> Path:
    """Write the demo field.toml under ``root`` and return its path (gui_snap's builder)."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
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
    the one disk lane (dry_compile). The tripwire fails the test if anything spends it."""
    def boom(_p):                                  # pragma: no cover - the fence itself
        raise AssertionError("dry_compile spent outside the user's Compile click")
    monkeypatch.setattr(behaviorscan, "dry_compile", boom)
    doc.show_field("BGLADE", demo_raw(), Path("unused.toml"))
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
                   "Go to Behavior", "_mount_behavior_instruments("):
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
