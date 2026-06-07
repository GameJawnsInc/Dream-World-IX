"""Author-facing item catalog -- give an item by NAME instead of a numeric id.

``give_item = ["Potion", 1]`` instead of ``[236, 1]``. Backed by :mod:`ff9mapkit._itemdb` (FF9 item
id <-> name, from Memoria's open-source ``RegularItem`` enum). Names match case / spacing / hyphen
insensitively, so ``"Potion"``, ``"potion"``, ``"Hi-Potion"``, ``"phoenix down"`` all resolve. A
numeric id (int or digit string) passes through, validated to 0-255.

Usage::

    from ff9mapkit import items
    items.resolve("Potion")       # -> 236
    items.resolve("hi-potion")    # -> 237
    items.resolve(236)            # -> 236  (raw id passes through)
    items.name_of(236)            # -> "Potion"
"""

from __future__ import annotations

import difflib

from ._itemdb import ITEMS

# normalized-name -> id (lowercased, alphanumerics only -> "Hi-Potion"/"hi potion" both match HiPotion)
_BY_NAME = {}


def _norm(s) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum())


for _id, _name in ITEMS.items():
    _BY_NAME[_norm(_name)] = _id


def resolve(name_or_id) -> int:
    """Resolve an item NAME or id to its numeric id. An int / digit-string passes through (validated
    0-255); a name is matched case/space/hyphen-insensitively. Raises ValueError (with near-miss
    suggestions) on an unknown name or out-of-range id."""
    if isinstance(name_or_id, bool):
        raise ValueError("item cannot be a boolean")
    if isinstance(name_or_id, int):
        if not 0 <= name_or_id <= 255:
            raise ValueError(f"item id {name_or_id} out of range (0-255)")
        return name_or_id
    s = str(name_or_id).strip()
    if s.isdigit():
        return resolve(int(s))
    key = _norm(s)
    if key in _BY_NAME:
        return _BY_NAME[key]
    hints = [ITEMS[_BY_NAME[h]] for h in difflib.get_close_matches(key, list(_BY_NAME), n=6, cutoff=0.4)]
    extra = f" Did you mean: {', '.join(hints)}?" if hints else " Run `ff9mapkit items` to list them."
    raise ValueError(f"unknown item {name_or_id!r}.{extra}")


def name_of(item_id: int):
    """Canonical name for an id (236 -> 'Potion'), or None."""
    return ITEMS.get(int(item_id))


def all_items() -> list:
    """Sorted ``[(id, name), ...]`` (for the CLI / docs)."""
    return sorted(ITEMS.items())
