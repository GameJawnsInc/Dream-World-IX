"""Engine behaviors keyed on a field's real ``fldMapNo``/``fldLocNo`` -- which a FORK keeps and which it loses on
a custom id -- the **lost-on-a-mint** axis of the fork-fidelity taxonomy (``docs/FORK_FIDELITY.md``), made
per-field queryable so ``fork-report`` can preview it.

When you fork a field it runs at a new custom id (>= 4000), so every engine special-case gated on the RAW real
id silently stops firing. The custom engine's fork-gate suite (``memoria-patches/``) routes many gates through
``EffectiveFieldId``, which restores them for a fork that RECORDS ITS DONOR: ``[verbatim_eb] donor`` /
``[field] source_field`` becomes a ``ForkDonorPatch.txt`` row, the only thing ``EffectiveFieldId`` reads.
``import --native``/``--verbatim`` record it; an ``--editable`` or plain BG-borrow import does not. An entry
whose detail says ``reproduced`` is kept on such a fork; ``fork-report`` counts the rest as losses. The
USER-VISIBLE ones:

* **Walkmesh hotfix** -- a load-time/dynamic ``BGI_triSetActive`` (catalogued in
  :mod:`ff9mapkit.walkmesh_hotfixes`: which gates the engine remaps for a fork, which the kit prepends, and which
  stay lost). Referenced here so the lost-on-mint list is one place.
* **Narrow-map letterbox** -- the engine letterboxes a field narrower than widescreen (``NarrowMapList``'s
  per-field width table). REPRODUCED: s23 looks the width up by the donor id and s65 wraps FieldMap's widescreen
  setup, so a donor-recorded fork gets the donor's exact width; with no donor row s23 falls back to the loaded BG
  camera's width. Widths baked in :mod:`ff9mapkit._narrowmap_data`.
* **Narrow-camera letterbox** -- ``NarrowMapList.RestrictedCams`` holds one camera of a field narrower than the
  field itself. LOST: ``PSXCameraAspect.LateUpdate`` reads it on the raw ``fldMapNo`` and no patch touches that file.
* **Chocobo dig HUD** -- the live Hot&Cold HUD state (``EventHUD.CheckUIMiniGameForMobile``, ``fldMapNo``
  2950-2952). REPRODUCED: s24 wraps that function's ``fldMapNo`` alias; the instruction popup keys on text zone
  945, which a fork keeps. On PC the MinigameHUD prefab itself never renders (``FieldHUD.DisplaySpecialHUD`` is
  mobile-only); the state still keeps player control on during the dig, fixes the Depth window's size and hides
  the "here" icon.
* **Intro FMV** -- the field-70 opening movie. LOST: ``LoadFieldMap``/``BG_init``/``BGI_DEF`` and the actor
  updates gate on the raw ``fldMapNo == 70`` (only two FieldMap camera sites are wrapped).
* **ATE achievement** -- a field's ATEs count toward the *ATE80* trophy via ``EMinigame.MappingATEID``, which
  keys on ``fldLocNo`` (the field's LOCATION). The engine sets ``fldLocNo = eventIDToMESID[fldMapNo]``
  (``HonoluluFieldMain.cs:19``) -- i.e. the field's registered MES/text-block id -- so we resolve it from the
  baked :data:`ff9mapkit._fieldtext.EVENT_ID_TO_MES`. Every kit import puts a fork on its donor's text block, so
  ``fldLocNo`` CARRIES (no engine patch needed). A few locations also compare ``fldMapNo`` inside the branch
  (:data:`ATE_FIELD_GATES`): s65 wraps all of them but field 956's, so only that compulsory ATE is lost. The ATE
  itself always PLAYS; only the trophy bookkeeping is at stake.
* **Per-actor tweak** -- a hardcoded ``FieldMapActor.cs`` per-actor special-case (a camera-priority override, a
  ``GeoAttach``/``GeoDetach`` parent-node graft quirk, or a shadow-render offset/depth override), keyed on
  ``fldMapNo`` plus an actor ``sid``/``uid``/``isPlayer``/``anim``/map-index condition. s65 wraps 661, 2102, 2107
  and 3002; the rest stay raw. NONE are reproducible by a fork's own ``.eb`` (no opcode sets ``frontCamera``, a
  shadow-renderer property, a ``GeoAttach`` offset, or ``HonoBehaviorSystem.ExtraLoopCount``), so a raw one is
  fork-in-place-or-accept. Baked in :mod:`ff9mapkit.fieldmapactor_tweaks`.

``tests/test_idgated.py`` and ``tests/test_fieldmapactor_tweaks.py`` check every remapped/raw claim here against
``memoria-patches/``. This is pure baked data (no install needed) -- safe to call from the install-free analysis
path.
"""
from __future__ import annotations

