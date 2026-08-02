"""Fences for the Workspace CUTSCENE tab -- the lane that shipped with none.

The defects these pin were all reproduced on a real ``Workspace`` window before the fix:

  * **THE [[cutscene]] DEADLOCK.** ``_commit`` normalized a plural section to block 0;
    ``_commit_active`` and ``_form_matches_baseline`` did not, so they ran ``list.pop(key, None)``
    -> ``TypeError``. ``_commit_active_ck`` sits on the nav / undo / redo / refresh / Check / save
    boundary, so mounting Cutscene on any ``[[cutscene]]`` field trapped the editor -- silently,
    because there is no excepthook and the entry point is a ``.pyw``. BOTH shipped stolen-ember
    examples tripped it. One owner now: :func:`shell._single_block`.
  * **THE SAME-KIND OVERWRITE.** ``Add / Update`` decided update-vs-append from the step KIND alone
    and then re-selected the row it wrote, so a second consecutive ``say`` replaced the first: three
    lines of dialogue in, one out. Split into ``Add step`` / ``Update selected``.
  * **THE DISPATCH BLINDNESS.** The Inspector and node lint bailed on any non-dict, so every
    per-step check was skipped for a dispatch, and they read the singular ``actor`` key the #13 v3
    redesign REMOVED.

Behaviour + data only -- no geometry or font claim -- so offscreen is sound here.
"""
from __future__ import annotations

import copy
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox,      # noqa: E402
                               QLineEdit, QListWidget, QPlainTextEdit, QPushButton)

from ff9mapkit.editor import forms                                       # noqa: E402
from ff9mapkit.editor.theme import pick_palette                          # noqa: E402
from ff9mapkit.workspace import shell                                    # noqa: E402

_MEMBER = "X"                     # the member key open_field uses is the [field] NAME
# A real walkmesh SIDECAR, not a quad: the staging check resolves the mesh through
# build.behavior_walkmesh, whose no-sidecar branch needs the camera art a fixture has no business
# shipping. The floor is x[-300,1000] z[-300,600] (the behaviour suite's synthetic mesh).
# Positions are spread well past the ~192u character collision radius -- stacked content is itself a
# staging warning ("inside X's collision box"), and a fixture that trips it cannot test anything else.
_HEAD = ('[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
         '[walkmesh]\nbgi = "walkmesh.bgi"\n\n'
         '[player]\nspawn = [-200, 500]\n\n'
         '[[npc]]\nname = "Cid"\nmodel = "GEO_SUB_F0_CID"\npos = [0, 400]\n\n'
         '[[marker]]\nname = "altar"\npos = [900, -200]\n\n')


def _mesh_bytes() -> bytes:
    """A kit-built synthetic floor (zero SE bytes) -- the behaviour suite's stage, reused."""
    from ff9mapkit.scene import bgi
    xs = (-300, 640, 680, 1000)
    verts = [(x, 0, z) for z in (600, 60, -300) for x in xs]
    tris = [(0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
            (4, 5, 9), (4, 9, 8), (5, 6, 10), (5, 10, 9), (6, 7, 11), (6, 11, 10)]
    return bgi.build(verts, tris).to_bytes()

# the SHIPPED shape -- stolen-ember HEARTH carries exactly this: two beat-gated scenes
_PLURAL = (_HEAD +
           '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 100\nset_scenario = 200\n'
           'steps = [ { say = "first scene" } ]\n\n'
           '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 300\nset_scenario = 400\n'
           'steps = [ { say = "second scene" } ]\n')

_SINGLETON = (_HEAD + '[cutscene]\nactors = ["Cid"]\nrequires_scenario = 100\n'
              'steps = [ { say = "only scene" } ]\n')


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app, tmp_path, monkeypatch):
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    w = shell.Workspace(pick_palette("dark"))
    yield w
    w.hide()


def _open(win, tmp_path, toml_text, name="X"):
    p = tmp_path / f"{name}.field.toml"
    p.write_text(toml_text, encoding="utf-8")
    (tmp_path / "walkmesh.bgi").write_bytes(_mesh_bytes())
    win.open_field(p)
    return p


def _mounted(win, tmp_path, toml_text, name="X"):
    p = _open(win, tmp_path, toml_text, name)
    win._goto_tree_section(_MEMBER, "cutscene")
    return p


