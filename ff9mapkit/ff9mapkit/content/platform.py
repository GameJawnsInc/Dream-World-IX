"""Carry-platform primitive -- a rideable lift/elevator that physically CARRIES the player within one
field (no Field() re-entry warp), recreating FF9's Pandemonium-elevator mechanism.

Decoded from Pandemonium/Elevator (fields 2712 `pd_elv` / 2713 `pd_evd`). The real ride is a fully
SCRIPTED, control-locked carry -- NOT an engine attach (there is ZERO MoveTileLoop/AttachTile/SIM in
either field). The boarding region disables control and `RunScriptSync`s a function grafted onto the
PLAYER object (UID 250); that function moves the player frame-by-frame with `MoveInstantXZY` until he
reaches the destination height, then control returns:

  - region (tag 2 tread "!" / tag 3 action): ``DisableMove ; RunScriptSync(2, 250, ride_tag) ; EnableMove``
  - the ride func (``ride_tag``, on the PLAYER): a per-frame loop
      ``{ scratch = selfY +/- step ; MoveInstantXZY(line_x, scratch, line_z) ; Wait(1) ;
         while (selfY hasn't reached arrive) }`` then SetPathing(1) (or the optional fade+Field tail).

This is the kit's navigable ladder climb (:func:`ladder.navigable_climb_body`) MINUS the d-pad input
and the mount/dismount arcs: instead of reading the held direction each frame, the carry advances a
FIXED step toward the destination, so it is auto-driven and always terminates (a linear ride of
~``duration`` frames). Every byte is emitted by the same proven primitives the climb uses (the ``_Asm``
label assembler, the ``0xA1`` expression-arg snap, the ``line()`` interpolation, the ladder flag).

selfY = -worldY (op78 field 1): a HIGHER physical position is a MORE-NEGATIVE selfY, so a lift going UP
(arrive above board) advances selfY in the NEGATIVE direction. The carry derives the step sign + the
arrival test from ``arrive.y`` vs ``board.y`` (they MUST differ -- a zero-height carry never moves).

v1 emits the CARRY only; the visible platform is the human's (paint a ride surface, or drive a placed
GEO model in lockstep -- a follow-up). docs: project memory `project-ff9-moving-platforms-elevators`.
"""
from __future__ import annotations

import math
import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region
from .ladder import _Asm, _arg, _const, _selfv, _stmt, F_Y, LADDER_FLAG, find_player_entry, square_zone

PLAYER_UID = 250          # the controlled player's runtime UID (standard across FF9 fields)
FIRST_PLATFORM_TAG = 56   # player ride funcs start here -- clear of ladder (17+) / jump (40+) climb tags,
                          #   below the object-carry player band (64+); one tag per platform
RUNSCRIPT_LEVEL = 2       # the script level RunScriptSync uses (matches the real ladder/jump triggers)
PLATFORM_SCRATCH = 3      # MAP.I16[3]: this frame's stepped selfY target (transient per-field)
PLATFORM_START = 4        # MAP.I16[4]: the captured boarding selfY (the height the player rides FROM)
PLATFORM_START_X = 5      # MAP.I16[5]: the captured boarding world-X
PLATFORM_START_Z = 6      # MAP.I16[6]: the captured boarding world-Z
DEFAULT_DURATION = 32     # ride frames (for the relative `rise` mode -- linear, always terminates)
DEFAULT_SPEED = 30        # world-units/frame for the absolute `land` mode (ride duration = distance/speed)


def _scratch() -> bytes:
    """This frame's stepped selfY target (MAP.I16[PLATFORM_SCRATCH]); transient per-field."""
    return _region._push_var(_region.MAP_INT16, PLATFORM_SCRATCH)


def _scratch_start() -> bytes:
    """The boarding selfY var (MAP.I16[PLATFORM_START]); captured from the player at ride start."""
    return _region._push_var(_region.MAP_INT16, PLATFORM_START)


