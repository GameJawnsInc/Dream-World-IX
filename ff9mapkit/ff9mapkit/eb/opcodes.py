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
    """MoveInstantXZY(x, z, y): teleport the actor to world (x, z, y) -- no walk animation.

    GOTCHA: the engine reads ``destZ = -getv2()`` (POS3 negates Z; CreateObject/Walk do NOT), so to
    land at world z we encode -z. Use to place an actor off-screen before a walk-in."""
    return encode(0xA1, x, -z, y)


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
def set_field_camera(cam_id: int) -> bytes:            # 0x7E (SETCAM) [1]
    """SetFieldCamera(cam_id): switch the active background camera (engine SetCurrentCameraIndex)."""
    return encode(0x7E, cam_id)


def terminate_entry(entry: int = 255) -> bytes:        # 0x1C (KILL) [1]
    """TerminateEntry(entry): stop an entry's code (255 = This). Used to deactivate a switch zone."""
    return encode(0x1C, entry)


# --- inventory (events / treasure) ---
def add_item(item_id: int, count: int = 1) -> bytes:   # 0x48 (ITEM) argsize [2, 1]
    """AddItem(item_id, count): add an item to the party inventory (real-chest opcode)."""
    return encode(0x48, item_id, count)


def add_gil(amount: int) -> bytes:                     # 0xCE (GETGIL) argsize [3]
    """AddGil(amount): add gil to the party purse."""
    return encode(0xCE, amount)