def _widgets(win):
    """The live step sub-editor widgets, by the accessible names _mount_cutscene sets."""
    host = win.doc_host
    return {
        "combo": next(c for c in host.findChildren(QComboBox)
                      if c.accessibleName() == "Cutscene step type"),
        "value": next(c for c in host.findChildren(QLineEdit)
                      if c.accessibleName() == "Cutscene step value"),
        "text": next(iter(host.findChildren(QPlainTextEdit))),
        "list": next(iter(host.findChildren(QListWidget))),
        "buttons": {b.text(): b for b in host.findChildren(QPushButton)},
    }


# --------------------------------------------------------------- _single_block (the one owner)
def test_single_block_normalizes_both_storage_shapes():
    assert shell._single_block({"cutscene": {"a": 1}}, "cutscene") == {"a": 1}
    assert shell._single_block({"cutscene": [{"a": 1}, {"b": 2}]}, "cutscene") == {"a": 1}
    assert shell._single_block({}, "cutscene") == {}
    assert shell._single_block({"cutscene": []}, "cutscene") == {}


def test_single_block_does_not_materialize_unless_asked():
    """The baseline/compare paths must never dirty the doc by merely LOOKING."""
    d = {}
    assert shell._single_block(d, "cutscene") == {}
    assert d == {}, "a read materialized the section"
    assert shell._single_block(d, "cutscene", create=True) == {}
    assert d == {"cutscene": {}}


def test_single_block_create_seats_block_zero_in_an_empty_list():
    d = {"cutscene": []}
    got = shell._single_block(d, "cutscene", create=True)
    got["actors"] = ["Cid"]
    assert d["cutscene"] == [{"actors": ["Cid"]}], "the write must land IN the list, not beside it"


# --------------------------------------------------------------- THE DEADLOCK
def test_a_singleton_cutscene_navigates_away_cleanly(win, tmp_path):
    """CONTROL: if this ever fails, the harness is wrong, not the plural path."""
    _mounted(win, tmp_path, _SINGLETON)
    assert win._commit_active() is True


def _dirty_the_form(win, key="requires_scenario", value="111"):
    """Type into a mounted form field so the fold ACTUALLY RUNS.

    THE TRAP THIS EXISTS FOR: `_commit_active` returns early at the `"mounted"` baseline check when the
    form is untouched -- a fast path this very sprint ADDED. Tests that mount and commit without typing
    exit there and never reach the plural normalization they claim to fence. Measured by mutation:
    with untouched forms, reverting BOTH `_single_block` call sites left the whole suite green."""
    getter = win._save_ctx["getters"][key]
    getter.__self__.setText(value)          # the bound widget behind the getter
    assert win._save_ctx["mounted"] != shell.read(win._save_ctx["getters"]), \
        "the form is still pristine -- the fold will short-circuit and fence nothing"


def test_a_plural_cutscene_no_longer_traps_the_editor(win, tmp_path):
    """THE REGRESSION: every caller of _commit_active_ck used to raise TypeError from one line.
    The form is DIRTIED first, or the commit short-circuits before reaching the fixed code."""
    _mounted(win, tmp_path, _PLURAL)
    _dirty_the_form(win)
    assert win._commit_active() is True
    _dirty_the_form(win, value="112")
    assert win._commit_active_ck() is True
    win._undo()                       # nav / history boundary -- used to raise
    win._redo()
    assert isinstance(win._form_matches_baseline(win._save_ctx), bool)


def test_form_matches_baseline_survives_a_plural_clean_snapshot(win, tmp_path):
    """The second reverted call site: `_clean[member]["cutscene"]` is a LIST for a dispatch, and
    comparing against it used to raise out of the dirty-dot path."""
    _mounted(win, tmp_path, _PLURAL)
    win._clean[_MEMBER] = copy.deepcopy(win._doc(_MEMBER).data)     # a plural baseline snapshot
    assert win._form_matches_baseline(win._save_ctx) is True        # pristine form == pristine baseline
    _dirty_the_form(win)
    assert win._form_matches_baseline(win._save_ctx) is False


def test_the_plural_fold_writes_into_block_zero_not_beside_it(win, tmp_path):
    """A fold must land in the list's first table -- never replace the list with a dict."""
    _mounted(win, tmp_path, _PLURAL)
    doc = win._doc(_MEMBER)
    _dirty_the_form(win)                       # or the fold never runs
    win._commit_active()
    cs = doc.data["cutscene"]
    assert isinstance(cs, list) and len(cs) == 2, "the dispatch must survive a fold"
    assert cs[0]["requires_scenario"] == 111, "the edit must land IN block 0"
    assert cs[1]["requires_scenario"] == 300, "the second scene must be untouched"


