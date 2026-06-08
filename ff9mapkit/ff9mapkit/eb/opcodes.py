"""Encoders for the event-script opcodes the kit emits.

A single :func:`encode` builds the exact byte sequence for an opcode + immediate operands,
following the engine's reader rules:
  * extended opcodes (>= 0x100) get a leading ``0xFF`` page byte,
  * opcodes >= 0x10 that take operands carry a 1-byte ``argFlag`` bitmask (0 = all immediate),
  * each immediate is little-endian, width per :func:`~ff9mapkit.eb.disasm.argsize`,
  * a set ``argFlag`` bit means that operand is a pre-encoded expression-token blob (``bytes``).

The named helpers below cover everything the content injectors produce. Each was checked
against the exact byte strings the original tools emitted (e.g. ``run_sound_code(0, 9)`` ==
``C5 00 00 00 09 00``; ``set_control_direction(-1, -1)`` == ``67 00 FF FF``).
"""

from __future__ import annotations

from ._optables import OP_ARG_COUNT, OP_NAMES
from .disasm import argsize

_NAME_TO_OP = {v: k for k, v in OP_NAMES.items()}


def resolve(op) -> int:
    """Accept an int opcode or a mnemonic string; return the int opcode."""
    if isinstance(op, str):
        if op not in _NAME_TO_OP:
            raise KeyError(f"unknown opcode mnemonic {op!r}")
        return _NAME_TO_OP[op]
    return op


def _imm(v: int, size: int) -> bytes:
    """Little-endian, two's-complement for negatives, masked to ``size`` bytes."""
    if size <= 0:
        return b""
    return (v & ((1 << (8 * size)) - 1)).to_bytes(size, "little")


def encode(op, *args, arg_flags: int = 0) -> bytes:
    """Encode one instruction. ``args`` are ints (immediates) or, for set arg_flags bits, bytes."""
    op = resolve(op)
    if op < len(OP_ARG_COUNT) and OP_ARG_COUNT[op] < 0:
        raise ValueError(f"opcode 0x{op:02X} has a variable operand count; encode it explicitly")
    head = bytes([0xFF, op & 0xFF]) if op >= 0x100 else bytes([op])
    argc = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
    body = bytearray()
    if op >= 0x10 and argc != 0:
        body.append(arg_flags & 0xFF)
    for i, a in enumerate(args):
        if arg_flags & (1 << i):
            body += bytes(a)               # pre-encoded expression operand
        else:
            body += _imm(int(a), argsize(op, i))
    return head + bytes(body)


# --- init/dispatch (entry activators) ---
def init_code(slot: int, arg: int = 0) -> bytes:   # 0x07
    return encode(0x07, slot, arg)


def init_region(slot: int, arg: int = 0) -> bytes:  # 0x08
    return encode(0x08, slot, arg)


def run_script_sync(level: int, uid: int, tag: int) -> bytes:   # 0x14 (REQEW) argsize [1,1,1]
    """RunScriptSync(level, uid, tag): run function ``tag`` on the object with this UID and WAIT for it
    to return. The FF9 ladder idiom: a region calls ``RunScriptSync(2, 250, <climb_tag>)`` to run the
    PLAYER's (UID 250) climb function in the player's own context (so its moves move the player),
    synchronously. Decoded from Treno/Residence's real ladder."""
    return encode(0x14, level, uid, tag)


def bubble(state: int) -> bytes:                               # 0x68 (BUBBLE) argsize [1]
    """Bubble(state): show(1)/hide(0) the floating "!" action-available prompt over the player. A
    ladder/sign region shows it on tread so the player knows to press the action button."""
    return encode(0x68, state)


def init_object(slot: int, arg: int = 0) -> bytes:  # 0x09
    return encode(0x09, slot, arg)


# --- flow / misc ---
def wait(n: int) -> bytes:                          # 0x22
    return encode(0x22, n)


