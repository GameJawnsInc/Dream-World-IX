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
from . import cutscene as _cutscene
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


FADE_SETTLE = 24          # frames to let the entry fade-in (FadeFilter ~16) lift before the rider moves


def _drop_to_bottom(rise: int) -> bytes:
    """Place the player ``rise`` world-units BELOW his spawn (the shaft bottom), detached. Spliced into
    the player Init so it runs UNDER the black entry fade -- the player is simply THERE at the bottom when
    the screen clears, never a visible teleport. Mirrors how 2713 spawns the rider at the shaft bottom in
    his OWN Init (entry-10 tag-0 op_0B spawn switch) before the post-fade ride eases him up."""
    def selfx(): return _selfv(0)
    def selfz(): return _selfv(2)
    def selfy(): return _selfv(F_Y)
    return (opcodes.add_character_attribute(LADDER_FLAG) + opcodes.set_pathing(0)
            + opcodes.encode(0xA1, _arg(selfx()),
                             _arg(selfy(), _const(abs(int(rise))), bytes([_region.T_PLUS])),  # selfY+rise = lower
                             _arg(selfz()), arg_flags=0b111))


def entry_rise_body(*, rise: int, duration: int = DEFAULT_DURATION, animation: int | None = None) -> bytes:
    """The ride function for the on-arrival elevator: ride the player straight UP ``rise`` world-units
    from his boarding position (the shaft bottom, where :func:`_drop_to_bottom` placed him in the player
    Init) to the spawn/let-off floor, then land (``SetPathing(1)`` on a real floor). It travels UP ONLY --
    the DROP is the separate Init splice run under the black fade -- so the player is seen carried up in
    the CLEAR, exactly as 2713's ride func does (which never drops inside the visible ride). Reuses the
    proven :func:`carry_body` rise mode."""
    return carry_body(rise=abs(int(rise)), duration=duration, animation=animation)


def inject_entry_rise(data, *, rise: int, ride_tag: int = FIRST_PLATFORM_TAG,
                      duration: int = DEFAULT_DURATION, animation: int | None = None,
                      player_uid: int = PLAYER_UID):
    """The on-ARRIVAL elevator (the real 2713 mechanism), split into 2713's three slots so the rise plays
    VISIBLY (an earlier single-function version did the drop+rise under the black fade -> nothing to see):

      1. graft the UP-only ride (:func:`entry_rise_body`) onto the player;
      2. splice a DROP into the player Init right after ``DefinePlayerCharacter`` (the proven
         re-entry-spawn splice point) so the engine places him at the shaft bottom UNDER the entry fade --
         no visible teleport;
      3. arm an ``InitCode`` coroutine that spins until ``usercontrol == 1`` (Main_Init's ``EnableMove``
         has run) then waits :data:`FADE_SETTLE` frames for the fade-in to lift, and only THEN locks
         control + runs the ride synchronously (the per-frame ``Wait(1)`` advances ``ProcessAnime``) --
         so the player is seen rising in the clear, post-fade, like 2713's tag-1 dispatcher.

    Unconditional (fires on every entry) -- a single on-entry rise; per-door gating (``D8:2 ==``) is a
    follow-up. Returns new ``.eb`` bytes."""
    out = data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    pe = find_player_entry(EbScript.from_bytes(out))
    # 1. the UP-only ride func on the player
    out = edit.add_function(out, pe, ride_tag, entry_rise_body(rise=rise, duration=duration, animation=animation))
    # 2. drop the player to the shaft bottom in his Init, after DefinePlayerCharacter (under the fade)
    eb = EbScript.from_bytes(out)
    init = eb.entry(pe).func_by_tag(0)
    if init is None:
        raise ValueError("player entry has no Init (tag 0); cannot place the elevator drop")
    dpc = next((i for i in eb.instrs(init) if i.op == 0x2C), None)        # DefinePlayerCharacter
    if dpc is None:
        raise ValueError("player Init has no DefinePlayerCharacter (0x2C); cannot place the elevator drop")
    out = edit.insert_in_function(out, pe, 0, dpc.end - init.abs_start, _drop_to_bottom(rise))
    # 3. fire the rise POST-FADE: spin until usercontrol==1, settle past the fade, then run the ride sync
    a = _Asm()
    a.label("WAITCTL")
    a.raw(opcodes.wait(1))
    a.raw(_region.cond_sysvar_eq(2, 0))                                  # usercontrol still 0 (no control yet)?
    a.jmp(_region.JMP_TRUE, "WAITCTL")                                   # yes -> keep spinning (op_03 = backward-safe;
                                                                         #   JMP_FALSE/op_02 is forward-only, unsigned)
    a.raw(opcodes.wait(FADE_SETTLE)                                      # let the fade-in lift
          + opcodes.DISABLE_MOVE
          + opcodes.run_script_sync(RUNSCRIPT_LEVEL, player_uid, ride_tag)
          + opcodes.ENABLE_MOVE + opcodes.RETURN)
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + a.assemble()
    slot = EbScript.from_bytes(out).first_free_slot()
    out = edit.append_entry(out, slot, entry)
    out = edit.activate(out, opcodes.init_code(slot, 0))
    return out