def _scratch_x() -> bytes:
    """The boarding world-X var (MAP.I16[PLATFORM_START_X]); captured at ride start (`land` mode)."""
    return _region._push_var(_region.MAP_INT16, PLATFORM_START_X)


def _scratch_z() -> bytes:
    """The boarding world-Z var (MAP.I16[PLATFORM_START_Z]); captured at ride start (`land` mode)."""
    return _region._push_var(_region.MAP_INT16, PLATFORM_START_Z)


def _carry_land_body(land, *, speed: int, animation: int | None,
                     warp_to: int | None, warp_entrance: int) -> bytes:
    """Ride the player from WHEREVER he boards to the absolute landing point ``land`` = ``(x, z, y)``, at
    ``speed`` world-units/frame, then re-attach to the walkmesh -- landing cleanly on the floor AT
    ``land`` (no end-of-ride floor-snap warp). RELATIVE start (captures the boarding position, no
    teleport-in) + ABSOLUTE end (the landing is a real floor). ``land`` must be ABOVE the boarding point
    (the elevator rides UP -> selfY decreases). Used for inter-field-style lifts where you board at the
    bottom and step off onto a higher floor elsewhere in the room."""
    lx, lz = int(land[0]), int(land[1])
    ly = int(land[2]) if len(land) > 2 else 0
    lsy = -ly                                          # landing selfY (= -worldY)
    speed = max(1, int(speed))

    def selfx(): return _selfv(0)
    def selfz(): return _selfv(2)
    def selfy(): return _selfv(F_Y)

    def interp(c_start: bytes, target: int) -> bytes:
        # c_start + (target - c_start) * (cur - csy) / (lsy - csy)   -- linear, parameterised by selfY
        return _arg(c_start,
                    _const(target), c_start, bytes([_region.T_MINUS]),                 # (target - c_start)
                    _scratch(), _scratch_start(), bytes([_region.T_MINUS]),            # (cur - csy)
                    bytes([_region.T_MULT]),
                    _const(lsy), _scratch_start(), bytes([_region.T_MINUS]),           # (lsy - csy)
                    bytes([_region.T_DIV]), bytes([_region.T_PLUS]))

    a = _Asm()
    a.raw(opcodes.add_character_attribute(LADDER_FLAG) + opcodes.set_pathing(0))   # grip + detach; NO teleport
    if animation is not None:
        a.raw(opcodes.run_animation(int(animation)))
    # capture the boarding position (x, z, selfY) -- the ride interpolates FROM here
    a.raw(_stmt(_scratch_x(), selfx(), bytes([_region.T_ASSIGN])))
    a.raw(_stmt(_scratch_z(), selfz(), bytes([_region.T_ASSIGN])))
    a.raw(_stmt(_scratch_start(), selfy(), bytes([_region.T_ASSIGN])))
    a.label("LOOP")
    a.raw(_stmt(_scratch(), selfy(), _const(speed), bytes([_region.T_MINUS]), bytes([_region.T_ASSIGN])))  # step UP
    a.raw(opcodes.encode(0xA1, interp(_scratch_x(), lx), _arg(_scratch()), interp(_scratch_z(), lz), arg_flags=0b111))
    a.raw(opcodes.wait(1))
    a.raw(_stmt(selfy(), _const(lsy), bytes([_region.T_GT])))      # selfY still above the landing?
    a.jmp(_region.JMP_TRUE, "LOOP")
    a.raw(opcodes.encode(0xA1, _arg(_const(lx)), _arg(_const(lsy)), _arg(_const(lz)), arg_flags=0b111))  # exact landing
    if warp_to is not None:
        a.raw(opcodes.fade_filter(6, 24, 0, 255, 255, 255) + opcodes.wait(25)
              + _region.set_field_entrance(int(warp_entrance))
              + opcodes.field(int(warp_to)) + opcodes.terminate_entry(255))
    else:
        a.raw(opcodes.remove_character_attribute(LADDER_FLAG) + opcodes.set_pathing(1))
    a.raw(opcodes.RETURN)
    return a.assemble()


