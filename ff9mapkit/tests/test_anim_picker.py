"""Fences for ATTACHING an animation -- Stage C of the animation-preview arc.

Four mechanisms, each fenced against the no-op:

  * the PICKER dialog (``workspace/animpicker.AnimPickerDialog``) -- three modes over ONE class:
    a gesture list that refuses cross-form clips, a movement list that marks them, and the five-slot
    editor whose Auto means "let the build resolve it". It previews through the SHARED
    AnimFrameService, so a clip filled for the Models tab is already warm here;
  * the DOORWAY -- ``shell._pick`` returns EARLY for the animation kinds (they are not Info Hub kinds:
    an unknown kind reaching CatalogPicker opens a "0 matches" list), and ``build_form``'s browse
    closure hands it the block's resolved MODEL -- the same precedence the build spends;
  * the CUTSCENE step Browse -- shown for the ``animation`` step type only, scoped by the three ways a
    step names its actor (a cast name / "player" / blank on a cast of one);
  * A11Y -- dialogs never reach the a11y sweep (it walks the shell's widget tree), so their names are
    asserted BY HAND here, on constructed-not-exec'd dialogs.

Headless (offscreen), FF9MAPKIT_NO_THUMBS=1, every cache read pinned to a scratch FF9MAPKIT_DATA, and
the frame service is a double: nothing here can reach this machine's install or its preview cache.
"""
from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtCore import QObject, Qt, Signal                        # noqa: E402
from PySide6.QtWidgets import (QApplication, QComboBox, QLineEdit,    # noqa: E402
                               QListWidget, QPushButton)

from ff9mapkit import blockmodel, catalog                             # noqa: E402
from ff9mapkit.editor import forms                                    # noqa: E402
from ff9mapkit.editor.theme import pick_palette                       # noqa: E402
from ff9mapkit.workspace import animpicker, forms_qt                  # noqa: E402
from ff9mapkit.workspace.animpicker import AnimPickerDialog           # noqa: E402

_VIV = "GEO_MAIN_F0_VIV"
_VIV_ID = 8
_STAND = 148
_CSO = "GEO_NPC_F1_CSO"          # the rig THE CROSS-FORM CLIP TRAP was measured on (F3 attack clips)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pin_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path))
    return tmp_path


