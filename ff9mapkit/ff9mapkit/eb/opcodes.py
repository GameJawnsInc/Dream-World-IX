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
ENABLE_MOVE = bytes([0x2E])     # EnableMove (0 args)
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
