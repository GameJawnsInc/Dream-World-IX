"""Cutscenes -- ordered, control-locked scripted sequences.

This is the one thing the declarative content (NPCs / events / flags) can't express: a SEQUENCE that
runs in order. A cutscene runs its actions in order with the player's control disabled for the
duration, optionally once (flag-gated), triggered on field entry.

There are two flavours, by whether the cutscene names an ``actor``:

* **Narration (v1, no actor)** -- a standalone code entry whose function steps through *controller-
  level* actions that need no per-actor targeting: ``say`` (a dialogue/narration window),
  ``wait`` (pause N frames), ``set_flag`` (set a story flag). Triggered on load via ``InitCode``.

* **Actor cutscene (v2, ``actor = "<npc>"``)** -- the sequence is spliced into THAT NPC's Init (see
  :func:`build_choreography`, used by :func:`ff9mapkit.content.npc.inject_npc` via its ``intro=``),
  so it runs in the NPC's own object context (``gExec`` == the NPC). That lets the *actor* steps work
  with plain base opcodes that act on the executing object: ``walk`` / ``teleport`` (MoveInstantXZY)
  / ``animation`` (RunAnimation+WaitAnimation) / ``turn`` (TimedTurn+WaitTurn) / ``face_player``
  (TurnTowardObject 250). ``say`` / ``wait`` / ``set_flag`` work there too (they're global). No
  cross-entry RunScript or UID targeting is needed -- and ``Walk`` self-blocks until arrival, so the
  steps stay ordered. The block is ``if (!once) { DisableMove; <steps>; EnableMove; once=1 }``.

Both grounded in the standard FF9 pattern -- ``DisableMove`` (0x2D) ... actions ... ``EnableMove``
(0x2E), flag-gated so a one-time scene doesn't replay -- and in real walk cutscenes (e.g. Gargan
Roo's Kuja walk function: SetWalkSpeed -> RunAnimation -> WaitAnimation -> InitWalk -> Walk).
"""

from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region
from . import event as _event

# Default flag for a "play once" cutscene: the SAVE-PERSISTENT Global bool (survives reloads), high in
# gEventGlobal and clear of the event auto-once band (8000+).
CUTSCENE_FLAG_CLASS = _region.GLOB_BOOL
DEFAULT_CUTSCENE_FLAG = 8100        # GLOB (save-persistent) once-flag: plays once EVER
DEFAULT_CUTSCENE_MAP_FLAG = 80      # MAP-bit (transient, byte 10 -- clear of the field's init bits 144-159
                                    # and the camera Map-byte 24): replays each visit, still once per visit

PLAYER_UID = 250        # GetObjUID(250) resolves to the player's control character (engine convention)

# A field's Main_Init enables control then runs a ~16-frame entry FadeFilter; for the first frames
# the field is still fading + the smooth-frame-updater is settling actor positions. Issuing an actor
# Walk during that window makes the actor circle and never converge (its synchronous Walk then hangs
# -> softlock). So an ACTOR cutscene waits a warm-up before commanding the actor -- exactly what real
# entry cutscenes do (Main_Loop `Wait(...)` before RunScript). Tunable via `[cutscene] warmup = N`.
DEFAULT_WARMUP = 30     # frames (~1s @ 30fps); generous margin over the 16-frame entry fade


