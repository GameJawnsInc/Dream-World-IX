"""Engine WALKMESH HOTFIXES keyed on a real field id -- which ones a fork keeps, and how -- the catalog.

A handful of real fields rely on a **hardcoded Memoria engine hotfix, keyed on the real ``fldMapNo``**, that
sets walkmesh-triangle active-state (``WalkMesh.BGI_triSetActive(triNdx, isActive)``, which SETS or CLEARS bit 0
of the triangle's ``triFlags`` -- the walkable bit -- both in the loaded ``BGI_DEF`` and the runtime mesh; an
absolute write, so the same ``(tri, state)`` applied twice is a no-op). A verbatim/native fork ships the same
``.bgi`` but runs at a CUSTOM id (>= 4000). Whether the hotfix still fires there depends on its gate:

* **REMAPPED** (``engine_remapped``): the custom engine's fork-gate suite routes the gate through
  ``EffectiveFieldId`` (s29: FieldMap 2507; s30: every ``effMapNo`` branch of DoEventCode -- 450, 1421, 1753,
  1606, and the RunScript arms of 900/2803; s65: FieldMap 2161), so it fires for a fork WHOSE DONOR IS RECORDED
  -- ``[verbatim_eb] donor`` / ``[field] source_field``, which the build/deploy turns into a ``ForkDonorPatch.txt``
  row, the only thing ``EffectiveFieldId`` reads. Forks require this engine (CLAUDE.md §5).
* **RAW** (FieldMap 2356; all of ``turnOffTriManually.cs`` -- 1900, 1455, and the other halves of 900/2803):
  ``fldMapNo == <real id>`` is false at a custom id, so the hotfix never fires -- the forked walkmesh is subtly
  wrong at that beat (a wall stays walkable, an NPC can't reach its spot, a blocked stair is open). This is the
  "real-``fldMapNo``-gated engine behavior is lost on a mint" residual from ``docs/FORK_FIDELITY.md``.

And two tractability classes for the KIT's own reproduction, where the engine's is missing:

* **LOAD-TIME, unconditional** (``FieldMap.HonoAwake`` / ``DelayedActiveTri``, keyed on ``fldMapNo`` only): the
  triangle state is asserted at field load with no runtime condition. A fork reproduces it EXACTLY by
  prepending ``EnablePathTriangle(tri, state)`` -- the same opcode (0x9A) whose handler IS ``BGI_triSetActive``
  -- to ``Main_Init`` (``content.walkmesh_hotfix.apply_tri_toggles``), unless it is ``delayed``. The ``.bgi``
  stays byte-verbatim. ``import`` auto-emits ``[field] walkmesh_tri_toggles`` exactly when the engine will not
  reproduce it for that fork (:meth:`Hotfix.needs_prepend`): a raw gate, or a fork with no donor row.
* **EVENT-CODE / DYNAMIC / OPCODE-AUGMENT** (``DoEventCode`` + ``turnOffTriManually``, keyed on ``mapNo`` plus a
  runtime condition -- an object uid/sid/tag, a position, or a story var): the toggle fires DURING play, so a
  static prepend can't reproduce it faithfully (e.g. Daguerreo's librarian tris TRACK ``gEventGlobal`` var
  761060). A remapped one fires when the fork reaches the same trigger (a ``--verbatim`` fork does by
  construction); a raw one is surfaced by ``fork-report`` as "fork in-place on the real id (or accept it)".
  Neither is auto-applied -- a per-field bespoke splice is a possible follow-up, recorded in each note.

Source (Memoria, ``Assembly-CSharp``, compile-matched to ``6b8bb2d5``; the wraps in ``memoria-patches/``):
``Global/Field/Map/FieldMap.cs`` (load-time), ``Global/Event/Engine/EventEngine.DoEventCode.cs`` (event-code +
the BGIACTIVE 0x9A handler's own ``mapNo`` augments), ``Global/Event/Engine/EventEngine.turnOffTriManually.cs``
(dynamic). Read-only reference data -- ships no Square-Enix bytes.
"""
from __future__ import annotations

from dataclasses import dataclass, field as _dc_field


