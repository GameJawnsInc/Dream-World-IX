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
"""
from __future__ import annotations

import re

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