def test_an_untouched_plural_form_short_circuits_the_fold(win, tmp_path):
    """The cutscene _save_ctx carries the at-mount baseline every other form has."""
    _mounted(win, tmp_path, _PLURAL)
    ctx = win._save_ctx
    assert "mounted" in ctx, "no baseline -> the untouched-form fast path can never fire"
    assert ctx["mounted"] == shell.read(ctx["getters"])


# --------------------------------------------------------------- THE SAME-KIND OVERWRITE (Add/Update)
def _type_value(w, kind, text):
    w["combo"].setCurrentIndex(list(forms.STEP_KIND).index(kind))
    (w["text"].setPlainText if kind == "say" else w["value"].setText)(text)


def test_three_consecutive_say_steps_all_survive(win, tmp_path):
    """THE REGRESSION: one overloaded button re-selected the row it wrote, so lines 2 and 3
    overwrote line 1 -- three lines of dialogue in, one out."""
    _mounted(win, tmp_path, _SINGLETON)
    w = _widgets(win)
    for line in ("Cid: Well now.", "Cid: That's torn it.", "Cid: Rubbish!"):
        _type_value(w, "say", line)
        w["buttons"]["Add step"].click()
    said = [s["say"] for s in win._doc(_MEMBER).data["cutscene"]["steps"] if "say" in s]
    assert said == ["only scene", "Cid: Well now.", "Cid: That's torn it.", "Cid: Rubbish!"]


def test_add_step_inserts_after_the_selection_so_you_can_author_into_the_middle(win, tmp_path):
    _mounted(win, tmp_path, _SINGLETON)
    w = _widgets(win)
    for line in ("second", "third"):
        _type_value(w, "say", line)
        w["buttons"]["Add step"].click()
    w["list"].setCurrentRow(0)                       # go back to the top and insert
    _type_value(w, "say", "inserted")
    w["buttons"]["Add step"].click()
    said = [s["say"] for s in win._doc(_MEMBER).data["cutscene"]["steps"]]
    assert said == ["only scene", "inserted", "second", "third"]
    assert w["list"].currentRow() == 1, "the new row must be selected"


def test_update_selected_can_change_a_steps_KIND_in_place(win, tmp_path):
    """The kind-mismatch used to take the append branch: original untouched, stray step at the end."""
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nsteps = [ { wait = 30 } ]\n')
    w = _widgets(win)
    w["list"].setCurrentRow(0)
    _type_value(w, "say", "converted")
    w["buttons"]["Update selected"].click()
    assert win._doc(_MEMBER).data["cutscene"]["steps"] == [{"say": "converted"}]


def test_update_with_nothing_selected_warns_instead_of_silently_appending(win, tmp_path):
    _mounted(win, tmp_path, _SINGLETON)
    w = _widgets(win)
    w["list"].setCurrentRow(-1)
    _type_value(w, "say", "orphan")
    w["buttons"]["Update selected"].click()
    steps = win._doc(_MEMBER).data["cutscene"]["steps"]
    assert steps == [{"say": "only scene"}], "nothing should have been written"


def test_update_preserves_the_keys_the_form_cannot_edit(win, tmp_path):
    """speaker/tail/speed have no widget; a re-save must never strip an attributed line."""
    _mounted(win, tmp_path, _HEAD +
             '[cutscene]\nactors = ["Cid"]\n'
             'steps = [ { say = "hi", speaker = "Cid", tail = "UPR", speed = 20 } ]\n')
    w = _widgets(win)
    w["list"].setCurrentRow(0)
    _type_value(w, "say", "hello")
    w["buttons"]["Update selected"].click()
    st = win._doc(_MEMBER).data["cutscene"]["steps"][0]
    assert st["say"] == "hello"
    assert st["speaker"] == "Cid" and st["tail"] == "UPR" and st["speed"] == 20


def test_duplicate_deep_copies_so_editing_the_copy_leaves_the_original(win, tmp_path):
    _mounted(win, tmp_path, _HEAD +
             '[cutscene]\nactors = ["Cid"]\nsteps = [ { path = [[0,0],[10,10]] } ]\n')
    w = _widgets(win)
    w["list"].setCurrentRow(0)
    w["buttons"]["Duplicate"].click()
    steps = win._doc(_MEMBER).data["cutscene"]["steps"]
    assert len(steps) == 2 and steps[0] == steps[1]
    steps[1]["path"].append([20, 20])
    assert steps[0]["path"] == [[0, 0], [10, 10]], "the duplicate shared the original's list"


