"""[[synthesis]] -- author a custom SYNTHESIS shop: recipes (a Synthesis.csv delta) + the Menu(2,id) opener.

A shop id opens as Synthesis iff it is NOT in ShopItems.csv (ff9buy.FF9Buy_GetType); a shop's recipes = every
Synthesis.csv (FF9MIX_DATA) row whose `Shops` contains the id. The engine MERGES recipes by Id (whole-row), so a
delta = the base header (`#! UseShopList` + legend) VERBATIM + minted rows (ids above the base max). These tests
pin the recipe builder with synthetic base text (install-free), plus validate + an install-gated end-to-end.
"""
from __future__ import annotations

import pytest

from ff9mapkit import items as _items
from ff9mapkit import itemstats as _itemstats
from ff9mapkit.content import synthesis as SY
from ff9mapkit.build import FieldProject, validate, _emit_synthesis
from ff9mapkit.config import ModLayout

BSWORD = _items.resolve("Butterfly Sword")   # 7
OGRE = _items.resolve("The Ogre")            # 8
EXPLODA = _items.resolve("Exploda")          # 9
DAGGER = _items.resolve("Dagger")            # 1
MM = _items.resolve("Mage Masher")           # 2

# synthetic base Synthesis.csv: 2 recipes (ids 0,1) -> a mint lands at id 2. `#! UseShopList` => Shops = Int32[].
SYNTH_CSV = (
    "#! UseShopList\n"
    "# Comment;Id;Shops;Price;Result;Ingredients\n"
    "# ;Int32;Int32[];UInt32;Int32;Int32[]\n"
    f"Butterfly Sword;0;32, 38;300;{BSWORD};{DAGGER}, {MM}\n"
    f"The Ogre;1;38;700;{OGRE};{MM}, {MM}\n"
)


def _rows(text):
    from ff9mapkit.content.itemdata import read_base_csv
    return read_base_csv(text)


# ---- base id + recipe minting ------------------------------------------------------------------
def test_base_max_id():
    assert SY.base_max_id(SYNTH_CSV) == 1
    assert SY.base_max_id("#! UseShopList\n# Comment;Id;Shops;Price;Result;Ingredients\n") == -1   # no rows


def test_recipe_rows_mints_above_base():
    blocks = [{"shop": 40, "recipes": [{"result": "Exploda", "ingredients": ["Mage Masher", "Dagger"], "price": 999}]}]
    rows = SY.recipe_rows(blocks, SYNTH_CSV)
    assert len(rows) == 1
    rid, shop, price, result, ingr, comment = rows[0]
    assert rid == 2 and shop == 40 and price == 999 and result == EXPLODA and ingr == [MM, DAGGER]
    assert comment == "Exploda"                          # comment defaults to the result's name


def test_recipe_rows_monotonic_across_blocks_and_recipes():
    blocks = [
        {"shop": 40, "recipes": [{"result": "Exploda", "ingredients": ["Dagger"], "price": 1},
                                 {"result": "Butterfly Sword", "ingredients": ["Mage Masher"], "price": 2}]},
        {"shop": 41, "recipes": [{"result": "The Ogre", "ingredients": ["Dagger"], "price": 3}]},
    ]
    rows = SY.recipe_rows(blocks, SYNTH_CSV)
    assert [r[0] for r in rows] == [2, 3, 4]              # minted ids monotonic, no reuse
    assert [r[1] for r in rows] == [40, 40, 41]           # shop carried per block


def test_recipe_rows_keeps_duplicate_ingredients_drops_noitem():
    # two Mage Mashers = need 2 (dups kept, unlike a shop's sells); a NoItem (255) ingredient is dropped
    blocks = [{"shop": 40, "recipes": [{"result": "Exploda", "ingredients": ["Mage Masher", "Mage Masher", 255]}]}]
    rows = SY.recipe_rows(blocks, SYNTH_CSV)
    assert rows[0][4] == [MM, MM]                         # dup kept, NoItem dropped


