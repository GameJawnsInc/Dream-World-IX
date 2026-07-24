"""``summons/seqlint.py`` -- the SILENT-SKIP GUARD for hand-authored SFX ``.seq`` text sequences (rung-8
kit item K5; contract ``studies/custom-summons/rung8-epic/STORYBOARD.md`` section 6.4).

WHY THIS EXISTS. The engine's sequence parser drops an unrecognized operation **without a log**::

    String[] defaultArgList;
    if (!BattleActionCode.operationArguments.TryGetValue(opCode, out defaultArgList))
        continue;                                  // BattleActionThread.cs:155-156

and an unrecognized ARGUMENT key is merely stored in a dictionary the executor never reads
(``BattleActionThread.cs:179-180``). So a typo in a hand-authored cast does not crash, does not warn, and
does not appear in ``Memoria.log`` -- it silently does nothing, and the only symptom is a beat that
"didn't happen" three playtests later. This module is the offline net.

TWO TABLES, AND THE SECOND ONE IS NOT THE ENGINE'S.

  * :data:`ENGINE_OPS` -- the 41 keys of ``BattleActionCode.operationArguments``
    (``BattleActionCode.cs:46-89``) **plus** ``EndThread``. ``EndThread`` is legal-but-absent from the
    table: the parser pops the thread stack at ``:150-154`` and only then falls through the same
    ``continue``, so the op does its job and is then discarded. An op outside this set is DEAD.
  * :data:`OUR_OPS` -- the per-op argument keys **derived from the EXECUTOR**
    (``UnifiedBattleSequencer.cs``), for the ~20 ops the kit's summon lane actually emits.
    ``operationArguments`` is a *positional-argument-name* table and is demonstrably out of sync with the
    executor in at least four places, so it is the wrong oracle for an argument check:

    ==========================  ==========================================================================
    ``CreateVisualEffect``      declares ``Time``/``Size``/``Speed``, but the ``SFXModel`` branch ignores
                                all three and reads a ``SFXModel`` key the table does not list
                                (``UnifiedBattleSequencer.cs:397``) -- the rung-5 law.
    ``PlayAnimation``           the executor reads ``Hold`` (``:497``); the table does not list it.
    ``PlayCamera``              the table declares ``IsAlternate``; the executor reads ``Alternate``
                                (``:830``).
    ``Message``/``LoadSFX``/... every op additionally honours ``Reflect`` -- a UNIVERSAL gate consulted at
                                ``UnifiedBattleSequencer.cs:188-191``, listed for no op at all.
    ==========================  ==========================================================================

    An op that is in :data:`ENGINE_OPS` but not in :data:`OUR_OPS` is accepted with a WARNING (it will
    run; we simply have no verified arg table for it and refuse to guess one).

WHAT ELSE IT CHECKS (the mechanically-expressible laws of the study's proven grammar):

  * **REFUSED OPS** -- ``PlayCamera`` and ``ShiftWorld`` are rejected outright, with citations
    (STORYBOARD section 2). ``PlayCamera`` ``break``s at ``Configuration.Battle.Speed >= 3`` in
    ``PHASE_NORMAL`` (``UnifiedBattleSequencer.cs:828-829``); ``ShiftWorld`` slides only
    ``battlebg.btlRoot`` -- the actors are not parented to it -- and has no automatic restore.
  * **THE PHASE-LOCK RULE** -- no clip-bound wait (``WaitAnimation``/``WaitMove``/``WaitTurn``/
    ``WaitSize``) after the first ``PlaySFX``: its length is unmeasured, and any slack it introduces
    slides the ``.seq`` clock against the ``.sfxmodel`` manifest clock.
  * **THE FIGURE-VISIBILITY LAW** -- an ``EffectPoint`` must land in a LIT window. The linter runs the
    fixed-``Wait`` tick clock, tracks every ``SetBackgroundIntensity`` ramp, and refuses an
    ``EffectPoint`` scheduled while the background is dark or still ramping back up (rung 4/6: the damage
    figures are UI, occluded by the fullscreen blackout; particle draws are exempt, different path).
  * **THE INTENSITY LAW** -- only ``Intensity=0`` and ``Intensity=1`` are legible destinations; a mid
    value only nudges a float nobody sees at the default camera, and STORYBOARD section 2.1 killed the
    ``PlayCamera`` pairing that used to rescue it. Mid values WARN.
  * **THE ANIM=IDLE RELEASE LAW** -- the cast must close on ``PlayAnimation: Char=Caster ; Anim=Idle``
    (the literal string ``Idle`` takes the ``releaseCmdIdle`` branch, ``UnifiedBattleSequencer.cs:505``).
  * **thread balance** -- ``StartThread``/``ElseThread`` vs ``EndThread``.
  * **cross-file** -- every ``SFXModel=`` path resolves to a staged particle file, and every
    ``SFX=``/``LoadSFX``/``PlaySFX``/``Wait*SFX*`` id equals the private effect id.

:func:`lint_sfxmodel_text` covers the same silent-failure family on the JSON side (a mixed
int/float ``ParameterMin``/``ParameterMax`` pair is dropped without a word by
``SFXDataMesh.cs:1389-1403``; a bad interpolation name silently becomes ``Constant``) plus two failures
that are LOUD but land far from their cause:

  * **THE TURNING SPLIT** (:data:`FBX_INTERPOLATIONS`) -- ``Turning1``/``Turning2`` are the only two
    interpolation arms that read ``customParam``, and they read it unguarded
    (``ParametricMovement.cs:233-237``). The FBX render path passes ``null``
    (``SFXDataMesh.cs:843-845``), so Turning on a creature curve is a NullReferenceException on every
    render frame; on a SPRITE ``Movement`` it is fine, but only when the emission carries a
    ``ParameterMin``/``ParameterMax`` pair (else ``p.param`` is null too, ``SFXDataMesh.cs:1379-1388``).
  * **THE OMITTED-CURVE SPLIT** (:data:`_FBX_SEED_TRAPS`) -- a missing ``Movement`` pins the model at
    the world origin and a missing ``Rotation`` pins it at euler ``(0,0,0)``, because an absent node is
    never ``LoadFromJSON``'d (``SFXDataMesh.cs:1007-1012``) and ``GetPosition`` then returns its
    ``Vector3.zero`` constructor seed forever. A missing ``Scaling`` is benign -- that one channel is
    built ``asScaling`` and seeds ``Vector3.one``.

PROVENANCE: pure code + engine-derived NAME tables. Zero game bytes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import NamedTuple

__all__ = [
    "SeqLintError", "ENGINE_OPS", "OUR_OPS", "REFUSED_OPS", "UNIVERSAL_ARGS", "INTERPOLATIONS",
    "FBX_INTERPOLATIONS", "TURNING_INTERPOLATIONS",
    "SeqLine", "SeqProblem", "SeqReport", "parse_seq", "analyze_seq", "lint_seq",
    "lint_sfxmodel_text", "lint_sfxmodel_file",
]


class SeqLintError(ValueError):
    """A ``.seq`` that could not even be read/parsed (not a lint finding -- those are returned)."""


# --------------------------------------------------------------------------- the engine op universe

#: The 41 keys of ``BattleActionCode.operationArguments`` (``BattleActionCode.cs:46-89``) + ``EndThread``.
#: An op OUTSIDE this set is dropped by ``BattleActionThread.cs:155-156`` with no log at all.
ENGINE_OPS = frozenset({
    "Wait", "WaitAnimation", "WaitMove", "WaitTurn", "WaitSize",
    "WaitMonsterSFXLoaded", "WaitMonsterSFXDone", "WaitSFXLoaded", "WaitSFXDone", "WaitReflect",
    "Channel", "StopChannel", "LoadMonsterSFX", "PlayMonsterSFX", "LoadSFX", "PlaySFX",
    "CreateVisualEffect", "Turn", "PlayAnimation", "PlayTextureAnimation", "ToggleStandAnimation",
    "MoveToTarget", "MoveToPosition", "ChangeSize", "ShowMesh", "ShowShadow",
    "ChangeCharacterProperty", "PlayCamera", "ResetCamera", "PlaySound", "StopSound",
    "EffectPoint", "Message", "SetBackgroundIntensity", "ShiftWorld", "SetVariable",
    "SetupReflect", "ActivateReflect", "StartThread", "ElseThread", "MOVE_WATER",
    # legal-but-absent from operationArguments: the parser pops the thread stack first (:150-154)
    "EndThread",
})

#: Read on EVERY op, before the switch: ``UnifiedBattleSequencer.cs:188-191`` skips a non-``Reflect``
#: code when the running thread is the reflect thread. Listed for no op in ``operationArguments``.
UNIVERSAL_ARGS = frozenset({"Reflect"})

#: op -> the argument keys the EXECUTOR actually reads (``UnifiedBattleSequencer.cs``), for the ops the
#: kit's summon lane emits. Deliberately narrower than the engine's whole vocabulary: an op we do not
#: emit gets a "no verified arg table" warning rather than a guessed whitelist.
OUR_OPS: dict = {
    # -- waits (BattleActionThread.cs:98-126 + UnifiedBattleSequencer.cs:210-257)
    "Wait": frozenset({"Time"}),
    "WaitAnimation": frozenset({"Char"}),
    "WaitMove": frozenset({"Char"}),
    "WaitTurn": frozenset({"Char"}),
    "WaitSize": frozenset({"Char"}),
    "WaitSFXLoaded": frozenset({"SFX", "Instance"}),
    "WaitSFXDone": frozenset({"SFX", "Instance"}),
    "WaitReflect": frozenset(),
    # -- the cast aura (:259-292)
    "Channel": frozenset({"Type", "Char", "SkipFlute"}),
    "StopChannel": frozenset({"Char"}),
    # -- the effect instance (:293-379)
    "LoadSFX": frozenset({"SFX", "Char", "Target", "TargetPosition", "UseCamera",
                          "FirstBone", "SecondBone", "Args", "MagicCaster"}),
    "PlaySFX": frozenset({"SFX", "Instance", "JumpToFrame", "SkipSequence", "HideMeshes", "MeshColors"}),
    # -- particles (:381-448). NOTE `SFXModel` is read at :397 and is NOT in operationArguments;
    #    `Time`/`Size`/`Speed` ARE in the table but are inert on the SFXModel branch (rung-5 law).
    "CreateVisualEffect": frozenset({"SFXModel", "SPS", "SHP", "Char", "Bone", "Offset",
                                     "UseSHP", "UseSFXModel", "Size", "Time", "Speed"}),
    # -- actor (:450-548)
    "Turn": frozenset({"Char", "BaseAngle", "Angle", "Time", "UsePitch"}),
    "PlayAnimation": frozenset({"Char", "Anim", "Speed", "Loop", "Palindrome", "Hold", "Frame"}),
    # -- audio (:858-964)
    "PlaySound": frozenset({"Sound", "SoundType", "Volume", "Pitch", "Panning"}),
    "StopSound": frozenset({"Sound", "SoundType", "FadeOut"}),
    # -- damage + presentation (:966-1043)
    "EffectPoint": frozenset({"Char", "Type"}),
    "Message": frozenset({"Text", "Title", "Priority"}),
    "SetBackgroundIntensity": frozenset({"Intensity", "Time", "HoldDuration"}),
    # -- reflect + threading (:1059-1082, BattleActionThread.cs:183-193)
    "SetupReflect": frozenset({"Delay"}),
    "ActivateReflect": frozenset(),
    "StartThread": frozenset({"Condition", "LoopCount", "Target", "TargetLoop", "Chain", "Sync"}),
    "ElseThread": frozenset({"Condition", "LoopCount", "Target", "TargetLoop", "Chain", "Sync"}),
    "EndThread": frozenset(),
}

#: ops the kit REFUSES to emit, with the reason (STORYBOARD section 2 -- pinned from source, not taste).
REFUSED_OPS: dict = {
    "PlayCamera":
        "PlayCamera is a HARD NO-OP on a Speed>=3 install: UnifiedBattleSequencer.cs:828-829 breaks when "
        "Configuration.Battle.Speed >= 3 && btl_phase == PHASE_NORMAL, and SFXRework (which this whole "
        "lane needs) is forced on at Speed >= 3. Even when it does run, the bare form only writes "
        "seq_work_set.CameraNo -- which no managed code reads -- and the Char= form hands control to "
        "FF9SpecialEffectPlugin.dll for an effect id with no native payload to drive it. "
        "Compose for the fixed default battle camera instead (blackout + rise-from-below + Scaling).",
    "ShiftWorld":
        "ShiftWorld is refused: battlebg.ShiftWorld (battlebg.cs:407-432) moves only battlebg.btlRoot -- "
        "the battle ACTORS are not parented to it (the reparenting code is commented out at :411-424) -- "
        "so it slides the scenery out from under the characters. And there is no automatic restore: "
        "UnshiftWorld (:455-462) guards on fields ShiftWorld no longer writes and has zero callers, so a "
        "shift persists for the rest of the battle.",
}

#: the seven ``ParametricMovement.InterpolateType`` names (``ParametricMovement.cs:262-271``). An unknown
#: string silently becomes ``Constant`` (``TryParseInterpolateType:273-285``) -- hence the hard check.
INTERPOLATIONS = frozenset({"Constant", "Linear", "Sinus", "SinusIn", "SinusOut", "Turning1", "Turning2"})

#: THE TURNING SPLIT. ``Turning1``/``Turning2`` are the only two ``InterpolateType`` arms that read the
#: ``customParam`` dictionary, and they read it with NO null guard::
#:
#:     Single baseAngle;
#:     customParam.TryGetValue(0, out baseAngle);          // ParametricMovement.cs:233-237
#:
#: so whether they are legal depends entirely on WHO calls ``GetPosition``:
#:
#:   * an **FBX** curve is always called with ``customParam = null`` (``SFXDataMesh.cs:843-845``) ->
#:     NullReferenceException on every render frame. Turning is ILLEGAL there, full stop.
#:   * a **Sprite** ``Movement`` curve is called with ``p.param`` (``SFXDataMesh.cs:1285``), which is
#:     itself ``null`` unless the emission carried a ``ParameterMin``/``ParameterMax`` pair
#:     (``SFXDataMesh.cs:1379, 1386-1388``) -> Turning is legal only WITH such a pair.
#:   * ``ColorInterpolation``/``ScaleInterpolation``/UV go through
#:     ``GetInterpolatedDictionaryValue`` -> ``Factor1``/``Factor2``, which never touch ``customParam``
#:     -> Turning is unconditionally safe there.
FBX_INTERPOLATIONS = frozenset(INTERPOLATIONS - {"Turning1", "Turning2"})

#: the two ``customParam``-reading arms (see :data:`FBX_INTERPOLATIONS`).
TURNING_INTERPOLATIONS = frozenset({"Turning1", "Turning2"})

_FBX_TURNING_MSG = (
    "is SPRITE-ONLY and CRASHES on an FBX curve: ParametricMovement.cs:233-237 calls "
    "customParam.TryGetValue(0, out baseAngle) unguarded on the Turning1/Turning2 arms, and the FBX "
    "render path passes customParam = null (SFXDataMesh.cs:843-845) -- a NullReferenceException on "
    "every render frame of the cast")

#: THE OMITTED-CURVE SPLIT (the ``.sfxmodel`` half of ``deploy._REQUIRED_CURVES``). ``LoadFBX`` only calls
#: ``LoadFromJSON`` for a node that EXISTS (``SFXDataMesh.cs:1007-1012``), so a missing curve key leaves
#: that ``ParametricMovement`` with zero pieces and ``GetPosition`` returns the constructor seed forever
#: (``ParametricMovement.cs:209-212, 226-227``). The seed differs per channel, so only two of the three
#: are traps -- ``Scaling`` is built with ``new ParametricMovement(true)`` (``SFXDataMesh.cs:1252``) and
#: seeds ``Vector3.one``, a benign identity scale.
_FBX_SEED_TRAPS = {
    "Movement":
        "an omitted Movement curve is never loaded (SFXDataMesh.cs:1007-1012), so GetPosition returns "
        "its Vector3.zero seed (ParametricMovement.cs:31-35, 226-227) and the model is pinned at the "
        "WORLD ORIGIN, off-camera, for the whole cast -- THE MOVEMENT TRAP",
    "Rotation":
        "an omitted Rotation curve is never loaded (SFXDataMesh.cs:1007-1012), so eulerAngles is written "
        "as (0,0,0) every frame (SFXDataMesh.cs:844, raw, no battle-actor base), overriding the FBX's "
        "own export orientation -- not the proven (0,180,180) ROTATION BASELINE",
}

_SPRITE_TURNING_MSG = (
    "needs an emission Parameter: a sprite Movement curve is evaluated with p.param "
    "(SFXDataMesh.cs:1285), which stays NULL unless the Emission carries a ParameterMin/ParameterMax "
    "pair (SFXDataMesh.cs:1379, 1386-1388) -- without one, the unguarded "
    "customParam.TryGetValue(0, ...) at ParametricMovement.cs:236 throws on every particle, every frame")

#: ops whose wait length is bound to a CLIP, not a tick count -- banned after ``PlaySFX``.
_CLIP_BOUND_WAITS = ("WaitAnimation", "WaitMove", "WaitTurn", "WaitSize")

_SFX_ID_OPS = ("LoadSFX", "PlaySFX", "WaitSFXLoaded", "WaitSFXDone",
               "LoadMonsterSFX", "PlayMonsterSFX", "WaitMonsterSFXLoaded", "WaitMonsterSFXDone")


# --------------------------------------------------------------------------- parse

class SeqLine(NamedTuple):
    """One parsed operation line."""
    lineno: int                 # 1-based
    op: str
    args: dict                  # key -> value (str), in file order
    raw: str
    dup_keys: tuple             # arg keys written more than once (the parser keeps the LAST)


class SeqProblem(NamedTuple):
    severity: str               # "error" | "warn"
    lineno: int                 # 0 = whole-file
    message: str

    def __str__(self) -> str:
        where = f"line {self.lineno}: " if self.lineno else ""
        return f"{self.severity.upper()}: {where}{self.message}"


class SeqReport(NamedTuple):
    lines: list                 # [SeqLine, ...]
    problems: list              # [SeqProblem, ...]
    total_ticks: int            # sum of fixed `Wait: Time=` ONLY -- see below
    clip_bound_waits: int       # how many unmeasurable clip-bound waits the total therefore excludes

    # ``total_ticks`` is the FIXED-WAIT floor of the cast, not its wall-clock length: a clip-bound wait
    # (WaitAnimation/...) counts 0 because only the running clip knows its length, and an SFX-bound wait
    # (WaitSFXDone) counts 0 because only the .sfxmodel manifest's Start/End window knows its. Both are
    # deliberately un-guessed -- the number is what the EffectPoint/intensity scheduling is derived from,
    # and inventing a length for the unmeasurable parts would corrupt exactly that.

    @property
    def errors(self) -> list:
        return [p for p in self.problems if p.severity == "error"]

    @property
    def warnings(self) -> list:
        return [p for p in self.problems if p.severity == "warn"]

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_seq(text: str) -> list:
    """Parse a ``.seq`` exactly the way ``BattleActionThread.LoadFromTextSequence`` does
    (``BattleActionThread.cs:134-200``) -- split on ``\\n``, strip from ``//``, split the op off at the
    first ``:``, split arguments on ``;``, split each on the first ``=``, ``Trim()`` everything.

    Returns every line that yields a non-empty op token, INCLUDING ops the engine would drop -- the
    dropping is exactly what we are here to report. Positional (``=``-less) arguments are recorded under
    the key ``"#<index>"`` so the arg-key check can flag them (the engine maps them onto
    ``operationArguments`` by position, which our executor-derived table deliberately does not model)."""
    out = []
    for i, raw in enumerate(text.split("\n"), start=1):
        body = raw.split("//", 1)[0]
        head, sep, argcode = body.partition(":")
        op = head.strip()
        if not op:
            continue
        args, dups = {}, []
        if sep:
            for j, chunk in enumerate(argcode.split(";")):
                if not chunk.strip():
                    continue                      # StringSplitOptions.RemoveEmptyEntries
                key, eq, value = chunk.partition("=")
                if eq:
                    key, value = key.strip(), value.strip()
                else:
                    key, value = f"#{j}", chunk.strip()
                if not key:
                    continue
                if key in args:
                    dups.append(key)
                args[key] = value
        out.append(SeqLine(i, op, args, raw.rstrip("\r\n"), tuple(dups)))
    return out


# --------------------------------------------------------------------------- analyze

def _as_float(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _as_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


class _Bbg:
    """The background-intensity clock. ``SetBackgroundIntensity`` starts a ramp from the CURRENT value to
    ``Intensity`` over ``Time`` ticks (``UnifiedBattleSequencer.cs:1030-1042`` ->
    ``SequenceBBGIntensity``); ``Time=0`` applies instantly. Battle starts fully lit."""

    def __init__(self):
        self.value = 1.0
        self.ramp = None        # (start_tick, end_tick, from_value, to_value)

    def set(self, tick: int, target: float, time: int) -> None:
        self.value = self.at(tick)
        self.ramp = (tick, tick + max(0, int(time)), self.value, float(target))

    def at(self, tick: int) -> float:
        if self.ramp is None:
            return self.value
        t0, t1, v0, v1 = self.ramp
        if tick <= t0:
            return v0
        if tick >= t1:
            return v1
        return v0 + (v1 - v0) * (tick - t0) / float(t1 - t0)


def analyze_seq(text: str, *, private_ef: "int | None" = None, particles=None,
                path: "str | None" = None) -> SeqReport:
    """Lint a ``.seq``'s TEXT. ``private_ef`` cross-checks every ``SFX=`` id; ``particles`` is the list of
    staged particle ``.sfxmodel`` file names (or paths) every ``SFXModel=`` must resolve into. Both are
    optional -- omit them for a pure grammar pass. Never raises on content; returns a :class:`SeqReport`."""
    lines = parse_seq(text)
    problems: list = []

    def err(ln, msg):
        problems.append(SeqProblem("error", ln, msg))

    def warn(ln, msg):
        problems.append(SeqProblem("warn", ln, msg))

    if not lines:
        err(0, f"{path or '<seq>'} has no operation lines at all -- an empty sequence renders nothing")

    want_particles = {Path(str(p)).name for p in (particles or [])}

    # THE PHASE-LOCK WINDOW: the two clocks only run together between PlaySFX (manifest frame 0) and the
    # WaitSFXDone that drains the instance. A clip-bound wait BEFORE PlaySFX shifts every phase uniformly
    # and costs nothing; one AFTER the instance has drained has no manifest clock left to slide against
    # (that is the proven rung-6 release tail: ... WaitReflect / Anim=Idle / Turn / WaitTurn). Only the
    # span in between is load-bearing.
    _idx = {i: ln.op for i, ln in enumerate(lines)}
    first_play = next((i for i, op in _idx.items() if op == "PlaySFX"), None)
    last_done = next((i for i in reversed(list(_idx)) if _idx[i] in ("WaitSFXDone", "WaitMonsterSFXDone")),
                     None)
    lock_end = last_done if last_done is not None else len(lines)

    tick = 0
    clip_bound = 0
    bbg = _Bbg()
    depth = 0
    seen_playsfx = False
    last_caster_anim = None          # (lineno, anim_value)
    effect_points: list = []         # (lineno, tick, type)

    for index, ln in enumerate(lines):
        op, args = ln.op, ln.args

        # -- 1. the op itself ------------------------------------------------------------------
        if op in REFUSED_OPS:
            err(ln.lineno, f"`{op}` is refused by this kit. {REFUSED_OPS[op]}")
        elif op not in ENGINE_OPS:
            err(ln.lineno,
                f"unknown operation `{op}` -- BattleActionThread.cs:155-156 drops an op that is not a key "
                f"of BattleActionCode.operationArguments, WITHOUT a log. This line would do nothing.")
        elif op not in OUR_OPS:
            warn(ln.lineno,
                 f"`{op}` is a real engine op but the kit has no executor-derived argument table for it -- "
                 f"its arguments are NOT checked here. Verify them against UnifiedBattleSequencer.cs.")

        # -- 2. argument keys ------------------------------------------------------------------
        allowed = OUR_OPS.get(op)
        if allowed is not None:
            for key in args:
                if key.startswith("#"):
                    err(ln.lineno,
                        f"`{op}` argument {args[key]!r} has no `Key=` -- the engine would map it onto "
                        f"operationArguments BY POSITION, a table that is out of sync with the executor. "
                        f"Write it as `Key=Value`.")
                elif key not in allowed and key not in UNIVERSAL_ARGS:
                    err(ln.lineno,
                        f"`{op}` has no argument `{key}` -- the executor never reads that key, so it is "
                        f"stored and ignored SILENTLY. Valid: {sorted(allowed | UNIVERSAL_ARGS)}")
        for key in ln.dup_keys:
            warn(ln.lineno, f"`{op}` sets `{key}` more than once -- the parser keeps the LAST value")

        # -- 3. threading ----------------------------------------------------------------------
        if op in ("StartThread", "ElseThread"):
            depth += 1
        elif op == "EndThread":
            depth -= 1
            if depth < 0:
                err(ln.lineno, "`EndThread` with no open StartThread/ElseThread")
                depth = 0

        # -- 4. the tick clock + the laws ------------------------------------------------------
        if op == "Wait":
            if "Time" not in args:
                warn(ln.lineno, "`Wait` with no `Time=` waits 0 ticks (waitFrame stays 0)")
            else:
                n = _as_int(args["Time"])
                if n is None:
                    err(ln.lineno, f"`Wait: Time={args['Time']}` is not an integer tick count")
                else:
                    tick += n
        elif op in _CLIP_BOUND_WAITS:
            clip_bound += 1
            if seen_playsfx and index < lock_end:
                err(ln.lineno,
                    f"THE PHASE-LOCK RULE: `{op}` inside the PlaySFX..WaitSFXDone window. A clip-bound "
                    f"wait has a length nobody measured, and its slack slides the .seq clock against the "
                    f".sfxmodel manifest clock (which counts frames from PlaySFX). Use a fixed "
                    f"`Wait: Time=N` here.")
        elif op == "PlaySFX":
            seen_playsfx = True
        elif op == "SetBackgroundIntensity":
            v = _as_float(args.get("Intensity", "1"))
            t = _as_int(args.get("Time", "0")) or 0
            if v is None:
                err(ln.lineno, f"`SetBackgroundIntensity: Intensity={args.get('Intensity')}` is not a number")
            else:
                if 0.0 < v < 1.0:
                    warn(ln.lineno,
                         f"THE INTENSITY SUBTLETY LAW: Intensity={v} is a mid value. Only 0 (which takes "
                         f"battlebg.cs:479-481's renderer.enabled=false branch -- the vanilla blackout) and "
                         f"1 are legible destinations at the default camera; a mid value just nudges the BG "
                         f"materials' _Intensity float. The ramp `Time=` is the expressive knob.")
                bbg.set(tick, v, t)
        elif op == "EffectPoint":
            effect_points.append((ln.lineno, tick, args.get("Type", "Both")))
        elif op == "PlayAnimation":
            if args.get("Char", "Caster") == "Caster":
                last_caster_anim = (ln.lineno, args.get("Anim"))

        # -- 5. cross-file ---------------------------------------------------------------------
        if op == "CreateVisualEffect":
            model = args.get("SFXModel")
            if model is not None:
                if not model.startswith("Data/"):
                    err(ln.lineno,
                        f"`SFXModel={model}` must be a FULL Data/-rooted path "
                        f"(e.g. Data/SpecialEffects/ef091/MistWisps.sfxmodel) -- the rung-5 law")
                if want_particles and Path(model).name not in want_particles:
                    err(ln.lineno,
                        f"`SFXModel={model}` names a file that is not staged: known particles are "
                        f"{sorted(want_particles)}. ModelSequence.Load returns null and the op `break`s "
                        f"SILENTLY (UnifiedBattleSequencer.cs:406-408).")
            if "Char" not in args:
                err(ln.lineno,
                    "`CreateVisualEffect` without `Char=` renders on NOBODY: TryGetArgCharacter defaults "
                    "the bitmask to 0 (BattleActionCode.cs:493-496) and the per-unit loop never runs "
                    "-- silently. (rung-5 law)")
            for inert in ("Time", "Size", "Speed"):
                if inert in args and "SFXModel" in args:
                    warn(ln.lineno,
                         f"`{inert}=` is parsed but INERT on the SFXModel branch (all timing lives in the "
                         f"JSON) -- drop it so the line does not imply an effect it has not got")
        if op in _SFX_ID_OPS and private_ef is not None:
            got = args.get("SFX")
            if got is not None and _as_int(got) is not None and _as_int(got) != int(private_ef):
                err(ln.lineno,
                    f"`{op}: SFX={got}` does not target this block's private effect id {private_ef}. A "
                    f"cast must never LoadSFX a stock id from a private host folder.")

        if op == "LoadSFX" and "UseCamera" not in args:
            warn(ln.lineno,
                 "`LoadSFX` without `UseCamera=False`: the computed default is TRUE on this install "
                 "(Speed<3 || phase!=NORMAL || !FF9BMenu_IsEnable() -- the menu is disabled during a "
                 "command, so the third disjunct holds; UnifiedBattleSequencer.cs:343-344), which hands "
                 "the cast to the native camera plugin for an id with no native payload.")
        if op == "PlaySFX" and args.get("SkipSequence", "").lower() != "true":
            warn(ln.lineno,
                 "`PlaySFX` without `SkipSequence=True`: SFXData.LoadSFX reads ef###/Sequence.seq "
                 "unconditionally (SFXData.cs:174), and any file left there threads in as a second, "
                 "duplicate-damage parallel thread.")

    # -- whole-file laws --------------------------------------------------------------------------
    if depth > 0:
        err(0, f"{depth} unclosed StartThread/ElseThread block(s) -- add the matching EndThread")

    for lineno, at, kind in effect_points:
        lit = bbg.at(at)
        if lit < 1.0 and kind in ("Figure", "Both"):
            err(lineno,
                f"THE FIGURE-VISIBILITY LAW: `EffectPoint: Type={kind}` fires at tick {at}, when the "
                f"background intensity is {lit:.2f}. Damage-number popups are UI and are OCCLUDED under a "
                f"fullscreen intensity overlay -- schedule it after the relight ramp COMPLETES (particle "
                f"draws are exempt: a different render path).")
        elif lit < 1.0:
            warn(lineno,
                 f"`EffectPoint: Type={kind}` fires at tick {at} with background intensity {lit:.2f}. The "
                 f"figures it queues will be popped by a later Type=Figure/Both -- make sure THAT one is "
                 f"in a lit window.")

    if last_caster_anim is None:
        err(0, "THE ANIM=IDLE RELEASE LAW: no `PlayAnimation: Char=Caster` anywhere -- the caster never "
               "returns to idle and the command never releases cleanly.")
    elif last_caster_anim[1] != "Idle":
        err(last_caster_anim[0],
            f"THE ANIM=IDLE RELEASE LAW: the last caster animation is `Anim={last_caster_anim[1]}`, not "
            f"the literal `Idle`. Only the exact string \"Idle\" takes the releaseCmdIdle branch "
            f"(UnifiedBattleSequencer.cs:505) that ends the command motion and restores the default idle.")

    return SeqReport(lines, problems, tick, clip_bound)


def lint_seq(text: str, **kw) -> list:
    """The list-of-strings shim every other kit lint returns: BLOCKING problems only (empty = clean).
    Advisories live on :func:`analyze_seq`'s report (``.warnings``)."""
    return [str(p) for p in analyze_seq(text, **kw).errors]


