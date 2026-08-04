"""SHELL-side fences for the cutscene lane after the redesign.

The Cutscene DOC TAB (:mod:`workspace.cutscenedoc`, fenced in ``test_cutscenedoc.py``) is the
ONE write surface. What this file owns is everything AROUND it:

  * the Editor tree's Cutscene node is a SUMMARY + the door to the tab — it must never
    materialize a section, never carry a ``_save_ctx``, and never trap navigation (the
    [[cutscene]] deadlock family's ghosts stay buried);
  * :func:`forms.single_block` (still the one owner for every OTHER maybe-plural single);
  * the forms↔compiler mirror fences (PARALLEL / GLOBAL / TEXT step vocabularies);
  * the Inspector / node lint / health badge over a dispatch;
  * the staging lane driven END-TO-END through the doc the way a user reaches it;
  * the tree delete's scene-#0 semantics (the A4 lesson: never a plural delete behind a
    singular label).

Behaviour + data only — no geometry or font claim — so offscreen is sound here.
"""
from __future__ import annotations

import time

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QComboBox, QPushButton   # noqa: E402

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
    """Open + land on the Editor tree's Cutscene node (the SUMMARY, post-redesign)."""
    p = _open(win, tmp_path, toml_text, name)
    win._goto_tree_section(_MEMBER, "cutscene")
    return p


def _doc_fed(win, tmp_path, toml_text, name="X"):
    """Open + show the Cutscene TAB — the path a user actually takes to the staging check."""
    p = _open(win, tmp_path, toml_text, name)
    win.tabs.setCurrentWidget(win.cutscene_doc)
    assert win.cutscene_doc._member == _MEMBER, "the tab-show feed must land on the open field"
    return p


# --------------------------------------------------------------- _single_block (the one owner)
def test_single_block_normalizes_both_storage_shapes():
    assert forms.single_block({"cutscene": {"once": True}}, "cutscene") == {"once": True}
    assert forms.single_block({"cutscene": [{"a": 1}, {"b": 2}]}, "cutscene") == {"a": 1}
    assert forms.single_block({}, "cutscene") == {}
    assert forms.single_block({"cutscene": []}, "cutscene") == {}


def test_single_block_does_not_materialize_unless_asked():
    d = {}
    forms.single_block(d, "cutscene")
    assert d == {}, "a read must not create the section"
    d2 = {"cutscene": []}
    forms.single_block(d2, "cutscene")
    assert d2 == {"cutscene": []}, "a read must not seat a block"


def test_single_block_create_seats_block_zero_in_an_empty_list():
    d = {"cutscene": []}
    blk = forms.single_block(d, "cutscene", create=True)
    blk["once"] = True
    assert d["cutscene"] == [{"once": True}], "the write must land IN the list, not beside it"


# --------------------------------------------------------------- the summary mount (post-flip)
def test_the_tree_node_mounts_a_summary_not_a_form(win, tmp_path):
    """THE ONE-WRITE-SURFACE LAW. The old form edited scene #0 while the doc tab edits any —
    two writers drift (the deadlock family's disease). The tree node is now a summary: no
    step combo, no _save_ctx, one accented door to the tab."""
    _mounted(win, tmp_path, _PLURAL)
    combos = [c for c in win.doc_host.findChildren(QComboBox)
              if c.accessibleName() == "Cutscene step type"]
    assert not combos, "the Editor tree must not carry a second step editor"
    assert win._save_ctx is None, "a summary has nothing to fold"
    doors = [b for b in win.doc_host.findChildren(QPushButton)
             if b.text() == "Open the Cutscene tab"]
    assert doors, "the summary must offer the door to the write surface"
    # navigation away stays clean (the deadlock's whole family: nav/undo/redo/Check all fold)
    assert win._commit_active() is True
    win._goto_tree_section(_MEMBER, "field")


