"""Read authored content back OUT of a real field's compiled ``.eb`` -- the inverse of the
``content/*`` injectors, used by ``import`` to fork a real field WITH its gateways, music,
encounters, and movement tuning (not just its camera/walkmesh/art).

Everything here keys on the exact byte patterns the injectors emit (and that real fields use),
verified against a real field's disassembly (Alexandria/Main Street, field 100):

  * EXIT / gateway -- a region entry (has both ``SetRegion`` 0x29 and ``Field`` 0x2B). The zone is
    the SetRegion polygon (each point packs as x = v & 0xFFFF, z = v>>16, signed i16); the target is
    the ``Field`` operand; the arrival entrance is the value assigned to the field-entrance variable
    (``D8 02``) right before ``Field`` -- i.e. ``05 D8 02 7D <entrance:i16> 2C 7F``.
  * field BGM     -- ``RunSoundCode(0, song)`` (0xC5, sound_code 0 = ff9fldsnd_song_play).
  * encounters    -- ``SetRandomBattles(slot, s1..s4)`` (0x3C) + ``SetRandomBattleFrequency`` (0x57).
  * movement dir  -- ``SetControlDirection(x, y)`` (0x67, TWIST) in Main_Init.

These are unambiguous single-opcode patterns; the lossy/contextual content (NPCs + their dialogue,
arbitrary event triggers, cutscenes) is deliberately NOT scanned -- you author that fresh on the fork.
"""

from __future__ import annotations

from .eb import EbScript

FIELD_OP = 0x2B            # Field(target)            -- a field transition (the exit)
SETREGION_OP = 0x29        # SetRegion(points)        -- the trigger polygon
SET_RANDOM_BATTLES = 0x3C  # SetRandomBattles(slot, s1..s4)
SET_BATTLE_FREQ = 0x57     # SetRandomBattleFrequency(freq)
RUN_SOUND_CODE = 0xC5      # RunSoundCode(code, id); code 0 = song_play (field BGM)
TWIST_OP = 0x67            # SetControlDirection(x, y)
RUN_SCRIPT_SYNC = 0x14     # RunScriptSync(level, uid, tag) -- REQEW: run obj `uid`'s func `tag`, wait
SETUP_JUMP = 0xE2          # SetupJump(x, y, z, arc) -- a climb's jump arc
ADD_CHAR_ATTR = 0xCC       # AddCharacterAttribute(flag); flag 4 (LADDER_FLAG) = "on a ladder"
DEFINE_PC = 0x2C           # DefinePlayerCharacter -- marks the controlled player's entry
BUBBLE_OP = 0x68           # Bubble(state) -- the "!" interact prompt (ladder tread func)
RUN_SHARED_SCRIPT = 0x43   # RunSharedScript(n) -- camera/sound polish a fork doesn't have
PLAYER_UID = 250           # the controlled player's runtime UID
LADDER_FLAG = 4            # GetLadderFlag() == (attr & 4)

# the field-entrance variable token: an expression statement `set D8:02 = <i16>` right before Field.
# 05=expr, D8 02=var(class 0xD8, idx 2), 7D=push-const, <i16>, 2C=assign, 7F=end  (8 bytes).
_ENTRANCE_SET_LEN = 8


def _s16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


def _region_points(instr) -> list:
    """Unpack a ``SetRegion`` instruction's packed-32 args into (x, z) i16 points."""
    pts = []
    for i, v in enumerate(instr.args):
        if instr.arg_is_expr[i]:
            return []                       # computed polygon -- can't extract statically
        pts.append((_s16(v & 0xFFFF), _s16((v >> 16) & 0xFFFF)))
    return pts


def _zone_quad(points) -> list:
    """Normalise a region polygon to the kit's quad: drop a doubled trailing vertex, take 4 corners."""
    pts = list(points)
    if len(pts) >= 2 and pts[-1] == pts[-2]:     # the IsInQuad-safe doubled last vertex (kit + real)
        pts = pts[:-1]
    return [list(p) for p in pts[:4]]


