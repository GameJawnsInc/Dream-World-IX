"""Ladder primitive -- a region the player climbs, replicating FF9's REAL ladder mechanism.

Decoded byte-for-byte from Treno/Residence (the real game; entry 15 = the ladder region, entry 19 =
the player):

  - tread  (tag 2): ``ifnot(usercontrol) return ; Bubble(1)``            -> the floating "!" prompt
  - action (tag 3): ``ifnot(usercontrol) return ; DisableMove ;
                     RunScriptSync(2, 250, <climb_tag>) ; EnableMove``    -> run the PLAYER's climb
  - the player's climb function (``climb_tag``): runs in the player's OWN context (UID 250), so its
    moves move the PLAYER; ``RunScriptSync`` waits for it.

Why this shape (the hard-won truth): the controlled player's script loop is NOT stepped while
``usercontrol == 1``, so a region -> flag -> player-loop scheme can't drive a climb during free
walking. The region must call the player's climb DIRECTLY via ``RunScriptSync`` (which is exactly what
the real game does). The real climb is bespoke per-ladder jump arcs (hard-coded coords) -- not
generalizable -- so the kit's climb is a simple teleport to the destination (+ an optional climb
gesture). The TRIGGER is faithful; the climb body is simplified.
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region

PLAYER_UID = 250          # the controlled player's object UID (standard across FF9 fields)
FIRST_CLIMB_TAG = 17      # the real Treno player ladder funcs start at tag 17; one tag per ladder
RUNSCRIPT_LEVEL = 2       # the script level arg the real ladder uses for RunScriptSync
WAIT = 0x22


def find_player_entry(eb: EbScript) -> int:
    """Index of the player entry -- the one running DefinePlayerCharacter (opcode 0x2C)."""
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == 0x2C:
                    return e.index
    raise ValueError("no player entry (DefinePlayerCharacter) found -- can't attach a climb function")


def climb_body(dest, *, animation: int | None = None, anim_hold: int = 40) -> bytes:
    """The player's climb function body: an optional climb gesture, then teleport to ``dest``
    ``(x, z)`` or ``(x, z, y)`` + re-enable walkmesh pathing. Runs in the player's context (via
    RunScriptSync), so ``MoveInstantXZY`` moves the player."""
    x, z = int(dest[0]), int(dest[1])
    y = int(dest[2]) if len(dest) > 2 else 0
    body = b""
    if animation is not None:
        body += opcodes.run_animation(int(animation)) + opcodes.encode(WAIT, int(anim_hold))
    body += opcodes.move_instant_xzy(x, z, y) + opcodes.set_pathing(1) + opcodes.RETURN
    return body


def ladder_region(zone, climb_tag: int, *, player_uid: int = PLAYER_UID) -> bytes:
    """A type-1 region entry: Init ``SetRegion(zone)`` / tread ``Bubble(1)`` / action ``DisableMove;
    RunScriptSync(player climb); EnableMove`` -- the real FF9 ladder trigger."""
    init = _region.set_region(zone) + opcodes.RETURN
    tread = _region.MOVEMENT_GATE + opcodes.bubble(1) + opcodes.RETURN
    action = (_region.MOVEMENT_GATE + opcodes.DISABLE_MOVE
              + opcodes.run_script_sync(RUNSCRIPT_LEVEL, player_uid, climb_tag)
              + opcodes.ENABLE_MOVE + opcodes.RETURN)
    funcs = [(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)]
    table = b""
    pos = len(funcs) * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def inject_ladder(data, zone, dest, *, climb_tag: int = FIRST_CLIMB_TAG, player_uid: int = PLAYER_UID,
                  animation: int | None = None, activate: bool = True):
    """Inject a ladder: add a climb function (``climb_tag``) to the player entry + a ladder region
    (tread "!" prompt + action -> RunScriptSync the climb), and arm the region. Returns
    ``(new_bytes, region_slot)``. For multiple ladders pass a distinct ``climb_tag`` each."""
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    data = edit.add_function(data, pe, climb_tag, climb_body(dest, animation=animation))
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, ladder_region([tuple(p) for p in zone], climb_tag,
                                                       player_uid=player_uid))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot
