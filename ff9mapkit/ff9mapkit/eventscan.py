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

import re

from .binutils import u16
from .eb import EbScript

FIELD_OP = 0x2B            # Field(target)            -- a field transition (the exit)
WORLDMAP_OP = 0xB6         # WorldMap(loc)            -- leave to the overworld; loc is a WORLD-MAP
                           #                            LOCATION id (e.g. 9000-9012), NOT a field id
SHARED_MENU_WARPS = frozenset(range(2950, 2956))  # chocobo/mognet shared menu warps -- not geography
SETREGION_OP = 0x29        # SetRegion(points)        -- the trigger polygon
SET_RANDOM_BATTLES = 0x3C  # SetRandomBattles(slot, s1..s4)
SET_BATTLE_FREQ = 0x57     # SetRandomBattleFrequency(freq)
RUN_SOUND_CODE = 0xC5      # RunSoundCode(code, id); code 0 = song_play (field BGM)
TWIST_OP = 0x67            # SetControlDirection(x, y)
RUN_SCRIPT_SYNC = 0x14     # RunScriptSync(level, uid, tag) -- REQEW: run obj `uid`'s func `tag`, wait
RUN_SCRIPT_ASYNC = 0x10    # RunScriptAsync(level, uid, tag) -- run obj `uid`'s func, don't wait
RUN_SCRIPT = 0x12          # RunScript(level, uid, tag) -- run obj `uid`'s func
DISPATCH_OPS = frozenset((RUN_SCRIPT_SYNC, RUN_SCRIPT_ASYNC, RUN_SCRIPT))   # region -> player-func calls
SETUP_JUMP = 0xE2          # SetupJump(x, y, z, arc) -- a climb's / a jump's arc destination
JUMP_OP = 0xDC             # Jump() -- perform the SetupJump arc (the navigable-jump signature, with SetupJump)
SET_JUMP_ANIM_OP = 0x94    # SetJumpAnimation(anim, a, b) -- the player Init's jump-clip setup
# A navigable hop is a SELF-CONTAINED arc: face -> jump-anim -> SetupJump/Jump -> land. If a
# SetupJump/Jump func ALSO does any of the following it's a scripted/cinematic sequence (a sand trap, a
# cutscene, a warp-jump), NOT player navigation -- and it references field-specific state (text, battle
# scenes, shared-script entries, destination fields) that doesn't port to a fork. Such arcs reuse
# SetupJump/Jump so they look like jumps by opcode, so scan_jumps excludes any that touch these:
NON_NAVIGABLE_OPS = frozenset((
    0x1F, 0x20, 0x95, 0x96,    # WindowSync/Async[Ex] -- a "press X!" prompt / dialogue (sand trap, cutscene)
    0x2A,                      # Battle -- a forced encounter mid-arc (sand traps spawn one)
    0x6F, 0x70,                # MoveCamera / ReleaseCamera -- a cinematic camera follow (e.g. Alexandria pan)
    0x2B, 0xB6, 0xFD,          # Field / WorldMap / PreloadField -- the "jump" warps to another field
    0x23, 0x25, 0xE8,          # Walk / InitWalk / SideWalkXZY -- a scripted walk (a hop is a JUMP, not a walk)
    0x10, 0x12, 0x14,          # RunScript / Sync / Async -- nested object scripts that won't port
    0x43, 0x44, 0x45,          # Run/Wait/StopSharedScript -- per-field concurrent helpers a fork lacks
    0xEC,                      # FadeFilter -- a screen fade (a transition, not a hop)
))
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


def scan_region_zones(eb_bytes) -> list:
    """Every static ``SetRegion`` trigger polygon in the script (exits AND interaction/event/trap
    regions), as ``[x, z]``-corner quads. Used to keep an imported field's spawn OFF a trigger: a spawn
    inside an exit gateway instant-warps you back out the moment you arrive, and inside a tread region it
    auto-fires (e.g. a sand trap). Computed polygons (expression args) are skipped (can't place them)."""
    eb = EbScript.from_bytes(eb_bytes)
    out = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == SETREGION_OP:
                    pts = _region_points(ins)
                    if len(pts) >= 3:
                        out.append(_zone_quad(pts))
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


def _func_ops(eb, player_index, tag):
    """The opcode set + an ``has_ladder_flag`` predicate for player function ``tag`` (or None)."""
    f = eb.entry(player_index).func_by_tag(tag)
    if f is None:
        return None, False
    ops = set()
    ladder = False
    for ins in eb.instrs(f):
        ops.add(ins.op)
        if ins.op == ADD_CHAR_ATTR and ins.imm(0) == LADDER_FLAG:
            ladder = True
    return ops, ladder


def _is_ladder_func(eb, player_index, tag) -> bool:
    """True if player function ``tag`` is a LADDER climb. The definitive signature is the ladder flag
    (``AddCharacterAttribute(4)``) -- a hold-to-climb. A SetupJump arc WITHOUT the flag is a one-shot
    navigable JUMP (see :func:`_is_jump_func`), not a ladder, so the flag is what separates them (the
    census confirms every real ladder sets it; the 10 fields that don't were jumps mis-read as ladders)."""
    ops, ladder = _func_ops(eb, player_index, tag)
    return bool(ladder)


def _is_jump_func(eb, player_index, tag) -> bool:
    """True if player function ``tag`` is a navigable JUMP arc: a ``SetupJump``+``Jump`` parabola that
    is NOT a ladder (no ladder flag) AND is SELF-CONTAINED (none of :data:`NON_NAVIGABLE_OPS`). The
    self-contained test is what separates an Ice-Cavern-style ledge HOP (face -> jump -> land) from the
    look-alikes that also use SetupJump/Jump: a Cleyra/Tree-Trunk SAND TRAP (a 'press X!' Window +
    struggle + Battle), a cinematic traversal (MoveCamera follow), a warp-jump (Field), or a scripted
    walk/nested-script sequence -- none of which are free navigation, and all of which reference
    field-specific state (text, scenes, shared-script entries, destinations) that a fork can't port."""
    ops, ladder = _func_ops(eb, player_index, tag)
    if ops is None or ladder or SETUP_JUMP not in ops or JUMP_OP not in ops:
        return False
    if ops & NON_NAVIGABLE_OPS:        # a scripted/cinematic sequence (trap, cutscene, warp), not a hop
        return False
    return True


def _is_climb_func(eb, player_index, tag) -> bool:
    """Back-compat: a climb is now strictly a flagged ladder (was: flag OR any SetupJump). Kept for any
    external caller; internal scanners use :func:`_is_ladder_func` / :func:`_is_jump_func`."""
    return _is_ladder_func(eb, player_index, tag)


def _entry_bytes(data, idx) -> bytes:
    """Raw bytes of entry ``idx`` (its type+func-table+bodies) via the entry table at offset 128."""
    slot = 128 + idx * 8
    off, sz = u16(data, slot), u16(data, slot + 2)
    return data[128 + off:128 + off + sz]


