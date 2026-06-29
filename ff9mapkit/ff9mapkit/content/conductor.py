"""Multi-actor cutscene CONDUCTOR -- FF9's central-director idiom (memory project-ff9-cutscene-multiactor).

A from-9-real-fields study (565/909/2554/2207/2169 ...) found FF9 coordinates 2+ scripted actors with a
single CONDUCTOR function -- NOT a per-actor flag handshake. ONE function (a code entry armed by
``InitCode`` in Main_Init) owns the control lock and sequences every actor, addressing each one BY UID via
the ``*Ex`` opcode family (``WindowSyncEx`` / ``TimedTurnEx`` / ``RunAnimationEx`` ...) so it never has to
context-switch into the actor. An actor's UID is its entry slot (``sid``); the player/control character is
uid 250 (the engine remaps 250 -> the active control uid). Timing between beats is a plain ``Wait``.

This module is the INCREMENT-1 director: SEQUENTIAL beats from a flat, actor-tagged ``steps`` list --
``say`` / ``turn`` / ``anim`` driven on a named actor by id, plus ``wait`` / ``set_flag`` at the conductor
level. Deliberately deferred (later increments, see the memory):
  * animated WALK -- needs ``RunScript`` into a per-actor walk tag (base ``Walk`` only animates in the
    actor's own tag-1 LOOP, state 1), so it's a bigger change than an inline ``*Ex`` op;
  * PARALLEL beats ("these run together") -- FF9 forks with ``RunScriptAsync`` and joins on the script
    *level* (``WaitSharedScript`` only joins the ONE shared script the SAME object spawned, not a global
    barrier), which needs its own grounding pass.

Softlock care, mirroring the kit's existing cutscene rules on player-cloned actors:
  * ``turn`` uses ``TurnInstantEx`` (instant, no wait) -- never ``WaitTurnEx`` (a player clone's turn anim
    may not drive the wait to completion -> hang);
  * ``anim`` uses ``RunAnimationEx`` + a fixed ``Wait`` hold -- never ``WaitAnimationEx`` (same hang risk).
"""

from __future__ import annotations

import struct

from ..eb import EbScript, cmdasm, edit, opcodes
from . import region as _region
from . import event as _event
from . import cutscene as _cutscene   # shared: once_flag_for / DEFAULT_WARMUP / ANIM_HOLD / REORDER_WAIT / say

PLAYER_UID = _cutscene.PLAYER_UID      # 250 -> the engine's control-character sentinel

# Spin-wait (frames) for the field/engine to grant control before locking. A field's entry transition
# (fade + scrolling-camera settle) RE-ENABLES control at a frame a fixed warmup can't predict -- in-game
# (2026-06-28) the player could walk + dismiss the first dialogue while the camera settled, then lost
# control. So: DisableMove, then SPIN until the engine RE-grants control, then DisableMove again -- the
# re-lock lands AFTER the grant and holds. Capped so a field that never re-grants can't hang.
CONTROL_POLL_CAP = 90                  # frames (~3s) -- the entry settle is ~0.5-1.5s; this is a safe ceiling


def wait_for_control_then_lock(cap: int = CONTROL_POLL_CAP) -> bytes:
    """Bytecode that spins until ``IsMovementEnabled`` (sysvar 2) becomes true -- the field/engine's entry
    control-grant -- then ``DisableMove`` so the lock lands AFTER that grant. Used AFTER an initial
    DisableMove, so it waits for the engine to RE-enable control (its entry-transition grant) and re-locks.

    Unrolled (no loop counter -> no MAP-byte out-of-bounds risk): ``cap`` copies of
    ``push IsMovementEnabled; JMP_IF granted; Wait(1)`` then ``granted: DisableMove``. Each check exits early
    via a forward ``JMP_IF`` the moment control is granted; if it's never granted the block falls through
    after ``cap`` frames and locks anyway. Assembled with :func:`cmdasm.assemble_block` (resolves the jumps)."""
    lines = []
    for _ in range(int(cap)):
        lines.append("SET({B_SYSVAR[2] B_EXPR_END})")   # push IsMovementEnabled (engine usercontrol)
        lines.append("JMP_IF(granted)")                  # granted -> stop spinning
        lines.append("op_22(1)")                         # else wait one frame and re-check
    lines += ["granted:", "DisableMove()"]               # lock NOW (after the grant) -- the lock that sticks
    return cmdasm.assemble_block("\n".join(lines))