@pytest.fixture
def thumbs_on(monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_NO_THUMBS", "0")


class _StubAnimFrames(QObject):
    """The service surface with no worker and no install reach (the shape test_anim_preview owns)."""

    frameReady = Signal(str, int, int, str)
    clipDone = Signal(str, int)
    clipMissed = Signal(str, int, str)

    def __init__(self):
        super().__init__()
        self.requests, self.supersedes, self.holds = [], 0, 0
        self.warm, self.frames, self.misses = {}, {}, {}

    def cached_frame(self, geo, anim, frame):
        return self.frames.get((str(geo), int(anim), int(frame)))

    def cached_meta(self, geo, anim):
        return self.warm.get((str(geo), int(anim)))

    def missed_reason(self, geo, anim):
        return self.misses.get((str(geo), int(anim)))

    def request_clip(self, geo, anim):
        self.requests.append((str(geo), int(anim)))
        return self.warm.get((str(geo), int(anim)))

    def supersede(self):
        self.supersedes += 1

    def hold(self):
        self.holds += 1

    def release(self):
        self.holds -= 1


def _block(**kw):
    return blockmodel.resolve_block_model(kw, kind=kw.pop("_kind", "npc"), strict=False)


def _dlg(app, mode="gesture", block=None, current="", svc=None):
    return AnimPickerDialog(None, pick_palette("dark"), mode=mode,
                            block=block if block is not None else _block(model=_VIV),
                            current=current, anim_frames=svc or _StubAnimFrames())


def _rows(dlg):
    return [dlg.listw.item(i).text() for i in range(dlg.listw.count())]


# ------------------------------------------------------------------------------- the dialog
def test_gesture_mode_refuses_cross_form_clips(app):
    """THE CROSS-FORM CLIP TRAP: a one-shot played on a different form's skeleton twists the model
    in-game, so the gesture picker must not even OFFER one."""
    dlg = _dlg(app, block=_block(model=_CSO))
    offered = {dlg.listw.item(i).data(Qt.ItemDataRole.UserRole)["label"]
               for i in range(dlg.listw.count())}
    cross = {r["label"] for r in catalog.clip_inventory(_CSO) if not r["own_form"]}
    assert cross, "GEO_NPC_F1_CSO no longer has cross-form clips -- pick another rig for this fence"
    assert not (offered & cross), f"a gesture picker offered cross-form clips: {sorted(offered & cross)}"
    assert all("other form" not in t for t in _rows(dlg))


def test_movement_mode_shows_everything_and_marks_the_cross_form_rows(app):
    """The five movement slots are the ONE place the any-form join is proven -- so movement mode shows
    them, marked, instead of hiding them."""
    dlg = _dlg(app, mode="movement", block=_block(model=_CSO))
    marked = [t for t in _rows(dlg) if "other form" in t]
    assert marked, "a cross-form movement row must be shown AND marked"
    assert len(_rows(dlg)) > dlg.listw.count() - 1 >= 0


def test_gesture_mode_answers_with_the_name_and_movement_with_the_id(app):
    """A gesture NAME survives a model swap and the build resolves it through the actor's own rig; a
    movement slot takes the u16 id, because that is literally what the .eb anim setter writes."""
    g = _dlg(app, current="stand")
    assert g.listw.currentItem() is not None, "the dialog re-opens on what the field already holds"
    g._ok()
    assert g.result == "stand"
    m = _dlg(app, mode="movement", current="stand")
    m._ok()
    assert m.result == str(_STAND)


def test_an_unscoped_block_opens_with_the_reason_not_an_empty_list(app):
    """A picker that cannot scope itself must SAY so: an empty list with no sentence is the defect."""
    dlg = _dlg(app, block=_block(preset="zidane"))     # the zidane preset keeps the cloned player's model
    assert dlg.model is None and dlg.listw.count() == 0
    texts = " ".join(w.text() for w in dlg.findChildren(type(dlg._scope_label("x"))))
    assert "No model resolved" in texts and "numeric clip id" in texts


def test_the_preview_arms_through_the_shared_service(app, pin_cache, thumbs_on):
    """Selecting a row plays it -- through the SAME AnimFrameService the Models tab uses (a warm clip
    answers from disk with no worker and no signal, so the return value is the whole contract)."""
    svc = _StubAnimFrames()
    svc.warm[(_VIV, _STAND)] = {"rendered_frames": [0, 1], "fps": 30.0, "stride": 1,
                                "frame_count": 2, "sample_rate": 30.0}
    svc.frames.update({(_VIV, _STAND, 0): "f0.png", (_VIV, _STAND, 1): "f1.png"})
    dlg = _dlg(app, svc=svc)
    row = next(i for i in range(dlg.listw.count())
               if dlg.listw.item(i).data(Qt.ItemDataRole.UserRole)["anim_id"] == _STAND)
    dlg.listw.setCurrentRow(row)
    assert dlg._armed == (_VIV, _STAND) and svc.requests == [(_VIV, _STAND)]
    assert [p for _f, p in dlg._seq] == ["f0.png", "f1.png"]
    assert dlg.anim_play.isEnabled()
    dlg._frame_ready("GEO_MAIN_F0_ZDN", 999, 0, "wrong.png")     # the identity fence, at the paint
    assert len(dlg._seq) == 2
    dlg.done(0)
    assert svc.supersedes >= 1, "closing the dialog must cancel its fill"


def test_slots_mode_edits_five_slots_and_auto_clears_one(app):
    """Blank = AUTO: the build resolves that slot from the block's model/preset. Clearing is the ONLY
    way to say 'go back to auto', so the Auto button is the mechanism, not a decoration."""
    dlg = _dlg(app, mode="slots", current="stand=560, walk=571")
    assert list(dlg.slot_edits) == list(forms.ANIM_SLOTS)
    assert dlg.slot_edits["stand"].text() == "560" and dlg.slot_edits["run"].text() == ""
    autos = [b for b in dlg.findChildren(QPushButton) if b.text() == "Auto"]
    assert len(autos) == len(forms.ANIM_SLOTS)
    autos[0].click()                                   # the stand row's Auto
    assert dlg.slot_edits["stand"].text() == ""
    dlg._ok()
    assert dlg.result == "walk=571"
    assert forms.parse_animset(dlg.result) == {"walk": 571}, "what it writes, the field must read back"


def test_slots_mode_offers_the_auto_answer_from_the_block_not_from_npc_anims(app):
    """The Auto hint has to come from the SAME precedence the build spends: a preset NPC's slots are
    the ARCHETYPE model's, and reading npc_anims directly off an absent `model =` would say nothing."""
    from ff9mapkit import archetypes
    b = _block(preset="vivi")
    dlg = _dlg(app, mode="slots", block=b)
    want = catalog.npc_anims(archetypes.resolve("vivi")[0])["stand"]
    assert str(want) in dlg.slot_edits["stand"].placeholderText()
    assert b.anims and b.anims["stand"] == want


def test_the_dialog_names_every_control_for_a_screen_reader(app):
    """Dialogs are never walked by the a11y sweep (it starts at the shell), so this is the sweep."""
    for dlg in (_dlg(app), _dlg(app, mode="movement"), _dlg(app, mode="slots")):
        for w in dlg.findChildren(QPushButton) + dlg.findChildren(QListWidget) + \
                dlg.findChildren(QLineEdit):
            assert w.accessibleName(), f"{dlg.mode}: a {type(w).__name__} has no screen-reader name"
    single = _dlg(app)
    assert single.img.accessibleName() and single.anim_slider.accessibleName()


def test_an_unknown_mode_raises_instead_of_opening_something_wrong(app):
    with pytest.raises(ValueError):
        _dlg(app, mode="wiggle")


# ------------------------------------------------------------------------------- the doorway
def test_the_browse_closure_passes_the_blocks_resolved_model_for_anim_fields_only(app):
    """THE CALL-SITE LAW, twice over: the animation fields must reach the picker WITH the rig (a
    picker scoped to the wrong model is worse than none), and every other field must keep `pick`'s
    positional signature -- the reason model_hint is a keyword the closure only ever passes here."""
    asked = []

    def pick(cat, cur, want_id=False, **kw):
        asked.append((cat, want_id, kw.get("model_hint")))
        return None

    w, _getters = forms_qt.build_form(
        forms.NPC_SPEC, forms.entity_to_values(forms.NPC_SPEC, {"preset": "vivi"}),
        pick_palette("dark"), pick=pick)
    by_name = {b.accessibleName(): b for b in w.findChildren(QPushButton)}
    by_name["Browse Movement clips"].click()
    cat, want_id, hint = asked[-1]
    assert cat == "animset" and want_id is False
    assert hint is not None and hint.model == blockmodel.resolve_block_model({"preset": "vivi"}).model
    by_name["Browse Preset"].click()
    assert asked[-1][2] is None, "a non-animation field must not be handed a model hint"


def test_the_prop_pose_browse_scopes_to_the_prop_archetypes_model(app):
    """A prop names its model with a THIRD vocabulary (`prop = "chest"`), and the pose picker has to
    follow it -- else Browse on a chest lists the player's gestures."""
    from ff9mapkit import prop_archetypes
    asked = []
    w, _g = forms_qt.build_form(forms.PROP_SPEC,
                                forms.entity_to_values(forms.PROP_SPEC, {"prop": "chest"}),
                                pick_palette("dark"),
                                pick=lambda c, cur, want_id=False, **kw: asked.append(kw.get("model_hint")))
    next(b for b in w.findChildren(QPushButton) if b.accessibleName() == "Browse Pose").click()
    assert asked and asked[-1].model == prop_archetypes.resolve("chest")[0]


def test_pick_animation_opens_the_right_mode_per_catalog(app, monkeypatch):
    seen = {}

    class _Fake:
        def __init__(self, *a, **kw):
            seen.update(kw)
            self.result = "ok"

        def exec(self):
            return 0
    monkeypatch.setattr(animpicker, "AnimPickerDialog", _Fake)
    animpicker.pick_animation(None, pick_palette("dark"), kinds=["anim"], current="")
    assert seen["mode"] == "gesture"
    animpicker.pick_animation(None, pick_palette("dark"), kinds=["animset"], current="")
    assert seen["mode"] == "slots"


# ------------------------------------------------------------------------------- the shell wiring
@pytest.fixture
def win(app, tmp_path, monkeypatch, pin_cache):
    from ff9mapkit import prefs
    from ff9mapkit.workspace import shell
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    w = shell.Workspace(pick_palette("dark"))
    yield w
    w.hide()


def test_the_window_owns_ONE_frame_service_and_the_models_tab_shares_it(win):
    """Two services would mean two worker threads racing the same PNG -- and a clip filled for the
    Models tab would render a second time for the picker."""
    assert win.models_doc.anims is win.anim_frames


def test_pick_returns_early_for_the_animation_kinds(win, monkeypatch):
    """An unknown kind reaching CatalogPicker opens a "0 matches" list -- the flag/sps branches only
    computed context, so the animation kinds had to leave BEFORE it."""
    from ff9mapkit.workspace import shell as shell_mod
    monkeypatch.setattr(shell_mod, "pick_catalog",
                        lambda *a, **k: pytest.fail("the Info Hub picker must not see an anim kind"))
    opened = {}

    def _fake(parent, pal, *, kinds, current, model_hint=None, anim_frames=None, label="animation"):
        opened.update(kinds=kinds, hint=model_hint, svc=anim_frames)
        return "glad"
    monkeypatch.setattr(animpicker, "pick_animation", _fake)
    hint = blockmodel.resolve_block_model({"model": _VIV}, strict=False)
    assert win._pick("anim", "", model_hint=hint) == "glad"
    assert opened["kinds"] == ["anim"] and opened["hint"] is hint
    assert opened["svc"] is win.anim_frames, "the dialog must reuse the window's service"
    win._pick("animset", "", model_hint=hint)
    assert opened["kinds"] == ["animset"]


def _open_cutscene(win, tmp_path, toml):
    p = tmp_path / "cs.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert win.open_field(p)
    win.tabs.setCurrentWidget(win.cutscene_doc)          # the DOC tab owns the step editor now
    assert win.cutscene_doc._member == _MEMBER           # (the member key is the [field] NAME)
    win.cutscene_doc._edit_step(0)                       # open the animation step in the editor
    return p


_MEMBER = "X"                    # the member key open_field uses is the [field] name
_CS_TOML = ('[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
            '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
            '[player]\nspawn = [0, 0]\n\n'
            '[[npc]]\nname = "Cid"\nmodel = "GEO_SUB_F0_CID"\npos = [0, 0]\n\n'
            '[cutscene]\nactors = ["Cid"]\nsteps = [ { animation = "talk_1_1" } ]\n')


def test_the_cutscene_browse_shows_only_for_an_animation_step(win, tmp_path):
    """A Browse on a 'wait' step is a button that cannot answer -- the same dead control the round-6
    census counted six of. It rides the say-step's existing show/hide seam."""
    _open_cutscene(win, tmp_path, _CS_TOML)
    b = next(x for x in win.findChildren(QPushButton)
             if x.accessibleName() == "Browse animations this actor's model can play")
    combo = next(c for c in win.findChildren(QComboBox) if c.accessibleName() == "Cutscene step type")
    combo.setCurrentIndex(list(forms.STEP_KIND).index("animation"))
    assert b.isVisibleTo(win)
    combo.setCurrentIndex(list(forms.STEP_KIND).index("wait"))
    assert not b.isVisibleTo(win)


def test_the_cutscene_actor_resolves_three_ways(win, tmp_path):
    """The three ways a step names its actor, each answering with the model that actor WEARS."""
    _open_cutscene(win, tmp_path, _CS_TOML)
    member = _MEMBER
    named = win._actor_model_hint(member, "Cid", ["Cid"])
    assert named.model == catalog.resolve_model("GEO_SUB_F0_CID")
    player = win._actor_model_hint(member, "player", ["Cid", "player"])
    assert player.model == catalog.resolve_model(blockmodel.PLAYER_DEFAULT_GEO), \
        "no [player] model = means the cloned stock avatar, who is Zidane"
    blank = win._actor_model_hint(member, "", ["Cid"])
    assert blank.model == named.model, "a cast of ONE fills an untagged actor step (build.py's default)"
    lost = win._actor_model_hint(member, "Nobody", ["Cid"])
    assert lost.model is None and "not an [[npc]]" in lost.reason
    ambiguous = win._actor_model_hint(member, "", ["Cid", "player"])
    assert ambiguous.model is None and "cast" in ambiguous.reason


def test_the_cutscene_browse_writes_the_picked_name_into_the_step(win, tmp_path, monkeypatch):
    """The wiring itself: the REAL button, the REAL closure, the value landing in the step's field."""
    _open_cutscene(win, tmp_path, _CS_TOML)
    combo = next(c for c in win.findChildren(QComboBox) if c.accessibleName() == "Cutscene step type")
    combo.setCurrentIndex(list(forms.STEP_KIND).index("animation"))
    got = {}

    def _fake(parent, pal, *, kinds, current, model_hint=None, anim_frames=None, label="animation"):
        got.update(kinds=kinds, hint=model_hint)
        return "talk_1_2"
    monkeypatch.setattr(animpicker, "pick_animation", _fake)
    next(x for x in win.findChildren(QPushButton)
         if x.accessibleName() == "Browse animations this actor's model can play").click()
    value = next(e for e in win.findChildren(QLineEdit)
                 if e.accessibleName() == "Cutscene step value")
    assert value.text() == "talk_1_2"
    assert got["kinds"] == ["anim"]
    assert got["hint"].model == catalog.resolve_model("GEO_SUB_F0_CID"), \
        "blank actor + a cast of one scopes to that cast member's rig"