def test_the_summary_lists_every_scene_of_the_dispatch(win, tmp_path):
    from PySide6.QtWidgets import QLabel
    _mounted(win, tmp_path, _PLURAL)
    body = " ".join(lb.text() for lb in win.doc_host.findChildren(QLabel))
    assert "scene #0" in body and "scene #1" in body
    assert "plays at beat 100" in body and "plays at beat 300" in body


def test_the_summary_never_materializes_the_section(win, tmp_path):
    _mounted(win, tmp_path, _HEAD)                     # no cutscene at all
    assert "cutscene" not in win._doc(_MEMBER).data, "browsing must never create the section"
    assert win._save_ctx is None


def test_the_summary_door_lands_on_the_doc(win, tmp_path):
    _mounted(win, tmp_path, _SINGLETON)
    door = next(b for b in win.doc_host.findChildren(QPushButton)
                if b.text() == "Open the Cutscene tab")
    door.click()
    assert win.tabs.currentWidget() is win.cutscene_doc
    assert win.cutscene_doc._member == _MEMBER
    assert win.cutscene_doc.rail.count() == 1


# --------------------------------------------------------------- forms <-> compiler mirrors
def test_forms_parallel_steps_matches_the_compilers_own_rule():
    from ff9mapkit import build
    assert tuple(forms.PARALLEL_STEPS) == tuple(build.PARALLEL_STEP_KINDS), \
        "the with_prev checkbox must enable exactly what the compiler accepts"


def test_the_gui_can_author_EVERY_global_step_the_compiler_accepts():
    """THE DRIFT FENCE (the six-kinds lesson): the compiler grew window steps and the GUI
    silently couldn't author them. The GUI's global-step list must equal the compiler's."""
    from ff9mapkit.content import cutscene as C
    compiler_globals = ("say", "wait", "set_flag") + C.WINDOW_STEP_KINDS
    assert set(forms.GLOBAL_STEPS) == set(compiler_globals), \
        f"GUI can't author: {set(compiler_globals) - set(forms.GLOBAL_STEPS)}"
    for k in compiler_globals:
        assert k in forms.STEP_KIND, f"{k} missing from STEP_KIND"
        assert k in forms.STEP_LABEL, f"{k} has no combo label"
        assert k in forms.STEP_HELP, f"{k} has no help line"


def test_text_steps_matches_the_txid_counter():
    """A text kind the GUI treats as a plain value silently shifts every later txid."""
    from ff9mapkit.content import cutscene as C
    assert tuple(forms.TEXT_STEPS) == tuple(C.TEXT_STEP_KINDS)


def test_all_blocks_agrees_with_the_builds_own_normalizer():
    from ff9mapkit.content import cutscene as C
    for raw in (None, {"a": 1}, [{"a": 1}, {"b": 2}], [{"a": 1}, "junk", {"b": 2}]):
        assert forms.all_blocks(raw) == C.blocks(raw)


# --------------------------------------------------------------- Inspector + node lint
def test_the_inspector_summarizes_every_scene_of_a_dispatch(win, tmp_path):
    _open(win, tmp_path, _PLURAL)
    body = " ".join(win._inspect_single("cutscene", win._doc(_MEMBER).data["cutscene"]))
    assert "2 scenes" in body
    assert "scene #0" in body and "scene #1" in body


def test_the_inspector_still_reads_a_singleton(win, tmp_path):
    _open(win, tmp_path, _SINGLETON)
    body = " ".join(win._inspect_single("cutscene", win._doc(_MEMBER).data["cutscene"]))
    assert "1 step" in body


def test_node_lint_checks_every_scene_and_names_which_one(win, tmp_path):
    toml = (_HEAD +
            '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 100\n'
            'steps = [ { say = "fine" } ]\n\n'
            '[[cutscene]]\nactors = ["Ghost"]\nrequires_scenario = 300\n'
            'steps = [ { walk = "nowhere" } ]\n')
    _open(win, tmp_path, toml)
    problems = win._node_problems("cutscene", win._doc(_MEMBER).data["cutscene"], _MEMBER)
    body = " ".join(problems)
    assert "Ghost" in body, "the off-field cast member must be caught"
    assert "scene #1" in body, "the warning must say WHICH scene"


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