def _uid_for(name, uid_by_name):
    """Resolve an actor NAME to its runtime UID: ``"player"`` -> 250 (control char); else its entry slot."""
    if name == "player":
        return PLAYER_UID
    return uid_by_name.get(name)


def actor_say(uid: int, text_id: int, *, flags: int = 128) -> bytes:
    """Step: the actor at ``uid`` speaks ``text_id`` -- ``WindowSyncEx(uid, 0, flags, txid)`` (the window
    is attributed to that actor by id, so its tail points at them). Blocks until dismissed."""
    return opcodes.window_sync_ex(uid, 0, flags, int(text_id))


def actor_turn(uid: int, angle: int) -> bytes:
    """Step: face ``angle`` INSTANTLY (0=S, 64=W, 128=N, 192=E) -- ``TurnInstantEx(uid, angle)``. Instant
    (no ``WaitTurnEx``) so it never hangs on a player-cloned actor whose turn anim doesn't complete."""
    return opcodes.turn_instant_ex(uid, int(angle))


def actor_anim(uid: int, anim: int, hold: int = _cutscene.ANIM_HOLD) -> bytes:
    """Step: play ``anim`` on the actor then hold ``hold`` frames -- ``RunAnimationEx(uid, anim)`` + a fixed
    ``Wait`` (NOT ``WaitAnimationEx``, which hangs if the clip doesn't drive the wait to completion)."""
    return opcodes.run_animation_ex(uid, int(anim)) + opcodes.wait(int(hold))


def compile_steps(steps, uid_by_name, txids, *, say_flags: int = 128, relock: bool = False) -> bytes:
    """Compile actor-tagged conductor steps to bytes. Each step is a dict with at most one action:
    ``say`` / ``turn`` / ``anim`` (need an ``actor = "<name>"``; ``say`` without an actor = a narration
    line), or ``wait`` / ``set_flag`` (conductor-level, no actor). ``say`` steps consume ``txids`` in order.
    The actor name resolves to a UID via ``uid_by_name`` (or ``"player"`` -> 250).

    ``relock`` prefixes every beat with ``DisableMove``: the field/engine re-grants player control while
    its entry transition (fade + scrolling-camera settle) completes, at a time a fixed warmup can't predict
    (in-game 2026-06-28: the player regained control as the camera settled). Re-asserting the lock before
    each beat means any such re-grant is undone by the very next beat, so the lock holds for the scene."""
    out, ti = [], 0
    for s in steps:
        if relock:
            out.append(opcodes.DISABLE_MOVE)          # re-lock: undo any entry-transition control re-grant
        name = s.get("actor")
        uid = _uid_for(name, uid_by_name) if name else None
        if "say" in s:
            out.append(actor_say(uid, txids[ti], flags=say_flags) if uid is not None
                       else _cutscene.say(txids[ti], flags=say_flags))
            ti += 1
        elif "wait" in s:
            out.append(opcodes.wait(int(s["wait"])))
        elif "set_flag" in s:
            sf = s["set_flag"]
            out.append(_cutscene.set_flag(int(sf[0]), int(sf[1]) if len(sf) > 1 else 1))
        elif "turn" in s:
            if uid is None:
                raise ValueError(f"conductor step {s!r}: turn needs actor = \"<name>\"")
            out.append(actor_turn(uid, s["turn"]))
        elif "anim" in s:
            if uid is None:
                raise ValueError(f"conductor step {s!r}: anim needs actor = \"<name>\"")
            out.append(actor_anim(uid, s["anim"]))
        else:
            raise ValueError(f"unknown conductor step: {s!r}")
    return b"".join(out)