def _assemble_entry(funcs) -> bytes:
    """Assemble a type-1 (region) entry from ``[(tag, body), ...]`` (the ladder/jump region layout):
    the func table (``<tag:u16><fpos:u16>`` x N) then the concatenated bodies."""
    table = b""
    pos = len(funcs) * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def carry_body(*, rise: int | None = None, land=None, speed: int = DEFAULT_SPEED,
               duration: int = DEFAULT_DURATION, animation: int | None = None,
               warp_to: int | None = None, warp_entrance: int = 0) -> bytes:
    """The player's ride function, run in the player's context (the region RunScriptSync's it) so the
    moves move the PLAYER. Two modes:

    * ``land = (x, z, y)`` -- ride from WHEREVER he boards to that absolute landing point (a real floor),
      so he steps off cleanly (no end-of-ride floor-snap). For inter-field-style lifts: board at the
      bottom, ride up, let off on a higher floor elsewhere. ``land`` must be ABOVE the boarding point.
    * ``rise = <units>`` -- lift him ``rise`` world-units vertically (positive = up) from his current
      height, keeping x/z. A pure in-place vertical lift (needs a real floor at the top, else he
      floor-snaps back down when collision re-enables).

    Both are RELATIVE at the start (capture the boarding position, no teleport-in -- an earlier absolute
    board-snap warped him under a platform model). VISIBILITY is governed by the FIELD CAMERA, not the
    carry: a vertical rise stays rendered only when the camera's depthOffset + shallow pitch map it into
    screen-Y (not depth -- the [100,3996] psxDepth cull) and its vrp band is tall enough to scroll up;
    fork an elevator-style scene+camera (e.g. Pandemonium 2713). With ``warp_to`` the ride ENDS in a
    fade + ``Field()`` re-entry (an inter-floor elevator)."""
    if land is not None:
        return _carry_land_body(land, speed=speed, animation=animation,
                                warp_to=warp_to, warp_entrance=warp_entrance)
    if rise is None:
        raise ValueError("carry_body needs land=[x,z,y] (ride to a floor) or rise=<units> (vertical lift)")
    rise = int(rise)
    if rise == 0:
        raise ValueError("carry_body: rise must be non-zero (positive = up) -- a zero ride never moves")
    duration = max(1, int(duration))
    smag = max(1, math.ceil(abs(rise) / duration))    # per-frame selfY step (terminates in ~duration frames)
    up = rise > 0                                     # UP => selfY (= -worldY) DECREASES
    step_tok = _region.T_MINUS if up else _region.T_PLUS
    test_tok = _region.T_GT if up else _region.T_LT   # loop while selfY hasn't reached the target

    def selfx(): return _selfv(0)                     # obj field 0 = world X
    def selfz(): return _selfv(2)                     # obj field 2 = world Z
    def selfy(): return _selfv(F_Y)                   # obj field 1 = worldY-up (= -pos.y)

    a = _Asm()
    a.raw(opcodes.add_character_attribute(LADDER_FLAG) + opcodes.set_pathing(0))   # grip + detach; NO teleport
    if animation is not None:
        a.raw(opcodes.run_animation(int(animation)))  # optional ride gesture (cosmetic; off by default)
    # capture the boarding selfY, then the destination = start - rise (UP decreases selfY). Ride from there.
    a.raw(_stmt(_scratch_start(), selfy(), bytes([_region.T_ASSIGN])))
    a.raw(_stmt(_scratch(), _scratch_start(), _const(rise), bytes([_region.T_MINUS]), bytes([_region.T_ASSIGN])))
    a.label("LOOP")
    # step selfY one notch toward the target, keeping the player's current x/z (read live, written back)
    a.raw(opcodes.encode(0xA1, _arg(selfx()),
                         _arg(selfy(), _const(smag), bytes([step_tok])),
                         _arg(selfz()), arg_flags=0b111))
    a.raw(opcodes.wait(1))                                          # one ride frame (deterministic timing)
    a.raw(_stmt(selfy(), _scratch(), bytes([test_tok])))           # selfY not yet at the target?
    a.jmp(_region.JMP_TRUE, "LOOP")
    a.raw(opcodes.encode(0xA1, _arg(selfx()), _arg(_scratch()), _arg(selfz()), arg_flags=0b111))  # exact final snap
    if warp_to is not None:                           # ELEVATOR: ride then re-enter the destination floor
        a.raw(opcodes.fade_filter(6, 24, 0, 255, 255, 255) + opcodes.wait(25)
              + _region.set_field_entrance(int(warp_entrance))
              + opcodes.field(int(warp_to)) + opcodes.terminate_entry(255))
    else:                                             # in-screen ride: land + hand control back
        a.raw(opcodes.remove_character_attribute(LADDER_FLAG) + opcodes.set_pathing(1))
    a.raw(opcodes.RETURN)
    return a.assemble()


