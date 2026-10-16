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
"""
from __future__ import annotations

import re
import struct

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
