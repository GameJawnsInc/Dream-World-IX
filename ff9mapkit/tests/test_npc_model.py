"""Offline (no game install) checks for the Info-Hub-backed [[npc]] model wiring.

These exercise build.resolve_npc_model / validate / lint_logic directly -- no field is built -- so they
run without the byte-level base templates (unlike test_build, which conftest skips when the FF9-derived
assets aren't extracted). They lock in:
  * [[npc]] model accepts an exact GEO name (resolved via the catalog) as well as a raw id;
  * a bad model NAME is a fatal validate() problem (a clean message instead of a build crash);
  * a raw model/animation id outside the known tables is a non-fatal lint warning (catches typos
    offline before they silently break in-game).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit.build import FieldProject, lint_logic, resolve_npc_model, validate


def _proj(npc=None, cutscene=None, prop=None):
    """A minimal otherwise-valid project (field + a pitch camera) so validate()'s only complaint is the
    content we're probing."""
    raw = {"field": {"id": 4003, "name": "T", "area": 11},
           "camera": {"pitch": 40, "distance": 3000, "fov": 42},
           "npc": npc or []}
    if cutscene:
        raw["cutscene"] = cutscene
    if prop:
        raw["prop"] = prop
    return FieldProject(raw, Path("."))


def test_resolve_npc_model_passthrough_and_name():
    assert resolve_npc_model(None) is None
    assert resolve_npc_model(8) == 8                       # raw id unchanged -> golden builds byte-identical
    assert resolve_npc_model("8") == 8
    assert resolve_npc_model("GEO_MAIN_F0_VIV") == 8       # exact GEO name -> id
    assert resolve_npc_model("geo_main_f0_viv") == 8       # case-insensitive
    assert resolve_npc_model(999999) == 999999             # an unknown raw id passes through (lint warns)
    with pytest.raises(ValueError):
        resolve_npc_model("GEO_NOPE")
    with pytest.raises(ValueError):
        resolve_npc_model(True)                            # a boolean is never a model


def test_validate_flags_unknown_npc_model_name():
    bad = validate(_proj(npc=[{"name": "guard", "pos": [0, 0], "model": "GEO_NOPE"}]))
    assert any("model" in p and "guard" in p for p in bad)          # a bad NAME is a fatal problem
    good = validate(_proj(npc=[{"name": "guard", "pos": [0, 0], "model": "GEO_NPC_F0_BAR"}]))
    assert good == []                                               # a real GEO name builds clean
    raw_id = validate(_proj(npc=[{"name": "g", "pos": [0, 0], "model": 999999}]))
    assert not any("model:" in p for p in raw_id)                   # an unknown raw id is NOT fatal (lint only)


def test_lint_warns_on_unknown_model_and_animation_ids():
    w = lint_logic(_proj(npc=[{"name": "g", "pos": [0, 0], "model": 999999,
                               "anims": {"stand": 999999999}}]))
    assert any("model id 999999" in x for x in w)
    assert any("anims" in x and "999999999" in x for x in w)
    clean = lint_logic(_proj(npc=[{"name": "g", "pos": [0, 0], "model": 8, "anims": {"stand": 148}}]))
    assert not any("model table" in x or "known animation" in x for x in clean)
    wc = lint_logic(_proj(npc=[{"name": "a", "pos": [0, 0], "preset": "vivi"}],
                          cutscene={"actor": "a", "steps": [{"animation": 999999999}]}))
    assert any("animation id 999999999" in x for x in wc)


# --- the anim lint knows about MINTED clips and about WHICH rig is playing --------------------------

def test_lint_exempts_the_mint_band_from_the_animation_db_check():
    """`model-anim-new` registers 60000-65535 keys at LAUNCH via a DictionaryPatch line, so they are
    deliberately absent from the baked AnimationDB -- every minted clip used to false-positive here."""
    from ff9mapkit.models.anim import _NEW_ANIM_KEY_BASE, _NEW_ANIM_KEY_MAX

    def warns(aid):
        w = lint_logic(_proj(npc=[{"name": "g", "pos": [0, 0], "model": 8, "anims": {"stand": aid}}]))
        return [x for x in w if "known animation id" in x]
    assert warns(_NEW_ANIM_KEY_BASE) == [] and warns(_NEW_ANIM_KEY_MAX) == []
    assert warns(_NEW_ANIM_KEY_BASE - 1), "below the band is still an unknown id"
    assert warns(_NEW_ANIM_KEY_MAX + 1), "above the band a field anim id cannot even fit its u16 slot"


def test_lint_warns_when_an_anim_is_not_one_of_the_resolved_models_clips():
    """A clip binds by BONE NAME, so a foreign rig's id attaches and poses the model wrong rather than
    failing loudly. 560 = ANH_NPC_F0_BBA_IDLE: a real id, just not one Vivi can play."""
    def warns(block):
        return [x for x in lint_logic(_proj(npc=[block])) if "own clips" in x]
    bad = warns({"name": "g", "pos": [0, 0], "model": "GEO_MAIN_F0_VIV", "anims": {"stand": 560}})
    assert bad and "GEO_MAIN_F0_VIV" in bad[0] and "ANH_NPC_F0_BBA_IDLE" in bad[0]
    # the model resolves through the SAME precedence the build spends -- an archetype/preset scopes it too
    assert warns({"name": "g", "pos": [0, 0], "preset": "vivi", "anims": {"stand": 560}})
    assert warns({"name": "g", "pos": [0, 0], "model": "GEO_MAIN_F0_VIV", "anims": {"stand": 148}}) == []
    assert warns({"name": "g", "pos": [0, 0], "anims": {"stand": 560}}) == []   # no model -> nothing to scope


def test_lint_warns_on_a_cross_form_prop_pose():
    """THE CROSS-FORM CLIP TRAP on a held pose: ANH_NPC_F3_CSO_ATTACK_CID_* exists only in the F3 form,
    and a one-shot from it on an F1 rig twists the model. It still BUILDS (backward compat) -- it warns."""
    def warns(pose):
        return [x for x in lint_logic(_proj(prop=[{"model": "GEO_NPC_F1_CSO", "pos": [0, 0],
                                                   "pose": pose}])) if "CROSS-FORM" in x]
    w = warns("attack_cid_3")
    assert w and "GEO_NPC_F1_CSO" in w[0] and "attack_cid_3" in w[0]
    assert warns("idle") == []                     # an own-form pose is clean
    assert warns("1872") == []                     # a raw id resolves verbatim, nothing to say


def test_a_cross_form_prop_pose_still_resolves_but_own_form_wins():
    from ff9mapkit import catalog as C
    from ff9mapkit.build import _resolve_prop_pose
    cso = C.resolve_model("GEO_NPC_F1_CSO")
    assert _resolve_prop_pose(cso, "attack_cid_3") == C.animations_for_model(cso)["attack_cid_3"]
    assert _resolve_prop_pose(cso, "idle") == C.own_form_gestures(cso)["idle"]     # own form, not F0's
