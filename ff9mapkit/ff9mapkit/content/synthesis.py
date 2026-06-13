"""``[[synthesis]]`` -- author a custom SYNTHESIS shop: recipes (a ``Synthesis.csv`` delta) + the SAME
``Menu(2, id)`` opener as :mod:`content.shop`.

A synthesis shop combines INGREDIENT items + gil -> a RESULT item. Two engine facts make it a pure data patch
(no DLL), grounded in the Memoria source:

* **A shop id opens as a SYNTHESIS shop iff it is NOT present in ``ShopItems.csv``** (``ff9buy.FF9Buy_GetType``:
  a missing id returns ``ShopType.Synthesis``; an id in ``ShopItems`` is a Buy shop). So a synth shop reuses the
  ``[[shop]]`` opener VERBATIM -- ``Menu(2, id)`` (``EventService.OpenShopMenu``) -- and the synth shop id must
  NOT also be a ``[[shop]]`` id (that would add it to ``ShopItems.csv`` and flip it to a BUY shop).
* **A shop's recipes = every ``Synthesis.csv`` row whose ``Shops`` list contains the shop id**
  (``ShopUI.InitializeMixList``). ``Synthesis.csv`` (``FF9MIX_DATA``) = ``Comment;Id;Shops;Price;Result;Ingredients``
  with ``#! UseShopList`` (so ``Shops`` parses as an ``Int32[]``); MERGED by Id low->high, whole-row
  (``ff9mix.LoadSynthesis`` via ``EnumerateCsvFromLowToHigh``). The kit MINTS recipe ids ABOVE the base max (63)
  so a delta only ADDS recipes, never clobbers a base one. Base rows are read LIVE from the install (cp1252),
  delta generated at build time -> the repo commits NO game data (same stance as :mod:`content.itemdata`).

The recipe CSV is mod-global (one ``Synthesis.csv`` per mod, recipes collected across every built field's
``[[synthesis]]`` blocks); the opener is per-field ``.eb`` (reused from :mod:`content.shop` -- ``Menu(2, id)`` is
byte-identical to a buy shop's, the engine decides Buy-vs-Synthesis from the id alone).

    [[synthesis]]
    shop = 40                       # the synth-shop id (NOT a [[shop]] buy id; 32..255)
    recipes = [
      { result = "Butterfly Sword", ingredients = ["Dagger", "Mage Masher"], price = 300 },
      { result = "The Ogre",        ingredients = ["Mage Masher", "Mage Masher"], price = 700 },
    ]
    # optional standalone opener (else open it from an NPC with opens_shop = 40):
    zone = [[-400, -900], [400, -900], [400, -500], [-400, -500]]
"""
from __future__ import annotations

from .. import items as _items
from . import shop as _shop
from .itemdata import read_base_csv, _read_text, CSV_ENCODING

PRICE_CAP = 9_999_999       # gil cap (UInt32 Price; a cost above the holdable gil cap is pointless)
NO_ITEM = 255               # NoItem -- meaningless as a result/ingredient (the engine skips it when counting)
FIRST_SYNTH_SHOP = _shop.FIRST_CUSTOM_SHOP   # >= 32: ids 0-31 are base BUY shops (in ShopItems) -> never Synthesis
MAX_SHOP_ID = _shop.MAX_SHOP_ID              # <= 255: the Menu(2, id) sub-id is a single byte


def base_max_id(base_text: str) -> int:
    """The highest recipe Id in the base ``Synthesis.csv`` (so a mint lands ABOVE every base recipe); -1 if none."""
    _h, _cols, _idc, rows = read_base_csv(base_text)
    return max(rows, default=-1)


def recipe_rows(synth_blocks, base_text) -> list:
    """``[(id, shop, price, result, [ingredient_id, ...], comment), ...]`` for every recipe across all
    ``[[synthesis]]`` blocks -- recipe ids MINTED above the base max (deterministic: block order, then recipe
    order). Result/ingredient names resolved via :func:`items.resolve`; ``NoItem`` dropped from ingredients
    (it is meaningless); a recipe with no real result or no real ingredient is SKIPPED here (lint flags it)."""
    mint = base_max_id(base_text) + 1
    out = []
    for b in synth_blocks:
        shop = int(b["shop"])
        for r in b.get("recipes", []):
            result = _items.resolve(r["result"])
            ingredients = []
            for entry in r.get("ingredients", []):
                iid = _items.resolve(entry)
                if iid != NO_ITEM:                       # NoItem ingredient = no-op (skip; keep dups -- need N)
                    ingredients.append(iid)
            if result == NO_ITEM or not ingredients:
                continue
            price = max(0, min(PRICE_CAP, int(r.get("price", 0))))
            comment = _shop.safe_comment(_items.name_of(result) or f"Recipe {mint}", mint)
            out.append((mint, shop, price, result, ingredients, comment))
            mint += 1
    return out


def render_synthesis(synth_blocks, base_text) -> str:
    """The ``Synthesis.csv`` delta text: the base header block VERBATIM (so ``#! UseShopList`` + the legend parse
    identically -> ``Shops`` reads as an ``Int32[]``) + one minted recipe row per recipe. A partial delta -- the
    engine merges it over the base by Id, so only the new recipes are listed. ``Comment;Id;Shops;Price;Result;
    Ingredients`` (the Comment cell is the result's name, delimiter-sanitised; no trailing comment -- the base
    rows have none, and a trailing ``#``-cell would be truncated away by ``CsvReader`` (``Array.Resize`` at the
    first ``#``-prefixed cell, before ``ParseEntry`` sees the row), so it is pointless rather than harmful)."""
    header, _cols, _idc, _rows = read_base_csv(base_text)
    banner = ("# ff9mapkit [[synthesis]] -- custom recipes (Synthesis.csv delta; MERGED by id over the base). "
              "Minted ids are above the base max; Shops = the synth-shop id you open with Menu(2, id).")
    lines = [header, banner]
    for rid, shop, price, result, ingredients, comment in recipe_rows(synth_blocks, base_text):
        ingr = ", ".join(str(i) for i in ingredients)
        lines.append(f"{comment};{rid};{shop};{price};{result};{ingr}")
    return "\n".join(lines) + "\n"


def write_synthesis(layout, synth_blocks, *, game=None) -> None:
    """Emit the synthesis-recipe delta into ``layout``'s mod root (``Data/Items/Synthesis.csv``). Reads the base
    rows from the install (raises a clear ValueError if it isn't reachable -- the delta needs the base header +
    max id). No blocks -> nothing written (no base clobber)."""
    if not synth_blocks:
        return
    from ..config import find_game_path, ConfigError
    try:                                                  # ConfigError (no resolvable install) is a RuntimeError,
        base = find_game_path(game) / "StreamingAssets" / "Data" / "Items" / "Synthesis.csv"   # NOT OSError --
        base_text = _read_text(base)                      # catch both so build.py's `except ValueError` warns+skips
    except (OSError, ConfigError) as e:
        raise ValueError("synthesis recipes ([[synthesis]]) need your FF9 install to read the base "
                         f"Synthesis.csv (header + recipe ids): {e}") from e
    path = layout.synthesis_csv
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_synthesis(synth_blocks, base_text), encoding=CSV_ENCODING, newline="\n")
