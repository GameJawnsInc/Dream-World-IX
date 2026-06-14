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

Known GAP (not yet per-field here): the **ATE achievement** (``EMinigame.MappingATEID``) is keyed on
``fldLocNo`` (location) + scenario, not a plain field id, so it needs a field->location map to surface
per-field -- deferred. The ATE itself still PLAYS in a fork; only the trophy bookkeeping is id-bound.

This is pure baked data (no install needed) -- safe to call from the install-free analysis path.
"""
from __future__ import annotations

from . import walkmesh_hotfixes as _wh
from ._narrowmap_data import FORK_DEFAULT_WIDTH, WIDTHS as _WIDTHS

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
        out.append(("walkmesh hotfix",
                    f"{h.name} ({'auto-reproduced on fork' if h.auto else 'fork-in-place'})"))
    if loses_letterbox(f):
        out.append(("narrow-map letterbox",
                    f"real width {_WIDTHS[f]} < widescreen; a fork renders widescreen "
                    f"(width {FORK_DEFAULT_WIDTH}) so the letterbox masking is lost"))
    if f in CHOCOBO_HUD_FIELDS:
        out.append(("Chocobo dig HUD", "the live Hot&Cold HUD is gated on fldMapNo 2950-2952 -> fork in-place"))
    if f in FMV_INTRO_FIELDS:
        out.append(("intro FMV", "the field-70 opening movie is id-bound -> retarget the stock field-70 override"))
    return out