def lint_seq_file(path, **kw) -> SeqReport:
    """:func:`analyze_seq` on a file (UTF-8, BOM-tolerant)."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8-sig")
    except OSError as e:
        raise SeqLintError(f"cannot read {p}: {e}") from e
    kw.setdefault("path", str(p))
    return analyze_seq(text, **kw)


# --------------------------------------------------------------------------- the .sfxmodel side

_VEC_RE = re.compile(r"^\(\s*[-+0-9.eE]+\s*(,\s*[-+0-9.eE]+\s*){1,3}\)$")


def lint_sfxmodel_text(text: str, *, path: "str | None" = None) -> list:
    """The JSON half of the silent-skip guard: a ``.sfxmodel`` manifest/particle file. Returns a list of
    problem strings (empty = clean). Checks only things the engine fails at SILENTLY:

      * the file parses at all (``JSONNode.Parse`` returning null makes ``ModelSequence.Load`` return null
        and ``CreateVisualEffect`` ``break`` with no message);
      * ``Indices`` is a multiple of 3 and every index is inside ``Vertices``;
      * every interpolation name is one of the seven (an unknown one becomes ``Constant``,
        ``ParametricMovement.cs:273-285``);
      * ``ColorInterpolation``/``ScaleInterpolation`` arrays are long enough for the keyframe SEGMENTS
        they have to cover (``GetInterpolatedDictionaryValue`` indexes them by segment,
        ``ParametricMovement.cs`` -- a short array silently falls back to entry 0);
      * ``ParameterMinK``/``ParameterMaxK`` are BOTH ints or BOTH floats. The engine sorts them into
        separate int/float dictionaries by ``Int32.TryParse`` and then drops any key whose partner is in
        the other dictionary (``SFXDataMesh.cs:1389-1403``) -- so ``ParameterMin1 = "0.35"`` paired with
        ``ParameterMax1 = "1"`` makes ``Parameter1`` vanish entirely, with no log;
      * an FBX entry's ``Animations`` playlist covers ``End - Start`` (else it FREEZES on its last frame
        -- THE ANIMATION-PLAYLIST LAW) is NOT checked here (it needs the clips' frame counts); that check
        lives in the staging emitter, which knows them.
    """
    who = path or "<sfxmodel>"
    try:
        doc = json.loads(text)
    except ValueError as e:
        return [f"{who}: not valid JSON ({e}) -- JSONNode.Parse returns null and the effect is skipped "
                f"silently (a trailing comma is the classic cause)"]
    if not isinstance(doc, dict):
        return [f"{who}: top level must be an object with \"FBX\" and/or \"Sprite\""]
    problems: list = []
    if "FBX" not in doc and "Sprite" not in doc:
        problems.append(f"{who}: neither \"FBX\" nor \"Sprite\" -- the file loads and renders nothing")

    def check_interp(where, node, key, segments, *, kind="safe", has_param=True):
        """``kind`` selects which half of THE TURNING SPLIT applies: ``"fbx"`` (customParam is null ->
        Turning is a hard NRE), ``"sprite_move"`` (Turning needs an emission Parameter), or ``"safe"``
        (the Color/Scale/UV dictionary path, which never touches customParam)."""
        val = node.get(key)
        if val is None:
            return
        names = val if isinstance(val, list) else [val]
        for n in names:
            if str(n) not in INTERPOLATIONS:
                problems.append(f"{who}: {where} {key} {n!r} is not one of {sorted(INTERPOLATIONS)} -- "
                                f"TryParseInterpolateType silently falls back to Constant")
            elif str(n) in TURNING_INTERPOLATIONS:
                if kind == "fbx":
                    problems.append(f"{who}: {where} {key} {n!r} {_FBX_TURNING_MSG}. Use one of "
                                    f"{sorted(FBX_INTERPOLATIONS)} on an FBX curve.")
                elif kind == "sprite_move" and not has_param:
                    problems.append(f"{who}: {where} {key} {n!r} {_SPRITE_TURNING_MSG}. Add a "
                                    f"ParameterMin0/ParameterMax0 pair to this Sprite's Emission, or use "
                                    f"one of {sorted(FBX_INTERPOLATIONS)}.")
        if isinstance(val, list) and segments is not None and len(val) < segments:
            problems.append(f"{who}: {where} {key} has {len(val)} entr(y/ies) but the keyframes make "
                            f"{segments} segment(s) -- segments past the array silently reuse entry 0")

    for si, sp in enumerate(doc.get("Sprite") or []):
        where = f"Sprite[{si}]"
        verts = sp.get("Vertices") or []
        idx = sp.get("Indices") or []
        for v in verts:
            if not _VEC_RE.match(str(v).strip()):
                problems.append(f"{who}: {where} vertex {v!r} is not a \"(x, y)\"/\"(x, y, z)\" tuple")
        if len(idx) % 3:
            problems.append(f"{who}: {where} has {len(idx)} Indices -- not a multiple of 3")
        for i in idx:
            n = _as_int(i)
            if n is None or not (0 <= n < len(verts)):
                problems.append(f"{who}: {where} index {i!r} is outside Vertices (0..{len(verts) - 1})")
        for anim_key, interp_key in (("ColorAnimation", "ColorInterpolation"),
                                     ("ScaleAnimation", "ScaleInterpolation")):
            keys = sp.get(anim_key) or []
            check_interp(where, sp, interp_key, max(0, len(keys) - 1) or None)
        for ci, ck in enumerate(sp.get("ColorAnimation") or []):
            cols = ck.get("VertexColors") or []
            if verts and len(cols) != len(verts):
                problems.append(f"{who}: {where} ColorAnimation[{ci}] has {len(cols)} VertexColors for "
                                f"{len(verts)} vertices -- the short tail renders opaque white")
        # THE TURNING SPLIT, sprite half: p.param is non-null only when the emission declared a
        # ParameterMin/ParameterMax pair (SFXDataMesh.cs:1386-1388).
        has_param = any(
            k.startswith(("ParameterMin", "ParameterMax"))
            for em in (sp.get("Emission") or []) if isinstance(em, dict) for k in em)
        mv = sp.get("Movement")
        if isinstance(mv, dict):
            for ax in "XYZ":
                check_interp(where, mv, f"InterpolationType{ax}", None,
                             kind="sprite_move", has_param=has_param)
        problems += _check_emission(who, where, sp.get("Emission"))

    for fi, fbx in enumerate(doc.get("FBX") or []):
        where = f"FBX[{fi}]"
        if not fbx.get("Path"):
            problems.append(f"{who}: {where} has no \"Path\" -- LoadFBX `continue`s past it silently "
                            f"(SFXDataMesh.cs:994-995)")
        for curve in ("Movement", "Rotation", "Scaling"):
            node = fbx.get(curve)
            pieces = node if isinstance(node, list) else ([node] if isinstance(node, dict) else [])
            if not pieces and curve in _FBX_SEED_TRAPS:
                problems.append(f"{who}: {where} has no \"{curve}\" -- {_FBX_SEED_TRAPS[curve]}")
            for pi, piece in enumerate(pieces):
                if not isinstance(piece, dict):
                    problems.append(f"{who}: {where} {curve}[{pi}] is not an object")
                    continue
                for ax in "XYZ":
                    check_interp(f"{where} {curve}[{pi}]", piece, f"InterpolationType{ax}", None,
                                 kind="fbx")
                if pi == 0 and not any(f"Origin{ax}" in piece for ax in "XYZ"):
                    problems.append(f"{who}: {where} {curve}[0] has no Origin* -- the first piece has no "
                                    f"previous destination to inherit (ParametricMovement.cs:88-105), so "
                                    f"its origin expression stays null")
    return problems


def _check_emission(who: str, where: str, emission) -> list:
    """The int/float ParameterMin/Max pairing trap (``SFXDataMesh.cs:1389-1403``)."""
    problems: list = []
    if not isinstance(emission, list):
        return problems
    for ei, em in enumerate(emission):
        if not isinstance(em, dict):
            continue
        kinds: dict = {}
        for key, val in em.items():
            for prefix in ("ParameterMin", "ParameterMax"):
                if key.startswith(prefix) and key[len(prefix):].isdigit():
                    k = int(key[len(prefix):])
                    kinds.setdefault(k, {})[prefix] = (
                        "int" if _as_int(val) is not None else "float", key, val)
        for k, seen in sorted(kinds.items()):
            if len(seen) < 2:
                problems.append(
                    f"{who}: {where} Emission[{ei}] Parameter{k} has only "
                    f"{sorted(v[1] for v in seen.values())} -- a Min without its Max (or vice versa) is "
                    f"DROPPED silently, so Parameter{k} evaluates to 0 in every expression")
                continue
            lo, hi = seen["ParameterMin"], seen["ParameterMax"]
            if lo[0] != hi[0]:
                problems.append(
                    f"{who}: {where} Emission[{ei}] pairs {lo[1]}={lo[2]!r} ({lo[0]}) with "
                    f"{hi[1]}={hi[2]!r} ({hi[0]}). The engine sorts Min/Max into SEPARATE int and float "
                    f"dictionaries by Int32.TryParse and drops any key whose partner landed in the other "
                    f"one -- Parameter{k} would vanish with no log. Write both with a decimal point, or "
                    f"both without.")
    return problems


def lint_sfxmodel_file(path) -> list:
    """:func:`lint_sfxmodel_text` on a file."""
    p = Path(path)
    try:
        return lint_sfxmodel_text(p.read_text(encoding="utf-8-sig"), path=str(p))
    except OSError as e:
        raise SeqLintError(f"cannot read {p}: {e}") from e