def platform_region(zone, ride_tag: int, *, trigger: str = "action", bubble: bool = True,
                    player_uid: int = PLAYER_UID) -> bytes:
    """A type-1 region entry that boards the player onto the ride (func ``ride_tag`` on the player).

    ``trigger="action"`` (default): Init ``SetRegion`` / tread ``Bubble(1)`` (if ``bubble``) / action
    ``DisableMove; RunScriptSync(player, ride_tag); EnableMove`` -- press to board. ``trigger="tread"``:
    the dispatch is on the tread func (auto-board on walk-in). Control is held for the whole ride
    (synchronous ``RunScriptSync``) -- the same proven shape as the ladder/jump trigger."""
    init = _region.set_region(zone) + opcodes.RETURN
    dispatch = (opcodes.DISABLE_MOVE
                + opcodes.run_script_sync(RUNSCRIPT_LEVEL, player_uid, ride_tag)
                + opcodes.ENABLE_MOVE + opcodes.RETURN)
    if trigger == "tread":
        body = _region.MOVEMENT_GATE + (opcodes.bubble(1) if bubble else b"") + dispatch
        funcs = [(0, init), (_region.RANGE_TAG, body)]
    else:                                             # "action" -- press-to-board (+ "!" prompt)
        tread = _region.MOVEMENT_GATE + (opcodes.bubble(1) if bubble else b"") + opcodes.RETURN
        action = _region.MOVEMENT_GATE + dispatch
        funcs = [(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)]
    return _assemble_entry(funcs)


def inject_platform(data, zone, *, rise: int | None = None, land=None, speed: int = DEFAULT_SPEED,
                    ride_tag: int = FIRST_PLATFORM_TAG,
                    duration: int = DEFAULT_DURATION, animation: int | None = None,
                    trigger: str = "action", bubble: bool = True, warp_to: int | None = None,
                    warp_entrance: int = 0, player_uid: int = PLAYER_UID, activate: bool = True):
    """Inject one carry platform: graft the ride function (``ride_tag``) onto the player entry, append a
    boarding region that fires it, and arm the region. Pass ``land=[x,z,y]`` (ride from the boarding spot
    to that landing floor) or ``rise=<units>`` (vertical lift). Returns ``(new_bytes, region_slot)``. For
    multiple platforms pass a distinct ``ride_tag`` each (start at :data:`FIRST_PLATFORM_TAG`)."""
    body = carry_body(rise=rise, land=land, speed=speed, duration=duration, animation=animation,
                      warp_to=warp_to, warp_entrance=warp_entrance)
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    data = edit.add_function(data, pe, ride_tag, body)
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, platform_region([tuple(p) for p in zone], ride_tag,
                                                         trigger=trigger, bubble=bubble, player_uid=player_uid))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot
