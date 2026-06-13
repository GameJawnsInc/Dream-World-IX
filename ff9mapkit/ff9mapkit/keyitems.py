"""Key/important-item NAMES, read LIVE from the install (provenance-clean) + the id<->name resolver.

FF9 has **no symbolic enum** for key items (unlike ``RegularItem``), so the kit ships no key-item name table.
Names are read LIVE from ``<install>/StreamingAssets/Text/<lang>/KeyItems.strings`` (entries
``"$keyNNNN" = "Name`` ...), cached in-memory, **shipping/committing nothing** (the same provenance-clean live
pattern as :mod:`ff9mapkit.itemstats`). If the install/file isn't reachable, every accessor returns ``None`` and
the editor falls back to raw numeric ids.

Usage::

    from ff9mapkit import keyitems
    keyitems.resolve("Silver Pendant")   # -> 0
    keyitems.name_of(4)                   # -> "Falcon Claw"
"""
from __future__ import annotations

import re

# id <-> first-line name from the .strings file:  "$key0004" = "Falcon Claw\n...help...";
_KEY_RE = re.compile(r'"\$key(\d+)"\s*=\s*"([^\n\r]*)')
KEYITEM_MAX = 255                                          # the main-block 2-bit rareItems bitfield covers 0-255

_CACHE = None    # None = not loaded yet; False = tried + unavailable; dict = {id: name}


def _norm(s) -> str:
    return "".join(c for c in str(s).lower() if c.isalnum())


def _load(game=None, lang: str = "US"):
    """``{id: name}`` from the install's KeyItems.strings (cached), or ``None`` if it can't be read."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE or None
    try:
        from .config import find_game_path
        p = find_game_path(game) / "StreamingAssets" / "Text" / lang / "KeyItems.strings"
        text = p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:                                      # noqa: BLE001 -- install not reachable -> degrade
        _CACHE = False
        return None
    out = {}
    for m in _KEY_RE.finditer(text):
        iid, name = int(m.group(1)), m.group(2).strip()
        if name and iid not in out:                        # first entry per id (the file has story-variant dups)
            out[iid] = name
    _CACHE = out or False
    return out or None


def name_of(iid, game=None):
    """Canonical key-item name for an id, or ``None`` (id unknown / install unreachable)."""
    d = _load(game)
    return d.get(int(iid)) if d else None


def resolve(name_or_id, game=None) -> int:
    """A key-item NAME or id -> its numeric id. An int / digit-string passes through (validated 0-255); a name is
    matched case/space/punct-insensitively against the live name table. Raises ValueError on an unknown name /
    out-of-range id (or if names can't be read and a name was given)."""
    if isinstance(name_or_id, bool):
        raise ValueError("key item cannot be a boolean")
    if isinstance(name_or_id, int):
        if not 0 <= name_or_id <= KEYITEM_MAX:
            raise ValueError(f"key-item id {name_or_id} out of range (0-{KEYITEM_MAX})")
        return name_or_id
    s = str(name_or_id).strip()
    if s.isdigit():
        return resolve(int(s), game)
    d = _load(game)
    if d:
        by_name = {_norm(v): k for k, v in d.items()}
        key = _norm(s)
        if key in by_name:
            return by_name[key]
        raise ValueError(f"unknown key item {name_or_id!r} (run `ff9mapkit items --keyitems` to list them)")
    raise ValueError(f"cannot resolve key item {name_or_id!r}: the install's KeyItems.strings isn't reachable -- "
                     "pass a numeric id (0-255) instead")


def available(game=None) -> bool:
    """True if the install's KeyItems.strings could be read (so key-item NAMES are live)."""
    return _load(game) is not None


def all_keyitems(game=None) -> list:
    """Sorted ``[(id, name), ...]`` (for the CLI / docs), or ``[]`` if unavailable."""
    return sorted((_load(game) or {}).items())


def _reset_cache():                                        # for tests
    global _CACHE
    _CACHE = None
