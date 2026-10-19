"""[ff9mapkit netsync B4] [ff9mapkit netsync B5] The battle co-op lane's wire pieces and pure decisions, in Python.

For composing the selftest benches' raw frames (``netsync bcmd <hex>``, ``netsync bctl <hex>``) and for reading what the
engine publishes about them (``netsync.battle``): studies/battle-coop/B4-B5-DESIGN.md sections 6.2 and 6.4 ("a Python
codec for composing bench markers").

PURE: no I/O, no engine, no clock. Every function mirrors ONE C# function of the live Memoria patch stack, named beside
it, and ``ff9mapkit/tests/test_harness_netsync.py`` pins it to the stack -- the NetSyncEnd constants read off the
patches, ClassifyEnd against the engine SelfTest's own rows, the sub-verb parsers against the agent's -- so a drift on
either side turns a test red. The stand-in (``fakegame.py``) fabricates its ``endbench`` blocks through this codec, the
way the engine fabricates its bench end through the real ParseView.

  * the v1 COMMAND frame (wire type 2, 9 bytes: ver slot action menu idLo idHi maskLo maskHi cursor) --
    NetSyncBattle.EncodeCommand / TryDecodeCommand (s102 extracted them byte for byte from BuildCommand and
    HandleCommandPayload);
  * the CONTROL frame (wire type 3, 2 bytes: 00 menuOpen) -- NetSyncBattle.BuildControl / ParseControl's acceptance;
  * the harness argument parsers ``ArgHex`` / ``ArgMask`` (HarnessAgent, s100) -- what a raw bench argument means;
  * the END BLOCK (the type-1 trailer, s103) -- NetSyncEnd.EncodeTrailer / ReadTrailer, ClassifyEnd, IsEndKind,
    KindName, the trail entry (AppendTrail) and ChaseStep (stage 10's table, pinned since s103);
  * the guest's pure decisions -- s104 PresentAction / PresentName / CloseResult / VictorySeq / InjectVerdict / W1Due /
    W2Due, s105 HostExitTrigger / TriggerName / StampResult / StampFor / IsTerminal / DeclineLateJoin / ExitVerdict /
    ExitWhy.
  * [ff9mapkit netsync B4] the v1 type-4 ROSTER (s106's bench: ``netsync bbench roster <hex>``) -- NetSyncBattle.BuildRoster /
    ParseRoster / NetSyncBattle.StockMenu's EncodeRoster and RosterSignature (``netsync.battle.menu.roster_sig``), and the
    stage-7 content hooks' bits (the ``bbench content <mask>`` lever).
  * [ff9mapkit netsync B5] the RESULT MANIFEST (s108, flags b1 of the end block) -- NetSyncEnd.EncodeManifest /
    DecodeManifest, LevelAfter, LearnSchedule, CapLearns, the shape AppendManifest publishes; and s109's replay
    decisions -- ArmVerdict / ArmWhy, ValidRowMask, FollowVerdict / FollowWhy, ExitWaitsForReplay, SongVerdict / SongWhy,
    ReplayOverflow, ReplayLevel, LearnsDue and the write guard's FpMix.
  * [ff9mapkit netsync s133] the HOST ACTION-START LANE (type 6, wire v14): the 0xA6 extension's IMPACT / START / END
    records (EncodeActionStart / EncodeActionEnd / WithImpactExt / ReadActionExt, and decode_action_legacy -- what an
    s110-s132 guest's 46-byte parse sees), the id books (ActNextId / ActStartStep / ActEndStep / ActIdOf), the describe
    check (ActVfxVerdict, btl_vfx.DescribeCommandVfx), the selftest loopback's audit (ActLoopBook) and the lane with its
    statics (ActHostLane: the stand-in's model, `netsync.battle.act.host`).
  * [ff9mapkit netsync s134] the GUEST ACTION REPLAY's pure decisions (NetSyncDiorama.Replay.cs): the two-step drain's
    book (ActRec / ActBook: RegisterStart / HostEnd / Park), ActDecide and its amended order, ActDeadMayRun,
    ActStanceGate, ActCmdMotionFilter, the backlog verdicts (ActBacklogTransport / ActBacklogBench), the battle clock
    (ActBattleDelta), ActAbortWhy, ActPendingAbortDue, ActRestoreScope, ActEndHoldStep, ActGraceArms, ActCmdStatusFor,
    ActMapMaskWith, the bench's hex parse, and the lane with its statics (ActGuestLane: the stand-in's model,
    `netsync.battle.act.guest`).
  * [ff9mapkit netsync s135] THE REPLAY HIT HOLD's pure rules (NetSyncDiorama.Replay.cs's ActHoldSelfTest twins): the
    arrival verdict (ActHoldVerdict), the life lanes, the superseded guard (ActHeldApplies, wrap-safe), the revive at
    release, the host-done / timeout clocks, the queue's FIFO block, the life and busy masks, the reconciler's skip, the
    decline-to-release mapping, the end-inject trigger, the hit's figure path, the flinch, figs[]' value, the lag's median,
    the hit's pick and the credits -- and the hold with its statics (ActHoldLane, owned by ActGuestLane:
    `netsync.battle.act.guest.hold`).
  * [ff9mapkit netsync s136] FALLBACK A's pure rules (NetSyncDiorama.Replay.cs's ActFallbackSelfTest twins): the player clip
    (ActFallbackPlayerClip, Item / Throw first), the command predicates, the enemy clip (ActFallbackFirstClip: the first
    NON-IDLE caster PlayAnimation), the key (by id, or (caster, cmd, sub) within 500 ms of battle time between arrivals),
    the once-per-action book (ActFallbackBook), COVERED vs UNCOVERED (ActFallbackCovered), the verdict's order, the call-site
    guards and the per-frame collapse -- and fallback A with its statics (ActFallbackLane, owned by ActGuestLane:
    `netsync.battle.act.guest.fallback`).
  * [ff9mapkit netsync s137] THE TRANCE BURST TIMING's pure rules (NetSyncDiorama.Replay.cs's ActTranceSelfTest twins): the
    gate (ActTranceDefers), the burst record (ActTranceIsBurst), the busy rule's naming (ActTranceRecNames), the grace, its
    busy hold and the cap with the burst's exemption (ActTranceStep), the decline end (ActTranceDeclineEnds), the
    resolution's order (ActTranceVerdict), the START-first swap (ActTranceOnArrival), the hit's probe (ActTranceHitSwaps),
    the end injection's flush (ActTranceFlushVerdict) and the present colour's guard (ActTrancePresents) -- and the timing
    with its statics (ActTranceLane, owned by ActGuestLane: `netsync.battle.act.guest.trance`).
  * [ff9mapkit netsync s138] THE DRESS INSTRUMENT (the guest's own field model, s138-s141): the keys it publishes and their
    sentinels (`player.*` after `control`, `objects[].model`, `netsync.dress`), the RIG space, and the Python twins of its
    two pure helpers -- NetSyncVisitor.FolderOf (AnimationFactory.AddAnimWithAnimatioName's naming rule) and
    NetSyncVisitor.TextureStem (a texture name's GEO-id stem). s139 adds the section-8 codec and ResolveAuto's twins here.
  * [ff9mapkit netsync s139] THE HOST'S DRESS RULE AND WIRE SECTION 8: the full rig table (RIGS, nine rows -- the moogle is
    row 8 -- with every column the audit's census fills), the loco translation (ClassifyLoco / LocoAnim), the pure rules
    (ResolveAuto with the owner's D2 spectator moogle, ResolveNamed, ResolveDressRule, the client's ResolveDressS138,
    GhostGuard, GhostAnim, MoogleWhenEmpty, DressCharId), the section-8 codec (DressSectionBody / TryParseDressSection) and
    the s103 section walkers an OLD guest runs (ApplyStoryTo / TryReadSection / ParseSections' walk), the selftest dress
    SITE (the mirror's rule behind the `selfdress` levers), and the offline half of DressSelfTest's rows with its mutants.
  * [ff9mapkit netsync s140] THE GUEST DRESSES ITSELF (+ the owner's CharacterId 8-11 rows): RIGS grows to thirteen rows (9
    Cinna, 10 Marcus, 11 Blank, 12 Beatrix -- the install's census), CharToRig / RigToChar / DressCharIdValid, ResolveAuto
    through the map, section 8's charId 8-11; NetSyncSelfDress's pure rules -- the closed loco-class table (by NAME),
    MapRigAnim / IsLocoFamily / IsGesture / BFrameTarget (the B_FRAME law), ArmDecision through the real readers, BenchFrame
    through the real encoders, SkipRule, ExcludedFieldId, SetModelRule (the dress order), LawOnRule, the `self` / `gate` /
    `law` parse -- with SelfTest's helper tables and mutants, the census frame table, and :data:`S139`: the s139 engine's
    rules FROZEN (the s139 patch's own rows run against it; it is s140's calibration engine).
  * [ff9mapkit netsync s141] THE DRESS POLISH: NetSyncSelfDress's pure s141 rules -- FootstepRule / UnbindOnEmptyRule /
    FootstepDecision (MapFootstep: Zidane's walk / run footstep keys moved to the worn rig's pair, Steiner's 925, the drop
    rigs, the empty-table guard), AttachBoneRule (a held prop to the rig's hand), KeepMeshRule, LightRowRule /
    GhostLpRowRule (the 98-row lighting fallback), PolishOnRule / TrySetPolish (the `polish` lever) -- the stock arithmetic
    their witnesses read (the FF9Snd footstep table, fldmcf's tint), and PolishSelfTest's fixtures, helper tables and
    mutants (the census oracle, studies/battle-coop/dress-census/polish.json).
"""
from __future__ import annotations

import re
import struct
import sys
from types import SimpleNamespace

# ======================================================================================== stock constants
# NOT in the patch stack (stock engine source -- the test reads them off the shared Memoria clone when it is present):
# Global/ff9/State/Battle/FF9StateBattleSystem.cs, Global/ff9/State/FF9StateGlobal.cs and BattleResultUI's private
# ResultState enum (Global/battle/Result/BattleResultUI.cs; s103's BattleResultUI.Net.cs pins NetStateStart..None to it).
PHASE_INIT_SYSTEM = 0
PHASE_EVENT = 1
PHASE_ENTER = 2
PHASE_MENU_ON = 3
PHASE_NORMAL = 4
PHASE_MENU_OFF = 5
PHASE_VICTORY = 6
PHASE_DEFEAT = 7
PHASE_CLOSE = 8

SEQ_DEFEATCLOSE_FADEOUT = 0
SEQ_DEFEATCLOSE_WAIT = 1
SEQ_MENU_OFF_VICTORY = 0
SEQ_MENU_OFF_DEFEAT = 1
SEQ_MENU_OFF_EVENT = 2
SEQ_MENU_OFF_ESCAPE = 3
SEQ_MENU_OFF_VICTORY_WITH_ENEMY = 4
SEQ_VICTORY_CAMERA_MOVE = 0
SEQ_VICTORY_FADEOUT = 1
SEQ_VICTORY_WAIT = 2

BTL_RESULT_INITIAL = 0
BTL_RESULT_VICTORY = 1
BTL_RESULT_VICTORY_NO_POSE = 2
BTL_RESULT_DEFEAT = 3
BTL_RESULT_ESCAPE = 4
BTL_RESULT_INTERRUPTION = 5
BTL_RESULT_GAMEOVER = 6
BTL_RESULT_ENEMY_FLEE = 7

#: btl_flag bits the presentation is read through (battle.BTL_PLAY_END_SONG / BTL_END_LOAD / BTL_CONTI_FLD_SONG)
BTL_PLAY_END_SONG = 32
BTL_END_LOAD = 64

RES_START = 0             # BattleResultUI.ResultState, in its order -- None (8) sorts AFTER Hide (7)
RES_EXP_TICK = 1
RES_END_EXP = 2
RES_START_GIL = 3
RES_ITEM_FULL = 4
RES_GIL_TICK = 5
RES_END = 6
RES_HIDE = 7
RES_NONE = 8

# ======================================================================================== the v1 command frame (B4)
#: NetSyncBattle's v1 actions (ActAttack .. ActInstant) and their ActionName text.
ACT_ATTACK, ACT_DEFEND, ACT_ABILITY, ACT_ITEM, ACT_INSTANT = 0, 1, 2, 3, 4
ACTION_NAMES = {ACT_ATTACK: "Attack", ACT_DEFEND: "Defend", ACT_ABILITY: "Ability", ACT_ITEM: "Item",
                ACT_INSTANT: "Instant"}
COMMAND_VERSION = 1
COMMAND_LEN = 9
#: The type-1 header flags byte (``host.caps`` / ``peer.caps``): bit 0 a random encounter, bit 1 a command-phase-gated
#: host (NetSyncBattle.CapCommandPhaseGated, s100).
CAP_RANDOM_ENCOUNTER = 1
CAP_COMMAND_PHASE_GATED = 2


def action_name(action: int) -> str:
    """NetSyncBattle.ActionName: ``"Attack"`` .. ``"Instant"``, else ``"action N"``."""
    return ACTION_NAMES.get(int(action), f"action {int(action)}")


def phase_why(phase: int) -> str:
    """NetSyncBattle.PhaseWhy (s100): the intake guard's reason for a phase that is not the command phase --
    ``host.refused_why`` and its log line ("... refused -- not in the command phase: <this> (phase N, menu on|off)")."""
    if phase in (PHASE_INIT_SYSTEM, PHASE_ENTER, PHASE_MENU_ON):
        return "the battle intro"
    return {PHASE_EVENT: "a scripted battle event", PHASE_MENU_OFF: "the battle is ending (menu off)",
            PHASE_VICTORY: "the victory", PHASE_DEFEAT: "the defeat",
            PHASE_CLOSE: "the battle is closing"}.get(phase, f"phase {phase}")


#: NetSyncBattle.RefuseOutsideCommandPhase's reason in PHASE_NORMAL with the menu disabled.
MENU_DISABLED_WHY = "the command menu is disabled (paused, a tutorial, or the last enemy falling)"


def encode_command(slot: int, action: int, menu: int = 0, ident: int = 0, mask: int = 0, cursor: int = 0) -> bytes:
    """NetSyncBattle.EncodeCommand: the 9-byte v1 frame -- ``ver slot action menu idLo idHi maskLo maskHi cursor``. Every
    field is the C# ``(Byte)`` cast of its value (truncated, never range-checked: a malformed-frame bench is a bench)."""
    return bytes([COMMAND_VERSION, slot & 0xFF, action & 0xFF, menu & 0xFF, ident & 0xFF, (ident >> 8) & 0xFF,
                  mask & 0xFF, (mask >> 8) & 0xFF, cursor & 0xFF])


def decode_command(frame) -> dict | None:
    """NetSyncBattle.TryDecodeCommand -- the host's acceptance test: None for a frame shorter than 9 bytes or not version
    1 (HandleCommandPayload then drops it, "malformed command frame"); else ``{slot, action, menu, id, mask, cursor}``.
    Bytes past the ninth are ignored, as the engine ignores them."""
    data = bytes(frame) if frame is not None else None
    if data is None or len(data) < COMMAND_LEN or data[0] != COMMAND_VERSION:
        return None
    return {"slot": data[1], "action": data[2], "menu": data[3], "id": data[4] | (data[5] << 8),
            "mask": data[6] | (data[7] << 8), "cursor": data[8]}


def command_hex(slot: int, action: int, menu: int = 0, ident: int = 0, mask: int = 0, cursor: int = 0) -> str:
    """The ``netsync bcmd`` argument for one v1 frame: ``command_hex(1, ACT_ATTACK, mask=0x10)`` ==
    ``"01 01 00 00 00 00 10 00 00"`` (slot 1 Attack at enemy btl slot 4)."""
    return hex_bytes(encode_command(slot, action, menu, ident, mask, cursor))


def control_hex(menu, nonce: int | None = None, boot: int | None = None) -> str:
    """The ``netsync bctl`` argument for one control frame (NetSyncBattle.BuildControl): ``"00 00"`` shut, ``"00 01"``
    open. A bool is the s100-s112 shape (True = 1, the legacy "open"). [ff9mapkit netsync R3 s113] an int is byte 1 --
    the guest window's DEPTH (:data:`CTL_SHUT` / :data:`CTL_LEGACY` / :data:`CTL_ROOT` / :data:`CTL_DEEP`); [ff9mapkit
    netsync R3 s114] with ``nonce`` and ``boot`` the 5-byte frame ``00 menu 01 nonce boot`` (:func:`encode_control`)."""
    return hex_bytes(encode_control(menu, nonce, boot))


def control_valid(frame) -> bool:
    """ParseControl's acceptance test (the frame stamps the control lane fresh): at least 2 bytes, the first 0."""
    data = bytes(frame) if frame is not None else b""
    return len(data) >= 2 and data[0] == 0


def hex_bytes(data) -> str:
    """The engine's rendering of a frame (``BitConverter.ToString(frame).Replace('-', ' ')``): upper-case pairs, one
    space apart -- what ``netsync.battle.menu.captured.hex`` and the agent's log lines print."""
    return " ".join(f"{b:02X}" for b in bytes(data))


_HEX = re.compile(r"[0-9A-Fa-f]*")
_SPACES = " \t\r\n\v\f"


def parse_hex(args) -> bytes | None:
    """HarnessAgent.ArgHex: the arguments joined as hex bytes (``"01 01 00"`` or ``"010100"``, each argument may carry a
    ``0x`` prefix); None = no argument, an odd digit count or a non-hex character -- refused, never half-parsed."""
    if isinstance(args, str):
        args = args.split()
    args = list(args)
    if not args:
        return None
    joined = []
    for a in args:
        a = str(a).strip(_SPACES)
        if a[:2].lower() == "0x":
            a = a[2:]
        joined.append(a)
    text = "".join(joined)
    if not text or len(text) % 2 or not _HEX.fullmatch(text):
        return None
    return bytes(int(text[i:i + 2], 16) for i in range(0, len(text), 2))


def parse_mask(text) -> int:
    """HarnessAgent.ArgMask: a party-slot mask 0-15, decimal or ``0x`` hex; -1 = absent or malformed (never a silent 0).
    Int32.TryParse's Integer style takes surrounding white space and a leading sign (``+2`` is 2; ``-1`` parses and is
    out of range); its HexNumber style takes no sign."""
    if text is None:
        return -1
    a = str(text).strip(_SPACES)
    try:
        if a[:2].lower() == "0x":
            body = a[2:].strip(_SPACES)
            if not body or not _HEX.fullmatch(body):
                return -1
            v = int(body, 16)
        else:
            if not re.fullmatch(r"[+-]?[0-9]+", a):
                return -1
            v = int(a)
    except ValueError:
        return -1
    if v >= 2 ** 31 or v < -2 ** 31:
        return -1                                    # TryParse fails on an Int32 overflow
    return v if 0 <= v <= 0x0F else -1


# ======================================================================================== the END BLOCK (B5, s103)
# NetSyncEnd's constants, by their C# names in CS_CONSTANTS (the test reads every integer `public const` off the stack's
# NetSyncEnd.cs and compares them by name).
TRAILER_MAGIC = 0xB5
FMT_END = 1
RECORD_HEADER_LEN = 4
END_BLOCK_LEN = 8

K_FIGHTING = 0
K_VICTORY_PENDING = 1
K_VICTORY = 2
K_VICTORY_NO_POSE = 3
K_DEFEAT = 4
K_ESCAPE = 5
K_OTHER_END = 6
K_EVENT = 7
KIND_NAMES = {K_FIGHTING: "fighting", K_VICTORY_PENDING: "victory-pending", K_VICTORY: "victory",
              K_VICTORY_NO_POSE: "victory-no-pose", K_DEFEAT: "defeat", K_ESCAPE: "escape", K_OTHER_END: "other-end",
              K_EVENT: "event"}

UI_OTHER = 0
UI_RESULT = 1
UI_GAMEOVER = 2
UI_TITLE = 3

RES_NO_SCREEN = 0xFF
RES_LOADING_BIT = 0x80

FLAG_AFTER_EVENT = 1
FLAG_MANIFEST = 2
FLAG_ITEM_OVERFLOW = 4
FLAG_ESCAPE_GIL = 8
FLAG_FIELD_SONG = 16

# [ff9mapkit netsync R3 s116] the FLEE RECORD (fmt 2): [fleeFlags u8][gilLost u32 LE] after the end block
FMT_FLEE = 2
FLEE_RECORD_LEN = 5
FLEE_GIL_DROP = 1                        # fleeFlags b0: the host's stock gil drop ran (its default flee method)
# NetSyncEnd.FleeMsgVerdict's codes (s116: may the guest show the host's "Dropped N Gil" now?)
FLEE_MSG_SHOW, FLEE_MSG_NOT_RUN_AWAY, FLEE_MSG_SHOWN, FLEE_MSG_BEFORE_R9B = 0, 1, 2, 3
FLEE_MSG_NOT_OURS, FLEE_MSG_NO_RECORD, FLEE_MSG_AFTER_R8 = 4, 5, 6

#: The selftest bench end's battle nonce (NetSyncEnd.BenchNonce, private): ``peer.end.nonce`` 181 on every bench end.
BENCH_NONCE = 0xB5
#: The end trail's cap (NetSyncEnd.TrailCap, private): past 48 distinct entries one "..." marks the cap.
TRAIL_CAP = 48

# ---- s104: the guest presentation
PRESENT_NONE = 0
PRESENT_VICTORY = 1
PRESENT_CLOSE = 2
PRESENT_HOLD = 3
PRESENT_FLEE = 4                         # [ff9mapkit netsync R3 s115] MENU_OFF + SEQ_MENU_OFF_ESCAPE: the stock run-away
PRESENT_ANNIHILATE = 5                   # [ff9mapkit netsync R3 s117] "Annihilated" + MENU_OFF + SEQ_MENU_OFF_DEFEAT
PRESENT_DEFEAT = 6                       # [ff9mapkit netsync R3 s117] DEFEAT + PHASE_DEFEAT + FADEOUT: var 34's writes
PRESENT_NAMES = {PRESENT_VICTORY: "victory", PRESENT_CLOSE: "close", PRESENT_HOLD: "hold", PRESENT_FLEE: "flee",
                 PRESENT_ANNIHILATE: "annihilate", PRESENT_DEFEAT: "defeat"}
W1_MS = 4000
W2_MS = 8000
GUEST_ON, GUEST_OFF, GUEST_SETTLE = 0, 1, 2
GUEST_HOLD, GUEST_NOR9B = 3, 4           # [ff9mapkit netsync R3 s115] `endbench guest hold|nor9b`
GUEST_MODE_NAMES = {GUEST_ON: "on", GUEST_OFF: "off", GUEST_SETTLE: "settle", GUEST_HOLD: "hold", GUEST_NOR9B: "nor9b"}

# ---- s105: the guest exit
EXIT_RETRY_MS = 1000
TRIGGER_NONE = 0
TRIGGER_RESULT_HIDE = 1
TRIGGER_GAME_OVER = 2
TRIGGER_TITLE = 3
TRIGGER_NAMES = {TRIGGER_RESULT_HIDE: "result-hide", TRIGGER_GAME_OVER: "game-over", TRIGGER_TITLE: "title"}
EXIT_GO = 0
EXIT_HELD_BY_LEVER = 1
EXIT_NOT_LATCHED = 2
EXIT_IN_FLIGHT = 3
EXIT_RATE_LIMITED = 4
EXIT_FADE_DEFER = 5
EXIT_MODE_ON, EXIT_MODE_OFF = 0, 1

# ---- s103: the host end-block lever (`endbench host on|cadence|off`)
MODE_ON, MODE_CADENCE, MODE_OFF = 0, 1, 2
HOST_MODE_NAMES = {MODE_ON: "on", MODE_CADENCE: "cadence", MODE_OFF: "off"}

# ---- s108: the result manifest (NetSyncEnd; the layout: see encode_manifest)
MANIFEST_MAX_ROWS = 4                    # RAW party slots 0-3
MANIFEST_MAX_LEARNS = 8                  # per row
MANIFEST_MAX_ITEMS = 6                   # BattleResultUI.ItemMax
MANIFEST_ROW_LEN = 23                    # charId flags lvBefore lvAfter expBefore(4) expGain(4) apGain(2) status(8) learnN
MANIFEST_LEARN_LEN = 6                   # i32 abilId, u16 apAt
MANIFEST_TOTALS_LEN = 14                 # u32 defaultExp, u16 defaultAp, u32 gilGain, u32 gilBefore
MANIFEST_ITEM_LEN = 5                    # i32 itemId, u8 count
#: NetSyncEnd.ManifestMaxBytes (a computed C# constant: 334)
MANIFEST_MAX_BYTES = (1 + MANIFEST_MAX_ROWS * (MANIFEST_ROW_LEN + MANIFEST_MAX_LEARNS * MANIFEST_LEARN_LEN)
                      + MANIFEST_TOTALS_LEN + 1 + MANIFEST_MAX_ITEMS * MANIFEST_ITEM_LEN + 4)
ROW_NEED_EXP, ROW_NEED_AP, ROW_DRAW = 1, 2, 4
LEARN_STEP_CAP = 9999                    # the learn schedule's 1-AP steps
EXP_CAP = 9999999                        # UpdateExp's own cap (NetSyncEnd.ExpCap, a UInt32 constant)
#: NetSyncEnd.CardNone = (Int32)TetraMasterCardId.NONE -- ``manifest.card`` 255 = no card
CARD_NONE = 255
MANIFEST_SHIP_ON, MANIFEST_SHIP_OFF = 0, 1
MANIFEST_MODE_NAMES = {MANIFEST_SHIP_ON: "on", MANIFEST_SHIP_OFF: "off"}
#: BattleStatus bits the bench's two-marker manifest adds to its first row (Poison, else Blind -- BattleStatus.cs)
STATUS_POISON = 1 << 16
STATUS_BLIND = 1 << 4

# ---- s109: the guest result-screen replay
REPLAY_STEP_MS = 1500                    # one injected step per local state per 1.5 s
REPLAY_EXIT_WAIT_MS = 5000               # the end-leave waits this long for an open replay to reach Hide
ARM_GO = 0
ARM_HELD_BY_LEVER = 1
ARM_NOT_INJECTED = 2
ARM_NO_R8 = 3
ARM_EXIT_LATCHED = 4
ARM_NOT_ON_SCREEN = 5
ARM_HOST_STATE = 6
ARM_AFTER_EVENT = 7
ARM_NO_MANIFEST = 8
ARM_HUD_NOT_UP = 9
ARM_NO_VALID_ROW = 10
FOLLOW_STEP = 0
FOLLOW_ABORTED = 1
FOLLOW_NOT_UP = 2
FOLLOW_QUIT = 3
FOLLOW_LOADING = 4
FOLLOW_NO_HOST = 5
FOLLOW_IN_STEP = 6
FOLLOW_RATE_LIMITED = 7
SONG_SHUT, SONG_HOST_KEEPS, SONG_LOCAL_KEEPS = 0, 1, 2
REPLAY_MODE_ON, REPLAY_MODE_OFF, REPLAY_MODE_LOCAL = 0, 1, 2
REPLAY_MODE_NAMES = {REPLAY_MODE_ON: "on", REPLAY_MODE_OFF: "off", REPLAY_MODE_LOCAL: "local"}
#: The write guard's FNV-1a 64 (NetSyncEnd.FpSeed / FpPrime -- UInt64 constants)
FP_SEED = 14695981039346656037
FP_PRIME = 1099511628211

#: The C# name of every integer NetSyncEnd constant this module mirrors (the test's pin) -> its Python value.
CS_CONSTANTS = {
    "TrailerMagic": TRAILER_MAGIC, "FmtEnd": FMT_END, "RecordHeaderLen": RECORD_HEADER_LEN, "EndBlockLen": END_BLOCK_LEN,
    "KFighting": K_FIGHTING, "KVictoryPending": K_VICTORY_PENDING, "KVictory": K_VICTORY,
    "KVictoryNoPose": K_VICTORY_NO_POSE, "KDefeat": K_DEFEAT, "KEscape": K_ESCAPE, "KOtherEnd": K_OTHER_END,
    "KEvent": K_EVENT, "UiOther": UI_OTHER, "UiResult": UI_RESULT, "UiGameOver": UI_GAMEOVER, "UiTitle": UI_TITLE,
    "ResNoScreen": RES_NO_SCREEN, "ResLoadingBit": RES_LOADING_BIT, "FlagAfterEvent": FLAG_AFTER_EVENT,
    "FlagManifest": FLAG_MANIFEST, "FlagItemOverflow": FLAG_ITEM_OVERFLOW, "FlagEscapeGil": FLAG_ESCAPE_GIL,
    "FlagFieldSong": FLAG_FIELD_SONG, "BenchNonce": BENCH_NONCE, "TrailCap": TRAIL_CAP,
    "PresentNone": PRESENT_NONE, "PresentVictory": PRESENT_VICTORY, "PresentClose": PRESENT_CLOSE,
    "PresentHold": PRESENT_HOLD, "W1Ms": W1_MS, "W2Ms": W2_MS, "GuestOn": GUEST_ON, "GuestOff": GUEST_OFF,
    "GuestSettle": GUEST_SETTLE, "ExitRetryMs": EXIT_RETRY_MS, "TriggerNone": TRIGGER_NONE,
    "TriggerResultHide": TRIGGER_RESULT_HIDE, "TriggerGameOver": TRIGGER_GAME_OVER, "TriggerTitle": TRIGGER_TITLE,
    "ExitGo": EXIT_GO, "ExitHeldByLever": EXIT_HELD_BY_LEVER, "ExitNotLatched": EXIT_NOT_LATCHED,
    "ExitInFlight": EXIT_IN_FLIGHT, "ExitRateLimited": EXIT_RATE_LIMITED, "ExitFadeDefer": EXIT_FADE_DEFER,
    "ExitModeOn": EXIT_MODE_ON, "ExitModeOff": EXIT_MODE_OFF, "ModeOn": MODE_ON, "ModeCadence": MODE_CADENCE,
    "ModeOff": MODE_OFF,
    # [ff9mapkit netsync B5] s108
    "ManifestMaxRows": MANIFEST_MAX_ROWS, "ManifestMaxLearns": MANIFEST_MAX_LEARNS, "ManifestMaxItems": MANIFEST_MAX_ITEMS,
    "ManifestRowLen": MANIFEST_ROW_LEN, "ManifestLearnLen": MANIFEST_LEARN_LEN, "ManifestTotalsLen": MANIFEST_TOTALS_LEN,
    "ManifestItemLen": MANIFEST_ITEM_LEN, "RowNeedExp": ROW_NEED_EXP, "RowNeedAp": ROW_NEED_AP, "RowDraw": ROW_DRAW,
    "LearnStepCap": LEARN_STEP_CAP, "ManifestShipOn": MANIFEST_SHIP_ON, "ManifestShipOff": MANIFEST_SHIP_OFF,
    # [ff9mapkit netsync B5] s109
    "ReplayStepMs": REPLAY_STEP_MS, "ReplayExitWaitMs": REPLAY_EXIT_WAIT_MS, "ArmGo": ARM_GO,
    "ArmHeldByLever": ARM_HELD_BY_LEVER, "ArmNotInjected": ARM_NOT_INJECTED, "ArmNoR8": ARM_NO_R8,
    "ArmExitLatched": ARM_EXIT_LATCHED, "ArmNotOnScreen": ARM_NOT_ON_SCREEN, "ArmHostState": ARM_HOST_STATE,
    "ArmAfterEvent": ARM_AFTER_EVENT, "ArmNoManifest": ARM_NO_MANIFEST, "ArmHudNotUp": ARM_HUD_NOT_UP,
    "ArmNoValidRow": ARM_NO_VALID_ROW, "FollowStep": FOLLOW_STEP, "FollowAborted": FOLLOW_ABORTED,
    "FollowNotUp": FOLLOW_NOT_UP, "FollowQuit": FOLLOW_QUIT, "FollowLoading": FOLLOW_LOADING,
    "FollowNoHost": FOLLOW_NO_HOST, "FollowInStep": FOLLOW_IN_STEP, "FollowRateLimited": FOLLOW_RATE_LIMITED,
    "SongShut": SONG_SHUT, "SongHostKeeps": SONG_HOST_KEEPS, "SongLocalKeeps": SONG_LOCAL_KEEPS,
    "ReplayModeOn": REPLAY_MODE_ON, "ReplayModeOff": REPLAY_MODE_OFF, "ReplayModeLocal": REPLAY_MODE_LOCAL,
    # [ff9mapkit netsync R3 s115] / s116 / s117 (FleeMsgShow's declaration line carries a `;` in its comment, so the
    # test's one-line reader skips it: it is pinned by its literal instead)
    "PresentFlee": PRESENT_FLEE, "PresentAnnihilate": PRESENT_ANNIHILATE, "PresentDefeat": PRESENT_DEFEAT,
    "GuestHold": GUEST_HOLD, "GuestNoR9b": GUEST_NOR9B, "FmtFlee": FMT_FLEE, "FleeRecordLen": FLEE_RECORD_LEN,
    "FleeGilDrop": FLEE_GIL_DROP, "FleeMsgNotRunAway": FLEE_MSG_NOT_RUN_AWAY,
    "FleeMsgShown": FLEE_MSG_SHOWN, "FleeMsgBeforeR9b": FLEE_MSG_BEFORE_R9B, "FleeMsgNotOurs": FLEE_MSG_NOT_OURS,
    "FleeMsgNoRecord": FLEE_MSG_NO_RECORD, "FleeMsgAfterR8": FLEE_MSG_AFTER_R8,
}


def kind_name(kind: int) -> str:
    """NetSyncEnd.KindName: ``"fighting"`` .. ``"event"``, else ``"kind N"``."""
    return KIND_NAMES.get(int(kind), f"kind {int(kind)}")


def classify_end(phase: int, seq: int, result: int) -> int:
    """NetSyncEnd.ClassifyEnd -- the host's (phase, seq, result) -> kind. MENU_OFF + seq 2 (var 32's park, result 0) is
    Event, NOT an end; CLOSE carrying DEFEAT/GAMEOVER is Defeat (a scripted defeat is CLOSE + 3)."""
    if phase == PHASE_MENU_OFF:
        if seq in (SEQ_MENU_OFF_VICTORY, SEQ_MENU_OFF_VICTORY_WITH_ENEMY):
            return K_VICTORY_PENDING
        if seq == SEQ_MENU_OFF_DEFEAT:
            return K_DEFEAT
        if seq == SEQ_MENU_OFF_ESCAPE:
            return K_ESCAPE
        return K_EVENT
    if phase == PHASE_VICTORY:
        return K_VICTORY
    if phase == PHASE_DEFEAT:
        return K_DEFEAT
    if phase == PHASE_CLOSE:
        if result in (BTL_RESULT_VICTORY, BTL_RESULT_VICTORY_NO_POSE):
            return K_VICTORY_NO_POSE
        if result == BTL_RESULT_ESCAPE:
            return K_ESCAPE
        if result in (BTL_RESULT_DEFEAT, BTL_RESULT_GAMEOVER):
            return K_DEFEAT
        return K_OTHER_END
    if phase == PHASE_EVENT:
        return K_EVENT
    return K_FIGHTING


def is_end_kind(kind: int) -> bool:
    """NetSyncEnd.IsEndKind: victory-pending .. other-end (never fighting, never event)."""
    return K_VICTORY_PENDING <= kind <= K_OTHER_END


def make_block(phase: int, seq: int, result: int, *, ui: int = UI_OTHER, state: int = 0, loading: bool = False,
               flags: int = 0, win_pose: int | None = None) -> dict:
    """An end block from its raw fields, as the engine's bench template builds it (NetSyncEnd.Fabricate): the kind
    DERIVED through :func:`classify_end`, ``res_state`` only while ui is 1 (else 0xFF), the win-pose mask 0x0F on a
    victory kind (unless given). Keys as the harness publishes them."""
    kind = classify_end(phase, seq, result)
    res = ((state & 0x7F) | (RES_LOADING_BIT if loading else 0)) if ui == UI_RESULT else RES_NO_SCREEN
    if win_pose is None:
        win_pose = 0x0F if kind in (K_VICTORY_PENDING, K_VICTORY) else 0
    return {"kind": kind, "phase": phase & 0xFF, "seq": seq & 0xFF, "result": result & 0xFF, "ui": ui & 0xFF,
            "res_byte": res & 0xFF, "flags": flags & 0xFF, "win_pose": win_pose & 0xFF, "manifest_len": 0}


def block_state(block: dict) -> int:
    """EndBlock.State: the ResultState (resState & 0x7F); -1 = no result screen (0xFF)."""
    res = block["res_byte"]
    return -1 if res == RES_NO_SCREEN else res & 0x7F


def block_loading(block: dict) -> bool:
    """EndBlock.Loading: a result screen whose resState carries bit 7."""
    res = block["res_byte"]
    return res != RES_NO_SCREEN and bool(res & RES_LOADING_BIT)


def published_end(block: dict, *, nonce: int | None = None, wire_seq: int | None = None,
                  bench: bool | None = None, with_manifest: bool = True, with_flee: bool = False) -> dict:
    """An end block the way HarnessAgent publishes it: ``host.end`` (AppendEndBlock) without the three peer fields,
    ``peer.end`` (AppendPeerEnd) with ``rows``, ``bench``, ``nonce`` and ``wire_seq`` -- and, from s108
    (``with_manifest``), ``rows`` the decoded manifest's row count plus ``manifest`` (:func:`published_manifest`; None =
    no flags b1, or a body that did not decode) and ``manifest_why`` (why it did not). Before s108 ``rows`` is 0.
    [ff9mapkit netsync R3 s116] ``with_flee``: ``flee_gil`` after ``manifest_len`` (the fmt-2 record's gilLost; -1 = no
    record)."""
    doc = {"kind": block["kind"], "kind_name": kind_name(block["kind"]), "phase": block["phase"],
           "seq": block["seq"], "result": block["result"], "ui": block["ui"], "res_state": block_state(block),
           "loading": block_loading(block), "flags": block["flags"], "win_pose": block["win_pose"],
           "manifest_len": block.get("manifest_len", 0)}
    if with_flee:
        doc["flee_gil"] = block.get("flee_gil", -1) if block.get("flee_flags", -1) >= 0 else -1
    if bench is not None:
        m = block.get("manifest") if with_manifest else None
        doc.update(rows=manifest_row_count(m) if m is not None else 0, bench=bool(bench), nonce=int(nonce or 0),
                   wire_seq=int(wire_seq or 0))
        if with_manifest:
            doc.update(manifest=None if m is None else published_manifest(m), manifest_why=block.get("manifest_why"))
    return doc


def block_text(block: dict) -> str:
    """EndBlock.ToString -- the shape every ``battle end block`` / ``endbench`` log line prints:
    ``victory (phase 6 seq 0 result 1; ui 0, res -, flags 0x00, pose 0x0F)``."""
    state = block_state(block)
    res = "-" if state < 0 else f"{state}{'L' if block_loading(block) else ''}"
    return (f"{kind_name(block['kind'])} (phase {block['phase']} seq {block['seq']} result {block['result']}; "
            f"ui {block['ui']}, res {res}, flags 0x{block['flags']:02X}, pose 0x{block['win_pose']:02X})")


def trail_entry(block: dict) -> str:
    """NetSyncEnd.AppendTrail's entry: ``"kind/ui/state"``, state ``-`` for no result screen, an ``L`` suffix while
    Loading (``"2/1/2L"``) -- the ``host.end_trail`` / ``peer.end_trail`` vocabulary."""
    state = block_state(block)
    tail = "-" if state < 0 else f"{state}{'L' if block_loading(block) else ''}"
    return f"{block['kind']}/{block['ui']}/{tail}"


def append_trail(trail: list, last_key: int, block: dict) -> int:
    """NetSyncEnd.AppendTrail: one entry per DISTINCT (kind, ui, resState) in arrival order, capped at TRAIL_CAP (one
    "..." marks the cap). Appends to ``trail`` in place and returns the new last key (start from -1)."""
    key = block["kind"] | (block["ui"] << 8) | (block["res_byte"] << 16)
    if key == last_key:
        return last_key
    if len(trail) > TRAIL_CAP:
        return key
    if len(trail) == TRAIL_CAP:
        trail.append("...")
        return key
    trail.append(trail_entry(block))
    return key


def encode_trailer(block: dict, manifest: bytes | None = None) -> bytes:
    """NetSyncEnd.EncodeTrailer: one fmt-1 record -- ``B5 01 lenLo lenHi`` + the 8-byte block (+ manifest bytes, which
    set flags b1; without them b1 is cleared)."""
    extra = bytes(manifest or b"")
    length = END_BLOCK_LEN + len(extra)
    if length > 0xFFFF:
        raise ValueError("an end-block body cannot exceed 65535 bytes")
    flags = block["flags"] | FLAG_MANIFEST if extra else block["flags"] & ~FLAG_MANIFEST & 0xFF
    return bytes([TRAILER_MAGIC, FMT_END, length & 0xFF, length >> 8, block["kind"] & 0xFF, block["phase"] & 0xFF,
                  block["seq"] & 0xFF, block["result"] & 0xFF, block["ui"] & 0xFF, block["res_byte"] & 0xFF,
                  flags & 0xFF, block["win_pose"] & 0xFF]) + extra


def read_trailer(payload, offset: int = 0) -> tuple[dict | None, str | None, int]:
    """NetSyncEnd.ReadTrailer: the records from ``offset`` to the end -> ``(block, why, skipped)``. No trailer at all is
    ``(None, None, 0)`` (a pre-B5 host); a malformed one ``(None, <the engine's reason>, n)``; an unknown fmt is skipped
    by its length (counted); the LAST fmt-1 record wins; a fmt-1 body past 8 bytes is a manifest (flags b1) or later
    growth, skipped. [ff9mapkit netsync B5] s108: under flags b1 the body past the 8 bytes is DECODED inside the record's
    own bounds (:func:`decode_manifest`) -- the block carries ``manifest`` (None = it did not decode) and
    ``manifest_why`` (the reason); a bad manifest never nulls the block. Without b1 both are None. [ff9mapkit netsync R3
    s116] A fmt-2 FLEE RECORD lands on the block as ``flee_flags`` / ``flee_gil`` (-1 = none; either order, the last one
    wins); a fmt-2 body shorter than 5 bytes is counted in ``skipped`` and never nulls the block."""
    data = bytes(payload) if payload is not None else None
    if data is None or offset < 0 or offset > len(data):
        return None, "the unit records overran the frame", 0
    found, skipped, p = None, 0, offset
    flee_flags, flee_gil = -1, -1                # [ff9mapkit netsync R3 s116] the fmt-2 record (-1 = none)
    while p < len(data):
        left = len(data) - p
        if left < RECORD_HEADER_LEN:
            return None, f"truncated record header ({left} byte(s))", skipped
        if data[p] != TRAILER_MAGIC:
            return None, f"foreign trailing bytes (0x{data[p]:02X}, not the 0xB5 magic)", skipped
        fmt = data[p + 1]
        length = data[p + 2] | (data[p + 3] << 8)
        if length > left - RECORD_HEADER_LEN:
            return None, f"truncated fmt-{fmt} body ({left - RECORD_HEADER_LEN} of {length} byte(s))", skipped
        body = p + RECORD_HEADER_LEN
        if fmt == FMT_END:
            if length < END_BLOCK_LEN:
                return None, f"short end block ({length} of {END_BLOCK_LEN} byte(s))", skipped
            flags = data[body + 6]
            found = {"kind": data[body], "phase": data[body + 1], "seq": data[body + 2], "result": data[body + 3],
                     "ui": data[body + 4], "res_byte": data[body + 5], "flags": flags, "win_pose": data[body + 7],
                     "manifest_len": length - END_BLOCK_LEN if flags & FLAG_MANIFEST else 0,
                     "manifest": None, "manifest_why": None}
            if flags & FLAG_MANIFEST:
                found["manifest"], found["manifest_why"] = decode_manifest(data, body + END_BLOCK_LEN,
                                                                           length - END_BLOCK_LEN)
        elif fmt == FMT_FLEE and length >= FLEE_RECORD_LEN:
            # [ff9mapkit netsync R3 s116] the host's flee record (the last one wins); bytes past the 5 are later growth
            flee_flags = data[body]
            flee_gil = data[body + 1] | (data[body + 2] << 8) | (data[body + 3] << 16) | (data[body + 4] << 24)
        else:
            skipped += 1                         # an unknown fmt -- or (s116) a SHORT fmt-2 body: the block stands
        p = body + length
    if found is not None:
        found["flee_flags"], found["flee_gil"] = flee_flags, flee_gil
    return found, None, skipped


def chase_step(local: int, host: int, host_loading: bool) -> bool:
    """NetSyncEnd.ChaseStep (stage 10's result-screen chase, pinned since s103): may a guest screen at ``local`` inject
    one Confirm step while the host reads ``host``? Never on None (8 sorts after Hide), never from Hide or None, never
    at a natural EndEXPAndAP (only while the host is Loading through its fade)."""
    if host == RES_NONE or host < RES_START or host > RES_NONE:
        return False
    if local == RES_START:
        return host > RES_START
    if local in (RES_EXP_TICK, RES_END_EXP):
        return host > RES_END_EXP or (host == RES_END_EXP and bool(host_loading))
    if local == RES_START_GIL:
        return host > RES_START_GIL
    if local == RES_ITEM_FULL:
        return host > RES_ITEM_FULL
    if local == RES_GIL_TICK:
        return host > RES_GIL_TICK
    if local == RES_END:
        return host == RES_HIDE
    return False


# ---- s104: the guest presentation's pure decisions
def present_action(kind: int) -> int:
    """NetSyncEnd.PresentAction: victory-pending / victory -> the stock victory tail; victory-no-pose / other-end -> the
    CLOSE fade; defeat / escape -> HOLD (v1); fighting / event / anything else -> nothing."""
    if kind in (K_VICTORY_PENDING, K_VICTORY):
        return PRESENT_VICTORY
    if kind in (K_VICTORY_NO_POSE, K_OTHER_END):
        return PRESENT_CLOSE
    if kind in (K_DEFEAT, K_ESCAPE):
        return PRESENT_HOLD
    return PRESENT_NONE


def present_name(action: int) -> str | None:
    """NetSyncEnd.PresentName -- ``netsync.battle.end.action``: "victory" | "close" | "hold" | None."""
    return PRESENT_NAMES.get(int(action))


def close_result(host_result: int) -> int:
    """NetSyncEnd.CloseResult: a CLOSE injection's btl_result -- VICTORY folded to VICTORY_NO_POSE, else the host's."""
    return BTL_RESULT_VICTORY_NO_POSE if host_result == BTL_RESULT_VICTORY else host_result


def victory_seq(guest_mode: int) -> int:
    """NetSyncEnd.VictorySeq: SEQ_MENU_OFF_VICTORY_WITH_ENEMY (no per-unit settle), or SEQ_MENU_OFF_VICTORY under the
    ``endbench guest settle`` lever (W2's red)."""
    return SEQ_MENU_OFF_VICTORY if guest_mode == GUEST_SETTLE else SEQ_MENU_OFF_VICTORY_WITH_ENEMY


def inject_verdict(guest_mode: int, load_latched: bool, phase: int, hud_up: bool) -> str | None:
    """NetSyncEnd.InjectVerdict: None = inject now; else the engine's reason (``netsync.battle.end.why`` carries it after
    ``"the host's <kind> waits: "``)."""
    if guest_mode == GUEST_OFF:
        return "the calibration lever `endbench guest off` holds the pre-stage guest (nothing presented)"
    if not load_latched:
        return "the diorama's units are not final yet (LOAD_INITNPC|LOAD_INITCHR)"
    if phase != PHASE_NORMAL:
        return f"the diorama is in phase {phase}, not its steady phase ({PHASE_NORMAL})"
    if not hud_up:
        return "the battle HUD is not the UI state (paused, a quit prompt or a tutorial is up)"
    return None


def w1_due(phase: int, seq: int, armed: bool, armed_ms: int) -> bool:
    """NetSyncEnd.W1Due: PHASE_VICTORY + SEQ_VICTORY_CAMERA_MOVE more than W1_MS after the host's ui >= 1."""
    return bool(armed) and armed_ms > W1_MS and phase == PHASE_VICTORY and seq == SEQ_VICTORY_CAMERA_MOVE


def w2_due(phase: int, injected_ms: int) -> bool:
    """NetSyncEnd.W2Due: still PHASE_MENU_OFF more than W2_MS after the injection."""
    return injected_ms > W2_MS and phase == PHASE_MENU_OFF


# ---- s105: the guest exit's pure decisions
def host_exit_trigger(ui: int, res_byte: int) -> int:
    """NetSyncEnd.HostExitTrigger: ui 1 at Hide (with or without Loading) -> result-hide; ui 2 -> game-over; ui 3 ->
    title; anything else (None, End, ui 0) -> none."""
    if ui == UI_RESULT:
        return TRIGGER_RESULT_HIDE if res_byte != RES_NO_SCREEN and (res_byte & 0x7F) == RES_HIDE else TRIGGER_NONE
    if ui == UI_GAMEOVER:
        return TRIGGER_GAME_OVER
    if ui == UI_TITLE:
        return TRIGGER_TITLE
    return TRIGGER_NONE


def trigger_name(trigger: int) -> str | None:
    """NetSyncEnd.TriggerName -- ``end_leave.trigger``: "result-hide" | "game-over" | "title" | None."""
    return TRIGGER_NAMES.get(int(trigger))


def stamp_result(host_result: int) -> int:
    """NetSyncEnd.StampResult: the btl_result a return carries -- NO_POSE folds to VICTORY; DEFEAT / ESCAPE /
    INTERRUPTION / ENEMY_FLEE carry; INITIAL, GAMEOVER and any undefined byte -> -1 (stamp nothing)."""
    if host_result in (BTL_RESULT_VICTORY, BTL_RESULT_VICTORY_NO_POSE):
        return BTL_RESULT_VICTORY
    if host_result in (BTL_RESULT_DEFEAT, BTL_RESULT_ESCAPE, BTL_RESULT_INTERRUPTION, BTL_RESULT_ENEMY_FLEE):
        return host_result
    return -1


def stamp_for(host_result: int, no_game_over: bool) -> int:
    """NetSyncEnd.StampFor: StampResult in the fight's own scene -- a DEFEAT outside a NoGameOver scene is a Game Over in
    transit, never carried."""
    if host_result == BTL_RESULT_DEFEAT and not no_game_over:
        return -1
    return stamp_result(host_result)


def is_terminal(kind: int, ui: int) -> bool:
    """NetSyncEnd.IsTerminal: an end kind, or the host on its result screen / Game Over / the title."""
    return is_end_kind(kind) or UI_RESULT <= ui <= UI_TITLE


def decline_late_join(kind: int, ui: int, end_nonce: int, boot_nonce: int, bench: bool) -> bool:
    """NetSyncEnd.DeclineLateJoin: True = the watcher declines booting battle ``boot_nonce`` (the lane's own block for
    that nonce is terminal); never on the bench seam."""
    return not bench and end_nonce == boot_nonce and is_terminal(kind, ui)


def exit_verdict(exit_mode: int, latched: bool, leave_in_flight: bool, fading: bool, since_try_ms: int) -> int:
    """NetSyncEnd.ExitVerdict, in the engine's order: the lever, the latch, a leave in flight, 1 Hz, a fade."""
    if exit_mode == EXIT_MODE_OFF:
        return EXIT_HELD_BY_LEVER
    if not latched:
        return EXIT_NOT_LATCHED
    if leave_in_flight:
        return EXIT_IN_FLIGHT
    if since_try_ms < EXIT_RETRY_MS:
        return EXIT_RATE_LIMITED
    if fading:
        return EXIT_FADE_DEFER
    return EXIT_GO


def exit_why(verdict: int) -> str | None:
    """NetSyncEnd.ExitWhy -- ``end_leave.why`` for each verdict (None = go)."""
    return {
        EXIT_GO: None,
        EXIT_HELD_BY_LEVER: "the calibration lever `endbench exit off` holds the pre-stage guest (no end-leave, no settle)",
        EXIT_NOT_LATCHED: "the host has not left its battle yet",
        EXIT_IN_FLIGHT: "a leave is already in flight (its teardown lands on arrival)",
        EXIT_RATE_LIMITED: "rate-limited (one end-leave attempt per second)",
        EXIT_FADE_DEFER: "a scene fade is in flight (Leave would defer) -- retrying at 1 Hz",
    }.get(int(verdict), f"exit verdict {int(verdict)}")


# ======================================================================================== the v1 ROSTER (B4, s106)
# The type-4 frame NetSyncBattle.BuildRoster writes and ParseRoster reads (and NetSyncBattle.StockMenu's EncodeRoster
# re-encodes for the `bbench roster auto` fabricator), little-endian:
#   u8 ver (1), u8 slotCount, per slot {u8 slot (WIRE index), u8 cmdCount, per command {u8 menu, u16 cmdId, u8 type,
#   u8 targetType, u8 abilCount, per ability {u16 id, u8 mp, u8 flags (b0 enabled, b1 forDead), u8 targetType}}},
#   u16 itemCount, per item {u16 id, u8 count, u8 targetType, u8 forDead}.
# A roster here is ``{"slots": {wire: [cmd, ...]}, "items": [item, ...]}``; a command ``{"menu", "cmd", "type",
# "target", "abils": [{"id", "mp", "enabled", "for_dead", "target"}]}``; an item ``{"id", "count", "target",
# "for_dead"}``. ``slots`` keeps the WIRE order (ParseRoster inserts in it; RosterSignature walks it).
ROSTER_VERSION = 1
#: The stage-7 content hooks (NetSyncBattle.StockMenu.ContentCommand .. ContentAll): `netsync bbench content <mask>`
#: names the hooks left ON; `netsync.battle.menu.content_off` the ones turned OFF; `content_hits` counts each by name.
CONTENT_COMMAND, CONTENT_GREY, CONTENT_ABILITY, CONTENT_BAG, CONTENT_COUNT, CONTENT_CAST, CONTENT_REFRESH = \
    1, 2, 4, 8, 16, 32, 64
CONTENT_ALL = 127
CONTENT_NAMES = ("command", "grey", "ability", "bag", "count", "cast", "refresh")
#: NetSyncBattle's timing constants the stage-8 / stage-11 benches are planned in (ms)
SAMPLE_MS = 150                          # the type-1 cadence (the bench feed's too)
STALE_MS = 2000                          # a parsed peer view older than this is not live
MENU_STALE_MS = 2500                     # the control lane's freshness window (a guest slot falls back after it)
MIRROR_REFUSE_MS = 2500                  # a forwarded command's bit still up this long ...
MIRROR_REFUSE_SEQS = 3                   # ... AND across this many host samples = refused or lost
MIRROR_NO_ROSTER_MS = 2500               # a Ready slot the roster never carries is stranded after this


def roster_cmd(menu: int, cmd: int, *, type: int = 1, target: int = 0, abils=()) -> dict:
    """One roster command (a builder for :func:`encode_roster`): ``abils`` are dicts or ``(id, mp, enabled)`` tuples."""
    out = []
    for a in abils:
        if isinstance(a, dict):
            out.append({"id": int(a["id"]), "mp": int(a.get("mp", 0)), "enabled": bool(a.get("enabled", True)),
                        "for_dead": bool(a.get("for_dead", False)), "target": int(a.get("target", 0))})
        else:
            aid, mp, enabled = a
            out.append({"id": int(aid), "mp": int(mp), "enabled": bool(enabled), "for_dead": False, "target": 0})
    return {"menu": int(menu), "cmd": int(cmd), "type": int(type), "target": int(target), "abils": out}


def encode_roster(roster: dict) -> bytes:
    """NetSyncBattle.StockMenu.EncodeRoster -- BuildRoster's v1 layout, slots ASCENDING (the C# sorts the keys); an MP or a
    count past 255 and an ability count past 255 are clamped, every other field the C# ``(Byte)`` / ``(UInt16)`` cast."""
    out = bytearray([ROSTER_VERSION])
    slots = sorted(int(s) for s in roster.get("slots", {}))
    out.append(len(slots) & 0xFF)
    by = {int(k): v for k, v in roster.get("slots", {}).items()}
    for s in slots:
        cmds = by[s] or []
        out += bytes([s & 0xFF, len(cmds) & 0xFF])
        for c in cmds:
            abils = list(c.get("abils", ()))[:255]
            out += bytes([c["menu"] & 0xFF, c["cmd"] & 0xFF, (c["cmd"] >> 8) & 0xFF, c.get("type", 0) & 0xFF,
                          c.get("target", 0) & 0xFF, len(abils)])
            for a in abils:
                out += bytes([a["id"] & 0xFF, (a["id"] >> 8) & 0xFF, min(int(a.get("mp", 0)), 255) & 0xFF,
                              (1 if a.get("enabled") else 0) | (2 if a.get("for_dead") else 0), a.get("target", 0) & 0xFF])
    items = list(roster.get("items", ()))
    out += bytes([len(items) & 0xFF, (len(items) >> 8) & 0xFF])
    for it in items:
        out += bytes([it["id"] & 0xFF, (it["id"] >> 8) & 0xFF, min(int(it.get("count", 0)), 255) & 0xFF,
                      it.get("target", 0) & 0xFF, 1 if it.get("for_dead") else 0])
    return bytes(out)


def parse_roster(data) -> dict | None:
    """NetSyncBattle.ParseRoster: None for a version byte other than 1 or a frame that ends early (the BinaryReader's
    EndOfStreamException -- "bad roster frame"); bytes past the item list are ignored, as the engine ignores them. A
    repeated wire slot REPLACES its commands in place (Dictionary's indexer)."""
    b = bytes(data) if data is not None else b""
    p = 0

    def take(n: int) -> bytes:
        nonlocal p
        if p + n > len(b):
            raise EOFError
        chunk = b[p:p + n]
        p += n
        return chunk

    def u8() -> int:
        return take(1)[0]

    def u16() -> int:
        lo, hi = take(2)
        return lo | (hi << 8)

    try:
        if u8() != ROSTER_VERSION:
            return None
        roster = {"slots": {}, "items": []}
        for _ in range(u8()):
            slot = u8()
            cmds = []
            for _ in range(u8()):
                cmd = {"menu": u8(), "cmd": u16(), "type": u8(), "target": u8(), "abils": []}
                for _ in range(u8()):
                    aid, mp, flags, tt = u16(), u8(), u8(), u8()
                    cmd["abils"].append({"id": aid, "mp": mp, "enabled": bool(flags & 1), "for_dead": bool(flags & 2),
                                         "target": tt})
                cmds.append(cmd)
            roster["slots"][slot] = cmds
        for _ in range(u16()):
            iid, count, tt, fd = u16(), u8(), u8(), u8()
            roster["items"].append({"id": iid, "count": count, "target": tt, "for_dead": fd != 0})
        return roster
    except EOFError:
        return None


def _fnv32(h: int, v: int) -> int:
    """NetSyncBattle.StockMenu.Fnv: FNV-1a 64 over the four little-endian bytes of an Int32."""
    for i in range(4):
        h ^= (int(v) >> (8 * i)) & 0xFF
        h = (h * FP_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def roster_signature(roster: dict) -> int:
    """NetSyncBattle.StockMenu.RosterSignature: FNV-1a over every field the panels can draw, in the roster's OWN slot order
    (the wire order ParseRoster inserted); never 0 for a roster. Equal = the same content."""
    h = FP_SEED
    for slot, cmds in roster.get("slots", {}).items():
        h = _fnv32(h, 0x5100 + int(slot))
        for c in cmds or ():
            for v in (c["menu"], c["cmd"], c.get("type", 0), c.get("target", 0)):
                h = _fnv32(h, v)
            for a in c.get("abils", ()):
                h = _fnv32(_fnv32(_fnv32(h, a["id"]), a.get("mp", 0)),
                           (1 if a.get("enabled") else 0) | (2 if a.get("for_dead") else 0) | (a.get("target", 0) << 2))
    h = _fnv32(h, 0x17E5)
    for it in roster.get("items", ()):
        h = _fnv32(_fnv32(h, it["id"]), it.get("count", 0) | (it.get("target", 0) << 8) | (0x10000 if it.get("for_dead")
                                                                                            else 0))
    return 1 if h == 0 else h


def roster_sig_text(roster: dict | None) -> str | None:
    """``netsync.battle.menu.roster_sig``: ``"0x" + RosterSignature.ToString("X16")``; None = no roster."""
    return None if roster is None else f"0x{roster_signature(roster):016X}"


def published_roster(roster: dict | None) -> dict | None:
    """``netsync.battle.menu.roster`` (AppendStockContent): ``slots[]`` {wire, cmds[] {menu, cmd, type, abils (the COUNT),
    on (the ENABLED count)}} for wire slots 0-3 ascending, + ``items[]`` {id, count}; None = no roster."""
    if roster is None:
        return None
    slots = []
    by = {int(k): v for k, v in roster.get("slots", {}).items()}
    for w in range(4):
        if w not in by:
            continue
        slots.append({"wire": w, "cmds": [{"menu": c["menu"], "cmd": c["cmd"], "type": c.get("type", 0),
                                           "abils": len(c.get("abils", ())),
                                           "on": sum(1 for a in c.get("abils", ()) if a.get("enabled"))}
                                          for c in by[w] or ()]})
    return {"slots": slots, "items": [{"id": it["id"], "count": it["count"]} for it in roster.get("items", ())]}


def parse_content_mask(text) -> int:
    """NetSyncBattle.StockMenu.BenchContent's argument: ``on`` = 127, ``off`` = 0, else a mask 0-127 (decimal or ``0x``
    hex) of the hooks left ON; -1 = refused ("netsync bbench content: on|off|<mask 0-127> ...")."""
    a = str(text if text is not None else "").strip().lower()
    if a == "on":
        return CONTENT_ALL
    if a == "off":
        return 0
    try:
        v = int(a[2:], 16) if a.startswith("0x") and re.fullmatch(r"[0-9a-f]+", a[2:]) else \
            int(a) if re.fullmatch(r"[+-]?[0-9]+", a) else None
    except ValueError:
        v = None
    return v if v is not None and 0 <= v <= CONTENT_ALL else -1


def parse_bench_int(text, maximum: int) -> int:
    """NetSyncBattle.StockMenu.ParseBenchInt: decimal or ``0x`` hex, 0..``maximum``; -1 = refused."""
    a = str(text if text is not None else "").strip().lower()
    if not a:
        return -1
    if a.startswith("0x"):
        v = int(a[2:], 16) if re.fullmatch(r"[0-9a-f]+", a[2:]) else None
    else:
        v = int(a) if re.fullmatch(r"[+-]?[0-9]+", a) else None
    return v if v is not None and 0 <= v <= maximum else -1


# ======================================================================================== the RESULT MANIFEST (B5, s108)
# After the fmt-1 END BLOCK's 8 bytes, while flags b1 is set (little-endian throughout):
#   u8 rowMask (bit per RAW party slot 0-3); per row, slots ascending: u8 charId, u8 rowFlags (b0 needExp, b1 needAp,
#   b2 draw), u8 lvBefore, u8 lvAfter, u32 expBefore, u32 expGain, u16 apGain, u64 status, u8 learnN (<= 8) x {i32 abilId,
#   u16 apAt}; u32 defaultExp, u16 defaultAp, u32 gilGain, u32 gilBefore; u8 itemN (<= 6) x {i32 itemId, u8 count};
#   i32 card. Bytes past the card are later growth (skipped).
# A manifest here is ``{"rows": [row | None] * 4, "default_exp", "default_ap", "gil_gain", "gil_before", "items": [{"id",
# "count"}], "card"}`` and a row ``{"char", "flags", "lv_before", "lv_after", "exp_before", "exp_gain", "ap_gain",
# "status" (an int), "learns": [{"abil", "ap_at"}]}`` -- :func:`published_manifest` is the shape the agent publishes.


def manifest_row(char: int, *, flags: int = ROW_NEED_EXP | ROW_NEED_AP | ROW_DRAW, lv_before: int = 1,
                 lv_after: int | None = None, exp_before: int = 0, exp_gain: int = 0, ap_gain: int = 0, status: int = 0,
                 learns=()) -> dict:
    """One manifest row (``learns`` are dicts or ``(abil, ap_at)`` tuples; ``lv_after`` defaults to ``lv_before``)."""
    ls = [{"abil": int(x["abil"]), "ap_at": int(x["ap_at"])} if isinstance(x, dict) else
          {"abil": int(x[0]), "ap_at": int(x[1])} for x in learns]
    return {"char": int(char), "flags": int(flags), "lv_before": int(lv_before),
            "lv_after": int(lv_before if lv_after is None else lv_after), "exp_before": int(exp_before),
            "exp_gain": int(exp_gain), "ap_gain": int(ap_gain), "status": _status_int(status), "learns": ls}


def make_manifest(rows, *, default_exp: int = 0, default_ap: int = 0, gil_gain: int = 0, gil_before: int = 0, items=(),
                  card: int = CARD_NONE) -> dict:
    """A manifest from up to four rows: a list of four (``None`` = no row in that RAW slot) or a ``{slot: row}`` dict."""
    slots = [None] * MANIFEST_MAX_ROWS
    if isinstance(rows, dict):
        for k, v in rows.items():
            slots[int(k)] = v
    else:
        for i, v in enumerate(rows):
            slots[i] = v
    its = [{"id": int(x["id"]), "count": int(x["count"])} if isinstance(x, dict) else {"id": int(x[0]), "count": int(x[1])}
           for x in items]
    return {"rows": slots, "default_exp": int(default_exp), "default_ap": int(default_ap), "gil_gain": int(gil_gain),
            "gil_before": int(gil_before), "items": its, "card": int(card)}


def _status_int(v) -> int:
    if isinstance(v, str):
        return int(v, 16) & 0xFFFFFFFFFFFFFFFF
    return int(v) & 0xFFFFFFFFFFFFFFFF


def manifest_row_mask(m: dict) -> int:
    """Manifest.RowMask: a bit per RAW slot carrying a row."""
    return sum(1 << i for i, r in enumerate(m["rows"][:MANIFEST_MAX_ROWS]) if r is not None)


def manifest_row_count(m: dict) -> int:
    return sum(1 for r in m["rows"][:MANIFEST_MAX_ROWS] if r is not None)


def manifest_learn_count(m: dict) -> int:
    return sum(len(r["learns"]) for r in m["rows"][:MANIFEST_MAX_ROWS] if r is not None)


def encode_manifest(m: dict) -> bytes:
    """NetSyncEnd.EncodeManifest -- the wire bytes; refuses (ValueError) what the encoder refuses: more than 6 items, a row
    with more than 8 learns, a manifest past MANIFEST_MAX_BYTES."""
    if len(m["items"]) > MANIFEST_MAX_ITEMS:
        raise ValueError(f"a manifest carries at most {MANIFEST_MAX_ITEMS} items")
    out = bytearray([manifest_row_mask(m)])
    for r in m["rows"][:MANIFEST_MAX_ROWS]:
        if r is None:
            continue
        if len(r["learns"]) > MANIFEST_MAX_LEARNS:
            raise ValueError(f"a manifest row carries at most {MANIFEST_MAX_LEARNS} learns")
        out += bytes([r["char"] & 0xFF, r["flags"] & 0xFF, r["lv_before"] & 0xFF, r["lv_after"] & 0xFF])
        out += (r["exp_before"] & 0xFFFFFFFF).to_bytes(4, "little") + (r["exp_gain"] & 0xFFFFFFFF).to_bytes(4, "little")
        out += (r["ap_gain"] & 0xFFFF).to_bytes(2, "little") + _status_int(r["status"]).to_bytes(8, "little")
        out.append(len(r["learns"]))
        for x in r["learns"]:
            out += (x["abil"] & 0xFFFFFFFF).to_bytes(4, "little") + (x["ap_at"] & 0xFFFF).to_bytes(2, "little")
    out += (m["default_exp"] & 0xFFFFFFFF).to_bytes(4, "little") + (m["default_ap"] & 0xFFFF).to_bytes(2, "little")
    out += (m["gil_gain"] & 0xFFFFFFFF).to_bytes(4, "little") + (m["gil_before"] & 0xFFFFFFFF).to_bytes(4, "little")
    out.append(len(m["items"]))
    for it in m["items"]:
        out += (it["id"] & 0xFFFFFFFF).to_bytes(4, "little") + bytes([it["count"] & 0xFF])
    out += (m["card"] & 0xFFFFFFFF).to_bytes(4, "little")
    if len(out) > MANIFEST_MAX_BYTES:
        raise ValueError(f"a manifest cannot exceed {MANIFEST_MAX_BYTES} bytes")
    return bytes(out)


def _i32(data: bytes, at: int) -> int:
    v = int.from_bytes(data[at:at + 4], "little")
    return v - (1 << 32) if v & 0x80000000 else v


def decode_manifest(payload, start: int = 0, length: int | None = None) -> tuple[dict | None, str | None]:
    """NetSyncEnd.DecodeManifest -- ``length`` bytes at ``start`` -> ``(manifest, None)``, or ``(None, <the engine's
    reason>)`` for what the encoder never writes: a row bit past slot 3, more than 8 learns, more than 6 items, a level
    that goes DOWN, or any truncation. Bytes past the card are later growth, skipped. Never raises."""
    p = bytes(payload) if payload is not None else None
    if length is None and p is not None:
        length = len(p) - start
    if p is None or start < 0 or length is None or length < 0 or start + length > len(p):
        return None, "manifest range outside the frame"
    at, end = start, start + length
    if end - at < 1:
        return None, "flags b1 without a manifest body"
    mask = p[at]
    at += 1
    if mask & ~0x0F:
        return None, f"row mask 0x{mask:02X} names a slot past 3"
    rows: list = [None] * MANIFEST_MAX_ROWS
    for i in range(MANIFEST_MAX_ROWS):
        if not mask & (1 << i):
            continue
        if end - at < MANIFEST_ROW_LEN:
            return None, f"truncated row {i} ({end - at} of {MANIFEST_ROW_LEN} byte(s))"
        r = {"char": p[at], "flags": p[at + 1], "lv_before": p[at + 2], "lv_after": p[at + 3],
             "exp_before": int.from_bytes(p[at + 4:at + 8], "little"),
             "exp_gain": int.from_bytes(p[at + 8:at + 12], "little"),
             "ap_gain": p[at + 12] | (p[at + 13] << 8), "status": int.from_bytes(p[at + 14:at + 22], "little"),
             "learns": []}
        learn_n = p[at + 22]
        at += MANIFEST_ROW_LEN
        if r["lv_after"] < r["lv_before"]:
            return None, f"row {i}'s level goes down ({r['lv_before']} -> {r['lv_after']})"
        if learn_n > MANIFEST_MAX_LEARNS:
            return None, f"row {i} carries {learn_n} learns (max {MANIFEST_MAX_LEARNS})"
        if end - at < learn_n * MANIFEST_LEARN_LEN:
            return None, f"truncated learns of row {i}"
        for _ in range(learn_n):
            r["learns"].append({"abil": _i32(p, at), "ap_at": p[at + 4] | (p[at + 5] << 8)})
            at += MANIFEST_LEARN_LEN
        rows[i] = r
    if end - at < MANIFEST_TOTALS_LEN + 1:
        return None, f"truncated totals ({end - at} of {MANIFEST_TOTALS_LEN + 1} byte(s))"
    m = {"rows": rows, "default_exp": int.from_bytes(p[at:at + 4], "little"), "default_ap": p[at + 4] | (p[at + 5] << 8),
         "gil_gain": int.from_bytes(p[at + 6:at + 10], "little"), "gil_before": int.from_bytes(p[at + 10:at + 14], "little"),
         "items": [], "card": CARD_NONE}
    at += MANIFEST_TOTALS_LEN
    item_n = p[at]
    at += 1
    if item_n > MANIFEST_MAX_ITEMS:
        return None, f"{item_n} items (max {MANIFEST_MAX_ITEMS})"
    if end - at < item_n * MANIFEST_ITEM_LEN + 4:
        return None, "truncated items / card"
    for _ in range(item_n):
        m["items"].append({"id": _i32(p, at), "count": p[at + 4]})
        at += MANIFEST_ITEM_LEN
    m["card"] = _i32(p, at)
    return m, None


def same_manifest(a: dict | None, b: dict | None) -> bool:
    """Manifest.SameAs -- wire-visible equality (the host-only notes are not compared)."""
    if a is None or b is None:
        return a is b
    keys = ("default_exp", "default_ap", "gil_gain", "gil_before", "card")
    if any(int(a[k]) != int(b[k]) for k in keys) or len(a["items"]) != len(b["items"]):
        return False
    if [_row_key(r) for r in a["rows"][:MANIFEST_MAX_ROWS]] != [_row_key(r) for r in b["rows"][:MANIFEST_MAX_ROWS]]:
        return False
    return all(int(x["id"]) == int(y["id"]) and int(x["count"]) == int(y["count"]) for x, y in zip(a["items"], b["items"]))


def _row_key(r: dict | None):
    if r is None:
        return None
    return (int(r["char"]), int(r["flags"]), int(r["lv_before"]), int(r["lv_after"]), int(r["exp_before"]),
            int(r["exp_gain"]), int(r["ap_gain"]), _status_int(r["status"]),
            tuple((int(x["abil"]), int(x["ap_at"])) for x in r["learns"]))


def published_manifest(m: dict, *, truncated: int = 0, learn_capped: bool = False) -> dict:
    """HarnessAgent.AppendManifest: ``row_mask``, ``rows`` [{slot, char, flags, need_exp, need_ap, draw, lv_before,
    lv_after, exp_before, exp_gain, ap_gain, status ("0x" + 16 hex digits), learns [{abil, ap_at}]}], ``default_exp``,
    ``default_ap``, ``gil_gain``, ``gil_before``, ``items`` [{id, count}], ``card`` (255 = none), ``learn_count`` and the
    host-only notes ``truncated`` / ``learn_capped`` (0 / false on a decoded manifest)."""
    rows = []
    for i, r in enumerate(m["rows"][:MANIFEST_MAX_ROWS]):
        if r is None:
            continue
        rows.append({"slot": i, "char": r["char"], "flags": r["flags"], "need_exp": bool(r["flags"] & ROW_NEED_EXP),
                     "need_ap": bool(r["flags"] & ROW_NEED_AP), "draw": bool(r["flags"] & ROW_DRAW),
                     "lv_before": r["lv_before"], "lv_after": r["lv_after"], "exp_before": r["exp_before"],
                     "exp_gain": r["exp_gain"], "ap_gain": r["ap_gain"], "status": f"0x{_status_int(r['status']):016X}",
                     "learns": [{"abil": x["abil"], "ap_at": x["ap_at"]} for x in r["learns"]]})
    return {"row_mask": manifest_row_mask(m), "rows": rows, "default_exp": m["default_exp"],
            "default_ap": m["default_ap"], "gil_gain": m["gil_gain"], "gil_before": m["gil_before"],
            "items": [{"id": it["id"], "count": it["count"]} for it in m["items"]], "card": m["card"],
            "learn_count": manifest_learn_count(m), "truncated": int(truncated), "learn_capped": bool(learn_capped)}


def manifest_from_published(doc: dict) -> dict:
    """The inverse of :func:`published_manifest` (the host-only notes dropped): what a bench reads off
    ``netsync.battle.host.manifest`` / ``peer.end.manifest``, back in the codec's shape -- ``encode_manifest`` of it is the
    bytes the host shipped."""
    rows: list = [None] * MANIFEST_MAX_ROWS
    for r in doc["rows"]:
        rows[int(r["slot"])] = manifest_row(r["char"], flags=r["flags"], lv_before=r["lv_before"], lv_after=r["lv_after"],
                                            exp_before=r["exp_before"], exp_gain=r["exp_gain"], ap_gain=r["ap_gain"],
                                            status=r["status"], learns=r["learns"])
    return make_manifest(rows, default_exp=doc["default_exp"], default_ap=doc["default_ap"], gil_gain=doc["gil_gain"],
                         gil_before=doc["gil_before"], items=doc["items"], card=doc["card"])


def level_after(level: int, exp: int, gain: int, level_count: int, threshold) -> int:
    """NetSyncEnd.LevelAfter: UpdateExp's level-up loop as a pure function of the FINAL exp -- ``threshold(L)`` is the exp
    at which level L becomes L + 1; EXP EQUAL to the threshold levels (stock's ``<=``); the final exp is capped at
    EXP_CAP; no gain, or exp already at the cap, leaves the level; a Byte guard at 255."""
    if gain == 0 or exp >= EXP_CAP:
        return level
    final = min(exp + gain, EXP_CAP)
    lv = level
    while lv < level_count and lv < 255 and threshold(lv) <= final:
        lv += 1
    return lv


def learn_schedule(pa, slots, ap_gain: int) -> tuple[list, bool]:
    """NetSyncEnd.LearnSchedule: AddAp's loop replayed on a CLONE of ``pa`` in 1-AP steps -> ``(learns, capped)``.
    ``slots`` are AddAp's occurrences in its order, ``(abil_id, index, max_ap)`` (index < 0 = not the character's); per
    step every occurrence advances its ability (an ability two items teach advances twice) and learns it the step its AP
    reaches max; stops after min(ap_gain, LEARN_STEP_CAP) steps or the first step that moves nothing. ``capped`` = the cap
    cut a schedule still advancing. ``pa`` itself is never written."""
    learns: list = []
    if pa is None or not slots or ap_gain == 0:
        return learns, False
    cur = list(pa)
    steps = min(ap_gain, LEARN_STEP_CAP)
    moved = False
    for step in range(1, steps + 1):
        moved = False
        for abil, index, max_ap in slots:
            if abil == 0 or index < 0 or index >= len(cur):
                continue
            c = cur[index]
            if max_ap <= c:
                continue
            moved = True
            if max_ap <= c + 1:
                cur[index] = max_ap
                learns.append({"abil": abil, "ap_at": step & 0xFFFF})
            else:
                cur[index] = c + 1
        if not moved:
            break
    return learns, bool(moved and ap_gain > LEARN_STEP_CAP)


def cap_learns(learns) -> tuple[list, int]:
    """NetSyncEnd.CapLearns: the EARLIEST MANIFEST_MAX_LEARNS learns kept -> ``(kept, dropped)``."""
    learns = list(learns)
    return learns[:MANIFEST_MAX_LEARNS], max(0, len(learns) - MANIFEST_MAX_LEARNS)


# ---- s109: the replay's pure decisions
def arm_verdict(replay_mode: int, injected: bool, r8_hits: int, exit_latched: bool, ui: int, host_state: int, flags: int,
                host_result: int, have_manifest: bool, hud_up: bool, valid_row_mask: int) -> int:
    """NetSyncEnd.ArmVerdict -- may the guest arm its result-screen replay NOW? In the engine's order: the lever, an
    injection, the first R8 hit, not leaving, ui 1, a host state 0..6, not AfterEvent, a manifest, the HUD, a valid row.
    [ff9mapkit netsync R3 s115] + ``host_result`` (the host's raw btl_result): an ESCAPE ignores b0 AfterEvent -- the
    host's BattleResultUI.Show takes its ESCAPE branch without reading it."""
    if replay_mode == REPLAY_MODE_OFF:
        return ARM_HELD_BY_LEVER
    if not injected:
        return ARM_NOT_INJECTED
    if r8_hits <= 0:
        return ARM_NO_R8
    if exit_latched:
        return ARM_EXIT_LATCHED
    if ui != UI_RESULT:
        return ARM_NOT_ON_SCREEN
    if host_state < RES_START or host_state >= RES_HIDE:
        return ARM_HOST_STATE
    if flags & FLAG_AFTER_EVENT and host_result != BTL_RESULT_ESCAPE:   # [ff9mapkit netsync R3 s115]
        return ARM_AFTER_EVENT
    if not have_manifest:
        return ARM_NO_MANIFEST
    if not hud_up:
        return ARM_HUD_NOT_UP
    if not valid_row_mask & 0x0F:
        return ARM_NO_VALID_ROW
    return ARM_GO


def arm_why(verdict: int) -> str | None:
    """NetSyncEnd.ArmWhy -- ``netsync.battle.end.replay.why`` for each verdict (None = go)."""
    return {
        ARM_GO: None,
        ARM_HELD_BY_LEVER: "the calibration lever `endbench replay off` holds the pre-stage guest (no replay: a black hold, "
                           "then the exit)",
        # [ff9mapkit netsync R3 s117] + run-away / defeat
        ARM_NOT_INJECTED: "this diorama presented no victory/close/run-away/defeat (a kind held by the `guest hold` lever, "
                          "or no end yet)",
        ARM_NO_R8: "the guest's own victory presentation is not done yet (no R8 hit: its fade is still running)",
        ARM_EXIT_LATCHED: "the guest is leaving (the host left its battle, or a leave is already in flight)",
        ARM_NOT_ON_SCREEN: "the host is not on its result screen (ui != 1)",
        ARM_HOST_STATE: "the host's result screen reads Hide / None / nothing (no reward pages to follow)",
        ARM_AFTER_EVENT: "the host runs an AfterEvent battle (its post-battle script, no reward pages; an escape is "
                         "exempt)",
        ARM_NO_MANIFEST: "no result manifest for this battle (a pre-stage-9 host, a manifest that did not decode, or the "
                         "host lever)",
        ARM_HUD_NOT_UP: "the guest's battle HUD is not the UI state (paused, a quit prompt or a tutorial is up)",
        ARM_NO_VALID_ROW: "REFUSED: no manifest row matches a seated party member (charId vs info.slot_no) -- a black "
                          "hold, then the exit",
    }.get(int(verdict), f"arm verdict {int(verdict)}")


def valid_row_mask(m: dict | None, seated) -> int:
    """NetSyncEnd.ValidRowMask: a bit per RAW slot whose row's charId equals the member SEATED in that same slot
    (``seated[i]`` = its slot_no, -1 = an empty seat)."""
    if m is None or seated is None:
        return 0
    mask = 0
    for i in range(min(MANIFEST_MAX_ROWS, len(seated))):
        r = m["rows"][i]
        if r is not None and seated[i] >= 0 and seated[i] == r["char"]:
            mask |= 1 << i
    return mask


def follow_verdict(aborted: bool, screen_up: bool, quit_up: bool, local_loading: bool, local: int, host: int,
                   host_loading: bool, last_step_state: int, since_step_ms: int) -> int:
    """NetSyncEnd.FollowVerdict -- the chase driver's per-frame question: step the replay now?"""
    if aborted:
        return FOLLOW_ABORTED
    if not screen_up:
        return FOLLOW_NOT_UP
    if quit_up:
        return FOLLOW_QUIT
    if local_loading:
        return FOLLOW_LOADING
    if host < RES_START or host > RES_NONE:
        return FOLLOW_NO_HOST
    if not chase_step(local, host, host_loading):
        return FOLLOW_IN_STEP
    if local == last_step_state and 0 <= since_step_ms < REPLAY_STEP_MS:
        return FOLLOW_RATE_LIMITED
    return FOLLOW_STEP


def follow_why(verdict: int) -> str | None:
    """NetSyncEnd.FollowWhy -- ``replay.screen.follow_why`` (None = step)."""
    return {
        FOLLOW_STEP: None,
        FOLLOW_ABORTED: "aborted (a leave ended the replay)",
        FOLLOW_NOT_UP: "the result screen is not the UI state (the guest's own pause)",
        FOLLOW_QUIT: "the guest's quit prompt is up (never answered by a host step)",
        FOLLOW_LOADING: "the local screen is Loading (a show / fade / hide in flight)",
        FOLLOW_NO_HOST: "no host result state this tick (a stale lane, another battle, or the host off its screen)",
        FOLLOW_IN_STEP: "in step: the host is not ahead",
        FOLLOW_RATE_LIMITED: f"this local state stepped less than {REPLAY_STEP_MS} ms ago",
    }.get(int(verdict), f"follow verdict {int(verdict)}")


def exit_waits_for_replay(trigger: int, replay_live: bool, since_latch_ms: int) -> bool:
    """NetSyncEnd.ExitWaitsForReplay: only a result-hide exit with a live replay, for under REPLAY_EXIT_WAIT_MS."""
    return trigger == TRIGGER_RESULT_HIDE and bool(replay_live) and 0 <= since_latch_ms < REPLAY_EXIT_WAIT_MS


def song_verdict(host_flags: int, local_keeps: bool) -> int:
    """NetSyncEnd.SongVerdict: the host's b4 first, then the guest's own BTL_CONTI_FLD_SONG; only SONG_SHUT shuts down."""
    if host_flags & FLAG_FIELD_SONG:
        return SONG_HOST_KEEPS
    if local_keeps:
        return SONG_LOCAL_KEEPS
    return SONG_SHUT


def song_why(verdict: int) -> str | None:
    """NetSyncEnd.SongWhy -- the stage-6 receipt strings (``end_leave.music_why``)."""
    return {
        SONG_SHUT: None,
        SONG_HOST_KEEPS: "the host keeps its field song (BTL_CONTI_FLD_SONG): nothing shut down",
        SONG_LOCAL_KEEPS: "this diorama keeps its field song (BTL_CONTI_FLD_SONG): nothing shut down",
    }.get(int(verdict), f"song verdict {int(verdict)}")


def replay_overflow(flags: int, host_state: int) -> bool:
    """NetSyncEnd.ReplayOverflow: the host's sticky b2, or its screen sitting on the ItemFullDialog."""
    return bool(flags & FLAG_ITEM_OVERFLOW) or host_state == RES_ITEM_FULL


def replay_level(level: int, exp: int, level_after_: int, level_count: int, threshold) -> int:
    """NetSyncEnd.ReplayLevel: the shadow level after the shadow exp moved -- never past the host's levelAfter."""
    lv = level
    while lv < level_after_ and lv < level_count and threshold(lv) <= exp:
        lv += 1
    return lv


def learns_due(row: dict | None, old_ap: int, new_ap: int) -> list:
    """NetSyncEnd.LearnsDue: the abilities whose apAt lies in (old_ap, new_ap], in the row's order."""
    if row is None or new_ap <= old_ap:
        return []
    return [x["abil"] for x in row["learns"] if old_ap < x["ap_at"] <= new_ap]


def fp_mix(h: int, v: int) -> int:
    """NetSyncEnd.FpMix: one UInt64 folded into the write guard's FNV-1a 64, byte by byte (little-endian)."""
    v &= 0xFFFFFFFFFFFFFFFF
    for i in range(8):
        h ^= (v >> (8 * i)) & 0xFF
        h = (h * FP_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h

# ======================================================================================== [ff9mapkit netsync R3] s111-s117
# Battle co-op round 3 (studies/battle-coop/R3-DESIGN.md section 2, the single wire/bit table): the intro mirror and the
# start hold's type-1 header bits, Wait parity's control byte and the start hold's control trailer, the guest's report and
# the host's hold decision, the swirl clamp, and the flee / defeat presentation's pure decisions. NetSyncBattle's constants
# are pinned by name in CS_BATTLE_CONSTANTS (the test reads them off the stack's NetSyncBattle.cs).

# ---- s111: the intro mirror (type-1 header flags, NetSyncBattle.FlagIntroSkipped / CapIntroMirror)
FLAG_INTRO_SKIPPED = 4                   # bit 2: the host skipped this battle's intro
CAP_INTRO_MIRROR = 8                     # bit 3: bit 2 is meaningful (an intro-mirror host)
# ---- s114: the start hold (header bit 4, observability only)
FLAG_START_HOLD = 16


def wire_intro(flags: int) -> int:
    """NetSyncBattle.WireIntro: a header flags byte's intro -- -1 = not an intro-mirror host (bit 3 clear: the guest keeps
    its own setting), 1 = the host skipped, 0 = the host played."""
    flags = int(flags)
    return -1 if not flags & CAP_INTRO_MIRROR else 1 if flags & FLAG_INTRO_SKIPPED else 0


def own_intro_skipped(skip_btl_camera: int, random_encounter: bool) -> bool:
    """The stock intro test (HonoluluBattleMain.Start, latched by NoteOwnBattleStart): the intro camera is skipped on a
    RANDOM encounter whose per-save ``cfg.skip_btl_camera`` reads 0."""
    return int(skip_btl_camera) == 0 and bool(random_encounter)


def own_battle_caps(gated: bool, random_encounter: bool, *, intro_on: bool = True, skipped: bool = False,
                    holding: bool = False) -> int:
    """SampleOwnBattle's header flags byte: bit 0 random, bit 1 gated (s100), bits 2-3 the intro (s111: both clear under
    the ``bench intro 0`` lever), bit 4 the start hold holding now (s114)."""
    f = (CAP_RANDOM_ENCOUNTER if random_encounter else 0) | (CAP_COMMAND_PHASE_GATED if gated else 0)
    if intro_on:
        f |= CAP_INTRO_MIRROR | (FLAG_INTRO_SKIPPED if skipped else 0)
    if holding:
        f |= FLAG_START_HOLD
    return f


# ---- s112: the diorama swirl clamp (NetSyncDiorama.SwirlFrames)
SWIRL_FPS = 30                           # SFX_Rush runs at 30 Hz
SWIRL_DEFAULT_FRAMES = 115               # [Graphics] BattleSwirlFrames' code default (~3.8 s)
SWIRL_BENCH_MAX_FRAMES = 1800            # `bench swirl local|clamp`'s ceiling (NetSyncDiorama.SwirlBenchMaxFrames)


def swirl_frames(local: int, booted: bool, clamp: int) -> int:
    """NetSyncDiorama.SwirlFrames: a swirl constructed while a diorama is BOOTED plays min(own, clamp) -- clamp -1 keeps
    the guest's own; every other swirl (a real battle on either machine) plays its own."""
    return min(int(local), int(clamp)) if booted and clamp >= 0 else int(local)


def swirl_ms(frames: int) -> int:
    """A swirl's nominal dwell at 30 Hz (``swirl_clamp.dwell_ms`` measures the real one)."""
    return int(frames) * 1000 // SWIRL_FPS


# ---- s113: Wait parity (the type-3 control frame's byte 1 = the guest window's DEPTH)
CTL_SHUT, CTL_LEGACY, CTL_ROOT, CTL_DEEP = 0, 1, 2, 3
CTL_NAMES = {CTL_SHUT: "shut", CTL_LEGACY: "legacy", CTL_ROOT: "root", CTL_DEEP: "deep"}
#: `bench ctl <name>` -> the byte the loopback / feed guest sends (auto = -1: its own encoding)
BENCH_CTL = {"auto": -1, "shut": CTL_SHUT, "legacy": CTL_LEGACY, "root": CTL_ROOT, "deep": CTL_DEEP}
# ---- s114: the start hold's control trailer [0][menu][fmt 1][host battle nonce][boot]
CTL_FMT1 = 1
CONTROL_LEN_V1 = 2
CONTROL_LEN_TRAILER = 5
BOOT_NONE, BOOT_BOOTING, BOOT_LIVE, BOOT_DECLINED, BOOT_BUSY = 0, 1, 2, 3, 4
BOOT_NAMES = {BOOT_NONE: "none", BOOT_BOOTING: "booting", BOOT_LIVE: "live", BOOT_DECLINED: "declined",
              BOOT_BUSY: "busy"}
#: `bench boot <op>`'s bench-only values (NetSyncBattle.BenchBootStale / Silent / Late)
BENCH_BOOT_STALE, BENCH_BOOT_SILENT, BENCH_BOOT_LATE = 5, 6, 7
BENCH_BOOT = {"auto": -1, "none": BOOT_NONE, "booting": BOOT_BOOTING, "live": BOOT_LIVE, "declined": BOOT_DECLINED,
              "busy": BOOT_BUSY, "stale": BENCH_BOOT_STALE, "silent": BENCH_BOOT_SILENT, "late": BENCH_BOOT_LATE}
START_HOLD_MS = 8000                     # [Netsync] StartHoldMs's default (0 = off)
START_HOLD_MAX_MS = 60000                # ...its ceiling (NetSyncBattle.StartHoldMaxMs)
LATE_ARM_MS = 1000                       # a BOOTING report this soon after the opening still arms (private LateArmMs)
LAPSE_RESERVE_MS = 2000                  # `bench lapse ... reserve`: the transport's re-serve window (private)
STALL_MEMORY_MS = 60000                  # `start_hold.guest.lane_ms` reads -1 past this (NetSyncBattle.StallMemoryMs)
# StartHoldStep's verdicts (NetSyncBattle.Hold*)
HOLD_NOTHING, HOLD_PRIMED, HOLD_UNPRIMED, HOLD_ARMED, HOLD_NOT_ARMED, HOLD_LATE_ARMED, HOLD_LATE_PASSED = 0, 1, 2, 3, 4, 5, 6
HOLD_REL_LIVE, HOLD_REL_DECLINED, HOLD_REL_LINK, HOLD_REL_OLD, HOLD_REL_CAP, HOLD_REL_OFF, HOLD_REL_ENDED = \
    7, 8, 9, 10, 11, 12, 13
#: a release verdict -> its `start_hold.release` name (ReleaseStartHold) and its `start_hold.released` counter key
HOLD_RELEASE_NAMES = {HOLD_REL_LIVE: "live", HOLD_REL_DECLINED: "declined", HOLD_REL_LINK: "link",
                      HOLD_REL_OLD: "old guest", HOLD_REL_CAP: "cap", HOLD_REL_ENDED: "ended", HOLD_REL_OFF: "off"}
HOLD_RELEASED_KEYS = {HOLD_REL_LIVE: "live", HOLD_REL_DECLINED: "declined", HOLD_REL_LINK: "link",
                      HOLD_REL_OLD: "oldguest", HOLD_REL_CAP: "cap", HOLD_REL_ENDED: "ended"}
#: `start_hold.state`'s vocabulary (HarnessStartHoldState)
HOLD_STATES = ("idle", "off", "intro", "primed", "holding", "late", "released", "not_armed")

#: NetSyncBattle's integer constants this module mirrors, by their C# names (the test reads the stack's NetSyncBattle.cs).
CS_BATTLE_CONSTANTS = {
    "CapCommandPhaseGated": CAP_COMMAND_PHASE_GATED, "FlagIntroSkipped": FLAG_INTRO_SKIPPED,
    "CapIntroMirror": CAP_INTRO_MIRROR, "FlagStartHold": FLAG_START_HOLD, "CtlFmt1": CTL_FMT1,
    "CtlShut": CTL_SHUT, "CtlOpenLegacy": CTL_LEGACY, "CtlOpenRoot": CTL_ROOT, "CtlOpenDeep": CTL_DEEP,
    "BootNone": BOOT_NONE, "BootBooting": BOOT_BOOTING, "BootLive": BOOT_LIVE, "BootDeclined": BOOT_DECLINED,
    "BootBusy": BOOT_BUSY, "BenchBootStale": BENCH_BOOT_STALE, "BenchBootSilent": BENCH_BOOT_SILENT,
    "BenchBootLate": BENCH_BOOT_LATE, "StartHoldMaxMs": START_HOLD_MAX_MS, "LateArmMs": LATE_ARM_MS,
    "LapseReserveMs": LAPSE_RESERVE_MS,
    "HoldNothing": HOLD_NOTHING, "HoldPrimed": HOLD_PRIMED, "HoldUnprimed": HOLD_UNPRIMED, "HoldArmed": HOLD_ARMED,
    "HoldNotArmed": HOLD_NOT_ARMED, "HoldLateArmed": HOLD_LATE_ARMED, "HoldLatePassed": HOLD_LATE_PASSED,
    "HoldRelLive": HOLD_REL_LIVE, "HoldRelDeclined": HOLD_REL_DECLINED, "HoldRelLink": HOLD_REL_LINK,
    "HoldRelOld": HOLD_REL_OLD, "HoldRelCap": HOLD_REL_CAP, "HoldRelOff": HOLD_REL_OFF, "HoldRelEnded": HOLD_REL_ENDED,
}


def ctl_name(menu: int) -> str:
    """NetSyncBattle.CtlName: a control byte 1's name (`host.wait.menu`'s vocabulary in the log lines)."""
    menu = int(menu)
    return CTL_NAMES.get(menu, "none" if menu < 0 else f"unknown {menu}")


def boot_name(boot: int) -> str | None:
    """NetSyncBattle.BootName: a report's boot state -> `boot_name` (None = -1, no report)."""
    boot = int(boot)
    return None if boot < 0 else BOOT_NAMES.get(boot, f"unknown {boot}")


def encode_control(menu, nonce: int | None = None, boot: int | None = None) -> bytes:
    """NetSyncBattle.BuildControl: ``[0][menu]`` (a bool menu is the pre-R3 shape: True = 1), or -- with ``nonce`` and
    ``boot`` -- the s114 report ``[0][menu][fmt 1][host battle nonce][boot]``."""
    m = (1 if menu else 0) if isinstance(menu, bool) else int(menu) & 0xFF
    if nonce is None and boot is None:
        return bytes([0, m])
    if nonce is None or boot is None:
        raise ValueError("a control trailer needs both the host battle nonce and the boot state")
    return bytes([0, m, CTL_FMT1, int(nonce) & 0xFF, int(boot) & 0xFF])


def decode_control(frame, host_nonce: int) -> dict | None:
    """NetSyncBattle.DecodeControl -- the HOST's decode of one control payload against its own battle nonce: None =
    malformed (null, short, not ver 0); else ``{menu, trailer, nonce, boot}``. ``menu`` is byte 1, EXCEPT under a trailer
    naming another battle: then CTL_SHUT (the byte-1 nonce gate -- a report about ANOTHER battle never freezes this one).
    A 2-byte frame, a short trailer or an unknown fmt is trailer-less (an older guest's frame: byte 1 read ungated)."""
    data = bytes(frame) if frame is not None else b""
    if len(data) < 2 or data[0] != 0:
        return None
    out = {"menu": data[1], "trailer": False, "nonce": -1, "boot": -1}
    if len(data) >= CONTROL_LEN_TRAILER and data[2] == CTL_FMT1:
        out.update(trailer=True, nonce=data[3], boot=data[4])
        if data[3] != (int(host_nonce) & 0xFF):
            out["menu"] = CTL_SHUT
    return out


def remote_menu_deep(menu_open: bool, menu_byte: int, parity_on: bool = True) -> bool:
    """NetSyncBattle.RemoteMenuDeep (the Wait freeze): a fresh open lane below the root -- 3, a legacy 1, an unknown byte;
    a 2 (the root, or a pick in flight) runs, exactly as a local window at its root. Under the ``bench waitparity 0``
    lever (``parity_on`` False) every open window freezes, the root included (the pre-stage host)."""
    return bool(menu_open) and (int(menu_byte) != CTL_ROOT or not parity_on)


def guest_boot_state(nonce: int, watching: bool, ui_free: bool, skip_nonce: int, booted: bool, booted_nonce: int,
                     live: bool) -> int:
    """NetSyncBattle.GuestBootState -- THE GUEST'S REPORT on the host battle ``nonce``: booted on it -> LIVE once its
    command phase latched, else BOOTING; a manual diorama (no wire nonce) -> DECLINED; an older battle's diorama ->
    BOOTING while watching, else NONE; not watching -> NONE; the skip nonce -> DECLINED; a busy UI -> BUSY; else
    BOOTING."""
    if booted:
        if booted_nonce == nonce:
            return BOOT_LIVE if live else BOOT_BOOTING
        if booted_nonce < 0:
            return BOOT_DECLINED
        return BOOT_BOOTING if watching else BOOT_NONE
    if not watching:
        return BOOT_NONE
    if skip_nonce == nonce:
        return BOOT_DECLINED
    if not ui_free:
        return BOOT_BUSY
    return BOOT_BOOTING


def new_hold_state() -> dict:
    """NetSyncBattle.StartHoldState at rest (``default(StartHoldState)``): one own battle's hold."""
    return {"open_seen": False, "primed": False, "decided": False, "armed": False, "started": False,
            "released": False, "cap_spent": False, "open_tick": 0, "since_tick": 0, "late_ms": 0}


def start_hold_step(h: dict, now: int, on: bool, cap_ms: int, phase_open: bool, rpt_this: bool, rpt_boot: int,
                    null_seen: bool, legacy_last: bool) -> int:
    """NetSyncBattle.StartHoldStep -- ONE TICK OF THE START HOLD, advancing ``h`` (:func:`new_hold_state`) in place;
    returns the verdict (HOLD_*). Released is final; off releases (HOLD_REL_OFF if it held); the intro follows the latest
    report (never primes on silence); the opening decides once (a BOOTING report arms); not armed, a BOOTING report
    within LATE_ARM_MS arms late; holding, it releases on LIVE, NONE/DECLINED/BUSY ("declined"), the transport's silence
    ("link"), a trailer-less frame ("old guest"), else the cap (or the getter's spent-cap latch) -- in that order."""
    if phase_open and not h["open_seen"]:
        h["open_seen"], h["open_tick"] = True, now
    if h["released"]:
        return HOLD_NOTHING
    if not on or cap_ms <= 0:
        holding = h["armed"]
        h["decided"] = h["released"] = True
        return HOLD_REL_OFF if holding else HOLD_NOTHING
    booting = bool(rpt_this) and rpt_boot == BOOT_BOOTING and not null_seen
    if not h["decided"]:
        if not h["open_seen"]:
            if booting == h["primed"]:
                return HOLD_NOTHING
            h["primed"] = booting
            return HOLD_PRIMED if booting else HOLD_UNPRIMED
        h["decided"] = True
        h["primed"] = booting
        if not booting:
            h["started"] = h["cap_spent"] = False
            return HOLD_NOT_ARMED
        h["armed"] = True
        if not h["started"]:
            h["started"], h["since_tick"] = True, now
        return HOLD_ARMED
    if not h["primed"]:
        if now - h["open_tick"] < LATE_ARM_MS:
            if not booting:
                return HOLD_NOTHING
            h.update(primed=True, armed=True, late_ms=now - h["open_tick"], started=True, since_tick=now,
                     cap_spent=False)
            return HOLD_LATE_ARMED
        h["released"] = True
        return HOLD_LATE_PASSED
    ev = HOLD_NOTHING
    if rpt_this and rpt_boot == BOOT_LIVE:
        ev = HOLD_REL_LIVE
    elif rpt_this and rpt_boot in (BOOT_NONE, BOOT_DECLINED, BOOT_BUSY):
        ev = HOLD_REL_DECLINED
    elif null_seen:
        ev = HOLD_REL_LINK
    elif legacy_last:
        ev = HOLD_REL_OLD
    elif h["cap_spent"] or (h["started"] and now - h["since_tick"] >= cap_ms):
        ev = HOLD_REL_CAP
    if ev != HOLD_NOTHING:
        h["released"] = True
    return ev


#: the design's name for the host's decision (R3-DESIGN.md 5.2) -- the same function
start_hold_verdict = start_hold_step


def hold_gate(h: dict, now: int, cap_ms: int) -> bool:
    """NetSyncBattle.HoldGate -- the StartHoldActive getter's body (read by IsNativeEnableAtb once the command menu is
    enabled): an unprimed, released or cap-spent hold never holds; the first read starts the clock; past the cap it
    latches ``cap_spent`` one-way, so a cap raised later never re-holds."""
    if not h["primed"] or h["released"] or h["cap_spent"]:
        return False
    if not h["started"]:
        h["started"], h["since_tick"] = True, now
    if now - h["since_tick"] < cap_ms:
        return True
    h["cap_spent"] = True
    return False


def hold_bit(h: dict) -> bool:
    """NetSyncBattle.StartHoldBit -- header flags bit 4: primed, its clock running, not released, its cap not spent."""
    return h["primed"] and h["started"] and not h["released"] and not h["cap_spent"]


def hold_state_name(h: dict | None, cap_ms: int) -> str:
    """NetSyncBattle.HarnessStartHoldState -- `start_hold.state` (``h`` None = no own battle: "idle")."""
    if h is None:
        return "idle"
    if h["released"]:
        return "released" if h["armed"] else "off" if cap_ms <= 0 else "not_armed"
    if cap_ms <= 0:
        return "off"
    if not h["decided"]:
        return "primed" if h["primed"] else "intro"
    return "holding" if h["primed"] else "late"


# ---- s115 / s117: the guest's flee and defeat presentation (NetSyncEnd's pure half)
BTL_FLAG_ABILITY_FLEE = 4                # stock battle.BTL_FLAG_ABILITY_FLEE (set only by the SysEscape executor)
BTL_SONG_FADEOUT = 16                    # stock battle.BTL_SONG_FADEOUT (ManageBattleSong(30, 6)'s mark)
MP_DISABLE = 4                           # BattlePlayerCharacter.PlayerMotionIndex.MP_DISABLE (down)
MP_ESCAPE = 17                           # ...MP_ESCAPE (the run-away pose) -- `battle.units[].mot`
DISAPPEAR_DONE = 5                       # `battle.units[].disappear` once the escape fade finished


def present_for(kind: int, phase: int, guest_mode: int, all_down_: bool, host_event: bool) -> int:
    """NetSyncEnd.PresentFor -- what the guest injects for the host's end NOW: the v1 table (:func:`present_action`) for
    every kind it does not hold, and the `guest hold` lever keeps it; an escape still in the host's MENU_OFF is the stock
    run-away, any other escape the CLOSE fade (s115); a defeat in the host's MENU_OFF is the stock annihilation, in its
    PHASE_DEFEAT the annihilation unless the party stands AND the host was last seen in its event phase (then var 34's
    scripted end), any other phase the CLOSE fade (s117)."""
    a = present_action(kind)
    if a != PRESENT_HOLD or guest_mode == GUEST_HOLD:
        return a
    if kind == K_ESCAPE:
        return PRESENT_FLEE if phase == PHASE_MENU_OFF else PRESENT_CLOSE
    if kind == K_DEFEAT:
        if phase == PHASE_MENU_OFF:
            return PRESENT_ANNIHILATE
        if phase == PHASE_DEFEAT:
            return PRESENT_ANNIHILATE if all_down_ or not host_event else PRESENT_DEFEAT
        return PRESENT_CLOSE
    return PRESENT_HOLD


def annihilate_settles(all_down_: bool, guest_mode: int) -> bool:
    """NetSyncEnd.AnnihilateSettles: an injected annihilation takes the stock per-unit settle (MENU_OFF +
    SEQ_MENU_OFF_DEFEAT) only when every local player is down -- else the defeat tail's writes at once (7/0); the
    `guest settle` lever always settles (W2's defeat-row bench)."""
    return bool(all_down_) or guest_mode == GUEST_SETTLE


def defeat_song_shuts(action: int, local_btl_flag: int) -> bool:
    """NetSyncEnd.DefeatSongShuts: a defeat presentation whose song 6 ran (BTL_SONG_FADEOUT) shuts it at the return,
    whatever the host's b4 says."""
    return action in (PRESENT_ANNIHILATE, PRESENT_DEFEAT) and bool(int(local_btl_flag) & BTL_SONG_FADEOUT)


def all_down(players: int, down: int) -> bool:
    """NetSyncEnd.AllDown: every linked local player under BattleEndFull -- and at least one (an empty party is not an
    annihilation)."""
    return players > 0 and down >= players


def w2_force(action: int) -> tuple[int, int, int]:
    """NetSyncEnd.W2Force -> ``(phase, seq, result)``: the tail of the kind actually injected -- a run-away the escape
    tail's writes (CLOSE / FADEOUT / ESCAPE), an annihilation or var 34's defeat the defeat tail's (PHASE_DEFEAT / FADEOUT
    / DEFEAT -- never VICTORY), anything else the victory tail's no-pose half. The engine ORs BTL_END_LOAD on every row."""
    if action == PRESENT_FLEE:
        return PHASE_CLOSE, SEQ_DEFEATCLOSE_FADEOUT, BTL_RESULT_ESCAPE
    if action in (PRESENT_ANNIHILATE, PRESENT_DEFEAT):
        return PHASE_DEFEAT, SEQ_DEFEATCLOSE_FADEOUT, BTL_RESULT_DEFEAT
    return PHASE_VICTORY, SEQ_VICTORY_FADEOUT, BTL_RESULT_VICTORY


def w2_force_why(action: int) -> str:
    """NetSyncEnd.W2ForceWhy -- the W2 line's "forced ..." phrase for the row."""
    if action == PRESENT_FLEE:
        return ("PHASE_CLOSE + SEQ_DEFEATCLOSE_FADEOUT + ESCAPE (the escape tail's writes: the run-away never finished, "
                "and R9b's state half was never reached)")
    if action in (PRESENT_ANNIHILATE, PRESENT_DEFEAT):
        return ("PHASE_DEFEAT + SEQ_DEFEATCLOSE_FADEOUT + DEFEAT (the defeat tail's writes: the party never settled "
                "down -- never VICTORY for a defeat; song 6 still only in a Game-Over scene)")
    return "PHASE_VICTORY + SEQ_VICTORY_FADEOUT (no fanfare/poses: the tail never ran)"


def no_leak_result(stamp: int, injected: bool, local: int, pre_inject: int, host_kind: int) -> int:
    """NetSyncEnd.NoLeakResult -- THE NO-LEAK RULE, scoped: the btl_result the return reverts to when nothing is stamped
    (-1 = leave the guest's own value). A stamp wins; nothing injected, no baseline or an unchanged value reverts
    nothing; a local DEFEAT / GAMEOVER always reverts, and any local value once the host's final kind is Defeat."""
    if stamp >= 0 or not injected or pre_inject < 0 or local == pre_inject:
        return -1
    if local in (BTL_RESULT_DEFEAT, BTL_RESULT_GAMEOVER):
        return pre_inject
    if host_kind == K_DEFEAT:
        return pre_inject
    return -1


def flee_msg_verdict(action: int, r9b: int, r8_hits: int, shown: bool, ours: bool, flee_flags: int, flee_gil: int) -> int:
    """NetSyncEnd.FleeMsgVerdict (s116) -- may the guest show the host's "Dropped N Gil" now? Only on a presented
    run-away, once, after R9b, from this battle's block, whose flee record has b0 and a u32 gil, before R8."""
    if action != PRESENT_FLEE:
        return FLEE_MSG_NOT_RUN_AWAY
    if shown:
        return FLEE_MSG_SHOWN
    if r9b <= 0:
        return FLEE_MSG_BEFORE_R9B
    if not ours:
        return FLEE_MSG_NOT_OURS
    if flee_flags < 0 or not flee_flags & FLEE_GIL_DROP or flee_gil < 0 or flee_gil > 0xFFFFFFFF:
        return FLEE_MSG_NO_RECORD
    if r8_hits > 0:
        return FLEE_MSG_AFTER_R8
    return FLEE_MSG_SHOW


def encode_flee_record(flee_flags: int, gil_lost: int) -> bytes:
    """NetSyncEnd.EncodeFleeRecord (s116): one fmt-2 record -- ``B5 02 05 00`` + [fleeFlags u8][gilLost u32 LE]."""
    g = int(gil_lost) & 0xFFFFFFFF
    return bytes([TRAILER_MAGIC, FMT_FLEE, FLEE_RECORD_LEN, 0, int(flee_flags) & 0xFF,
                  g & 0xFF, (g >> 8) & 0xFF, (g >> 16) & 0xFF, g >> 24])


#: `end.follow_msg`'s vocabulary (NetSyncDiorama's ShowFollowMessage names)
FOLLOW_MSG_ANNIHILATED = "annihilated"
FOLLOW_MSG_DROPPED_GIL = "dropped-gil"


# ======================================================================================== [ff9mapkit netsync R3] s118-s121
# THE SITTING-A FIX ROUND (studies/battle-coop/R3-SITTING-A-FIXES.md): s118 the host's hand-back keyed on the guest's
# report, s119 the guest's diorama hold keyed on the PEER, s120 the one session grace, s121 the audible menu refusal.
# THE LAW every link-down test keeps: PEER-ALIVE = IsConnected && GetRemote().Valid (:func:`peer_alive`), never
# IsConnected alone -- behind the local bridge the game's hop stays up through any upstream cut. Each pure decision
# below is its C# twin; test_harness_netsync.py EVALUATES the engine's own selftest rows against it (ControlSelfTest's
# s118 block, DioramaWatchSelfTest, SessionGraceSelfTest, MenuRefusalSelfTest -- read off the stack), and pins the
# constants by name (CS_OWN_CONSTANTS / CS_CLIENT_CONSTANTS / CS_FIELD_CONSTANTS).

# ---- the selftest proof block (NetSyncClient's, logged once per process on the first in-scope selftest tick): the R3
# lines' heads, in its order, and each line's row count -- "[NetSync] <head>OK (<rows> rows)"
PROOF_CONTROL = "battle control selftest: "        # NetSyncBattle.ControlSelfTest (s114)
PROOF_WATCH = "diorama watcher selftest: "         # NetSyncClient.DioramaWatchSelfTest (s119)
PROOF_GRACE = "session grace selftest: "           # NetSyncClient.SessionGraceSelfTest (s120)
PROOF_MENU = "main menu refusal selftest: "        # NetSyncField.MenuRefusalSelfTest (s121)
CONTROL_SELFTEST_ROWS_S114 = 33                    # ControlSelfTest s114-s117
CONTROL_SELFTEST_ROWS = 53                         # ...from s118 (+ its 20 ownership rows)
WATCH_SELFTEST_ROWS = 24                           # s119; s120 leaves its rows alone (WatchAt passes stall cap = cap)
GRACE_SELFTEST_ROWS = 31                           # s120: 25 + the six stall-cap rows of its review fix (NOT 25)
MENU_SELFTEST_ROWS = 14                            # s121: 10 + the four route rows of its review fix (NOT 10)


def proof_ok(head: str, rows: int) -> str:
    """A proof-block line's OK text, ``"<head>OK (<rows> rows)"`` (the engine prefixes Memoria's stamp and ``[NetSync] ``)."""
    return f"{head}OK ({int(rows)} rows)"


def peer_alive(is_connected: bool, remote_valid: bool) -> bool:
    """PEER-ALIVE (s119-s120, the law): the hop up AND the peer's position lane valid (GetRemote().Valid -- the socket layer
    stale-invalidates it ~2 s after the peer's last frame). IsConnected alone is a liar behind the local bridge."""
    return bool(is_connected) and bool(remote_valid)


# ---- s118: THE HAND-BACK NEEDS A LIVE GUEST (NetSyncBattle.GuestOwnsFromReport / GuestOwnsStep, the host's ParseControl)
def guest_owns_from_report(trailer: bool, rpt_nonce: int, rpt_boot: int, battle_nonce: int, diorama_seen: bool) -> bool:
    """NetSyncBattle.GuestOwnsFromReport -- THE OWNERSHIP RULE for one valid control frame (ParseControl stamps the
    ownership tick, IsGuestOwnedSlot's one input, only on True). A trailer-less frame (an s110-s113 guest, an unknown fmt, a
    short trailer) owns: no report, the pre-s118 rule. A report owns only when it names THIS battle with the guest's diorama
    LIVE or BOOTING -- or NONE while ``diorama_seen`` is down (no diorama report on this battle yet: the panel-only guest,
    review S118-NONE-PANEL). DECLINED, BUSY, an unknown state, NONE after the latch, or any report about another battle
    keep the guest's slots with the host's ready loop (owner decision, sitting A)."""
    if not trailer:
        return True
    if int(rpt_nonce) != int(battle_nonce) & 0xFF:
        return False
    if rpt_boot in (BOOT_LIVE, BOOT_BOOTING):
        return True
    return rpt_boot == BOOT_NONE and not diorama_seen


def new_own_latch() -> dict:
    """The per-own-battle latch GuestOwnsStep advances, at rest (``_rptDioramaSeen`` false: NoteOwnBattleStart clears it,
    and so does a harness release of a `bench boot` lever or a `bctl` stamp)."""
    return {"seen": False}


def guest_owns_step(latch: dict, trailer: bool, rpt_nonce: int, rpt_boot: int, battle_nonce: int) -> bool:
    """NetSyncBattle.GuestOwnsStep -- one valid frame through :func:`guest_owns_from_report` WITH this own battle's latch,
    advanced in place (:func:`new_own_latch`): ``seen`` rises on the first report naming THIS battle with any state but
    NONE (BOOTING, LIVE, DECLINED, BUSY, an unknown one) and stays up until the next own battle; a report about another
    battle, or a trailer-less frame, never moves it."""
    if trailer and int(rpt_nonce) == int(battle_nonce) & 0xFF and rpt_boot != BOOT_NONE:
        latch["seen"] = True
    return guest_owns_from_report(trailer, rpt_nonce, rpt_boot, battle_nonce, latch["seen"])


def parse_control_owned(frame, battle_nonce: int, latch: dict, loopback_auto: bool = False) -> dict | None:
    """NetSyncBattle.ParseControl's s118 half on the HOST: :func:`decode_control`, then the ownership step (the latch
    advanced in place even for the loopback; ``loopback_auto`` = SelfTestPump's own frame under ``bench boot auto``, whose
    stand-in NONE owns as before s118) -> the decode plus ``owns``. A frame that does not own still stamps the LANE (the
    caller's) but reads byte 1 SHUT: a guest that commands no slot here never freezes the host's Wait gauges. None =
    malformed (nothing stamped, the latch unmoved)."""
    d = decode_control(frame, battle_nonce)
    if d is None:
        return None
    owns = guest_owns_step(latch, d["trailer"], d["nonce"], d["boot"], battle_nonce) or bool(loopback_auto)
    d["owns"] = owns
    if not owns:
        d["menu"] = CTL_SHUT
    return d


def refused_report_phrase(rpt_nonce: int, rpt_boot: int, battle_nonce: int) -> str:
    """NetSyncBattle.RefusedReportPhrase -- the refused report in words (the refusal line's, the capture line's): "it
    reports declined for this battle" | "it reports none for this battle after reporting a diorama of it" | "its report
    names another battle (nonce N, live)"."""
    boot = boot_name(rpt_boot) or "?"
    if int(rpt_nonce) == int(battle_nonce) & 0xFF:
        return f"it reports {boot} for this battle" + (" after reporting a diorama of it" if rpt_boot == BOOT_NONE else "")
    return f"its report names another battle (nonce {int(rpt_nonce)}, {boot})"


HANDBACK_LOG_BUDGET = 8                  # hand-back lines per own battle (NetSyncBattle.HandbackLogBudget)


# ---- s119: THE DIORAMA HOLD KEYED ON THE PEER (NetSyncClient.DioramaWatchStep -- the guest's DioramaTick, booted branch)
WATCH_NOTHING, WATCH_HOLD, WATCH_LEAVE_FINAL = 0, 1, 2
WATCH_WHY_NONE, WATCH_WHY_NEW_NONCE, WATCH_WHY_TERMINAL, WATCH_WHY_HOST_FIELD, WATCH_WHY_HOLD_CAP = 0, 1, 2, 3, 4
WATCH_WHY_STALL_CAP = 5                  # [ff9mapkit netsync R3 s120] the peer alive, its battle lane silent past the stall cap
#: `netsync.diorama.hold.state` / `.why` (WatchStateName / WatchWhyName; null = none)
WATCH_STATE_NAMES = {WATCH_NOTHING: "nothing", WATCH_HOLD: "hold", WATCH_LEAVE_FINAL: "leave_final"}
WATCH_WHY_NAMES = {WATCH_WHY_NEW_NONCE: "new_nonce", WATCH_WHY_TERMINAL: "terminal", WATCH_WHY_HOST_FIELD: "host_field",
                   WATCH_WHY_HOLD_CAP: "cap", WATCH_WHY_STALL_CAP: "stall_cap"}
DIORAMA_SETTLE_MS = 500                  # the unbroken peer-alive run an over-verdict needs (and when a hold is COUNTED)
DIORAMA_HOLD_CAP_S119_MS = 8000          # s119's cap (the s56 DioramaBlipHoldMs); from s120 the cap IS the session grace
DIORAMA_STALL_CAP_MS = 8000              # s120's stall cap: a peer ALIVE that says nothing keeps s119's bound
DIORAMA_HOLD_LOG_MAX = 3                 # hold/resume line pairs per boot, then counted only
NO_FIELD = 65535                         # a position lane's "no field" (never a real one)
#: DioramaWatchSelfTest's own constants (WatchAt fixes the booted nonce, the settle and the cap -- and from s120 passes the
#: stall cap = the cap, so the s119 rows read as before)
WATCH_TEST_NONCE, WATCH_TEST_SETTLE, WATCH_TEST_CAP = 0x41, 500, 8000


def diorama_watch_step(live: bool, nonce: int, booted_nonce: int, peer_alive_: bool, host_field: int,
                       terminal_latched: bool, stale_ms: int, alive_ms: int, settle_ms: int, cap_ms: int,
                       stall_cap_ms: int, leave_why: int) -> tuple[int, int]:
    """NetSyncClient.DioramaWatchStep -> ``(verdict, why)``: THE WATCHER'S STEP for a booted wire diorama. Live: the same
    nonce is NOTHING, another LEAVE_FINAL (new_nonce). Stale: a decided leave (``leave_why``) stands; GENUINELY OVER only
    with the peer alive for ``settle_ms`` AND (the end latched terminal, or the host on a real field -- neither 0 nor
    65535); past ``cap_ms`` of staleness LEAVE_FINAL (cap); [s120] then, the peer alive for the settle and saying nothing,
    past ``stall_cap_ms`` LEAVE_FINAL (stall_cap) -- tested after the cap, so a stall cap at or above it changes nothing;
    every other stale frame HOLDS (frozen at the last applied state, no Leave). ``why`` is WATCH_WHY_NONE unless leaving."""
    if live:
        return (WATCH_NOTHING, WATCH_WHY_NONE) if nonce == booted_nonce else (WATCH_LEAVE_FINAL, WATCH_WHY_NEW_NONCE)
    if leave_why != WATCH_WHY_NONE:
        return WATCH_LEAVE_FINAL, leave_why
    settled = bool(peer_alive_) and alive_ms >= settle_ms
    if settled:
        if terminal_latched:
            return WATCH_LEAVE_FINAL, WATCH_WHY_TERMINAL
        if host_field > 0 and host_field != NO_FIELD:
            return WATCH_LEAVE_FINAL, WATCH_WHY_HOST_FIELD
    if stale_ms > cap_ms:
        return WATCH_LEAVE_FINAL, WATCH_WHY_HOLD_CAP
    if settled and stale_ms > stall_cap_ms:
        return WATCH_LEAVE_FINAL, WATCH_WHY_STALL_CAP
    return WATCH_HOLD, WATCH_WHY_NONE


def s56_watch_step(live: bool, nonce: int, booted_nonce: int, transport_up: bool, stale_ms: int,
                   cap_ms: int = DIORAMA_HOLD_CAP_S119_MS) -> int:
    """The PRE-s119 booted branch (s56, removed by s119) -- the calibration's red: live = the same nonce NOTHING, a new one
    LEAVE; stale with the hop UP = LEAVE at once ("stale + link UP -> the fight is over": behind the local bridge the hop
    stays up through any cut, so sitting A's cut left within ~2 s); stale with the hop down HOLDS until ``cap_ms``."""
    if live:
        return WATCH_NOTHING if nonce == booted_nonce else WATCH_LEAVE_FINAL
    if transport_up:
        return WATCH_LEAVE_FINAL
    return WATCH_LEAVE_FINAL if stale_ms > cap_ms else WATCH_HOLD


def watch_state_name(state: int) -> str | None:
    """NetSyncClient.WatchStateName -- `hold.state` (None = -1, no wire diorama stepped)."""
    return WATCH_STATE_NAMES.get(int(state))


def watch_why_name(why: int) -> str | None:
    """NetSyncClient.WatchWhyName -- `hold.why` (None = no LEAVE_FINAL this boot)."""
    return WATCH_WHY_NAMES.get(int(why))


def hold_cap_ms(session_grace_ms: int | None) -> int:
    """NetSyncClient.DioramaHoldCapMs -- THE ONE SEAM `hold.cap_ms` reads: s119's 8000, from s120 the session grace (pass
    None for an s119 engine)."""
    return DIORAMA_HOLD_CAP_S119_MS if session_grace_ms is None else int(session_grace_ms)


# ---- s120: THE SESSION GRACE (NetSyncClient.SessionGraceStep / SessionRampArms / ParseSessionGrace -- guest only)
SESSION_GRACE_DEFAULT_MS = 40000         # [Netsync] SessionGraceMs absent: [ff9mapkit netsync s132] the maximum (owner, sitting B)
SESSION_GRACE_DEFAULT_S120_MS = 30000    # ...and on s120-s131 (s120's owner decision: 30 s)
SESSION_GRACE_MIN_MS = 5000              # under this a Wi-Fi re-association reads as the session ending
SESSION_GRACE_MAX_MS = 40000             # under the bridge's 45 s redial hard cap (and the relay's 60 s rejoin grace)
SESSION_NONE, SESSION_LIVE, SESSION_GRACE, SESSION_ENDED = 0, 1, 2, 3
SESSION_STATE_NAMES = {SESSION_NONE: "none", SESSION_LIVE: "live", SESSION_GRACE: "grace", SESSION_ENDED: "ended"}
RAMP_CAUSE_NONE, RAMP_CAUSE_GRACE, RAMP_CAUSE_CONFIG, RAMP_CAUSE_UNFOLLOW = 0, 1, 2, 3
RAMP_CAUSE_NAMES = {RAMP_CAUSE_GRACE: "grace", RAMP_CAUSE_CONFIG: "config", RAMP_CAUSE_UNFOLLOW: "unfollow"}
SESSION_LOG_MAX = 20                     # outage/resume line pairs per link, then counted only
EXIT_RAMP_DEBOUNCE_S117_MS = 3000        # the link-loss ramp's debounce BEFORE s120 (ExitRampDebounceMs, removed)
#: `netsync.session.overlay`'s vocabulary (NetSyncClient.OverlayName; null = none composed yet)
OVERLAY_NAMES = ("off", "elsewhere", "no_code", "connecting", "waiting", "peer_elsewhere", "following", "peer_no_field",
                 "reconnecting")


def session_grace_step(peer_alive_: bool, seen: bool, out_ms: int, grace_ms: int) -> int:
    """NetSyncClient.SessionGraceStep -- THE SESSION'S STEP: the peer alive (PEER-ALIVE) is LIVE (an outage inside the
    grace RESUMES); nothing to lose (``seen`` false: no live peer on this link, no outage running, no mirror armed) is
    NONE; a silent peer is GRACE up to and AT ``grace_ms`` of outage, then ENDED."""
    if peer_alive_:
        return SESSION_LIVE
    if not seen:
        return SESSION_NONE
    return SESSION_ENDED if out_ms > grace_ms else SESSION_GRACE


def session_ramp_arms(mirroring: bool, pending: bool, follow_host: bool, state: int) -> bool:
    """NetSyncClient.SessionRampArms -- does the link-loss exit ramp arm now? Only for a mirroring guest whose ramp is not
    already pending, and only once the session ENDED (FollowHost dropped mid-mirror arms at once): an outage inside the
    grace arms nothing, so a peer back inside it leaves no ramp behind."""
    return bool(mirroring) and not pending and (not follow_host or state == SESSION_ENDED)


_INT32 = re.compile(r"[+-]?[0-9]+")


def parse_session_grace(raw) -> tuple[int, str | None]:
    """NetSyncClient.ParseSessionGrace -> ``(grace_ms, note)``: [Netsync] SessionGraceMs as the engine reads it. Quotes
    accepted (trimmed inside too); empty or absent keeps the default quietly; malformed (not an Int32) keeps it with a
    note; outside 5000-40000 -- a 0 too: the grace has no off switch -- clamps with a note. ``note`` = the line's text
    after ``[NetSync] `` (None = nothing logged). The live stack's default: [ff9mapkit netsync s132] 40000."""
    return _parse_session_grace(raw, SESSION_GRACE_DEFAULT_MS)


def parse_session_grace_s120(raw) -> tuple[int, str | None]:
    """:func:`parse_session_grace` as an s120-s131 engine reads the key: the same clamp and notes, its default 30000."""
    return _parse_session_grace(raw, SESSION_GRACE_DEFAULT_S120_MS)


def _parse_session_grace(raw, default: int) -> tuple[int, str | None]:
    s = "" if raw is None else str(raw).strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1].strip()
    if not _INT32.fullmatch(s) or not -2 ** 31 <= int(s) < 2 ** 31:
        note = None
        if s:
            note = (f"SessionGraceMs '{s}' malformed (want ms, {SESSION_GRACE_MIN_MS}-{SESSION_GRACE_MAX_MS}) -- keeping "
                    f"{default}")
        return default, note
    n = int(s)
    if n < SESSION_GRACE_MIN_MS or n > SESSION_GRACE_MAX_MS:
        c = SESSION_GRACE_MIN_MS if n < SESSION_GRACE_MIN_MS else SESSION_GRACE_MAX_MS
        why = ("a shorter grace ends the session on an ordinary Wi-Fi re-association" if n < SESSION_GRACE_MIN_MS
               else "the bridge gives up on its upstream at 45 s, the relay at 60 s")
        return c, (f"SessionGraceMs {n} is outside {SESSION_GRACE_MIN_MS}-{SESSION_GRACE_MAX_MS} -- clamped to {c} ms "
                   f"({why})")
    return n, None


def session_state_name(state: int) -> str | None:
    """NetSyncClient.SessionStateName -- `session.state` ("none" on a host / the selftest role; None = no instance)."""
    return SESSION_STATE_NAMES.get(int(state))


def ramp_cause_name(cause: int) -> str | None:
    """NetSyncClient.RampCauseName -- `session.ramp_cause` (None = none pending)."""
    return RAMP_CAUSE_NAMES.get(int(cause))


def session_left_ms(state: int, out_ms: int, grace_ms: int) -> int:
    """NetSyncClient.SessionGraceLeftMs -- the grace left in this outage (`session.left_ms`; -1 = not inside one: only
    GRACE has a countdown), floored at 0."""
    if state != SESSION_GRACE or out_ms < 0:
        return -1
    return max(0, int(grace_ms) - int(out_ms))


def overlay_left_sec(left_ms: int) -> int:
    """NetSyncClient.SessionGraceLeftSec -- the "reconnecting (N s left)" overlay's whole seconds, rounded UP (0 when none)."""
    return 0 if left_ms <= 0 else (int(left_ms) + 999) // 1000


# ---- s121: THE AUDIBLE MENU REFUSAL (NetSyncField.MenuKeyStep / MenuKeyRoute -- UIKeyTrigger's s38 gate, guest only)
MENU_KEY_OPEN, MENU_KEY_STOCK_OFF, MENU_KEY_REFUSE_AUDIBLE, MENU_KEY_REFUSE_SILENT, MENU_KEY_DIALOG_PATH = 0, 1, 2, 3, 4
#: `netsync.menu_refusal.now`'s vocabulary (NetSyncField.MenuKeyName; null = no UIManager)
MENU_KEY_NAMES = {MENU_KEY_OPEN: "open", MENU_KEY_STOCK_OFF: "off", MENU_KEY_REFUSE_AUDIBLE: "audible",
                  MENU_KEY_REFUSE_SILENT: "silent", MENU_KEY_DIALOG_PATH: "dialog"}
MENU_REFUSAL_SFX = 102                   # FF9Sfx 102: the stock refusal buzz (the Alt+F2 / Alt+F5 / Alt+F9 gates' own)
#: UIManager.GetSceneFromState's states WITH a scene (UIKeyTrigger's scene branch can run there). Folklore / Journal are
#: null while their [Folklore] / [Journal] section is off; Initial, QuadMistBattle, Quit and PreEnding have none.
UI_SCENE_STATES = frozenset(("FieldHUD", "WorldHUD", "BattleHUD", "Pause", "MainMenu", "Item", "Ability", "Equip",
                             "Status", "Card", "Config", "Serialize", "Cloud", "Shop", "NameSetting", "PartySetting",
                             "BattleResult", "Tutorial", "GameOver", "Title", "QuadMist", "Chocograph", "Ending",
                             "EndGame", "Folklore", "Journal"))


def menu_key_step(menu_control_enable: bool, mirroring: bool, state: str) -> int:
    """NetSyncField.MenuKeyStep -- THE MENU KEY'S VERDICT at UIKeyTrigger's s38 gate: a scene's own MENUOFF
    (IsMenuControlEnable false) is stock's silent refusal even on a mirroring guest; no mirror opens the main menu; a
    mirroring guest is refused AUDIBLY on FieldHUD / WorldHUD and silently anywhere else (the diorama's BattleHUD above
    all). ``state`` = the UIManager.UIState NAME."""
    if not menu_control_enable:
        return MENU_KEY_STOCK_OFF
    if not mirroring:
        return MENU_KEY_OPEN
    return MENU_KEY_REFUSE_AUDIBLE if state in ("FieldHUD", "WorldHUD") else MENU_KEY_REFUSE_SILENT


def menu_key_route(has_scene: bool, dialog_active: bool, paused: bool, verdict: int) -> int:
    """NetSyncField.MenuKeyRoute (review S121-R1) -- where UIKeyTrigger sends the press: its scene branch (the s38 gate,
    RefuseMainMenu) only with a scene for the state and no dialogue window -- or the pause screen up; otherwise the
    DIALOGUE path, which s121 never sees (on a mirroring guest a silent drop counted nowhere)."""
    return MENU_KEY_DIALOG_PATH if not has_scene or (dialog_active and not paused) else verdict


def menu_key_name(verdict: int) -> str | None:
    """NetSyncField.MenuKeyName -- `menu_refusal.now`."""
    return MENU_KEY_NAMES.get(int(verdict))


def menu_key_now(menu_control_enable: bool, mirroring: bool, state: str, dialog_active: bool, paused: bool,
                 *, has_scene: bool | None = None) -> str | None:
    """NetSyncField.HarnessMenuKeyNow -- what a Menu press would do RIGHT NOW (a bench gates its press on "audible", never
    on ui_state FieldHUD: under a dialogue window it reads "dialog"). ``has_scene`` defaults to the state's
    :data:`UI_SCENE_STATES` membership; ``paused`` is UIManager.IsPause."""
    scene = state in UI_SCENE_STATES if has_scene is None else bool(has_scene)
    return menu_key_name(menu_key_route(scene, dialog_active, paused, menu_key_step(menu_control_enable, mirroring, state)))


def menu_refusal_place(state: str, fld_map_no: int, wld_map_no: int) -> int:
    """RefuseMainMenu's place (review S121-R2): wldMapNo on WorldHUD -- no world-map code writes fldMapNo, which keeps the
    field the party LEFT -- else fldMapNo (`menu_refusal.last_field`)."""
    return int(wld_map_no) if state == "WorldHUD" else int(fld_map_no)


def menu_refusal_latch(state: str) -> str:
    """The DeclineOnce gate-class an audible refusal latches on: "main menu" on a field, "main menu (world map)" on
    WorldHUD (DeclineOnceAt, its own class)."""
    return "main menu (world map)" if state == "WorldHUD" else "main menu"


def menu_refusal_line(state: str, place: int) -> str:
    """The audible refusal's one line (DeclineOnce / DeclineOnceAt: once per process per (class, place), never cleared at
    session end): "...on field N", or "...on world map W" on WorldHUD."""
    where = f"world map {int(place)}" if state == "WorldHUD" else f"field {int(place)}"
    return f"[NetSync] main menu suppressed (following guest) on {where}"


# ---- the round's log needles: literal heads of stack lines a bench greps (test_harness_netsync.py pins each one)
LOG_HANDBACK_CAPTURE = "[NetSync] hand-back: the host's local window holds guest slot "     # s110 (s118 names a report)
LOG_HANDBACK_HANDED = " handed BACK to the guest -- "                                        # s110, after "guest slot N"
LOG_HANDBACK_REFUSED = "[NetSync] hand-back: the guest's control lane is live but "          # s118, once per own battle
LOG_DIORAMA_HOLD_CUT = "[NetSync] diorama: peer silent mid-battle -- holding the scene frozen"           # s119
LOG_DIORAMA_HOLD_STALL = "[NetSync] diorama: the host's battle lane stalled mid-battle with the peer alive on field "
LOG_DIORAMA_RESUME = "[NetSync] diorama: the host's battle lane is back on the same fight (nonce "
LOG_DIORAMA_GAVE_UP = "[NetSync] diorama: the host's battle lane is still silent after "    # the cap / the stall cap
LOG_SESSION_OUTAGE = "[NetSync] session: the host went silent ("                             # s120
LOG_SESSION_BACK = "[NetSync] session: the host is back after "
LOG_SESSION_GAVE_UP = "[NetSync] session: the host has been silent for "
LOG_MENU_SUPPRESSED = "[NetSync] main menu suppressed (following guest) on "                 # s121
#: the deployed s117's RED markers (sitting A's guest log, laptop-Memoria.log:155-166): a cut read as "the fight is over"
LOG_RED_LEAVE_REQUESTED = "[NetSync] diorama LEAVE requested -> FieldMap"
LOG_RED_WATCHER_SETTLED = "[NetSync] diorama watcher-leave settled (nonce "
LOG_RED_SESSION_ENDED = "[NetSync] session ended -> reloading own autosave (Continue)"
LOG_S56_BLIP_HOLD = "[NetSync] diorama: mid-battle link blip -- holding the scene frozen"    # s56's hold line (s119 removed it)

#: NetSyncBattle's integer constants the s118 half reads by C# name (the rule itself reads s114's Boot* / Ctl*).
CS_OWN_CONSTANTS = {"HandbackLogBudget": HANDBACK_LOG_BUDGET}
#: NetSyncClient's s119-s120 integer constants, by C# name (the test reads them off the stack's NetSyncClient.cs).
CS_CLIENT_CONSTANTS = {
    "WatchNothing": WATCH_NOTHING, "WatchHold": WATCH_HOLD, "WatchLeaveFinal": WATCH_LEAVE_FINAL,
    "WatchWhyNone": WATCH_WHY_NONE, "WatchWhyNewNonce": WATCH_WHY_NEW_NONCE, "WatchWhyTerminal": WATCH_WHY_TERMINAL,
    "WatchWhyHostField": WATCH_WHY_HOST_FIELD, "WatchWhyHoldCap": WATCH_WHY_HOLD_CAP,
    "WatchWhyStallCap": WATCH_WHY_STALL_CAP, "DioramaSettleMs": DIORAMA_SETTLE_MS,
    "DioramaStallCapMs": DIORAMA_STALL_CAP_MS, "DioramaHoldLogMax": DIORAMA_HOLD_LOG_MAX,
    "WatchTestNonce": WATCH_TEST_NONCE, "WatchTestSettle": WATCH_TEST_SETTLE, "WatchTestCap": WATCH_TEST_CAP,
    "SessionGraceDefaultMs": SESSION_GRACE_DEFAULT_MS, "SessionGraceMinMs": SESSION_GRACE_MIN_MS,
    "SessionGraceMaxMs": SESSION_GRACE_MAX_MS, "SessionNone": SESSION_NONE, "SessionLive": SESSION_LIVE,
    "SessionGrace": SESSION_GRACE, "SessionEnded": SESSION_ENDED, "RampCauseNone": RAMP_CAUSE_NONE,
    "RampCauseGrace": RAMP_CAUSE_GRACE, "RampCauseConfig": RAMP_CAUSE_CONFIG, "RampCauseUnfollow": RAMP_CAUSE_UNFOLLOW,
    "SessionLogMax": SESSION_LOG_MAX,
}
#: NetSyncField's s121 integer constants, by C# name.
CS_FIELD_CONSTANTS = {"MenuKeyOpen": MENU_KEY_OPEN, "MenuKeyStockOff": MENU_KEY_STOCK_OFF,
                      "MenuKeyRefuseAudible": MENU_KEY_REFUSE_AUDIBLE, "MenuKeyRefuseSilent": MENU_KEY_REFUSE_SILENT,
                      "MenuKeyDialogPath": MENU_KEY_DIALOG_PATH}


# ======================================================================================== [ff9mapkit netsync s131]
# THE EXPIRED SEQ (studies/battle-coop/R3-SITTING-A-FIXES.md, "The hold-onset variance: the Pump null RE-ADOPT"). The
# guest's Pump keys its battle lane's freshness to the HOST's seq (s40): `_peerViewTick` is restamped only when a new seq is
# adopted, and the first stale frame nulls `_peerView`. The transport keeps serving the host's last frame until its own
# last receipt + 2000 (the host re-sends each seq 4-5 times), so that frame outlives the run-out by the cut's "tail"
# (0-133 ms) -- and before s131 the `_peerView == null` disjunct RE-ADOPTED it on the next Update: a phantom second 2000 ms
# of "live" in ~79% of cuts (the s119 hold started ~1.9 s late). s131 remembers the expired (nonce, seq) and refuses the
# transport's repeats of it; a new seq or a new nonce is adopted as before. Each function below is its C# twin in
# NetSyncBattle; test_harness_netsync.py EVALUATES PeerAdoptSelfTest's own rows against them (read off the stack) and pins
# the constants by name (CS_ADOPT_CONSTANTS). OWNER-ACCEPTED SIDE EFFECT: a host whose game thread stalls while its writer
# keeps re-sending one seq now reads stale at 2000 ms and STAYS stale (a 'stalled' hold, then the s120 stall cap's final
# leave) -- :class:`PeerLane` with ``tail_ms < 0`` scripts.
PROOF_ADOPT = "peer adopt selftest: "              # NetSyncBattle.PeerAdoptSelfTest (s131), logged right after PROOF_MENU
ADOPT_SELFTEST_ROWS = 20                           # 15 step rows + 5 rows of Pump's lane order over served-frame scripts
ADOPT_NONE, ADOPT_REPEAT, ADOPT_NEW, ADOPT_REFUSED = 0, 1, 2, 3
READOPT_LOG_MAX = 3                                # refused re-adopt EPISODES logged per host battle (its nonce), then one
                                                   # 'further ones ... counted, not logged' line; Reset() re-arms the budget
#: PeerAdoptSelfTest's own constants (the table is pure: a retuned live StaleMs never moves its rows)
ADOPT_TEST_NONCE, ADOPT_TEST_STALE_MS, ADOPT_TEST_FRAME_MS, ADOPT_TEST_SAMPLE_MS = 0x41, 2000, 10, 150
#: `netsync.battle.peer.expired` in AppendPeerExpired's key order, at AppendNetsync's catch-line sentinels: ``seq`` /
#: ``nonce`` the expired memo (-1 = none), ``count`` run-outs, ``refused`` refused re-adopt EPISODES, ``frames`` refused
#: repeat frames (the three monotonic per process: read DELTAS), ``ms`` the last episode's run-out to its last refused
#: repeat (-1 = none yet). The key absent = an engine that still re-adopts (s121 and older).
PEER_EXPIRED_SENTINELS = {"seq": -1, "nonce": -1, "count": 0, "refused": 0, "frames": 0, "ms": -1}
#: the episode line's head (the first READOPT_LOG_MAX per host battle) and the budget's last line's head
LOG_READOPT_REFUSED = "[NetSync] battle lane: the host's last frame (nonce "
LOG_READOPT_MUTED = "[NetSync] battle lane: refused re-adopt "


def new_peer_lane_memo() -> dict:
    """NetSyncBattle.PeerLaneMemo at its default -- no memo (Reset's state, and the first view ever's): ``armed`` (a view's
    freshness ran out and nothing was adopted since), ``seq`` / ``nonce`` (that view's), ``refused`` (the transport's
    repeats of it refused since; 1 = this run-out's episode just opened)."""
    return {"armed": False, "seq": 0, "nonce": 0, "refused": 0}


def peer_adopt_step(m: dict, seq: int, nonce: int, cur_seq: int) -> int:
    """NetSyncBattle.PeerAdoptStep -- THE ADOPT DECISION in Pump's guest branch, advancing the memo ``m`` in place.
    ``seq`` / ``nonce`` = the frame the transport serves this tick (seq -1 = none, or it did not parse); ``cur_seq`` = the
    seq of the view in hand (-1 = none: nulled, or never one). A view in hand yields only to a NEW seq (the s40 guard,
    seq only: the same seq re-served is ADOPT_REPEAT); with none in hand any frame is ADOPT_NEW -- except a transport
    repeat of the (nonce, seq) whose freshness ran out (``m`` armed by :func:`peer_expire_step`): ADOPT_REFUSED, counted in
    ``m["refused"]``. Every adopt clears the memo."""
    if seq < 0:
        return ADOPT_NONE
    if cur_seq >= 0 and seq == cur_seq:
        return ADOPT_REPEAT
    if cur_seq < 0 and m["armed"] and seq == m["seq"] and nonce == m["nonce"]:
        m["refused"] += 1
        return ADOPT_REFUSED
    m.update(new_peer_lane_memo())
    return ADOPT_NEW


def peer_expire_step(m: dict, cur_seq: int, cur_nonce: int) -> bool:
    """NetSyncBattle.PeerExpireStep -- THE RUN-OUT (Pump's stale branch, right before it nulls the view): the view in hand
    (``cur_seq`` >= 0) becomes the expired frame, its episode not yet open (refused 0); nothing in hand leaves the memo as
    it is. True = a view ran out (Pump counts it in ``count`` and stamps the run-out's tick)."""
    if cur_seq < 0:
        return False
    m.update(armed=True, seq=int(cur_seq), nonce=int(cur_nonce), refused=0)
    return True


def peer_lane_forget(m: dict) -> None:
    """NetSyncBattle.PeerLaneForget -- Reset's half: no expired frame (the first frame after it is adopted, whatever it
    is)."""
    m.update(new_peer_lane_memo())


def pre_s131_adopts(seq: int, cur_seq: int) -> bool:
    """The PRE-s131 adopt test (s37's null-reset under s40's seq guard, the one line s131 removed) -- the calibration's
    red: ``view != null && (_peerView == null || view.Seq != _peerView.Seq)``. With nothing in hand ANY frame is adopted,
    the expired one included: the phantom second 2000 ms."""
    return seq >= 0 and (cur_seq < 0 or seq != cur_seq)


def cut_script(last_ms: int, tail_ms: int, resume_ms: int, total_ms: int) -> list:
    """NetSyncBattle.CutScript -- a served-frame script over ``total_ms`` (frame i at tick i * ADOPT_TEST_FRAME_MS; each
    entry the seq the transport serves then, -1 = none): the host's seq advances every ADOPT_TEST_SAMPLE_MS up to its last
    pre-cut seq (first served at ``last_ms``, a multiple of the cadence), which the transport serves until that seq's last
    receipt (``last_ms + tail_ms``) + ADOPT_TEST_STALE_MS -- ``tail_ms`` < 0 = forever: a stalled host whose writer keeps
    re-sending it -- then nothing; from ``resume_ms`` (>= 0) the host's new seqs."""
    out = []
    last = last_ms // ADOPT_TEST_SAMPLE_MS
    for i in range(total_ms // ADOPT_TEST_FRAME_MS + 1):
        t = i * ADOPT_TEST_FRAME_MS
        if 0 <= resume_ms <= t:
            out.append(last + 1 + (t - resume_ms) // ADOPT_TEST_SAMPLE_MS)
        elif t < last_ms:
            out.append(t // ADOPT_TEST_SAMPLE_MS)
        elif tail_ms < 0 or t <= last_ms + tail_ms + ADOPT_TEST_STALE_MS:
            out.append(last)
        else:
            out.append(-1)
    return out


def adopt_replay(served, memo: bool) -> tuple:
    """NetSyncBattle.AdoptReplay -> ``(refused, stale_at, reopen_at)``: Pump's lane order over a served-frame script (frame
    i at tick i * ADOPT_TEST_FRAME_MS) -- the adopt (a new frame restamps), the freshness test (ADOPT_TEST_STALE_MS), the
    run-out (:func:`peer_expire_step`, then the null). ``memo`` False = the PRE-s131 step (the memo forgotten before every
    adopt: the old ``_peerView == null`` disjunct). ``refused`` = the refused repeats; ``stale_at`` = the first
    live->stale tick, ``reopen_at`` = the first stale->live tick after it (-1 = never)."""
    m = new_peer_lane_memo()
    cur, tick, refused, was_live, stale_at, reopen_at = -1, 0, 0, False, -1, -1
    for i, seq in enumerate(served):
        now = i * ADOPT_TEST_FRAME_MS
        if not memo:
            peer_lane_forget(m)
        adopt = peer_adopt_step(m, seq, ADOPT_TEST_NONCE, cur)
        if adopt == ADOPT_NEW:
            cur, tick = seq, now
        elif adopt == ADOPT_REFUSED:
            refused += 1
        live = cur >= 0 and now - tick < ADOPT_TEST_STALE_MS
        if not live:
            peer_expire_step(m, cur, ADOPT_TEST_NONCE)
            cur = -1
        if was_live and not live and stale_at < 0:
            stale_at = now
        elif not was_live and live and stale_at >= 0 and reopen_at < 0:
            reopen_at = now
        was_live = live
    return refused, stale_at, reopen_at


def readopt_line(nonce: int, seq: int, refused: int) -> str:
    """NoteRefusedReadopt's episode line (logged on an episode's FIRST refused repeat, for the first READOPT_LOG_MAX
    episodes of a host battle); ``refused`` = the episode count after it (`peer.expired.refused`)."""
    return (f"{LOG_READOPT_REFUSED}{int(nonce)}, seq {int(seq)}) ran out of freshness and the transport served it again -- "
            f"not re-adopted: a repeat is never news, the lane stays stale until a new frame (a fight's end, a cut or a "
            f"stalled host); refused={int(refused)}")


def readopt_muted_line(n: int, nonce: int, refused: int) -> str:
    """NoteRefusedReadopt's budget line: episode ``n`` (= READOPT_LOG_MAX + 1) of a host battle, the last one logged."""
    return (f"{LOG_READOPT_MUTED}{int(n)} on the host's battle (nonce {int(nonce)}) -- further ones on it are counted, not "
            f"logged (netsync.battle.peer.expired); refused={int(refused)}")


class PeerLane:
    """[ff9mapkit netsync s131] The GUEST's battle lane as Pump runs it, with s131's statics: the memo, the run-out counter
    and tick, the refused episodes / frames / span, the log budget -- `netsync.battle.peer.expired` is :meth:`doc`, and
    every line NoteRefusedReadopt writes is appended to :attr:`lines`. Per PROCESS like the engine's statics: the counters
    survive :meth:`reset` (NetSyncBattle.Reset: the memo forgotten, the view nulled, the log budget re-armed). ``memo``
    False models the PRE-s131 engine (the memo forgotten before every adopt: the re-adopt, no refusals) -- its lane only:
    that engine publishes no `expired` key. The selftest role never steps this (its loopback writes the view directly,
    so nothing runs out): a wire replay with a cut is its bench."""

    def __init__(self, memo: bool = True, stale_ms: int = STALE_MS) -> None:
        self.memo_on = bool(memo)
        self.stale_ms = int(stale_ms)
        self.m = new_peer_lane_memo()               # _peerLane
        self.view = None                            # _peerView as (seq, nonce); None = no view in hand
        self.tick = 0                               # _peerViewTick (the adopt's tick)
        self.live = False                           # PeerBattleLive
        self.expiries = 0                           # _peerExpiries -- monotonic
        self.expiry_tick = -60000                   # _peerExpiryTick (tick-baseline law: 60 s before the first pump)
        self.episodes = 0                           # _readoptEpisodes -- monotonic
        self.frames = 0                             # _readoptFrames -- monotonic
        self.ms = -1                                # _readoptMs (-1 = none yet)
        self.log_nonce = -1                         # _readoptLogNonce (-1 = none -- reset() re-arms it)
        self.logged = 0                             # _readoptLogged
        self.lines: list = []                       # the Log.Message lines, in order (each WITH its "[NetSync] " head)

    def pump(self, now_ms: int, served=None) -> bool:
        """One Pump tick at ``now_ms`` -> PeerBattleLive. ``served`` = the ``(seq, nonce)`` the transport serves this tick
        (None = GetRemoteBattle null; a seq of -1 = a frame that did not parse). The adopt, then the freshness test, then
        -- not live -- the run-out and the null (Pump's stale branch)."""
        if served is not None:
            seq, nonce = int(served[0]), int(served[1])
            if not self.memo_on:
                peer_lane_forget(self.m)
            adopt = peer_adopt_step(self.m, seq, nonce, self.view[0] if self.view is not None else -1)
            if adopt == ADOPT_NEW:
                self.view, self.tick = (seq, nonce), int(now_ms)
            elif adopt == ADOPT_REFUSED:
                self._note_refused(int(now_ms))
        live = self.view is not None and int(now_ms) - self.tick < self.stale_ms
        if not live:
            if self.view is not None and peer_expire_step(self.m, self.view[0], self.view[1]):
                self.expiries += 1
                self.expiry_tick = int(now_ms)
            self.view = None
        self.live = live
        return live

    def _note_refused(self, now_ms: int) -> None:
        """NoteRefusedReadopt: every refused repeat counts a frame and the episode's span; the FIRST refused repeat of a
        run-out counts one episode and writes its one line (the first READOPT_LOG_MAX of a host battle; then one budget
        line; then nothing -- the counters never stop)."""
        self.frames += 1
        self.ms = now_ms - self.expiry_tick
        if self.m["refused"] != 1:
            return
        self.episodes += 1
        if self.m["nonce"] != self.log_nonce:
            self.log_nonce, self.logged = self.m["nonce"], 0
        self.logged += 1
        if self.logged <= READOPT_LOG_MAX:
            self.lines.append(readopt_line(self.m["nonce"], self.m["seq"], self.episodes))
        elif self.logged == READOPT_LOG_MAX + 1:
            self.lines.append(readopt_muted_line(self.logged, self.m["nonce"], self.episodes))

    def reset(self) -> None:
        """NetSyncBattle.Reset's s131 half (and its null of the view): the memo forgotten, the log budget re-armed; the
        counters stay."""
        self.view = None
        self.live = False
        peer_lane_forget(self.m)
        self.log_nonce, self.logged = -1, 0

    def run(self, served, *, nonce: int = ADOPT_TEST_NONCE, frame_ms: int = ADOPT_TEST_FRAME_MS, t0_ms: int = 0) -> list:
        """Pump a served-seq script (:func:`cut_script`'s shape: -1 = nothing served) one tick per ``frame_ms`` from
        ``t0_ms``, every frame of host battle ``nonce`` -> the PeerBattleLive flags, in order."""
        return [self.pump(t0_ms + i * frame_ms, None if seq < 0 else (seq, nonce)) for i, seq in enumerate(served)]

    def doc(self) -> dict:
        """HarnessAgent.AppendPeerExpired -- `netsync.battle.peer.expired` (the memo's seq / nonce only while it is armed)."""
        armed = self.m["armed"]
        return {"seq": self.m["seq"] if armed else -1, "nonce": self.m["nonce"] if armed else -1, "count": self.expiries,
                "refused": self.episodes, "frames": self.frames, "ms": self.ms}


#: NetSyncBattle's s131 integer constants, by C# name (StaleMs / SampleMs: the live lane's, which the test table mirrors).
CS_ADOPT_CONSTANTS = {"AdoptNone": ADOPT_NONE, "AdoptRepeat": ADOPT_REPEAT, "AdoptNew": ADOPT_NEW,
                      "AdoptRefused": ADOPT_REFUSED, "ReadoptLogMax": READOPT_LOG_MAX, "AdoptTestNonce": ADOPT_TEST_NONCE,
                      "AdoptTestStaleMs": ADOPT_TEST_STALE_MS, "AdoptTestFrameMs": ADOPT_TEST_FRAME_MS,
                      "AdoptTestSampleMs": ADOPT_TEST_SAMPLE_MS, "StaleMs": STALE_MS, "SampleMs": SAMPLE_MS}


# ======================================================================================== [ff9mapkit netsync s133]
# THE HOST ACTION-START LANE (studies/battle-coop/R3-DESIGN.md 2 and 3.3.2, as amended by R3-ACTION-REPLAY-AUDIT.md 2.1 --
# the design's "s122": group 2 was renumbered s133-s141). HOST ONLY, no visible change: every action an own battle runs
# ships a START record before its first impact and an END after its last, each impact carries the action's id, and type-1
# header flags bit 5 says so. Three additive type-6 records ride behind the unchanged 46-byte layout (wire stays v14):
#   IMPACT, 52 B: the 46 bytes, then [46] 0xA6 [47] fmt 1 [48] extLen 3 [49] kind 1 [50-51] actId (0 = no lifecycle);
#   START,  76 B: an INERT head ([0] nonce [1-2] the host _seq NOT consumed [3-4] 0xFF 0xFF [5-40] zero [41] flags 0x04
#                 [42-45] cmd/sub) + [46] 0xA6 [47] 1 [48] 27 [49] kind 2 [50-51] actId [52] actor slot [53] actor flags
#                 [54-55] cmd_no [56-59] sub_no [60-61] tar_id [62] cursor [63] info [64-65] magic_caster_id [66] vfx kind
#                 [67-70] vfx num [71-74] PatchedVfx [75] host Speed;
#   END,    52 B: the inert head with flags 0x08 + [46] 0xA6 [47] 1 [48] 3 [49] kind 3 [50-51] actId.
# extLen is a u8 (audit D7) -- NOT the 0xB5 end trailer's u16. Stat ticks (flags bit 7) stay 46 bytes (D3). Every function
# below is its C# twin in NetSyncBattle (s133); test_harness_netsync.py EVALUATES ActionSelfTest's own 30 rows against them
# (read off the stack, in order) and pins the constants by name (CS_ACTION_CONSTANTS, audit amendment 11) -- a drift on
# either side turns a test red. :class:`ActHostLane` is the lane with its statics (the stand-in's model of it).
CAP_ACTION_STARTS = 0x20                 # type-1 header flags bit 5: this host sends action STARTs/ENDs and impact ids
ACT_FLAG_START = 0x04                    # type-6 flags bit 2: a START record (slots 0xFF/0xFF)
ACT_FLAG_END = 0x08                      # type-6 flags bit 3: an END record (slots 0xFF/0xFF)
ACT_FLAG_STAT_TICK = 0x80                # type-6 flags bit 7 (B3.6): a stat tick -- 46 bytes, never extended
ACT_EXT_TAG = 0xA6                       # byte 46
ACT_EXT_FMT1 = 1                         # byte 47
ACT_EXT_LEN_ID = 3                       # byte 48 of an IMPACT or an END (kind + id)
ACT_EXT_LEN_START = 27                   # byte 48 of a START (kind + id + the 24-byte body)
ACT_EXT_IMPACT, ACT_EXT_START, ACT_EXT_END = 1, 2, 3       # byte 49
ACT_LEGACY_LEN, ACT_ID_RECORD_LEN, ACT_START_RECORD_LEN = 46, 52, 76
VFX_KIND_NONE, VFX_KIND_SEQ, VFX_KIND_ENEMY, VFX_KIND_SPECIAL, VFX_KIND_COMMON, VFX_KIND_UNKNOWN = 0, 1, 2, 3, 4, 0xFF
#: `netsync.battle.act.host.kinds`, in AppendAct's order (HarnessActKind 0..5: unknown is index 5)
VFX_KIND_KEYS = ("none", "seq", "enemy", "special", "common", "unknown")
ACTOR_IS_PLAYER, ACTOR_HOST_REWORK, ACTOR_HOST_FAST, ACTOR_SCRIPTED = 0x01, 0x02, 0x04, 0x08
ACTOR_MONSTER_TRANSFORM, ACTOR_COUNTER_SLOT, ACTOR_DOUBLE_CAST = 0x10, 0x20, 0x40
ACT_INFO_METEOR_MISS, ACT_INFO_SHORT_SUMMON, ACT_INFO_COVER = 0x01, 0x02, 0x04
ACT_TAPE_CAP, ACT_TAPE_PAGE_MAX = 1024, 16
ACT_EXT_READ_NONE, ACT_EXT_READ_OK, ACT_EXT_READ_BAD, ACT_EXT_READ_FMT = 0, 1, 2, 3
ACT_STEP_NEW, ACT_STEP_TAKEOVER, ACT_STEP_RESTART, ACT_STEP_REENTRY, ACT_STEP_REUSE = 0, 1, 2, 3, 4
ACT_LOG_TAKEOVER, ACT_LOG_REENTRY, ACT_LOG_RESTART, ACT_LOG_UNRESOLVED, ACT_LOG_DRIFT = 1, 2, 4, 8, 16
ACT_TEST_NONCE = 0x5A                    # ActionSelfTest's own nonce (the table is pure)
ACTION_BUFFER_CAP = 64                   # the host's drop-oldest _actionsOut (unchanged by s133: audit D4)
PROOF_ACTION = "action lane selftest: "  # NetSyncBattle.ActionSelfTest (s133), logged right after PROOF_ADOPT
ACTION_SELFTEST_ROWS = 30                # 13 codec + 8 id-book + 6 loopback-audit + 3 describe-verdict rows
#: the stock ids the lane's twins and the s133 bench name (BattleCommandId; BattleAbilityId.Attack; RegularItem.Potion;
#: SpecialEffect.Special_No_Effect) -- stock enums, not in the patch stack: test_harness_netsync.py reads each off the
#: shared Memoria clone when it is present (CS_STOCK_IDS: the C# name -> the value here)
CMD_ATTACK_ID, CMD_DEFEND_ID, CMD_CHANGE_ID, CMD_ITEM_ID, CMD_BLACK_MAGIC_ID = 1, 4, 7, 14, 22
CMD_ENEMY_ATK, CMD_MAGIC_COUNTER, CMD_ENEMY_COUNTER, CMD_ENEMY_DYING, CMD_ENEMY_REACTION = 47, 50, 53, 54, 55
CMD_SYS_TRANS = 59
SPECIAL_NO_EFFECT = -1
ABILITY_ATTACK_ID = 176                  # BattleAbilityId.Attack: the Attack command's sub_no
ITEM_POTION_ID = 236                     # RegularItem.Potion: an Item command's sub_no
CS_STOCK_IDS = {
    "BattleCommandId.Attack": CMD_ATTACK_ID, "BattleCommandId.Defend": CMD_DEFEND_ID,
    "BattleCommandId.Change": CMD_CHANGE_ID, "BattleCommandId.Item": CMD_ITEM_ID,
    "BattleCommandId.BlackMagic": CMD_BLACK_MAGIC_ID, "BattleCommandId.EnemyAtk": CMD_ENEMY_ATK,
    "BattleCommandId.MagicCounter": CMD_MAGIC_COUNTER, "BattleCommandId.EnemyCounter": CMD_ENEMY_COUNTER,
    "BattleCommandId.EnemyDying": CMD_ENEMY_DYING, "BattleCommandId.EnemyReaction": CMD_ENEMY_REACTION,
    "BattleCommandId.SysTrans": CMD_SYS_TRANS, "SpecialEffect.Special_No_Effect": SPECIAL_NO_EFFECT,
    "BattleAbilityId.Attack": ABILITY_ATTACK_ID, "RegularItem.Potion": ITEM_POTION_ID}

#: `netsync.battle.act.host` at AppendNetsync's catch-line sentinels, in AppendAct's key order (counts 0, nonce / ms -1,
#: bools false, strings and nullable records null, the fixed sub-objects written out whole). The live block differs at
#: rest only where the agent reads a static: `tape.state` reads "off" (HarnessActTapeState), `on` reads Enabled && the lever.
ACT_HOST_SENTINELS = {
    "on": False, "lever_off": False, "nonce": -1, "starts": 0, "ends": 0, "ext_impacts": 0, "noid_impacts": 0,
    "scripted": 0, "open": 0, "dropped": 0, "wire_dropped": 0, "unresolved": 0, "scripted_takeover": 0,
    "scripted_reentry": 0,
    "restarted": 0, "no_end": 0, "cut": 0, "edge_declined": 0,
    "kinds": {k: 0 for k in VFX_KIND_KEYS},
    "vfx": {"checked": 0, "drift": 0, "unchecked": 0, "why": None},
    "last": None,
    "loop": {"starts": 0, "ends": 0, "impacts": 0, "impacts_ext": 0, "stat": 0, "ext_bad": 0, "paired": 0, "orphans": 0,
             "caster_mismatch": 0, "no_end": 0, "cut": 0},
    "tape": {"state": None, "frames": 0, "starts": 0, "ms": -1, "overflow": 0, "page": None},
}
#: `act.host.last` (HarnessActLast: the last START as shipped, decoded) -> the PeerAction field it reads
ACT_LAST_FIELDS = {"id": "act_id", "actor": "actor_slot", "flags": "actor_flags", "cmd": "act_cmd_no", "sub": "act_sub_no",
                   "tar": "act_tar_id", "cursor": "act_cursor", "info": "act_info", "magic": "act_magic_caster",
                   "kind": "vfx_kind", "num": "vfx_num", "patched": "act_patched_vfx", "speed": "host_speed"}
#: `act.host.tape.page` (one `tape dump`) and each of its frames, in AppendAct's order
ACT_PAGE_KEYS = ("from", "count", "total", "frames")
ACT_PAGE_FRAME_KEYS = ("i", "ms", "hex")
#: the engine's words (each a C# literal of the stack, or its head)
LOG_ACT_CLOSED = "[NetSync] action lane: own battle (nonce "
LOG_ACT_NEVER_ENDED = " START(s) never ENDed at the own battle's "
LOG_ACT_DRIFT = "[NetSync] action lane: describe drift -- "
LOG_ACT_UNRESOLVED = " has no wire actor -- no START, no id, "
LOG_ACT_EDGE = "START before the own battle's rising edge declined ("
LOG_ACT_CODEC_DRIFT = "[NetSync] selftest: an action frame failed to parse (codec drift)"
LOG_ACT_DROP = "[NetSync] action buffer hit its cap ("
LOG_ACT_LEVER_OFF = ("[NetSync] harness: action STARTs OFF -- CALIBRATION: the pre-s133 host (no START/END records, no "
                     "impact ids, no caps bit 5)")
LOG_ACT_LEVER_ON = "[NetSync] harness: action STARTs ON"
LOG_ACT_LEVER_RELEASED = "[NetSync] harness: action STARTs back ON (released with the harness)"
LOG_ACT_TAPE_REC = "[NetSync] harness: action tape RECORDING -- every type-6 frame the selftest loopback receives, up to "
LOG_ACT_TAPE_STOPPED = "[NetSync] harness: action tape stopped -- "
LOG_ACT_TAPE_CLEARED = "[NetSync] harness: action tape cleared ("
LOG_ACT_TAPE_FULL = "[NetSync] action tape: full at "
LOG_ACT_TAPE_INFO = "[NetSync] action tape: "
LOG_ACT_TAPE_PAGE = "[NetSync] harness: action tape frames "

_ACT_HEAD = struct.Struct("<BHBBHiiHiiIIIIBHH")          # the 46-byte type-6 layout (QueueActionFrame / TryParseAction)
_ACT_START_BODY = struct.Struct("<BBBBHBBHiHBBHBiiB")     # bytes 46-75 of a START
_ACT_ID_EXT = struct.Struct("<BBBBH")                     # bytes 46-51 of an IMPACT / END (WriteIdExt)
#: the 46-byte fields, in TryParseAction's read order -- PeerAction's names, snake_cased
ACT_LEGACY_FIELDS = ("nonce", "seq_horizon", "caster_slot", "target_slot", "fig_info_t", "fig_hp_t", "fig_mp_t",
                     "fig_info_c", "fig_hp_c", "fig_mp_c", "tgt_hp_raw", "tgt_mp_raw", "cast_hp_raw", "cast_mp_raw",
                     "flags", "cmd_no", "sub_no")
#: the extension's fields (ReadActionExt / ClearActionExt), PeerAction's names snake_cased
ACT_EXT_FIELDS = ("has_ext", "ext_kind", "act_id", "actor_slot", "actor_flags", "act_cmd_no", "act_sub_no", "act_tar_id",
                  "act_cursor", "act_info", "act_magic_caster", "vfx_kind", "vfx_num", "act_patched_vfx", "host_speed")


def _act_u8(v: int) -> int:
    return int(v) & 0xFF


def _act_u16(v: int) -> int:
    return int(v) & 0xFFFF


def _act_i32(v: int) -> int:
    v = int(v) & 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def _act_u32(v: int) -> int:
    return int(v) & 0xFFFFFFFF


def vfx_kind_name(kind: int) -> str:
    """NetSyncBattle.VfxKindName: none / seq / enemy / special / common, anything else "unknown"."""
    return {VFX_KIND_NONE: "none", VFX_KIND_SEQ: "seq", VFX_KIND_ENEMY: "enemy", VFX_KIND_SPECIAL: "special",
            VFX_KIND_COMMON: "common"}.get(int(kind), "unknown")


def act_kind_index(kind: int) -> int:
    """NetSyncBattle.ActKindIndex: the `kinds` slot of a vfx kind (0-4 as is, anything else 5 = unknown)."""
    return int(kind) if 0 <= int(kind) <= VFX_KIND_COMMON else 5


def _act_flag_props(a: dict) -> dict:
    """PeerAction's computed flag properties (DmgMot .. StatTick), kept beside the Flags they read."""
    f = int(a.get("flags", 0))
    a.update(dmg_mot=bool(f & 1), dodge=bool(f & 2), is_drain=bool(f & 16), target_is_player=bool(f & 32),
             caster_is_player=bool(f & 64), stat_tick=bool(f & ACT_FLAG_STAT_TICK))
    return a


def _act_ext_props(a: dict) -> dict:
    """PeerAction.IsStart / IsEnd, kept beside HasExt + ExtKind."""
    a.update(is_start=bool(a.get("has_ext")) and a.get("ext_kind") == ACT_EXT_START,
             is_end=bool(a.get("has_ext")) and a.get("ext_kind") == ACT_EXT_END)
    return a


def decode_action_legacy(payload) -> dict | None:
    """TryParseAction as EVERY reader reads it (s110-s132's guests too): the 46-byte fields, by PeerAction's names
    snake_cased, plus its computed flag properties -- bytes past the 46th are never read. None under 46 bytes. What an
    s110-s132 guest makes of a START or an END: caster and target 0xFF (it resolves neither and returns), flags 0x04 /
    0x08 alone, no figures, the legacy cmd/sub."""
    data = bytes(payload or b"")
    if len(data) < ACT_LEGACY_LEN:
        return None
    return _act_flag_props(dict(zip(ACT_LEGACY_FIELDS, _ACT_HEAD.unpack_from(data))))


def clear_action_ext(a: dict) -> dict:
    """NetSyncBattle.ClearActionExt: every extension field at its default (none)."""
    a.update({k: (False if k == "has_ext" else 0) for k in ACT_EXT_FIELDS})
    return _act_ext_props(a)


def parse_action(payload) -> dict | None:
    """s133's TryParseAction: ``a = default(PeerAction)`` (the extension fields cleared), then the 46 bytes -- the struct
    :func:`read_action_ext` fills in."""
    a = decode_action_legacy(payload)
    return None if a is None else clear_action_ext(a)


def read_action_ext(payload, a: dict) -> int:
    """NetSyncBattle.ReadActionExt -- THE EXTENSION READER, after the 46-byte parse, filling ``a`` in place and answering
    ACT_EXT_READ_*: only at length >= 52 with byte 46 == 0xA6 (a 46-byte frame or a foreign byte 46: NONE); fmt 1 (another
    fmt is skipped: FMT); extLen >= 3 and inside the frame; the kind agreeing with flags bits 2-3 (an impact neither, a
    START bit 2, an END bit 3); a START/END id non-zero; a START's extLen >= 27; anything else BAD. A bad or unknown
    extension leaves ``has_ext`` False and the 46-byte fields untouched -- it never fails the frame. A longer fmt-1
    extension reads its known fields."""
    clear_action_ext(a)
    p = bytes(payload or b"")
    if len(p) <= ACT_LEGACY_LEN or p[ACT_LEGACY_LEN] != ACT_EXT_TAG:
        return ACT_EXT_READ_NONE
    if len(p) < ACT_ID_RECORD_LEN:
        return ACT_EXT_READ_BAD
    if p[47] != ACT_EXT_FMT1:
        return ACT_EXT_READ_FMT
    ln = p[48]
    if ln < ACT_EXT_LEN_ID or 49 + ln > len(p):
        return ACT_EXT_READ_BAD
    kind = p[49]
    act_id = p[50] | (p[51] << 8)
    flags = int(a.get("flags", 0))
    f_start, f_end = bool(flags & ACT_FLAG_START), bool(flags & ACT_FLAG_END)
    if kind == ACT_EXT_IMPACT:
        if f_start or f_end:
            return ACT_EXT_READ_BAD
    elif kind == ACT_EXT_END:
        if not f_end or f_start or act_id == 0:
            return ACT_EXT_READ_BAD
    elif kind == ACT_EXT_START:
        if not f_start or f_end or act_id == 0 or ln < ACT_EXT_LEN_START:
            return ACT_EXT_READ_BAD
        (_tag, _fmt, _len, _kind, _id, actor, aflags, cmd, sub, tar, cursor, info, magic, vkind, vnum, patched,
         speed) = _ACT_START_BODY.unpack_from(p, ACT_LEGACY_LEN)
        a.update(actor_slot=actor, actor_flags=aflags, act_cmd_no=cmd, act_sub_no=sub, act_tar_id=tar, act_cursor=cursor,
                 act_info=info, act_magic_caster=magic, vfx_kind=vkind, vfx_num=vnum, act_patched_vfx=patched,
                 host_speed=speed)
    else:
        return ACT_EXT_READ_BAD
    a.update(has_ext=True, ext_kind=kind, act_id=act_id)
    _act_ext_props(a)
    return ACT_EXT_READ_OK


def decode_action(payload) -> dict | None:
    """A whole type-6 record as an s133+ reader sees it: :func:`parse_action` + :func:`read_action_ext` (its answer as
    ``ext_read``, the payload's length as ``len``). None when the 46-byte parse refuses it."""
    a = parse_action(payload)
    if a is None:
        return None
    a["ext_read"] = read_action_ext(payload, a)
    a["len"] = len(bytes(payload or b""))
    return a


def classify_action(a: dict | None) -> str:
    """One parsed record's class, as ActLoopBook and the tape's summary count it: "stat" (bit 7 -- never an impact),
    "start", "end", "impact" (neither START nor END flag), "bad" (a START/END flag with no good extension), "unparsed"
    (None: under 46 bytes)."""
    if a is None:
        return "unparsed"
    if a.get("stat_tick"):
        return "stat"
    if a.get("is_start"):
        return "start"
    if a.get("is_end"):
        return "end"
    if not a["flags"] & (ACT_FLAG_START | ACT_FLAG_END):
        return "impact"
    return "bad"


def encode_action_impact(nonce: int, seq: int, caster: int, target: int, *, fig_t=(0, 0, 0), fig_c=(0, 0, 0),
                         raws=(0, 0, 0, 0), flags: int = 0, cmd_no: int = 0, sub_no: int = 0,
                         act_id: int | None = None) -> bytes:
    """QueueActionFrame's record: the 46 bytes (``fig_t`` / ``fig_c`` = (info u16, hp i32, mp i32); ``raws`` = the target's
    then the caster's raw hp / mp, u32), and with ``act_id`` (not None) the 6-byte id extension -- 52 bytes, s133's impact."""
    legacy = _ACT_HEAD.pack(_act_u8(nonce), _act_u16(seq), _act_u8(caster), _act_u8(target), _act_u16(fig_t[0]), _act_i32(fig_t[1]),
                            _act_i32(fig_t[2]), _act_u16(fig_c[0]), _act_i32(fig_c[1]), _act_i32(fig_c[2]),
                            *(_act_u32(r) for r in raws), _act_u8(flags), _act_u16(cmd_no), _act_u16(sub_no))
    return legacy if act_id is None else with_impact_ext(legacy, act_id)


def with_impact_ext(legacy, act_id: int) -> bytes:
    """NetSyncBattle.WithImpactExt: a 46-byte impact with the id extension appended (WriteIdExt: A6 01 03 01 id LE)."""
    return bytes(legacy)[:ACT_LEGACY_LEN] + _ACT_ID_EXT.pack(ACT_EXT_TAG, ACT_EXT_FMT1, ACT_EXT_LEN_ID, ACT_EXT_IMPACT,
                                                              _act_u16(act_id))


def _inert_head(nonce: int, seq: int, flags: int, cmd_no: int, sub_no: int) -> bytes:
    """WriteInertHead: no caster, no target (0xFF/0xFF), no figures or raws (36 zero bytes), the flags, the legacy cmd/sub;
    the host _seq written, NOT consumed."""
    return struct.pack("<BHBB36sBHH", _act_u8(nonce), _act_u16(seq), 0xFF, 0xFF, bytes(36), _act_u8(flags), _act_u16(cmd_no), _act_u16(sub_no))


def encode_action_start(nonce: int, seq: int, act_id: int, actor_slot: int, actor_flags: int, cmd_no: int, sub_no: int,
                        tar_id: int, cursor: int, info: int, magic_caster: int, vfx_kind: int, vfx_num: int,
                        patched_vfx: int, host_speed: int) -> bytes:
    """NetSyncBattle.EncodeActionStart: a START record, 76 bytes (the layout above)."""
    return _inert_head(nonce, seq, ACT_FLAG_START, cmd_no, sub_no) + _ACT_START_BODY.pack(
        ACT_EXT_TAG, ACT_EXT_FMT1, ACT_EXT_LEN_START, ACT_EXT_START, _act_u16(act_id), _act_u8(actor_slot), _act_u8(actor_flags),
        _act_u16(cmd_no), _act_i32(sub_no), _act_u16(tar_id), _act_u8(cursor), _act_u8(info), _act_u16(magic_caster), _act_u8(vfx_kind),
        _act_i32(vfx_num), _act_i32(patched_vfx), _act_u8(host_speed))


def encode_action_end(nonce: int, seq: int, act_id: int, cmd_no: int, sub_no: int) -> bytes:
    """NetSyncBattle.EncodeActionEnd: an END record, 52 bytes (the inert head with flags 0x08 + A6 01 03 03 id LE)."""
    return _inert_head(nonce, seq, ACT_FLAG_END, cmd_no, sub_no) + _ACT_ID_EXT.pack(
        ACT_EXT_TAG, ACT_EXT_FMT1, ACT_EXT_LEN_ID, ACT_EXT_END, _act_u16(act_id))


def action_hex(payload) -> str:
    """A type-6 record as `act.host.tape.page.frames[].hex` publishes it (``BitConverter.ToString(..).Replace("-", "")``:
    compact upper-case hex, no separators). ``bytes.fromhex`` reads it back."""
    return bytes(payload).hex().upper()


def action_text(payload) -> str:
    """One type-6 record for a log or ``coop_peer dump``: ``START id 3 actor 0 ... kind special 100``, ``END id 3``,
    ``impact 0->4 cmd 1/176 hp 33 id 3``, ``impact ... (46 B: no id -- a pre-s133 host)``, ``stat tick ->4``, ``bad ext``,
    ``unparsed``."""
    a = decode_action(payload)
    if a is None:
        return f"unparsed ({len(bytes(payload or b''))} B: under the 46-byte layout)"
    kind = classify_action(a)
    if kind == "start":
        return (f"START id {a['act_id']} actor {a['actor_slot']} flags 0x{a['actor_flags']:02X} cmd {a['act_cmd_no']} "
                f"sub {a['act_sub_no']} tar 0x{a['act_tar_id']:X} cursor {a['act_cursor']} info 0x{a['act_info']:02X} "
                f"kind {vfx_kind_name(a['vfx_kind'])} {a['vfx_num']} speed {a['host_speed']}")
    if kind == "end":
        return f"END id {a['act_id']} (cmd {a['cmd_no']}/{a['sub_no']})"
    if kind == "stat":
        return f"stat tick ->{a['target_slot']} hp {a['fig_hp_t']} ({a['len']} B)"
    if kind == "impact":
        head = f"impact {a['caster_slot']}->{a['target_slot']} cmd {a['cmd_no']}/{a['sub_no']} hp {a['fig_hp_t']}"
        if a["has_ext"]:
            return head + f" id {a['act_id']}"
        if a["len"] == ACT_LEGACY_LEN:
            return head + " (46 B: no id -- a pre-s133 host)"
        return head + f" (an extension not read: {('none', 'ok', 'bad', 'unknown fmt')[a['ext_read']]})"
    return f"bad ext (flags 0x{a['flags']:02X}, ext read {a['ext_read']}, {a['len']} B)"


# ---- the id books (NetSyncBattle._actIds END-eligible, _actScripted never ENDed; keyed by CMD_DATA reference)
def new_act_record(act_id: int, actor: int, cmd_no: int, sub_no: int, scripted: bool) -> dict:
    """NetSyncBattle.ActRecord: one START on the host's id books."""
    return {"id": _act_u16(act_id), "actor": _act_u8(actor), "cmd_no": _act_u16(cmd_no), "sub_no": _act_u16(sub_no),
            "scripted": bool(scripted)}


def act_next_id(last: int) -> int:
    """NetSyncBattle.ActNextId(ref last): the next id -- from 1, never 0 (a wrap skips it). The caller stores it back as
    ``last`` (C#'s ref)."""
    last = (int(last) + 1) & 0xFFFF
    return last if last != 0 else 1


def act_start_step(live: dict, scripted: dict, key, fresh: dict, seq_running: bool) -> tuple:
    """NetSyncBattle.ActStartStep -> ``(verdict, displaced)``: the fresh record goes into its own book (live = END-
    eligible, scripted = never ENDed) and the key leaves the other. An open END-eligible lifecycle on the key is DISPLACED
    (handed back for its END to be sent first): a TAKEOVER for a scripted START (audit amendment 6), a RESTART for a
    CommandEngine one; a scripted lifecycle is retired silently (REUSE), or as a REENTRY when a CommandEngine START meets
    it while its sequence still runs (``seq_running``)."""
    displaced, verdict = None, ACT_STEP_NEW
    if key in live:
        displaced = live.pop(key)
        verdict = ACT_STEP_TAKEOVER if fresh["scripted"] else ACT_STEP_RESTART
    elif key in scripted:
        scripted.pop(key)
        verdict = ACT_STEP_REENTRY if not fresh["scripted"] and seq_running else ACT_STEP_REUSE
    (scripted if fresh["scripted"] else live)[key] = fresh
    return verdict, displaced


def act_end_step(live: dict, key) -> dict | None:
    """NetSyncBattle.ActEndStep (FinishCommand): the END-eligible lifecycle on ``key``, taken off its book; None = none
    (never STARTed -- a failed inspection, a declined START -- or a scripted one, which no END reads)."""
    if key is None or key not in live:
        return None
    return live.pop(key)


def act_id_of(live: dict, scripted: dict, key) -> int:
    """NetSyncBattle.ActIdOf: an impact's action id -- the END-eligible book first, then the scripted one; 0 = none."""
    if key is None:
        return 0
    rec = live.get(key) or scripted.get(key)
    return rec["id"] if rec is not None else 0


def act_vfx_verdict(kind: int, num: int, added: bool, enemy_seq: bool, effect_num: int) -> bool:
    """NetSyncBattle.ActVfxVerdict -- the describe check (audit D2): the START's kind against the action SelectCommandVfx
    added. NONE = nothing added; SEQ and COMMON = an action added (a copied .seq may be either type); ENEMY = an
    EnemySequence of that sub_no; SPECIAL = a SpecialEffect of that number; UNKNOWN (the describe threw) always drifts."""
    if kind == VFX_KIND_NONE:
        return not added
    if kind in (VFX_KIND_SEQ, VFX_KIND_COMMON):
        return bool(added)
    if kind == VFX_KIND_ENEMY:
        return bool(added and enemy_seq and effect_num == num)
    if kind == VFX_KIND_SPECIAL:
        return bool(added and not enemy_seq and effect_num == num)
    return False


def describe_command_vfx(*, rework: bool, cmd_no: int, sub_no: int, player: bool | None, vfx_action: bool = False,
                         beatrix: bool = False, vfx_index: int = 0, special: int = SPECIAL_NO_EFFECT,
                         throws: bool = False) -> tuple:
    """btl_vfx.DescribeCommandVfx -> ``(kind, num)``: the PURE MIRROR of SelectCommandVfx for this machine's own mode
    (``rework`` = [Battle] SFXRework). ``player`` = the caster's ``bi.player != 0`` (None = no regist); ``vfx_action`` =
    ``aa.Info.VfxAction != null`` already (BTL_SCENE loads every enemy attack's eagerly); ``beatrix`` = the Beatrix fix's
    predicate (SequenceFile null, an enemy, dms_geo_id 427, VfxIndex 457) EVALUATED; ``special`` = what
    GetPlayerCommandSFX resolves (SPECIAL_NO_EFFECT = none); ``throws`` = the describe threw (UNKNOWN, num 0). Kind 1 is
    never keyed on SequenceFile alone (audit amendment 10): a CSV .seq not yet loaded reads as the branch below it."""
    if throws:
        return VFX_KIND_UNKNOWN, 0
    if rework:
        if cmd_no != CMD_MAGIC_COUNTER:
            if vfx_action or beatrix:
                return VFX_KIND_SEQ, int(vfx_index)
            if player is False and cmd_no != CMD_SYS_TRANS:
                return VFX_KIND_ENEMY, int(sub_no)
    elif cmd_no in (CMD_ENEMY_ATK, CMD_ENEMY_COUNTER, CMD_ENEMY_DYING, CMD_ENEMY_REACTION):
        return VFX_KIND_ENEMY, int(sub_no)
    if special != SPECIAL_NO_EFFECT:
        return VFX_KIND_SPECIAL, int(special)
    if cmd_no in (CMD_CHANGE_ID, CMD_DEFEND_ID):
        return VFX_KIND_COMMON, int(cmd_no)
    return VFX_KIND_NONE, 0


class ActLoopBook:
    """[ff9mapkit netsync s133] NetSyncBattle.ActLoopBook -- THE LOOPBACK AUDIT (`act.host.loop`): every type-6 frame the
    selftest loopback receives, classified -- STARTs, ENDs, impacts (and of them the extended ones), stat ticks (bit 7,
    never an impact), bad extensions -- with the pairing checked: an END that closes an open END-eligible START is
    ``paired``; an END with no open START (or naming a scripted one), an impact naming an id that is not open, and a second
    START on an open id are ``orphans``; an impact whose caster is not its START's actor is a ``caster_mismatch``; at the
    own battle's close the END-eligible STARTs still open are ``no_end`` (a normal end) or ``cut`` (a reset or a mid-action
    teardown) -- a scripted START (actor flags b3) owes no END (audit amendment 7)."""

    KEYS = ("starts", "ends", "impacts", "impacts_ext", "stat", "ext_bad", "paired", "orphans", "caster_mismatch", "no_end",
            "cut")

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        for k in self.KEYS:
            setattr(self, k, 0)
        self._open = {}                              # id -> actor slot | 0x100 scripted

    @property
    def fed(self) -> bool:
        return self.starts + self.ends + self.impacts + self.stat + self.ext_bad > 0

    def feed(self, a: dict, ext_read: int) -> None:
        """Feed(ref a, extRead): one parsed record and ReadActionExt's answer for it."""
        if ext_read in (ACT_EXT_READ_BAD, ACT_EXT_READ_FMT):
            self.ext_bad += 1
        if a["flags"] & ACT_FLAG_STAT_TICK:
            self.stat += 1
            return
        if a["is_start"]:
            self.starts += 1
            if a["act_id"] in self._open:
                self.orphans += 1
            else:
                self._open[a["act_id"]] = a["actor_slot"] | (0x100 if a["actor_flags"] & ACTOR_SCRIPTED else 0)
            return
        if a["is_end"]:
            self.ends += 1
            o = self._open.get(a["act_id"])
            if o is not None and not o & 0x100:
                self.paired += 1
                del self._open[a["act_id"]]
            else:
                self.orphans += 1
            return
        if a["flags"] & (ACT_FLAG_START | ACT_FLAG_END):
            if ext_read == ACT_EXT_READ_NONE:
                self.ext_bad += 1                    # a START/END record with no extension at all
            return
        self.impacts += 1
        if not a["has_ext"]:
            return
        self.impacts_ext += 1
        if a["act_id"] == 0:
            return
        o = self._open.get(a["act_id"])
        if o is None:
            self.orphans += 1
        elif a["caster_slot"] != 0xFF and a["caster_slot"] != (o & 0xFF):
            self.caster_mismatch += 1

    def close(self, cut: bool) -> int:
        """Close(cut): the END-eligible STARTs still open, counted as ``cut`` or ``no_end``; the book is emptied."""
        n = sum(1 for o in self._open.values() if not o & 0x100)
        if cut:
            self.cut += n
        else:
            self.no_end += n
        self._open.clear()
        return n

    def doc(self) -> dict:
        """`netsync.battle.act.host.loop`, in AppendAct's order."""
        return {k: getattr(self, k) for k in self.KEYS}


def act_tape_summary(frames) -> dict:
    """ActTapeSummary's scan of a tape (each frame's bytes) through the real codec: ``starts``, ``ends``, ``impacts``
    (``ext`` of them with the id extension), ``stat``, ``bad`` (an unparsed frame, a bad / unknown-fmt extension, or a
    START/END flag with no extension at all -- ActLoopBook's ``ext_bad`` rule)."""
    out = {"frames": 0, "starts": 0, "ends": 0, "impacts": 0, "ext": 0, "stat": 0, "bad": 0}
    for frame in frames:
        out["frames"] += 1
        a = parse_action(frame)
        if a is None:
            out["bad"] += 1
            continue
        r = read_action_ext(frame, a)
        if r in (ACT_EXT_READ_BAD, ACT_EXT_READ_FMT):
            out["bad"] += 1
        if a["stat_tick"]:
            out["stat"] += 1
        elif a["is_start"]:
            out["starts"] += 1
        elif a["is_end"]:
            out["ends"] += 1
        elif not a["flags"] & (ACT_FLAG_START | ACT_FLAG_END):
            out["impacts"] += 1
            if a["has_ext"]:
                out["ext"] += 1
        elif r == ACT_EXT_READ_NONE:
            out["bad"] += 1                          # a START/END flag with no extension at all
    return out


def act_tape_info_line(state: str, frames, last_ms: int, overflow: int) -> str:
    """`actbench tape info`'s summary line (ActTapeSummary), with its ``[NetSync] `` head."""
    s = act_tape_summary(frames)
    return (f"{LOG_ACT_TAPE_INFO}{state}, {s['frames']} frame(s) -- {s['starts']} START(s), {s['ends']} END(s), "
            f"{s['impacts']} impact(s) ({s['ext']} with the id extension), {s['stat']} stat tick(s), {s['bad']} bad; "
            f"{last_ms} ms, overflow {overflow}")


def act_tape_page_frames(page: dict | None) -> list:
    """`act.host.tape.page` -> ``[(i, ms, bytes)]`` (each frame's compact hex read back); [] for a null page."""
    if not isinstance(page, dict):
        return []
    return [(int(f["i"]), int(f["ms"]), bytes.fromhex(f["hex"])) for f in page.get("frames") or []]


def act_order_violations(frames) -> list:
    """THE FIFO PROMISE over a tape (each frame's bytes, in arrival order): every impact naming id k arrives AFTER START k
    and BEFORE END k, and every END after its START. -> the violations, as text (empty = the promise held). Stat ticks and
    id-0 impacts name no lifecycle. A lifecycle is (nonce, id) -- ids restart at 1 every own battle (ActBattleStart), and a
    tape or a coop_peer recording may span battles -- and a second START of one is a violation (ActLoopBook's orphan)."""
    started, ended, out = {}, {}, []
    for i, frame in enumerate(frames):
        a = decode_action(frame)
        kind = classify_action(a)
        if kind not in ("start", "end", "impact"):
            continue
        k = (a["nonce"], a["act_id"])
        if kind == "start":
            if k in started:
                out.append(f"START {k[1]} (nonce {k[0]}) at frame {i} again (first at frame {started[k]})")
            else:
                started[k] = i
        elif kind == "end":
            if k not in started:
                out.append(f"END {k[1]} (nonce {k[0]}) at frame {i} before any START {k[1]}")
            ended.setdefault(k, i)
        elif a["has_ext"] and a["act_id"]:
            if k not in started:
                out.append(f"impact id {k[1]} (nonce {k[0]}) at frame {i} before its START")
            elif k in ended:
                out.append(f"impact id {k[1]} (nonce {k[0]}) at frame {i} after its END (frame {ended[k]})")
    return out


#: the 46-byte head's figure and raw fields: zero on an INERT head (a START or an END -- WriteInertHead)
ACT_INERT_ZERO_FIELDS = ("fig_info_t", "fig_hp_t", "fig_mp_t", "fig_info_c", "fig_hp_c", "fig_mp_c", "tgt_hp_raw",
                         "tgt_mp_raw", "cast_hp_raw", "cast_mp_raw")


def act_inert_head(legacy: dict | None) -> bool:
    """A START's or an END's 46-byte head as EVERY reader reads it (:func:`decode_action_legacy`) is INERT, byte for byte:
    caster and target 0xFF/0xFF (an s110-s132 guest resolves neither and returns -- a resolvable slot's zero raws would
    read as LETHAL there: ``lethalT = a.TgtHpRaw == 0``) and every figure and raw 0."""
    return (legacy is not None and legacy["caster_slot"] == 0xFF and legacy["target_slot"] == 0xFF
            and all(legacy[f] == 0 for f in ACT_INERT_ZERO_FIELDS))


def _seq_after(a: int, b: int) -> bool:
    """``a`` strictly after ``b`` on the u16 sample clock (wrap-aware: within half the ring)."""
    return 1 <= ((a - b) & 0xFFFF) <= 0x7FFF


def act_horizon_violations(frames) -> list:
    """THE STATE-WRITE<=>HORIZON law over a tape (each frame's bytes, in FIFO order), per nonce: every CONSUMING frame (an
    impact or a stat tick -- ``bw.Write(_seq++)``) stamps a seq strictly after the previous consuming frame's (wrap-aware);
    every START and END stamps the live clock WITHOUT consuming it -- strictly after the previous consuming frame's seq and
    at or before the next one's -- so a stale, zeroed or replayed seq on a START/END is caught (a START/END that CONSUMED
    the clock cannot be told from a type-1 sample in between: test_harness_netsync.py pins that at the call sites). -> the
    violations, as text."""
    out, rows = [], []
    for i, frame in enumerate(frames):
        a = decode_action(frame)
        kind = classify_action(a)
        if kind in ("impact", "stat", "start", "end"):
            rows.append((i, kind, a["nonce"], a["seq_horizon"]))
    for nonce in dict.fromkeys(r[2] for r in rows):
        mine = [r for r in rows if r[2] == nonce]
        consuming = [(i, seq) for i, kind, _n, seq in mine if kind in ("impact", "stat")]
        for (i0, s0), (i1, s1) in zip(consuming, consuming[1:]):
            if not _seq_after(s1, s0):
                out.append(f"frame {i1} (nonce {nonce}) consumes seq {s1}, not after frame {i0}'s {s0}")
        for i, kind, _n, seq in mine:
            if kind not in ("start", "end"):
                continue
            prev = [s for j, s in consuming if j < i]
            nxt = [s for j, s in consuming if j > i]
            if prev and not _seq_after(seq, prev[-1]):
                out.append(f"{kind.upper()} at frame {i} (nonce {nonce}) stamps seq {seq}, not after the last consumed "
                           f"{prev[-1]} (stale or zeroed)")
            if nxt and seq != nxt[0] and not _seq_after(nxt[0], seq):
                out.append(f"{kind.upper()} at frame {i} (nonce {nonce}) stamps seq {seq}, past the next consumed "
                           f"{nxt[0]}")
    return out


def act_identity_violations(frames, *, require_id: bool = True) -> list:
    """What the 46-byte reader cannot vouch for itself, checked on a tape against each lifecycle's own START (keyed (nonce,
    id)): every IMPACT's legacy head is an impact's (flags bits 2-3 clear, each slot < 8 or 0xFF, at least one < 8), it
    carries the id extension and names an id (``require_id``: never 0 -- a bench whose `noid_impacts` must read 0) that a
    START on the tape carries, repeats that START's legacy identity (cmd_no and sub_no as QueueActionFrame writes them,
    u16) and is cast by that START's actor or 0xFF (the offline twin of `loop.caster_mismatch`); every END repeats its
    START's legacy cmd/sub. -> the violations, as text."""
    decoded = [(i, decode_action(frame)) for i, frame in enumerate(frames)]
    starts, out = {}, []
    for _i, a in decoded:
        if classify_action(a) == "start":
            starts.setdefault((a["nonce"], a["act_id"]), a)
    for i, a in decoded:
        kind = classify_action(a)
        if kind == "end":
            s = starts.get((a["nonce"], a["act_id"]))
            if s is not None and (a["cmd_no"], a["sub_no"]) != (s["act_cmd_no"] & 0xFFFF, s["act_sub_no"] & 0xFFFF):
                out.append(f"END {a['act_id']} at frame {i}: legacy cmd/sub {a['cmd_no']}/{a['sub_no']} != its START's "
                           f"{s['act_cmd_no']}/{s['act_sub_no']}")
            continue
        if kind != "impact":
            continue
        c, t = a["caster_slot"], a["target_slot"]
        if a["flags"] & (ACT_FLAG_START | ACT_FLAG_END) or not all(x < 8 or x == 0xFF for x in (c, t)) or min(c, t) >= 8:
            out.append(f"impact at frame {i}: legacy head flags 0x{a['flags']:02X} slots {c}/{t}")
        if not a["has_ext"]:
            out.append(f"impact at frame {i}: no id extension")
            continue
        if not a["act_id"]:
            if require_id:
                out.append(f"impact at frame {i}: id 0")
            continue
        s = starts.get((a["nonce"], a["act_id"]))
        if s is None:
            out.append(f"impact id {a['act_id']} at frame {i}: no START on the tape carries it")
            continue
        if (a["cmd_no"], a["sub_no"]) != (s["act_cmd_no"] & 0xFFFF, s["act_sub_no"] & 0xFFFF):
            out.append(f"impact id {a['act_id']} at frame {i}: legacy cmd/sub {a['cmd_no']}/{a['sub_no']} != its START's "
                       f"{s['act_cmd_no']}/{s['act_sub_no']}")
        if c != 0xFF and c != s["actor_slot"]:
            out.append(f"impact id {a['act_id']} at frame {i}: caster slot {c} != its START's actor {s['actor_slot']}")
    return out


class ActHostLane:
    """[ff9mapkit netsync s133] The HOST's action-start lane as NetSyncBattle runs it, with s133's statics: QueueActionStart
    (:meth:`start`), CheckActionVfx (:meth:`check_vfx`), QueueActionFrame's tail (:meth:`impact`), QueueStatFrame
    (:meth:`stat_tick`), QueueActionEnd (:meth:`end`), the shared drop-oldest EnqueueActionPayload (:meth:`enqueue`),
    ActBattleStart / ActCloseBattle (:meth:`battle_start` / :meth:`close_battle`), the selftest loopback's LoopActions
    (:meth:`loop_actions`: the tape and the audit), HarnessActBench (:meth:`bench`) and ActHarnessRelease (:meth:`release`)
    -- `netsync.battle.act.host` is :meth:`doc`, and every Log.Message line lands in :attr:`lines` (each WITH its
    "[NetSync] " head). Per own battle like the engine's counters (reset at the rising edge, kept after the battle until
    the next one starts); ``edge_declined``, the lever and the tape are per PROCESS. The caller supplies what the engine
    reads off the battle (the gate's inputs, the actor's wire slot and flags, the describe's kind and number, what
    SelectCommandVfx added) -- this model owns only the lane's own decisions, through the twins above."""

    def __init__(self) -> None:
        self.lever_off = False                       # BenchActStartsOff
        self.edge_declined = 0                       # monotonic per process
        self._edge_logged = False
        self.tape: list = []                         # [(ms, bytes)]
        self.tape_rec = False
        self._tape_rec_ms = -60000                   # the tick-baseline law
        self.tape_starts = 0
        self.tape_overflow = 0
        self._tape_full_logged = False
        self.tape_page = None
        self.out: list = []                          # _actionsOut (impacts, stat ticks, STARTs, ENDs)
        self._drop_logged = False
        self._parse_logged = False
        self.lines: list = []
        self.battle_open = False
        self.nonce = -1
        self._battle_reset()

    def _battle_reset(self) -> None:
        self.ids: dict = {}
        self.scripted: dict = {}
        self.next_id = 0
        self.starts = self.ends = self.scripted_starts = self.ext_impacts = self.noid_impacts = 0
        self.dropped = self.unresolved = self.takeovers = self.reentries = self.restarted = 0
        self.wire_dropped = 0                        # `wire_dropped`: the transport out-queue's (Pump only -- the stand-in
                                                     # and the selftest loopback have no transport: always 0 here)
        self.no_end = self.cut = 0
        self.kinds = [0] * 6
        self.vfx_checked = self.vfx_drift = self.vfx_unchecked = 0
        self.vfx_why = None
        self.last_start = None
        self.log_mask = 0
        self._check = None
        self.loop = ActLoopBook()

    def _log(self, text: str) -> None:
        self.lines.append(text)

    # -- the gate and the budget
    def starts_on(self, selftest_role: bool) -> bool:
        """ActStartsOn: the lever bites only under the selftest role (a lever stranded across an ini edit never strips a
        real host)."""
        return not (self.lever_off and selftest_role)

    def enqueue(self, payload: bytes) -> None:
        """EnqueueActionPayload -- THE ONE drop-oldest enqueue (audit amendment 4): impacts, stat ticks and the START/END
        records share the 64-frame budget; ``dropped`` counts it this own battle; the drop line once per battle."""
        if len(self.out) >= ACTION_BUFFER_CAP:
            self.out.pop(0)
            self.dropped += 1
            if not self._drop_logged:
                self._drop_logged = True
                self._log(f"{LOG_ACT_DROP}{ACTION_BUFFER_CAP}) this battle -- oldest dropped (figures lost, state self-heals)")
        self.out.append(bytes(payload))

    # -- the own battle's edges
    def battle_start(self, nonce: int) -> None:
        """ActBattleStart (NoteOwnBattleStart, after the nonce bump): the books and this battle's counters start clean."""
        self._battle_reset()
        self.battle_open = True
        self.nonce = int(nonce)
        self._drop_logged = False

    def close_battle(self, cut: bool, mid_action: bool = False) -> None:
        """ActCloseBattle: idempotent. Open END-eligible ids count as ``cut`` (a Reset, or ``mid_action``: a command still
        in cur_cmd_list at the falling edge) or ``no_end`` (a normal end -- a defect); the loopback audit closes the same
        way; one summary line when the lane did anything."""
        if not self.battle_open:
            return
        self.battle_open = False
        as_cut = cut or mid_action
        n_open = len(self.ids)
        if n_open:
            ids = ", ".join(f"{r['id']} (slot {r['actor']})" for r in self.ids.values())
            if as_cut:
                self.cut += n_open
                tail = f"cut (a reset mid-battle or a mid-action teardown) -- cut={self.cut}"
            else:
                self.no_end += n_open
                tail = f"end -- no_end={self.no_end} (a normal end cannot orphan one: a defect)"
            self._log(f"[NetSync] action lane: {n_open}{LOG_ACT_NEVER_ENDED}{tail}; ids {ids}")
        looped = self.loop.fed
        self.loop.close(as_cut)
        if self.starts > 0 or self.ext_impacts > 0 or self.dropped > 0 or looped:
            lp = self.loop
            self._log(f"{LOG_ACT_CLOSED}{self.nonce}) closed -- {self.starts} START(s) ({self.scripted_starts} scripted), "
                      f"{self.ends} END(s), {self.ext_impacts} impact(s) with an id ({self.noid_impacts} of them 0), "
                      f"dropped {self.dropped}, describe drift {self.vfx_drift}"
                      + (f"; loopback: {lp.starts} starts, {lp.ends} ends, {lp.paired} paired, {lp.orphans} orphan(s), "
                         f"{lp.caster_mismatch} caster mismatch(es), no_end {lp.no_end}, cut {lp.cut}" if looped else ""))
        self.ids.clear()
        self.scripted.clear()
        self._check = None

    # -- the records
    def start(self, key, *, scripted: bool, actor_slot: int, actor_flags: int, cmd_no: int, sub_no: int, tar_id: int,
              nonce: int, seq: int, enabled: bool, selftest_role: bool, booted: bool = False, is_debug: bool = False,
              was_in_battle: bool = True, cursor: int = 0, info: int = 0, magic_caster: int = 0,
              vfx: tuple = (VFX_KIND_NONE, 0), patched_vfx: int = 0, host_speed: int = 5,
              seq_running: bool = False) -> int:
        """QueueActionStart. ``actor_flags`` = every bit but SCRIPTED (added here for a scripted START); ``vfx`` = the
        describe's (kind, num) -- a scripted START ignores it (kind 2, num = sub_no). Returns the id issued (0 = no
        START)."""
        if not enabled:
            return 0
        if booted or is_debug or not self.starts_on(selftest_role) or key is None:
            return 0
        if not was_in_battle:
            self.edge_declined += 1
            if not self._edge_logged:
                self._edge_logged = True
                self._log(f"[NetSync] action lane: a {'scripted ' if scripted else ''}{LOG_ACT_EDGE}{cmd_no}, sub {sub_no}) "
                          f"-- it would ride the previous battle's nonce; edge_declined={self.edge_declined} (logged once "
                          f"per process)")
            return 0
        if _act_u8(actor_slot) == 0xFF:
            self.unresolved += 1
            if not self.log_mask & ACT_LOG_UNRESOLVED:
                self.log_mask |= ACT_LOG_UNRESOLVED
                self._log(f"[NetSync] action lane: {cmd_no} (sub {sub_no}){LOG_ACT_UNRESOLVED}no END (unresolved="
                          f"{self.unresolved}; logged once per battle)")
            return 0
        flags = _act_u8(actor_flags) | (ACTOR_SCRIPTED if scripted else 0)
        kind, num = (VFX_KIND_ENEMY, int(sub_no)) if scripted else (int(vfx[0]), int(vfx[1]))
        running = (not scripted) and key in self.scripted and seq_running
        self.next_id = act_next_id(self.next_id)
        rec = new_act_record(self.next_id, actor_slot, cmd_no, sub_no, scripted)
        record = encode_action_start(nonce, seq, rec["id"], actor_slot, flags, cmd_no, sub_no, tar_id, cursor, info,
                                     magic_caster, kind, num, patched_vfx, max(0, min(255, int(host_speed))))
        step, displaced = act_start_step(self.ids, self.scripted, key, rec, running)
        if displaced is not None:
            self.enqueue(encode_action_end(nonce, seq, displaced["id"], displaced["cmd_no"], displaced["sub_no"]))
            self.ends += 1
        self.enqueue(record)
        self.starts += 1
        if scripted:
            self.scripted_starts += 1
        self.kinds[act_kind_index(kind)] += 1
        self.last_start = record
        self._note_step(step, rec, displaced)
        if not scripted:
            self._check = (key, kind, num, rec["id"], _act_u8(actor_slot), cmd_no, sub_no)
        return rec["id"]

    def _note_step(self, step: int, rec: dict, displaced: dict | None) -> None:
        if step == ACT_STEP_TAKEOVER:
            self.takeovers += 1
            if not self.log_mask & ACT_LOG_TAKEOVER:
                self.log_mask |= ACT_LOG_TAKEOVER
                self._log(f"[NetSync] action lane: a scripted sequence (StartBtlSeq, seq {rec['sub_no']}) took over slot "
                          f"{rec['actor']}'s open command (id {displaced['id']}) -- its END sent first; the sequence is id "
                          f"{rec['id']}, never ENDed (scripted_takeover={self.takeovers}; logged once per battle)")
        elif step == ACT_STEP_RESTART:
            self.restarted += 1
            if not self.log_mask & ACT_LOG_RESTART:
                self.log_mask |= ACT_LOG_RESTART
                self._log(f"[NetSync] action lane: slot {rec['actor']}'s command started again (id {rec['id']}) with id "
                          f"{displaced['id']} still open (no FinishCommand) -- its END sent first (restarted="
                          f"{self.restarted}; logged once per battle)")
        elif step == ACT_STEP_REENTRY:
            self.reentries += 1
            if not self.log_mask & ACT_LOG_REENTRY:
                self.log_mask |= ACT_LOG_REENTRY
                self._log(f"[NetSync] action lane: slot {rec['actor']}'s command re-entered SELECT_VFX while its scripted "
                          f"sequence still runs -- the scripted id is retired, the command is id {rec['id']} "
                          f"(scripted_reentry={self.reentries}; logged once per battle)")

    def check_vfx(self, key, *, rework: bool = True, added: tuple | None = None) -> None:
        """CheckActionVfx, right after SelectCommandVfx: ``added`` = ``(enemy_seq, effect_num)`` of the action it added to
        runningActions since the START (None = none added); the old engine (``rework`` False) is ``unchecked``."""
        chk, self._check = self._check, None
        if chk is None or chk[0] != key:
            return
        _key, kind, num, act_id, actor, cmd_no, sub_no = chk
        if not rework:
            self.vfx_unchecked += 1
            return
        self.vfx_checked += 1
        enemy_seq, effect_num = (bool(added[0]), int(added[1])) if added is not None else (False, 0)
        if act_vfx_verdict(kind, num, added is not None, enemy_seq, effect_num):
            return
        self.vfx_drift += 1
        self.vfx_why = (f"id {act_id} slot {actor} {cmd_no} sub {sub_no}: described {vfx_kind_name(kind)} {num}, "
                        f"SelectCommandVfx " + ("added no action" if added is None else
                                                "added " + ("an EnemySequence " if enemy_seq else "a SpecialEffect ")
                                                + str(effect_num)))
        if not self.log_mask & ACT_LOG_DRIFT:
            self.log_mask |= ACT_LOG_DRIFT
            self._log(f"{LOG_ACT_DRIFT}{self.vfx_why} (drift={self.vfx_drift}; logged once per battle)")

    def end(self, key, *, nonce: int, seq: int, enabled: bool) -> int:
        """QueueActionEnd (the head of FinishCommand): the END of an open END-eligible lifecycle -- even with the lever
        pulled after its START (an id exists only if its START was sent). Returns the id ENDed (0 = none)."""
        if not enabled or not self.ids:
            return 0
        rec = act_end_step(self.ids, key)
        if rec is None:
            return 0
        self.enqueue(encode_action_end(nonce, seq, rec["id"], rec["cmd_no"], rec["sub_no"]))
        self.ends += 1
        return rec["id"]

    def impact(self, key, legacy: bytes, *, enabled: bool, selftest_role: bool, booted: bool = False,
               is_debug: bool = False) -> bytes | None:
        """QueueActionFrame's tail: a 46-byte impact (caster AND target 0xFF: nothing sent) gets the id extension unless
        the lever is pulled -- the id of ``key``'s lifecycle, 0 for none. Returns the frame queued (None = none)."""
        if not enabled or booted or is_debug:
            return None
        legacy = bytes(legacy)[:ACT_LEGACY_LEN]
        if legacy[3] == 0xFF and legacy[4] == 0xFF:
            return None
        ext = self.starts_on(selftest_role)
        act_id = act_id_of(self.ids, self.scripted, key) if ext else 0
        frame = with_impact_ext(legacy, act_id) if ext else legacy
        self.enqueue(frame)
        if ext:
            self.ext_impacts += 1
            if act_id == 0:
                self.noid_impacts += 1
        return frame

    def stat_tick(self, legacy: bytes, *, enabled: bool, booted: bool = False, is_debug: bool = False) -> None:
        """QueueStatFrame: a 46-byte bit-7 frame through the same budget (never extended: audit D3)."""
        if enabled and not booted and not is_debug:
            self.enqueue(bytes(legacy)[:ACT_LEGACY_LEN])

    # -- the selftest loopback and its tape
    def loop_actions(self, now_ms: int) -> None:
        """LoopActions: every queued frame round-trips the codec -- the tape takes it as received, then TryParseAction (a
        failure is codec drift, logged once), then the extension into the audit."""
        frames, self.out = self.out, []
        for frame in frames:
            self._tape_record(frame, now_ms)
            a = parse_action(frame)
            if a is None:
                if not self._parse_logged:
                    self._parse_logged = True
                    self._log(LOG_ACT_CODEC_DRIFT)
                continue
            self.loop.feed(a, read_action_ext(frame, a))

    def _tape_record(self, frame: bytes, now_ms: int) -> None:
        if not self.tape_rec:
            return
        if len(self.tape) >= ACT_TAPE_CAP:
            self.tape_overflow += 1
            if not self._tape_full_logged:
                self._tape_full_logged = True
                self._log(f"{LOG_ACT_TAPE_FULL}{ACT_TAPE_CAP} frames -- later frames are counted (overflow), not recorded")
            return
        self.tape.append((int(now_ms) - self._tape_rec_ms, bytes(frame)))
        if (len(frame) >= ACT_START_RECORD_LEN and frame[41] & ACT_FLAG_START and frame[ACT_LEGACY_LEN] == ACT_EXT_TAG
                and frame[49] == ACT_EXT_START):
            self.tape_starts += 1

    def _tape_clear(self) -> None:
        self.tape = []
        self.tape_rec = False
        self.tape_starts = self.tape_overflow = 0
        self._tape_full_logged = False
        self.tape_page = None

    @property
    def tape_state(self) -> str:
        """HarnessActTapeState: "rec", "stopped" (frames kept) or "off"."""
        return "rec" if self.tape_rec else "stopped" if self.tape else "off"

    @property
    def tape_ms(self) -> int:
        """HarnessActTapeMs: the last frame's offset from `tape rec` (-1 = none)."""
        return self.tape[-1][0] if self.tape else -1

    def bench(self, op: str, value: str, frm: int, count: int, *, selftest_role: bool, now_ms: int) -> tuple:
        """HarnessActBench -> ``(ok, why)``, in the engine's words (the agent's argument parse runs before it)."""
        if not selftest_role:
            return False, "netsync actbench: needs the selftest role (netsync selftest 1)"
        op, value = (op or "").lower(), (value or "").lower()
        if op == "hoststarts":
            if value not in ("on", "off"):
                return False, "netsync actbench hoststarts: expected `hoststarts on|off`"
            self.lever_off = value == "off"
            self._log(LOG_ACT_LEVER_OFF if self.lever_off else LOG_ACT_LEVER_ON)
            return True, None
        if op != "tape":
            return False, f"netsync actbench: unknown op '{op}' (tape|hoststarts)"
        if value == "rec":
            self._tape_clear()
            self.tape_rec = True
            self._tape_rec_ms = int(now_ms)
            self._log(f"{LOG_ACT_TAPE_REC}{ACT_TAPE_CAP} (a new tape)")
            return True, None
        if value == "stop":
            self.tape_rec = False
            self._log(f"{LOG_ACT_TAPE_STOPPED}{len(self.tape)} frame(s), {self.tape_starts} START(s), {self.tape_ms} ms, "
                      f"overflow {self.tape_overflow}")
            return True, None
        if value == "clear":
            self._log(f"{LOG_ACT_TAPE_CLEARED}{len(self.tape)} frame(s))")
            self._tape_clear()
            return True, None
        if value == "info":
            self._log(act_tape_info_line(self.tape_state, [f for _ms, f in self.tape], self.tape_ms, self.tape_overflow))
            return True, None
        if value == "dump":
            return self._dump(frm, count)
        return False, "netsync actbench tape: expected `tape rec|stop|clear|info` or `tape dump <from> <count>`"

    def _dump(self, frm: int, count: int) -> tuple:
        """ActTapeDump: one page (at most ACT_TAPE_PAGE_MAX frames, clipped at the tape's end) published."""
        if not self.tape:
            return False, "netsync actbench tape dump: the tape is empty (`actbench tape rec` first)"
        if frm < 0 or frm >= len(self.tape):
            return False, (f"netsync actbench tape dump: from {frm} is past the tape's last frame ({len(self.tape)} "
                           f"frame(s))")
        if count < 1 or count > ACT_TAPE_PAGE_MAX:
            return False, f"netsync actbench tape dump: count must be 1-{ACT_TAPE_PAGE_MAX}"
        n = min(count, len(self.tape) - frm)
        self.tape_page = {"from": frm, "count": n, "total": len(self.tape),
                          "frames": [{"i": frm + k, "ms": self.tape[frm + k][0], "hex": action_hex(self.tape[frm + k][1])}
                                     for k in range(n)]}
        self._log(f"{LOG_ACT_TAPE_PAGE}{frm}..{frm + n - 1} of {len(self.tape)} published "
                  f"(netsync.battle.act.host.tape.page)")
        return True, None

    def release(self) -> None:
        """ActHarnessRelease (HarnessReleaseBench's s133 half): the lever back on, the tape stopped and emptied."""
        if self.lever_off:
            self._log(LOG_ACT_LEVER_RELEASED)
        self.lever_off = False
        if self.tape or self.tape_rec or self.tape_page is not None:
            self._log(f"{LOG_ACT_TAPE_CLEARED}{len(self.tape)} frame(s); released with the harness)")
        self._tape_clear()

    def last_doc(self) -> dict | None:
        """HarnessActLast: the last START as shipped, decoded through the codec (None = none this battle)."""
        if self.last_start is None:
            return None
        a = decode_action(self.last_start)
        if a is None or a["ext_read"] != ACT_EXT_READ_OK:
            return None
        return {k: a[f] for k, f in ACT_LAST_FIELDS.items()}

    def doc(self, *, enabled: bool, selftest_role: bool) -> dict:
        """HarnessAgent.AppendAct's `host` half -- published in EVERY role (audit 3.6)."""
        page = self.tape_page
        return {"on": bool(enabled) and self.starts_on(selftest_role), "lever_off": self.lever_off, "nonce": self.nonce,
                "starts": self.starts, "ends": self.ends, "ext_impacts": self.ext_impacts,
                "noid_impacts": self.noid_impacts, "scripted": self.scripted_starts, "open": len(self.ids),
                "dropped": self.dropped, "wire_dropped": self.wire_dropped, "unresolved": self.unresolved,
                "scripted_takeover": self.takeovers,
                "scripted_reentry": self.reentries, "restarted": self.restarted, "no_end": self.no_end, "cut": self.cut,
                "edge_declined": self.edge_declined, "kinds": dict(zip(VFX_KIND_KEYS, self.kinds)),
                "vfx": {"checked": self.vfx_checked, "drift": self.vfx_drift, "unchecked": self.vfx_unchecked,
                        "why": self.vfx_why},
                "last": self.last_doc(), "loop": self.loop.doc(),
                "tape": {"state": self.tape_state, "frames": len(self.tape), "starts": self.tape_starts, "ms": self.tape_ms,
                         "overflow": self.tape_overflow,
                         "page": None if page is None else {"from": page["from"], "count": page["count"],
                                                            "total": page["total"],
                                                            "frames": [dict(f) for f in page["frames"]]}}}


#: NetSyncBattle's s133 integer constants, by C# name (audit amendment 11). ActionBufferCap's comment carries a `;`, so
#: the test reads it as its one literal line instead.
CS_ACTION_CONSTANTS = {
    "CapActionStarts": CAP_ACTION_STARTS, "ActFlagStart": ACT_FLAG_START, "ActFlagEnd": ACT_FLAG_END,
    "ActFlagStatTick": ACT_FLAG_STAT_TICK, "ActExtTag": ACT_EXT_TAG, "ActExtFmt1": ACT_EXT_FMT1,
    "ActExtLenId": ACT_EXT_LEN_ID, "ActExtLenStart": ACT_EXT_LEN_START, "ActExtImpact": ACT_EXT_IMPACT,
    "ActExtStart": ACT_EXT_START, "ActExtEnd": ACT_EXT_END, "ActLegacyLen": ACT_LEGACY_LEN,
    "ActIdRecordLen": ACT_ID_RECORD_LEN, "ActStartRecordLen": ACT_START_RECORD_LEN, "VfxKindNone": VFX_KIND_NONE,
    "VfxKindSeq": VFX_KIND_SEQ, "VfxKindEnemy": VFX_KIND_ENEMY, "VfxKindSpecial": VFX_KIND_SPECIAL,
    "VfxKindCommon": VFX_KIND_COMMON, "VfxKindUnknown": VFX_KIND_UNKNOWN, "ActorIsPlayer": ACTOR_IS_PLAYER,
    "ActorHostRework": ACTOR_HOST_REWORK, "ActorHostFast": ACTOR_HOST_FAST, "ActorScripted": ACTOR_SCRIPTED,
    "ActorMonsterTransform": ACTOR_MONSTER_TRANSFORM, "ActorCounterSlot": ACTOR_COUNTER_SLOT,
    "ActorDoubleCast": ACTOR_DOUBLE_CAST, "ActInfoMeteorMiss": ACT_INFO_METEOR_MISS,
    "ActInfoShortSummon": ACT_INFO_SHORT_SUMMON, "ActInfoCover": ACT_INFO_COVER, "ActTapeCap": ACT_TAPE_CAP,
    "ActTapePageMax": ACT_TAPE_PAGE_MAX, "ActExtReadNone": ACT_EXT_READ_NONE, "ActExtReadOk": ACT_EXT_READ_OK,
    "ActExtReadBad": ACT_EXT_READ_BAD, "ActExtReadFmt": ACT_EXT_READ_FMT, "ActStepNew": ACT_STEP_NEW,
    "ActStepTakeover": ACT_STEP_TAKEOVER, "ActStepRestart": ACT_STEP_RESTART, "ActStepReentry": ACT_STEP_REENTRY,
    "ActStepReuse": ACT_STEP_REUSE, "ActLogTakeover": ACT_LOG_TAKEOVER, "ActLogReentry": ACT_LOG_REENTRY,
    "ActLogRestart": ACT_LOG_RESTART, "ActLogUnresolved": ACT_LOG_UNRESOLVED, "ActLogDrift": ACT_LOG_DRIFT,
    "ActTestNonce": ACT_TEST_NONCE}


# ======================================================================================== [ff9mapkit netsync s134]
# THE GUEST ACTION REPLAY (studies/battle-coop/R3-DESIGN.md 3.3.3 as amended by R3-ACTION-REPLAY-AUDIT.md 2.2 and section 3
# -- the audit's "s123"; group 2 was renumbered s133-s141). The s133 host ships a START before every action and an END
# after it; an s134 guest REPLAYS each START on its battle diorama: a standalone CMD_DATA, never enqueued, runs through the
# stock SFXRework sequencer, presentation only (THE CONTAINMENT LAW: btl_cmd.ExecVfxCommand's first statement short-circuits
# every replay hit; CalcMain's head and the SysTrans case count a fall-through -- `act.guest.calc_while_booted`, THE
# TRIPWIRE). Everything below is the C# twin of a PURE decision in NetSyncDiorama.Replay.cs (the two-step drain's book, the
# decision and its order, the backlog verdicts, the battle clock, the abort / restore / end-hold / grace rules, the
# cmd_status filter, the mask mapping); test_harness_netsync.py EVALUATES ActReplaySelfTest's own 34 rows against them (read
# off the stack, in order) and pins the constants by name (CS_REPLAY_CONSTANTS). :class:`ActGuestLane` is the stand-in's
# model of the lane with its statics -- the decisions through these twins, the sequencer NOT (see its docstring).
ACT_MAX_RUNNING = 6                      # "six replays already running" declines `busy`
ACT_PENDING_ABORT_MS = 1500              # a parked START hard-aborts its actor's command-motion replay after this (battle time)
ACT_DEATH_GRACE_MS = 1500                # the death-attack grace (battle time from the lethal impact)
ACT_HOST_END_ABORT_MS = 6000             # a replay still running this long after the host's END is aborted (battle time)
ACT_WALL_CAP_MS = 90000                  # the one WALL-clock timer: no replay outlives this
ACT_W3_MS = 4000                         # W3: an injected end + this; also the run-away hold's bound (battle time)
ACT_WAIT_MAX_MS = 6000                   # a parked START never waits longer than this (battle time)
ACT_INBOX_CAP = 2048                     # the selftest bench inbox
ACT_BOOK_CAP = 512                       # records kept per boot (finished ones trimmed first)
ACT_START_LOG_MAX = 4                    # "started" lines per boot
ACT_ABORT_LOG_MAX = 8                    # "ABORTED" lines per boot
ACT_ST_REGISTERED, ACT_ST_WAITING, ACT_ST_RUNNING, ACT_ST_ENDED, ACT_ST_DECLINED, ACT_ST_ABORTED, ACT_ST_NOOP = range(7)
ACT_GO, ACT_NOOP = 0, 1
ACT_WHY_KNOB, ACT_WHY_LEVER, ACT_WHY_REWORK, ACT_WHY_END, ACT_WHY_STALE, ACT_WHY_BACKLOG = 10, 11, 12, 13, 14, 15
ACT_WHY_ACTOR, ACT_WHY_HIDDEN, ACT_WHY_DEAD, ACT_WHY_KIND, ACT_WHY_TRANSFORM, ACT_WHY_TARGET = 16, 17, 18, 19, 20, 21
ACT_WHY_BUSY, ACT_WHY_LEAVE = 22, 23
ACT_END_NO_HOLD, ACT_END_HOLD, ACT_END_ABORT_THEN_INJECT = 0, 1, 2
ACT_RESTORE_NONE, ACT_RESTORE_FULL, ACT_RESTORE_LIMITED = 0, 1, 2
ACT_SFX_KEEP, ACT_SFX_CANCEL, ACT_SFX_UNLOCK = 0, 1, 2   # ActSfxDropPlan's bits (one SFX of an aborted replay)
ACT_REPLAY_TEST_NONCE = 0x5B             # ActReplaySelfTest's own nonce (NetSyncDiorama's private ActTestNonce; s133's is 0x5A)
ACT_FEEDAT_MAX_MS = 600000               # `actbench feedat <ms 0-600000>`
ACT_PLAY_PCT_MIN, ACT_PLAY_PCT_MAX = 1, 1000   # `actbench tape play [pct 1-1000]`
ACT_HEX_MIN, ACT_HEX_MAX = ACT_LEGACY_LEN * 2, 8192   # one fed frame: an even run of 92-8192 hex digits (46-4096 bytes)
PROOF_REPLAY = "action replay selftest: "   # NetSyncDiorama.ActReplaySelfTest (s134), logged right after PROOF_ACTION
REPLAY_SELFTEST_ROWS = 34                # 14 decision + 2 stance/motion + 3 drain + 2 pending + 2 backlog + 1 clock + 10 rule
#: the stock ids s134's twins and bench name beyond s133's (BattleCommandId; SpecialEffect) -- read off the shared clone by
#: test_harness_netsync.py when it is present, as CS_STOCK_IDS already is
CMD_SUMMON_GARNET, CMD_RUSH_ATTACK, CMD_SYS_PHANTOM, CMD_SYS_LAST_PHOENIX, CMD_SCRIPT_COUNTER1 = 16, 52, 57, 58, 63
CMD_BOUNDARY_UPPER_CHECK = 99
ABILITY_LEVIATHAN_ID = 60                # BattleAbilityId.Leviathan (a SummonGarnet sub_no)
SPECIAL_LEVIATHAN_FULL = 179             # SpecialEffect.Leviathan__Full: a LONG summon (the W3 leg's replay)
SPECIAL_TRANCE_ACTIVATE = 257            # SpecialEffect.Special_Trance_Activate (the SysTrans tripwire leg)
CS_STOCK_IDS.update({
    "BattleCommandId.SummonGarnet": CMD_SUMMON_GARNET, "BattleCommandId.RushAttack": CMD_RUSH_ATTACK,
    "BattleCommandId.SysPhantom": CMD_SYS_PHANTOM, "BattleCommandId.SysLastPhoenix": CMD_SYS_LAST_PHOENIX,
    "BattleCommandId.ScriptCounter1": CMD_SCRIPT_COUNTER1, "BattleCommandId.BoundaryUpperCheck": CMD_BOUNDARY_UPPER_CHECK,
    "BattleAbilityId.Leviathan": ABILITY_LEVIATHAN_ID, "SpecialEffect.Leviathan__Full": SPECIAL_LEVIATHAN_FULL,
    "SpecialEffect.Special_Trance_Activate": SPECIAL_TRANCE_ACTIVATE})
#: BattlePlayerCharacter.PlayerMotionIndex values the s134 bench reads off `battle.units[].mot` (a player's own motion index)
MP_IDLE_NORMAL, MP_DAMAGE1, MP_DAMAGE2, MP_IDLE_CMD, MP_SET, MP_ATTACK = 0, 2, 3, 9, 20, 23

#: `netsync.battle.act.guest` at AppendNetsync's catch-line sentinels, in AppendActGuest's key order (counts 0, ids / ms /
#: knob / host_caps / rx_dropped / battle_ms -1, booleans false, strings and `last` null, the fixed sub-objects written out
#: whole). The live block differs at rest only where the agent reads a static: `on` / `rework` / `knob` (the ini's
#: ActionReplay, this machine's SFXRework: true / true / 1 with no lever pulled).
ACT_GUEST_SENTINELS = {
    "on": False, "why": None, "rework": False, "knob": -1, "host_caps": -1, "bit5": False,
    "levers": {"replay_off": False, "rework_off": False, "shortcircuit_off": False, "knob": -1},
    "inbox": 0, "starts_rx": 0, "ends_rx": 0, "started": 0, "queued": 0, "waiting": 0, "running": 0, "declined": 0,
    "declined_why": None, "stale": 0, "backlog": 0, "superseded": 0, "noop": 0, "dropped": 0, "aborted": 0,
    "abort_why": None, "aborts": {"pending": 0, "host_end": 0, "cap": 0, "actor": 0, "fault": 0, "leave": 0, "w3": 0, "r8": 0,
                                  "clear": 0},
    "discarded": {"pending": 0, "running": 0}, "ended": 0, "faulted": 0, "hits": 0, "credits": 0, "paired": 0, "swing_skipped": 0, "calc_while_booted": 0,
    "var_refused": 0, "old_host": False, "grace": {"armed": 0, "mask": 0}, "hold_through": 0, "end_held": 0,
    "rx_dropped": -1, "battle_ms": -1, "paused_ms": 0, "window": {"open": False, "restores": 0, "limited": 0},
    "last": None,
}
#: `act.guest.last` (HarnessActLast: the last START received this boot), in AppendActGuest's order
ACT_GUEST_LAST_KEYS = ("id", "actor", "cmd", "sub", "kind", "num", "speed", "state", "why", "arrive_ms", "launch_ms",
                       "first_hit_ms", "end_ms", "hits")
#: `battle.units[]`'s s134 keys, in AppendBattleUnits' order (after s115's `z`, before `status`)
UNIT_ACT_KEYS = ("anim", "anim_frame", "away", "rot_y", "acting", "die_seq", "row")
#: ActStateName: a record's state as `last.state` reads it
ACT_STATE_NAMES = {ACT_ST_REGISTERED: "queued", ACT_ST_WAITING: "waiting", ACT_ST_RUNNING: "running",
                   ACT_ST_ENDED: "ended", ACT_ST_DECLINED: "declined", ACT_ST_ABORTED: "aborted", ACT_ST_NOOP: "noop"}
#: ActWhyName: a verdict's decline reason (anything else "go")
ACT_WHY_NAMES = {ACT_WHY_KNOB: "knob", ACT_WHY_LEVER: "lever", ACT_WHY_REWORK: "rework", ACT_WHY_END: "end",
                 ACT_WHY_LEAVE: "leave", ACT_WHY_STALE: "stale", ACT_WHY_BACKLOG: "backlog", ACT_WHY_ACTOR: "actor",
                 ACT_WHY_HIDDEN: "hidden", ACT_WHY_DEAD: "dead", ACT_WHY_KIND: "kind", ACT_WHY_TRANSFORM: "transform",
                 ACT_WHY_TARGET: "target", ACT_WHY_BUSY: "busy", ACT_NOOP: "noop"}
#: ActWhyDetail: each early / decided decline's detail in the "declined" line ("" = none)
ACT_WHY_DETAILS = {
    ACT_WHY_KNOB: "[Netsync] ActionReplay=0 (or `actbench knob 0`)",
    ACT_WHY_LEVER: "the `actbench replay off` lever: the pre-s134 guest",
    ACT_WHY_REWORK: "this machine has no [Battle] SFXRework (the sequencer's Loop returns at once without it)",
    ACT_WHY_END: "the end is already being presented",
    ACT_WHY_LEAVE: "a Leave of the diorama is in flight",
    ACT_WHY_STALE: "its END arrived before it launched -- the host already finished it",
    ACT_WHY_BACKLOG: "drained in a backlog Update (before the boot's LIVE latch, or around a stale battle lane)",
    ACT_WHY_ACTOR: "its actor has no local unit",
    ACT_WHY_HIDDEN: "its actor is hidden here",
    ACT_WHY_DEAD: "its actor is dead or dying and stock would not run this command",
    ACT_WHY_KIND: "an unknown vfx kind",
    ACT_WHY_TRANSFORM: "a monster-transform command",
    ACT_WHY_TARGET: "its target mask maps to no local unit",
    ACT_WHY_BUSY: f"{ACT_MAX_RUNNING} replays are already running",
}
#: the decline reasons a START can end on (`declined_why`): ActDecide's, then the lane's own
ACT_DECLINE_REASONS = ("knob", "lever", "rework", "end", "leave", "stale", "backlog", "actor", "hidden", "dead", "kind",
                       "transform", "target", "busy", "noop", "superseded", "timeout", "nosequence", "duplicate", "fault",
                       "clear", "w3", "r8")
#: the abort reasons (`abort_why`), in NetSyncDiorama.ActAbortReasons' order -- `act.guest.aborts` counts each under its key
ACT_ABORT_REASONS = ("pending", "host-end", "cap", "actor", "fault", "leave", "w3", "r8", "clear")
#: `act.guest.aborts`' keys (AppendActGuest's order: each reason, `-` as `_`)
ACT_ABORTS_KEYS = tuple(r.replace("-", "_") for r in ACT_ABORT_REASONS)
#: the aborts an END presentation owns (R8, W3 or its hold's break, a Leave) -- every other reason is a mid-battle timing
#: failure (`pending` / `host-end` / `cap`) or a defect (`actor` / `fault`); `clear` is the bench's own
ACT_END_ABORTS = ("r8", "w3", "leave")
#: `actbench <op>` -- the GUEST half's ops (NetSyncDiorama.IsActGuestBenchOp, routed BEFORE s133's HarnessActBench); `tape`
#: is one only with the value `play`
ACT_GUEST_BENCH_OPS = ("feed", "feedat", "replay", "rework", "shortcircuit", "knob", "clear", "teardown")
#: the engine's words (each a C# literal of the stack, or its head)
LOG_REPLAY = "[NetSync] action replay: "
LOG_REPLAY_OLD_HOST = ("[NetSync] action replay: host predates action replay -- its impacts carry no action id (no 0xA6 "
                       "extension), so every impact takes the legacy route (numbers, the flinch, the player MP_ATTACK swing; "
                       "logged once per boot)")
LOG_REPLAY_DECLINED = "[NetSync] action replay: declined "
LOG_REPLAY_NOOP = "[NetSync] action replay: noop -- id "
LOG_REPLAY_STARTED = "[NetSync] action replay: started id "
LOG_REPLAY_ABORTED = "[NetSync] action replay: ABORTED id "
LOG_REPLAY_WINDOW = "[NetSync] action replay: busy window closed after an abort -- "
LOG_REPLAY_DISCARD = "[NetSync] action replay: ActDiscardAll ("
LOG_REPLAY_SUMMARY = "[NetSync] action replay: boot summary ("
LOG_REPLAY_TRIPWIRE = ("[NetSync] action replay: TRIPWIRE -- the battle calculator ran while a diorama is booted "
                       "(calc_while_booted=")
LOG_REPLAY_FAULTED = " faulted in the sequencer -- released and aborted (`fault`; logged once per boot): "
LOG_REPLAY_TICK_FAILED = ("[NetSync] action replay tick failed (logged once per boot; the teardown still discards every "
                          "replay): ")
LOG_REPLAY_END_WAITS = " acting replay(s) -- the stock tail would hide or settle a unit mid-replay; held at most "
LOG_REPLAY_NO_SHORT = (" runs WITHOUT the short-circuit -- CALIBRATION: its hits reach the battle calculator (the tripwire's "
                       "red; the selftest save only)")
LOG_REPLAY_BENCH = "[NetSync] harness: action replay bench -- "
LOG_REPLAY_OFF = ("[NetSync] harness: action replay OFF -- CALIBRATION: the pre-s134 guest (every START declines `lever`, "
                  "impacts take the legacy route)")
LOG_REPLAY_ON = "[NetSync] harness: action replay ON"
LOG_REPLAY_REWORK_OFF = "[NetSync] harness: action replay sees NO SFXRework -- every START declines `rework`"
LOG_REPLAY_REWORK_ON = "[NetSync] harness: action replay sees this machine's own [Battle] SFXRework"
LOG_REPLAY_SHORT_OFF = ("[NetSync] harness: action replay short-circuit OFF for the NEXT replay -- CALIBRATION: its hits reach "
                        "the battle calculator (the tripwire's red; the selftest save only)")
LOG_REPLAY_SHORT_ON = "[NetSync] harness: action replay short-circuit ON"
LOG_REPLAY_KNOB = "[NetSync] harness: action replay knob "
LOG_REPLAY_CLEARED = "[NetSync] harness: action replay bench cleared ("
LOG_REPLAY_LEVERS_BACK = ("[NetSync] harness: action replay levers back (replay ON, the machine's own SFXRework, the "
                          "short-circuit ON, the ini's ActionReplay; released with the harness)")
LOG_REPLAY_INBOX_EMPTIED = "[NetSync] harness: action replay inbox emptied ("


# ---- the pure decisions (each NetSyncDiorama's method of the same name, its parameters in its order)
def act_battle_delta(delta: int, paused_prev: bool, paused_now: bool) -> int:
    """NetSyncDiorama.ActBattleDelta -- THE BATTLE CLOCK's step (audit 3.5): ``delta`` wall ms since the previous read count
    unless BOTH reads were paused (the EndWatchdogs rule: a span is skipped only between two paused reads, never
    inflated); a negative delta counts nothing."""
    if delta <= 0 or (paused_prev and paused_now):
        return 0
    return int(delta)


def act_backlog_transport(live_latched: bool, lane_live_now: bool, lane_live_prev: bool) -> bool:
    """NetSyncDiorama.ActBacklogTransport (audit amendment 5): the transport drain's Update is a BACKLOG before the boot's
    LIVE latch, while the battle lane is stale, or in the Update the lane went stale -> live."""
    return not live_latched or not lane_live_now or not lane_live_prev


def act_backlog_bench(normal_latched: bool, live_latched: bool, bench_edge: bool) -> bool:
    """NetSyncDiorama.ActBacklogBench: the selftest bench drain's backlog -- before the boot's steady (or LIVE) latch, or
    the Update after a bench-feed lane edge."""
    return (not normal_latched and not live_latched) or bool(bench_edge)


#: ActDecideIn's fields (snake_cased), the struct ActDecide reads
ACT_DECIDE_FIELDS = ("knob_off", "lever_off", "no_rework", "end_presented", "leaving", "stale", "backlog", "actor_missing",
                     "actor_hidden", "dead_or_dying", "actor_linked", "monster_transform", "cmd_no", "die_seq", "kind",
                     "mapped_tar", "running")


def act_decide_in(**kw) -> dict:
    """``new ActDecideIn()`` -- every field at its default (false / 0), then ``kw`` (snake_cased field names)."""
    d = {f: (0 if f in ("cmd_no", "die_seq", "kind", "mapped_tar", "running") else False) for f in ACT_DECIDE_FIELDS}
    bad = set(kw) - set(d)
    if bad:
        raise KeyError(f"act_decide_in: no field {sorted(bad)}")
    d.update(kw)
    return d


def act_dead_may_run(cmd_no: int, die_seq: int, linked: bool) -> bool:
    """NetSyncDiorama.ActDeadMayRun (review F3): stock lets a Death-status caster run cmd_no 54-99 (EnemyDying,
    EnemyReaction, the Sys* ids); the replay mirrors that while die_seq < 5 and the actor is still linked."""
    return CMD_ENEMY_COUNTER < int(cmd_no) <= CMD_BOUNDARY_UPPER_CHECK and int(die_seq) < 5 and bool(linked)


def act_decide(d: dict) -> int:
    """NetSyncDiorama.ActDecide -- THE DECISION, in the amended order: knob, lever, rework, end, leave, stale, backlog,
    actor, hidden, dead (unless stock would run it), kind, transform, target; then NOOP for kind none; then the running
    cap; else go."""
    if d["knob_off"]:
        return ACT_WHY_KNOB
    if d["lever_off"]:
        return ACT_WHY_LEVER
    if d["no_rework"]:
        return ACT_WHY_REWORK
    if d["end_presented"]:
        return ACT_WHY_END
    if d["leaving"]:
        return ACT_WHY_LEAVE
    if d["stale"]:
        return ACT_WHY_STALE
    if d["backlog"]:
        return ACT_WHY_BACKLOG
    if d["actor_missing"]:
        return ACT_WHY_ACTOR
    if d["actor_hidden"]:
        return ACT_WHY_HIDDEN
    if d["dead_or_dying"] and not act_dead_may_run(d["cmd_no"], d["die_seq"], d["actor_linked"]):
        return ACT_WHY_DEAD
    if d["kind"] > VFX_KIND_COMMON:
        return ACT_WHY_KIND
    if d["monster_transform"]:
        return ACT_WHY_TRANSFORM
    if d["mapped_tar"] == 0:
        return ACT_WHY_TARGET
    if d["kind"] == VFX_KIND_NONE:
        return ACT_NOOP
    if d["running"] >= ACT_MAX_RUNNING:
        return ACT_WHY_BUSY
    return ACT_GO


def act_why_name(why: int) -> str:
    """NetSyncDiorama.ActWhyName."""
    return ACT_WHY_NAMES.get(int(why), "go")


def act_stance_gate(player: bool, monster_transform: bool, cmd_no: int) -> bool:
    """NetSyncDiorama.ActStanceGate (audit amendment 2): MP_IDLE_CMD at the launch for a player, not monster-transformed,
    whose cmd_no <= RushAttack or > BoundaryUpperCheck -- the host's SELECT_VFX gate (no Sys* stance)."""
    return bool(player) and not monster_transform and (int(cmd_no) <= CMD_RUSH_ATTACK
                                                       or int(cmd_no) > CMD_BOUNDARY_UPPER_CHECK)


def act_cmd_motion_filter(include_sys_cmd: bool, cmd_no: int) -> bool:
    """NetSyncDiorama.ActCmdMotionFilter: btl_util.IsBtlUsingCommandMotion's stock cmd_no filter (audit amendment 1)."""
    return bool(include_sys_cmd) or int(cmd_no) <= CMD_ENEMY_REACTION or int(cmd_no) >= CMD_SCRIPT_COUNTER1


def act_abort_why(actor_gone: bool, host_ended: bool, host_end_ms: int, now_ms: int, wall_ms: int) -> str | None:
    """NetSyncDiorama.ActAbortWhy: a running replay is aborted when its actor is gone, at the host's END + 6 s (battle
    time), or past the 90 s WALL cap; None = it runs on."""
    if actor_gone:
        return "actor"
    if host_ended and now_ms - host_end_ms > ACT_HOST_END_ABORT_MS:
        return "host-end"
    if wall_ms > ACT_WALL_CAP_MS:
        return "cap"
    return None


def act_pending_abort_due(wait_since_ms: int, now_ms: int) -> bool:
    """NetSyncDiorama.ActPendingAbortDue: a parked START hard-aborts its actor's command-motion replay once it waited
    1500 ms of battle time."""
    return now_ms - wait_since_ms >= ACT_PENDING_ABORT_MS


def act_restore_scope(aborted: bool, end_injected: bool) -> int:
    """NetSyncDiorama.ActRestoreScope (audit 3.2 / amendment 9): nothing after a natural end; the full restore after an
    abort; only the shared lanes once an end was injected."""
    if not aborted:
        return ACT_RESTORE_NONE
    return ACT_RESTORE_LIMITED if end_injected else ACT_RESTORE_FULL


def act_end_hold_step(hold_kind: bool, acting: bool, held_ms: int) -> int:
    """NetSyncDiorama.ActEndHoldStep (audit D02): the run-away / the annihilation's MENU_OFF settle waits while a replay
    acts, at most W3 of battle time; past it every replay is aborted and the end injects."""
    if not hold_kind or not acting:
        return ACT_END_NO_HOLD
    return ACT_END_ABORT_THEN_INJECT if held_ms >= ACT_W3_MS else ACT_END_HOLD


def act_cursor_bit_after(current: int, snap_bit: int, limited: bool) -> int:
    """NetSyncDiorama.ActCursorBitAfter: the FULL restore puts back cmd_status bit 1 as the busy window opened with it (an
    abort between a sequence's `&65533` and its `|2` would strand the target pointers hidden); the LIMITED restore leaves
    it (InjectEnd cleared it on purpose)."""
    return int(current) & 0xFFFF if limited else ((int(current) & ~2) | (int(snap_bit) & 2)) & 0xFFFF


def act_restores_disappear(player: bool, dead: bool) -> bool:
    """NetSyncDiorama.ActRestoresDisappear: the full restore's disappear -- every unit's but an ENEMY that died during the
    window (its fade stays); a dead player's body is shown again."""
    return bool(player) or not dead


def act_pre_inject_mask(aborted: int, running: int) -> int:
    """NetSyncDiorama.ActPreInjectMask: right before an end injection, the units of replays aborted before it that no
    still-running replay acts with are restored."""
    return int(aborted) & ~int(running)


def act_end_hold_breaks(holding: bool, block_now: bool, hold_kind_now: bool) -> bool:
    """NetSyncDiorama.ActEndHoldBreaks: a waiting hold whose host block is gone (a stale lane) or no longer asks for a
    holding presentation (a flee's CLOSE+ESCAPE) injects what it HELD at once."""
    return bool(holding) and (not block_now or not hold_kind_now)


def act_sfx_drop_plan(running: int, is_load_cur: bool, use_camera: bool, load_has_ended: bool) -> int:
    """NetSyncDiorama.ActSfxDropPlan: one SFX of a hard-aborted replay -- a playing one is the release's (keep); any other
    is cancelled, and a camera SFX that is LoadCur with its load ended (it holds SFXData.lockLoading) is unlocked too."""
    if int(running) > 0:
        return ACT_SFX_KEEP
    return ACT_SFX_CANCEL | (ACT_SFX_UNLOCK if is_load_cur and use_camera and load_has_ended else ACT_SFX_KEEP)


def act_grace_arms(bit5: bool, can_replay: bool, caster_is_player: bool, target_is_player: bool, die_atk: bool,
                   already_dead: bool) -> bool:
    """NetSyncDiorama.ActGraceArms (amendment 8, D10): the host advertised bit 5, this guest can replay, a lethal impact
    from a PLAYER caster on an AttackOnDeath enemy that is not dead yet -- nothing less."""
    return bool(bit5 and can_replay and caster_is_player and not target_is_player and die_atk and not already_dead)


def act_cmd_status_for(current: int, wanted: int) -> int:
    """NetSyncDiorama.ActCmdStatusFor: a replay's SetVariable may change only bit 1 of cmd_status (UInt16)."""
    return ((int(current) & ~2) | (int(wanted) & 2)) & 0xFFFF


def act_map_mask_with(wire: int, resolve) -> int:
    """NetSyncDiorama.ActMapMaskWith: a host wire mask (bits 0-3 its compacted players, 4-7 its enemy slots) onto local
    btl_ids through ``resolve`` (wire index -> local btl_id, 0 = none)."""
    m = 0
    for i in range(8):
        if int(wire) & (1 << i):
            m |= int(resolve(i))
    return m & 0xFFFF


class ActRec:
    """NetSyncDiorama.ActRec -- one START, from its arrival to its end (the fields the book, the decision and the stand-in
    read; the CMD_DATA / sequencer half is the engine's alone)."""

    def __init__(self, act_id: int, nonce: int, actor_slot: int, actor_flags: int = ACTOR_IS_PLAYER, *,
                 cmd_no: int = CMD_ATTACK_ID, sub_no: int = 0, tar_id: int = 0, cursor: int = 0, info: int = 0,
                 magic_caster: int = 0, vfx_kind: int = VFX_KIND_SPECIAL, vfx_num: int = 0, patched_vfx: int = -1,
                 host_speed: int = 5, host_seq: int = 0, state: int = ACT_ST_REGISTERED):
        self.id = _act_u16(act_id)
        self.nonce = _act_u8(nonce)
        self.key = ActBook.key_of(self.nonce, self.id)
        self.host_seq = _act_u16(host_seq)
        self.actor_slot, self.actor_flags = _act_u8(actor_slot), _act_u8(actor_flags)
        self.cmd_no, self.sub_no, self.tar_id = _act_u16(cmd_no), int(sub_no), _act_u16(tar_id)
        self.cursor, self.info, self.magic_caster = _act_u8(cursor), _act_u8(info), _act_u16(magic_caster)
        self.vfx_kind, self.vfx_num, self.patched_vfx = _act_u8(vfx_kind), int(vfx_num), int(patched_vfx)
        self.host_speed = _act_u8(host_speed)
        self.state = state
        self.why = None
        self.stale = self.backlog = self.bench = self.host_ended = self.faulted = False
        self.no_short_circuit = self.row_switched = False
        self.arrive_ms, self.wait_since_ms, self.launch_ms, self.first_hit_ms = 0, -1, -1, -1
        self.end_ms = self.host_end_ms = -1
        self.launch_wall = 0
        self.hits = self.credits = 0
        self.impact_mask = 0
        self.frames = 0                          # (the stand-in's model: frames since its launch)
        self.actor = None                        # (the stand-in's model: the resolved actor unit)
        self.targets = []                        # (the stand-in's model: the resolved target units)
        # [ff9mapkit netsync s135] the hold's CREDITS (ActRec.HoldCreditUnits / HoldCreditMs, null until the first): one per
        # hit on a master target that released no held impact -- its btl_id and the battle ms of the hit, oldest first
        self.hold_credit_units = None
        self.hold_credit_ms = None

    @classmethod
    def from_start(cls, a: dict) -> "ActRec":
        """ActRegisterStart's record: a parsed START (:func:`decode_action` / :func:`read_action_ext`)."""
        return cls(a["act_id"], a["nonce"], a["actor_slot"], a["actor_flags"], cmd_no=a["act_cmd_no"],
                   sub_no=a["act_sub_no"], tar_id=a["act_tar_id"], cursor=a["act_cursor"], info=a["act_info"],
                   magic_caster=a["act_magic_caster"], vfx_kind=a["vfx_kind"], vfx_num=a["vfx_num"],
                   patched_vfx=a["act_patched_vfx"], host_speed=a["host_speed"], host_seq=a["seq_horizon"])

    @property
    def is_player(self) -> bool:
        return bool(self.actor_flags & ACTOR_IS_PLAYER)

    @property
    def scripted(self) -> bool:
        return bool(self.actor_flags & ACTOR_SCRIPTED)

    @property
    def monster_transform(self) -> bool:
        return bool(self.actor_flags & ACTOR_MONSTER_TRANSFORM)

    @property
    def pending(self) -> bool:
        return self.state in (ACT_ST_REGISTERED, ACT_ST_WAITING)

    @property
    def covers_swing(self) -> bool:
        """An impact of this action skips the legacy swing: a replay is, was or will be its clip -- or none at all (NOOP)."""
        return self.state in (ACT_ST_REGISTERED, ACT_ST_WAITING, ACT_ST_RUNNING, ACT_ST_ENDED, ACT_ST_NOOP)


class ActBook:
    """NetSyncDiorama.ActBook -- THE BOOK (pure; the selftest drives fresh ones): every record of this boot by key, and
    the records not yet decided or launched, in arrival order. ``register_start`` / ``host_end`` are the two-step drain's
    first step; ``park`` is the per-actor pending slot."""

    def __init__(self) -> None:
        self.by_id: dict = {}
        self.queue: list = []
        self._order: list = []

    @staticmethod
    def key_of(nonce: int, act_id: int) -> int:
        """ActBook.KeyOf(Byte nonce, UInt16 id): ``(nonce << 16) | id``."""
        return (_act_u8(nonce) << 16) | _act_u16(act_id)

    def register_start(self, r: ActRec) -> bool:
        """Step one of the drain for a START: False = a duplicate key (not registered)."""
        if r.key in self.by_id:
            return False
        self._trim()
        self.by_id[r.key] = r
        self._order.append(r.key)
        self.queue.append(r)
        return True

    def host_end(self, key: int, now: int) -> ActRec | None:
        """Step one of the drain for an END: a record not yet launched turns STALE; a running one is marked host-ended at
        ``now`` (the END + 6 s abort). None = no such START this boot."""
        r = self.by_id.get(key)
        if r is None:
            return None
        if r.pending:
            r.stale = True
        if not r.host_ended:
            r.host_ended = True
            r.host_end_ms = int(now)
        return r

    def find(self, key: int) -> ActRec | None:
        return self.by_id.get(key)

    def park(self, r: ActRec, now: int) -> ActRec | None:
        """The per-actor pending slot: ``r`` waits from ``now``; an older WAITING record of the same actor (slot and side)
        is SUPERSEDED -- returned for its decline."""
        older = next((q for q in self.queue if q is not r and q.state == ACT_ST_WAITING and q.actor_slot == r.actor_slot
                      and q.is_player == r.is_player), None)
        r.state = ACT_ST_WAITING
        r.wait_since_ms = int(now)
        return older

    def settle(self, r: ActRec) -> None:
        if r in self.queue:
            self.queue.remove(r)

    def clear(self) -> None:
        self.by_id.clear()
        self.queue.clear()
        self._order.clear()

    def _trim(self) -> None:
        """At most ACT_BOOK_CAP records: the oldest FINISHED ones go first (a live one is never dropped)."""
        i = 0
        while len(self.by_id) >= ACT_BOOK_CAP and i < len(self._order):
            r = self.by_id.get(self._order[i])
            if r is not None and (r.pending or r.state == ACT_ST_RUNNING):
                i += 1
                continue
            self.by_id.pop(self._order[i], None)
            del self._order[i]


def act_parse_hex_frames(text) -> tuple:
    """NetSyncDiorama.ActParseHexFrames: ``hex[,hex...]`` -> ``(frames, why)`` -- each frame an even run of 92-8192 hex
    digits (46-4096 bytes); why = the engine's refusal (None = parsed)."""
    frames = []
    for raw in str(text or "").split(","):
        h = raw.strip()
        if len(h) < ACT_HEX_MIN or len(h) > ACT_HEX_MAX or len(h) & 1:
            return [], "netsync actbench feed: each frame is an even run of 92-8192 hex digits (46-4096 bytes)"
        for i in range(0, len(h), 2):
            pair = h[i:i + 2]
            if any(c not in "0123456789abcdefABCDEF" for c in pair):
                return [], f"netsync actbench feed: '{pair}' is not hex"
        frames.append(bytes.fromhex(h))
    return frames, None


def act_feed_arg(frames) -> str:
    """The ``hex[,hex...]`` argument of `actbench feed|feedat` for ``frames`` (one feed = one drain)."""
    return ",".join(action_hex(f) for f in frames)


def act_tape_play_due(offsets, now_ms: int, pct: int = 100) -> list:
    """`actbench tape play [pct]`'s due times: each frame's offset from the FIRST, scaled by 100 / pct (C#'s Int64 product
    and integer division), from ``now_ms``."""
    if not offsets:
        return []
    base = offsets[0]
    return [int(now_ms) + int((int(ms) - base) * 100 // int(pct)) for ms in offsets]


class ActGuestLane:
    """[ff9mapkit netsync s134] The GUEST's action replay as NetSyncDiorama.Replay.cs runs it, with its statics -- the
    stand-in's model. MODELLED, through the twins above: the per-boot reset (ActResetForBoot), the selftest levers and their
    role gate (`replay|rework|shortcircuit on|off`, `knob 0|1|ini`; ActBenchRelease), the bench inbox (`feed|feedat|tape
    play`, ActParseHexFrames, the 2048 cap), the bench drain (ActionTickBench: the steady gate, the backlog verdict) and its
    route (ActRouteFrame: a START registers -- the early declines --, an END marks its record stale / host-ended, an impact
    pairs with the record its id names: `paired`, `swing_skipped`, an old host's 46-byte impact: `old_host`), the battle
    clock (ActBattleDelta over the caller's clock and pause), the tick (ActTick: the R8 / W3 aborts, the running replays'
    natural end / END+6 s / the 90 s cap / a gone actor, the queue's decide / park / supersede / timeout / pending abort /
    launch), the busy window's close (ActRestoreScope; the restore itself is counted, not performed), ActAbortAll,
    ActDiscardAll, the counters (each abort by its reason -- `aborts` --, the parked STARTs an abort-all drops -- `dropped`
    --, a teardown's drops -- `discarded`) and `last`, and every Log.Message line (each with its "[NetSync] " head, in
    :attr:`lines`). The aborts are judged every tick, paused too (the engine's ActCheckRunning); the sequencer frame is not.
    NOT MODELLED -- the stand-in has no sequencer, no SFX and no BTL_DATA motion: a launched replay RUNS
    :attr:`REPLAY_FRAMES` frames and HITS each of its mapped targets once at :attr:`HIT_FRAME` (ActOnHit's counts and
    credits; a Change replay flips its actor's row there; a `shortcircuit off` replay's hits fall through to the
    tripwire, `calc_while_booted` +1 each); its actor's `anim` is a SHAPE (``ACT_<kind>_<num>`` while acting, ``IDLE``
    otherwise), `away` a triangle peaking at :attr:`AWAY_PEAK` at the hit for a player's short-range Attack; no
    `nosequence` (every kind 1-4 runs), no fault, no zombie, no SFX loader, no hold-through, no run-away hold (`end_held`) and
    no hold break, no pre-injection restore, no death-attack grace (no
    AttackOnDeath enemy: `grace` stays 0), no `var_refused`, no transport (`rx_dropped` -1); an applied impact's figures,
    flinch and HP/MP writes are not modelled (its pairing is).
    [ff9mapkit netsync s135] With :attr:`with_hold` true (the stand-in's `acthold` rung) the lane carries THE REPLAY HIT
    HOLD (:class:`ActHoldLane`, :attr:`hold`): ApplyActionFrame's intake, the releases at the hit (ActOnHit), at the natural
    end, the abort, a decline / noop, the timers, the end injection and the teardown's discard -- and from that rung on the
    arrival path's state writes, figures (`figs[]`) and flinch ARE modelled (an s134 lane keeps s134's model: pairing
    only). A hit's figure is DISPLAYED :attr:`FIGURE_FRAMES` frames after the hit (the sequence's Figure point).
    [ff9mapkit netsync s136] With :attr:`with_fallback` true (the stand-in's `actfallback` rung; it needs the hold's) the
    lane carries FALLBACK A (:class:`ActFallbackLane`, :attr:`fallback`): ApplyActionFrameNow's motion step and
    ActReleaseHeld's fallback step play one stock clip per action no replay covers -- an s135 lane keeps the s110 swing.
    [ff9mapkit netsync s137] With :attr:`with_trance` true (the stand-in's `acttrance` rung; it needs fallback A's) the lane
    carries THE TRANCE BURST TIMING (:class:`ActTranceLane`, :attr:`trance`): ApplyUnit's model check records a deferral,
    ActTick resolves it every tick, a SysTrans replay's hit swaps the model -- an s136 lane swaps at the sample (and
    publishes no worn model: `battle.units[].trance_model` is s137's)."""

    REPLAY_FRAMES = 30
    HIT_FRAME = 15
    AWAY_PEAK = 600.0
    FIGURE_FRAMES = 4                            # [ff9mapkit netsync s135] the hit -> its Figure point (audit amendment 8)

    def __init__(self) -> None:
        #: [ff9mapkit netsync s135] the replay hit hold (its state and levers; ``with_hold`` decides whether it RUNS)
        self.hold = ActHoldLane(self)
        #: [ff9mapkit netsync s135] True, or a callable answering it (the stand-in: its `acthold` rung) -- False = s134
        self.with_hold_fn = False
        #: [ff9mapkit netsync s136] fallback A (its state and lever; ``with_fallback`` decides whether it RUNS)
        self.fallback = ActFallbackLane(self)
        #: [ff9mapkit netsync s136] True, or a callable answering it (the stand-in: its `actfallback` rung) -- False = s135
        self.with_fallback_fn = False
        #: [ff9mapkit netsync s136] [fix pass: timing-1] true while :meth:`abort_all` runs (fallback A's end block)
        self.aborting_all = False
        #: [ff9mapkit netsync s137] the trance burst timing (its state and lever; ``with_trance`` decides whether it RUNS)
        self.trance = ActTranceLane(self)
        #: [ff9mapkit netsync s137] True, or a callable answering it (the stand-in: its `acttrance` rung) -- False = s136
        self.with_trance_fn = False
        self.ctx_last: dict = {}                 # the last ctx a drain / tick / bench passed (the hold's releases resolve by it)
        self.action_replay = True                # [Netsync] ActionReplay (the ini's; default 1)
        self.sfx_rework = True                   # this machine's [Battle] SFXRework
        self.bench_replay_off = False
        self.bench_rework_off = False
        self.bench_short_off = False
        self.bench_knob = -1
        self.inbox: list = []                    # [[due_ms, bytes]]
        self.lines: list = []
        self.last = None
        self.restores = self.restores_limited = 0
        self.rows: dict = {}                     # (the stand-in's model: a Change replay's row flips, by unit slot)
        self.swings: dict = {}                   # (the stand-in's model: a legacy swing's frames left, by unit slot)
        self.reset_for_boot(True)

    # -- the role-gated levers (ActLeverOff / ActReworkOn / ActKnobOn / ActCanReplay)
    def knob_on(self, role: bool) -> bool:
        return self.bench_knob != 0 if (self.bench_knob >= 0 and role) else bool(self.action_replay)

    def lever_off(self, role: bool) -> bool:
        return self.bench_replay_off and bool(role)

    def rework_on(self, role: bool) -> bool:
        return bool(self.sfx_rework) and not (self.bench_rework_off and role)

    def can_replay(self, role: bool) -> bool:
        return self.knob_on(role) and not self.lever_off(role) and self.rework_on(role)

    def why_not(self, role: bool) -> str | None:
        """HarnessActGuestWhy."""
        return "knob" if not self.knob_on(role) else "lever" if self.lever_off(role) else \
            "rework" if not self.rework_on(role) else None

    def _log(self, text: str) -> None:
        self.lines.append(text)

    # -- the per-boot reset
    def reset_for_boot(self, counters: bool) -> None:
        """ActResetForBoot: the boot block (``counters`` true), Boot's catch and ActDiscardAll (false: the counters stay
        readable after the teardown). The levers are harness-scoped, never per boot."""
        self.book = ActBook()
        self.running: list = []
        self.inbox = []
        self.decline_logged: list = []
        self.last = None if counters else self.last
        self.now_ms = 0
        self.clock_last = None
        self.clock_paused = False
        self.bit5 = False
        self.host_caps = -1
        self.lane_seen = False
        self.bench_edge = False
        self.grace_mask = 0
        self.end_inject_ms = -1
        self.end_hold_since = -1
        self.window_open = self.window_aborted = False
        self.window_row_mask = 0
        self.window_abort_mask = 0               # [ff9mapkit netsync s136] [fix pass 2: rtiming-1] _actWindowAbortMask
        self.start_logged = self.abort_logged = 0
        self.old_host_logged = self.trip_logged = False
        # [ff9mapkit netsync s136] ActFallbackReset(counters), before the counters' own early return: the spent keys, the
        # sequence cache and the frame's collapse mask always; its counters, log budgets and `last` with the boot's
        self.fallback.reset(counters)
        # [ff9mapkit netsync s137] ActTranceReset(counters), right after fallback A's: the pending deferrals and the burst
        # marks always; its counters, log budget and `last` with the boot's (and the stand-in's worn models: a boot's units)
        self.trance.reset(counters)
        if not counters:
            return
        # (the stand-in's unit shapes: a diorama BOOT's new units -- ActDiscardAll / `actbench teardown` keeps them, as the
        # engine's ActResetForBoot never touches a unit row)
        self.rows = {}
        self.swings = {}
        self.paused_ms = 0
        self.aborts_by = dict.fromkeys(ACT_ABORT_REASONS, 0)
        self.dropped = self.discarded_pending = self.discarded_running = 0
        self.starts_rx = self.ends_rx = self.started = self.declined = self.stale = self.backlog = 0
        self.superseded = self.noop = self.aborted = self.ended = self.faulted = self.hits = self.credits = 0
        self.paired = self.swing_skipped = self.calc_while_booted = self.grace_armed = self.hold_through = 0
        self.end_held = self.restores = self.restores_limited = self.var_refused = 0
        self.declined_why = self.abort_why = None
        self.old_host = False
        self.rx_dropped = -1
        # [ff9mapkit netsync s135] the boot block's ActHoldClear + ActHoldResetCounters (the mask, the applied seqs, the held
        # and queued frames; the counters, figs[] and the lag)
        self.hold.clear()
        self.hold.reset_counters()

    @property
    def with_hold(self) -> bool:
        """[ff9mapkit netsync s135] The replay hit hold runs (an s135+ engine; the stand-in's `acthold` rung)."""
        fn = self.with_hold_fn
        return bool(fn()) if callable(fn) else bool(fn)

    @property
    def with_fallback(self) -> bool:
        """[ff9mapkit netsync s136] Fallback A exists (an s136+ engine; the stand-in's `actfallback` rung -- the ladder puts
        it after `acthold`: a lane without the hold has no ApplyActionFrameNow to carry it)."""
        fn = self.with_fallback_fn
        return (bool(fn()) if callable(fn) else bool(fn)) and self.with_hold

    def fallback_on(self, role: bool) -> bool:
        """[ff9mapkit netsync s136] ActFallbackOn: fallback A exists and its lever is not pulled (`actbench fallback off`
        needs the selftest role to bite, as the engine's getter)."""
        return self.with_fallback and self.fallback.on(role)

    @property
    def with_trance(self) -> bool:
        """[ff9mapkit netsync s137] The trance burst timing exists (an s137+ engine; the stand-in's `acttrance` rung -- the
        ladder puts it after `actfallback`)."""
        fn = self.with_trance_fn
        return (bool(fn()) if callable(fn) else bool(fn)) and self.with_fallback

    def model_check(self, d, slot: int, bit: bool, role: bool) -> None:
        """[ff9mapkit netsync s137] ApplyUnit's model check (the reconciler's stateless probe: a player with a trance model
        whose worn model differs from the mirrored bit): from s137 ActTranceAtSample -- an s136 lane swaps at the sample,
        as before (no counter: the pre-s137 reconciler's own SetTranceModel)."""
        if not self.trance.has_model(d) or self.trance.wears(d) == bool(bit):
            return
        if self.with_trance:
            self.trance.at_sample(d, slot, bool(bit), role)
        else:
            self.trance.swap(d, bool(bit))

    def dead_model_check(self, d, slot: int, bit: bool, role: bool) -> None:
        """[ff9mapkit netsync s137] (fix: rmodel-1) ApplyUnit's DEATH lane, after it mirrored a dead player's bit: the probe
        with the on-arrival rule (ActTranceAtDeadSample) -- an s136 lane's death lane swaps nothing (as before)."""
        if not self.with_trance or not self.trance.has_model(d) or self.trance.wears(d) == bool(bit):
            return
        self.trance.at_dead_sample(d, slot, bool(bit), role)

    @property
    def live(self) -> bool:
        """ActLive: a replay CMD_DATA is registered."""
        return bool(self.running)

    # -- the bench (HarnessActGuestBench)
    @staticmethod
    def is_bench_op(op: str, value: str, hold: bool = False, fallback: bool = False, trance: bool = False) -> bool:
        """NetSyncDiorama.IsActGuestBenchOp. [ff9mapkit netsync s135] ``hold``: the engine has the replay hit hold (its
        `hold|lifeskip|unit` ops route here too). [ff9mapkit netsync s136] ``fallback``: ...and fallback A (`fallback`).
        [ff9mapkit netsync s137] ``trance``: ...and the trance burst timing (`trancegrace`)."""
        return op in ACT_GUEST_BENCH_OPS or (op == "tape" and value == "play") or (bool(hold) and op in ACT_HOLD_BENCH_OPS) \
            or (bool(fallback) and op in ACT_FALLBACK_BENCH_OPS) or (bool(trance) and op in ACT_TRANCE_BENCH_OPS)

    def bench(self, args: list, *, booted: bool, role: bool, tape=None, ctx: dict | None = None) -> tuple:
        """HarnessActGuestBench(args) -> ``(ok, why)`` in the engine's words; ``args`` the verb's whole list (args[0] =
        "actbench"); ``tape`` = the host lane's tape [(ms, bytes)] (NetSyncBattle.ActTapeCopy) for `tape play`.
        [ff9mapkit netsync s135] ``ctx`` (the tick's) for `unit` (HarnessActHoldBench: the steady gate, the resolve)."""
        if not role:
            return False, "netsync actbench: needs the selftest role (netsync selftest 1)"
        op = str(args[1]).lower() if len(args) > 1 else ""
        val = str(args[2]).lower() if len(args) > 2 else ""
        if self.with_hold and op in ACT_HOLD_BENCH_OPS:
            if ctx is not None:
                self.ctx_last = ctx
            return self.hold.bench(args, op, val, booted=booted, role=role, ctx=ctx or self.ctx_last)
        if self.with_fallback and op in ACT_FALLBACK_BENCH_OPS:
            return self.fallback.bench(args, val)           # [ff9mapkit netsync s136] HarnessActFallbackBench
        if self.with_trance and op in ACT_TRANCE_BENCH_OPS:
            return self.trance.bench(args, val)             # [ff9mapkit netsync s137] HarnessActTranceBench
        if op in ("feed", "feedat"):
            ms = 0
            if op == "feed":
                if len(args) != 3:
                    return False, "netsync actbench feed: expected `feed <hex[,hex...]>`"
                text = args[2]
            else:
                ms = _cs_int(args[2]) if len(args) == 4 else None
                if ms is None or ms < 0 or ms > ACT_FEEDAT_MAX_MS:
                    return False, "netsync actbench feedat: expected `feedat <ms 0-600000> <hex[,hex...]>`"
                text = args[3]
            if not booted:
                return False, f"netsync actbench {op}: needs a booted battle diorama (`netsync dioboot <scene>`)"
            frames, why = act_parse_hex_frames(text)
            if why is not None:
                return False, why
            if len(self.inbox) + len(frames) > ACT_INBOX_CAP:
                return False, (f"netsync actbench {op}: the bench inbox holds at most {ACT_INBOX_CAP} frames "
                               f"({len(self.inbox)} queued)")
            for f in frames:
                self.inbox.append([self.now_ms + ms, f])
            self._log(f"{LOG_REPLAY_BENCH}{len(frames)} frame(s) into the inbox, due "
                      + ("now" if ms == 0 else f"in {ms} ms of battle time") + f" ({len(self.inbox)} queued)")
            return True, None
        if op == "tape":
            pct = _cs_int(args[3]) if len(args) == 4 else 100
            if val != "play" or len(args) > 4 or pct is None or (len(args) == 4 and not
                                                                  ACT_PLAY_PCT_MIN <= pct <= ACT_PLAY_PCT_MAX):
                return False, "netsync actbench tape play: expected `tape play [pct 1-1000]`"
            if not booted:
                return False, "netsync actbench tape play: needs a booted battle diorama (`netsync dioboot <scene>`)"
            tape = list(tape or [])
            if not tape:
                return False, "netsync actbench tape play: the tape is empty (`actbench tape rec` during an own battle first)"
            if len(self.inbox) + len(tape) > ACT_INBOX_CAP:
                return False, (f"netsync actbench tape play: the bench inbox holds at most {ACT_INBOX_CAP} frames "
                               f"({len(self.inbox)} queued)")
            dues = act_tape_play_due([ms for ms, _f in tape], self.now_ms, pct)
            for due, (_ms, f) in zip(dues, tape):
                self.inbox.append([due, bytes(f)])
            self._log(f"{LOG_REPLAY_BENCH}the action tape ({len(tape)} frame(s), {tape[-1][0] - tape[0][0]} ms) plays "
                      f"into the inbox at {pct}% speed")
            return True, None
        if op in ("replay", "rework", "shortcircuit"):
            if len(args) != 3 or val not in ("on", "off"):
                return False, f"netsync actbench {op}: expected `{op} on|off`"
            off = val == "off"
            if op == "replay":
                self.bench_replay_off = off
                self._log(LOG_REPLAY_OFF if off else LOG_REPLAY_ON)
            elif op == "rework":
                self.bench_rework_off = off
                self._log(LOG_REPLAY_REWORK_OFF if off else LOG_REPLAY_REWORK_ON)
            else:
                self.bench_short_off = off
                self._log(LOG_REPLAY_SHORT_OFF if off else LOG_REPLAY_SHORT_ON)
            return True, None
        if op == "knob":
            if len(args) != 3 or val not in ("0", "1", "ini"):
                return False, "netsync actbench knob: expected `knob 0|1|ini`"
            self.bench_knob = -1 if val == "ini" else 1 if val == "1" else 0
            self._log(LOG_REPLAY_KNOB + (f"back to [Netsync] ActionReplay ({1 if self.action_replay else 0})"
                                         if val == "ini" else f"{val} for this process (Memoria.ini untouched)"))
            return True, None
        if op in ("clear", "teardown"):
            if len(args) != 2:
                return False, f"netsync actbench {op}: takes no argument"
            if not booted:
                return False, f"netsync actbench {op}: needs a booted battle diorama"
            if op == "clear":
                n = len(self.inbox)
                self.inbox = []
                self.abort_all("clear", booted=True)
                self._log(f"{LOG_REPLAY_CLEARED}{n} inbox frame(s) dropped; every replay aborted)")
            else:
                self.discard_all("teardown (bench)")
            return True, None
        return False, f"netsync actbench: unknown op '{op}'"

    def release(self) -> None:
        """ActBenchRelease (HarnessReleaseBench's s134 half): every lever back, the inbox emptied."""
        if self.bench_replay_off or self.bench_rework_off or self.bench_short_off or self.bench_knob >= 0:
            self._log(LOG_REPLAY_LEVERS_BACK)
        self.bench_replay_off = self.bench_rework_off = self.bench_short_off = False
        self.bench_knob = -1
        self.hold.release()                      # [ff9mapkit netsync s135] the hold's levers back (its own line first)
        self.fallback.release()                  # [ff9mapkit netsync s136] fallback A's lever back (its own line)
        self.trance.release()                    # [ff9mapkit netsync s137] the trance grace lever back (its own line)
        if self.inbox:
            self._log(f"{LOG_REPLAY_INBOX_EMPTIED}{len(self.inbox)} frame(s); released with the harness)")
        self.inbox = []

    # -- the clock, the latch, the lane edge
    def clock(self, now_ms: int, paused: bool) -> None:
        """ActTick's clock: the caller's monotonic ms (the stand-in's virtual one) through ActBattleDelta."""
        if self.clock_last is None:
            self.clock_last, self.clock_paused = int(now_ms), bool(paused)
            return
        delta = int(now_ms) - self.clock_last
        self.now_ms += act_battle_delta(delta, self.clock_paused, paused)
        if self.clock_paused and paused and delta > 0:
            self.paused_ms += delta
        self.clock_last, self.clock_paused = int(now_ms), bool(paused)

    def latch_caps(self, caps: int, booted: bool) -> None:
        """ActLatchCaps: OR the host's header flags into this boot's latch (never cleared by a null view)."""
        if caps is None or caps < 0 or not booted:
            return
        self.host_caps = int(caps) & 0xFF
        if caps & CAP_ACTION_STARTS:
            self.bit5 = True

    def lane_tick(self, live: bool, role: bool, caps: int = -1, booted: bool = True) -> None:
        """ActLaneTick (LiveTick's half): the latch from a live view, and the lane edge the bench drain reads."""
        if live:
            self.latch_caps(caps, booted)
        if live and not self.lane_seen and role:
            self.bench_edge = True
        self.lane_seen = bool(live)

    # -- the drain (ActionTickBench + ActRouteFrame)
    def drain_bench(self, ctx: dict) -> None:
        """ActionTickBench: ``ctx`` = {booted, role, steady, normal_latched, live_latched, ...} (see :meth:`route`)."""
        if not ctx.get("booted"):
            return
        self.ctx_last = ctx
        edge, self.bench_edge = self.bench_edge, False
        if not self.inbox:
            return
        if not ctx.get("role"):
            self.inbox = []
            return
        if not ctx.get("steady"):
            return
        backlog = act_backlog_bench(ctx.get("normal_latched", False), ctx.get("live_latched", False), edge)
        i = 0
        while i < len(self.inbox):
            due, frame = self.inbox[i]
            if due > self.now_ms:
                i += 1
                continue
            del self.inbox[i]
            a = parse_action(frame)
            if a is None:
                continue
            self.route(frame, a, backlog, True, ctx)

    def route(self, payload: bytes, a: dict, backlog: bool, bench: bool, ctx: dict) -> None:
        """ActRouteFrame: the extension read; a START registers, an END marks its record, anything else applies with the
        record its id names (``ctx["resolve"](wire_index, is_player)`` -> a unit dict or None)."""
        ext = read_action_ext(payload, a)
        if a["is_start"]:
            self._register_start(a, backlog, bench, ctx)
            return
        if a["is_end"]:
            self.ends_rx += 1
            self.book.host_end(ActBook.key_of(a["nonce"], a["act_id"]), self.now_ms)
            return
        rec = None
        if a["has_ext"] and a["ext_kind"] == ACT_EXT_IMPACT and a["act_id"] != 0:
            rec = self.book.find(ActBook.key_of(a["nonce"], a["act_id"]))
        elif ext == ACT_EXT_READ_NONE and not a["stat_tick"] and not a["flags"] & (ACT_FLAG_START | ACT_FLAG_END):
            self._note_old_host()
        self._apply(a, rec, ctx, backlog)

    def _register_start(self, a: dict, backlog: bool, bench: bool, ctx: dict) -> None:
        self.starts_rx += 1
        r = ActRec.from_start(a)
        r.backlog, r.bench, r.arrive_ms = bool(backlog), bool(bench), self.now_ms
        self.last = r
        if not self.book.register_start(r):
            self._decline(r, "duplicate", "a second START with the same id this boot")
            return
        role = ctx.get("role", False)
        d = act_decide_in(knob_off=not self.knob_on(role), lever_off=self.lever_off(role),
                          no_rework=not self.rework_on(role), end_presented=bool(ctx.get("end_presented")),
                          leaving=bool(ctx.get("leaving")), backlog=bool(backlog), actor_linked=True, cmd_no=r.cmd_no,
                          kind=VFX_KIND_SPECIAL, mapped_tar=1)
        early = act_decide(d)
        if early != ACT_GO:
            self._decline(r, act_why_name(early), ACT_WHY_DETAILS.get(early, ""))

    def _note_old_host(self) -> None:
        self.old_host = True
        if not self.old_host_logged:
            self.old_host_logged = True
            self._log(LOG_REPLAY_OLD_HOST)

    def _apply(self, a: dict, rec: ActRec | None, ctx: dict, backlog: bool = False) -> None:
        """ApplyActionFrame's s134 half: a paired impact counts (`paired`) and marks its target for the credits; the
        player-only MP_ATTACK swing is SKIPPED (counted) when a replay covers it -- else it plays (the stand-in: the
        caster's `mot` reads MP_ATTACK for a few frames). Figures, flinch and HP / MP are not modelled.
        [ff9mapkit netsync s135] With the hold (:attr:`with_hold`): the paired accounting first, then ActHoldIntake --
        held, released late or queued -- else the arrival path (ApplyActionFrameNow: the state writes, the figures into
        figs[] "arrival", the flinch, the swing), all modelled from this rung on."""
        resolve = ctx.get("resolve") or (lambda i, p: None)
        dc = resolve(a["caster_slot"], a["caster_is_player"]) if a["caster_slot"] != 0xFF else None
        dt = resolve(a["target_slot"], a["target_is_player"]) if a["target_slot"] != 0xFF else None
        if self.with_hold:
            covered = rec is not None and rec.covers_swing
            if rec is not None:
                self.paired += 1
                if dt is not None:
                    rec.impact_mask |= int(dt.get("id", 0))
            self_cast = dt is not None and dt is dc
            if self.hold.intake(a, dt, dc, self_cast, rec, bool(backlog), covered, ctx):
                return
            self.hold.apply_now(a, dt, dc, self_cast, covered, bool(backlog), ACT_VIA_ARRIVAL, self.now_ms, False, ctx,
                                rec=rec)         # [ff9mapkit netsync s136] + the record (fallback A's covered rule)
            return
        if a["stat_tick"]:
            return
        covered = rec is not None and rec.covers_swing
        if rec is not None:
            self.paired += 1
            if dt is not None:
                rec.impact_mask |= int(dt.get("id", 0))
        if dc is not None and dc is not dt and a["caster_is_player"] and dc.get("alive", True):
            if covered:
                self.swing_skipped += 1
            else:
                self.swings[int(dc.get("slot", -1))] = 20

    # -- the decisions (ActDecideNow), the queue, the launch
    def _decide_now(self, r: ActRec, ctx: dict) -> tuple:
        role = ctx.get("role", False)
        resolve = ctx.get("resolve") or (lambda i, p: None)
        actor = resolve(r.actor_slot, r.is_player) if r.actor_slot <= 7 else None
        d = act_decide_in(knob_off=not self.knob_on(role), lever_off=self.lever_off(role),
                          no_rework=not self.rework_on(role), end_presented=bool(ctx.get("end_presented")),
                          leaving=bool(ctx.get("leaving")), stale=r.stale, backlog=r.backlog, cmd_no=r.cmd_no,
                          kind=r.vfx_kind, monster_transform=r.monster_transform, running=len(self.running),
                          actor_missing=actor is None)
        tar = 0
        if actor is not None:
            d["actor_hidden"] = not r.is_player and bool(int(ctx.get("hidden_mask", 0)) & (1 << r.actor_slot))
            dead = not actor.get("alive", True)
            d["dead_or_dying"] = dead
            # [ff9mapkit netsync s137] die_seq is the ENEMY fade's counter (a dead stand-in enemy is fully faded); a dead PLAYER keeps
            # 0 -- so its Sys* commands (a corpse's SysTrans END) may run, as ActDeadMayRun lets them in the engine
            d["die_seq"] = 5 if dead and not r.is_player else 0
            d["actor_linked"] = True

            def unit_id(i):
                u = resolve(i, i < 4)
                return int(u.get("id", 0)) if u is not None else 0
            tar = act_map_mask_with(r.tar_id, unit_id)
        d["mapped_tar"] = tar
        return act_decide(d), actor, tar

    def _decline(self, r: ActRec, why: str, detail: str) -> None:
        r.state, r.why, r.end_ms = ACT_ST_DECLINED, why, self.now_ms
        self.book.settle(r)
        self.declined += 1
        self.declined_why = why
        if why == "stale":
            self.stale += 1
        elif why == "backlog":
            self.backlog += 1
        if self.with_hold:                       # [ff9mapkit netsync s135] it never launches: its held impacts go now
            self.hold.release_rec(r, act_decline_via(why))
        if self.with_trance:                     # [ff9mapkit netsync s137] a SysTrans START declined: its grace ends at once
            self.trance.on_decline(r, why)
        if why in self.decline_logged or len(self.decline_logged) >= 16:
            return
        self.decline_logged.append(why)
        self._log(f"{LOG_REPLAY_DECLINED}{why} -- id {r.id} slot {r.actor_slot} cmd {r.cmd_no} sub {r.sub_no}"
                  + (f" ({detail})" if detail else "") + f"; its impacts take the legacy route (logged once per boot per "
                  f"reason; declined={self.declined})")

    def _mark_noop(self, r: ActRec) -> None:
        r.state, r.why, r.end_ms = ACT_ST_NOOP, "noop", self.now_ms
        self.book.settle(r)
        self.noop += 1
        self.declined += 1
        self.declined_why = "noop"
        if self.with_hold:                       # [ff9mapkit netsync s135] nothing will hit: its held impacts apply now
            self.hold.release_rec(r, "declined")
        if self.with_trance:                     # [ff9mapkit netsync s137] a SysTrans with no vfx: no burst will come
            self.trance.on_decline(r, "noop")
        if "noop" in self.decline_logged:
            return
        self.decline_logged.append("noop")
        self._log(f"{LOG_REPLAY_NOOP}{r.id} slot {r.actor_slot} cmd {r.cmd_no} has no vfx (kind none): nothing to replay, "
                  "its impacts apply at once (logged once per boot)")

    def _motion_holder(self, actor) -> ActRec | None:
        """ActMotionHolder: the actor's running replay still holding its command motion. A STAND-IN SHAPE, not the engine's
        rule: the stand-in has no sequencer, so ANY running replay of the actor holds it (the engine releases the hold at
        the sequence's Anim Idle -- UnifiedBattleSequencer.cs's cmd_motion clear -- so a park there can launch sooner)."""
        return next((x for x in self.running if x.actor is actor), None)

    def _launch(self, r: ActRec, actor: dict, tar: int, ctx: dict) -> None:
        self._window_check(ctx)
        if not self.running:
            self._window_open()
        r.actor = actor
        resolve = ctx.get("resolve") or (lambda i, p: None)
        r.targets = [u for u in (resolve(i, i < 4) for i in range(8) if r.tar_id & (1 << i)) if u is not None]
        if self.bench_short_off and ctx.get("role"):
            self.bench_short_off = False         # one-shot: THIS replay's hits fall through
            r.no_short_circuit = True
            self._log(f"[NetSync] harness: action replay id {r.id}{LOG_REPLAY_NO_SHORT}")
        self.running.append(r)
        r.state, r.launch_ms, r.launch_wall, r.frames = ACT_ST_RUNNING, self.now_ms, int(ctx.get("wall_ms", 0)), 0
        self.book.settle(r)
        self.started += 1
        if self.start_logged >= ACT_START_LOG_MAX:
            return
        self.start_logged += 1
        self._log(f"{LOG_REPLAY_STARTED}{r.id} slot {r.actor_slot} {'(player)' if r.is_player else '(enemy)'} cmd {r.cmd_no} "
                  f"sub {r.sub_no} kind {r.vfx_kind} num {r.vfx_num} tar 0x{tar & 0xFFFF:02X} host speed {r.host_speed}"
                  + (" scripted" if r.scripted else "") + " -- " + (
                      "presentation only (the short-circuit owns every hit)" if self.start_logged < ACT_START_LOG_MAX
                      else "further starts this boot are counted, not logged"))

    def _decide_queue(self, ctx: dict, paused: bool) -> None:
        steady = bool(ctx.get("steady"))
        for r in list(self.book.queue):
            if not r.pending:
                self.book.settle(r)
                continue
            verdict, actor, tar = self._decide_now(r, ctx)
            if verdict == ACT_NOOP:
                self._mark_noop(r)
                continue
            if verdict != ACT_GO:
                self._decline(r, act_why_name(verdict), ACT_WHY_DETAILS.get(verdict, ""))
                continue
            if r.state == ACT_ST_REGISTERED:
                older = self.book.park(r, self.now_ms)
                if older is not None:
                    self.superseded += 1
                    self._decline(older, "superseded", f"a newer START of the same actor (id {r.id}) replaced it in the "
                                                       "actor's pending slot")
            if self.now_ms - r.wait_since_ms > ACT_WAIT_MAX_MS:
                self._decline(r, "timeout", f"it waited {ACT_WAIT_MAX_MS} ms of battle time without a launch")
                continue
            if not steady or paused:
                continue
            holder = self._motion_holder(actor)
            if holder is not None:
                if not act_pending_abort_due(r.wait_since_ms, self.now_ms):
                    continue
                self._abort(holder, "pending", ctx)
                self._window_check(ctx)
            self._launch(r, actor, tar, ctx)

    # -- the running replays, the aborts, the window
    def _hit(self, r: ActRec, target: dict) -> None:
        """ActOnHit: the hit counted, a credit when no impact of this action had reached that target yet; a Change replay
        switches its actor's row once; a `shortcircuit off` replay falls through (the tripwire counts it)."""
        r.hits += 1
        self.hits += 1
        if r.first_hit_ms < 0:
            r.first_hit_ms = self.now_ms
        if not r.impact_mask & int(target.get("id", 0)):
            r.credits += 1
            self.credits += 1
        if r.cmd_no == CMD_CHANGE_ID and not r.row_switched and r.actor is not None and r.actor.get("player"):
            r.row_switched = True
            slot = int(r.actor.get("slot", -1))
            self.window_row_mask |= int(r.actor.get("id", 0))
            self.rows[slot] = 1 - self.rows.get(slot, 1)
        if r.no_short_circuit:
            self.note_calc_while_booted()
        if self.with_trance:
            # [ff9mapkit netsync s137] THE TRANCE BURST (ActTranceOnHit, before the hold's release): a SysTrans replay's hit
            # swaps its actor's model by the probe with the mirrored bit, under the gate
            self.trance.on_hit(r, bool((self.ctx_last or {}).get("role", False)))
        if self.with_hold:
            # [ff9mapkit netsync s135] THE HIT RELEASE (ActHoldOnHit; the stand-in has no slave parts: the master is the
            # target): inside EffectPoint's bracket unless the replay falls through the short-circuit
            self.hold.on_hit(r, target, not r.no_short_circuit)

    def note_calc_while_booted(self) -> None:
        """NoteCalcWhileBooted -- THE TRIPWIRE (the stand-in: a fall-through hit)."""
        self.calc_while_booted += 1
        if not self.trip_logged:
            self.trip_logged = True
            self._log(f"{LOG_REPLAY_TRIPWIRE}{self.calc_while_booted}): a replay fell through the short-circuit or a stock "
                      "path computed in the diorama (logged once per boot)")

    def _check_running(self, ctx: dict, paused: bool = False) -> None:
        """ActCheckRunning: the stand-in's sequencer frame (the hit, the natural end) advances only while BattleMain runs --
        never paused -- but the aborts are judged EVERY tick, paused too (the engine's ActCheckRunning runs each ActTick: the
        WALL cap and a gone actor fire in a pause; the END + 6 s rides battle time, which a pause does not advance)."""
        linked = ctx.get("linked") or (lambda u: True)
        for r in list(self.running):
            if not paused:
                r.frames += 1
                if r.frames == self.HIT_FRAME:
                    for t in r.targets:
                        self._hit(r, t)
                if r.frames == self.HIT_FRAME + self.FIGURE_FRAMES and self.with_hold:
                    self.hold.figure_point(r)    # [ff9mapkit netsync s135] the sequence's Figure point: the hit's figures
                if r.frames >= self.REPLAY_FRAMES:
                    self._finish_ended(r)
                    continue
            why = act_abort_why(r.actor is None or not linked(r.actor), r.host_ended, r.host_end_ms, self.now_ms,
                                int(ctx.get("wall_ms", 0)) - r.launch_wall)
            if why is not None:
                self._abort(r, why, ctx)

    def _finish_ended(self, r: ActRec) -> None:
        r.state, r.end_ms = ACT_ST_ENDED, self.now_ms
        self.ended += 1
        if r in self.running:
            self.running.remove(r)
        if self.with_hold:                       # [ff9mapkit netsync s135] what it never hit: the legacy path, now
            self.hold.release_rec(r, "end")
        if self.with_trance:                     # [ff9mapkit netsync s137] a SysTrans burst is over: its end mark, the colour
            self.trance.on_replay_over(r, None, self.ctx_last)

    def _units_of(self, r: ActRec) -> int:
        """ActUnitsOf: the btl_ids a replay acts with -- its actor and its mapped targets (the stand-in: no reflect, no magic
        caster)."""
        m = int(r.actor.get("id", 0)) if getattr(r, "actor", None) is not None else 0
        for t in getattr(r, "targets", None) or ():
            m |= int(t.get("id", 0))
        return m

    def _abort(self, r: ActRec, why: str, ctx: dict) -> None:
        units = self._units_of(r)
        if not ctx.get("end_injected"):
            self.window_abort_mask |= units      # [ff9mapkit netsync s136] [fix pass 2: rtiming-1] (s134's mask, modelled)
        self.fallback.post_abort_mask &= ~units  # [ff9mapkit netsync s136] [fix pass 2: rtiming-1] a clip before THIS abort
        r.state, r.why, r.end_ms = ACT_ST_ABORTED, why, self.now_ms
        if r in self.running:
            self.running.remove(r)
        if self.with_hold:                       # [ff9mapkit netsync s135] its hit will never come: the legacy path, now
            self.hold.release_rec(r, "abort")
        if self.with_trance:                     # [ff9mapkit netsync s137] a SysTrans burst cut: its end mark, the colour
            self.trance.on_replay_over(r, why, ctx)
        self.aborted += 1
        self.abort_why = why
        if why in self.aborts_by:
            self.aborts_by[why] += 1
        if why == "fault":
            self.faulted += 1
        self.window_aborted = True
        if self.abort_logged >= ACT_ABORT_LOG_MAX:
            return
        self.abort_logged += 1
        injected = bool(ctx.get("end_injected"))
        self._log(f"{LOG_REPLAY_ABORTED}{r.id} slot {r.actor_slot} cmd {r.cmd_no} ({why}) after "
                  + (f"{self.now_ms - r.launch_ms} ms of battle time" if r.launch_ms >= 0 else "no launch")
                  + f", {r.hits} hit(s) -- a hard release"
                  + (" (the end presentation owns the units: no per-unit restore)" if injected else
                     " plus the busy-window restore")
                  + ("; further aborts this boot are counted, not logged" if self.abort_logged == ACT_ABORT_LOG_MAX
                     else ""))

    def abort_all(self, why: str, *, booted: bool = True, ctx: dict | None = None) -> None:
        """ActAbortAll: every running replay hard-released, every parked START declined ``why``; the window closes.
        [ff9mapkit netsync s136] [fix pass: timing-1] :attr:`aborting_all` holds while it runs (fallback A plays no clip for
        the frames its releases unblock)."""
        was = self.aborting_all
        self.aborting_all = True
        try:
            if not booted:
                return
            ctx = ctx or {}
            for r in list(self.running):
                self._abort(r, why, ctx)
            for r in list(self.book.queue):
                if r.pending:
                    self.dropped += 1
                    self._decline(r, why, f"dropped by {why} before it launched")
            self._window_check(ctx)
        finally:
            self.aborting_all = was

    def discard_all(self, why: str) -> None:
        """ActDiscardAll (ForceDisarm; `actbench teardown`): every record dropped, NOTHING applied or restored -- counted
        apart (`discarded`: neither started / declined nor aborted); the summary line; then the state's per-boot reset (the
        counters stay). [ff9mapkit netsync s135] Its first statement is ActHoldDiscardAll: the life mask cleared FIRST, every
        held / queued frame dropped (`act.guest.hold.discarded`), nothing applied."""
        self.hold.discard_all(why)
        running = len(self.running)
        queued = sum(1 for r in self.book.queue if r.pending)
        for r in self.running:
            r.state, r.why = ACT_ST_ABORTED, why
        self.discarded_pending += queued
        self.discarded_running += running
        if running or queued or self.inbox:
            self._log(f"{LOG_REPLAY_DISCARD}{why}) -- {running} running replay(s) dropped ({running} released from the "
                      f"sequencer), {queued} parked START(s) and {len(self.inbox)} inbox frame(s) dropped; nothing applied, "
                      "nothing restored")
        if self.starts_rx or self.old_host or self.calc_while_booted:
            self._log(f"{LOG_REPLAY_SUMMARY}{why}) -- {self.starts_rx} START(s) received, {self.started} started, "
                      f"{self.declined} declined ({self.stale} stale, {self.backlog} backlog, {self.noop} noop, "
                      f"{self.superseded} superseded), {self.ended} ended, {self.aborted} aborted ({self.faulted} faulted), "
                      f"{self.hits} hit(s), {self.swing_skipped} swing(s) skipped; calc_while_booted="
                      f"{self.calc_while_booted}" + ("; the host predates action replay" if self.old_host else ""))
        self.fallback.drop_deferred()            # [ff9mapkit netsync s136] [fix pass: cover-2] still waiting: `guarded`
        self.fallback.log_summary(why)           # [ff9mapkit netsync s136] fallback A's line (only when it did anything)
        if self.with_trance:                     # [ff9mapkit netsync s137] a pending deferral: `dropped`, nothing applied
            self.trance.discard_all(why)
        self.reset_for_boot(False)

    def _window_open(self) -> None:
        self.window_open, self.window_aborted, self.window_row_mask = True, False, 0
        self.window_abort_mask = 0               # [ff9mapkit netsync s136] [fix pass 2: rtiming-1]
        self.fallback.post_abort_mask = 0

    def _window_check(self, ctx: dict) -> None:
        if not self.window_open or self.running:
            return
        self.window_open = False
        aborted_units, self.window_abort_mask = self.window_abort_mask, 0          # [fix pass 2: rtiming-1]
        post_abort, self.fallback.post_abort_mask = self.fallback.post_abort_mask, 0
        scope = act_restore_scope(self.window_aborted, bool(ctx.get("end_injected")))
        self.window_aborted = False
        if scope == ACT_RESTORE_NONE:
            return
        limited = scope == ACT_RESTORE_LIMITED
        if not limited and self.with_fallback:
            self.fallback.restore_cut(aborted_units, post_abort)   # [ff9mapkit netsync s136] the clip half of ActRestoreUnit
        units = 0 if limited else len(ctx.get("units") or [])
        if limited:
            self.restores_limited += 1
        else:
            self.restores += 1
        self._log(LOG_REPLAY_WINDOW + (
            "the shared lanes released only (bbg intensity, the world shift, the camera; the end presentation owns the units)"
            if limited else f"{units} unit(s) restored (rot, scale, meshes, weapons, row, base_pos, pos = base_pos, the default "
                            "idle) and the shared lanes released (the cursor bit too)"))

    # -- the tick (ActTick)
    def tick(self, ctx: dict) -> None:
        """ActTick: ``ctx`` = {booted, role, steady, paused, now_ms (the caller's clock), wall_ms, end_injected, r8_hits,
        end_presented, leaving, hidden_mask, resolve, linked, units}."""
        if not ctx.get("booted"):
            return
        paused = bool(ctx.get("paused"))
        self.clock(int(ctx.get("now_ms", 0)), paused)
        self.ctx_last = ctx
        for slot in list(self.swings):
            self.swings[slot] -= 1
            if self.swings[slot] <= 0:
                del self.swings[slot]
        self.hold.age_flinches()                 # [ff9mapkit netsync s135] (the stand-in's flinch shapes)
        self.fallback.age()                      # [ff9mapkit netsync s136] (the stand-in's clip shapes)
        if ctx.get("end_injected") and self.end_inject_ms < 0:
            self.end_inject_ms = self.now_ms
        live = bool(self.running) or bool(self.book.queue)
        if live and int(ctx.get("r8_hits", 0)) > 0:
            self.abort_all("r8", ctx=ctx)
        elif live and ctx.get("end_injected") and self.now_ms - self.end_inject_ms > ACT_W3_MS:
            self.abort_all("w3", ctx=ctx)
        self._check_running(ctx, paused)         # (the stand-in's sequencer stops while BattleMain is paused; aborts do not)
        self._window_check(ctx)
        self._decide_queue(ctx, paused)
        self._window_check(ctx)
        if self.with_fallback:
            self.fallback.deferred_tick(ctx)     # [ff9mapkit netsync s136] [fix pass: cover-2] ActFallbackDeferredTick
        if self.with_hold:
            self.hold.tick(ctx)                  # [ff9mapkit netsync s135] ActHoldTick (PHASE_NORMAL only)
        if self.with_trance:
            self.trance.tick(ctx)                # [ff9mapkit netsync s137] ActTranceTick, last (both branches, every frame)

    # -- the published block and the units' observables
    def acting_record(self, unit: dict) -> ActRec | None:
        return next((r for r in self.running if r.actor is unit), None)

    def unit_doc(self, unit: dict) -> dict:
        """`battle.units[]`'s s134 keys for one stand-in unit (see the class docstring: shapes, not engine clips)."""
        r = self.acting_record(unit)
        slot = int(unit.get("slot", -1))
        player = bool(unit.get("player"))
        away = 0.0
        if r is not None and player and r.cmd_no == CMD_ATTACK_ID:
            k = r.frames
            away = self.AWAY_PEAK * (k / self.HIT_FRAME if k <= self.HIT_FRAME else
                                     max(0.0, (self.REPLAY_FRAMES - k) / (self.REPLAY_FRAMES - self.HIT_FRAME)))
        dead = not unit.get("alive", True)
        clip = self.fallback.clip_on.get(slot) if r is None and not dead else None   # [ff9mapkit netsync s136]
        return {"anim": f"ACT_{r.vfx_kind}_{r.vfx_num}" if r is not None else (
                    clip["clip"] if clip is not None else "DISABLE" if dead else "IDLE"),
                "anim_frame": r.frames if r is not None else 0, "away": float(round(away, 3)),
                "rot_y": 0.0 if player else 180.0, "acting": r is not None, "die_seq": 5 if dead else 0,
                "row": self.rows.get(slot, 1) if player else 0,
                # [ff9mapkit netsync s137] `trance_model`, after `row` (an s136 lane publishes none): the worn model
                **({"trance_model": self.trance.wears(unit)} if self.with_trance else {})}

    def last_doc(self) -> dict | None:
        r = self.last
        if r is None:
            return None
        return {"id": r.id, "actor": r.actor_slot, "cmd": r.cmd_no, "sub": r.sub_no, "kind": r.vfx_kind, "num": r.vfx_num,
                "speed": r.host_speed, "state": ACT_STATE_NAMES.get(r.state, "?"), "why": r.why, "arrive_ms": r.arrive_ms,
                "launch_ms": r.launch_ms, "first_hit_ms": r.first_hit_ms, "end_ms": r.end_ms, "hits": r.hits}

    def doc(self, *, role: bool, booted: bool) -> dict:
        """HarnessAgent.AppendActGuest -- published in EVERY role (audit 3.6)."""
        return {"on": self.can_replay(role), "why": self.why_not(role), "rework": self.rework_on(role),
                "knob": 1 if self.knob_on(role) else 0, "host_caps": self.host_caps, "bit5": self.bit5,
                "levers": {"replay_off": self.bench_replay_off, "rework_off": self.bench_rework_off,
                           "shortcircuit_off": self.bench_short_off, "knob": self.bench_knob},
                "inbox": len(self.inbox), "starts_rx": self.starts_rx, "ends_rx": self.ends_rx, "started": self.started,
                "queued": sum(1 for r in self.book.queue if r.state == ACT_ST_REGISTERED),
                "waiting": sum(1 for r in self.book.queue if r.state == ACT_ST_WAITING), "running": len(self.running),
                "declined": self.declined, "declined_why": self.declined_why, "stale": self.stale,
                "backlog": self.backlog, "superseded": self.superseded, "noop": self.noop, "dropped": self.dropped,
                "aborted": self.aborted, "abort_why": self.abort_why,
                "aborts": {k: self.aborts_by[r] for k, r in zip(ACT_ABORTS_KEYS, ACT_ABORT_REASONS)},
                "discarded": {"pending": self.discarded_pending, "running": self.discarded_running}, "ended": self.ended, "faulted": self.faulted, "hits": self.hits,
                "credits": self.credits, "paired": self.paired, "swing_skipped": self.swing_skipped,
                "calc_while_booted": self.calc_while_booted, "var_refused": self.var_refused, "old_host": self.old_host,
                "grace": {"armed": self.grace_armed, "mask": self.grace_mask}, "hold_through": self.hold_through,
                "end_held": self.end_held, "rx_dropped": self.rx_dropped, "battle_ms": self.now_ms if booted else -1,
                "paused_ms": self.paused_ms,
                "window": {"open": self.window_open, "restores": self.restores, "limited": self.restores_limited},
                "last": self.last_doc(),
                # [ff9mapkit netsync s135] AppendActGuestHold, after `last` (an s134 lane publishes none)
                **({"hold": self.hold.doc(role=role)} if self.with_hold else {}),
                # [ff9mapkit netsync s136] AppendActGuestFallback, after `hold` (an s135 lane publishes none)
                **({"fallback": self.fallback.doc(role=role)} if self.with_fallback else {}),
                # [ff9mapkit netsync s137] AppendActGuestTrance, the LAST key (an s136 lane publishes none)
                **({"trance": self.trance.doc(role=role, booted=booted)} if self.with_trance else {})}


def _cs_int(text) -> int | None:
    """Int32.TryParse's integer (an optional sign, digits) -> int, None when it would refuse."""
    s = str(text).strip()
    if not re.fullmatch(r"[+-]?\d+", s):
        return None
    v = int(s)
    return v if -(1 << 31) <= v < (1 << 31) else None


def act_guest_invariant(block: dict | None) -> bool:
    """The `act.guest` book's identity: every START received is started, declined, queued, waiting -- or dropped by a
    teardown's ActDiscardAll (starts_rx == started + declined + queued + waiting + discarded.pending) -- False for an absent
    block."""
    if not isinstance(block, dict):
        return False
    try:
        disc = block.get("discarded")
        pend = int(disc["pending"]) if isinstance(disc, dict) else 0
        return int(block["starts_rx"]) == (int(block["started"]) + int(block["declined"]) + int(block["queued"])
                                           + int(block["waiting"]) + pend)
    except (KeyError, TypeError, ValueError):
        return False


def act_guest_ends_balance(block: dict | None) -> bool:
    """The `act.guest` runs' identity AT REST (running 0): every launched replay ended, was aborted, or was dropped by a
    teardown (ended + aborted + discarded.running == started) -- False for an absent block or one still running."""
    if not isinstance(block, dict):
        return False
    try:
        disc = block.get("discarded")
        run = int(disc["running"]) if isinstance(disc, dict) else 0
        return int(block["running"]) == 0 and int(block["ended"]) + int(block["aborted"]) + run == int(block["started"])
    except (KeyError, TypeError, ValueError):
        return False


#: NetSyncDiorama.Replay.cs's integer constants, by C# name (the pin, both ways -- test_harness_netsync.py reads every
#: `internal const` the s134 file declares, comments stripped). The selftest's private ActTestNonce is ACT_REPLAY_TEST_NONCE.
CS_REPLAY_CONSTANTS = {
    "ActMaxRunning": ACT_MAX_RUNNING, "ActPendingAbortMs": ACT_PENDING_ABORT_MS, "ActDeathGraceMs": ACT_DEATH_GRACE_MS,
    "ActHostEndAbortMs": ACT_HOST_END_ABORT_MS, "ActWallCapMs": ACT_WALL_CAP_MS, "ActW3Ms": ACT_W3_MS,
    "ActWaitMaxMs": ACT_WAIT_MAX_MS, "ActInboxCap": ACT_INBOX_CAP, "ActBookCap": ACT_BOOK_CAP,
    "ActStartLogMax": ACT_START_LOG_MAX, "ActAbortLogMax": ACT_ABORT_LOG_MAX,
    "ActStRegistered": ACT_ST_REGISTERED, "ActStWaiting": ACT_ST_WAITING, "ActStRunning": ACT_ST_RUNNING,
    "ActStEnded": ACT_ST_ENDED, "ActStDeclined": ACT_ST_DECLINED, "ActStAborted": ACT_ST_ABORTED, "ActStNoop": ACT_ST_NOOP,
    "ActGo": ACT_GO, "ActNoop": ACT_NOOP, "ActWhyKnob": ACT_WHY_KNOB, "ActWhyLever": ACT_WHY_LEVER,
    "ActWhyRework": ACT_WHY_REWORK, "ActWhyEnd": ACT_WHY_END, "ActWhyStale": ACT_WHY_STALE,
    "ActWhyBacklog": ACT_WHY_BACKLOG, "ActWhyActor": ACT_WHY_ACTOR, "ActWhyHidden": ACT_WHY_HIDDEN,
    "ActWhyDead": ACT_WHY_DEAD, "ActWhyKind": ACT_WHY_KIND, "ActWhyTransform": ACT_WHY_TRANSFORM,
    "ActWhyTarget": ACT_WHY_TARGET, "ActWhyBusy": ACT_WHY_BUSY, "ActWhyLeave": ACT_WHY_LEAVE,
    "ActEndNoHold": ACT_END_NO_HOLD, "ActEndHold": ACT_END_HOLD, "ActEndAbortThenInject": ACT_END_ABORT_THEN_INJECT,
    "ActRestoreNone": ACT_RESTORE_NONE, "ActRestoreFull": ACT_RESTORE_FULL, "ActRestoreLimited": ACT_RESTORE_LIMITED,
    "ActSfxKeep": ACT_SFX_KEEP, "ActSfxCancel": ACT_SFX_CANCEL, "ActSfxUnlock": ACT_SFX_UNLOCK}


# ======================================================================================== [ff9mapkit netsync s135]
# THE REPLAY HIT HOLD (studies/battle-coop/R3-DESIGN.md 3.3.4 as amended by R3-ACTION-REPLAY-AUDIT.md 2.3 -- amendments 1-15,
# decisions D01-D12 -- and section 3; the audit's "s124": group 2 was renumbered s133-s141). Numbers, the flinch and deaths
# on the guest wait for the action replay's OWN hit instead of landing when the host's impact frame ARRIVES (the owner's
# rule, 2026-10-13: the numbers wait for the replay's hit; the HP and MP bars still follow the host). THE CONTAINMENT LAW
# holds: the hold only DELAYS applying the host's own values. Everything below is the C# twin of a PURE rule of
# NetSyncDiorama.Replay.cs's hold (each method of the same name, its parameters in its order); test_harness_netsync.py
# EVALUATES ActHoldSelfTest's own 28 rows against them (read off the stack, in order) and pins the constants by name both
# ways (CS_HOLD_CONSTANTS). :class:`ActHoldLane` is the stand-in's model of the hold with its statics (its docstring says
# what it models and what it cannot).
ACT_HOLD_TIMEOUT_MS = 2500                # a held impact never waits longer than this (battle ms from its arrival)
ACT_HOLD_HOST_DONE_MS = 1500              # ...nor longer than this after its host's END (keyed on the action id)
ACT_HOLD_CAP = 64                         # held + queued at most: past it a frame takes the arrival path (never dropped)
ACT_HOLD_LOG_MAX = 48                     # release lines per boot (then one "further releases" line, then counted)
ACT_HOLD_FIGS_MAX = 16                    # figs[]: the last displays
ACT_HOLD_LAG_CAP = 512                    # lag samples kept per boot for the median (n counts on past it)
ACT_HOLD_CREDIT_CAP = 32                  # credits kept per replay
ACT_HOLD_APPLY, ACT_HOLD_HOLD, ACT_HOLD_LATE, ACT_HOLD_QUEUE = 0, 1, 2, 3   # ActHoldVerdict's answers
ACT_FIG_NONE, ACT_FIG_BRACKET, ACT_FIG_DIRECT = 0, 1, 2                    # ActHitFigPath's answers
ACT_VIA_ARRIVAL = "arrival"               # ActViaArrival: the arrival path's figs[] reason
#: ActHoldVias: every release reason of a HELD impact, in `act.guest.hold.rel_*` order
ACT_HOLD_VIAS = ("hit", "late", "end", "hostdone", "timeout", "abort", "replaced", "declined", "end-inject")
#: `act.guest.hold`'s per-reason keys (`rel_<via>`, `-` as `_`), in AppendActGuestHold's order
ACT_HOLD_REL_KEYS = tuple("rel_" + v.replace("-", "_") for v in ACT_HOLD_VIAS)
#: every `figs[].via` the engine writes: the arrival path, a held impact's nine reasons, a queued frame's release
ACT_FIG_VIAS = (ACT_VIA_ARRIVAL,) + ACT_HOLD_VIAS + ("queued",)
#: the releases that PAIR (their lag is kept: hit_ms - arrival_ms, negative for a credit)
ACT_HOLD_PAIRED_VIAS = ("hit", "late")
INT32_MIN = -(1 << 31)                    # Int32.MinValue: ActHeld.CreditMs's "none", ActHoldLog's "no lag"
PROOF_HOLD = "action hold selftest: "     # NetSyncDiorama.ActHoldSelfTest (s135), logged right after PROOF_REPLAY
HOLD_SELFTEST_ROWS = 28                   # 6 verdict + 3 lane / guard / revive + 1 clock + 3 queue / masks / skip + 3 release
#                                           + 4 figure / flinch / value / lag + 3 pick / credits -- and the fix pass's 5: a
#                                           queued lane's release, the deferred drain, the catch-up, a cut replay's pending
#                                           figure, the release's grace
#: `actbench <op>` -- the replay hit hold's ops (HarnessActHoldBench, routed through the guest bench: IsActGuestBenchOp)
ACT_HOLD_BENCH_OPS = ("hold", "lifeskip", "unit")
#: `actbench unit <slot 0-7> <state>`'s states
ACT_HOLD_UNIT_STATES = ("dead", "alive", "trance0", "trance1")
#: `act.guest.hold.lag` and one `figs[]` entry, in AppendActGuestHold's order
ACT_HOLD_LAG_KEYS = ("n", "min", "p50", "max")
ACT_HOLD_FIG_KEYS = ("slot", "value", "via", "arrival_ms", "release_ms")
#: `netsync.battle.act.guest.hold` at AppendNetsync's catch-line sentinels, in AppendActGuestHold's order -- the LAST key of
#: `act.guest`. The live block differs at rest only where the agent reads a static: `on` / `lifeskip` (true with no lever).
ACT_GUEST_HOLD_SENTINELS = {
    "on": False, "lifeskip": False, "held_now": 0, "held": 0, "queued_now": 0, "queued": 0,
    **dict.fromkeys(ACT_HOLD_REL_KEYS, 0),
    "rel_queued": 0, "superseded": 0, "discarded": 0, "life_mask": 0, "mask_skips": 0,
    "lag": {"n": 0, "min": -1, "p50": -1, "max": -1}, "figs": [],
}
ACT_GUEST_SENTINELS["hold"] = ACT_GUEST_HOLD_SENTINELS      # (after `last`: s135's key, the last of act.guest)
#: the engine's words (each a C# literal of the stack, or its head)
LOG_HOLD = "[NetSync] action replay hold: "
LOG_HOLD_FIRST_HELD = "[NetSync] action replay hold: an impact HELD for its replay's hit"
LOG_HOLD_FIRST_QUEUED = "[NetSync] action replay hold: a frame QUEUED behind a held life change"
LOG_HOLD_FIRST_TAIL = (" -- numbers, the flinch and deaths wait for the replay's own hit; the bars follow the host (logged "
                       "once per boot)")
LOG_HOLD_HELD_IMPACT = "[NetSync] action replay hold: held impact"
LOG_HOLD_QUEUED_FRAME = "[NetSync] action replay hold: queued frame"
LOG_HOLD_RELEASED_VIA = " released via "
LOG_HOLD_HIT_FIRST = ": the replay's hit came first"
LOG_HOLD_SUPERSEDED = " -- its life change SUPERSEDED by a newer frame (the figure and the flinch only)"
LOG_HOLD_FURTHER = "[NetSync] action replay hold: further releases this boot are counted, not logged (act.guest.hold)"
#: [fix pass: rtiming-1] ActHoldLog's per-release line, parsed anywhere in a log line (Memoria.log's prefix kept): "<held
#: impact|queued frame>[ of id N] on wire slot S released via V after M ms of battle time[ (lag L ms...)][<superseded>]"
_HOLD_RELEASE_RX = re.compile(
    "(" + re.escape(LOG_HOLD_HELD_IMPACT) + "|" + re.escape(LOG_HOLD_QUEUED_FRAME) + r")(?: of id (\d+))? on wire slot (\d+)"
    + re.escape(LOG_HOLD_RELEASED_VIA) + r"([a-z-]+) after (-?\d+) ms of battle time(?: \(lag (-?\d+) ms)?")


def parse_hold_release(line: str) -> dict | None:
    """One ActHoldLog release line -> {queued, id (None for a frame naming no record), slot (the TARGET's wire slot),
    via, held_ms (battle time from its arrival), lag (None unless a paired release), superseded}; None for any other
    line. The line is written at the RELEASE whether or not its figure showed (btl2d drops a figure on a unit the
    replay's own sequence hid), so a timer release is judged on it, never on figs[] (fix pass: rtiming-1)."""
    m = _HOLD_RELEASE_RX.search(line or "")
    if m is None:
        return None
    return {"queued": m.group(1) == LOG_HOLD_QUEUED_FRAME, "id": int(m.group(2)) if m.group(2) else None,
            "slot": int(m.group(3)), "via": m.group(4), "held_ms": int(m.group(5)),
            "lag": int(m.group(6)) if m.group(6) else None, "superseded": LOG_HOLD_SUPERSEDED in line}


LOG_HOLD_MASK_SKIP = "[NetSync] action replay hold: the reconciler skips wire slot "
#: [fix pass: life-2] the catch-up's once-per-boot line: "<head><slot><piece><seq>) re-applied at <why><tail>"
LOG_HOLD_CATCH_UP = "[NetSync] action replay hold: wire slot "
LOG_HOLD_CATCH_UP_PIECE = "'s skipped record (seq "
LOG_HOLD_CATCH_UP_TAIL = " -- the reconciler's sample the life mask kept off it lands now (logged once per boot)"
LOG_HOLD_FLUSH = "[NetSync] action replay hold: the end injection released "
LOG_HOLD_FLUSH_TAIL = (" queued frame(s) at once (the legacy path: every kill lands before the end presentation reads the "
                       "party; logged once per boot)")
LOG_HOLD_DISCARDED = " held / queued frame(s) DISCARDED ("
LOG_HOLD_FAULTED = ("[NetSync] action replay hold faulted (logged once per boot; the frame or release in hand fell back as "
                    "best it could): ")
LOG_HOLD_OFF = ("[NetSync] harness: action replay hold OFF -- CALIBRATION: the pre-s135 guest (numbers, the flinch and deaths "
                "land when the host's impact ARRIVES)")
LOG_HOLD_ON = "[NetSync] harness: action replay hold ON"
LOG_LIFESKIP_OFF = ("[NetSync] harness: action replay life-mask skip OFF -- CALIBRATION: the reconciler applies a held slot's "
                    "sample (a dead one kills before the replay's hit)")
LOG_LIFESKIP_ON = "[NetSync] harness: action replay life-mask skip ON"
LOG_HOLD_UNIT = "[NetSync] harness: action replay bench -- a type-1 record for wire slot "
LOG_HOLD_UNIT_SKIPPED = "met the life mask: SKIPPED (its kill or revive waits for the replay's hit)"
LOG_HOLD_UNIT_APPLIED = "went through the reconciler's ApplyUnit"
LOG_HOLD_LEVERS_BACK = ("[NetSync] harness: action replay hold levers back (the hold ON, the life-mask skip ON; released with "
                        "the harness)")
#: the hold's refusals (HarnessActHoldBench; `hold` / `lifeskip` splice their op: "netsync actbench <op>: expected `<op>
#: on|off`")
HOLD_UNIT_USAGE = "netsync actbench unit: expected `unit <slot 0-7> dead|alive|trance0|trance1`"
HOLD_UNIT_STEADY = ("netsync actbench unit: needs a booted battle diorama in its steady state (PHASE_NORMAL, the units "
                    "latched)")
HOLD_UNIT_NO_UNIT = "netsync actbench unit: wire slot "      # + slot + " has no local unit"


def _i16(v: int) -> int:
    """C#'s (Int16) cast of an int: the low 16 bits, signed."""
    v = int(v) & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


# ---- the pure rules (each NetSyncDiorama's method of the same name, its parameters in its order)
def act_hold_verdict(hold_on: bool, stat_tick: bool, paired_state: int, target_resolved: bool, credit: bool, masked: bool,
                     room: bool) -> int:
    """NetSyncDiorama.ActHoldVerdict -- THE ARRIVAL VERDICT. ``hold_on`` false = the pre-s135 arrival path. A frame PAIRS
    when it is not a stat tick, its target resolved, and its record is queued / waiting / running -- or ended with a credit
    for that target. A pairing frame without a credit is HELD (a full list applies it now); with a credit it releases LATE
    -- unless a slot it touches is busy (masked): then it QUEUES behind the older change, as does every other frame on a
    busy slot (a full list applies it now). Anything else applies now."""
    if not hold_on:
        return ACT_HOLD_APPLY
    live = paired_state in (ACT_ST_REGISTERED, ACT_ST_WAITING, ACT_ST_RUNNING)
    pairs = not stat_tick and bool(target_resolved) and (live or (paired_state == ACT_ST_ENDED and bool(credit)))
    if pairs and not credit:
        return ACT_HOLD_HOLD if room else ACT_HOLD_APPLY
    if masked:
        return ACT_HOLD_QUEUE if room else ACT_HOLD_APPLY
    return ACT_HOLD_LATE if pairs else ACT_HOLD_APPLY


def act_lane_is_life(lethal: bool, dead_now: bool, slot_busy: bool) -> bool:
    """NetSyncDiorama.ActLaneIsLife: a held lane's state waits for the release when it is a LIFE change -- lethal (raw wire
    HP 0), a unit dead here now (its revive is decided at release, amendment 11), or a slot an older frame still holds."""
    return bool(lethal or dead_now or slot_busy)


def act_held_applies(seq: int, seen: bool, stamp: int) -> bool:
    """NetSyncDiorama.ActHeldApplies -- THE SUPERSEDED GUARD: a deferred lane's state applies only if no NEWER frame already
    applied that slot -- ``(Int16)(seq - stamp) > 0`` (UInt16 operands: wrap-safe); a slot nothing stamped this boot always
    applies."""
    return not seen or _i16((int(seq) & 0xFFFF) - (int(stamp) & 0xFFFF)) > 0


def act_deferred_applies(deferred: bool, revive: bool, life_at_queue: bool, seq: int, seen: bool, stamp: int) -> bool:
    """NetSyncDiorama.ActDeferredApplies (the s135 fix pass: life-1, timing-2) -- a lane's state in ApplyActionFrameNow: an
    arrival or a late release always applies; a DEFERRED (queued) frame's lane only if no newer state applied that slot
    (the superseded guard -- the reconciler's samples stamp too) and never a REVIVE through a lane that was not a life
    lane when the frame queued."""
    if not deferred:
        return True
    if revive and not life_at_queue:
        return False
    return act_held_applies(seq, seen, stamp)


def act_catch_up_slots(skipped: int, mask: int) -> int:
    """NetSyncDiorama.ActCatchUpSlots (fix pass: life-2): the skipped records due for their catch-up -- every cached slot
    that has left the life mask."""
    return int(skipped) & ~int(mask)


def act_drains_at_hit(bracket: bool) -> bool:
    """NetSyncDiorama.ActDrainsAtHit (fix pass: stock-1): a hit release drains the queue at once only OUTSIDE EffectPoint's
    bracket; inside it the drain waits for the next ActHoldTick."""
    return not bracket


def act_shows_pending_at(via: str) -> bool:
    """NetSyncDiorama.ActShowsPendingAt (fix pass: timing-1): a hit figure its Figure point has not shown yet is shown at
    once when its replay is released ``via`` -- any cut, never a natural `end`."""
    return via != "end"


def act_release_arms_grace(lethal: bool, caster_is_player: bool, target_is_player: bool, backlog: bool, via: str,
                           no_replay: bool) -> bool:
    """NetSyncDiorama.ActReleaseArmsGrace (fix pass: timing-4): a released kill arms the death-attack grace -- a PLAYER
    caster's lethal blow on an enemy, not a backlog frame, and only while an EnemyDying replay can still follow (never at
    `end-inject`, never once the end is presented or a Leave is in flight)."""
    return bool(lethal) and bool(caster_is_player) and not target_is_player and not backlog and via != "end-inject" \
        and not no_replay


def act_revive_at_release(lethal: bool, dead_now: bool) -> bool:
    """NetSyncDiorama.ActReviveAtRelease (amendment 11, D11): not lethal, and the unit dead here NOW."""
    return not lethal and bool(dead_now)


def act_held_timer_why(host_ended: bool, host_end_ms: int, arrive_ms: int, now_ms: int) -> str | None:
    """NetSyncDiorama.ActHeldTimerWhy: `hostdone` once its host's END is ACT_HOLD_HOST_DONE_MS old, `timeout` once its own
    arrival is ACT_HOLD_TIMEOUT_MS old (battle ms; host-done first when both); None = it waits on."""
    if host_ended and now_ms - host_end_ms >= ACT_HOLD_HOST_DONE_MS:
        return "hostdone"
    if now_ms - arrive_ms >= ACT_HOLD_TIMEOUT_MS:
        return "timeout"
    return None


def act_queue_blocked(slots: int, older_held_life: int, older_queued: int) -> bool:
    """NetSyncDiorama.ActQueueBlocked: a queued frame stays queued while an OLDER held frame's life lane, or an older
    queued frame, touches one of its slots (FIFO per slot)."""
    return (int(slots) & (int(older_held_life) | int(older_queued))) != 0


def act_life_skips(mask: int, index: int, skip_on: bool) -> bool:
    """NetSyncDiorama.ActLifeSkips: ApplyUnit's skip -- the slot is in the life mask and the skip is in force (the
    `lifeskip off` lever is its calibration red)."""
    return bool(skip_on) and 0 <= int(index) < 8 and (int(mask) & (1 << int(index))) != 0


def act_decline_via(why: str) -> str:
    """NetSyncDiorama.ActDeclineVia: which release a decline of a pending START gives its held impacts -- `replaced` for a
    newer START that took its pending slot (amendment 9), `abort` for an abort-all's drop (r8, w3, leave, clear), else
    `declined`."""
    if why == "superseded":
        return "replaced"
    if why in ("r8", "w3", "leave", "clear"):
        return "abort"
    return "declined"


def act_end_inject_flushes(ours: bool, kind: int) -> bool:
    """NetSyncDiorama.ActEndInjectFlushes -- EndTick's release trigger (amendment 2, D02): THIS boot's battle shows an END
    kind (NetSyncEnd.IsEndKind)."""
    return bool(ours) and is_end_kind(kind)


def act_hit_fig_path(hidden: bool, bracket: bool) -> int:
    """NetSyncDiorama.ActHitFigPath: none for a unit hidden here (amendment 3); inside EffectPoint's bracket the fig write (a
    hit through the sequencer's own call, the short-circuit in force); else the direct Btl2dReq."""
    if hidden:
        return ACT_FIG_NONE
    return ACT_FIG_BRACKET if bracket else ACT_FIG_DIRECT


def act_release_flinches(dmg_mot: bool, lethal: bool, revive: bool, hidden: bool, can_play: bool) -> bool:
    """NetSyncDiorama.ActReleaseFlinches (F5): the host's DmgMot, not lethal, not a revive, not hidden, and a unit that may
    play a cosmetic motion."""
    return bool(dmg_mot) and not lethal and not revive and not hidden and bool(can_play)


def act_fig_value(hp: int, mp: int) -> int:
    """NetSyncDiorama.ActFigValue: figs[]' value -- the HP figure, else the MP one."""
    return int(hp) if int(hp) != 0 else int(mp)


def act_lag_p50(samples) -> int:
    """NetSyncDiorama.ActLagP50: the lag's LOWER median (``s[(n - 1) / 2]`` of the sorted samples); -1 for none."""
    if not samples:
        return -1
    s = sorted(int(x) for x in samples)
    return s[(len(s) - 1) // 2]


class ActHeld:
    """NetSyncDiorama.ActHeld -- one host frame the hold keeps: HELD for its replay's hit, or QUEUED behind an older held
    life change (the whole frame deferred). ``a`` is the parsed frame (:func:`decode_action`'s dict) -- the C# PeerAction."""

    def __init__(self, ord: int = 0, a: dict | None = None, rec=None, queued: bool = False,     # noqa: A002 (C#'s Ord)
                 life_t: bool = False, life_c: bool = False, self_cast: bool = False, covered: bool = False,
                 backlog: bool = False, unit_id: int = 0, slots: int = 0, life_slots: int = 0, arrive_ms: int = 0,
                 credit_ms: int = INT32_MIN):
        self.ord = int(ord)                      # arrival ordinal: one FIFO across the held and the queued
        self.a = a
        self.rec = rec                           # the replay it waits for (queued: the record it named, or None)
        self.queued = bool(queued)
        self.life_t, self.life_c = bool(life_t), bool(life_c)
        self.self_cast, self.covered, self.backlog = bool(self_cast), bool(covered), bool(backlog)
        self.unit_id = int(unit_id)              # the master target's btl_id: the hit key with ``rec`` (0 = none)
        self.slots, self.life_slots = int(slots), int(life_slots)
        self.arrive_ms = int(arrive_ms)
        self.credit_ms = int(credit_ms)          # a LATE frame queued behind a blocker: its credit's hit (INT32_MIN = none)


def act_busy_mask_of(held, queued) -> int:
    """NetSyncDiorama.ActBusyMaskOf: the intake's BUSY slots -- every held frame's LIFE lanes and every queued frame's slots
    (a held frame's non-life lanes already applied: they order nothing)."""
    m = 0
    for h in held:
        m |= int(h.life_slots)
    for q in queued:
        m |= int(q.slots)
    return m


def act_life_mask_of(held, queued) -> int:
    """NetSyncDiorama.ActLifeMaskOf -- THE LIFE MASK: the life lanes of every held and queued frame."""
    m = 0
    for h in held:
        m |= int(h.life_slots)
    for q in queued:
        m |= int(q.life_slots)
    return m


def act_pick_oldest(held, rec, unit_id: int) -> int:
    """NetSyncDiorama.ActPickOldest -- the hit's pick: the index of the OLDEST held (never queued) impact of ``rec`` (BY
    REFERENCE) on the master target ``unit_id``; -1 = none (the hit is a credit)."""
    best = -1
    for i, h in enumerate(held):
        if h.queued or h.rec is not rec or h.unit_id != int(unit_id):
            continue
        if best < 0 or h.ord < held[best].ord:
            best = i
    return best


def act_credit_add(r, unit_id: int, ms: int) -> None:
    """NetSyncDiorama.ActCreditAdd: a hit that released nothing adds a credit for that master target (at most
    ACT_HOLD_CREDIT_CAP per replay)."""
    if r.hold_credit_units is None:
        r.hold_credit_units, r.hold_credit_ms = [], []
    if len(r.hold_credit_units) >= ACT_HOLD_CREDIT_CAP:
        return
    r.hold_credit_units.append(int(unit_id))
    r.hold_credit_ms.append(int(ms))


def act_credit_find(r, unit_id: int) -> int:
    """NetSyncDiorama.ActCreditFind: the index of the OLDEST credit for that master target; -1 = none."""
    if r.hold_credit_units is None:
        return -1
    return r.hold_credit_units.index(int(unit_id)) if int(unit_id) in r.hold_credit_units else -1


def act_credit_take(r, index: int) -> int:
    """NetSyncDiorama.ActCreditTake: that credit removed; its hit ms returned (the late release's lag)."""
    ms = r.hold_credit_ms[index]
    del r.hold_credit_units[index]
    del r.hold_credit_ms[index]
    return ms


class ActHoldLane:
    """[ff9mapkit netsync s135] THE REPLAY HIT HOLD as NetSyncDiorama.Replay.cs runs it, with its statics -- the stand-in's
    model, owned by an :class:`ActGuestLane` (its battle clock, its log, its records). MODELLED, through the twins above:
    ApplyActionFrame's intake (ActHoldIntake: the verdict, the life lanes, the non-life lanes applied at arrival -- the bars
    follow the host --, the horizon gate stamped, the credit taken for a late frame), the arrival path (ApplyActionFrameNow:
    raw HP / MP, the kill and the revive, the figures into figs[] at the display, the flinch, the swing; deferred for a
    queued frame: the superseded guard per lane), the hit release (ActHoldOnHit: the oldest held impact of the replay on
    that target, its figures into the hit's pending list -- DISPLAYED at the replay's Figure point,
    ActGuestLane.FIGURE_FRAMES after the hit, only for a unit whose collected fig.info is non-zero: EffectPoint's own
    collect rule --, or a credit), the record releases (ActHoldReleaseRec: end / abort / replaced / declined), the timers
    (ActHoldTick: host-done, timeout -- only in the steady phase), the queue's FIFO drain, the end-inject flush
    (ActHoldFlush), the teardown's discard (ActHoldDiscardAll: the mask first), the per-boot reset, the levers
    (`hold|lifeskip on|off`, their role gate, ActBenchRelease's half), the bench's `unit <slot> <state>` through a model of
    the reconciler's ApplyUnit (the life-mask skip, the kill, the revive -- a dead enemy holds dead: the stand-in's dead
    enemies are fully faded --, trance), every counter, figs[], the lag and every Log.Message line -- and the s135 fix
    pass: the reconciler's stamp of THE SUPERSEDED GUARD (a record really applied), the skipped-record cache and its
    catch-up (a slot leaving the mask in the steady tick; the end-inject flush), a hit's drain deferred to the next tick,
    a cut replay's pending hit figure shown at once (never at a natural `end`), and a queued lane that was no life lane at
    queue time never reviving (ActDeferredApplies).
    NOT MODELLED: slave parts (the master is the target), the hidden mask (the stand-in hides nothing: ctx ``hidden_mask``
    0 -- the twin's rule is pinned by the selftest row), the death-attack grace at a release (no AttackOnDeath enemy), the
    crit shove, a fault (the 'hold faulted' line), the reconciler's other lanes (max HP/MP, hide, ATB: only a `unit` op
    reaches it) and the transport (ActionTick's drain: only the bench inbox feeds the intake)."""

    FLINCH_FRAMES = 12                           # (the stand-in's flinch: the unit's `mot` reads MP_DAMAGE1 this long)

    def __init__(self, lane) -> None:
        self.lane = lane
        self.bench_hold_off = False              # `hold off`: the pre-s135 guest (harness-scoped, never per boot)
        self.bench_lifeskip_off = False          # `lifeskip off`: ApplyUnit ignores the life mask
        self.clear()
        self.reset_counters()

    # -- the levers (their getters need the selftest role, as the engine's)
    def hold_on(self, role: bool) -> bool:
        """ActHoldOn / HarnessHoldOn."""
        return not (self.bench_hold_off and bool(role))

    def lifeskip_on(self, role: bool) -> bool:
        """ActLifeSkipOn / HarnessHoldLifeSkip."""
        return not (self.bench_lifeskip_off and bool(role))

    def release(self) -> None:
        """ActBenchRelease's s135 half: both levers back (one line when either was pulled)."""
        if self.bench_hold_off or self.bench_lifeskip_off:
            self._log(LOG_HOLD_LEVERS_BACK)
        self.bench_hold_off = self.bench_lifeskip_off = False

    # -- the per-boot state
    def clear(self) -> None:
        """ActHoldClear (the boot block): the mask FIRST, the applied seqs, the held, queued and pending-figure lists (and
        the stand-in's unit shapes of a boot)."""
        self.clear_seq()
        self.held: list = []
        self.queued: list = []
        self.fig_pending: list = []
        self.flinches: dict = {}
        self.trance: dict = {}

    def clear_seq(self) -> None:
        """ActHoldClearSeq (ForceDisarm's half): the life mask and every slot's applied seq -- and the stand-in's horizon
        gate seqs (the engine's _gateSeq, cleared at the same sites)."""
        self.life_mask = 0
        self.applied_seq = [0] * 8
        self.applied_seen = [False] * 8
        self.gate_seq = [0] * 8
        self.skipped: dict = {}                  # [fix pass: life-2] slot -> (state, seq): the latest record the mask skipped
        self.drain_due = False                   # [fix pass: stock-1] a hit's drain, deferred to the next tick
        #: [ff9mapkit netsync s137] (fix: timing-3) slot -> the battle ms its FIRST skipped record met the mask (the engine's
        #: _actSkippedSinceMs: written as the slot enters the cache, read only while it is in it)
        self.skipped_since: dict = {}
        self.catch_up_since = -1                 # [ff9mapkit netsync s137] ActHoldCatchUp's, around its ApplyUnit only
        #: [ff9mapkit netsync s137] (fix: rmodel-1) slot -> the skipped record's own InTrance (a lane rig's ``in_trance``;
        #: the engine caches the WHOLE PeerUnit record): re-applied with it at the catch-up
        self.skipped_trance: dict = {}

    def reset_counters(self) -> None:
        """ActHoldResetCounters (the boot block): the counters, figs[] and the lag -- kept after a teardown until the next
        boot."""
        self.ord = 0
        self.held_count = self.queued_count = self.rel_queued = self.superseded = self.discarded = self.mask_skips = 0
        self.rel_by = dict.fromkeys(ACT_HOLD_VIAS, 0)
        self.figs: list = []
        self.lag: list = []
        self.lag_n = self.lag_min = self.lag_max = 0
        self.logged = 0
        self.first_logged = self.mask_logged = self.flush_logged = self.catch_up_logged = False

    # -- helpers
    def _log(self, text: str) -> None:
        self.lane._log(text)

    @property
    def now(self) -> int:
        return self.lane.now_ms

    def _ctx(self, ctx: dict | None) -> dict:
        return ctx if ctx and ctx.get("resolve") else (self.lane.ctx_last or ctx or {})

    def _resolve(self, ctx: dict | None, index: int, is_player: bool):
        if index is None or index < 0 or index > 7:
            return None
        resolve = self._ctx(ctx).get("resolve")
        return resolve(index, is_player) if resolve else None

    @staticmethod
    def _dead(u) -> bool:
        return u is not None and not u.get("alive", True)

    @staticmethod
    def _can_play(u) -> bool:
        """CanPlayCosmeticMotion, as the stand-in models it: a living unit (no Petrify / Stop seated here)."""
        return u is not None and bool(u.get("alive", True))

    @staticmethod
    def _hidden(ctx: dict, slot: int, is_player: bool) -> bool:
        """ActHiddenNow: an ENEMY wire slot in the hidden mask (re-read at every release: amendment 3)."""
        return not is_player and 0 <= slot <= 7 and bool(int(ctx.get("hidden_mask", 0) or 0) & (1 << slot))

    def _disappeared(self, u, ctx: dict | None) -> bool:
        fn = self._ctx(ctx).get("disappeared")
        return bool(fn(u)) if callable(fn) else False

    def busy_mask(self) -> int:
        return act_busy_mask_of(self.held, self.queued)

    def recompute_mask(self) -> None:
        self.life_mask = act_life_mask_of(self.held, self.queued)

    def stamp(self, slot: int, seq: int) -> None:
        """ActStampApplied: THE SUPERSEDED GUARD's stamp (a frame's state applied to that wire slot)."""
        if 0 <= slot <= 7:
            self.applied_seq[slot] = int(seq) & 0xFFFF
            self.applied_seen[slot] = True

    def gate(self, slot: int, seq: int) -> None:
        """The horizon gate's stamp (_gated / _gateSeq): a type-1 sample older than this frame skips the slot."""
        if 0 <= slot <= 7:
            self.gate_seq[slot] = int(seq) & 0xFFFF

    def applies(self, slot: int, seq: int) -> bool:
        return act_held_applies(seq, self.applied_seen[slot], self.applied_seq[slot]) if 0 <= slot <= 7 else True

    def deferred_applies(self, deferred: bool, revive: bool, life_slots: int, slot: int, seq: int) -> bool:
        """ActDeferredApplies for one lane (``life_slots``: the queued frame's life lanes at queue time)."""
        if not 0 <= slot <= 7:
            return True
        return act_deferred_applies(deferred, revive, bool(int(life_slots) & (1 << slot)), seq, self.applied_seen[slot],
                                    self.applied_seq[slot])

    @staticmethod
    def apply_state(u: dict, slot: int, lethal: bool, revive: bool, hp_raw: int, mp_raw: int) -> None:
        """ApplyActionState, as the stand-in models it: raw HP / MP against raw max (the logical `hp` follows by the unit's
        own offset), the kill (lethal) or the revive."""
        offset = max(0, int(u.get("hp_max_raw", 0) or 0) - int(u.get("hp_max", 0) or 0))
        u["hp_raw"] = 0 if lethal else int(hp_raw)
        if "hp" in u:
            u["hp"] = max(0, u["hp_raw"] - offset)
        u["mp"] = int(mp_raw)
        if lethal:
            u["alive"] = False
        elif revive:
            u["alive"] = True

    def flinch(self, u) -> None:
        """SetDamageMotion(unit, null), as the stand-in shows it: the unit's `mot` reads MP_DAMAGE1 for FLINCH_FRAMES."""
        self.flinches[int(u.get("slot", -1))] = self.FLINCH_FRAMES

    def age_flinches(self) -> None:
        for slot in list(self.flinches):
            self.flinches[slot] -= 1
            if self.flinches[slot] <= 0:
                del self.flinches[slot]

    def record_fig(self, slot: int, value: int, via: str, arrive_ms: int, release_ms: int) -> None:
        """ActFigRecord: one figure DISPLAYED (figs[]: the last ACT_HOLD_FIGS_MAX, oldest first)."""
        self.figs.append({"slot": int(slot), "value": int(value), "via": via, "arrival_ms": int(arrive_ms),
                          "release_ms": int(release_ms)})
        del self.figs[:-ACT_HOLD_FIGS_MAX]

    def show_figure(self, u, slot: int, hp: int, mp: int, via: str, arrive_ms: int, ctx: dict | None) -> None:
        """ActShowFigure / ActShowStatFigure: figs[] at the display (bi.disappear 0: btl2d's own gate), then the stock
        request (the stand-in draws nothing)."""
        if not self._disappeared(u, ctx):
            self.record_fig(slot, act_fig_value(hp, mp), via, arrive_ms, self.now)

    def add_lag(self, lag: int) -> None:
        """ActHoldLag: n, min, max over every paired release; the samples (capped) for the median."""
        if self.lag_n == 0 or lag < self.lag_min:
            self.lag_min = int(lag)
        if self.lag_n == 0 or lag > self.lag_max:
            self.lag_max = int(lag)
        self.lag_n += 1
        if len(self.lag) < ACT_HOLD_LAG_CAP:
            self.lag.append(int(lag))

    def count(self, via: str) -> None:
        if via in self.rel_by:
            self.rel_by[via] += 1

    def log_release(self, r, slot: int, via: str, held_ms: int, lag: int, superseded: bool, queued: bool) -> None:
        """ActHoldLog: ONE line per release (amendment 10), capped per boot."""
        if self.logged > ACT_HOLD_LOG_MAX:
            return
        self.logged += 1
        if self.logged > ACT_HOLD_LOG_MAX:
            self._log(LOG_HOLD_FURTHER)
            return
        self._log((LOG_HOLD_QUEUED_FRAME if queued else LOG_HOLD_HELD_IMPACT) + (f" of id {r.id}" if r is not None else "")
                  + f" on wire slot {slot}{LOG_HOLD_RELEASED_VIA}{via} after {held_ms} ms of battle time"
                  + ((f" (lag {lag} ms" + (LOG_HOLD_HIT_FIRST if lag < 0 else "") + ")") if lag != INT32_MIN else "")
                  + (LOG_HOLD_SUPERSEDED if superseded else ""))

    def note_first(self, h: ActHeld) -> None:
        if self.first_logged:
            return
        self.first_logged = True
        self._log((LOG_HOLD_FIRST_QUEUED if h.queued else LOG_HOLD_FIRST_HELD)
                  + (f" (id {h.rec.id})" if h.rec is not None else "") + f" on wire slot {h.a['target_slot']}"
                  + (f", life mask 0x{self.life_mask:02X}" if h.life_slots else "") + LOG_HOLD_FIRST_TAIL)

    # -- the arrival (ActHoldIntake) and the arrival path (ApplyActionFrameNow)
    def intake(self, a: dict, dt, dc, self_cast: bool, rec, backlog: bool, covered: bool, ctx: dict) -> bool:
        """ActHoldIntake: True = the hold took the frame (held, released late, or queued); False = the arrival path applies
        it now, as before."""
        role = self._ctx(ctx).get("role", False)
        if not self.hold_on(role) or (rec is None and not self.held and not self.queued):
            return False
        has_c = dc is not None and not self_cast
        bit_t = (1 << a["target_slot"]) if dt is not None else 0
        bit_c = (1 << a["caster_slot"]) if dc is not None else 0
        slots = bit_t | bit_c
        busy = self.busy_mask()
        masked = (slots & busy) != 0
        credit = act_credit_find(rec, int(dt.get("id", 0))) if rec is not None and dt is not None and not a["stat_tick"] \
            else -1
        room = len(self.held) + len(self.queued) < ACT_HOLD_CAP
        verdict = act_hold_verdict(True, a["stat_tick"], rec.state if rec is not None else -1, dt is not None, credit >= 0,
                                   masked, room)
        if verdict == ACT_HOLD_APPLY:
            return False
        credit_ms = INT32_MIN
        if credit >= 0 and verdict != ACT_HOLD_HOLD:
            credit_ms = act_credit_take(rec, credit)
        if verdict == ACT_HOLD_LATE:
            # the replay already hit that target: at once, through the legacy path (no older change on its slots)
            # [ff9mapkit netsync s136] + the record (fallback A's covered rule, read at this step)
            self.apply_now(a, dt, dc, self_cast, covered, backlog, "late", self.now, False, ctx, rec=rec)
            self.held_count += 1
            self.count("late")
            self.add_lag(credit_ms - self.now)
            self.log_release(rec, a["target_slot"], "late", 0, credit_ms - self.now, False, False)
            return True
        self.ord += 1
        h = ActHeld(ord=self.ord, a=a, rec=rec, queued=verdict == ACT_HOLD_QUEUE, self_cast=self_cast, covered=covered,
                    backlog=backlog, unit_id=int(dt.get("id", 0)) if dt is not None else 0, slots=slots,
                    arrive_ms=self.now, credit_ms=credit_ms)
        h.life_t = dt is not None and act_lane_is_life(a["tgt_hp_raw"] == 0, self._dead(dt), bool(bit_t & busy))
        h.life_c = has_c and act_lane_is_life(a["cast_hp_raw"] == 0, self._dead(dc), bool(bit_c & busy))
        h.life_slots = (bit_t if h.life_t else 0) | (bit_c if h.life_c else 0)
        if not h.queued:
            # HELD: the non-life lanes apply NOW (the bars follow the host) and stamp their slots; the life lanes, the
            # figures and the flinch wait for the release
            self.held.append(h)
            self.held_count += 1
            if dt is not None and not h.life_t:
                self.apply_state(dt, a["target_slot"], False, False, a["tgt_hp_raw"], a["tgt_mp_raw"])
                self.stamp(a["target_slot"], a["seq_horizon"])
            if has_c and not h.life_c:
                self.apply_state(dc, a["caster_slot"], False, False, a["cast_hp_raw"], a["cast_mp_raw"])
                self.stamp(a["caster_slot"], a["seq_horizon"])
            if covered and has_c and a["caster_is_player"] and a["cast_hp_raw"] != 0 and self._can_play(dc):
                self.lane.swing_skipped += 1     # the legacy player swing is the replay's
        else:
            self.queued.append(h)
            self.queued_count += 1
        if dt is not None:                       # THE HORIZON GATE, now (both slots)
            self.gate(a["target_slot"], a["seq_horizon"])
        if dc is not None:
            self.gate(a["caster_slot"], a["seq_horizon"])
        self.recompute_mask()
        self.note_first(h)
        return True

    def apply_now(self, a: dict, dt, dc, self_cast: bool, covered: bool, backlog: bool, via: str, arrive_ms: int,
                  deferred: bool, ctx: dict | None, life_slots: int = 0, rec=None) -> None:
        """ApplyActionFrameNow -- steps c-h of the arrival path (an arrival, a late release, a queued frame's release:
        ``deferred`` = each lane's state only if no newer state applied that slot -- a reconciler record included -- and
        never a revive through a lane that was not a life lane when it queued (``life_slots``, the fix pass); its gate
        stamped on arrival). [ff9mapkit netsync s136] ``rec``: the record the frame's id names (None = none) -- step (e)'s
        motion is FALLBACK A (:class:`ActFallbackLane`) where the s110 player-only swing played; `fallback off` (or an s135
        lane) keeps the swing verbatim."""
        ctx = self._ctx(ctx)
        lethal_t, lethal_c = a["tgt_hp_raw"] == 0, a["cast_hp_raw"] == 0
        revive_t = dt is not None and not lethal_t and self._dead(dt)
        revive_c = dc is not None and not lethal_c and self._dead(dc)
        hidden_t = dt is not None and self._hidden(ctx, a["target_slot"], a["target_is_player"])
        hidden_c = dc is not None and self._hidden(ctx, a["caster_slot"], a["caster_is_player"])
        seq = a["seq_horizon"]
        apply_t = dt is not None and self.deferred_applies(deferred, revive_t, life_slots, a["target_slot"], seq)
        apply_c = dc is not None and not self_cast and self.deferred_applies(deferred, revive_c, life_slots,
                                                                           a["caster_slot"], seq)
        if (dt is not None and not apply_t) or (dc is not None and not self_cast and not apply_c):
            self.superseded += 1                 # ActHoldNoteSuperseded
        if a["stat_tick"]:
            if dt is not None and not hidden_t and (a["fig_hp_t"] or a["fig_mp_t"]):
                self.show_figure(dt, a["target_slot"], a["fig_hp_t"], a["fig_mp_t"], via, arrive_ms, ctx)
            if dt is not None:
                if apply_t:
                    self.apply_state(dt, a["target_slot"], a["tgt_hp_raw"] == 0, revive_t, a["tgt_hp_raw"],
                                     a["tgt_mp_raw"])
                    self.stamp(a["target_slot"], seq)
                if not deferred:
                    self.gate(a["target_slot"], seq)
            return
        if dt is not None and not hidden_t and (a["fig_info_t"] or a["fig_hp_t"] or a["fig_mp_t"]):
            self.show_figure(dt, a["target_slot"], a["fig_hp_t"], a["fig_mp_t"], via, arrive_ms, ctx)
        if dc is not None and not self_cast and not hidden_c and (a["fig_info_c"] or a["fig_hp_c"] or a["fig_mp_c"]):
            self.show_figure(dc, a["caster_slot"], a["fig_hp_c"], a["fig_mp_c"], via, arrive_ms, ctx)
        if dt is not None and a["dmg_mot"] and not lethal_t and not revive_t and not hidden_t and self._can_play(dt):
            self.flinch(dt)
        # [ff9mapkit netsync s136] the s110 swing's guard, kept whole: swing_skipped counts exactly as before; with fallback A
        # in force the action's ONE stock clip replaces the swing (ActFallbackAtImpact, behind the call site's own guards)
        s110_swing = dc is not None and not self_cast and a["caster_is_player"] and not lethal_c and not revive_c \
            and not hidden_c and self._can_play(dc)
        fb_on = self.lane.fallback_on(ctx.get("role", False))
        if s110_swing and covered:
            self.lane.swing_skipped += 1
        elif not fb_on:
            if s110_swing:
                self.lane.swings[int(dc.get("slot", -1))] = 20
        if fb_on:
            self.lane.fallback.at_impact(a, dc, self_cast, lethal_c, revive_c, hidden_c, rec, backlog, via, arrive_ms, ctx)
        if apply_t:
            self.apply_state(dt, a["target_slot"], lethal_t, revive_t, a["tgt_hp_raw"], a["tgt_mp_raw"])
            self.stamp(a["target_slot"], seq)
        if apply_c:
            self.apply_state(dc, a["caster_slot"], lethal_c, revive_c, a["cast_hp_raw"], a["cast_mp_raw"])
            self.stamp(a["caster_slot"], seq)
        if deferred:
            return
        if dt is not None:
            self.gate(a["target_slot"], seq)
        if dc is not None:
            self.gate(a["caster_slot"], seq)

    # -- the releases
    def on_hit(self, r, master: dict, bracket: bool) -> None:
        """ActHoldOnHit: the oldest held impact of ``r`` on ``master`` is released `hit` (its figures into the hit's
        pending list when ``bracket``, else shown at once), then the queue drains; none held = a CREDIT (while the hold is
        on)."""
        if master is None:
            return
        i = act_pick_oldest(self.held, r, int(master.get("id", 0)))
        if i < 0:
            if self.hold_on(self._ctx(None).get("role", False)):
                act_credit_add(r, int(master.get("id", 0)), self.now)
            return
        self.release_held(self.held[i], "hit", bracket, master)
        if act_drains_at_hit(bracket):
            self.drain_queue()
        elif self.queued:
            self.drain_due = True                # [fix pass: stock-1] never inside EffectPoint's bracket: the next tick

    def release_rec(self, r, via: str) -> None:
        """ActHoldReleaseRec: every held impact of ``r`` released ``via`` (oldest first), then the queue drains; its hit
        figures still waiting for a Figure point are forgotten (that point never comes)."""
        if r is None:
            return
        if act_shows_pending_at(via):
            self.show_pending(r, via)            # [fix pass: timing-1] a cut replay's collected hit figures: shown NOW
        self.fig_pending = [e for e in self.fig_pending if e["rec"] is not r]
        if not self.held:
            return
        released = False
        for h in list(self.held):
            if h.rec is not r:
                continue
            self.release_held(h, via, False, None)
            released = True
        if released:
            self.drain_queue()

    def release_held(self, h: ActHeld, via: str, bracket: bool, hit, ctx: dict | None = None) -> None:
        """ActReleaseHeld -- ONE held impact released ``via``: its figures (the hidden guard re-read), the flinch (wire
        lethality first, the revive decided NOW), each LIFE lane's kill or revive -- only if no newer frame applied that slot
        (the superseded guard) --, the lag (a hit), the count, one line."""
        if h in self.held:
            self.held.remove(h)
        ctx = self._ctx(ctx)
        a = h.a
        dt = self._resolve(ctx, a["target_slot"], a["target_is_player"])
        dc = self._resolve(ctx, a["caster_slot"], a["caster_is_player"]) if not h.self_cast else None
        hidden_t = dt is not None and self._hidden(ctx, a["target_slot"], a["target_is_player"])
        hidden_c = dc is not None and self._hidden(ctx, a["caster_slot"], a["caster_is_player"])
        lethal_t, lethal_c = a["tgt_hp_raw"] == 0, a["cast_hp_raw"] == 0
        revive_t = h.life_t and dt is not None and act_revive_at_release(lethal_t, self._dead(dt))
        revive_c = h.life_c and dc is not None and act_revive_at_release(lethal_c, self._dead(dc))
        if dt is not None and (a["fig_info_t"] or a["fig_hp_t"] or a["fig_mp_t"]):
            self.figure(h, hit if hit is not None and bracket else dt, a["target_slot"], a["fig_info_t"], a["fig_hp_t"],
                        a["fig_mp_t"], act_hit_fig_path(hidden_t, bracket), via, ctx)
        if dc is not None and (a["fig_info_c"] or a["fig_hp_c"] or a["fig_mp_c"]):
            self.figure(h, dc, a["caster_slot"], a["fig_info_c"], a["fig_hp_c"], a["fig_mp_c"],
                        act_hit_fig_path(hidden_c, bracket), via, ctx)
        if dt is not None and act_release_flinches(a["dmg_mot"], lethal_t, revive_t, hidden_t, self._can_play(dt)):
            self.flinch(dt)
        # [ff9mapkit netsync s136] FALLBACK A at a held release, after the flinch and before the life lanes (the arrival path's
        # order): covered for every release of a replayed action; a held impact whose START then DECLINED plays its action's
        # one clip now. The caster's guards are read HERE (a self-cast's caster is the target: its wire lethality, its revive)
        if self.lane.fallback_on(ctx.get("role", False)):
            fc = dt if h.self_cast else dc
            f_lethal = lethal_t if h.self_cast else lethal_c
            self.lane.fallback.at_impact(a, fc, h.self_cast, f_lethal,
                                         fc is not None and act_revive_at_release(f_lethal, self._dead(fc)),
                                         hidden_t if h.self_cast else hidden_c, h.rec, h.backlog, via, h.arrive_ms, ctx)
        superseded = False
        seq = a["seq_horizon"]
        if h.life_t and dt is not None:
            if self.applies(a["target_slot"], seq):
                self.apply_state(dt, a["target_slot"], lethal_t, revive_t, a["tgt_hp_raw"], a["tgt_mp_raw"])
                self.stamp(a["target_slot"], seq)
            else:
                superseded = True
        if h.life_c and dc is not None:
            if self.applies(a["caster_slot"], seq):
                self.apply_state(dc, a["caster_slot"], lethal_c, revive_c, a["cast_hp_raw"], a["cast_mp_raw"])
                self.stamp(a["caster_slot"], seq)
            else:
                superseded = True
        if superseded:
            self.superseded += 1
        lag = INT32_MIN
        if via == "hit":
            lag = self.now - h.arrive_ms
            self.add_lag(lag)
        self.count(via)
        self.log_release(h.rec, a["target_slot"], via, self.now - h.arrive_ms, lag, superseded, False)
        self.recompute_mask()

    def figure(self, h: ActHeld, u, slot: int, info: int, hp: int, mp: int, path: int, via: str, ctx: dict) -> None:
        """ActHoldFigure: none (hidden), the fig write inside EffectPoint's bracket (pending: figs[] at the Figure
        point), or the direct display (figs[] now)."""
        if path == ACT_FIG_NONE:
            return
        if path == ACT_FIG_BRACKET:
            if h.rec is None or u is None:
                return
            if len(self.fig_pending) >= 32:
                del self.fig_pending[0]
            self.fig_pending.append({"rec": h.rec, "unit": u, "slot": int(slot), "arrive_ms": h.arrive_ms,
                                     "info": int(info), "hp": int(hp), "mp": int(mp)})
            return
        self.show_figure(u, slot, hp, mp, via, h.arrive_ms, ctx)

    def show_pending(self, r, via: str) -> None:
        """ActHoldShowPending (fix pass: timing-1): each unit's collected hit figure of ``r`` that no Figure point showed --
        its pending writes summed; never collected when its fig.info sums to 0 (EffectPoint's `info != 0`) -- shown
        directly ``via`` (figs[] at the display), its arrival the oldest pending; none for a unit hidden here."""
        ctx = self._ctx(None)
        units: list = []
        for e in self.fig_pending:
            if e["rec"] is r and not any(e["unit"] is u for u in units):
                units.append(e["unit"])
        for u in units:
            mine = [e for e in self.fig_pending if e["rec"] is r and e["unit"] is u]
            info, hp, mp = 0, 0, 0
            for e in mine:
                info, hp, mp = info | e["info"], hp + e["hp"], mp + e["mp"]
            if info == 0 or self._hidden(ctx, mine[0]["slot"], bool(u.get("player"))):
                continue
            self.show_figure(u, mine[0]["slot"], hp, mp, via, min(e["arrive_ms"] for e in mine), ctx)

    def figure_point(self, r) -> None:
        """EffectPoint's Figure half for replay ``r`` (ActNoteFigure): each unit's collected figure -- its pending writes
        summed; a unit whose fig.info sums to 0 is never collected (EffectPoint's `info != 0`), so never shown -- recorded
        in figs[] "hit" at the DISPLAY (amendment 8), its arrival the oldest pending."""
        units: list = []
        for e in self.fig_pending:
            if e["rec"] is r and not any(e["unit"] is u for u in units):
                units.append(e["unit"])
        for u in units:
            mine = [e for e in self.fig_pending if e["rec"] is r and e["unit"] is u]
            info, hp, mp = 0, 0, 0
            for e in mine:
                info, hp, mp = info | e["info"], hp + e["hp"], mp + e["mp"]
            if info == 0:
                continue
            self.fig_pending = [e for e in self.fig_pending if not any(e is m for m in mine)]
            if not self._disappeared(u, None):
                self.record_fig(mine[0]["slot"], act_fig_value(hp, mp), "hit", min(e["arrive_ms"] for e in mine), self.now)

    def release_queued(self, q: ActHeld, via: str, ctx: dict | None = None) -> None:
        """ActReleaseQueued: the whole frame through the arrival path's own steps, DEFERRED."""
        if q in self.queued:
            self.queued.remove(q)
        ctx = self._ctx(ctx)
        a = q.a
        dt = self._resolve(ctx, a["target_slot"], a["target_is_player"])
        dc = self._resolve(ctx, a["caster_slot"], a["caster_is_player"])
        superseded0 = self.superseded
        if dt is not None or dc is not None:
            self.apply_now(a, dt, dc, dt is not None and dt is dc, q.covered, q.backlog, via, q.arrive_ms, True, ctx,
                           q.life_slots, rec=q.rec)     # [ff9mapkit netsync s136] + the record it named (read now)
        lag = INT32_MIN
        if q.credit_ms != INT32_MIN:
            lag = q.credit_ms - q.arrive_ms                  # a LATE frame a blocker kept: still a paired release
            self.add_lag(lag)
        self.rel_queued += 1
        self.log_release(q.rec, a["target_slot"], via, self.now - q.arrive_ms, lag, self.superseded != superseded0, True)
        self.recompute_mask()

    def drain_queue(self) -> None:
        """ActHoldDrainQueue: every queued frame whose blockers are gone, in arrival order (FIFO per slot)."""
        older_queued, i = 0, 0
        while i < len(self.queued):
            q = self.queued[i]
            older_held = 0
            for h in self.held:
                if h.ord < q.ord:
                    older_held |= h.life_slots
            if act_queue_blocked(q.slots, older_held, older_queued):
                older_queued |= q.slots
                i += 1
                continue
            self.release_queued(q, "queued")         # removes q: the same index is the next frame
        self.recompute_mask()

    def tick(self, ctx: dict) -> None:
        """ActHoldTick (ActTick's last step, outside its try): a hit's deferred drain first (any phase); then -- only in the
        steady phase (PHASE_NORMAL, the scene ours: D12) -- host-done and timeout of every held impact (battle time), the
        queue's drain and its own timeouts, and the catch-up of every skipped record whose slot left the mask."""
        if self.drain_due:
            self.drain_due = False
            self.drain_queue()
        if not self.held and not self.queued and not self.skipped:
            return
        if not ctx.get("steady"):
            return
        for h in list(self.held):
            why = act_held_timer_why(h.rec is not None and h.rec.host_ended,
                                     h.rec.host_end_ms if h.rec is not None else 0, h.arrive_ms, self.now)
            if why is not None and h in self.held:
                self.release_held(h, why, False, None, ctx)
        self.drain_queue()
        for q in list(self.queued):
            if act_held_timer_why(False, 0, q.arrive_ms, self.now) is not None and q in self.queued:
                self.release_queued(q, "timeout", ctx)
        if self.skipped:
            self.catch_up(ctx, "its release")

    def catch_up(self, ctx: dict | None, why: str) -> None:
        """ActHoldCatchUp (fix pass: life-2): every skipped record whose slot left the life mask (act_catch_up_slots)
        through the reconciler's ApplyUnit at its own seq -- once (its cache entry dropped first); one line per boot."""
        ctx = self._ctx(ctx)
        mask = 0
        for slot in self.skipped:
            mask |= 1 << slot
        due = act_catch_up_slots(mask, self.life_mask)
        for slot in range(8):
            if not due & (1 << slot) or slot not in self.skipped:
                continue
            state, seq = self.skipped.pop(slot)
            in_trance = self.skipped_trance.pop(slot, None)
            d = self._resolve(ctx, slot, slot < 4)
            if d is None:
                continue
            # [ff9mapkit netsync s137] (fix: timing-3) the record froze from here (the engine's _trCatchUpSinceMs)
            self.catch_up_since = int(self.skipped_since.get(slot, -1))
            try:
                self.apply_unit(d, slot, state, seq, bool(ctx.get("role", False)), in_trance=in_trance)
            finally:
                self.catch_up_since = -1
            if not self.catch_up_logged:
                self.catch_up_logged = True
                self._log(f"{LOG_HOLD_CATCH_UP}{slot}{LOG_HOLD_CATCH_UP_PIECE}{seq}) re-applied at {why}"
                          f"{LOG_HOLD_CATCH_UP_TAIL}")

    def flush(self, via: str, ctx: dict | None = None) -> None:
        """ActHoldFlush -- THE END-INJECT RELEASE (amendment 2, D02): every held impact and every queued frame, in arrival
        order, through the legacy path; the lists emptied, the mask 0. A no-op when nothing is held."""
        if not self.held and not self.queued:
            if self.skipped:
                self.catch_up(ctx, "the end injection")
            return
        held, queued = len(self.held), len(self.queued)
        for e in sorted(self.held + self.queued, key=lambda x: x.ord):
            if e.queued:
                if e in self.queued:
                    self.release_queued(e, via, ctx)
            elif e in self.held:
                self.release_held(e, via, False, None, ctx)
        if not self.flush_logged:
            self.flush_logged = True
            self._log(f"{LOG_HOLD_FLUSH}{held} held impact(s) and {queued}{LOG_HOLD_FLUSH_TAIL}")
        self.held, self.queued = [], []
        self.life_mask = 0
        self.drain_due = False
        if self.skipped:                         # [fix pass: life-2] what the mask skipped lands before the party is read
            self.catch_up(ctx, "the end injection")

    def discard_all(self, why: str) -> None:
        """ActHoldDiscardAll (ActDiscardAll's first statement): the life mask FIRST, then every held and queued frame
        DROPPED, counted (`discarded`) -- nothing applied, nothing shown."""
        self.life_mask = 0
        self.skipped, self.drain_due = {}, False
        self.skipped_trance = {}
        n = len(self.held) + len(self.queued)
        self.discarded += n
        self.held, self.queued, self.fig_pending = [], [], []
        if n > 0:
            self._log(f"{LOG_HOLD}{n}{LOG_HOLD_DISCARDED}{why}) -- nothing applied, nothing shown")

    # -- the reconciler's skip and the bench (HarnessActHoldBench)
    def mirror_dead_trance(self, d: dict, in_trance) -> None:
        """[ff9mapkit netsync s137] (fix: model-1) ApplyUnit's death lane on a dead PLAYER's sample: its Trance bit (and glow)
        mirrored from the record -- the host's own, so a SysTrans hit on the corpse reads the host's state. ``in_trance``
        None = the bench record's own (it carries the unit's current bit: no change)."""
        if d.get("player") and in_trance is not None:
            self.trance[int(d.get("slot", -1))] = bool(in_trance)

    def apply_unit(self, d: dict, slot: int, state: str, seq: int, role: bool, in_trance=None) -> None:
        """ApplyUnit for one bench record (the stand-in's model): the horizon gate passes (post-horizon by construction),
        THE LIFE MASK skips the whole record (counted, one line per boot; the fix pass CACHES it for its catch-up), else --
        the record really applied: the slot's cache dropped, THE SUPERSEDED GUARD stamped when newer (the fix pass) -- the
        death lane (a kill; [ff9mapkit netsync s137] a dead player's Trance bit mirrored: :meth:`mirror_dead_trance`, then --
        fix rmodel-1 -- its on-arrival probe: ActGuestLane.dead_model_check), the
        revive (a dead enemy is fully faded here: it holds dead), trance. ``in_trance`` (a lane rig's only): the record's
        InTrance where it differs from the bench record's own (the unit's current bit, or trance0 / trance1's)."""
        if self.life_mask != 0 and act_life_skips(self.life_mask, slot, self.lifeskip_on(role)):
            if slot not in self.skipped:         # [ff9mapkit netsync s137] (fix: timing-3) the slot's freeze began
                self.skipped_since[slot] = self.now
            self.skipped[slot] = (state, int(seq) & 0xFFFF)   # [fix pass: life-2] the latest skipped record, for its catch-up
            if in_trance is None:                # [ff9mapkit netsync s137] (fix: rmodel-1) ...with its own InTrance
                self.skipped_trance.pop(slot, None)
            else:
                self.skipped_trance[slot] = bool(in_trance)
            self.mask_skips += 1
            if not self.mask_logged:
                self.mask_logged = True
                self._log(f"{LOG_HOLD_MASK_SKIP}{slot}'s record -- its kill or revive waits for the replay's hit (life mask "
                          f"0x{self.life_mask:02X}; logged once per boot)")
            return
        # [ff9mapkit netsync s137] (fix: timing-3) THIS record's freeze (ActSampleApplied: a skipped one it overtakes, or the
        # catch-up's re-apply) -- the trance lane's on-arrival window reads it
        self.lane.trance.apply_since = int(self.skipped_since.get(slot, -1)) if slot in self.skipped else \
            int(self.catch_up_since)
        self.skipped.pop(slot, None)             # [fix pass: life-1] a record really applied: it overtakes the skipped one
        self.skipped_trance.pop(slot, None)
        if self.applies(slot, seq):              # ...and stamps THE SUPERSEDED GUARD when newer
            self.stamp(slot, seq)
        dead = self._dead(d)
        alive = (state == "alive") if state in ("dead", "alive") else not dead
        if not alive:
            if not dead:                             # KillUnit
                d["alive"] = False
                d["hp_raw"] = 0
                if "hp" in d:
                    d["hp"] = 0
            self.mirror_dead_trance(d, in_trance)    # [ff9mapkit netsync s137] (fix: model-1) the corpse's bit: the host's
            if d.get("player"):                      # [ff9mapkit netsync s137] (fix: rmodel-1) ...and its on-arrival probe
                self.lane.dead_model_check(d, int(slot), bool(self.trance.get(int(d.get("slot", -1)), False)), bool(role))
            return                                   # dead: the death lane owns everything else
        if dead:
            if not d.get("player"):
                return                               # "revive requested for a fully-faded enemy -- holding dead"
            d["alive"] = True
            if int(d.get("hp_raw", 0) or 0) == 0:
                d["hp_raw"] = 1
                if "hp" in d:
                    d["hp"] = 1
        if state in ("trance0", "trance1"):
            self.trance[int(d.get("slot", -1))] = state == "trance1"
        # [ff9mapkit netsync s137] the model check after the TRANCE lane (the bit and the glow follow the record at once): the
        # stateless probe -- the worn model against the mirrored bit -- through ActTranceAtSample (an s136 lane: at once)
        self.lane.model_check(d, int(slot), bool(self.trance.get(int(d.get("slot", -1)), False)), bool(role))

    def bench(self, args: list, op: str, val: str, *, booted: bool, role: bool, ctx: dict | None) -> tuple:
        """HarnessActHoldBench (after HarnessActGuestBench's role gate) -> ``(ok, why)`` in the engine's words."""
        if op in ("hold", "lifeskip"):
            if len(args) != 3 or val not in ("on", "off"):
                return False, f"netsync actbench {op}: expected `{op} on|off`"
            off = val == "off"
            if op == "hold":
                self.bench_hold_off = off
                self._log(LOG_HOLD_OFF if off else LOG_HOLD_ON)
            else:
                self.bench_lifeskip_off = off
                self._log(LOG_LIFESKIP_OFF if off else LOG_LIFESKIP_ON)
            return True, None
        state = str(args[3]).lower() if len(args) > 3 else ""
        slot = _cs_int(args[2]) if len(args) > 2 else None
        if len(args) != 4 or slot is None or not 0 <= slot <= 7 or state not in ACT_HOLD_UNIT_STATES:
            return False, HOLD_UNIT_USAGE
        ctx = ctx or {}
        if not booted or not ctx.get("steady"):
            return False, HOLD_UNIT_STEADY
        d = self._resolve(ctx, slot, slot < 4)
        if d is None:
            return False, f"{HOLD_UNIT_NO_UNIT}{slot} has no local unit"
        seq = (self.gate_seq[slot] + 1) & 0xFFFF
        masked = act_life_skips(self.life_mask, slot, self.lifeskip_on(role))
        self.apply_unit(d, slot, state, seq, role)
        self._log(f"{LOG_HOLD_UNIT}{slot} ({state}, seq {seq}, post-horizon) "
                  + (LOG_HOLD_UNIT_SKIPPED if masked else LOG_HOLD_UNIT_APPLIED))
        return True, None

    # -- the published block
    def doc(self, *, role: bool) -> dict:
        """HarnessAgent.AppendActGuestHold -- `act.guest.hold`, in every role."""
        n = self.lag_n
        return {"on": self.hold_on(role), "lifeskip": self.lifeskip_on(role), "held_now": len(self.held),
                "held": self.held_count, "queued_now": len(self.queued), "queued": self.queued_count,
                **{k: self.rel_by[v] for k, v in zip(ACT_HOLD_REL_KEYS, ACT_HOLD_VIAS)},
                "rel_queued": self.rel_queued, "superseded": self.superseded, "discarded": self.discarded,
                "life_mask": self.life_mask, "mask_skips": self.mask_skips,
                "lag": {"n": n, "min": self.lag_min if n else -1, "p50": act_lag_p50(self.lag) if n else -1,
                        "max": self.lag_max if n else -1},
                "figs": [dict(f) for f in self.figs]}


def act_hold_released(block: dict | None) -> int | None:
    """The held impacts an `act.guest.hold` block says were released this boot (the sum of its nine `rel_*`); None for an
    absent or malformed block."""
    if not isinstance(block, dict):
        return None
    try:
        return sum(int(block[k]) for k in ACT_HOLD_REL_KEYS)
    except (KeyError, TypeError, ValueError):
        return None


def act_hold_at_rest(block: dict | None) -> bool:
    """`act.guest.hold` AT REST: nothing held or queued now, the life mask 0, and every frame that entered the hold left
    it exactly once -- with no teardown discard this boot, every held impact by exactly one reason (held == sum of rel_*)
    and every queued frame released (queued == rel_queued); with a discard (its held / queued split is not published), the
    whole account: held + queued == sum of rel_* + rel_queued + discarded (a double-counted or a lost release is red).
    False for an absent block."""
    rel = act_hold_released(block)
    if rel is None:
        return False
    try:
        if int(block["held_now"]) or int(block["queued_now"]) or int(block["life_mask"]):
            return False
        if int(block["discarded"]):
            return int(block["held"]) + int(block["queued"]) == rel + int(block["rel_queued"]) + int(block["discarded"])
        return int(block["held"]) == rel and int(block["queued"]) == int(block["rel_queued"])
    except (KeyError, TypeError, ValueError):
        return False


#: NetSyncDiorama.Replay.cs's s135 integer constants, by C# name (the pin, both ways -- test_harness_netsync.py reads every
#: `internal const Int32` the s135 patch declares, comments stripped); ActViaArrival and ActHoldVias are pinned by value.
CS_HOLD_CONSTANTS = {
    "ActHoldTimeoutMs": ACT_HOLD_TIMEOUT_MS, "ActHoldHostDoneMs": ACT_HOLD_HOST_DONE_MS, "ActHoldCap": ACT_HOLD_CAP,
    "ActHoldLogMax": ACT_HOLD_LOG_MAX, "ActHoldFigsMax": ACT_HOLD_FIGS_MAX, "ActHoldLagCap": ACT_HOLD_LAG_CAP,
    "ActHoldCreditCap": ACT_HOLD_CREDIT_CAP, "ActHoldApply": ACT_HOLD_APPLY, "ActHoldHold": ACT_HOLD_HOLD,
    "ActHoldLate": ACT_HOLD_LATE, "ActHoldQueue": ACT_HOLD_QUEUE, "ActFigNone": ACT_FIG_NONE,
    "ActFigBracket": ACT_FIG_BRACKET, "ActFigDirect": ACT_FIG_DIRECT}


# ======================================================================================== [ff9mapkit netsync s136]
# FALLBACK A -- ONE STOCK CLIP PER UNCOVERED ACTION (studies/battle-coop/R3-DESIGN.md 3.3.5 as amended by
# R3-ACTION-REPLAY-AUDIT.md 2.4 -- amendments 1-6, decisions D-a / D-b / D-c -- and 3.5; the audit's "s125": group 2 was
# renumbered s133-s141). Until s136 an impact NO action replay covers (an old host without bit 5, a declined / stale /
# dropped / never-received START, ActionReplay=0, a guest without SFXRework) showed only the s110 player-only MP_ATTACK
# swing, and an enemy's nothing. s136 plays ONE stock clip chosen by the ACTION, at most once per action: a player's Item /
# AutoPotion / Throw -> MP_ITEM1, magic (category & 16) -> MP_MAGIC, Defend / Change -> none, anything else -> MP_ATTACK;
# an ENEMY -> the first NON-IDLE caster PlayAnimation of its scene sequence (parsed, never executed). THE CONTAINMENT LAW
# holds: a clip is presentation only (no figure, no HP / MP / status, no calculation). Everything below is the C# twin of
# a PURE rule of NetSyncDiorama.Replay.cs's fallback A (each method of the same name, its parameters in its order);
# test_harness_netsync.py EVALUATES ActFallbackSelfTest's own 30 rows against them (read off the stack, in order) and pins
# the constants by name both ways (CS_FALLBACK_CONSTANTS). :class:`ActFallbackLane` is the stand-in's model of fallback A
# with its statics (its docstring says what it models and what it cannot). [fix pass] + the deferral (cover-2), the sliding
# window (cover-5 / timing-5 / timing-6), the run-away hold and abort-all end blocks (timing-1), the restore's kept pose
# (timing-2) and the write's refusal of a clip the unit lacks (stock-1). [fix pass 2] + the RECORD deferral (rcover-2: an
# impact covered only by a still-pending START waits for its decision), the Loop and scripted enemy commands (rstock-1) and
# the ORDER-aware kept pose (rtiming-1: a clip written after its unit's abort survives the window's restore).
ACT_FALLBACK_WINDOW_MS = 500              # the old-host / id-0 key's window (battle ms between ARRIVALS, either way round)
ACT_FALLBACK_ID_CAP = 4096                # spent (nonce, actId) keys kept per boot (then the set restarts)
ACT_FALLBACK_WIN_CAP = 512                # spent (caster, cmd, sub) keys kept per boot (then the map restarts)
ACT_FALLBACK_SEQ_CACHE_CAP = 256          # parsed (scene, sub) sequences kept per boot
ACT_FALLBACK_LOG_MAX = 8                  # clip lines per boot (then counted, not logged)
ACT_FALLBACK_DEFER_MAX_MS = 4000          # [fix pass: cover-2] a deferred clip waits at most this long after its arrival
ACT_FALLBACK_DEFER_CAP = 16               # [fix pass: cover-2] deferred impacts kept (the oldest dropped first)
ACT_FB_NONE, ACT_FB_ATTACK, ACT_FB_MAGIC, ACT_FB_ITEM, ACT_FB_ENEMY = 0, 1, 2, 3, 4          # the clip an action chose
ACT_FB_DECIDE, ACT_FB_COVERED, ACT_FB_DEDUPED, ACT_FB_BACKLOG, ACT_FB_GUARDED = 0, 1, 2, 3, 4   # ActFallbackVerdict
ACT_FB_DEFER_WAIT, ACT_FB_DEFER_PLAY, ACT_FB_DEFER_DROP = 0, 1, 2                             # ActFallbackDeferStep
ACT_FB_DEFER_COVERED = 3                  # [fix pass 2: rcover-2] ActFallbackRecordStep: still pending past the bound
ACT_VIA_DEFERRED = "deferred"             # ActViaDeferred: `last.via` of a deferred impact's clip (cover-2)
#: ActFallbackKindName, by kind (anything else "none")
ACT_FB_KIND_NAMES = {ACT_FB_ATTACK: "attack", ACT_FB_MAGIC: "magic", ACT_FB_ITEM: "item", ACT_FB_ENEMY: "enemy"}
PROOF_FALLBACK = "action fallback selftest: "   # NetSyncDiorama.ActFallbackSelfTest (s136), logged right after PROOF_HOLD
FALLBACK_SELFTEST_ROWS = 30               # 6 clip + 3 enemy + 6 once/key + 4 covered + 1 verdict + 3 guard + 1 collapse
                                          # + 2 defer + 1 restore + 1 write (the fix pass) + 2 defer (fix pass 2: rcover-2)
#: `actbench <op>` -- fallback A's op (HarnessActFallbackBench, routed through the guest bench: IsActGuestBenchOp)
ACT_FALLBACK_BENCH_OPS = ("fallback",)
#: `act.guest.fallback.last` (HarnessFallbackLast: the last clip written this boot), in AppendActGuestFallback's order
ACT_FALLBACK_LAST_KEYS = ("actor", "clip", "cmd", "sub", "keyed_by", "kind", "id", "via", "ms")
#: `act.guest.fallback`'s buckets: every impact that reaches the motion step with a resolved caster counts exactly one
#: (none, clips and collapsed once per ACTION -- deduped, covered, guarded and backlog per impact)
ACT_FALLBACK_BUCKETS = ("clips", "deduped", "covered", "none", "guarded", "backlog", "collapsed")
#: `netsync.battle.act.guest.fallback` at AppendNetsync's catch-line sentinels, in AppendActGuestFallback's order -- the
#: LAST key of `act.guest`. The live block differs at rest only where the agent reads a static: `on` (true, no lever).
ACT_GUEST_FALLBACK_SENTINELS = {
    "on": False, "clips": 0, "deduped": 0, "covered": 0, "none": 0, "guarded": 0, "backlog": 0, "collapsed": 0,
    "parse_failed": 0, "last": None,
}
ACT_GUEST_SENTINELS["fallback"] = ACT_GUEST_FALLBACK_SENTINELS      # (after `hold`: s136's key, the last of act.guest)
#: BattlePlayerCharacter.PlayerMotionIndex: the two fallback A adds to s134's (MP_ATTACK 23 is there)
MP_MAGIC, MP_ITEM1 = 28, 31
#: [fix pass: harness-06] the three fallback motions by their enum NAMES (ActFallbackClipFor's "has no <MP_...>" reason)
MP_MOTION_NAMES = {MP_ATTACK: "MP_ATTACK", MP_MAGIC: "MP_MAGIC", MP_ITEM1: "MP_ITEM1"}
#: the stock ids fallback A's twins and bench name beyond s134's (BattleCommandId; BattleAbilityId) -- read off the shared
#: clone by test_harness_netsync.py when it is present, as CS_STOCK_IDS already is
CMD_THROW_ID, CMD_AUTO_POTION = 15, 51
ABILITY_FIRE_ID = 25                      # BattleAbilityId.Fire: a BlackMagic sub_no (Actions.csv category 19: magic)
#: [fix pass 2: rstock-1] the enemy AI's Loop moves (btl_scrp.SetEnemyCommand: sub_no the attack number) and
#: BattleCommandId.None (btlseq.RunSequence's cmd[0]: a battle script's scripted sequence, sub_no its pSeqNo -- `None` is
#: no name a Python row can use: the selftest row writes 0)
CMD_SCRIPT_COUNTER1, CMD_SCRIPT_COUNTER2, CMD_SCRIPT_COUNTER3 = 63, 64, 65
CMD_NONE_ID = 0
CS_STOCK_IDS.update({"BattleCommandId.Throw": CMD_THROW_ID, "BattleCommandId.AutoPotion": CMD_AUTO_POTION,
                     "BattleAbilityId.Fire": ABILITY_FIRE_ID, "BattleCommandId.ScriptCounter1": CMD_SCRIPT_COUNTER1,
                     "BattleCommandId.ScriptCounter2": CMD_SCRIPT_COUNTER2,
                     "BattleCommandId.ScriptCounter3": CMD_SCRIPT_COUNTER3})
#: CharacterCommandType (Memoria/Data/Characters/CharacterCommandType.cs): GetCommandTypeSafe's answers
CMD_TYPE_NORMAL, CMD_TYPE_ABILITY, CMD_TYPE_ITEM, CMD_TYPE_THROW, CMD_TYPE_INSTANT = 0, 1, 2, 3, 4
#: the engine's words (each a C# literal of the stack, or its head)
LOG_FALLBACK = "[NetSync] action fallback: "
LOG_FALLBACK_CLIP_TAIL = " -- one stock clip for an action no replay covers"
LOG_FALLBACK_COLLAPSED = " -- collapsed onto this frame's earlier clip on that unit"
LOG_FALLBACK_FURTHER = "; further clips this boot are counted, not logged"
LOG_FALLBACK_BY_CASTER = "keyed by caster, cmd and sub within "
LOG_FALLBACK_NONE = "[NetSync] action fallback: no clip for wire slot "
LOG_FALLBACK_NONE_TAIL = ") -- the action plays nothing (logged once per boot; `none` counts the rest)"
LOG_FALLBACK_PARSE = "[NetSync] action fallback: enemy sequence "
LOG_FALLBACK_PARSE_TAIL = ") -- played as nothing (logged once per boot; `parse_failed` counts the rest)"
LOG_FALLBACK_SUMMARY = "[NetSync] action fallback: boot summary ("
LOG_FALLBACK_FAULTED = ("[NetSync] action fallback faulted (logged once per boot; the impact's figures and state still "
                        "applied): ")
LOG_FALLBACK_OFF = ("[NetSync] harness: action fallback OFF -- CALIBRATION: the pre-s136 guest (an impact no replay covers "
                    "gets the s110 player-only MP_ATTACK swing; enemies nothing)")
LOG_FALLBACK_ON = "[NetSync] harness: action fallback ON"
LOG_FALLBACK_LEVER_BACK = "[NetSync] harness: action fallback lever back (fallback A ON; released with the harness)"
#: HarnessActFallbackBench's refusal of a malformed form (after the guest bench's role gate)
FALLBACK_USAGE = "netsync actbench fallback: expected `fallback on|off`"
#: the none line's reasons (ActFallbackClipFor / ActFallbackEnemyClip), each a piece the engine splices
FALLBACK_NONE_DEFEND = "Defend / Change"
FALLBACK_NONE_TRANSFORM = "a monster-transformed caster"
FALLBACK_NONE_IDLE = " plays only Idle"            # "sequence <sub>" + this
FALLBACK_NONE_MISSING = " is not on the unit -- refused: a name no clip answers would freeze it"   # "clip <name>" + this
#: [fix pass: cover-2] the deferral's line (once per boot): its head and its piece after the action
LOG_FALLBACK_DEFER = "[NetSync] action fallback: wire slot "
LOG_FALLBACK_DEFER_MID = " acts in a running replay -- its uncovered action (cmd "
LOG_FALLBACK_DEFER_TAIL = " ms of battle time (logged once per boot)"
#: [fix pass 2: rcover-2] the RECORD deferral's line (once per boot): LOG_FALLBACK_DEFER's head, these pieces, its tail
LOG_FALLBACK_AWAIT_MID = "'s action (cmd "
LOG_FALLBACK_AWAIT_WAITS = ") waits for its START's decision ("
LOG_FALLBACK_AWAIT_TAIL = ") -- a launch covers it, a decline plays its clip; at most "
#: ActFallbackWrite's clip line, parsed anywhere in a log line (Memoria.log's prefix kept)
_FALLBACK_CLIP_RX = re.compile(
    re.escape(LOG_FALLBACK) + r"(attack|magic|item|enemy) clip (\S+) on wire slot (\d+) \(cmd (\d+) sub (\d+), "
    r"(?:keyed by id (\d+)|" + re.escape(LOG_FALLBACK_BY_CASTER) + r"\d+ ms), via ([a-z-]+)\) at battle ms (-?\d+)")


def parse_fallback_clip(line: str) -> dict | None:
    """One ActFallbackWrite clip line -> {kind, clip, slot (the CASTER's wire slot), cmd, sub, keyed_by ("id" |
    "caster"), id (0 when keyed by caster), via, ms (battle ms of the write), collapsed}; None for any other line."""
    m = _FALLBACK_CLIP_RX.search(line or "")
    if m is None:
        return None
    return {"kind": m.group(1), "clip": m.group(2), "slot": int(m.group(3)), "cmd": int(m.group(4)),
            "sub": int(m.group(5)), "keyed_by": "id" if m.group(6) else "caster",
            "id": int(m.group(6)) if m.group(6) else 0, "via": m.group(7), "ms": int(m.group(8)),
            "collapsed": LOG_FALLBACK_COLLAPSED in line}


# ---- the pure rules (each NetSyncDiorama's method of the same name, its parameters in its order)
def act_fallback_covered(state: int, why: str | None) -> bool:
    """NetSyncDiorama.ActFallbackCovered -- COVERED vs UNCOVERED, read at the impact's motion step: True = a replay covers
    the impact's action -- it launched (running, ended, aborted after its launch), may still launch (queued, waiting), is a
    NOOP, was REPLACED by a newer START of its actor, or an abort-all (r8, w3, leave, clear) dropped it. False = no replay
    of it ever launched: no record (state -1: an old host, id 0, a START never received) or any other decline."""
    if state in (ACT_ST_REGISTERED, ACT_ST_WAITING, ACT_ST_RUNNING, ACT_ST_ENDED, ACT_ST_ABORTED, ACT_ST_NOOP):
        return True
    if state == ACT_ST_DECLINED:
        return why == "superseded" or act_decline_via(why) == "abort"
    return False


def act_fallback_keyed_by_id(has_ext: bool, ext_kind: int, act_id: int) -> bool:
    """NetSyncDiorama.ActFallbackKeyedById: an impact with the s133 extension and a non-zero action id is keyed (nonce,
    actId); any other (an old host's 46 bytes, id 0) by (caster, cmd, sub) within the 500 ms window."""
    return bool(has_ext) and int(ext_kind) == ACT_EXT_IMPACT and int(act_id) != 0


def act_fallback_window_key(caster_slot: int, caster_is_player: bool, cmd_no: int, sub_no: int) -> int:
    """NetSyncDiorama.ActFallbackWindowKey: the caster's wire slot and side, the command and its sub (16 bits each, as the
    impact's 46-byte head carries them)."""
    return ((int(caster_slot) & 0xFF) << 40) | ((1 if caster_is_player else 0) << 32) | ((int(cmd_no) & 0xFFFF) << 16) \
        | (int(sub_no) & 0xFFFF)


def act_fallback_within_window(spent_ms: int, arrive_ms: int) -> bool:
    """NetSyncDiorama.ActFallbackWithinWindow: two arrivals of one (caster, cmd, sub) are one action when they lie LESS
    than 500 ms of battle time apart, either way round (a queued sibling arrived first and is released later)."""
    return abs(int(arrive_ms) - int(spent_ms)) < ACT_FALLBACK_WINDOW_MS


def act_fallback_guard(self_cast: bool, dmg_mot: bool, lethal: bool, revive: bool, hidden: bool, can_play: bool,
                       acting: bool, end_or_leave: bool) -> bool:
    """NetSyncDiorama.ActFallbackGuard -- THE CALL-SITE GUARDS (amendment 6): self-cast only without a DmgMot (amendment 4,
    D-b), not lethal, not a revive, not hidden, a unit free to move (CanPlayCosmeticMotion, a model), not acting in a
    running replay, and no end presentation / end-inject flush / Leave in flight."""
    return (not self_cast or not dmg_mot) and not lethal and not revive and not hidden and bool(can_play) \
        and not acting and not end_or_leave


def act_fallback_end_blocks(end_presented: bool, end_held: bool, aborting_all: bool, leaving: bool, via: str) -> bool:
    """NetSyncDiorama.ActFallbackEndBlocks: no clip once the end is presented or injected, at the end-inject flush (it runs
    BEFORE the injection sets either), or while a Leave of the diorama is in flight -- [fix pass: timing-1] nor while the
    s115 run-away / annihilation-settle hold waits (``end_held``), nor inside an abort-all (``aborting_all``: a Leave's own
    runs before its stamp)."""
    return bool(end_presented) or bool(end_held) or bool(aborting_all) or bool(leaving) or via == "end-inject"


def act_fallback_defers(by_id: bool, guard_idle: bool, acting: bool) -> bool:
    """NetSyncDiorama.ActFallbackDefers -- [fix pass: cover-2] THE DEFERRAL: an impact keyed by its action id whose ONLY
    failing guard is "acting" (``guard_idle``: every guard with acting false) waits for its caster's replay; an id-0 /
    old-host impact never does."""
    return bool(by_id) and bool(acting) and bool(guard_idle)


def act_fallback_defer_step(expired: bool, acting: bool, holder_acting: bool, pending_turn: bool) -> int:
    """NetSyncDiorama.ActFallbackDeferStep -- [fix pass: cover-2] a deferred impact's step each tick: dropped once stale;
    while its caster acts it waits on the replay that held it (another one acting: a NEWER replay owns the turn -- dropped);
    once free, a pending START of the actor owns the turn (dropped); else it plays."""
    if expired:
        return ACT_FB_DEFER_DROP
    if acting:
        return ACT_FB_DEFER_WAIT if holder_acting else ACT_FB_DEFER_DROP
    if pending_turn:
        return ACT_FB_DEFER_DROP
    return ACT_FB_DEFER_PLAY


def act_fallback_awaits_record(covered: bool, rec_pending: bool) -> bool:
    """NetSyncDiorama.ActFallbackAwaitsRecord -- [fix pass 2: rcover-2] an impact COVERED only because its record is still
    PENDING (queued, waiting) has no verdict yet: it waits for that record's decision (a START that then declines uncovered
    -- `target`, stale, busy... -- would otherwise leave its action with no clip). A decided record's verdict stands."""
    return bool(covered) and bool(rec_pending)


def act_fallback_record_step(expired: bool, rec_pending: bool) -> int:
    """NetSyncDiorama.ActFallbackRecordStep -- [fix pass 2: rcover-2] a record-deferred impact's step each tick: once its
    record is decided it decides again (PLAY: `covered`, or the action's clip); while the record stays pending it waits, and
    past ActFallbackDeferMaxMs it keeps its arrival verdict (COVERED)."""
    if not rec_pending:
        return ACT_FB_DEFER_PLAY
    return ACT_FB_DEFER_COVERED if expired else ACT_FB_DEFER_WAIT


def act_fallback_keeps_pose(aborted_unit: bool, clip_after_abort: bool, shows_clip: bool) -> bool:
    """NetSyncDiorama.ActFallbackKeepsPose -- [fix pass: timing-2] the busy window's FULL restore keeps the pose of a unit
    that still shows its fallback clip and was none of the aborted replays' units -- [fix pass 2: rtiming-1] or was one but
    got that clip AFTER the abort (ORDER-aware: a later abort touching the unit takes it back)."""
    return (not aborted_unit or bool(clip_after_abort)) and bool(shows_clip)


def act_fallback_clip_playable(has_anim: bool, has_clip: bool) -> bool:
    """NetSyncDiorama.ActFallbackClipPlayable -- [fix pass: stock-1] a clip is written only onto a unit whose Animation
    holds it after the defensive attach (stock's TryGetArgAnimation refuses the same)."""
    return bool(has_anim) and bool(has_clip)


def act_fallback_verdict(covered: bool, seen: bool, backlog: bool, guard_ok: bool) -> int:
    """NetSyncDiorama.ActFallbackVerdict -- THE VERDICT, in its order: covered, then an action already decided (deduped),
    then a backlog drain (no clip, the key spent: D-c), then the guards (nothing spent); else the action decides."""
    if covered:
        return ACT_FB_COVERED
    if seen:
        return ACT_FB_DEDUPED
    if backlog:
        return ACT_FB_BACKLOG
    if not guard_ok:
        return ACT_FB_GUARDED
    return ACT_FB_DECIDE


def act_fallback_player_clip(item_or_throw: bool, defend_or_change: bool, monster_transform: bool, category: int) -> int:
    """NetSyncDiorama.ActFallbackPlayerClip -- THE PLAYER CLIP: a monster-transformed caster none; Item / AutoPotion /
    Throw MP_ITEM1 FIRST (amendment 3: an item's category reads Void's); Defend / Change none; magic (category & 16)
    MP_MAGIC; anything else MP_ATTACK."""
    if monster_transform:
        return ACT_FB_NONE
    if item_or_throw:
        return ACT_FB_ITEM
    if defend_or_change:
        return ACT_FB_NONE
    if int(category) & 16:
        return ACT_FB_MAGIC
    return ACT_FB_ATTACK


def command_type_safe(cmd_no: int, commands: dict | None = None) -> int:
    """btl_util.GetCommandTypeSafe (stock): Item / AutoPotion -> Item, Throw -> Throw, else the command table's type
    (``commands``: {cmd_no: CharacterCommandType}; the stand-in has none: Normal)."""
    if int(cmd_no) in (CMD_ITEM_ID, CMD_AUTO_POTION):
        return CMD_TYPE_ITEM
    if int(cmd_no) == CMD_THROW_ID:
        return CMD_TYPE_THROW
    return int((commands or {}).get(int(cmd_no), CMD_TYPE_NORMAL))


def act_fallback_item_or_throw(t: int) -> bool:
    """NetSyncDiorama.ActFallbackItemOrThrow: an item command by its type -- GetCommandTypeSafe's Item (Item, AutoPotion, a
    mod item command) or Throw."""
    return int(t) in (CMD_TYPE_ITEM, CMD_TYPE_THROW)


def act_fallback_defend_or_change(cmd_no: int) -> bool:
    """NetSyncDiorama.ActFallbackDefendOrChange."""
    return int(cmd_no) in (CMD_DEFEND_ID, CMD_CHANGE_ID)


def act_fallback_enemy_seq_cmd(cmd_no: int) -> bool:
    """NetSyncDiorama.ActFallbackEnemySeqCmd: an enemy command whose sub_no names a scene sequence -- btlseq's own four
    (EnemyAtk, EnemyCounter, EnemyDying, EnemyReaction), [fix pass 2: rstock-1] the AI's Loop moves ScriptCounter1-3 and a
    battle script's scripted sequence (cmd None: btlseq.RunSequence). A whitelist, not SFXRework's wider rule."""
    return int(cmd_no) in (CMD_ENEMY_ATK, CMD_ENEMY_COUNTER, CMD_ENEMY_DYING, CMD_ENEMY_REACTION, CMD_SCRIPT_COUNTER1,
                           CMD_SCRIPT_COUNTER2, CMD_SCRIPT_COUNTER3, CMD_NONE_ID)


def act_fallback_motion(kind: int) -> int:
    """NetSyncDiorama.ActFallbackMotion: the player motion of a kind (MP_ITEM1, MP_MAGIC, else MP_ATTACK)."""
    return MP_ITEM1 if kind == ACT_FB_ITEM else MP_MAGIC if kind == ACT_FB_MAGIC else MP_ATTACK


def act_fallback_kind_name(kind: int) -> str:
    """NetSyncDiorama.ActFallbackKindName (`last.kind`)."""
    return ACT_FB_KIND_NAMES.get(kind, "none")


class ActCode:
    """A BattleActionCode as fallback A reads one: its ``operation`` and its ``argument`` dictionary (name -> value)."""

    def __init__(self, operation: str, *pairs) -> None:
        self.operation = operation
        self.argument = {str(pairs[i]): str(pairs[i + 1]) for i in range(0, len(pairs) - 1, 2)}


class ActThread:
    """A BattleActionThread as fallback A reads one: its ``code`` (a list of :class:`ActCode`)."""

    def __init__(self, *codes) -> None:
        self.code = list(codes)


def act_fallback_first_clip(threads) -> str | None:
    """NetSyncDiorama.ActFallbackFirstClip -- THE ENEMY CLIP (amendment 2, D-a): the first PlayAnimation with Char=Caster
    whose Anim is a real clip -- "Idle" and an empty name skipped -- in the main thread, then the sub-threads in their order;
    None = none (play nothing)."""
    if threads is None:
        return None
    for th in threads:
        if th is None or getattr(th, "code", None) is None:
            continue
        for c in th.code:
            if c is None or c.operation != "PlayAnimation" or c.argument is None:
                continue
            if c.argument.get("Char") != "Caster":
                continue
            anim = c.argument.get("Anim")
            if not anim or anim == "Idle":
                continue
            return anim
    return None


def act_fallback_collapses(frame_mask: int, btl_id: int) -> bool:
    """NetSyncDiorama.ActFallbackCollapses: several clips on one actor in one frame collapse to the last one written -- this
    unit already got one this frame."""
    return int(btl_id) != 0 and (int(frame_mask) & int(btl_id)) != 0


class ActFallbackBook:
    """NetSyncDiorama.ActFallbackBook -- THE ONCE-PER-ACTION BOOK (pure: the selftest drives fresh ones): the (nonce, actId)
    keys spent this boot, and the (caster, cmd, sub) keys with the arrival that spent each."""

    #: the window rule the book reads (ActFallbackWithinWindow -- a class seam, so a test's mutant of the rule reaches the
    #: book exactly as the engine's static does)
    within = staticmethod(act_fallback_within_window)

    def __init__(self) -> None:
        self.ids: set = set()
        self.win: dict = {}

    def seen(self, by_id: bool, id_key: int, win_key: int, arrive_ms: int) -> bool:
        """The action already had its decision: its id key spent, or its window key spent within 500 ms of this arrival."""
        if by_id:
            return int(id_key) in self.ids
        at = self.win.get(int(win_key))
        return at is not None and self.within(at, arrive_ms)

    def note(self, by_id: bool, id_key: int, win_key: int, arrive_ms: int) -> None:
        """Spend the action's key (a clip, a "none" choice, a backlog impact): the window key keeps the NEWER of its arrival
        and this one ([fix pass: timing-6] a queued frame's older arrival never rewinds a newer action's)."""
        if by_id:
            if len(self.ids) >= ACT_FALLBACK_ID_CAP:
                self.ids.clear()
            self.ids.add(int(id_key))
            return
        at = self.win.get(int(win_key))
        if at is not None:
            self.win[int(win_key)] = max(at, int(arrive_ms))
            return
        if len(self.win) >= ACT_FALLBACK_WIN_CAP:
            self.win.clear()
        self.win[int(win_key)] = int(arrive_ms)

    def slide(self, win_key: int, arrive_ms: int) -> None:
        """[fix pass: cover-5, timing-5] A deduped sibling of a window-keyed action SLIDES the window to its own arrival
        (never back); a key never spent stays unspent."""
        at = self.win.get(int(win_key))
        if at is not None and int(arrive_ms) > at:
            self.win[int(win_key)] = int(arrive_ms)

    def clear(self) -> None:
        self.ids.clear()
        self.win.clear()


def act_seq_threads(anims) -> list:
    """A scene sequence as BattleActionThread.LoadFromBtlSeq parses it, for fallback A's read (the stand-in's model and the
    benches' offline oracle share it): one main thread, a PlayAnimation Char=Caster per case-5 op in order (``None`` -- the
    anim byte 255 -- reads the literal "Idle"), then END's WaitAnimation + PlayAnimation Anim=Idle (the Idle that END
    appends to EVERY sequence)."""
    main = ActThread(*[ActCode("PlayAnimation", "Char", "Caster", "Anim", "Idle" if a is None else str(a))
                       for a in anims or ()])
    main.code.append(ActCode("WaitAnimation", "Char", "Caster"))
    main.code.append(ActCode("PlayAnimation", "Char", "Caster", "Anim", "Idle"))
    return [main]


class ActFallbackLane:
    """[ff9mapkit netsync s136] FALLBACK A as NetSyncDiorama.Replay.cs runs it, with its statics -- the stand-in's model,
    owned by an :class:`ActGuestLane` (its battle clock, its log, its records). MODELLED, through the twins above:
    ActFallbackAtImpact at the arrival path's motion step and at a held release (the covered rule on the record's state AT
    THAT STEP, the key -- by id, else the (caster, cmd, sub) window between ARRIVALS --, the verdict's order, the call-site
    guards: self-cast with a DmgMot, lethal, revive, hidden, a unit free to move -- the stand-in's alive --, the caster
    acting in a running replay, the end / end-inject / a Leave), the clip choice (the player table by the action: Item /
    AutoPotion / Throw through GetCommandTypeSafe's hard-coded ids FIRST, Defend / Change, the category, a transformed
    caster; the enemy's scene sequence by its sub, parsed once per (scene, sub) a boot, a sequence the scene lacks a parse
    failure), the per-frame collapse (ctx ``frame``), every counter, `last`, the lever (`fallback on|off`, its role gate,
    ActBenchRelease's half), the per-boot reset and every Log.Message line. [fix pass] + THE DEFERRAL (cover-2: an id-keyed
    impact refused only for its caster's running replay waits, decides at :meth:`deferred_tick` with via "deferred", or is
    dropped `guarded` -- a newer replay's turn, stale, the cap, the teardown), the sliding window (cover-5 / timing-5 /
    timing-6), the end blocks of the run-away hold (ctx ``end_held``) and an abort-all (the lane's ``aborting_all``), a unit
    hidden by bi.disappear (ctx ``disappeared``), and a motion table without the motion (harness-06: ``mot_names`` given).
    [fix pass 2] + THE RECORD DEFERRAL (rcover-2: an impact covered only by a still-PENDING record waits -- at any call
    site -- and decides again once the record is decided: a launch / NOOP / covered decline `covered`, an uncovered decline
    its clip via "declined"; still pending past the bound, the cap or the teardown `covered`), the Loop and scripted enemy
    commands (rstock-1), and the busy window's ORDER-aware kept pose (rtiming-1: :meth:`restore_cut` -- at a FULL restore
    a clip on an aborted replay's unit is cut to idle unless it was written AFTER that abort).
    NOT MODELLED -- shapes, not engine data: a player's motion table is the unit's ``mot_names`` (else
    ``ANH_FAKE_P<slot>_<index>``), a unit's category is :attr:`categories` (else 16 for the stand-in's magic commands
    16-23, 0 otherwise -- a support ability's override is not mirrored in the engine either), the scene's sequences are
    :attr:`scene_seqs` ({sub: anims for :func:`act_seq_threads`, or None = no sequence}), the stock clip attach and its
    refusal of a clip the unit lacks (the stand-in has no Animation: ActFallbackClipPlayable is pinned by its selftest row),
    the slave / afFreeze / stop_anim freeze (no such units here), a zombie (no sequencer), the restore of any pose but a
    fallback clip's (the stand-in restores no other unit pose), the clip's own length (a clip reads on the unit for
    :attr:`CLIP_FRAMES` frames, then idle), and a fault (the 'faulted' line)."""

    CLIP_FRAMES = 24                             # (the stand-in's clip: the unit's anim / mot read it this long)
    #: the stand-in's scene sequences: sub -> case-5 anims (None = byte 255, "Idle"); sub 1 and 4 hold only END
    FAKE_SCENE_SEQS = {0: ("ANH_MON_FAKE_001_010", "ANH_MON_FAKE_001_011"), 1: (), 2: (None, "ANH_MON_FAKE_001_030"),
                       3: ("ANH_MON_FAKE_002_010",), 4: ()}
    #: the stand-in's magic commands (SummonGarnet .. DoubleBlackMagic): category 16 unless :attr:`categories` says
    FAKE_MAGIC_CMDS = tuple(range(16, 24))

    def __init__(self, lane) -> None:
        self.lane = lane
        self.bench_off = False                   # `fallback off`: the pre-s136 guest (harness-scoped, never per boot)
        self.scene_seqs: dict = dict(self.FAKE_SCENE_SEQS)
        self.categories: dict = {(CMD_BLACK_MAGIC_ID, ABILITY_FIRE_ID): 19}
        self.commands: dict = {}                 # GetCommandTypeSafe's table (the stand-in has none: Normal)
        self.book = ActFallbackBook()
        self.seq_cache: dict = {}
        self.clip_on: dict = {}
        self.deferred: list = []                 # [fix pass: cover-2] the deferred impacts, in arrival order
        self.reset(True)

    # -- the lever (its getter needs the selftest role, as the engine's)
    def on(self, role: bool) -> bool:
        """ActFallbackOn / HarnessFallbackOn (the rung's presence is the owner's)."""
        return not (self.bench_off and bool(role))

    def release(self) -> None:
        """ActBenchRelease's s136 half: the lever back (one line when it was pulled)."""
        if self.bench_off:
            self._log(LOG_FALLBACK_LEVER_BACK)
        self.bench_off = False

    def bench(self, args: list, val: str) -> tuple:
        """HarnessActFallbackBench (after HarnessActGuestBench's role gate) -> ``(ok, why)`` in the engine's words."""
        if len(args) != 3 or val not in ("on", "off"):
            return False, FALLBACK_USAGE
        self.bench_off = val == "off"
        self._log(LOG_FALLBACK_OFF if self.bench_off else LOG_FALLBACK_ON)
        return True, None

    # -- the per-boot state
    def reset(self, counters: bool) -> None:
        """ActFallbackReset: the spent keys, the sequence cache and the frame's collapse mask always; the counters, the log
        budgets and `last` with the boot block's counters (kept after the teardown until the next boot)."""
        self.book.clear()
        self.seq_cache.clear()
        self.deferred = []                       # (discard_all counted them `guarded` first: drop_deferred)
        self.frame, self.frame_mask = -1, 0
        self.post_abort_mask = 0                 # [fix pass 2: rtiming-1] _fbPostAbortMask
        if not counters:
            return
        self.clips = self.deduped = self.covered = self.none = self.guarded = self.backlog = self.collapsed = 0
        self.parse_failed = 0
        self.logged = 0
        self.none_logged = self.parse_logged = self.defer_logged = False
        self.await_logged = False                # [fix pass 2: rcover-2] the record deferral's line
        self.last = None
        self.clip_on = {}                        # (the stand-in's unit shapes: a boot's new units)

    def _log(self, text: str) -> None:
        self.lane._log(text)

    def age(self) -> None:
        for slot in list(self.clip_on):
            self.clip_on[slot]["frames"] -= 1
            if self.clip_on[slot]["frames"] <= 0:
                del self.clip_on[slot]

    # -- the motion step (ActFallbackAtImpact)
    def at_impact(self, a: dict, caster, self_cast: bool, lethal: bool, revive: bool, hidden: bool, rec, backlog: bool,
                  via: str, arrive_ms: int, ctx: dict | None) -> None:
        """ActFallbackAtImpact: covered, deduped, backlog, guarded, or the action decides its one clip (none, or written).
        ``caster`` the resolved caster (the target itself on a self-cast); lethal / revive / hidden the CALL SITE's own;
        ``rec`` the record the impact's id names (None = none); ``arrive_ms`` the impact's own arrival. [fix pass: cover-2]
        An id-keyed impact refused ONLY because its caster acts in a running replay is DEFERRED (no counter yet). [fix pass
        2: rcover-2] So is one covered only by a still-PENDING record (:meth:`defer_on_record`)."""
        if caster is None or a["stat_tick"]:
            return
        ctx = ctx or {}
        covered = act_fallback_covered(rec.state if rec is not None else -1, rec.why if rec is not None else None)
        by_id = act_fallback_keyed_by_id(a["has_ext"], a["ext_kind"], a["act_id"])
        id_key = ActBook.key_of(a["nonce"], a["act_id"]) if by_id else 0
        win_key = act_fallback_window_key(a["caster_slot"], a["caster_is_player"], a["cmd_no"], a["sub_no"])
        seen = not covered and self.book.seen(by_id, id_key, win_key, arrive_ms)
        vanished = ctx.get("disappeared")
        can_play = bool(caster.get("alive", True)) and not (callable(vanished) and vanished(caster))   # [fix pass: stock-2]
        acting = self.lane.acting_record(caster) is not None
        end_blocks = act_fallback_end_blocks(bool(ctx.get("end_presented")) or bool(ctx.get("end_injected")),
                                             bool(ctx.get("end_held")), bool(self.lane.aborting_all),
                                             bool(ctx.get("leaving")), via)            # [fix pass: timing-1]
        guard_ok = not covered and not seen and not backlog and act_fallback_guard(
            self_cast, a["dmg_mot"], lethal, revive, hidden, can_play, acting, end_blocks)
        verdict = act_fallback_verdict(covered, seen, backlog, guard_ok)
        if verdict == ACT_FB_COVERED:
            # [fix pass 2: rcover-2] covered ONLY by a still-PENDING record is no verdict yet: it waits for the decision
            if rec is not None and act_fallback_awaits_record(covered, rec.pending):
                self.defer_on_record(a, caster, self_cast, lethal, revive, rec, backlog, arrive_ms)
                return
            self.covered += 1
            return
        if verdict == ACT_FB_DEDUPED:
            if not by_id:
                self.book.slide(win_key, arrive_ms)     # [fix pass: cover-5, timing-5] the window follows the action's hits
            self.deduped += 1
            return
        if verdict == ACT_FB_BACKLOG:
            self.book.note(by_id, id_key, win_key, arrive_ms)
            self.backlog += 1
            return
        if verdict == ACT_FB_GUARDED:
            idle = act_fallback_guard(self_cast, a["dmg_mot"], lethal, revive, hidden, can_play, False, end_blocks)
            if act_fallback_defers(by_id, idle, acting) and self.defer(a, caster, self_cast, rec, arrive_ms):
                return                                  # [fix pass: cover-2] it waits for its caster's replay
            self.guarded += 1
            return
        clip, kind, why = self.clip_for(caster, a, ctx)
        self.book.note(by_id, id_key, win_key, arrive_ms)
        if clip is None:
            self.none += 1
            if not self.none_logged:
                self.none_logged = True
                self._log(f"{LOG_FALLBACK_NONE}{a['caster_slot']} cmd {a['cmd_no']} sub {a['sub_no']} ({why or 'none'}"
                          f"{LOG_FALLBACK_NONE_TAIL}")
            return
        self.write(caster, clip, kind, a, by_id, via, ctx)

    # -- [fix pass: cover-2] the deferral (ActFallbackDefer, ActFallbackDeferredTick, ActFallbackDropDeferred)
    def defer(self, a: dict, caster: dict, self_cast: bool, rec, arrive_ms: int) -> bool:
        """ActFallbackDefer: park the impact (its key unspent) with the replay holding its caster; past the cap the oldest
        is dropped (`guarded`). False = nothing holds the caster (the caller counts `guarded`). One line per boot."""
        holder = self.lane.acting_record(caster)
        if holder is None:
            return False
        self.park({"a": a, "caster": caster, "holder": holder, "self_cast": bool(self_cast), "rec": rec,
                   "arrive_ms": int(arrive_ms), "on_record": False})
        if not self.defer_logged:
            self.defer_logged = True
            self._log(f"{LOG_FALLBACK_DEFER}{a['caster_slot']}{LOG_FALLBACK_DEFER_MID}{a['cmd_no']} sub {a['sub_no']}, id "
                      f"{a['act_id']}) waits for that replay's end, at most {ACT_FALLBACK_DEFER_MAX_MS}"
                      f"{LOG_FALLBACK_DEFER_TAIL}")
        return True

    def defer_on_record(self, a: dict, caster: dict, self_cast: bool, lethal: bool, revive: bool, rec, backlog: bool,
                        arrive_ms: int) -> None:
        """ActFallbackDeferOnRecord -- [fix pass 2: rcover-2] park an impact covered only by its still-PENDING record: the
        frame, the caster, the record, the call site's own lethal / revive and backlog, its arrival; its key unspent, no
        counter until it decides or drops. One line per boot."""
        self.park({"a": a, "caster": caster, "holder": None, "self_cast": bool(self_cast), "rec": rec,
                   "arrive_ms": int(arrive_ms), "on_record": True, "lethal": bool(lethal), "revive": bool(revive),
                   "backlog": bool(backlog)})
        if self.await_logged:
            return
        self.await_logged = True
        self._log(f"{LOG_FALLBACK_DEFER}{a['caster_slot']}{LOG_FALLBACK_AWAIT_MID}{a['cmd_no']} sub {a['sub_no']}, id "
                  f"{a['act_id']}{LOG_FALLBACK_AWAIT_WAITS}{ACT_STATE_NAMES.get(rec.state, '?')}{LOG_FALLBACK_AWAIT_TAIL}"
                  f"{ACT_FALLBACK_DEFER_MAX_MS}{LOG_FALLBACK_DEFER_TAIL}")

    def park(self, e: dict) -> None:
        """ActFallbackPark -- [fix pass 2: rcover-2] one deferral in; past ActFallbackDeferCap the oldest out
        (:meth:`drop_entry`)."""
        if len(self.deferred) >= ACT_FALLBACK_DEFER_CAP:
            self.drop_entry(self.deferred.pop(0))
        self.deferred.append(e)

    def drop_entry(self, e: dict) -> None:
        """ActFallbackDropEntry -- [fix pass 2: rcover-2] a deferral dropped undecided counts its verdict when parked:
        `covered` for one that waited on its pending record, `guarded` for one that waited on its caster's replay."""
        if e.get("on_record"):
            self.covered += 1
        else:
            self.guarded += 1

    def deferred_tick(self, ctx: dict | None) -> None:
        """ActFallbackDeferredTick (ActTick, after the queue): each deferred impact waits while the replay that held its
        caster runs; once free -- no newer replay of the actor running or pending -- it decides with via "deferred" (every
        guard re-read; neither lethal nor a revive: its life lanes applied); dropped `guarded` when stale or a newer
        replay owns the turn. [fix pass 2: rcover-2] A record-deferred one waits while its record is pending, then decides
        again on the record's state NOW (via its decline's: "declined"; the call site's lethal / revive / backlog kept);
        still pending past the bound it counts `covered`."""
        if not self.deferred:
            return
        ctx = ctx or {}
        hidden_mask = int(ctx.get("hidden_mask", 0))
        for e in list(self.deferred):
            a = e["a"]
            if e.get("on_record"):
                rec = e["rec"]
                rstep = act_fallback_record_step(self.lane.now_ms - e["arrive_ms"] > ACT_FALLBACK_DEFER_MAX_MS,
                                                 rec is not None and rec.pending)
                if rstep == ACT_FB_DEFER_WAIT:
                    continue
                self.deferred.remove(e)
                if rstep == ACT_FB_DEFER_COVERED:
                    self.covered += 1
                    continue
                hidden = not a["caster_is_player"] and bool(hidden_mask & (1 << a["caster_slot"]))
                self.at_impact(a, e["caster"], e["self_cast"], e["lethal"], e["revive"], hidden, rec, e["backlog"],
                               act_decline_via(rec.why if rec is not None else None), e["arrive_ms"], ctx)
                continue
            now = self.lane.acting_record(e["caster"])
            acting = now is not None
            pending = not acting and any(r.pending and r.actor_slot == a["caster_slot"]
                                         and r.is_player == bool(a["caster_is_player"]) for r in self.lane.book.queue)
            step = act_fallback_defer_step(self.lane.now_ms - e["arrive_ms"] > ACT_FALLBACK_DEFER_MAX_MS, acting,
                                           e["holder"] in self.lane.running, pending)
            if step == ACT_FB_DEFER_WAIT:
                continue
            self.deferred.remove(e)
            if step == ACT_FB_DEFER_DROP:
                self.guarded += 1
                continue
            hidden = not a["caster_is_player"] and bool(hidden_mask & (1 << a["caster_slot"]))
            self.at_impact(a, e["caster"], e["self_cast"], False, False, hidden, e["rec"], False, ACT_VIA_DEFERRED,
                           e["arrive_ms"], ctx)

    def drop_deferred(self) -> None:
        """ActFallbackDropDeferred (the teardown, before the summary): every deferred impact counted `guarded` ([fix pass 2:
        rcover-2] one that waited on its pending record `covered`: drop_entry)."""
        for e in self.deferred:
            self.drop_entry(e)
        self.deferred = []

    def restore_cut(self, aborted_units: int, post_abort: int) -> None:
        """ActRestoreUnit's fallback half at the busy window's FULL restore (the stand-in's only unit pose: a clip) -- [fix
        pass: timing-2] a clip on an aborted replay's unit is cut to idle, a bystander's plays on; [fix pass 2: rtiming-1]
        ORDER-aware: one written AFTER that abort (``post_abort``) plays on too (ActFallbackKeepsPose)."""
        for slot, e in list(self.clip_on.items()):
            uid = int(e.get("id", 0))
            if not act_fallback_keeps_pose(bool(aborted_units & uid), bool(post_abort & uid), True):
                del self.clip_on[slot]

    def clip_for(self, d: dict, a: dict, ctx: dict) -> tuple:
        """ActFallbackClipFor: (clip | None, kind, why) -- the player table by the action, or the enemy's scene sequence."""
        if d.get("player"):
            item_or_throw = act_fallback_item_or_throw(command_type_safe(a["cmd_no"], self.commands))
            defend_or_change = act_fallback_defend_or_change(a["cmd_no"])
            transformed = bool(d.get("monster_transform"))
            category = 0 if item_or_throw or defend_or_change or transformed else self.category(a["cmd_no"], a["sub_no"])
            kind = act_fallback_player_clip(item_or_throw, defend_or_change, transformed, category)
            if kind == ACT_FB_NONE:
                return None, ACT_FB_NONE, FALLBACK_NONE_TRANSFORM if transformed else FALLBACK_NONE_DEFEND
            idx = act_fallback_motion(kind)
            names = d.get("mot_names")
            if not isinstance(names, (list, tuple)):                    # (no table given: the stand-in's own clip names)
                return f"ANH_FAKE_P{int(d.get('slot', -1))}_{idx:03d}", kind, None
            # [fix pass: harness-06] a table given is the engine's d.mot: too short, or an empty name, plays NOTHING
            if idx >= len(names) or not names[idx]:
                return None, ACT_FB_NONE, f"the unit's motion table has no {MP_MOTION_NAMES.get(idx, idx)}"
            return names[idx], kind, None
        if not act_fallback_enemy_seq_cmd(a["cmd_no"]):
            return None, ACT_FB_NONE, f"enemy cmd {a['cmd_no']} names no scene sequence"
        clip, why = self.enemy_clip(int(a["sub_no"]), ctx)
        return (clip, ACT_FB_ENEMY, None) if clip is not None else (None, ACT_FB_NONE, why)

    def category(self, cmd_no: int, sub_no: int) -> int:
        """The scratch CMD_DATA's AbilityCategory, as the stand-in models it (:attr:`categories`, else the magic rule)."""
        return int(self.categories.get((int(cmd_no), int(sub_no)), 16 if int(cmd_no) in self.FAKE_MAGIC_CMDS else 0))

    def enemy_clip(self, sub: int, ctx: dict) -> tuple:
        """ActFallbackEnemyClip: (clip | None, why), cached per (scene, sub) for the boot; a sequence the scene lacks is a
        parse failure (counted, logged once per boot, played as nothing)."""
        scene = int(ctx.get("scene", -1))
        key = (scene, int(sub))
        e = self.seq_cache.get(key)
        if e is None:
            anims = self.scene_seqs.get(int(sub)) if int(sub) >= 0 else None
            if anims is None:
                e = {"clip": None, "fail": f"the scene has no sequence {sub}"}
            else:
                e = {"clip": act_fallback_first_clip(act_seq_threads(anims)), "fail": None}
            if len(self.seq_cache) >= ACT_FALLBACK_SEQ_CACHE_CAP:
                self.seq_cache.clear()
            self.seq_cache[key] = e
            if e["fail"] is not None:
                self.parse_failed += 1
                if not self.parse_logged:
                    self.parse_logged = True
                    self._log(f"{LOG_FALLBACK_PARSE}{sub} of scene {scene} could not be parsed ({e['fail']}"
                              f"{LOG_FALLBACK_PARSE_TAIL}")
        why = (f"sequence {sub}: {e['fail']}" if e["fail"] is not None else
               f"sequence {sub}{FALLBACK_NONE_IDLE}" if e["clip"] is None else None)
        return e["clip"], why

    def write(self, d: dict, clip: str, kind: int, a: dict, by_id: bool, via: str, ctx: dict) -> None:
        """ActFallbackWrite: the clip on the unit (the stand-in: its anim / mot for :attr:`CLIP_FRAMES`), counted when
        written -- one per actor per frame (`clips`), the rest `collapsed` -- `last` recorded, one line (capped a boot)."""
        frame = int(ctx.get("frame", 0))
        if frame != self.frame:
            self.frame, self.frame_mask = frame, 0
        btl_id = int(d.get("id", 0))
        collapsed = act_fallback_collapses(self.frame_mask, btl_id)
        self.clip_on[int(d.get("slot", -1))] = {"frames": self.CLIP_FRAMES, "clip": clip, "id": btl_id,
                                                "mot": act_fallback_motion(kind) if d.get("player") else -1}
        self.frame_mask |= btl_id
        # [fix pass 2: rtiming-1] a clip on a unit an abort of the open busy window already touched: written AFTER it
        if self.lane.window_open and self.lane.window_abort_mask & btl_id:
            self.post_abort_mask |= btl_id
        if collapsed:
            self.collapsed += 1
        else:
            self.clips += 1
        self.last = {"actor": int(a["caster_slot"]), "clip": clip, "cmd": int(a["cmd_no"]), "sub": int(a["sub_no"]),
                     "keyed_by": "id" if by_id else "caster", "kind": act_fallback_kind_name(kind),
                     "id": int(a["act_id"]) if by_id else 0, "via": via, "ms": int(self.lane.now_ms)}
        if self.logged >= ACT_FALLBACK_LOG_MAX:
            return
        self.logged += 1
        self._log(f"{LOG_FALLBACK}{act_fallback_kind_name(kind)} clip {clip} on wire slot {a['caster_slot']} (cmd "
                  f"{a['cmd_no']} sub {a['sub_no']}, "
                  + (f"keyed by id {a['act_id']}" if by_id else f"{LOG_FALLBACK_BY_CASTER}{ACT_FALLBACK_WINDOW_MS} ms")
                  + f", via {via}) at battle ms {self.lane.now_ms}"
                  + (LOG_FALLBACK_COLLAPSED if collapsed else LOG_FALLBACK_CLIP_TAIL)
                  + (LOG_FALLBACK_FURTHER if self.logged == ACT_FALLBACK_LOG_MAX else ""))

    def log_summary(self, why: str) -> None:
        """ActFallbackLogSummary: one line per boot at its end, only when fallback A did anything (a covered impact alone
        logs none)."""
        if self.clips + self.collapsed + self.deduped + self.none + self.guarded + self.backlog + self.parse_failed == 0:
            return
        self._log(f"{LOG_FALLBACK_SUMMARY}{why}) -- {self.clips} clip(s), {self.collapsed} collapsed, {self.deduped} "
                  f"deduped, {self.covered} covered, {self.none} none, {self.guarded} guarded, {self.backlog} backlog, "
                  f"{self.parse_failed} parse failure(s)")

    # -- the published block
    def doc(self, *, role: bool) -> dict:
        """HarnessAgent.AppendActGuestFallback -- `act.guest.fallback`, in every role."""
        return {"on": self.on(role), "clips": self.clips, "deduped": self.deduped, "covered": self.covered,
                "none": self.none, "guarded": self.guarded, "backlog": self.backlog, "collapsed": self.collapsed,
                "parse_failed": self.parse_failed, "last": dict(self.last) if self.last is not None else None}


def act_fallback_decided(block: dict | None) -> int | None:
    """The impacts an `act.guest.fallback` block says reached the motion step with a resolved caster (the sum of its
    buckets); None for an absent or malformed block."""
    if not isinstance(block, dict):
        return None
    try:
        return sum(int(block[k]) for k in ACT_FALLBACK_BUCKETS)
    except (KeyError, TypeError, ValueError):
        return None


#: NetSyncDiorama.Replay.cs's s136 integer constants, by C# name (the pin, both ways -- test_harness_netsync.py reads every
#: `internal const Int32` the s136 patch declares, comments stripped).
CS_FALLBACK_CONSTANTS = {
    "ActFallbackWindowMs": ACT_FALLBACK_WINDOW_MS, "ActFallbackIdCap": ACT_FALLBACK_ID_CAP,
    "ActFallbackWinCap": ACT_FALLBACK_WIN_CAP, "ActFallbackSeqCacheCap": ACT_FALLBACK_SEQ_CACHE_CAP,
    "ActFallbackLogMax": ACT_FALLBACK_LOG_MAX, "ActFallbackDeferMaxMs": ACT_FALLBACK_DEFER_MAX_MS,
    "ActFallbackDeferCap": ACT_FALLBACK_DEFER_CAP, "ActFbNone": ACT_FB_NONE, "ActFbAttack": ACT_FB_ATTACK,
    "ActFbMagic": ACT_FB_MAGIC, "ActFbItem": ACT_FB_ITEM, "ActFbEnemy": ACT_FB_ENEMY, "ActFbDecide": ACT_FB_DECIDE,
    "ActFbCovered": ACT_FB_COVERED, "ActFbDeduped": ACT_FB_DEDUPED, "ActFbBacklog": ACT_FB_BACKLOG,
    "ActFbGuarded": ACT_FB_GUARDED, "ActFbDeferWait": ACT_FB_DEFER_WAIT, "ActFbDeferPlay": ACT_FB_DEFER_PLAY,
    "ActFbDeferDrop": ACT_FB_DEFER_DROP, "ActFbDeferCovered": ACT_FB_DEFER_COVERED}


# ======================================================================================== [ff9mapkit netsync s137]
# THE TRANCE BURST TIMING (studies/battle-coop/R3-DESIGN.md 3.3.6 as amended by R3-ACTION-REPLAY-AUDIT.md 2.5 --
# amendments 1-6, decisions D1-D6 -- and 3.5; the design's and the audit's "s126": group 2 was renumbered s133-s141). Until
# s137 the guest's reconciler swapped a player's MODEL the moment the host's type-1 sample carried the trance stat bit --
# ahead of the SysTrans burst the guest has replayed since s134. s137 DEFERS that model change (and only it: the trance
# status, enable_trance_glow, the gauge and the ATB still follow the host at the sample) to the SysTrans replay's own hit
# -- the host's own swap point -- else to a 400 ms GRACE of battle time after nothing names the unit, capped at 2500 ms
# from the sample (never while the unit's own SysTrans burst is in flight -- that waits for its hit, at most THE BURST
# CEILING, 8500 ms from the sample). THE CONTAINMENT LAW holds: the swap's argument is the guest's MIRRORED stat bit (D2),
# probe-guarded; nothing writes trance_no. Everything below is the C# twin of a PURE rule of NetSyncDiorama.Replay.cs's
# trance burst (each method of the same name, its parameters in its order); test_harness_netsync.py EVALUATES
# ActTranceSelfTest's own 21 rows against them (read off the stack, in order) and pins the constants by name both ways
# (CS_TRANCE_CONSTANTS). :class:`ActTranceLane` is the stand-in's model of the live half with its statics (its docstring
# says what it models and what it cannot).
ACT_TRANCE_GRACE_MS = 400                 # the grace after the unit was last named (battle ms)
ACT_TRANCE_CAP_MS = 2500                  # ...capped this long after the record (battle ms; never cuts its own burst)
ACT_TRANCE_BURST_MAX_MS = 8500            # ...and its own burst, at most this long after the record (ActWaitMaxMs + the cap)
ACT_TRANCE_LOG_MAX = 12                   # deferral / swap lines per boot (then counted, not logged)
ACT_TR_STEP_WAIT, ACT_TR_STEP_GRACE, ACT_TR_STEP_CAP, ACT_TR_STEP_BURST_MAX = 0, 1, 2, 3      # ActTranceStep's answers
#: ActTranceVerdict's (and ActTranceFlushVerdict's) answers
ACT_TR_WAIT, ACT_TR_MOOT, ACT_TR_DROP_LEAVE, ACT_TR_DROP_UNIT, ACT_TR_DROP_DEAD, ACT_TR_SWAP_GATE = 0, 1, 2, 3, 4, 5
ACT_TR_SWAP_DECLINE, ACT_TR_SWAP_END, ACT_TR_SWAP_CAP, ACT_TR_SWAP_GRACE, ACT_TR_SWAP_INJECT = 6, 7, 8, 9, 10
PROOF_TRANCE = "action trance selftest: "  # NetSyncDiorama.ActTranceSelfTest (s137), logged right after PROOF_FALLBACK
TRANCE_SELFTEST_ROWS = 21                 # 1 gate + 1 burst + 1 names + 5 grace / busy / cap / burst exemption / ceiling
#                                           + 1 decline + 6 verdict order (the frozen wait's one) + 2 arrival (the
#                                           catch-up's one) + 2 hit / trust + 2 inject + 1 present
#: `actbench <op>` -- the trance burst timing's op (HarnessActTranceBench, routed through the guest bench: IsActGuestBenchOp)
ACT_TRANCE_BENCH_OPS = ("trancegrace",)
#: `act.guest.trance.last` (HarnessTranceLast: the last swap or resolution this boot), in AppendActGuestTrance's order
ACT_TRANCE_LAST_KEYS = ("slot", "swapped", "to", "via", "id", "record_ms", "ms")
#: every `last.via` the engine writes ("frozen" / "contradicted": an untrusted hit, no resolution) -- [s137 fix pass 2]
#: PINNED both ways against the s137 patch's own literals, the stand-in's and the bench's judged ones
#: (test_harness_netsync.py: test_the_trance_vias_are_the_engines_both_ways)
ACT_TRANCE_VIAS = ("immediate", "on-arrival", "hit", "grace", "cap", "declined", "gate", "ended", "inject", "moot", "leave",
                   "teardown", "dead", "unit", "fault", "frozen", "contradicted")
#: the ways a DEFERRAL ends (each counted once): deferred == the sum of these + the bits of `pending`
ACT_TRANCE_RESOLVED_KEYS = ("swaps_by_hit", "swaps_by_grace", "swaps_by_cap", "swaps_by_decline", "swaps_by_end",
                            "swaps_by_inject", "moot", "dropped")
#: `netsync.battle.act.guest.trance` at AppendNetsync's catch-line sentinels, in AppendActGuestTrance's order -- the LAST key
#: of `act.guest`. The live block differs at rest only where the agent reads a static: `on` (true, no lever).
ACT_GUEST_TRANCE_SENTINELS = {
    "on": False, "gate": False, "deferred": 0, "pending": 0, **dict.fromkeys(ACT_TRANCE_RESOLVED_KEYS[:6], 0),
    "moot": 0, "dropped": 0, "immediate": 0, "on_arrival": 0, "hit_unpaired": 0, "hit_untrusted": 0, "present": 0,
    "last": None,
}
ACT_GUEST_SENTINELS["trance"] = ACT_GUEST_TRANCE_SENTINELS      # (after `fallback`: s137's key, the last of act.guest)
#: BattleStatus.Trance (Memoria/Data/Battle/BattleStatus.cs: 1 << 14) -- the bit `battle.units[].status` carries
BATTLE_STATUS_TRANCE = 1 << 14
#: SpecialEffect.Special_Trance_End -- the host-resolved vfx of a SysTrans that LEAVES Trance (Activate is s134's 257)
SPECIAL_TRANCE_END = 489
CS_STOCK_IDS.update({"SpecialEffect.Special_Trance_End": SPECIAL_TRANCE_END})
#: `battle.units[]`'s s137 key, after s134's `row`, before `status` (AppendBattleUnits)
UNIT_TRANCE_KEYS = ("trance_model",)
#: the engine's words (each a C# literal of the stack, or its head)
LOG_TRANCE = "[NetSync] action trance: "
LOG_TRANCE_SLOT = "[NetSync] action trance: wire slot "
LOG_TRANCE_WAITS = " model waits for its SysTrans burst "                 # "<head><slot>'s <trance|normal>" + this
LOG_TRANCE_WAITS_TAIL = (" ms without its START) -- the trance status, the glow and the gauge already follow the host")
LOG_TRANCE_FURTHER = "; further lines this boot are counted, not logged"
LOG_TRANCE_KEEPS = " keeps its model"
LOG_TRANCE_AFTER = " ms of battle time after its sample"
LOG_TRANCE_SUMMARY = "[NetSync] action trance: boot summary ("
LOG_TRANCE_FAULTED = "[NetSync] action trance: a step faulted (its deferral dropped; logged once per boot): "
LOG_TRANCE_OFF = ("[NetSync] harness: action trance grace OFF -- CALIBRATION: the pre-s137 timing (a trance model swaps when "
                  "the host's sample carries the bit; the SysTrans replay's hit swaps nothing)")
LOG_TRANCE_ON = "[NetSync] harness: action trance grace ON"
LOG_TRANCE_LEVER_BACK = ("[NetSync] harness: action trance grace lever back (the model swap waits for the burst again; released "
                         "with the harness)")
#: HarnessActTranceBench's refusal of a malformed form (after the guest bench's role gate)
TRANCE_USAGE = "netsync actbench trancegrace: expected `trancegrace on|off`"
#: ActTranceNote's swap / keep line, parsed anywhere in a log line (Memoria.log's prefix kept)
_TRANCE_LINE_RX = re.compile(
    re.escape(LOG_TRANCE_SLOT) + r"(\d+)(?: -> the (trance|normal) model|" + re.escape(LOG_TRANCE_KEEPS) + r") \(([a-z-]+)"
    r"(?:, replay id (\d+))?(?:, (-?\d+)" + re.escape(LOG_TRANCE_AFTER) + r")?; battle ms (-?\d+)\)")
_TRANCE_WAITS_RX = re.compile(re.escape(LOG_TRANCE_SLOT) + r"(\d+)'s (trance|normal)" + re.escape(LOG_TRANCE_WAITS))


def parse_trance_line(line: str) -> dict | None:
    """One ActTranceNote line -> {slot (the WIRE slot), swapped, to (True = the trance model; None when kept), via, id (0 =
    none), after_ms (battle ms from its sample; None when not deferred), ms (battle ms of the swap or resolution),
    further}; None for any other line (the deferral's "waits" line too: :func:`parse_trance_waits`)."""
    m = _TRANCE_LINE_RX.search(line or "")
    if m is None:
        return None
    return {"slot": int(m.group(1)), "swapped": m.group(2) is not None,
            "to": (m.group(2) == "trance") if m.group(2) else None, "via": m.group(3),
            "id": int(m.group(4)) if m.group(4) else 0, "after_ms": int(m.group(5)) if m.group(5) else None,
            "ms": int(m.group(6)), "further": LOG_TRANCE_FURTHER in line}


def parse_trance_waits(line: str) -> dict | None:
    """ActTranceAtSample's deferral line -> {slot, to (True = the trance model the unit waits for)}; None otherwise."""
    m = _TRANCE_WAITS_RX.search(line or "")
    return {"slot": int(m.group(1)), "to": m.group(2) == "trance"} if m else None


# ---- the pure rules (each NetSyncDiorama's method of the same name, its parameters in its order)
def act_trance_defers(bit5: bool, can_replay: bool, grace_on: bool) -> bool:
    """NetSyncDiorama.ActTranceDefers -- THE GATE (amendment 3): a model change waits for the burst only with bit 5 latched,
    a guest that can replay, and the `trancegrace` lever on. Anything else swaps at the sample."""
    return bool(bit5) and bool(can_replay) and bool(grace_on)


def act_trance_is_burst(cmd_no: int, is_player: bool, actor_slot: int) -> bool:
    """NetSyncDiorama.ActTranceIsBurst: a SysTrans of a PLAYER wire slot 0-3 (an enemy wears no trance model; SysPhantom is
    Garnet's recast, not the burst)."""
    return int(cmd_no) == CMD_SYS_TRANS and bool(is_player) and 0 <= int(actor_slot) <= 3


def act_trance_decline_ends(why) -> bool:
    """NetSyncDiorama.ActTranceDeclineEnds (amendment 3): ANY decline of the unit's SysTrans START ends the grace -- except a
    DUPLICATE copy's (the first START of that id is still in the book and may launch)."""
    return why != "duplicate"


def act_trance_rec_names(slot: int, actor_slot: int, actor_is_player: bool, tar_wire: int, magic_wire: int) -> bool:
    """NetSyncDiorama.ActTranceRecNames: a START names the wire slot as its actor (same side), or by a wire target or
    magic-caster bit (bits 0-3 the host's compacted players, 4-7 its enemy slots)."""
    if slot < 0 or slot > 7:
        return False
    if bool(actor_is_player) == (slot < 4) and int(actor_slot) == int(slot):
        return True
    return ((int(tar_wire) | int(magic_wire)) & (1 << int(slot))) != 0


def act_trance_passed(now_ms: int, from_ms: int, at_ms: int) -> bool:
    """NetSyncDiorama.ActTrancePassed (private): ``at_ms`` set, never after ``now_ms`` and no earlier than ``from_ms``."""
    return int(at_ms) >= 0 and int(at_ms) <= int(now_ms) and int(at_ms) >= int(from_ms)


def act_trance_on_arrival(now_ms: int, since_ms: int, hit_ms: int, decline_ms: int, end_ms: int) -> bool:
    """NetSyncDiorama.ActTranceOnArrival: the burst already PASSED at a sample -- the slot's SysTrans hit, its START's
    decline or its replay's end at most ActTranceGraceMs before ``now_ms`` (-1 = none) -- [fix: timing-3] or, for a record
    s135's life mask froze since ``since_ms`` (-1 = none), at most ActTranceGraceMs before that freeze began -- and never
    after ``now_ms``: the sample swaps at once."""
    base = int(since_ms) if 0 <= int(since_ms) < int(now_ms) else int(now_ms)
    from_ms = base - ACT_TRANCE_GRACE_MS
    return act_trance_passed(now_ms, from_ms, hit_ms) or act_trance_passed(now_ms, from_ms, decline_ms) \
        or act_trance_passed(now_ms, from_ms, end_ms)


def act_trance_step(record_ms: int, last_busy_ms: int, busy_now: bool, burst: bool, now_ms: int) -> int:
    """NetSyncDiorama.ActTranceStep -- THE GRACE (amendment 3, D3, audit 3.5's battle time): the unit's own burst in flight
    waits (no cap: it ends by its own bounds -- [fix: timing-1] or by THE BURST CEILING, ActTranceBurstMaxMs after the
    record); else the cap, ActTranceCapMs after the record, even while something names the unit; else it waits while
    something names it, then ActTranceGraceMs from the later of the record and the last frame it was named."""
    if burst:
        return ACT_TR_STEP_BURST_MAX if int(now_ms) - int(record_ms) >= ACT_TRANCE_BURST_MAX_MS else ACT_TR_STEP_WAIT
    if int(now_ms) - int(record_ms) >= ACT_TRANCE_CAP_MS:
        return ACT_TR_STEP_CAP
    if busy_now:
        return ACT_TR_STEP_WAIT
    return ACT_TR_STEP_GRACE if int(now_ms) - max(int(record_ms), int(last_busy_ms)) >= ACT_TRANCE_GRACE_MS \
        else ACT_TR_STEP_WAIT


def act_trance_verdict(gate: bool, leaving: bool, normal: bool, unit_ok: bool, wearing: bool, bit: bool, frozen: bool,
                       dead: bool, burst: bool, hit: bool, declined: bool, ended: bool, step: int) -> int:
    """NetSyncDiorama.ActTranceVerdict -- THE RESOLUTION of one pending deferral, in its order: a Leave drops, no unit drops,
    a matching model is moot, a slot s135's life mask freezes waits ([fix: model-2]), outside PHASE_NORMAL it waits, the
    gate falling swaps at once, the unit's own burst in flight waits (past THE BURST CEILING the cap swaps it: [fix:
    timing-1]), a decline of its SysTrans START swaps at once, then its replay's end or abort -- [fix: rmodel-1] a dead unit
    swaps by those rows (the host swaps a corpse at its own hit) and otherwise waits, never graced: dropped only at the cap
    with no ``hit`` of its own since the record -- then the cap, then the grace; else it waits."""
    if leaving:
        return ACT_TR_DROP_LEAVE
    if not unit_ok:
        return ACT_TR_DROP_UNIT
    if bool(wearing) == bool(bit):
        return ACT_TR_MOOT
    if frozen:
        return ACT_TR_WAIT
    if not normal:
        return ACT_TR_WAIT
    if not gate:
        return ACT_TR_SWAP_GATE
    if burst:
        return ACT_TR_SWAP_CAP if step == ACT_TR_STEP_BURST_MAX else ACT_TR_WAIT
    if declined:
        return ACT_TR_SWAP_DECLINE
    if ended:
        return ACT_TR_SWAP_END
    if dead:
        return ACT_TR_DROP_DEAD if step == ACT_TR_STEP_CAP and not hit else ACT_TR_WAIT
    if step == ACT_TR_STEP_CAP:
        return ACT_TR_SWAP_CAP
    if step == ACT_TR_STEP_GRACE:
        return ACT_TR_SWAP_GRACE
    return ACT_TR_WAIT


def act_trance_flush_verdict(leaving: bool, unit_ok: bool, wearing: bool, bit: bool, dead: bool, passed: bool,
                             burst_running: bool) -> int:
    """NetSyncDiorama.ActTranceFlushVerdict -- THE END INJECTION's flush of one pending deferral: a Leave drops, no unit
    drops, a matching model is moot; [fix: timing-2] its OWN SysTrans replay already running unhit waits (its hit or its end
    resolves it) -- [fix: rmodel-1] a corpse's too; a dead unit swaps only when its own burst ``passed`` since the record
    (hit, declined or ended: the host swapped it there), else it drops; else it swaps NOW (the pre-s137 guest already wore
    it)."""
    if leaving:
        return ACT_TR_DROP_LEAVE
    if not unit_ok:
        return ACT_TR_DROP_UNIT
    if bool(wearing) == bool(bit):
        return ACT_TR_MOOT
    if burst_running:
        return ACT_TR_WAIT
    if dead:
        return ACT_TR_SWAP_INJECT if passed else ACT_TR_DROP_DEAD
    return ACT_TR_SWAP_INJECT


def act_trance_hit_swaps(gate: bool, wearing: bool, bit: bool) -> bool:
    """NetSyncDiorama.ActTranceHitSwaps -- THE HIT (D2): a SysTrans replay's hit swaps its actor's model only under the gate,
    and only when the worn model differs from the mirrored bit (the stateless probe)."""
    return bool(gate) and bool(wearing) != bool(bit)


def act_trance_hit_trusts(frozen: bool, vfx_num: int, bit: bool) -> bool:
    """NetSyncDiorama.ActTranceHitTrusts -- (fix: model-1, model-2) the hit may TRUST the mirrored bit: not while s135's
    life mask freezes the slot, and not when the bit contradicts the replay's own vfx (the host chose an End from a clear
    bit, an Activate from a set one -- GetPlayerCommandSFX); any other vfx number is not judged."""
    if frozen:
        return False
    if int(vfx_num) == SPECIAL_TRANCE_END and bit:
        return False
    return not (int(vfx_num) == SPECIAL_TRANCE_ACTIVATE and not bit)


def act_trance_presents(end_injected: bool, leaving: bool, has_model: bool, fading: bool) -> bool:
    """NetSyncDiorama.ActTrancePresents -- THE PRESENT COLOUR's guard (amendment 5): never after an end injection, at a Leave,
    without a model or on a FADING enemy corpse -- [fix: model-3] a player corpse presents (stock's SysTrans finish)."""
    return not end_injected and not leaving and bool(has_model) and not fading


def act_trance_accounted(block: dict | None) -> bool | None:
    """The `act.guest.trance` block's identity: every deferral ends exactly once -- deferred == swaps_by_hit +
    swaps_by_grace + swaps_by_cap + swaps_by_decline + swaps_by_end + swaps_by_inject + moot + dropped + the bits of
    `pending` (wire slots 0-3). None for an absent or malformed block."""
    if not isinstance(block, dict):
        return None
    try:
        pending = int(block["pending"])
        return int(block["deferred"]) == sum(int(block[k]) for k in ACT_TRANCE_RESOLVED_KEYS) + bin(pending & 0xF).count("1")
    except (KeyError, TypeError, ValueError):
        return None


class ActTranceLane:
    """[ff9mapkit netsync s137] THE TRANCE BURST TIMING as NetSyncDiorama.Replay.cs runs it, with its statics -- the
    stand-in's model, owned by an :class:`ActGuestLane` (its battle clock, its book, its running replays, its hold, its
    log). MODELLED, through the twins above: ApplyUnit's model check (ActTranceAtSample, from the hold lane's ApplyUnit
    model: the `unit <slot> trance0|trance1` bench record and the catch-up -- a slot already pending keeps its record
    under the gate and resolves "gate" without it (fix: timing-4), the swap at the sample ungated (`immediate`), the
    START-first order (`on_arrival`: a hit, decline or end of the slot's SysTrans within 400 ms -- or since the record's
    freeze began, fix: timing-3), the record), the resolver every tick (ActTranceTick after the hold's tick: the busy rule --
    a queued or pending START naming the unit as actor, wire target or magic caster, a running replay acting with it
    (ActUnitsOf), a held or queued impact on its slot -- the burst (its own SysTrans START pending, or its replay running
    unhit), the frozen slot (s135's life mask, its skipped record: fix model-2), the unlinked unit (fix: stock-unlinked-swap),
    the verdict's whole order with the burst ceiling (fix: timing-1)), the hit (ActTranceOnHit at ActGuestLane's ActOnHit:
    the probe with the mirrored bit and its trust, `swaps_by_hit` / `hit_unpaired` / `hit_untrusted` / `moot`), a decline /
    NOOP of a SysTrans START (ActTranceOnDecline, a duplicate excepted), a SysTrans replay's end or abort
    (ActTranceOnReplayOver: the end mark, the present colour, the post-injection resolution: fix timing-2), the end
    injection's flush (ActTranceFlush at InjectEnd's head: a running burst left pending), the teardown (ActTranceDiscardAll:
    every pending one dropped, nothing applied, the summary line), the per-boot reset, the lever (`trancegrace on|off`, its
    role gate, ActBenchRelease's half), every counter, `last` and every Log.Message line -- the present colour's guard
    (counted: `present`) -- and a hidden unit's model kept hidden by every swap made outside a sequence (ActTranceSwap,
    fix: stock-hidden-swap: :attr:`active`, the worn model's SetActive state, False for a disappeared unit's kept swap);
    [fix: rmodel-1] a corpse's deferral waiting for its own burst (the verdict's `hit`, the flush's `passed`) and the death
    lane's on-arrival swap (ActTranceAtDeadSample: :meth:`at_dead_sample`); [fix: rstock-1] the renderer normalisation
    every s137 swap carries (ActTranceSetModel: :meth:`set_model`) against stock's renderer CACHE -- :attr:`rendering`, each
    model's renderers by (btl slot, model), and :attr:`cache`, the unit's meshIsRendering (ChangeModel resets it to True;
    :meth:`disp` is DispCharacter's mesh pass, which writes a renderer only when the cache differs; a truthy
    ``meshflags`` on the unit dict = every mesh flag-hidden).
    NOT MODELLED -- shapes, not engine data: the worn model is :attr:`worn` (by the unit's btl slot; a boot's units wear
    their normal model), a unit has a trance model when it is a player (a unit dict with ``trance_go`` False has none), a
    unit is hidden when its dict carries a truthy ``disappear`` (bi.disappear), the mirrored stat bit is the hold lane's
    :attr:`ActHoldLane.trance` (the reconciler's TRANCE lane -- a dead player's too, fix model-1 -- which the stand-in
    publishes in `battle.units[].status`), the swap itself (SetTranceModel: no mesh, no motion set, no weapon bones), the
    colours (SetPresentColor counted, never drawn), a SysTrans replay that falls through the short-circuit (the stock
    case's own SetTranceModel: the stand-in's tripwire counts it, the model stays), the horizon gate's freeze of the bit
    (the bench records are post-horizon by construction) and a fault (the 'a step faulted' line)."""

    def __init__(self, lane) -> None:
        self.lane = lane
        self.bench_off = False                   # `trancegrace off`: the pre-s137 timing (harness-scoped, never per boot)
        self.worn: dict = {}                     # (the stand-in's model: the worn model by unit btl slot; True = trance)
        self.active: dict = {}                   # (...and its SetActive state: False = kept hidden by ActTranceSwap)
        self.rendering: dict = {}                # [fix: rstock-1] each model's renderers, by (btl slot, model): True = on
        self.cache: dict = {}                    # ...and the unit's meshIsRendering cache (one flag: all meshes alike)
        self.reset(True)

    # -- the lever (its getter needs the selftest role, as the engine's)
    def on(self, role: bool) -> bool:
        """ActTranceGraceOn / HarnessTranceOn."""
        return not (self.bench_off and bool(role))

    def gate(self, role: bool) -> bool:
        """ActTranceGate: bit 5 latched this boot, a guest that can replay, the lever on."""
        return act_trance_defers(self.lane.bit5, self.lane.can_replay(role), self.on(role))

    def release(self) -> None:
        """ActBenchRelease's s137 half: the lever back (one line when it was pulled)."""
        if self.bench_off:
            self._log(LOG_TRANCE_LEVER_BACK)
        self.bench_off = False

    def bench(self, args: list, val: str) -> tuple:
        """HarnessActTranceBench (after HarnessActGuestBench's role gate) -> ``(ok, why)`` in the engine's words."""
        if len(args) != 3 or val not in ("on", "off"):
            return False, TRANCE_USAGE
        self.bench_off = val == "off"
        self._log(LOG_TRANCE_OFF if self.bench_off else LOG_TRANCE_ON)
        return True, None

    # -- the per-boot state
    def reset(self, counters: bool) -> None:
        """ActTranceReset: the pending deferrals and the burst marks always; the counters, the log budget and `last` with
        the boot block's counters (kept after the teardown until the next boot)."""
        self.pend = 0
        self.record_ms = [-1] * 4
        self.busy_ms = [-1] * 4
        self.want = [False] * 4
        self.hit_ms = [-1] * 4
        self.decline_ms = [-1] * 4
        self.end_ms = [-1] * 4
        self.apply_since = -1                    # [fix: timing-3] ActSampleApplied's _trApplySinceMs (the hold lane writes it)
        if not counters:
            return
        self.deferred = self.by_hit = self.by_grace = self.by_cap = self.by_decline = self.by_end = self.by_inject = 0
        self.moot = self.dropped = self.immediate = self.on_arrival = self.hit_unpaired = self.hit_untrusted = 0
        self.present = 0
        self.logged = 0
        self.err_logged = False
        self.last = None
        self.worn = {}                           # (the stand-in's unit shapes: a boot's new units wear their normal model)
        self.active = {}
        self.rendering = {}
        self.cache = {}

    def _log(self, text: str) -> None:
        self.lane._log(text)

    @property
    def now(self) -> int:
        return self.lane.now_ms

    # -- the stand-in's unit shapes
    @staticmethod
    def has_model(d) -> bool:
        """tranceGo != null && gameObject != null, as the stand-in models it: a player (``trance_go`` False: none)."""
        return d is not None and bool(d.get("player")) and d.get("trance_go", True) is not False

    def wears(self, d) -> bool:
        """gameObject == tranceGo (`battle.units[].trance_model`): False for a unit without a trance model."""
        return self.has_model(d) and bool(self.worn.get(int(d.get("slot", -1)), False))

    def bit_of(self, d) -> bool:
        """The unit's MIRRORED Trance stat bit (d.stat.cur): the reconciler's TRANCE lane, the hold lane's record of it."""
        return d is not None and bool(self.lane.hold.trance.get(int(d.get("slot", -1)), False))

    @staticmethod
    def hidden(d) -> bool:
        """bi.disappear != 0, as the stand-in models it: a truthy ``disappear`` on the unit dict."""
        return d is not None and bool(d.get("disappear"))

    def frozen(self, s: int, role: bool) -> bool:
        """ActTranceFrozen (fix: model-2): s135's life mask freezes wire slot ``s``'s bit -- masked, or its skipped record not
        yet caught up."""
        hold = self.lane.hold
        return act_life_skips(hold.life_mask, s, hold.lifeskip_on(role)) or s in hold.skipped

    def swap(self, d, bit: bool) -> None:
        """btl_vfx.SetTranceModel(d, bit) -- the stand-in: the worn model flips, and ChangeModel ACTIVATES it and resets the
        renderer CACHE to on (BTL_DATA.ChangeModel: meshIsRendering all-true -- the renderers themselves untouched)."""
        slot = int(d.get("slot", -1))
        self.worn[slot] = bool(bit)
        self.active[slot] = True
        self.cache[slot] = True

    # -- [fix: rstock-1] the renderers and stock's cache of them
    @staticmethod
    def flagged(d) -> bool:
        """geo.geoMeshChkFlags != 0 for every mesh, as the stand-in models it: a truthy ``meshflags`` on the unit dict."""
        return d is not None and bool(d.get("meshflags"))

    def renders(self, d) -> bool:
        """The WORN model's renderers on (the stand-in's: every mesh alike)."""
        slot = int(d.get("slot", -1))
        return bool(self.rendering.get((slot, bool(self.worn.get(slot, False))), True))

    def disp(self, d) -> None:
        """btlseq.DispCharacter's mesh pass (every frame, stock): SetIsEnabledMeshRenderer(m, flags clear) -- a write that
        lands only when the cache differs (BTL_DATA.cs: it returns early on the cache)."""
        slot = int(d.get("slot", -1))
        on = not self.flagged(d)
        if bool(self.cache.get(slot, True)) != on:
            self.rendering[(slot, bool(self.worn.get(slot, False)))] = on
            self.cache[slot] = on

    def set_model(self, d, bit: bool) -> None:
        """ActTranceSetModel (fix: rstock-1) -- EVERY s137 swap: the worn model's flag-disabled renderers back on before the
        swap (ActTranceShowWorn: ChangeModel deactivates it in the same call), SetTranceModel, then this frame's mesh flags
        written onto the incoming model past the reset cache (ActTranceApplyMeshFlags)."""
        slot = int(d.get("slot", -1))
        if not bool(self.cache.get(slot, True)):
            self.rendering[(slot, bool(self.worn.get(slot, False)))] = True
            self.cache[slot] = True
        self.swap(d, bit)
        on = not self.flagged(d)
        self.rendering[(slot, bool(bit))] = on
        self.cache[slot] = on

    def swap_kept(self, d, bit: bool) -> None:
        """ActTranceSwap (fix: stock-hidden-swap) -- every swap made outside a sequence: SetTranceModel (normalised: fix
        rstock-1, :meth:`set_model`), then a hidden unit's new model deactivated again (its own SetDisappear(false) shows it
        later)."""
        hidden = self.hidden(d)
        self.set_model(d, bit)
        if hidden:
            self.active[int(d.get("slot", -1))] = False

    def _linked(self, ctx: dict | None):
        return (ctx or {}).get("linked") or (lambda u: True)

    # -- the record (ActTranceAtSample: ApplyUnit's model check, with a probe that differs)
    def at_sample(self, d, slot: int, bit: bool, role: bool) -> None:
        """A slot already PENDING keeps its record under the gate -- and with the gate down resolves it here ("gate"; fix:
        timing-4); UNGATED -- the pre-s137 swap at the sample (`immediate`); gated, with the unit's burst already passed (since
        the record's freeze, fix: timing-3) -- at once (`on_arrival`); else RECORDED (`deferred`) for :meth:`tick`."""
        gate = self.gate(role)
        if 0 <= slot <= 3 and self.pend & (1 << slot):
            if gate:
                return
            self.swap_kept(d, bit)
            self.by_decline += 1
            self.present_on(d, None, self.lane.ctx_last)
            self.resolved(slot, True, bit, "gate", 0)
            return
        if slot < 0 or slot > 3 or not gate:
            self.swap(d, bit)
            self.immediate += 1
            self.present_on(d, None, self.lane.ctx_last)
            self.note(slot, True, bit, "immediate", 0, -1)
            return
        if act_trance_on_arrival(self.now, self.apply_since, self.hit_ms[slot], self.decline_ms[slot], self.end_ms[slot]):
            self.swap_kept(d, bit)
            self.on_arrival += 1
            self.present_on(d, None, self.lane.ctx_last)
            self.note(slot, True, bit, "on-arrival", 0, -1)
            return
        self.pend |= 1 << slot
        self.record_ms[slot] = self.now
        self.busy_ms[slot] = -1
        self.want[slot] = bool(bit)
        self.deferred += 1
        if self.logged >= ACT_TRANCE_LOG_MAX:
            return
        self.logged += 1
        self._log(f"{LOG_TRANCE_SLOT}{slot}'s {'trance' if bit else 'normal'}{LOG_TRANCE_WAITS}(the replay's hit; else "
                  f"{ACT_TRANCE_GRACE_MS} ms of battle time after nothing names the unit, at most {ACT_TRANCE_CAP_MS}"
                  f"{LOG_TRANCE_WAITS_TAIL}" + (LOG_TRANCE_FURTHER if self.logged == ACT_TRANCE_LOG_MAX else ""))

    def at_dead_sample(self, d, slot: int, bit: bool, role: bool) -> None:
        """ActTranceAtDeadSample (fix: rmodel-1) -- ApplyUnit's DEATH lane, its bit mirrored, the worn model differing: the
        on-arrival rule (a corpse whose own burst hit, declined or ended within the window -- or since the record's freeze --
        swaps now: the host's hit swapped it whatever its state). Gated only; a pending slot is the resolver's; an unlinked
        unit swaps nothing."""
        if slot < 0 or slot > 3 or not self.gate(role) or self.pend & (1 << slot):
            return
        if not self._linked(self.lane.ctx_last)(d):
            return
        if not act_trance_on_arrival(self.now, self.apply_since, self.hit_ms[slot], self.decline_ms[slot],
                                     self.end_ms[slot]):
            return
        self.swap_kept(d, bit)
        self.on_arrival += 1
        self.present_on(d, None, self.lane.ctx_last)
        self.note(slot, True, bit, "on-arrival", 0, -1)

    # -- the resolver (ActTranceTick: every tick, after the hold's)
    def tick(self, ctx: dict | None) -> None:
        if self.pend == 0:
            return
        ctx = ctx or {}
        normal = bool(ctx.get("steady"))
        role = bool(ctx.get("role", False))
        gate = self.gate(role)
        leaving = bool(ctx.get("leaving"))
        for s in range(4):
            if self.pend & (1 << s):
                self.step_slot(s, normal, gate, leaving, ctx)

    def busy_of(self, s: int, d) -> tuple:
        """ActTranceBusyOf -- THE BUSY RULE (amendment 3): (busy, burst) for wire slot ``s`` and its unit ``d``."""
        busy = burst = False
        for r in self.lane.book.queue:
            if not r.pending:
                continue
            if act_trance_rec_names(s, r.actor_slot, r.is_player, r.tar_id, r.magic_caster):
                busy = True
            if r.actor_slot == s and act_trance_is_burst(r.cmd_no, r.is_player, r.actor_slot):
                burst = True
        for r in self.lane.running:
            if self.lane._units_of(r) & int(d.get("id", 0)):
                busy = True
            if r.actor_slot == s and act_trance_is_burst(r.cmd_no, r.is_player, r.actor_slot) and r.first_hit_ms < 0:
                burst = True
        bit = 1 << s
        for h in list(self.lane.hold.held) + list(self.lane.hold.queued):
            if int(h.slots) & bit:
                busy = True
        if burst:
            busy = True
        return busy, burst

    def burst_running(self, s: int) -> bool:
        """ActTranceBurstRunning (fix: timing-2): the slot's OWN SysTrans replay runs and has not hit yet."""
        return any(r.actor_slot == s and act_trance_is_burst(r.cmd_no, r.is_player, r.actor_slot) and r.first_hit_ms < 0
                   for r in self.lane.running)

    def passed_since(self, s: int) -> bool:
        """ActTrancePassedSince (fix: rmodel-1): the pending slot's own burst passed since its record -- a SysTrans hit, a
        decline of its START or its replay's end or abort (the flush's ``passed``)."""
        rec = self.record_ms[s]
        return self.hit_ms[s] >= rec or self.decline_ms[s] >= rec or self.end_ms[s] >= rec

    def unit_of(self, s: int, ctx: dict):
        """ActTranceUnit: the pending slot's unit, with its trance model, still linked (fix: stock-unlinked-swap) -- None =
        none."""
        resolve = ctx.get("resolve") or (lambda i, p: None)
        d = resolve(s, True)
        return d if self.has_model(d) and self._linked(ctx)(d) else None

    def step_slot(self, s: int, normal: bool, gate: bool, leaving: bool, ctx: dict) -> None:
        """ActTranceStepSlot: the unit and its probe, what names it, the verdict -- then the swap (with the present colour)
        or the resolution without one."""
        d = self.unit_of(s, ctx)
        unit_ok = d is not None
        wearing = unit_ok and self.wears(d)
        bit = unit_ok and self.bit_of(d)
        dead = unit_ok and not d.get("alive", True)
        busy = burst = False
        if unit_ok:
            busy, burst = self.busy_of(s, d)
        if busy:
            self.busy_ms[s] = self.now
        step = act_trance_step(self.record_ms[s], self.busy_ms[s], busy, burst, self.now)
        v = act_trance_verdict(gate, leaving, normal, unit_ok, wearing, bit, self.frozen(s, bool(ctx.get("role", False))),
                               dead, burst, self.hit_ms[s] >= self.record_ms[s], self.decline_ms[s] >= self.record_ms[s],
                               self.end_ms[s] >= self.record_ms[s], step)
        if v == ACT_TR_WAIT:
            return
        if v == ACT_TR_MOOT:
            self.moot += 1
            self.resolved(s, False, bit, "moot", 0)
            return
        if v in (ACT_TR_DROP_LEAVE, ACT_TR_DROP_UNIT, ACT_TR_DROP_DEAD):
            self.dropped += 1
            self.resolved(s, False, bit, "leave" if v == ACT_TR_DROP_LEAVE else "unit" if v == ACT_TR_DROP_UNIT else "dead",
                          0)
            return
        self.swap_kept(d, bit)                   # the mirrored bit NOW (D2), as the reconciler's own swap (kept hidden)
        if v == ACT_TR_SWAP_GATE:
            self.by_decline += 1
            via = "gate"
        elif v == ACT_TR_SWAP_DECLINE:
            self.by_decline += 1
            via = "declined"
        elif v == ACT_TR_SWAP_END:
            self.by_end += 1
            via = "ended"
        elif v == ACT_TR_SWAP_CAP:
            self.by_cap += 1
            via = "cap"
        else:
            self.by_grace += 1
            via = "grace"
        self.present_on(d, None, ctx)
        self.resolved(s, True, bit, via, 0)

    # -- the hit, the decline, the end (ActTranceOnHit / ActTranceOnDecline / ActTranceOnReplayOver)
    def on_hit(self, r, role: bool) -> None:
        """ActTranceOnHit, for every hit of a SysTrans replay of a player: the burst's mark, then -- under the gate, when the
        worn model differs from the mirrored bit and that bit can be trusted (fix: model-1, model-2) -- the swap (a pending
        deferral `swaps_by_hit`; none pending `hit_unpaired`); an untrusted bit swaps nothing (`hit_untrusted`); a matching
        model resolves a pending deferral `moot`. An unlinked actor swaps nothing. Ungated the hit swaps nothing."""
        if r is None or not act_trance_is_burst(r.cmd_no, r.is_player, r.actor_slot):
            return
        s = int(r.actor_slot)
        self.hit_ms[s] = self.now
        d = getattr(r, "actor", None)
        if not self.has_model(d) or not self._linked(self.lane.ctx_last)(d):
            return
        pending = bool(self.pend & (1 << s))
        gate = self.gate(role)
        wearing, bit = self.wears(d), self.bit_of(d)
        if not act_trance_hit_swaps(gate, wearing, bit):
            if pending and gate:
                self.moot += 1
                self.resolved(s, False, bit, "moot", r.id)
            return
        frozen = self.frozen(s, role)
        if not act_trance_hit_trusts(frozen, r.vfx_num, bit):
            self.hit_untrusted += 1              # a stale or contradicting bit: no swap on it
            self.note(s, False, bit, "frozen" if frozen else "contradicted", r.id, -1)
            return
        self.set_model(d, bit)                   # the host's own swap point (its present colour follows at the replay's end);
        #                                          [fix: rstock-1] its renderers normalised (inside a mesh-flag hide too)
        if pending:
            self.by_hit += 1
            self.resolved(s, True, bit, "hit", r.id)
        else:
            self.hit_unpaired += 1
            self.note(s, True, bit, "hit", r.id, -1)

    def on_decline(self, r, why) -> None:
        """ActTranceOnDecline (ActDecline / ActMarkNoop): a decline of a player's SysTrans START (any reason but a duplicate
        copy) marks its slot."""
        if r is not None and act_trance_is_burst(r.cmd_no, r.is_player, r.actor_slot) and act_trance_decline_ends(why):
            self.decline_ms[int(r.actor_slot)] = self.now

    def on_replay_over(self, r, why, ctx: dict | None) -> None:
        """ActTranceOnReplayOver (ActFinishEnded: ``why`` None / ActAbort): a SysTrans replay is over -- its player slot's end
        mark, then stock's present colour on its actor (never after an end injection, at a Leave, on a fading enemy or an
        unlinked unit) -- and (fix: timing-2), after an end injection, the deferral the flush left for this burst resolves
        here (`swaps_by_end`)."""
        if r is None or int(r.cmd_no) != CMD_SYS_TRANS:
            return
        burst = act_trance_is_burst(r.cmd_no, r.is_player, r.actor_slot)
        if burst:
            self.end_ms[int(r.actor_slot)] = self.now
        ctx = ctx or self.lane.ctx_last or {}
        d = getattr(r, "actor", None)
        if d is not None and self._linked(ctx)(d):
            self.present_on(d, why, ctx)
        if burst and ctx.get("end_injected") and self.pend & (1 << int(r.actor_slot)):
            self.end_after_inject(int(r.actor_slot), why, r.id, ctx)

    def end_after_inject(self, s: int, why, act_id: int, ctx: dict) -> None:
        """ActTranceEndAfterInject (fix: timing-2): the flush's own verdict (its burst no longer running), the swap counted
        `swaps_by_end` -- no present colour (the tails own the units)."""
        d = self.unit_of(s, ctx)
        unit_ok = d is not None
        wearing = unit_ok and self.wears(d)
        bit = unit_ok and self.bit_of(d)
        v = act_trance_flush_verdict(why == "leave" or bool(ctx.get("leaving")), unit_ok, wearing, bit,
                                     unit_ok and not d.get("alive", True), self.passed_since(s), False)
        if v == ACT_TR_MOOT:
            self.moot += 1
            self.resolved(s, False, bit, "moot", act_id)
        elif v != ACT_TR_SWAP_INJECT:
            self.dropped += 1
            self.resolved(s, False, bit, "leave" if v == ACT_TR_DROP_LEAVE else "unit" if v == ACT_TR_DROP_UNIT else "dead",
                          act_id)
        else:
            self.swap_kept(d, bit)
            self.by_end += 1
            self.resolved(s, True, bit, "ended", act_id)

    # -- the end injection and the teardown
    def flush(self, ctx: dict | None) -> None:
        """ActTranceFlush -- InjectEnd's head (every inject path, still in PHASE_NORMAL): every pending deferral swaps by the
        probe NOW (`swaps_by_inject`; ActTranceFlushVerdict) -- except one whose own SysTrans replay runs unhit (fix:
        timing-2): left pending for its hit or its end."""
        if self.pend == 0:
            return
        ctx = ctx or self.lane.ctx_last or {}
        leaving = bool(ctx.get("leaving"))
        for s in range(4):
            if not self.pend & (1 << s):
                continue
            d = self.unit_of(s, ctx)
            unit_ok = d is not None
            wearing = unit_ok and self.wears(d)
            bit = unit_ok and self.bit_of(d)
            v = act_trance_flush_verdict(leaving, unit_ok, wearing, bit, unit_ok and not d.get("alive", True),
                                         self.passed_since(s), self.burst_running(s))
            if v == ACT_TR_WAIT:
                continue
            if v == ACT_TR_MOOT:
                self.moot += 1
                self.resolved(s, False, bit, "moot", 0)
            elif v != ACT_TR_SWAP_INJECT:
                self.dropped += 1
                self.resolved(s, False, bit, "leave" if v == ACT_TR_DROP_LEAVE else "unit" if v == ACT_TR_DROP_UNIT else
                              "dead", 0)
            else:
                self.swap_kept(d, bit)
                self.by_inject += 1
                self.present_on(d, None, dict(ctx, end_injected=False))   # (before the injection writes its phase)
                self.resolved(s, True, bit, "inject", 0)

    def discard_all(self, why: str) -> None:
        """ActTranceDiscardAll (ActDiscardAll, before its state reset): every pending deferral DROPPED ("teardown") -- nothing
        applied -- and one summary line when the boot did anything."""
        for s in range(4):
            if self.pend & (1 << s):
                self.dropped += 1
                self.resolved(s, False, self.want[s], "teardown", 0)
        if self.deferred + self.immediate + self.on_arrival + self.hit_unpaired + self.hit_untrusted == 0:
            return
        self._log(f"{LOG_TRANCE_SUMMARY}{why}) -- {self.deferred} deferred ({self.by_hit} at the hit, {self.by_grace} by the "
                  f"grace, {self.by_cap} by the cap, {self.by_decline} by a decline, {self.by_end} at the burst's end, "
                  f"{self.by_inject} at the end injection, {self.moot} moot, {self.dropped} dropped), {self.immediate} "
                  f"immediate, {self.on_arrival} on arrival, {self.hit_unpaired} unpaired hit(s), {self.hit_untrusted} "
                  f"untrusted hit(s); {self.present} present colour(s)")

    # -- the present colour, the resolution, `last` and the line
    def present_on(self, d, why, ctx: dict | None) -> None:
        """ActTrancePresent: SetPresentColor behind ActTrancePresents (``why`` = an abort's reason) -- counted; a FADING
        enemy corpse is guarded (fix: model-3: a player corpse presents)."""
        ctx = ctx or {}
        if d is None or not act_trance_presents(bool(ctx.get("end_injected")), why == "leave" or bool(ctx.get("leaving")),
                                                True, not d.get("player") and not d.get("alive", True)):
            return
        self.present += 1

    def resolved(self, slot: int, swapped: bool, to: bool, via: str, act_id: int) -> None:
        """ActTranceResolved: the slot leaves `pending`; `last` and one line (capped)."""
        record_ms = self.record_ms[slot] if 0 <= slot <= 3 else -1
        if 0 <= slot <= 3:
            self.pend &= ~(1 << slot)
            self.record_ms[slot] = -1
            self.busy_ms[slot] = -1
        self.note(slot, swapped, to, via, act_id, record_ms)

    def note(self, slot: int, swapped: bool, to: bool, via: str, act_id: int, record_ms: int) -> None:
        """ActTranceNote: `last` and the line (capped per boot)."""
        self.last = {"slot": int(slot), "swapped": bool(swapped), "to": bool(to), "via": via, "id": int(act_id),
                     "record_ms": int(record_ms), "ms": int(self.now)}
        if self.logged >= ACT_TRANCE_LOG_MAX:
            return
        self.logged += 1
        self._log(f"{LOG_TRANCE_SLOT}{slot}" + (f" -> the {'trance' if to else 'normal'} model" if swapped else
                                                LOG_TRANCE_KEEPS)
                  + f" ({via}" + (f", replay id {act_id}" if act_id > 0 else "")
                  + (f", {self.now - record_ms}{LOG_TRANCE_AFTER}" if record_ms >= 0 else "") + f"; battle ms {self.now})"
                  + (LOG_TRANCE_FURTHER if self.logged == ACT_TRANCE_LOG_MAX else ""))

    # -- the published block
    def doc(self, *, role: bool, booted: bool) -> dict:
        """HarnessAgent.AppendActGuestTrance -- `act.guest.trance`, in every role."""
        return {"on": self.on(role), "gate": bool(booted) and self.gate(role), "deferred": self.deferred,
                "pending": self.pend, "swaps_by_hit": self.by_hit, "swaps_by_grace": self.by_grace,
                "swaps_by_cap": self.by_cap, "swaps_by_decline": self.by_decline, "swaps_by_end": self.by_end,
                "swaps_by_inject": self.by_inject, "moot": self.moot, "dropped": self.dropped,
                "immediate": self.immediate, "on_arrival": self.on_arrival, "hit_unpaired": self.hit_unpaired,
                "hit_untrusted": self.hit_untrusted, "present": self.present,
                "last": dict(self.last) if self.last is not None else None}


#: NetSyncDiorama.Replay.cs's s137 integer constants, by C# name (the pin, both ways -- test_harness_netsync.py reads every
#: `internal const Int32` the s137 patch declares, comments stripped).
CS_TRANCE_CONSTANTS = {
    "ActTranceGraceMs": ACT_TRANCE_GRACE_MS, "ActTranceCapMs": ACT_TRANCE_CAP_MS,
    "ActTranceBurstMaxMs": ACT_TRANCE_BURST_MAX_MS, "ActTranceLogMax": ACT_TRANCE_LOG_MAX,
    "ActTrStepWait": ACT_TR_STEP_WAIT, "ActTrStepGrace": ACT_TR_STEP_GRACE, "ActTrStepCap": ACT_TR_STEP_CAP,
    "ActTrStepBurstMax": ACT_TR_STEP_BURST_MAX,
    "ActTrWait": ACT_TR_WAIT, "ActTrMoot": ACT_TR_MOOT, "ActTrDropLeave": ACT_TR_DROP_LEAVE,
    "ActTrDropUnit": ACT_TR_DROP_UNIT, "ActTrDropDead": ACT_TR_DROP_DEAD, "ActTrSwapGate": ACT_TR_SWAP_GATE,
    "ActTrSwapDecline": ACT_TR_SWAP_DECLINE, "ActTrSwapEnd": ACT_TR_SWAP_END, "ActTrSwapCap": ACT_TR_SWAP_CAP,
    "ActTrSwapGrace": ACT_TR_SWAP_GRACE, "ActTrSwapInject": ACT_TR_SWAP_INJECT}


# ================================================================================================ s138
# [ff9mapkit netsync s138] THE DRESS INSTRUMENT (studies/battle-coop/R3-DESIGN.md 3.4.2 as amended by R3-FIELD-MODEL-AUDIT.md
# 2.1 amendments 3-8 and 13, and its 3.1 key design): harness keys only -- no behaviour on any role. Three homes:
#   * `player.*` (OUTSIDE netsync, after `control`): the s90 THREE CASES -- an ABSENT key is an engine that cannot publish
#     the body (s137 and older), null is one that can and has no controlled actor this sample, anything else is the raw
#     value. `anim` is the clip ID (`battle.units[].anim` is a NAME); `clip` is that id's NAME (AnimationDB, the same
#     derivation as `netsync.dress.ghost.clip`). `body` and `anim_geo` are the two WITNESSES a dress cannot compute: the
#     worn texture's GEO-id stem, and the folder of the clip the Animation component ACTUALLY plays.
#   * `objects[].model` (after `sid`): PosObj.model, a plain field read (raw: MODEL_NONE = no SetModel yet).
#   * `netsync.dress` (netsync's LAST key, after `battle`): `ghost` (a FIXED sub-object, always whole: what the peer's ghost
#     WEARS on this screen) then `party` (the four slots' raw CharacterId). s139 appends `codec`, `rig_idle_frames` and its
#     levers at the end of `ghost`; s140 appends `self`; s141 adds keys only inside `self`.

#: AppendPlayerDress's keys, in its order (HarnessAgent.cs WritePlayerDress, right after `control`) -- s138's, and the whole
#: player block's: the audit's amendment 5 publishes every key s139-s141 judge NOW, so no later rung adds a player key (the
#: level home, fakegame.NETSYNC_PLAYER_CAP_KEYS, holds one row; a test pins the live writer against its ladder).
PLAYER_DRESS_KEYS = ("model", "anim", "geo", "anim_geo", "eye", "uid", "sid", "body", "clip", "clip_playing", "frame_n",
                     "anim_frame", "meshflags")
#: AppendObjects' s138 key (right after `sid`).
OBJECT_DRESS_KEYS = ("model",)
#: PosObj.model's constructor default (PosObj.cs:16): no SetModel has run yet -- updateModelsToBeAdded's own "no model" test.
MODEL_NONE = 65535
#: `netsync.dress.ghost` at its sentinels, in AppendDress's order: no ghost (or no NetSyncClient instance) -- the LIVE union
#: (s139 appends its levers at the end of `ghost`: bench_mask, empty_mask, rule, wire, mode). What a probe or a stand-in
#: holds a given rung to is that rung's FROZEN row, :data:`DRESS_GHOST_KEYS_BY_RUNG` -- never this live union (an s138
#: engine publishes six keys whatever s139 adds here).
DRESS_GHOST_SENTINELS = {"model": -1, "geo": None, "clip": None, "rig": -1, "playing": False, "body": None,
                         # [ff9mapkit netsync s139] the selftest `selfdress` levers AS SET (-1 / null = off), `mode`, then the
                         # ghost's VISIBILITY (the rest mask's witness: -1 / null = no ghost)
                         "bench_mask": -1, "empty_mask": -1, "rule": None, "wire": -1, "wire_anim": -1, "mode": None,
                         "rest_mask": -1, "shown_mask": -1, "hidden": None,
                         # [ff9mapkit netsync s141] the mapconfig row the ghost's tint used (ApplyGhostLighting: the ghost
                         # model's own row, else the LOCAL player's stand-in row -- its netDressSrc when dressed and the
                         # polish is on, else its model -- else 65535); -1 = no re-tint this field load; then the tint it
                         # WROTE, read back off the ghost's first renderer's `_Color` (null = no ghost / no renderer)
                         "light_row": -1, "light_rgb": None}
#: [ff9mapkit netsync s138] Each dress rung's OWN `ghost` keys, frozen at its patch, in AppendDress's order -- the rows the
#: bench probe (coop_self_dress.probe), the stand-in's per-rung ghost (fakegame) and the s138 patch pin read; only the
#: live-catch pins read the union (:data:`DRESS_GHOST_SENTINELS`). s139 adds its row ("dresshost": its five levers).
DRESS_GHOST_KEYS_BY_RUNG = {"dressinstr": ("model", "geo", "clip", "rig", "playing", "body"),
                            # [ff9mapkit netsync s139] its levers at the END of `ghost` (AppendDress), then `mode`, then the
                            # ghost's visibility
                            "dresshost": ("bench_mask", "empty_mask", "rule", "wire", "wire_anim", "mode", "rest_mask",
                                          "shown_mask", "hidden"),
                            # [ff9mapkit netsync s141] the ghost's lighting row and the tint it wrote, at the END of `ghost`
                            # (after `hidden`)
                            "dresspolish": ("light_row", "light_rgb")}
#: `netsync.dress.party`'s two non-member values: an EMPTY slot (FF9.party.member[i] null) and an UNREADABLE one (its read
#: threw: AppendDress's Try fallback) -- never read -2 as an empty seat the engine's ResolveAuto saw. The catch line's
#: [-1 x 4] means the whole block failed to build.
PARTY_EMPTY = -1
PARTY_UNREADABLE = -2
#: [ff9mapkit netsync s140] `netsync.dress.self` at its sentinels, in AppendDressSelf's order (a FIXED sub-object: always
#: whole, never null, in EVERY role -- a host reads its sentinels; s141 appends its polish keys after `selftest`). Counts 0,
#: ids -1, booleans false, strings null; `law_off` a FIXED sub-object of four falses (the `law` lever AS SET, one per law).
DRESS_SELF_LAW_OFF_KEYS = ("bframe", "attach", "alias", "timeline")
DRESS_SELF_SENTINELS = {"knob": False, "armed": False, "src": -1, "want_model": -1, "want_char": -1, "want_rig": -1,
                        "rig": -1, "why": None, "uid": -1, "net_byte": -1, "from": None, "confirmed": 0,
                        "ctl_elsewhere": 0, "ctl_elsewhere_field": -1, "skip_npc": 0, "skip_second": 0, "remaps": 0,
                        "timeline_kept": 0, "gate": False, "bframe_remaps": 0, "src_attached": 0, "src_list_clips": 0,
                        "attach_cold": 0, "attach_warm": 0, "faults": 0, "parse_fallback": 0, "defence_kept": 0,
                        "defence_dropped": 0, "bench_self": None,
                        "law_off": dict.fromkeys(DRESS_SELF_LAW_OFF_KEYS, False), "selftest": None}
#: [ff9mapkit netsync s141] THE DRESS POLISH's keys inside `netsync.dress.self`, after `selftest` -- AppendDressPolish's
#: order and sentinels (audit 3.1's table + the orchestrator's `attach_last` and `polish`): `steps` [] (the engine's OWN
#: footstep table filtered to the controlled uid, [anim, frame, sndEffectID[0]] triples -- never null live), the per-load
#: counts 0, `light_row` -1, `light_rgb` null (a nullable list; the body's OWN first mesh renderer's `_Color`),
#: `light_floor` -1 (the floor fldmcf lit the body by: light_rgb's oracle input), `attach_last` a FIXED sub-object written whole (its
#: `parent` a nullable string: the carried go's LIVE transform.parent name) and `polish` false (the lever AS SET; its live
#: default is true -- the house rule for a boolean sentinel, as s140's `knob` / `gate`). :data:`DRESS_SELF_SENTINELS`
#: stays s140's own frozen row; the LIVE `self` is the two in order (:data:`DRESS_SELF_KEYS_BY_RUNG`).
DRESS_POLISH_ATTACH_LAST_KEYS = ("uid", "bone_in", "bone_out", "parent")
DRESS_POLISH_SENTINELS = {"steps": [], "steps_dropped": 0, "steps_passed": 0, "steps_fired": 0, "steps_fired_player": 0,
                          "light_row": -1, "light_rgb": None, "light_floor": -1, "mesh_drops": 0, "attach_remaps": 0,
                          "attach_notes": 0,
                          "attach_last": {"uid": -1, "bone_in": -1, "bone_out": -1, "parent": None}, "polish": False}
DRESS_POLISH_KEYS = tuple(DRESS_POLISH_SENTINELS)
#: [ff9mapkit netsync s141] Each rung's OWN keys inside `netsync.dress.self`, frozen at its patch (the stand-in publishes its
#: rungs' rows; the live catch the union, in this order): s140 AppendDressSelf's, s141 AppendDressPolish's.
DRESS_SELF_KEYS_BY_RUNG = {"dressself": tuple(DRESS_SELF_SENTINELS), "dresspolish": DRESS_POLISH_KEYS}


def _copy_sentinel(v):
    return dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v


#: [ff9mapkit netsync s141] the LIVE `netsync.dress.self` at its sentinels: s140's keys, then s141's polish keys.
DRESS_SELF_LIVE_SENTINELS = {**{k: _copy_sentinel(v) for k, v in DRESS_SELF_SENTINELS.items()},
                             **{k: _copy_sentinel(v) for k, v in DRESS_POLISH_SENTINELS.items()}}
#: `netsync.dress` at the catch line's sentinels (its SECOND literal): `ghost`, then `party` ([-1 x 4]: the block failed).
#: The live `party` is a LIVE read of FF9.party.member[i].Index (PARTY_EMPTY / PARTY_UNREADABLE as above) -- never
#: NetSyncParty.Slots, where the selftest mirror seats its "BENCH" stand-in (the s134 lesson).
DRESS_SENTINELS = {"ghost": dict(DRESS_GHOST_SENTINELS), "party": [-1, -1, -1, -1],
                   # [ff9mapkit netsync s139] after `party`: the codec proof's verdict (null until it ran), the rig rows'
                   # idle frame counts (-1 = not measured) and the party mirror an old reader landed (null = none) --
                   # [ff9mapkit netsync s140] thirteen rows on s140+ (an s139 engine's catch line has nine)
                   "codec": None, "rig_idle_frames": [-1] * 13, "mirror_party": None,
                   # [ff9mapkit netsync s140] `self`, the guest's own dress -- `dress`'s LAST key
                   # [ff9mapkit netsync s141] ...with the polish keys after `selftest` (the LIVE catch line)
                   "self": {k: _copy_sentinel(v) for k, v in DRESS_SELF_LIVE_SENTINELS.items()}}
#: [ff9mapkit netsync s139] Each dress rung's OWN `netsync.dress` keys, frozen at its patch (the stand-in publishes its rungs'
#: rows; the live catch the union): s138 `ghost` / `party`, s139 `codec` / `rig_idle_frames` / `mirror_party`
#: (fakegame.NETSYNC_DRESS_CAP_KEYS is the same ladder; a test pins both against the catch lines). [ff9mapkit netsync s140]
#: + `self` (a fixed sub-object, :data:`DRESS_SELF_SENTINELS`).
DRESS_KEYS_BY_RUNG = {"dressinstr": ("ghost", "party"), "dresshost": ("codec", "rig_idle_frames", "mirror_party"),
                      "dressself": ("self",),                    # [ff9mapkit netsync s140] `self`, after `mirror_party`
                      # [ff9mapkit netsync s141] no new `netsync.dress` key: the polish keys sit INSIDE `self` and `ghost`
                      # (:data:`DRESS_SELF_KEYS_BY_RUNG`, :data:`DRESS_GHOST_KEYS_BY_RUNG`)
                      "dresspolish": ()}
#: [ff9mapkit netsync s138] THE DRESS PROBE LADDER: the key each dress patch is told by (R3-FIELD-MODEL-AUDIT.md 3.1 names
#: them) -- s138 its own fixed `ghost`, s139 `codec` (appended to `netsync.dress`), s140 `self` (a fixed sub-object), s141
#: `self.steps` (a key inside it). An engine is the HIGHEST rung whose key it publishes, every rung below present too.
DRESS_PROBES = {138: "netsync.dress.ghost", 139: "netsync.dress.codec", 140: "netsync.dress.self",
                141: "netsync.dress.self.steps"}
#: NetSyncClient.FallbackGeo: what EnsureGhost BUILDS when the asked-for id does not resolve or load (`ghost.geo`).
GHOST_FALLBACK_GEO = "GEO_MAIN_F0_ZDN"
#: THE RIG SPACE (`ghost.rig`; s140's `self.rig`): -1 = undressed / no ghost, 0-7 = the CharacterId rows (Zidane ..
#: Amarant), 8 = the moogle (s139). Rig 8 is NOT CharacterId 8 (Cinna): decode through this table, never compare a rig
#: with a CharacterId when it reads 8. [ff9mapkit netsync s140] 9-12 = CharacterId 8-11 IN CHARACTERID ORDER (9 Cinna, 10
#: Marcus, 11 Blank, 12 Beatrix -- the owner's "their own models"): rig 9 is Cinna, CharacterId 9 is Marcus -- the ONLY
#: bridges are :func:`char_to_rig` / :func:`rig_to_char`.
RIG_NONE = -1
RIG_MOOGLE = 8
RIG_NAMES = ("zidane", "vivi", "garnet", "steiner", "freya", "quina", "eiko", "amarant", "moogle",
             "cinna", "marcus", "blank", "beatrix")                # [ff9mapkit netsync s140] rows 9-12


def rig_name(rig) -> str | None:
    """A dress rig's name (:data:`RIG_NAMES`); None for -1 / anything outside 0-12 / a non-int."""
    if isinstance(rig, bool) or not isinstance(rig, int) or not 0 <= rig < len(RIG_NAMES):
        return None
    return RIG_NAMES[rig]


def folder_of(clip) -> str | None:
    """NetSyncVisitor.FolderOf (s138), case for case: the GEO folder a clip NAME loads from, by
    AnimationFactory.AddAnimWithAnimatioName's OWN rule -- "GEO_" + tokens 1-3 of the '_'-split name
    ("ANH_MAIN_F0_ZDN_IDLE" -> "GEO_MAIN_F0_ZDN"). None for a null or empty name, or one of fewer than 4 tokens; never
    raises. NOT GetAnimationFolder (a path-table remap with a latent KeyNotFound). Two traps for a reader: anim 0 is
    ANH_MAIN_F0_STN_B (never judge a folder at anim 0), and ids 200 and 324 share ANH_MAIN_F0_ZDN_IDLE (classify by NAME)."""
    if not isinstance(clip, str) or clip == "":
        return None
    token = clip.split("_")
    if len(token) < 4:
        return None
    return "GEO_" + token[1] + "_" + token[2] + "_" + token[3]


def texture_stem(name) -> str | None:
    """NetSyncVisitor.TextureStem (s138), case for case: the GEO-id stem of a model texture's NAME -- the text before its
    first '_' ("98_0" / "98_1" -> "98" Zidane, "192_0" -> "192" Freya, "220_0" -> "220" the moogle). A name with no '_',
    or one that starts with it, is its own stem; None for a null or empty name; never raises."""
    if not isinstance(name, str) or name == "":
        return None
    cut = name.find("_")
    return name if cut <= 0 else name[:cut]


#: HarnessAgent.BodyOf's mesh: the actor root's DIRECT child of this name (PosObj.SetIsEnabledMeshRenderer's own rule;
#: ModelImporter names an external model's meshes mesh{i} too).
BODY_MESH = "mesh0"


def body_of(renderers) -> str | None:
    """HarnessAgent.BodyOf (s138) as a rule over a body's renderers IN UNITY'S DEPTH-FIRST ORDER -- ``[(path, texture name),
    ...]``, each path relative to the actor root ("battle_model/battle_model0", "bone000/.../mesh0", "mesh0"): the texture
    stem of the root's DIRECT child :data:`BODY_MESH` when it has a renderer, else of the FIRST renderer; None with no
    renderer, or an unnamed texture (None / "" -- a loose-FBX or CustomModelField body: "cannot judge"). NEVER the first
    renderer when mesh0 is there: on Zidane (98) that is the hidden Orichalcum overlay battle_model0, and on the other rigs
    the bone subtree is walked first -- a prop GeoAttach parents under a bone would be read as the body."""
    rows = [r for r in (renderers or ()) if isinstance(r, (tuple, list)) and len(r) == 2]
    if not rows:
        return None
    pick = next((r for r in rows if r[0] == BODY_MESH), rows[0])
    return texture_stem(pick[1])


def eye_of(eye_byte: int) -> int:
    """PosObj.eye from SetModel's eye byte: ``po.eye = -4 * getv1()`` (DoEventCode.cs SetModel) -- Zidane's 93 -> -372."""
    return -4 * int(eye_byte)


# ================================================================================================ s139
# [ff9mapkit netsync s139] THE HOST'S DRESS RULE AND WIRE SECTION 8 (studies/battle-coop/R3-DESIGN.md 3.4.3 as amended by
# R3-FIELD-MODEL-AUDIT.md 2.2 and 3.1-3.3, with the owner's two decisions of 2026-10-17 -- D1 Option A: the host's GhostAs is
# the one knob for both screens and the position frame is unchanged; D2: a spectating guest, GuestSlots 0, is the MOOGLE).
# Every function below is the PURE C# rule of the same name in NetSyncVisitor.cs (same parameters, same answers), pinned by
# test_harness_netsync.py to the s139 patch's lines and to NetSyncClient.DressSelfTest's rows (evaluated here off the
# stack). HOST-SIDE: the host's ghost of its guest takes the s139 rule; a client keeps the s138 rule (resolve_dress_s138).

#: THE FULL RIG TABLE, NetSyncVisitor.Rigs (the s139 patch's nine rows, the moogle row 8), each column as the audit's census
#: fills it (R3-FIELD-MODEL-AUDIT.md 2.2 amendment 2: every value checked against all 817 field-script exports and the
#: clips in p0data5). A test pins these rows to the patch's text AND to the kit's playerswap.CHARACTERS (model, eye, idle,
#: walk, run, left, right) with literals for the moogle row and the new columns. Columns:
#:   eye        SetModel's eye byte (po.eye = -4 x eye)
#:   inactive   the idle-break clip; 0 = NONE (EventEngine CheckSleep's own `p.sleep == 0` test -- never "the idle")
#:   walk_step_a/b, run_step_a/b   the footfall frames (RunModelCode(16, clip, frame)); -1 = none (Quina, the moogle)
#:   step_sound the step-sound override (Steiner 925); 0 = keep the source key's id
#:   idle_alias the second id naming the same idle clip (classify by NAME)
#:   hand_bone / hand_bone_end   R_hand / R_hand_end (s141's prop remap) -- [ff9mapkit netsync s141] the INSTALL's pair, never
#:              labels_for (one bone toward the shoulder on Steiner's and Amarant's arms): the skin's hand (the right arm's
#:              third skinned bone) and its end (the next bone, else the hand), checked against stock's own AttachObject on
#:              each body (polish.json e_hands) -- Steiner 15 / 16 (was 14 / 15), Amarant 16 / 16 (was 15 / 16)
RIG_COLUMNS = ("model", "idle", "walk", "run", "turn_l", "turn_r", "eye", "inactive", "walk_step_a", "walk_step_b",
               "run_step_a", "run_step_b", "step_sound", "idle_alias", "hand_bone", "hand_bone_end")
RIGS = (
    (98, 200, 25, 38, 40, 41, 93, 57, 4, 13, 0, 8, 0, 324, 12, 13),                 # 0 Zidane
    (8, 148, 571, 419, 917, 918, 61, 912, 4, 14, 0, 9, 0, 573, 16, 17),             # 1 Vivi
    (185, 2089, 2086, 2091, 2088, 2084, 91, 3160, 4, 15, 0, 9, 0, 2090, 14, 15),    # 2 Garnet
    (5489, 2001, 1996, 2005, 1986, 2010, 104, 119, 4, 14, 0, 9, 925, 2002, 15, 16),  # 3 Steiner (s141: hand 15 / 16)
    (192, 2556, 2553, 2558, 2555, 2551, 94, 0, 4, 16, 0, 9, 0, 2557, 12, 12),        # 4 Freya
    (273, 3228, 3237, 3230, 3235, 3227, 92, 0, -1, -1, -1, -1, 0, 3229, 13, 14),     # 5 Quina
    (443, 7503, 7518, 7506, 7516, 7514, 63, 9590, 1, 13, 0, 9, 0, 7504, 14, 15),     # 6 Eiko
    (509, 8307, 8316, 8312, 8310, 8314, 122, 0, 6, 23, 10, 21, 0, 8308, 16, 16),     # 7 Amarant (s141: hand 16 / 16, a leaf)
    (220, 2904, 2927, 2907, 2923, 2911, 50, 0, -1, -1, -1, -1, 0, 2905, 19, 19),     # 8 the MOOGLE
    # [ff9mapkit netsync s140] OWNER (2026-10-17): CharacterId 8-11 get "their own models" -- each row ONLY from the install's
    # census (studies/battle-coop/dress-census/rigs_8_11.json `rows`; a test pins these to it AND to the s140 patch)
    (107, 470, 761, 105, 104, 107, 87, 0, -1, -1, -1, -1, 0, 101, 24, 25),          # 9  Cinna   (CharacterId 8)
    (109, 474, 367, 365, 368, 364, 100, 0, 4, 18, 0, 10, 0, 363, 5, 6),             # 10 Marcus  (CharacterId 9)
    (5467, 462, 5225, 5222, 5223, 5224, 87, 0, 7, 18, 6, 16, 0, 5221, 13, 14),      # 11 Blank   (CharacterId 10)
    (204, 2978, 2975, 2981, 2980, 2974, 100, 0, 7, 18, 6, 16, 0, 2977, 15, 16),     # 12 Beatrix (CharacterId 11)
)
#: the rig space's bounds (NetSyncVisitor): the CharacterId rows 0-7 guard the PARTY path (CharacterId 8 is Cinna, never the
#: moogle row); RIG_ROW_COUNT = Rigs.Length (`netsync.dress.rig_idle_frames` has one value per row); the named path guards on
#: it, so `GhostAs = moogle` dresses. [ff9mapkit netsync s140] MAIN_RIG_COUNT now means only "the 8 mains" (the CLIENT's s138
#: cap, party and names); the HOST's party path and section 8 go through char_to_rig / rig_to_char. RIG_ROW_COUNT is the LIVE
#: table's (13 on s140+: `rig_idle_frames` publishes 13 entries); an s139 engine's is RIG_ROW_COUNT_S139 (:data:`S139`).
MAIN_RIG_COUNT = 8
RIG_ROW_COUNT = 13
RIG_ROW_COUNT_S139 = 9                   # [ff9mapkit netsync s140] the s139 engine's Rigs.Length (rig_idle_frames: 9)
#: [ff9mapkit netsync s141] the s139 patch's OWN nine rows, frozen: s141 corrected two hand pairs IN PLACE (rlook-1 / 2:
#: Steiner 14 / 15 -> 15 / 16, Amarant 15 / 16 -> 16 / 16 -- s139's were labels_for reads, one bone toward the shoulder),
#: so the s139 view keeps s139's literals (no s139 or s140 path reads the hand columns: s141's prop remap is their consumer)
RIG_HAND_FIX_S141 = {3: ((14, 15), (15, 16)), 7: ((15, 16), (16, 16))}
RIGS_S139 = tuple(r[:14] + RIG_HAND_FIX_S141[i][0] if i in RIG_HAND_FIX_S141 else r
                  for i, r in enumerate(RIGS[:RIG_ROW_COUNT_S139]))
SUB_RIG_FIRST = 9                        # [ff9mapkit netsync s140] rig 9 = CharacterId 8 (Cinna) .. rig 12 = 11 (Beatrix)
SUB_CHAR_FIRST = 8                       # [ff9mapkit netsync s140] CharacterId 8, the first non-main with a rig
SUB_RIG_COUNT = 4                        # [ff9mapkit netsync s140] Cinna, Marcus, Blank, Beatrix
MOOGLE_MODEL = 220                       # GEO_NPC_F0_MOG
PLAIN_ZIDANE_MODEL = 98                  # GEO_MAIN_F0_ZDN: the body an undressed (s117 / SelfDress=0) guest sends
CHAR_NONE = 0xFF                         # CharacterId.NONE: section 8's charId for the moogle and for no dress
#: NetSyncVisitor.NameToRig (the named path; s139 adds `moogle`): the kit's ff9mapkit.coop.GHOST_NAMES are exactly its keys.
#: [ff9mapkit netsync s140] + cinna / marcus / blank / beatrix (rows 9-12): the HOST's named path (`< Rigs.Length`) dresses
#: them, a client's s138 cap at the mains refuses them.
NAME_TO_RIG = {"zidane": 0, "vivi": 1, "garnet": 2, "dagger": 2, "steiner": 3, "freya": 4, "quina": 5, "eiko": 6,
               "amarant": 7, "salamander": 7, "moogle": 8, "cinna": 9, "marcus": 10, "blank": 11, "beatrix": 12}
#: NetSyncVisitor's loco classes (the wire's rig-neutral locomotion byte).
LOCO_OTHER, LOCO_IDLE, LOCO_WALK, LOCO_RUN, LOCO_TURN_L, LOCO_TURN_R = range(6)
#: Section 8 (NetSyncVisitor.SectionDress): the host's type-5 state frame's dress section, right after section 7 --
#: NetSyncState uses 0 and 4-7 and NetSyncParty 1-3, so 8 was free. Its body is always DRESS_BODY_LEN bytes.
SECTION_STORY, SECTION_PARTY, SECTION_KEY_ITEMS, SECTION_BAG = 0, 1, 2, 3
SECTION_INTENT, SECTION_EVENT, SECTION_TALK, SECTION_DIALOG, SECTION_DRESS = 4, 5, 6, 7, 8
DRESS_BODY_LEN = 3
STORY_LEN = 2048                         # NetSyncState.StoryLen: ApplyStoryTo applies an id-0 section of exactly this
STORY_MASK = (2032, 2041)                # ...outside MaskLo..MaskHi (the coop cells: never carried)
#: The selftest proof block's s139 lines (NetSyncClient: right after the s137 trance line), in its order.
PROOF_DRESS = "dress codec selftest: "   # NetSyncClient.DressSelfTest
#: 4 rig + 1 auto table + 2 named / mode + 1 s138 + 2 guard / anim + 1 role + 1 charId + 2 codec + 1 producer + 11 frame /
#: wire / old-guest (sections 5 and 7, the absent-id reads that cross section 8, section 8 itself, the story, the party with
#: its key items and bag, a section AFTER section 8) / truncation / forward + 3 mutants -- s139's 29.
#: [ff9mapkit netsync s140] 38 on s140+: + rows 9-12 = the census, every row's clips in its own folder, the CharToRig /
#: RigToChar map, the `sub` guard / loco / anim row, Cinna..Beatrix's hand-checked bytes, the guest's charId check, and the
#: mains-cap / charId / acceptance mutants (the CharacterId-as-rig mutant replaces s139's Rigs.Length one).
DRESS_SELFTEST_ROWS = 38
DRESS_SELFTEST_ROWS_S139 = 29
PROOF_DRESS_SECTION = "dress section 8 as this machine would host now: "    # + DressSectionText(HostDressSection())
PROOF_RIG_IDLE = "dress rig idle frames: "      # + one int per rig row + " (<n> of <rows> measured)" (9 on s139, 13 on s140)
#: `netsync.dress.codec`'s two verdict shapes (null until the proof ran): "ok", or "fail: <the first failing row's name>".
DRESS_CODEC_OK = "ok"
DRESS_CODEC_FAIL = "fail: "
#: `netsync.dress.ghost.mode`: "bench:auto" while the `ghost` lever holds (the selftest role), else "ini:" + the ini's
#: GhostAs as read (trimmed -- "ini:" = none); null = no NetSyncClient instance.
DRESS_MODE_BENCH = "bench:auto"
DRESS_MODE_INI = "ini:"
#: The `selfdress` ops (NetSyncClient.HarnessSelfDress), in its "unknown op" refusal's order, and its rule values.
#: [ff9mapkit netsync s140] the LIVE list: s139's five + `self` / `gate` / `law` (the guest's own dress, NetSyncSelfDress) --
#: an s139 engine prints SELFDRESS_OPS_S139 (no `polish`: that is s141's, an s140 engine answers it "unknown op").
SELFDRESS_OPS_S139 = ("ghost", "empty", "rule", "wire", "clear")
SELFDRESS_SELF_OPS = ("self", "gate", "law")
#: [ff9mapkit netsync s141] s140's eight (its "unknown op" list -- an s140 engine answers `polish` with it), then the LIVE
#: list: + `polish` (the dress polish's calibration lever, NetSyncSelfDress.TrySetPolish).
SELFDRESS_OPS_S140 = SELFDRESS_OPS_S139 + SELFDRESS_SELF_OPS
SELFDRESS_POLISH_OPS = ("polish",)
SELFDRESS_OPS = SELFDRESS_OPS_S140 + SELFDRESS_POLISH_OPS
SELFDRESS_RULES = ("s138", "s139")


def rig_row(rig) -> dict | None:
    """One rig row as {column: value} (:data:`RIG_COLUMNS`); None outside the table (TryGetRig: 0-12 on s140)."""
    if isinstance(rig, bool) or not isinstance(rig, int) or not 0 <= rig < len(RIGS):
        return None
    return dict(zip(RIG_COLUMNS, RIGS[rig]))


def rig_for_model(model) -> int:
    """NetSyncVisitor.RigForModel: the rig row wearing ``model`` (the moogle included), -1 for any other model."""
    for i, row in enumerate(RIGS):
        if row[0] == model:
            return i
    return -1


def classify_loco(model, anim) -> int:
    """NetSyncVisitor.ClassifyLoco (SENDER side): ``anim``'s rig-neutral loco class on ``model``'s rig -- LOCO_OTHER for a
    model with no rig or a clip that is no loco clip (a gesture, a break clip: Zidane's 57)."""
    r = rig_row(rig_for_model(model))
    if r is None:
        return LOCO_OTHER
    for col, loco in (("idle", LOCO_IDLE), ("walk", LOCO_WALK), ("run", LOCO_RUN), ("turn_l", LOCO_TURN_L),
                      ("turn_r", LOCO_TURN_R)):
        if anim == r[col]:
            return loco
    return LOCO_OTHER


def loco_anim(rig_idx, loco) -> int:
    """NetSyncVisitor.LocoAnim (RECEIVER side): ``rig_idx``'s clip for a loco class (OTHER and IDLE -> its idle); 0 outside
    the rig space."""
    r = rig_row(rig_idx)
    if r is None:
        return 0
    return {LOCO_WALK: r["walk"], LOCO_RUN: r["run"], LOCO_TURN_L: r["turn_l"], LOCO_TURN_R: r["turn_r"]}.get(loco,
                                                                                                         r["idle"])


def dress_mode(ghost_as) -> str:
    """NetSyncVisitor.DressMode: a GhostAs value trimmed and lower-cased (None -> "")."""
    return ("" if ghost_as is None else str(ghost_as)).strip().lower()


def dress_mode_off(mode) -> bool:
    """NetSyncVisitor.DressModeOff: "", "off" and "0" (and None) dress nothing."""
    return mode is None or mode in ("", "off", "0")


def moogle_when_empty(role, self_test_role: bool) -> bool:
    """NetSyncVisitor.MoogleWhenEmpty -- POSITIVE and read at call time: the host or the selftest role (IsSelfTestRole:
    enabled AND role "selftest"). A client, a typo'd role (Role=guest runs the selftest branch without being the selftest
    role) and a disabled selftest are never the moogle -- ``role != "client"`` would hand the typo the moogle."""
    return role == "host" or bool(self_test_role)


def _slot_char(slot_char, slot: int) -> int:
    """NetSyncVisitor.SlotCharOf: a slot's CharacterId off a party read -- PARTY_UNREADABLE (-2) when there is no read (None)
    or no such slot, -1 for an empty one."""
    if slot_char is None or not 0 <= slot < len(slot_char):
        return PARTY_UNREADABLE
    v = slot_char[slot]
    return v if isinstance(v, int) and not isinstance(v, bool) else -1


def resolve_auto_core(mask: int, moogle_when_empty_: bool, slot_char, char_to_rig_) -> tuple:
    """NetSyncVisitor.ResolveAutoCore -> (model, rig). [ff9mapkit netsync s140] s139's ``party_cap`` int is now
    ``char_to_rig_``, the party path's CharacterId -> rig MAP (:func:`char_to_rig` in production): a null map, or a rig
    outside the table, reads as "no rig" -- undressed, never the moogle. The selftest's mutants pass "the CharacterId IS the
    rig" (Cinna in the moogle suit) and s139's cap at the mains, and the auto table must catch both."""
    mask = int(mask) & 0x0F                            # party slots 0-3 only
    if mask:
        for slot in range(4):
            if not mask & (1 << slot):
                continue
            char = _slot_char(slot_char, slot)
            if char == PARTY_UNREADABLE:
                return 0, -1                           # a read that threw (or no party read): undressed, NEVER the moogle
            if char < 0:
                continue                               # an EMPTY named slot: the next named one
            rig = char_to_rig_(char) if char_to_rig_ is not None else -1   # [ff9mapkit netsync s140] never `char` as a rig
            if not isinstance(rig, int) or rig < 0 or rig >= len(RIGS):
                return 0, -1                           # a custom character (12+): no rig -> the wire body
            return RIGS[rig][0], rig
    if not moogle_when_empty_:                         # mask 0 (OWNER D2: a spectator) or every named slot empty
        return 0, -1
    return MOOGLE_MODEL, RIG_MOOGLE


def resolve_auto(mask: int, moogle_when_empty_: bool, slot_char) -> tuple:
    """NetSyncVisitor.ResolveAuto(mask, moogleWhenEmpty, slotChar) -> (model, rig), in its rule order: (1) mask 0 -- a
    SPECTATING guest -- the MOOGLE (220, rig 8) when ``moogle_when_empty_`` (OWNER D2: "moogle. 2 zidanes just looks weird,
    and the host will never be a moogle."), else 0; (2) the FIRST OCCUPIED named slot decides: a main (0-7) its row,
    [ff9mapkit netsync s140] Cinna..Beatrix (8-11) their rows 9-12 (the owner's "their own models"; s139: undressed), a
    custom member (12+) 0, an empty named slot skipped, an UNREADABLE one (-2: its read threw) 0 -- a party-read fault never
    wears the moogle; (3) every named slot empty: the moogle when allowed, else 0. ``slot_char`` is the four slots' raw
    CharacterId (-1 = empty, -2 = unreadable; None = no party read at all: every slot unreadable)."""
    return resolve_auto_core(mask, moogle_when_empty_, slot_char, char_to_rig)


def resolve_named(mode, cap: int) -> tuple:
    """NetSyncVisitor.ResolveNamed -> (model, rig): a NameToRig name whose row is below ``cap`` its row; anything else (0,
    -1). The s139 host rule passes RIG_ROW_COUNT (`GhostAs = moogle` dresses), the s138 rule MAIN_RIG_COUNT (a client and
    the `rule s138` lever: no moogle by name -- the host is never a moogle)."""
    rig = NAME_TO_RIG.get(mode) if isinstance(mode, str) else None
    if rig is None or not 0 <= rig < min(int(cap), len(RIGS)):
        return 0, -1
    return RIGS[rig][0], rig


def resolve_dress_rule(ghost_as, mask: int, moogle_when_empty_: bool, slot_char) -> tuple:
    """NetSyncVisitor.ResolveDressRule -- THE s139 RULE -> (model, rig): GhostAs "" / off / 0 dress nothing; "auto" is
    :func:`resolve_auto`; a name is :func:`resolve_named`. Guard-free (the guard is :func:`ghost_guard`, the caller's)."""
    mode = dress_mode(ghost_as)
    if dress_mode_off(mode):
        return 0, -1
    if mode == "auto":
        return resolve_auto(mask, moogle_when_empty_, slot_char)
    return resolve_named(mode, len(RIGS))


def resolve_dress_s138(ghost_as, mask: int, slot_char) -> tuple:
    """NetSyncVisitor.ResolveDressS138 -- THE s138 RULE (a CLIENT's dress of the host's ghost; the selftest's `selfdress
    rule s138` lever) -> (model, rig): "auto" = the FIRST named bit, no skip, no moogle (an empty first named slot or a
    member 8+ -> 0); a name -> :func:`resolve_named` capped at the mains (`moogle` dresses nothing: byte for byte s138)."""
    mode = dress_mode(ghost_as)
    if dress_mode_off(mode):
        return 0, -1
    if mode != "auto":
        return resolve_named(mode, MAIN_RIG_COUNT)
    mask = int(mask)
    if mask == 0:
        return 0, -1
    slot = 0
    while slot < 4 and not mask & (1 << slot):
        slot += 1
    if slot >= 4:
        return 0, -1
    char = _slot_char(slot_char, slot)
    if char < 0 or char >= MAIN_RIG_COUNT:
        return 0, -1
    return RIGS[char][0], char


def ghost_guard(dress_model: int, wire_model: int) -> int:
    """NetSyncVisitor.GhostGuard: keep the dress on a plain-Zidane wire body (98: an s117 guest, or an opted-out SelfDress=0
    one -- owner D1) or one already wearing it (an s140 guest); any other wire body (a Steiner-led guest, ZDD 532) shows
    as it is (0 = undressed)."""
    if not dress_model:
        return 0
    return dress_model if wire_model in (PLAIN_ZIDANE_MODEL, dress_model) else 0


def ghost_anim(dress_model: int, dress_rig: int, wire_model: int, wire_loco: int, wire_anim: int) -> int:
    """NetSyncVisitor.GhostAnim: a dress on a body OTHER than the wire's plays the dressed rig's loco clip for the wire's
    loco class; a ghost on the wire's OWN body plays the RAW wire anim (a gesture or a break clip is never flattened)."""
    if dress_model and dress_model != wire_model:
        return loco_anim(dress_rig, wire_loco)
    return wire_anim


def dress_char_id(model: int, rig_idx: int) -> int:
    """NetSyncVisitor.DressCharId: section 8's charId -- the row of a MAIN (0-7), else CHAR_NONE (the moogle, no dress).
    [ff9mapkit netsync s140] through :func:`rig_to_char`: Cinna..Beatrix's rigs 9-12 ship CharacterId 8-11 (never the rig
    index -- rig 9 is Cinna, CharacterId 9 Marcus); the moogle, no dress and a rig outside the table ship 0xFF."""
    return rig_to_char(rig_idx) if model and isinstance(rig_idx, int) and rig_idx >= 0 else CHAR_NONE


def dress_section_body(model: int, char_id: int) -> bytes:
    """NetSyncVisitor.DressSectionBody: [model u16 LE][charId u8] -- (192, 4) C0 00 04, (220, FF) DC 00 FF, (0, FF) 00 00 FF."""
    return bytes((int(model) & 0xFF, (int(model) >> 8) & 0xFF, int(char_id) & 0xFF))


def parse_dress_section(body) -> tuple | None:
    """NetSyncVisitor.TryParseDressSection -> (model, charId), or None for a null or truncated (< 3 B) body; a longer body
    reads its first 3 bytes (the forward rule)."""
    if body is None or len(body) < DRESS_BODY_LEN:
        return None
    return body[0] | (body[1] << 8), body[2]


def dress_section_text(body) -> str:
    """NetSyncClient.DressSectionText -- how the proof block logs a section-8 body: "DC 00 FF (model 220, charId 255)";
    "malformed" for a body its reader refuses."""
    got = parse_dress_section(body)
    if got is None:
        return "malformed"
    return f"{body[0]:02X} {body[1]:02X} {body[2]:02X} (model {got[0]}, charId {got[1]})"


def host_dress_section(ghost_as, guest_slots: int, role, selftest_role: bool, slot_char) -> bytes:
    """NetSyncClient.HostDressSection's body (Enabled): the s139 rule for the HOST's config -- its GhostAs and GuestSlots
    (the forced selftest pins GuestSlots 0; the `ghost` lever never reaches it, the `empty` lever does: ``slot_char``),
    never guarded (section 8 carries the dress itself). The mode is read first and the party only for `auto` (HostDress)."""
    mode = dress_mode(ghost_as)
    model, rig = (0, -1) if dress_mode_off(mode) else resolve_dress_rule(
        mode, guest_slots, moogle_when_empty(role, selftest_role), slot_char if mode == "auto" else None)
    return dress_section_body(model, dress_char_id(model, rig))


def live_slot_chars(party, empty_mask: int = 0) -> list:
    """NetSyncVisitor.LiveSlotChars over a party read (``party`` = the four slots' raw CharacterId, -1 / None empty, -2
    UNREADABLE -- `netsync.dress.party`'s own values): ``empty_mask``'s slots (the `selfdress empty` lever) read EMPTY; an
    unreadable slot stays -2 (never an empty seat)."""
    seats = (list(party or ()) + [-1] * 4)[:4]
    out = []
    for i, v in enumerate(seats):
        if (int(empty_mask) >> i) & 1:
            out.append(-1)
        elif isinstance(v, int) and not isinstance(v, bool) and v == PARTY_UNREADABLE:
            out.append(PARTY_UNREADABLE)
        elif not isinstance(v, int) or isinstance(v, bool) or v < 0:
            out.append(-1)
        else:
            out.append(v)
    return out


# ---- the section framing an OLD guest walks (NetSyncState.cs / NetSyncParty.cs, untouched since s103)
def append_section(frame: bytes, section_id: int, body) -> bytes:
    """NetSyncState.AppendSection: [id u8][len u16 LE][body] appended; a null or EMPTY body is a no-op (why section 8 is
    never empty: "absent" must stay distinct from "model 0")."""
    if not body:
        return bytes(frame or b"")
    return bytes(frame or b"") + bytes((section_id & 0xFF, len(body) & 0xFF, (len(body) >> 8) & 0xFF)) + bytes(body)


def walk_sections(payload) -> tuple:
    """A type-5 payload's sections as the engine frames them -> ([(id, body), ...], truncated): walked while 3 header
    bytes remain; a section whose length runs past the end stops the walk (``truncated`` True)."""
    out, off, data = [], 0, bytes(payload or b"")
    while off + 3 <= len(data):
        sid, ln = data[off], data[off + 1] | (data[off + 2] << 8)
        if off + 3 + ln > len(data):
            return out, True
        out.append((sid, data[off + 3:off + 3 + ln]))
        off += 3 + ln
    return out, False


def old_apply_story(payload) -> bytes | None:
    """NetSyncState.ApplyStoryTo's walk (an s117 guest's): the 2048-byte story it would land (outside the coop-cell mask;
    those bytes read 0 here), or None when no id-0 section of exactly STORY_LEN applied before the walk stopped."""
    target, applied = bytearray(STORY_LEN), False
    for sid, body in walk_sections(payload)[0]:
        if sid == SECTION_STORY and len(body) == STORY_LEN:
            for i in range(STORY_LEN):
                if i < STORY_MASK[0] or i > STORY_MASK[1]:
                    target[i] = body[i]
            applied = True
    return bytes(target) if applied else None


def old_try_read_section(payload, section_id: int) -> bytes | None:
    """NetSyncState.TryReadSection: the FIRST section with ``section_id``; None when it is absent OR a truncated section
    comes before it (the whole payload refused)."""
    off, data = 0, bytes(payload or b"")
    while off + 3 <= len(data):
        sid, ln = data[off], data[off + 1] | (data[off + 2] << 8)
        if off + 3 + ln > len(data):
            return None
        if sid == section_id:
            return data[off + 3:off + 3 + ln]
        off += 3 + ln
    return None


def old_party_sections(payload) -> list:
    """NetSyncParty.ParseSections' walk: the sections 1-3 it consumes, in order, as (id, body) -- every other id skipped by
    length, the walk stopped at a truncation (the bodies' own parse is not twinned here)."""
    return [(sid, body) for sid, body in walk_sections(payload)[0]
            if sid in (SECTION_PARTY, SECTION_KEY_ITEMS, SECTION_BAG)]


def decode_dress(payload) -> tuple | None:
    """Section 8 of a host type-5 payload, as an s140+ guest reads it: (model, charId); None when the host sent none (an
    s138-or-older host) or its body is truncated -- the caller tells "absent" (no id 8) from "malformed" by
    :func:`old_try_read_section`."""
    return parse_dress_section(old_try_read_section(payload, SECTION_DRESS))


#: NetSyncParty's section-1 seat: [present u8] then, when present, CharId, Serial, Level, Row (u8 x4), CurHp, MaxHp, CurMp,
#: MaxMp (u32 x4), Equip (u16 x5), [name len u8][name], then the v9 block -- BasisMaxHp, BasisMaxMp (u32 x2), Dex, Str, Mgc,
#: Wpr (u8 x4), BasisMaxCapa (u32), Status (u64), Trance (u8), [SA count u8][SA ids u32 x n].
_SEAT_HEAD = 4 + 16 + 10
_SEAT_V9 = 8 + 4 + 4 + 8 + 1


def party_slot_chars(body) -> list | None:
    """[ff9mapkit netsync s139] NetSyncParty.ParseParty's walk over a section-1 body -> the four seats' CharId (-1 = an absent
    seat), or None when the body is malformed (ParseParty's own refusals). The CharId byte is PLAYER.info.slot_no -- the
    host's PLAYER.Index, the very value its LiveSlotChars reads -- so a frame's own party is what its section 8 must agree
    with (coop_peer.py dress)."""
    data, off, out = bytes(body or b""), 0, []
    end = len(data)
    for _ in range(4):
        if off >= end:
            return None
        present = data[off] != 0
        off += 1
        if not present:
            out.append(-1)
            continue
        if off + _SEAT_HEAD + 1 > end:
            return None
        out.append(data[off])
        off += _SEAT_HEAD
        name_len = data[off]
        off += 1 + name_len
        if off > end or off + _SEAT_V9 + 1 > end:
            return None
        off += _SEAT_V9
        sa = data[off]
        off += 1 + 4 * sa
        if off > end:
            return None
    return out


def frame_slot_chars(payload) -> list | None:
    """The host's party as one type-5 payload carries it (its FIRST section 1, :func:`party_slot_chars`); None when the frame
    has no readable section 1."""
    body = old_try_read_section(payload, SECTION_PARTY)
    return None if body is None else party_slot_chars(body)


# ---- [ff9mapkit netsync s139] THE GHOST'S VISIBILITY (the rest mask's witness: `ghost.rest_mask` / `shown_mask` / `hidden`)
#: ModelFactory.garnetShortHairTable: the GEOs whose field load hides one of Garnet's two hairstyles.
GARNET_SHORT_HAIR_GEOS = ("GEO_MAIN_F0_GRN", "GEO_MAIN_F1_GRN", "GEO_MAIN_B0_002", "GEO_MAIN_B0_003", "GEO_MAIN_B0_004",
                          "GEO_MAIN_B0_005", "GEO_MON_B3_149")
#: FF9StateSystem.EventState.ScenarioCounter from which `GarnetHair = 0` (the default) wears the SHORT hair.
GARNET_SHORT_HAIR_SCENARIO = 10300


def garnet_short_hair(garnet_hair, scenario) -> bool:
    """ModelFactory.CreateModel's hair choice: [Graphics] GarnetHair 1 = long, 2 = short, anything else (0, the default) =
    short from ScenarioCounter 10300 on."""
    if garnet_hair == 1:
        return False
    if garnet_hair == 2:
        return True
    return int(scenario) >= GARNET_SHORT_HAIR_SCENARIO


def field_hides(geo, transforms, renderers, *, garnet_hair=0, scenario=0) -> list:
    """ModelFactory.CreateModel's FIELD-MODE hides (isBattle false), as a rule over a prefab -- ``transforms``: every
    transform's path under the root in depth-first pre-order (the root itself excluded); ``renderers``: the renderers' paths
    in GetComponentsInChildren order. GetChildByName(name) is the FIRST transform of that name, depth-first; every renderer in
    its subtree (itself included) is disabled. Garnet's GEOs (GARNET_SHORT_HAIR_GEOS) hide `long_hair` when she wears the
    short hair (:func:`garnet_short_hair`), else `short_hair`; every model hides `battle_model`. -> the hidden renderers'
    paths, in renderer order."""
    roots = []
    if geo in GARNET_SHORT_HAIR_GEOS:
        roots.append("long_hair" if garnet_short_hair(garnet_hair, scenario) else "short_hair")
    roots.append("battle_model")
    picked = []
    for name in roots:
        first = next((t for t in transforms if t.rsplit("/", 1)[-1] == name), None)
        if first is not None:
            picked.append(first)
    return [r for r in renderers if any(r == p or r.startswith(p + "/") for p in picked)]


def visibility_mask(renderers, hidden) -> int:
    """The bit mask (bit i = renderer i, at most 16 -- ApplyGhostMask's reach) of the renderers NOT in ``hidden``."""
    hid = set(hidden or ())
    return sum(1 << i for i, r in enumerate(list(renderers)[:16]) if r not in hid)


# ---- THE SELFTEST DRESS SITE (NetSyncClient's selftest branch, s139): the mirror IS the guest, this machine its host
def selftest_dress(*, ghost_as, guest_slots: int, me_model: int, me_anim: int, party, role="selftest",
                   selftest_role: bool = True, enabled: bool = True, bench_mask: int = -1, empty_mask: int = -1,
                   rule=None, wire: int = -1, wire_anim: int = -1) -> dict:
    """What the selftest mirror's ghost WEARS and PLAYS this frame (NetSyncClient's selftest dress site, s139, its
    `selfdress` levers read on the selftest role only) -> {"model", "rig", "anim", "mask"}: ``model`` is EnsureGhost's
    model (the dress, else the wire body), ``rig`` its rig (-1 undressed), ``anim`` DriveGhost's clip id, ``mask`` which
    renderer mask applies ("local" the player's own -- index-valid on its own model only --, "rest" CreateModel's own hides
    (the rest mask), "all" every renderer: the `rule s138` lever re-asserts 0xFFFF on a body that is not the player's).
    ``party`` is the four slots' raw CharacterId (-1 empty, -2 unreadable). The `wire` lever stands in for the mirror's wire
    body: it moves with ITS rig's clip for my loco, where it has a rig -- or, with ``wire_anim`` (`wire <model> <anim>`),
    PLAYS that raw clip, its loco byte that clip's class on that body (as a real guest's sender classifies it).
    [ff9mapkit netsync s140] the LIVE engine's site (rows 9-12 in the table: Cinna..Beatrix dress, 107 / 109 / 5467 / 204
    classify); an s139 engine's is :data:`S139`'s ``selftest_dress``."""
    return _selftest_dress_in(sys.modules[__name__], ghost_as=ghost_as, guest_slots=guest_slots, me_model=me_model,
                              me_anim=me_anim, party=party, role=role, selftest_role=selftest_role, enabled=enabled,
                              bench_mask=bench_mask, empty_mask=empty_mask, rule=rule, wire=wire, wire_anim=wire_anim)


def _selftest_dress_in(R, *, ghost_as, guest_slots: int, me_model: int, me_anim: int, party, role="selftest",
                       selftest_role: bool = True, enabled: bool = True, bench_mask: int = -1, empty_mask: int = -1,
                       rule=None, wire: int = -1, wire_anim: int = -1) -> dict:
    """[ff9mapkit netsync s140] :func:`selftest_dress` over one stage's rules ``R`` (this module = the live engine, or
    :data:`S139`): its rig table, ClassifyLoco / RigForModel / LocoAnim and the host rule ResolveDressRule."""
    bench = bool(selftest_role)
    st_wire = wire if bench and wire >= 0 else me_model
    pinned = bench and wire >= 0 and wire_anim >= 0
    st_loco = R.classify_loco(st_wire, wire_anim) if pinned else R.classify_loco(me_model, me_anim)
    wire_rig = R.rig_for_model(st_wire)
    wire_anim = (wire_anim if pinned else me_anim if st_wire == me_model
                 else R.loco_anim(wire_rig, st_loco) if wire_rig >= 0 else me_anim)
    st_mask = bench_mask if bench and bench_mask >= 0 else guest_slots
    st_mode = "auto" if bench and bench_mask >= 0 else ghost_as
    old_rule = bench and rule == "s138"
    chars = live_slot_chars(party, empty_mask if bench and empty_mask >= 0 else 0)
    dress, rig = 0, -1
    if enabled:
        if old_rule:
            dress, rig = resolve_dress_s138(st_mode, st_mask, chars)
        else:
            m, rig = R.resolve_dress_rule(st_mode, st_mask, moogle_when_empty(role, selftest_role), chars)
            dress = ghost_guard(m, st_wire)
    if dress == 0:
        rig = -1
    model = dress if dress else st_wire
    if old_rule:
        anim = R.loco_anim(rig, st_loco) if dress else wire_anim
        mask = "local" if (dress == 0 and st_wire == me_model) or dress == me_model else "all"
    else:
        anim = R.ghost_anim(dress, rig, st_wire, st_loco, wire_anim)
        if dress == 0 or dress == st_wire:
            mask = "local" if st_wire == me_model else "rest"
        elif dress == me_model:
            mask = "local"
        else:
            mask = "rest"
    return {"model": model, "rig": rig, "anim": anim, "mask": mask}


# ---- DressSelfTest's rows, the OFFLINE half (rows 1-15 and the mutants: the rows 16-26 need a real host frame -- in game)
DRESS_PARTY4 = (0, 1, 2, 3)                               # Zidane, Vivi, Garnet, Steiner
#: ResolveAuto's row table (DressAutoTable, in its order): (name, mask, moogle_when_empty, slot_char, model, rig) -- the
#: production rule passes every row; each mutant fails one. [ff9mapkit netsync s140] AS THE s139 PATCH WROTE IT (frozen:
#: Cinna..Beatrix undressed) -- the live s140 table is :data:`DRESS_AUTO_TABLE`.
DRESS_AUTO_TABLE_S139 = (
    ("mask 0 -> the moogle on the host / selftest (owner D2)", 0, True, DRESS_PARTY4, 220, 8),
    ("mask 0 -> undressed on a client", 0, False, DRESS_PARTY4, 0, -1),
    ("slot 1 named -> its member (Vivi, 8)", 2, True, DRESS_PARTY4, 8, 1),
    ("slot 0 named -> Zidane (98)", 1, True, DRESS_PARTY4, 98, 0),
    ("an empty first named slot -> the next named member", 6, True, (0, -1, 2, -1), 185, 2),
    ("every named slot empty -> the moogle (host / selftest)", 6, True, (0, -1, -1, -1), 220, 8),
    ("every named slot empty -> undressed on a client", 6, False, (0, -1, -1, -1), 0, -1),
    ("Cinna (CharacterId 8) -> undressed, never the moogle row", 2, True, (0, 8, -1, -1), 0, -1),
    ("Blank (10) -> undressed", 2, True, (0, 10, -1, -1), 0, -1),
    ("a custom character (12) -> undressed", 2, True, (0, 12, -1, -1), 0, -1),
    ("the first OCCUPIED named slot decides (Cinna before Vivi)", 6, True, (0, 8, 1, -1), 0, -1),
    ("bits above slot 3 are no party slots", 0x12, True, DRESS_PARTY4, 8, 1),
    ("an UNREADABLE named slot (-2) -> undressed, never the moogle", 6, True, (0, -1, -2, -1), 0, -1),
    ("no party read -> unreadable: undressed, never the moogle", 2, True, None, 0, -1),
)
#: [ff9mapkit netsync s140] THE LIVE TABLE (s140's DressAutoTable, in its order): OWNER (2026-10-17) -- Cinna..Beatrix wear
#: their own rows 9-12 whatever the moogle predicate; a custom member (12+) stays undressed, never the next slot.
DRESS_AUTO_TABLE = (
    ("mask 0 -> the moogle on the host / selftest (owner D2)", 0, True, DRESS_PARTY4, 220, 8),
    ("mask 0 -> undressed on a client", 0, False, DRESS_PARTY4, 0, -1),
    ("slot 1 named -> its member (Vivi, 8)", 2, True, DRESS_PARTY4, 8, 1),
    ("slot 0 named -> Zidane (98)", 1, True, DRESS_PARTY4, 98, 0),
    ("an empty first named slot -> the next named member", 6, True, (0, -1, 2, -1), 185, 2),
    ("every named slot empty -> the moogle (host / selftest)", 6, True, (0, -1, -1, -1), 220, 8),
    ("every named slot empty -> undressed on a client", 6, False, (0, -1, -1, -1), 0, -1),
    ("Cinna (CharacterId 8) -> her own rig 9 (107), never the moogle row", 2, True, (0, 8, -1, -1), 107, 9),
    ("Marcus (9) -> rig 10 (109)", 2, True, (0, 9, -1, -1), 109, 10),
    ("Blank (10) -> rig 11 (5467)", 2, True, (0, 10, -1, -1), 5467, 11),
    ("Beatrix (11) -> rig 12 (204)", 2, True, (0, 11, -1, -1), 204, 12),
    ("Cinna dresses whatever the moogle predicate (an EMPTY puppet's alone)", 2, False, (0, 8, -1, -1), 107, 9),
    ("a custom character (12) -> undressed", 2, True, (0, 12, -1, -1), 0, -1),
    ("a custom character named first -> undressed, never the next slot", 6, True, (0, 12, 1, -1), 0, -1),
    ("the first OCCUPIED named slot decides (Cinna before Vivi)", 6, True, (0, 8, 1, -1), 107, 9),
    ("bits above slot 3 are no party slots", 0x12, True, DRESS_PARTY4, 8, 1),
    ("an UNREADABLE named slot (-2) -> undressed, never the moogle", 6, True, (0, -1, -2, -1), 0, -1),
    ("no party read -> unreadable: undressed, never the moogle", 2, True, None, 0, -1),
)


def dress_auto_table(rule) -> str | None:
    """DressAutoTable (the live s140 rows): None when ``rule(mask, moogle_when_empty, slot_char) -> (model, rig)`` passes
    every row, else the first failing row's name."""
    return _auto_table(DRESS_AUTO_TABLE, rule)


def dress_auto_table_s139(rule) -> str | None:
    """[ff9mapkit netsync s140] DressAutoTable as the s139 patch wrote it (frozen)."""
    return _auto_table(DRESS_AUTO_TABLE_S139, rule)


def _auto_table(table, rule) -> str | None:
    for name, mask, mwe, chars, model, rig in table:
        if tuple(rule(mask, mwe, chars)) != (model, rig):
            return name
    return None


def mutant_rigs_length_guard(mask, mwe, slot_char) -> tuple:
    """s139's DressSelfTest mutant (FROZEN, the s139 table): the party path guarded on Rigs.Length (9) -- Cinna (8) would
    wear the moogle row. [ff9mapkit netsync s140] its grown form on the live table is :func:`mutant_char_is_rig`."""
    return resolve_auto_core(mask, mwe, slot_char, lambda c: c if 0 <= c < RIG_ROW_COUNT_S139 else -1)


def mutant_moogle_on_client(mask, mwe, slot_char) -> tuple:
    """DressSelfTest's mutant: the moogle handed to every role (the client included)."""
    return resolve_auto(mask, True, slot_char)


def mutant_role_not_client(role) -> bool:
    """DressSelfTest's mutant predicate: ``role != "client"`` (a typo'd Role=guest would get the moogle)."""
    return role != "client"


def swapped_dress_body(model: int, char_id: int) -> bytes:
    """DressSelfTest's mutant encoder: the model big-endian (a symmetric byte-order bug round-trips its own encoder)."""
    return bytes(((int(model) >> 8) & 0xFF, int(model) & 0xFF, int(char_id) & 0xFF))


# ================================================================================================ s140
# [ff9mapkit netsync s140] THE GUEST DRESSES ITSELF (studies/battle-coop/R3-DESIGN.md 3.4.4 as amended by
# R3-FIELD-MODEL-AUDIT.md 2.3 -- amendments 1-14, decisions D1-D7 -- and its 3.1 key design), with the OWNER's decision of
# 2026-10-17 folded in: Cinna, Marcus, Blank and Beatrix (CharacterId 8-11) get "their own models" -- rig rows 9-12 (the
# table above), ResolveAuto maps them, section 8 carries charId 8-11. Two halves, each the PURE C# rule of the same name:
#   (1) NetSyncVisitor's CharacterId <-> rig map (CharToRig / RigToChar / DressCharIdValid) and DressSelfTest's grown rows'
#       tables and mutants (the charId table, the guest's charId check, the census rows, the CharacterId-as-rig mutant);
#   (2) NetSyncSelfDress.cs -- the guest's own dress: the closed loco-class table (by NAME), MapRigAnim (own clips pass,
#       loco families -> the slot clip, a gesture -> the idle ALIAS on RunAnimation / in the jump slot, the idle in a
#       stand / walk / run / turn slot, none in the sleep slot), the B_FRAME law, the one timeline law, the arm decision
#       (section 8 through the real readers), the bench frame (through the real encoders), the skip rule, the exclusion,
#       the dress order, the law levers, `self` / `gate` / `law`'s parse, and SelfTest's helper tables and mutants.
# test_harness_netsync.py holds every one against the s140 patch and EVALUATES DressSelfTest's 38 rows and
# NetSyncSelfDress.SelfTest's 29 rows off the stack against these twins (each made to fail by a mutant twin).

# ---- (1) THE OWNER'S 8-11 ROWS: NetSyncVisitor's CharacterId <-> rig map
def char_to_rig(char_id) -> int:
    """NetSyncVisitor.CharToRig: CharacterId 0-7 -> rig 0-7; 8-11 (Cinna, Marcus, Blank, Beatrix) -> rig 9-12; anything else
    (a custom 12+, CharacterId.NONE, a negative read) -> -1. Never the moogle rig (8): CharacterId 8 is Cinna."""
    if isinstance(char_id, bool) or not isinstance(char_id, int):
        return -1
    if 0 <= char_id < MAIN_RIG_COUNT:
        return char_id
    if SUB_CHAR_FIRST <= char_id < SUB_CHAR_FIRST + SUB_RIG_COUNT:
        return char_id - SUB_CHAR_FIRST + SUB_RIG_FIRST
    return -1


def rig_to_char(rig_idx) -> int:
    """NetSyncVisitor.RigToChar: rig 0-7 -> CharacterId 0-7; 9-12 -> 8-11; the moogle (8) and anything else -> 0xFF."""
    if isinstance(rig_idx, bool) or not isinstance(rig_idx, int):
        return CHAR_NONE
    if 0 <= rig_idx < MAIN_RIG_COUNT:
        return rig_idx
    if SUB_RIG_FIRST <= rig_idx < SUB_RIG_FIRST + SUB_RIG_COUNT:
        return rig_idx - SUB_RIG_FIRST + SUB_CHAR_FIRST
    return CHAR_NONE


def dress_char_id_valid(char_id) -> bool:
    """NetSyncVisitor.DressCharIdValid: a section-8 charId the GUEST accepts -- 0xFF (the moogle / no dress) or a CharacterId
    with a rig (0-11). 12-254 is MALFORMED: the guest's "charid" disarm ("charId outside 0-11 and not 0xFF")."""
    return char_id == CHAR_NONE or char_to_rig(char_id) >= 0


#: NetSyncClient.SubRigsAreCensus' literals: rows 9-12, every column, in RIG_COLUMNS order -- the census's rows
#: (studies/battle-coop/dress-census/rigs_8_11.json `rows`, CharacterId 8-11 -> rig 9-12). A test pins them to the JSON, to
#: the patch's Rig rows and to :data:`RIGS`.
SUB_RIG_CENSUS = {
    9: (107, 470, 761, 105, 104, 107, 87, 0, -1, -1, -1, -1, 0, 101, 24, 25),          # Cinna   (CharacterId 8)
    10: (109, 474, 367, 365, 368, 364, 100, 0, 4, 18, 0, 10, 0, 363, 5, 6),            # Marcus  (CharacterId 9)
    11: (5467, 462, 5225, 5222, 5223, 5224, 87, 0, 7, 18, 6, 16, 0, 5221, 13, 14),     # Blank   (CharacterId 10)
    12: (204, 2978, 2975, 2981, 2980, 2974, 100, 0, 7, 18, 6, 16, 0, 2977, 15, 16),    # Beatrix (CharacterId 11)
}


def sub_rigs_are_census(rigs=None) -> bool:
    """NetSyncClient.SubRigsAreCensus over ``rigs`` (default :data:`RIGS`): rows 9-12 equal :data:`SUB_RIG_CENSUS`."""
    rigs = RIGS if rigs is None else rigs
    return all(len(rigs) > i and tuple(rigs[i]) == row for i, row in SUB_RIG_CENSUS.items())


def char_rig_map_holds(char_to_rig_=None, rig_to_char_=None) -> bool:
    """NetSyncClient.CharRigMapHolds over a map pair (default the production twins): 0-7 the same both ways; CharacterId 8-11
    <-> rig 9-12; the moogle rig -> 0xFF and NO CharacterId ever -> the moogle rig; 12+ / NONE / a negative read -> no
    rig; past the table -> 0xFF; every mapped value round-trips (swept over -2..255)."""
    c2r = char_to_rig if char_to_rig_ is None else char_to_rig_
    r2c = rig_to_char if rig_to_char_ is None else rig_to_char_
    if any(c2r(c) != c or r2c(c) != c for c in range(8)):
        return False
    if (c2r(8), c2r(9), c2r(10), c2r(11), c2r(12), c2r(-1), c2r(-2), c2r(0xFF)) != (9, 10, 11, 12, -1, -1, -1, -1):
        return False
    if (r2c(8), r2c(9), r2c(10), r2c(11), r2c(12), r2c(13), r2c(-1)) != (CHAR_NONE, 8, 9, 10, 11, CHAR_NONE, CHAR_NONE):
        return False
    for c in range(-2, 0x100):
        rig = c2r(c)
        if rig == RIG_MOOGLE or rig >= RIG_ROW_COUNT or (rig >= 0 and r2c(rig) != c):
            return False
    for rig in range(RIG_ROW_COUNT):
        c = r2c(rig)
        if (c != CHAR_NONE) if rig == RIG_MOOGLE else (c2r(c) != rig):
            return False
    return True


def rig_clips_in_own_folder(rigs=None) -> bool:
    """NetSyncClient.RigClipsInOwnFolder over ``rigs`` (default :data:`RIGS`), through the kit's copies of AnimationDB and
    FF9BattleDB.GEO (:func:`anim_name` / :func:`geo_name`): every row's idle / walk / run / turns / idle alias and its
    break clip (when it has one) is a named clip whose folder (:func:`folder_of`) is the row's own GEO."""
    for row in (RIGS if rigs is None else rigs):
        r = dict(zip(RIG_COLUMNS, row))
        geo = geo_name(r["model"])
        if not geo:
            return False
        for col in ("idle", "walk", "run", "turn_l", "turn_r", "idle_alias", "inactive"):
            if col == "inactive" and r[col] == 0:
                continue                                # Inactive 0 = none
            if folder_of(anim_name(r[col])) != geo:
                return False
    return True


def _map_char_is_rig(char_id) -> int:
    return char_id if isinstance(char_id, int) and 0 <= char_id < RIG_ROW_COUNT else -1


def _map_mains_only(char_id) -> int:
    return char_id if isinstance(char_id, int) and 0 <= char_id < MAIN_RIG_COUNT else -1


def mutant_char_is_rig(mask, mwe, slot_char) -> tuple:
    """DressSelfTest's s140 mutant (MutantCharIsRig): the CharacterId used AS the rig index -- Cinna (8) in the moogle suit,
    Marcus (9) as Cinna, Blank (10) as Marcus, a custom 12 as Beatrix. The auto table must catch it."""
    return resolve_auto_core(mask, mwe, slot_char, _map_char_is_rig)


def mutant_mains_cap(mask, mwe, slot_char) -> tuple:
    """DressSelfTest's s140 mutant (MutantMainsCap): s139's production map -- the mains only (Cinna..Beatrix undressed
    again). The auto table must catch it."""
    return resolve_auto_core(mask, mwe, slot_char, _map_mains_only)


def dress_char_table(rule) -> str | None:
    """NetSyncClient.DressCharTable: section 8's charId as ``rule(model, rig)`` -- None when every row holds, else the first
    failing row's name."""
    if rule(98, 0) != 0 or rule(192, 4) != 4 or rule(509, 7) != 7:
        return "a main ships its own row (0-7)"
    if rule(220, 8) != CHAR_NONE:
        return "the moogle ships 0xFF"
    if rule(0, -1) != CHAR_NONE or rule(0, 9) != CHAR_NONE:
        return "no dress ships 0xFF"
    if rule(107, 9) != 8:
        return "Cinna (rig 9) ships CharacterId 8, never 9 (Marcus)"
    if rule(109, 10) != 9 or rule(5467, 11) != 10 or rule(204, 12) != 11:
        return "Marcus / Blank / Beatrix (rigs 10-12) ship 9 / 10 / 11"
    if rule(1, 13) != CHAR_NONE or rule(1, -5) != CHAR_NONE:
        return "a rig outside the table ships 0xFF"
    return None


def mutant_rig_as_char_id(model, rig_idx) -> int:
    """DressSelfTest's mutant (MutantRigAsCharId): the rig index shipped as the charId (the moogle kept 0xFF)."""
    return rig_idx if model and 0 <= rig_idx < RIG_ROW_COUNT and rig_idx != RIG_MOOGLE else CHAR_NONE


def mutant_char_id_mains_only(model, rig_idx) -> int:
    """DressSelfTest's mutant (MutantCharIdMainsOnly): s139's DressCharId -- a main's row, else 0xFF."""
    return rig_idx if model and 0 <= rig_idx < MAIN_RIG_COUNT else CHAR_NONE


def dress_char_id_valid_table(valid) -> str | None:
    """NetSyncClient.DressCharIdValidTable: the guest's charId check as ``valid(charId)`` -- None when it holds."""
    if not all(valid(c) for c in range(8)):
        return "a main's charId (0-7) is accepted"
    if not all(valid(c) for c in range(8, 12)):
        return "Cinna..Beatrix's charId (8-11) is accepted"
    if not valid(CHAR_NONE):
        return "0xFF (the moogle / no dress) is accepted"
    if valid(12) or valid(13) or valid(0x7F) or valid(0xFE):
        return "a charId of 12-254 is malformed"
    return None


def mutant_char_id_mains_valid(char_id) -> bool:
    """DressSelfTest's mutant (MutantCharIdMainsValid): the pre-owner check -- 0-7 and 0xFF only (Cinna refused)."""
    return char_id == CHAR_NONE or 0 <= char_id < MAIN_RIG_COUNT


def mutant_char_id_rig_space_valid(char_id) -> bool:
    """DressSelfTest's mutant (MutantCharIdRigSpaceValid): the RIG space taken for CharacterIds -- 0-12 accepted."""
    return char_id == CHAR_NONE or 0 <= char_id < RIG_ROW_COUNT


# ---- the kit's copies of the open-source tables (Memoria's FF9DBAll.AnimationDB / FF9BattleDB.GEO, 0 differences per the
# census): loaded lazily, so this module imports without the kit
def anim_name(anim) -> str | None:
    """AnimationDB.TryGetValue(anim) -- the clip's NAME (None for an id the table lacks, or a non-int)."""
    if isinstance(anim, bool) or not isinstance(anim, int):
        return None
    from ff9mapkit._animdb_all import ANIMATIONS
    return ANIMATIONS.get(anim)


def geo_name(model) -> str | None:
    """FF9BattleDB.GEO.TryGetValue(model) -- the model's GEO name (None for an id the table lacks)."""
    if isinstance(model, bool) or not isinstance(model, int):
        return None
    from ff9mapkit._modeldb import MODELS
    return MODELS.get(model)


# ---- (2) THE SELF-DRESS (NetSyncSelfDress.cs)
#: THE CLOSED LOCO-CLASS TABLE (R3-FIELD-MODEL-AUDIT.md 2.3 amendment 3; NetSyncSelfDress.LocoClassSuffixes): the 40 non-OTHER
#: names of the 401 GEO_MAIN_F0_ZDN names, one row per class (row index == the class code; each suffix follows
#: LOCO_CLASS_PREFIX). Any other name -- every non-ZDN name included -- is OTHER. Generated by
#: studies/battle-coop/dress-census/gen_loco_table.py (loco_table.json `engine_map`); a test pins this table to the patch's C#
#: row for row AND to the JSON's `table` on all 401 names. Codes 0-5 == NetSyncVisitor.LocoOther..LocoTurnR.
LOCO_CLASS_OTHER, LOCO_CLASS_IDLE, LOCO_CLASS_WALK, LOCO_CLASS_RUN, LOCO_CLASS_TURN_L, LOCO_CLASS_TURN_R, \
    LOCO_CLASS_INACTIVE, LOCO_CLASS_JUMP_LADDER = range(8)
LOCO_CLASS_NAMES = ("OTHER", "IDLE", "WALK", "RUN", "TURN_L", "TURN_R", "INACTIVE", "JUMP_LADDER")
LOCO_CLASS_PREFIX = "ANH_MAIN_F0_ZDN_"
LOCO_CLASS_SUFFIXES = (
    (),
    ("COLD_IDLE", "FRA_IDLE", "IDLE", "MBG_IDLE", "SWORD_IDLE"),
    ("COLD_WALK", "FRA_WALK", "MBG_WALK", "POT_WALK", "SWORD_WALK", "TKE_WALK", "WALK"),
    ("MBG_RUN", "RUN", "SWORD_RUN"),
    ("COLD_TURN_L", "POT_TURN_L", "SWORD_TURN_L", "TURN_L"),
    ("COLD_TURN_R", "POT_TURN_R", "SWORD_TURN_R", "TURN_R"),
    ("BREAK1_FLEX", "BREAK1_FLEX2", "BREAK1_HEAD", "BREAK1_LOOK", "BREAK1_LOOKB", "BREAK1_STRCH", "BREAK1_XARM"),
    ("JUMP", "JUMP1", "JUMP_1", "JUMP_2", "JUMP_3", "LADDER_1_1", "LADDER_1_2", "LADDER_1_3", "LADDER_2_1", "LADDER_2_3"),
)
LOCO_CLASS_BY_NAME = {LOCO_CLASS_PREFIX + s: code for code, row in enumerate(LOCO_CLASS_SUFFIXES) for s in row}


def loco_class_of(name) -> int:
    """NetSyncSelfDress.LocoClassOf: a clip NAME's class off the closed table (OTHER for null, a non-string, any name the
    table lacks -- every non-ZDN name included). Classify by NAME: ids 200 and 324 are both ANH_MAIN_F0_ZDN_IDLE."""
    return LOCO_CLASS_BY_NAME.get(name, LOCO_CLASS_OTHER) if isinstance(name, str) else LOCO_CLASS_OTHER


def loco_class_of_id(anim) -> int:
    """NetSyncSelfDress.LocoClassOfId: an anim id's class by its AnimationDB NAME (an id with no name -> OTHER)."""
    return loco_class_of(anim_name(anim))


#: The stock sites MapAndAttach runs at (NetSyncSelfDress.SitePlay..SiteJump): RunAnimation / RunAnimationEx, then the
#: stand / walk / run / turn-left / turn-right / sleep (ASLEEP) / jump (AJUMP) slots.
SITE_PLAY, SITE_IDLE, SITE_WALK, SITE_RUN, SITE_TURN_L, SITE_TURN_R, SITE_SLEEP, SITE_JUMP = range(8)
SITE_NAMES = ("play", "idle", "walk", "run", "turn_l", "turn_r", "sleep", "jump")
#: The s140 laws' bits (NetSyncSelfDress.LawBFrame..LawTimeline) and the `law` lever's names, in that order -- each switched
#: off by `selfdress law <name> off` on the selftest role ONLY (a client never reads one).
LAW_BFRAME, LAW_ATTACH, LAW_ALIAS, LAW_TIMELINE = 1, 2, 4, 8
LAW_NAMES = ("bframe", "attach", "alias", "timeline")


def rig_geo(rig_idx) -> str | None:
    """NetSyncSelfDress.RigGeo: the rig's GEO name (the folder its OWN clips load from); None outside the table."""
    r = rig_row(rig_idx)
    return geo_name(r["model"]) if r is not None else None


def is_own_clip(rig_idx, name) -> bool:
    """NetSyncSelfDress.IsOwnClip: a clip whose folder (AnimationFactory's naming rule) is the rig's GEO."""
    geo = rig_geo(rig_idx)
    return geo is not None and isinstance(name, str) and folder_of(name) == geo


def map_rig_anim(rig_idx, id_, site, alias_law) -> int:
    """NetSyncSelfDress.MapRigAnim -- THE MAP, pure over (rig, id, site, alias law): a rig outside the table returns the id
    unchanged; the sleep slot's 0 stays 0; the rig's OWN clips pass through; a loco family maps to the rig's slot clip (a
    break clip to the rig's own, when it has one); everything else is THE GESTURE FALLBACK -- the sleep slot 0 (none), a
    RunAnimation or the jump slot the rig's IDLE ALIAS (amendment 4; `law alias off`: the idle itself, its red), a stand /
    walk / run / turn slot the rig's idle (a slot plays native; it must never hold the alias a gesture plays)."""
    r = rig_row(rig_idx)
    if r is None:
        return id_
    if site == SITE_SLEEP and id_ == 0:
        return 0
    name = anim_name(id_)
    if name is not None and is_own_clip(rig_idx, name):
        return id_
    c = loco_class_of(name)
    if c == LOCO_CLASS_IDLE:
        return r["idle"]
    if c == LOCO_CLASS_WALK:
        return r["walk"]
    if c == LOCO_CLASS_RUN:
        return r["run"]
    if c == LOCO_CLASS_TURN_L:
        return r["turn_l"]
    if c == LOCO_CLASS_TURN_R:
        return r["turn_r"]
    if c == LOCO_CLASS_INACTIVE and r["inactive"] != 0:
        return r["inactive"]
    if site == SITE_SLEEP:
        return 0
    if site in (SITE_PLAY, SITE_JUMP):
        return r["idle_alias"] if alias_law else r["idle"]
    return r["idle"]


def site_fallback(rig_idx, site, alias_law) -> int:
    """NetSyncSelfDress.SiteFallback -- THE SITE'S FALLBACK (MapRigAnim's gesture fallback and MapAndAttach's fault
    answer): 0 = none in the sleep slot; the idle ALIAS on RunAnimation and in the jump slot (`law alias off`: the idle); the
    rig's idle in a stand / walk / run / turn slot. None outside the table."""
    r = rig_row(rig_idx)
    if r is None:
        return None
    if site == SITE_SLEEP:
        return 0
    if site in (SITE_PLAY, SITE_JUMP):
        return r["idle_alias"] if alias_law else r["idle"]
    return r["idle"]


def body_rig(net_self_dress) -> int:
    """NetSyncSelfDress.BodyRig -- THE BODY'S RIG (amendment 5): PosObj.netSelfDress - 1, -1 undressed -- the ONE place
    every s140 hook resolves its rig (MapAnim, MapAndAttach, KeepSourceTimeline, BFrame, AttachDress, the defence branch,
    the harness `rig`), never the arm's WantRig."""
    return int(net_self_dress) - 1 if net_self_dress else -1


def mutant_body_rig_on_arm(want_rig, net_self_dress) -> int:
    """SelfTest's mutant (MutantBodyRigOnArm): a hook's rig read off the ARM (WantRig), not off the body."""
    return want_rig if net_self_dress else -1


def map_anim(net_self_dress, id_, site, alias_law: bool = True) -> int:
    """NetSyncSelfDress.MapAnim -- keyed on the BODY (amendment 5, :func:`body_rig`): ``net_self_dress`` is the body's
    PosObj.netSelfDress (rig + 1; 0 = undressed -> the id unchanged), never the arm's WantRig. MapAndAttach -- every
    stock-site hook's map -- calls it."""
    rig = body_rig(net_self_dress)
    if rig < 0:
        return id_
    return map_rig_anim(rig, id_, site, alias_law)


def jump_frame_n(rig_idx, raw, frames_of, *, keep: bool = True, alias_law: bool = True) -> int | None:
    """[ff9mapkit netsync s140] The frame count a dressed body's JUMP SLOT runs on at PREJUMP / POSTJUMP / SETVY3
    (EventEngine.ExecAnim(actor.jump), then NetSyncSelfDress.KeepJumpTimeline): the slot holds the mapped id (the idle alias
    for every JUMP / LADDER / OTHER id), ExecAnim sets frameN to ITS count, and KeepJumpTimeline (``keep``: the law on and the
    hook present) puts back the SOURCE clip's (``raw``) for a gesture. ``frames_of(id)`` is the frame count oracle (None =
    unknown). Undressed (rig -1): the raw clip's own count -- stock."""
    if rig_row(rig_idx) is None:
        return frames_of(raw)
    mapped = map_rig_anim(rig_idx, raw, SITE_JUMP, alias_law)
    if keep and mapped != raw and is_gesture(rig_idx, raw):
        return frames_of(raw)
    return frames_of(mapped)


def jump_ticks(frame_n, jump0, jump1) -> tuple:
    """[ff9mapkit netsync s140] (PREJUMP's ticks, POSTJUMP's landing ticks) at aspeed 16 (one frame a tick) on a clip of
    ``frame_n`` frames -- EventEngine.ProcessAnime runs to min(outFrame, frameN - 1): PREJUMP inFrame 0 .. outFrame jump0 - 1
    (byte: 255 for jump0 0), POSTJUMP inFrame jump1 + 1 .. outFrame 255. None for an unknown clip."""
    if frame_n is None:
        return None
    pre = max(0, min((int(jump0) - 1) & 0xFF, frame_n - 1))
    land = max(0, min(255, frame_n - 1) - (int(jump1) + 1))
    return pre, land


def is_loco_family(rig_idx, id_) -> bool:
    """NetSyncSelfDress.IsLocoFamily: ``id_`` played on the rig runs on a loco family's NATIVE timeline -- IDLE / WALK / RUN
    / TURN_L / TURN_R, and INACTIVE only on a rig with an inactive clip; false for the rig's own clips and every gesture."""
    r = rig_row(rig_idx)
    if r is None:
        return False
    name = anim_name(id_)
    if name is None or is_own_clip(rig_idx, name):
        return False
    c = loco_class_of(name)
    if LOCO_CLASS_IDLE <= c <= LOCO_CLASS_TURN_R:
        return True
    return c == LOCO_CLASS_INACTIVE and r["inactive"] != 0


def is_gesture(rig_idx, raw) -> bool:
    """NetSyncSelfDress.IsGesture: a named clip that is neither the rig's own nor a loco family -- the only ids whose
    RunAnimation keeps the SOURCE timeline (KeepSourceTimeline)."""
    name = anim_name(raw)
    return name is not None and not is_own_clip(rig_idx, name) and not is_loco_family(rig_idx, raw)


def bframe_target(rig_idx, id_, bframe_law, alias_law) -> int:
    """NetSyncSelfDress.BFrameTarget -- THE B_FRAME LAW's target: a loco family's NATIVE slot clip while the law is on;
    ``id_`` itself (stock) for a gesture, an own clip, a rig outside the table, or the law switched off."""
    if not bframe_law or not is_loco_family(rig_idx, id_):
        return id_
    mapped = map_rig_anim(rig_idx, id_, SITE_PLAY, alias_law)
    return mapped if mapped != 0 else id_


def law_on_rule(law_off, law, self_test_role) -> bool:
    """NetSyncSelfDress.LawOnRule: a law is ON unless the SELFTEST role switched it off (a client never reads a lever)."""
    return (int(law_off) & int(law)) == 0 or not self_test_role


#: NetSyncSelfDress.SkipRule's answers: the selftest role arms itself (ArmBench); a client while mirroring KEEPS the last
#: arm (sticky through a blip, amendment 6); a client not mirroring disarms with a line ("not mirroring", B26); any other
#: role (a host) disarms silently.
SKIP_SELF_TEST, SKIP_KEEP, SKIP_DISARM, SKIP_DISARM_QUIET = 0, 1, 2, 3


def skip_rule(self_test_role, client_role, mirroring) -> int:
    """NetSyncSelfDress.SkipRule: what a SKIPPED state apply does to the arm."""
    if self_test_role:
        return SKIP_SELF_TEST
    if client_role and mirroring:
        return SKIP_KEEP
    return SKIP_DISARM if client_role else SKIP_DISARM_QUIET


def skip_why(rule) -> str | None:
    """NetSyncSelfDress.SkipWhy: the `why` a disarming skip publishes -- "not mirroring" for a CLIENT (B26's witness), null
    for any other role (a host never mirrors: its `why` never claims a mirror state)."""
    return "not mirroring" if rule == SKIP_DISARM else None


def excluded_field_id(eff) -> bool:
    """NetSyncSelfDress.ExcludedFieldId: New Game's 70 and the ending's 3000-3012, by the EFFECTIVE field id (their forks
    too) -- never dressed (a SetModel-time skip: the arm untouched)."""
    return eff == 70 or 3000 <= eff <= 3012


#: NetSyncSelfDress.SetModelRule's outcomes.
DRESS_NONE, DRESS_EXCLUDED, DRESS_SKIP_NPC, DRESS_SKIP_SECOND, DRESS_YES = range(5)


def set_model_rule(armed, asked, client_or_self_test, excluded, gate_on, defines_player, other_dressed_ctl) -> int:
    """NetSyncSelfDress.SetModelRule -- THE DRESS ORDER at SetModel's fresh branch (review dress F5): nothing unless armed,
    a 98 (re-)model and a client / selftest role; then the EXCLUSION (``excluded()``); then THE PLAYER GATE (gate on and
    ``defines_player()`` false -> skip_npc) BEFORE the control check (``other_dressed_ctl()`` -> skip_second); else dress.
    The three reads are LAZY callables, each asked only when the order reaches it."""
    if not armed or asked != PLAIN_ZIDANE_MODEL or not client_or_self_test:
        return DRESS_NONE
    if excluded():
        return DRESS_EXCLUDED
    if gate_on and not defines_player():
        return DRESS_SKIP_NPC
    if other_dressed_ctl():
        return DRESS_SKIP_SECOND
    return DRESS_YES


def mutant_ctl_first(armed, asked, client_or_self_test, excluded, gate_on, defines_player, other_dressed_ctl) -> int:
    """SelfTest's mutant (MutantCtlFirst): the control check BEFORE the player gate (the order review dress F5 refused)."""
    if not armed or asked != PLAIN_ZIDANE_MODEL or not client_or_self_test:
        return DRESS_NONE
    if excluded():
        return DRESS_EXCLUDED
    if other_dressed_ctl():
        return DRESS_SKIP_SECOND
    if gate_on and not defines_player():
        return DRESS_SKIP_NPC
    return DRESS_YES


#: NetSyncSelfDress.ArmDecision's reasons, in amendment 7's order (WHY_ARMED when it arms).
WHY_ARMED = "armed"
ARM_REASONS = ("section absent", "section8_len", "model 0", "zidane", "charid", "no rig")
#: `netsync.dress.self.why`'s other values: the skip rule's disarm, a caught fault, Clear(), and the SetModel outcomes.
SELF_WHY_OTHER = ("not mirroring", "fault", "cleared", "excluded", "dressed")


def arm_decision(payload) -> tuple:
    """NetSyncSelfDress.ArmDecision -> (why, model, charId, rig): section 8 of a host payload through the REAL readers (the
    FIRST id-8 section -- :func:`old_try_read_section`, a truncated frame refused whole -- then
    :func:`parse_dress_section`, a body under 3 bytes refused, a longer one read forward), the reason in amendment 7's
    order: "section absent", "section8_len", "model 0", "zidane" (charId 0; also 98 under any charId), "charid" (outside
    0-11 and not 0xFF), "no rig" -- else "armed". model / charId / rig as read (-1 = no section 8 read). No knob, no field:
    neither is an arm state (amendment 6)."""
    body = old_try_read_section(payload, SECTION_DRESS)
    if body is None:
        return "section absent", -1, -1, -1
    got = parse_dress_section(body)
    if got is None:
        return "section8_len", -1, -1, -1
    m, c = got
    rig = rig_for_model(m) if m != 0 else -1
    if m == 0:
        return "model 0", m, c, rig
    if c == 0:
        return "zidane", m, c, rig
    if not dress_char_id_valid(c):
        return "charid", m, c, rig
    if rig < 0:
        return "no rig", m, c, rig
    if rig == 0:
        return "zidane", m, c, rig
    return WHY_ARMED, m, c, rig


def bench_frame(spec, auto_mask, guest_slots, moogle_when_empty_, read_slot_chars) -> bytes | None:
    """NetSyncSelfDress.BenchFrame -- the `self` bench spec's section-8 FRAME through the REAL encoders: no spec -> None (no
    section 8: "section absent", an s137 host); "off" -> 00 00 FF ("model 0"); "auto" -> ResolveAuto over ``auto_mask`` (or,
    when it is -1, ``guest_slots`` -- the selftest pin 0: the moogle) with ``moogle_when_empty_`` and the party
    ``read_slot_chars()``; a name -> ResolveNamed over the whole table."""
    if spec is None:
        return None
    if spec == "off":
        model, rig = 0, -1
    elif spec == "auto":
        model, rig = resolve_auto(auto_mask if auto_mask >= 0 else guest_slots, moogle_when_empty_,
                                  read_slot_chars() if read_slot_chars is not None else None)
    else:
        model, rig = resolve_named(spec, RIG_ROW_COUNT)
    body = dress_section_body(model, dress_char_id(model, rig))
    return append_section(b"", SECTION_DRESS, body)


#: NetSyncSelfDress.SelfNames -- the `self` names, exactly NameToRig's keys in the table's order (the kit's
#: ff9mapkit.coop.GHOST_NAMES follows this list).
SELF_NAMES = ("zidane", "vivi", "garnet", "dagger", "steiner", "freya", "quina", "eiko", "amarant", "salamander", "moogle",
              "cinna", "marcus", "blank", "beatrix")
#: HarnessSelfDress' s140 refusals, in its words (NetSyncSelfDress.SelfUsage / LawUsage and the two TrySetBenchSelf ones).
SELF_USAGE = ("netsync selfdress self: expected `self off|auto [mask 0-15]|<name>|moogle` (names: " + " ".join(SELF_NAMES)
              + ")")
SELF_OFF_NO_MASK = "netsync selfdress self off: takes no mask"
GATE_USAGE = "netsync selfdress gate: expected `gate 1|0`"
LAW_USAGE = "netsync selfdress law: expected `law bframe|attach|alias|timeline on|off`"


def self_auto_mask_refusal(mask: int) -> str:
    """TrySetBenchSelf's `self auto <mask>` refusal for a mask past 0x0F."""
    return f"netsync selfdress self auto: mask {mask} is outside 0-15 (party slots 0-3)"


def _num_none(text) -> int | None:
    """Int32.TryParse(text, NumberStyles.None, InvariantCulture): digits only, no sign / space; an Int32 overflow fails."""
    return int(text) if isinstance(text, str) and text.isascii() and text.isdigit() and int(text) < 2 ** 31 else None


def selfdress_s140_op(args) -> tuple:
    """HarnessSelfDress' s140 ops (`self`, `gate`, `law`) parsed as the engine parses them -- ``args`` the agent's s.Args
    ("selfdress" first; an op it does not own is the caller's) -> ``(why, action)``: ``why`` the refusal in its words
    (None = well made), ``action`` ("self", spec, mask) / ("gate", on) / ("law", name, on). The role is the caller's to
    check FIRST (the engine's order: role, op, value)."""
    n = len(args)
    op = str(args[1]).lower() if n > 1 else ""
    val = str(args[2]).lower() if n > 2 else ""
    if op == "self":
        mask = -1
        if n == 4:
            mask = _num_none(str(args[3]).lower())
            if mask is None:
                return SELF_USAGE, None
        elif n != 3:
            return SELF_USAGE, None
        s = dress_mode(val)
        if s == "off":
            if mask >= 0:
                return SELF_OFF_NO_MASK, None
        elif s == "auto":
            if mask > 0x0F:
                return self_auto_mask_refusal(mask), None
        elif mask >= 0 or s == "" or resolve_named(s, RIG_ROW_COUNT)[0] == 0:
            return SELF_USAGE, None
        return None, ("self", s, mask if s == "auto" else -1)
    if op == "gate":
        if n != 3 or val not in ("1", "0"):
            return GATE_USAGE, None
        return None, ("gate", val == "1")
    if op == "law":
        law_val = str(args[3]).lower() if n > 3 else ""
        if n != 4 or law_val not in ("on", "off"):
            return LAW_USAGE, None
        name = dress_mode(val)
        if name not in LAW_NAMES:
            return LAW_USAGE, None
        return None, ("law", name, law_val == "on")
    raise ValueError(f"selfdress_s140_op: {op!r} is no s140 op")


def bench_self_text(spec, mask) -> str | None:
    """NetSyncSelfDress.HarnessBenchSelf (`netsync.dress.self.bench_self`): null = never set; "off" | "auto" | "auto <mask>" |
    a name."""
    if spec is None:
        return None
    return f"auto {mask}" if spec == "auto" and mask >= 0 else spec


#: `netsync.dress.self` at its sentinels: :data:`DRESS_SELF_SENTINELS` (with the s138 keys above, so DRESS_SENTINELS holds it).
#: The selftest proof block's s140 line (NetSyncClient: right after the s139 rig-idle line) and NetSyncSelfDress.SelfTest's
#: rows: the char map, the loco table and its sample (+ the suffix-rule mutant), the map (CHO_WALK / FRA_WALK / break clip
#: / by name), own clips pass, the alias table (+ the slot-id mutant), the slots, the idempotent store, the BODY's rig (+
#: the arm-keyed mutant), the B_FRAME law on every rig, the one timeline law, the law bits, T2, the arm from real bytes
#: (disarms, arms), the bench spec (names, auto), the sticky skip (+ two mutants), the knob, the exclusion, the dress order
#: (+ the control-first mutant), the 0x2C parse, the names.
PROOF_SELF_DRESS = "self-dress selftest: "
SELF_DRESS_SELFTEST_ROWS = 29
SELF_DRESS_SELFTEST_OK = "ok"
SELF_DRESS_SELFTEST_FAIL = "fail: "
#: `netsync.dress` grows by one key per s140 (`self`), and `rig_idle_frames` by four entries (rows 9-12).
DRESS_SELF_KEYS = tuple(DRESS_SELF_SENTINELS)
#: Each dress rung's rig-row count (`rig_idle_frames`' length and the proof line's "(n of N measured)").
RIG_ROWS_BY_RUNG = {"dresshost": RIG_ROW_COUNT_S139, "dressself": RIG_ROW_COUNT,
                    "dresspolish": RIG_ROW_COUNT}            # [ff9mapkit netsync s141] the table is s140's (no new row)

#: THE FRAME-COUNT ORACLE (studies/battle-coop/dress-census/rigs_8_11.json `frames_13`: read off the install's p0data5 by
#: the kit's clip reader, round(length x rate) + 1) -- per rig: idle, walk, run, turn_l, turn_r, the inactive clip (None =
#: none) and the idle alias (the same clip as the idle). A test pins it to the JSON and the s139 oracle; the stand-in reads
#: it as a MODELLED value (it reads no clip). RIG_IDLE_FRAMES is `netsync.dress.rig_idle_frames` on an s140 engine.
RIG_FRAME_COLUMNS = ("idle", "walk", "run", "turn_l", "turn_r", "inactive", "idle_alias")
RIG_FRAMES = (
    (60, 20, 18, 20, 20, 60, 60),        # 0 Zidane
    (45, 20, 18, 20, 20, 50, 45),        # 1 Vivi
    (30, 20, 18, 20, 20, 68, 30),        # 2 Garnet
    (60, 20, 18, 20, 20, 110, 60),       # 3 Steiner
    (50, 24, 18, 20, 20, None, 50),      # 4 Freya
    (40, 26, 22, 20, 20, None, 40),      # 5 Quina
    (30, 24, 20, 20, 20, 83, 30),        # 6 Eiko
    (45, 32, 24, 20, 20, None, 45),      # 7 Amarant
    (72, 16, 10, 20, 20, None, 72),      # 8 the moogle
    (40, 24, 20, 20, 20, None, 40),      # 9 Cinna
    (30, 28, 20, 20, 20, None, 30),      # 10 Marcus
    (40, 24, 20, 20, 20, None, 40),      # 11 Blank
    (45, 24, 20, 20, 20, None, 45),      # 12 Beatrix
)
RIG_IDLE_FRAMES = tuple(row[0] for row in RIG_FRAMES)
#: ...and the SOURCE clips the s140 bench field's conductors play on the player (studies/test-harness/scenarios/
#: _selfdress_field.py; bframe_sites.json's `frame_table.clips`): X's BREAK1_LOOK 186, T1's COLD_FAINT_1 2572, T3's
#: FRA_WALK 8847 and FRA_IDLE 7922 -- frames on Zidane's own body.
SOURCE_FRAMES = {186: 70, 2572: 70, 8847: 40, 7922: 68}


def rig_frames(rig_idx, col: str):
    """A rig's frame count for one of :data:`RIG_FRAME_COLUMNS` (None = no such clip / no such rig)."""
    if isinstance(rig_idx, bool) or not isinstance(rig_idx, int) or not 0 <= rig_idx < len(RIG_FRAMES):
        return None
    return RIG_FRAMES[rig_idx][RIG_FRAME_COLUMNS.index(col)]


def rig_clip_frames(rig_idx, anim) -> int | None:
    """The frame count of the clip ``anim`` on rig ``rig_idx``'s own table (its slot clips, alias and break clip), else the
    SOURCE table (:data:`SOURCE_FRAMES`) -- None when neither knows it."""
    r = rig_row(rig_idx)
    if r is not None:
        for col in RIG_FRAME_COLUMNS:
            if r[col] == anim and anim != 0:
                return rig_frames(rig_idx, col)
    return SOURCE_FRAMES.get(anim)


# ---- NetSyncSelfDress.SelfTest's helper tables and mutants (each run by the rows; the test evaluates the rows off the stack)
#: LocoSampleIds / LocoSampleCodes (loco_table.json `selftest_rows`), by NAME through AnimationDB.
LOCO_SAMPLE = ((12782, 0), (8847, 2), (192, 6), (200, 1), (324, 1), (9181, 0), (11187, 0), (11453, 7), (2575, 2),
               (7935, 3), (4041, 4), (3516, 5), (2556, 0))
#: TimelineSampleIds: a census sample of ZDN ids (never a rig 1-12's own clip).
TIMELINE_SAMPLE = (12782, 8847, 192, 200, 324, 9181, 11187, 11453, 2575, 7935, 4041, 3516, 186, 185, 106, 3005, 12429,
                   57, 25, 38, 40, 41)


def loco_table(classify) -> str | None:
    """SelfTest's LocoTable: None when ``classify(name)`` gives every sample's code (and OTHER for a null name), else the
    first failing sample as "<id> <name>"."""
    for anim, code in LOCO_SAMPLE:
        name = anim_name(anim)
        if name is None or classify(name) != code:
            return f"{anim} {name or '?'}"
    return None if classify(None) == LOCO_CLASS_OTHER else "a null name"


def mutant_suffix_class(name) -> int:
    """SelfTest's mutant (MutantSuffixClass): R3-DESIGN 3.4.4's literal rule -- a name SUFFIX, any family (CHO_WALK a
    walk: a dressed rider walking in mid-air)."""
    if not isinstance(name, str):
        return LOCO_CLASS_OTHER
    for suffix, code in (("_IDLE", LOCO_CLASS_IDLE), ("_WALK", LOCO_CLASS_WALK), ("_RUN", LOCO_CLASS_RUN),
                         ("_TURN_L", LOCO_CLASS_TURN_L), ("_TURN_R", LOCO_CLASS_TURN_R)):
        if name.endswith(suffix):
            return code
    return LOCO_CLASS_INACTIVE if "_BREAK" in name else LOCO_CLASS_OTHER


def alias_table(alias_law, map_rig_anim_=None) -> str | None:
    """SelfTest's AliasTable: the gesture fallback on every rig 1-12 -- None when each plays its idle ALIAS (never the slot
    id), else the first failure."""
    mapf = map_rig_anim if map_rig_anim_ is None else map_rig_anim_
    for i in range(1, RIG_ROW_COUNT):
        r = rig_row(i)
        if r is None or r["idle_alias"] == r["idle"]:
            return f"rig {i}: no alias distinct from its idle"
        for anim, site, what in ((12782, SITE_PLAY, "CHO_WALK on RunAnimation"), (3005, SITE_PLAY, "SIT_1 on RunAnimation"),
                                 (11453, SITE_PLAY, "LADDER_2_3 on RunAnimation"), (106, SITE_JUMP, "JUMP in the jump slot")):
            if mapf(i, anim, site, alias_law) != r["idle_alias"]:
                return f"rig {i}: {what}"
    return None


def store_idempotent(map_rig_anim_=None) -> bool:
    """SelfTest's StoreIdempotent: every rig 1-12's own idle / walk / run / turns / alias / break clip maps to itself at
    every site, under either alias law (a warm return re-stores the same ids)."""
    mapf = map_rig_anim if map_rig_anim_ is None else map_rig_anim_
    for i in range(1, RIG_ROW_COUNT):
        r = rig_row(i)
        if r is None:
            return False
        for anim in (r["idle"], r["walk"], r["run"], r["turn_l"], r["turn_r"], r["idle_alias"], r["inactive"]):
            if anim == 0:
                continue
            if any(mapf(i, anim, site, law) != anim for site in range(SITE_PLAY, SITE_JUMP + 1) for law in (True, False)):
                return False
    return True


def mutant_map_on_arm(want_rig, net_self_dress, id_, site) -> int:
    """SelfTest's mutant (MutantMapOnArm): the map keyed on the ARM (WantRig), not on the body."""
    if not net_self_dress:
        return id_
    return map_rig_anim(want_rig, id_, site, True)


def one_timeline_law(is_gesture_=None, bframe_target_=None) -> bool:
    """SelfTest's OneTimelineLaw: over rigs 1-12 x :data:`TIMELINE_SAMPLE` (never a rig's own clip), an id keeps the source
    timeline (IsGesture) exactly where B_FRAME answers stock (BFrameTarget(...) == id)."""
    gest = is_gesture if is_gesture_ is None else is_gesture_
    bft = bframe_target if bframe_target_ is None else bframe_target_
    for i in range(1, RIG_ROW_COUNT):
        for anim in TIMELINE_SAMPLE:
            name = anim_name(anim)
            if name is None or is_own_clip(i, name):
                return False
            if gest(i, anim) != (bft(i, anim, True, True) == anim):
                return False
    return True


def skip_table(rule) -> str | None:
    """SelfTest's SkipTable: None when ``rule(selfTestRole, clientRole, mirroring)`` is the skip rule, else the first row."""
    if rule(True, False, False) != SKIP_SELF_TEST or rule(True, True, True) != SKIP_SELF_TEST:
        return "the selftest role arms itself (ArmBench)"
    if rule(False, True, True) != SKIP_KEEP:
        return "a client mirroring keeps the last arm (sticky through a blip)"
    if rule(False, True, False) != SKIP_DISARM:
        return "a client not mirroring disarms (not mirroring, B26)"
    if rule(False, False, True) != SKIP_DISARM_QUIET or rule(False, False, False) != SKIP_DISARM_QUIET:
        return "a host disarms silently, mirroring or not"
    return None


def mutant_never_sticky(self_test_role, client_role, mirroring) -> int:
    """SelfTest's mutant (MutantNeverSticky): a skipped apply always disarms a client."""
    return SKIP_SELF_TEST if self_test_role else SKIP_DISARM if client_role else SKIP_DISARM_QUIET


def mutant_sticky_any_role(self_test_role, client_role, mirroring) -> int:
    """SelfTest's mutant (MutantStickyAnyRole): sticky on any mirroring role (a host keeps an arm)."""
    return (SKIP_SELF_TEST if self_test_role else SKIP_KEEP if mirroring else SKIP_DISARM if client_role
            else SKIP_DISARM_QUIET)


class _Probe:
    """SelfTest's Probe: a lazy read that records whether the order reached it."""

    def __init__(self, value: bool):
        self.value, self.asked = bool(value), False

    def get(self) -> bool:
        self.asked = True
        return self.value


def dress_order_table(rule) -> str | None:
    """SelfTest's DressOrderTable: None when ``rule`` is the dress order (:func:`set_model_rule`), else the first row."""
    P = _Probe
    if rule(False, 98, True, P(False).get, True, P(True).get, P(False).get) != DRESS_NONE:
        return "unarmed (SelfDress=0 reads unarmed) -> nothing"
    if rule(True, 220, True, P(False).get, True, P(True).get, P(False).get) != DRESS_NONE:
        return "a non-98 model -> nothing"
    if rule(True, 98, False, P(False).get, True, P(True).get, P(False).get) != DRESS_NONE:
        return "a host never dresses itself"
    d, c = P(False), P(True)
    if rule(True, 98, True, P(True).get, True, d.get, c.get) != DRESS_EXCLUDED or d.asked or c.asked:
        return "the exclusion first: a skip asking neither the gate nor the control"
    d, c = P(False), P(True)
    if rule(True, 98, True, P(False).get, True, d.get, c.get) != DRESS_SKIP_NPC or not d.asked or c.asked:
        return "the player gate BEFORE the control check: an NPC twin is skip_npc, never skip_second"
    if rule(True, 98, True, P(False).get, True, P(True).get, P(True).get) != DRESS_SKIP_SECOND:
        return "a second player Zidane under a dressed control char -> skip_second"
    if rule(True, 98, True, P(False).get, True, P(True).get, P(False).get) != DRESS_YES:
        return "the player's own entry -> dressed"
    d = P(False)
    if rule(True, 98, True, P(False).get, False, d.get, P(False).get) != DRESS_YES or d.asked:
        return "gate 0 dresses the twin without parsing it (N2)"
    if rule(True, 98, True, P(False).get, False, P(False).get, P(True).get) != DRESS_SKIP_SECOND:
        return "gate 0: the control check still holds"
    return None


#: EventEngineUtils.BinaryScript's opArgCount length: an op at or past it (Memoria's 0x112-0x11E family) makes the parser
#: throw IndexOutOfRange -- EntryDefinesPlayer then answers by the character band (parse_fallback).
PARSER_OP_LIMIT = 274


def parse_defines_player(raw, sid=0) -> bool:
    """NetSyncSelfDress.ParseDefinesPlayer over an entry SLICE (entry-relative, as BinaryScript.Entry reads one: [type u8]
    [function count u8], then per function [tag u16][offset u16] -- offsets relative to the function table, byte 2): True
    when any function holds op 0x2C (DefinePlayerCharacter). Raises ValueError where the engine's parser throws: an op at or
    past :data:`PARSER_OP_LIMIT`. Instructions decode through the kit's .eb reader (ff9mapkit.eb.disasm.read_code)."""
    if not raw:
        return False
    from ff9mapkit.eb import disasm
    data = bytes(raw)
    count = data[1]
    offs = [int.from_bytes(data[4 + 4 * k:6 + 4 * k], "little") for k in range(count)]
    for k, off in enumerate(offs):
        pos, end = off + 2, (offs[k + 1] + 2 if k + 1 < count else len(data))
        while pos < end:
            op = data[pos] if data[pos] != 0xFF else 0x100 | data[pos + 1]
            if op >= PARSER_OP_LIMIT:
                raise ValueError(f"op {op:#x} is past the parser's table ({PARSER_OP_LIMIT} ops)")
            ins, pos = disasm.read_code(data, pos)
            if ins.op == 0x2C:
                return True
    return False


# ---- s140's frozen view of s139 (an s139 engine -- the calibration engine of s140, `caps_through("dresshost")`)
def _s139_rig_row(rig) -> dict | None:
    return dict(zip(RIG_COLUMNS, RIGS_S139[rig])) if isinstance(rig, int) and not isinstance(rig, bool) and \
        0 <= rig < RIG_ROW_COUNT_S139 else None


def _s139_rig_for_model(model) -> int:
    r = rig_for_model(model)
    return r if 0 <= r < RIG_ROW_COUNT_S139 else -1


def _s139_classify_loco(model, anim) -> int:
    return classify_loco(model, anim) if _s139_rig_for_model(model) >= 0 else LOCO_OTHER


def _s139_loco_anim(rig_idx, loco) -> int:
    return loco_anim(rig_idx, loco) if _s139_rig_row(rig_idx) is not None else 0


def _s139_resolve_auto(mask, mwe, slot_char) -> tuple:
    return resolve_auto_core(mask, mwe, slot_char, _map_mains_only)


def _s139_resolve_named(mode, cap) -> tuple:
    return resolve_named(mode, min(int(cap), RIG_ROW_COUNT_S139))


def _s139_resolve_dress_rule(ghost_as, mask, mwe, slot_char) -> tuple:
    mode = dress_mode(ghost_as)
    if dress_mode_off(mode):
        return 0, -1
    if mode == "auto":
        return _s139_resolve_auto(mask, mwe, slot_char)
    return _s139_resolve_named(mode, RIG_ROW_COUNT_S139)


def _s139_dress_char_id(model, rig_idx) -> int:
    return rig_idx if model and 0 <= rig_idx < MAIN_RIG_COUNT else CHAR_NONE


def _s139_ghost_anim(dress_model, dress_rig, wire_model, wire_loco, wire_anim) -> int:
    if dress_model and dress_model != wire_model:
        return _s139_loco_anim(dress_rig, wire_loco)
    return wire_anim


def _s139_host_dress_section(ghost_as, guest_slots, role, selftest_role, slot_char) -> bytes:
    mode = dress_mode(ghost_as)
    model, rig = (0, -1) if dress_mode_off(mode) else _s139_resolve_dress_rule(
        mode, guest_slots, moogle_when_empty(role, selftest_role), slot_char if mode == "auto" else None)
    return dress_section_body(model, _s139_dress_char_id(model, rig))


def _s139_mutant_moogle_on_client(mask, mwe, slot_char) -> tuple:
    return _s139_resolve_auto(mask, True, slot_char)


#: [ff9mapkit netsync s140] THE s139 ENGINE, FROZEN: its nine-row table (no Cinna..Beatrix rows), its ResolveAuto capped at
#: the mains, its DressCharId (a main's row, else 0xFF), its 29-row codec proof and its five `selfdress` ops -- what the
#: s139 patch's own lines say (its tests evaluate the s139 DressSelfTest against THESE), and what the stand-in's
#: calibration engine for s140 (``caps_through("dresshost")``) runs. Every name here is the live module's twin of the
#: same name, frozen at s139.
S139 = SimpleNamespace(
    RIGS=RIGS_S139, RIG_ROW_COUNT=RIG_ROW_COUNT_S139,
    NAME_TO_RIG={k: v for k, v in NAME_TO_RIG.items() if v < RIG_ROW_COUNT_S139},
    RIG_NAMES=RIG_NAMES[:RIG_ROW_COUNT_S139], DRESS_SELFTEST_ROWS=DRESS_SELFTEST_ROWS_S139,
    SELFDRESS_OPS=SELFDRESS_OPS_S139, DRESS_AUTO_TABLE=DRESS_AUTO_TABLE_S139,
    RIG_IDLE_FRAMES=RIG_IDLE_FRAMES[:RIG_ROW_COUNT_S139],
    rig_row=_s139_rig_row, rig_for_model=_s139_rig_for_model, classify_loco=_s139_classify_loco,
    loco_anim=_s139_loco_anim, resolve_auto=_s139_resolve_auto, resolve_named=_s139_resolve_named,
    resolve_dress_rule=_s139_resolve_dress_rule, resolve_dress_s138=resolve_dress_s138, ghost_guard=ghost_guard,
    ghost_anim=_s139_ghost_anim, dress_char_id=_s139_dress_char_id, host_dress_section=_s139_host_dress_section,
    dress_auto_table=dress_auto_table_s139, mutant_rigs_length_guard=mutant_rigs_length_guard,
    mutant_moogle_on_client=_s139_mutant_moogle_on_client)
S139.selftest_dress = lambda **kw: _selftest_dress_in(S139, **kw)


def dress_rules(rung: str):
    """[ff9mapkit netsync s140] The dress rules an engine AT a dress rung runs: :data:`S139` at `dresshost`, this module (the
    live engine) from `dressself` on."""
    return S139 if rung == "dresshost" else sys.modules[__name__]


def dress_selftest_offline_s139() -> list:
    """s139's DressSelfTest rows that need no game (rows 1-15: the rig table, the rules, the role predicate, the codec on
    hand-checked bytes) and its three mutants (rows 27-29), as [(row name, ok)] -- FROZEN with the s139 engine's rules
    (:data:`S139`): test_harness_netsync.py holds them against the s139 patch's lines. Row 4 is the alias / footfall rule
    over the table (its AnimationDB half is the test's with the kit's copy) and row 15 the producer on the forced
    selftest's own config (GuestSlots 0, GhostAs auto)."""
    R = S139
    rows = []
    moog = R.rig_row(8)
    rows.append(("rigs: nine rows -- the mains 0-7, the moogle row 8 (model 220)",
                 len(R.RIGS) == R.RIG_ROW_COUNT and MAIN_RIG_COUNT == 8 and RIG_MOOGLE == 8 and R.rig_for_model(220) == 8
                 and R.rig_for_model(98) == 0 and R.rig_for_model(509) == 7 and R.rig_for_model(532) == -1))
    rows.append(("rigs: the moogle row is GEO_NPC_F0_MOG's census row (eye 50, no break clip, no footsteps)",
                 moog is not None and (moog["model"], moog["idle"], moog["walk"], moog["run"], moog["turn_l"],
                                       moog["turn_r"], moog["eye"], moog["inactive"], moog["walk_step_a"],
                                       moog["run_step_a"], moog["idle_alias"]) == (220, 2904, 2927, 2907, 2923, 2911, 50,
                                                                                   0, -1, -1, 2905)
                 and R.rig_row(9) is None and R.rig_row(-1) is None))
    rows.append(("rigs: the moogle's loco clips classify and translate",
                 R.loco_anim(8, LOCO_WALK) == 2927 and R.loco_anim(8, LOCO_OTHER) == 2904 and R.loco_anim(9, LOCO_WALK) == 0
                 and R.classify_loco(220, 2907) == LOCO_RUN))
    pairs = all((r[8] < 0) == (r[9] < 0) and (r[10] < 0) == (r[11] < 0) and (r[8] < 0 or r[8] < r[9])
                and (r[10] < 0 or r[10] < r[11]) for r in R.RIGS)
    rows.append(("rigs: each row's idle alias names its idle's clip; footfalls come in ordered pairs or not at all", pairs))
    auto = R.dress_auto_table(R.resolve_auto)
    rows.append(("auto: " + (auto or "the table"), auto is None))
    rows.append(("named: moogle 220 on any role, zidane 98, the aliases; an unknown name dresses nothing",
                 R.resolve_dress_rule("moogle", 0, False, None) == (220, 8)
                 and R.resolve_dress_rule(" Zidane ", 0, False, None) == (98, 0)
                 and R.resolve_dress_rule("dagger", 0, True, None) == (185, 2)
                 and R.resolve_dress_rule("salamander", 0, True, None) == (509, 7)
                 and R.resolve_dress_rule("cinna", 2, True, DRESS_PARTY4) == (0, -1)))
    rows.append(("mode: GhostAs \"\" / off / 0 dress nothing -- the spectator's moogle comes with auto only",
                 R.resolve_dress_rule("", 0, True, DRESS_PARTY4) == (0, -1)
                 and R.resolve_dress_rule("off", 0, True, DRESS_PARTY4)[0] == 0
                 and R.resolve_dress_rule("0", 6, True, DRESS_PARTY4)[0] == 0
                 and R.resolve_dress_rule(None, 0, True, DRESS_PARTY4)[0] == 0
                 and R.resolve_dress_rule("AUTO", 0, True, DRESS_PARTY4) == (220, 8)))
    rows.append(("s138: the first named bit -- no skip, no moogle (not even by name), Cinna undressed",
                 resolve_dress_s138("auto", 0, DRESS_PARTY4) == (0, -1)
                 and resolve_dress_s138("auto", 6, (0, -1, 2, -1))[0] == 0
                 and resolve_dress_s138("auto", 2, (0, -1, -1, -1))[0] == 0
                 and resolve_dress_s138("auto", 2, (0, 8, -1, -1))[0] == 0
                 and resolve_dress_s138("auto", 6, DRESS_PARTY4) == (8, 1)
                 and resolve_dress_s138("moogle", 0, None) == (0, -1)
                 and resolve_dress_s138("vivi", 0, None) == (8, 1)))
    rows.append(("guard: wire 98 or the dress -> dressed; wire 532 / 5489 -> shown as it is",
                 ghost_guard(185, 98) == 185 and ghost_guard(185, 185) == 185 and ghost_guard(185, 532) == 0
                 and ghost_guard(185, 5489) == 0 and ghost_guard(220, 98) == 220 and ghost_guard(0, 98) == 0))
    rows.append(("anim: translated onto another body, raw on the wire's own (a break clip is never flattened to idle)",
                 R.ghost_anim(185, 2, 98, LOCO_WALK, 25) == 2086 and R.ghost_anim(185, 2, 185, LOCO_OTHER, 3160) == 3160
                 and R.ghost_anim(0, -1, 5489, LOCO_WALK, 1996) == 1996 and R.ghost_anim(220, 8, 98, LOCO_RUN, 38) == 2907
                 and R.ghost_anim(220, 8, 98, LOCO_OTHER, 57) == 2904))
    rows.append(("role: the moogle for the host and the selftest role only (a typo'd role is neither)",
                 moogle_when_empty("host", False) and moogle_when_empty("selftest", True)
                 and not moogle_when_empty("client", False) and not moogle_when_empty("guest", False)
                 and not moogle_when_empty("selftest", False) and not moogle_when_empty(None, False)))
    rows.append(("charId: a main's row; 0xFF for the moogle and for no dress",
                 R.dress_char_id(98, 0) == 0 and R.dress_char_id(192, 4) == 4 and R.dress_char_id(509, 7) == 7
                 and R.dress_char_id(220, 8) == 0xFF and R.dress_char_id(0, -1) == 0xFF))
    rows.append(("codec: hand-checked bytes -- (192, 4) C0 00 04, (220, FF) DC 00 FF, (0, FF) 00 00 FF",
                 dress_section_body(192, 4) == bytes((0xC0, 0x00, 0x04))
                 and dress_section_body(220, 0xFF) == bytes((0xDC, 0x00, 0xFF))
                 and dress_section_body(0, 0xFF) == bytes((0x00, 0x00, 0xFF))
                 and dress_section_body(5489, 3) == bytes((0x71, 0x15, 0x03))))
    rows.append(("codec: the reader refuses fewer than 3 bytes and reads a longer body's first 3 (forward)",
                 parse_dress_section(bytes((0xC0, 0x00, 0x04))) == (192, 4)
                 and parse_dress_section(bytes((0xDC, 0x00, 0xFF, 0x5A, 0xA5))) == (220, 0xFF)
                 and parse_dress_section(bytes((0xDC, 0x00))) is None and parse_dress_section(bytes((0xDC,))) is None
                 and parse_dress_section(b"") is None and parse_dress_section(None) is None))
    own = R.host_dress_section("auto", 0, "selftest", True, DRESS_PARTY4)
    got = parse_dress_section(own)
    rows.append(("producer: HostDressSection is never empty -- 3 bytes that parse",
                 len(own) == DRESS_BODY_LEN and got is not None and (got[1] == CHAR_NONE or got[1] < MAIN_RIG_COUNT)))
    swapped_caught = (swapped_dress_body(192, 4) != bytes((0xC0, 0x00, 0x04))
                      and swapped_dress_body(5489, 3) != bytes((0x71, 0x15, 0x03))
                      and (parse_dress_section(swapped_dress_body(192, 4)) or (None,))[0] != 192)
    rows.append(("mutant: a swapped (big-endian) encoder is caught by the hand-checked bytes and the real reader",
                 swapped_caught))
    rows.append(("mutant: a Rigs.Length party guard (Cinna would wear the moogle row) is caught by the auto table",
                 R.dress_auto_table(R.mutant_rigs_length_guard) is not None))
    rows.append(("mutant: the moogle on the client role (or `role != \"client\"`) is caught",
                 R.dress_auto_table(R.mutant_moogle_on_client) is not None
                 and mutant_role_not_client("guest") != moogle_when_empty("guest", False)))
    return rows


S139.dress_selftest_offline = dress_selftest_offline_s139


# ================================================================================================ s141
# [ff9mapkit netsync s141] THE DRESS POLISH (studies/battle-coop/R3-DESIGN.md 3.4.5 as amended by R3-FIELD-MODEL-AUDIT.md 2.4
# -- amendments 1-6 and 8, decisions D3-D7 -- its 3.1 key design, and the orchestrator's O1-O9). On s140 a dressed body is lit
# by the mapconfig's DEFAULT row, walks with Zidane's footstep keys (which never match its clip: silent) and holds a prop on
# Zidane's bone index on the wrong rig part. s141's five stock-site hooks, each the twin of ONE pure C# rule of
# NetSyncSelfDress.cs (test_harness_netsync.py pins every one to the s141 patch, and EVALUATES the engine's own "dress polish
# selftest" rows -- PolishSelfTest -- off the stack against these twins, each row made to fail by a mutant twin):
#   MapFootstep (DoEventCode CHRFX 0x88)  -- :func:`footstep_rule`, :func:`unbind_on_empty_rule`, :func:`footstep_decision`;
#   AtAttach (ATTACH 0x4C, gMode 1)       -- :func:`attach_bone_rule` (the RIG TABLE's hand pair, never labels_for);
#   KeepMeshOp (MESHSHOW / MESHHIDE)      -- :func:`keep_mesh_rule`;
#   DressedCharRow (fldmcf's actor row)   -- :func:`light_row_rule`, and the ghost's stand-in row :func:`ghost_lp_row_rule`;
#   the calibration lever `polish on|off` -- :func:`polish_on_rule`, :func:`try_set_polish`;
# plus the stock arithmetic their witnesses read: the FF9Snd footstep table (:func:`fldchar_footstep`, :func:`replay_steps`
# -- `netsync.dress.self.steps` is that table filtered to the controlled uid) and fldmcf's tint (:func:`mcf_light_color` --
# `light_rgb` is the `_Color` fldchar writes from it; the census's oracle, studies/battle-coop/dress-census/polish_census.py
# light_color, is its independent twin). Every count is PER FIELD LOAD (:func:`on_sound_table_reset`).

#: FootstepRule / FootstepDecision's verdicts (NetSyncSelfDress.StepUntouched .. StepDroppedEmpty), and the census twin's
#: names for the first four (polish_census.map_footstep: "untouched" / "map" / "drop" / "pass").
STEP_UNTOUCHED, STEP_MAPPED, STEP_DROPPED, STEP_PASSED, STEP_BYPASSED, STEP_DROPPED_EMPTY = 0, 1, 2, 3, 4, 5
STEP_CENSUS_NAMES = {STEP_UNTOUCHED: "untouched", STEP_MAPPED: "map", STEP_DROPPED: "drop", STEP_PASSED: "pass"}
#: AttachBoneRule's verdicts (NetSyncSelfDress.AttachBypass / AttachRemap / AttachNote) and the census twin's names.
ATTACH_BYPASS, ATTACH_REMAP, ATTACH_NOTE = 0, 1, 2
ATTACH_CENSUS_NAMES = {ATTACH_BYPASS: "bypass", ATTACH_REMAP: "remap", ATTACH_NOTE: "note"}
#: NetSyncSelfDress.SourceRig (the SOURCE body's row: Zidane, 98 -- its walk / run, footfall pair and hand bones) and
#: DefaultMcfRow (fldmcf's default DMSMapChar row: ff9fieldMCFGetCharByID(mcf, -1)).
SOURCE_RIG = 0
DEFAULT_MCF_ROW = 0xFFFF
FOOTSTEP_CODES = (16, 17, 18, 19)
#: The `polish` lever's words (NetSyncSelfDress.PolishUsage, TrySetPolish's two log lines) and the release line s141 rewrote
#: (ReleaseBench: "... self / gate / law / polish levers released (<cause>)"; s140's lacks `polish`).
POLISH_USAGE = "netsync selfdress polish: expected `polish on|off`"
POLISH_ON_LOG = ("[NetSync] harness: selfdress polish on -- the s141 polish (footsteps, the mesh-op drop, the prop remap, "
                 "both lighting fallbacks)")
POLISH_OFF_LOG = ("[NetSync] harness: selfdress polish OFF -- CALIBRATION: MapFootstep, the mesh-op drop, the prop remap and "
                  "both lighting fallbacks are bypassed on this selftest role (the witnesses keep reading)")
SELF_RELEASE_LINE_S140 = "selfdress self / gate / law levers released ("
SELF_RELEASE_LINE = "selfdress self / gate / law / polish levers released ("
#: The proof block's s141 line (NetSyncClient, right after s140's self-dress line): NetSyncSelfDress.PolishSelfTest's rows.
#: No verdict key publishes it (audit 3.1 lists none): the line is the record.
PROOF_DRESS_POLISH = "dress polish selftest: "
DRESS_POLISH_SELFTEST_ROWS = 20


def _rig_cols(rig) -> dict | None:
    """A rig as {column: value} (:data:`RIG_COLUMNS`): an index into :data:`RIGS`, or a row dict / tuple already."""
    if isinstance(rig, dict):
        return rig
    if isinstance(rig, (tuple, list)):
        return dict(zip(RIG_COLUMNS, rig))
    return rig_row(rig)


# ---- MapFootstep (O4; amendments 1-2)
def footstep_rule(rig, code, anim, frame, sound) -> tuple:
    """NetSyncSelfDress.FootstepRule -> (verdict, anim', frame', sound'): one CHRFX op (Arg2 anim, Arg3 frame, Arg4 sound)
    on a DRESSED body wearing ``rig`` -- STEP_UNTOUCHED a code other than 16-19; STEP_PASSED an anim other than the SOURCE
    row's walk (25) / run (38), or a frame outside its footfall pair; STEP_DROPPED the source walk / run at a pair frame on
    a rig whose pair for that slot is -1 (Quina, the moogle, Cinna: codes 16, 17, 18 AND 19 alike); else STEP_MAPPED: the
    rig's walk / run at the SAME ordinal in its pair, the sound the rig's StepSound (Steiner's 925) on codes 16 and 17
    ONLY (sndEffectID[0] / [1]; 18's Arg4 is the pitch flag, 19's unused). The outs are the inputs but on a map."""
    if code < 16 or code > 19:
        return STEP_UNTOUCHED, anim, frame, sound
    src, r = rig_row(SOURCE_RIG), _rig_cols(rig)
    if src is None or r is None:
        return STEP_PASSED, anim, frame, sound
    if anim == src["walk"]:
        pair, dst, dst_anim = (src["walk_step_a"], src["walk_step_b"]), (r["walk_step_a"], r["walk_step_b"]), r["walk"]
    elif anim == src["run"]:
        pair, dst, dst_anim = (src["run_step_a"], src["run_step_b"]), (r["run_step_a"], r["run_step_b"]), r["run"]
    else:
        return STEP_PASSED, anim, frame, sound
    ordinal = 0 if frame == pair[0] else 1 if frame == pair[1] else -1
    if ordinal < 0:
        return STEP_PASSED, anim, frame, sound
    if dst[0] < 0 or dst[1] < 0:
        return STEP_DROPPED, anim, frame, sound
    snd = r["step_sound"] if r["step_sound"] != 0 and code in (16, 17) else sound
    return STEP_MAPPED, dst_anim, dst[ordinal], snd


def unbind_on_empty_rule(code, table_use) -> bool:
    """NetSyncSelfDress.UnbindOnEmptyRule: a code 19 (unbind) headed for an EMPTY footstep table -- stock DeleteChar indexes
    charSoundArray[charSoundUse - 1] and throws (``table_use`` is charSoundUse: every body's records)."""
    return code == 19 and table_use <= 0


def footstep_decision(rig, code, anim, frame, sound, polish, table_use) -> tuple:
    """NetSyncSelfDress.FootstepDecision -> (verdict, anim', frame', sound'): what MapFootstep does with one op on a DRESSED
    body -- STEP_UNTOUCHED a code other than 16-19; with the polish on :func:`footstep_rule`'s verdict, off STEP_BYPASSED (the
    op as read); a STEP_DROPPED stays one; then a code 19 still headed for an EMPTY table is STEP_DROPPED_EMPTY (the guard
    holds under `polish off` too: a fault guard, not polish)."""
    if code < 16 or code > 19:
        return STEP_UNTOUCHED, anim, frame, sound
    got = footstep_rule(rig, code, anim, frame, sound) if polish else (STEP_BYPASSED, anim, frame, sound)
    if got[0] == STEP_DROPPED:
        return got
    if unbind_on_empty_rule(code, table_use):
        return (STEP_DROPPED_EMPTY,) + tuple(got[1:])
    return got


# ---- the FF9Snd footstep table (stock: fldchar.cs codes 16-19, FF9Snd GetChar / NewChar / DeleteChar) -- `steps`' witness
def fldchar_footstep(table: list, code, anim, frame, arg4) -> str | None:
    """fldchar.FF9FieldCharDispatch's codes 16-19 on ONE body's records (``table``: [anim, frame, snd0, snd1, pitch] rows in
    charSoundArray order, mutated in place): GetChar finds the TOP record with (anim, frame); 16-18 create one when none
    exists (NewChar appends), then set sndEffectID[0] (16) / [1] (17) / pitchRand (18: Arg4 != 0); 19 runs DeleteChar,
    which only does charSoundUse-- per matching record (the TOP records leave, whichever matched) -- and on an EMPTY table
    indexes charSoundArray[-1]: stock THROWS (returned as a fault string, the table untouched). Other codes: no record."""
    if code not in FOOTSTEP_CODES:
        return None
    if code == 19:
        if not table:
            return f"code 19 on ({anim}, {frame}) with an EMPTY table: stock DeleteChar indexes charSoundArray[-1] and throws"
        hits = sum(1 for r in table if r[0] == anim and r[1] == frame)
        if hits:
            del table[len(table) - hits:]
        return None
    rec = next((r for r in reversed(table) if r[0] == anim and r[1] == frame), None)
    if rec is None:
        rec = [anim, frame, 0, 0, 0]
        table.append(rec)
    if code == 16:
        rec[2] = arg4 & 0xFFFF
    elif code == 17:
        rec[3] = arg4 & 0xFFFF
    else:
        rec[4] = 0 if arg4 == 0 else 1
    return None


def steps_of(table: list) -> list:
    """`netsync.dress.self.steps` off a table: [anim, frame, sndEffectID[0]] per record, in table order."""
    return [[r[0], r[1], r[2]] for r in table]


def replay_steps(rig, ops, *, map_footstep: bool = True, polish: bool = True, table: list | None = None,
                 decision=None, dispatch=None) -> dict:
    """Footstep ops (``ops``: (code, anim, frame, Arg4) in script order) on ONE body through the s141 hook when
    ``map_footstep`` (a DRESSED body on an s141 engine -- :func:`footstep_decision` with ``polish``, its table use the
    table's length) and the stock table (:func:`fldchar_footstep`): an undressed body, or a dressed one on s140 (no hook),
    registers every op as read. -> {"table", "steps", "steps_dropped", "steps_passed", "faults"} (the counts; `faults` the
    empty-table throws stock would raise). ``table`` an existing one (a later op on the same load); ``decision`` /
    ``dispatch`` replace the hook's rule / the stock table's (a mutant, to prove a row bites)."""
    decide = footstep_decision if decision is None else decision
    send = fldchar_footstep if dispatch is None else dispatch
    table = [] if table is None else table
    dropped = passed = 0
    faults = []
    for code, anim, frame, arg4 in ops:
        if map_footstep:
            v, anim, frame, arg4 = decide(rig, code, anim, frame, arg4, polish, len(table))
            if v in (STEP_DROPPED, STEP_DROPPED_EMPTY):
                dropped += 1
                continue
            if v == STEP_PASSED:
                passed += 1
        fault = send(table, code, anim, frame, arg4)
        if fault:
            faults.append(fault)
    return {"table": table, "steps": steps_of(table), "steps_dropped": dropped, "steps_passed": passed, "faults": faults}


# ---- the held-prop remap (O6; amendment 5, D3)
def attach_bone_rule(rig, bone, polish) -> tuple:
    """NetSyncSelfDress.AttachBoneRule -> (bone', verdict): on a DRESSED carrier wearing ``rig`` the SOURCE row's HandBone
    (12) -> the rig's HandBone, its HandBoneEnd (13) -> the rig's HandBoneEnd (ATTACH_REMAP); any other bone unchanged
    (ATTACH_NOTE); `polish off` -> the bone unchanged (ATTACH_BYPASS). The RIG TABLE's columns, never labels_for."""
    src, r = rig_row(SOURCE_RIG), _rig_cols(rig)
    if not polish or src is None:
        return bone, ATTACH_BYPASS
    if bone == src["hand_bone"]:
        return r["hand_bone"], ATTACH_REMAP
    if bone == src["hand_bone_end"]:
        return r["hand_bone_end"], ATTACH_REMAP
    return bone, ATTACH_NOTE


def bone_name(bone) -> str:
    """geo.geoAttach's parent node: GetChildByName("bone" + bone.ToString("D3"))."""
    return f"bone{int(bone):03d}"


# ---- the mesh-op drop (O7; amendment 6)
def keep_mesh_rule(dressed, polish) -> bool:
    """NetSyncSelfDress.KeepMeshRule: an op on an undressed body is kept; on a dressed one dropped while the polish is on."""
    return not dressed or not polish


def mesh_op(meshflags: int, mesh: int, show: bool) -> int:
    """PosObj.geoMeshShow / geoMeshHide on the meshflags word: hide sets bit 1 << mesh, show clears it (UInt16 masks)."""
    bit = (1 << int(mesh)) & 0xFFFF
    return (int(meshflags) & ~bit & 0xFFFFFFFF) if show else (int(meshflags) | bit)


# ---- the lighting fallback (O8; amendment 4, D6)
def light_row_rule(model, has_own_row, dress_src, has_src_row, polish) -> int:
    """NetSyncSelfDress.LightRowRule: the mapconfig row an actor's tint and blob shadow use -- its own model's row; else, on
    a dressed body (dress_src != 0) with the polish on, its SOURCE row (98); else the default 0xFFFF row."""
    if has_own_row:
        return int(model) & 0xFFFF
    if dress_src != 0 and polish and has_src_row:
        return int(dress_src) & 0xFFFF
    return DEFAULT_MCF_ROW


def ghost_lp_row_rule(lp_model, lp_dress_src, polish) -> int:
    """NetSyncSelfDress.GhostLpRowRule: the LOCAL player's row id ApplyGhostLighting falls back to -- its netDressSrc when
    dressed and the polish is on, else its po.model (s140's rule)."""
    return lp_dress_src if lp_dress_src != 0 and polish else lp_model


#: Field 250's mapconfig (EVT_EFOREST1_EF_ENT_0; polish.json `d_lighting.field250`, read through ff9mapkit.mapconfig.parse):
#: its DMSMapChar rows (geoNo, shadowI, shadowR, clr) and its lights (type, clr, the four floor bytes) in table order --
#: numbers only. A test pins both to the census JSON.
FIELD250_MCF = {"chars": ((0xFFFF, 16, 11, (16, 16, 16)), (176, 1, 8, (8, 10, 13)), (98, 1, 10, (10, 12, 15))),
                "lights": ((1, (0, 0, 0), (-1, -1, -1, -1)), (2, (0, 0, 0), (-1, -1, -1, -1)), (0, (0, 0, 0), (0, -1, -1, -1)),
                           (0, (-3, -3, -4), (1, 2, -1, -1)), (0, (-6, -6, -7), (3, -1, -1, -1)))}


def mcf_char(mcf, geo):
    """fldmcf.ff9fieldMCFGetCharByID: the row whose geoNo == (UInt16)geo (-1 -> the default 0xFFFF row); None = no row."""
    if not mcf:
        return None
    return next((c for c in mcf["chars"] if c[0] == (int(geo) & 0xFFFF)), None)


def mcf_floor_light(mcf, floor):
    """fldmcf.ff9fieldMCFGetLightByCharFloor: the HIGHEST-index type-0 light one of whose floor bytes names ``floor`` (& 255);
    None for floor 255 or no such light."""
    if (int(floor) & 255) == 255:
        return None
    for lt in reversed(mcf["lights"]):
        if lt[0] == 0 and any((int(f) & 255) == (int(floor) & 255) for f in lt[2]):
            return lt
    return None


def mcf_tint(char_clr, light_clr) -> list:
    """fldmcf's tint: (Byte)((row.clr[i] + light.clr[i]) << 3) per channel -- what fldchar writes into `_Color`'s rgb."""
    return [((int(char_clr[i]) + int(light_clr[i])) << 3) & 0xFF for i in range(3)]


def mcf_light_color(mcf, model, floor, dress_src: int = 0, polish: bool = True, ladder: bool = False) -> dict:
    """fldmcf.ff9fieldMCFService for ONE actor with s141's DressedCharRow -> {"row", "rgb"}: the row id
    :func:`light_row_rule` picks (own / the dress source / 65535) and the tint under the actor's light (the ladder light on
    a ladder, else its floor's, else the type-1 default); a kit field (no mapconfig) -> {"row": -1, "rgb": None} -- the
    service returns at its top, nothing is written. The census's polish_census.light_color is its independent twin."""
    if not mcf:
        return {"row": -1, "rgb": None}
    row_id = light_row_rule(model, mcf_char(mcf, model) is not None, dress_src,
                            dress_src != 0 and mcf_char(mcf, dress_src) is not None, polish)
    row = mcf_char(mcf, row_id)
    lad = next((lt for lt in mcf["lights"] if lt[0] == 2), None) if ladder else None
    lt = lad or mcf_floor_light(mcf, floor) or next((x for x in mcf["lights"] if x[0] == 1), None)
    return {"row": row_id, "rgb": mcf_tint(row[3], lt[1] if lt is not None else (0, 0, 0))}


def dressed_row_core(mcf, model, dress_src, own, polish) -> tuple:
    """NetSyncSelfDress.DressedRowCore -> (row, used): ``own`` (the mapconfig's row for the actor's own model, or None) when
    it has one, else -- on a dressed body (dress_src != 0) with the polish on -- the SOURCE row (:func:`mcf_char`), else
    None (the stock default row); ``used`` names the row RETURNED (its geoNo; DEFAULT_MCF_ROW for None)."""
    src = mcf_char(mcf, dress_src) if own is None and polish and dress_src != 0 else None
    row = own if own is not None else src
    return row, (int(row[0]) if row is not None else DEFAULT_MCF_ROW)


def ghost_row_core(mcf, ghost_model, has_lp, lp_model, lp_dress_src, polish, rule=None) -> tuple:
    """NetSyncSelfDress.GhostRowCore (ApplyGhostLighting's own row choice, through GhostRow) -> (row, used): the ghost
    model's own row; else, with a local player (``has_lp``), its stand-in row (:func:`ghost_lp_row_rule`, ``rule``
    replacing it); else the stock default row (lookup -1); ``used`` names the row RETURNED (DEFAULT_MCF_ROW for the
    default); row None = no row at all."""
    used = int(ghost_model) & 0xFFFF
    row = mcf_char(mcf, ghost_model)
    if row is None and has_lp:
        used = int((rule or ghost_lp_row_rule)(lp_model, lp_dress_src, polish)) & 0xFFFF
        row = mcf_char(mcf, used)
    if row is None:
        used = DEFAULT_MCF_ROW
        row = mcf_char(mcf, -1)
    return row, used


def ghost_mcf_light_color(mcf, ghost_model, lp_model, lp_floor, lp_dress_src: int = 0, polish: bool = True) -> dict:
    """NetSyncClient.ApplyGhostLighting with s141's GhostRow -> {"row", "rgb"}: :func:`ghost_row_core` with a local player
    (the ghost model's own row, else the LOCAL player's stand-in row, else the default row); the light the local player's
    floor light, else the default light. `netsync.dress.ghost.light_row` is the row; -1 / None with no mapconfig (a kit
    field)."""
    if not mcf:
        return {"row": -1, "rgb": None}
    row, row_id = ghost_row_core(mcf, ghost_model, True, lp_model, lp_dress_src, polish)
    lt = mcf_floor_light(mcf, lp_floor) or next((x for x in mcf["lights"] if x[0] == 1), None)
    return {"row": row_id, "rgb": mcf_tint(row[3], lt[1] if lt is not None else (0, 0, 0))}


# ---- the calibration lever (O9)
def polish_on_rule(polish_off, self_test_role) -> bool:
    """NetSyncSelfDress.PolishOnRule: the polish is ON unless the SELFTEST role switched it off (a client never reads it)."""
    return not polish_off or not self_test_role


def polish_value_rule(val) -> int:
    """NetSyncSelfDress.PolishValueRule: DressMode's trim + lower-case, then 1 = `on`, 0 = `off`, -1 = refused."""
    v = dress_mode(val)
    return 1 if v == "on" else 0 if v == "off" else -1


def try_set_polish(val, rule=None) -> tuple:
    """NetSyncSelfDress.TrySetPolish -> (ok, why, polish_off): :func:`polish_value_rule` (``rule`` replaces it); a
    refusal (null, `1`, `maybe`) answers :data:`POLISH_USAGE` and changes nothing (polish_off None)."""
    v = (rule or polish_value_rule)(val)
    if v < 0:
        return False, POLISH_USAGE, None
    return True, None, v == 0


#: NetSyncSelfDress.OnSoundTableReset's statics at their sentinels (the per-load law: HonoluluFieldMain.ff9InitStateFieldMap
#: right after FF9StateFieldMap.ff9ResetStateFieldMap -- one field load each; a test pins the C# body statement for statement;
#: the `polish` lever, `_polishOff`, is NOT one of them: a load never releases it, only ReleaseBench does).
POLISH_LOAD_SENTINELS = {"StepsDropped": 0, "StepsPassed": 0, "StepsFired": 0, "StepsFiredPlayer": 0, "MeshDrops": 0,
                         "AttachRemaps": 0, "AttachNotes": 0, "LightRow": -1, "GhostLightRow": -1, "AttachLastUid": -1,
                         "AttachLastBoneIn": -1, "AttachLastBoneOut": -1, "_attachLastGo": None, "_loggedStepDrop": False,
                         "_loggedUnbindEmpty": False, "_loggedMeshDrop": False, "_loggedAttach": False}


def on_sound_table_reset(statics: dict) -> None:
    """NetSyncSelfDress.OnSoundTableReset over a dict of its statics: every one back to :data:`POLISH_LOAD_SENTINELS`."""
    statics.update(POLISH_LOAD_SENTINELS)


# ---- NetSyncSelfDress.PolishSelfTest's fixtures (the install census, polish.json -- never the rig table) and helper tables
#: PolishFootOracle: per rig 0-12, Zidane's pair keys' targets {walk, walk A, walk B, run, run A, run B, step sound}; walk -1
#: = a DROP rig (no stock footfall registration: Quina, the moogle, Cinna -- O1).
POLISH_FOOT_ORACLE = (
    (25, 4, 13, 38, 0, 8, 0), (571, 4, 14, 419, 0, 9, 0), (2086, 4, 15, 2091, 0, 9, 0), (1996, 4, 14, 2005, 0, 9, 925),
    (2553, 4, 16, 2558, 0, 9, 0), (-1, -1, -1, -1, -1, -1, 0), (7518, 1, 13, 7506, 0, 9, 0), (8316, 6, 23, 8312, 10, 21, 0),
    (-1, -1, -1, -1, -1, -1, 0), (-1, -1, -1, -1, -1, -1, 0), (367, 4, 18, 365, 0, 10, 0), (5225, 7, 18, 5222, 6, 16, 0),
    (2975, 7, 18, 2981, 6, 16, 0))
#: PolishHandOracle: per rig 0-12 {R_hand, R_hand_end} -- polish.json e_hands (the install's skin: the hand's bone and its end,
#: else the hand itself; cross-checked against stock's own AttachObject on each body), never labels_for.
POLISH_HAND_ORACLE = ((12, 13), (16, 17), (14, 15), (15, 16), (12, 12), (13, 14), (14, 15), (16, 16), (19, 19), (24, 25),
                      (5, 6), (13, 14), (15, 16))
POLISH_KEY_ANIM = (25, 25, 38, 38)
POLISH_KEY_FRAME = (4, 13, 0, 8)
POLISH_PASS_ANIM = (25, 25, 38, 38, 200, 2553)
POLISH_PASS_FRAME = (0, 7, 4, 13, 4, 4)
POLISH_OTHER_CODES = (0, 4, 15, 20)
POLISH_BONE_SAMPLE = (0, 1, 6, 11, 12, 13, 14, 16, 19, 21, 24, 25)
#: Field250Steps: field 250's twelve Zidane_Init footstep ops (test2_67.txt:1092-1109; Zidane_13 runs the same twelve on a
#: warm return), in script order (code, anim, frame, Arg4) -- polish.json `a_field250.load_ops`.
FIELD250_STEPS = ((16, 25, 4, 919), (17, 25, 4, 914), (18, 25, 4, 1), (16, 25, 13, 919), (17, 25, 13, 914),
                  (18, 25, 13, 1), (16, 38, 0, 919), (17, 38, 0, 914), (18, 38, 0, 1), (16, 38, 8, 919),
                  (17, 38, 8, 914), (18, 38, 8, 1))
#: Field250Oracle: per rig 0-12, `steps` after one load (polish.json `a_field250.per_rig[*].s141.steps`; [] = 12 dropped).
FIELD250_ORACLE = (
    [[25, 4, 919], [25, 13, 919], [38, 0, 919], [38, 8, 919]], [[571, 4, 919], [571, 14, 919], [419, 0, 919], [419, 9, 919]],
    [[2086, 4, 919], [2086, 15, 919], [2091, 0, 919], [2091, 9, 919]],
    [[1996, 4, 925], [1996, 14, 925], [2005, 0, 925], [2005, 9, 925]],
    [[2553, 4, 919], [2553, 16, 919], [2558, 0, 919], [2558, 9, 919]], [],
    [[7518, 1, 919], [7518, 13, 919], [7506, 0, 919], [7506, 9, 919]],
    [[8316, 6, 919], [8316, 23, 919], [8312, 10, 919], [8312, 21, 919]], [], [],
    [[367, 4, 919], [367, 18, 919], [365, 0, 919], [365, 10, 919]],
    [[5225, 7, 919], [5225, 18, 919], [5222, 6, 919], [5222, 16, 919]],
    [[2975, 7, 919], [2975, 18, 919], [2981, 6, 919], [2981, 16, 919]])


def steps_text(steps) -> str:
    """Replay250's string form of `steps` (the C# oracle's literals): "[[a,f,s],...]" without spaces."""
    return "[" + ",".join("[" + ",".join(str(int(x)) for x in row) + "]" for row in steps) + "]"


def _rigs_of(rigs):
    return [dict(zip(RIG_COLUMNS, r)) for r in (RIGS if rigs is None else rigs)]


def foot_table(rule, rigs=None) -> str | None:
    """PolishSelfTest's FootTable: ``rule(rig, code, anim, frame, sound) -> (verdict, anim', frame', sound')`` over every rig
    (``rigs``: the table, default :data:`RIGS`) x codes 16-19 x Zidane's four pair keys (a distinct Arg4, 900 + code), the
    pass ops and the untouched codes -- None when it answers :data:`POLISH_FOOT_ORACLE`, else the first failure (the C#
    message's words)."""
    table = _rigs_of(rigs)
    if len(POLISH_FOOT_ORACLE) != len(table):
        return f"the oracle covers {len(POLISH_FOOT_ORACLE)} rigs, the table {len(table)}"
    for i, rig in enumerate(table):
        o = POLISH_FOOT_ORACLE[i]
        drop = o[0] < 0
        for code in range(16, 20):
            for k, (anim, frame) in enumerate(zip(POLISH_KEY_ANIM, POLISH_KEY_FRAME)):
                sound = 900 + code
                v, a, f, s = rule(rig, code, anim, frame, sound)
                at = f"rig {i} code {code} ({anim}, {frame})"
                if drop:
                    if v != STEP_DROPPED or a != anim or f != frame or s != sound:
                        return at + f": verdict {v}, not dropped"
                    continue
                walk = anim == 25
                want_anim = o[0 if walk else 3]
                want_frame = o[(1 if walk else 4) + (k & 1)]
                want_sound = o[6] if o[6] != 0 and code in (16, 17) else sound
                if v != STEP_MAPPED or a != want_anim or f != want_frame or s != want_sound:
                    return (at + f" -> ({a}, {f}, {s}) verdict {v}, want ({want_anim}, {want_frame}, {want_sound}) "
                                 f"mapped")
        for pa, pf in zip(POLISH_PASS_ANIM, POLISH_PASS_FRAME):
            for code in range(16, 20):
                v, a, f, s = rule(rig, code, pa, pf, 919)
                if v != STEP_PASSED or a != pa or f != pf or s != 919:
                    return f"rig {i} code {code} ({pa}, {pf}): verdict {v}, not passed unmapped"
        for code in POLISH_OTHER_CODES:
            v, a, f, s = rule(rig, code, 25, 4, 919)
            if v != STEP_UNTOUCHED or a != 25 or f != 4 or s != 919:
                return f"rig {i} code {code}: touched (verdict {v})"
    return None


def decision_polish_on(rig, code, anim, frame, sound, decision=None) -> tuple:
    """PolishSelfTest's DecisionPolishOn: what MapFootstep dispatches with the polish on and a non-empty table."""
    return (decision or footstep_decision)(rig, code, anim, frame, sound, True, 1)


def bypass_table(decision=None, rigs=None) -> str | None:
    """PolishSelfTest's BypassTable: under `polish off` every 16-19 op on every rig is sent through as read; code 4 stays
    untouched."""
    decide = decision or footstep_decision
    for i, rig in enumerate(_rigs_of(rigs)):
        for code in range(16, 20):
            for anim, frame in zip(POLISH_KEY_ANIM, POLISH_KEY_FRAME):
                v, a, f, s = decide(rig, code, anim, frame, 919, False, 1)
                if v != STEP_BYPASSED or a != anim or f != frame or s != 919:
                    return f"rig {i} code {code} ({anim}, {frame}) not bypassed"
        if decide(rig, 4, 1, -100, 0, False, 1)[0] != STEP_UNTOUCHED:
            return f"rig {i}: code 4 touched under polish off"
    return None


def guard_rows(decision=None, unbind=None) -> bool:
    """PolishSelfTest's GuardRows: THE EMPTY-TABLE GUARD inside FootstepDecision on a mapped rig (Freya) and a drop rig (the
    moogle), its rows as the C# writes them."""
    d, ub = decision or footstep_decision, unbind or unbind_on_empty_rule
    freya, moogle = rig_row(4), rig_row(RIG_MOOGLE)
    return (ub(19, 0) and ub(19, -1) and not ub(19, 1) and not ub(16, 0) and not ub(17, 0) and not ub(18, 0)
            and d(freya, 19, 25, 13, 0, True, 0)[0] == STEP_DROPPED_EMPTY
            and tuple(d(freya, 19, 25, 13, 0, True, 4)[:3]) == (STEP_MAPPED, 2553, 16)
            and d(freya, 19, 25, 13, 0, False, 0)[0] == STEP_DROPPED_EMPTY
            and tuple(d(freya, 19, 25, 13, 0, False, 4)[:3]) == (STEP_BYPASSED, 25, 13)
            and d(freya, 19, 190, 4, 0, True, 0)[0] == STEP_DROPPED_EMPTY
            and tuple(d(freya, 19, 190, 4, 0, True, 2)[:3]) == (STEP_PASSED, 190, 4)
            and tuple(d(freya, 16, 25, 4, 919, True, 0)[:3]) == (STEP_MAPPED, 2553, 4)
            and d(freya, 18, 38, 8, 1, False, 0)[0] == STEP_BYPASSED
            and d(moogle, 19, 25, 4, 0, True, 0)[0] == STEP_DROPPED
            and d(moogle, 19, 25, 4, 0, True, 4)[0] == STEP_DROPPED
            and d(moogle, 19, 25, 4, 0, False, 0)[0] == STEP_DROPPED_EMPTY
            and d(moogle, 4, 1, -100, 0, True, 0)[0] == STEP_UNTOUCHED)


def replay_ops(rig, polish, *blocks, decision=None, dispatch=None) -> tuple:
    """PolishSelfTest's Replay -> (`steps` text -- "throw" when stock DeleteChar would index charSoundArray[-1] -- , ops
    dropped): each block's ops in order through FootstepDecision into fldchar's table semantics (16-18 find the TOP (anim,
    frame) record or create one; 19 DeleteChar's top shrink)."""
    got = replay_steps(rig, [op for block in blocks for op in block], polish=polish, decision=decision, dispatch=dispatch)
    return ("throw" if got["faults"] else steps_text(got["steps"])), got["steps_dropped"]


def replay250(rig, polish, decision=None, dispatch=None) -> tuple:
    """PolishSelfTest's Replay over field 250's twelve ops (:data:`FIELD250_STEPS`)."""
    return replay_ops(rig, polish, FIELD250_STEPS, decision=decision, dispatch=dispatch)


#: Guard2930: field 2930 Zidane_Init's RunModelCode(19, 190, 4, 0) (test2_790.txt:515 -- the bench field's F2d op);
#: GuardKey19: a 19 on Zidane's walk key (25, 13).
GUARD_2930 = ((19, 190, 4, 0),)
GUARD_KEY19 = ((19, 25, 13, 0),)
#: GuardReplayRows' literals -- polish_census.expected_steps(guard=True) over the same ops (a test pins them there):
#: (rig, polish, blocks, steps text, dropped)
GUARD_REPLAY_ORACLE = (
    (RIG_MOOGLE, True, ("FIELD250_STEPS", "GUARD_2930"), "[]", 13),
    (RIG_MOOGLE, False, ("FIELD250_STEPS", "GUARD_2930"), "[[25,4,919],[25,13,919],[38,0,919],[38,8,919]]", 0),
    (4, True, ("FIELD250_STEPS", "GUARD_KEY19"), "[[2553,4,919],[2553,16,919],[2558,0,919]]", 0),
    (4, True, ("GUARD_2930",), "[]", 1))


def guard_replay_rows(decision=None, dispatch=None, rigs=None) -> bool:
    """PolishSelfTest's GuardReplayRows: THE GUARD INSIDE A LOAD'S REPLAY (:data:`GUARD_REPLAY_ORACLE`) -- the moogle's
    twelve dropped then 2930's 19 on the emptied table ([] with 13: the bench's F2d), `polish off` stock's no-op on
    Zidane's four, Freya's 19 on (25, 13) DeleteChar's top shrink, a lone 19 on an empty table the guard's."""
    table = _rigs_of(rigs)
    for rig, polish, names, want, want_dropped in GUARD_REPLAY_ORACLE:
        blocks = [globals()[n] for n in names]
        if replay_ops(table[rig], polish, *blocks, decision=decision, dispatch=dispatch) != (want, want_dropped):
            return False
    return True


#: THE KIT PLAYER'S footstep registrations (the bench field 30606's player Init: the blank template's RunModelCode 16 / 17 /
#: 18 on Zidane's four keys, Arg4 912 / 912 / 1 -- read off the seated build; a template-gated test pins them there): the
#: stand-in's FAKE_FIELD_FOOTSTEPS[30606], F2d's precondition (a drop rig drops all twelve, so 2930's 19 meets an EMPTY table).
KIT_PLAYER_STEPS = ((16, 25, 4, 912), (17, 25, 4, 912), (18, 25, 4, 1), (16, 25, 13, 912), (17, 25, 13, 912),
                    (18, 25, 13, 1), (16, 38, 0, 912), (17, 38, 0, 912), (18, 38, 0, 1), (16, 38, 8, 912),
                    (17, 38, 8, 912), (18, 38, 8, 1))


def field250_table(polish, decision=None, rigs=None, dispatch=None) -> str | None:
    """PolishSelfTest's Field250Table: every rig's `steps` / dropped after one load of field 250 == :data:`FIELD250_ORACLE`
    (polish on), or Zidane's four with 0 dropped on every rig (polish off -- the calibration red)."""
    table = _rigs_of(rigs)
    if len(FIELD250_ORACLE) != len(table):
        return f"the oracle covers {len(FIELD250_ORACLE)} rigs, the table {len(table)}"
    for i, rig in enumerate(table):
        steps, dropped = replay250(rig, polish, decision, dispatch)
        want = steps_text(FIELD250_ORACLE[i] if polish else FIELD250_ORACLE[0])
        want_dropped = len(FIELD250_STEPS) if polish and want == "[]" else 0
        if steps != want or dropped != want_dropped:
            return f"rig {i}: steps {steps} dropped {dropped}, want {want} dropped {want_dropped}"
    return None


def bone_table(rule, rigs=None) -> str | None:
    """PolishSelfTest's BoneTable: ``rule(rig, bone, polish) -> (bone', verdict)`` over every rig x both lever states x
    :data:`POLISH_BONE_SAMPLE` == :data:`POLISH_HAND_ORACLE` (12 / 13 remapped, any other a note; off a bypass)."""
    table = _rigs_of(rigs)
    if len(POLISH_HAND_ORACLE) != len(table):
        return f"the oracle covers {len(POLISH_HAND_ORACLE)} rigs, the table {len(table)}"
    for i, rig in enumerate(table):
        for polish in (True, False):
            for bone in POLISH_BONE_SAMPLE:
                got, v = rule(rig, bone, polish)
                want = bone if not polish else POLISH_HAND_ORACLE[i][0] if bone == 12 else \
                    POLISH_HAND_ORACLE[i][1] if bone == 13 else bone
                want_v = ATTACH_BYPASS if not polish else ATTACH_REMAP if bone in (12, 13) else ATTACH_NOTE
                if got != want or v != want_v:
                    return (f"rig {i} bone {bone}{'' if polish else ' (polish off)'} -> {got} (verdict {v}), want {want} "
                            f"(verdict {want_v})")
    return None


def mesh_table(keep) -> str | None:
    """PolishSelfTest's MeshTable over ``keep(dressed, polish)``."""
    if not keep(False, True) or not keep(False, False):
        return "an undressed body's op is kept"
    if keep(True, True):
        return "a dressed body's op is dropped"
    if not keep(True, False):
        return "`polish off` keeps a dressed body's op"
    return None


def light_table(rule) -> str | None:
    """PolishSelfTest's LightTable over ``rule(model, has_own_row, dress_src, has_src_row, polish)``."""
    if rule(192, True, 98, True, True) != 192:
        return "a dressed Freya whose model HAS a row keeps it"
    if rule(192, False, 98, True, True) != 98 or rule(5467, False, 98, True, True) != 98:
        return "a dressed body with no own row takes its SOURCE row 98"
    if rule(192, False, 98, False, True) != DEFAULT_MCF_ROW:
        return "no own row and no 98 row -> the default row"
    if rule(220, False, 0, True, True) != DEFAULT_MCF_ROW:
        return "an undressed body with no own row -> the default row, never 98"
    if rule(98, True, 0, True, True) != 98:
        return "an undressed Zidane keeps his own row"
    if rule(192, False, 98, True, False) != DEFAULT_MCF_ROW:
        return "`polish off` -> the default row (s140)"
    if rule(192, True, 98, True, False) != 192:
        return "`polish off` keeps an own row"
    return None


def ghost_table(rule) -> str | None:
    """PolishSelfTest's GhostTable over ``rule(lp_model, lp_dress_src, polish)``."""
    if rule(192, 98, True) != 98 or rule(220, 98, True) != 98:
        return "a dressed local player: its SOURCE row 98"
    if rule(98, 0, True) != 98 or rule(5489, 0, True) != 5489:
        return "an undressed local player: its model"
    if rule(192, 98, False) != 192:
        return "`polish off`: s140's lp.model"
    return None


def polish_on_table(rule) -> str | None:
    """PolishSelfTest's PolishOnTable over ``rule(polish_off, selftest_role)``."""
    if not rule(False, True) or not rule(False, False):
        return "on by default, any role"
    if rule(True, True):
        return "`polish off` turns it off on the selftest role"
    if not rule(True, False):
        return "`polish off` never acts off the selftest role"
    return None


def mcf250_table(light_rule=None, ghost_rule=None, mcf=None, tint_fn=None, core=None, ghost_core=None) -> str | None:
    """PolishSelfTest's Mcf250Table: field 250's three rows (``mcf``, default :data:`FIELD250_MCF`) through the lookup's
    twin (:func:`mcf_char`), DressedCharRow's OWN core (:func:`dressed_row_core`, ``core`` replacing it: CoreRow -- its
    `used` witness required to equal :func:`light_row_rule`'s answer, ``light_rule`` replacing that), ApplyGhostLighting's
    OWN core (:func:`ghost_row_core`, ``ghost_core`` replacing it; ``ghost_rule`` the stand-in rule it is handed) and
    fldmcf's tint -- the dressed Freya (F4) and the ghost wearing her model (F4g) take row 98: (80, 96, 120) on floor 0,
    (56, 72, 88) on floors 1-2; `polish off` the default row (128, 128, 128) / (104, 104, 96); DefaultMcfRow is the row the
    stock -1 lookup finds; no 98 row -> the default; an undressed Zidane reads his own 98; the ghost's OWN row (176) wins
    over the stand-in, an undressed local player (Zidane) stands in with his 98, no local player reads the default."""
    lr, gr, tf, cr = light_rule or light_row_rule, ghost_rule or ghost_lp_row_rule, tint_fn or mcf_tint, core or dressed_row_core
    gc = ghost_core or ghost_row_core
    mcf = FIELD250_MCF if mcf is None else mcf
    no98 = {"chars": tuple(c for c in mcf["chars"] if c[0] != 98), "lights": mcf["lights"]}

    def core_row(m, model, src, polish):
        own = mcf_char(m, model)
        row, used = cr(m, model, src, own, polish)
        has_src = src != 0 and mcf_char(m, src) is not None
        return (used if used == lr(model, own is not None, src, has_src, polish) else -1), row

    def tint_of(row, light):
        return "none" if row is None else ",".join(str(x) for x in tf(row[3], light))

    stock, mine = mcf_char(mcf, -1), mcf_char(mcf, DEFAULT_MCF_ROW)
    if stock is None or mine is None or stock[0] != mine[0] or mine[0] != 0xFFFF:
        return "DefaultMcfRow is not the row stock's default lookup (-1) finds"
    (on, r_on), (off, r_off) = core_row(mcf, 192, 98, True), core_row(mcf, 192, 98, False)
    if on != 98 or off != DEFAULT_MCF_ROW or r_off is not None:
        return (f"the dressed Freya's row: polish on {on}, off {off} (want 98 / 65535; -1 = the core's witness and "
                f"LightRowRule part)")
    t0, t1 = tint_of(r_on, (0, 0, 0)), tint_of(r_on, (-3, -3, -4))
    if t0 != "80,96,120" or t1 != "56,72,88":
        return f"the 98 row's tint {t0} / {t1}"
    lit = r_off if r_off is not None else stock
    d0, d1 = tint_of(lit, (0, 0, 0)), tint_of(lit, (-3, -3, -4))
    if d0 != "128,128,128" or d1 != "104,104,96":
        return f"the default row's tint {d0} / {d1}"
    no98_used, no98_row = core_row(no98, 192, 98, True)
    if no98_used != DEFAULT_MCF_ROW or no98_row is not None:
        return "a mapconfig with no 98 row did not fall to the default"
    zid_used, zid_row = core_row(mcf, 98, 0, True)
    if zid_used != 98 or tint_of(zid_row, (0, 0, 0)) != "80,96,120":
        return "an undressed Zidane did not read his own 98 row"

    (rg, g), (rg_off, g_off) = gc(mcf, 192, True, 192, 98, True, rule=gr), gc(mcf, 192, True, 192, 98, False, rule=gr)
    if g != 98 or g_off != DEFAULT_MCF_ROW or tint_of(rg, (0, 0, 0)) != "80,96,120" or \
            tint_of(rg_off, (0, 0, 0)) != "128,128,128":
        return (f"the ghost wearing the dressed Freya: polish on {g} {tint_of(rg, (0, 0, 0))}, off {g_off} "
                f"{tint_of(rg_off, (0, 0, 0))} (want 98 80,96,120 / 65535 128,128,128)")
    rg_own, g_own = gc(mcf, 176, True, 192, 98, True, rule=gr)
    if g_own != 176 or tint_of(rg_own, (0, 0, 0)) != "64,80,104":
        return f"a ghost whose own model has a row (176) read {g_own} (the stand-in before the ghost's own row)"
    rg_zid, g_zid = gc(mcf, 192, True, 98, 0, True, rule=gr)
    if rg_zid is None or g_zid != 98:
        return f"an undressed local player (Zidane) did not stand in with its model: {g_zid}"
    rg_nolp, g_nolp = gc(mcf, 192, False, 192, 98, True, rule=gr)
    if g_nolp != DEFAULT_MCF_ROW or tint_of(rg_nolp, (0, 0, 0)) != "128,128,128":
        return f"no local player: the ghost read {g_nolp} (want the default 65535)"
    rg_no98, g_no98 = gc(no98, 192, True, 192, 98, True, rule=gr)
    if rg_no98 is None or g_no98 != DEFAULT_MCF_ROW:
        return f"a mapconfig with no 98 row: the ghost read {g_no98} (want the default 65535)"
    return None


def reset_row(reset=None) -> bool:
    """PolishSelfTest's ResetRow over a model of the per-load statics: every one set away from its sentinel (counts 7, the
    light rows 98, the attach ids 13, the logged flags true, the go a LIVE stand-in object -- the engine probes with the
    EventEngine's own) and the `polish` lever held OFF (``_polishOff`` True), then OnSoundTableReset (``reset``, default
    :func:`on_sound_table_reset`) -- True when every one reads its sentinel after AND the lever is still off (a load never
    releases it)."""
    away = {}
    for k, v in POLISH_LOAD_SENTINELS.items():
        if v is None:
            away[k] = object()
        elif isinstance(v, bool):
            away[k] = True
        elif k in ("LightRow", "GhostLightRow"):
            away[k] = 98
        else:
            away[k] = 7 if v == 0 else 13
    away["_polishOff"] = True
    (reset or on_sound_table_reset)(away)
    lever = away.pop("_polishOff", None)
    return away == POLISH_LOAD_SENTINELS and lever is True


# ---- PolishSelfTest's mutants (each required to be caught by its table)
def mutant_ordinal_swap(rig, code, anim, frame, sound) -> tuple:
    """MutantOrdinalSwap: the rig pair's A <-> B."""
    v, a, f, s = footstep_rule(rig, code, anim, frame, sound)
    if v == STEP_MAPPED:
        r = _rig_cols(rig)
        walk = a == r["walk"]
        pa, pb = (r["walk_step_a"], r["walk_step_b"]) if walk else (r["run_step_a"], r["run_step_b"])
        f = pb if f == pa else pa
    return v, a, f, s


def mutant_nineteen_harmless(rig, code, anim, frame, sound) -> tuple:
    """MutantNineteenHarmless: a drop rig's 19 sent on to stock DeleteChar (the lane's "19 is harmless")."""
    got = footstep_rule(rig, code, anim, frame, sound)
    return (STEP_PASSED,) + tuple(got[1:]) if got[0] == STEP_DROPPED and code == 19 else got


def mutant_sound_any_code(rig, code, anim, frame, sound) -> tuple:
    """MutantSoundAnyCode: the step sound on codes 18 / 19 too (18's Arg4 is the pitch flag)."""
    v, a, f, s = footstep_rule(rig, code, anim, frame, sound)
    r = _rig_cols(rig)
    return (v, a, f, r["step_sound"]) if v == STEP_MAPPED and r["step_sound"] != 0 else (v, a, f, s)


def mutant_any_frame(rig, code, anim, frame, sound) -> tuple:
    """MutantAnyFrame: any frame of 25 / 38 mapped (no pair check) -- the anim to the rig's walk / run, the frame as read."""
    v, a, f, s = footstep_rule(rig, code, anim, frame, sound)
    if v == STEP_PASSED and anim in (25, 38):
        r = _rig_cols(rig)
        return STEP_MAPPED, r["walk"] if anim == 25 else r["run"], f, s
    return v, a, f, s


def mutant_bone_swap(rig, bone, polish) -> tuple:
    """MutantBoneSwap: 12 -> R_hand_end, 13 -> R_hand."""
    if polish and bone in (12, 13):
        r = _rig_cols(rig)
        return (r["hand_bone_end"] if bone == 12 else r["hand_bone"]), ATTACH_REMAP
    return attach_bone_rule(rig, bone, polish)


def mutant_bone_any(rig, bone, polish) -> tuple:
    """MutantBoneAny: every bone to the rig's hand."""
    return (_rig_cols(rig)["hand_bone"], ATTACH_REMAP) if polish else (bone, ATTACH_BYPASS)


def mutant_mesh_lever_blind(dressed, polish) -> bool:
    """MutantMeshLeverBlind: the drop ignores the lever."""
    return not dressed


def mutant_src_first(model, has_own_row, dress_src, has_src_row, polish) -> int:
    """MutantSrcFirst: the source row before an own row."""
    if dress_src != 0 and polish and has_src_row:
        return int(dress_src) & 0xFFFF
    return int(model) & 0xFFFF if has_own_row else DEFAULT_MCF_ROW


def mutant_no_src_fallback(model, has_own_row, dress_src, has_src_row, polish) -> int:
    """MutantNoSrcFallback: s140 -- the default row."""
    return int(model) & 0xFFFF if has_own_row else DEFAULT_MCF_ROW


def mutant_ghost_model(lp_model, lp_dress_src, polish) -> int:
    """MutantGhostModel: s140's ApplyGhostLighting (the local player's po.model)."""
    return lp_model


def mutant_polish_any_role(polish_off, self_test_role) -> bool:
    """MutantPolishAnyRole: a lever that acts on a client too."""
    return not polish_off
