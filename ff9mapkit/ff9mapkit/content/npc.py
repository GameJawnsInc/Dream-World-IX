"""Inject an NPC into a field script, and move the player's spawn.

An NPC is built by cloning the field's player object (the entry that calls
``DefinePlayerCharacter``), neutralising it (NOP that opcode so it's an NPC, not a 2nd
player), repositioning it, optionally swapping its model + animations, and adding a
``_SpeakBTN`` (func tag 3) that opens a dialogue window. The clone is appended into a free
entry slot and spawned by overwriting a Main_Init ``Wait(2)`` filler with ``InitObject`` —
shift-free, so nothing else in the script moves.

Offsets are located **symbolically** (via the disassembler / byte patterns), not hardcoded,
so this works on any field whose player object follows the standard template — while
reproducing the proven hand-built results byte-for-byte.
"""

from __future__ import annotations

import struct

from ..binutils import pi16, pu16
from ..eb import EbScript, edit, opcodes
from ..eb.disasm import iter_code
from . import region as _region

# Character presets: (model, animset, {stand, walk, run, left, right} animation ids)
PRESETS = {
    "vivi": (8, 61, {"stand": 148, "walk": 571, "run": 419, "left": 917, "right": 918}),
    "zidane": (None, None, None),  # keep the cloned player's model/anims as-is
}
ANIM_ORDER = ("stand", "walk", "run", "left", "right")

DEFINE_PLAYER = 0x2C
SET_MODEL = 0x2F
SET_STAND_ANIM = 0x33


def _find_player_entry(eb: EbScript) -> int:
    for e in eb.entries:
        if e.empty:
            continue
        f0 = e.func_by_tag(0)
        if f0 and any(ins.op == DEFINE_PLAYER for ins in eb.instrs(f0)):
            return e.index
    raise ValueError("no player object (DefinePlayerCharacter) found in any entry")


def _func0_locations(eb: EbScript, entry):
    """Return offsets (relative to func0 body start) of the opcodes we patch."""
    f0 = entry.func_by_tag(0)
    base = f0.abs_start
    loc = {"dpc": None, "model": None, "animset": None, "stand": None}
    for ins in iter_code(eb.data, f0.abs_start, f0.abs_end):
        if ins.op == DEFINE_PLAYER and loc["dpc"] is None:
            loc["dpc"] = ins.off - base
        elif ins.op == SET_MODEL and loc["model"] is None:
            # SetModel: op, argFlag, model(2), animset(1) -> model@+2, animset@+4
            loc["model"] = ins.off - base + 2
            loc["animset"] = ins.off - base + 4
        elif ins.op == SET_STAND_ANIM and loc["stand"] is None:
            loc["stand"] = ins.off - base + 2   # first anim-setter arg; 4 more follow every 4 bytes
    return f0, base, loc


def _find_var_const(body: bytes, var_index: int) -> int:
    """Offset (within body) of the 2-byte const a ``SetVar D9(var_index) = const`` assigns.

    Pattern: 05 D9 <var_index> 7D <lo> <hi> 2C 7F -> the const is the 2 bytes after 0x7D.
    """
    pat = bytes([0x05, 0xD9, var_index, 0x7D])
    i = body.find(pat)
    if i < 0:
        raise ValueError(f"no SetVar D9({var_index}) const found")
    return i + len(pat)