def _climb_sequences(eb, func) -> dict:
    """The field entries a climb launches via ``STARTSEQ`` (RunSharedScript, 0x43) -- run as concurrent
    per-frame Seqs on the climber (e.g. the SetPitchAngle forward-lean: the climb ramps a pitch helper
    entry in, then out). STARTSEQ arg0 is an ENTRY index in THIS field, so a faithful fork must carry
    those entries too (not NOP the calls). Returns ``{entry_index: entry_bytes}`` (deduped)."""
    seqs = {}
    for ins in eb.instrs(func):
        if ins.op == RUN_SHARED_SCRIPT and ins.args:
            ei = int(ins.args[0])
            if ei not in seqs:
                seqs[ei] = _entry_bytes(eb.data, ei)
    return seqs


def scan_ladders(eb_bytes) -> list:
    """FF9 ladders, the truthful way: a region whose trigger ``RunScriptSync``s the player's CLIMB
    function -- where 'climb' is defined by the ladder flag / jump arcs, not just any RunScriptSync.

    Returns ``[{zone, climb_tag, trigger, bubble, climb, sequences}]``:
      * ``zone``     -- the trigger polygon (up to 4 [x, z] corners), or None if computed.
      * ``climb_tag``-- the player function tag the trigger runs (the climb).
      * ``trigger``  -- the region function tag that fires it (2 = tread/auto, 3 = action/press).
      * ``bubble``   -- whether the trigger shows the "!" interact prompt.
      * ``climb``    -- the climb function's raw bytecode, VERBATIM (STARTSEQ calls intact).
      * ``sequences``-- ``{entry_index: bytes}`` for each entry the climb launches via STARTSEQ (the
        concurrent per-frame helpers, e.g. the SetPitchAngle forward-lean); empty for simple ladders.

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
                if tag is None or (e.index, tag) in seen or not _is_ladder_func(eb, pe, tag):
                    continue
                seen.add((e.index, tag))
                cf = eb.entry(pe).func_by_tag(tag)
                out.append({"zone": zone, "climb_tag": int(tag), "trigger": int(f.tag),
                            "bubble": bool(bubble), "climb": eb.data[cf.abs_start:cf.abs_end],
                            "sequences": _climb_sequences(eb, cf)})
    return out


def scan_jumps(eb_bytes) -> list:
    """FF9 navigable JUMPS -- ledge/gap hops (Ice Cavern etc.): a region whose trigger dispatches the
    player's one-shot jump-arc function (``SetupJump``+``Jump``, NOT a ladder climb). The cousin of
    :func:`scan_ladders`; the two are disjoint (ladder = has the ladder flag, jump = doesn't).

    Returns ``[{zone, trigger, bubble, jump}]``:
      * ``zone``    -- the trigger polygon (up to 4 [x, z] corners), or None if computed.
      * ``trigger`` -- "action" (press the action button in the zone, the Ice-Cavern "!"+confirm hop)
        or "tread" (auto-fires on walk-in), from whether the dispatch sits in the action (tag 3) or
        tread (tag 2) func.
      * ``bubble``  -- whether the region shows the floating "!" prompt.
      * ``jump``    -- the player's jump-arc bytecode, VERBATIM (the exact perspective-tuned world
        coords -- only copyable, like a ladder climb).

    The dispatch may be ``RunScriptSync``/``Async``/``RunScript`` and may reference the player by the
    runtime UID 250 OR by the player's entry index (Ice Cavern uses the entry index -- which is exactly
    why these jumps slipped past the uid-250-only ladder scan and were dropped on fork)."""
    eb = EbScript.from_bytes(eb_bytes)
    pe = _player_entry_index(eb)
    if pe is None:
        return []
    out, seen = [], set()
    for e in eb.entries:
        if e.empty or e.index == pe:
            continue
        zone = None
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == SETREGION_OP and zone is None:
                    pts = _region_points(ins)
                    if len(pts) >= 3:
                        zone = _zone_quad(pts)
        if zone is None:
            # The dispatching entry isn't a navigable region: either it has NO SetRegion (the jump is
            # fired from Main_Loop / a cutscene sequence -- a scripted hop, not player navigation) or its
            # SetRegion is computed (expression args -> not statically placeable). Either way it's not an
            # authorable ledge jump, so skip it. (A field can mix both: field 950 has a loop-fired hop in
            # entry 0 AND a real region jump in entry 6 -- this keeps only the latter.)
            continue
        bubble = any(ins.op == BUBBLE_OP for f in e.funcs for ins in eb.instrs(f))
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op not in DISPATCH_OPS:
                    continue
                if ins.imm(1) not in (PLAYER_UID, pe):       # not a call into the player object
                    continue
                tag = ins.imm(2)
                if tag is None or (e.index, tag) in seen or not _is_jump_func(eb, pe, tag):
                    continue
                seen.add((e.index, tag))
                jf = eb.entry(pe).func_by_tag(tag)
                trigger = "action" if int(f.tag) == 3 else "tread"
                out.append({"zone": zone, "trigger": trigger, "bubble": bool(bubble),
                            "jump": eb.data[jf.abs_start:jf.abs_end]})
    return out


# --- persistent NPCs / props (faithful fork) ---------------------------------------------
SET_MODEL_OP = 0x2F        # SetModel(model, animset)
SET_STAND_ANIM_OP = 0x33   # SetStandAnimation(pose)
MOVE_INSTANT_OP = 0xA1     # MoveInstantXZY(worldX, -worldY, worldZ) -- the object's static placement
TURN_INSTANT_OP = 0x36     # TurnInstant(dir)
SET_OBJECT_FLAGS_OP = 0x93 # SetObjectFlags(bits); bit 1 = SHOW model (off => loaded hidden, script-driven)
SHOW_MODEL_BIT = 1
INIT_OBJECT_OP = 0x09      # InitObject(slot, arg) in Main_Init -- spawns/activates object `slot`
SETVAR_EXPR_OP = 0x05      # an expression; `05 D9 idx 7D lo hi 2C 7F` = SetVar D9(idx)=const
POS_VAR_CLASS = 0xD9       # the D9 var class CreateObject/MoveInstantXZY read for x/y/z


def _read_object_init(eb, init_func) -> dict:
    """Decode the render-defining fields an object's Init (tag 0) sets: model/animset, pose, face, a
    literal placement (``lit``), the object's OWN local D9 consts, its SetObjectFlags, and whether it is
    the player. Shared by :func:`scan_objects` (decoded facts) and :func:`scan_objects_verbatim` (graft)."""
    model = animset = pose = face = lit = flags = None
    local: dict = {}
    player = False
    for ins in eb.instrs(init_func):
        if ins.op == DEFINE_PC:
            player = True
        elif ins.op == SETVAR_EXPR_OP:
            raw = eb.data[ins.off:ins.off + 8]
            if len(raw) >= 6 and raw[1] == POS_VAR_CLASS and raw[3] == 0x7D:
                local[raw[2]] = _s16(raw[4] | (raw[5] << 8))
        elif ins.op == SET_MODEL_OP and model is None and len(ins.args) >= 2 \
                and isinstance(ins.args[0], int):
            model, animset = int(ins.args[0]), int(ins.args[1])
        elif ins.op == SET_STAND_ANIM_OP and pose is None and ins.args and isinstance(ins.args[0], int):
            pose = int(ins.args[0])
        elif ins.op == TURN_INSTANT_OP and face is None and ins.args and isinstance(ins.args[0], int):
            face = int(ins.args[0])
        elif ins.op == MOVE_INSTANT_OP and lit is None and len(ins.args) >= 3 \
                and all(isinstance(a, int) for a in ins.args[:3]):
            lit = (_s16(int(ins.args[0])), _s16(int(ins.args[2])))      # (worldX, worldZ)
        elif ins.op == SET_OBJECT_FLAGS_OP and ins.args and isinstance(ins.args[0], int):
            flags = int(ins.args[0])                  # last wins (an object may hide then show)
    return {"model": model, "animset": animset, "pose": pose, "face": face, "lit": lit,
            "local": local, "flags": flags, "player": player}


# --- the cross-reference surface a verbatim graft must remap (docs/OBJECT_CARRY.md S3) -------------
# Every reference-bearing opcode's uid/slot operand is a 1-byte immediate (verified vs eb/_optables.py),
# so a graft remap is always a same-length in-place patch (like the ladder STARTSEQ remap). UID-space:
# 250=player, 255=self, 251-254=party, else == an entry slot. SLOT-space: Init*/STARTSEQ entry index.
# (0x44/0x45 Wait/StopSharedScript have NO operand -- they act on the current shared script -- so they
# are NOT here; same for 0x16/18/1A REPLY* which target the dynamic caller, and 0xD4/0x1D/0xA2 which act
# on self with non-uid args.)
REF_OPS = {
    0x09: {"slot": (0,), "uid": (1,)}, 0x07: {"slot": (0,), "uid": (1,)}, 0x08: {"slot": (0,), "uid": (1,)},
    0x10: {"uid": (1,)}, 0x12: {"uid": (1,)}, 0x14: {"uid": (1,)},   # RunScript[Async|Sync](level, uid, tag)
    0x24: {"uid": (0,)}, 0x39: {"uid": (0,)}, 0x3A: {"uid": (0,)},   # Walk/Show/HideObject
    0x4C: {"uid": (0, 1)},                                           # AttachObject(attached, carrying, bone)
    0x4D: {"uid": (0,)}, 0x51: {"uid": (0,)}, 0x87: {"uid": (0,)}, 0x8A: {"uid": (0,)},
    0x8F: {"uid": (0,)}, 0x95: {"uid": (0,)}, 0x96: {"uid": (0,)}, 0x97: {"uid": (0,)},
    0x9F: {"uid": (0,)}, 0xA9: {"uid": (0,)}, 0xAD: {"uid": (0,)}, 0xBB: {"uid": (0,)},
    0xBC: {"uid": (0,)}, 0xBD: {"uid": (0,)}, 0xBE: {"uid": (0,)}, 0xBF: {"uid": (0,)},
    0xB5: {"uid": (0,)}, 0xC2: {"uid": (0,)},
    0x43: {"slot": (0,)},                                            # RunSharedScript (STARTSEQ) -- entry idx
}
INIT_OPS = (0x09, 0x07, 0x08)        # the uid arg defaults to the slot when it is 0 (not an explicit ref)
RUNSCRIPT_OPS = (0x10, 0x12, 0x14)   # carry a (uid, tag) -- the tag is the player function the object calls
UID_PLAYER, UID_SELF = 250, 255
PARTY_UIDS = (251, 252, 253, 254)
FORK_PLAYER_TAGS = frozenset((0, 1))  # a blank fork's player (Zidane) defines only Init+Loop -- a carried
#                                       object that RunScripts a player tag >= 2 dangles (softlock); that
#                                       interaction can only be lit up by a later donor-player-script graft.
RENDER_TAGS = (0, 1)                  # Init + Loop: model/pose/placement/flags/size all live here
_OBJVAR_RE = re.compile(r"op78\((\d+),")  # B_OBJSPECA expression token: op78(uid, field) -- a uid read

# --- player-function graft (docs/PLAYER_GRAFT.md): carry the donor player funcs a carried object RunScripts ---
RUN_MODEL_CODE_OP = 0x88     # RunModelCode(code, pack) -- the player Init's animation-pack loads
ZIDANE_MODELS = frozenset((98, 93))   # the blank fork's player rig; a non-Zidane donor's clips won't match (532 too)
TEXT_OPS = frozenset((0x1F, 0x20, 0x95, 0x96))   # WindowSync/Async[Ex] -- references a .mes TXID the fork lacks
ANIM_OPS = frozenset((0x33, 0x34, 0x40, 0x94))   # Set{Stand,Walk}Animation/RunAnimation/SetJumpAnimation: MODEL-keyed clips
# --- STARTSEQ-helper closure (docs/OBJECT_CARRY.md S2 v1.5): a carried object launches a concurrent type-1
# Seq helper via STARTSEQ (0x43, an ENTRY index). The fork drops the helper -> the object refused/init_only.
# Carry the helper too (like the ladder `sequences` graft). But a bare type-1 check is WRONG: ~15 of the 164
# real helpers contain a CUTSCENE op (a MoveCamera sweep, a Battle, a Field warp, a menu) that must NOT fire in
# a static fork -- so vet the helper BODY. UNSAFE_SEQ_OPS = warp / battle / camera / menu / window / fade (the
# census found ONLY these families across all 164 helpers; reproduces the 48/32/9 flip split byte-for-byte).
UNSAFE_SEQ_OPS = frozenset((
    0x1F, 0x20, 0x21, 0x95, 0x96, 0x8E, 0xEB, 0x54, 0x53, 0xC9,   # Window* / Close*Window / Raise/WaitWindow / tile-loop
    0x2A, 0x8C, 0xD0, 0xE1, 0x1B, 0x3C, 0x4A, 0x57,               # Battle / BattleEx / BattleDialog / ...Battle...
    0x2B, 0xB6, 0xFD,                                             # Field / WorldMap / PreloadField (a warp mid-Seq)
    0x6F, 0x70,                                                   # MoveCamera / ReleaseCamera (a cutscene camera)
    0x75, 0xAA, 0xAB,                                             # Menu / Enable / DisableMenu
    0xEC,                                                         # FadeFilter
))
# the allow-list for a graft-safe player GESTURE: turn / animation / wait / head-focus / char-attr / jump-arc +
# structure (nop/jumps/return/expr/switch/wait). Anything ELSE (text, warp, camera, scripted walk, menu, sound,
# give-item, a sibling uid ref, a RunScript) disqualifies the func -> it stays refused (its object stays init_only).
SAFE_GESTURE_OPS = frozenset((
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x22,       # nop / jumps / return / expr / switch / wait
    0x36, 0x56, 0x9B, 0x50, 0x99,                         # TurnInstant/TimedTurn/TurnTowardPosition/WaitTurn/SetTurnSpeed
    0x33, 0x34, 0x40, 0x41, 0x3F, 0x3D,                   # Set{Stand,Walk}Anim/RunAnimation/WaitAnimation/AnimFlags/AnimInOut
    0x47, 0x8B,                                           # EnableHeadFocus / SetHeadFocusMask
    0xCC, 0xCD,                                           # Add/RemoveCharacterAttribute (ladder flag etc.)
    0xE2, 0xDC, 0x9C, 0x9D, 0x94, 0xA8,                   # jump-arc: SetupJump/Jump/RunJump/RunLand/SetJumpAnim/SetPathing
))


def _is_player_entry(val, donor_player_entry) -> bool:
    """True if ``val`` is a donor player ENTRY INDEX. ``donor_player_entry`` is an int (the primary PC) OR a
    collection of every PC entry index (182 real fields define >1 ``DefinePlayerCharacter`` -- a secondary-PC
    ref must classify as ``player``, else it leaks into ``uncarried`` and is mistaken for a closeable sibling)."""
    if donor_player_entry is None:
        return False
    if isinstance(donor_player_entry, int):
        return val == donor_player_entry
    return val in donor_player_entry


def _seq_helper_safe(eb, ei: int) -> bool:
    """Is entry ``ei`` a CLOSEABLE STARTSEQ helper (docs/OBJECT_CARRY.md S2 v1.5)? In-range + a type-1
    Seq/region entry + a BENIGN body (no :data:`UNSAFE_SEQ_OPS` cutscene op and no nested ``STARTSEQ`` --
    census: depth-1, 0 nested). A benign helper is launched as a concurrent per-frame Seq, so carrying it +
    remapping the launcher's entry-arg is the proven ladder ``sequences`` graft. An unsafe one (a MoveCamera
    sweep / a Battle / a warp) must stay refused so it can't fire in a static fork."""
    if not (0 <= ei < eb.entry_count):
        return False
    e = eb.entry(ei)
    if e.empty or _entry_bytes(eb.data, ei)[:1] != bytes([1]):   # type byte 1 = a Seq/region helper entry
        return False
    for f in e.funcs:
        for ins in eb.instrs(f):
            if ins.op == RUN_SHARED_SCRIPT or ins.op in UNSAFE_SEQ_OPS:   # nested STARTSEQ or a cutscene op
                return False
    return True


def _classify_ref(kind: str, val: int, donor_player_entry, carried_slots, self_slot: int) -> str:
    """Classify one slot/uid reference value: self | player | party | sibling | uncarried."""
    if val == self_slot:
        return "self"
    if kind == "uid":
        if val == UID_SELF:
            return "self"
        if val == UID_PLAYER or _is_player_entry(val, donor_player_entry):
            return "player"                          # 250, or the player BY ENTRY INDEX (-> 250 on graft)
        if val in PARTY_UIDS:
            return "party"
    return "sibling" if val in carried_slots else "uncarried"


def _expr_obj_uids(expr) -> list:
    """The object UIDs an expression operand reads via the ``op78(uid, field)`` token (B_OBJSPECA)."""
    return [int(m) for m in _OBJVAR_RE.findall(expr)] if isinstance(expr, str) else []


def _classify_entry_refs(eb, entry, donor_player_entry, carried_slots, self_slot):
    """Classify every outbound slot/uid reference the entry's functions make. Returns
    ``(refs, player_tags)`` -- ``refs`` is one record per reference (func_tag/op/kind/value/klass[/tag]);
    ``player_tags`` is the set of player function tags the entry RunScripts (the donor-script dependency)."""
    refs, player_tags = [], set()
    for f in entry.funcs:
        for ins in eb.instrs(f):
            spec = REF_OPS.get(ins.op)
            if spec:
                for kind in ("slot", "uid"):
                    for ai in spec.get(kind, ()):
                        if ins.arg_is_expr[ai] if ai < len(ins.arg_is_expr) else False:
                            refs.append({"func_tag": f.tag, "op": ins.op, "op_name": ins.name,
                                         "kind": kind, "arg_index": ai, "value": None, "klass": "expr"})
                            continue
                        val = ins.imm(ai)
                        if val is None:
                            continue
                        if kind == "uid" and ins.op in INIT_OPS and val == 0:
                            continue                 # uid 0 aliases the slot arg -- not an explicit ref
                        rec = {"func_tag": f.tag, "op": ins.op, "op_name": ins.name, "kind": kind,
                               "arg_index": ai, "value": int(val),
                               "klass": _classify_ref(kind, int(val), donor_player_entry, carried_slots, self_slot)}
                        if ins.op in RUNSCRIPT_OPS and ai == 1:
                            t = ins.imm(2)               # the called function tag (player OR self/sibling)
                            if t is not None:
                                rec["tag"] = int(t)
                                if rec["klass"] == "player":
                                    player_tags.add(int(t))
                        refs.append(rec)
            for ai, is_expr in enumerate(ins.arg_is_expr):
                if is_expr:
                    for uidv in _expr_obj_uids(ins.args[ai]):
                        refs.append({"func_tag": f.tag, "op": ins.op, "op_name": ins.name,
                                     "kind": "expr_objvar", "arg_index": ai, "value": uidv,
                                     "klass": _classify_ref("uid", uidv, donor_player_entry, carried_slots, self_slot)})
    return refs, player_tags


