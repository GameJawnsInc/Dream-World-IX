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
    level gate and spawns the walk in the actor's context), an anim via ``RunAnimationEx``, a turn via
    ``TimedTurnEx`` (fire-and-forget; its hold folds into the join Wait);
  * the conductor then JOINS: one ``Wait`` covering the longest anim hold (anims play while walks run async),
    then a ``RunScriptSync`` (op 0x14) into each walking actor's bare-``RETURN`` join tag -- which ``stay()``s
    on the actor's busy script level until its async walk RETURNs (frees the level). That per-actor sync-drain
    is the engine's ONLY async barrier (``WaitSharedScript`` only joins the SAME object's own shared script,
    not a global wait). A ``say`` / ``wait`` / ``set_flag`` is a sequential barrier -- never ``with_prev``.

Softlock care, mirroring the kit's existing cutscene rules:
  * ``turn`` uses ``TimedTurnEx`` (animated, the stock look) + a fixed ``Wait`` hold -- never
    ``WaitTurnEx`` (a clip that doesn't drive the wait to completion hangs it);
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
CONTROL_POLL_CAP = 240                 # frames (~8s). Was 90 (~3s) -- IN-GAME DISPROVEN 2026-07-12 on the
#                                        stolen-ember campaign: a BG-borrow/scrolling (Moguri'd) field's
#                                        entry grant can land AFTER 3s, so the spin fell through, the beats
#                                        started, and the LATE grant handed the player control mid-scene
#                                        (walking into the actor's path stalls its synchronous walk forever).
#                                        The cap is now pacing-only: the WATCHDOG below owns correctness.

# The control WATCHDOG (the deterministic half of the fix): a tiny concurrent code entry that, while a
# scene-running MAP flag is up, re-locks control within ONE frame of ANY grant -- whatever granted it (the
# field's own Main_Init EnableMove, the engine's entry transition, a hotfix). The conductor raises the flag
# on entry and lowers it before restoring control; the spin above then only PACES the scene start.
WATCHDOG_MAP_FLAG = 110                # MAP bit (transient): clear of the dispatch once-band (80+k),
#                                        the camera Map-byte 24, and the field-init bits 144-159


def watchdog_body(flag: int = WATCHDOG_MAP_FLAG) -> bytes:
    """The watchdog entry's function body: an infinite 1-frame poll -- while MAP ``flag`` is up (a cast
    scene owns control) and the engine has (re)granted ``usercontrol``, ``DisableMove`` re-locks it. Armed
    once per field from Main_Init; idles at one expression per frame when no scene is running."""
    lines = [
        "top:",
        f"SET({{Map.Bit[{int(flag)}] B_SYSVAR[2] B_ANDAND B_EXPR_END}})",  # scene running AND control granted
        "JMP_IFNOT(rest)",
        "DisableMove()",                                   # a late/rogue grant -> re-lock within one frame
        "rest:",
        "op_22(1)",
        "JMP(top)",
    ]
    return cmdasm.assemble_block("\n".join(lines))


def inject_watchdog(data, *, flag: int = WATCHDOG_MAP_FLAG, reserve_party_band: bool = False) -> bytes:
    """Append + arm the control watchdog as its own code entry (once per field -- shared by every cast
    scene via the one MAP flag).

    ⚠ THE TICK-ORDER LAW (in-game 2026-07-12, the 8-second scene-start stall): tick order = Main_Init
    activation order, and the conductor's grant-catch spin must CHECK before the watchdog's re-lock each
    frame, while the watchdog must tick AFTER the grant sources (the player entry's EnableMove) -- else
    the watchdog kills every grant in the frame it lands and the spin starves to its full
    CONTROL_POLL_CAP (~8s of dead air before every scene). So the watchdog and its conductors PIN to the
    Main_Init INSERT path (never a Wait filler -- filler positions vary with the field's content mix; the
    gate-law fix freed two late fillers and this InitCode landed AFTER the player, starving both stolen-
    ember scenes). Insert is LIFO at Main_Init start: activate the watchdog FIRST, conductors after ->
    conductors sit above it and tick first."""
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + watchdog_body(flag) + opcodes.RETURN
    out, slot = _object.seat_entry(data, entry, reserve_party_band=reserve_party_band)
    return edit.activate_block(out, opcodes.init_code(slot, 0))


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


def actor_turn(uid: int, angle: int, hold: int = _cutscene.TURN_HOLD) -> bytes:
    """Step: face ``angle`` (0=S, 64=W, 128=N, 192=E) ANIMATED -- ``TimedTurnEx(uid, angle, 16)`` + a
    fixed ``Wait`` hold (the anim-hold idiom; NOT ``WaitTurnEx``, which hangs if the turn anim doesn't
    drive it to completion)."""
    return opcodes.timed_turn_ex(uid, int(angle), _cutscene.TURN_SPEED) + opcodes.wait(int(hold))


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


# the step kinds that run as a pre-generated TAG on the actor's own entry (RunScriptSync'd into it, so the
# op executes in the actor's context -- base Walk/MoveInstant/TurnTowardObject act on the EXECUTING object).
TAG_STEP_KINDS = ("walk", "path", "teleport", "face_player")


def _emit_sequential_step(i, s, uid_by_name, txids, ti, say_flags, tag_calls):
    """Emit ONE step run sequentially (blocking). Returns ``(bytes, new_ti)``. Vocab: ``say`` / ``turn`` /
    ``animation`` / ``walk`` / ``path`` / ``teleport`` / ``face_player`` (need an ``actor = "<name>"``;
    ``say`` without one = a narration line) + ``wait`` / ``set_flag`` (conductor-level). The
    :data:`TAG_STEP_KINDS` run as a ``RunScriptSync(2, uid, tag)`` into a pre-generated tag on the actor's
    OWN entry -- the conductor can't move an actor inline (base ``Walk``/``MoveInstantXZY``/
    ``TurnTowardObject`` act on the EXECUTING object; there is no targeted *Ex form) -- so the caller passes
    ``tag_calls`` (``step_index -> (uid, tag)``); the sync runs the tag in the actor's context (so it
    animates) and BLOCKS until it returns."""
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
    if "animation" in s:
        if uid is None:
            raise ValueError(f"conductor step {s!r}: animation needs actor = \"<name>\"")
        return actor_anim(uid, s["animation"]), ti
    for kind in TAG_STEP_KINDS:
        if kind in s:
            if i not in tag_calls:
                raise ValueError(f"conductor step {s!r}: {kind} needs a pre-generated actor tag (tag_calls)")
            t_uid, t_tag = tag_calls[i]
            return opcodes.run_script_sync(WALK_LEVEL, t_uid, t_tag), ti   # run the actor's tag, block
    raise ValueError(f"unknown conductor step: {s!r}")


def _emit_parallel_group(group, uid_by_name, tag_calls, join_tags) -> bytes:
    """Emit a PARALLEL group (2+ beats that run together). Each member is FORKED non-blocking, then the
    conductor JOINS. Fork: a walk/path -> ``RunScriptAsync(2, uid, tag)`` (op 0x10, no level gate -> always
    spawns the tag in the actor's context); an animation -> ``RunAnimationEx`` (fire only, the hold is
    absorbed into the join); a turn -> ``TimedTurnEx`` (fire only, same). Join (block until the whole group
    is done): one ``Wait(max anim-hold)`` -- the anims play out while the walks run async alongside -- then a
    ``RunScriptSync(2, uid, join_tag)`` per WALKING actor, which ``stay()``s on the actor's busy script level
    until its async walk RETURNs (the engine's only async barrier). Only ``walk`` / ``path`` / ``turn`` /
    ``animation`` may be parallel members (``say`` / ``wait`` / ``set_flag`` / ``teleport`` / ``face_player``
    are sequential -- enforced by validation)."""
    fan, drains, max_hold = [], [], 0
    for i, s in group:
        name = s.get("actor")
        uid = _uid_for(name, uid_by_name) if name else None
        if "walk" in s or "path" in s:
            if i not in tag_calls:
                raise ValueError(f"conductor parallel step {s!r}: walk/path needs a pre-generated tag")
            w_uid, w_tag = tag_calls[i]
            fan.append(opcodes.run_script_async(WALK_LEVEL, w_uid, w_tag))   # non-blocking fork (no level gate)
            jt = join_tags.get(w_uid)
            if jt is None:
                raise ValueError(f"conductor parallel step {s!r}: walk/path needs a join tag (join_tags)")
            if w_uid not in {u for u, _ in drains}:
                drains.append((w_uid, jt))
        elif "turn" in s:
            if uid is None:
                raise ValueError(f"conductor parallel step {s!r}: turn needs actor = \"<name>\"")
            fan.append(opcodes.timed_turn_ex(uid, int(s["turn"]), _cutscene.TURN_SPEED))  # fire only;
            max_hold = max(max_hold, _cutscene.TURN_HOLD)                   # hold -> the join Wait
        elif "animation" in s:
            if uid is None:
                raise ValueError(f"conductor parallel step {s!r}: animation needs actor = \"<name>\"")
            fan.append(opcodes.run_animation_ex(uid, int(s["animation"])))  # fire only; hold -> the join Wait
            max_hold = max(max_hold, _cutscene.ANIM_HOLD)
        else:
            raise ValueError(f"conductor parallel step {s!r}: only walk/path/turn/animation may run with_prev")
    out = b"".join(fan)
    if max_hold:
        out += opcodes.wait(max_hold)                  # anims play during this; walks run async alongside
    for w_uid, jt in drains:
        out += opcodes.run_script_sync(WALK_LEVEL, w_uid, jt)   # block until this actor's async walk frees its level
    return out


def compile_steps(steps, uid_by_name, txids, *, say_flags: int = 128, relock: bool = False,
                  tag_calls=None, join_tags=None) -> bytes:
    """Compile actor-tagged conductor steps to bytes. Beats run sequentially unless ``with_prev = true`` runs
    one IN PARALLEL with the preceding beat(s) -- see :func:`group_parallel`. A singleton group compiles via
    :func:`_emit_sequential_step` (a tag-kind -> blocking ``RunScriptSync``); a multi-member group via
    :func:`_emit_parallel_group` (async fork + sync-drain join). ``say`` steps consume ``txids`` in order;
    the actor name resolves to a UID via ``uid_by_name`` (or ``"player"`` -> 250). ``tag_calls``
    (``step_index -> (uid, tag)``) is required iff any step is a :data:`TAG_STEP_KINDS`; ``join_tags``
    (``uid -> join_tag``) iff any walk/path runs ``with_prev``.

    ``relock`` prefixes every GROUP with ``DisableMove`` -- see :func:`build_body` for why the entry control
    grant needs the spin-lock + per-group re-lock."""
    tag_calls = tag_calls or {}
    join_tags = join_tags or {}
    out, ti = [], 0
    for group in group_parallel(steps):
        if relock:
            out.append(opcodes.DISABLE_MOVE)          # re-lock: undo any entry-transition control re-grant
        if len(group) == 1:
            i, s = group[0]
            chunk, ti = _emit_sequential_step(i, s, uid_by_name, txids, ti, say_flags, tag_calls)
            out.append(chunk)
        else:
            out.append(_emit_parallel_group(group, uid_by_name, tag_calls, join_tags))
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


def follow_tag_body(target_uid: int, speed: int | None = None) -> bytes:
    """A walk-up-to-a-LIVE-object tag body: ``WalkTowardObject`` (0x24 MOVA) walks toward the target's
    LIVE position each frame and -- the load-bearing engine fact (``MoveToward_mixed``'s follow mode) --
    **ends the moment it collides with that target**. So a ``walk = "@player"`` compiled this way cannot
    be blocked by the player standing in the path (in-game 2026-07-12: a build-time static target let a
    one-frame input window brick the scene -- the player stepped toward the actor and the frozen target
    landed inside the player's own box, stalling the synchronous Walk forever). This is FF9's own
    "NPC walks up to you" primitive; a third character in the path can still block (stage clear paths)."""
    body = b""
    if speed is not None:
        body += opcodes.encode(0x26, int(speed))           # SetWalkSpeed
    body += opcodes.encode(0x55, 255)                      # SetWalkTurnSpeed (the kit's actor-walk recipe)
    body += opcodes.encode(0x25)                           # InitWalk -- make the follow synchronous
    body += opcodes.encode(0x24, int(target_uid))          # WalkTowardObject(target) -- ends ON CONTACT
    return body + opcodes.RETURN


def path_tag_body(legs, speed: int | None = None) -> bytes:
    """The body of a per-actor PATH tag: several straight walk legs in order (each self-blocks until
    arrival, exactly like :func:`walk_tag_body`) + a RETURN. Used for an authored ``path`` step AND for an
    auto-routed ``walk`` (the builder's A* detour compiles to a path -- same as the single-actor lane did)."""
    return b"".join(_cutscene.actor_walk(int(x), int(z), speed) for x, z in legs) + opcodes.RETURN


def teleport_tag_body(x: int, z: int) -> bytes:
    """The body of a per-actor TELEPORT tag: an instant ``MoveInstantXZY`` in the actor's own context
    (there is no targeted *Ex form) + a RETURN. Instant -- the sync caller unblocks immediately."""
    return _cutscene.actor_teleport(int(x), int(z)) + opcodes.RETURN


def face_player_tag_body(speed: int = 16) -> bytes:
    """The body of a per-actor FACE-PLAYER tag: ``TurnTowardObject(250)`` in the actor's own context (the
    250 sentinel resolves to the control character) + a RETURN."""
    return _cutscene.actor_face(PLAYER_UID, speed) + opcodes.RETURN


def build_body(steps, uid_by_name, txids, once_flag: int | None, *, flag_class=_region.GLOB_BOOL,
               warmup: int = _cutscene.DEFAULT_WARMUP, owns_control: bool = True,
               then_warp: int | None = None, say_flags: int = 128, ate_mode: int | None = None,
               reorder: int = _cutscene.REORDER_WAIT, tag_calls=None, join_tags=None,
               gate: bytes = b"", end_writes: bytes = b"", watchdog_flag: int | None = None) -> bytes:
    """The conductor function body, run from a standalone ``InitCode``-armed code entry.

    Shape: ``[Wait(reorder)] [DisableMove] [Wait(warmup)] <beats> [EnableMove]`` gated
    ``if (!once_flag) { ...; once_flag = 1 }`` when ``once_flag`` is set. The leading ``reorder`` Wait lets
    Main_Init reach its own ``EnableMove`` first so the conductor's ``DisableMove`` is the last control-setter
    (the lock sticks); the ``warmup`` Wait (after the lock, so the player can't wander) lets the field's entry
    fade settle AND lets the actor objects finish spawning before the conductor addresses them by uid.

    ``then_warp`` (a field id) ends the scene with a fade-to-black ``Field(then_warp)`` instead of restoring
    control (the warp sits OUTSIDE the once-gate so it always fires); the fade avoids the destination loading
    in the clear. With ``then_warp`` set, no ``EnableMove`` is emitted (the destination restores control).

    Control lock (the load-bearing part -- two in-game iterations to get right, 2026-06-28): a fixed warmup
    can't beat the field's entry control-grant, which re-enables control as the fade + scrolling-camera settle
    finish (the player could walk + dismiss the first window mid-settle). So under ``owns_control`` the conductor
    (1) ``DisableMove`` immediately, (2) ``wait_for_control_then_lock`` -- SPINS until the engine RE-grants
    control, then ``DisableMove`` again so the lock lands AFTER the grant -- and (3) ``compile_steps(relock=True)``
    re-locks before every beat as a backstop. The spin doubles as the actor-spawn settle (it runs ~until the
    grant, by which point the InitObject'd actors exist for the by-id ``*Ex`` ops)."""
    inner = opcodes.wait(int(reorder)) if reorder and reorder > 0 else b""
    if owns_control:
        if watchdog_flag is not None:                 # raise the scene-running flag FIRST: from here on the
            inner += _region.set_var(_region.MAP_BOOL, int(watchdog_flag), 1)   # watchdog re-locks ANY grant
        inner += opcodes.DISABLE_MOVE                 # disable, so the spin waits for the engine's RE-grant
        inner += wait_for_control_then_lock()         # ... spin to that grant, then re-lock (the lock that holds)
    elif warmup > 0:
        inner += opcodes.wait(int(warmup))            # no lock: still settle so the actors exist before the beats
    if ate_mode is not None:
        inner += opcodes.ate(int(ate_mode))           # compulsory-ATE HUD bracket (parity with narration)
    inner += compile_steps(steps, uid_by_name, txids, say_flags=say_flags, relock=owns_control,
                           tag_calls=tag_calls, join_tags=join_tags)
    if ate_mode is not None:
        inner += opcodes.ate(0)                       # disarm before control returns (close the bracket)
    if owns_control and watchdog_flag is not None:    # lower the flag BEFORE re-granting (on the warp path the
        inner += _region.set_var(_region.MAP_BOOL, int(watchdog_flag), 0)   # MAP array resets at field unload)
    if owns_control and then_warp is None:
        inner += opcodes.ENABLE_MOVE
    # the DIRECTOR advance (#13): set_scenario/set_flags bytes INSIDE the once-gate (before the once-flag
    # set) -- the story advances exactly once, only when the scene actually played. Empty -> byte-identical.
    inner += end_writes
    if once_flag is not None:
        inner += _region.set_var(flag_class, once_flag, 1)
        body = _region.if_block(_region.cond_not(flag_class, once_flag), inner)
    else:
        body = inner
    if then_warp is not None:
        body += _event.warp(int(then_warp), fade=True)
    # the DIRECTOR gate (#13): a story-gate prologue (cutscene.early_return_unless, stacked for AND) FIRST --
    # outside its beat the scene (once-flag, warp and all) simply doesn't run. Empty -> byte-identical.
    return gate + body + opcodes.RETURN


def inject_conductor(data, steps, uid_by_name, txids, *, once_flag: int | None = None,
                     flag_class=_region.GLOB_BOOL, warmup: int = _cutscene.DEFAULT_WARMUP,
                     owns_control: bool = True, then_warp: int | None = None, say_flags: int = 128,
                     ate_mode: int | None = None,
                     tag_calls=None, join_tags=None, reserve_party_band: bool = False,
                     gate: bytes = b"", end_writes: bytes = b"", watchdog_flag: int | None = None) -> bytes:
    """Seat the conductor as a single-function code entry and arm it via ``InitCode`` in Main_Init.
    Returns new .eb bytes. ``tag_calls`` (a dict ``step_index -> (uid, tag)``) maps each tag-kind step
    (walk/path/teleport/face_player) to its pre-generated per-actor tag; ``join_tags`` (``uid ->
    join_tag``) maps each PARALLEL-walking actor to its bare-RETURN join tag. ``then_warp`` ends the
    scene with a fade + ``Field()`` (parity with narration).

    Activation PINS to the Main_Init insert path -- never a Wait filler -- so the conductor always ticks
    BEFORE the watchdog and the player entry (see THE TICK-ORDER LAW on :func:`inject_watchdog`; a
    conductor created after the player has its grant-catch spin starved to the full CONTROL_POLL_CAP).
    Activate the shared watchdog FIRST, conductors after (insert is LIFO -> conductors end up above it).

    ``reserve_party_band``: on a VERBATIM fork the donor's last 9 slots are the playable characters, so the
    conductor INSERTS just below them (``object.seat_entry``) -- keeping the band as the top slots and not
    perturbing the actors it addresses (which seat below the band before it, so their uids stay valid)."""
    body = build_body(steps, uid_by_name, txids, once_flag, flag_class=flag_class, warmup=warmup,
                      owns_control=owns_control, then_warp=then_warp, say_flags=say_flags,
                      ate_mode=ate_mode, tag_calls=tag_calls, join_tags=join_tags,
                      gate=gate, end_writes=end_writes, watchdog_flag=watchdog_flag)
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
    out, slot = _object.seat_entry(data, entry, reserve_party_band=reserve_party_band)
    return edit.activate_block(out, opcodes.init_code(slot, 0))
