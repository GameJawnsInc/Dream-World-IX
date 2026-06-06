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


def scan_content(eb_bytes) -> dict:
    """All importable content from a field's ``.eb`` in one pass:
    ``{gateways, music, encounter, control_direction}`` (the inverse of the content injectors)."""
    return {
        "gateways": scan_gateways(eb_bytes),
        "music": scan_music(eb_bytes),
        "encounter": scan_encounter(eb_bytes),
        "control_direction": scan_control_direction(eb_bytes),
    }