def _graft_safety(entry, refs, fork_player_tags, *, graftable_player_tags=frozenset(),
                  seq_closeable=frozenset()):
    """Per the carry policy (docs/OBJECT_CARRY.md S4): is the WHOLE entry graftable, only its
    render-defining tags (the rest reference player funcs a blank fork lacks / uncarried siblings), or
    must it be refused? Returns ``(safety, carry_tags)``. A reference is SAFE when it resolves to
    self / a carried sibling / the player at a tag the fork has / a BENIGN STARTSEQ helper the closure
    carries (``seq_closeable``); everything else (a player tag >= 2, an uncarried sibling, party, an
    expression-computed uid, an UNSAFE STARTSEQ helper) leaves its function un-graftable. A FIXPOINT then
    also drops any function that ``RunScript``s a SELF tag we are dropping (else it would dangle).
    ``seq_closeable`` defaults empty -> byte-identical to before (the v1.5 closure is opt-in)."""
    bad_tags, self_deps = set(), {}
    for r in refs:
        if r["op"] in RUNSCRIPT_OPS and r["kind"] == "uid" and r["klass"] == "self" and "tag" in r:
            self_deps.setdefault(r["func_tag"], set()).add(r["tag"])    # F depends on its own func `tag`
        if r["klass"] in ("self", "sibling"):
            ok = True
        elif r["klass"] == "player":
            # safe if the fork player has the tag (0/1) OR it WILL be grafted (the player-function graft,
            # docs/PLAYER_GRAFT.md). graftable_player_tags defaults empty -> byte-identical to before.
            ok = r.get("tag") is None or r["tag"] in fork_player_tags or r["tag"] in graftable_player_tags
        elif r["op"] == RUN_SHARED_SCRIPT and r["kind"] == "slot" and r.get("value") in seq_closeable:
            ok = True                                # an uncarried but BENIGN STARTSEQ helper -> closure carries it
        else:                                        # party / uncarried / expr / unsafe-helper -> not resolvable
            ok = False
        if not ok:
            bad_tags.add(r["func_tag"])
    changed = True
    while changed:                                   # propagate: a kept func calling a dropped func is bad
        changed = False
        for ftag, targets in self_deps.items():
            if ftag not in bad_tags and (targets & bad_tags):
                bad_tags.add(ftag)
                changed = True
    all_tags = sorted({f.tag for f in entry.funcs})
    if not bad_tags:
        return "clean", all_tags
    if any(t in bad_tags for t in RENDER_TAGS):       # can't even render faithfully -> hand back to author
        return "refuse", []
    return "init_only", [t for t in all_tags if t not in bad_tags]


