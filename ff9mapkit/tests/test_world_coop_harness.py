"""[ff9mapkit netsync s144] WORLD-MAP CO-OP's REPO HARNESS CORE -- what the repo builds on the s144 patch: the stand-in's world
model (fakegame's `worldwait` rung) and its fault levers, the driver (Session.world_battle, the `bench worldfreeze` gate),
the accessors, the section-7 readers (b6 / b7), and the call-site twins battlewire keeps beside piece D's pure ones.

tests/test_world_coop.py pins the ENGINE's pure steps (every FreezeRow / RejoinRow / OvlRow evaluated against battlewire's
twins). This file pins the rest:

  * THE WORDS: every battlewire rendering of an engine line (the overlay's words, the world battle verb's statuses and
    refusals, the freeze / rejoin / hold / redirect / teleport lines) decomposes into WHOLE string literals of the live patch
    stack's own file -- and a one-word mutant does not (the check can fail).
  * THE CHAIN: battlewire's twin of Update's overlay chain runs its branches in the stack's call-site order.
  * THE STAND-IN BENCH: two legs driven through the real Session against the stand-in -- SOLO (the selftest role under
    `bench 1`: the hold, the freeze, the keys, the full map, a second world visit's edge, the lever, the control, the world
    battle verb's round trip, the release) and the FOLLOWED CLIENT (the rejoin's arm and landing with the host's snapshot,
    the hold, the redirect, an unregistered field, a stale snapshot, F11, the waiting line on the world map and on a field,
    an old host's fallback). Each row judged on a witness the stand-in's ENGINE half does not compute (x / z, ui_state,
    field_id, the published words) beside the engine's own claim.
  * EVERY TWIN CAN FAIL: each pure twin the three s144 selftests pin, drifted by one line in memory, turns at least one of
    the engine's own selftest rows (evaluated against the twins: tests/test_world_coop.py's tables) red.
  * EVERY ROW CAN FAIL: each fault lever (FG.WORLD_FAULTS) turns EXACTLY its WORLD_FAULT_REDS rows red; the faults
    together cover every row; the s143 stand-in (caps_through("leaderguard")) reads exactly OLD_PREDICTED red, and the solo
    leg under the calibration lever (`bench worldfreeze off`) exactly LEVER_PREDICTED.
"""
import json
import pathlib
import re
import struct
import sys

import pytest

from ._patchstack import msr, net_lines, net_lines_ordered

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import HarnessError, Session                              # noqa: E402
from harness import battlewire as BW                                   # noqa: E402
from harness import channel as CH                                      # noqa: E402
from harness import coop_peer as CP                                    # noqa: E402
from harness import fakegame as FG                                     # noqa: E402
from harness.fakegame import FakeGame                                  # noqa: E402

PATCH = "s144-netsync-world-wait.patch"
FIELDS = (250, 300, 6603)                     # the stand-in install's custom registrations (250 / 300 are stock anyway)


# ------------------------------------------------------------------------------------------------ the engine's literals
_LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')


_LINES_CACHE: dict = {}