def test_step_rows_are_numbered_0_based_like_the_builds_own_lint(win, tmp_path):
    _mounted(win, tmp_path, _SINGLETON)
    assert _widgets(win)["list"].item(0).text().startswith("0")


# --------------------------------------------------------------- with_prev (B2) + wrap preview (B4)
def test_forms_parallel_steps_matches_the_compilers_own_rule():
    """The checkbox must never offer a beat validate() will reject."""
    from ff9mapkit import build
    assert tuple(forms.PARALLEL_STEPS) == tuple(build.PARALLEL_STEP_KINDS)


def _with_prev_box(win):
    return next(c for c in win.doc_host.findChildren(QCheckBox)
                if "parallel" in c.accessibleName())


def test_with_prev_is_writable_and_round_trips(win, tmp_path):
    """It was RENDERED in the step summary and writable by nothing."""
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\nsteps = [ { walk = "altar" } ]\n')
    w, box = _widgets(win), _with_prev_box(win)
    _type_value(w, "walk", "altar")
    w["list"].setCurrentRow(0)
    w["buttons"]["Add step"].click()                 # row 1 -- a parallel beat is legal here
    assert box.isEnabled(), "walk on a non-first row must allow with_prev"
    box.setChecked(True)
    w["buttons"]["Update selected"].click()
    assert win._doc(_MEMBER).data["cutscene"]["steps"][1].get("with_prev") is True
    w["list"].setCurrentRow(0)
    w["list"].setCurrentRow(1)                       # re-select -> the box reflects the stored value
    assert box.isChecked()


def test_with_prev_is_disabled_where_the_compiler_would_reject_it(win, tmp_path):
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\n'
             'steps = [ { walk = "altar" }, { walk = "altar" } ]\n')
    w, box = _widgets(win), _with_prev_box(win)
    w["list"].setCurrentRow(0)
    assert not box.isEnabled(), "step 0 has nothing to run with (build.py rejects it)"
    w["list"].setCurrentRow(1)
    assert box.isEnabled()
    _type_value(w, "say", "a line")                  # a sequential kind on the same row
    assert not box.isEnabled(), "say/wait/set_flag/teleport/face_player are sequential"
    assert not box.isChecked(), "disabling must also clear it, or a hidden true would ship"


def test_a_parallel_beat_the_gui_writes_passes_the_builds_own_validator(win, tmp_path):
    """END TO END: the checkbox must produce a scene validate() accepts."""
    from ff9mapkit import build
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid", "player"]\n'
             'steps = [ { walk = "altar", actor = "Cid" } ]\n')
    w, box = _widgets(win), _with_prev_box(win)
    w["list"].setCurrentRow(0)
    _type_value(w, "walk", "altar")
    w["value"].setText("altar")
    win.doc_host.findChildren(QLineEdit)             # actor line is set below
    next(c for c in win.doc_host.findChildren(QLineEdit)
         if c.accessibleName() == "Cutscene step actor").setText("player")
    w["buttons"]["Add step"].click()
    box.setChecked(True)
    w["buttons"]["Update selected"].click()
    win._commit_active()
    raw = win._doc(_MEMBER).data
    probs = [p for p in build.validate(build.FieldProject(raw, tmp_path)) if "cutscene" in p]
    assert probs == [], f"the GUI wrote a scene the compiler rejects: {probs}"


def _preview_box(win):
    """The wrap preview's read-only pane (the step's own say box is editable)."""
    return next(b for b in win.doc_host.findChildren(QPlainTextEdit) if b.isReadOnly())


def test_the_say_box_has_a_live_wrap_preview(win, tmp_path):
    """FF9 never auto-wraps, so the kit pre-breaks lines -- this is the field where authors type the
    most text and it was the one dialogue field with no preview."""
    from ff9mapkit import dialogue as _dlg
    _mounted(win, tmp_path, _SINGLETON)
    w = _widgets(win)
    long_line = "The hut is silent, and the ember on the hearth has burned down to nothing at all."
    _type_value(w, "say", long_line)
    shown = _preview_box(win).toPlainText()
    assert shown == _dlg.wrap_preview(long_line, win._wrap_width(_MEMBER)), \
        "the preview must use the SAME wrapper the build spends"
    assert "\n" in shown, "a long line must visibly break"