def scan_objects(eb_bytes) -> list:
    """Persistent NPCs/props a real field places, for a FAITHFUL fork. Returns a list of
    ``{kind: "npc"|"prop", model, model_id, animset, pose, x, z, face, talkable, slot}``.

    FF9 spawns an object with ``InitObject(slot)`` in Main_Init (entry 0, tag 0); the object's own Init
    (tag 0) does ``SetModel`` + ``SetStandAnimation`` + a placement. We walk Main_Init in order, tracking
    the D9 position vars (``SetVar D9(0/2/4)=const``) so each ``InitObject`` records the (x,z) in force;
    then read each spawned object's Init. Placement = a LITERAL ``MoveInstantXZY(worldX,-worldY,worldZ)``
    if present, else the tracked D9 (x,z). One entry InitObject'd N times yields N instances (a row of
    boxes). SKIPPED: the player (``DefinePlayerCharacter``) and ``GEO_MAIN`` models (the party) -- and
    CUTSCENE actors fall out naturally (they have neither a literal ``MoveInstantXZY`` nor a tracked D9
    placement; they position by expression). Objects loaded HIDDEN -- ``SetObjectFlags`` without the
    show-model bit (1) -- are also skipped: those are SCRIPT-driven (a save point's moogle/book/tent, an
    event prop), shown/animated by the field script, NOT static set-dressing (carrying them places the
    machinery wrong, e.g. an always-deployed tent). A talkable object (tag 3) -> ``"npc"``; else ->
    ``"prop"``. The model + pose + placement ARE carried; dialogue TEXT is NOT (author it on the fork)."""
    from ._modeldb import MODELS                  # local: only import needs the model-name table
    eb = EbScript.from_bytes(eb_bytes)
    e0 = next((e for e in eb.entries if not e.empty and e.index == 0), None)
    f0 = e0.func_by_tag(0) if e0 else None
    if f0 is None:
        return []

    # 1) walk Main_Init: track D9(idx)=const, record each InitObject(slot) at the current (x,z)
    d9: dict = {}
    instances = []                               # (slot, x_or_None, z_or_None)
    for ins in eb.instrs(f0):
        if ins.op == SETVAR_EXPR_OP:
            raw = eb.data[ins.off:ins.off + 8]
            if len(raw) >= 6 and raw[1] == POS_VAR_CLASS and raw[3] == 0x7D:
                d9[raw[2]] = _s16(raw[4] | (raw[5] << 8))
        elif ins.op == INIT_OBJECT_OP and ins.args:
            instances.append((int(ins.args[0]), d9.get(0), d9.get(4)))
    slot_count: dict = {}
    for s, _x, _z in instances:
        slot_count[s] = slot_count.get(s, 0) + 1

    # 2) read each spawned object's Init
    out = []
    for slot, dx, dz in instances:
        if not 0 <= slot < eb.entry_count:
            continue
        e = eb.entry(slot)
        fi = e.func_by_tag(0) if not e.empty else None
        if fi is None:
            continue
        rd = _read_object_init(eb, fi)
        model, animset, pose, face = rd["model"], rd["animset"], rd["pose"], rd["face"]
        lit, local, flags, player = rd["lit"], rd["local"], rd["flags"], rd["player"]
        if player or model is None:
            continue
        if flags is not None and not (flags & SHOW_MODEL_BIT):
            continue                                  # loaded HIDDEN -> shown/animated by SCRIPT (a save
            #                                           point, an event prop), NOT static set-dressing
        name = MODELS.get(model)
        if name and name.startswith("GEO_MAIN"):     # the party -- not set-dressing
            continue
        if lit is not None:                          # a literal MoveInstantXZY -- the real props
            x, z = lit
        elif 0 in local and 4 in local and slot_count[slot] == 1:   # the object set its OWN single position
            x, z = local[0], local[4]                # (a kit-injected prop, or a single real D9-positioned one)
        elif dx is not None and dz is not None:      # position carried in Main_Init's D9 before InitObject
            x, z = dx, dz
        else:
            continue                                 # no STATIC placement (cutscene actor / arg-instanced) -> skip
        out.append({"kind": "npc" if e.func_by_tag(3) is not None else "prop",
                    "model": name or model, "model_id": model, "animset": animset, "pose": pose,
                    "x": int(x), "z": int(z), "face": face,
                    "talkable": e.func_by_tag(3) is not None, "slot": slot})
    return out