def _literal_lines(file_name: str) -> list:
    """The C# string literals the LIVE stack leaves in ``file_name``, per source line in FILE order (unescaped)."""
    if file_name not in _LINES_CACHE:
        rows = []
        for ln in net_lines_ordered(file_name, r'"'):
            lits = [m.group(1).replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\") for m in _LIT.finditer(ln)]
            if any(lits):
                rows.append([lit for lit in lits if lit])
        _LINES_CACHE[file_name] = rows
    return _LINES_CACHE[file_name]


#: a piece's literals must all come from one window of this many consecutive literal-bearing source lines (a C# string
#: built across a few `+` continuation lines and its `?:` alternatives) -- never two stray literals from far apart
_WINDOW = 8


def _whole_literals(piece: str, lits: set) -> bool:
    """``piece`` is a concatenation of WHOLE literals of ``lits`` (a DP over its cut points)."""
    ok = [False] * (len(piece) + 1)
    ok[0] = True
    for i in range(len(piece)):
        if ok[i]:
            for j in range(i + 1, len(piece) + 1):
                if not ok[j] and piece[i:j] in lits:
                    ok[j] = True
    return ok[len(piece)]


def _piece_said(piece: str, rows: list) -> bool:
    """``piece`` is whole literals of ONE window of nearby source lines (anchored on a line whose literal starts it)."""
    for n, lits in enumerate(rows):
        if not any(piece.startswith(lit) for lit in lits):
            continue
        window = {lit for row in rows[max(0, n - 2):n + _WINDOW] for lit in row}
        if _whole_literals(piece, window):
            return True
    return False


def _says(file_name: str, text: str, *values) -> bool:
    """The engine can SAY ``text``: cut at each variable's rendering (``values``), every piece is whole literals of one
    window of nearby lines of the live stack's ``file_name``."""
    rows = _literal_lines(file_name)
    marked = text
    for v in sorted({str(v) for v in values}, key=len, reverse=True):
        marked = marked.replace(v, "\0")
    return all(_piece_said(p, rows) for p in marked.split("\0") if p)


# (file, the twin's rendering, the variables it carries) -- each must be the engine's own words
_W, _D, _S, _F = 9011, 31337, 27182, 4242      # a world map, a destination, a scene, another field: distinctive renderings


def _L(text: str) -> str:
    """A LOG line as Memoria.log carries it: Log.Message's "[NetSync] " prefix (the engine's literal holds it)."""
    return "[NetSync] " + text


SAID = [
    # THE OVERLAY'S WORDS (NetSyncClient.SetOverlay's switch)
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_WAITING, 0, code="ABCD"), "ABCD"),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_WAITING, 0), BW.SESSION_CODE_NONE),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_PEER_ELSEWHERE, _D), _D),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_PEER_ELSEWHERE, _D, follow_host=False), _D),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_FOLLOWING, _D), _D),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_PEER_NO_FIELD, _D), _D),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_RECONNECTING, 17), 17),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_RECONNECTING, 17, mirroring=True), 17),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_CONNECTING, 1, code="ABCD", relay_url="ws://r"), "ABCD"),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_CONNECTING, 1, peer="10.0.0.9", port=49201), "10.0.0.9", 49201),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_CONNECTING, 0, code="ABCD", relay_url="ws://r"), "ABCD", "ws://r"),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_CONNECTING, 0, role="host", relay_url="ws://r"), "ws://r"),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_CONNECTING, 0, role="host", port=49201), 49201),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_CONNECTING, 0, peer="10.0.0.9", port=49201), "10.0.0.9", 49201),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_ELSEWHERE, 0, code="ABCD", target_field=_D), "ABCD", _D),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_ELSEWHERE, 0, role="host", code="ABCD", target_field=_D), "ABCD", _D),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_NO_CODE, 0)),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_HOST_WORLD, 0)),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_REJOINING, _D), _D),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_WORLD_HOLD, _D), _D, BW.WORLD_HOLD_MS // 1000),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_HOST_TITLE, 0)),
    ("NetSyncClient.cs", BW.overlay_words(BW.OVL_HOST_AWAY, 0)),
    # THE REJOIN's lines (NetSyncClient)
    # (a reason passed in from another site is a variable of the format line -- and said by its own site, below)
    ("NetSyncClient.cs", _L(BW.log_world_rejoin_waits(_D, "a world script holds control")), _D, "a world script holds control"),
    ("NetSyncClient.cs", BW.world_arm_refusal(True, 3, False, False, True, True, False, False, False, False, None)),
    ("NetSyncClient.cs", BW.world_arm_refusal(True, 3, False, False, True, True, False, True, True, False, None)),
    ("NetSyncClient.cs", _L(BW.log_world_pass(_F, _W, BW.REDIR_PASS_NOT_FOLLOWING, _D)), _F, _W),
    ("NetSyncClient.cs", _L(BW.log_follow_cancelled(_D, _F)), _D, _F),
    ("NetSyncClient.cs", _L(BW.log_follow_warp_dropped(_D)), _D),
    ("NetSyncClient.cs", _L(BW.log_follow_latch_dropped(_D, _W)), _D, _W),
    ("NetSyncClient.cs", _L(BW.log_pass_entrance_kept(_D, 9993, 11)), _D, 9993, 11),
    ("NetSyncClient.cs", _L(BW.log_world_rejoining(_D, _W)), _D, _W),
    ("NetSyncClient.cs", _L(BW.log_world_rejoining(_D, _W, intent=True)), _D, _W),
    ("NetSyncClient.cs", _L(BW.log_world_rejoin_landed(_D, _D, 812)), _D, 812),
    ("NetSyncClient.cs", _L(BW.log_world_rejoin_landed(_F, _D, 812)), _F, _D, 812),
    ("NetSyncClient.cs", _L(BW.log_world_rejoin_timeout(_D, _W, None)), _D, _W, BW.WORLD_ARM_TIMEOUT_MS // 1000),
    ("NetSyncClient.cs", _L(BW.log_world_rejoin_timeout(_D, _W, "a fade is in flight")), _D, _W,
     BW.WORLD_ARM_TIMEOUT_MS // 1000, "a fade is in flight"),
    ("NetSyncClient.cs", _L(BW.log_world_hold_latched(_F, _W)), _F, _W, BW.WORLD_HOLD_MS // 1000),
    ("NetSyncClient.cs", _L(BW.log_world_hold_released(_F, True)), _F, BW.WORLD_HOLD_MS // 1000),
    ("NetSyncClient.cs", _L(BW.log_world_hold_released(_F, False)), _F),
    ("NetSyncClient.cs", _L(BW.log_world_hold_ended(_F, _D)), _F, _D),
    ("NetSyncClient.cs", _L(BW.log_world_redirect(_F, _D, _W)), _F, _D, _W),
    ("NetSyncClient.cs", _L(BW.log_world_pass(_F, _W, BW.REDIR_PASS_HOST, _D)), _F, _W),
    ("NetSyncClient.cs", _L(BW.log_world_pass(_F, _W, BW.REDIR_PASS_UNREGISTERED, _D)), _F, _W, _D),
    ("NetSyncClient.cs", _L(BW.log_world_pass(_F, _W, BW.REDIR_PASS_NO_SNAPSHOT, _D)), _F, _W),
    ("NetSyncClient.cs", _L(BW.log_world_pass(_F, _W, BW.REDIR_PASS_OFF_FIELD, _D)), _F, _W),
    ("NetSyncClient.cs", _L(BW.log_world_pass(_F, _W, BW.REDIR_PASS_HELD, _D)), _F, _W, _D),          # [review 2]
    ("NetSyncClient.cs", _L(BW.log_world_hold_rides(_F, _D)), _F, _D),
    ("NetSyncClient.cs", _L(BW.log_field_follow_held(_D, _F)), _D, _F, BW.WORLD_HOLD_MS // 1000),
    ("NetSyncClient.cs", _L(BW.log_world_intent_unregistered(_D)), _D),
    ("NetSyncClient.cs", _L(BW.log_teleport_world(_D, _W)), _D, _W),
    ("NetSyncClient.cs", _L(BW.log_teleport_declined(BW.TP_WORLD_SELFTEST)), BW.TP_WORLD_SELFTEST),
    ("NetSyncClient.cs", BW.TP_WORLD_SELFTEST),
    ("NetSyncClient.cs", BW.TP_WORLD_NOT_LIVE),
    ("NetSyncClient.cs", BW.tp_world_decline(False, _D, True, False)),
    ("NetSyncClient.cs", BW.tp_world_decline(False, _D, True, True)),
    ("NetSyncClient.cs", BW.tp_world_decline(True, 0, True, True)),
    ("NetSyncClient.cs", BW.tp_world_decline(True, _D, False, False), _D),
    # THE FREEZE's lines (NetSyncField)
    ("NetSyncField.cs", _L(BW.log_world_freeze_on("bench", _W)), "bench", _W),
    ("NetSyncField.cs", _L(BW.log_world_freeze_on("live", _W, autopilot=True)), "live", _W),
    ("NetSyncField.cs", _L(BW.log_world_freeze_lifted(_W, "why")), _W, "why"),
    ("NetSyncField.cs", BW.world_freeze_lift_why(True, True, True, False, False)),
    ("NetSyncField.cs", BW.world_freeze_lift_why(False, False, False, False, False)),
    ("NetSyncField.cs", BW.world_freeze_lift_why(True, False, False, False, True)),
    ("NetSyncField.cs", BW.world_freeze_lift_why(True, False, False, True, False)),
    ("NetSyncField.cs", _L(BW.log_world_freeze_released("~ menu", _W)), "~ menu", _W),
    ("NetSyncField.cs", _L(BW.LOG_WORLD_FREEZE_RELEASE_ENDED)),
    ("NetSyncField.cs", _L(BW.LOG_WORLD_FREEZE_REARMED)),
    # [ff9mapkit netsync s145] the world load's re-arm line is s144's (a world load keeps a release from s145: the s144 stack says
    # it, the live one no longer -- tests/test_world_diorama.py); the TITLE's is the live one's
    ("NetSyncField.cs", _L(BW.LOG_WORLD_FREEZE_REARMED_TITLE)),
    ("NetSyncField.cs", _L(BW.LOG_WORLD_FREEZE_OFF)),
    ("NetSyncField.cs", _L(BW.decline_line("what", f"world map {_W}")), "what", _W),        # DeclineOnceHere's world line
    ("NetSyncField.cs", BW.WORLD_POLL_DECLINE),
    ("NetSyncField.cs", BW.WORLD_UI_DECLINE_MAP),
    ("NetSyncField.cs", BW.WORLD_UI_DECLINE_LOCATION),
    ("NetSyncField.cs", BW.POLL_DECLINE_PICKUP),
    ("NetSyncField.cs", BW.POLL_DECLINE_ATE),
    # (the op is DoEventCode's literal, passed in: a variable here)
    ("NetSyncField.cs", BW.world_scripted_battle_decline("ENCOUNT", _S), "ENCOUNT", _S),
    ("NetSyncField.cs", BW.WORLD_FREEZE_BENCH_REFUSAL),
    ("NetSyncField.cs", _L(BW.LOG_WORLD_FREEZE_ON)),
    ("NetSyncField.cs", _L(BW.LOG_WORLD_FREEZE_RELEASED)),
    # THE WORLD BATTLE VERB (Ff9mkDebugMenu) and the release row's refusal line
    ("Ff9mkDebugMenu.cs", BW.world_battle_arm_status(_S, 3, True), _S, 3),
    ("Ff9mkDebugMenu.cs", BW.world_battle_arm_status(_S, -1, False), _S),
    ("Ff9mkDebugMenu.cs", BW.world_battle_armed_refusal(_S), _S),
    ("Ff9mkDebugMenu.cs", BW.world_battle_started(_S, 3, True, _W), _S, 3, _W),
    ("Ff9mkDebugMenu.cs", BW.world_battle_started(_S, -1, False, _W), _S, _W),
    ("Ff9mkDebugMenu.cs", BW.world_battle_dropped(_S, BW.world_battle_own_result(4)), _S, 4),
    ("Ff9mkDebugMenu.cs", BW.world_battle_dropped(_S, BW.world_battle_stale(3412)), _S, 3412),
    ("Ff9mkDebugMenu.cs", _L(BW.log_release_refused("x")), "x"),
]


@pytest.mark.parametrize("file_name,text,values", [(f, t, v) for f, t, *v in SAID],
                         ids=[f"{f}:{t[:40]}" for f, t, *_ in SAID])
def test_every_twin_line_is_the_engines_own_words(file_name, text, values):
    assert _says(file_name, text, *values), text


def test_the_words_check_can_fail():
    """A check that cannot fail proves nothing: a one-word drift of a twin's rendering (or the right words against the wrong
    file) is refused."""
    assert _says("NetSyncClient.cs", _L(BW.log_world_rejoin_waits(_D, "x")), _D, "x")
    assert not _says("NetSyncClient.cs", _L(BW.log_world_rejoin_waits(_D, "x")).replace("waits:", "waiting:"), _D, "x")
    assert not _says("NetSyncClient.cs", BW.log_world_rejoin_waits(_D, "x"), _D, "x")      # the log line without its prefix
    assert not _says("NetSyncClient.cs", BW.overlay_words(BW.OVL_HOST_WORLD).replace("next stop", "next field"))
    assert not _says("NetSyncField.cs", BW.log_world_rejoining(_D, _W), _D, _W)            # the rejoin's line is the client's
    assert not _says("Ff9mkDebugMenu.cs", BW.world_battle_started(_S, 3, True, _W).replace("started", "begun"), _S, 3, _W)


def test_the_world_battle_refusals_run_in_the_engines_order():
    """WorldBattleRefusal's `return` reasons in file order are the twin's, gate by gate (each refused with every earlier gate
    passing), and each reason the engine's own words."""
    block = [ln for ln in net_lines_ordered("Ff9mkDebugMenu.cs", r".")]
    i = next(k for k, ln in enumerate(block) if ln.startswith("private static String WorldBattleRefusal("))
    j = next(k for k in range(i, len(block)) if block[k] == "return null;")
    engine = [_LIT.search(ln).group(1) for ln in block[i:j] if ln.startswith("return ") and '"' in ln]
    engine += ["(ValidateWireBoot's reason)"]
    # (each gate failed alone, with the variables its reason carries -- Int16 / SByte's MaxValue are computed there)
    gates = [(dict(world_hud=False), ()), (dict(sys_mode=1), (1,)), (dict(bee=True), ()), (dict(scene=-1), (-1, 32767)),
             (dict(group=-2), (-2, 127)), (dict(fading=True), ()), (dict(next_mode=1), ("0000", 1)),
             (dict(events_off=True), ()), (dict(phase=0), ()), (dict(full_map=True), ()), (dict(walker=False), ()),
             (dict(control=False), ()), (dict(travel=6), (6,)), (dict(topo=52), ()), (dict(registered=False), (0,)),
             (dict(boot_why="(ValidateWireBoot's reason)"), ("(ValidateWireBoot's reason)",))]
    twin = [BW.world_battle_refusal(**g) for g, _v in gates]
    assert all(w is not None for w in twin) and BW.world_battle_refusal() is None
    assert BW.world_battle_refusal(registered=False, boot_why="x", deep=False) is None        # the cheap re-check at the tick
    assert len(twin) == len(engine), (twin, engine)
    for t, e, (_g, values) in zip(twin, engine, gates):
        assert t.startswith(e), (t, e)
        assert _says("Ff9mkDebugMenu.cs", t, *values), t


def test_the_constants_are_the_engines():
    assert net_lines("NetSyncClient.cs", r"private const Int32 FollowStableMs = ")[0].startswith(
        f"private const Int32 FollowStableMs = {BW.FOLLOW_STABLE_MS};")
    assert any(ln.startswith(f"private const Int32 WorldBattleArmMs = {BW.WORLD_BATTLE_ARM_MS};")
               for ln in net_lines("Ff9mkDebugMenu.cs", r"WorldBattleArmMs = "))
    assert dict(zip(BW.HOST_FLAG_NAMES, (1 << i for i in range(8)))) == CH.State.HOST_FLAG_BITS
    assert BW.overlay_name(BW.OVL_HOST_AWAY) == "host_away" and BW.overlay_name(-2) is None and BW.overlay_name(99) is None
    assert BW.WORLD_POLL_READ_MASK & BW.HOST_OWNED_KEYS == BW.EV_CONFIRM | BW.EV_CANCEL | BW.EV_SPECIAL | BW.EV_MENU


# ------------------------------------------------------------------------------------------------ the overlay chain
def test_the_chain_twin_runs_in_the_engines_call_site_order():
    """Update's not-paired chain, as the live stack leaves it (call sites in file order), is the twin's branch order: the
    grace's countdown, THE WORLD GUEST's chain ahead of `local == null`, the peer lost, a field follow in flight, an
    unregistered host field, another screen, a battle, THE TAIL."""
    lines = net_lines_ordered("NetSyncClient.cs", r".")
    i = next(k for k, ln in enumerate(lines) if ln.startswith("SetOverlay(OvlReconnecting, SessionGraceLeftSec());"))
    want = ["else if (onWorld && WaitLineOn)", "SetWorldGuestOverlay(rs, peerLost);",
            'else if (onWorld && _role == "host" && peerLost)', "SetOverlay(OvlConnecting, 0);", "else if (local == null)",
            "SetOverlay(onField && !inScope ? OvlElsewhere : OvlOff);", "else if (peerLost)", "SetOverlay(OvlConnecting,",
            "else if (_followWarpPending >= 0)", "SetOverlay(OvlFollowing, _followWarpPending);",
            "SetOverlay(OvlPeerNoField, rs.Field);", "SetOverlay(OvlPeerElsewhere, rs.Field);",
            "else if (NetSyncBattle.PeerBattleLive)", "SetOverlay(OvlOff);", "Int32 tail = FieldWaitTail(WaitLineOn && _hostWorld,",
            "if (tail != OvlKeep)", "SetOverlay(tail);"]
    got, k = [], i + 1
    for w in want:
        while k < len(lines) and not lines[k].startswith(w):
            k += 1
        assert k < len(lines), (w, got)
        got.append(lines[k])
        k += 1
    C = BW.guest_overlay_chain
    base = dict(host_valid=True, host_field=300, my_field=250, wait_on=True, follow_host=True)
    assert C(**base) == (BW.OVL_PEER_ELSEWHERE, 300)
    assert C(**base, grace=True, grace_left=9, on_world=True, peer_lost=True) == (BW.OVL_RECONNECTING, 9)
    assert C(**dict(base, local=False), on_world=True, peer_lost=True) == (BW.OVL_CONNECTING, 1)
    assert C(**dict(base, local=False, wait_on=False), on_world=True) == (BW.OVL_OFF, 0)          # s143 for a free roamer
    assert C(**base, peer_lost=True, follow_pending=300) == (BW.OVL_CONNECTING, 1)
    assert C(**base, follow_pending=300, host_registered=False) == (BW.OVL_FOLLOWING, 300)
    assert C(**base, host_registered=False, battle_live=True) == (BW.OVL_PEER_NO_FIELD, 300)
    assert C(**dict(base, host_field=0), battle_live=True, host_world=True) == (BW.OVL_OFF, 0)
    assert C(**dict(base, host_field=0), host_world=True) == (BW.OVL_HOST_WORLD, 0)
    assert C(**dict(base, host_field=0, wait_on=False), host_world=True) == (BW.OVL_WAITING, 0)   # a free roamer: s143
    assert C(**dict(base, host_field=250)) == (BW.OVL_OFF, 0)                                     # paired: the ghost
    assert C(**dict(base, host_field=0), current=BW.OVL_HOST_WORLD) == (BW.OVL_WAITING, 0)        # no keep window: waiting
    assert C(**dict(base, host_field=0), current=BW.OVL_HOST_WORLD, keep_window=True) == (BW.OVL_KEEP, 0)   # wire-2: kept
    assert C(**dict(base, host_field=0), current=BW.OVL_WAITING, keep_window=True) == (BW.OVL_WAITING, 0)   # its own lines only
    assert C(**dict(base, local=False, host_field=0), on_world=True, current=BW.OVL_HOST_WORLD, keep_window=True) == (BW.OVL_KEEP, 0)
    assert C(**dict(base, local=False, host_field=0), on_world=True, current=BW.OVL_HOST_WORLD) == (BW.OVL_OFF, 0)   # wire-1
    assert C(local=False, on_world=True, role="host", peer_lost=True) == (BW.OVL_CONNECTING, 0)    # a world-map host
    assert C(local=False, on_world=True, role="host") == (BW.OVL_OFF, 0)


# ------------------------------------------------------------------------------------------------ the stand-in, in-process
def _game(root, fields=FIELDS):
    (root / "x64").mkdir(parents=True)
    (root / "x64" / "FF9.exe").write_bytes(b"MZ")
    (root / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    mod = root / "FF9CustomMap"
    mod.mkdir()
    (mod / "DictionaryPatch.txt").write_text("".join(f"FieldScene {f} 11 T{f} T{f} {f}\n" for f in fields),
                                             encoding="utf-8")
    return root


def _fake(root, faults=(), caps=None) -> FakeGame:
    fake = FakeGame(root, fps=600)
    if caps is not None:
        fake.netsync_caps = caps
    fake.world_faults = set(faults)
    fake.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    fake.world_locations = {300: (150.0, 100.0, 10.0)}
    fake.world_swirl_frames = 40
    fake.world_exit_frames = 40
    return fake


def _session(root, fake) -> Session:
    return Session(game_path=root, run_dir=root / "run", save_dir=root / "player-saves", pid_probe=lambda: [],
                   launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False)


def _log(fake) -> str:
    return pathlib.Path(fake.memoria_log).read_text(encoding="utf-8", errors="replace")


class _Rows:
    """The stand-in bench's ledger: a row is (ok, detail); a step that cannot run reds its row 'not reached'."""

    def __init__(self):
        self.rows = {}

    def row(self, name, fn):
        try:
            ok, detail = fn()
        except Exception as err:                       # noqa: BLE001 -- any step that cannot run reds ITS row, never the bench
            ok, detail = False, f"not reached: {str(err)[:300]}"
        self.rows[name] = (bool(ok), detail)

    @property
    def red(self):
        return sorted(n for n, (ok, _d) in self.rows.items() if not ok)


def _w(st, key, default=None):
    """A `netsync.world` leaf off a state (absent = the default: an engine without the block)."""
    node = (st.netsync or {}).get("world")
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def _to_world(g, fake, wld=9011, x=100.0, z=100.0, *, from_field=False):
    """Stand the stand-in on world map ``wld`` and wait for a state PUBLISHED after it (never a cached earlier one)."""
    f0 = fake.frame
    fake.enter_world(wld, x, z, from_field=from_field)
    return g.wait_for(lambda s: s.on_world and s.world_id == wld and s.frame > f0 + 2, timeout=6.0, what="the world map")


def _hold_up(g, frames=30):
    st = g.state
    x0, z0 = st.world_x, st.world_z
    g.send(f"hold up {frames}")
    g.wait_frames(frames + 6)
    st = g.state
    return st, abs(st.world_x - x0) + abs(st.world_z - z0)


def _solo(g, fake) -> dict:
    """THE SOLO LEG (the selftest role under `bench 1`): newgame, 6603, the field's own WorldMap() exit onto 9011."""
    led = _Rows()
    g.newgame(settle=0)
    g.warp(6603)
    g.netsync("selftest", 1)
    g.netsync("bench", 1)
    base = dict(_w(g.state, "freeze") or {})
    st0 = _to_world(g, fake, from_field=True)

    def f0():
        latched = st0.follow_hold == 6603 and BW.log_world_hold_latched(6603, 9011) in _log(fake)
        return latched, f"hold {st0.follow_hold!r}"
    led.row("F0-HOLD", f0)

    def f1_walk():
        st, moved = _hold_up(g)
        f1_walk.st = st
        return moved < 2.0, f"moved {moved:.2f}u under the freeze"
    led.row("F1-WALK", f1_walk)

    def f1_keys():
        st = g.state
        fz = _w(st, "freeze") or {}
        ok = (fz.get("on") is True and fz.get("why") == "bench" and fz.get("skips", 0) - base.get("skips", 0) >= 20
              and fz.get("edges", 0) - base.get("edges", 0) == 1 and _log(fake).count(BW.log_world_freeze_on("bench", 9011)) == 1)
        return ok, f"freeze {fz!r}"
    led.row("F1-KEYS", f1_keys)

    def f2():
        k0 = _w(g.state, "freeze.keys", 0)
        g.teleport(150.0, 100.0)
        g.send("press confirm")
        g.wait_frames(10)
        st = g.state
        ok = (st.ui_state == "WorldHUD" and _w(st, "freeze.keys", 0) == k0 + 1
              and BW.decline_line(BW.WORLD_POLL_DECLINE, "world map 9011") in _log(fake))
        return ok, f"ui {st.ui_state} keys {k0}->{_w(st, 'freeze.keys')}"
    led.row("F2-CONFIRM", f2)

    def f2v():
        """freeze-key-closure-unwitnessed: a guest frozen ABOARD a vehicle (the stand-in's model: gEventGlobal[190] nonzero)
        presses Cancel -- the dispatchers' dismount / land key -- and stays aboard: the witness is the vehicle byte, beside
        `keys`. A mask that counts but returns F1's (`keys_counted_s143`) lets the Cancel through."""
        k0 = _w(g.state, "freeze.keys", 0)
        fake.world["vehicle"] = 6
        g.send("press cancel")
        g.wait_frames(10)
        st = g.state
        veh = st.raw["world"].get("vehicle")
        fake.world["vehicle"] = 0                    # back on foot (the world battle verb is on foot only)
        ok = veh == 6 and _w(st, "freeze.keys", 0) == k0 + 1 and st.ui_state == "WorldHUD"
        return ok, f"vehicle 6 -> {veh} after Cancel, keys {k0}->{_w(st, 'freeze.keys')}"
    led.row("F2V-VEHICLE", f2v)

    def f3():
        """WorldHUD's STOCK Select cycle: a New Game's world map lands in HUDNoMiniMap, so the first Select only turns the
        minimap on; the HUD -> FullMap step is the one the freeze refuses -- at most two presses, stopping once `map` counts."""
        m0 = _w(g.state, "freeze.map", 0)
        presses = 0
        for _ in range(2):
            g.send("press select")
            g.wait_frames(6)
            presses += 1
            if _w(g.state, "freeze.map", 0) != m0:
                break
        st = g.state
        ok = (_w(st, "freeze.map", 0) == m0 + 1
              and _log(fake).count(BW.decline_line(BW.WORLD_UI_DECLINE_MAP, "world map 9011")) == 1)
        g.send("press cancel")                       # stock: Cancel closes no full map (frozen: nothing at all)
        g.wait_frames(6)
        if fake.world_full_map:                      # the map OPENED (a fault, the lever, s143): a Select closes it (the
            g.send("press select")                   # stand-in's own state read: the test's cleanup, never its verdict)
            g.wait_frames(6)
        return ok, f"{presses} press(es): map {m0}->{_w(st, 'freeze.map')}"
    led.row("F3-MAP", f3)

    def f6():
        e0 = _w(g.state, "freeze.edges", 0)
        g.warp(6603)                                  # a field load ...
        _to_world(g, fake, from_field=True)           # ... and the second WorldMap() exit: a new world load
        st, moved = _hold_up(g, 10)
        ok = _w(st, "freeze.edges", 0) == e0 + 1 and moved < 2.0
        return ok, f"edges {e0}->{_w(st, 'freeze.edges')}, moved {moved:.2f}"
    led.row("F6-EDGE", f6)

    def f4():
        g.netsync("bench", "worldfreeze", "off")
        st, moved = _hold_up(g)
        fz = _w(st, "freeze") or {}
        k0 = fz.get("keys", 0)
        g.teleport(150.0, 100.0)
        g.send("press confirm")                      # the spectator's F1 mask still takes Confirm: no location
        g.wait_frames(10)
        st2 = g.state
        ok = (moved > 2.0 and fz.get("on") is False and fz.get("off") is True and st2.ui_state == "WorldHUD"
              and _w(st2, "freeze.keys", 0) == k0)
        return ok, f"moved {moved:.2f}, freeze {fz!r}, ui {st2.ui_state}"
    led.row("F4-LEVER", f4)

    def f5():
        if g.state.coop_world_wait:                   # the lever back on -- only where the engine has it (the probe)
            g.netsync("bench", "worldfreeze", "on")
        g.netsync("bench", 0)
        g.teleport(100.0, 100.0)
        st, moved = _hold_up(g)
        g.teleport(150.0, 100.0)
        g.send("press confirm")
        st2 = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=6.0, what="the location's field")
        return moved > 2.0 and st2.field_id == 300, f"moved {moved:.2f}, field {st2.field_id}"
    led.row("F5-CONTROL", f5)

    def wb():
        _to_world(g, fake, 9011, 120.0, 80.0)
        before = g.state.battle_epoch
        g.send("battle 67 0 rand")
        swirl = g.wait_for(lambda s: s.world_next_mode == 2, timeout=6.0, what="the swirl (nextMode 2)")
        wb.latch = _w(swirl, "rejoin.latch")
        st = g.wait_battle(timeout=10.0, after_epoch=before)
        ok = st.debug_status == BW.world_battle_started(67, 0, True, 9011) and st.ui_state == "BattleHUD"
        return ok, f"status {st.debug_status!r}, ui {st.ui_state}"
    led.row("WB-START", wb)
    led.row("WB-SWIRL", lambda: (getattr(wb, "latch", None) is True, f"latch {getattr(wb, 'latch', None)!r}"))

    def wb_return():
        fake.end_battle(1)
        st = g.wait_for(lambda s: s.ui_state in ("WorldHUD", "FieldHUD"), timeout=6.0, what="the battle's return")
        ok = (st.ui_state == "WorldHUD" and st.world_id == 9011 and abs(st.world_x - 120.0) < 1 and abs(st.world_z - 80.0) < 1
              and st.world_next_mode == 3)
        return ok, f"ui {st.ui_state} world {st.world_id} ({st.world_x}, {st.world_z}) next_mode {st.world_next_mode}"
    led.row("WB-RETURN", wb_return)

    def release():
        g.netsync("bench", "worldfreeze", "off")
        g.send("reset")
        g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        g.netsync("selftest", 1)
        st = g.wait_for(lambda s: s.netsync["forced"], timeout=5.0, what="the role again")
        n = _log(fake).count(BW.LOG_WORLD_FREEZE_RELEASED)
        return st.world_freeze_off is False and n == 1, f"off {st.world_freeze_off!r}, release lines {n}"
    led.row("R-RELEASE", release)
    return led.rows


def _client(g, fake) -> dict:
    """THE FOLLOWED-CLIENT LEG: a live followed session (the stand-in's ``follow_session``), its host on the wire."""
    led = _Rows()
    g.newgame(settle=0)
    g.warp(250)
    fake.follow_session(250, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, entrance=11)
    g.wait_frames(4)

    def arm():
        a0 = _w(g.state, "rejoin.arms", 0)
        fake.host_at(300)                                     # the host walks on while the guest stands on the world map
        _to_world(g, fake)
        st = g.wait_for(lambda s: s.follow_world_armed == 300, timeout=6.0, what="the arm")
        arm.st = st
        ok = (_w(st, "rejoin.arms", 0) == a0 + 1 and _w(st, "rejoin.last") == 300 and _w(st, "rejoin.why") is None
              and st.follow_on_world is True)
        return ok, f"arms {a0}->{_w(st, 'rejoin.arms')}, last {_w(st, 'rejoin.last')}, why {_w(st, 'rejoin.why')!r}"
    led.row("J-ARM", arm)

    def ovl():
        st = getattr(arm, "st", None) or g.state
        ok = (st.session_overlay == "rejoining" and st.session_overlay_detail == 300
              and st.session_overlay_text == BW.wait_line_text(BW.OVL_REJOINING, 300) and st.world_waitline_line == "rejoin")
        return ok, f"overlay {st.session_overlay!r} {st.session_overlay_detail!r}: {st.session_overlay_text!r}"
    led.row("J-OVL", ovl)

    def land():
        st0 = getattr(arm, "st", None) or g.state
        n0, t0 = _w(st0, "rejoin.lands", 0), _w(st0, "rejoin.timeouts", 0)
        st = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=8.0, what="the landing")
        g.wait_frames(4)
        st = g.state
        ok = (st.field_id == 300 and _w(st, "rejoin.lands", 0) == n0 + 1 and st.follow_world_armed == -1
              and _w(st, "rejoin.timeouts", 0) == t0 and st.netsync["session"]["mirroring"] is True
              and st.field_entrance == 11)
        return ok, (f"field {st.field_id}, lands {n0}->{_w(st, 'rejoin.lands')}, armed {st.follow_world_armed}, entrance "
                    f"{st.field_entrance}")
    led.row("J-LAND", land)

    def hold():
        g.warp(300)
        fake.host_at(300)
        a0 = _w(g.state, "rejoin.arms", 0)
        _to_world(g, fake, from_field=True)                    # the guest walks out on its own; the host stays on 300
        g.wait_frames(150)                                     # past FollowStableMs, inside the 15 s hold
        st = g.state
        held = (st.follow_hold == 300 and _w(st, "rejoin.arms", 0) == a0 and st.session_overlay == "world_hold"
                and "source-field hold" in (_w(st, "rejoin.why") or ""))
        st2 = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=25.0, what="the rejoin after the hold")
        return held and st2.field_id == 300, f"hold {st.follow_hold}, overlay {st.session_overlay!r}, then {st2.field_id}"
    led.row("J-HOLD", hold)

    def redirect():
        fake.host_at(300)
        r0 = _w(_to_world(g, fake), "rejoin.redirects", 0)
        fake._world_mapjump(2856)                             # a world script's own Field(2856) before the rejoin arms
        st = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=8.0, what="the world script's field")
        return st.field_id == 300 and _w(st, "rejoin.redirects", 0) == r0 + 1, f"field {st.field_id}"
    led.row("J-REDIR", redirect)

    def unreg():
        fake.host_at(30999)
        _to_world(g, fake)
        st = g.wait_for(lambda s: s.session_overlay == "peer_no_field", timeout=4.0, what="peer_no_field")
        g.wait_frames(150)
        st = g.state
        ok = (st.session_overlay_detail == 30999 and st.ui_state == "WorldHUD"
              and st.session_overlay_text == BW.overlay_words(BW.OVL_PEER_NO_FIELD, 30999))
        return ok, f"overlay {st.session_overlay!r} {st.session_overlay_detail}, why {_w(st, 'rejoin.why')!r}"
    led.row("W-UNREG", unreg)

    def stale():
        g.warp(300)
        fake.host_at(300, fresh=False)                         # the host's state lane goes stale (its position lane lives)
        _to_world(g, fake)
        g.wait_frames(150)
        st = g.state
        ok = st.ui_state == "WorldHUD" and _w(st, "rejoin.why") == "no fresh host snapshot on the wire"
        fake.host_at(fresh=True)
        st2 = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=8.0, what="the rejoin once fresh")
        return ok and st2.field_id == 300, f"ui {st.ui_state}, why {_w(st, 'rejoin.why')!r}"
    led.row("J-STALE", stale)

    def f11():
        g.warp(300)
        fake.host_at(300)
        st0 = _to_world(g, fake, from_field=True)              # the hold on 300 ...
        r0 = _w(st0, "rejoin.rearms", 0)
        fake.teleport_to_host()                                # ... F11 clears it at once
        st = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=6.0, what="the F11 rejoin")
        ok = st0.follow_hold == 300 and st.field_id == 300 and _w(st, "rejoin.rearms", 0) == r0 + 1
        return ok, f"hold {st0.follow_hold}, field {st.field_id}, rearms {r0}->{_w(st, 'rejoin.rearms')}"
    led.row("J-F11", f11)

    def w_field():
        g.warp(300)
        fake.host_at(300, flags=BW.HF_ON_FIELD | BW.HF_CONTROL)
        g.wait_for(lambda s: s.session_overlay == "off", timeout=4.0, what="paired on 300")
        fake.host_at(0, flags=BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL)   # the host walks out to the world map
        st = g.wait_for(lambda s: s.session_overlay == "host_world", timeout=4.0, what="the waiting line on the field")
        return (st.ui_state == "FieldHUD" and st.session_overlay_text == BW.WAIT_TEXT_HOST_WORLD
                and st.follow_host_world is True), f"overlay {st.session_overlay!r}"
    led.row("W-FIELD", w_field)

    def w_world():
        _to_world(g, fake, from_field=True)
        g.wait_frames(4)
        st = g.state
        ok = (st.session_overlay == "host_world" and st.world_waitline_line == "host_world" and st.follow_hold == -1
              and BW.log_world_hold_released(300, False) in _log(fake))
        return ok, f"overlay {st.session_overlay!r}, hold {st.follow_hold}"
    led.row("W-WORLD", w_world)

    def away():
        g.warp(300)
        fake.host_at(300, flags=BW.HF_ON_FIELD | BW.HF_CONTROL)   # paired first: no waiting line of its own to keep (wire-2)
        g.wait_for(lambda s: s.session_overlay == "off", timeout=4.0, what="paired on 300")
        fake.host_at(0, flags=-1)                             # an OLD host (no section 7) off-field
        g.wait_frames(60)
        early = g.state.session_overlay
        st = g.wait_for(lambda s: s.session_overlay == "host_away", timeout=8.0, what="the old host's fallback")
        ok = (early == "waiting" and st.world_waitline_fallback is True and (st.world_waitline_away_ms or 0) >= BW.WAIT_AWAY_MS
              and st.session_overlay_text == BW.WAIT_TEXT_HOST_AWAY)
        return ok, f"early {early!r}, fallback {st.world_waitline_fallback}, away_ms {st.world_waitline_away_ms}"
    led.row("W-AWAY", away)

    def latch():
        """rejoin-stale-warpedto: a FIELD follow to 300 still in its fade when the guest's own exit script reaches WMAPJUMP:
        its stamp must not survive onto the world map -- the host on 300, the world rejoin arms into 300."""
        g.warp(250)
        fake.host_at(300, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True, entrance=11)
        fake.field_follow_stamp(300)                           # StartFollowWarp's first half: in its fade, stamped
        _to_world(g, fake, from_field=True)                    # ... the exit script's WMAPJUMP wins
        st = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=8.0, what="the rejoin into 300")
        return st.field_id == 300, f"field {st.field_id}, warped_to {st.follow_warped_to}"
    led.row("J-LATCH", latch)

    def seed():
        """rejoin-fieldentrance-stale-landing: the lane goes stale between the arm and its landing (the apply skips) -- the
        guest still arrives through the HOST's entrance (11), seeded from the arm's own fresh snapshot, never the world's
        region key (35)."""
        g.warp(300)                                            # co-located first: any follow latch of an earlier row lands
        fake.host_at(300, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True, entrance=11)
        g.wait_frames(4)
        g.warp(250)
        fake.coop_stale_after_arm = True
        f0 = fake.frame
        fake.enter_world(9011, 100.0, 100.0, entrance=35)
        st = g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.frame > f0, timeout=8.0, what="the stale landing")
        fake.host_at(fresh=True)
        return st.field_id == 300 and st.field_entrance == 11, f"field {st.field_id}, entrance {st.field_entrance}"
    led.row("J-SEED", seed)

    def passent():
        """pairing-passthrough-entrance: a world script's own Field(2856) that PASSES (the host on the world map) keeps the
        entrance it wrote (9993) over the landing's host snapshot (the host's 11 -- another field's)."""
        g.warp(250)
        fake.host_at(0, flags=BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL, fresh=True, entrance=11)
        _to_world(g, fake)
        fake.story_bytes[2:4] = bytes((9993 & 0xFF, 9993 >> 8))   # the world script's SET Global.Int16[2] = 9993
        fake._world_mapjump(2856)
        st = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=8.0, what="the passed field")
        return st.field_id == 2856 and st.field_entrance == 9993, f"field {st.field_id}, entrance {st.field_entrance}"
    led.row("J-PASSENT", passent)

    def unfollowed():
        """rejoin-redirect-after-unfollow: an UNFOLLOWED guest still mirroring (its exit ramp pending) is no following guest
        -- a world script's Field(2856) passes, never redirected into the host's field 300."""
        g.warp(250)
        fake.host_at(300, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True, entrance=11)
        fake.unfollow_ramp()                                   # (before the world: the ramp pending refuses the world arm)
        st0 = _to_world(g, fake)
        mirroring = st0.netsync["session"]["mirroring"] is True     # the premise: SpectatorField still holds, by the mirror
        r0 = _w(st0, "rejoin.redirects", 0)
        fake._world_mapjump(2856)
        st = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=8.0, what="the world script's field")
        return (mirroring and st.field_id == 2856 and _w(st, "rejoin.redirects", 0) == r0,
                f"mirroring {mirroring}; field {st.field_id}, redirects {r0}->{_w(st, 'rejoin.redirects')}")
    led.row("J-UNFOLLOW", unfollowed)

    def quick():
        """rfreeze-1 [review 2]: a RELEASED guest (the ~ menu) presses Confirm on the area-52 quicksand. Its dispatcher's battle
        check polls Confirm with no usercontrol term, so the release's Confirm reaches Battle(0, 144); the spectator's skip
        continues the script INLINE into the location poll. The skip must CONSUME the press: the guest stays on WorldHUD with
        control ON and its own FieldEntrance (35) -- `battles` +1 beside it -- never the location prologue's strand (DisableMove,
        FieldEntrance 9999; area 52 is the switch's default: no field, so a 'no MAPJUMP' witness could not fail)."""
        g.warp(250)
        fake.follow_session(250, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, entrance=11)   # a fresh session (the last row's ramp gone)
        fake.host_at(0, flags=BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL)              # the host on the world map: nothing to rejoin
        g.wait_frames(4)
        f0 = fake.frame
        fake.enter_world(9011, 100.0, 100.0, entrance=35)
        g.wait_for(lambda s: s.on_world and s.world_id == 9011 and s.frame > f0 + 2, timeout=6.0, what="the world map")
        why = fake.release_world_freeze()
        if why is not None:
            return False, f"the ~ menu's release refused: {why}"
        b0 = _w(g.state, "freeze.battles", 0)
        fake.world_area = 52
        try:
            g.send("press confirm")
            g.wait_frames(10)
            st = g.state
        finally:
            fake.world_area = 0
        ok = (st.ui_state == "WorldHUD" and st.control is True and st.field_entrance == 35
              and _w(st, "freeze.battles", 0) == b0 + 1)
        return ok, (f"ui {st.ui_state}, control {st.control}, entrance {st.field_entrance}, battles {b0}->"
                    f"{_w(st, 'freeze.battles')}")
    led.row("J-QUICK", quick)

    def heldpass():
        """rrejoin-1 [review 2]: decision 4 binds EVERY rejoin into the field the guest just left. The guest leaves 300 on its own
        (the hold), the host stays there; a world script's own Field(2856) inside the hold (an event world's ending) PASSES --
        never rewritten back into 300 -- the hold rides that landing, and the FIELD follow on 2856 (the stand-in's opt-in) waits
        it out past FollowStableMs; the host leaving 300 ends it and the follow resumes (301). Witnesses: the field id at each
        step, beside the engine's `follow.hold` / `rejoin.redirects`."""
        g.warp(300)
        fake.follow_session(300, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, entrance=11)
        g.wait_frames(4)                                           # the stand-in reads the new host (b6 off) first
        fake.coop_field_follow = True
        try:
            _to_world(g, fake, from_field=True)                    # the hold on 300; the host stays there
            r0 = _w(g.state, "rejoin.redirects", 0)
            fake._world_mapjump(2856)                             # the world script's own Field(2856), inside the hold
            st = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=8.0, what="the world script's field")
            landed = st.field_id
            g.wait_frames(int(2.0 * fake._render_fps))             # 2 s of game time: past FollowStableMs, inside the 15 s hold
            st2 = g.state
            fake.host_at(301)                                      # the host leaves 300: the hold ends, the follow resumes
            st3 = g.wait_for(lambda s: s.ui_state == "FieldHUD" and s.field_id != st2.field_id, timeout=8.0,
                             what="the field follow once the host leaves")
        finally:
            fake.coop_field_follow = False
        ok = (landed == 2856 and st2.field_id == 2856 and st2.follow_hold == 300 and _w(st2, "rejoin.redirects", 0) == r0
              and st3.field_id == 301)
        return ok, (f"landed {landed}, after 2 s {st2.field_id} (hold {st2.follow_hold}, redirects {r0}->"
                    f"{_w(st2, 'rejoin.redirects')}), then {st3.field_id}")
    led.row("J-HELDPASS", heldpass)
    return led.rows