def test_the_wrap_preview_belongs_to_the_dialogue_box_only(win, tmp_path):
    """On a `wait` step a wrap preview would be a pane that cannot answer. (Assert the PANEL, not its
    inner box -- a child of a hidden parent is not itself `isHidden`.)"""
    _mounted(win, tmp_path, _SINGLETON)
    w = _widgets(win)
    panel = _preview_box(win).parent()
    _type_value(w, "say", "hello")
    assert not panel.isHidden()
    _type_value(w, "wait", "30")
    assert panel.isHidden()
def test_all_blocks_agrees_with_the_builds_own_normalizer():
    """forms.all_blocks is the editor-side twin of content.cutscene.blocks -- they must never drift."""
    from ff9mapkit.content import cutscene as _cs
    for raw in (None, {}, {"steps": []}, [], [{"a": 1}], [{"a": 1}, {"b": 2}], [{"a": 1}, "junk"]):
        assert forms.all_blocks(raw) == _cs.blocks(raw), f"drifted on {raw!r}"


def test_the_inspector_summarizes_every_scene_of_a_dispatch(win, tmp_path):
    _open(win, tmp_path, _PLURAL)
    lines = win._inspect_single("cutscene", win._doc(_MEMBER).data["cutscene"])
    body = " ".join(lines)
    assert "2 scenes" in body
    assert "scene #0" in body and "scene #1" in body
    assert "Cid" in body, "the cast must be named -- it used to read the removed singular `actor`"
    assert "narration" not in body, "a cast scene is not narration"


def test_the_inspector_still_reads_a_singleton(win, tmp_path):
    _open(win, tmp_path, _SINGLETON)
    body = " ".join(win._inspect_single("cutscene", win._doc(_MEMBER).data["cutscene"]))
    assert "1 step" in body and "Cid" in body
    assert "scene #" not in body, "a singleton must not grow scene numbering"


def test_node_lint_checks_every_scene_and_names_which_one(win, tmp_path):
    """A dispatch used to return [] -- every per-step check silently skipped."""
    toml = (_HEAD +
            '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 100\n'
            'steps = [ { walk = "altar" } ]\n\n'
            '[[cutscene]]\nactors = ["Ghost"]\nrequires_scenario = 300\n'
            'steps = [ { walk = "nowhere" } ]\n')
    _open(win, tmp_path, toml)
    probs = win._node_problems("cutscene", win._doc(_MEMBER).data["cutscene"], _MEMBER)
    body = " ".join(probs)
    assert probs, "the dispatch must be linted at all"
    assert "nowhere" in body, "scene #1's bad walk target must be caught"
    assert "scene #1" in body, "the warning must say WHICH scene"
    assert "Ghost" in body, "an undefined cast member must be caught"
    assert "altar" not in body, "the valid marker in scene #0 must not warn"


def test_node_lint_catches_a_step_actor_outside_the_cast(win, tmp_path):
    toml = (_HEAD + '[cutscene]\nactors = ["Cid"]\n'
            'steps = [ { say = "hi", actor = "Typo" } ]\n')
    _open(win, tmp_path, toml)
    body = " ".join(win._node_problems("cutscene", win._doc(_MEMBER).data["cutscene"], _MEMBER))
    assert "Typo" in body


def test_a_clean_dispatch_reports_no_problems(win, tmp_path):
    _open(win, tmp_path, _PLURAL)
    assert win._node_problems("cutscene", win._doc(_MEMBER).data["cutscene"], _MEMBER) == []


def test_the_health_badge_counts_a_broken_dispatch(win, tmp_path):
    """_count_node_problems fed the raw list straight in; the guard used to drop it."""
    toml = (_HEAD + '[[cutscene]]\nactors = ["Nobody"]\nsteps = [ { say = "x" } ]\n')
    _open(win, tmp_path, toml)
    assert win._count_node_problems(_MEMBER) >= 1


# --------------------------------------------------------------- THE STAGING CHECK (B1)
def test_the_staging_checker_is_reachable_from_a_gui_call_site():
    """THE CALL-SITE LAW: build._validate_cutscene_movement predicts the in-game SOFTLOCK and no GUI
    path could reach it. If this import ever goes away the mechanism is orphaned again."""
    from ff9mapkit.workspace import cutscenescan
    assert callable(cutscenescan.check_staging) and callable(cutscenescan.load_walkmesh)