def test_recipe_rows_skips_empty_recipe():
    # no real result or no real ingredient -> skipped (lint flags it); does not consume a mint id
    blocks = [{"shop": 40, "recipes": [{"result": 255, "ingredients": ["Dagger"]},          # NoItem result
                                       {"result": "Exploda", "ingredients": [255]},          # all-NoItem ingredients
                                       {"result": "Exploda", "ingredients": ["Dagger"]}]}]   # valid
    rows = SY.recipe_rows(blocks, SYNTH_CSV)
    assert len(rows) == 1 and rows[0][0] == 2            # only the valid one, minted at 2 (skips don't burn ids)


def test_recipe_rows_clamps_price():
    blocks = [{"shop": 40, "recipes": [{"result": "Exploda", "ingredients": ["Dagger"], "price": 99_999_999}]}]
    assert SY.recipe_rows(blocks, SYNTH_CSV)[0][2] == SY.PRICE_CAP


def test_recipe_rows_empty():
    assert SY.recipe_rows([], SYNTH_CSV) == []


# ---- render (the Synthesis.csv delta text) ----------------------------------------------------
def test_render_preserves_useshoplist_header():
    blocks = [{"shop": 40, "recipes": [{"result": "Exploda", "ingredients": ["Dagger", "Mage Masher"], "price": 50}]}]
    out = SY.render_synthesis(blocks, SYNTH_CSV)
    assert "#! UseShopList" in out                        # ★ load-bearing: else Shops parses as a byte bitmask
    assert "Comment;Id;Shops;Price;Result;Ingredients" in out


def test_render_row_format():
    blocks = [{"shop": 40, "recipes": [{"result": "Exploda", "ingredients": ["Dagger", "Mage Masher"], "price": 50}]}]
    out = SY.render_synthesis(blocks, SYNTH_CSV)
    _h, cols, _idc, rows = _rows(out)
    row = rows[2].split(";")                              # minted id 2
    assert row[cols["Shops"]] == "40" and row[cols["Price"]] == "50"
    assert row[cols["Result"]] == str(EXPLODA) and row[cols["Ingredients"]].strip() == f"{DAGGER}, {MM}"
    assert row[0] == "Exploda" and 0 not in rows and 1 not in rows   # comment col + base rows NOT re-emitted


# ---- validate ([[synthesis]]) ------------------------------------------------------------------
BASE = """
[field]
id = 4003
name = "SYNTHTEST"
area = 11
text_block = 1073
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[player]
spawn = [0, -300]
"""