RETURN = bytes([0x04])          # function return (level-0 return drives ExitBattleEnd)
NOP = bytes([0x00])
ENABLE_MOVE = bytes([0x2E])     # EnableMove (0 args) -- give the player control
DISABLE_MOVE = bytes([0x2D])    # DisableMove (0 args) -- lock control (cutscenes)
DEFINE_PLAYER_CHARACTER = bytes([0x2C])


# --- objects / models / animation ---
def set_model(model: int, animset: int) -> bytes:   # 0x2F  argsize [2,1]
    return encode(0x2F, model, animset)


def create_object(x: int, z: int) -> bytes:         # 0x1D  argsize [2,2]
    return encode(0x1D, x, z)


def set_stand_animation(anim: int) -> bytes:        # 0x33  argsize [2]
    return encode(0x33, anim)


def set_control_direction(x: int, y: int) -> bytes:  # 0x67 (TWIST)
    return encode(0x67, x, y)


# --- actor movement / animation / turning (cutscene "v2" steps) ---
# These all act on the EXECUTING object (gExec) -- so they're emitted into a specific NPC's own
# function (its Init choreography), where gExec == that NPC. Grounded in the engine's DoEventCode
# handlers + real cutscene scripts (e.g. Gargan/Kuja walk functions: SetWalkSpeed -> RunAnimation ->
# WaitAnimation -> InitWalk -> Walk).
def init_walk() -> bytes:                            # 0x25 (CLRDIST) 0 args
    """InitWalk(): make the following Walk synchronous (the canonical idiom; Walk also self-blocks)."""
    return encode(0x25)


def walk(x: int, z: int) -> bytes:                   # 0x23 (MOVE) argsize [2, 2]
    """Walk(x, z): walk the executing actor to world (x, z); blocks (stay()) until it arrives."""
    return encode(0x23, x, z)


def set_walk_speed(speed: int) -> bytes:             # 0x26 (MSPEED) argsize [1]
    """SetWalkSpeed(speed): set the actor's walk speed (units/frame; vanilla cutscenes use ~15)."""
    return encode(0x26, speed)


def set_walk_turn_speed(speed: int) -> bytes:        # 0x55 (MROT) argsize [1]
    """SetWalkTurnSpeed(speed): how fast the actor rotates toward its target WHILE walking (omega;
    default 16 ~= 11 deg/frame). Cranking it high (255 ~= 179 deg/frame) shrinks the turn-while-walk
    arc to ~nothing, so a Walk to a point BEHIND the actor turns and goes straight instead of orbiting
    it forever -- without the animated-turn path (TimedTurn/TurnTowardPosition) that can hang at 180."""
    return encode(0x55, speed)


def move_instant_xzy(x: int, z: int, y: int = 0) -> bytes:   # 0xA1 (POS3) argsize [2, 2, 2]
    """MoveInstantXZY: teleport the actor to world (x, z) at height y -- no walk animation.

    GOTCHA (verified from source): the engine reads ``destX=arg1; destZ=-arg2; destY=arg3`` then calls
    ``SetActorPosition(po, destX, destZ, destY)`` = ``po.x=destX; po.y=destZ; po.z=destY``. So despite
    the "XZY" name the bytecode args are (worldX, -worldY, worldZ): arg2 is the NEGATED height, arg3 is
    the world depth Z (NOT arg2). So encode (x, -y, z). Use to place an actor before a walk-in."""
    return encode(0xA1, x, -y, z)


def run_animation(anim: int) -> bytes:               # 0x40 (ANIM) argsize [2]
    """RunAnimation(anim): play an animation on the executing actor (async; pair WaitAnimation)."""
    return encode(0x40, anim)


def wait_animation() -> bytes:                       # 0x41 (WAITANIM) 0 args
    """WaitAnimation(): block until the executing actor's current animation has ended."""
    return encode(0x41)


def stop_animation() -> bytes:                       # 0x42 (ENDANIM) 0 args
    """StopAnimation(): stop the current animation -> resets to idle and CLEARS the anim flags
    (afExec/afLower/afFreeze). Needed before a Walk: the engine only swaps idle->walk when moving if
    those flags are clear (ProcessEvents), and a player-cloned NPC's idle can leave afExec set, so it
    glides in the idle pose. StopAnimation first => the auto walk-anim swap fires."""
    return encode(0x42)


