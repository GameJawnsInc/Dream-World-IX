"""THE s140 BENCH FIELD's contract -- field 30606 SELFDRESS (studies/battle-coop/bench/selfdress.field.toml), importable.

R3 group 2's legs N / X / T (studies/battle-coop/R3-FIELD-MODEL-AUDIT.md 4.1 and 4.4; s141's F8 rides it too) run on a
kit field whose .eb is the kit's build of the toml PLUS a seat step (studies/battle-coop/bench/selfdress_bench.py): the
toml builds the player, the TWIN and the LATE entry with the kit's own blocks; the seat adds the CALLER (a code entry
of conductors), the T3 function inside the PLAYER's entry, and DefinePlayerCharacter in a never-run function of the
LATE entry. This module is the ONE home of the numbers both sides share -- the sids, the flag indices, the conductor
operands --, of the two seated bodies (:func:`t3_body`, :func:`caller_body`: the seat writes them, the preflight compares
the deployed bytes to them), and of :func:`preflight`, which re-checks the .eb the bench reads from the DEPLOYED mod folder at run time
and FAILS CLOSED: it returns a reason string unless every row holds (None = clean). Nothing here writes the install
or touches the game: :func:`deployed_eb` only reads the mod folders, and every other function is pure over the bytes
it is handed.

THE ENTRIES (sid == uid: every InitObject / InitCode here passes uid 0, which is the slot).
    PLAYER_SID 1  the kit Zidane player: SetModel(98, 93) + DefinePlayerCharacter in its Init (tag 0); the seat adds
                  T3_TAG, the field-2705 loop. B_FRAME (GetAnimDuration) evaluates on gCur, the RUNNING object
                  (EventEngine.DoCalcOperationExt.cs:24-26), so the loop must run as a function of THIS entry. The
                  seat also adds J_TAG, field 404's ladder jump (SetJumpAnimation / RunJumpAnimation / RunLandAnimation
                  act on the running object too).
    TWIN_SID 2    a Zidane [[npc]] (SetModel(98, 93)), NO DefinePlayerCharacter anywhere in its entry, activated
                  behind `requires_flag_clear = TWIN_GATE` -- a guarded call, so the kit's activate_block inserts it
                  at Main_Init's START: its InitObject precedes the player's (THE MAIN_INIT_ORDER ROW). Identify it by
                  this sid, never by model (s140's N2 dresses it).
    LATE_SID 3    a second Zidane [[npc]] whose load-time InitObject is guarded by `requires_flag = LATE_GATE` (set by
                  nothing, so it never inits at load); the caller's N3 conductor InitObjects it AFTER the player's CC
                  has run. The seat adds LATE_CC_TAG = [DefinePlayerCharacter, RET] -- a function nothing calls, so
                  EntryDefinesPlayer reads true while control never moves (audit 2.3 amendment 11).
    CUP_SID 4     a kit [[prop]] cup (GEO_ACC_F0_CUP, model 234): s141's F8 attach target.
    CALLER_SID 5  a seated code entry (type 0, one tag-0 loop, LOC Instance bytes), armed by InitCode right AFTER the
                  player's InitObject. It polls the TRIG_* bits each tick and runs one conductor per trigger.

THE FLAG PROTOCOL (gEventGlobal bits in the safe band, declared as [[flag]] rows in the toml so the kit's lint and
allocator see them; nothing else in the repo uses 13200-13239). The harness writes bits with `flag <bit> <0|1>` and
reads them with `watch`.
    1. Before warping in: clear READY. The caller's Init zeroes every IO_BITS bit (fresh per load), then sets READY.
    2. Set ONE TRIG_* bit. The caller clears it first, runs the conductor, then sets its DONE_* bit -- or WEDGED_T1 /
       WEDGED_T3 / WEDGED_J when the bounded wait times out (a red the bench can read without a softlock: X/T1/T3/J
       hold control off with DisableMove only while they run, and every exit path gives it back with EnableMove --
       the preflight's ESCAPE rows pin every WEDGED / DONE write, every bound and the EnableMove count).
    3. T3 also publishes the player function's own phase: T3_LOOP (it entered the 2705 while-loop) and T3_END (it got
       past the loop and restored the player's stand/walk/run ids). On a WEDGED_T3 the player's level-2 function is
       still walking in place: warp to recover (a field load discards it). Until that warp, a second T3 BLOCKS the
       caller in RunScript (the player's script level stays 2), so read WEDGED_T3 as the end of the field's run.
    TWIN_GATE and LATE_GATE must read 0 for the whole run (nothing sets them).
    EXPOSURE: 13200-13239 sit in flags.py's CAMPAIGN LANE ([FIRST_SAFE_FLAG, KIT_STANDING_FLOOR): the live opening
    campaign's per-member windows, baked into a real save). The caller WRITES them on every load of 30606 (READY = 1,
    every IO bit 0) -- harmless on the harness's own newgame, but never enter 30606 from a real opening-campaign save
    (the same bench-grade exposure the actor-shadow and fight-ledger benches carry).

THE CONDUCTORS (each op copied from a stock field that runs it; `selfdress_bench.py build` prints them beside the
install's own bytes, read-only):
    X   RunAnimationEx(250, 186 ZDN BREAK1_LOOK, 70 frames) + WaitAnimationEx(250)
        -- field 554 Lindblum Inn Main_Loop: RunAnimationEx(12, 186) / WaitAnimationEx(12) on its player entry 12.
    T1  RunAnimationEx(250, 2572 ZDN COLD_FAINT_1, 70 frames), then `while GetEntryAnimFrame(250) < 58 { Wait(1) }`
        (bounded: T1_LIMIT ticks -> WEDGED_T1), then WaitAnimationEx(250)
        -- field 307's `< 58` after RunAnimation(2572) (test2_87.txt:1557-1562); the conductor-side
        GetEntryAnimFrame(250) wait is field 612's (test2_167.txt:364).
    T3  RunScript(2, 250, T3_TAG) -- 2705's own call form (`RunScript( 2, 6, 25 )`, test2_708.txt:645) -- then poll
        T3_END; T3_LOOP_LIMIT ticks after T3_LOOP (or T3_TOTAL_LIMIT in all) -> WEDGED_T3. The player function:
        SetWalkAnimation(8847 FRA_WALK) SetStandAnimation(7922 FRA_IDLE) (test2_708.txt:1245-1246); InitWalk +
        Walk(T3_P1); SetWalkSpeed(7) InitWalk MakeAnimationLoop(40) Walk(T3_P2); T3_LOOP; then Zidane_25's loop
        verbatim with the walk target swapped (test2_708.txt:1264):
            while (GetEntryAnimFrame(255) < GetAnimDuration(8847) - 1) { InitWalk; MakeAnimationLoop(1); Walk(T3_P2) }
        then SetWalkSpeed(30) and the player's own stand/walk/run ids back; T3_END; RET. The lane T3_P1 -> T3_P2 is
        2000u at speed 7 (~286 ticks): a dressed walk that never reaches the bound is still walking when the caller's
        T3_LOOP_LIMIT runs out, so a wedge reads red instead of ending by the idle clip once the walk stops.
    N3  once per load (an Instance latch): Wait(1), InitObject(LATE_SID, 0), Wait(2), DONE_N3.
    J   RunScript(2, 250, J_TAG), then poll J_END (bounded: J_LIMIT ticks -> WEDGED_J). The player function is field
        404's ladder mount without its arc (test2_107.txt:1191-1199): SetJumpAnimation(10687 LADDER_1_1, 2, 6)
        RunJumpAnimation WaitAnimation, J_LAND, RunLandAnimation WaitAnimation, J_END, RET. Stock lands in
        8 - 1 - (6 + 1) = 0 ticks; a dressed body whose jump slot ran on the idle ALIAS's count (30-72 frames) would
        hold 22-64 ticks -- s140's KeepJumpTimeline keeps the SOURCE count (X3 judges the landing's frame_n and its
        duration between the J_LAND and J_END publishes).
    F8  (s141) attach: AttachObject(CUP_SID, 250, 13) -- stock's `AttachObject( 4, 13, 13 )` Gargan_Flower on Zidane --;
        detach: DetachObject(CUP_SID).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                                   # studies/test-harness/scenarios -> the checkout root

FIELD_ID = 30606
FIELD_NAME = "TEST30606"                 # deploy_field.py's forced sandbox name for --id 30606 (EVT_TEST30606)
MOD_FOLDER = "FF9CustomMap-msgs"
TOML = REPO / "studies" / "battle-coop" / "bench" / "selfdress.field.toml"
DEPLOY = ("py", "studies/battle-coop/bench/selfdress_bench.py", "deploy")

# ------------------------------------------------------------------------------------------------ the entries
PLAYER_SID, TWIN_SID, LATE_SID, CUP_SID, CALLER_SID = 1, 2, 3, 4, 5
SIDS = {"player": PLAYER_SID, "twin": TWIN_SID, "late": LATE_SID, "cup": CUP_SID, "caller": CALLER_SID}
CONTROL_UID = 250                        # the engine's slot-independent control alias (GetObjUID(250))
SELF_UID = 255
ZIDANE_MODEL, ZIDANE_ANIMSET = 98, 93    # SetModel(98, 93): po.eye = -372
CUP_MODEL = 234                          # GEO_ACC_F0_CUP
T3_TAG = 48                              # the player-entry function the seat adds (the 2705 loop)
LATE_CC_TAG = 49                         # the late entry's never-run DefinePlayerCharacter function
J_TAG = 50                               # the player-entry function the seat adds (field 404's ladder jump, no arc)
SCRIPT_LEVEL = 2                         # RunScript's level -- the stock cutscene idiom (2705: RunScript( 2, 6, 25 ))
CALLER_LOC = 6                           # Instance bytes: Int16[0] loop count, Int16[2] total count, Byte[4] N3 latch

# ------------------------------------------------------------------------------------------------ the conductors
ANIM_X = 186                             # ANH_MAIN_F0_ZDN_BREAK1_LOOK, 70 frames (p0data5, the kit's clip reader)
ANIM_X_FRAMES = 70
ANIM_T1 = 2572                           # ANH_MAIN_F0_ZDN_COLD_FAINT_1, 70 frames: a GESTURE (not a loco family)
ANIM_T1_FRAMES = 70
T1_THRESHOLD = 58                        # field 307's `GetEntryAnimFrame(255) < 58` after RunAnimation(2572)
T1_LIMIT = 150                           # ticks (5 s): 58 frames reach it in ~58 on the source timeline
ANIM_T3_WALK = 8847                      # ANH_MAIN_F0_ZDN_FRA_WALK, 40 frames -> 2705's bound 39
ANIM_T3_WALK_FRAMES = 40
ANIM_T3_STAND = 7922                     # ANH_MAIN_F0_ZDN_FRA_IDLE, 68 frames
T3_WALK_SPEED = 7                        # 2705 Zidane_25's SetWalkSpeed(7)
T3_RESTORE_SPEED = 30                    # Actor.cs's default speed (the controller re-stamps 30/60 under control)
T3_PRE_LOOP = 40                         # 2705's MakeAnimationLoop(40) before the while
T3_P1 = (-1000, -1700)                   # the lane's west end (walked to at the player's own speed first)
T3_P2 = (1000, -1700)                    # the lane's east end (2000u at speed 7 ~ 286 ticks)
T3_LOOP_LIMIT = 90                       # ticks after T3_LOOP: the law's worst case is one walk cycle (<= 40)
T3_TOTAL_LIMIT = 600                     # ticks after RunScript: the pre-loop walks never take this long
ATTACH_BONE = 13                         # stock's held-item bone on Zidane (s141 amendment 5)
ANIM_J = 10687                           # ANH_MAIN_F0_ZDN_LADDER_1_1, 8 frames (p0data5): a JUMP_LADDER id
ANIM_J_FRAMES = 8
J_JUMP0, J_JUMP1 = 2, 6                  # field 404's SetJumpAnimation(10687, 2, 6) (test2_107.txt:1191)
J_LIMIT = 120                            # ticks after RunScript: stock ends in ~3, an alias-timed landing in <= ~70
                                         # (never T1_LIMIT's 150: each bound's statement must be its own bytes)

# ------------------------------------------------------------------------------------------------ the flags
TWIN_GATE = 13200        # never set: the twin's InitObject requires it CLEAR (requires_flag_clear)
LATE_GATE = 13201        # never set: the late entry's load-time InitObject requires it SET (requires_flag)
READY = 13202            # the caller is up: its Init zeroed IO_BITS, then set this
TRIG_X, TRIG_T1, TRIG_T3, TRIG_N3, TRIG_F8A, TRIG_F8D = 13203, 13204, 13205, 13206, 13207, 13208
DONE_X, DONE_T1, DONE_T3, DONE_N3, DONE_F8A, DONE_F8D = 13209, 13210, 13211, 13212, 13213, 13214
WEDGED_T1, WEDGED_T3 = 13215, 13216
T3_LOOP, T3_END = 13217, 13218           # written by the PLAYER's T3 function (its phase), read by the caller
TRIG_J, DONE_J, WEDGED_J = 13219, 13220, 13221
J_LAND, J_END = 13222, 13223             # written by the PLAYER's J function: right before RunLandAnimation / after it
TRIGGERS = {"x": TRIG_X, "t1": TRIG_T1, "t3": TRIG_T3, "n3": TRIG_N3, "f8a": TRIG_F8A, "f8d": TRIG_F8D, "j": TRIG_J}
DONES = {"x": DONE_X, "t1": DONE_T1, "t3": DONE_T3, "n3": DONE_N3, "f8a": DONE_F8A, "f8d": DONE_F8D, "j": DONE_J}
WEDGES = {"t1": WEDGED_T1, "t3": WEDGED_T3, "j": WEDGED_J}
IO_BITS = tuple(TRIGGERS.values()) + tuple(DONES.values()) + tuple(WEDGES.values()) + (T3_LOOP, T3_END, J_LAND, J_END)
#: the toml's [[flag]] table, name -> index (the kit's lint + allocator see every bench bit through it)
TOML_FLAGS = {"sd_twin_gate": TWIN_GATE, "sd_late_gate": LATE_GATE, "sd_ready": READY,
              **{f"sd_trig_{k}": v for k, v in TRIGGERS.items()}, **{f"sd_done_{k}": v for k, v in DONES.items()},
              **{f"sd_wedged_{k}": v for k, v in WEDGES.items()}, "sd_t3_loop": T3_LOOP, "sd_t3_end": T3_END,
              "sd_j_land": J_LAND, "sd_j_end": J_END}
ALL_FLAGS = tuple(sorted(TOML_FLAGS.values()))

# ------------------------------------------------------------------------------------------------ opcodes
OP_JMP, OP_JMP_IFNOT, OP_JMP_IF, OP_RET, OP_EXPR = 0x01, 0x02, 0x03, 0x04, 0x05
OP_INIT_CODE, OP_INIT_OBJECT = 0x07, 0x09
OP_RUN_SCRIPT, OP_WAIT, OP_WALK, OP_INIT_WALK, OP_WALK_SPEED = 0x12, 0x22, 0x23, 0x25, 0x26
OP_DEFINE_PLAYER, OP_DISABLE_MOVE, OP_ENABLE_MOVE, OP_SET_MODEL = 0x2C, 0x2D, 0x2E, 0x2F
OP_STAND, OP_WALK_ANIM, OP_RUN_ANIM = 0x33, 0x34, 0x35
OP_ATTACH, OP_DETACH, OP_ANIM_LOOP, OP_RUN_ANIM_EX, OP_WAIT_ANIM_EX = 0x4C, 0x4D, 0x98, 0xBD, 0xBE
OP_WAIT_ANIM, OP_SET_JUMP, OP_RUN_JUMP, OP_RUN_LAND = 0x41, 0x94, 0x9C, 0x9D
CODE_ENTRY_TYPE = 0x00

#: 2705's loop bound, as the bytes of its expression statement (0x05 + tokens): GetEntryAnimFrame(255) <
#: GetAnimDuration(8847) - 1 -- obj(uid=255).f[7] const(8847) B_FRAME const(1) B_MINUS B_LT B_EXPR_END
T3_BOUND_STMT = bytes.fromhex("05 78 ff 07 7d 8f 22 6a 7d 01 00 15 18 7f")
#: T1's wait: GetEntryAnimFrame(250) < 58 -- obj(uid=250).f[7] const(58) B_LT B_EXPR_END
T1_WAIT_STMT = bytes([OP_EXPR, 0x78, CONTROL_UID, 0x07, 0x7D, T1_THRESHOLD, 0x00, 0x18, 0x7F])

_KIT = None


def _kit():
    """``ff9mapkit`` from THIS checkout (asserted), or raise naming where it resolved instead."""
    global _KIT
    if _KIT is not None:
        return _KIT
    pkg_root = REPO / "ff9mapkit"
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    import ff9mapkit                                       # noqa: E402 - path pinned above
    where = Path(getattr(ff9mapkit, "__file__", "") or ".").resolve()
    if not where.is_relative_to(pkg_root.resolve()):
        raise RuntimeError(f"ff9mapkit resolved to {where}, not this checkout's {pkg_root}")
    _KIT = ff9mapkit
    return ff9mapkit


def deployed_eb(game, lang: str = "us") -> tuple:
    """(bytes, where) of EVT_<FIELD_NAME> as the engine would load it -- the FIRST mod folder in Memoria.ini's
    FolderNames order that ships it (a stale copy in a higher folder wins over the bench's own) -- or (None, why).
    READ-ONLY."""
    _kit()
    from ff9mapkit import extract as X
    game = Path(game)
    rel = ("StreamingAssets", "assets", "resources", "commonasset", "eventengine", "eventbinary", "field", lang,
           f"EVT_{FIELD_NAME}.eb.bytes")
    folders = X._mod_folders(game)
    for folder in folders:
        p = game.joinpath(folder, *rel)
        if p.is_file():
            return p.read_bytes(), str(p.relative_to(game))
    return None, f"EVT_{FIELD_NAME}.eb.bytes ({lang}) is in none of {folders}: deploy with `{' '.join(DEPLOY)}`"


def _code(data: bytes, f) -> list:
    from ff9mapkit.eb import disasm
    return list(disasm.iter_code(data, f.abs_start, f.abs_end))


def _stmt(expr: str) -> bytes:
    """One expression STATEMENT (0x05 + the kit's assembled tokens) -- the seat's own form, so the preflight compares bytes."""
    _kit()
    from ff9mapkit.eb import exprasm, opcodes as O
    return O.encode(OP_EXPR, exprasm.assemble(expr + " B_EXPR_END"), arg_flags=0b1)


def glob_test(bit: int) -> bytes:
    """`Global.Bit[bit]` as a statement (a JMP_IF / JMP_IFNOT condition)."""
    return _stmt(f"Global.Bit[{bit}]")


def glob_set(bit: int, value: int) -> bytes:
    """`Global.Bit[bit] = value`."""
    return _stmt(f"Global.Bit[{bit}] const({value}) B_LET")


def int16_gt(slot: int, value: int) -> bytes:
    """`Instance.Int16[slot] > value` -- a bounded wait's escape test."""
    return _stmt(f"Instance.Int16[{slot}] const({value}) B_GT")


def int16_inc(slot: int) -> bytes:
    """`Instance.Int16[slot] = Instance.Int16[slot] + 1` -- a bounded wait's tick count."""
    return _stmt(f"Instance.Int16[{slot}] Instance.Int16[{slot}] const(1) B_PLUS B_LET")


def int16_set(slot: int, value: int) -> bytes:
    """`Instance.Int16[slot] = value`."""
    return _stmt(f"Instance.Int16[{slot}] const({value}) B_LET")


# ------------------------------------------------------------------------------------------------ the seated bodies
# THE ONE HOME of the two bodies the seat writes (selfdress_bench.py imports them): preflight compares the DEPLOYED T3
# function and caller to these byte for byte, exactly as J is compared to _expected_j() -- so a stale or hand-edited
# seat (a phase bit moved or dropped, another lane, another bound) reads a reason instead of a verdict the engine never
# earned. Position-independent: the kit's encoders and labelasm's relative jumps only.
def t3_body(stand: int, walk: int, run: int) -> bytes:
    """The player-entry function T3_TAG: field 2705's Zidane_23 setters + Zidane_25's walk-in and its while-loop, verbatim
    but for the walk targets (this field's lane), then the player's own ids back (``stand`` / ``walk`` / ``run``: the
    player Init's own immediates, :func:`player_ids`). Phase bits T3_LOOP / T3_END."""
    _kit()
    from ff9mapkit.eb import opcodes as O
    from ff9mapkit.eb.labelasm import JMP, JMP_IF, asm, label
    (x1, z1), (x2, z2) = T3_P1, T3_P2
    return asm([
        O.encode(OP_WALK_ANIM, ANIM_T3_WALK),                  # SetWalkAnimation(8847)   test2_708.txt:1245
        O.encode(OP_STAND, ANIM_T3_STAND),                     # SetStandAnimation(7922)  test2_708.txt:1246
        O.init_walk(), O.walk(x1, z1),                         # to the lane's west end, at the player's own speed
        O.set_walk_speed(T3_WALK_SPEED),                       # Zidane_25: SetWalkSpeed(7)
        O.init_walk(), O.encode(OP_ANIM_LOOP, T3_PRE_LOOP), O.walk(x2, z2),   # InitWalk MakeAnimationLoop(40) Walk
        glob_set(T3_LOOP, 1),
        (JMP, "cond"),                                         # Zidane_25's while, exactly as stock assembles it:
        label("body"),                                         #   JMP cond; body: InitWalk; MakeAnimationLoop(1); Walk
        O.init_walk(), O.encode(OP_ANIM_LOOP, 1), O.walk(x2, z2),
        label("cond"),                                         #   cond: GetEntryAnimFrame(255) < GetAnimDuration(8847) - 1
        T3_BOUND_STMT,
        (JMP_IF, "body"),
        O.set_walk_speed(T3_RESTORE_SPEED),
        O.encode(OP_STAND, stand), O.encode(OP_WALK_ANIM, walk), O.encode(OP_RUN_ANIM, run),
        glob_set(T3_END, 1),
        O.RETURN,
    ])


def caller_body() -> bytes:
    """The caller's one tag-0 loop: zero the bench bits, READY, then poll a trigger per tick and run its conductor.
    Instance.Int16[0] = the bounded wait's count, Int16[2] = T3's total count, Byte[4] = N3's once-per-load latch."""
    _kit()
    from ff9mapkit.eb import opcodes as O
    from ff9mapkit.eb.labelasm import JMP, JMP_IF, JMP_IFNOT, asm, label
    B = [glob_set(b, 0) for b in IO_BITS] + [glob_set(READY, 1), label("top")]
    for key in TRIGGERS:
        B += [glob_test(TRIGGERS[key]), (JMP_IF, f"do_{key}")]
    B += [O.wait(1), (JMP, "top")]
    # X -- field 554's Main_Loop form, on the control alias
    B += [label("do_x"), glob_set(TRIG_X, 0), O.DISABLE_MOVE,
          O.run_animation_ex(CONTROL_UID, ANIM_X), O.wait_animation_ex(CONTROL_UID),
          O.ENABLE_MOVE, glob_set(DONE_X, 1), (JMP, "top")]
    # T1 -- a gesture on the source timeline, then field 307's `< 58` frame wait (bounded)
    B += [label("do_t1"), glob_set(TRIG_T1, 0), O.DISABLE_MOVE,
          O.run_animation_ex(CONTROL_UID, ANIM_T1), int16_set(0, 0), (JMP, "t1_cond"),
          label("t1_body"), int16_inc(0), int16_gt(0, T1_LIMIT), (JMP_IF, "t1_wedged"), O.wait(1),
          label("t1_cond"), T1_WAIT_STMT, (JMP_IF, "t1_body"),
          O.wait_animation_ex(CONTROL_UID), O.ENABLE_MOVE, glob_set(DONE_T1, 1), (JMP, "top"),
          label("t1_wedged"), O.ENABLE_MOVE, glob_set(WEDGED_T1, 1), (JMP, "top")]
    # T3 -- 2705's call form into the PLAYER's own entry, then poll its phase bits (bounded)
    B += [label("do_t3"), glob_set(TRIG_T3, 0), glob_set(T3_LOOP, 0), glob_set(T3_END, 0), O.DISABLE_MOVE,
          O.run_script(SCRIPT_LEVEL, CONTROL_UID, T3_TAG), int16_set(0, 0), int16_set(2, 0),
          label("t3_poll"), glob_test(T3_END), (JMP_IF, "t3_ok"),
          int16_inc(2), int16_gt(2, T3_TOTAL_LIMIT), (JMP_IF, "t3_wedged"),
          glob_test(T3_LOOP), (JMP_IFNOT, "t3_wait"),
          int16_inc(0), int16_gt(0, T3_LOOP_LIMIT), (JMP_IF, "t3_wedged"),
          label("t3_wait"), O.wait(1), (JMP, "t3_poll"),
          label("t3_ok"), O.ENABLE_MOVE, glob_set(DONE_T3, 1), (JMP, "top"),
          label("t3_wedged"), O.ENABLE_MOVE, glob_set(WEDGED_T3, 1), (JMP, "top")]
    # J -- the jump slot on the SOURCE timeline: RunScript into the PLAYER's own J function, then poll J_END (bounded)
    B += [label("do_j"), glob_set(TRIG_J, 0), glob_set(J_LAND, 0), glob_set(J_END, 0), O.DISABLE_MOVE,
          O.run_script(SCRIPT_LEVEL, CONTROL_UID, J_TAG), int16_set(0, 0),
          label("j_poll"), glob_test(J_END), (JMP_IF, "j_ok"),
          int16_inc(0), int16_gt(0, J_LIMIT), (JMP_IF, "j_wedged"), O.wait(1), (JMP, "j_poll"),
          label("j_ok"), O.ENABLE_MOVE, glob_set(DONE_J, 1), (JMP, "top"),
          label("j_wedged"), O.ENABLE_MOVE, glob_set(WEDGED_J, 1), (JMP, "top")]
    # N3 -- the late 98 entry, once per load, after a Wait (the player's CC ran long before any trigger)
    B += [label("do_n3"), glob_set(TRIG_N3, 0), _stmt("Instance.Byte[4]"), (JMP_IF, "n3_done"),
          _stmt("Instance.Byte[4] const(1) B_LET"), O.wait(1), O.init_object(LATE_SID, 0), O.wait(2),
          label("n3_done"), glob_set(DONE_N3, 1), (JMP, "top")]
    # F8 (s141) -- the held-prop attach to the player's bone 13, and its detach
    B += [label("do_f8a"), glob_set(TRIG_F8A, 0), O.encode(OP_ATTACH, CUP_SID, CONTROL_UID, ATTACH_BONE),
          glob_set(DONE_F8A, 1), (JMP, "top"),
          label("do_f8d"), glob_set(TRIG_F8D, 0), O.encode(OP_DETACH, CUP_SID), glob_set(DONE_F8D, 1), (JMP, "top"),
          O.RETURN]
    return asm(B)


def player_ids(eb: bytes) -> tuple | None:
    """The player Init's own (stand, walk, run) immediates -- what T3 restores -- or None when its tag-0 function lacks
    any of the three setters (PURE over the bytes; the kit's .eb reader)."""
    return facts(eb)["player_ids"]


def _first_diff(got: bytes, want: bytes) -> str:
    k = next((n for n, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
    return f"{len(got)} B vs {len(want)} B, first difference at +{k}"


def facts(eb: bytes) -> dict:
    """What the script itself says (PURE over the bytes; the kit's .eb reader). Raises on bytes it cannot parse.

    {"main_init": [(op, offset, sid, uid)] for every InitObject/InitCode in Main_Init (offset = Main_Init-relative),
     "entries": {sid: {"type", "funcs" [tags], "init_model" (model, animset) | None, "define_tags" [tags holding a
     DefinePlayerCharacter]}}, "t3": the player's T3 function's facts (its whole "body" among them) or None, "caller":
     the caller's instructions and whole tag-0 "body", "player_ids": the player Init's own (stand, walk, run) or None}."""
    _kit()
    from ff9mapkit.eb.model import EbScript
    s = EbScript(eb)
    out = {"main_init": [], "entries": {}, "t3": None, "caller": None, "late_cc": None, "j": None, "late_guard": [],
           "player_ids": None}
    f0 = s.main.func_by_tag(0) if s.entries else None
    if f0 is None:
        raise ValueError("no Main_Init (entry 0 tag 0)")
    mcode = _code(eb, f0)
    for k, ins in enumerate(mcode):
        if ins.op == OP_INIT_OBJECT and ins.imm(0) == LATE_SID:
            # the late entry's load-time InitObject and the two instructions before it (the kit's guarded call)
            out["late_guard"].append([(i.op, eb[i.off:i.end]) for i in mcode[max(0, k - 2):k]])
    for ins in mcode:
        if ins.op in (OP_INIT_OBJECT, OP_INIT_CODE):
            sid, uid = ins.imm(0), ins.imm(1)
            out["main_init"].append((ins.op, ins.off - f0.abs_start, sid, sid if uid == 0 else uid))
    for e in s.entries[1:]:
        if e.empty:
            continue
        info = {"type": e.type, "loc": e.loc, "funcs": [f.tag for f in e.funcs], "init_model": None,
                "define_tags": []}
        for f in e.funcs:
            code = _code(eb, f)
            if any(i.op == OP_DEFINE_PLAYER for i in code):
                info["define_tags"].append(f.tag)
            if f.tag == 0:
                sm = next((i for i in code if i.op == OP_SET_MODEL), None)
                if sm is not None:
                    info["init_model"] = (sm.imm(0), sm.imm(1))
        out["entries"][e.index] = info
    pe = s.entries[PLAYER_SID] if PLAYER_SID < len(s.entries) and not s.entries[PLAYER_SID].empty else None
    p0 = pe.func_by_tag(0) if pe is not None else None
    if p0 is not None:
        code = _code(eb, p0)
        ids = tuple(next((i.imm(0) for i in code if i.op == op), None) for op in (OP_STAND, OP_WALK_ANIM, OP_RUN_ANIM))
        out["player_ids"] = None if None in ids else ids
    t3 = pe.func_by_tag(T3_TAG) if pe is not None else None
    if t3 is not None:
        code = _code(eb, t3)
        stmts = [eb[i.off:i.end] for i in code if i.op == OP_EXPR]
        out["t3"] = {"ops": [i.op for i in code], "has_bound": T3_BOUND_STMT in stmts,
                     "walk_anim": [i.imm(0) for i in code if i.op == OP_WALK_ANIM],
                     "stand_anim": [i.imm(0) for i in code if i.op == OP_STAND],
                     "loop_closes": _loop_closes(eb, code), "body": bytes(eb[t3.abs_start:t3.abs_end])}
    jf = pe.func_by_tag(J_TAG) if pe is not None else None
    if jf is not None:
        out["j"] = [(i.op, eb[i.off:i.end]) for i in _code(eb, jf)]
    le = s.entries[LATE_SID] if LATE_SID < len(s.entries) and not s.entries[LATE_SID].empty else None
    lf = le.func_by_tag(LATE_CC_TAG) if le is not None else None
    if lf is not None:
        out["late_cc"] = [i.op for i in _code(eb, lf)]
    ce = s.entries[CALLER_SID] if CALLER_SID < len(s.entries) and not s.entries[CALLER_SID].empty else None
    if ce is not None and ce.func_by_tag(0) is not None:
        code = _code(eb, ce.func_by_tag(0))
        f0c = ce.func_by_tag(0)
        out["caller"] = {"funcs": [f.tag for f in ce.funcs], "type": ce.type, "loc": ce.loc,
                         "raw": [eb[i.off:i.end] for i in code], "ops": [i.op for i in code],
                         "body": bytes(eb[f0c.abs_start:f0c.abs_end])}
    return out


def _loop_closes(eb: bytes, code: list) -> bool:
    """The bound statement is followed by a JMP_IF whose target is BEFORE it (the while-loop's back edge)."""
    from ff9mapkit.eb import disasm
    for a, b in zip(code, code[1:]):
        if eb[a.off:a.end] == T3_BOUND_STMT and b.op == OP_JMP_IF:
            tgt = disasm.jump_target(b)
            return tgt is not None and tgt < a.off
    return False


def _expected_caller_ops() -> list:
    """The conductor instructions the caller must hold, as exact bytes (the s140 legs' discriminators)."""
    _kit()
    from ff9mapkit.eb import opcodes as O
    return [("X: RunAnimationEx(250, 186)", O.run_animation_ex(CONTROL_UID, ANIM_X)),
            ("X/T1: WaitAnimationEx(250)", O.wait_animation_ex(CONTROL_UID)),
            ("T1: RunAnimationEx(250, 2572)", O.run_animation_ex(CONTROL_UID, ANIM_T1)),
            ("T1: GetEntryAnimFrame(250) < 58", T1_WAIT_STMT),
            ("T3: RunScript(2, 250, T3_TAG)", O.run_script(SCRIPT_LEVEL, CONTROL_UID, T3_TAG)),
            ("J: RunScript(2, 250, J_TAG)", O.run_script(SCRIPT_LEVEL, CONTROL_UID, J_TAG)),
            ("N3: InitObject(LATE_SID, 0)", O.init_object(LATE_SID, 0)),
            ("F8: AttachObject(CUP_SID, 250, 13)", O.encode(OP_ATTACH, CUP_SID, CONTROL_UID, ATTACH_BONE)),
            ("F8: DetachObject(CUP_SID)", O.encode(OP_DETACH, CUP_SID))]


#: the caller's ESCAPE PROTOCOL: every wedge and completion write, every bound, and the EnableMove before each DONE / WEDGED
#: of a conductor that held DisableMove (X, T1 done + wedged, T3 ok + wedged, J ok + wedged) -- a caller missing any of
#: them turns a lever red into a timeout with DisableMove held, so the preflight refuses it
CALLER_ENABLE_MOVES = 7


def _expected_caller_escape() -> list:
    """The escape statements the caller must hold, as exact bytes: (label, bytes)."""
    rows = [(f"WEDGED_{k.upper()} = 1", glob_set(b, 1)) for k, b in WEDGES.items()]
    rows += [(f"DONE_{k.upper()} = 1", glob_set(b, 1)) for k, b in DONES.items()]
    rows += [("T1: Int16[0] > T1_LIMIT", int16_gt(0, T1_LIMIT)),
             ("T3: Int16[2] > T3_TOTAL_LIMIT", int16_gt(2, T3_TOTAL_LIMIT)),
             ("T3: Int16[0] > T3_LOOP_LIMIT", int16_gt(0, T3_LOOP_LIMIT)), ("J: Int16[0] > J_LIMIT", int16_gt(0, J_LIMIT))]
    return rows


def _expected_j() -> list:
    """J_TAG's body as (op, bytes) rows -- field 404's ladder mount without its arc, the phase bits around the landing."""
    _kit()
    from ff9mapkit.eb import opcodes as O
    return [(OP_SET_JUMP, O.set_jump_animation(ANIM_J, J_JUMP0, J_JUMP1)), (OP_RUN_JUMP, O.run_jump_animation()),
            (OP_WAIT_ANIM, O.wait_animation()), (OP_EXPR, glob_set(J_LAND, 1)), (OP_RUN_LAND, O.run_land_animation()),
            (OP_WAIT_ANIM, O.wait_animation()), (OP_EXPR, glob_set(J_END, 1)), (OP_RET, O.RETURN)]


def main_init_order(eb: bytes, f: dict | None = None) -> tuple:
    """THE MAIN_INIT_ORDER ROW (audit 4.1): (ok, why). The twin's InitObject comes BEFORE the player's in Main_Init (so
    the twin's SetModel runs first, while control is still null), each exactly once, both with uid = sid; the caller's
    InitCode comes AFTER the player's. (The late entry's load-time InitObject behind its gate is :func:`preflight`'s LATE
    GATE row, read off the same facts.)"""
    f = f if f is not None else facts(eb)
    calls = f["main_init"]
    obj = [(off, sid, uid) for op, off, sid, uid in calls if op == OP_INIT_OBJECT]
    code = [(off, sid, uid) for op, off, sid, uid in calls if op == OP_INIT_CODE]
    p = [c for c in obj if c[1] == PLAYER_SID]
    t = [c for c in obj if c[1] == TWIN_SID]
    c = [c for c in code if c[1] == CALLER_SID]
    if len(p) != 1 or len(t) != 1:
        return False, f"Main_Init InitObjects the player {len(p)}x and the twin {len(t)}x (want 1 each): {calls}"
    if p[0][2] != PLAYER_SID or t[0][2] != TWIN_SID:
        return False, f"uids: player {p[0][2]} (want {PLAYER_SID}), twin {t[0][2]} (want {TWIN_SID})"
    if not t[0][0] < p[0][0]:
        return False, (f"the twin's InitObject is at Main_Init+{t[0][0]}, AFTER the player's at +{p[0][0]}: its SetModel "
                       f"would run once the player's CC already bound control (N1/N2 test nothing)")
    if len(c) != 1 or not c[0][0] > p[0][0]:
        return False, f"the caller's InitCode {c} (want exactly one, after the player's InitObject at +{p[0][0]})"
    return True, (f"twin InitObject({TWIN_SID}) at Main_Init+{t[0][0]} < player InitObject({PLAYER_SID}) at "
                  f"+{p[0][0]} < caller InitCode({CALLER_SID}) at +{c[0][0]}")


def preflight(eb: bytes) -> str | None:
    """FAIL CLOSED: None when the deployed .eb is the bench this module describes, else the first reason it is not.

    Rows: MAIN_INIT_ORDER (:func:`main_init_order`); SIDS -- the player entry's Init holds SetModel(98, 93) and its
    DefinePlayerCharacter, the twin's holds SetModel(98, 93) and NO DefinePlayerCharacter anywhere in its entry, the
    late entry's holds SetModel(98, 93) and its DefinePlayerCharacter lives ONLY in LATE_CC_TAG (never in its Init),
    the cup is model 234, the caller is a code entry with one tag-0 function; T3 -- the player entry has T3_TAG, whose
    loop bound is 2705's statement byte for byte and closes back on itself, with SetWalkAnimation(8847) /
    SetStandAnimation(7922) ahead of it, and the WHOLE function is :func:`t3_body` of the player Init's own stand / walk /
    run ids byte for byte (the phase bits, the lane, the speeds, the restore setters); LATE GATE -- the late entry's load-time InitObject is the kit's guarded call
    (GlobBit[LATE_GATE] + JMP_IFNOT); J -- the player entry's J_TAG is field 404's ladder jump (:func:`_expected_j`);
    CALLER -- every conductor instruction is present (:func:`_expected_caller_ops`); ESCAPE -- every WEDGED / DONE write,
    every bound and >= CALLER_ENABLE_MOVES EnableMoves (:func:`_expected_caller_escape`); and the caller's whole tag-0
    body is :func:`caller_body` byte for byte (the structure: which bit each poll tests, where each branch lands). The
    named rows come first so a broken deploy reads the specific reason; the whole-body rows catch everything else."""
    try:
        f = facts(eb)
    except Exception as err:                               # noqa: BLE001 - an unparseable .eb is a reason, not a crash
        return f"the .eb does not parse: {type(err).__name__}: {err}"
    try:
        ok, why = main_init_order(eb, f)
        if not ok:
            return f"MAIN_INIT_ORDER: {why}"
        ents = f["entries"]
        want98 = (ZIDANE_MODEL, ZIDANE_ANIMSET)
        for name, sid in (("player", PLAYER_SID), ("twin", TWIN_SID), ("late", LATE_SID)):
            got = ents.get(sid, {}).get("init_model")
            if got != want98:
                return f"SIDS: the {name} entry {sid}'s Init sets model {got} (want SetModel{want98})"
        if 0 not in ents[PLAYER_SID]["define_tags"]:
            return f"SIDS: the player entry {PLAYER_SID} has no DefinePlayerCharacter in its Init ({ents[PLAYER_SID]})"
        if ents[TWIN_SID]["define_tags"]:
            return f"SIDS: the twin entry {TWIN_SID} holds DefinePlayerCharacter in tags {ents[TWIN_SID]['define_tags']}"
        if ents[LATE_SID]["define_tags"] != [LATE_CC_TAG]:
            return (f"SIDS: the late entry {LATE_SID}'s DefinePlayerCharacter is in tags "
                    f"{ents[LATE_SID]['define_tags']} (want only the never-run {LATE_CC_TAG}, never its Init)")
        cup = ents.get(CUP_SID, {}).get("init_model")
        if not cup or cup[0] != CUP_MODEL:
            return f"SIDS: entry {CUP_SID} sets model {cup} (want the cup, {CUP_MODEL})"
        defined = sorted(sid for sid, e in ents.items() if 0 in e["define_tags"])
        if defined != [PLAYER_SID]:
            return f"SIDS: entries {defined} run DefinePlayerCharacter in their Init (want only the player {PLAYER_SID})"
        t3 = f["t3"]
        if t3 is None:
            return f"T3: the player entry {PLAYER_SID} has no function {T3_TAG}"
        if not t3["has_bound"] or not t3["loop_closes"]:
            return (f"T3: function {T3_TAG}'s loop bound is not 2705's `GetEntryAnimFrame(255) < "
                    f"GetAnimDuration(8847) - 1` closing a while-loop (bound {t3['has_bound']}, "
                    f"back edge {t3['loop_closes']})")
        if not t3["walk_anim"] or t3["walk_anim"][0] != ANIM_T3_WALK or not t3["stand_anim"] \
                or t3["stand_anim"][0] != ANIM_T3_STAND:
            return f"T3: SetWalk/SetStandAnimation {t3['walk_anim']} / {t3['stand_anim']} (want {ANIM_T3_WALK} / {ANIM_T3_STAND} first)"
        ids = f["player_ids"]
        if ids is None:
            return (f"T3: the player entry {PLAYER_SID}'s Init lacks an immediate SetStand / SetWalk / SetRunAnimation -- "
                    f"T3's restore setters have nothing to be checked against")
        want_t3 = t3_body(*ids)
        if t3["body"] != want_t3:
            return (f"T3: function {T3_TAG} is not the bench's t3_body{ids} byte for byte ({_first_diff(t3['body'], want_t3)})"
                    f" -- a stale or hand-edited seat (its T3_LOOP / T3_END phase bits, the lane's Walk targets, "
                    f"SetWalkSpeed({T3_WALK_SPEED}) / MakeAnimationLoop({T3_PRE_LOOP}), the restore setters) lets T3 pass or "
                    f"wedge whatever the engine does")
        if f["late_cc"] is None or OP_DEFINE_PLAYER not in f["late_cc"]:
            return f"N3: the late entry {LATE_SID} has no function {LATE_CC_TAG} holding DefinePlayerCharacter"
        guard = f["late_guard"]
        if len(guard) != 1 or [op for op, _b in guard[0]] != [OP_EXPR, OP_JMP_IFNOT] \
                or guard[0][0][1] != glob_test(LATE_GATE):
            return (f"LATE GATE: Main_Init's InitObject({LATE_SID}) is not the kit's guarded call (GlobBit[{LATE_GATE}] then "
                    f"JMP_IFNOT) -- found {[(hex(op), raw.hex(' ')) for g in guard for op, raw in g]} over {len(guard)} "
                    f"call(s): an unguarded late entry inits at LOAD, before the player's CC, and N3 tests nothing")
        if f["j"] is None:
            return f"J: the player entry {PLAYER_SID} has no function {J_TAG}"
        if f["j"] != _expected_j():
            return (f"J: function {J_TAG} is {[(hex(op), raw.hex(' ')) for op, raw in f['j']]} (want field 404's "
                    f"SetJumpAnimation({ANIM_J}, {J_JUMP0}, {J_JUMP1}) RunJumpAnimation WaitAnimation J_LAND "
                    f"RunLandAnimation WaitAnimation J_END RET)")
        cal = f["caller"]
        if cal is None:
            return f"CALLER: no code entry at sid {CALLER_SID}"
        if cal["type"] != CODE_ENTRY_TYPE or cal["funcs"] != [0] or cal["loc"] < CALLER_LOC:
            return (f"CALLER: entry {CALLER_SID} is type {cal['type']}, funcs {cal['funcs']}, loc {cal['loc']} (want a "
                    f"type-{CODE_ENTRY_TYPE} code entry, funcs [0], >= {CALLER_LOC} Instance bytes)")
        raw = cal["raw"]
        for label, want in _expected_caller_ops():
            if want not in raw:
                return f"CALLER: missing the conductor instruction {label} ({want.hex(' ')})"
        for label, want in _expected_caller_escape():
            if want not in raw:
                return f"ESCAPE: the caller lacks `{label}` ({want.hex(' ')}) -- a lever red would read as a timeout"
        moves = sum(1 for op in cal["ops"] if op == OP_ENABLE_MOVE)
        if moves < CALLER_ENABLE_MOVES:
            return (f"ESCAPE: the caller gives control back {moves}x (want >= {CALLER_ENABLE_MOVES}: an EnableMove before "
                    f"every DONE / WEDGED of a conductor that held DisableMove)")
        want_caller = caller_body()
        if cal["body"] != want_caller:
            return (f"CALLER: entry {CALLER_SID}'s tag-0 body is not the bench's caller_body() byte for byte "
                    f"({_first_diff(cal['body'], want_caller)}) -- its control flow (which bit each poll tests, where each "
                    f"branch lands) is what turns a conductor into DONE / WEDGED")
        return None
    except Exception as err:                               # noqa: BLE001 - fail closed on anything unexpected
        return f"preflight raised {type(err).__name__}: {err}"


def toml_flag_problems(raw: dict | None = None) -> list:
    """The toml's [[flag]] table vs :data:`TOML_FLAGS` (both directions), through the kit's own reader -- [] = agree."""
    _kit()
    import tomllib
    from ff9mapkit import flags as K
    raw = raw if raw is not None else tomllib.loads(TOML.read_text(encoding="utf-8"))
    got = K.collect_flag_defs(raw)                         # {normalized name: index}; raises on a bad table
    want = {K._norm(n): i for n, i in TOML_FLAGS.items()}
    out = []
    for name, idx in want.items():
        if got.get(name) != idx:
            out.append(f"[[flag]] {name}: toml {got.get(name)}, contract {idx}")
    for name in sorted(set(got) - set(want)):
        out.append(f"[[flag]] {name}: in the toml, not in the contract")
    for idx in ALL_FLAGS:
        if not K.is_safe_custom(idx):
            out.append(f"flag {idx} is outside the safe band / reserved")
    return out