def _bench(root, faults=(), caps=None) -> dict:
    rows = {}
    for leg, fn in (("solo", _solo), ("client", _client)):
        game = _game(root / leg)
        fake = _fake(game, faults, caps)
        with _session(game, fake) as g:
            rows.update(fn(g, fake))
    return rows


ROWS = ("F0-HOLD", "F1-WALK", "F1-KEYS", "F2-CONFIRM", "F2V-VEHICLE", "F3-MAP", "F6-EDGE", "F4-LEVER", "F5-CONTROL",
        "WB-START", "WB-SWIRL", "WB-RETURN", "R-RELEASE", "J-ARM", "J-OVL", "J-LAND", "J-HOLD", "J-REDIR", "W-UNREG", "J-STALE",
        "J-F11", "W-FIELD", "W-WORLD", "W-AWAY", "J-LATCH", "J-SEED", "J-PASSENT", "J-UNFOLLOW", "J-QUICK", "J-HELDPASS")
#: each fault lever's reds -- EXACTLY these rows, and why
WORLD_FAULT_REDS = {
    "dispatch_ungated": ("F1-WALK", "F6-EDGE"),        # the walker walks while the keys say frozen (the x / z witness)
    "keys_unmasked": ("F2-CONFIRM", "F2V-VEHICLE"),    # `keys` never counts (and aboard, Cancel dismounts)
    "keys_counted_s143": ("F2V-VEHICLE",),             # counted, but F1's mask: Cancel dismounts (F2's Confirm cannot see it)
    "fullmap_open": ("F3-MAP",),                       # `map` never counts (the bench's second Select closes the map it opened)
    "lever_ignored": ("F4-LEVER",),                    # `off` true, the walker still held
    "lever_stuck": ("R-RELEASE",),                     # the release leaves the lever
    "bench0_stuck": ("F5-CONTROL",),                   # the control row: `bench 0` still held
    "edge_once": ("F6-EDGE",),                         # the second world visit counts no edge
    # no hold: the client walks straight back in (J-HOLD), F11 finds none to clear (J-F11), b6 ends none (W-WORLD's line)
    "hold_unlatched": ("F0-HOLD", "J-HOLD", "J-F11", "W-WORLD", "J-HELDPASS"),   # [review 2] no hold: the Field() redirected
    "battle_nextmode": ("WB-START", "WB-RETURN"),      # the world strands in nextMode 2 (the swirl's latch still reads busy)
    "battle_field_return": ("WB-RETURN",),             # back on the field, not the world map
    "rejoin_field_recipe": ("J-LAND", "J-HOLD", "J-STALE", "J-F11", "J-LATCH", "J-SEED"),   # armed (J-ARM, J-OVL), never lands
    "rejoin_departed": ("J-HOLD", "J-STALE", "J-F11"),  # the host on the field the guest LEFT reads "arrived": never armed
    "rejoin_no_snapshot": ("J-STALE",),                # a stale lane arms and lands with no story
    "rejoin_no_hold": ("J-HOLD",),                     # pulled straight back into the field it left
    "line_s143": ("J-OVL", "J-HOLD", "W-UNREG", "W-WORLD"),     # a world guest sees nothing
    "tail_s143": ("W-FIELD", "W-AWAY"),                # the field keeps s143's bare 'waiting'
    "redirect_bounce": ("J-REDIR", "J-PASSENT", "J-UNFOLLOW", "J-HELDPASS"),   # bounced to fldMapNo: a pass too lands on the field it LEFT
    "counters_dark": ("F1-KEYS", "F6-EDGE"),           # held, but `skips` / `edges` never move (the engine's claim lies)
    "arm_uncounted": ("J-ARM",),                       # armed and landed, `arms` / `last` never stamped
    "latch_free": ("WB-SWIRL",),                       # the swirl's latch reads free (mode 2 / attr 0x1000 hold it in the engine)
    "stale_warpedto": ("J-LATCH",),                    # a field follow's stamp survives onto the world map: the rejoin never arms
    "redirect_unfollowed": ("J-UNFOLLOW",),            # an unfollowed guest is redirected into the host's field
    "entrance_unseeded": ("J-SEED",),                  # a stale landing carries the world's own region key
    "pass_entrance_host": ("J-PASSENT",),              # a passed entry lands with the host's entrance (another field's)
    "skip_unconsumed": ("J-QUICK",),                   # [review 2] the location poll re-reads the press: control off, 9999
    "redirect_unheld": ("J-HELDPASS",),                # [review 2] the world script's Field() rewritten back into 300
    "landing_unheld": ("J-HELDPASS",),                 # [review 2] the hold ends at the landing: the field follow chases 300
    # [s144 bench] the follow's world branches absent: a guest on the world map never arms (the overlay still names the
    # host's field -- J-OVL reads the world chain, not the arm), so nothing that needs the rejoin lands
    "rejoin_unarmed": ("J-ARM", "J-LAND", "J-HOLD", "J-STALE", "J-F11", "J-LATCH", "J-SEED"),
}
#: the s143 stand-in (the calibration engine): every row reads red but the control (bench 0 walks and Confirm enters a
#: location on every engine)
OLD_PREDICTED = tuple(r for r in ROWS if r != "F5-CONTROL")
#: the solo leg under the calibration lever (`bench worldfreeze off` pulled before it): the pre-s144 world map at every
#: freeze seam -- the walker walks, nothing counts, the full map opens -- while the hold, the world battle verb, the lever's
#: own row, the control and the release stay green (the client leg never reads the lever: it frees no real guest)
LEVER_PREDICTED = ("F1-KEYS", "F1-WALK", "F2-CONFIRM", "F2V-VEHICLE", "F3-MAP", "F6-EDGE")


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    return _bench(tmp_path_factory.mktemp("clean"))


