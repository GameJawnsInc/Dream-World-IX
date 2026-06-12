"""``[[shop]]`` -- author a custom shop: its INVENTORY (a ``ShopItems.csv`` delta) + an OPENER.

Two channels, like every item feature on this branch:

* **Inventory (data).** A custom shop's stock is a row in ``<mod>/StreamingAssets/Data/Items/ShopItems.csv``
  -- ``Comment;Id;item1, item2, ...``. The engine **MERGES** these by id low->high (``ff9buy.LoadShopItems``
  via ``EnumerateCsvFromLowToHigh`` -> ``result[shop.Id] = shop``), so a PARTIAL delta (just the custom shops)
  works: the base file supplies shops 0-31 (the engine's ``>= 32`` guard is satisfied by the base), and our
  delta adds the new ids. ★ A custom shop id must be **>= 32** (0-31 are the base shops; a clash OVERRIDES the
  vanilla shop -- allowed but lint-warned). The id is also the ``Menu`` sub-id (one byte), so it is **<= 255**.

* **Opener (.eb).** A shop opens with ``Menu(2, shopId)`` (0x75 -> ``EventService.FF9Menu_Command`` case 2u ->
  ``OpenShopMenu``) -- the same opcode family as the save point (``Menu(4, 0)``). Two shapes:

    - a **shopkeeper NPC** -- ``[[npc]] opens_shop = N`` builds a tag-3 talk body that (optionally greets, then)
      opens the shop; reuses :mod:`content.npc`'s ``speak_body`` slot. ``opens_shop`` may point at a VANILLA shop
      (0-31) too (e.g. open Dali's weapon shop). This is the authentic "talk to the merchant" UX.
    - a **standalone press-region** -- ``[[shop]] zone = [...]`` mints a press-to-interact region (the save-point
      shape: Init ``SetRegion`` / tread ``Bubble`` / action ``DisableMove; Menu(2, id); EnableMove``) so you can
      walk up to a counter and open the shop with no NPC. Place a cosmetic ``[[npc]]``/``[[prop]]`` over it for the
      visible merchant, exactly like the save moogle.

The inventory CSV is mod-global (one ``ShopItems.csv`` per mod, collected across every built field's ``[[shop]]``
blocks); the opener is per-field ``.eb``. (memory project-ff9-items-equipment / project-ff9-branch-lanes.)

    [[shop]]
    id = 40
    comment = "Hut Item Shop"
    sells = ["Potion", "Hi-Potion", "Phoenix Down", "Tent", "Ether"]
    # optional standalone opener (else open it from an NPC):
    zone = [[-400, -900], [400, -900], [400, -500], [-400, -500]]

    [[npc]]
    name = "Shopkeeper"
    pos = [0, -700]
    dialogue = "Welcome! Care to buy something?"
    opens_shop = 40
"""
from __future__ import annotations

import struct

from .. import items as _items
from ..eb import EbScript, edit, opcodes
from . import region as _region

SHOP_MENU_ID = 2          # FF9Menu_Command case 2u -> EventService.OpenShopMenu
FIRST_CUSTOM_SHOP = 32    # base game ships shops 0-31; a custom shop must be >= 32 (0-31 are vanilla)
MAX_SHOP_ID = 255         # the Menu sub-id is a single byte, so a shop id is <= 255
NO_ITEM = 255             # terminates a shop's item list (ShopItems.ParseEntry stops at NoItem)


# --- opener bodies ---------------------------------------------------------------------------------

def open_shop(shop_id: int) -> bytes:
    """The single op that opens shop ``shop_id``: ``Menu(2, shop_id)``."""
    return opcodes.menu(SHOP_MENU_ID, int(shop_id))


def shop_speak_body(shop_id: int, *, greeting_txid: int | None = None) -> bytes:
    """A shopkeeper NPC's tag-3 talk body: (optional greeting window ->) open the shop -> RETURN. The talk
    already halts the player, so -- unlike the press-region -- no ``DisableMove`` bracket is needed."""
    body = b""
    if greeting_txid is not None:
        body += opcodes.window_sync(1, 128, int(greeting_txid))
    return body + open_shop(shop_id) + opcodes.RETURN


def shop_dispatch(shop_id: int) -> bytes:
    """The press-region action body: ``DisableMove; Menu(2, id); EnableMove; RETURN`` -- locks control while
    the shop UI is up (so the player can't walk out from under it) and restores it after. Mirrors
    :func:`content.savepoint.save_dispatch`, with the shop menu in place of the save menu."""
    return (opcodes.DISABLE_MOVE
            + open_shop(shop_id)
            + opcodes.ENABLE_MOVE + opcodes.RETURN)


