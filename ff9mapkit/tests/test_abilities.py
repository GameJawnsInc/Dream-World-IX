"""The ability id<->token codec + the best-effort name/AP lookup (ff9mapkit.abilities). The codec tests are
pure arithmetic (no install); the name/AP tests are install-gated."""
from __future__ import annotations

import pytest

from ff9mapkit import abilities as A


# ---- the mod-agnostic codec (always available) ------------------------------------------------
@pytest.mark.parametrize("abil_id", [0, 1, 101, 108, 191, 192, 193, 255, 256, 26661, 40146, 65535])
def test_token_round_trips(abil_id):
    assert A.encode_token(A.decode_token(abil_id)) == abil_id


def test_decode_token_active_vs_support():
    assert A.decode_token(101) == "AA:101" and A.kind_of(101) == "AA"
    assert A.decode_token(192) == "SA:0" and A.kind_of(192) == "SA"
    assert A.decode_token(255) == "SA:63"                  # last support id in pool 0
    assert A.decode_token(256) == "AA:192"                 # pool 1, active 0


def test_encode_token_forms():
    assert A.encode_token("AA:108") == 108
    assert A.encode_token("SA:0") == 192
    assert A.encode_token("sa:12") == 204                  # case-insensitive
    assert A.encode_token(108) == 108
    assert A.encode_token("108") == 108                    # digit string == raw id


def test_encode_token_matches_anyability_formula():
    # Memoria CsvParser.AnyAbility: AA -> (X//192)*256 + X%192 ; SA -> (X//64)*256 + X%64 + 192
    for x in (0, 50, 191, 192, 20005):
        assert A.encode_token(f"AA:{x}") == (x // 192) * 256 + x % 192
    for x in (0, 18, 63, 64, 10002):
        assert A.encode_token(f"SA:{x}") == (x // 64) * 256 + x % 64 + 192


def test_encode_token_rejects_garbage():
    for bad in ("", "Fire", "AA:", "XX:5", "AA:-1"):
        with pytest.raises(ValueError):
            A.encode_token(bad)
    with pytest.raises(ValueError):
        A.encode_token(True)


def test_resolve_token_and_id_need_no_install():
    assert A.resolve(0, "AA:108") == 108
    assert A.resolve(None, "SA:0") == 192
    assert A.resolve(0, 192) == 192
    assert A.resolve(0, "192") == 192


# ---- best-effort name + AP (install-gated) ----------------------------------------------------
@pytest.mark.skipif(not A.available(), reason="no FF9 install reachable for ability names")
def test_name_and_ap_from_pool():
    assert len(A.pool_for_preset(0)) > 0                   # Zidane has a pool
    assert A.name_of(108) == "Thievery"                    # base id resolves
    assert A.ap_required(0, 108) == 100
    assert A.resolve(0, "thievery") == 108                 # name (case/space-insensitive)
    assert A.name_of(192, 0) == "Auto-Reflect"


@pytest.mark.skipif(not A.available(), reason="no FF9 install reachable for ability names")
def test_modded_id_falls_back_to_token():
    assert A.name_of(26661) is None                        # not in any base pool -> token-only
    assert A.ap_required(0, 26661) is None
    with pytest.raises(ValueError):
        A.resolve(0, "Definitely Not A Real Ability")
