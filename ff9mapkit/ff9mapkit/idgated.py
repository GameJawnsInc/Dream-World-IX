"""Engine behaviors keyed on a field's real ``fldMapNo``/``fldLocNo`` that a FORK loses on a custom id --
the **lost-on-a-mint** axis of the fork-fidelity taxonomy (``docs/FORK_FIDELITY.md``), made per-field
queryable so ``fork-report`` can preview it.

When you fork a field it runs at a new custom id (>= 4000), so every engine special-case gated on the real id
silently stops firing. Most are internal (camera/position fixups); the USER-VISIBLE ones a fork loses are:

* **Walkmesh hotfix** -- a load-time/dynamic ``BGI_triSetActive`` (catalogued + sometimes auto-reproduced in
  :mod:`ff9mapkit.walkmesh_hotfixes`). Referenced here so the lost-on-mint list is one place.
* **Narrow-map letterbox** -- the engine letterboxes a field narrower than widescreen (NarrowMapList, a
  per-field width table); a fork defaults to width 500 (widescreen), so the side masking is lost and off-screen
  party can draw over where the bars were. Widths baked in :mod:`ff9mapkit._narrowmap_data`.
* **Chocobo dig HUD** -- the live Hot&Cold timer/HUD is gated on ``fldMapNo`` 2950-2952 (``EventHUD.cs``).
* **Intro FMV** -- the field-70 opening movie is id-bound.
* **ATE achievement** -- a field's ATEs count toward the *ATE80* trophy via ``EMinigame.MappingATEID``, which
  keys on ``fldLocNo`` (the field's LOCATION). The engine sets ``fldLocNo = eventIDToMESID[fldMapNo]``
  (``HonoluluFieldMain.cs:19``) -- i.e. the field's registered MES/text-block id -- so we resolve it from the
  baked :data:`ff9mapkit._fieldtext.EVENT_ID_TO_MES`. A mint runs at a custom id with a different text-block,
  so its ATEs don't map to the trophy. The ATE itself still PLAYS; only the achievement bookkeeping is lost.

This is pure baked data (no install needed) -- safe to call from the install-free analysis path.
"""
from __future__ import annotations

from . import walkmesh_hotfixes as _wh
from ._fieldtext import EVENT_ID_TO_MES as _EVENT_TO_MES
from ._narrowmap_data import FORK_DEFAULT_WIDTH, WIDTHS as _WIDTHS

# fldLocNo == the field's MES id (HonoluluFieldMain.cs:19). These LOCATIONS have ATE-seen trophy mappings
# (EMinigame.MappingATEID, lines 532-669 -- all `fldLocNo == N` cases; Memoria source, provenance-clean).
ATE_ACHIEVEMENT_LOCS = frozenset({4, 8, 32, 37, 40, 44, 47, 52, 53, 70, 88, 90,
                                  276, 289, 344, 358, 359, 485, 525, 595, 741, 943})

# ~16:9 of the 240px PSX height: a field narrower than this is letterboxed in-game, but a fork (width 500)
# renders widescreen, so the side letterbox masking is lost (the project-ff9-narrow-map-fork-letterbox bug).
WIDESCREEN_WIDTH = 426
CHOCOBO_HUD_FIELDS = frozenset({2950, 2951, 2952})   # EventHUD.cs: the live Chocobo Hot&Cold dig HUD
FMV_INTRO_FIELDS = frozenset({70})                    # field-70 opening movie (Cinematic ops + MBG)


def _as_id(field):
    try:
        return int(field)
    except (TypeError, ValueError):
        return None


def narrow_map_width(field) -> int:
    """The field's real PSX screen width (NarrowMapList), or the fork default (500) for an unlisted id."""
    f = _as_id(field)
    return _WIDTHS.get(f, FORK_DEFAULT_WIDTH) if f is not None else FORK_DEFAULT_WIDTH


def loses_letterbox(field) -> bool:
    """True if the real field is narrower than widescreen, so a fork (default width 500) loses its letterbox."""
    f = _as_id(field)
    return f is not None and f in _WIDTHS and _WIDTHS[f] < WIDESCREEN_WIDTH


def field_loc_no(field):
    """The field's ``fldLocNo`` (== its registered MES/text-block id, ``eventIDToMESID[fldMapNo]``), or None."""
    f = _as_id(field)
    return _EVENT_TO_MES.get(f) if f is not None else None


def has_ate_achievement(field) -> bool:
    """True if the field's location has an ATE-seen trophy mapping (lost on a mint -- a different fldLocNo)."""
    loc = field_loc_no(field)
    return loc is not None and loc in ATE_ACHIEVEMENT_LOCS


def lost_on_mint(field) -> list:
    """``[(label, detail), ...]`` for every USER-VISIBLE id-gated engine behavior a fork of ``field`` loses on
    its custom id. Empty for most fields. The walkmesh entry notes whether the kit auto-reproduces it; the rest
    steer to *fork in-place on the real id* (or accept the loss). Used by ``fork-report``."""
    f = _as_id(field)
    if f is None:
        return []
    out = []
    h = _wh.info(f)
    if h is not None:
        if h.engine_remapped:
            repro = "reproduced by the engine fork-donor remap"
        elif h.auto:
            repro = "auto-reproduced on fork"
        else:
            repro = "fork-in-place"
        out.append(("walkmesh hotfix", f"{h.name} ({repro})"))
    if loses_letterbox(f):
        out.append(("narrow-map letterbox",
                    f"real width {_WIDTHS[f]} < widescreen; a fork renders widescreen "
                    f"(width {FORK_DEFAULT_WIDTH}) so the letterbox masking is lost"))
    if f in CHOCOBO_HUD_FIELDS:
        out.append(("Chocobo dig HUD", "the live Hot&Cold HUD is gated on fldMapNo 2950-2952 -> fork in-place"))
    if f in FMV_INTRO_FIELDS:
        out.append(("intro FMV", "the field-70 opening movie is id-bound -> retarget the stock field-70 override"))
    if has_ate_achievement(f):
        out.append(("ATE achievement",
                    f"this location (fldLocNo {field_loc_no(f)}) has an ATE-seen trophy (EMinigame.MappingATEID); "
                    f"a mint's different fldLocNo loses the ATE80 bookkeeping (the ATE still plays) -> fork in-place"))
    return out