def test_the_stand_in_bench_is_green_on_s144(clean):
    assert tuple(clean) == ROWS, list(clean)
    assert not [n for n, (ok, _d) in clean.items() if not ok], {n: d for n, (ok, d) in clean.items() if not ok}


@pytest.mark.parametrize("fault", FG.WORLD_FAULTS)
def test_each_world_fault_turns_exactly_its_rows_red(tmp_path, fault):
    rows = _bench(tmp_path, (fault,))
    red = sorted(n for n, (ok, _d) in rows.items() if not ok)
    assert red == sorted(WORLD_FAULT_REDS[fault]), {n: rows[n][1] for n in set(red) ^ set(WORLD_FAULT_REDS[fault])}


def test_the_faults_cover_every_row_and_the_table_is_the_fakes():
    """Every row -- the control included -- is red under at least one fault, every fault reds something, and each fault
    is documented where it lives (fakegame's WORLD_FAULTS block)."""
    assert set(WORLD_FAULT_REDS) == set(FG.WORLD_FAULTS) and len(FG.WORLD_FAULTS) == len(set(FG.WORLD_FAULTS))
    assert all(WORLD_FAULT_REDS[f] for f in FG.WORLD_FAULTS)
    covered = {r for reds in WORLD_FAULT_REDS.values() for r in reds}
    assert covered == set(ROWS), set(ROWS) - covered
    src = (REPO / "tools" / "harness" / "fakegame.py").read_text(encoding="utf-8")
    assert all(f'#:   "{f}"' in src for f in FG.WORLD_FAULTS)


