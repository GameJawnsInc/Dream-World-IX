"""Engine FieldMapActor.cs PER-ACTOR TWEAKS that a fork loses on a minted id -- the catalog.

A handful of real fields rely on a **hardcoded Memoria per-actor tweak in ``FieldMapActor.cs``, keyed on the
real ``fldMapNo``** plus an actor condition (``sid``/``uid``/``isPlayer``/``anim``/a map-index story var): a
camera-priority override (``actor.frontCamera``, deciding which actor draws in FRONT when depth-sorting goes
out of range), a ``GeoAttach``/``GeoDetach`` parent-node graft quirk (a ``curPos`` special-case, an attach-offset
override, or a ``HonoBehaviorSystem.ExtraLoopCount`` bump on detach), or a shadow-render tweak (a hardcoded
shadow offset, a renderer's ``_CharZ``, or a shadow-position override). A verbatim/native fork ships the same
actor at a CUSTOM id (>= 4000), so every ``fldMapNo == <real id>`` guard is false and the tweak never fires --
the forked actor is subtly wrong at that beat (the wrong actor draws in front, a graft snaps to the wrong spot,
a shadow sits in the wrong place). This is ``docs/FORK_FIDELITY.md`` residual #5 ("Field-70 FMV + ~12 per-actor
anim tweaks on a mint" -- *generalizes: any real-``fldMapNo``-gated engine behavior is lost on a mint*), made
concrete + per-field-queryable for the per-actor dimension.

**NONE of these are reproducible by a fork's own ``.eb``**: there is no opcode that sets ``actor.frontCamera``,
a shadow-renderer property, a ``GeoAttach`` offset, or ``HonoBehaviorSystem.ExtraLoopCount`` -- so, unlike the
walkmesh hotfix's ``EnablePathTriangle`` opcode (:mod:`ff9mapkit.walkmesh_hotfixes`), no ``content/*.py`` injector
exists for this axis. The whole axis is fork-in-place-or-accept, like the narrow-map letterbox
(:mod:`ff9mapkit._narrowmap_data`): cataloged here so ``fork-report`` (:mod:`ff9mapkit.idgated`) can surface it
as "lost on a mint", never auto-applied.

Source (Memoria, ``Assembly-CSharp``, compile-matched to ``6b8bb2d5``): ``Global/Field/Map/Actor/FieldMapActor.cs``.
Read-only reference data -- ships no Square-Enix bytes.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActorTweak:
    """One real field's ``FieldMapActor.cs`` per-actor tweak.

    ``kind``     : ``camera_priority`` (the ``HonoLateUpdate`` out-of-depth-range ``frontCamera`` fallback) |
                   ``geo_attach`` (a ``GeoAttach``/``GeoDetach`` parent-node graft quirk) | ``shadow_render`` (a
                   shadow offset / renderer ``_CharZ`` / shadow-position override).
    ``severity`` : ``FUNCTIONAL`` (changes actor BEHAVIOR -- draw priority or attach position) | ``COSMETIC``
                   (visual-only -- a shadow's offset/depth), matching the tier in ``docs/FORK_IDGATE_MAP.md``.
    ``note``     : what the tweak does + the actor/condition it keys on (sid/uid/isPlayer/anim/map-index),
                   verified against the live source, prose.
    ``source``   : ``FieldMapActor.cs:<line>``.
    """

    field_id: int
    name: str
    kind: str
    severity: str
    note: str
    source: str


_TWEAKS = {
    # --- camera_priority (HonoLateUpdate's out-of-depth-range actor.frontCamera fallback) --------------------
    1413: (ActorTweak(1413, "Fossil Roo/Nest", "camera_priority",
                       "FUNCTIONAL",
                       "HonoLateUpdate's out-of-depth-range branch (psxDepth < 100 or > 3996) sets "
                       "actor.frontCamera = (originalActor.sid == 12) -- true only for Zidane (sid 12), so he "
                       "alone keeps front-camera draw priority when this actor falls out of depth range.",
                       "FieldMapActor.cs:135"),),
    1414: (ActorTweak(1414, "Fossil Roo/Nest", "camera_priority",
                       "FUNCTIONAL",
                       "Same out-of-depth-range branch as 1413, keyed on sid == 16 instead of 12 (a different "
                       "Zidane-bearing actor slot in this room's second camera/entrance set).",
                       "FieldMapActor.cs:141"),),
    2752: (ActorTweak(2752, "Invincible/Bridge", "camera_priority",
                       "FUNCTIONAL",
                       "The out-of-depth-range branch's general fallback (actor.frontCamera = false) is itself "
                       "gated: it fires for every field EXCEPT fldMapNo 2752 and 1707, so on those two ids the "
                       "actor's frontCamera keeps whatever value it already had instead of being forced off.",
                       "FieldMapActor.cs:147"),),
    1707: (ActorTweak(1707, "Mdn. Sari/Secret Room", "camera_priority",
                       "FUNCTIONAL",
                       "The out-of-depth-range branch's general fallback (actor.frontCamera = false) is itself "
                       "gated: it fires for every field EXCEPT fldMapNo 2752 and 1707, so on those two ids the "
                       "actor's frontCamera keeps whatever value it already had instead of being forced off.",
                       "FieldMapActor.cs:147"),),

    # --- geo_attach (GeoAttach/GeoDetach parent-node graft quirks) --------------------------------------------
    1410: (ActorTweak(1410, "Fossil Roo zone", "geo_attach",
                       "FUNCTIONAL",
                       "GeoAttach's Fossil Roo range gate (fldMapNo 1400-1425) normally snaps a PLAYER-controlled "
                       "actor's curPos to the parent node's position on attach; field 1410 is exempted from that "
                       "snap (isPlayer's curPos is left at the temporary zeroed pre-attach value) -- unlike 1412 "
                       "(below), which restores the ORIGINAL curPos instead.",
                       "FieldMapActor.cs:243"),),
    1412: (ActorTweak(1412, "Fossil Roo zone", "geo_attach",
                       "FUNCTIONAL",
                       "Same shared Fossil Roo range gate (fldMapNo 1400-1425) as 1410; on field 1412 a "
                       "PLAYER-controlled actor's curPos is explicitly restored to its PRE-attach value (captured "
                       "before the temporary zero-reset) rather than snapping to the parent node (the general "
                       "rule for the rest of the range) or staying zeroed (1410's case).",
                       "FieldMapActor.cs:243"),),
    2954: (ActorTweak(2954, "Chocobo's Air Garden", "geo_attach",
                       "FUNCTIONAL",
                       "GeoAttach overrides the attach offset to (30,150,0) when fldMapNo == 2954 AND the "
                       "map-index story var (EBin.MAP_INDEX_SVR) reads 8 -- a specific floor/mapindex of the "
                       "Air Garden gets a taller attach point than the shared default offset.",
                       "FieldMapActor.cs:261"),),
    3002: (ActorTweak(3002, "(Ending)", "geo_attach",
                       "FUNCTIONAL",
                       "GeoDetach sets HonoBehaviorSystem.ExtraLoopCount = 1 when fldMapNo == 3002 AND the "
                       "detaching actor's originalActor.sid == 2 with originalActor.anim == 11022 -- a specific "
                       "actor/clip pair on the ending field gets one extra animation loop on detach.",
                       "FieldMapActor.cs:297"),),

    # --- shadow_render (COSMETIC: shadow offset / renderer _CharZ / shadow-position override) -----------------
    2510: (ActorTweak(2510, "I. Castle/Mural Room", "shadow_render",
                       "COSMETIC",
                       "HonoLateUpdate sets the actor's renderer material _CharZ = 20 when fldMapNo == 2510 AND "
                       "actor.uid == 8 (the Water_Mirror actor) -- a draw-depth nudge, not a behavior change.",
                       "FieldMapActor.cs:164"),),
    2363: (ActorTweak(2363, "Gulug/Path", "shadow_render",
                       "COSMETIC",
                       "HonoLateUpdate sets renderer _CharZ = 20 when fldMapNo == 2363 AND actor.uid == 33 "
                       "(Thorn) -- a draw-depth nudge.",
                       "FieldMapActor.cs:169"),
           ActorTweak(2363, "Gulug/Path", "shadow_render",
                       "COSMETIC",
                       "A second, separate check applies a shadow offset (0,-15,0) when fldMapNo == 2363 AND "
                       "actor.uid is 15, 16, 32, or 33 (Zorn or Thorn) -- a wider uid set than the uid==33-only "
                       "_CharZ tweak above, and a different property (shadow position, not draw depth).",
                       "FieldMapActor.cs:187")),
    661: (ActorTweak(661, "Marsh/Master's House", "shadow_render",
                      "COSMETIC",
                      "A hardcoded shadow offset (-39,-14,80) is applied when fldMapNo == 661 AND actor.uid == 3 "
                      "(Quale).",
                      "FieldMapActor.cs:181"),),
    1659: (ActorTweak(1659, "Iifa Tree/Seashore", "shadow_render",
                       "COSMETIC",
                       "A shadow offset (0,-66,0) is applied when fldMapNo == 1659 AND actor.uid == 128 "
                       "(Queen_Brahne, instance 1).",
                       "FieldMapActor.cs:183"),
            ActorTweak(1659, "Iifa Tree/Seashore", "shadow_render",
                       "COSMETIC",
                       "A sibling else-if applies a DIFFERENT shadow offset (0,-21,0) when fldMapNo == 1659 AND "
                       "actor.uid == 129 (Queen_Brahne, instance 2 -- the field carries two Queen_Brahne actors, "
                       "each with its own offset).",
                       "FieldMapActor.cs:185")),
    2107: (ActorTweak(2107, "Lindblum/Square", "shadow_render",
                       "COSMETIC",
                       "The shadow position is overridden to the actor's own transform XZ with y=0 (instead of "
                       "the usual computed shadow-ground position) when fldMapNo == 2107 AND actor.uid == 5 -- "
                       "shares its site with field 2102 below (the Pickaxe prop).",
                       "FieldMapActor.cs:190"),),
    2102: (ActorTweak(2102, "Lindblum/Main Street", "shadow_render",
                       "COSMETIC",
                       "Same shared site as 2107 above; fires when fldMapNo == 2102 AND actor.uid == 4 instead "
                       "(the Pickaxe prop's other placement).",
                       "FieldMapActor.cs:190"),),
}


def info(field_id) -> tuple:
    """Every :class:`ActorTweak` for a real field id, or ``()`` if the field has no ``FieldMapActor.cs``
    per-actor tweak (the vast majority). ``field_id`` may be an int or a numeric string."""
    try:
        return _TWEAKS.get(int(field_id), ())
    except (TypeError, ValueError):
        return ()