from . import fieldmapactor_tweaks as _fma
from . import walkmesh_hotfixes as _wh
from ._fieldtext import EVENT_ID_TO_MES as _EVENT_TO_MES
from ._narrowmap_data import FORK_DEFAULT_WIDTH, RESTRICTED_CAMS as _CAMS, WIDTHS as _WIDTHS

# fldLocNo == the field's MES id (HonoluluFieldMain.cs:19). These LOCATIONS have ATE-seen trophy mappings
# (EMinigame.MappingATEID, lines 532-669 -- all `fldLocNo == N` cases; Memoria source, provenance-clean).
ATE_ACHIEVEMENT_LOCS = frozenset({4, 8, 32, 37, 40, 44, 47, 52, 53, 70, 88, 90,
                                  276, 289, 344, 358, 359, 485, 525, 595, 741, 943})

# MappingATEID's INNER fldMapNo compares: field -> (the location branch it sits in, the patch that routes it through
# EffectiveFieldId, or None while it is still raw). A compare only counts for a field that belongs to that location:
# 204 sits in loc 4's branch but is itself loc 40, so stock never reaches it.
ATE_FIELD_GATES = {206: (40, "s65"), 204: (4, "s65"), 253: (4, "s65"), 262: (4, "s65"), 306: (8, "s65"),
                   554: (276, "s65"), 552: (276, "s65"), 565: (276, "s65"), 1307: (485, "s65"),
                   1353: (525, "s65"), 956: (359, None), 2169: (943, "s65"), 2113: (595, "s65"),
                   2173: (943, "s65")}
# Locations whose branch maps NOTHING but its inner compare: their other fields have no ATE trophy at all.
_ATE_ONLY_BY_FIELD = {8: 306, 359: 956, 525: 1353}

# ~16:9 of the 240px PSX height: a field narrower than this is letterboxed in-game.
WIDESCREEN_WIDTH = 426
CHOCOBO_HUD_FIELDS = frozenset({2950, 2951, 2952})   # EventHUD.cs: the live Chocobo Hot&Cold dig HUD
FMV_INTRO_FIELDS = frozenset({70})                    # field-70 opening movie (Cinematic ops + MBG)

_REMAP = "reproduced by the engine fork-donor remap on a fork that records its donor"


def _as_id(field):
    try:
        return int(field)
    except (TypeError, ValueError):
        return None


def narrow_map_width(field) -> int:
    """The field's real PSX screen width (NarrowMapList), or the stock default (500) for an unlisted id."""
    f = _as_id(field)
    return _WIDTHS.get(f, FORK_DEFAULT_WIDTH) if f is not None else FORK_DEFAULT_WIDTH


def is_letterboxed(field) -> bool:
    """True if the real field is narrower than widescreen, so the engine letterboxes it."""
    f = _as_id(field)
    return f is not None and f in _WIDTHS and _WIDTHS[f] < WIDESCREEN_WIDTH


def loses_letterbox(field, *, donor_recorded: bool = True) -> bool:
    """True if a fork of ``field`` is not guaranteed the real field's letterbox width. A fork that records its donor
    gets the donor's exact width (s23 + s65), so this is False for it; with no donor row the width falls back to the
    loaded BG camera's, which the kit cannot check offline -- True for a letterboxed field."""
    return is_letterboxed(field) and not donor_recorded


def restricted_cams(field) -> tuple:
    """``((camera index, PSX width), ...)`` for the field's ``RestrictedCams`` rows that narrow a camera below the
    field's own width -- read on the raw ``fldMapNo``, so lost on a mint. ``()`` for most fields. A row no narrower
    than the field (63's camera 0, 2363's camera 0) changes nothing, even on the real field."""
    f = _as_id(field)
    if f is None:
        return ()
    width = _WIDTHS.get(f, FORK_DEFAULT_WIDTH)
    return tuple((cam, w) for cam, w in _CAMS.get(f, ()) if w < width)


def field_loc_no(field):
    """The field's ``fldLocNo`` (== its registered MES/text-block id, ``eventIDToMESID[fldMapNo]``), or None."""
    f = _as_id(field)
    return _EVENT_TO_MES.get(f) if f is not None else None


def has_ate_achievement(field) -> bool:
    """True if one of the field's ATEs maps to an ATE-seen trophy id (``EMinigame.MappingATEID``)."""
    f, loc = _as_id(field), field_loc_no(field)
    if loc is None or loc not in ATE_ACHIEVEMENT_LOCS:
        return False
    return _ATE_ONLY_BY_FIELD.get(loc, f) == f