def test_the_s143_stand_in_reads_exactly_old_predicted_red(tmp_path):
    """THE CALIBRATION ENGINE: on the s143 stand-in (the ladder through `leaderguard`) every s144 row reads red -- the keys
    absent, the driver refusing `bench worldfreeze` and `world_battle`, the world guest seeing nothing -- but the control."""
    rows = _bench(tmp_path, caps=FG.caps_through("leaderguard"))
    red = sorted(n for n, (ok, _d) in rows.items() if not ok)
    assert red == sorted(OLD_PREDICTED), {n: rows[n][1] for n in set(red) ^ set(OLD_PREDICTED)}


def test_the_lever_reads_exactly_lever_predicted_red(tmp_path):
    game = _game(tmp_path)
    fake = _fake(game)
    fake._wf_off = True                     # NetSyncField.BenchWorldFreezeOff, pulled before the leg
    with _session(game, fake) as g:
        rows = _solo(g, fake)
    red = sorted(n for n, (ok, _d) in rows.items() if not ok)
    assert red == sorted(LEVER_PREDICTED), {n: rows[n][1] for n in set(red) ^ set(LEVER_PREDICTED)}


def test_the_stand_ins_worldhud_runs_the_stock_select_cycle(tmp_path):
    """[s144 bench] the in-game probe (2026-10-21): after a New Game's walk out the world HUD is HUDNoMiniMap (no minimap on
    screen: WorldHUD.Show by w_naviMode 0), and WorldHUD.OnKeySelect cycles HUD -> FullMap -> HUDNoMiniMap -> HUD with the
    s144 refusal on the HUD -> FullMap step ALONE. Frozen: select 1 turns the minimap on (`map` 0), selects 2-4 are refused
    (`map` 1, 2, 3; one line), the HUD stays. Unfrozen: select 1 opens the full map (the dispatcher stops), select 2 shuts it
    to HUDNoMiniMap, `map` unmoved. w_naviMode persists across a world load (1 -> HUD); an open full map left for a field
    comes back ForceCloseFullMap'd (HUD, 1), from anything else it stays open (WorldHUD.Show reads its persisted state
    first); a saved 2 alone reloads as 0 (#697); a New Game zeroes it; the arrival title's dead map button takes no step and
    asks no refusal (the close needs no button)."""
    f = _fake(_game(tmp_path))
    f.ui_state = "Title"
    f._execute(["newgame"])
    f.story_mirroring = True                                     # SpectatorField (the mirror): frozen on the world map
    f.enter_world(9011, 100.0, 100.0)
    assert f.world_hud_state == "HUDNoMiniMap" and f._world_frozen()
    seq = []
    for _ in range(4):
        f._world_key("select")
        seq.append((f.world_hud_state, f._wf_n["map"]))
    assert seq == [("HUD", 0), ("HUD", 1), ("HUD", 2), ("HUD", 3)], seq
    assert _log(f).count(BW.decline_line(BW.WORLD_UI_DECLINE_MAP, "world map 9011")) == 1
    f.story_mirroring = False                                    # unfrozen (the lever's world map, or no co-op at all)
    f._world_key("select")
    assert f.world_full_map and f.world_navi == 2 and f._wf_n["map"] == 3
    f._world_key("cancel")                                       # stock: Cancel never closes the full map
    assert f.world_full_map
    f._world_key("select")
    assert f.world_hud_state == "HUDNoMiniMap" and f.world_navi == 0 and f._wf_n["map"] == 3
    f._world_key("select")                                       # the minimap back on: HUD, saved as 1 ...
    f.enter_world(9011, 100.0, 100.0)
    assert f.world_hud_state == "HUD"                            # ... and a world load lands there
    f._world_key("select")
    assert f.world_full_map
    f.ui_state, f.field_id = "FieldHUD", 6603                    # left the world with the full map OPEN, then back from a
    f.enter_world(9011, 100.0, 100.0)                            # field: WorldHUD.Show's persisted FullMap is ForceCloseFullMap'd
    assert f.world_hud_state == "HUD" and f.world_navi == 1      # -- HUD, w_naviMode 1 (WorldHUD.cs 32-37, 528-536)
    f._world_key("select")                                       # open again, then a world load from anything but a field:
    assert f.world_full_map                                      # Show's other branch keeps it open
    f._world_load("BattleHUD")
    assert f.world_full_map and f.world_navi == 2
    f._world_key("select")
    assert f.world_hud_state == "HUDNoMiniMap" and f.world_navi == 0
    f.world_navi = 2                                             # a save made with the map open, loaded cold: the HUD state
    f.ui_state, f.field_id = "FieldHUD", 6603                    # not FullMap, w_naviMode 2 -> #697 reads it as 0
    f.enter_world(9011, 100.0, 100.0)
    assert f.world_hud_state == "HUDNoMiniMap" and f.world_navi == 0
    f.world_title_ticks = 50                                     # the arrival title (a story scene pointer's): the map button dead
    f.story_mirroring = True
    f.world_navi = 1
    f.enter_world(9011, 100.0, 100.0)
    f._world_key("select")
    assert f.world_hud_state == "HUD" and f._wf_n["map"] == 3    # no step, no refusal asked
    f._wt["counter"] = 50                                        # the title closed
    f._world_key("select")
    assert f.world_hud_state == "HUD" and f._wf_n["map"] == 4    # refused
    f.ui_state = "Title"
    f._execute(["newgame"])
    assert f.world_navi == 0                                     # gEventGlobal[100] zeroed


