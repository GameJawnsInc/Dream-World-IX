"""Character animation catalog: pick a cutscene gesture by name. Pure (no game install needed) --
backed by the baked _animdb (Memoria's open-source AnimationDB). Also covers the build wiring that
resolves a named `animation` step to its numeric id via the actor NPC's preset."""
from __future__ import annotations

import pytest

from ff9mapkit import animations as A
from ff9mapkit import build


def test_token_normalization():
    assert A._token("VIV") == "VIV"          # a raw token
    assert A._token("vivi") == "VIV"         # a preset
    assert A._token("dagger") == "GRN"       # a friendly alias
    with pytest.raises(ValueError):
        A._token("gandalf")


def test_resolve_core_action_and_passthrough():
    assert A.resolve("vivi", "idle") == 148              # CORE alias -> the standard IDLE id
    assert A.resolve("vivi", "turn_left") == A.resolve("vivi", "TURN_L")
    assert isinstance(A.resolve("vivi", "TALK_3_1"), int)   # an action label (case-insensitive)
    assert A.resolve("vivi", 7302) == 7302              # a raw id passes through
    assert A.resolve("vivi", "902") == 902              # a numeric string passes through
    assert A.name_of(7302) == "ANH_MAIN_F0_VIV_TALK_3_1"


def test_resolve_unknown_raises_with_hints():
    with pytest.raises(ValueError) as e:
        A.resolve("vivi", "moonwalk")
    assert "moonwalk" in str(e.value)


def test_every_character_has_core_gestures():
    for ch in ("vivi", "zidane", "garnet", "steiner", "freya", "quina", "eiko", "amarant"):
        cat = A.catalog(ch)
        for core in ("idle", "walk", "run", "turn_l", "turn_r"):
            assert core in cat, f"{ch} missing {core}"


def test_duplicate_named_ids_collapse_to_one_action():
    # 7301 and 7302 are BOTH "ANH_MAIN_F0_VIV_TALK_3_1"; the engine plays by name so either id is the
    # same clip. The catalog exposes the action once and resolves to a valid id.
    assert A.name_of(7301) == A.name_of(7302)
    assert A.resolve("vivi", "talk_3_1") in (7301, 7302)


# --- build wiring: a named `animation` step resolves via the STEP's actor preset -----------
def test_resolve_conductor_steps_animation_names_and_cast_default():
    """#13 v3: animation names resolve per the STEP's actor model; a cast of ONE fills the actor tag on
    untagged actor steps (migration ergonomics -- a renamed single-actor scene needs no per-step edits)."""
    import types
    project = types.SimpleNamespace(raw={"npc": [{"name": "V", "preset": "vivi"}], "player": {}, "marker": []})
    steps = [{"say": "hi"}, {"animation": "glad"}, {"animation": 7302}]
    out = build._resolve_conductor_steps(steps, project, cast=["V"])
    assert out[1]["animation"] == A.resolve("vivi", "glad")   # name -> id
    assert out[1]["actor"] == "V"                             # the sole-cast default filled the tag
    assert out[2]["animation"] == 7302                        # int untouched
    assert out[0] == {"say": "hi"}                            # untagged say stays narration (no actor fill)


def test_resolve_conductor_steps_custom_model_name_is_error():
    import types
    project = types.SimpleNamespace(raw={"npc": [{"name": "X", "model": 270}], "player": {}, "marker": []})
    with pytest.raises(ValueError):        # 'glad' is a VIV action -- Cid's rig cannot play it under any name
        build._resolve_conductor_steps([{"animation": "glad"}], project, cast=["X"])
    # but a numeric id is fine even on a custom model
    out = build._resolve_conductor_steps([{"animation": 5}], project, cast=["X"])
    assert out[0]["animation"] == 5


# --- the MODEL actor path: a gesture name for an actor with no playable preset --------------
def _proj(npcs, player=None):
    import types
    return types.SimpleNamespace(raw={"npc": npcs, "player": player or {}, "marker": []})


