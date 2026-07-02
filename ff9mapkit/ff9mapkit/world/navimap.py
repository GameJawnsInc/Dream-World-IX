"""Overworld minimap MARKER registry + the reveal helper (``[startup] reveal_markers``).

The 64 world-overview location markers (the town/dungeon dots) are each drawn by the engine iff their
**save-backed discovery bit** is set: ``gEventGlobal`` bit ``NAVI_BIT_BASE + locId`` — i.e. bytes 92-99 /
bits 736-799 (``keventNaviLocF0..F3``, ``ff9.cs:6957``), read by ``w_naviLocationAvailable`` (a marker draws
iff its coords are non-zero AND its bit is set). The real game sets these from a field's exit cascade
(``opE4(736+locId)=1``) as you reach each place. **A mod reveals a marker the exact same way — a plain
GLOB-bit set — so ``[startup] reveal_markers = [...]`` compiles to ``(736+locId, 1)`` bit presets with no
engine change** (see ``ff9mapkit/docs/OVERWORLD_ENGINE.md`` § minimap, and ``[[flag]]`` for the primitive).

:data:`MARKER_NAMES` is *derived reference data* (the location labels, like the InfoHub catalogs) for by-name
authoring. Names repeat across slots (``South Gate`` = 6-10, ``Qu's Marsh`` = 21/29/40/45, ``Gizamaluke's
Grotto`` = 16/20/59), so a NAME resolves to ALL its slots; author by ``locId`` (0-63) for a single dot.
"""
from __future__ import annotations

NAVI_BIT_BASE = 736          # gEventGlobal bit for marker locId 0 (byte 92 << 3); marker N -> bit 736+N
NAVI_LOCATION_COUNT = 64     # w_naviLocationPos is navipos[2, 64]

# locId -> display name. Derived from the world-map field text (txid 0, split by newline, index locId+1);
# slots 50-52 (placeholders "?"/"???") and 60-62 (unnamed/unused) are intentionally absent. locId 63 is an
# engine alias that shows "Chocobo's Paradise" (== locId 49). Apostrophes normalised to ASCII.
MARKER_NAMES: dict[int, str] = {
    0: "Alexandria Harbor", 1: "Alexandria", 2: "Evil Forest", 3: "Ice Cavern", 4: "Quan's Dwelling",
    5: "Treno", 6: "South Gate", 7: "South Gate", 8: "South Gate", 9: "South Gate", 10: "South Gate",
    11: "Ice Cavern", 12: "Observatory Mountain", 13: "Dali", 14: "North Gate", 15: "North Gate",
    16: "Gizamaluke's Grotto", 17: "Burmecia", 18: "Cleyra", 19: "Chocobo's Forest",
    20: "Gizamaluke's Grotto", 21: "Qu's Marsh", 22: "Pinnacle Rocks", 23: "Lindblum Dragon's Gate",
    24: "Lindblum", 25: "Lindblum Harbor", 26: "Earth Shrine", 27: "Desert Palace", 28: "Mognet Central",
    29: "Qu's Marsh", 30: "Black Mage Village", 31: "Fossil Roo", 32: "Conde Petie", 33: "Madain Sari",
    34: "Conde Petie Mountain Path", 35: "Conde Petie Mountain Path", 36: "Iifa Tree", 37: "Chocobo's Lagoon",
    38: "Wind Shrine", 39: "Daguerreo", 40: "Qu's Marsh", 41: "Oeilvert", 42: "Landing Site",
    43: "Water Shrine", 44: "Ipsen's Castle", 45: "Qu's Marsh", 46: "Shimmering Island", 47: "Esto Gaza",
    48: "Fire Shrine", 49: "Chocobo's Paradise", 53: "Memoria", 54: "Chocobo's Air Garden",
    55: "Chocobo's Air Garden", 56: "Chocobo's Air Garden", 57: "Chocobo's Air Garden",
    58: "Chocobo's Air Garden", 59: "Gizamaluke's Grotto",
}


def marker_bit(loc_id: int) -> int:
    """The ``gEventGlobal`` discovery bit index for marker ``loc_id`` (0-63)."""
    if not (0 <= loc_id < NAVI_LOCATION_COUNT):
        raise ValueError(f"marker locId must be 0..{NAVI_LOCATION_COUNT - 1} (got {loc_id})")
    return NAVI_BIT_BASE + loc_id


def _norm(s: str) -> str:
    """Case/punctuation-insensitive key for name matching ('Qu's Marsh' == 'qus marsh' == 'qusmarsh')."""
    return "".join(c for c in s.lower() if c.isalnum())


_NAME_TO_LOCIDS: dict[str, list[int]] = {}
for _loc, _nm in MARKER_NAMES.items():
    _NAME_TO_LOCIDS.setdefault(_norm(_nm), []).append(_loc)
for _k in _NAME_TO_LOCIDS:
    _NAME_TO_LOCIDS[_k].sort()


def resolve_markers(entries) -> list[int]:
    """Resolve a ``reveal_markers`` list to a sorted list of unique marker locIds (0-63).

    Each entry is an ``int`` locId (0-63), a location NAME (str; resolves to ALL its slots, so ``"South
    Gate"`` -> [6,7,8,9,10]), or the literal ``"all"`` (every slot 0-63). Raises ``ValueError`` on an unknown
    name or out-of-range id. A single string that isn't ``"all"`` and isn't a known name is an error (with a
    hint), so a typo can't silently no-op."""
    if entries is None:
        return []
    if isinstance(entries, (str, int)) and not isinstance(entries, bool):
        entries = [entries]
    out: set[int] = set()
    for e in entries:
        if isinstance(e, bool):
            raise ValueError(f"reveal_markers entry must be a locId int or a location name (got {e!r})")
        if isinstance(e, int):
            if not (0 <= e < NAVI_LOCATION_COUNT):
                raise ValueError(f"reveal_markers locId must be 0..{NAVI_LOCATION_COUNT - 1} (got {e})")
            out.add(e)
        elif isinstance(e, str):
            if e.strip().lower() == "all":
                out.update(range(NAVI_LOCATION_COUNT))
                continue
            locs = _NAME_TO_LOCIDS.get(_norm(e))
            if not locs:
                raise ValueError(
                    f"unknown worldmap marker {e!r} -- use a location name "
                    f"(e.g. 'Alexandria', 'Ice Cavern'), a locId 0..63, or 'all'")
            out.update(locs)
        else:
            raise ValueError(f"reveal_markers entry must be a locId int or a location name (got {e!r})")
    return sorted(out)


def marker_presets(entries) -> list[tuple[int, int]]:
    """``reveal_markers`` -> ``(bit_index, 1)`` GLOB-bit presets for :func:`content.startup.startup_body`."""
    return [(marker_bit(loc), 1) for loc in resolve_markers(entries)]