# ------------------------------------------------------------------------------------------------ the driver
def test_world_battle_refuses_a_field_and_an_s143_engine_before_the_step(tmp_path):
    game = _game(tmp_path / "old")
    old = _fake(game, caps=FG.caps_through("leaderguard"))
    with _session(game, old) as g:
        g.newgame(settle=0)
        with pytest.raises(HarnessError, match="start_battle"):
            g.world_battle(67)
        old.enter_world(9011)
        g.wait_world(timeout=5)
        n = len(old.executed)
        with pytest.raises(HarnessError, match=r"no `world\.next_mode` .*\(memoria-patch s144\)"):
            g.world_battle(67)
        assert len(old.executed) == n                                  # Not sent
        with pytest.raises(HarnessError, match="battle: field only"):  # what that engine would answer
            g.send("battle 67 0")
        with pytest.raises(HarnessError, match="world_battle"):
            g.start_battle(67)


@pytest.mark.parametrize("setup,why", [
    (lambda f: f.world.update(vehicle=6), "world battle: on foot only (travel mode 6)"),
    (lambda f: setattr(f, "world_topo", 52), "world battle: the walker stands on topograph 52 (no battles there)"),
    (lambda f: setattr(f, "battle_map_names", {1}), "world battle: scene 67 is not registered (Battle.mapName)"),
    (lambda f: setattr(f, "control", False), "world battle: no user control (a world script holds it)"),
    (lambda f: setattr(f, "world_bee", True), "world battle: the bee scene has no battles"),
    (lambda f: setattr(f, "world_battle_boot_refusal", "scene 67 has no pattern 0"), "world battle: scene 67 has no pattern 0"),
])
def test_the_world_battle_verb_refuses_with_the_engines_reason(tmp_path, setup, why):
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        g.newgame(settle=0)
        _to_world(g, fake)
        setup(fake)
        with pytest.raises(HarnessError, match=re.escape(why)):
            g.send("battle 67 0")
        assert g.state.debug_status == why and g.state.ui_state == "WorldHUD"