# --------------------------------------------------------------- THE STAGING CHECK (via the doc)
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
            'steps = [ { walk = [9000, 9000] } ]\n')          # far outside the floor
    _doc_fed(win, tmp_path, toml)
    win.cutscene_doc.stage_now(sync=True)
    res = win.cutscene_doc._last_stage
    assert res.error == "", res.error
    assert res.warnings, "an off-mesh walk target must be reported"
    assert "stall" in " ".join(res.warnings).lower()
    assert win.cutscene_doc.stage_list.count() == len(res.warnings)
    assert not win.cutscene_doc.stage_list.isHidden()


def test_staging_check_passes_a_reachable_walk(win, tmp_path):
    toml = (_HEAD + '[cutscene]\nactors = ["Cid"]\nsteps = [ { walk = "altar" } ]\n')
    _doc_fed(win, tmp_path, toml)
    win.cutscene_doc.stage_now(sync=True)
    res = win.cutscene_doc._last_stage
    assert not (res.error or res.warnings or res.skipped), \
        f"a reachable walk must be clean: {res.error or res.warnings or res.skipped}"
    assert "reaches its target" in res.summary()
    assert win.cutscene_doc.stage_list.isHidden()


def test_staging_check_says_a_narration_scene_has_nothing_to_stage(win, tmp_path):
    _doc_fed(win, tmp_path, _HEAD + '[cutscene]\nsteps = [ { say = "alone" } ]\n')
    win.cutscene_doc.stage_now(sync=True)
    assert "narration" in win.cutscene_doc._last_stage.summary().lower()


def test_staging_warnings_name_which_scene_in_a_dispatch(win, tmp_path):
    """'step 0' is ambiguous across a dispatch -- the build's own labels disambiguate it."""
    toml = (_HEAD +
            '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 100\n'
            'steps = [ { walk = "altar" } ]\n\n'
            '[[cutscene]]\nactors = ["Cid"]\nrequires_scenario = 300\n'
            'steps = [ { walk = [9000, 9000] } ]\n')
    _doc_fed(win, tmp_path, toml)
    win.cutscene_doc.stage_now(sync=True)
    body = " ".join(win.cutscene_doc._last_stage.warnings)
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


def test_the_staging_lane_passes_the_campaigns_flag_names(win, tmp_path, monkeypatch):
    """THE CALL-SITE LAW: the loader accepting flag_names is worthless if the doc sends none."""
    seen = {}
    from ff9mapkit.workspace import cutscenescan
    real = cutscenescan.load_walkmesh
    monkeypatch.setattr(cutscenescan, "load_walkmesh",
                        lambda path, names=None: (seen.setdefault("names", names), real(path, names))[1])
    _doc_fed(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\nsteps = [ { walk = "altar" } ]\n')
    win.cutscene_doc.stage_now(sync=True)
    assert "names" in seen, "the staging check never called the loader"
    assert seen["names"] == {}, "a loose field has no campaign names, but the argument must be PASSED"


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
    win.tabs.setCurrentWidget(win.cutscene_doc)
    win.cutscene_doc.stage_now(sync=True)
    res = win.cutscene_doc._last_stage
    assert res.warnings, "the off-mesh walk must be caught even though the cast is scene-placed"


def test_a_scene_the_checker_SKIPPED_is_never_reported_as_clean(win, tmp_path):
    """`_validate_cutscene_movement` silently `continue`s past a scene whose names don't resolve.
    A bare tick over unchecked work is the false green this panel exists to prevent."""
    _doc_fed(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\n'
             'steps = [ { walk = "no_such_marker" } ]\n')
    win.cutscene_doc.stage_now(sync=True)
    res = win.cutscene_doc._last_stage
    assert res.skipped, "an unresolvable target must be reported as NOT CHECKED"
    assert "not checked" in res.summary().lower()
    assert "reaches its target" not in res.summary(), "never a clean tick over a skipped scene"
    assert not win.cutscene_doc.stage_list.isHidden(), "the skipped scene must be listed"


def test_the_staging_BUTTON_is_wired(win, tmp_path):
    """THE CALL-SITE LAW, applied to this suite's own fence: every other staging test calls
    `stage_now` directly, so deleting the button's clicked.connect would leave the suite green
    with a dead control shipped."""
    _doc_fed(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\n'
             'steps = [ { walk = [9000, 9000] } ]\n')
    doc = win.cutscene_doc
    doc._last_stage = None
    doc.stage_btn.click()                         # the real user gesture (async worker)
    deadline = time.time() + 20
    while doc._last_stage is None and time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.02)
    assert doc._last_stage is not None, "clicking the button produced no result"
    assert doc._last_stage.warnings, "the off-mesh walk should have been caught"