def scan_objects_verbatim(eb_bytes, *, fork_player_tags=FORK_PLAYER_TAGS, graft_player_funcs=False,
                          carry_text=False, graft_seq_helpers=False) -> list:
    """Graft specs for a FAITHFUL fork: each persistent object's VERBATIM ``.eb`` entry plus the data
    needed to append it at a free slot, arm it, and remap its references -- the faithful counterpart of
    :func:`scan_objects` (which emits human-authored ``[[npc]]``/``[[prop]]`` stubs). Where scan_objects
    returns the DECODED facts (model/pose/pos), this carries the RAW entry bytes so the object renders
    byte-identical to the real field (no player-clone lossiness), with the cross-reference classification
    that decides the carry (docs/OBJECT_CARRY.md). The FULL entry bytes are ALWAYS carried (non-
    destructive), so a later 'graft the donor player scripts' pass can light up the deferred tags.

    Skips the same non-set-dressing objects as scan_objects (player / ``GEO_MAIN`` party / script-hidden)
    AND adds the player-entry-index guard ``scan_jumps`` uses. One dict per carried object (grouped by
    donor slot):
      ``donor_idx, entry_bytes, kind, model, model_id, animset, pose, face, instances[{arg,x,z}],
      self_positions, needs_d9{idx:val}, donor_player_entry, donor_player_entries, refs[...],
      player_tags_needed[...], graft_safety("clean"|"init_only"|"refuse"), carry_tags[...], seqs[...]``.

    ``graft_seq_helpers`` (docs/OBJECT_CARRY.md S2 v1.5): when on, an object whose only blocker is an
    uncarried but BENIGN ``STARTSEQ`` (RunSharedScript) helper entry is un-refused -- the closure carries the
    helper too (``seqs``: one ``{entry, bytes}`` per distinct closeable helper the object launches from a kept
    tag) and ``build`` appends + remaps it like the ladder ``sequences`` graft. OFF by default -> byte-identical.
    """
    from ._modeldb import MODELS
    eb = EbScript.from_bytes(eb_bytes)
    pents = resolve_player_entries(eb)           # ALL DefinePlayerCharacter entries (182 fields define >1)
    dpe = pents[0] if pents else None            # the primary, kept for the sidecar/grafter back-compat
    e0 = next((e for e in eb.entries if not e.empty and e.index == 0), None)
    f0 = e0.func_by_tag(0) if e0 else None
    if f0 is None:
        return []

    # 1) walk Main_Init: each InitObject records the D9 position snapshot in force + its instancing arg
    d9: dict = {}
    grouped: dict = {}
    order = []
    for ins in eb.instrs(f0):
        if ins.op == SETVAR_EXPR_OP:
            raw = eb.data[ins.off:ins.off + 8]
            if len(raw) >= 6 and raw[1] == POS_VAR_CLASS and raw[3] == 0x7D:
                d9[raw[2]] = _s16(raw[4] | (raw[5] << 8))
        elif ins.op == INIT_OBJECT_OP and ins.args and isinstance(ins.args[0], int):
            slot = int(ins.args[0])
            arg = int(ins.args[1]) if len(ins.args) >= 2 and isinstance(ins.args[1], int) else 0
            if slot not in grouped:
                grouped[slot] = []
                order.append(slot)
            grouped[slot].append((arg, dict(d9)))
    slot_count = {s: len(v) for s, v in grouped.items()}

    # 2) which slots are actually carried (apply the skip rules first, so sibling refs classify right)
    info: dict = {}
    for slot in order:
        if not 0 <= slot < eb.entry_count or slot in pents:      # player-entry guard (every PC, as scan_jumps does)
            continue
        e = eb.entry(slot)
        fi = e.func_by_tag(0) if not e.empty else None
        if fi is None:
            continue
        rd = _read_object_init(eb, fi)
        if rd["player"] or rd["model"] is None:
            continue
        if rd["flags"] is not None and not (rd["flags"] & SHOW_MODEL_BIT):
            continue                                             # script-hidden (save machinery / event)
        name = MODELS.get(rd["model"])
        if name and name.startswith("GEO_MAIN"):                 # the party -- not set-dressing
            continue
        info[slot] = rd
    carried = set(info)

    # the player funcs the player-function graft WILL carry (docs/PLAYER_GRAFT.md): those tags become SAFE,
    # flipping an object from init_only to whole-entry. OFF by default (byte-identical). scan_player_funcs
    # calls scan_objects_verbatim WITHOUT this flag, so there is no recursion. ``carry_text`` ALSO admits a
    # "text" player func (its window TXID is carried + remapped by content.textcarry, so its bytes are
    # graft-safe once the text ships) -- so the seeding object carries its interactive tag whole.
    graftable_player = frozenset()
    if graft_player_funcs:
        ok = {"clean", "text"} if carry_text else {"clean"}
        graftable_player = frozenset(p["donor_tag"] for p in scan_player_funcs(eb_bytes) if p["safety"] in ok)

    # the BENIGN STARTSEQ helpers the closure carries (docs/OBJECT_CARRY.md S2 v1.5): every uncarried entry a
    # carried object launches via STARTSEQ that passes the body vet. OFF by default (byte-identical). These make
    # a STARTSEQ ref SAFE in _graft_safety, flipping an object refuse->graftable / init_only->whole-entry.
    seq_closeable = frozenset()
    if graft_seq_helpers:
        cand = set()
        for slot in carried:
            for f in eb.entry(slot).funcs:
                for ins in eb.instrs(f):
                    if ins.op == RUN_SHARED_SCRIPT and ins.args and isinstance(ins.args[0], int):
                        ei = int(ins.args[0])
                        if ei not in carried:                # a carried sibling already resolves; vet the rest
                            cand.add(ei)
        seq_closeable = frozenset(ei for ei in cand if _seq_helper_safe(eb, ei))

    # 3) build a graft spec per carried object
    out = []
    for slot in order:
        if slot not in info:
            continue
        rd = info[slot]
        e = eb.entry(slot)
        insts = grouped[slot]
        self_positions = rd["lit"] is not None or (0 in rd["local"] and 4 in rd["local"] and slot_count[slot] == 1)
        instances = []
        for arg, snap in insts:
            if rd["lit"] is not None:
                x, z = rd["lit"]
            elif 0 in rd["local"] and 4 in rd["local"] and slot_count[slot] == 1:
                x, z = rd["local"][0], rd["local"][4]
            elif 0 in snap and 4 in snap:
                x, z = snap[0], snap[4]
            else:
                x, z = None, None
            instances.append({"arg": arg, "x": x, "z": z})
        needs_d9: dict = {}
        if not self_positions:                                   # Main_Init-D9-positioned (the moogle class)
            snap0 = insts[0][1]
            needs_d9 = {i: snap0[i] for i in (0, 2, 4) if i in snap0}
        refs, player_tags = _classify_entry_refs(eb, e, pents, carried, slot)
        safety, carry_tags = _graft_safety(e, refs, fork_player_tags, graftable_player_tags=graftable_player,
                                           seq_closeable=seq_closeable)
        spec = {
            "donor_idx": slot,
            "entry_bytes": _entry_bytes(eb.data, slot),          # VERBATIM (full entry, all tags)
            "kind": "npc" if e.func_by_tag(3) is not None else "prop",
            "model": MODELS.get(rd["model"], rd["model"]), "model_id": rd["model"],
            "animset": rd["animset"], "pose": rd["pose"], "face": rd["face"],
            "instances": instances, "self_positions": self_positions, "needs_d9": needs_d9,
            "donor_player_entry": dpe, "donor_player_entries": pents,
            "refs": refs, "player_tags_needed": sorted(player_tags),
            "graft_safety": safety, "carry_tags": carry_tags,
        }
        if seq_closeable:                                        # the closeable helpers this object launches
            keep = set(carry_tags)                               # from a KEPT tag (a dropped tag's Seq never runs)
            seqs, seen = [], set()
            for f in e.funcs:
                if f.tag not in keep:
                    continue
                for ins in eb.instrs(f):
                    if ins.op == RUN_SHARED_SCRIPT and ins.args and isinstance(ins.args[0], int):
                        ei = int(ins.args[0])
                        if ei in seq_closeable and ei not in seen:
                            seen.add(ei)
                            seqs.append({"entry": ei, "bytes": _entry_bytes(eb.data, ei)})
            if seqs:
                spec["seqs"] = seqs
        out.append(spec)
    return out


def resolve_player_entries(eb) -> list:
    """Every entry index that defines a player character (``DefinePlayerCharacter`` 0x2C). A field can have
    MORE THAN ONE (fields 820/108/316-319/332/...); :func:`_player_entry_index` returns only the FIRST, which
    misses a referenced func defined on a later player entry."""
    return [e.index for e in eb.entries if not e.empty
            and any(ins.op == DEFINE_PC for f in e.funcs for ins in eb.instrs(f))]