def test_the_world_battle_one_shot_drops_stale_and_on_the_worlds_own_result(tmp_path):
    """TakePendingWorldBattle consumes the one-shot on the first world tick that reaches it: the world's own result first
    drops it (the status and the line), a second arm before the tick is refused, a fresh arm then fires."""
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        g.newgame(settle=0)
        _to_world(g, fake)
        fake.mode = "frozen"                                 # hold the world ticks while the verb arms
        try:
            fake._world_battle_verb(67, 0, False)
            with pytest.raises(RuntimeError, match=re.escape(BW.world_battle_armed_refusal(67))):
                fake._world_battle_verb(67, 0, False)
            fake.world_tick_result = 4
        finally:
            fake.mode = "normal"
        st = g.wait_for(lambda s: "dropped" in (s.debug_status or ""), timeout=5.0, what="the drop")
        assert st.debug_status == BW.world_battle_dropped(67, BW.world_battle_own_result(4)) and st.ui_state == "WorldHUD"
        assert "[NetSync] " + st.debug_status in _log(fake)
        fake._wt["arm"] = {"scene": 67, "group": 0, "rand": False, "rt": fake.rt - 4.0, "counter": fake._wt["counter"]}
        st = g.wait_for(lambda s: "stale" in (s.debug_status or ""), timeout=5.0, what="the stale drop")
        assert st.debug_status.startswith(BW.world_battle_dropped(67, "stale (armed "))
        st = g.world_battle(67, group=-1)
        assert st.debug_status == BW.world_battle_started(67, -1, False, 9011)


# ------------------------------------------------------------------------------------------------ the keys, the accessors
def _agent_nothing() -> dict:
    catch = net_lines("HarnessAgent.cs", r'outer\.Append\("\\"netsync\\":\{\\"enabled')
    head = net_lines("HarnessAgent.cs", r'NetsyncF3Retired = "')
    tail = net_lines("HarnessAgent.cs", r'\+ "\\"align_win')
    a, b = _LIT.findall(catch[0])
    pinned = "".join(_LIT.findall(head[0]) + _LIT.findall(tail[0]))
    return json.loads("{" + (a + pinned + b).replace('\\"', '"') + "}")["netsync"]


def test_the_follow_accessors_are_the_agents_follow_keys():
    """`netsync.session.follow`'s keys are exactly the follow table's (its own table: NETSYNC_TOP_ACCESSORS' law pins
    `session`'s first level), each reading its sentinel on the live catch line and None on an s143 block."""
    nothing = _agent_nothing()
    follow = nothing["session"]["follow"]
    table = CH.State.NETSYNC_FOLLOW_ACCESSORS
    assert list(table) == list(follow) == list(BW.SESSION_FOLLOW_SENTINELS)
    st = CH.State({"frame": 1, "netsync": nothing})
    assert {k: getattr(st, n) for k, n in table.items()} == follow
    old = CH.State({"frame": 1, "netsync": {"session": {"grace_ms": -1}}})
    assert all(getattr(old, n) is None for n in table.values())
    assert not set(table.values()) & set(CH.State.NETSYNC_TOP_ACCESSORS.values())


def test_the_stand_in_publishes_the_world_keys_on_s144_and_none_on_s143(tmp_path):
    """Top-level `gmode`, `field.entrance` and the world block's live keys (in the agent's order, after `vehicle`) on the s144
    stand-in -- -1 / null off the world map -- and none of them on s143's; `debug_status` the verb's. [ff9mapkit netsync s145]
    The s144 stand-in is the ladder through `worldwait` (s145 appends six witness keys after `next_mode`:
    tests/test_world_diorama_harness.py)."""
    game = _game(tmp_path)
    fake = _fake(game, caps=FG.caps_through("worldwait"))
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        st = g.wait_for(lambda s: s.gmode == 1, timeout=4.0, what="gMode 1")
        assert list(st.raw["world"])[-5:] == ["area", "topo", "move", "phase", "next_mode"]
        assert (st.world_area, st.world_topo, st.world_move, st.world_phase, st.world_next_mode) == (-1, -1, None, -1, -1)
        assert list(st.raw)[list(st.raw).index("sys_mode") + 1] == "gmode" and st.field_entrance == 0
        fake.world_area, fake.world_topo = 7, 31
        fake.enter_world(9011, 100.0, 100.0)
        st = g.wait_for(lambda s: s.gmode == 3 and s.world_phase == 2, timeout=4.0, what="the world map")
        assert (st.world_area, st.world_topo, st.world_move, st.world_next_mode, st.raw["sys_mode"]) == (7, 31, False, 3, 3)
        _st, moved = _hold_up(g, 10)
        assert moved > 2.0
    old_game = _game(tmp_path / "old")
    old = _fake(old_game, caps=FG.caps_through("leaderguard"))
    with _session(old_game, old) as g:
        g.newgame(settle=0)
        old.enter_world(9011)
        st = g.wait_world(timeout=5)
        assert st.gmode is None and st.field_entrance is None and st.world_next_mode is None and st.world_move is None
        assert "gmode" not in st.raw and set(st.raw["world"]) == {"id", "x", "z", "vehicle"}


# ------------------------------------------------------------------------------------------------ section 7's b6 / b7
def _state_frame(flags: int, field: int = 0) -> bytes:
    """A host type-5 frame carrying only section 7 (header + empty open set and ring) -- battlewire's codec twin."""
    return CP.build_frame(CP.TYPE_STATE, BW.append_section(b"", BW.SECTION_DIALOG, BW.dialog_section(0x0144, 7, flags, 0, field)))


def _tape(tmp_path, name, frames) -> pathlib.Path:
    """A minimal .f9tape: ``frames`` = [(t, payload)] host records."""
    head = json.dumps({"tool": "test"}).encode("utf-8")
    body = b"".join(struct.pack("<dBI", t, CP.DIR_HOST, len(p)) + p for t, p in frames)
    path = tmp_path / name
    path.write_bytes(b"F9TAPE01" + struct.pack("<I", len(head)) + head + body)
    return path


def test_coop_peer_where_reads_b6_b7_and_an_old_tape_parses_as_before(tmp_path, capsys):
    """`coop_peer.py where`: an s144 host's tape (on 250, then the world map with b6 + b4 + b1, then the title with b7)
    passes --want world / title; an s143 host's tape (the same walk, no b6 / b7) parses with no bit and passes --want none
    -- and fails --want world (the check can fail); b6 on a frame the lane puts on a real field fails --want world."""
    pos = lambda f: CP.build_pos_frame(f)                                   # noqa: E731
    s144 = [(0.0, pos(250)), (0.1, _state_frame(BW.HF_ON_FIELD | BW.HF_CONTROL, 250)), (1.0, pos(0)),
            (1.1, _state_frame(BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL)), (2.0, _state_frame(BW.HF_TITLE))]
    s143 = [(0.0, pos(250)), (0.1, _state_frame(BW.HF_ON_FIELD | BW.HF_CONTROL, 250)), (1.0, pos(0)),
            (1.1, _state_frame(BW.HF_MENU | BW.HF_CONTROL)), (2.0, _state_frame(0))]          # the same walk, no b6 / b7
    new, old = _tape(tmp_path, "new.f9tape", s144), _tape(tmp_path, "old.f9tape", s143)
    d = CP.tape_where(CP.read_tape(new)[1])
    assert (d["frames"], d["with7"], d["world"], d["title"], d["world_on_field"], d["off_field"], d["off_field_said"]) == \
        (3, 3, 1, 1, 0, 2, 2) and d["stage"] == "s144" and d["first_world"] == 1.1
    assert CP.main(["where", str(new), "--want", "world"]) == 0 and CP.main(["where", str(new), "--want", "title"]) == 0
    assert CP.main(["where", str(new), "--want", "none"]) == 1
    od = CP.tape_where(CP.read_tape(old)[1])
    assert od["world"] == od["title"] == od["refused"] == od["parity_diff"] == 0 and od["with7"] == 3
    assert od["stage"].startswith("s143")
    assert CP.main(["where", str(old), "--want", "none"]) == 0 and CP.main(["where", str(old), "--want", "world"]) == 1
    bad = _tape(tmp_path, "bad.f9tape", [(0.0, pos(250)), (0.1, _state_frame(BW.HF_WORLD | BW.HF_ON_FIELD, 250))])
    assert CP.main(["where", str(bad), "--want", "world"]) == 1
    out = capsys.readouterr().out
    assert "VERDICT (--want world): OK" in out and "s143-or-older" in out
    # the dump's state frame names its flags (an old reader's bytes unchanged)
    assert CP.describe_frame(CP.TYPE_STATE, CP.parse_frame(_state_frame(0xC8))[1]).endswith("section 7 flags 0xC8 "
                                                                                             "(on_field,world,title)")


def test_the_stand_ins_old_section_7_reader_ignores_b6_b7(tmp_path):
    """The stand-in's guest reads section 7's bits one by one (scene, on-field, battle, line, menu, control): a host frame
    with b6 / b7 set reads exactly as without -- what every s143 reader does (TryParseHostSection copies the byte)."""
    game = _game(tmp_path)
    reads = []
    for extra in (0, BW.HF_WORLD | BW.HF_TITLE):
        fake = FakeGame(game)
        fake.ui_state, fake.field_id = "FieldHUD", 250
        fake._netsync(["selftest", "1"])
        fake._netsync(["bench", "1"])
        fake._netsync(["lock", "1"])
        fake._netsync(["host", "menu", "1"])
        fake._bench_host_tick()
        fake._bench.state["flags"] |= extra
        fake._guest.observe(fake._bench.state, fake._guest_now())
        fake._step_netsync()
        doc = fake._netsync_doc()
        reads.append({k: doc[k] for k in ("host_menu", "host_battle", "chip", "suppress")})
    assert reads[0] == reads[1], reads


