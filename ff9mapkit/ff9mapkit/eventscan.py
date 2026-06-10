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
# An arc with a message WINDOW or a mid-arc BATTLE is an INTERACTIVE sequence, NOT a clean navigable
# hop: it's the Cleyra/Tree-Trunk SAND TRAP (fall in -> a "press X!" window + a button-mash struggle
# counter + camera sink + sometimes a Battle -> escape arcs) or a scripted cutscene hop. These reuse
# SetupJump/Jump for the fall/escape, so they look like jumps by opcode but aren't player navigation --
# and they carry field-specific text/battle ids that don't port to a fork. Excluded from scan_jumps.
WINDOW_OPS = frozenset((0x1F, 0x20, 0x95, 0x96))   # WindowSync / WindowAsync / WindowSyncEx / WindowAsyncEx
BATTLE_OP = 0x2A           # Battle(type, scene) -- a forced encounter (sand traps can spawn one mid-struggle)
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
    is NOT a ladder (no ladder flag) AND NOT an interactive sequence (no message Window / mid-arc
    Battle). The window/battle exclusion is what separates an Ice-Cavern-style ledge HOP (a silent arc)
    from a Cleyra/Tree-Trunk SAND TRAP or a scripted cutscene hop (both reuse SetupJump/Jump but wrap
    them in a 'press X!' struggle + dialogue/battle the kit can't port)."""
    ops, ladder = _func_ops(eb, player_index, tag)
    if ops is None or ladder or SETUP_JUMP not in ops or JUMP_OP not in ops:
        return False
    if ops & WINDOW_OPS or BATTLE_OP in ops:        # an interactive trap/cutscene, not a clean hop
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


def scan_content(eb_bytes) -> dict:
    """All importable content from a field's ``.eb`` in one pass:
    ``{gateways, music, encounter, control_direction, ladders, jumps}`` (inverse of the injectors)."""
    return {
        "gateways": scan_gateways(eb_bytes),
        "music": scan_music(eb_bytes),
        "encounter": scan_encounter(eb_bytes),
        "control_direction": scan_control_direction(eb_bytes),
        "ladders": scan_ladders(eb_bytes),
        "jumps": scan_jumps(eb_bytes),
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