def _player_model(eb, player_entry_index):
    """The model id the player entry's Init ``SetModel``s (the donor player rig), or None."""
    fi = eb.entry(player_entry_index).func_by_tag(0) if 0 <= player_entry_index < eb.entry_count else None
    return _read_object_init(eb, fi)["model"] if fi is not None else None


def _player_init_packs(eb, player_entries) -> list:
    """The animation-pack loads (``RunModelCode``) in the player Init(s). The fork player loads only the
    blank-field default pack, so a grafted func that plays a clip from one of these donor packs needs the
    pack spliced into the fork player Init (else the clip is silently unloaded -- docs/PLAYER_GRAFT.md S4)."""
    packs = []
    for pe in player_entries:
        fi = eb.entry(pe).func_by_tag(0)
        if fi is None:
            continue
        for ins in eb.instrs(fi):
            if ins.op == RUN_MODEL_CODE_OP and ins.args and not any(ins.arg_is_expr):
                t = tuple(int(a) for a in ins.args)
                if t not in packs:
                    packs.append(t)
    return packs


def _player_func_safety(eb, func, donor_model, donor_player_entry):
    """Classify a referenced player function for graftability (docs/PLAYER_GRAFT.md S2). Returns
    ``(safety, runscript_tags)`` -- safety in clean | text | sibling | transitive | model | exotic | missing.
    Only ``clean`` is v1-graftable; the rest keep the seeding object ``init_only`` (lint-warned)."""
    if func is None:
        return "missing", []
    ops, rs_tags, sibling = set(), [], False
    for ins in eb.instrs(func):
        ops.add(ins.op)
        spec = REF_OPS.get(ins.op)
        if spec:
            for ai in spec.get("uid", ()):
                if ai >= len(ins.arg_is_expr) or ins.arg_is_expr[ai]:
                    continue
                v = ins.imm(ai)
                if v is None or (ins.op in INIT_OPS and v == 0):
                    continue
                if v in (UID_PLAYER, UID_SELF) or (donor_player_entry is not None and v == donor_player_entry):
                    if ins.op in RUNSCRIPT_OPS and ai == 1:
                        t = ins.imm(2)
                        if t is not None:
                            rs_tags.append(int(t))        # a player->player call (transitive; depth-0 in practice)
                else:
                    sibling = True                        # a sibling / party / uncarried uid ref
    if ops & TEXT_OPS:
        return "text", rs_tags                            # needs a .mes the fork doesn't carry -> v1.5
    if sibling:
        return "sibling", rs_tags                         # references another object -> can't resolve on a fork
    if rs_tags:
        return "transitive", rs_tags                      # depth-0 census -> v1 refuses (no closure walker)
    if (ops & ANIM_OPS) and donor_model not in ZIDANE_MODELS:
        return "model", rs_tags                           # clip ids are another character's -> wrong on Zidane
    if ops - SAFE_GESTURE_OPS:
        return "exotic", rs_tags                          # warp / camera / scripted-walk / menu / sound / give
    return "clean", rs_tags


def scan_player_funcs(eb_bytes) -> list:
    """The donor PLAYER functions a fork must graft so its carried objects' INTERACTIONS fire -- the tags an
    object's interactive func ``RunScript``s (the object scanner's ``player_tags_needed``). One spec per needed
    tag: ``{donor_tag, safety, body (verbatim), runscript_tags, donor_player_entry, donor_player_model,
    donor_init_packs}``. ``safety == "clean"`` is v1-graftable (grafted onto the fork player via
    ``edit.add_function`` at a fresh tag); the rest keep the seeding object ``init_only``. The donor tag is
    later remapped to a fresh fork-player tag (docs/PLAYER_GRAFT.md)."""
    eb = EbScript.from_bytes(eb_bytes)
    specs = scan_objects_verbatim(eb_bytes)
    needed = sorted({t for s in specs for t in s["player_tags_needed"]})
    if not needed:
        return []
    pents = resolve_player_entries(eb)
    if not pents:
        return []
    model = _player_model(eb, pents[0])
    packs = _player_init_packs(eb, pents)
    out = []
    for tag in needed:
        func = pe = None
        for p in pents:
            func = eb.entry(p).func_by_tag(tag)
            if func is not None:
                pe = p
                break
        safety, rs_tags = _player_func_safety(eb, func, model, pe)
        out.append({"donor_tag": tag, "safety": safety,
                    "body": eb.data[func.abs_start:func.abs_end] if func is not None else b"",
                    "runscript_tags": rs_tags, "donor_player_entry": pe,
                    "donor_player_model": model, "donor_init_packs": packs})
    return out


def scan_content(eb_bytes) -> dict:
    """All importable content from a field's ``.eb`` in one pass: ``{gateways, music, encounter,
    control_direction, ladders, jumps, objects, objects_verbatim}`` (inverse of the injectors)."""
    return {
        "gateways": scan_gateways(eb_bytes),
        "music": scan_music(eb_bytes),
        "encounter": scan_encounter(eb_bytes),
        "control_direction": scan_control_direction(eb_bytes),
        "ladders": scan_ladders(eb_bytes),
        "jumps": scan_jumps(eb_bytes),
        "objects": scan_objects(eb_bytes),
        # the STARTSEQ-helper closure (docs/OBJECT_CARRY.md S2 v1.5) is a pure fidelity win for the import
        # carry, so the import-content aggregator scans WITH it (the default `import` path reads this).
        "objects_verbatim": scan_objects_verbatim(eb_bytes, graft_seq_helpers=True),
    }


def _entry_has_region(eb, entry) -> bool:
    """True if any function in ``entry`` contains a ``SetRegion`` (so its ``Field`` ops are walk-in)."""
    for f in entry.funcs:
        for ins in eb.instrs(f):
            if ins.op == SETREGION_OP:
                return True
    return False


def _classify_trigger(entry_index: int, tag: int) -> str:
    """Cheap classification of a scripted warp from its host entry/tag (grounded in the real-bytes
    survey): Main_Init -> auto-on-entry; tag 10 -> after-battle reinit; tag 1 -> cutscene/sequence loop."""
    if entry_index == 0 and tag == 0:
        return "auto-on-entry"
    if tag == 10:
        return "after-battle"
    if tag == 1:
        return "cutscene-loop"
    return "scripted"


