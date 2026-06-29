"""Multi-actor cutscene CONDUCTOR -- FF9's central-director idiom (memory project-ff9-cutscene-multiactor).

A from-9-real-fields study (565/909/2554/2207/2169 ...) found FF9 coordinates 2+ scripted actors with a
single CONDUCTOR function -- NOT a per-actor flag handshake. ONE function (a code entry armed by
``InitCode`` in Main_Init) owns the control lock and sequences every actor, addressing each one BY UID via
the ``*Ex`` opcode family (``WindowSyncEx`` / ``TimedTurnEx`` / ``RunAnimationEx`` ...) so it never has to
context-switch into the actor. An actor's UID is its entry slot (``sid``); the player/control character is
uid 250 (the engine remaps 250 -> the active control uid). Timing between beats is a plain ``Wait``.

This module drives a flat, actor-tagged ``steps`` list. Beats run SEQUENTIALLY by default --
``say`` / ``turn`` / ``anim`` / ``walk`` driven on a named actor by id, plus ``wait`` / ``set_flag`` at the
conductor level -- but a beat marked ``with_prev = true`` runs IN PARALLEL with the beat(s) before it.

PARALLEL beats ("these run together") use FF9's real async-fork + script-level join, confirmed in the engine
(``EventEngine.DoEventCode.cs``: ``requestAcceptable(obj, lv) == lv < obj.level``):
  * each parallel member is FORKED non-blocking -- a walk via ``RunScriptAsync`` (op 0x10, which bypasses the
    level gate and spawns the walk in the actor's context), an anim via ``RunAnimationEx``, an instant turn
    via ``TurnInstantEx``;
  * the conductor then JOINS: one ``Wait`` covering the longest anim hold (anims play while walks run async),
    then a ``RunScriptSync`` (op 0x14) into each walking actor's bare-``RETURN`` join tag -- which ``stay()``s
    on the actor's busy script level until its async walk RETURNs (frees the level). That per-actor sync-drain
    is the engine's ONLY async barrier (``WaitSharedScript`` only joins the SAME object's own shared script,
    not a global wait). A ``say`` / ``wait`` / ``set_flag`` is a sequential barrier -- never ``with_prev``.

Softlock care, mirroring the kit's existing cutscene rules on player-cloned actors:
  * ``turn`` uses ``TurnInstantEx`` (instant, no wait) -- never ``WaitTurnEx`` (a player clone's turn anim
    may not drive the wait to completion -> hang);
  * ``anim`` uses ``RunAnimationEx`` + a fixed ``Wait`` hold -- never ``WaitAnimationEx`` (same hang risk).
"""

from __future__ import annotations

import struct

from ..eb import EbScript, cmdasm, edit, opcodes
from . import object as _object        # seat_entry (verbatim below-party-band seating)
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


WALK_LEVEL = 2          # RunScript script-level for a walk call (matches real fields 565/909/2554)
WALK_TAG_BASE = 20      # first walk-choreography tag added to an actor's entry (clear of inject_npc's 0/1/3)
PARALLEL_JOIN_TAG = 19  # a bare-RETURN tag added to a PARALLEL-walking actor's entry; the conductor
                        # RunScriptSyncs into it to block until the actor's async walk frees its script
                        # level (the join). Distinct from the walk tags (20+) and inject_npc's 0/1/3.


def join_tag_body() -> bytes:
    """The body of a parallel-walk JOIN tag: a bare ``RETURN``. The conductor ``RunScriptSync``s into it
    AFTER forking an async walk on the same actor -- the sync ``stay()``s on the actor's busy script level
    until the walk RETURNs (frees the level), then runs this (instant) and unblocks. Never polled (it's only
    ever called explicitly), so a 1-byte body is safe (unlike a tag-3 talk func)."""
    return opcodes.RETURN


def group_parallel(steps):
    """Group steps into PARALLEL runs: a step with ``with_prev = true`` joins the PRECEDING group; any other
    step starts a new group. Returns a list of groups, each a list of ``(index, step)``. (A ``with_prev`` on
    step 0 has no preceding group, so it becomes its own leader -- :func:`ff9mapkit.build._validate_conductor`
    flags that as an error; here we stay permissive.)"""
    groups = []
    for i, s in enumerate(steps):
        if s.get("with_prev") and groups:
            groups[-1].append((i, s))
        else:
            groups.append([(i, s)])
    return groups