def _entrance_at(data: bytes, off: int):
    """If the instruction at ``off`` is ``set D8:02 = <i16>``, return that i16 (the arrival entrance)."""
    r = data[off:off + _ENTRANCE_SET_LEN]
    if (len(r) == _ENTRANCE_SET_LEN and r[0] == 0x05 and r[1] == 0xD8 and r[2] == 0x02
            and r[3] == 0x7D and r[6] == 0x2C and r[7] == 0x7F):
        return _s16(r[4] | (r[5] << 8))
    return None


def scan_gateways(eb_bytes) -> list:
    """Exit gateways in the script. Returns ``[{to, entrance, zone}]`` (zone = up to 4 [x, z] corners).

    A gateway is an entry that holds BOTH a ``SetRegion`` (the trigger polygon) and a ``Field``
    (the destination) -- the walk-into-a-zone exit pattern. A bare ``Field`` with no region (e.g. a
    scripted cutscene warp) is intentionally skipped. The arrival entrance is the ``D8:02`` assignment
    immediately preceding the ``Field`` (default 0)."""
    eb = EbScript.from_bytes(eb_bytes)
    out = []
    for e in eb.entries:
        if e.empty:
            continue
        zone = None
        fields = []                          # (target, entrance) for each Field in this entry
        for f in e.funcs:
            entrance = 0
            for ins in eb.instrs(f):
                if ins.op == SETREGION_OP and zone is None:
                    pts = _region_points(ins)
                    if len(pts) >= 3:
                        zone = _zone_quad(pts)
                elif ins.op == 0x05:
                    ent = _entrance_at(eb.data, ins.off)
                    if ent is not None:
                        entrance = ent
                elif ins.op == FIELD_OP:
                    tgt = ins.imm(0)
                    if tgt is not None:
                        fields.append((tgt, entrance))
        if zone and fields:
            for tgt, entrance in fields:
                out.append({"to": int(tgt), "entrance": int(entrance), "zone": zone})
    return out


def _first_instr(eb, op, *, entry_index=None):
    """First instruction with opcode ``op`` (optionally restricted to one entry), or None."""
    entries = [eb.entry(entry_index)] if entry_index is not None else eb.entries
    for e in entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == op:
                    yield ins


def scan_music(eb_bytes):
    """The field BGM song id (first ``RunSoundCode(0, song)``), or None. Prefers Main_Init (entry 0)."""
    eb = EbScript.from_bytes(eb_bytes)
    for source in (0, None):                 # Main_Init first, then anywhere
        for ins in _first_instr(eb, RUN_SOUND_CODE, entry_index=source):
            if ins.imm(0) == 0 and ins.imm(1) is not None:
                return int(ins.imm(1))
    return None


def scan_encounter(eb_bytes):
    """Random-battle config, or None. ``{scenes:[s1..s4], freq, pattern}`` from the first
    ``SetRandomBattles`` + the nearest ``SetRandomBattleFrequency``."""
    eb = EbScript.from_bytes(eb_bytes)
    srb = next(_first_instr(eb, SET_RANDOM_BATTLES), None)
    if srb is None:
        return None
    if any(srb.arg_is_expr[:5]):             # computed slot/scenes -- skip
        return None
    pattern = int(srb.imm(0))
    scenes = [int(srb.imm(i)) for i in range(1, 5)]
    freq_ins = next(_first_instr(eb, SET_BATTLE_FREQ), None)
    freq = int(freq_ins.imm(0)) if (freq_ins is not None and freq_ins.imm(0) is not None) else 255
    return {"scenes": scenes, "freq": freq, "pattern": pattern}


def scan_control_direction(eb_bytes):
    """The Main_Init ``SetControlDirection`` (TWIST) x value, or None (the WASD-vs-camera tuning)."""
    eb = EbScript.from_bytes(eb_bytes)
    ins = next(_first_instr(eb, TWIST_OP, entry_index=0), None)
    if ins is None:
        ins = next(_first_instr(eb, TWIST_OP), None)
    return None if ins is None else (None if ins.imm(0) is None else int(ins.imm(0)))