def _assemble_entry(funcs) -> bytes:
    """Assemble a type-1 (region) entry from ``[(tag, body), ...]`` -- the func table (``<tag:u16><fpos:u16>``
    each) then the concatenated bodies. Same layout as :func:`content.savepoint._assemble_entry`."""
    table = b""
    pos = len(funcs) * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def shop_region(zone, shop_id: int, *, bubble: bool = True) -> bytes:
    """A type-1 region entry that opens a shop: Init ``SetRegion(zone)`` / tread (tag 2) ``Bubble(1)`` (the
    floating "!" prompt, if ``bubble``) / action (tag 3) :func:`shop_dispatch`. Both trigger funcs are gated
    by :data:`content.region.MOVEMENT_GATE` (fire only while ``usercontrol == 1``), like every real region."""
    init = _region.set_region([tuple(p) for p in zone]) + opcodes.RETURN
    tread = _region.MOVEMENT_GATE + (opcodes.bubble(1) if bubble else b"") + opcodes.RETURN
    action = _region.MOVEMENT_GATE + shop_dispatch(shop_id)
    funcs = [(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)]
    return _assemble_entry(funcs)


def inject_shop_region(data, zone, shop_id: int, *, bubble: bool = True, activate: bool = True):
    """Inject one standalone shop opener: append a shop region at the next free slot and arm it
    (``InitRegion`` in Main_Init). Returns ``(new_bytes, region_slot)``."""
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, shop_region(zone, shop_id, bubble=bubble))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot


def inject_shop_regions(data, shops, *, activate: bool = True):
    """Inject a standalone press-region for every ``[[shop]]`` that carries a ``zone``. Returns
    ``(new_bytes, [slot, ...])``. Shops without a ``zone`` (opened from an NPC instead) are skipped."""
    slots = []
    for sh in shops:
        if not sh.get("zone"):
            continue
        data, slot = inject_shop_region(data, sh["zone"], int(sh["id"]),
                                        bubble=bool(sh.get("bubble", True)), activate=activate)
        slots.append(slot)
    return data, slots


# --- inventory CSV ---------------------------------------------------------------------------------

def safe_comment(text: str, sid: int) -> str:
    """Make the CSV column-0 label delimiter-safe. The comment is free author text but column 0 of a
    semicolon-delimited row whose Id is column 1, so a stray delimiter mis-parses or DROPS the shop:
    a ``;`` splits the row (the engine reads the wrong Id column), a leading ``#`` makes the engine's
    CsvReader skip the whole line (the shop silently never loads), and a newline breaks the row. We
    neutralise all three (``;`` -> ``,``, newlines -> space, strip a leading ``#``); the label is cosmetic
    (the shop is keyed by Id), so this is lossless to behaviour. Empty -> the default ``Shop NNNN`` label."""
    text = str(text).replace("\r", " ").replace("\n", " ").replace(";", ",").strip().lstrip("#").strip()
    return text or f"Shop {sid:04d}"


def shop_rows(shops) -> list:
    """``[{id, sells, comment}, ...]`` -> ``[(id, [item_id, ...], comment), ...]`` sorted by id.

    Item names/ids resolved via :func:`items.resolve`; ``NoItem`` (255) dropped (it would terminate the
    shop's list); duplicate items within a shop collapsed (order-preserving, first wins). A duplicate SHOP id
    keeps the last definition (last wins -- the engine's own merge rule); the build lints the duplicate."""
    by_id: dict = {}
    for sh in shops:
        sid = int(sh["id"])
        seen, ids = set(), []
        for entry in sh.get("sells", []):
            iid = _items.resolve(entry)
            if iid == NO_ITEM or iid in seen:
                continue
            seen.add(iid)
            ids.append(iid)
        by_id[sid] = (ids, safe_comment(sh.get("comment") or "", sid))
    return [(sid, ids, comment) for sid, (ids, comment) in sorted(by_id.items())]


def render_shop_items(shops) -> str:
    """The ``ShopItems.csv`` delta text (legend + one ``Comment;Id;items;# names`` row per custom shop). A
    partial delta -- the engine merges it over the base by id, so only the custom shops are listed."""
    lines = [
        "# ff9mapkit [[shop]] -- custom shop inventories (ShopItems.csv delta; the engine MERGES by id over the",
        "# base, which supplies shops 0-31). Custom shop ids are >= 32.",
        "# Comment;Id;Items",
        "# ;Int32;Int32[]",
    ]
    for sid, ids, comment in shop_rows(shops):
        names = ", ".join(_items.name_of(i) or str(i) for i in ids)
        items_csv = ", ".join(str(i) for i in ids)
        lines.append(f"{comment};{sid};{items_csv}" + (f";# {names}" if names else ""))
    return "\n".join(lines) + "\n"


def write_shop_items(layout, shops) -> None:
    """Pure writer: emit the shop-inventory delta into ``layout``'s mod root
    (``Data/Items/ShopItems.csv``)."""
    path = layout.shop_items_csv
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_shop_items(shops), encoding="utf-8", newline="\n")