def inject_npc(data, x: int, z: int, *, preset: str | None = None, model=None, animset=None,
               anims=None, talk_text_id: int = 62, slot: int | None = None,
               spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0,
               gate_flag: int | None = None, gate_require_set: bool = True,
               intro: bytes | None = None) -> bytes:
    """Inject an NPC at world (x, z). Returns new .eb bytes.

    ``gate_flag`` (a GlobBool index) makes the NPC conditional: its Init returns early -- so it never
    creates its model and is absent/non-interactable -- unless the flag is in the required state
    (``gate_require_set`` True = appears when the flag is SET, False = when CLEAR). This is the
    standard FF9 way to show/hide an NPC by story state.

    ``intro`` (bytes) is an ACTOR cutscene's gated choreography block (from
    :func:`ff9mapkit.content.cutscene.build_choreography`), spliced into this NPC's Init just before
    its RETURN so it runs in the NPC's own object context (``gExec`` == this NPC) after CreateObject."""
    if preset is not None:
        model, animset, anims = PRESETS[preset]

    eb = EbScript.from_bytes(data)
    pe = _find_player_entry(eb)
    entry = eb.entry(pe)
    f0, base0, loc = _func0_locations(eb, entry)
    f1 = entry.func_by_tag(1)
    if f1 is None:
        raise ValueError("player entry has no Loop function (tag 1)")

    body0 = bytearray(data[f0.abs_start:f0.abs_end])
    body1 = bytes(data[f1.abs_start:f1.abs_end])

    # 1) neutralise DefinePlayerCharacter
    body0[loc["dpc"]] = opcodes.NOP[0]
    # 2) reposition (the CreateObject reads D9(0)=x, D9(4)=z set by SetVar consts)
    xo, zo = _find_var_const(body0, 0), _find_var_const(body0, 4)
    body0[xo:xo + 2] = pi16(x)
    body0[zo:zo + 2] = pi16(z)
    # 3) optional model + animset
    if model is not None:
        body0[loc["model"]:loc["model"] + 2] = pu16(model)
    if animset is not None:
        body0[loc["animset"]] = animset & 0xFF
    # 4) optional animation ids (5 consecutive setters from SetStandAnimation)
    if anims:
        for k, name in enumerate(ANIM_ORDER):
            if name in anims:
                o = loc["stand"] + 4 * k
                body0[o:o + 2] = pu16(anims[name])

    # 4b) optional story-flag gate: prepend `ifnot (flag) return` to the Init so a gated-out NPC
    # returns before CreateObject -> no model, absent. (body0 grows; the func table is rebuilt from
    # body lengths below, so fpos stays correct.)
    if gate_flag is not None:
        body0 = bytearray(_region.flag_gate(_region.GLOB_BOOL, gate_flag,
                                            require_set=gate_require_set)) + body0

    # 4c) optional ACTOR-cutscene choreography: splice the gated block into the Init right before its
    # trailing RETURN, so it runs in THIS NPC's context (gExec == the NPC) after CreateObject. The block
    # self-gates `if (!once) {...}` so it plays once. The func table is rebuilt from body lengths below,
    # so growing body0 is safe.
    if intro:
        if not body0 or body0[-1] != opcodes.RETURN[0]:
            raise ValueError("NPC Init does not end with RETURN; cannot splice cutscene choreography")
        body0 = body0[:-1] + bytearray(intro) + body0[-1:]

    # 5) _SpeakBTN (func tag 3): WindowSync(1, 128, text) ; return
    f2 = opcodes.window_sync(1, 128, talk_text_id) + opcodes.RETURN

    # 6) assemble the new 3-function entry (type cloned from the player entry)
    table_len = 3 * 4
    nf0, nf1, nf2 = table_len, table_len + len(body0), table_len + len(body0) + len(body1)
    table = struct.pack("<HH", 0, nf0) + struct.pack("<HH", 1, nf1) + struct.pack("<HH", 3, nf2)
    entry_bytes = bytes([entry.type, 3]) + table + bytes(body0) + body1 + f2

    # 7) append + spawn (shift-free): overwrite a Main_Init Wait(n) with InitObject(slot,0)
    if slot is None:
        slot = eb.first_free_slot()
    out = edit.append_entry(data, slot, entry_bytes)
    out = edit.activate(out, opcodes.init_object(slot, 0), spawn_wait_n=spawn_wait_n,
                        spawn_wait_occurrence=spawn_wait_occurrence)
    return out


def set_player_spawn(data, x: int, z: int, *, entry_index: int | None = None) -> bytes:
    """Move the player's spawn position (the SetVar D9(0)/D9(4) consts in its Init func)."""
    eb = EbScript.from_bytes(data)
    pe = entry_index if entry_index is not None else _find_player_entry(eb)
    f0 = eb.entry(pe).func_by_tag(0)
    body = bytearray(data[f0.abs_start:f0.abs_end])
    xo, zo = _find_var_const(body, 0), _find_var_const(body, 4)
    abs_x = f0.abs_start + xo
    abs_z = f0.abs_start + zo
    return edit.patch_bytes(edit.patch_bytes(data, abs_x, pi16(x)), abs_z, pi16(z))
