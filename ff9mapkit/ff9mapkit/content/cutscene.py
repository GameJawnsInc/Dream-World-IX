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


def say(text_id: int, *, window: int = 1, flags: int = 128) -> bytes:
    """Step: open a dialogue/narration window showing ``text_id`` (blocks until the player dismisses)."""
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


def compile_steps(steps, txids) -> bytes:
    """Compile ordered cutscene step dicts to bytes. Handles global steps (``say`` / ``wait`` /
    ``set_flag``) and actor-context steps (``walk`` / ``teleport`` / ``animation`` / ``turn`` /
    ``face_player``). ``say`` steps consume ``txids`` (a list of resolved text ids) in order.

    Actor steps are only meaningful inside an ``actor`` cutscene (they act on the executing object);
    :func:`ff9mapkit.build.validate` enforces that. Same encoders the round-trip tests cover."""
    out, ti = [], 0
    for s in steps:
        if "say" in s:
            out.append(say(txids[ti])); ti += 1
        elif "wait" in s:
            out.append(wait(int(s["wait"])))
        elif "set_flag" in s:
            sf = s["set_flag"]
            out.append(set_flag(int(sf[0]), int(sf[1]) if len(sf) > 1 else 1))
        elif "walk" in s:
            out.append(actor_walk(s["walk"][0], s["walk"][1], s.get("speed")))
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
                       warmup: int = DEFAULT_WARMUP) -> bytes:
    """The gated choreography block, PREPENDED to the actor NPC's LOOP (tag 1) -- NOT its Init -- by
    :func:`ff9mapkit.content.npc.inject_npc`. Runs in the NPC's own context (so the actor steps target
    it) AND while the object is 'running' (engine state 1), where the engine ADVANCES animation frames.
    (An Init runs at state 2, where ProcessAnime is skipped -> the model glides frozen; confirmed by an
    in-engine probe -- so the choreography must live in the loop, like real FF9 cutscenes.)

    Shape: ``if (!flag) { DisableMove; Wait(warmup); <steps>; EnableMove; flag=1 }`` (no trailing RETURN
    -- the loop body + its RETURN follow). ALWAYS gated -- the loop runs every frame, so an ungated
    block would re-fire endlessly; the flag makes it run once per visit. The ``warmup`` Wait (after the
    lock, so the player can't wander) lets the field's entry fade settle before the actor moves."""
    inner = opcodes.DISABLE_MOVE
    if warmup > 0:
        inner += opcodes.wait(int(warmup))
    inner += compile_steps(steps, txids) + opcodes.ENABLE_MOVE + _region.set_var(flag_class, flag_idx, 1)
    return _region.if_block(_region.cond_not(flag_class, flag_idx), inner)


def build_body(steps, once_flag: int | None, flag_class=CUTSCENE_FLAG_CLASS) -> bytes:
    """The cutscene function body: ``DisableMove`` + the ordered ``steps`` + ``EnableMove``, all gated
    ``if (!once_flag) { ...; once_flag = 1 }`` when ``once_flag`` is set (so it plays once)."""
    inner = opcodes.DISABLE_MOVE + b"".join(steps) + opcodes.ENABLE_MOVE
    if once_flag is not None:
        inner += _region.set_var(flag_class, once_flag, 1)
        return _region.if_block(_region.cond_not(flag_class, once_flag), inner) + opcodes.RETURN
    return inner + opcodes.RETURN


def inject_cutscene(data, steps, *, once_flag: int | None = None, flag_class=CUTSCENE_FLAG_CLASS,
                    spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0) -> bytes:
    """Append a cutscene code entry (the sequence in :func:`build_body`) and run it on field load via
    an ``InitCode`` (over a Wait filler, or inserted into Main_Init). Returns new .eb bytes."""
    body = build_body(steps, once_flag, flag_class)
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
    slot = EbScript.from_bytes(data).first_free_slot()
    out = edit.append_entry(data, slot, entry)
    return edit.activate(out, opcodes.init_code(slot, 0), spawn_wait_n=spawn_wait_n,
                         spawn_wait_occurrence=spawn_wait_occurrence)
