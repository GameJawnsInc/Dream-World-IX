"""Engine WALKMESH HOTFIXES that a fork loses on a minted id -- the catalog.

A handful of real fields rely on a **hardcoded Memoria engine hotfix, keyed on the real ``fldMapNo``**, that
toggles walkmesh-triangle active-state (``WalkMesh.BGI_triSetActive(triNdx, isActive)``, which flips bit 0 of
the triangle's ``triFlags`` -- the walkable bit -- both in the loaded ``BGI_DEF`` and the runtime mesh). A
verbatim/native fork ships the same ``.bgi`` but runs at a CUSTOM id (>= 4000), so every ``mapNo == <real id>``
guard is false and the hotfix never fires -- the forked walkmesh is subtly wrong at that beat (a wall stays
walkable, an NPC can't reach its spot, a blocked stair is open). This is the "real-``fldMapNo``-gated engine
behavior is lost on a mint" residual from ``docs/FORK_FIDELITY.md`` (the carry taxonomy), made concrete for the
walkmesh dimension.

There are two tractability classes:

* **LOAD-TIME, unconditional** (``FieldMap.BG_init`` / ``DelayedActiveTri``, keyed on ``fldMapNo`` only): the
  triangle state is asserted at field load with no runtime condition. A fork reproduces it EXACTLY by
  prepending ``EnablePathTriangle(tri, state)`` -- the same opcode (0x9A) whose handler IS ``BGI_triSetActive``
  -- to ``Main_Init`` (``content.walkmesh_hotfix.apply_tri_toggles``). The ``.bgi`` stays byte-verbatim; the
  fix lives in the script layer, exactly as the engine's own opcode would. These carry ``toggles`` and are
  AUTO-reproduced by the build (``[field] walkmesh_tri_toggles``, auto-emitted by ``import`` for these donors).
* **EVENT-CODE / DYNAMIC / OPCODE-AUGMENT** (``DoEventCode`` + ``turnOffTriManually``, keyed on ``mapNo`` plus a
  runtime condition -- an object uid/sid/tag, a position, or a story var): the toggle fires DURING play, so a
  static prepend can't reproduce it faithfully (e.g. Daguerreo's librarian tris TRACK ``gEventGlobal`` var
  761060). These are cataloged with a reproduction ``note`` and surfaced by ``fork-report`` as "lost on a mint
  -> fork in-place on the real id (or accept it)". They are NOT auto-applied -- a per-field bespoke splice
  (locate the trigger ``.eb`` site, splice the toggle) is a possible follow-up, recorded in each note.

Source (Memoria, ``Assembly-CSharp``, compile-matched to ``6b8bb2d5``):
``Global/Field/Map/FieldMap.cs`` (load-time), ``Global/Event/Engine/EventEngine.DoEventCode.cs`` (event-code +
the BGIACTIVE 0x9A handler's own ``mapNo`` augments), ``Global/Event/Engine/EventEngine.turnOffTriManually.cs``
(dynamic). Read-only reference data -- ships no Square-Enix bytes.
"""
from __future__ import annotations

from dataclasses import dataclass, field as _dc_field


@dataclass(frozen=True)
class Hotfix:
    """One real field's engine walkmesh hotfix.

    ``kind``    : ``load_time`` (auto-reproducible) | ``event_code`` | ``dynamic`` | ``opcode_augment``.
    ``toggles`` : the load-time ``(tri, state)`` pairs (state 1 = active/walkable, 0 = inactive) -- the AUTO
                  set, non-empty only for ``load_time``.
    ``tris``    : every triangle index the hotfix touches (for reporting, incl. the non-auto kinds).
    ``note``    : what it does + the runtime condition + (for non-auto) the reproduction recipe.
    ``source``  : the Memoria source location.
    ``engine_remapped`` : the SHIPPED custom engine already reproduces this hotfix faithfully for a fork (its
                  ``fldMapNo`` gate is wrapped with ``EffectiveFieldId``, so it fires for the fork id too) WITH the
                  original timing -- so the kit must NOT also prepend a Main_Init toggle. Set when the engine hotfix
                  is DELAYED (e.g. 2507's ``DelayedActiveTri`` runs 0.5s after load): the at-load toggle prepend
                  fires BEFORE the field's own props settle onto those tris, snapping them to the wrong floor (the
                  Ipsen chests dropped a level). Reproduce delayed hotfixes via the engine remap, not the prepend.
    """

    field_id: int
    name: str
    kind: str
    note: str
    source: str
    toggles: tuple = ()
    tris: tuple = ()
    engine_remapped: bool = False

    @property
    def auto(self) -> bool:
        """True when the build SHOULD reproduce this hotfix via a Main_Init tri-toggle prepend. False for an
        ``engine_remapped`` hotfix: the shipped engine already reproduces it for the fork id (correct timing),
        and the at-load prepend would mis-time it (see ``engine_remapped``)."""
        return self.kind == "load_time" and bool(self.toggles) and not self.engine_remapped


