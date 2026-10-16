"""``tools/harness/coop_peer.py`` -- the solo two-role bench peer (battle co-op R3, sitting-A fix round, tool T2).

What these pin, and what they cannot: the tool's WIRE (NetSyncWire v14 frames built and accepted exactly as the engine
builds and accepts them -- a byte fixture laid out from NetSyncSocket.cs, and the constants read off the live patch
stack), its WebSocket framing (round-trips, and interop with tools/netsync-bridge/test_relay_roundtrip.py's own
helpers), the TAPE (write/read, a torn tail, the battle anchors), the REPLAY's timing and blackhole under a fake clock,
the fake guest's decisions, and the local RELAY's pairing -- end to end over loopback sockets, the production bridge
in the loop once. They say nothing about the ENGINE's reaction to any of it: that is the calibration replay's job
(R3-SITTING-A-FIXES.md T2: the five guest lines before the instrument judges anything).

Every socket is loopback on an ephemeral port, every wait has a timeout, every thread is a daemon (the suite runs
under ``-n 6``).
"""
from __future__ import annotations

import importlib.util
import io
import pathlib
import re
import socket
import struct
import sys
import threading
import time

import pytest

from ff9mapkit import netsync_bridge as NB

from ._patchstack import net_lines

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                               # noqa: E402
from harness import coop_peer as CP                                # noqa: E402

CLONE_NETSYNC = pathlib.Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Netsync")
TIMEOUT = 5.0