def turn_instant(angle: int) -> bytes:               # 0x36 (DIRE) argsize [1]
    """TurnInstant(angle): face an angle instantly (0=south, 64=west, 128=north, 192=east)."""
    return encode(0x36, angle)


def timed_turn(angle: int, speed: int = 16) -> bytes:        # 0x56 (TURN) argsize [1, 1]
    """TimedTurn(angle, speed): face an angle, animated (0=S,64=W,128=N,192=E; pair WaitTurn)."""
    return encode(0x56, angle, speed)


def turn_toward_object(uid: int, speed: int = 16) -> bytes:  # 0x51 (TURNA) argsize [1, 1]
    """TurnTowardObject(uid, speed): turn to face an object by UID (250=player), animated; pair WaitTurn."""
    return encode(0x51, uid, speed)


def turn_toward_position(x: int, z: int) -> bytes:   # 0x9B (TURNTO) argsize [2, 2]
    """TurnTowardPosition(x, z): turn the actor IN PLACE to face world (x, z), animated (uses the
    actor's turn speed). No Z-negation (uses posZ directly, like Walk). Pair with WaitTurn. Emit this
    before a Walk so the actor faces its destination first -- otherwise it ARCS toward a target behind
    it (moves at full speed while turning only ~omega/frame) and orbits a nearby point forever."""
    return encode(0x9B, x, z)


def wait_turn() -> bytes:                            # 0x50 (WAITTURN) 0 args
    """WaitTurn(): block until the executing actor's (animated) turn has finished."""
    return encode(0x50)


def set_pathing(active: int) -> bytes:               # 0xA8 (BGI) argsize [1]
    """SetPathing(active): enable(1)/disable(0) the actor's walkmesh collision. MoveInstantXZY
    DISABLES it (so a teleport off the mesh doesn't snap back); call SetPathing(1) after to re-enable
    it before walking (the real walk-in pattern: MoveInstantXZY -> SetPathing(1) -> ... -> Walk)."""
    return encode(0xA8, active)


def setup_jump(x: int, z: int, y: int, steps: int = 6) -> bytes:   # 0xE2 (SETVY3) argsize [2,2,2,1]
    """SetupJump(x, z, y, steps): set the destination + duration for a following Jump. Same arg
    convention as MoveInstantXZY -- (worldX, -worldY, worldZ) -- so encode (x, -y, z). `steps` is the
    jump duration in frames (0 -> 8). `y` is the world HEIGHT (up = positive; a ladder top is y>0).
    Pair with Jump(); the engine interpolates a parabolic arc from the actor's current pos to here."""
    return encode(0xE2, x, -y, z, steps)


def jump() -> bytes:                                 # 0xDC (JUMP3) 0 args
    """Jump(): perform the jump set up by SetupJump -- synchronous (blocks `steps` frames) and moves
    the actor along a parabolic arc to the SetupJump destination (incl. the height y)."""
    return encode(0xDC)


def set_jump_animation(anim: int, a: int = 2, b: int = 6) -> bytes:   # 0x94 (SETJUMP) argsize [2,1,1]
    """SetJumpAnimation(anim, a, b): set the animation played during the next Jump arc (e.g. a ladder
    mount/dismount climb-grab). Verified vs field 706's vine: ``94 00 BF29 02 06`` = (10687, 2, 6)."""
    return encode(0x94, anim, a, b)


def run_jump_animation() -> bytes:                   # 0x9C (RUNJUMP) 0 args
    """RunJumpAnimation(): play the animation set by SetJumpAnimation (paired with a Jump)."""
    return encode(0x9C)


def run_land_animation() -> bytes:                   # 0x9D (RUNLAND) 0 args
    """RunLandAnimation(): play the landing animation after a Jump arc."""
    return encode(0x9D)


def set_animation_flags(a: int, b: int) -> bytes:    # 0x3F (ANIMFLAG) argsize [1,1]
    """SetAnimationFlags(a, b): configure the actor's animation blending. A ladder climb sets (1,0) at
    mount and restores (0,0) on dismount (field 706). Verified: ``3F 00 01 00`` = (1, 0)."""
    return encode(0x3F, a, b)


def set_animation_in_out(a: int, b: int) -> bytes:   # 0x3D (ANIMINOUT) argsize [1,1]
    """SetAnimationInOut(a, b): set the in/out frame window of the current animation. Verified vs
    field 706: ``3D 00 00 00`` = (0, 0)."""
    return encode(0x3D, a, b)


def add_character_attribute(flag: int) -> bytes:     # 0xCC (ADDATTR) argsize [2]
    """AddCharacterAttribute(flag): set a character attribute bit. Flag 4 = the LADDER flag -- tells
    the engine the actor is on a ladder so it isn't snapped to the floor during a height climb."""
    return encode(0xCC, flag)


def remove_character_attribute(flag: int) -> bytes:  # 0xCD (DELATTR) argsize [2]
    """RemoveCharacterAttribute(flag): clear a character attribute bit (e.g. 4 = ladder, on dismount)."""
    return encode(0xCD, flag)


def disable_move() -> bytes:                         # 0x2D (UCOFF) 0 args
    """DisableMove(): lock the player's movement control (cutscene start)."""
    return DISABLE_MOVE


def enable_move() -> bytes:                          # 0x2E (UCON) 0 args
    """EnableMove(): restore the player's movement control (cutscene end)."""
    return ENABLE_MOVE


# --- text windows ---
def window_sync(win: int, flags: int, text_id: int) -> bytes:   # 0x1F
    return encode(0x1F, win, flags, text_id)


def window_async(win: int, flags: int, text_id: int) -> bytes:  # 0x20
    return encode(0x20, win, flags, text_id)


# --- audio ---
def run_sound_code(sound_code: int, sound_id: int) -> bytes:    # 0xC5  argsize [2,2]
    return encode(0xC5, sound_code, sound_id)


# --- visual ---
def fade_filter(a: int, b: int, c: int, d: int, e: int, f: int) -> bytes:  # 0xEC  6x1
    return encode(0xEC, a, b, c, d, e, f)


# --- battles ---
def set_random_battles(slot: int, b1: int, b2: int, b3: int, b4: int) -> bytes:  # 0x3C [1,2,2,2,2]
    return encode(0x3C, slot, b1, b2, b3, b4)


def set_random_battle_frequency(freq: int) -> bytes:   # 0x57 [1]
    return encode(0x57, freq)


# --- field camera (multi-camera) ---
def run_script_sync(script_level: int, uid: int, func_tag: int) -> bytes:   # 0x14 (REQEW) [1,1,1]
    """RunScriptSync(level, uid, tag): run object ``uid``'s function ``tag`` and WAIT until it returns
    (the engine's REQEW). Targets by UID (GetObjUID). A director uses this to drive an NPC's
    choreography function -- which then runs while the NPC is 'running' (so its animations advance,
    unlike code spliced into the NPC's Init). ``level`` is the script level (real cutscenes use 2)."""
    return encode(0x14, script_level, uid, func_tag)


def set_field_camera(cam_id: int) -> bytes:            # 0x7E (SETCAM) [1]
    """SetFieldCamera(cam_id): switch the active background camera (engine SetCurrentCameraIndex)."""
    return encode(0x7E, cam_id)


def enable_dialog_choices(avail_mask: int, default: int = 0) -> bytes:   # 0x7C (CHOOSEPARAM) [2,1]
    """EnableDialogChoices(avail_mask, default): configure the NEXT choice window. ``avail_mask`` is the
    availability bitmask (bit i = row i selectable, LSB-first; -1/0xFFFF = all on) -> ETb.sChooseMask;
    ``default`` is the initially-highlighted row. The engine only APPLIES the mask if the choice text
    carries a ``[PCHM]`` tag (``[PCHC]`` passes default/cancel but ignores the mask). Grounded in the
    field-100 ATE menu: ``EnableDialogChoices( VAR_GenInt16_241 | 32768, 0 )``. See content.choice."""
    return encode(0x7C, avail_mask & 0xFFFF, default)