_HOTFIXES = {
    # --- LOAD-TIME (unconditional at field load; AUTO-reproduced) -------------------------------------------
    2356: Hotfix(2356, "Gulug/Room (the Red-Dragon-wall room)", "load_time",
                 "At field load the engine deactivates 3 floor triangles around a 3D treasure-chest prop (entry "
                 "5, GEO_ACC_F0_TBX @ (-426,1664)). The engine comment '(Red Dragon bursting through wall)' names "
                 "the ROOM (field 2356), not these tris' job. ★ IN-GAME PROVEN by A/B (2026-06-14): teleporting "
                 "to the patch EDGE (-543,1667) -- ~120u from the chest, beyond its collision -- is STUCK with the "
                 "toggle (id 30003) and FREE without it (id 30004), so the toggle (not the chest) blocks that "
                 "floor. The patch extends ~120u around the chest, so it blocks more than the chest's collision "
                 "alone -- the hotfix is NOT redundant. (Confound to avoid: the tri-78 CENTER (39u) coincides "
                 "with the chest collision; test the edge.)",
                 "FieldMap.cs:112-117", toggles=((78, 0), (79, 0), (80, 0)), tris=(78, 79, 80)),
    2161: Hotfix(2161, "L. Castle/Guest Room (disc 3)", "load_time",
                 "At field load the engine deactivates one triangle (a disc-3 room-layout block). Unconditional.",
                 "FieldMap.cs:119-122", toggles=((69, 0),), tris=(69,)),
    2507: Hotfix(2507, "I. Castle/Stairwell (ladders + stairs)", "load_time",
                 "0.5s AFTER load the engine deactivates four stairwell triangles AND drops every non-player NPC's "
                 "walkmesh collision (DelayedActiveTri). ENGINE-REMAPPED: the s29 fork-donor patch wraps this gate "
                 "with EffectiveFieldId, so it fires for the fork id too -- with the original 0.5s delay AND the "
                 "NPC-collision drop. The kit must NOT also prepend an at-load toggle: tris 174/175/177/178 are the "
                 "FLOOR the two treasure-chest props snap onto, and the real field's 0.5s delay lets them settle "
                 "FIRST, then removes the tris. An at-load prepend removes them BEFORE the chests place, snapping "
                 "the chests a floor down (★ caught in-game 2026-06-23). So reproduce via the engine remap only.",
                 "FieldMap.cs:139-148", toggles=((174, 0), (175, 0), (177, 0), (178, 0)),
                 tris=(174, 175, 177, 178), engine_remapped=True),

    # --- EVENT-CODE one-shot (locatable trigger; reproducible-but-bespoke; NOT auto-applied) ----------------
    450: Hotfix(450, "Dali/Field (Grandma's initial position)", "event_code",
                "When Grandma (sid 3) is created at (363, 88) the engine deactivates one triangle. Reproducible "
                "by splicing EnablePathTriangle(24,0) after that CreateObject in the fork's .eb (bespoke; not "
                "auto-applied -- a synth fork's spawn/positions may differ).",
                "DoEventCode.cs:291-292", tris=(24,)),

    # --- OPCODE-AUGMENT (the BGIACTIVE 0x9A handler itself has mapNo special-cases) ------------------------
    1753: Hotfix(1753, "(EnablePathTriangle augment)", "opcode_augment",
                 "When the field's own .eb runs EnablePathTriangle(207, x), the engine ALSO toggles triangle "
                 "208 to the same state. A fork keeps the donor's EnablePathTriangle(207,x) but loses the paired "
                 "208 toggle. Reproducible by emitting a paired EnablePathTriangle(208, x) beside it.",
                 "DoEventCode.cs:2566-2567", tris=(207, 208)),
    1606: Hotfix(1606, "(EnablePathTriangle augment)", "opcode_augment",
                 "When the field's own .eb runs EnablePathTriangle(107, x), the engine FORCES x = 1 (always "
                 "activate). A fork's EnablePathTriangle(107, 0) would deactivate instead. Reproducible by "
                 "rewriting that toggle's state operand to 1 in the fork's .eb.",
                 "DoEventCode.cs:2568-2569", tris=(107,)),

    # --- DYNAMIC (toggle tracks runtime story/position state; NOT statically reproducible) -----------------
    2803: Hotfix(2803, "Daguerreo/2nd Floor (LibrarianB book quest)", "dynamic",
                 "The librarian's walkable triangles 105/106 are activated when RunScript(uid 20, tag 18) fires "
                 "AND are continuously re-evaluated against gEventGlobal var 761060 (turnOffTriManually). A "
                 "static prepend can't track the story var. The interaction also depends on Main_Init shared "
                 "helpers (the #14-infeasible quest logic) -- fork in-place on 2803, or accept the book-quest "
                 "geometry is at scenario-zero.",
                 "DoEventCode.cs:158-162 + turnOffTriManually.cs:39-44", tris=(105, 106)),
    900: Hotfix(900, "Treno/Pub (Steiner_11)", "dynamic",
                "Triangle 62 is activated when RunScriptAsync(uid 14, level 2, tag 11) fires, and 56/62 are "
                "deactivated by turnOffTriManually on later beats. Tracks runtime script/manual-var state -> "
                "not a static toggle; fork in-place for faithful pub geometry.",
                "DoEventCode.cs:149-150 + turnOffTriManually.cs:14-31", tris=(56, 62)),
    1421: Hotfix(1421, "Fossil Roo/Mining Site (Lindblum_Worker)", "dynamic",
                 "Triangles 109/110 toggle on/off as the worker (sid 5) moves between positions (a moving "
                 "block). Position-driven during play -> not a static toggle.",
                 "DoEventCode.cs:296-309", tris=(109, 110)),
    1900: Hotfix(1900, "(turnOffTriManually, sid 4)", "dynamic",
                 "Triangle 56 is deactivated by turnOffTriManually when an object with sid 4 triggers it. "
                 "Object-driven -> not a static load-time toggle.",
                 "turnOffTriManually.cs:8-12", tris=(56,)),
    1455: Hotfix(1455, "(turnOffTriManually, sid 5)", "dynamic",
                 "Triangle 16 is deactivated by turnOffTriManually when an object with sid 5 triggers it. "
                 "Object-driven -> not a static load-time toggle.",
                 "turnOffTriManually.cs:32-36", tris=(16,)),
}


def info(field_id) -> "Hotfix | None":
    """The :class:`Hotfix` record for a real field id, or ``None`` if the field has no engine walkmesh hotfix
    (the vast majority). ``field_id`` may be an int or a numeric string."""
    try:
        return _HOTFIXES.get(int(field_id))
    except (TypeError, ValueError):
        return None


def load_time_toggles(field_id) -> list:
    """The ``[(tri, state), ...]`` a fork of ``field_id`` should prepend at load to reproduce its (auto)
    engine walkmesh hotfix, or ``[]`` when the field has none / its hotfix isn't statically reproducible."""
    h = info(field_id)
    return [list(t) for t in h.toggles] if (h and h.auto) else []


def all_ids() -> list:
    """Every real field id with a cataloged engine walkmesh hotfix (sorted)."""
    return sorted(_HOTFIXES)