def test_has_cast_scene_ignores_narration():
    from ff9mapkit.workspace import cutscenescan
    assert not cutscenescan.has_cast_scene({"cutscene": {"steps": [{"say": "hi"}]}})
    assert cutscenescan.has_cast_scene({"cutscene": {"actors": ["Cid"], "steps": []}})
    assert cutscenescan.has_cast_scene(
        {"cutscene": [{"steps": []}, {"actors": ["Cid"], "steps": []}]}), "scene #1 has a cast"
    assert not cutscenescan.has_cast_scene({})


def test_staging_check_catches_a_walk_that_would_stall(win, tmp_path):
    """A walk target off the walkmesh softlocks the scene in-game. The panel must SAY so."""
    toml = (_HEAD + '[cutscene]\nactors = ["Cid"]\n'
            'steps = [ { walk = [9000, 9000] } ]\n')          # far outside the 600x600 quad
    _mounted(win, tmp_path, toml)
    win._cs_stage["run"](sync=True)                            # deterministic lane, no thread
    res = win._cs_stage["last"]
    assert res.error == "", res.error
    assert res.warnings, "an off-mesh walk target must be reported"
    assert "stall" in " ".join(res.warnings).lower()
    assert win._cs_stage["list"].count() == len(res.warnings)
    assert not win._cs_stage["list"].isHidden()


def test_staging_check_passes_a_reachable_walk(win, tmp_path):
    toml = (_HEAD + '[cutscene]\nactors = ["Cid"]\nsteps = [ { walk = "altar" } ]\n')
    _mounted(win, tmp_path, toml)
    win._cs_stage["run"](sync=True)
    res = win._cs_stage["last"]
    assert not (res.error or res.warnings or res.skipped), \
        f"a reachable walk must be clean: {res.error or res.warnings or res.skipped}"
    assert "reaches its target" in res.summary()
    assert win._cs_stage["list"].isHidden()


def test_staging_check_says_a_narration_scene_has_nothing_to_stage(win, tmp_path):
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nsteps = [ { say = "alone" } ]\n')
    win._cs_stage["run"](sync=True)
    assert "narration" in win._cs_stage["last"].summary().lower()


def test_staging_warnings_name_which_scene_in_a_dispatch(win, tmp_path):
    """'step 0' is ambiguous across a dispatch -- the build's own labels disambiguate it."""
    toml = (_HEAD +
            '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 100\n'
            'steps = [ { walk = "altar" } ]\n\n'
            '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 300\n'
            'steps = [ { walk = [9000, 9000] } ]\n')
    _mounted(win, tmp_path, toml)
    win._cs_stage["run"](sync=True)
    body = " ".join(win._cs_stage["last"].warnings)
    assert body, "the dispatch must be staged at all"
    assert "#1" in body, f"the warning must name the offending scene: {body}"


def test_the_walkmesh_load_resolves_a_CAMPAIGN_members_named_flags(tmp_path):
    """A campaign member gates on flag NAMES the campaign owns and its own toml never defines. Without
    them the load dies in flag resolution -- reported to the author as "no walkmesh", which is a lie
    about a field whose mesh is fine. Both shipped stolen-ember members are shaped exactly like this."""
    from ff9mapkit.workspace import behaviorscan
    (tmp_path / "walkmesh.bgi").write_bytes(_mesh_bytes())
    p = tmp_path / "M.field.toml"
    p.write_text(_HEAD + '[cutscene]\nactors = ["Cid"]\nrequires_flag = "chapel_open"\n'
                 'steps = [ { walk = "altar" } ]\n', encoding="utf-8")

    mesh, err = behaviorscan.load_walkmesh(p)                      # no names -> the misleading failure
    assert mesh is None and "chapel_open" in err

    mesh, err = behaviorscan.load_walkmesh(p, {"chapel_open": 8824})
    assert mesh is not None, f"the campaign's flag names must unblock the load: {err}"


def test_the_staging_button_passes_the_campaigns_flag_names(win, tmp_path, monkeypatch):
    """THE CALL-SITE LAW: the loader accepting flag_names is worthless if the button sends none."""
    seen = {}
    from ff9mapkit.workspace import cutscenescan
    real = cutscenescan.load_walkmesh
    monkeypatch.setattr(cutscenescan, "load_walkmesh",
                        lambda path, names=None: (seen.setdefault("names", names), real(path, names))[1])
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\nsteps = [ { walk = "altar" } ]\n')
    win._cs_stage["run"](sync=True)
    assert "names" in seen, "the staging check never called the loader"
    assert seen["names"] == {}, "a loose field has no campaign names, but the argument must be PASSED"


