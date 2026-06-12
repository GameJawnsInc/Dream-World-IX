"""playerswap: swap who you WALK as in a forked field (Tier-A, productionized). Offline against the ALEX100
(Vivi) fixture -- the transform is a pure eb->eb same-length byte patch (memory project-ff9-pc-party-system)."""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import eventscan, playerswap
from ff9mapkit.eb import EbScript

ALEX100 = (Path(__file__).parent / "fixtures" / "alex100-us.eb.bytes").read_bytes()  # field 100, played as Vivi


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
    with pytest.raises(ValueError, match="unknown character"):
        playerswap.resolve_char("kuja")                      # not a field-playable (no F0 player model)


def test_every_character_spec_has_the_movement_set():
    # table integrity: all 8 have model+eye + the 5 always-present movement clips
    for name, spec in playerswap.CHARACTERS.items():
        for key in ("model", "eye", "idle", "walk", "run", "left", "right"):
            assert key in spec, f"{name} missing {key}"


def test_unknown_char_raises_before_touching_bytes():
    with pytest.raises(ValueError):
        playerswap.swap_player(ALEX100, "bogus")
