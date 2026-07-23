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

``[[synthesis_edit]]`` retunes (or removes) a VANILLA recipe -- the same whole-row-merge makes an OVERRIDE of a
base id (0..63 vanilla) mechanically sound; the kit re-emits the base row with only the edited cells changed:

    [[synthesis_edit]]
    recipe = "Butterfly Sword"      # the base recipe: its RESULT item's name, or the recipe's integer Id
    price = 500                     # any of price / ingredients / result / shops (each optional, >= 1 required)
    ingredients = ["Dagger", "Dagger"]   # FULL replacement (dups = need N copies)
    shops = [37, 38]                # FULL replacement of which synthesists list it (32..255)

    [[synthesis_edit]]
    recipe = "Pumice"
    remove = true                   # unlist from EVERY shop (empty Shops cell -> ShopUI never shows it);
                                    # exclusive with the other edit keys

Removal = an EMPTY ``Shops`` cell: ``CsvParser.Int32Array("")`` parses to an empty array, and
``ShopUI.InitializeMixList`` only shows rows whose ``Shops`` contains the open shop's id -- so the recipe row
stays defined (Memoria's runtime ``AddShopSynthesis`` event op could even re-add it) but no shop offers it.
"""
from __future__ import annotations

from .. import items as _items
from . import shop as _shop
from .itemdata import read_base_csv, _read_text, CSV_ENCODING

PRICE_CAP = 9_999_999       # gil cap (UInt32 Price; a cost above the holdable gil cap is pointless)
NO_ITEM = 255               # NoItem -- meaningless as a result/ingredient (the engine skips it when counting)
FIRST_SYNTH_SHOP = _shop.FIRST_CUSTOM_SHOP   # >= 32: ids 0-31 are base BUY shops (in ShopItems) -> never Synthesis
MAX_SHOP_ID = _shop.MAX_SHOP_ID              # <= 255: the Menu(2, id) sub-id is a single byte


# the fixed Synthesis.csv cell layout (Comment;Id;Shops;Price;Result;Ingredients...) -- FF9MIX_DATA.ParseEntry
# reads Shops from cell 2, Price 3, Result 4, and EVERY cell from 5 onward as ingredient lists.
_COL_COMMENT, _COL_ID, _COL_SHOPS, _COL_PRICE, _COL_RESULT, _COL_INGREDIENTS = range(6)


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


def install_base_rows(game=None):
    """``{id: raw_row}`` from the INSTALL's base ``Synthesis.csv``, or ``None`` when no install is reachable --
    lint's best-effort ``[[synthesis_edit]]`` selector check (build reads the base itself via
    :func:`write_synthesis`, which raises instead)."""
    from ..config import find_game_path, ConfigError
    try:
        base = find_game_path(game) / "StreamingAssets" / "Data" / "Items" / "Synthesis.csv"
        return read_base_csv(_read_text(base))[3]
    except (OSError, ConfigError):
        return None


def resolve_recipe_selector(sel, base_rows) -> list:
    """The base recipe id(s) a ``[[synthesis_edit]] recipe =`` selector names: an integer = the recipe's own
    ``Id`` (``[id]`` when present in the base, else ``[]``); a string = the RESULT item's name (every base recipe
    whose ``Result`` is that item -- unique in vanilla, but ambiguity is the caller's to flag). Raises ValueError
    on an unresolvable item name (mirrors :func:`items.resolve`)."""
    if isinstance(sel, bool):
        raise ValueError(f"recipe selector must be a result-item name or a recipe id, got {sel!r}")
    if isinstance(sel, int):
        return [sel] if sel in base_rows else []
    result = _items.resolve(sel)                          # raises on an unknown name
    out = []
    for rid, row in sorted(base_rows.items()):
        parts = row.split(";")
        try:
            if int(parts[_COL_RESULT].strip()) == result:
                out.append(rid)
        except (ValueError, IndexError):
            continue
    return out


def edit_rows(edit_blocks, base_text):
    """``([(id, row_string), ...], notes)`` -- one FULL replacement row per edited base recipe (whole-row-wins
    merge; the base row's cells are kept verbatim except the edited ones). Edits to the same recipe across
    blocks COALESCE in block order (later block wins per key -- noted). A block whose selector does not match
    exactly one base recipe, or whose values do not resolve, is SKIPPED with a note (lint flags it precisely)."""
    _h, _cols, _idc, base_rows = read_base_csv(base_text)
    notes: list = []
    per_id: dict = {}                                     # recipe id -> coalesced edit dict (insertion-ordered)
    for b in edit_blocks:
        sel = b.get("recipe")
        try:
            matches = resolve_recipe_selector(sel, base_rows)
        except (ValueError, TypeError) as e:
            notes.append(f"[[synthesis_edit]] recipe {sel!r} skipped: {e}")
            continue
        if not matches:
            notes.append(f"[[synthesis_edit]] recipe {sel!r} matches no base recipe -- skipped "
                         f"(an integer selects the recipe's Id, a string its RESULT item's name)")
            continue
        if len(matches) > 1:
            notes.append(f"[[synthesis_edit]] recipe {sel!r} is ambiguous (base recipe ids "
                         f"{', '.join(map(str, matches))} all produce it) -- skipped; select by integer Id")
            continue
        rid = matches[0]
        if rid in per_id:
            notes.append(f"[[synthesis_edit]] recipe {sel!r} (id {rid}) is edited more than once -- "
                         f"the edits merge, later blocks win per key")
        merged = per_id.setdefault(rid, {})
        for key in ("price", "ingredients", "result", "shops", "remove"):
            if key in b:
                merged[key] = b[key]
    out = []
    for rid, edit in per_id.items():
        parts = base_rows[rid].split(";")
        if len(parts) <= _COL_INGREDIENTS:                # malformed base row -- never true of a real install
            notes.append(f"[[synthesis_edit]] base recipe {rid} row is malformed ({len(parts)} cells) -- skipped")
            continue
        if edit.get("remove"):
            parts[_COL_SHOPS] = ""                        # empty Shops -> Int32Array("") = [] -> no shop lists it
        else:
            if "shops" in edit:
                try:
                    parts[_COL_SHOPS] = ", ".join(str(int(s)) for s in edit["shops"])
                except (ValueError, TypeError):
                    notes.append(f"[[synthesis_edit]] recipe id {rid}: shops must be a list of shop ids -- "
                                 f"shops edit skipped")
            if "price" in edit:
                try:
                    parts[_COL_PRICE] = str(max(0, min(PRICE_CAP, int(edit["price"]))))
                except (ValueError, TypeError):
                    notes.append(f"[[synthesis_edit]] recipe id {rid}: price must be an integer -- price edit skipped")
            if "result" in edit:
                try:
                    result = _items.resolve(edit["result"])
                    if result == NO_ITEM:
                        raise ValueError("NoItem (255) -- use remove = true to retire the recipe")
                    parts[_COL_RESULT] = str(result)
                    name = _items.name_of(result)         # keep the cosmetic Comment honest for the new result
                    if name:
                        parts[_COL_COMMENT] = _shop.safe_comment(name, rid)
                except (ValueError, IndexError, TypeError) as e:
                    notes.append(f"[[synthesis_edit]] recipe id {rid}: result: {e} -- result edit skipped")
            if "ingredients" in edit:
                resolved, bad = [], False
                raw_ingredients = edit["ingredients"]
                if not isinstance(raw_ingredients, (list, tuple)):
                    notes.append(f"[[synthesis_edit]] recipe id {rid}: ingredients must be a list of items -- "
                                 f"ingredients edit skipped")
                    bad = True
                else:
                    for entry in raw_ingredients:
                        try:
                            iid = _items.resolve(entry)
                        except (ValueError, IndexError, TypeError) as e:
                            notes.append(f"[[synthesis_edit]] recipe id {rid}: ingredients: {e} -- "
                                         f"ingredients edit skipped")
                            bad = True
                            break
                        if iid != NO_ITEM:                # NoItem dropped; dups kept (need N copies)
                            resolved.append(iid)
                if not bad:
                    if resolved:
                        # ONE joined cell replaces every ingredient cell (ParseEntry reads cells 5..end)
                        parts[_COL_INGREDIENTS:] = [", ".join(str(i) for i in resolved)]
                    else:
                        notes.append(f"[[synthesis_edit]] recipe id {rid}: ingredients resolve to nothing -- "
                                     f"ingredients edit skipped")
        out.append((rid, ";".join(parts)))
    return out, notes


def render_synthesis(synth_blocks, base_text, edit_blocks=(), notes=None) -> str:
    """The ``Synthesis.csv`` delta text: the base header block VERBATIM (so ``#! UseShopList`` + the legend parse
    identically -> ``Shops`` reads as an ``Int32[]``) + one FULL override row per ``[[synthesis_edit]]``-edited
    base recipe + one minted recipe row per ``[[synthesis]]`` recipe. A partial delta -- the engine merges it
    over the base by Id, so only edited + new recipes are listed. ``Comment;Id;Shops;Price;Result;Ingredients``
    (the Comment cell is the result's name, delimiter-sanitised; no trailing comment -- the base rows have none,
    and a trailing ``#``-cell would be truncated away by ``CsvReader`` (``Array.Resize`` at the first
    ``#``-prefixed cell, before ``ParseEntry`` sees the row), so it is pointless rather than harmful).
    ``notes``, when a list, collects the edit-side skip/merge notes (build surfaces them as warnings)."""
    header, _cols, _idc, _rows = read_base_csv(base_text)
    banner = ("# ff9mapkit [[synthesis]]/[[synthesis_edit]] -- custom + edited recipes (Synthesis.csv delta; "
              "MERGED by id over the base). Minted ids are above the base max; an edited base id overrides its "
              "vanilla row whole; Shops = the synth-shop id you open with Menu(2, id).")
    lines = [header, banner]
    edited, edit_notes = edit_rows(edit_blocks, base_text)
    if notes is not None:
        notes.extend(edit_notes)
    for _rid, row in edited:
        lines.append(row)
    for rid, shop, price, result, ingredients, comment in recipe_rows(synth_blocks, base_text):
        ingr = ", ".join(str(i) for i in ingredients)
        lines.append(f"{comment};{rid};{shop};{price};{result};{ingr}")
    return "\n".join(lines) + "\n"


def write_synthesis(layout, synth_blocks, *, edit_blocks=(), game=None, notes=None) -> None:
    """Emit the synthesis-recipe delta into ``layout``'s mod root (``Data/Items/Synthesis.csv``). Reads the base
    rows from the install (raises a clear ValueError if it isn't reachable -- the delta needs the base header +
    max id + the edited rows). No blocks of either kind -> nothing written (no base clobber)."""
    if not synth_blocks and not edit_blocks:
        return
    from ..config import find_game_path, ConfigError
    try:                                                  # ConfigError (no resolvable install) is a RuntimeError,
        base = find_game_path(game) / "StreamingAssets" / "Data" / "Items" / "Synthesis.csv"   # NOT OSError --
        base_text = _read_text(base)                      # catch both so build.py's `except ValueError` warns+skips
    except (OSError, ConfigError) as e:
        raise ValueError("synthesis recipes ([[synthesis]]/[[synthesis_edit]]) need your FF9 install to read "
                         f"the base Synthesis.csv (header + recipe rows): {e}") from e
    path = layout.synthesis_csv
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_synthesis(synth_blocks, base_text, edit_blocks, notes=notes),
                    encoding=CSV_ENCODING, newline="\n")
