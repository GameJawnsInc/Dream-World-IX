"""Tests for the read-live battle catalogs (battle.battlecsv).

PURE: the committed scriptId catalog + element/status encode<->decode + graceful offline degradation.
INSTALL-GATED: the real Actions.csv / StatusData.csv / StatusSets.csv join.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit.battle import battlecsv as B


def test_script_catalog_known_and_uncatalogued():
    assert B.script_name(9) == "MagicAttack"
    assert B.script_name(19) == "PhysicalAttack"
    assert B.script_name(63) == "MagicSwordAttack"
    assert B.is_stock_script(9) is True
    assert B.is_stock_script(64) is False              # a legacy id not in the externalized catalog
    assert B.script_name(64) == "scriptId 64"          # neutral label (NOT an over-claimed "needs a DLL")


def test_encode_decode_elements():
    assert B.encode_elements(["Fire", "Thunder"]) == 5
    assert B.encode_elements(5) == 5                    # raw int passes through
    assert B.encode_elements([1, "Holy"]) == 1 | 64     # mixed ints + names
    assert set(B.decode_elements(5)) == {"Fire", "Thunder"}
    with pytest.raises(ValueError):
        B.encode_elements(["Nope"])


def test_encode_decode_status():
    assert B.encode_status(["Death"]) == (1 << 8)
    assert B.encode_status(["Petrify", "Death"]) == (1 << 0) | (1 << 8)
    assert B.decode_status((1 << 8)) == ["Death"]
    with pytest.raises(ValueError):
        B.encode_status(["Bogus"])


def test_offline_degrades(monkeypatch):
    from ff9mapkit import config
    monkeypatch.setattr(config, "find_game_path", lambda *a, **k: Path("nonexistent_ff9_dir_xyz"))
    B._reset_cache()
    try:
        assert B.available() is False
        assert B.action(25) is None and B.actions() == []
        assert B.status_set_names(9) == []
    finally:
        B._reset_cache()


def _installed() -> bool:
    B._reset_cache()
    try:
        return B.available()
    finally:
        B._reset_cache()


@pytest.mark.skipif(not _installed(), reason="needs the FF9 install (Data/Battle/*.csv)")
def test_real_actions_join():
    fire = B.action(25)
    assert fire is not None and fire.name == "Fire"
    assert fire.script_id == 9 and "Fire" in fire.elements and fire.mp == 6
    assert "MagicAttack" in fire.summary()
    assert len(B.actions()) >= 192                     # the engine requires 0-191 post-merge
    assert B.action_by_name("Firaga").power > fire.power


@pytest.mark.skipif(not _installed(), reason="needs the FF9 install (Data/Battle/*.csv)")
def test_real_status_sets_resolve_action_status_index():
    silence = B.action(14)                             # the Silence spell
    assert silence is not None
    assert "Silence" in B.status_set_names(silence.status_index)
    # StatusData has 0-32; a known one decodes
    poison = B.status(16)
    assert poison is not None and poison.name.lower().startswith("poison") and poison.tick > 0


def test_target_and_status_list_encoders():
    from ff9mapkit.battle import battlecsv as B
    import pytest as _pt
    assert B.encode_target_type("AllEnemy") == "AllEnemy(8)"
    assert B.encode_target_type("singleenemy") == "SingleEnemy(2)" and B.encode_target_type(3) == "ManyAny(3)"
    assert B.encode_target_display("Mp") == "Mp(2)" and B.encode_target_display(0) == "None(0)"
    assert B.encode_status_list(["Defend", "Poison"]) == "Defend(15), Poison(16)"   # the real base format
    assert B.encode_status_list("Haste") == "Haste(19)"
    assert B.encode_status_list("none") == "" and B.encode_status_list(None) == ""
    for bad in (lambda: B.encode_target_type("Nope"), lambda: B.encode_target_type(99),
                lambda: B.encode_status_list(["Nope"])):
        with _pt.raises(ValueError):
            bad()