def test_a_model_actor_resolves_a_gesture_name_through_its_own_rig():
    """FORMAT.md's documented gap: a name used to REQUIRE a playable preset, so every NPC wearing a
    plain model had to hand-hunt numeric ids. It resolves through the model the block wears now --
    own-form first, because a different form is a different skeleton."""
    from ff9mapkit import catalog as C
    project = _proj([{"name": "Cid", "model": "GEO_SUB_F0_CID"}])
    out = build._resolve_conductor_steps([{"animation": "talk_1_1"}], project, cast=["Cid"])
    assert out[0]["animation"] == C.own_form_gestures("GEO_SUB_F0_CID")["talk_1_1"]


def test_a_model_actor_takes_the_shared_alias_words_too():
    """ONE alias table (animations.CORE): 'idle'/'stand'/'left' mean the same gesture whether the actor
    is a playable preset or a plain rig -- otherwise 'walk' would work on Vivi and fail on the innkeeper."""
    from ff9mapkit import catalog as C
    project = _proj([{"name": "Cid", "model": "GEO_SUB_F0_CID"}])
    steps = build._resolve_conductor_steps([{"animation": "stand"}, {"animation": "left"}],
                                           project, cast=["Cid"])
    assert steps[0]["animation"] == C.own_form_gestures("GEO_SUB_F0_CID")["idle"]
    assert steps[1]["animation"] == C.npc_anims("GEO_SUB_F0_CID")["left"], \
        "a turn is one of the five MOVEMENT slots -- the one place the any-form join is proven"
    assert A.normalize_action("Turn-Left") == "turn_l" == A.normalize_action("left")


def test_an_archetype_actor_resolves_through_the_archetype_model():
    """A preset/archetype NPC's clips belong to the ARCHETYPE's model, not to an absent `model =` --
    the precedence the build spends (blockmodel.resolve_block_model), not a second guess."""
    from ff9mapkit import archetypes, catalog as C
    mid = archetypes.resolve("moogle")[0]
    project = _proj([{"name": "Mog", "archetype": "moogle"}])
    out = build._resolve_conductor_steps([{"animation": "idle"}], project, cast=["Mog"])
    assert out[0]["animation"] == C.own_form_gestures(mid)["idle"]


def test_a_cross_form_gesture_name_is_refused_with_the_own_form_options():
    """THE CROSS-FORM CLIP TRAP: a one-shot on another form's skeleton twists the model in-game, so a
    name only the any-form join answers must fail LOUDLY, listing what the rig can actually play."""
    from ff9mapkit import catalog as C
    geo = "GEO_NPC_F1_CSO"
    cross = set(C.animations_for_model(geo)) - set(C.own_form_gestures(geo))
    assert cross, "GEO_NPC_F1_CSO no longer has cross-form clips -- pick another rig for this fence"
    name = sorted(cross)[0]
    project = _proj([{"name": "Soldier", "model": geo}])
    with pytest.raises(ValueError) as e:
        build._resolve_conductor_steps([{"animation": name}], project, cast=["Soldier"])
    assert "CROSS-FORM" in str(e.value) and "Own-form gestures" in str(e.value)


def test_the_player_actor_resolves_against_the_player_block():
    """The player actor used to error on ANY name: it has no [[npc]] block, so the 'no preset' branch
    caught it. Its model is [player] model=, and its absence means the stock avatar (Zidane)."""
    from ff9mapkit import blockmodel, catalog as C
    default = C.own_form_gestures(blockmodel.PLAYER_DEFAULT_GEO)
    out = build._resolve_conductor_steps([{"animation": "idle"}], _proj([]), cast=["player"])
    assert out[0]["animation"] == default["idle"]
    skinned = _proj([], player={"model": "GEO_SUB_F0_CID"})
    out = build._resolve_conductor_steps([{"animation": "talk_1_1"}], skinned, cast=["player"])
    assert out[0]["animation"] == C.own_form_gestures("GEO_SUB_F0_CID")["talk_1_1"]


