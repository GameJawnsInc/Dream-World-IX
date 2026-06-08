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
from ..eb.disasm import iter_code
from . import region as _region

PLAYER_UID = 250          # the controlled player's object UID (standard across FF9 fields)
FIRST_CLIMB_TAG = 17      # the real Treno player ladder funcs start at tag 17; one tag per ladder
RUNSCRIPT_LEVEL = 2       # the script level arg the real ladder uses for RunScriptSync
WAIT = 0x22
STARTSEQ = 0x43           # RunSharedScript -- launches "entry arg0 of this field" as a concurrent Seq
SETUP_JUMP = 0xE2         # SetupJump(x, y, z, arc): the climb's per-rung jump arcs (absolute dest)
ZONE_MARGIN = 150         # padding (world units) around the climb's span when auto-sizing a zone


def _s16(v: int) -> int:
    return v - 65536 if v >= 32768 else v


def climb_landings(climb_bytes: bytes) -> list:
    """Every ``SetupJump`` (X, Z) destination in a climb -- the absolute world points the player
    lands on while climbing (top, bottom, and any intermediate rungs)."""
    from ..eb.disasm import read_code
    out, pos = [], 0
    while pos < len(climb_bytes):
        try:
            ins, nxt = read_code(climb_bytes, pos)
        except Exception:
            break
        if ins.op == SETUP_JUMP and len(ins.args) >= 3:
            out.append((_s16(ins.args[0]), _s16(ins.args[2])))   # args = (jumpX, jumpY, jumpZ, steps)
        pos = nxt
    return out


def widen_zone_for_climb(zone, climb_bytes: bytes, margin: int = ZONE_MARGIN) -> list:
    """Return a 4-corner bbox quad covering BOTH the real entry zone AND every climb landing point.

    An imported real ladder's ``SetRegion`` zone only covers the side the player normally approaches
    from, so a FORK (where the player can end up at either end) gets no '!' prompt at the far end and
    can't climb back. Unioning the zone with the climb's ``SetupJump`` destinations (+ margin) makes
    the trigger span the whole ladder, so it's bidirectional. (Proven in-game: CPMP simple ladder.)"""
    pts = [tuple(p) for p in (zone or [])] + climb_landings(climb_bytes)
    if not pts:
        return zone
    xs = [p[0] for p in pts]
    zs = [p[1] for p in pts]
    x0, x1 = min(xs) - margin, max(xs) + margin
    z0, z1 = min(zs) - margin, max(zs) + margin
    return [[x0, z1], [x1, z1], [x1, z0], [x0, z0]]


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


def inject_ladder(data, zone, dest=None, *, climb_bytes: bytes | None = None,
                  sequences: dict | None = None, climb_tag: int = FIRST_CLIMB_TAG,
                  player_uid: int = PLAYER_UID, animation: int | None = None, activate: bool = True):
    """Inject a ladder: add a climb function (``climb_tag``) to the player entry + a ladder region
    (tread "!" prompt + action -> RunScriptSync the climb), and arm the region. Returns
    ``(new_bytes, region_slot)``. For multiple ladders pass a distinct ``climb_tag`` each.

    The climb is either FAITHFUL or EMULATED:
      * ``climb_bytes`` -- a real ladder's climb function extracted verbatim by
        ``eventscan.scan_ladders`` (exact jump arcs, perspective-correct). Grafted as-is; its internal
        jumps are function-relative so they survive the move. This is what ``import`` emits for a fork.
      * ``dest`` -- ``(x, z[, y])``; ``climb_body`` builds a teleport (+ optional gesture). The simple
        generic climb when you have no real ladder to copy.

    ``sequences`` (``{original_entry_index: entry_bytes}``, from ``scan_ladders``) are the concurrent
    helper entries the climb launches via STARTSEQ (e.g. the SetPitchAngle forward-lean). Each is
    appended at a free slot and the climb's STARTSEQ entry-args are remapped to those slots (a
    same-length 1-byte patch -- the climb stays byte-for-byte otherwise). Empty for simple ladders."""
    if climb_bytes is None and dest is None:
        raise ValueError("inject_ladder needs either climb_bytes (faithful) or dest (emulated)")
    body = bytearray(climb_bytes if climb_bytes is not None else climb_body(dest, animation=animation))
    if sequences:                                            # graft the STARTSEQ helper entries + remap
        ei2slot = {}
        for ei in sorted(sequences):
            slot = EbScript.from_bytes(data).first_free_slot()
            data = edit.append_entry(data, slot, sequences[ei])
            ei2slot[ei] = slot
        for ins in iter_code(bytes(body), 0, len(body)):
            if ins.op == STARTSEQ and ins.args and ins.args[0] in ei2slot:
                body[ins.off + 2] = ei2slot[ins.args[0]]     # STARTSEQ = 0x43, argflag, entry-arg
    body = bytes(body)
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    data = edit.add_function(data, pe, climb_tag, body)
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, ladder_region([tuple(p) for p in zone], climb_tag,
                                                       player_uid=player_uid))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot
