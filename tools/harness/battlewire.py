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


def control_hex(menu_open: bool) -> str:
    """The ``netsync bctl`` argument for one control frame (NetSyncBattle.BuildControl): ``"00 00"`` shut, ``"00 01"``
    open."""
    return hex_bytes(bytes([0, 1 if menu_open else 0]))


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

#: The selftest bench end's battle nonce (NetSyncEnd.BenchNonce, private): ``peer.end.nonce`` 181 on every bench end.
BENCH_NONCE = 0xB5
#: The end trail's cap (NetSyncEnd.TrailCap, private): past 48 distinct entries one "..." marks the cap.
TRAIL_CAP = 48

# ---- s104: the guest presentation
PRESENT_NONE = 0
PRESENT_VICTORY = 1
PRESENT_CLOSE = 2
PRESENT_HOLD = 3
PRESENT_NAMES = {PRESENT_VICTORY: "victory", PRESENT_CLOSE: "close", PRESENT_HOLD: "hold"}
W1_MS = 4000
W2_MS = 8000
GUEST_ON, GUEST_OFF, GUEST_SETTLE = 0, 1, 2
GUEST_MODE_NAMES = {GUEST_ON: "on", GUEST_OFF: "off", GUEST_SETTLE: "settle"}

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
                  bench: bool | None = None) -> dict:
    """An end block the way HarnessAgent publishes it: ``host.end`` (AppendEndBlock) without the three peer fields,
    ``peer.end`` (AppendPeerEnd) with ``rows``, ``bench``, ``nonce`` and ``wire_seq``."""
    doc = {"kind": block["kind"], "kind_name": kind_name(block["kind"]), "phase": block["phase"],
           "seq": block["seq"], "result": block["result"], "ui": block["ui"], "res_state": block_state(block),
           "loading": block_loading(block), "flags": block["flags"], "win_pose": block["win_pose"],
           "manifest_len": block.get("manifest_len", 0)}
    if bench is not None:
        doc.update(rows=0, bench=bool(bench), nonce=int(nonce or 0), wire_seq=int(wire_seq or 0))
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
    growth, skipped."""
    data = bytes(payload) if payload is not None else None
    if data is None or offset < 0 or offset > len(data):
        return None, "the unit records overran the frame", 0
    found, skipped, p = None, 0, offset
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
                     "manifest_len": length - END_BLOCK_LEN if flags & FLAG_MANIFEST else 0}
        else:
            skipped += 1
        p = body + length
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