@dataclass(frozen=True)
class Hotfix:
    """One real field's engine walkmesh hotfix.

    ``kind``    : ``load_time`` (prependable unless ``delayed``) | ``event_code`` | ``dynamic`` | ``opcode_augment`` |
                  ``collision`` (a per-TRIANGLE collision rule in ``FieldMapActorController`` -- it reads the tri the
                  actor stands on, it toggles nothing).
    ``toggles`` : the load-time ``(tri, state)`` pairs (state 1 = active/walkable, 0 = inactive) -- non-empty only
                  for ``load_time``.
    ``tris``    : every triangle index the hotfix touches (for reporting, incl. the non-load-time kinds).
    ``note``    : what it does + the runtime condition + (for non-auto) the reproduction recipe.
    ``source``  : the Memoria source location (stock ``6b8bb2d5`` line numbers).
    ``engine_remapped`` : EVERY gate of this hotfix reads ``EffectiveFieldId`` in the shipped custom engine
                  (s29/s30/s65), so the engine applies it -- under the real field's own condition and timing -- on a
                  fork whose donor is recorded (a ForkDonorPatch row). A hotfix with one gate remapped and another
                  raw (900, 2803: the DoEventCode arm vs ``turnOffTriManually``) is NOT engine_remapped; its
                  ``fork_tris`` name what survives.
    ``delayed`` : the engine applies it AFTER load (2507's ``DelayedActiveTri``, 0.5s), so a Main_Init prepend
                  cannot reproduce it: it fires BEFORE the field's own props settle onto those tris and snaps them a
                  floor down (the Ipsen chests, ★ caught in-game 2026-06-23). Only the engine remap reproduces it.
    ``fork_tris`` : the subset of ``tris`` the SHIPPED custom engine still toggles on a FORK of this donor -- its
                  gate reads ``EffectiveFieldId`` (every ``effMapNo`` branch in DoEventCode.cs, the s30 fork walk;
                  FieldMap.cs 2507 + 2161, s29/s65), so it fires at the fork's id against the FORK's walkmesh. A
                  gate still on the raw ``fldMapNo`` (FieldMap.cs 2356; all of turnOffTriManually.cs) never fires on
                  a fork, so its tris are absent here. The fork walkmesh-literal lint
                  (``build._lint_fork_walkmesh_ids``) checks these ids survive a rebuilt walkmesh.
    ``trigger_tris`` : for an ``opcode_augment`` -- the tri(s) whose ``EnablePathTriangle`` in the FIELD'S OWN
                  script makes the engine act. The lint reports only what the engine ADDS (``fork_tris`` minus these;
                  the script's own toggle is in the .eb scan), and only when carried donor code toggles a trigger.
    ``detaches_actors`` : the same engine pass also detaches every actor whose ``isPlayer`` is false from the
                  walkmesh (2507: ``BGI_charSetActive(fac, 0)``) -- by design for the donor's props, and harmless to
                  a player already bound by ``DefinePlayerCharacter``. A KIT-BUILT player used to be caught too:
                  the template Init's zero-filled sound ops were 48 one-tick yields between ``SetModel`` and
                  ``DefinePlayerCharacter``, so it was not yet the player at 0.5 s and walked off the mesh
                  (★ harness-proven, studies/fork-walkmesh-hotfix). ``content.npc.neutralize_player_audio_cruft``
                  now skips those ops with a JMP, so the kit player binds on its first tick like the real one.
    """

    field_id: int
    name: str
    kind: str
    note: str
    source: str
    toggles: tuple = ()
    tris: tuple = ()
    engine_remapped: bool = False
    fork_tris: tuple = ()
    delayed: bool = False
    trigger_tris: tuple = ()
    detaches_actors: bool = False

    @property
    def prependable(self) -> bool:
        """True when a Main_Init ``EnablePathTriangle`` prepend reproduces this hotfix FAITHFULLY: unconditional
        and applied AT LOAD (``load_time`` with ``toggles``, not ``delayed``)."""
        return self.kind == "load_time" and bool(self.toggles) and not self.delayed

    def needs_prepend(self, *, donor_recorded: bool = True) -> bool:
        """True when the KIT must reproduce this hotfix with a Main_Init toggle prepend because the engine will not:
        it is ``prependable`` AND either its gate is still on the raw ``fldMapNo`` or the fork records no donor
        (``donor_recorded=False`` -- no ForkDonorPatch row, so ``EffectiveFieldId`` returns the fork's own id; a
        fork whose donor id did not resolve at import is one). Never on a donor-recorded fork of an
        ``engine_remapped`` hotfix: the engine sets those tris in ``FieldMap.HonoAwake``, before Main_Init runs,
        so the prepend would only write the same bits again -- redundant, not harmful."""
        return self.prependable and not (self.engine_remapped and donor_recorded)

    @property
    def auto(self) -> bool:
        """:meth:`needs_prepend` for the usual fork, one that records its donor (``import --native``/``--verbatim``/
        ``--editable``, every campaign member): True only while the engine gate is RAW (2356)."""
        return self.needs_prepend()