def ate_field_gate(field):
    """``(loc, patch)`` when the field's trophy mapping also compares its own ``fldMapNo`` (``patch`` None = the
    compare is still raw), else None -- the location key alone decides."""
    f = _as_id(field)
    gate = ATE_FIELD_GATES.get(f) if f is not None else None
    return gate if gate is not None and gate[0] == field_loc_no(f) else None


def actor_tweaks(field) -> tuple:
    """The ``FieldMapActor.cs`` per-actor tweak(s) (:mod:`ff9mapkit.fieldmapactor_tweaks`) keyed on this field's
    real id -- camera priority / geo-attach / shadow-render. ``()`` for the vast majority of fields."""
    f = _as_id(field)
    return _fma.info(f) if f is not None else ()


def lost_on_mint(field) -> list:
    """``[(label, detail), ...]`` for every USER-VISIBLE id-gated engine behavior of ``field`` a fork on a custom id
    could lose. Empty for most fields. Each detail says whether the engine remap or the kit reproduces it; the rest
    steer to *fork in-place on the real id* (or accept the loss). Used by ``fork-report``, whose verdict counts an
    entry as lost unless its detail says ``reproduced``."""
    f = _as_id(field)
    if f is None:
        return []
    out = []
    h = _wh.info(f)
    if h is not None:
        if h.engine_remapped and h.kind == "load_time":
            repro = _REMAP
        elif h.engine_remapped and h.kind == "collision":
            repro = ("reproduced by the engine fork-donor remap -- a per-triangle collision rule, keyed on the "
                     "fork's own walkmesh ids")
        elif h.engine_remapped:
            repro = ("reproduced by the engine fork-donor remap on a fork that runs the donor's own trigger "
                     "(--verbatim)")
        elif h.auto:
            repro = "auto-reproduced on fork"
        elif h.fork_tris:              # one arm remapped, another still on the raw id -> still a loss
            repro = (f"fork-in-place -- the engine fork-donor remap keeps only its remapped arm "
                     f"(tri {', '.join(map(str, h.fork_tris))}); the rest stays on the raw id")
        else:
            repro = "fork-in-place"
        out.append(("walkmesh hotfix", f"{h.name} ({repro})"))
    if is_letterboxed(f):
        out.append(("narrow-map letterbox",
                    f"real width {_WIDTHS[f]} < widescreen -- {_REMAP} (s23 NarrowMapList + s65 FieldMap: the "
                    f"donor's exact width); with no donor row s23 uses the BG camera's own width instead"))
    for cam, w in restricted_cams(f):
        out.append(("narrow-camera letterbox",
                    f"camera {cam} is held to width {w} (NarrowMapList.RestrictedCams), read on the raw fldMapNo in "
                    f"PSXCameraAspect.cs, which no patch touches -> a fork renders it at the field's width; "
                    f"fork in-place"))
    if f in CHOCOBO_HUD_FIELDS:
        out.append(("Chocobo dig HUD",
                    f"the live Hot&Cold HUD state is gated on fldMapNo 2950-2952 (EventHUD.cs) -- {_REMAP} (s24); "
                    f"the instruction popup keys on text zone 945, which a fork keeps"))
    if f in FMV_INTRO_FIELDS:
        out.append(("intro FMV", "the field-70 opening movie is id-bound (LoadFieldMap, BG_init, BGI_DEF and the "
                                 "actor updates gate on the raw fldMapNo 70) -> retarget the stock field-70 override"))
    if has_ate_achievement(f):
        loc, gate = field_loc_no(f), ate_field_gate(f)
        head = f"this location (fldLocNo {loc}) has an ATE-seen trophy (EMinigame.MappingATEID)"
        if gate is None:
            detail = (f"{head}, keyed on fldLocNo alone -- reproduced on any fork that stays on the donor's text "
                      f"block (every kit import does), since fldLocNo is the registered mes id")
        elif gate[1] is None:
            detail = (f"{head}; its compulsory ATE maps only on the raw fldMapNo {f}, which no patch wraps -> a "
                      f"fork's compulsory ATE counts toward no trophy (the ATE still plays); fork in-place")
        else:
            detail = (f"{head} and a fldMapNo {f} compare -- {_REMAP} ({gate[1]} wraps the compare; fldLocNo "
                      f"carries with the donor's text block)")
        out.append(("ATE achievement", detail))
    for t in _fma.info(f):
        tail = f"{_REMAP} (s65)" if t.engine_remapped else "fork in-place"
        out.append((f"actor {t.kind.replace('_', ' ')}", f"{t.note} ({t.source}, {t.severity}) -> {tail}"))
    return out