def test_the_release_frees_a_followed_guest_until_the_next_field_load(tmp_path):
    """Decision 8's ~ menu row on the followed client (NetSyncField.ReleaseWorldFreeze): refused off the world map, then on
    the frozen world map it frees the walker (`released`, its line) until the next field load (the re-armed line, frozen
    again); a second release is refused; the guest's own scripted world battle stays skipped while released (the ENCOUNT
    gate keys on SpectatorField alone: `battles`, one line per world map); unfollowing lifts the freeze with its reason and
    [ff9mapkit netsync s145] -- ON THE s144 STAND-IN (the ladder through `worldwait`): s144 ended a release at a world load too;
    s145 keeps it there and ends it at the title (tests/test_world_diorama_harness.py pins that stage) --
    the next scripted battle runs."""
    game = _game(tmp_path)
    fake = _fake(game, caps=FG.caps_through("worldwait"))      # [ff9mapkit netsync s145] the s144 stage
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(250)
        fake.follow_session(30999, flags=BW.HF_ON_FIELD | BW.HF_CONTROL)   # a host field this install lacks: no rejoin
        g.wait_frames(4)
        assert fake.release_world_freeze() == "world map only"
        _to_world(g, fake)
        st, moved = _hold_up(g, 10)
        assert moved < 2.0 and st.world_freeze_on is True and st.world_freeze_why == "live"
        assert fake.release_world_freeze() is None
        st, moved = _hold_up(g, 10)
        assert moved > 2.0 and st.world_freeze_released is True and st.world_freeze_on is False
        assert fake.release_world_freeze() == "already released (until the next field or world load)"
        assert fake.world_script_battle(941) is False and fake.world_script_battle(942, "ENCOUNT2") is False
        st = g.wait_for(lambda s: s.world_freeze_battles == 2, timeout=4.0, what="the skipped battles")
        log = _log(fake)
        assert _L(BW.log_world_freeze_released_s144("~ menu", 9011)) in log      # [ff9mapkit netsync s145] the s144 stage's words
        assert log.count("suppressed (following guest) on world map 9011") >= 1
        assert log.count(BW.decline_line(BW.world_scripted_battle_decline("ENCOUNT", 941), "world map 9011")) == 1
        assert BW.world_scripted_battle_decline("ENCOUNT2", 942) not in log        # one line per class per world map
        # freeze-release-confirm-masked: released, Confirm on a location tile ENTERS it (the host's field is not on this
        # install: decision 6's rule passes the world's own Field(300))
        g.teleport(150.0, 100.0)
        g.send("press confirm")
        st = g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=6.0, what="the released guest's location")
        assert st.field_id == 300 and st.world_freeze_released is False                  # the field load ended the release
        # ...and a WORLD load ends a release too (OnWorldLoadWorldFreeze)
        _to_world(g, fake)
        assert fake.release_world_freeze() is None
        _to_world(g, fake, 9011, 110.0, 100.0)
        assert fake._wf_released is False and _L(BW.LOG_WORLD_FREEZE_REARMED_WORLD) in _log(fake)
        g.warp(250)
        st = g.wait_for(lambda s: s.world_freeze_released is False, timeout=4.0, what="the field load's re-arm")
        assert _L(BW.LOG_WORLD_FREEZE_REARMED) in _log(fake)
        _to_world(g, fake)
        st, moved = _hold_up(g, 10)
        assert moved < 2.0 and st.world_freeze_on is True
        fake.unfollow()
        st, moved = _hold_up(g, 10)
        assert moved > 2.0 and st.world_freeze_on is False
        assert _L(BW.log_world_freeze_lifted(9011, BW.world_freeze_lift_why(False, False, False, False, False))) in _log(fake)
        assert fake.world_script_battle(941) is True
        g.wait_for(lambda s: s.ui_state == "BattleHUD", timeout=4.0, what="the scripted battle")


# ------------------------------------------------------------------------------------------------ every twin can fail
_O = {name: getattr(BW, name) for name in (
    "world_freeze_rule", "world_freeze_why_term", "world_freeze_lift_why", "world_freeze_edge_step", "control_on_script_keys",
    "world_freeze_release_refusal", "world_freeze_bench_refusal", "on_world_rule", "follow_field_for", "world_arm_refusal",
    "world_hold_step", "world_redirect_step", "world_latch_step", "world_arm_timed_out", "ramp_world_settled",
    "host_where_bits", "host_where_read", "wait_away_condition", "wait_away_due", "wait_line_tail", "world_guest_overlay",
    "world_guest_detail", "wait_line_text", "wait_line_name", "released_world_script_keys", "world_follow_latch",
    "host_entrance_of", "pass_keeps_own_entrance", "pass_entrance_restores", "wait_keep_window", "field_wait_sticky",
    "field_wait_tail", "host_flag_reads", "flag_reads_blind")}
#: one mutant per twin the three s144 selftests pin (each a one-line drift of battlewire's twin), and the selftest whose
#: ENGINE rows -- evaluated against the twins, tests/test_world_coop.py's FREEZE_ROWS / REJOIN_ROWS / OVL_ROWS -- must go red
TWIN_MUTANTS = [
    ("freeze", "world_freeze_rule", lambda s, b, t, r, e: bool(s and not r and not (b and t))),               # no bee term
    ("freeze", "world_freeze_why_term", lambda live, mir, bench: "bench" if bench else _O["world_freeze_why_term"](live, mir, bench)),
    ("freeze", "world_freeze_lift_why", lambda s, b, t, r, e: None if r else _O["world_freeze_lift_why"](s, b, t, r, e)),
    ("freeze", "world_freeze_edge_step", lambda held, last, counter: not held),                               # no counter-back
    ("freeze", "control_on_script_keys", lambda k, f: int(k) & ~(BW.EV_CONFIRM | BW.EV_SPECIAL | BW.EV_SELECT) & 0xFFFFFFFF),
    ("freeze", "world_freeze_release_refusal", lambda live, on, fr, rel: _O["world_freeze_release_refusal"](live, True, fr, rel)),
    ("freeze", "world_freeze_bench_refusal", lambda role: None),
    ("rejoin", "on_world_rule", lambda g, s: g == 3),
    ("rejoin", "follow_field_for", lambda w, f: int(f)),
    ("rejoin", "world_arm_refusal", lambda h, m, f, r, s, g, e, c, fm, hd, l: _O["world_arm_refusal"](h, m, f, r, s, g, e, True, fm, hd, l)),
    ("rejoin", "world_hold_step", lambda h, ms, host, w, d: _O["world_hold_step"](h, ms - 1, host, w, d)),     # `>` for `>=`
    ("rejoin", "world_redirect_step", lambda d, df, h, reg, snap, fol: _O["world_redirect_step"](d, df, h, reg, True, fol)),
    ("rejoin", "world_latch_step", lambda w, m, a, x, f, b, r, j: _O["world_latch_step"](w, m, a, x, f, b, r, False)),
    ("rejoin", "world_arm_timed_out", lambda a, ms, w: a >= 0 and bool(w) and ms >= BW.WORLD_ARM_TIMEOUT_MS),
    ("rejoin", "ramp_world_settled", lambda e, c: True),
    ("overlay", "host_where_bits", lambda w, t: (BW.HF_TITLE if w else 0) | (BW.HF_WORLD if t else 0)),
    ("overlay", "host_where_read", lambda fl, bit: bool(fl & bit)),
    ("overlay", "wait_away_condition", lambda v, f, fl, b: bool(v and not b and f in (0, 65535))),
    ("overlay", "wait_away_due", lambda c, a, ms: bool(c)),
    ("overlay", "wait_line_tail", lambda w, t, aw, o: BW.OVL_HOST_TITLE if t else _O["wait_line_tail"](w, t, aw, o)),
    ("overlay", "world_guest_overlay", lambda pl, a, h, r, hd, b, w, t, aw, kp, cur: _O["world_guest_overlay"](pl, a, h, r, -1, b, w, t, aw, kp, cur)),
    ("overlay", "world_guest_detail", lambda s, a, h: h if s == BW.OVL_REJOINING else _O["world_guest_detail"](s, a, h)),
    ("overlay", "wait_line_text", lambda s, d=0: (_O["wait_line_text"](s, d) or "").split("\n")[0] or None),
    ("overlay", "wait_line_name", lambda s: "rejoining" if s == BW.OVL_REJOINING else _O["wait_line_name"](s)),
    ("freeze", "released_world_script_keys", lambda k: int(k) & ~(BW.EV_CONFIRM | BW.EV_SPECIAL | BW.EV_SELECT) & 0xFFFFFFFF),  # F1's
    ("rejoin", "world_follow_latch", lambda w, a, l: int(l)),                                                  # s143's guard
    ("rejoin", "host_entrance_of", lambda state: 9999),                                                        # the forced seed
    ("rejoin", "pass_keeps_own_entrance", lambda code: code != BW.REDIR_TO_HOST),                               # PassHost too
    ("rejoin", "pass_entrance_restores", lambda s, f: s > 0),                                                   # any field
    ("overlay", "wait_keep_window", lambda v, f, fl, b: bool(v and f in (0, 65535))),                          # b3 kept
    ("overlay", "field_wait_sticky", lambda s: s in (BW.OVL_HOST_WORLD, BW.OVL_HOST_TITLE, BW.OVL_HOST_AWAY, BW.OVL_WAITING)),
    ("overlay", "field_wait_tail", lambda w, t, aw, kp, cur: _O["wait_line_tail"](w, t, aw, BW.OVL_WAITING)),   # never keeps
    ("overlay", "host_flag_reads", lambda f: _O["host_flag_reads"](f) | (BW.HR_MENU if int(f) & BW.HF_WORLD else 0)),   # b6 read
    ("overlay", "flag_reads_blind", lambda rule=None: True),
]


def _engine_rows(kind: str) -> dict:
    from . import test_world_coop as WC
    return {"freeze": WC.FREEZE_ROWS, "rejoin": WC.REJOIN_ROWS, "overlay": WC.OVL_ROWS}[kind]


@pytest.mark.parametrize("kind,name,mutant", TWIN_MUTANTS, ids=[m[1] for m in TWIN_MUTANTS])
def test_each_twin_mutant_turns_an_engine_row_red(monkeypatch, kind, name, mutant):
    """EVERY CHECK CAN FAIL: with one twin drifted (in memory), at least one of the engine's own selftest rows evaluated
    against the twins reads red -- and with the twins as shipped, none does."""
    rows = _engine_rows(kind)
    assert all(check() is True for check in rows.values())
    monkeypatch.setattr(BW, name, mutant)
    red = []
    for row, check in rows.items():
        try:
            if check() is not True:
                red.append(row)
        except Exception:                            # noqa: BLE001 -- a drifted twin that throws reads red too
            red.append(row)
    assert red, f"{name}: no {kind} row read the mutant"


def test_every_pure_twin_has_a_mutant():
    assert {m[1] for m in TWIN_MUTANTS} == set(_O)