def test_up_and_down_move_the_step_the_way_they_are_labelled(win, tmp_path):
    """LAYER-3: swapping move(-1)/move(1) left the suite bit-for-bit green. Nothing asserted ORDER."""
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nsteps = [ { say = "A" }, { say = "B" }, { say = "C" } ]\n')
    w = _widgets(win)
    doc = win._doc(_MEMBER)
    order = lambda: [s["say"] for s in doc.data["cutscene"]["steps"]]        # noqa: E731
    w["list"].setCurrentRow(2)                       # select "C"
    w["buttons"]["Up"].click()
    assert order() == ["A", "C", "B"], "Up must move the selected step EARLIER"
    assert w["list"].currentRow() == 1, "selection follows the moved step"
    w["buttons"]["Down"].click()
    assert order() == ["A", "B", "C"], "Down must move it LATER again"


def test_duplicate_lands_next_to_its_source_and_is_a_deep_copy(win, tmp_path):
    """LAYER-3: Duplicate's insert position had no fence (append passed), nor did the deep copy."""
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\nsteps = [ '
             '{ path = [[0, 100], [0, 200]], actor = "Cid" }, { say = "tail" } ]\n')
    w = _widgets(win)
    steps = win._doc(_MEMBER).data["cutscene"]["steps"]
    w["list"].setCurrentRow(0)
    w["buttons"]["Duplicate"].click()
    assert len(steps) == 3
    assert "path" in steps[1], "the copy must sit directly AFTER its source, not at the end"
    assert "say" in steps[2], "the original tail must be pushed down, not overwritten"
    steps[1]["path"][0][0] = 999                     # mutate the COPY's nested list
    assert steps[0]["path"][0][0] == 0, "Duplicate must deep-copy: the source was aliased"


def test_the_staging_controls_have_accessible_names(win, tmp_path):
    """LAYER-3: deleting both setAccessibleName calls left the suite green -- the a11y sweep never
    reaches this panel, so the only fence is here."""
    _mounted(win, tmp_path, _SINGLETON)
    assert win._cs_stage["btn"].accessibleName(), "the staging button needs an accessible name"
    assert win._cs_stage["list"].accessibleName(), "the staging results list needs an accessible name"


def test_removing_a_cutscene_from_a_dispatch_removes_ONE_SCENE(win, tmp_path, monkeypatch):
    """A4. It used to pop the whole array: three authored scenes destroyed by one click, behind a
    confirm saying "this cutscene", written to disk at once, and Undo restored NOTHING (measured).
    The form edits scene #0, so the delete must remove scene #0."""
    import tomllib
    monkeypatch.setattr(shell.QMessageBox, "question",
                        staticmethod(lambda *a, **k: shell.QMessageBox.StandardButton.Yes))
    p = _mounted(win, tmp_path, _PLURAL)
    assert len(tomllib.loads(p.read_text(encoding="utf-8"))["cutscene"]) == 2
    win._delete_object(_MEMBER, "cutscene", single=True, label="cutscene")
    left = tomllib.loads(p.read_text(encoding="utf-8"))["cutscene"]
    assert len(left) == 1, "only the edited scene may go"
    assert left[0]["requires_scenario"] == 300, "the SURVIVOR must be the second scene"


def test_removing_the_last_scene_leaves_no_bare_section(win, tmp_path, monkeypatch):
    import tomllib
    monkeypatch.setattr(shell.QMessageBox, "question",
                        staticmethod(lambda *a, **k: shell.QMessageBox.StandardButton.Yes))
    p = _mounted(win, tmp_path, _HEAD + '[[cutscene]]\nactors = ["Cid"]\n'
                 'steps = [ { say = "only" } ]\n')
    win._delete_object(_MEMBER, "cutscene", single=True, label="cutscene")
    assert "cutscene" not in tomllib.loads(p.read_text(encoding="utf-8"))


def test_a_singleton_cutscene_delete_still_removes_the_section(win, tmp_path, monkeypatch):
    """CONTROL: the plural fix must not change the singleton's behaviour."""
    import tomllib
    monkeypatch.setattr(shell.QMessageBox, "question",
                        staticmethod(lambda *a, **k: shell.QMessageBox.StandardButton.Yes))
    p = _mounted(win, tmp_path, _SINGLETON)
    win._delete_object(_MEMBER, "cutscene", single=True, label="cutscene")
    assert "cutscene" not in tomllib.loads(p.read_text(encoding="utf-8"))