def _roundtrip_helpers():
    """tools/netsync-bridge/test_relay_roundtrip.py (a hyphenated dir, not a package): its ws_client_connect /
    send_binary / recv_frame -- the framing the existing bridge test speaks -- as an independent oracle."""
    path = REPO / "tools" / "netsync-bridge" / "test_relay_roundtrip.py"
    spec = importlib.util.spec_from_file_location("_coop_peer_relay_roundtrip", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _log():
    buf = io.StringIO()
    return CP.Log(stream=buf), buf


def _wait_for(pred, timeout=TIMEOUT, every=0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(every)
    return pred()


# ======================================================================================== the wire (v14)
# NetSyncWire.BuildFrame(TypePos, BuildPosPayload(250, 0x0102, 0x0304, 0x0506, 3, (1.5, -2, 3), (0, 0, 0.5, 1))),
# laid out by hand from NetSyncSocket.cs: [F9][0E][type][len lo][len hi], then BinaryWriter's LE writes in order --
# (UInt16)field, anim, model, meshVis, loco (byte), pos.x/y/z, rot.x/y/z/w (Single).
POS_FIXTURE = bytes.fromhex(
    "F9 0E 00 25 00"          # magic 0xF9, version 14, type 0 (pos), len 37 LE
    "FA 00"                   # field 250
    "02 01"                   # anim 0x0102
    "04 03"                   # model 0x0304
    "06 05"                   # meshVis 0x0506
    "03"                      # loco 3 (run)
    "00 00 C0 3F"             # pos.x  1.5
    "00 00 00 C0"             # pos.y -2.0
    "00 00 40 40"             # pos.z  3.0
    "00 00 00 00"             # rot.x  0
    "00 00 00 00"             # rot.y  0
    "00 00 00 3F"             # rot.z  0.5
    "00 00 80 3F"             # rot.w  1.0
)
# A type-1 head as SampleOwnBattle writes it: seq u16, mapNo u16, guestSlots, patNum, startType, flags, nonce,
# songId u16 (v10), unitCount -- then (none here) the unit records.
BATTLE_FIXTURE = bytes.fromhex("F9 0E 01 0C 00" "02 01" "9C 01" "02" "01" "00" "0B" "07" "FF FF" "00")
# The s114 control frame [0][menu 2 root][fmt 1][nonce 7][boot 2 LIVE].
CONTROL_FIXTURE = bytes.fromhex("F9 0E 03 05 00" "00 02 01 07 02")


def test_pos_frame_matches_the_engine_byte_layout():
    built = CP.build_pos_frame(250, anim=0x0102, model=0x0304, mesh_vis=0x0506, loco=3, pos=(1.5, -2.0, 3.0),
                               rot=(0.0, 0.0, 0.5, 1.0))
    assert built == POS_FIXTURE
    assert len(built) == CP.HEADER_SIZE + CP.POS_LEN == 42
    wtype, payload = CP.parse_frame(built)
    assert wtype == CP.TYPE_POS
    p = CP.parse_pos_payload(payload)
    assert (p["field"], p["anim"], p["model"], p["mesh_vis"], p["loco"]) == (250, 0x0102, 0x0304, 0x0506, 3)
    assert p["pos"] == (1.5, -2.0, 3.0) and p["rot"] == (0.0, 0.0, 0.5, 1.0)


def test_pos_field_truncates_like_the_csharp_cast():
    # (UInt16)field: the int is truncated, never range-checked
    assert CP.parse_pos_payload(CP.build_pos_payload(0x1_00FA))["field"] == 250
    assert CP.parse_pos_payload(CP.build_pos_payload(CP.FIELD_SENTINEL))["field"] == 65535


def test_battle_head_and_control_frame_fixtures():
    wtype, payload = CP.parse_frame(BATTLE_FIXTURE)
    assert wtype == CP.TYPE_BATTLE
    assert CP.parse_battle_head(payload) == {"seq": 0x0102, "map": 412, "guest_slots": 2, "pattern": 1,
                                             "start_type": 0, "flags": 0x0B, "nonce": 7, "song": 0xFFFF, "units": 0}
    assert CP.parse_battle_head(payload[:-1]) is None
    # the control frame is battlewire's codec (pinned to NetSyncBattle by test_harness_netsync), framed v14
    assert CP.build_frame(CP.TYPE_CONTROL, BW.encode_control(BW.CTL_ROOT, 7, BW.BOOT_LIVE)) == CONTROL_FIXTURE
    c = CP.decode_control_raw(CP.parse_frame(CONTROL_FIXTURE)[1])
    assert c == {"menu": 2, "fmt": 1, "trailer": True, "nonce": 7, "boot": BW.BOOT_LIVE}
    assert CP.control_text(c) == "menu 2 (root) | fmt-1 report: nonce 7 boot LIVE"
    legacy = CP.decode_control_raw(BW.encode_control(True))
    assert legacy["trailer"] is False and CP.control_text(legacy).endswith("no trailer (a pre-R3 guest's 2-byte frame)")
    assert CP.decode_control_raw(b"\x01\x02") is None and CP.decode_control_raw(b"\x00") is None


@pytest.mark.parametrize("message", [
    bytes([0xF9, 13, 0, 0, 0]),                        # a v13 peer: the version byte rejects it
    bytes([0xF8, 14, 0, 0, 0]),                        # not our magic
    CP.build_frame(0, b"\x00" * 4)[:-1],               # header length != the message's rest
    CP.build_frame(0, b"\x00" * 4) + b"\x00",          # ...either way
    bytes([0xF9, 14, 0, 0x01, 0x20]) + bytes(8193),    # len 8193 > MaxPayload
    b"\xF9\x0E\x00",                                   # shorter than the header
], ids=["v13", "magic", "short-body", "long-body", "over-max-payload", "short-header"])
def test_parse_frame_refuses_what_the_engine_drops(message):
    assert CP.parse_frame(message) is None


def test_build_frame_holds_an_empty_and_a_maximal_payload():
    assert CP.build_frame(CP.TYPE_STATE) == bytes([0xF9, 14, 5, 0, 0])
    big = bytes(range(256)) * 32                        # 8192 = MaxPayload
    assert CP.parse_frame(CP.build_frame(CP.TYPE_STATE, big)) == (CP.TYPE_STATE, big)
    with pytest.raises(ValueError):
        CP.build_frame(CP.TYPE_STATE, bytes(0x10000))


def test_wire_constants_match_the_live_patch_stack():
    """NetSyncWire's constants, read off memoria-patches/ (no clone needed): a wire bump turns this red."""
    def const(pattern):
        lines = net_lines("NetSyncSocket.cs", pattern)
        assert len(lines) == 1, (pattern, lines)
        return int(re.search(r"=\s*(0x[0-9A-Fa-f]+|\d+)", lines[0]).group(1), 0)
    assert const(r"public const Byte Magic = ") == CP.WIRE_MAGIC
    assert const(r"public const Byte Version = ") == CP.WIRE_VERSION
    assert const(r"public const Int32 HeaderSize = ") == CP.HEADER_SIZE
    assert const(r"public const Int32 MaxPayload = ") == CP.MAX_PAYLOAD
    types = {}
    for line in net_lines("NetSyncSocket.cs", r"public const Byte Type\w+ = "):
        m = re.search(r"Type(\w+) = (\d+);", line)
        types[m.group(1).lower()] = int(m.group(2))
    assert types == {name: t for t, name in CP.TYPE_NAMES.items()}
    stale = net_lines("NetSyncSocket.cs", r"private const Int32 StaleMs = ")
    assert stale and all(re.search(r"= 2000;", s) for s in stale)
    assert CP.STALE_S == 2.0


def _method_body(text, signature):
    i = text.index(signature)
    j = text.index("\n        }\n", i)
    return text[i:j]


@pytest.mark.skipif(not (CLONE_NETSYNC / "NetSyncSocket.cs").is_file(), reason="no shared Memoria clone")
def test_pos_payload_write_order_matches_the_clone_source():
    """BuildPosPayload's BinaryWriter order (the clone's working tree IS the applied stack)."""
    text = (CLONE_NETSYNC / "NetSyncSocket.cs").read_text(encoding="utf-8").replace("\r\n", "\n")
    body = _method_body(text, "public static Byte[] BuildPosPayload(")
    assert "Int32 field, UInt16 anim, UInt16 model, UInt16 meshVis, Byte loco, Vector3 pos, Quaternion rot" in body
    assert "new Byte[37]" in body and CP.POS_LEN == 37
    assert re.findall(r"bw\.Write\(([^;]+?)\);", body) == [
        "(UInt16)field", "anim", "model", "meshVis", "loco", "pos.x", "pos.y", "pos.z", "rot.x", "rot.y", "rot.z",
        "rot.w"]
    frame = _method_body(text, "public static Byte[] BuildFrame(")
    assert re.findall(r"frame\[(\d)\] = ([^;]+);", frame) == [
        ("0", "Magic"), ("1", "Version"), ("2", "type"), ("3", "(Byte)(len & 0xFF)"), ("4", "(Byte)((len >> 8) & 0xFF)")]


@pytest.mark.skipif(not (CLONE_NETSYNC / "NetSyncBattle.cs").is_file(), reason="no shared Memoria clone")
def test_battle_head_read_order_matches_the_clone_source():
    text = (CLONE_NETSYNC / "NetSyncBattle.cs").read_text(encoding="utf-8").replace("\r\n", "\n")
    body = _method_body(text, "private static BattleView ParseView(Byte[] payload)")
    head = body[:body.index("for (Int32 i = 0; i < count")]
    reads = re.findall(r"(?:view\.(\w+)|Byte (openFlags)|Int32 (count)) = br\.Read(\w+)\(\)", head)
    assert [(a or b or c, m) for a, b, c, m in reads] == [
        ("Seq", "UInt16"), ("MapNo", "UInt16"), ("GuestSlots", "Byte"), ("PatNum", "Byte"), ("StartType", "Byte"),
        ("openFlags", "Byte"), ("Nonce", "Byte"), ("SongId", "UInt16"), ("count", "Byte")]
    assert CP._BATTLE_HEAD.format == "<HHBBBBBHB"


# ======================================================================================== WebSocket framing
@pytest.mark.parametrize("n", [0, 1, 125, 126, 1000, 65535, 65536])
@pytest.mark.parametrize("masked", [False, True])
def test_ws_encode_decode_round_trip(n, masked):
    payload = bytes((i * 7 + 3) & 0xFF for i in range(n))
    frame = CP.ws_encode(payload, CP.OP_BINARY, b"\x11\x22\x33\x44" if masked else None)
    fin, op, got, used = CP.ws_decode(bytearray(frame))
    assert (fin, op, got, used) == (True, CP.OP_BINARY, payload, len(frame))
    for cut in (1, len(frame) // 2, len(frame) - 1):  # any prefix is "incomplete", never a misparse
        if 0 < cut < len(frame):
            assert CP.ws_decode(bytearray(frame[:cut])) is None


def test_ws_decode_caps_an_implausible_length():
    with pytest.raises(CP.WsProtocolError):
        CP.ws_decode(bytearray([0x82, 127]) + (1 << 40).to_bytes(8, "big"))


def test_ws_framing_interoperates_with_the_roundtrip_helpers():
    """The existing bridge test's client helpers are an independent oracle: what they send, WsConn reads; what WsConn
    (server side, unmasked) sends, they read -- and a WsConn client's masked frames read back through a server WsConn."""
    TR = _roundtrip_helpers()
    a, b = socket.socketpair()
    try:
        server = CP.WsConn(b, client=False)
        pkt = CP.build_pos_frame(250)
        TR.send_binary(a, pkt)                             # masked, as NetSyncRelay emits
        assert server.recv(poll=TIMEOUT) == (CP.OP_BINARY, pkt)
        state = CP.build_frame(CP.TYPE_STATE, bytes(range(200)) * 10)   # 2 KB: a 16-bit length
        server.send(state)
        assert TR.recv_frame(a, time.time() + TIMEOUT) == (0x2, state)
        client = CP.WsConn(a, client=True)
        client.send(state)
        assert server.recv(poll=TIMEOUT) == (CP.OP_BINARY, state)
    finally:
        a.close()
        b.close()


def test_wsconn_answers_pings_reassembles_fragments_and_reports_a_clean_close():
    a, b = socket.socketpair()
    try:
        a.settimeout(TIMEOUT)
        server = CP.WsConn(b, client=False)
        a.sendall(CP.ws_encode(b"hi", CP.OP_PING, b"\x01\x02\x03\x04")
                  + CP.ws_encode(b"ab", CP.OP_BINARY, b"\x05\x06\x07\x08", fin=False)
                  + CP.ws_encode(b"cd", CP.OP_CONT, b"\x09\x0A\x0B\x0C"))
        assert server.recv(poll=TIMEOUT) == (CP.OP_BINARY, b"abcd")
        pong = CP.ws_decode(bytearray(a.recv(64)))
        assert pong[1] == CP.OP_PONG and pong[2] == b"hi"
        assert server.recv(poll=0.05) is None             # nothing pending: a poll, not an error
        a.sendall(CP.ws_encode((1000).to_bytes(2, "big") + b"bye", CP.OP_CLOSE, b"\x00\x00\x00\x01"))
        with pytest.raises(CP.WsClosed) as err:
            server.recv(poll=TIMEOUT)
        assert err.value.code == 1000 and err.value.clean
        a.close()                                          # then the peer just goes: EOF (or a reset) is no clean close
        with pytest.raises(CP.WsClosed) as err:
            server.recv(poll=TIMEOUT)
        assert err.value.code is None and not err.value.clean
    finally:
        a.close()
        b.close()


def test_log_file_failure_never_raises_into_the_caller(tmp_path):
    """The log runs inside the reader/pump threads: a tee file that stops taking writes (a full disk) must drop to
    stdout-only, never raise -- a raise there ends the bench session it was only describing."""
    buf = io.StringIO()
    log = CP.Log(tmp_path / "peer.log", stream=buf)

    class _Full:
        def write(self, _text):
            raise OSError(28, "No space left on device")

        def close(self):
            pass

    log("before")
    log._file.close()
    log._file = _Full()
    log("during")                                          # must not raise
    log("after")
    log.close()
    text = buf.getvalue()
    assert "during" in text and "after" in text and "log file disabled" in text
    assert "before" in (tmp_path / "peer.log").read_text(encoding="utf-8")


def test_session_path_round_trip():
    assert CP.session_path("ff9-abcd1234", "guest") == "/sess/ff9-abcd1234?role=guest"
    assert CP.parse_session_path("/sess/ff9-abcd1234?role=host") == ("ff9-abcd1234", "host")
    assert CP.parse_session_path(CP.session_path("a b/c", "guest")) == ("a b/c", "guest")
    assert CP.parse_session_path("/other?role=host") == ("", "host")


# ======================================================================================== the tape
def _write_tape(path, spec, mode="test"):
    """``spec`` = [(t, dir, payload)] -> a tape on disk, through the real writer (its clock reads each t)."""
    clock = {"now": 0.0}
    tap = CP.TapeWriter(path, mode=mode, clock=lambda: clock["now"])
    for t, d, payload in spec:
        clock["now"] = t
        tap.write(d, payload)
    tap.close()
    return tap


def test_tape_write_read_round_trip(tmp_path):
    path = tmp_path / "host.f9tape"
    spec = [(0.0, CP.DIR_NOTE, b"host game connected, session ff9-x"),
            (0.010, CP.DIR_HOST, CP.build_pos_frame(250)),
            (0.012, CP.DIR_GUEST, CP.build_pos_frame(250)),
            (0.043, CP.DIR_HOST, CP.build_frame(CP.TYPE_STATE, bytes(2048)))]
    tap = _write_tape(path, spec)
    assert tap.records == 4
    header, records, torn = CP.read_tape(path)
    assert header["tool"] == "coop_peer" and header["wire"] == 14 and header["mode"] == "test"
    assert torn == 0
    assert [(r.t, r.dir, r.payload) for r in records] == spec
    assert [r.payload for r, _, _ in CP.host_frames(records)] == [spec[1][2], spec[3][2]]


def test_tape_torn_tail_keeps_the_whole_records(tmp_path):
    path = tmp_path / "torn.f9tape"
    _write_tape(path, [(0.0, CP.DIR_HOST, CP.build_pos_frame(1)), (0.5, CP.DIR_HOST, CP.build_pos_frame(2))])
    data = path.read_bytes()
    path.write_bytes(data[:-10])                           # a run killed mid-write
    _, records, torn = CP.read_tape(path)
    assert len(records) == 1 and torn == CP._REC.size + 42 - 10


def test_read_tape_refuses_a_foreign_file(tmp_path):
    path = tmp_path / "x.bin"
    path.write_bytes(b"not a tape at all")
    with pytest.raises(CP.TapeError):
        CP.read_tape(path)


def _battle_frame(seq, nonce, map_no=412, flags=0x0B):
    return CP.build_frame(CP.TYPE_BATTLE, struct.pack("<HHBBBBBHB", seq, map_no, 0, 0, 0, flags, nonce, 0xFFFF, 0))


def _synthetic_host(duration=10.0, battles=((3.0, 6.0, 7),), field=250, dt=1 / 30):
    """A host tape's records: a pos frame every tick (field 0 inside a battle), a type-1 frame with an advancing seq
    inside each ``(start, end, nonce)`` battle."""
    recs = []
    n = int(duration / dt)
    seq = 0
    for i in range(n + 1):
        t = round(i * dt, 6)
        inside = [b for b in battles if b[0] <= t <= b[1]]
        recs.append(CP.Record(t, CP.DIR_HOST, CP.build_pos_frame(0 if inside else field)))
        if inside:
            seq += 1
            recs.append(CP.Record(t, CP.DIR_HOST, _battle_frame(seq, inside[0][2])))
    return recs


def test_tape_battles_and_fields_segment_by_nonce_and_gap():
    recs = _synthetic_host(duration=20.0, battles=((2.0, 5.0, 7), (5.5, 8.0, 8), (12.0, 14.0, 8)))
    battles = CP.tape_battles(recs)
    assert [(b["n"], b["nonce"]) for b in battles] == [(1, 7), (2, 8), (3, 8)]   # nonce 8 twice: split by the gap
    assert battles[0]["start"] == pytest.approx(2.0, abs=0.04) and battles[0]["end"] == pytest.approx(5.0, abs=0.04)
    fields = CP.tape_fields(recs)
    assert [f for _, f in fields] == [250, 0, 250, 0, 250, 0, 250]
    assert fields[1][0] == pytest.approx(2.0, abs=0.04) and fields[2][0] == pytest.approx(5.0, abs=0.04)
    assert CP.resolve_time("battle+10", battles) == pytest.approx(battles[0]["start"] + 10)
    assert CP.resolve_time("battle2-1.5", battles) == pytest.approx(battles[1]["start"] - 1.5)
    assert CP.resolve_time("battle3.end+0.5", battles) == pytest.approx(battles[2]["end"] + 0.5)
    assert CP.resolve_time("battle.end", battles) == pytest.approx(battles[0]["end"])
    assert CP.resolve_time("45.25", battles) == 45.25
    for bad in ("battle4+1", "soon", "battle+", "-3"):
        with pytest.raises(ValueError):
            CP.resolve_time(bad, battles)


# ======================================================================================== the replay (fake clock)
class FakeClock:
    def __init__(self, start=1000.0):
        self.now = start
        self.slept = 0.0

    def __call__(self):
        return self.now

    def sleep(self, dt):
        assert dt >= 0
        self.now += dt
        self.slept += dt


def _replay(recs, *, start=None, stop_at=None, blackholes=(), accept=True):
    """Run a Replayer over ``recs`` on a fake clock: ``sent`` = [(wall, tape t)] of every frame a guest took."""
    clock = FakeClock()
    sent = []
    lines = []
    frames = CP.host_frames(recs)
    rep = CP.Replayer(frames, start=frames[0][0].t if start is None else start, stop_at=stop_at,
                      blackholes=blackholes, send=lambda payload: accept,
                      on_sent=lambda rec, wtype, payload: sent.append((clock.now, rec.t)),
                      log=lambda m: lines.append((clock.now, m)), clock=clock, sleep=clock.sleep, progress_every=1e9)
    wall0 = clock.now
    summary = rep.run()
    return rep, summary, sent, lines, wall0


def test_replay_keeps_the_original_timing():
    recs = _synthetic_host(duration=4.0, battles=((1.0, 3.0, 5),))
    rep, summary, sent, _, wall0 = _replay(recs)
    assert summary["why"] == "tape end" and summary["dropped"] == 0 and summary["unsent"] == 0
    assert summary["sent"] == len(CP.host_frames(recs)) == len(sent)
    for wall, t in sent:
        assert wall - wall0 == pytest.approx(t, abs=1e-6)  # due at wall0 + (t - start), start = 0
    assert summary["max_lag"] == pytest.approx(0.0, abs=1e-6)


def test_blackhole_sends_nothing_in_the_window_and_resumes_on_the_original_timeline():
    recs = _synthetic_host(duration=10.0, battles=((2.0, 8.0, 9),))
    rep, summary, sent, lines, wall0 = _replay(recs, blackholes=[(4.0, 2.0)])
    times = sent
    assert times and all(not (4.0 <= t < 6.0) for _, t in times)
    inside = [r for r, _, _ in CP.host_frames(recs) if 4.0 <= r.t < 6.0]
    assert summary["dropped"] == len(inside) > 100       # ~2 s of 30 Hz pos + battle frames
    assert summary["sent"] + summary["dropped"] == len(CP.host_frames(recs))
    for wall, t in times:                                 # resumes at the frames' OWN times -- nothing shifted
        assert wall - wall0 == pytest.approx(t, abs=1e-6)
    before = max(t for _, t in times if t < 4.0)
    after = min(t for _, t in times if t >= 6.0)
    assert before == pytest.approx(4.0, abs=0.04) and after == pytest.approx(6.0, abs=0.04)
    begin = [(w, m) for w, m in lines if m.startswith("BLACKHOLE at tape")]
    end = [(w, m) for w, m in lines if m.startswith("BLACKHOLE over at tape")]
    assert len(begin) == 1 and len(end) == 1
    assert begin[0][0] - wall0 == pytest.approx(4.0) and "for 2.00 s" in begin[0][1]
    assert end[0][0] - wall0 == pytest.approx(6.0)


def test_blackhole_from_a_battle_anchor_and_several_windows():
    recs = _synthetic_host(duration=12.0, battles=((2.0, 10.0, 3),))
    battles = CP.tape_battles(recs)
    at = CP.resolve_time("battle+3", battles)              # the sitting-A row's shape: battle+N for M s
    rep, summary, sent, lines, _ = _replay(recs, blackholes=[(at, 1.0), (8.0, 0.5)])
    times = [t for _, t in sent]
    assert not any(at <= t < at + 1.0 or 8.0 <= t < 8.5 for t in times)
    assert sum(1 for _, m in lines if m.startswith("BLACKHOLE at")) == 2


def test_stop_at_and_from_bound_the_replay():
    recs = _synthetic_host(duration=6.0, battles=())
    rep, summary, sent, lines, wall0 = _replay(recs, start=1.0, stop_at=3.0)
    times = sent
    assert summary["why"] == "stop-at"
    assert min(t for _, t in times) == pytest.approx(1.0, abs=0.04)
    assert max(t for _, t in times) < 3.0
    assert any(m.startswith("STOP-AT tape 3.00") for _, m in lines)
    for wall, t in times:
        assert wall - wall0 == pytest.approx(t - 1.0, abs=1e-6)


def test_replay_with_no_guest_attached_counts_the_frames_unsent():
    recs = _synthetic_host(duration=1.0, battles=())
    _, summary, _, _, _ = _replay(recs, accept=False)
    assert summary["sent"] == 0 and summary["unsent"] == len(CP.host_frames(recs))


def test_replay_stop_event_ends_it_early():
    recs = _synthetic_host(duration=5.0, battles=())
    clock = FakeClock()
    stop = threading.Event()
    frames = CP.host_frames(recs)
    n = {"sent": 0}

    def send(payload):
        n["sent"] += 1
        if n["sent"] == 10:
            stop.set()
        return True
    rep = CP.Replayer(frames, start=0.0, send=send, log=lambda m: None, clock=clock, sleep=clock.sleep)
    assert rep.run(stop)["why"] == "stopped" and n["sent"] == 10


# ======================================================================================== the fake guest (pure)
def test_guest_model_mirrors_the_host_field_and_starts_on_the_sentinel():
    m = CP.GuestModel(offset=(10.0, 0.0, -5.0))
    first = CP.parse_pos_payload(CP.parse_frame(m.outgoing(0.0)[0])[1])
    assert first["field"] == CP.FIELD_SENTINEL            # NetSyncRelay's constructor sentinel until the host speaks
    ev = m.on_host_frame(CP.TYPE_POS, CP.build_pos_payload(250, anim=7, model=98, mesh_vis=3, loco=2,
                                                           pos=(100.0, 0.0, 200.0)), 0.1)
    assert ev == ["host pos: field 250 (was none)"]
    p = CP.parse_pos_payload(CP.parse_frame(m.outgoing(0.1)[0])[1])
    assert (p["field"], p["model"], p["anim"], p["loco"], p["pos"]) == (250, 98, 7, 2, (110.0, 0.0, 195.0))
    m.on_host_frame(CP.TYPE_POS, CP.build_pos_payload(0), 0.2)    # the host in battle: field 0, mirrored
    assert CP.parse_pos_payload(CP.parse_frame(m.outgoing(0.2)[0])[1])["field"] == 0
    pinned = CP.GuestModel(field=30003)
    pinned.on_host_frame(CP.TYPE_POS, CP.build_pos_payload(250), 0.0)
    assert CP.parse_pos_payload(CP.parse_frame(pinned.outgoing(0.0)[0])[1])["field"] == 30003


def _battle_payload(seq, nonce):
    return CP.parse_frame(_battle_frame(seq, nonce))[1]


def test_guest_model_reports_live_only_while_the_host_battle_lane_is_live():
    m = CP.GuestModel(report=BW.BOOT_LIVE, menu=BW.CTL_SHUT)
    assert len(m.outgoing(0.0)) == 1                       # no battle lane: no control frame (Pump's live gate)
    ev = m.on_host_frame(CP.TYPE_BATTLE, _battle_payload(1, 7), 1.0)
    assert len(ev) == 1 and ev[0].startswith("host battle lane UP: nonce 7 map 412")
    frames = m.outgoing(1.0)
    assert [f[2] for f in frames] == [CP.TYPE_POS, CP.TYPE_CONTROL]   # CollectOutgoing's order
    assert frames[1][CP.HEADER_SIZE:] == bytes([0, BW.CTL_SHUT, BW.CTL_FMT1, 7, BW.BOOT_LIVE])
    # the SAME seq re-served is no freshness (the transport's repeats): stale 2 s after the seq last advanced
    m.on_host_frame(CP.TYPE_BATTLE, _battle_payload(1, 7), 2.9)
    assert len(m.outgoing(2.9)) == 2
    assert len(m.outgoing(3.0)) == 1
    assert m.tick(3.0)[0].startswith("host battle lane STALE: nonce 7 seq 1")
    assert m.tick(3.1) == []                                # one edge, not a stream
    m.on_host_frame(CP.TYPE_BATTLE, _battle_payload(2, 8), 4.0)
    assert m.outgoing(4.0)[1][CP.HEADER_SIZE:] == bytes([0, 0, 1, 8, BW.BOOT_LIVE])   # names the CURRENT nonce


def test_guest_model_live_after_reports_booting_first_and_legacy_has_no_trailer():
    m = CP.GuestModel(report=BW.BOOT_LIVE, menu=BW.CTL_ROOT, live_after=1.5)
    m.on_host_frame(CP.TYPE_BATTLE, _battle_payload(1, 3), 10.0)
    assert m.control_payload(10.5) == bytes([0, 2, 1, 3, BW.BOOT_BOOTING])
    m.on_host_frame(CP.TYPE_BATTLE, _battle_payload(2, 3), 11.6)
    assert m.control_payload(11.6) == bytes([0, 2, 1, 3, BW.BOOT_LIVE])
    legacy = CP.GuestModel(report="legacy", menu=1)
    legacy.on_host_frame(CP.TYPE_BATTLE, _battle_payload(1, 3), 0.0)
    assert legacy.control_payload(0.0) == b"\x00\x01"
    off = CP.GuestModel()
    off.on_host_frame(CP.TYPE_BATTLE, _battle_payload(1, 3), 0.0)
    assert off.control_payload(0.0) is None


def test_guest_watch_decodes_the_guest_control_frames_against_the_host_nonce():
    w = CP.GuestWatch()
    pos = CP.build_pos_frame(250)
    assert w.on_guest_message(pos, 0.0) == ["guest pos: field 250 (was none)"]
    assert w.on_guest_message(pos, 0.03) == []              # edges only
    ctl = CP.build_frame(CP.TYPE_CONTROL, BW.encode_control(BW.CTL_ROOT, 3, BW.BOOT_LIVE))
    assert w.on_guest_message(ctl, 0.1) == ["guest control: menu 2 (root) | fmt-1 report: nonce 3 boot LIVE -- "
                                            "no host battle on the wire yet"]
    w.note_host(CP.TYPE_BATTLE, _battle_payload(1, 3))
    declined = CP.build_frame(CP.TYPE_CONTROL, BW.encode_control(BW.CTL_SHUT, 3, BW.BOOT_DECLINED))
    assert w.on_guest_message(declined, 0.2) == ["guest control: menu 0 (shut) | fmt-1 report: nonce 3 boot DECLINED "
                                                 "-- names THIS battle (host nonce 3)"]
    w.note_host(CP.TYPE_BATTLE, _battle_payload(2, 4))
    other = CP.build_frame(CP.TYPE_CONTROL, BW.encode_control(BW.CTL_SHUT, 3, BW.BOOT_LIVE))
    assert w.on_guest_message(other, 0.3)[0].endswith("names ANOTHER battle (host nonce 4)")
    cmd = CP.build_frame(CP.TYPE_COMMAND, BW.encode_command(1, 1, mask=0x10))
    assert w.on_guest_message(cmd, 0.4) == ["guest COMMAND: slot 1 action 1 menu 0 id 0 mask 0x0010 cursor 0"]
    state = CP.build_frame(CP.TYPE_STATE, b"\x00")
    assert len(w.on_guest_message(state, 0.5)) == 1 and w.on_guest_message(state, 0.6) == []
    assert w.on_guest_message(bytes([0xF9, 13, 0, 0, 0]), 0.7)[0].startswith("guest sent a frame the engine would DROP")
    stale = w.tick(2.7)
    assert any(s.startswith("guest pos lane STALE") for s in stale)
    assert any(s.startswith("guest control lane SHUT") for s in stale)
    assert w.tick(2.8) == []


# ======================================================================================== end to end (loopback)
def _ws_url(port):
    return f"ws://127.0.0.1:{port}"


def _recv_frames(conn, seconds):
    """Every NetSyncWire frame a WsConn receives for ``seconds``: [(monotonic, type, payload)]."""
    out = []
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        msg = conn.recv(poll=max(0.01, deadline - time.monotonic()))
        if msg is not None:
            got = CP.parse_frame(msg[1])
            assert got is not None, msg
            out.append((time.monotonic(), got[0], got[1]))
    return out


def test_serve_guest_plays_the_guest_of_a_host_game_and_tapes_it(tmp_path):
    log, buf = _log()
    tap = CP.TapeWriter(tmp_path / "host.f9tape", mode="serve-guest")
    served = CP.ServeGuest(lambda: CP.GuestModel(report=BW.BOOT_LIVE), log=log, tap=tap, status_every=60)
    listener = CP.Listener(0, served.on_conn, log=log)
    try:
        host = CP.dial_ws(_ws_url(listener.port), CP.session_path("ff9-bench", "host"))   # the HOST game's dial
        host.send(CP.build_pos_frame(250, model=98))
        host.send(_battle_frame(1, 6))
        frames = _recv_frames(host, 0.6)
        pos = [CP.parse_pos_payload(p) for _, t, p in frames if t == CP.TYPE_POS]
        ctl = [p for _, t, p in frames if t == CP.TYPE_CONTROL]
        assert len(pos) >= 9                                # ~30 Hz for 0.6 s
        assert pos[-1]["field"] == 250 and pos[-1]["model"] == 98
        assert ctl and ctl[-1] == bytes([0, 0, 1, 6, BW.BOOT_LIVE])
        host.close(1000)
        assert _wait_for(lambda: served.ended)
        # the host's close frame, or -- when Windows answers a close over unread bytes with a reset -- the reset
        assert served.ended[0].startswith(("the host game hop closed", "send failed")), served.ended
    finally:
        listener.close()
        served.stop("test over")
        tap.close()
    text = buf.getvalue()
    assert "HOST game connected (session ff9-bench)" in text and "host battle lane UP: nonce 6" in text
    assert all(line.startswith("[coop-peer ") for line in text.splitlines())   # never "[bridge]"
    _, records, torn = CP.read_tape(tmp_path / "host.f9tape")
    assert torn == 0
    host_sent = [CP.parse_frame(r.payload)[0] for r in records if r.dir == CP.DIR_HOST]
    assert host_sent == [CP.TYPE_POS, CP.TYPE_BATTLE]
    assert sum(1 for r in records if r.dir == CP.DIR_GUEST) >= 9
    assert any(r.dir == CP.DIR_NOTE for r in records)


def test_each_mode_refuses_the_wrong_role_with_a_400():
    log, buf = _log()
    served = CP.ServeGuest(CP.GuestModel, log=log)
    rh = CP.ReplayHost(CP.host_frames(_synthetic_host(duration=0.1, battles=())), start=0.0, log=log)
    listeners = [CP.Listener(0, served.on_conn, log=log), CP.Listener(0, rh.on_conn, log=log)]
    try:
        with pytest.raises(ConnectionError, match="400"):    # the game logs "relay refused upgrade: ... 400"
            CP.dial_ws(_ws_url(listeners[0].port), CP.session_path("ff9-x", "guest"))
        with pytest.raises(ConnectionError, match="400"):
            CP.dial_ws(_ws_url(listeners[1].port), CP.session_path("ff9-x", "host"))
        assert _wait_for(lambda: "a role=guest game wants `replay-host`" in buf.getvalue()
                         and "a role=host game wants `serve-guest`" in buf.getvalue())
    finally:
        rh.close()
        for listener in listeners:
            listener.close()


def test_listener_refuses_a_busy_port_instead_of_co_binding():
    log, _ = _log()
    first = CP.Listener(0, lambda s, a: None, log=log)
    try:
        with pytest.raises(CP.PortBusy, match="REPLACES the bridge"):
            CP.Listener(first.port, lambda s, a: None, log=log)
    finally:
        first.close()


def test_replay_host_replays_into_a_guest_game_with_a_blackhole_and_logs_its_reports(tmp_path):
    recs = _synthetic_host(duration=2.0, battles=((0.2, 2.0, 7),))
    frames = CP.host_frames(recs)
    log, buf = _log()
    tap = CP.TapeWriter(tmp_path / "replay.f9tape", mode="replay-host")
    rh = CP.ReplayHost(frames, start=0.0, blackholes=[(0.8, 0.6)], log=log, tap=tap)
    listener = CP.Listener(0, rh.on_conn, log=log)
    runner = threading.Thread(target=rh.run, daemon=True)
    runner.start()
    try:
        guest = CP.dial_ws(_ws_url(listener.port), CP.session_path("ff9-bench", "guest"))   # the GUEST game's dial
        t0 = time.monotonic()
        guest.send(CP.build_pos_frame(250))               # its keepalive starts the replay clock
        got = []
        reported = False
        deadline = t0 + 3.0
        while time.monotonic() < deadline and runner.is_alive():
            msg = guest.recv(poll=0.05)
            if msg is not None:
                got.append((time.monotonic() - t0, CP.parse_frame(msg[1])))
                if not reported and got[-1][1][0] == CP.TYPE_BATTLE:
                    reported = True                       # answer like an s114 guest, on the nonce it was sent
                    guest.send(CP.build_frame(CP.TYPE_CONTROL, BW.encode_control(BW.CTL_ROOT, 7, BW.BOOT_LIVE)))
        runner.join(TIMEOUT)
        assert not runner.is_alive()
        # the blackhole is a SILENCE on an open link: a gap of ~0.6 s, then frames again on the same connection
        gaps = [(b[0] - a[0], a[0]) for a, b in zip(got, got[1:])]
        biggest, at = max(gaps)
        assert 0.45 < biggest < 0.95 and 0.6 < at < 1.1
        assert got[-1][0] > 1.6                            # frames resumed after the cut (no reconnect)
        assert rh.result["why"] == "tape end" and rh.result["dropped"] > 0 and rh.result["unsent"] == 0
        assert rh.port.conn is not None                    # the TCP is still open after the tape ('hold')
    finally:
        rh.close()
        listener.close()
        tap.close()
    text = buf.getvalue()
    assert "guest pos: field 250 (was none)" in text
    assert ("guest control: menu 2 (root) | fmt-1 report: nonce 7 boot LIVE -- names THIS battle (host nonce 7)"
            in text)
    assert "BLACKHOLE at tape 0.80 s" in text and "BLACKHOLE over at tape 1.40 s" in text
    _, records, _ = CP.read_tape(tmp_path / "replay.f9tape")
    notes = [r.payload.decode() for r in records if r.dir == CP.DIR_NOTE]
    assert any(n.startswith("BLACKHOLE at tape 0.80") for n in notes)
    assert any(r.dir == CP.DIR_GUEST and CP.parse_frame(r.payload)[0] == CP.TYPE_CONTROL for r in records)


# ======================================================================================== the local relay
@pytest.fixture
def relay():
    log, buf = _log()
    r = CP.LocalRelay(log=log, pair_wait=3.0, rejoin_grace=60.0, idle=30.0)
    listener = CP.Listener(0, r.handle, log=log)
    r.port = listener.port
    r.buf = buf
    yield r
    r.close_all()
    listener.close()


def _dial(relay, code, role):
    return CP.dial_ws(_ws_url(relay.port), CP.session_path(code, role))


def _recv_data(conn, timeout=TIMEOUT):
    msg = conn.recv(poll=timeout)
    assert msg is not None, "nothing arrived"
    return msg[1]


def _expect_closed(conn, timeout=TIMEOUT):
    """The far side ends this connection within ``timeout`` (any data still in flight is skipped)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            conn.recv(poll=0.1)
        except CP.WsClosed:
            return
    pytest.fail("the connection stayed open")


def test_relay_pairs_by_code_and_forwards_both_ways(relay):
    host = _dial(relay, "ff9-pair1", "host")
    early = CP.build_pos_frame(250)
    host.send(early)                                       # before the guest: the relay does not read it yet...
    guest = _dial(relay, "FF9-PAIR1", "guest")             # ...codes compare upper-cased (main.go)
    assert _recv_data(guest) == early                      # ...and forwards it once paired
    g = CP.build_frame(CP.TYPE_CONTROL, BW.encode_control(BW.CTL_ROOT, 1, BW.BOOT_LIVE))
    guest.send(g)
    assert _recv_data(host) == g
    big = CP.build_frame(CP.TYPE_STATE, bytes(range(256)) * 8)
    host.send(big)
    assert _recv_data(guest) == big
    assert _wait_for(lambda: "relay session FF9-PAIR1: guest paired -- forwarding" in relay.buf.getvalue())


def test_relay_never_cross_wires_two_sessions(relay):
    h1, h2 = _dial(relay, "ff9-a", "host"), _dial(relay, "ff9-b", "host")
    g1, g2 = _dial(relay, "ff9-a", "guest"), _dial(relay, "ff9-b", "guest")
    h1.send(b"for-a")
    h2.send(b"for-b")
    assert _recv_data(g1) == b"for-a" and _recv_data(g2) == b"for-b"
    assert g1.recv(poll=0.2) is None and g2.recv(poll=0.2) is None


def test_relay_holds_a_dropped_leg_for_rejoin_and_resumes(relay):
    host = _dial(relay, "ff9-rejoin", "host")
    guest = _dial(relay, "ff9-rejoin", "guest")
    host.send(b"one")
    assert _recv_data(guest) == b"one"
    guest.close()                                          # an ABNORMAL drop (no close frame)
    assert _wait_for(lambda: "guest parked -- holding the session for rejoin" in relay.buf.getvalue())
    host.send(b"lost")                                     # dropped while parked; the host leg survives
    assert host.recv(poll=0.3) is None
    guest2 = _dial(relay, "ff9-rejoin", "guest")
    assert _wait_for(lambda: "guest rejoined" in relay.buf.getvalue())
    host.send(b"two")
    assert _recv_data(guest2) == b"two"
    guest2.send(b"back")
    assert _recv_data(host) == b"back"


def test_relay_clean_close_tears_the_session_down(relay):
    host = _dial(relay, "ff9-quit", "host")
    guest = _dial(relay, "ff9-quit", "guest")
    host.send(b"x")
    assert _recv_data(guest) == b"x"
    host.close(1000)                                       # a deliberate quit ends the whole session
    _expect_closed(guest)
    assert "host quit cleanly -- closing the session" in relay.buf.getvalue()
    assert "FF9-QUIT" not in relay.sessions


def test_relay_unpaired_leg_times_out(relay):
    relay.pair_wait = 0.3
    lone = _dial(relay, "ff9-lonely", "host")
    _expect_closed(lone)
    assert "host timed out waiting for its partner" in relay.buf.getvalue()


def test_relay_gc_ends_a_session_past_the_rejoin_grace(relay):
    host = _dial(relay, "ff9-gc", "host")
    guest = _dial(relay, "ff9-gc", "guest")
    host.send(b"x")
    assert _recv_data(guest) == b"x"
    guest.close()
    assert _wait_for(lambda: "guest parked" in relay.buf.getvalue())
    assert relay.gc(time.monotonic() + 1.0) == []          # inside the grace: kept
    assert relay.gc(time.monotonic() + 61.0) == ["FF9-GC"]
    assert "guest rejoin grace expired" in relay.buf.getvalue()
    _expect_closed(host)


def test_relay_tap_records_each_message_by_its_senders_role(tmp_path):
    log, _ = _log()
    tap = CP.TapeWriter(tmp_path / "relay.f9tape", mode="relay")
    r = CP.LocalRelay(log=log, tap=tap, pair_wait=3.0)
    listener = CP.Listener(0, r.handle, log=log)
    try:
        host = CP.dial_ws(_ws_url(listener.port), CP.session_path("ff9-tap", "host"))
        guest = CP.dial_ws(_ws_url(listener.port), CP.session_path("ff9-tap", "guest"))
        host.send(CP.build_pos_frame(250))
        assert _recv_data(guest) == CP.build_pos_frame(250)
        guest.send(CP.build_pos_frame(251))
        assert _recv_data(host) == CP.build_pos_frame(251)
    finally:
        r.close_all()
        listener.close()
        tap.close()
    _, records, _ = CP.read_tape(tmp_path / "relay.f9tape")
    data = [(r.dir, CP.parse_pos_payload(CP.parse_frame(r.payload)[1])["field"]) for r in records
            if r.dir != CP.DIR_NOTE]
    assert data == [(CP.DIR_HOST, 250), (CP.DIR_GUEST, 251)]


def test_the_production_bridge_in_the_loop_reaches_a_fake_guest_client(relay, capsys):
    """game(host) -> the REAL bridge -> this relay <- fake-guest-client: the T1 bench's wiring, end to end."""
    bridge, _ = NB.run_server("127.0.0.1", 0, _ws_url(relay.port), False)
    bport = bridge.getsockname()[1]
    rc = {}
    client = threading.Thread(target=lambda: rc.update(rc=CP.main([
        "fake-guest-client", "--relay", _ws_url(relay.port), "--code", "ff9-loop", "--once", "--report", "live",
        "--status", "60"])), daemon=True)
    client.start()
    try:
        TR = _roundtrip_helpers()
        game = TR.ws_client_connect(bport, CP.session_path("ff9-loop", "host"))   # the host game, as NetSyncRelay
        TR.send_binary(game, CP.build_pos_frame(250))
        TR.send_binary(game, _battle_frame(1, 4))
        fields, ctl = [], None
        deadline = time.time() + TIMEOUT
        while time.time() < deadline and not (len(fields) >= 5 and fields[-1] == 250 and ctl is not None):
            op, payload = TR.recv_frame(game, deadline)
            wtype, body = CP.parse_frame(payload)
            if wtype == CP.TYPE_POS:
                fields.append(CP.parse_pos_payload(body)["field"])
            elif wtype == CP.TYPE_CONTROL:
                ctl = body
            if len(fields) % 10 == 0:
                TR.send_binary(game, _battle_frame(len(fields) + 2, 4))     # keep the host's battle lane advancing
        assert len(fields) >= 5 and fields[-1] == 250
        assert ctl == bytes([0, 0, 1, 4, BW.BOOT_LIVE])
        game.close()                                        # the game quits; the bridge closes its upstream
        for s in list(relay.sessions.values()):             # end the fake guest's leg (as a relay teardown would)
            relay._teardown(s)
        client.join(TIMEOUT)
        assert rc.get("rc") == 0
    finally:
        bridge.close()
    out = capsys.readouterr().out
    assert "coop_peer fake-guest-client -- SOLO BENCH PEER. THIS IS NOT THE PRODUCTION NETSYNC BRIDGE." in out


# ======================================================================================== the CLI's read-only modes
def test_info_and_dump_read_a_tape(tmp_path, capsys):
    path = tmp_path / "t.f9tape"
    recs = _synthetic_host(duration=3.0, battles=((1.0, 2.0, 2),))
    clock = {"now": 0.0}
    tap = CP.TapeWriter(path, mode="test", clock=lambda: clock["now"])
    tap.note("host game connected, session ff9-x")
    for r in recs:
        clock["now"] = r.t
        tap.write(r.dir, r.payload)
    tap.close()
    lines = CP.tape_info(path)
    assert any(line.startswith("  battle1: nonce 2 map 412 tape 1.0") for line in lines)
    assert any("field 0 (not on a field" in line for line in lines)
    assert any(line.strip().startswith("host  battle") for line in lines)
    assert CP.main(["info", str(path)]) == 0
    assert CP.main(["dump", str(path), "--type", "1", "--limit", "2", "--hex"]) == 0
    out = capsys.readouterr().out
    dumped = [ln for ln in out.splitlines() if " host  battle seq " in ln]
    assert len(dumped) == 2 and "F9 0E 01 0C 00" in dumped[0]


def test_dump_and_info_decode_an_s133_hosts_action_records(tmp_path, capsys):
    """[ff9mapkit netsync s133] audit D5: `dump` / `info` decode type 6 through battlewire -- an s133 host's START (its
    actor, its vfx kind), the impact's action id, the END; a pre-s133 host's 46-byte impact named as such; `info` counts
    the host's action records (the tape fact s134's act leg reads: STARTs on this tape)."""
    start = BW.encode_action_start(7, 10, 3, 0, BW.ACTOR_IS_PLAYER, 1, 176, 0x10, 0, 0, 0, BW.VFX_KIND_SPECIAL, 100, -1, 5)
    impact = BW.encode_action_impact(7, 10, 0, 4, fig_t=(0, 33, 0), flags=65, cmd_no=1, sub_no=176, act_id=3)
    end = BW.encode_action_end(7, 10, 3, 1, 176)
    old = BW.encode_action_impact(7, 10, 0, 4, fig_t=(0, 33, 0), flags=65, cmd_no=1, sub_no=176)
    texts = [CP.describe_frame(CP.TYPE_ACTION, p) for p in (start, impact, end, old)]
    assert texts[0].startswith("action START id 3 actor 0 flags 0x01 cmd 1 sub 176 tar 0x10") and "kind special 100" \
        in texts[0]
    assert texts[1] == "action impact 0->4 cmd 1/176 hp 33 id 3" and texts[2] == "action END id 3 (cmd 1/176)"
    assert texts[3].endswith("(46 B: no id -- a pre-s133 host)")
    path = tmp_path / "act.f9tape"
    tap = CP.TapeWriter(path, mode="test", clock=lambda: 0.0)
    for p in (start, impact, end, old):
        tap.write(CP.DIR_HOST, CP.build_frame(CP.TYPE_ACTION, p))
    tap.close()
    lines = CP.tape_info(path)
    assert "host action records: 1 START(s), 1 END(s), 2 impact(s) (1 with an action id), 0 stat tick(s), 0 bad" in lines
    assert CP.main(["dump", str(path), "--type", str(CP.TYPE_ACTION)]) == 0
    out = capsys.readouterr().out
    assert "action START id 3" in out and "action END id 3" in out and "a pre-s133 host" in out
    pre = tmp_path / "pre.f9tape"
    tap = CP.TapeWriter(pre, mode="test", clock=lambda: 0.0)
    tap.write(CP.DIR_HOST, CP.build_frame(CP.TYPE_ACTION, old))
    tap.close()
    assert any(ln.endswith("-- no START: a pre-s133 host (or its `actbench hoststarts off`)") for ln in CP.tape_info(pre))


def test_replay_host_cli_refuses_a_bad_plan_before_listening(tmp_path, capsys):
    path = tmp_path / "t.f9tape"
    _write_tape(path, [(0.0, CP.DIR_HOST, CP.build_pos_frame(250))])
    assert CP.main(["replay-host", str(path), "--blackhole-at", "battle+3", "--blackhole-for", "2"]) == 2
    assert "the tape has 0 battle(s)" in capsys.readouterr().out
    assert CP.main(["replay-host", str(path), "--dial", "ws://127.0.0.1:1"]) == 2
    assert "--dial needs --code" in capsys.readouterr().out
    assert CP.main(["replay-host", str(path), "--blackhole-at", "1", "--blackhole-at", "2", "--blackhole-for", "1",
                    "--blackhole-for", "0"]) == 2