_HOTFIXES = {
    # --- LOAD-TIME (unconditional at field load; the kit prepends it wherever the engine won't) -------------
    2356: Hotfix(2356, "Gulug/Room (the Red-Dragon-wall room)", "load_time",
                 "At field load the engine deactivates 3 floor triangles around a 3D treasure-chest prop (entry "
                 "5, GEO_ACC_F0_TBX @ (-426,1664)). The engine comment '(Red Dragon bursting through wall)' names "
                 "the ROOM (field 2356), not these tris' job. RAW gate -- no fork-gate patch wraps it -- so the "
                 "kit's toggle prepend is every fork's only copy. ★ IN-GAME PROVEN by A/B (2026-06-14): teleporting "
                 "to the patch EDGE (-543,1667) -- ~120u from the chest, beyond its collision -- is STUCK with the "
                 "toggle (id 30003) and FREE without it (id 30004), so the toggle (not the chest) blocks that "
                 "floor. The patch extends ~120u around the chest, so it blocks more than the chest's collision "
                 "alone -- the hotfix is NOT redundant. (Confound to avoid: the tri-78 CENTER (39u) coincides "
                 "with the chest collision; test the edge.)",
                 "FieldMap.cs:112-117", toggles=((78, 0), (79, 0), (80, 0)), tris=(78, 79, 80),
                 fork_tris=()),                  # raw fldMapNo gate -- the kit toggle prepend is the fork's copy
    2161: Hotfix(2161, "L. Castle/Guest Room (disc 3)", "load_time",
                 "At field load the engine deactivates one triangle (a disc-3 room-layout block). Unconditional. "
                 "ENGINE-REMAPPED since s65 (the member-donor gate sweep wraps this FieldMap gate with "
                 "EffectiveFieldId), so a fork with a donor row gets it from the engine at load; the kit prepends "
                 "it only for a fork that records no donor (one whose donor id did not resolve). The donor's own .eb "
                 "never toggles tri 69, so the engine + prepend double write that forks carried before this was "
                 "redundant, not harmful.",
                 "FieldMap.cs:119-122", toggles=((69, 0),), tris=(69,), engine_remapped=True, fork_tris=(69,)),
    2507: Hotfix(2507, "I. Castle/Stairwell (ladders + stairs)", "load_time",
                 "0.5s AFTER load the engine deactivates four stairwell triangles AND drops every non-player NPC's "
                 "walkmesh collision (DelayedActiveTri). ENGINE-REMAPPED: the s29 fork-donor patch wraps this gate "
                 "with EffectiveFieldId, so it fires for the fork id too -- with the original 0.5s delay AND the "
                 "NPC-collision drop. The kit must NOT also prepend an at-load toggle: tris 174/175/177/178 are the "
                 "FLOOR the two treasure-chest props snap onto, and the real field's 0.5s delay lets them settle "
                 "FIRST, then removes the tris. An at-load prepend removes them BEFORE the chests place, snapping "
                 "the chests a floor down (★ caught in-game 2026-06-23). So reproduce via the engine remap only -- "
                 "a fork with no donor row (its donor id did not resolve at import) loses it. The same pass "
                 "detached the player of a KIT-BUILT fork (★ harness-proven: 360u off the walkway) while the "
                 "template player's zero-filled Init still yielded 48 ticks before DefinePlayerCharacter; the "
                 "player now binds on its first tick, as the real one does, so the pass skips it.",
                 "FieldMap.cs:139-148", toggles=((174, 0), (175, 0), (177, 0), (178, 0)),
                 tris=(174, 175, 177, 178), engine_remapped=True,
                 fork_tris=(174, 175, 177, 178), delayed=True, detaches_actors=True),

    # --- EVENT-CODE one-shot (locatable trigger; the s30 remap fires it on a fork that reaches it) ----------
    450: Hotfix(450, "Dali/Field (Grandma's initial position)", "event_code",
                "When Grandma (sid 3) is created at (363, 88) the engine deactivates one triangle. ENGINE-REMAPPED "
                "(s30 routes this DoEventCode gate through effMapNo), so a fork that creates her there -- a "
                "--verbatim fork does by construction -- keeps it. A synth fork's spawn/sids may differ; there the "
                "recipe is splicing EnablePathTriangle(24,0) after that CreateObject (bespoke; not auto-applied).",
                "DoEventCode.cs:291-292", tris=(24,), engine_remapped=True, fork_tris=(24,)),

    # --- OPCODE-AUGMENT (the BGIACTIVE 0x9A handler itself has mapNo special-cases) ------------------------
    1753: Hotfix(1753, "(EnablePathTriangle augment)", "opcode_augment",
                 "When the field's own .eb runs EnablePathTriangle(207, x), the engine ALSO toggles triangle "
                 "208 to the same state. ENGINE-REMAPPED (s30: the 0x9A handler tests effMapNo), so a fork that "
                 "runs the donor's EnablePathTriangle(207, x) -- it sits in entry 0's Main_Init/Main_Reinit, which "
                 "a --verbatim fork keeps -- gets the paired 208 toggle too.",
                 "DoEventCode.cs:2566-2567", tris=(207, 208), engine_remapped=True, fork_tris=(207, 208),
                 trigger_tris=(207,)),
    1606: Hotfix(1606, "(EnablePathTriangle augment)", "opcode_augment",
                 "When the field's own .eb runs EnablePathTriangle(107, x), the engine FORCES x = 1 (always "
                 "activate). ENGINE-REMAPPED (s30: the 0x9A handler tests effMapNo), so a fork running the donor's "
                 "EnablePathTriangle(107, 0) has it forced to 1 exactly as the real field does.",
                 "DoEventCode.cs:2568-2569", tris=(107,), engine_remapped=True, fork_tris=(107,),
                 trigger_tris=(107,)),

    # --- COLLISION (FieldMapActorController's per-triangle rejection rules; tris READ, never toggled) ---------
    406: Hotfix(406, "Dali/Underground (the room under the well)", "collision",
                "The actor collision rejection factor drops to 0.4 while the actor stands on triangles 103/111/113 "
                "(a softer push-back against the forces there). ENGINE-REMAPPED (s65 wraps the gate with "
                "EffectiveFieldId), so it applies on a donor-recorded fork -- against the FORK's walkmesh, so a "
                "rebuilt mesh that moved those ids softens other triangles.",
                "FieldMapActorController.cs:1243 (s65)", tris=(103, 111, 113), engine_remapped=True,
                fork_tris=(103, 111, 113)),
    1752: Hotfix(1752, "Iifa Tree/Inner Roots (2nd area)", "collision",
                 "The actor collision rejection factor drops to 0.4 (0.6 on tri 80) on triangles 77-80. RAW gate "
                 "(fldMapNo) -- lost on a mint: fork in-place, or accept the stiffer push-back there.",
                 "FieldMapActorController.cs:1238", tris=(77, 78, 79, 80), fork_tris=()),

    # --- DYNAMIC (toggle tracks runtime story/position state; NOT statically reproducible) -----------------
    2803: Hotfix(2803, "Daguerreo/2nd Floor (LibrarianB book quest)", "dynamic",
                 "The librarian's walkable triangles 105/106 are activated when RunScript(uid 20, tag 18) fires "
                 "(remapped by s30 -- fires on a fork that runs it) AND are continuously re-evaluated against "
                 "gEventGlobal var 761060 by turnOffTriManually (RAW -- lost on a mint). A static prepend can't "
                 "track the story var. The interaction also depends on Main_Init shared helpers (the "
                 "#14-infeasible quest logic) -- fork in-place on 2803, or accept the book-quest geometry is at "
                 "scenario-zero.",
                 "DoEventCode.cs:158-162 + turnOffTriManually.cs:39-44", tris=(105, 106),
                 fork_tris=(105, 106)),          # the REQSW arm (effMapNo); turnOffTriManually stays raw
    900: Hotfix(900, "Treno/Pub (Steiner_11)", "dynamic",
                "Triangle 62 is activated when RunScriptAsync(uid 14, level 2, tag 11) fires (remapped by s30 -- "
                "fires on a fork that runs it), and 56/62 are deactivated by turnOffTriManually on later beats (RAW "
                "-- lost on a mint). Tracks runtime script/manual-var state -> not a static toggle; fork in-place "
                "for faithful pub geometry.",
                "DoEventCode.cs:149-150 + turnOffTriManually.cs:14-31", tris=(56, 62),
                fork_tris=(62,)),                # the REQ arm (effMapNo); 56 is turnOffTriManually-only (raw)
    1421: Hotfix(1421, "Fossil Roo/Mining Site (Lindblum_Worker)", "dynamic",
                 "Triangles 109/110 toggle on/off as the worker (sid 5) moves between positions (a moving "
                 "block). Position-driven during play -> not a static toggle. ENGINE-REMAPPED (s30 routes this "
                 "DoEventCode gate through effMapNo), so a fork whose worker walks the donor's route -- a "
                 "--verbatim fork does -- keeps the moving block.",
                 "DoEventCode.cs:296-309", tris=(109, 110), engine_remapped=True, fork_tris=(109, 110)),
    1900: Hotfix(1900, "(turnOffTriManually, sid 4)", "dynamic",
                 "Triangle 56 is deactivated by turnOffTriManually when an object with sid 4 triggers it. "
                 "Object-driven -> not a static load-time toggle. RAW gate (turnOffTriManually is unwrapped) -- "
                 "lost on a mint.",
                 "turnOffTriManually.cs:8-12", tris=(56,), fork_tris=()),
    1455: Hotfix(1455, "(turnOffTriManually, sid 5)", "dynamic",
                 "Triangle 16 is deactivated by turnOffTriManually when an object with sid 5 triggers it. "
                 "Object-driven -> not a static load-time toggle. RAW gate (turnOffTriManually is unwrapped) -- "
                 "lost on a mint.",
                 "turnOffTriManually.cs:32-36", tris=(16,), fork_tris=()),
}


def info(field_id) -> "Hotfix | None":
    """The :class:`Hotfix` record for a real field id, or ``None`` if the field has no engine walkmesh hotfix
    (the vast majority). ``field_id`` may be an int or a numeric string."""
    try:
        return _HOTFIXES.get(int(field_id))
    except (TypeError, ValueError):
        return None


def detaching_ids() -> tuple:
    """The real field ids whose engine hotfix detaches actors from the walkmesh (:attr:`Hotfix.detaches_actors`)."""
    return tuple(fid for fid, h in _HOTFIXES.items() if h.detaches_actors)


def load_time_toggles(field_id, *, donor_recorded: bool = True) -> list:
    """The ``[(tri, state), ...]`` a fork of ``field_id`` should prepend at load to reproduce its engine walkmesh
    hotfix -- :meth:`Hotfix.needs_prepend` -- or ``[]`` when the field has none, the engine reproduces it for this
    fork, or it isn't statically reproducible. ``donor_recorded``: the fork's toml records its donor, so it gets a
    ForkDonorPatch row (False only when the import could not resolve the donor id)."""
    h = info(field_id)
    return [list(t) for t in h.toggles] if (h and h.needs_prepend(donor_recorded=donor_recorded)) else []