def test_a_preset_actor_still_resolves_exactly_as_before():
    """The fence under the whole change: every shipped scene's bytes are the preset path's, and the
    preset path is untouched (a model fallback that shadowed it would silently re-point real fields)."""
    project = _proj([{"name": "V", "preset": "vivi", "model": "GEO_SUB_F0_CID"}])
    out = build._resolve_conductor_steps([{"animation": "glad"}], project, cast=["V"])
    assert out[0]["animation"] == A.resolve("vivi", "glad"), \
        "a preset actor resolves through its CHARACTER catalog even when a model= is also present"


def test_lint_and_build_agree_on_a_model_actor(tmp_path):
    """What lints clean must BUILD: _validate_conductor runs the very same resolver now."""
    good = ('[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
            '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
            '[[npc]]\nname = "Cid"\nmodel = "GEO_SUB_F0_CID"\npos = [0, 0]\n\n'
            '[cutscene]\nactors = ["Cid"]\nsteps = [ { animation = "%s" } ]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(good % "talk_1_1", encoding="utf-8")
    assert not [m for m in build.validate(build.FieldProject.load(p)) if "animation" in m]
    p.write_text(good % "definitely_not_a_clip", encoding="utf-8")
    assert any("definitely_not_a_clip" in m for m in build.validate(build.FieldProject.load(p)))


def _cs_toml(anim):
    return ('[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
            '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
            '[[npc]]\nname = "Vivi"\npreset = "vivi"\npos = [0, 0]\n\n'
            '[cutscene]\nactors = ["Vivi"]\nsteps = [ { animation = "%s" } ]\n' % anim)


def test_validate_flags_bad_animation_name(tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(_cs_toml("definitely_not_an_anim"), encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("definitely_not_an_anim" in m for m in probs)


def test_validate_accepts_good_animation_name(tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(_cs_toml("glad"), encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert not any("animation" in m and "glad" in m for m in probs)


def test_full_build_emits_resolved_animation(tmp_path):
    """End-to-end: a [cutscene] with animation = "glad" compiles, and the actor's choreography carries
    the resolved RunAnimation(id). Needs the extracted blank .eb template."""
    from ff9mapkit import provision
    if not provision.templates_present():
        pytest.skip("base templates not extracted (run `ff9mapkit extract-templates`)")
    from ff9mapkit.eb import EbScript, disasm
    from ff9mapkit.eb import opcodes
    from ff9mapkit.config import LANGS
    proj_dir = tmp_path / "room"
    proj_dir.mkdir()
    # a buildable custom-scene field (synth camera + quad walkmesh, no art) with an actor cutscene
    (proj_dir / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "ANIMT"\narea = 11\n\n'
        '[camera]\npitch = 48.0\ndistance = 4500\nfov = 42.2\n[camera.frame]\nback = 205\nfront = 432\n\n'
        '[walkmesh]\nquad = [[-500, 200], [500, 200], [500, -800], [-500, -800]]\nframe = "world"\n\n'
        '[[npc]]\nname = "Vivi"\npreset = "vivi"\npos = [0, -300]\n\n'
        '[cutscene]\nactors = ["Vivi"]\nonce = false\nsteps = [ { animation = "glad" } ]\n', encoding="utf-8")
    out = build.build_mod([build.FieldProject.load(proj_dir / "f.field.toml")], tmp_path / "mod")
    name = out["dictionary"][0].split()[4]
    eb = (tmp_path / "mod").rglob(f"EVT_{name}.eb.bytes")
    data = next(eb).read_bytes()
    glad = A.resolve("vivi", "glad")
    # the resolved id appears as a by-uid RunAnimationEx (0xBD <uid> <u16 id>) -- the conductor drives the
    # actor by uid (#13 v3; the old in-context RunAnimation splice is gone)
    import re, struct
    assert re.search(re.escape(bytes([0xBD])) + b".." + re.escape(struct.pack("<H", glad)), data, re.S)
