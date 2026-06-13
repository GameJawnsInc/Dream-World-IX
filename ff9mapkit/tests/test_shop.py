"""[[shop]] -- author a custom shop: its inventory (a ShopItems.csv delta) + an opener.

Two channels, like every item feature on this branch: the INVENTORY is a mod-global ``ShopItems.csv`` delta
(merged by id over the base, which supplies shops 0-31), and the OPENER is ``Menu(2, shopId)`` (0x75 -> case
2u -> OpenShopMenu) -- either a shopkeeper NPC (``[[npc]] opens_shop = id``) or a standalone press-region (the
save-point shape). These tests pin the opener bytecode, the CSV delta (name resolution / dedup / sort / format),
the build integration (NPC talk body + standalone region + CSV emitted at mod-write), byte-identity when absent,
validation, and the cross-field warnings (dup id / vanilla override / dangling opens_shop).
"""
from __future__ import annotations

import pytest

from ff9mapkit.build import FieldProject, build_mod, validate, _emit_shops
from ff9mapkit.config import ModLayout
from ff9mapkit.content import shop
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit import items as _items

BASE = """
[field]
id = 4003
name = "SHOPROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


# ---- opener bytecode --------------------------------------------------------------------------
def test_open_shop_is_menu_2_id():
    # Menu(2, id): op 0x75, arg-flag 0x00, menu_id 0x02, sub_id = the shop id (cf. menu(4,0) = 75 00 04 00)
    assert shop.open_shop(40) == bytes([0x75, 0x00, 0x02, 40])
    assert shop.open_shop(40) == opcodes.menu(2, 40)


def test_shop_speak_body_greeting_optional():
    # no greeting -> straight to the shop, then RETURN
    assert shop.shop_speak_body(40) == shop.open_shop(40) + opcodes.RETURN
    # with a greeting -> window first, then the shop
    body = shop.shop_speak_body(40, greeting_txid=63)
    assert body == opcodes.window_sync(1, 128, 63) + shop.open_shop(40) + opcodes.RETURN


def test_shop_dispatch_locks_control():
    # the press-region action brackets the menu in DisableMove/EnableMove (mirrors save_dispatch)
    assert shop.shop_dispatch(40) == (opcodes.DISABLE_MOVE + shop.open_shop(40)
                                      + opcodes.ENABLE_MOVE + opcodes.RETURN)


# ---- inventory CSV ----------------------------------------------------------------------------
def test_shop_rows_resolve_dedup_sort():
    rows = shop.shop_rows([
        {"id": 41, "sells": ["Tent"]},
        {"id": 40, "sells": ["Potion", "Potion", "Phoenix Down"], "comment": "Hut Shop"},
    ])
    # sorted by id
    assert [r[0] for r in rows] == [40, 41]
    # names resolved, duplicate Potion collapsed (order-preserving)
    pid, pdn = _items.resolve("Potion"), _items.resolve("Phoenix Down")
    assert rows[0] == (40, [pid, pdn], "Hut Shop")
    # default comment when omitted
    assert rows[1][2] == "Shop 0041"


def test_shop_rows_drop_noitem():
    rows = shop.shop_rows([{"id": 40, "sells": ["Potion", 255, "Tent"]}])
    assert shop.NO_ITEM not in rows[0][1]
    assert rows[0][1] == [_items.resolve("Potion"), _items.resolve("Tent")]


def test_shop_rows_dup_id_last_wins():
    rows = shop.shop_rows([{"id": 40, "sells": ["Potion"]}, {"id": 40, "sells": ["Tent"]}])
    assert len(rows) == 1
    assert rows[0][1] == [_items.resolve("Tent")]


def test_render_shop_items_format():
    text = shop.render_shop_items([{"id": 40, "sells": ["Potion", "Tent"], "comment": "Hut Shop"}])
    assert text.startswith("# ff9mapkit [[shop]]")
    pid, tid = _items.resolve("Potion"), _items.resolve("Tent")
    assert f"Hut Shop;40;{pid}, {tid};# Potion, Tent" in text
    assert text.endswith("\n")


# ---- comment sanitization (CSV column-0 safety) -----------------------------------------------
def test_safe_comment_strips_delimiters():
    # a ';' would split the row (mis-parse the Id column); a leading '#' makes the engine skip the line
    assert ";" not in shop.safe_comment("Bob; the Merchant", 40)
    assert shop.safe_comment("Bob; the Merchant", 40) == "Bob, the Merchant"
    assert not shop.safe_comment("#1 Item Shop", 40).startswith("#")
    assert "\n" not in shop.safe_comment("line1\nline2", 40)
    assert shop.safe_comment("", 40) == "Shop 0040"          # empty -> default label
    assert shop.safe_comment("###", 40) == "Shop 0040"       # all-stripped -> default label


def test_render_shop_items_sanitizes_nasty_comment():
    text = shop.render_shop_items([{"id": 40, "sells": ["Potion"], "comment": "#Cheap; deals"}])
    row = [ln for ln in text.splitlines() if ln and not ln.startswith("#")][0]
    assert not row.startswith("#")                            # the data row never begins with '#'
    assert row.split(";")[1] == "40"                          # the Id column is intact (no stray ';' shifted it)


# ---- build integration ------------------------------------------------------------------------
def _build(tmp_path, toml: str):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    layout = ModLayout(out)
    eb = EbScript.from_bytes(layout.eb_path("us", "EVT_SHOPROOM.eb.bytes").read_bytes())
    return eb, layout


SHOP_BLOCK = '\n[[shop]]\nid = 40\ncomment = "Hut Shop"\nsells = ["Potion", "Hi-Potion", "Tent"]\n'


def test_npc_opens_shop_injects_menu(tmp_path):
    toml = BASE + SHOP_BLOCK + (
        '\n[[npc]]\nname = "Shopkeeper"\npos = [0, -600]\n'
        'dialogue = "Welcome!"\nopens_shop = 40\n')
    eb, layout = _build(tmp_path, toml)
    assert shop.open_shop(40) in eb.data                  # the talk body opens the shop
    assert list(eb.instrs(eb.entry(0).func_by_tag(0)))    # Main_Init still parses
    # the inventory CSV was written at the mod-write stage
    assert layout.shop_items_csv.is_file()
    assert "Hut Shop;40;" in layout.shop_items_csv.read_text(encoding="utf-8")


def test_standalone_zone_region_injects_opener(tmp_path):
    toml = BASE + (
        '\n[[shop]]\nid = 45\nsells = ["Potion", "Ether"]\n'
        'zone = [[-300, -700], [300, -700], [300, -400], [-300, -400]]\n')
    eb, layout = _build(tmp_path, toml)
    assert shop.open_shop(45) in eb.data                  # the region action opens the shop
    assert layout.shop_items_csv.is_file()
    assert list(eb.instrs(eb.entry(0).func_by_tag(0)))    # Main_Init armed the region, still parses


def test_no_shop_writes_no_csv(tmp_path):
    """No [[shop]] anywhere -> ShopItems.csv is NOT written (the base is not clobbered)."""
    eb, layout = _build(tmp_path, BASE)
    assert not layout.shop_items_csv.exists()
    assert shop.open_shop(40) not in eb.data


# ---- validation -------------------------------------------------------------------------------
def _problems(toml: str, tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return validate(FieldProject.load(p))


def test_validate_bad_shop_id(tmp_path):
    probs = _problems(BASE + '\n[[shop]]\nid = 999\nsells = ["Potion"]\n', tmp_path)
    assert any("out of range" in m for m in probs)


def test_validate_unknown_item(tmp_path):
    probs = _problems(BASE + '\n[[shop]]\nid = 40\nsells = ["Nonexistent Sword"]\n', tmp_path)
    assert any("[[shop]] id 40 sells" in m for m in probs)


def test_validate_empty_sells(tmp_path):
    probs = _problems(BASE + '\n[[shop]]\nid = 40\nsells = []\n', tmp_path)
    assert any("no `sells`" in m for m in probs)


def test_validate_bad_zone(tmp_path):
    probs = _problems(BASE + '\n[[shop]]\nid = 40\nsells = ["Potion"]\nzone = [[0,0],[1,1]]\n', tmp_path)
    assert any("zone must have 4 or 5" in m for m in probs)


def test_validate_scalar_zone_no_crash(tmp_path):
    # a non-list zone must be a clean lint PROBLEM, never a TypeError from len() (mirrors the synthesis guard)
    probs = _problems(BASE + '\n[[shop]]\nid = 40\nsells = ["Potion"]\nzone = 5\n', tmp_path)
    assert any("zone must have 4 or 5" in m for m in probs)


def test_validate_string_sells_no_per_char_noise(tmp_path):
    # a bare-string `sells` = one clean "must be a list", not per-character 'unknown item' noise
    probs = _problems(BASE + '\n[[shop]]\nid = 40\nsells = "Potion"\n', tmp_path)
    assert any("sells must be a list" in m for m in probs)
    assert not any("unknown item 'P'" in m for m in probs)


def test_validate_opens_shop_range(tmp_path):
    toml = BASE + '\n[[npc]]\nname = "X"\npos = [0, -600]\nopens_shop = 9999\n'
    assert any("opens_shop must be a shop id" in m for m in _problems(toml, tmp_path))


def test_validate_sells_only_noitem(tmp_path):
    # a non-empty `sells` that resolves entirely to NoItem(255) would build an empty shop -> flagged
    probs = _problems(BASE + '\n[[shop]]\nid = 40\nsells = [255]\n', tmp_path)
    assert any("only NoItem" in m for m in probs)


def test_validate_npc_choice_and_opens_shop_conflict(tmp_path):
    toml = BASE + (
        '\n[[shop]]\nid = 40\nsells = ["Potion"]\n'
        '\n[[npc]]\nname = "Merchant"\npos = [0, -600]\ndialogue = "Hi"\nopens_shop = 40\n'
        '\n[[choice]]\nnpc = "Merchant"\nprompt = "Well?"\n'
        '[[choice.options]]\ntext = "Yes"\n'
        '[[choice.options]]\ntext = "No"\n')
    assert any("both a [[choice]] and opens_shop" in m for m in _problems(toml, tmp_path))


# ---- cross-field warnings (_emit_shops) -------------------------------------------------------
def _proj(toml: str, tmp_path, name="f"):
    p = tmp_path / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8")
    return FieldProject.load(p)


def test_emit_shops_vanilla_override_warns(tmp_path):
    layout = ModLayout(tmp_path / "mod")
    warns = _emit_shops([_proj(BASE + '\n[[shop]]\nid = 5\nsells = ["Potion"]\n', tmp_path)], layout)
    assert any("OVERRIDES vanilla shop 5" in w for w in warns)


def test_emit_shops_vanilla_dup_fires_both_warnings(tmp_path):
    # a vanilla id (5) defined in two fields is BOTH a duplicate AND a vanilla override -- both fire
    p1 = _proj(BASE + '\n[[shop]]\nid = 5\nsells = ["Potion"]\n', tmp_path, "a")
    p2 = _proj(BASE.replace("SHOPROOM", "SHOP2").replace("4003", "4004")
               + '\n[[shop]]\nid = 5\nsells = ["Tent"]\n', tmp_path, "b")
    warns = _emit_shops([p1, p2], ModLayout(tmp_path / "mod"))
    assert any("defined twice" in w for w in warns)
    assert any("OVERRIDES vanilla shop 5" in w for w in warns)


def test_emit_shops_bad_id_skipped_not_crash(tmp_path):
    # build doesn't run validate(); a malformed id must not crash the build -- it's skipped with a warning
    warns = _emit_shops([_proj(BASE + '\n[[shop]]\nid = "oops"\nsells = ["Potion"]\n', tmp_path)],
                        ModLayout(tmp_path / "mod"))
    assert any("missing/invalid id" in w for w in warns)


def test_emit_shops_dup_id_warns(tmp_path):
    p1 = _proj(BASE + '\n[[shop]]\nid = 40\nsells = ["Potion"]\n', tmp_path, "a")
    p2 = _proj(BASE.replace("SHOPROOM", "SHOP2").replace("4003", "4004")
               + '\n[[shop]]\nid = 40\nsells = ["Tent"]\n', tmp_path, "b")
    warns = _emit_shops([p1, p2], ModLayout(tmp_path / "mod"))
    assert any("defined twice" in w for w in warns)


def test_emit_shops_dangling_opens_shop_warns(tmp_path):
    toml = BASE + '\n[[npc]]\nname = "X"\npos = [0, -600]\nopens_shop = 99\n'
    warns = _emit_shops([_proj(toml, tmp_path)], ModLayout(tmp_path / "mod"))
    assert any("no [[shop]] or [[synthesis]] defines shop 99" in w for w in warns)


def test_emit_shops_vanilla_opens_shop_ok(tmp_path):
    """opens_shop pointing at a VANILLA shop (0-31) is fine -- it's in the base CSV, no warning."""
    toml = BASE + '\n[[npc]]\nname = "X"\npos = [0, -600]\nopens_shop = 0\n'
    warns = _emit_shops([_proj(toml, tmp_path)], ModLayout(tmp_path / "mod"))
    assert not any("opens_shop" in w for w in warns)