def scan_all_warps(eb_bytes) -> dict:
    """Every field-to-field connection in the script, classified by KIND -- the import-chain taxonomy.
    Returns ``{walk_in, scripted, overworld_exits}``:

      * ``walk_in``         -- a ``SetRegion``+``Field`` region exit (from :func:`scan_gateways`); the
        player walks into a zone. Each carries the extra ``story_conditional`` flag: True when >=2
        edges share a BYTE-IDENTICAL zone polygon but reach DIFFERENT destinations -- FF9's stacked /
        ``if(flag){A}else{B}`` story-conditional door (only one active per story state; re-author with
        ``requires_flag`` on each). ~2.9% of real region exits; the rest are plain unconditional doors.
      * ``scripted``        -- ``[{to, entrance, host_entry, host_tag, trigger}]`` for a bare ``Field()``
        whose entry has NO region (cutscene / teleport / post-battle warp). Target + entrance are
        literals (FF9 never computes a warp id). ~41% of real connectivity is scripted, so the strict
        walk-in scan alone misses a lot -- but these are predominantly one-way story transitions, so a
        walk should treat them as seams by default, not auto-followed.
      * ``overworld_exits`` -- sorted ``WorldMap`` (0xB6) operands: WORLD-MAP LOCATION ids (e.g.
        9000-9012), NOT field ids. A 'this screen leaves to the overworld' marker, never a graph edge.

    Shared chocobo/mognet menu warps (2950-2955) are filtered out (they appear in nearly every field).
    Field ops in a region-bearing entry are attributed to ``walk_in`` (matching :func:`scan_gateways`)."""
    eb = EbScript.from_bytes(eb_bytes)

    walk_in = scan_gateways(eb_bytes)
    by_zone: dict = {}
    for g in walk_in:
        by_zone.setdefault(tuple(map(tuple, g["zone"])), set()).add(g["to"])
    for g in walk_in:
        g["story_conditional"] = len(by_zone[tuple(map(tuple, g["zone"]))]) > 1

    scripted, overworld = [], []
    for e in eb.entries:
        if e.empty:
            continue
        region_entry = _entry_has_region(eb, e)
        for f in e.funcs:
            entrance = 0
            for ins in eb.instrs(f):
                if ins.op == 0x05:
                    ent = _entrance_at(eb.data, ins.off)
                    if ent is not None:
                        entrance = ent
                elif ins.op == WORLDMAP_OP:
                    loc = ins.imm(0)
                    if loc is not None:
                        overworld.append(int(loc))
                elif ins.op == FIELD_OP and not region_entry:
                    tgt = ins.imm(0)
                    if tgt is None or int(tgt) in SHARED_MENU_WARPS:
                        continue
                    scripted.append({"to": int(tgt), "entrance": int(entrance),
                                     "host_entry": e.index, "host_tag": int(f.tag),
                                     "trigger": _classify_trigger(e.index, f.tag)})
    return {"walk_in": walk_in, "scripted": scripted, "overworld_exits": sorted(set(overworld))}


# --- GLOB story-flag scanners (cross-field flag dependencies; raw-byte, like _entrance_at) ---
# Filters to GLOBAL bools (save-persistent gEventGlobal). MAP bools (0xC5/0xE5) are per-field TRANSIENT
# -> never a cross-field dependency, so _glob_var_token returns None for them.
GLOB_BOOL_SHORT = 0xC4    # Global+Bit, idx <= 0xFF (1-byte index)
GLOB_BOOL_LONG = 0xE4     # Global+Bit, long-index form (class | 0x20) for idx > 0xFF (2-byte LE)
_PUSH_CONST16 = 0x7D
_T_ASSIGN = 0x2C
_T_OR_ASSIGN = 0x3F
_T_NOT = 0x0E
_T_END = 0x7F
_JMP_FALSE = 0x02
_JMP_TRUE = 0x03
_RETURN = 0x04            # eb/opcodes.RETURN == bytes([0x04])


def _glob_var_token(data: bytes, off: int):
    """If ``data[off]`` is a GLOBAL bool var token, return ``(glob_idx, token_len)``; else None.
    0xC4 -> (data[off+1], 2);  0xE4 -> (u16le, 3). MAP bools (0xC5/0xE5) and everything else -> None."""
    if off >= len(data):
        return None
    b = data[off]
    if b == GLOB_BOOL_SHORT and off + 1 < len(data):
        return (data[off + 1], 2)
    if b == GLOB_BOOL_LONG and off + 2 < len(data):
        return (data[off + 1] | (data[off + 2] << 8), 3)
    return None


def _expr_offsets(eb):
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == 0x05:            # EXPR statement -> the byte after is the var token
                    yield ins.off


def scan_flags_set(eb_bytes) -> list:
    """GLOB flag WRITES. Pattern ``05 <glob-var> 7D <i16> <2C|3F> 7F`` (set / or-assign). Returns
    sorted-unique ``[(glob_idx, op)]`` with op in {'set', 'or'}. Round-trips region.set_var/or_var."""
    eb = EbScript.from_bytes(eb_bytes)
    d = eb.data
    out = set()
    for off in _expr_offsets(eb):
        tok = _glob_var_token(d, off + 1)
        if tok is None:
            continue
        idx, vlen = tok
        p = off + 1 + vlen
        if p + 4 < len(d) and d[p] == _PUSH_CONST16 and d[p + 3] in (_T_ASSIGN, _T_OR_ASSIGN) and d[p + 4] == _T_END:
            out.add((idx, "set" if d[p + 3] == _T_ASSIGN else "or"))
    return sorted(out)


def scan_required_flags(eb_bytes) -> list:
    """GLOB flag READS that drive a conditional jump (general if-block, ANY body length). Pattern
    ``05 <glob-var> [0E] 7F <02|03> <skip:i16> ...``. Returns sorted-unique ``[(glob_idx, require_set)]``
    (require_set = the flag state that lets the guarded block run). Catches region.flag_gate as a special case."""
    eb = EbScript.from_bytes(eb_bytes)
    d = eb.data
    out = set()
    for off in _expr_offsets(eb):
        tok = _glob_var_token(d, off + 1)
        if tok is None:
            continue
        idx, vlen = tok
        p = off + 1 + vlen
        negated = p < len(d) and d[p] == _T_NOT
        if negated:
            p += 1
        if p + 1 >= len(d) or d[p] != _T_END:
            continue
        jmp = d[p + 1]
        if jmp not in (_JMP_FALSE, _JMP_TRUE):
            continue
        require_set = (jmp == _JMP_TRUE and not negated) or (jmp == _JMP_FALSE and negated)
        out.add((idx, require_set))
    return sorted(out)


def scan_edge_flag_gates(eb_bytes) -> list:
    """STRICT kit-prologue gate ``05 <glob-var> 7F <02|03> 01 00 04`` (skip=1 + RETURN=0x04) -- the exact
    shape region.flag_gate emits. Returns ``[(glob_idx, require_set)]``. (Use scan_required_flags for the
    general real-field form; this is the round-trip self-test target.)"""
    eb = EbScript.from_bytes(eb_bytes)
    d = eb.data
    out = set()
    for off in _expr_offsets(eb):
        tok = _glob_var_token(d, off + 1)
        if tok is None:
            continue
        idx, vlen = tok
        p = off + 1 + vlen
        if (p + 4 < len(d) and d[p] == _T_END and d[p + 1] in (_JMP_FALSE, _JMP_TRUE)
                and d[p + 2] == 0x01 and d[p + 3] == 0x00 and d[p + 4] == _RETURN):
            out.add((idx, d[p + 1] == _JMP_TRUE))
    return sorted(out)