def _proj(toml, tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return FieldProject.load(p)


def test_validate_no_shop_and_no_recipes(tmp_path):
    probs = validate(_proj(BASE + '\n[[synthesis]]\nrecipes = []\n', tmp_path))
    assert any("[[synthesis]] #0 needs an integer `shop`" in p for p in probs)


def test_validate_shop_out_of_range(tmp_path):
    probs = validate(_proj(BASE + '\n[[synthesis]]\nshop = 5\nrecipes = [{result="Exploda",ingredients=["Dagger"]}]\n',
                           tmp_path))
    assert any("out of range" in p and "BUY shops" in p for p in probs)


def test_validate_shop_collides_with_buy_shop(tmp_path):
    toml = (BASE + '\n[[shop]]\nid = 40\nsells = ["Potion"]\n'
            + '\n[[synthesis]]\nshop = 40\nrecipes = [{result="Exploda",ingredients=["Dagger"]}]\n')
    probs = validate(_proj(toml, tmp_path))
    assert any("is also a [[shop]] id" in p for p in probs)


def test_validate_empty_recipes(tmp_path):
    probs = validate(_proj(BASE + '\n[[synthesis]]\nshop = 40\nrecipes = []\n', tmp_path))
    assert any("has no `recipes`" in p for p in probs)


def test_validate_recipe_bad_result_and_ingredients(tmp_path):
    toml = (BASE + '\n[[synthesis]]\nshop = 40\nrecipes = ['
            '{result="Definitely Not An Item", ingredients=["Dagger"]}, '
            '{result="Exploda", price=-5}]\n')
    probs = validate(_proj(toml, tmp_path))
    assert any("recipe #0 result:" in p and "Definitely Not An Item" in p for p in probs)
    assert any("recipe #1 needs `ingredients`" in p for p in probs)
    assert any("recipe #1 price cannot be negative" in p for p in probs)


def test_validate_zone_bad(tmp_path):
    toml = (BASE + '\n[[synthesis]]\nshop = 40\nzone = [[0,0],[1,1]]\n'
            'recipes = [{result="Exploda", ingredients=["Dagger"]}]\n')
    probs = validate(_proj(toml, tmp_path))
    assert any("zone must have 4 or 5 points" in p for p in probs)


def test_validate_clean(tmp_path):
    toml = (BASE + '\n[[synthesis]]\nshop = 40\n'
            'recipes = [{result="Exploda", ingredients=["Mage Masher","Dagger"], price=999}]\n')
    probs = validate(_proj(toml, tmp_path))
    assert not any("[[synthesis]]" in p for p in probs)


def test_validate_scalar_zone_no_crash(tmp_path):
    # review (low): a non-list zone must be a clean lint PROBLEM, never a TypeError from len()
    toml = (BASE + '\n[[synthesis]]\nshop = 40\nzone = 5\n'
            'recipes = [{result="Exploda", ingredients=["Dagger"]}]\n')
    probs = validate(_proj(toml, tmp_path))
    assert any("zone must have 4 or 5 points" in p for p in probs)


def test_validate_string_ingredients_no_per_char_noise(tmp_path):
    # review (nit): a bare-string ingredients = one clean "must be a list", not per-character 'unknown item' noise
    toml = BASE + '\n[[synthesis]]\nshop = 40\nrecipes = [{result="Exploda", ingredients="Dagger"}]\n'
    probs = validate(_proj(toml, tmp_path))
    assert any("ingredients must be a list" in p for p in probs)
    assert not any("unknown item 'D'" in p for p in probs)


def test_emit_synthesis_no_install_warns_not_crashes(tmp_path, monkeypatch):
    # review (medium): ConfigError (no resolvable install) must be caught -> a warn+skip, not an escaped crash
    from ff9mapkit import config as _config

    def _boom(game=None):
        raise _config.ConfigError("no install")
    monkeypatch.setattr(_config, "find_game_path", _boom)

    class P:
        raw = {"synthesis": [{"shop": 40, "recipes": [{"result": "Exploda", "ingredients": ["Dagger"]}]}]}
        path = tmp_path / "f.toml"
    warns = _emit_synthesis([P()], ModLayout(tmp_path / "mod"))   # must NOT raise ConfigError
    assert any("skipped" in w for w in warns)


# ---- install-gated end-to-end (reads the real base Synthesis.csv) -----------------------------
@pytest.mark.skipif(not _itemstats.available(), reason="write_synthesis reads the install's base Synthesis.csv")
def test_emit_synthesis_writes_delta(tmp_path):
    class P:
        raw = {"synthesis": [{"shop": 40, "recipes": [
            {"result": "Exploda", "ingredients": ["Mage Masher", "Dagger"], "price": 1234}]}]}
        path = tmp_path / "f.toml"
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_synthesis([P()], layout)
    assert not [w for w in warns if "skipped" in w]
    assert layout.synthesis_csv.exists()
    text = layout.synthesis_csv.read_text(encoding="cp1252")
    assert "#! UseShopList" in text                       # header preserved
    _h, cols, _idc, rows = _rows(text)
    # the minted recipe lands above the base max (vanilla base has ids 0-63 -> id >= 64)
    minted = [r for rid, r in rows.items() if rid >= 64]
    assert minted, "a recipe should be minted above the base max id"
    row = minted[0].split(";")
    assert row[cols["Shops"]] == "40" and row[cols["Price"]] == "1234" and row[cols["Result"]] == str(EXPLODA)


@pytest.mark.skipif(not _itemstats.available(), reason="reads the install's base Synthesis.csv")
def test_emit_synthesis_warns_on_buy_collision(tmp_path):
    class P:
        raw = {"shop": [{"id": 40, "sells": ["Potion"]}],
               "synthesis": [{"shop": 40, "recipes": [{"result": "Exploda", "ingredients": ["Dagger"]}]}]}
        path = tmp_path / "f.toml"
    warns = _emit_synthesis([P()], ModLayout(tmp_path / "mod"))
    assert any("is ALSO a [[shop]] buy id" in w for w in warns)