def _player_entry_index(eb):
    """Index of the controlled player's entry (the one defining the player character), or None."""
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == DEFINE_PC:
                    return e.index
    return None


def _is_climb_func(eb, player_index, tag) -> bool:
    """True if player function ``tag`` is a LADDER climb -- the definitive signature is the ladder
    flag (``AddCharacterAttribute(4)``) or a jump arc (``SetupJump``). This isolates real ladders from
    cosmetic region->player triggers (e.g. Treno's facing/stand-anim tweaks, which have neither)."""
    f = eb.entry(player_index).func_by_tag(tag)
    if f is None:
        return False
    for ins in eb.instrs(f):
        if ins.op == SETUP_JUMP:
            return True
        if ins.op == ADD_CHAR_ATTR and ins.imm(0) == LADDER_FLAG:
            return True
    return False


def _nop_shared_scripts(eb, func) -> bytes:
    """The climb function's raw bytecode with ``RunSharedScript`` (camera/sound polish) NOPed -- those
    depend on shared scripts a minted fork doesn't have (proven by the faithful-graft experiment)."""
    body = bytearray(eb.data[func.abs_start:func.abs_end])
    for ins in eb.instrs(func):
        if ins.op == RUN_SHARED_SCRIPT:
            rel = ins.off - func.abs_start
            body[rel:rel + ins.length] = b"\x00" * ins.length
    return bytes(body)


def scan_ladders(eb_bytes) -> list:
    """FF9 ladders, the truthful way: a region whose trigger ``RunScriptSync``s the player's CLIMB
    function -- where 'climb' is defined by the ladder flag / jump arcs, not just any RunScriptSync.

    Returns ``[{zone, climb_tag, trigger, bubble, climb}]``:
      * ``zone``     -- the trigger polygon (up to 4 [x, z] corners), or None if computed.
      * ``climb_tag``-- the player function tag the trigger runs (the climb).
      * ``trigger``  -- the region function tag that fires it (2 = tread/auto, 3 = action/press).
      * ``bubble``   -- whether the trigger shows the "!" interact prompt.
      * ``climb``    -- the climb function's raw bytecode (RunSharedScript NOPed) for a faithful graft.

    The climb is verbatim because its jump coordinates are hand-tuned to the ladder's geometry +
    the fixed camera -- that perspective tuning can't be regenerated, only copied."""
    eb = EbScript.from_bytes(eb_bytes)
    pe = _player_entry_index(eb)
    if pe is None:
        return []
    out, seen = [], set()
    for e in eb.entries:
        if e.empty:
            continue
        zone = None
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == SETREGION_OP and zone is None:
                    pts = _region_points(ins)
                    if len(pts) >= 3:
                        zone = _zone_quad(pts)
        # the "!" prompt belongs to the region, not a single func -- the Bubble is usually in the tread
        # (tag 2) while the climb's RunScriptSync is in the action (tag 3); check the whole entry.
        bubble = any(ins.op == BUBBLE_OP for f in e.funcs for ins in eb.instrs(f))
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op != RUN_SCRIPT_SYNC or ins.imm(1) != PLAYER_UID:
                    continue
                tag = ins.imm(2)
                if tag is None or (e.index, tag) in seen or not _is_climb_func(eb, pe, tag):
                    continue
                seen.add((e.index, tag))
                climb = _nop_shared_scripts(eb, eb.entry(pe).func_by_tag(tag))
                out.append({"zone": zone, "climb_tag": int(tag), "trigger": int(f.tag),
                            "bubble": bool(bubble), "climb": climb})
    return out


def scan_content(eb_bytes) -> dict:
    """All importable content from a field's ``.eb`` in one pass:
    ``{gateways, music, encounter, control_direction, ladders}`` (inverse of the content injectors)."""
    return {
        "gateways": scan_gateways(eb_bytes),
        "music": scan_music(eb_bytes),
        "encounter": scan_encounter(eb_bytes),
        "control_direction": scan_control_direction(eb_bytes),
        "ladders": scan_ladders(eb_bytes),
    }