# A compulsory / auto-advance ATE (FF9's FORCED "Active Time Event" cutscene -- no menu, plays at a story
# beat, e.g. field 956 Gargant / the Festival-of-the-Hunt cluster) is an ordinary cutscene with two cosmetic
# ATE flourishes, both grounded byte-for-byte in the real grey mode-6 fields (`docs/ATE_SYSTEM.md` Flavor A):
#   * its dialogue windows carry the winATE caption flag (64) -> the "Active Time Event" header. This flag
#     is ALSO what makes the engine tag the closed dialog `isCompulsory` (ETb.ProcessATEDialog) -- the
#     defining, engine-recognized marker of a compulsory ATE.
#   * the body is bracketed `ATE(6) ... ATE(0)` (0xD7) -- the grey-unskippable HUD-icon arm (Gray+force; the
#     mode arg is a 3-bit flag word, not an enum -- &3==2 Gray, &4 force; see EIcon.cs:416-454 / ATE_SYSTEM.md).
#     (NB field 1901's Eiko ATE is the OPTIONAL Blue mode-1 menu hub, NOT this forced flavor -- don't mirror it.)
# TWO real templates for an auto-playing ATE (676-field byte sweep + the grey-unskippable re-classification,
# docs/ATE_SYSTEM.md):
#   * ate_mode = 6 (GREY + force-show) = the AUTHENTIC UNSKIPPABLE ATE and the DEFAULT -- the real game's forced
#     ATEs (field 956, the Festival-of-the-Hunt cluster) use ATE(6): a grey, force-shown icon that renders even
#     under the control-lock. It drives the bottom-left "ACTIVE TIME EVENT" HUD banner (ActiveTimeEvent.cs), whose
#     grey "ATE" sprite blinks 1s on / 1s off (DisplayGrayATEText) and shows NO press glyph. ★ in-game proven @30008.
#   * ate_mode = 1 (Blue, no force) = the opt-in quiet no-icon variant: mode 1's render gate
#     (`mode>0 && ((mode&4) || GetUserControl())`) FAILS under the control-lock, so no HUD banner shows -- the
#     winATE CAPTION window is the only marker (also proven @30008, before the mode-6 switch).
# AVOID ate_mode = 5 (Blue + force): a force-shown Blue icon re-flashes the "Press SELECT" glyph (the Blue
# coroutine), wrongly inviting a press during an auto-play. mode 2 is unused in the real game; the only grey is 6.
# (NB the kit holds ATE(6) armed across the whole body so the grey banner blinks throughout -- more legible than
# real 956, which clears it behind a white fade-in; this matches what players remember seeing.)
# Seen-state + the ATE80 trophy register only on a REAL field id (MappingATEID keyed on fldMapNo/SC) -- the wall.
# Mirrors `ate.WIN_ATE`; kept local to avoid importing the ate module (which imports choice -> region).
ATE_CAPTION_FLAG = 64
ATE_DEFAULT_MODE = 6     # ATE(mode) HUD arm. 6 = the authentic GREY UNSKIPPABLE banner (default, in-game proven
                         # @30008); 1 = opt-in quiet no-icon variant. Avoid 5 (Blue force-show re-flashes press glyph)


def say(text_id: int, *, window: int = 1, flags: int = 128) -> bytes:
    """Step: open a dialogue/narration window showing ``text_id`` (blocks until the player dismisses).
    ``flags = 64`` (winATE) renders it with the "Active Time Event" caption (a compulsory-ATE window)."""
    return opcodes.window_sync(window, flags, text_id)


def wait(frames: int) -> bytes:
    """Step: pause for ``frames`` frames."""
    return opcodes.wait(frames)


def set_flag(idx: int, value: int = 1, *, flag_class=CUTSCENE_FLAG_CLASS) -> bytes:
    """Step: set a GlobBool story flag (advance/record state from within the scene)."""
    return _region.set_var(flag_class, idx, value)


# --- actor-context steps (v2) -- only valid inside an `actor` cutscene (run in the NPC's entry) ---
# How fast the actor rotates toward its destination while walking (omega, 0..255). High = the
# turn-while-walk arc shrinks to ~nothing, so a walk to a point BEHIND the actor turns and goes
# straight instead of orbiting it forever. This replaces a separate animated pre-turn
# (TurnTowardPosition/TimedTurn + WaitTurn), which can HANG at ~180deg (the animated big-turn path
# never completing -> WaitTurn stuck -> softlock). Self-converging + deterministic at exactly 180.
WALK_TURN_SPEED = 255


def actor_walk(x: int, z: int, speed: int | None = None) -> bytes:
    """Step: the actor walks to world (x, z).

    Sets a high walk-turn-speed first so the Walk rotates tightly toward the destination and walks
    straight (no arc), converging even when the target is directly BEHIND the actor -- without the
    animated pre-turn that hangs at ~180deg. ``StopAnimation`` clears the anim flags first so the
    engine actually swaps idle->walk while moving (else a player-cloned NPC glides in its idle pose).
    ``Walk`` blocks until arrival. Optional ``speed`` sets the walk movement speed. Uses the NPC's
    walk animation (set in its Init)."""
    pre = opcodes.set_walk_speed(int(speed)) if speed is not None else b""
    return (pre + opcodes.set_walk_turn_speed(WALK_TURN_SPEED) + opcodes.stop_animation()
            + opcodes.init_walk() + opcodes.walk(int(x), int(z)))


def actor_teleport(x: int, z: int) -> bytes:
    """Step: instantly move the actor to world (x, z) -- no walk animation -- then re-enable its
    walkmesh pathing (MoveInstantXZY disables it). Use it as a cutscene's FIRST step to place the
    actor off-screen for a walk-in (the kit handles the engine's POS3 Z-negation; a leading teleport
    runs before the warm-up so the actor settles off-screen rather than flashing at its spawn)."""
    return opcodes.move_instant_xzy(int(x), int(z), 0) + opcodes.set_pathing(1)


# Cutscene steps are NON-BLOCKING on the animation system: we never use WaitAnimation/WaitTurn,
# because they HANG if the actor's anim playback doesn't drive them to completion (a player-cloned
# NPC's walk/turn anims don't always engage -> WaitTurn/WaitAnimation never return -> softlock). A
# turn is done INSTANTLY (no turn anim needed); an animation is played then given a fixed hold.
ANIM_HOLD = 40          # frames to let a played animation run before the next step (~1.3s)


def actor_animation(anim: int, hold: int = ANIM_HOLD) -> bytes:
    """Step: play animation ``anim`` on the actor, then hold ``hold`` frames (RunAnimation + a fixed
    Wait -- NOT WaitAnimation, which hangs if the anim doesn't complete)."""
    return opcodes.run_animation(int(anim)) + opcodes.wait(int(hold))


def actor_turn(angle: int) -> bytes:
    """Step: face ``angle`` INSTANTLY (0=south, 64=west, 128=north, 192=east). Instant (TurnInstant) so
    it works without a turn animation and never hangs."""
    return opcodes.turn_instant(int(angle))


def actor_face(uid: int = PLAYER_UID, speed: int = 16) -> bytes:
    """Step: turn the actor to face an object by UID (default 250 = the player), animated, non-blocking
    (no WaitTurn). Visible only if the turn anim engages; for a guaranteed instant facing use ``turn``."""
    return opcodes.turn_toward_object(int(uid), int(speed))


def compile_steps(steps, txids, *, say_flags: int = 128) -> bytes:
    """Compile ordered cutscene step dicts to bytes. Handles global steps (``say`` / ``wait`` /
    ``set_flag``) and actor-context steps (``walk`` / ``path`` / ``teleport`` / ``animation`` /
    ``turn`` / ``face_player``). ``say`` steps consume ``txids`` (a list of resolved text ids) in order.

    Actor steps are only meaningful inside an ``actor`` cutscene (they act on the executing object);
    :func:`ff9mapkit.build.validate` enforces that. ``say_flags`` is the window flag for every ``say``
    step -- pass ``ATE_CAPTION_FLAG`` (64) to render a compulsory ATE's windows with the ATE caption.
    Same encoders the round-trip tests cover."""
    out, ti = [], 0
    for s in steps:
        if "say" in s:
            out.append(say(txids[ti], flags=say_flags)); ti += 1
        elif "wait" in s:
            out.append(wait(int(s["wait"])))
        elif "set_flag" in s:
            sf = s["set_flag"]
            out.append(set_flag(int(sf[0]), int(sf[1]) if len(sf) > 1 else 1))
        elif "walk" in s:
            out.append(actor_walk(s["walk"][0], s["walk"][1], s.get("speed")))
        elif "path" in s:                          # a multi-waypoint route = consecutive straight walks
            for pt in s["path"]:
                out.append(actor_walk(int(pt[0]), int(pt[1])))
        elif "teleport" in s:
            out.append(actor_teleport(s["teleport"][0], s["teleport"][1]))
        elif "animation" in s:
            out.append(actor_animation(s["animation"]))
        elif "turn" in s:
            out.append(actor_turn(s["turn"]))
        elif "face_player" in s:
            out.append(actor_face())
        else:
            raise ValueError(f"unknown cutscene step: {s!r}")
    return b"".join(out)


def once_flag_for(cs: dict):
    """(flag_class, flag_idx) for a cutscene's gate. ``once=true`` -> a SAVE-PERSISTENT Global bool
    (plays once ever); ``once=false`` -> a TRANSIENT Map bool (replays each visit -- the Map var resets
    on field load -- but still runs once per visit). An explicit ``flag = N`` overrides the index."""
    if cs.get("once", True):
        return _region.GLOB_BOOL, int(cs.get("flag", DEFAULT_CUTSCENE_FLAG))
    return _region.MAP_BOOL, int(cs.get("flag", DEFAULT_CUTSCENE_MAP_FLAG))


def build_choreography(steps, txids, flag_idx: int, *, flag_class=CUTSCENE_FLAG_CLASS,
                       warmup: int = DEFAULT_WARMUP, ate_mode: int | None = None,
                       say_flags: int = 128) -> bytes:
    """The gated choreography block, PREPENDED to the actor NPC's LOOP (tag 1) -- NOT its Init -- by
    :func:`ff9mapkit.content.npc.inject_npc`. Runs in the NPC's own context (so the actor steps target
    it) AND while the object is 'running' (engine state 1), where the engine ADVANCES animation frames.
    (An Init runs at state 2, where ProcessAnime is skipped -> the model glides frozen; confirmed by an
    in-engine probe -- so the choreography must live in the loop, like real FF9 cutscenes.)

    Shape: ``if (!flag) { DisableMove; Wait(warmup); <steps>; EnableMove; flag=1 }`` (no trailing RETURN
    -- the loop body + its RETURN follow). ALWAYS gated -- the loop runs every frame, so an ungated
    block would re-fire endlessly; the flag makes it run once per visit. The ``warmup`` Wait (after the
    lock, so the player can't wander) lets the field's entry fade settle before the actor moves.

    ``ate_mode`` (not None) styles it as a compulsory ATE: brackets the steps ``ATE(mode) ... ATE(0)``
    and (with ``say_flags=ATE_CAPTION_FLAG``) gives its windows the ATE caption -- mirrors the real grey
    mode-6 fields (e.g. 956 Gargant), NOT field 1901 (which is the optional Blue mode-1 menu hub)."""
    inner = opcodes.DISABLE_MOVE
    if warmup > 0:
        inner += opcodes.wait(int(warmup))
    if ate_mode is not None:
        inner += opcodes.ate(int(ate_mode))                  # arm the blinking "Active Time Event" prompt
    inner += compile_steps(steps, txids, say_flags=say_flags)
    if ate_mode is not None:
        inner += opcodes.ate(0)                              # disarm before control returns (close the bracket)
    inner += opcodes.ENABLE_MOVE + _region.set_var(flag_class, flag_idx, 1)
    return _region.if_block(_region.cond_not(flag_class, flag_idx), inner)


# A narration cutscene runs in a SEPARATE code entry armed by `InitCode` in Main_Init -- but Main_Init
# itself calls `EnableMove` (and a fade) AFTER that InitCode. If the director's `DisableMove` ran first
# it would be immediately overridden by Main_Init's `EnableMove`, so the player keeps control during the
# text. Yielding a couple of frames first lets Main_Init reach its `EnableMove` (it does so in the first
# frame), so the director's `DisableMove` is the LAST control-setter and the lock sticks. (An ACTOR
# cutscene avoids this by living in the NPC's LOOP, which only runs after Init completes.) ~2 frames is
# imperceptible (<100ms) and the window only shows during the entry fade.
REORDER_WAIT = 2


def build_body(steps, once_flag: int | None, flag_class=CUTSCENE_FLAG_CLASS,
               reorder: int = REORDER_WAIT, *, ate_mode: int | None = None,
               then_warp: int | None = None) -> bytes:
    """The cutscene function body: a brief reorder ``Wait`` (so the lock outlives Main_Init's EnableMove)
    then ``DisableMove`` + the ordered ``steps`` + ``EnableMove``, all gated ``if (!once_flag) { ...;
    once_flag = 1 }`` when ``once_flag`` is set (so it plays once).

    ``ate_mode`` (not None) brackets the steps ``ATE(mode) ... ATE(0)`` -- a compulsory ATE's HUD prompt
    (the winATE caption on its windows is set by the caller via ``compile_steps(say_flags=...)``).

    ``then_warp`` (a field id) makes the scene AUTO-RETURN: it ends with a FADE-TO-BLACK then
    ``Field(then_warp)`` instead of restoring control -- exactly how real grey ATEs end (field 956 ->
    ``Field(2054)``). The warp sits OUTSIDE the once-gate so it ALWAYS fires (even on a re-entry that skips
    a once'd cutscene, the player still warps back); it transitions away, so it's the last op (no
    ``EnableMove`` -- the destination's Main_Init restores control). It fades out first (``warp(fade=True)``)
    so the destination doesn't load in the clear (the static-screen bug). Field() transitions from this
    InitCode'd entry just like the World-Hub menu-row warp does (same code-entry context -- NOT the
    Main_Init no-op case)."""
    pre = opcodes.wait(int(reorder)) if reorder and reorder > 0 else b""
    inner = pre + opcodes.DISABLE_MOVE
    if ate_mode is not None:
        inner += opcodes.ate(int(ate_mode))
    inner += b"".join(steps)
    if ate_mode is not None:
        inner += opcodes.ate(0)
    if then_warp is None:
        inner += opcodes.ENABLE_MOVE                      # restore control (a normal cutscene stays put)
    if once_flag is not None:
        inner += _region.set_var(flag_class, once_flag, 1)
        body = _region.if_block(_region.cond_not(flag_class, once_flag), inner)
    else:
        body = inner
    if then_warp is not None:
        # fade=True: fade to black BEFORE the warp, like every field transition (gateway/ladder/choice).
        # Without it the destination loads in the clear and you see its camera-init frames (the static-
        # screen bug). A real grey-ATE return may already be black behind the ATE banner, but the kit
        # doesn't reproduce that, so an explicit source-side fade is the safe default. See event.warp.
        body += _event.warp(int(then_warp), fade=True)    # AUTO-RETURN: fade to black, then transition
    return body + opcodes.RETURN


def inject_cutscene(data, steps, *, once_flag: int | None = None, flag_class=CUTSCENE_FLAG_CLASS,
                    spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0,
                    ate_mode: int | None = None, then_warp: int | None = None) -> bytes:
    """Append a cutscene code entry (the sequence in :func:`build_body`) and run it on field load via
    an ``InitCode`` (over a Wait filler, or inserted into Main_Init). Returns new .eb bytes.
    ``ate_mode`` (not None) styles it as a compulsory ATE (the ``ATE(mode)`` HUD bracket); ``then_warp``
    (a field id) makes it auto-return with ``Field(then_warp)`` at the end."""
    body = build_body(steps, once_flag, flag_class, ate_mode=ate_mode, then_warp=then_warp)
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
    slot = EbScript.from_bytes(data).first_free_slot()
    out = edit.append_entry(data, slot, entry)
    return edit.activate(out, opcodes.init_code(slot, 0), spawn_wait_n=spawn_wait_n,
                         spawn_wait_occurrence=spawn_wait_occurrence)
