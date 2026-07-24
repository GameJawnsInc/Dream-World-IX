"""Item stat/effect catalog -- joins the FF9 item-data CSVs from YOUR install (provenance: stats are game
DATA, read live + cached, never committed -- docs/PROVENANCE.md). Pure logic (decoders / CSV parser /
formatters / graceful degradation) runs offline; the real-value join is gated on the install being present.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import itemstats as S


@pytest.fixture(autouse=True)
def _fresh_cache():
    # each test starts with an unloaded cache (so a prior test's load/None doesn't leak) and cleans up after.
    S._reset_cache()
    yield
    S._reset_cache()


# ---- pure decoders --------------------------------------------------------------------------------
def test_decode_elements_bitmask():
    assert S.decode_elements(0) == []
    assert S.decode_elements(1) == ["Fire"]
    assert S.decode_elements(5) == ["Fire", "Thunder"]          # 1 | 4
    assert S.decode_elements(255) == ["Fire", "Ice", "Thunder", "Earth", "Water", "Wind", "Holy", "Dark"]
    assert S.decode_elements("bad") == []                       # never raises


def test_decode_category_omits_the_default_flag():
    assert S.decode_category(1) == ["short-range"]
    assert S.decode_category(5) == ["short-range", "throw"]     # 1 | 4
    assert S.decode_category(128) == []                         # the "Default" no-op flag -> nothing


def test_decode_status_bitmask():
    assert S.decode_status(0) == []
    assert S.decode_status(1) == ["Petrify"]
    assert S.decode_status(256) == ["Death"]                    # 1 << 8
    assert S.decode_status(256 | 65536) == ["Death", "Poison"]  # bit-order: Death (8) before Poison (16)
    assert S.decode_status("x") == []                           # never raises


# ---- the CSV parser (legend detection + comment handling) -----------------------------------------
def test_read_csv_parses_legend_and_skips_comments(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text("#! IncludeId\n# a prose comment\n# Comment;Id;Power\n# ;Int32;Int32\n"
                 "Bonus 0000 # Empty;0;12\nSword;1;99;# 001 - Sword\n", encoding="utf-8")
    cols, rows = S._read_csv(p)
    assert cols == {"Comment": 0, "Id": 1, "Power": 2}          # the names legend, not the '#! Include' / types line
    assert rows[0][0] == "Bonus 0000 # Empty" and rows[0][2] == "12"   # a data row whose col 0 CONTAINS '#'
    assert rows[1][1] == "1" and rows[1][2] == "99"            # trailing '# 001 - Sword' is an extra cell, ignored


# ---- formatters on synthetic records (no install needed) ------------------------------------------
def test_summary_and_facts_for_a_weapon():
    st = S.ItemStat(id=99, name="T", types=["weapon"], price=500, sell=250, equip=["Zidane"],
                    abilities=["AA:1"], power=42, elements=["Fire"], category=["short-range", "throw"])
    S._CACHE = {99: st}
    assert S.summary(99) == "weapon - Atk 42 Fire, 500 gil"
    facts = dict(S.facts(99))
    assert facts["attack"] == "42" and facts["element"] == "Fire"
    assert facts["weapon class"] == "short-range/throw"
    assert facts["equippable by"] == "Zidane" and facts["teaches"] == "AA:1"


def test_summary_and_facts_for_a_consumable_with_bonus_and_affinity():
    st = S.ItemStat(id=98, name="T", types=["item", "usable"], price=50, sell=25,
                    effect_power=10, effect_elements=["Holy"],
                    bonus={"Strength": 3}, affinity={"absorb": ["Fire"]})
    S._CACHE = {98: st}
    s = S.summary(98)
    assert "item/usable" in s and "effect power 10, Holy" in s and "Strength+3" in s
    facts = dict(S.facts(98))
    assert facts["use-effect"] == "power 10, Holy"
    assert facts["stat bonus"] == "Strength+3" and facts["absorb"] == "Fire"


def test_status_only_effect_is_named_not_pow_zero():
    # a cure/revive item has Power 0 and acts via the Status mask -> show the status, NOT a misleading "pow 0".
    st = S.ItemStat(id=97, name="Revive", types=["item", "usable"], price=150, sell=75,
                    effect_power=0, effect_status=256, effect_statuses=["Death"])
    S._CACHE = {97: st}
    assert st.has_use_effect and st.effect_desc() == "status Death"
    assert "effect status Death" in S.summary(97)
    assert dict(S.facts(97))["use-effect"] == "status Death"


def test_empty_effect_row_shows_no_use_effect_line():
    # an item with an EffectId that joined an ALL-ZERO effect row (e.g. a stat accessory) -> no phantom "pow 0".
    st = S.ItemStat(id=96, name="Acc", types=["accessory"], price=10, sell=5,
                    effect_power=0, bonus={"Magic": 2})
    S._CACHE = {96: st}
    assert st.is_consumable and not st.has_use_effect          # has an effect ROW, but nothing worth showing
    assert "effect" not in S.summary(96) and "Magic+2" in S.summary(96)
    assert "use-effect" not in dict(S.facts(96))


# ---- synthesis recipes (the Synthesis.csv join) ---------------------------------------------------
SYNTH_FIXTURE = (
    "#! UseShopList\n"
    "# Comment;Id;Shops;Price;Result;Ingredients\n"
    "# ;Int32;Int32[];UInt32;Int32;Int32[]\n"
    "Butterfly Sword;0;32, 38;300;7;1, 2\n"
    "The Ogre;1;38;700;8;2, 2\n"
    "Unlisted;2;;500;9;1, 255\n"                                # empty Shops (removed) + a NoItem ingredient
)


def _fake_synth_install(tmp_path, monkeypatch, text=SYNTH_FIXTURE):
    d = tmp_path / "StreamingAssets" / "Data" / "Items"
    d.mkdir(parents=True)
    (d / "Synthesis.csv").write_text(text, encoding="utf-8")
    import ff9mapkit.config as cfg
    monkeypatch.setattr(cfg, "find_game_path", lambda *a, **k: tmp_path)


def test_synthesis_join_indexes_result_and_ingredients(tmp_path, monkeypatch):
    _fake_synth_install(tmp_path, monkeypatch)
    made = S.synthesis_of(7)                                    # Butterfly Sword <- Dagger + Mage Masher
    assert len(made) == 1 and made[0].price == 300 and made[0].shops == [32, 38]
    assert made[0].ingredients == [1, 2]
    assert S.synthesis_of(8)[0].ingredients == [2, 2]           # dup ingredient kept (need 2 copies)
    assert {r.result for r in S.synthesis_uses(2)} == {7, 8}    # a dup ingredient indexes its recipe ONCE
    assert [r.result for r in S.synthesis_uses(1)] == [7, 9]
    assert S.synthesis_of(9)[0].shops == []                     # an empty Shops cell = unlisted (removed)
    assert S.synthesis_of(9)[0].ingredients == [1]              # the NoItem (255) ingredient dropped
    assert S.synthesis_of(236) == [] and S.synthesis_uses(236) == []


def test_recipe_desc_names_and_unlisted():
    # names come from items.name_of -- the kit's PascalCase table names ("MageMasher"), as everywhere else
    assert S.recipe_desc(S.SynthRecipe(0, [32, 38], 300, 7, [1, 2])) \
        == "Dagger + MageMasher @ 300 gil (synth shops 32, 38)"
    assert S.recipe_desc(S.SynthRecipe(1, [38], 700, 8, [2, 2])) \
        == "MageMasher + MageMasher @ 700 gil (synth shop 38)"
    assert "no shop (unlisted)" in S.recipe_desc(S.SynthRecipe(2, [], 500, 9, [1]))


def test_facts_include_synthesis_lines(tmp_path, monkeypatch):
    _fake_synth_install(tmp_path, monkeypatch)
    S._CACHE = {7: S.ItemStat(id=7, name="Butterfly Sword", types=["weapon"], power=21),
                2: S.ItemStat(id=2, name="Mage Masher", types=["weapon"], power=14)}
    assert dict(S.facts(7))["synthesize"] == "Dagger + MageMasher @ 300 gil (synth shops 32, 38)"
    assert dict(S.facts(2))["synth ingredient of"] == "ButterflySword, TheOgre"
    assert "synth ingredient of" not in dict(S.facts(7))        # 7 is a result, never an ingredient here


def test_synthesis_unavailable_degrades(monkeypatch):
    import ff9mapkit.config as cfg
    monkeypatch.setattr(cfg, "find_game_path", lambda *a, **k: Path("nonexistent_ff9_dir_xyz"))
    assert S.synthesis_of(7) == [] and S.synthesis_uses(2) == []


@pytest.mark.skipif(not S.available(), reason="needs the FF9 install (StreamingAssets/Data/Items/*.csv)")
def test_synthesis_real_base_join():
    made = S.synthesis_of(7)                                    # the real recipe 0: Butterfly Sword
    assert made and made[0].price == 300 and 38 in made[0].shops
    uses = {r.result for r in S.synthesis_uses(2)}              # Mage Masher feeds the thief-sword tree
    assert 7 in uses and 8 in uses
    facts = dict(S.facts(7))
    assert "synthesize" in facts and "@ 300 gil" in facts["synthesize"]


# ---- graceful degradation when the install isn't reachable ----------------------------------------
def test_unavailable_install_degrades_to_none(monkeypatch):
    import ff9mapkit.config as cfg
    monkeypatch.setattr(cfg, "find_game_path", lambda *a, **k: Path("nonexistent_ff9_dir_xyz"))
    assert S.available() is False
    assert S.for_id(236) is None
    assert S.summary(236) is None
    assert S.facts(236) == []


# ---- the real join (install-gated, mirrors test_forkreport / test_eventscan) ----------------------
def _installed() -> bool:
    try:
        return S.available()
    except Exception:
        return False


@pytest.mark.skipif(not _installed(), reason="needs the FF9 install (StreamingAssets/Data/Items/*.csv)")
def test_real_join_weapon_armor_consumable_accessory():
    dagger = S.for_id(1)                                        # Dagger: a Zidane short-range/throw weapon
    assert dagger.is_weapon and dagger.power == 12 and "Zidane" in dagger.equip and dagger.types == ["weapon"]
    exc = S.for_id(28)                                          # Excalibur: a holy Steiner sword
    assert exc.power == 77 and exc.elements == ["Holy"] and exc.equip == ["Steiner"]
    helm = S.for_id(138)                                        # Iron Helm: head armor, ArmorId 50 (M.Def 7)
    assert helm.is_armor and helm.mdef == 7 and helm.types == ["head"] and "Steiner" in helm.equip
    potion = S.for_id(236)                                      # Potion: a usable item with a use-effect
    assert potion.is_consumable and potion.effect_power == 10 and "usable" in potion.types
    assert not potion.is_weapon and not potion.is_armor


@pytest.mark.skipif(not _installed(), reason="needs the FF9 install (StreamingAssets/Data/Items/*.csv)")
def test_real_summary_and_facts_are_well_formed():
    assert S.summary(28) == "weapon - Atk 77 Holy, 19000 gil"
    facts = dict(S.facts(236))
    assert facts["type"] == "item/usable" and facts["use-effect"].startswith("power 10")
    # a status-only consumable (Phoenix Down, id 240) names the status -- NOT a misleading "pow 0"
    pd = S.for_id(240)
    assert "Death" in pd.effect_statuses and pd.has_use_effect
    assert "status Death" in S.summary(240) and "pow 0" not in S.summary(240)
    # every item resolves to a record (no gaps / no crash across the whole 0-254 space); 255 (NoItem) is skipped
    assert all(S.for_id(i) is not None for i in range(0, 255))
    assert S.for_id(255) is None
