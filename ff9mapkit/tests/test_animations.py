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


# --- build wiring: a named `animation` step resolves via the actor's preset ----------------
def test_resolve_anim_steps_named_and_passthrough():
    actor = {"name": "V", "preset": "vivi"}
    steps = [{"say": "hi"}, {"animation": "glad"}, {"animation": 7302}, {"walk": [0, -100]}]
    out = build._resolve_anim_steps(steps, actor)
    assert out[1]["animation"] == A.resolve("vivi", "glad")   # name -> id
    assert out[2]["animation"] == 7302                        # int untouched
    assert out[0] == {"say": "hi"} and out[3] == {"walk": [0, -100]}


def test_resolve_anim_steps_custom_model_name_is_error():
    actor = {"name": "X", "model": 270}                       # custom model, no preset
    with pytest.raises(ValueError):
        build._resolve_anim_steps([{"animation": "glad"}], actor)
    # but a numeric id is fine even on a custom model
    assert build._resolve_anim_steps([{"animation": 5}], actor) == [{"animation": 5}]


def _cs_toml(anim):
    return ('[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
            '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
            '[[npc]]\nname = "Vivi"\npreset = "vivi"\npos = [0, 0]\n\n'
            '[cutscene]\nactor = "Vivi"\nsteps = [ { animation = "%s" } ]\n' % anim)


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
        '[cutscene]\nactor = "Vivi"\nonce = false\nsteps = [ { animation = "glad" } ]\n', encoding="utf-8")
    out = build.build_mod([build.FieldProject.load(proj_dir / "f.field.toml")], tmp_path / "mod")
    name = out["dictionary"][0].split()[4]
    eb = (tmp_path / "mod").rglob(f"EVT_{name}.eb.bytes")
    data = next(eb).read_bytes()
    glad = A.resolve("vivi", "glad")
    # the resolved RunAnimation(glad) opcode (0x40 + u16 id) appears in the script bytes
    assert opcodes.run_animation(glad) in data
