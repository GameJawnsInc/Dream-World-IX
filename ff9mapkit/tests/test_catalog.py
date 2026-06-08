"""The Info Hub catalog: models, the model->animation join, battle scenes, cross-kind search.

Pure (no game install needed) -- backed by the baked _modeldb / _animdb_all / _scenedb dicts (Memoria's
open-source id<->name tables). The load-bearing assertion is the (group, token) animation join,
validated against known-good data: model id 8 = GEO_MAIN_F0_VIV, whose movement gestures are exactly
the kit's built-in `vivi` NPC preset (idle=148 / walk=571 / run=419 / turn_l=917 / turn_r=918).
"""
from __future__ import annotations

import pytest

from ff9mapkit import catalog as C


# --- models ------------------------------------------------------------------
def test_model_lookup_by_id_and_name():
    m = C.model(8)
    assert m is not None
    assert m.name == "GEO_MAIN_F0_VIV"
    assert (m.group, m.form, m.token) == ("MAIN", "F0", "VIV")
    assert m.kind == "playable" and m.field is True
    assert C.model("GEO_MAIN_F0_VIV").id == 8          # exact name (case-insensitive)
    assert C.model("geo_main_f0_viv").id == 8
    assert C.model("8").id == 8                          # digit string
    assert C.model(999999) is None                       # unknown id


def test_resolve_model_and_errors():
    assert C.resolve_model("GEO_MAIN_F0_VIV") == 8
    assert C.resolve_model(8) == 8
    with pytest.raises(ValueError):
        C.resolve_model("GEO_NOPE")
    with pytest.raises(ValueError):
        C.resolve_model(999999)


def test_models_filtering():
    npcs = C.models(group="NPC")
    assert npcs, "expected NPC models"
    assert all(m.group == "NPC" for m in npcs)
    assert C.models(group="npc") == npcs                 # kind label also works
    field = C.models(field_only=True)
    assert field and all(m.field for m in field)
    assert all(m.form.startswith("F") for m in field)
    # substring matches name or token
    assert all("viv" in m.name.lower() or "viv" in m.token.lower() for m in C.models("viv"))


def test_all_models_count_and_provenance():
    allm = C.all_models()
    assert len(allm) == 710
    assert all(m.name.startswith("GEO_") for m in allm)  # identifiers only, never game bytes


# --- the model -> animation join (the headline) ------------------------------
def test_animations_for_vivi_model_match_the_preset():
    anims = C.animations_for_model(8)                     # GEO_MAIN_F0_VIV
    # the five movement gestures every field actor uses. Compare by CLIP NAME, not raw id: FF9 has
    # duplicate-id clips (ANH_MAIN_F0_VIV_WALK is BOTH 147 and 571) and the engine plays by name, so
    # the catalog picks one id per name -- it must name the same clip as the `vivi` preset's id.
    assert C.animation_name(anims["idle"]) == "ANH_MAIN_F0_VIV_IDLE"
    assert C.animation_name(anims["walk"]) == "ANH_MAIN_F0_VIV_WALK"
    assert C.animation_name(anims["run"]) == "ANH_MAIN_F0_VIV_RUN"
    assert C.animation_name(anims["turn_l"]) == "ANH_MAIN_F0_VIV_TURN_L"
    assert C.animation_name(anims["turn_r"]) == "ANH_MAIN_F0_VIV_TURN_R"
    assert C.animation_name(anims["talk_3_1"]) == "ANH_MAIN_F0_VIV_TALK_3_1"


def test_catalog_agrees_with_builtin_npc_preset():
    """Cross-check the join against the kit's hardcoded preset so the two can't silently diverge. The
    catalog must, for each preset slot, choose an id naming the SAME clip as the preset's id."""
    from ff9mapkit.content.npc import PRESETS
    model_id, _animset, preset_anims = PRESETS["vivi"]
    assert model_id == 8
    anims = C.animations_for_model(model_id)
    slot_to_action = {"stand": "idle", "walk": "walk", "run": "run", "left": "turn_l", "right": "turn_r"}
    for slot, aid in preset_anims.items():
        action = slot_to_action[slot]
        assert C.animation_name(anims[action]) == C.animation_name(aid), f"{slot} -> {action}"


def test_animations_for_npc_model_nonempty():
    # a townsfolk model resolves to a gesture set via the same (group, token) rule
    bar = C.model("GEO_NPC_F0_BAR")
    assert bar is not None
    acts = C.animations_for_model(bar.id)
    assert acts, "expected NPC_BAR to have animations"
    assert all(isinstance(v, int) for v in acts.values())


def test_animation_name_lookup():
    assert C.animation_name(7302) == "ANH_MAIN_F0_VIV_TALK_3_1"
    assert C.animation_name(148) == "ANH_MAIN_F0_VIV_IDLE"
    assert C.animation_name(999999999) is None


def test_animations_for_model_unknown_is_empty():
    assert C.animations_for_model(999999) == {}


# --- battle scenes -----------------------------------------------------------
def test_battle_scenes_and_resolve():
    rows = C.battle_scenes()
    assert len(rows) == 856
    assert all(nm.startswith("BSC_") for nm, _ in rows)
    name, sid = rows[0]
    assert C.resolve_scene(name) == sid
    assert C.resolve_scene(67) == 67                     # a raw id passes through
    assert C.resolve_scene("67") == 67
    with pytest.raises(ValueError):
        C.resolve_scene("BSC_NOPE")


def test_battle_scenes_filter():
    ac = C.battle_scenes("AC_")
    assert ac and all("ac_" in nm.lower() for nm, _ in ac)


# --- thin wrappers + cross-kind search ---------------------------------------
def test_items_and_fields_wrappers():
    its = C.items("potion")
    assert ("Potion".lower() in (n.lower() for _, n in its))
    assert all(n != "NoItem" for _, n in C.items())
    flds = C.fields("alex")
    assert flds and all("alex" in fbg.lower() or "alex" in evt.lower() for fbg, _, evt in flds)


def test_cross_kind_search():
    res = C.search("vivi")
    assert set(res) == {"models", "items", "scenes", "fields"}
    assert any(m.token == "VIV" for m in res["models"])  # GEO_MAIN_F0_VIV surfaces
