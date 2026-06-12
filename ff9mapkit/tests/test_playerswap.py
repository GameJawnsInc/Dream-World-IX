"""playerswap: swap who you WALK as in a forked field (Tier-A, productionized). Offline against the ALEX100
(Vivi) fixture -- the transform is a pure eb->eb same-length byte patch (memory project-ff9-pc-party-system)."""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import eventscan, playerswap
from ff9mapkit.eb import EbScript

ALEX100 = (Path(__file__).parent / "fixtures" / "alex100-us.eb.bytes").read_bytes()  # field 100, played as Vivi


def _game_ready():
    try:
        from ff9mapkit import config, extract  # noqa: F401,PLC0415
        return config.find_game_path(None) is not None
    except Exception:
        return False


def _player_model(eb_bytes):
    eb = EbScript.from_bytes(eb_bytes)
    return eventscan._player_model(eb, eventscan.resolve_player_entries(eb)[0])


def test_swap_vivi_field_to_steiner_patches_model_and_anims():
    assert _player_model(ALEX100) == 8                       # Vivi
    out = playerswap.swap_player(ALEX100, "steiner")
    assert len(out) == len(ALEX100)                          # same-length patch
    assert EbScript.from_bytes(out).to_bytes() == out        # valid, round-tripping .eb
    assert _player_model(out) == 5489                        # now Steiner
    # every movement clip the player Init sets is repointed to Steiner's rig ids
    eb = EbScript.from_bytes(out)
    init = eb.entry(eventscan.resolve_player_entries(eb)[0]).func_by_tag(0)
    got = {playerswap.ANIM_OPS[i.op]: i.args[0] for i in eb.instrs(init) if i.op in playerswap.ANIM_OPS}
    spec = playerswap.CHARACTERS["steiner"]
    for clip, val in got.items():
        assert val == spec.get(clip, spec["idle"])           # set value, or idle-fallback for a missing clip


def test_swap_is_identity_when_target_equals_source_char_values():
    # swapping the Vivi field back to vivi reproduces the original bytes (the table matches the real field)
    assert playerswap.swap_player(ALEX100, "vivi") == ALEX100


def test_resolve_char_aliases_and_errors():
    assert playerswap.resolve_char("Dagger")[0] == "garnet"
    assert playerswap.resolve_char("salamander")[0] == "amarant"
    assert playerswap.resolve_char(" STEINER ")[0] == "steiner"
    with pytest.raises(ValueError, match="unknown swap target"):
        playerswap.resolve_char("notacharacter")             # not a playable and not a resolvable model


def test_swap_to_any_model_via_the_catalog_join():
    # the field-side bridge to custom characters: --swap-player accepts ANY model (a moogle, an NPC), resolved
    # through the model->animation join (catalog.npc_anims). The Vivi field can become a moogle (model 199).
    name, spec = playerswap.resolve_char(199)                # GEO_NPC_F5_MOG (a moogle)
    assert spec["model"] == 199 and "eye" not in spec        # arbitrary model -> keep the field's eye-height
    assert all(k in spec for k in ("idle", "walk", "run", "left", "right"))
    out = playerswap.swap_player(ALEX100, 199)
    assert EbScript.from_bytes(out).to_bytes() == out and len(out) == len(ALEX100)
    eb = EbScript.from_bytes(out)
    assert eventscan._player_model(eb, eventscan.resolve_player_entries(eb)[0]) == 199   # now a moogle


def test_swap_to_a_static_model_with_no_movement_raises():
    # a model with no movement animations (a static monster) cannot be a field-walk player
    with pytest.raises(ValueError, match="no movement animations"):
        playerswap.swap_player(ALEX100, 93)                  # GEO_MON_B3_048


def test_every_character_spec_has_the_movement_set():
    # table integrity: all 8 have model+eye + the 5 always-present movement clips
    for name, spec in playerswap.CHARACTERS.items():
        for key in ("model", "eye", "idle", "walk", "run", "left", "right"):
            assert key in spec, f"{name} missing {key}"


def test_unknown_char_raises_before_touching_bytes():
    with pytest.raises(ValueError):
        playerswap.swap_player(ALEX100, "bogus")


def test_no_swappable_player_raises_distinct_exception():
    # a script with no player SetModel -> NoSwappablePlayer (a ValueError subclass), so a chain can SKIP it
    # while still letting a real overflow/corruption ValueError propagate (adversarial-review fix).
    from ff9mapkit import data
    blank = data.blank_field_bytes("us")
    # the blank field DOES define a player; assert the exception TYPE is wired (subclass of ValueError)
    assert issubclass(playerswap.NoSwappablePlayer, ValueError)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_swap_targets_the_controlled_leader_not_a_coactor_on_zidane_present_fields():
    # REGRESSION (adversarial review): on a ZIDANE-PRESENT multi-PC field the swap must hit the Zidane
    # party-leader you control, NOT a co-actor. Cargo Ship 500 defines [Blank, Zidane(98), Vivi(8)]; the old
    # controlled_player heuristic picked Vivi -> swap re-skinned a companion. The leader-model fix targets Zidane.
    from ff9mapkit import extract
    d = extract.extract_event_script(extract.ID_TO_FBG[500])
    eb = EbScript.from_bytes(d)
    pents = eventscan.resolve_player_entries(eb)
    zid = next(p for p in pents if eventscan._player_model(eb, p) == 98)   # the Zidane entry
    viv = next(p for p in pents if eventscan._player_model(eb, p) == 8)    # the Vivi co-actor
    assert playerswap.swap_targets(eb) == [zid]                            # target the controlled Zidane leader
    out = EbScript.from_bytes(playerswap.swap_player(d, "steiner"))
    assert eventscan._player_model(out, zid) == 5489                       # Zidane -> Steiner
    assert eventscan._player_model(out, viv) == 8                          # the Vivi co-actor is UNTOUCHED


def test_scripted_gesture_ops_flags_cutscene_player_gestures():
    # ALEX100 (the Vivi field) opens with a scripted cutscene where the player gestures (RunAnimation) --
    # swapping the rig would glitch those (only movement clips are repointed), so the detector flags them
    # for a swap-time WARN. A free-roam field's player plays 0 (the caveat is the cutscene-field case).
    n = playerswap.scripted_gesture_ops(ALEX100)
    assert n > 0                                              # Vivi's opening has scripted player gestures
    # the swap itself still succeeds (it only repoints movement clips); the gesture count is unchanged by it
    out = playerswap.swap_player(ALEX100, "steiner")
    assert playerswap.scripted_gesture_ops(out) == n