def test_a_crashing_worker_re_enables_the_button(win, tmp_path, monkeypatch):
    """The only re-enable is _finish_stage; an exception in the worker used to strand the old
    form's button disabled and reading 'Checking…' forever, with no way back."""
    from ff9mapkit.workspace import cutscenescan
    monkeypatch.setattr(cutscenescan, "load_walkmesh",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    _doc_fed(win, tmp_path, _HEAD + '[cutscene]\nactors = ["Cid"]\nsteps = [ { walk = "altar" } ]\n')
    win.cutscene_doc.stage_now(sync=True)
    assert win.cutscene_doc.stage_btn.isEnabled(), "the button must never strand disabled"
    assert win.cutscene_doc.stage_btn.text() == "Check the staging"
    assert "boom" in win.cutscene_doc.stage_note.text(), "the crash must be SAID, not eaten"


# --------------------------------------------------------------- the tree delete (A4)
def test_removing_a_cutscene_from_a_dispatch_removes_ONE_SCENE(win, tmp_path, monkeypatch):
    """A4. It used to pop the whole array: three authored scenes destroyed by one click, behind a
    confirm saying "this cutscene", written to disk at once, and Undo restored NOTHING (measured)."""
    import tomllib
    monkeypatch.setattr(shell.QMessageBox, "question",
                        staticmethod(lambda *a, **k: shell.QMessageBox.StandardButton.Yes))
    p = _mounted(win, tmp_path, _PLURAL)
    assert len(tomllib.loads(p.read_text(encoding="utf-8"))["cutscene"]) == 2
    win._delete_object(_MEMBER, "cutscene", single=True, label="cutscene")
    left = tomllib.loads(p.read_text(encoding="utf-8"))["cutscene"]
    assert len(left) == 1, "only scene #0 may go"
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


# --------------------------------------------------------------- the shipped examples
def test_the_shipped_stolen_ember_examples_mount_and_navigate(win, tmp_path):
    """Both examples are [[cutscene]] arrays; both used to trap the editor on mount. Now the
    tree mounts the summary AND the doc tab must render both dispatches."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2] / "examples" / "stolen-ember"
    for name in ("HEARTH", "CHAPEL"):
        p = root / name / f"{name}.field.toml"
        if not p.exists():
            pytest.skip(f"{name} example not present")
        win.open_field(p)
        win._goto_tree_section(name, "cutscene")
        assert win._commit_active() is True, f"{name} traps the editor"
        win.tabs.setCurrentWidget(win.cutscene_doc)
        assert win.cutscene_doc._member == name
        assert win.cutscene_doc.rail.count() >= 1, f"{name}'s dispatch must render in the doc"
        win.tabs.setCurrentWidget(win.doc_scroll)