def _emit_sequential_step(i, s, uid_by_name, txids, ti, say_flags, walk_calls):
    """Emit ONE step run sequentially (blocking). Returns ``(bytes, new_ti)``. Vocab: ``say`` / ``turn`` /
    ``anim`` / ``walk`` (need an ``actor = "<name>"``; ``say`` without one = a narration line) + ``wait`` /
    ``set_flag`` (conductor-level). A ``walk`` is a ``RunScriptSync(2, uid, walk_tag)`` -- the conductor can't
    walk an actor inline (base ``Walk`` acts on the EXECUTING object; no targeted WalkEx), so the caller
    pre-generates a walk tag on the actor's OWN entry and passes ``walk_calls`` (``step_index -> (uid, tag)``);
    the sync runs it in the actor's context (so it animates) and BLOCKS until it returns."""
    name = s.get("actor")
    uid = _uid_for(name, uid_by_name) if name else None
    if "say" in s:
        b = (actor_say(uid, txids[ti], flags=say_flags) if uid is not None
             else _cutscene.say(txids[ti], flags=say_flags))
        return b, ti + 1
    if "wait" in s:
        return opcodes.wait(int(s["wait"])), ti
    if "set_flag" in s:
        sf = s["set_flag"]
        return _cutscene.set_flag(int(sf[0]), int(sf[1]) if len(sf) > 1 else 1), ti
    if "turn" in s:
        if uid is None:
            raise ValueError(f"conductor step {s!r}: turn needs actor = \"<name>\"")
        return actor_turn(uid, s["turn"]), ti
    if "anim" in s:
        if uid is None:
            raise ValueError(f"conductor step {s!r}: anim needs actor = \"<name>\"")
        return actor_anim(uid, s["anim"]), ti
    if "walk" in s:
        if i not in walk_calls:
            raise ValueError(f"conductor step {s!r}: walk needs a pre-generated walk tag (walk_calls)")
        w_uid, w_tag = walk_calls[i]
        return opcodes.run_script_sync(WALK_LEVEL, w_uid, w_tag), ti   # run the actor's walk tag, block
    raise ValueError(f"unknown conductor step: {s!r}")


def _emit_parallel_group(group, uid_by_name, walk_calls, join_tags) -> bytes:
    """Emit a PARALLEL group (2+ beats that run together). Each member is FORKED non-blocking, then the
    conductor JOINS. Fork: a walk -> ``RunScriptAsync(2, uid, walk_tag)`` (op 0x10, no level gate -> always
    spawns the walk in the actor's context); an anim -> ``RunAnimationEx`` (fire only, the hold is absorbed
    into the join); an instant turn -> ``TurnInstantEx`` (no wait). Join (block until the whole group is done):
    one ``Wait(max anim-hold)`` -- the anims play out while the walks run async alongside -- then a
    ``RunScriptSync(2, uid, join_tag)`` per WALKING actor, which ``stay()``s on the actor's busy script level
    until its async walk RETURNs (the engine's only async barrier). Only ``walk`` / ``turn`` / ``anim`` may be
    parallel members (``say`` / ``wait`` / ``set_flag`` are sequential barriers -- enforced by validation)."""
    fan, drains, max_hold = [], [], 0
    for i, s in group:
        name = s.get("actor")
        uid = _uid_for(name, uid_by_name) if name else None
        if "walk" in s:
            if i not in walk_calls:
                raise ValueError(f"conductor parallel step {s!r}: walk needs a pre-generated walk tag")
            w_uid, w_tag = walk_calls[i]
            fan.append(opcodes.run_script_async(WALK_LEVEL, w_uid, w_tag))   # non-blocking fork (no level gate)
            jt = join_tags.get(w_uid)
            if jt is None:
                raise ValueError(f"conductor parallel step {s!r}: walk needs a join tag (join_tags)")
            if w_uid not in {u for u, _ in drains}:
                drains.append((w_uid, jt))
        elif "turn" in s:
            if uid is None:
                raise ValueError(f"conductor parallel step {s!r}: turn needs actor = \"<name>\"")
            fan.append(actor_turn(uid, s["turn"]))                          # instant -- nothing to join
        elif "anim" in s:
            if uid is None:
                raise ValueError(f"conductor parallel step {s!r}: anim needs actor = \"<name>\"")
            fan.append(opcodes.run_animation_ex(uid, int(s["anim"])))       # fire only; hold -> the join Wait
            max_hold = max(max_hold, _cutscene.ANIM_HOLD)
        else:
            raise ValueError(f"conductor parallel step {s!r}: only walk/turn/anim may run with_prev")
    out = b"".join(fan)
    if max_hold:
        out += opcodes.wait(max_hold)                  # anims play during this; walks run async alongside
    for w_uid, jt in drains:
        out += opcodes.run_script_sync(WALK_LEVEL, w_uid, jt)   # block until this actor's async walk frees its level
    return out


