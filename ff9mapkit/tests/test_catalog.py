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


# --- npc_anims: model -> the five field-NPC slots (the archetype payoff) ------
def test_npc_anims_vivi_matches_builtin_preset_by_name():
    from ff9mapkit.content.npc import PRESETS
    _model, _animset, preset = PRESETS["vivi"]
    got = C.npc_anims(8)
    assert set(got) == {"stand", "walk", "run", "left", "right"}
    for slot, pid in preset.items():               # same clip NAME as the proven preset (dup-id safe)
        assert C.animation_name(got[slot]) == C.animation_name(pid), slot


def test_npc_anims_complete_model_uses_its_own_clips():
    got = C.npc_anims("GEO_NPC_F0_BAR")
    assert set(got) == {"stand", "walk", "run", "left", "right"}
    assert all(isinstance(v, int) for v in got.values())
    assert all("_BAR_" in C.animation_name(v) for v in got.values())   # BAR token, never a foreign clip


def test_npc_anims_partial_model_falls_back_to_own_clips():
    got = C.npc_anims("GEO_NPC_F0_BRI")            # has only idle + walk
    assert set(got) == {"stand", "walk", "run", "left", "right"}
    assert got["run"] == got["walk"]              # missing run -> walk
    assert got["left"] == got["right"] == got["stand"]   # missing turns -> idle


def test_npc_anims_empty_for_non_field_model():
    assert C.npc_anims(999999) == {}
    mon = next(m for m in C.all_models() if not m.field and not C.animations_for_model(m.id))
    assert C.npc_anims(mon.id) == {}              # a battle-only monster has no field gestures


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


# --- regression lock-ins -----------------------------------------------------
def test_join_matches_build_resolver_for_all_playables():
    """The Info Hub join (backed by _animdb_all) must agree with the BUILD's own gesture resolver
    (animations.catalog, backed by the _animdb MAIN subset) for EVERY playable -- so the two
    independently-regenerated anim tables can't silently drift. Verified: identical {action: id} for
    all 8 main characters."""
    from ff9mapkit import animations as A
    for token in sorted(set(A.TOKENS.values())):
        m = C.model(f"GEO_MAIN_F0_{token}")
        assert m is not None, token
        assert A.catalog(token) == C.animations_for_model(m.id), token


def test_every_field_form_model_has_animations():
    """Every field-form model (the ones you place as a field NPC) resolves to a non-empty gesture set
    via the (group, token) join; the only models with an empty join are battle-form monsters."""
    empty = [m for m in C.all_models() if not C.animations_for_model(m.id)]
    assert all(not m.field for m in empty)                      # no field-form model is empty
    assert all(m.group == "MON" and m.form[:1] == "B" for m in empty)  # the empties are battle monsters


def test_join_id_selection_is_deterministic_min_id():
    """For an action whose clip name is shared by several ids (FF9 dup-id clips), the join returns the
    SMALLEST id, deterministically -- so a future table regen/reorder can't silently change which id an
    author is shown for a gesture."""
    from ff9mapkit._animdb_all import ANIMATIONS
    anims = C.animations_for_model(8)                            # GEO_MAIN_F0_VIV
    for action in ("walk", "run"):
        nm = C.animation_name(anims[action])
        assert anims[action] == min(i for i, n in ANIMATIONS.items() if n == nm)
    assert anims["walk"] == 147 and anims["run"] == 145          # pin the exact ids


def test_animation_name_non_numeric_returns_none():
    """animation_name() honors its 'or None' contract for a non-numeric / None id instead of raising."""
    assert C.animation_name("abc") is None
    assert C.animation_name(None) is None
    assert C.animation_name(7302) == "ANH_MAIN_F0_VIV_TALK_3_1"  # a real id still resolves