def enable_dialog_choices_var(mask_expr: bytes, default: int = 0) -> bytes:   # 0x7C, arg0 = expression
    """EnableDialogChoices where the mask is a RUNTIME EXPRESSION (e.g. a scratch var built from story
    flags) rather than a literal. ``mask_expr`` is a bare RPN token blob terminated by ``0x7F`` (see
    ``region.var_expr``); the gArgFlag bit for arg0 is set so the engine evaluates it (getv->CalcExpr).
    Real-field verified (Dali/Storage 407: ``7c 01 d9 21 7d 04 00 26 7f 00`` = ``EnableDialogChoices(VAR | 4, 0)``)."""
    return encode(0x7C, mask_expr, default, arg_flags=0b01)


def terminate_entry(entry: int = 255) -> bytes:        # 0x1C (KILL) [1]
    """TerminateEntry(entry): stop an entry's code (255 = This). Used to deactivate a switch zone."""
    return encode(0x1C, entry)


# --- field transitions (a ladder top that exits to another field / the world map) ---
# NOTE: there is deliberately NO preload_field() helper. FF9's PreloadField is opcode 0xFD (HINT),
# "ignored in the non-PSX versions" -- a no-op on Steam, so a Field() alone warps. Do NOT encode it as
# 0x2A: that opcode is **Battle**, and emitting it before a Field warp literally starts a battle using
# the field id as the battle-scene id (invalid id -> InitBattleScene null-ref crash; valid id -> a real
# battle). This bit us once; keep the warp to just Field().
def field(target: int) -> bytes:                          # 0x2B (MAPJUMP) argsize [2]
    """Field(target): transition to field ``target`` (arriving via the entrance var D8:2, set just
    before). Verified vs field 70's warp: ``2B 00 <id>``."""
    return encode(0x2B, target)


def world_map(entry: int) -> bytes:                       # 0xB6 (WMAPJUMP) argsize [2]
    """WorldMap(entry): transition to the world map at ``entry`` -- a world-exit vine's top boundary
    (e.g. Gizamaluke's vine to the world map). Real fields branch the entry by story-progress; this
    emits the simple single-target form."""
    return encode(0xB6, entry)


# --- inventory (events / treasure) ---
def add_item(item_id: int, count: int = 1) -> bytes:   # 0x48 (ITEM) argsize [2, 1]
    """AddItem(item_id, count): add an item to the party inventory (real-chest opcode)."""
    return encode(0x48, item_id, count)


def set_text_variable(slot: int, value: int) -> bytes:   # 0x66 (MESVALUE) argsize [1, 2]
    """SetTextVariable(slot, value): set dialogue text-variable ``slot`` -> ``value`` (ETb.gMesValue).
    A ``[ITEM=slot]`` tag in the next window renders that value's item name, ``[VAR=slot]`` its number.
    The chest "Received [ITEM=0]!" pattern uses SetTextVariable(0, item) (real-field verified, field 407:
    ``66 00 00 ec 00`` = SetTextVariable(0, 236))."""
    return encode(0x66, slot, value)


def add_gil(amount: int) -> bytes:                     # 0xCE (GILADD) argsize [3]
    """AddGil(amount): add gil to the party purse. ``amount`` is an UNSIGNED 24-bit value -- the engine
    does ``party.gil += amount`` (caps at 9999999), so a negative here wraps to a huge add. To SUBTRACT
    gil use :func:`remove_gil`."""
    return encode(0xCE, amount)


def remove_gil(amount: int) -> bytes:                  # 0xCF (GILDELETE) argsize [3]
    """RemoveGil(amount): subtract gil from the party purse (engine ``party.gil -= amount``, floored at
    0). ``amount`` is a POSITIVE 24-bit value."""
    return encode(0xCF, amount)