def compile_steps(steps, uid_by_name, txids, *, say_flags: int = 128, relock: bool = False,
                  walk_calls=None, join_tags=None) -> bytes:
    """Compile actor-tagged conductor steps to bytes. Beats run sequentially unless ``with_prev = true`` runs
    one IN PARALLEL with the preceding beat(s) -- see :func:`group_parallel`. A singleton group compiles via
    :func:`_emit_sequential_step` (a walk -> blocking ``RunScriptSync``); a multi-member group via
    :func:`_emit_parallel_group` (async fork + sync-drain join). ``say`` steps consume ``txids`` in order;
    the actor name resolves to a UID via ``uid_by_name`` (or ``"player"`` -> 250). ``walk_calls``
    (``step_index -> (uid, walk_tag)``) is required iff any step has ``walk``; ``join_tags``
    (``uid -> join_tag``) iff any walk runs ``with_prev``.

    ``relock`` prefixes every GROUP with ``DisableMove`` -- see :func:`build_body` for why the entry control
    grant needs the spin-lock + per-group re-lock."""
    walk_calls = walk_calls or {}
    join_tags = join_tags or {}
    out, ti = [], 0
    for group in group_parallel(steps):
        if relock:
            out.append(opcodes.DISABLE_MOVE)          # re-lock: undo any entry-transition control re-grant
        if len(group) == 1:
            i, s = group[0]
            chunk, ti = _emit_sequential_step(i, s, uid_by_name, txids, ti, say_flags, walk_calls)
            out.append(chunk)
        else:
            out.append(_emit_parallel_group(group, uid_by_name, walk_calls, join_tags))
    return b"".join(out)


def walk_tag_body(x: int, z: int, speed: int | None = None) -> bytes:
    """The body of a per-actor WALK tag, run via RunScript in the actor's own context (gExec == the actor,
    so base ``Walk`` moves IT and animates). Reuses the kit's actor-walk recipe (SetWalkTurnSpeed(255) +
    StopAnimation + InitWalk + Walk -- no WaitTurn/WaitAnimation, which hang on a player clone) + a RETURN
    so the blocking ``RunScriptSync`` caller unblocks on arrival.

    A base ``Walk`` SELF-BLOCKS until arrival, so if another actor's collision box sits in the path it never
    arrives => softlock (in-game 2026-06-28: a walk into a neighbor locked). The cure is faithful STAGING --
    author clear paths between an actor's start and its target (real FF9 does the same; the kit can't reroute
    around live actors). A ``SetPathing(0)`` collision-off wrap was tried and dropped: off the walkmesh the
    Walk can fail to register arrival (a different hang) and the actor can drift off-mesh -- clean spacing is
    both safer and how the real game stages cutscene walks."""
    return _cutscene.actor_walk(int(x), int(z), speed) + opcodes.RETURN


def build_body(steps, uid_by_name, txids, once_flag: int | None, *, flag_class=_region.GLOB_BOOL,
               warmup: int = _cutscene.DEFAULT_WARMUP, owns_control: bool = True,
               exit_warp: int | None = None, say_flags: int = 128,
               reorder: int = _cutscene.REORDER_WAIT, walk_calls=None, join_tags=None) -> bytes:
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
    inner += compile_steps(steps, uid_by_name, txids, say_flags=say_flags, relock=owns_control,
                           walk_calls=walk_calls, join_tags=join_tags)
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
                     walk_calls=None, join_tags=None, reserve_party_band: bool = False,
                     spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0) -> bytes:
    """Seat the conductor as a single-function code entry and arm it via ``InitCode`` in Main_Init (over a
    Wait filler), exactly like a narration cutscene. Returns new .eb bytes. ``walk_calls`` (a dict
    ``step_index -> (uid, tag)``) maps each ``walk`` step to its pre-generated per-actor walk tag;
    ``join_tags`` (``uid -> join_tag``) maps each PARALLEL-walking actor to its bare-RETURN join tag.

    ``reserve_party_band``: on a VERBATIM fork the donor's last 9 slots are the playable characters, so the
    conductor INSERTS just below them (``object.seat_entry``) -- keeping the band as the top slots and not
    perturbing the actors it addresses (which seat below the band before it, so their uids stay valid)."""
    body = build_body(steps, uid_by_name, txids, once_flag, flag_class=flag_class, warmup=warmup,
                      owns_control=owns_control, exit_warp=exit_warp, say_flags=say_flags,
                      walk_calls=walk_calls, join_tags=join_tags)
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
    out, slot = _object.seat_entry(data, entry, reserve_party_band=reserve_party_band)
    return edit.activate(out, opcodes.init_code(slot, 0), spawn_wait_n=spawn_wait_n,
                         spawn_wait_occurrence=spawn_wait_occurrence)