def build_body(steps, uid_by_name, txids, once_flag: int | None, *, flag_class=_region.GLOB_BOOL,
               warmup: int = _cutscene.DEFAULT_WARMUP, owns_control: bool = True,
               exit_warp: int | None = None, say_flags: int = 128,
               reorder: int = _cutscene.REORDER_WAIT) -> bytes:
    """The conductor function body, run from a standalone ``InitCode``-armed code entry.

    Shape: ``[Wait(reorder)] [DisableMove] [Wait(warmup)] <beats> [EnableMove]`` gated
    ``if (!once_flag) { ...; once_flag = 1 }`` when ``once_flag`` is set. The leading ``reorder`` Wait lets
    Main_Init reach its own ``EnableMove`` first so the conductor's ``DisableMove`` is the last control-setter
    (the lock sticks); the ``warmup`` Wait (after the lock, so the player can't wander) lets the field's entry
    fade settle AND lets the actor objects finish spawning before the conductor addresses them by uid.

    ``exit_warp`` (a field id) ends the scene with a fade-to-black ``Field(exit_warp)`` instead of restoring
    control (the warp sits OUTSIDE the once-gate so it always fires); the fade avoids the destination loading
    in the clear. With ``exit_warp`` set, no ``EnableMove`` is emitted (the destination restores control).

    Control lock (the load-bearing part -- two in-game iterations to get right, 2026-06-28): a fixed warmup
    can't beat the field's entry control-grant, which re-enables control as the fade + scrolling-camera settle
    finish (the player could walk + dismiss the first window mid-settle). So under ``owns_control`` the conductor
    (1) ``DisableMove`` immediately, (2) ``wait_for_control_then_lock`` -- SPINS until the engine RE-grants
    control, then ``DisableMove`` again so the lock lands AFTER the grant -- and (3) ``compile_steps(relock=True)``
    re-locks before every beat as a backstop. The spin doubles as the actor-spawn settle (it runs ~until the
    grant, by which point the InitObject'd actors exist for the by-id ``*Ex`` ops)."""
    inner = opcodes.wait(int(reorder)) if reorder and reorder > 0 else b""
    if owns_control:
        inner += opcodes.DISABLE_MOVE                 # disable, so the spin waits for the engine's RE-grant
        inner += wait_for_control_then_lock()         # ... spin to that grant, then re-lock (the lock that holds)
    elif warmup > 0:
        inner += opcodes.wait(int(warmup))            # no lock: still settle so the actors exist before the beats
    inner += compile_steps(steps, uid_by_name, txids, say_flags=say_flags, relock=owns_control)
    if owns_control and exit_warp is None:
        inner += opcodes.ENABLE_MOVE
    if once_flag is not None:
        inner += _region.set_var(flag_class, once_flag, 1)
        body = _region.if_block(_region.cond_not(flag_class, once_flag), inner)
    else:
        body = inner
    if exit_warp is not None:
        body += _event.warp(int(exit_warp), fade=True)
    return body + opcodes.RETURN


def inject_conductor(data, steps, uid_by_name, txids, *, once_flag: int | None = None,
                     flag_class=_region.GLOB_BOOL, warmup: int = _cutscene.DEFAULT_WARMUP,
                     owns_control: bool = True, exit_warp: int | None = None, say_flags: int = 128,
                     spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0) -> bytes:
    """Append the conductor as a single-function code entry and arm it via ``InitCode`` in Main_Init
    (over a Wait filler), exactly like a narration cutscene. Returns new .eb bytes."""
    body = build_body(steps, uid_by_name, txids, once_flag, flag_class=flag_class, warmup=warmup,
                      owns_control=owns_control, exit_warp=exit_warp, say_flags=say_flags)
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
    slot = EbScript.from_bytes(data).first_free_slot()
    out = edit.append_entry(data, slot, entry)
    return edit.activate(out, opcodes.init_code(slot, 0), spawn_wait_n=spawn_wait_n,
                         spawn_wait_occurrence=spawn_wait_occurrence)