def test_the_staging_check_sees_a_cast_that_lives_in_the_SCENE_toml(win, tmp_path):
    """The kit's documented split puts positions (and often the cast's NPCs) in the sibling
    scene.toml. Scoring the logic-only doc found no actor, walked nothing, and printed a confident
    all-clear over a walk `ff9mapkit lint` calls a softlock."""
    head = ('[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
            '[walkmesh]\nbgi = "walkmesh.bgi"\n\n[player]\nspawn = [-200, 500]\n\n')
    p = tmp_path / "X.field.toml"
    p.write_text(head + '[cutscene]\nactors = ["Cid"]\nsteps = [ { walk = [9000, 9000] } ]\n',
                 encoding="utf-8")
    (tmp_path / "X.scene.toml").write_text(                  # the cast lives HERE, not in the logic
        '[[npc]]\nname = "Cid"\nmodel = "GEO_SUB_F0_CID"\npos = [0, 400]\n', encoding="utf-8")
    (tmp_path / "walkmesh.bgi").write_bytes(_mesh_bytes())
    win.open_field(p)
    win._goto_tree_section(_MEMBER, "cutscene")
    win._cs_stage["run"](sync=True)
    res = win._cs_stage["last"]
    assert res.warnings, "the off-mesh walk must be caught even though the cast is scene-placed"


def test_a_scene_the_checker_SKIPPED_is_never_reported_as_clean(win, tmp_path):
    """`_validate_cutscene_movement` silently `continue`s past a scene whose names don't resolve.
    A bare tick over unchecked work is the false green this panel exists to prevent."""
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\n'
             'steps = [ { walk = "no_such_marker" } ]\n')
    win._cs_stage["run"](sync=True)
    res = win._cs_stage["last"]
    assert res.skipped, "an unresolvable target must be reported as NOT CHECKED"
    assert "not checked" in res.summary().lower() or "NOT checked" in res.summary()
    assert "reaches its target" not in res.summary(), "never a clean tick over a skipped scene"
    assert not win._cs_stage["list"].isHidden(), "the skipped scene must be listed"


def test_the_staging_BUTTON_is_wired(win, tmp_path):
    """THE CALL-SITE LAW, applied to this sprint's own fence: every other staging test calls
    `_cs_stage["run"]` directly, so deleting the button's clicked.connect left the suite green
    with a dead control shipped."""
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\n'
             'steps = [ { walk = [9000, 9000] } ]\n')
    btn = win._cs_stage["btn"]
    win._cs_stage.pop("last", None)
    btn.click()                                   # the real user gesture (async worker)
    deadline = time.time() + 20
    while "last" not in win._cs_stage and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.02)
    assert "last" in win._cs_stage, "clicking the button produced no result"
    assert win._cs_stage["last"].warnings, "the off-mesh walk should have been caught"


def test_a_crashing_worker_re_enables_the_button(win, tmp_path, monkeypatch):
    """The only re-enable is paint_staging; an exception in the worker used to strand the button
    disabled and reading 'Checking...' forever, with no way back."""
    from ff9mapkit.workspace import cutscenescan
    monkeypatch.setattr(cutscenescan, "load_walkmesh",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    _mounted(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\nsteps = [ { walk = "altar" } ]\n')
    win._cs_stage["run"](sync=True)
    assert win._cs_stage["btn"].isEnabled(), "the button must never strand disabled"
    assert win._cs_stage["btn"].text() == "Check the staging"


def test_a_stale_staging_result_never_paints(win, tmp_path):
    """The worker outlives the panel; a result for a torn-down tab must be dropped."""
    _mounted(win, tmp_path, _SINGLETON)
    stale_gen = win._cs_stage_gen
    win._goto_tree_section(_MEMBER, "field")            # tear the cutscene panel down
    from ff9mapkit.workspace import cutscenescan
    win._on_cs_stage_done((stale_gen, cutscenescan.StagingResult(error="boom")))   # must not raise


def test_the_shipped_stolen_ember_examples_mount_and_navigate(win, tmp_path):
    """Both examples are [[cutscene]] arrays; both used to trap the editor on mount."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2] / "examples" / "stolen-ember"
    for name in ("HEARTH", "CHAPEL"):
        p = root / name / f"{name}.field.toml"
        if not p.exists():
            pytest.skip(f"{name} example not present")
        win.open_field(p)
        win._goto_tree_section(name, "cutscene")
        assert win._commit_active() is True, f"{name} traps the editor"
