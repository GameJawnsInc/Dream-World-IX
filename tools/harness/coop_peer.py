#!/usr/bin/env python3
"""coop_peer -- the SOLO TWO-ROLE BENCH PEER for FF9 co-op netsync. [ff9mapkit netsync R3 T2]

    *** A BENCH INSTRUMENT. NOT THE PRODUCTION NETSYNC BRIDGE. ***

Every line it prints starts ``[coop-peer`` (the production bridge prints ``[bridge]``), every mode opens with a banner
saying so, and its HTTP 101 carries ``X-Coop-Peer: bench``. It REPLACES the bridge on the game's RelayUrl port; it never
sits beside it (the listener binds exclusively, so a running bridge makes it refuse loudly instead of co-binding).

WHY (studies/battle-coop/R3-SITTING-A-FIXES.md, "T2"). No guest-side watcher, exit-ramp or mirror-gated behaviour could
be benched solo: the selftest role returns before the transport and DioramaTick exist, and IsMirroringStory needs a real
socket. This tool stands in for the bridge on ws://127.0.0.1:49201 (the game's RelayUrl), so ONE desktop game can be
benched as the host OR as the guest:

  serve-guest        the HOST game dials in (GET /sess/<code>?role=host). This tool IS its guest: a v14 type-0
                     position frame at 30 Hz on the host's field (the engine's own WriteLoop cadence), optionally a
                     type-3 control frame carrying an s114 fmt-1 report on the host's current battle nonce
                     (``--report live``) -- and it RECORDS every frame the host sends to a tape (``--tap FILE``).
  replay-host        the GUEST game dials in (role=guest). This tool replays a recorded host tape with its original
                     timing. ``--blackhole-at T --blackhole-for N`` keeps the TCP open and sends NOTHING for N s -- what
                     a Wi-Fi cut looks like behind the decoupled bridge (netsync_bridge.py's docstring: the loopback hop
                     stays up, frames are dropped, never queued). ``--stop-at T`` ends the host there. Everything the
                     guest sends is logged decoded (position field edges, control menu byte + fmt-1 nonce/boot, commands)
                     and can be taped too. ``--dial URL --code C`` replays through a relay as role=host instead.
  relay              a minimal local relay (default port 7777) that pairs role=host and role=guest by session code and
                     forwards whole messages, after studies/battle-coop/relay/main.go v2 (pair wait, rejoin grace,
                     clean-close teardown) -- so the REAL bridge can be put in the loop:
                     ``ff9mapkit coop bridge --relay ws://127.0.0.1:7777``. ``--tap`` records both directions.
  fake-guest-client  the serve-guest guest, but DIALLING a relay as role=guest (the T1 hang-sentinel bench's fake guest).
  info / dump        read a tape: its battles, field edges and frame counts (pick a ``--blackhole-at`` from them).
  dress              [ff9mapkit netsync s139] SECTION 8 ON A REAL WIRE: every HOST type-5 frame on a tape (recorded off the
                     socket by ``serve-guest --tap``: coop_tape_record.py on an s139+ host) carries the host's dress section
                     right after section 7, its body the one the host's config gives (``--expect HEX``, or the twin's for
                     ``--ghost-as/--guest-slots`` over each frame's own party, or a fixed ``--party``), and the s103
                     readers an OLD guest runs (battlewire's twins of
                     ApplyStoryTo / TryReadSection / ParseSections' walk) land the same story, party sections and sections
                     4-7 with section 8 stripped. Exit 0 when every frame holds, 1 when one does not, 2 on a bad tape.
                     A relative tape path missing from the cwd is looked up under the MAIN repo, then by name in the
                     tape home (COOP_TAPE_DIR, else <main repo>/.harness-runs/coop-tapes): a worktree has no tapes.
  where              [ff9mapkit netsync s144] WHERE AN OFF-FIELD HOST SAYS IT STANDS: section 7's b6 world / b7 title on
                     every HOST type-5 frame, against the host's position-lane field (``--want world|title|none|any``;
                     none = an s143-or-older host, whose tape parses exactly as before). Exit 0 / 1 / 2 as ``dress``.

THE TAPE (``.f9tape``) -- stdlib, binary, append-only, crash-tolerant (a torn tail is reported, never fatal):
  ``F9TAPE01`` | u32 LE header length | UTF-8 JSON header | records ``[t f64 LE][dir u8][len u32 LE][payload]``.
  ``t`` = seconds since the tape opened (monotonic); ``dir`` = WHO SENT IT: 0 the host, 1 the guest, 2 a note (UTF-8
  text: connections, blackhole edges). ``payload`` = the WebSocket message, UNMASKED = one whole NetSyncWire frame
  ``[0xF9][14][type][len u16 LE][payload]``. A replay sends only the dir-0 records.

TIME SPECS (``--from``, ``--stop-at``, ``--blackhole-at``) are TAPE seconds, or an anchor on the tape's battles (a
battle = a run of host type-1 frames on one nonce): ``battle+10`` (10 s after the first battle's first frame),
``battle2-1.5``, ``battle.end+0.5`` (after its last frame -- the recorded victory). ``info`` prints the anchors.

THE BENCHES (R3-SITTING-A-FIXES.md):
  record   desktop Role=host, RelayUrl ws://127.0.0.1:49201:   py tools/harness/coop_peer.py serve-guest --tap host.f9tape
           walk 250 into a random encounter, fight ~40 s, win; Ctrl+C. (``--report live`` makes the fake guest report
           its diorama LIVE on each battle nonce, so an s114 start hold never arms; the host's GuestSlots should be 0 --
           a LIVE guest owns its slots and this one never commands.)
  replay   desktop Role=client, FollowHost=1, its own save on 250:
           py tools/harness/coop_peer.py replay-host host.f9tape                    (the CALIBRATION run: it must give
           'paired on the host's field', 'state-mirror ARMED', 'diorama BOOT', 'diorama LIVE' and the end-leave before
           the instrument judges anything) then ``--blackhole-at battle+10 --blackhole-for 6`` (the sitting-A row).
  T1 hang  py tools/harness/coop_peer.py relay  +  ff9mapkit coop bridge --relay ws://127.0.0.1:7777  +
           py tools/harness/coop_peer.py fake-guest-client --code <the host's SessionCode>

LAWS IT KEEPS. Wire v14 (NetSyncWire.Version) -- it builds frames exactly as NetSyncWire.BuildFrame/BuildPosPayload and
accepts exactly what NetSyncRelay.ReadLoop accepts; it sends nothing a real peer would not (the fake guest never sends a
battle lane, a roster or a state frame). The containment law is the ENGINE's, not this tool's: a replayed host is a
recording, and the guest still computes nothing of its own. Stdlib only; the WebSocket handshake primitives are the
production bridge's own (``ff9mapkit.netsync_bridge``: read_http_headers / ws_accept / open_upstream), imported, not
copied; the control-frame codec is tools/harness/battlewire.py's. The framing here UNMASKS (the bridge deliberately never
does), which is why it carries its own small codec -- cross-checked in the tests against
tools/netsync-bridge/test_relay_roundtrip.py's send_binary/recv_frame.

HONEST LIMITS. An instrument, calibrated before it judges: a replayed host does not answer the guest (its commands land
nowhere), replaying one tape twice into ONE guest session repeats the host's dialogue epoch (relaunch the guest between
replays), and a tape recorded on one engine build replays that build's wire.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import re
import select
import socket
import struct
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

try:                                                       # imported as harness.coop_peer (the tests)
    from . import battlewire as BW
except ImportError:                                        # run as a script: tools/harness is sys.path[0]
    import battlewire as BW                                # type: ignore[no-redef]

_REPO = Path(__file__).resolve().parents[2]
_KIT = _REPO / "ff9mapkit"
if "ff9mapkit" not in sys.modules and (_KIT / "ff9mapkit" / "netsync_bridge.py").is_file() and str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))                          # this checkout's kit shadows any installed one
from ff9mapkit import netsync_bridge as NB                 # noqa: E402 -- the production bridge's WS primitives

# ======================================================================================== the wire (NetSyncWire v14)
# NetSyncSocket.cs NetSyncWire: every message is ONE frame [magic 0xF9][version 14][type u8][len u16 LE][payload].
WIRE_MAGIC = 0xF9
WIRE_VERSION = 14
HEADER_SIZE = 5
MAX_PAYLOAD = 8192
TYPE_POS, TYPE_BATTLE, TYPE_COMMAND, TYPE_CONTROL, TYPE_ROSTER, TYPE_STATE, TYPE_ACTION, TYPE_DIALOG = range(8)
TYPE_NAMES = {TYPE_POS: "pos", TYPE_BATTLE: "battle", TYPE_COMMAND: "command", TYPE_CONTROL: "control",
              TYPE_ROSTER: "roster", TYPE_STATE: "state", TYPE_ACTION: "action", TYPE_DIALOG: "dialog"}
#: NetSyncFrames.StaleMs / NetSyncBattle.StaleMs: a lane with no fresh frame this long is gone
STALE_S = 2.0
#: NetSyncRelay.WriteLoop: Thread.Sleep(33) between ticks (~30 Hz)
TICK_S = 0.033
#: NetSyncRelay's constructor sentinel: field 65535 = "not on a field yet" (the peer filters it as "not here")
FIELD_SENTINEL = 65535

# BuildPosPayload: field u16, anim u16, model u16, meshVis u16, loco u8, pos 3f, rot 4f (x y z w) -- 37 bytes, LE.
_POS = struct.Struct("<HHHHB3f4f")
POS_LEN = _POS.size
# NetSyncBattle.SampleOwnBattle / ParseView's head: seq u16, mapNo u16, guestSlots u8, patNum u8, startType u8,
# flags u8, nonce u8, songId u16 (v10), unitCount u8 -- the unit records and the 0xB5 trailer follow.
_BATTLE_HEAD = struct.Struct("<HHBBBBBHB")
BATTLE_HEAD_LEN = _BATTLE_HEAD.size


def build_frame(wtype: int, payload=b"") -> bytes:
    """NetSyncWire.BuildFrame: ``[0xF9][14][type][len lo][len hi]`` + payload. A u16 length is all the header holds."""
    payload = bytes(payload or b"")
    n = len(payload)
    if n > 0xFFFF:
        raise ValueError(f"a NetSyncWire payload of {n} bytes does not fit the u16 length")
    return bytes([WIRE_MAGIC, WIRE_VERSION, wtype & 0xFF, n & 0xFF, (n >> 8) & 0xFF]) + payload


def parse_frame(message) -> tuple | None:
    """NetSyncRelay.ReadLoop's acceptance of one WS message: TryParseHeader (magic, version 14, len <= MaxPayload) AND
    the header's length equal to the rest of the message. -> ``(type, payload)``, or None (a foreign or old peer's
    frame, which the engine drops silently)."""
    data = bytes(message or b"")
    if len(data) < HEADER_SIZE or data[0] != WIRE_MAGIC or data[1] != WIRE_VERSION:
        return None
    n = data[3] | (data[4] << 8)
    if n > MAX_PAYLOAD or n != len(data) - HEADER_SIZE:
        return None
    return data[2], data[HEADER_SIZE:]


def frame_header_text(message) -> str:
    """A rejected message's first bytes, for the one log line that names WHY (magic / version / length)."""
    data = bytes(message or b"")
    if len(data) < HEADER_SIZE:
        return f"{len(data)} byte(s), shorter than the 5-byte header"
    n = data[3] | (data[4] << 8)
    return (f"magic 0x{data[0]:02X} version {data[1]} type {data[2]} len {n} in a {len(data)}-byte message"
            + (" -- a different wire version (mixed engine builds never sync)" if data[0] == WIRE_MAGIC
               and data[1] != WIRE_VERSION else ""))


def build_pos_payload(field: int, anim: int = 0, model: int = 0, mesh_vis: int = 0, loco: int = 0,
                      pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0, 1.0)) -> bytes:
    """NetSyncWire.BuildPosPayload (37 bytes; ``(UInt16)field`` truncates as the C# cast does)."""
    return _POS.pack(int(field) & 0xFFFF, int(anim) & 0xFFFF, int(model) & 0xFFFF, int(mesh_vis) & 0xFFFF,
                     int(loco) & 0xFF, *(float(v) for v in pos), *(float(v) for v in rot))


def parse_pos_payload(payload) -> dict | None:
    """NetSyncWire.TryParsePosPayload: None under 37 bytes (bytes past the 37th are ignored, as the engine ignores them)."""
    data = bytes(payload or b"")
    if len(data) < POS_LEN:
        return None
    f, anim, model, mesh, loco, px, py, pz, rx, ry, rz, rw = _POS.unpack_from(data)
    return {"field": f, "anim": anim, "model": model, "mesh_vis": mesh, "loco": loco,
            "pos": (px, py, pz), "rot": (rx, ry, rz, rw)}


def build_pos_frame(field: int, **kw) -> bytes:
    return build_frame(TYPE_POS, build_pos_payload(field, **kw))


def parse_battle_head(payload) -> dict | None:
    """ParseView's head of a type-1 payload (the 12 bytes before the unit records): None when shorter."""
    data = bytes(payload or b"")
    if len(data) < BATTLE_HEAD_LEN:
        return None
    seq, map_no, slots, pat, start, flags, nonce, song, units = _BATTLE_HEAD.unpack_from(data)
    return {"seq": seq, "map": map_no, "guest_slots": slots, "pattern": pat, "start_type": start, "flags": flags,
            "nonce": nonce, "song": song, "units": units}


def decode_control_raw(payload) -> dict | None:
    """A type-3 control payload as the GUEST wrote it (NetSyncBattle.BuildControl), with no host nonce gate:
    ``{menu, fmt, trailer, nonce, boot}`` -- ``trailer`` = an s114 fmt-1 report ``[0][menu][1][nonce][boot]``; a 2-byte
    frame is a pre-R3 guest's. None = what ParseControl refuses (short, or byte 0 not 0)."""
    data = bytes(payload or b"")
    if len(data) < BW.CONTROL_LEN_V1 or data[0] != 0:
        return None
    out = {"menu": data[1], "fmt": data[2] if len(data) >= 3 else None, "trailer": False, "nonce": None, "boot": None}
    if len(data) >= BW.CONTROL_LEN_TRAILER and data[2] == BW.CTL_FMT1:
        out.update(trailer=True, nonce=data[3], boot=data[4])
    return out


def control_text(ctl: dict) -> str:
    """One decoded control frame, for the log: ``menu 2 (root) | fmt-1 report: nonce 3 boot LIVE``."""
    text = f"menu {ctl['menu']} ({BW.ctl_name(ctl['menu'])})"
    if ctl["trailer"]:
        return text + f" | fmt-1 report: nonce {ctl['nonce']} boot {str(BW.boot_name(ctl['boot'])).upper()}"
    if ctl["fmt"] is None:
        return text + " | no trailer (a pre-R3 guest's 2-byte frame)"
    return text + f" | no fmt-1 trailer (byte 2 = {ctl['fmt']}: an unknown or short record)"


def describe_frame(wtype: int, payload) -> str:
    """A short human reading of one NetSyncWire frame (``dump``, the logs). [ff9mapkit netsync s133] A type-6 action
    record is decoded through battlewire (audit D5): an s133+ host's START / END / id-carrying impact, a pre-s133 host's
    46-byte impact, a stat tick."""
    name = TYPE_NAMES.get(wtype, f"type{wtype}")
    if wtype == TYPE_POS:
        p = parse_pos_payload(payload)
        if p:
            x, y, z = p["pos"]
            return f"{name} field {p['field']} model {p['model']} anim {p['anim']} at ({x:.0f}, {y:.0f}, {z:.0f})"
    elif wtype == TYPE_BATTLE:
        h = parse_battle_head(payload)
        if h:
            return (f"{name} seq {h['seq']} map {h['map']} nonce {h['nonce']} units {h['units']} "
                    f"flags 0x{h['flags']:02X} slots {h['guest_slots']}")
    elif wtype == TYPE_CONTROL:
        c = decode_control_raw(payload)
        if c:
            return f"{name} {control_text(c)}"
    elif wtype == TYPE_COMMAND:
        c = BW.decode_command(payload)
        if c:
            return (f"{name} slot {c['slot']} action {c['action']} menu {c['menu']} id {c['id']} "
                    f"mask 0x{c['mask']:04X} cursor {c['cursor']}")
    elif wtype == TYPE_ACTION:
        return f"{name} {BW.action_text(payload)}"            # [ff9mapkit netsync s133]
    elif wtype == TYPE_STATE:
        # [ff9mapkit netsync s144] the host's section 7 flags byte, by name (b6 world / b7 title are s144's; an older host never
        # sets them, and a frame without section 7 -- a guest's, a pre-ring host's -- reads as before)
        view = BW.parse_dialog_section(BW.old_try_read_section(payload, BW.SECTION_DIALOG) or b"")
        if view is not None:
            names = ",".join(BW.host_flag_names(view["flags"])) or "none"
            return f"{name} {len(bytes(payload or b''))} B; section 7 flags 0x{view['flags']:02X} ({names})"
    return f"{name} {len(bytes(payload or b''))} B"


def tape_actions(records) -> dict:
    """[ff9mapkit netsync s133] The HOST's type-6 action records on a tape, counted through battlewire's codec
    (battlewire.act_tape_summary: ``starts``, ``ends``, ``impacts`` -- ``ext`` of them with the id extension --, ``stat``,
    ``bad``): an s133+ host's tape carries STARTs; a pre-s133 host's, 46-byte impacts only."""
    return BW.act_tape_summary([p for _t, p in tape_action_frames(records)])


def tape_action_frames(records) -> list:
    """[ff9mapkit netsync s134] The HOST's type-6 action records on a tape, in order -> ``[(t, payload bytes)]``: what a
    replay-host sends the guest's action lane (the s134 tape leg judges what the guest replayed against them)."""
    out = []
    for r in records:
        if r.dir != DIR_HOST:
            continue
        got = parse_frame(r.payload)
        if got is not None and got[0] == TYPE_ACTION:
            out.append((r.t, bytes(got[1])))
    return out


# ======================================================================================== WebSocket framing (RFC 6455)
OP_CONT, OP_TEXT, OP_BINARY, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA
CLEAN_CLOSE_CODES = (1000, 1001)                           # gorilla's IsCloseError(Normal, GoingAway): a deliberate quit


class WsProtocolError(Exception):
    """A frame header claimed an implausible length -- the stream cannot be resynced."""


class WsClosed(Exception):
    """The connection ended: a close frame (``code``; ``clean`` for 1000/1001) or EOF/reset (``code`` None)."""

    def __init__(self, why: str, code: int | None = None):
        super().__init__(why)
        self.code = code
        self.clean = code in CLEAN_CLOSE_CODES


def ws_encode(payload, opcode: int = OP_BINARY, mask_key: bytes | None = None, fin: bool = True) -> bytes:
    """One WS frame. ``mask_key`` (4 bytes) = a CLIENT frame, masked (NetSyncRelay.WriteBinaryFrame's shape); None = a
    server frame, unmasked (what the relay/bridge hand the game). 7-, 16- and 64-bit lengths."""
    data = bytes(payload or b"")
    n = len(data)
    out = bytearray([(0x80 if fin else 0) | (opcode & 0x0F)])
    mbit = 0x80 if mask_key is not None else 0
    if n < 126:
        out.append(mbit | n)
    elif n < 65536:
        out.append(mbit | 126)
        out += n.to_bytes(2, "big")
    else:
        out.append(mbit | 127)
        out += n.to_bytes(8, "big")
    if mask_key is not None:
        key = bytes(mask_key)
        if len(key) != 4:
            raise ValueError("a WS mask key is 4 bytes")
        out += key
        out += _xor(data, key)
    else:
        out += data
    return bytes(out)


def _xor(data: bytes, key: bytes) -> bytes:
    if not data:
        return b""
    reps = key * (len(data) // 4 + 1)
    return (int.from_bytes(data, "little") ^ int.from_bytes(reps[:len(data)], "little")).to_bytes(len(data), "little")


def ws_decode(buf, max_payload: int = NB.WS_MAX_FRAME) -> tuple | None:
    """Parse ONE frame off the front of ``buf``: ``(fin, opcode, payload_unmasked, consumed)``, or None while it is
    incomplete. Raises WsProtocolError on a length past ``max_payload`` (the bridge's cap)."""
    if len(buf) < 2:
        return None
    b0, b1 = buf[0], buf[1]
    n = b1 & 0x7F
    pos = 2
    if n == 126:
        if len(buf) < 4:
            return None
        n = int.from_bytes(bytes(buf[2:4]), "big")
        pos = 4
    elif n == 127:
        if len(buf) < 10:
            return None
        n = int.from_bytes(bytes(buf[2:10]), "big")
        pos = 10
    if n > max_payload:
        raise WsProtocolError(f"ws frame payload {n} exceeds the {max_payload}-byte cap")
    key = None
    if b1 & 0x80:
        if len(buf) < pos + 4:
            return None
        key = bytes(buf[pos:pos + 4])
        pos += 4
    if len(buf) < pos + n:
        return None
    payload = bytes(buf[pos:pos + n])
    if key is not None:
        payload = _xor(payload, key)
    return bool(b0 & 0x80), b0 & 0x0F, payload, pos + n


def _readable(sock, timeout: float) -> bool:
    """select() for one socket, aware of an SSL socket's already-decrypted bytes (select cannot see those)."""
    pending = getattr(sock, "pending", None)
    if pending is not None and pending():
        return True
    r, _, _ = select.select([sock], [], [], max(0.0, timeout))
    return bool(r)


class WsConn:
    """One WebSocket connection, either end. ``client`` = this side masks its frames (it dialled). ``send`` is thread-safe
    (one lock: data and pongs never interleave); ``recv`` is for ONE reader thread. The socket keeps a fixed timeout
    that bounds every send (the relay's 5 s write deadline); reads poll with select, so a reader can watch a stop flag."""

    def __init__(self, sock, *, client: bool, name: str = "peer", send_timeout: float = 5.0):
        self.sock = sock
        self.client = client
        self.name = name
        self._buf = bytearray()
        self._frag = None                                  # (opcode, bytearray) while a fragmented message arrives
        self._send_lock = threading.Lock()
        self._closed = False
        try:
            sock.settimeout(send_timeout)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass

    def send(self, payload, opcode: int = OP_BINARY) -> None:
        frame = ws_encode(payload, opcode, os.urandom(4) if self.client else None)
        with self._send_lock:
            self.sock.sendall(frame)

    def recv(self, poll: float | None = None) -> tuple | None:
        """The next DATA message ``(opcode, payload)``; None once ``poll`` seconds pass without a whole one (None = wait
        forever). Pings are answered, pongs dropped, fragments reassembled; a close frame or EOF raises WsClosed."""
        deadline = None if poll is None else time.monotonic() + poll
        while True:
            got = ws_decode(self._buf)
            if got is not None:
                fin, op, payload, used = got
                del self._buf[:used]
                msg = self._message(fin, op, payload)
                if msg is not None:
                    return msg
                continue
            wait = 0.5 if deadline is None else deadline - time.monotonic()
            if deadline is not None and wait <= 0:
                return None
            try:
                if not _readable(self.sock, min(wait, 0.5)):
                    continue
                chunk = self.sock.recv(65536)
            except (OSError, ValueError) as err:          # ValueError: select on a socket closed under us
                raise WsClosed("closed by this tool" if self._closed else f"read failed ({err})") from None
            if not chunk:
                raise WsClosed("EOF" + (" mid-frame" if self._buf else ""))
            self._buf += chunk

    def _message(self, fin: bool, op: int, payload: bytes):
        if op == OP_PING:
            self._quiet_send(payload[:125], OP_PONG)
            return None
        if op == OP_PONG:
            return None
        if op == OP_CLOSE:
            code = int.from_bytes(payload[:2], "big") if len(payload) >= 2 else None
            reason = payload[2:].decode("utf-8", "replace") if len(payload) > 2 else ""
            self._quiet_send(payload[:2], OP_CLOSE)
            raise WsClosed(f"close frame (code {code}{', ' + repr(reason) if reason else ''})", code)
        if op == OP_CONT:
            if self._frag is None:
                return None                                # a stray continuation: nothing to append it to
            self._frag[1].extend(payload)
            if not fin:
                return None
            first, data = self._frag
            self._frag = None
            return first, bytes(data)
        if not fin:
            self._frag = (op, bytearray(payload))
            return None
        return op, payload

    def _quiet_send(self, payload, opcode):
        try:
            self.send(payload, opcode)
        except OSError:
            pass

    def close(self, code: int | None = None, reason: str = "") -> None:
        """Close the socket; with ``code``, a close frame first (best effort)."""
        if self._closed:
            return
        self._closed = True
        if code is not None:
            self._quiet_send(code.to_bytes(2, "big") + reason.encode("utf-8")[:120], OP_CLOSE)
        for step in (lambda: self.sock.shutdown(socket.SHUT_RDWR), self.sock.close):
            try:
                step()
            except OSError:
                pass


# ======================================================================================== the upgrade (both ends)
BENCH_HEADER = "X-Coop-Peer: bench (NOT the production netsync bridge)"


class HandshakeRefused(Exception):
    """The request was not a WebSocket upgrade this mode serves (already answered 400 and closed)."""


def session_path(code: str, role: str) -> str:
    """NetSyncRelay's request path: ``/sess/<EscapeDataString(code)>?role=<role>``."""
    return "/sess/" + quote(code.strip(), safe="") + "?role=" + role


def parse_session_path(path: str) -> tuple:
    """``/sess/<code>?role=<role>`` -> ``(code, role)``; ``("", "")`` parts when absent. Codes are compared upper-cased
    by the relay (main.go); returned here as sent."""
    parts = urlsplit(path)
    code = ""
    if parts.path.startswith("/sess/"):
        code = unquote(parts.path[len("/sess/"):].split("/", 1)[0])
    role = parse_qs(parts.query).get("role", [""])[0]
    return code, role


def _refuse(sock, why: str) -> None:
    body = (why + "\n").encode("utf-8", "replace")
    try:
        sock.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Type: text/plain\r\n"
                     + f"Content-Length: {len(body)}\r\n{BENCH_HEADER}\r\n\r\n".encode("ascii") + body)
    except OSError:
        pass
    try:
        sock.close()
    except OSError:
        pass


def accept_ws(sock, *, want_role: str | None = None, mode: str = "coop-peer") -> tuple:
    """The SERVER side of the upgrade (what the bridge's handle_client does, minus the upstream): read the request with
    the bridge's own ``read_http_headers``, validate it, answer 101 with ``ws_accept``. Returns ``(WsConn, code, role)``.
    A request this mode does not serve -- not an upgrade, no session path, a role other than ``want_role`` -- is
    answered 400 (the game logs "relay refused upgrade: HTTP/1.1 400") and raises HandshakeRefused."""
    try:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass
    req = NB.read_http_headers(sock)
    lines = req.split("\r\n")
    try:
        method, path, version = lines[0].split(" ", 2)
    except ValueError:
        _refuse(sock, "malformed request line")
        raise HandshakeRefused(f"malformed request line {lines[0]!r}") from None
    if not all(NB._REQ_TOKEN_RE.match(t) for t in (method, path, version)):
        _refuse(sock, "control bytes in the request line")
        raise HandshakeRefused(f"control bytes in the request line {lines[0]!r}")
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    key = headers.get("sec-websocket-key")
    if method != "GET" or "websocket" not in headers.get("upgrade", "").lower() or not key:
        _refuse(sock, "not a WebSocket upgrade")
        raise HandshakeRefused(f"not a WebSocket upgrade: {lines[0]!r}")
    code, role = parse_session_path(path)
    if not code or role not in ("host", "guest"):
        _refuse(sock, "expected /sess/<code>?role=host|guest")
        raise HandshakeRefused(f"no session code/role in {path!r}")
    if want_role is not None and role != want_role:
        other = {"host": "serve-guest", "guest": "replay-host"}[role]
        why = (f"this is coop_peer {mode}: it serves a role={want_role} game; a role={role} game wants `{other}`")
        _refuse(sock, why)
        raise HandshakeRefused(f"refused a role={role} game ({why})")
    sock.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                  f"Sec-WebSocket-Accept: {NB.ws_accept(key)}\r\n{BENCH_HEADER}\r\n\r\n").encode("ascii"))
    return WsConn(sock, client=False, name=f"{role} game"), code, role


def dial_ws(url: str, path: str, *, insecure: bool = False, timeout: float = 10.0, name: str = "relay") -> WsConn:
    """The CLIENT side: the production bridge's own ``open_upstream`` (TCP, optional TLS, its handshake + accept check)."""
    return WsConn(NB.open_upstream(url, path, insecure, connect_timeout=timeout), client=True, name=name)


# ======================================================================================== the tape
TAPE_MAGIC = b"F9TAPE01"
TAPE_FORMAT = 1
DIR_HOST, DIR_GUEST, DIR_NOTE = 0, 1, 2
DIR_NAMES = {DIR_HOST: "host", DIR_GUEST: "guest", DIR_NOTE: "note"}
_REC = struct.Struct("<dBI")
Record = collections.namedtuple("Record", "t dir payload")


class TapeError(Exception):
    """Not a coop_peer tape (bad magic or header)."""


class TapeWriter:
    """Append-only tape writer, shared by a session's threads (one lock). Flushed every ``flush_every`` seconds and on
    close, so a killed run loses at most that much (``read_tape`` reports the torn tail)."""

    def __init__(self, path, *, mode: str, clock=time.monotonic, extra: dict | None = None, flush_every: float = 0.5):
        self.path = Path(path)
        self._clock = clock
        self._lock = threading.Lock()
        self._flush_every = flush_every
        header = {"tool": "coop_peer", "format": TAPE_FORMAT, "wire": WIRE_VERSION, "mode": mode,
                  "started": datetime.datetime.now().isoformat(timespec="milliseconds"),
                  "dirs": {str(k): v for k, v in DIR_NAMES.items()}}
        header.update(extra or {})
        blob = json.dumps(header, sort_keys=True).encode("utf-8")
        self._f = open(self.path, "wb")
        self._f.write(TAPE_MAGIC + struct.pack("<I", len(blob)) + blob)
        self._t0 = clock()
        self._last_flush = self._t0
        self.records = 0
        self.bytes = 0

    def now(self) -> float:
        return self._clock() - self._t0

    def write(self, direction: int, payload, t: float | None = None) -> float:
        data = bytes(payload or b"")
        with self._lock:
            if self._f is None:
                return 0.0
            now = self._clock()
            stamp = (now - self._t0) if t is None else t
            self._f.write(_REC.pack(stamp, direction, len(data)) + data)
            self.records += 1
            self.bytes += _REC.size + len(data)
            if now - self._last_flush >= self._flush_every:
                self._f.flush()
                self._last_flush = now
            return stamp

    def note(self, text: str) -> float:
        """A note record, flushed at once (notes mark connection edges: a killed run keeps everything up to them)."""
        stamp = self.write(DIR_NOTE, text.encode("utf-8"))
        with self._lock:
            if self._f is not None:
                self._f.flush()
                self._last_flush = self._clock()
        return stamp

    def close(self) -> None:
        with self._lock:
            if self._f is not None:
                self._f.close()
                self._f = None


def read_tape(path) -> tuple:
    """``(header, [Record...], torn)``: ``torn`` = the bytes of a partial last record (a run killed mid-write) -- the whole
    records before it are returned. Raises TapeError when the file is not a tape."""
    data = Path(path).read_bytes()
    if not data.startswith(TAPE_MAGIC) or len(data) < len(TAPE_MAGIC) + 4:
        raise TapeError(f"{path}: not a coop_peer tape (no {TAPE_MAGIC!r} magic)")
    pos = len(TAPE_MAGIC)
    hlen = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    try:
        header = json.loads(data[pos:pos + hlen].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as err:
        raise TapeError(f"{path}: bad tape header ({err})") from None
    pos += hlen
    records = []
    while pos + _REC.size <= len(data):
        t, d, n = _REC.unpack_from(data, pos)
        if pos + _REC.size + n > len(data):
            break
        records.append(Record(t, d, data[pos + _REC.size:pos + _REC.size + n]))
        pos += _REC.size + n
    return header, records, len(data) - pos


def host_frames(records) -> list:
    """The dir-0 records that parse as v14 frames, as ``(record, type, payload)`` (what a replay sends)."""
    out = []
    for r in records:
        if r.dir == DIR_HOST:
            got = parse_frame(r.payload)
            if got is not None:
                out.append((r, got[0], got[1]))
    return out


def tape_battles(records, gap: float = STALE_S) -> list:
    """The tape's host battles: a run of host type-1 frames on ONE nonce with no gap over ``gap`` seconds (the lane's
    staleness window -- a guest reads a longer gap as the battle over). ``[{n, nonce, map, start, end, frames}]``."""
    battles = []
    cur = None
    for rec, wtype, payload in host_frames(records):
        if wtype != TYPE_BATTLE:
            continue
        head = parse_battle_head(payload)
        if head is None:
            continue
        if cur is None or head["nonce"] != cur["nonce"] or rec.t - cur["end"] > gap:
            cur = {"n": len(battles) + 1, "nonce": head["nonce"], "map": head["map"], "start": rec.t, "end": rec.t,
                   "frames": 0, "seq_first": head["seq"], "seq_last": head["seq"]}
            battles.append(cur)
        cur["end"] = rec.t
        cur["frames"] += 1
        cur["seq_last"] = head["seq"]
    return battles


def battle_unit_flags(payload) -> list | None:
    """[ff9mapkit netsync s143] ParseView's unit records of a type-1 payload, as ``[(index, player, ready)]`` (at most 8,
    as the reader stops; a record that overruns the frame ends the list). None under the head."""
    head = parse_battle_head(payload)
    if head is None:
        return None
    data, p, out = bytes(payload), BATTLE_HEAD_LEN, []
    for _ in range(min(head["units"], 8)):
        if p + 23 > len(data):
            break
        info, n = data[p + 1], data[p + 22]
        if p + 24 + n > len(data):
            break
        out.append((data[p], bool(info & 1), bool(info & 4)))
        p += 24 + n
    return out


def tape_offers(records) -> list:
    """[ff9mapkit netsync s143] THE HOST'S OFFER on a tape: per host battle (:func:`tape_battles`), the type-1 header's guest
    mask (the byte every guest-side ownership decision reads -- an s143 host's leader-guarded EffectiveGuestSlots) on every
    frame from the FIRST one with a player Ready bit on (the command phase: the battle's units are organized, the guard has
    latched). ``[{n, nonce, map, ready_t, offers: [mask, ...]}]`` (``ready_t`` None: no Ready frame)."""
    out = []
    for b in tape_battles(records):
        row = {"n": b["n"], "nonce": b["nonce"], "map": b["map"], "ready_t": None, "offers": []}
        for rec, wtype, payload in host_frames(records):
            if wtype != TYPE_BATTLE or not b["start"] <= rec.t <= b["end"]:
                continue
            head = parse_battle_head(payload)
            if head is None or head["nonce"] != b["nonce"]:
                continue
            if row["ready_t"] is None:
                units = battle_unit_flags(payload) or []
                if not any(player and ready for _i, player, ready in units):
                    continue
                row["ready_t"] = rec.t
            row["offers"].append(head["guest_slots"])
        out.append(row)
    return out


def tape_offer_lines(path, want: int) -> tuple:
    """(ok, lines) for ``offer``: every battle's header offers ``want`` on EVERY frame from its first Ready one on (and has
    such a frame)."""
    _header, records, torn = read_tape(path)
    rows = tape_offers(records)
    lines = [f"{path}: {len(rows)} host battle(s); want the offer 0x{int(want) & 0x0F:X} from each battle's first Ready "
             f"frame on" + (f" (torn tail {torn} B)" if torn else "")]
    ok = bool(rows)
    for r in rows:
        seen = sorted(set(r["offers"]))
        good = r["ready_t"] is not None and seen == [int(want) & 0x0F]
        ok = ok and good
        lines.append(f"  battle{r['n']} nonce {r['nonce']} map {r['map']}: "
                     + (f"no player Ready frame (the host never reached its command phase)" if r["ready_t"] is None else
                        f"{len(r['offers'])} frame(s) from tape {r['ready_t']:.2f} s offer {[f'0x{m:X}' for m in seen]}")
                     + ("" if good else "  <-- NOT the want"))
    if not rows:
        lines.append("  no host battle (type-1 run) on the tape")
    return ok, lines


def tape_fields(records) -> list:
    """The host's field edges on the tape: ``[(t, field)]`` at each change of its type-0 field."""
    out = []
    last = None
    for rec, wtype, payload in host_frames(records):
        if wtype == TYPE_POS:
            p = parse_pos_payload(payload)
            if p and p["field"] != last:
                last = p["field"]
                out.append((rec.t, last))
    return out


_TIME_SPEC = re.compile(r"\s*(?:(?P<anchor>battle(?P<n>\d+)?(?P<end>\.end)?)\s*(?P<off>[+-]\s*\d+(?:\.\d+)?)?"
                        r"|(?P<abs>\d+(?:\.\d+)?))\s*\Z")


def resolve_time(spec, battles) -> float:
    """A time spec -> tape seconds: ``45.5``, ``battle+10``, ``battle2-1``, ``battle.end+0.5`` (see the module doc)."""
    if isinstance(spec, (int, float)):
        return float(spec)
    m = _TIME_SPEC.match(str(spec))
    if not m:
        raise ValueError(f"bad time {spec!r}: tape seconds, or battle[N][.end][+-S]")
    if m.group("abs") is not None:
        return float(m.group("abs"))
    n = int(m.group("n") or 1)
    if n < 1 or n > len(battles):
        raise ValueError(f"{spec!r}: the tape has {len(battles)} battle(s)")
    b = battles[n - 1]
    base = b["end"] if m.group("end") else b["start"]
    off = float(m.group("off").replace(" ", "")) if m.group("off") else 0.0
    return base + off


# ======================================================================================== the log
class Log:
    """``[coop-peer HH:MM:SS.mmm] msg`` to stdout (or ``stream``), teed to ``path``; thread-safe. Never ``[bridge]``."""

    def __init__(self, path=None, stream=None):
        self._lock = threading.Lock()
        self._stream = stream if stream is not None else sys.stdout
        self._file = open(path, "a", encoding="utf-8") if path else None

    def __call__(self, msg: str) -> None:
        stamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[coop-peer {stamp}] {msg}"
        with self._lock:
            try:
                print(line, file=self._stream, flush=True)
            except (OSError, ValueError, UnicodeEncodeError):
                pass
            if self._file is not None:
                try:
                    self._file.write(line + "\n")
                    self._file.flush()
                except (OSError, ValueError) as err:   # a full disk / gone file: stop teeing, never raise into a
                    f, self._file = self._file, None     # reader or pump thread (it would end the session)
                    try:
                        f.close()
                    except (OSError, ValueError):
                        pass
                    try:
                        print(f"[coop-peer {stamp}] log file disabled ({err}) -- stdout only from here",
                              file=self._stream, flush=True)
                    except (OSError, ValueError, UnicodeEncodeError):
                        pass

    def close(self) -> None:
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None


def banner(log: Log, mode: str, lines) -> None:
    bar = "=" * 78
    log(bar)
    log(f" coop_peer {mode} -- SOLO BENCH PEER. THIS IS NOT THE PRODUCTION NETSYNC BRIDGE.")
    for line in lines:
        log(" " + line)
    log(bar)


# ======================================================================================== the fake GUEST
REPORTS = {"off": None, "legacy": "legacy", "none": BW.BOOT_NONE, "booting": BW.BOOT_BOOTING, "live": BW.BOOT_LIVE,
           "declined": BW.BOOT_DECLINED, "busy": BW.BOOT_BUSY}
MENU_NAMES = {v: k for k, v in BW.CTL_NAMES.items()}


class GuestModel:
    """What the fake guest knows of the host and what it answers, as pure state (the clock is passed in):

    * type 0 -- every tick, ``[field][anim][model][meshVis][loco][pos][rot]``: ``field`` None mirrors the host's own
      field (0 while it fights, the 65535 sentinel until its first frame -- what a following guest's diorama and a
      pre-field engine send), with its model/anim/loco and its position plus ``offset``; an int pins a field.
    * type 3 -- only while the host's battle lane is LIVE (its seq advanced within 2 s: NetSyncBattle.Pump's freshness
      rule, keyed on the seq, not on receipt) -- the guest Pump's ``live && !inBattle`` branch. ``report`` None sends
      none; ``"legacy"`` the pre-R3 2-byte ``[0][menu]``; a boot state the s114 ``[0][menu][1][nonce][boot]`` naming
      the host's CURRENT nonce. ``live_after`` > 0 reports BOOTING for that long after a nonce first appears (a diorama
      booting), then ``report``."""

    def __init__(self, *, field: int | None = None, offset=(0.0, 0.0, 0.0), report=None, menu: int = 0,
                 live_after: float = 0.0):
        self._lock = threading.Lock()
        self.field = field
        self.offset = tuple(float(v) for v in offset)
        self.report = report
        self.menu = int(menu) & 0xFF
        self.live_after = float(live_after)
        self.host_pos = None
        self.host_pos_t = None
        self.view = None
        self.view_t = None                                 # when the host's battle seq last ADVANCED
        self.state_t = None
        self._nonce_first = {}
        self._lane_live = False
        self._pos_live = False
        self._state_live = False
        self.actions_this_battle = 0
        self.last_control = None

    def on_host_frame(self, wtype: int, payload: bytes, now: float) -> list:
        """Feed one host frame; returns the log events it caused (edges only, never per frame)."""
        ev = []
        with self._lock:
            if wtype == TYPE_POS:
                p = parse_pos_payload(payload)
                if p is not None:
                    was = self.host_pos["field"] if self.host_pos else None
                    if p["field"] != was:
                        ev.append(f"host pos: field {p['field']} (was {_field_text(was)})")
                    self.host_pos, self.host_pos_t = p, now
                    if not self._pos_live:
                        self._pos_live = True
                        if was is not None:
                            ev.append(f"host pos lane back (field {p['field']})")
            elif wtype == TYPE_BATTLE:
                h = parse_battle_head(payload)
                if h is not None and (self.view is None or h["seq"] != self.view["seq"]):
                    new_nonce = self.view is None or h["nonce"] != self.view["nonce"] or not self._lane_live
                    self.view, self.view_t = h, now
                    self._nonce_first.setdefault(h["nonce"], now)
                    if new_nonce:
                        self._lane_live = True
                        self.actions_this_battle = 0
                        ev.append(f"host battle lane UP: nonce {h['nonce']} map {h['map']} pattern {h['pattern']} "
                                  f"guest slots {h['guest_slots']} flags 0x{h['flags']:02X} song {h['song']}")
            elif wtype == TYPE_STATE:
                self.state_t = now
                if not self._state_live:
                    self._state_live = True
                    ev.append(f"host story-state lane (type 5) up, {len(payload)} B")
            elif wtype == TYPE_ACTION:
                self.actions_this_battle += 1
        return ev

    def tick(self, now: float) -> list:
        """The staleness edges at ``now`` (one event per lane going quiet)."""
        ev = []
        with self._lock:
            if self._lane_live and (self.view_t is None or now - self.view_t >= STALE_S):
                self._lane_live = False
                ev.append(f"host battle lane STALE: nonce {self.view['nonce']} seq {self.view['seq']} stopped advancing "
                          f"{STALE_S:.0f} s ago ({self.actions_this_battle} action frame(s) this battle) -- over, or "
                          "the host went silent")
            if self._pos_live and (self.host_pos_t is None or now - self.host_pos_t >= STALE_S):
                self._pos_live = False
                ev.append(f"host pos lane STALE: no type-0 for {STALE_S:.0f} s "
                          f"(last field {_field_text(self.host_pos['field'] if self.host_pos else None)})")
            if self._state_live and (self.state_t is None or now - self.state_t >= STALE_S):
                self._state_live = False
                ev.append("host story-state lane (type 5) stale")
        return ev

    def lane_live(self, now: float) -> bool:
        with self._lock:
            return self.view is not None and self.view_t is not None and now - self.view_t < STALE_S

    def pos_frame(self) -> bytes:
        with self._lock:
            hp = self.host_pos
            if self.field is not None:
                field = self.field
            else:
                field = hp["field"] if hp else FIELD_SENTINEL
            if hp is None:
                return build_pos_frame(field)
            x, y, z = hp["pos"]
            dx, dy, dz = self.offset
            return build_pos_frame(field, anim=hp["anim"], model=hp["model"], mesh_vis=hp["mesh_vis"],
                                   loco=hp["loco"], pos=(x + dx, y + dy, z + dz), rot=hp["rot"])

    def control_payload(self, now: float) -> bytes | None:
        if self.report is None or not self.lane_live(now):
            return None
        with self._lock:
            nonce = self.view["nonce"]
            if self.report == "legacy":
                return BW.encode_control(self.menu)
            boot = self.report
            first = self._nonce_first.get(nonce, now)
            if self.live_after > 0 and now - first < self.live_after:
                boot = BW.BOOT_BOOTING
            return BW.encode_control(self.menu, nonce, boot)

    def outgoing(self, now: float) -> list:
        """The NetSyncWire frames due this tick: the position slot, then (when declared) the control slot --
        NetSyncFrames.CollectOutgoing's order."""
        frames = [self.pos_frame()]
        ctl = self.control_payload(now)
        if ctl is not None:
            frames.append(build_frame(TYPE_CONTROL, ctl))
        return frames


def _field_text(field) -> str:
    if field is None:
        return "none"
    return {0: "0 (not on a field: battle/menu/load)", FIELD_SENTINEL: "65535 (sentinel: not on a field yet)"}.get(
        field, str(field))


class GuestSession:
    """One connection's fake GUEST: a reader thread feeds the host's frames to the model (and the tape); ``run`` sends the
    model's frames every ``tick`` seconds (the engine's 30 Hz WriteLoop) and a status line every ``status_every``."""

    def __init__(self, conn: WsConn, model: GuestModel, *, log: Log, tap: TapeWriter | None = None,
                 clock=time.monotonic, sleep=None, tick: float = TICK_S, status_every: float = 5.0):
        self.conn = conn
        self.model = model
        self.log = log
        self.tap = tap
        self._clock = clock
        self._stop = threading.Event()
        self._sleep = sleep if sleep is not None else self._stop.wait   # the default wakes at once on stop()
        self._tick = tick
        self._status_every = status_every
        self.why = None
        self._count_lock = threading.Lock()                # the reader adds keys while the status line copies
        self.rx = collections.Counter()
        self.tx = collections.Counter()
        self._foreign_logged = False
        self._last_ctl = None

    def stop(self, why: str) -> None:
        if self.why is None:
            self.why = why
        self._stop.set()

    def _reader(self) -> None:
        try:
            while not self._stop.is_set():
                msg = self.conn.recv(poll=0.25)
                if msg is None:
                    continue
                _, payload = msg
                if self.tap is not None:
                    self.tap.write(DIR_HOST, payload)
                got = parse_frame(payload)
                if got is None:
                    with self._count_lock:
                        self.rx["foreign"] += 1
                    if not self._foreign_logged:
                        self._foreign_logged = True
                        self.log(f"host sent a frame the engine would DROP: {frame_header_text(payload)} (logged once)")
                    continue
                wtype, body = got
                with self._count_lock:
                    self.rx[wtype] += 1
                for ev in self.model.on_host_frame(wtype, body, self._clock()):
                    self.log(ev)
        except WsClosed as err:
            self.stop(f"the {self.conn.name} hop closed ({err})")
        except WsProtocolError as err:
            self.stop(f"the {self.conn.name} hop sent a malformed WS frame ({err})")
        except Exception as err:                           # noqa: BLE001 -- a reader must never die silently
            self.stop(f"reader failed ({type(err).__name__}: {err})")

    def run(self) -> str:
        reader = threading.Thread(target=self._reader, name="coop-peer-guest-reader", daemon=True)
        reader.start()
        nxt = self._clock()
        last_status = nxt
        rx_mark, tx_mark = collections.Counter(), collections.Counter()
        try:
            while not self._stop.is_set():
                now = self._clock()
                for ev in self.model.tick(now):
                    self.log(ev)
                frames = self.model.outgoing(now)
                ctl = frames[1] if len(frames) > 1 else None
                if ctl != self._last_ctl:
                    self._last_ctl = ctl
                    if ctl is None:
                        self.log("fake guest: control lane shut (nothing to report)")
                    else:
                        self.log(f"fake guest now sends control: {control_text(decode_control_raw(ctl[HEADER_SIZE:]))}")
                send_err = None
                for frame in frames:
                    try:
                        self.conn.send(frame)
                    except OSError as err:
                        send_err = err
                        break
                    with self._count_lock:
                        self.tx[frame[2]] += 1
                    if self.tap is not None:
                        self.tap.write(DIR_GUEST, frame)
                if send_err is not None:
                    reader.join(1.0)                       # the reader usually knows WHY (a close frame, an EOF)
                    self.stop(f"send failed ({send_err})")
                    break
                if now - last_status >= self._status_every:
                    with self._count_lock:
                        rx_now, tx_now = collections.Counter(self.rx), collections.Counter(self.tx)
                    self.log(self._status(now, now - last_status, rx_now, rx_mark, tx_now, tx_mark))
                    last_status, rx_mark, tx_mark = now, rx_now, tx_now
                nxt += self._tick
                delay = nxt - self._clock()
                if delay < -0.5:                           # fell far behind (a stall): re-phase, never burst
                    nxt = self._clock()
                elif delay > 0:
                    self._sleep(delay)
        finally:
            self._stop.set()
            self.conn.close()
            reader.join(timeout=2.0)
        return self.why or "stopped"

    def _status(self, now, span, rx, rx_mark, tx, tx_mark) -> str:
        def rate(counter, mark, key):
            return (counter[key] - mark[key]) / span if span > 0 else 0.0
        m = self.model
        hp = m.host_pos["field"] if m.host_pos else None
        lane = "none"
        if m.view is not None:
            lane = (f"nonce {m.view['nonce']} seq {m.view['seq']} "
                    + ("LIVE" if m.lane_live(now) else "stale")
                    + f", {m.actions_this_battle} action(s)")
        rates = " ".join(f"{TYPE_NAMES[t]} {rate(rx, rx_mark, t):.0f}/s" for t in sorted(TYPE_NAMES)
                         if rx[t] - rx_mark[t])
        if rx["foreign"] - rx_mark["foreign"]:
            rates += f" NOT-v14 {rx['foreign'] - rx_mark['foreign']}"
        tap = f" | tap {self.tap.records} rec {self.tap.bytes / 1e6:.1f} MB" if self.tap is not None else ""
        return (f"status: host field {_field_text(hp)} | battle {lane} | rx {rates.strip() or 'nothing'} | "
                f"tx pos {rate(tx, tx_mark, TYPE_POS):.0f}/s ctl {rate(tx, tx_mark, TYPE_CONTROL):.0f}/s{tap}")


# ======================================================================================== the recorded HOST (replay)
class Replayer:
    """Replays host frames on their original timing against an injectable clock: frame ``t`` is due at
    ``wall0 + (t - start)``. A BLACKHOLE ``[at, at+for)`` drops every frame in it (the TCP stays open, nothing is sent,
    nothing is queued -- latest-state wire, as the decoupled bridge drops game->relay frames while its upstream is down)
    and resumes on the original timeline after it. ``stop_at`` ends the host there. ``send(payload) -> bool`` reports
    whether a guest connection took it (False = none attached: the frame is lost, counted)."""

    def __init__(self, frames, *, start: float, stop_at: float | None = None, blackholes=(), send, log,
                 clock=time.monotonic, sleep=time.sleep, on_sent=None, on_note=None, progress_every: float = 10.0,
                 lag_warn: float = 0.25):
        self.frames = [f for f in frames if f[0].t >= start and (stop_at is None or f[0].t < stop_at)]
        self.start = start
        self.stop_at = stop_at
        self.blackholes = sorted((float(a), float(a) + float(n)) for a, n in blackholes)
        self._send = send
        self._log = log
        self._clock = clock
        self._sleep = sleep
        self._on_sent = on_sent
        self._on_note = on_note
        self._progress_every = progress_every
        self._lag_warn = lag_warn
        self.sent = 0
        self.dropped = 0                                   # inside a blackhole
        self.unsent = 0                                    # no guest attached
        self.max_lag = 0.0
        self.tape_end = frames[-1][0].t if frames else start
        self._field = None
        self._nonce = None

    def in_blackhole(self, t: float) -> bool:
        return any(a <= t < b for a, b in self.blackholes)

    def _events(self) -> list:
        ev = []
        for a, b in self.blackholes:
            if b > self.start and (self.stop_at is None or a < self.stop_at):
                ev.append((max(a, self.start), 1, "bh-begin", (a, b)))
                ev.append((b, 0, "bh-end", (a, b)))
        if self.stop_at is not None:
            ev.append((self.stop_at, 3, "stop", None))
        ev.extend((f[0].t, 2, "frame", f) for f in self.frames)
        ev.sort(key=lambda e: (e[0], e[1]))
        return ev

    def _note(self, text: str) -> None:
        self._log(text)
        if self._on_note is not None:
            self._on_note(text)

    def _track(self, wtype, payload, t) -> None:
        if wtype == TYPE_POS:
            p = parse_pos_payload(payload)
            if p and p["field"] != self._field:
                self._log(f"tape {t:.2f}: host field {_field_text(self._field)} -> {_field_text(p['field'])}")
                self._field = p["field"]
        elif wtype == TYPE_BATTLE:
            h = parse_battle_head(payload)
            if h and h["nonce"] != self._nonce:
                self._nonce = h["nonce"]
                self._log(f"tape {t:.2f}: host battle nonce {h['nonce']} (map {h['map']}, pattern {h['pattern']}) "
                          "on the wire")

    def run(self, stop_event: threading.Event | None = None) -> dict:
        events = self._events()
        wall0 = self._clock()
        last_progress = wall0
        lag_logged = False
        self._log(f"REPLAY start: tape {self.start:.2f} s -> now; {len(self.frames)} host frame(s) up to tape "
                  f"{(self.stop_at if self.stop_at is not None else self.tape_end):.2f} s")
        for t, _, kind, item in events:
            due = wall0 + (t - self.start)
            while True:
                if stop_event is not None and stop_event.is_set():
                    return self.summary("stopped")
                wait = due - self._clock()
                if wait <= 0:
                    break
                self._sleep(min(wait, 0.2))
            lag = self._clock() - due
            if lag > self.max_lag:
                self.max_lag = lag
            if kind == "frame":
                rec, wtype, payload = item
                if self.in_blackhole(t):
                    self.dropped += 1
                    continue
                if lag > self._lag_warn and not lag_logged:
                    lag_logged = True
                    self._log(f"replay running {lag:.2f} s late at tape {t:.2f} (the guest is not reading fast "
                              "enough? frames go out back to back to catch up; logged once)")
                if self._send(rec.payload):
                    self.sent += 1
                    if self._on_sent is not None:
                        self._on_sent(rec, wtype, payload)
                else:
                    self.unsent += 1
                self._track(wtype, payload, t)
            elif kind == "bh-begin":
                a, b = item
                self._note(f"BLACKHOLE at tape {t:.2f} s: the link stays open and the host sends NOTHING for "
                           f"{b - t:.2f} s (a Wi-Fi cut behind the decoupled bridge)")
            elif kind == "bh-end":
                self._note(f"BLACKHOLE over at tape {t:.2f} s: host frames resume ({self.dropped} dropped so far)")
            elif kind == "stop":
                self._note(f"STOP-AT tape {t:.2f} s reached: the host sends nothing more")
                return self.summary("stop-at")
            now = self._clock()
            if now - last_progress >= self._progress_every:
                last_progress = now
                self._log(f"replay at tape {t:.2f} / {self.tape_end:.2f} s: sent {self.sent}, dropped {self.dropped}, "
                          f"unsent (no guest) {self.unsent}")
        return self.summary("tape end")

    def summary(self, why: str) -> dict:
        return {"why": why, "sent": self.sent, "dropped": self.dropped, "unsent": self.unsent,
                "max_lag": self.max_lag}


class GuestWatch:
    """The REAL guest's frames during a replay, decoded to edges for the log (never per frame): its position field, its
    control frame (menu byte + the s114 fmt-1 report, read against the host nonce currently on the wire), its commands,
    anything a guest should never send, and each lane going quiet."""

    def __init__(self):
        self._lock = threading.Lock()
        self.host_nonce = None
        self.pos_field = None
        self.pos_t = None
        self.ctl = None
        self.ctl_t = None
        self._pos_live = False
        self._ctl_live = False
        self.counts = collections.Counter()
        self._odd_types = set()
        self._foreign = False

    def note_host(self, wtype: int, payload: bytes) -> None:
        if wtype == TYPE_BATTLE:
            h = parse_battle_head(payload)
            if h is not None:
                with self._lock:
                    self.host_nonce = h["nonce"]

    def on_guest_message(self, message: bytes, now: float) -> list:
        ev = []
        got = parse_frame(message)
        with self._lock:
            if got is None:
                self.counts["foreign"] += 1
                if not self._foreign:
                    self._foreign = True
                    ev.append(f"guest sent a frame the engine would DROP: {frame_header_text(message)} (logged once)")
                return ev
            wtype, payload = got
            self.counts[wtype] += 1
            if wtype == TYPE_POS:
                p = parse_pos_payload(payload)
                if p is not None:
                    if p["field"] != self.pos_field or not self._pos_live:
                        ev.append(f"guest pos: field {_field_text(p['field'])} (was {_field_text(self.pos_field)})")
                    self.pos_field, self.pos_t, self._pos_live = p["field"], now, True
            elif wtype == TYPE_CONTROL:
                c = decode_control_raw(payload)
                key = None if c is None else (c["menu"], c["fmt"], c["nonce"], c["boot"])
                if key != self.ctl or not self._ctl_live:
                    ev.append("guest control: " + (f"{control_text(c)}{self._nonce_text(c)}" if c else
                                                   f"MALFORMED {BW.hex_bytes(payload)} (ParseControl refuses it)"))
                self.ctl, self.ctl_t, self._ctl_live = key, now, True
            elif wtype == TYPE_COMMAND:
                ev.append("guest COMMAND: " + describe_frame(wtype, payload)[len("command "):])
            elif wtype not in self._odd_types:
                self._odd_types.add(wtype)
                ev.append(f"guest sent a type-{wtype} ({TYPE_NAMES.get(wtype, '?')}) frame, {len(payload)} B -- "
                          "not a lane a guest feeds (logged once per type)")
        return ev

    def _nonce_text(self, c: dict) -> str:
        if not c["trailer"]:
            return ""
        if self.host_nonce is None:
            return " -- no host battle on the wire yet"
        return (f" -- names THIS battle (host nonce {self.host_nonce})" if c["nonce"] == self.host_nonce
                else f" -- names ANOTHER battle (host nonce {self.host_nonce})")

    def tick(self, now: float) -> list:
        ev = []
        with self._lock:
            if self._pos_live and now - self.pos_t >= STALE_S:
                self._pos_live = False
                ev.append(f"guest pos lane STALE: no type-0 for {STALE_S:.0f} s (last field "
                          f"{_field_text(self.pos_field)})")
            if self._ctl_live and now - self.ctl_t >= STALE_S:
                self._ctl_live = False
                ev.append(f"guest control lane SHUT: no type-3 for {STALE_S:.0f} s")
        return ev

    def summary(self) -> str:
        with self._lock:
            parts = [f"{TYPE_NAMES.get(k, k)} {v}" for k, v in sorted(self.counts.items(), key=lambda kv: str(kv[0]))]
        return "guest sent: " + (", ".join(parts) if parts else "nothing")


class PeerPort:
    """The connection currently attached to the game (or relay): swapped on reconnect; ``send`` drops when none."""

    def __init__(self):
        self._lock = threading.Lock()
        self.conn = None

    def attach(self, conn: WsConn):
        with self._lock:
            old, self.conn = self.conn, conn
        if old is not None:
            old.close()
        return old

    def detach(self, conn: WsConn) -> None:
        with self._lock:
            if self.conn is conn:
                self.conn = None

    def send(self, payload: bytes) -> bool:
        with self._lock:
            conn = self.conn
        if conn is None:
            return False
        try:
            conn.send(payload)
            return True
        except OSError:
            self.detach(conn)
            conn.close()
            return False

    def close(self, code: int | None = None) -> None:
        with self._lock:
            conn, self.conn = self.conn, None
        if conn is not None:
            conn.close(code)


# ======================================================================================== the local RELAY
class _RelaySession:
    def __init__(self, code: str, now: float):
        self.code = code
        self.created = now
        self.lock = threading.Lock()
        self.legs = {"host": None, "guest": None}
        self.drops = {"host": None, "guest": None}         # when a paired leg was parked (drives the rejoin grace)
        self.ever_paired = False
        self.paired = threading.Event()
        self.closed = threading.Event()
        self.forwarded = collections.Counter()


class LocalRelay:
    """A minimal relay after studies/battle-coop/relay/main.go v2: the first arrival waits (unread) for its partner up to
    ``pair_wait``; once paired each leg's messages go to whoever holds the partner slot (dropped while it is parked); an
    ABNORMAL drop parks the slot for ``rejoin_grace`` (a same-role rejoin resumes, a stale occupant is replaced); a CLEAN
    close (1000/1001) tears the whole session down; ``idle`` seconds of silence on a leg is death. Codes compare
    upper-cased. ``handle`` serves one connection and blocks (the Listener's per-connection thread)."""

    def __init__(self, *, log: Log, tap: TapeWriter | None = None, pair_wait: float = 60.0,
                 rejoin_grace: float = 60.0, idle: float = 90.0, clock=time.monotonic):
        self.log = log
        self.tap = tap
        self.pair_wait = pair_wait
        self.rejoin_grace = rejoin_grace
        self.idle = idle
        self._clock = clock
        self._lock = threading.Lock()
        self.sessions = {}

    def _register(self, code: str, role: str, conn: WsConn) -> tuple:
        with self._lock:
            sess = self.sessions.get(code)
            if sess is None:
                sess = self.sessions[code] = _RelaySession(code, self._clock())
        with sess.lock:
            rejoined = sess.ever_paired
            old = sess.legs[role]
            sess.legs[role] = conn
            sess.drops[role] = None
            if sess.legs["host"] is not None and sess.legs["guest"] is not None and not sess.ever_paired:
                sess.ever_paired = True
                sess.paired.set()
                if self.tap is not None:
                    self.tap.note(f"relay paired session {code}")
        if old is not None:
            old.close()
        return sess, rejoined, old is not None

    def handle(self, sock, addr=None) -> None:
        try:
            conn, code, role = accept_ws(sock, mode="relay")
        except HandshakeRefused as err:
            self.log(f"relay: {err}")
            return
        except Exception as err:                           # noqa: BLE001
            self.log(f"relay: handshake failed ({err})")
            try:
                sock.close()
            except OSError:
                pass
            return
        code = code.upper()
        sess, rejoined, replaced = self._register(code, role, conn)
        self.log(f"relay session {code}: {role} " + ("reconnected (replacing a stale connection)" if replaced
                                                     else "rejoined" if rejoined else "joined"))
        deadline = self._clock() + self.pair_wait
        while not sess.paired.is_set():
            if sess.closed.is_set():
                conn.close()
                return
            if self._clock() >= deadline:
                with sess.lock:
                    made = sess.ever_paired
                if not made:
                    self.log(f"relay session {code}: {role} timed out waiting for its partner")
                    self._teardown(sess)
                    return
            sess.paired.wait(0.1)
        if sess.closed.is_set():
            conn.close()
            return
        if not rejoined:
            self.log(f"relay session {code}: {role} paired -- forwarding")
        why, clean = self._pump(sess, role, conn)
        self.log(f"relay session {code}: {role} pump ended ({why})")
        if clean:
            self.log(f"relay session {code}: {role} quit cleanly -- closing the session")
            self._teardown(sess)
            return
        self._park(sess, role, conn)

    def _pump(self, sess: _RelaySession, role: str, conn: WsConn) -> tuple:
        other = "guest" if role == "host" else "host"
        direction = DIR_HOST if role == "host" else DIR_GUEST
        last = self._clock()
        while True:
            if sess.closed.is_set():
                return "the session was torn down", False
            try:
                msg = conn.recv(poll=0.25)
            except WsClosed as err:
                return str(err), err.clean
            except WsProtocolError as err:
                return str(err), False
            if msg is None:
                if self._clock() - last >= self.idle:
                    return f"idle {self.idle:.0f} s", False
                continue
            last = self._clock()
            op, payload = msg
            if self.tap is not None:
                self.tap.write(direction, payload)
            with sess.lock:
                partner = sess.legs[other]
                sess.forwarded[f"{role}->{other}" if partner is not None else f"{role}->dropped"] += 1
            if partner is None:
                continue                                   # partner parked: drop (latest-state wire)
            try:
                partner.send(payload, op)
            except OSError as err:
                with sess.lock:
                    if sess.legs[other] is partner:
                        sess.legs[other] = None
                        sess.drops[other] = self._clock()
                    else:
                        partner = None
                if partner is not None:
                    partner.close()
                    self.log(f"relay session {sess.code}: {other} parked (write failed: {err})")

    def _park(self, sess: _RelaySession, role: str, conn: WsConn) -> None:
        with sess.lock:
            if sess.closed.is_set():
                return
            if sess.legs[role] is not conn:
                self.log(f"relay session {sess.code}: old {role} connection retired (already replaced)")
                return
            sess.legs[role] = None
            sess.drops[role] = self._clock()
        conn.close()
        self.log(f"relay session {sess.code}: {role} parked -- holding the session for rejoin "
                 f"({self.rejoin_grace:.0f} s grace)")

    def _teardown(self, sess: _RelaySession) -> None:
        with self._lock:
            if self.sessions.get(sess.code) is sess:
                del self.sessions[sess.code]
        with sess.lock:
            sess.closed.set()
            legs = [c for c in sess.legs.values() if c is not None]
        for c in legs:
            c.close()

    def expired_reason(self, sess: _RelaySession, now: float) -> str:
        with sess.lock:
            paired = sess.legs["host"] is not None and sess.legs["guest"] is not None
            if not sess.ever_paired and not paired and now - sess.created > self.pair_wait:
                return "idle expired"
            for role in ("host", "guest"):
                d = sess.drops[role]
                if sess.ever_paired and sess.legs[role] is None and d is not None and now - d > self.rejoin_grace:
                    return f"{role} rejoin grace expired"
        return ""

    def gc(self, now: float | None = None) -> list:
        now = self._clock() if now is None else now
        with self._lock:
            sessions = list(self.sessions.values())
        gone = []
        for sess in sessions:
            why = self.expired_reason(sess, now)
            if why:
                self.log(f"relay session {sess.code}: {why}")
                self._teardown(sess)
                gone.append(sess.code)
        return gone

    def close_all(self) -> None:
        with self._lock:
            sessions = list(self.sessions.values())
        for sess in sessions:
            self._teardown(sess)

    def status(self) -> list:
        with self._lock:
            sessions = list(self.sessions.values())
        out = []
        for s in sessions:
            with s.lock:
                legs = "+".join(r for r in ("host", "guest") if s.legs[r] is not None) or "none"
                fwd = ", ".join(f"{k} {v}" for k, v in sorted(s.forwarded.items())) or "nothing yet"
            out.append(f"relay session {s.code}: legs {legs}; forwarded {fwd}")
        return out


# ======================================================================================== listening
class PortBusy(Exception):
    pass


class Listener:
    """A loopback accept loop; each connection runs ``on_conn(sock, addr)`` on its own daemon thread (closed after).
    Binds EXCLUSIVELY on Windows (SO_EXCLUSIVEADDRUSE): Windows SO_REUSEADDR would let this co-bind beside a running
    production bridge and steal half its connections; this refuses instead."""

    def __init__(self, port: int, on_conn, *, log: Log, host: str = "127.0.0.1", max_conns: int = 16):
        self.log = log
        self._on_conn = on_conn
        self._stop = threading.Event()
        self._slots = threading.BoundedSemaphore(max_conns)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as err:
            sock.close()
            raise PortBusy(f"cannot listen on {host}:{port} ({err}) -- is the production bridge "
                           "(`ff9mapkit coop host/join/bridge`) or another coop_peer already there? Stop it first: "
                           "this bench peer REPLACES the bridge, it never sits beside it. Or pass --port and point "
                           "the game's RelayUrl at it.") from None
        sock.listen(8)
        sock.settimeout(0.25)
        self.sock = sock
        self.port = sock.getsockname()[1]
        self.thread = threading.Thread(target=self._loop, name="coop-peer-accept", daemon=True)
        self.thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                client, addr = self.sock.accept()
            except socket.timeout:
                continue
            except OSError as err:
                if self._stop.is_set() or self.sock.fileno() == -1:
                    return
                self.log(f"accept error, continuing: {err}")
                time.sleep(0.05)
                continue
            if not self._slots.acquire(blocking=False):
                self.log(f"refusing {addr[0]}: too many connections")
                client.close()
                continue

            def serve(client=client, addr=addr):
                try:
                    self._on_conn(client, addr)
                except Exception as err:                   # noqa: BLE001 -- one bad connection never kills the loop
                    self.log(f"connection from {addr[0]} failed: {type(err).__name__}: {err}")
                finally:
                    try:
                        client.close()
                    except OSError:
                        pass
                    self._slots.release()
            threading.Thread(target=serve, name="coop-peer-conn", daemon=True).start()

    def close(self) -> None:
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass
        self.thread.join(timeout=2.0)


def _wait_forever(stop: threading.Event, every: float = 0.25, on_tick=None) -> None:
    """Block until ``stop`` (Ctrl+C raises KeyboardInterrupt out of here -- short waits keep it deliverable on Windows)."""
    while not stop.is_set():
        stop.wait(every)
        if on_tick is not None:
            on_tick()


# ======================================================================================== the modes
def _parse_offset(text: str) -> tuple:
    parts = [p for p in re.split(r"[,\s]+", text.strip()) if p]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(f"--offset wants dx,dy,dz (got {text!r})")
    return tuple(float(p) for p in parts)


def _parse_field(text: str):
    if text.strip().lower() == "mirror":
        return None
    v = int(text, 0)
    if not 0 <= v <= 0xFFFF:
        raise argparse.ArgumentTypeError("--field is a u16 field id (or 'mirror')")
    return v


def _parse_menu(text: str) -> int:
    t = text.strip().lower()
    if t in MENU_NAMES:
        return MENU_NAMES[t]
    v = int(t, 0)
    if not 0 <= v <= 255:
        raise argparse.ArgumentTypeError("--menu is a byte (or shut/legacy/root/deep)")
    return v


def _model_from(args) -> GuestModel:
    return GuestModel(field=args.field, offset=args.offset, report=REPORTS[args.report], menu=args.menu,
                      live_after=args.live_after)


def _guest_lines(args) -> list:
    report = ("none (no type-3 control frame)" if args.report == "off" else
              f"{args.report} on the host's current battle nonce, menu byte {args.menu}"
              + (f", BOOTING for the first {args.live_after:g} s of each battle" if args.live_after > 0 else ""))
    return [f"position: type-0 at 30 Hz on {'the HOST field (mirrored)' if args.field is None else f'field {args.field}'}"
            f"{'' if args.offset == (0.0, 0.0, 0.0) else f', offset {args.offset}'}",
            f"report: {report}",
            f"tap: {args.tap or 'off (pass --tap FILE to record the host)'}"]


class ServeGuest:
    """serve-guest's connection handler: each HOST game connection gets its own GuestSession and a fresh model (the
    engine redials every 2 s after a drop; a newer connection replaces an older one, as the relay replaces a stale leg)."""

    def __init__(self, model_factory, *, log: Log, tap: TapeWriter | None = None, status_every: float = 5.0,
                 tick: float = TICK_S):
        self._model_factory = model_factory
        self.log = log
        self.tap = tap
        self._status_every = status_every
        self._tick = tick
        self._lock = threading.Lock()
        self.current = None
        self.connections = 0
        self.ended = []                                    # each finished connection's reason, in order

    def on_conn(self, sock, addr=None) -> None:
        try:
            conn, code, _ = accept_ws(sock, want_role="host", mode="serve-guest")
        except HandshakeRefused as err:
            self.log(str(err))
            return
        self.log(f"HOST game connected (session {code}) -- this tool is its guest now")
        if self.tap is not None:
            self.tap.note(f"host game connected, session {code}")
        sess = GuestSession(conn, self._model_factory(), log=self.log, tap=self.tap, status_every=self._status_every,
                            tick=self._tick)
        with self._lock:
            old, self.current = self.current, sess
            self.connections += 1
        if old is not None:
            old.stop("replaced by a new host connection")
        why = sess.run()
        self.log(f"host connection ended: {why}")
        if self.tap is not None:
            self.tap.note(f"host connection ended: {why}")
        with self._lock:
            self.ended.append(why)
            if self.current is sess:
                self.current = None

    def stop(self, why: str) -> None:
        with self._lock:
            sess = self.current
        if sess is not None:
            sess.stop(why)


def _close_tap(tap: TapeWriter | None, log: Log) -> None:
    if tap is not None:
        tap.close()
        log(f"tape {tap.path}: {tap.records} record(s), {tap.bytes / 1e6:.1f} MB")


def cmd_serve_guest(args) -> int:
    log = Log(args.log)
    banner(log, "serve-guest", [f"It stands in for the bridge on ws://127.0.0.1:{args.port}: point the HOST game's "
                                f"RelayUrl here (Role=host).",
                                "It plays the GUEST itself -- nothing reaches any relay."] + _guest_lines(args))
    try:
        tap = TapeWriter(args.tap, mode="serve-guest") if args.tap else None
    except OSError as err:
        log(f"ERROR: cannot open the tape: {err}")
        return 2
    served = ServeGuest(lambda: _model_from(args), log=log, tap=tap, status_every=args.status)
    try:
        listener = Listener(args.port, served.on_conn, log=log)
    except PortBusy as err:
        log(f"ERROR: {err}")
        _close_tap(tap, log)
        return 2
    log(f"listening on ws://127.0.0.1:{listener.port} -- waiting for the HOST game (Ctrl+C to stop)")
    try:
        _wait_forever(threading.Event())
    except KeyboardInterrupt:
        log("stopping")
    finally:
        listener.close()
        served.stop("Ctrl+C")
        _close_tap(tap, log)
        log.close()
    return 0


def cmd_fake_guest_client(args) -> int:
    log = Log(args.log)
    path = session_path(args.code, "guest")
    banner(log, "fake-guest-client", [f"It DIALS {args.relay}{path} as the GUEST (a stand-in for a guest game).",
                                      "Put the real bridge between the host game and this relay to bench the bridge."]
           + _guest_lines(args))
    try:
        tap = TapeWriter(args.tap, mode="fake-guest-client", extra={"relay": args.relay, "code": args.code}) \
            if args.tap else None
    except OSError as err:
        log(f"ERROR: cannot open the tape: {err}")
        return 2
    try:
        while True:
            try:
                conn = dial_ws(args.relay, path, insecure=args.insecure)
            except Exception as err:                       # noqa: BLE001 -- any dial failure retries like the engine
                log(f"dial {args.relay} failed ({err}); retrying in 2 s")
                if args.once:
                    return 1
                time.sleep(2.0)
                continue
            log(f"connected to {args.relay} as role=guest, session {args.code} (the relay forwards nothing until the "
                "host pairs)")
            if tap is not None:
                tap.note(f"dialled {args.relay} as guest, session {args.code}")
            why = GuestSession(conn, _model_from(args), log=log, tap=tap, status_every=args.status).run()
            log(f"relay connection ended: {why}")
            if args.once:
                return 0
            log("redialling in 2 s (the engine's ConnectLoop cadence)")
            time.sleep(2.0)
    except KeyboardInterrupt:
        log("stopping")
        return 0
    finally:
        _close_tap(tap, log)
        log.close()


class ReplayHost:
    """replay-host's engine: ONE recorded host timeline (a Replayer) shared by however many GUEST connections come and go
    (a PeerPort -- a real host plays on while its guest redials), every guest message taped and decoded (a GuestWatch).
    The timeline starts at the guest's first frame (its 30 Hz keepalive proves it is there). ``on_conn`` serves a guest
    game that dialled in; ``dial_loop`` reaches one through a relay as role=host."""

    def __init__(self, frames, *, start: float, stop_at: float | None = None, blackholes=(), log: Log,
                 tap: TapeWriter | None = None, code: str | None = None, clock=time.monotonic, sleep=time.sleep):
        self.frames = frames
        self.start = start
        self.stop_at = stop_at
        self.blackholes = list(blackholes)
        self.log = log
        self.tap = tap
        self.code = code
        self._clock = clock
        self._sleep = sleep
        self.watch = GuestWatch()
        self.port = PeerPort()
        self.stop = threading.Event()
        self.seen = threading.Event()
        self.result = None

    def serve(self, conn: WsConn, label: str) -> str:
        """Attach one guest connection and read it until it ends (blocks)."""
        old = self.port.attach(conn)
        self.log(f"GUEST {label}" + (" (replacing the previous connection)" if old is not None else ""))
        if self.tap is not None:
            self.tap.note(f"guest {label}")
        why = "stopped"
        try:
            while not self.stop.is_set():
                msg = conn.recv(poll=0.25)
                if msg is None:
                    continue
                _, payload = msg
                if self.tap is not None:
                    self.tap.write(DIR_GUEST, payload)
                self.seen.set()
                for ev in self.watch.on_guest_message(payload, self._clock()):
                    self.log(ev)
        except WsClosed as err:
            why = f"closed ({err})"
        except WsProtocolError as err:
            why = f"malformed WS frame ({err})"
        finally:
            self.port.detach(conn)
            conn.close()
        self.log(f"guest connection ended: {why}")
        if self.tap is not None:
            self.tap.note(f"guest connection ended: {why}")
        return why

    def on_conn(self, sock, addr=None) -> None:
        try:
            conn, code, _ = accept_ws(sock, want_role="guest", mode="replay-host")
        except HandshakeRefused as err:
            self.log(str(err))
            return
        if self.code and code.upper() != self.code.upper():
            self.log(f"note: the guest's session code {code} is not --code {self.code} (served anyway)")
        self.serve(conn, f"game connected (session {code})")

    def dial_loop(self, url: str, code: str, insecure: bool = False) -> None:
        path = session_path(code, "host")
        while not self.stop.is_set():
            try:
                conn = dial_ws(url, path, insecure=insecure)
            except Exception as err:                       # noqa: BLE001 -- any dial failure retries
                self.log(f"dial {url} failed ({err}); retrying in 2 s")
                self.stop.wait(2.0)
                continue
            self.serve(conn, f"reached through {url} (session {code}, this tool as role=host)")
            self.stop.wait(2.0)

    def _on_sent(self, rec, wtype, payload) -> None:
        self.watch.note_host(wtype, payload)
        if self.tap is not None:
            self.tap.write(DIR_HOST, rec.payload)

    def _on_note(self, text: str) -> None:
        if self.tap is not None:
            self.tap.note(text)

    def tick(self) -> None:
        for ev in self.watch.tick(self._clock()):
            self.log(ev)

    def run(self, poll: float = 0.25) -> dict:
        """Wait for the guest, replay the timeline (on its own thread, ticking the watch here), return the summary."""
        self.log("the replay clock starts at the guest's first frame")
        while not self.seen.wait(poll):
            if self.stop.is_set():
                self.result = {"why": "stopped before a guest came", "sent": 0, "dropped": 0, "unsent": 0,
                               "max_lag": 0.0}
                return self.result
        rep = Replayer(self.frames, start=self.start, stop_at=self.stop_at, blackholes=self.blackholes,
                       send=self.port.send, log=self.log, clock=self._clock, sleep=self._sleep, on_sent=self._on_sent,
                       on_note=self._on_note)
        result = {}
        runner = threading.Thread(target=lambda: result.update(rep.run(self.stop)), name="coop-peer-replay",
                                  daemon=True)
        runner.start()
        while runner.is_alive():
            runner.join(poll)
            self.tick()
        self.result = result
        self.log(f"replay done ({result.get('why')}): sent {result.get('sent')}, dropped in blackholes "
                 f"{result.get('dropped')}, unsent (no guest attached) {result.get('unsent')}, max lag "
                 f"{result.get('max_lag', 0.0):.3f} s")
        return result

    def hold(self, seconds: float | None = None, poll: float = 0.25) -> None:
        """Keep every link open and silent (decoding what the guest still sends) for ``seconds``, or until stop."""
        deadline = None if seconds is None else self._clock() + seconds
        while not self.stop.is_set() and (deadline is None or self._clock() < deadline):
            self.stop.wait(poll)
            self.tick()

    def close(self, code: int | None = None) -> None:
        self.stop.set()
        self.port.close(code)


def _replay_plan(args, records) -> tuple:
    """The replay's frames, start, stop and blackholes from the CLI; raises ValueError with the reason."""
    frames = host_frames(records)
    if not frames:
        raise ValueError(f"{args.tape} holds no host frames (dir 0) to replay")
    battles = tape_battles(records)
    start = resolve_time(args.from_, battles) if args.from_ is not None else frames[0][0].t
    stop_at = resolve_time(args.stop_at, battles) if args.stop_at is not None else None
    ats = [resolve_time(a, battles) for a in args.blackhole_at]
    fors = [float(f) for f in args.blackhole_for]
    if len(fors) == 1 and len(ats) > 1:
        fors = fors * len(ats)
    if len(ats) != len(fors) or any(f <= 0 for f in fors):
        raise ValueError("give one --blackhole-for (> 0 s) per --blackhole-at (or one for all)")
    if args.dial and not args.code:
        raise ValueError("--dial needs --code (the session the guest game uses)")
    return frames, battles, start, stop_at, list(zip(ats, fors))


def cmd_replay_host(args) -> int:
    log = Log(args.log)
    try:
        header, records, torn = read_tape(args.tape)
        frames, battles, start, stop_at, blackholes = _replay_plan(args, records)
    except (OSError, TapeError, ValueError) as err:
        log(f"ERROR: {err}")
        log.close()
        return 2
    where = (f"DIALS {args.dial} as role=host, session {args.code}" if args.dial else
             f"stands in for the bridge on ws://127.0.0.1:{args.port}: point the GUEST game's RelayUrl here "
             "(Role=client)")
    lines = [f"It {where}.", f"It replays a RECORDED host ({args.tape}, recorded {header.get('started', '?')}) -- "
             "nothing it sends is live, and the guest's commands land nowhere."]
    lines.append(f"tape: {len(frames)} host frame(s), tape {frames[0][0].t:.2f}..{frames[-1][0].t:.2f} s; "
                 f"{len(battles)} battle(s)" + (f"; TORN tail of {torn} B ignored" if torn else ""))
    for b in battles:
        lines.append(f"  battle{b['n']}: nonce {b['nonce']} map {b['map']} tape {b['start']:.2f}..{b['end']:.2f} s")
    lines.append(f"replay from tape {start:.2f} s" + (f", stop at {stop_at:.2f} s" if stop_at is not None else "")
                 + "; at the end: " + ("HOLD the link open, silent (a host quit behind the bridge)"
                                       if args.at_end == "hold" else "CLOSE it (code 1000)"))
    for a, n in blackholes:
        lines.append(f"BLACKHOLE tape {a:.2f}..{a + n:.2f} s ({n:g} s): the TCP stays open, nothing is sent")
    banner(log, "replay-host", lines)

    try:
        tap = TapeWriter(args.tap, mode="replay-host", extra={"source_tape": str(args.tape), "blackholes": blackholes,
                                                              "from": start, "stop_at": stop_at}) if args.tap else None
    except OSError as err:
        log(f"ERROR: cannot open the tape: {err}")
        log.close()
        return 2
    rh = ReplayHost(frames, start=start, stop_at=stop_at, blackholes=blackholes, log=log, tap=tap, code=args.code)
    listener = None
    if args.dial:
        threading.Thread(target=rh.dial_loop, args=(args.dial, args.code, args.insecure), name="coop-peer-dial",
                         daemon=True).start()
    else:
        try:
            listener = Listener(args.port, rh.on_conn, log=log)
        except PortBusy as err:
            log(f"ERROR: {err}")
            _close_tap(tap, log)
            log.close()
            return 2
        log(f"listening on ws://127.0.0.1:{listener.port} -- waiting for the GUEST game")
    try:
        rh.run()
        if args.at_end == "close":
            log("closing the guest's link (code 1000)")
            rh.port.close(1000)
        else:
            log("holding the link open, sending nothing" + (f" for {args.linger:g} s" if args.linger else
                                                             " (Ctrl+C to stop)"))
        if args.at_end == "hold" or args.linger:
            rh.hold(args.linger or None)
    except KeyboardInterrupt:
        log("stopping")
    finally:
        rh.close()
        if listener is not None:
            listener.close()
        log(rh.watch.summary())
        _close_tap(tap, log)
        log.close()
    return 0


def cmd_relay(args) -> int:
    log = Log(args.log)
    banner(log, "relay", [f"A minimal LOCAL relay on ws://127.0.0.1:{args.port} (after relay/main.go v2) -- not the "
                          "public relay.",
                          f"Put the real bridge in the loop: ff9mapkit coop bridge --relay ws://127.0.0.1:{args.port}",
                          f"pair wait {args.pair_wait:g} s, rejoin grace {args.rejoin_grace:g} s, idle {args.idle:g} s; "
                          f"tap: {args.tap or 'off'}"])
    try:
        tap = TapeWriter(args.tap, mode="relay") if args.tap else None
    except OSError as err:
        log(f"ERROR: cannot open the tape: {err}")
        return 2
    relay = LocalRelay(log=log, tap=tap, pair_wait=args.pair_wait, rejoin_grace=args.rejoin_grace, idle=args.idle)
    try:
        listener = Listener(args.port, relay.handle, log=log)
    except PortBusy as err:
        log(f"ERROR: {err}")
        _close_tap(tap, log)
        return 2
    log(f"relay listening on ws://127.0.0.1:{listener.port} (Ctrl+C to stop)")
    marks = {"gc": time.monotonic(), "status": time.monotonic()}

    def on_tick():
        now = time.monotonic()
        if now - marks["gc"] >= 5.0:
            marks["gc"] = now
            relay.gc(now)
        if args.status and now - marks["status"] >= args.status:
            marks["status"] = now
            for line in relay.status():
                log(line)

    try:
        _wait_forever(threading.Event(), on_tick=on_tick)
    except KeyboardInterrupt:
        log("stopping")
    finally:
        listener.close()
        relay.close_all()
        _close_tap(tap, log)
        log.close()
    return 0


def tape_info(path) -> list:
    """The ``info`` report's lines (pure over the file)."""
    header, records, torn = read_tape(path)
    out = [f"tape {path}", "header: " + json.dumps(header, sort_keys=True)]
    if not records:
        return out + ["no records"]
    span = records[-1].t - records[0].t
    out.append(f"{len(records)} record(s), tape {records[0].t:.2f}..{records[-1].t:.2f} s ({span:.1f} s)"
               + (f"; TORN tail {torn} B" if torn else ""))
    counts = collections.Counter()
    sizes = collections.Counter()
    foreign = collections.Counter()
    for r in records:
        if r.dir == DIR_NOTE:
            counts[("note", None)] += 1
            continue
        got = parse_frame(r.payload)
        if got is None:
            foreign[DIR_NAMES.get(r.dir, r.dir)] += 1
            continue
        counts[(DIR_NAMES.get(r.dir, r.dir), got[0])] += 1
        sizes[(DIR_NAMES.get(r.dir, r.dir), got[0])] += len(r.payload)
    for (d, t), n in sorted(counts.items(), key=lambda kv: (str(kv[0][0]), kv[0][1] if kv[0][1] is not None else -1)):
        if d == "note":
            out.append(f"  notes: {n}")
        else:
            out.append(f"  {d:5} {TYPE_NAMES.get(t, t):8} {n:7d} frame(s) {sizes[(d, t)] / 1e3:9.1f} KB"
                       + (f"  ~{n / span:.0f}/s" if span >= 1.0 else ""))
    for d, n in foreign.items():
        out.append(f"  {d:5} NOT v14  {n:7d} message(s) (the engine would drop these)")
    acts = tape_actions(records)
    if acts["frames"]:                                     # [ff9mapkit netsync s133] what the host's action lane carried
        out.append(f"host action records: {acts['starts']} START(s), {acts['ends']} END(s), {acts['impacts']} impact(s) "
                   f"({acts['ext']} with an action id), {acts['stat']} stat tick(s), {acts['bad']} bad"
                   + ("" if acts["starts"] else " -- no START: a pre-s133 host (or its `actbench hoststarts off`)"))
    out.append("host field edges:")
    for t, f in tape_fields(records):
        out.append(f"  tape {t:9.2f}  field {_field_text(f)}")
    battles = tape_battles(records)
    out.append(f"battles: {len(battles)} (anchors: battleN = start, battleN.end = last frame)")
    for b in battles:
        out.append(f"  battle{b['n']}: nonce {b['nonce']} map {b['map']} tape {b['start']:.2f}..{b['end']:.2f} s "
                   f"({b['end'] - b['start']:.1f} s, {b['frames']} frame(s), seq {b['seq_first']}..{b['seq_last']})")
    notes = [(r.t, r.payload.decode("utf-8", "replace")) for r in records if r.dir == DIR_NOTE]
    if notes:
        out.append("notes:")
        out.extend(f"  tape {t:9.2f}  {text}" for t, text in notes)
    return out


def cmd_info(args) -> int:
    try:
        for line in tape_info(args.tape):
            print(line)
    except (OSError, TapeError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    return 0


def cmd_dump(args) -> int:
    try:
        _, records, torn = read_tape(args.tape)
    except (OSError, TapeError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    want_dir = {"host": DIR_HOST, "guest": DIR_GUEST, "note": DIR_NOTE}.get(args.dir) if args.dir else None
    shown = 0
    for r in records:
        if want_dir is not None and r.dir != want_dir:
            continue
        if r.dir == DIR_NOTE:
            if args.type is not None:
                continue
            line = f"{r.t:10.3f} note  {r.payload.decode('utf-8', 'replace')}"
        else:
            got = parse_frame(r.payload)
            if got is None:
                if args.type is not None:
                    continue
                line = f"{r.t:10.3f} {DIR_NAMES.get(r.dir, r.dir):5} NOT v14: {frame_header_text(r.payload)}"
            else:
                if args.type is not None and got[0] != args.type:
                    continue
                line = f"{r.t:10.3f} {DIR_NAMES.get(r.dir, r.dir):5} {describe_frame(got[0], got[1])}"
            if args.hex:
                line += "  " + BW.hex_bytes(r.payload)
        print(line)
        shown += 1
        if args.limit and shown >= args.limit:
            break
    if torn:
        print(f"(torn tail: {torn} B ignored)")
    return 0


# ======================================================================================== [ff9mapkit netsync s139] section 8
def strip_section(payload, section_id: int) -> bytes:
    """``payload`` re-framed without its sections of ``section_id`` (the walk stops where the engine's does: a truncated
    tail is dropped with it)."""
    out = b""
    for sid, body in BW.walk_sections(payload)[0]:
        if sid != section_id:
            out = out + bytes((sid, len(body) & 0xFF, (len(body) >> 8) & 0xFF)) + body
    return out


#: the sentinel section tape_dress appends AFTER section 8 (an id no engine uses): an old walker must step over section 8 by
#: its length to reach it -- a walker that STOPPED at id 8 would answer every earlier read identically, so the strip
#: comparison alone could not tell (section 8 is always last on a real frame)
SENTINEL_SECTION, SENTINEL_BODY = 0xC8, b"\x5a"


def tape_dress(records, expect=None) -> dict:
    """Section 8 on a tape's HOST type-5 frames (PURE over the records): how many frames, how many carry section 8, how
    many with it RIGHT AFTER section 7 and LAST, how many bodies the reader refuses (< 3 B), the bodies seen (hex ->
    count), and how many frames an OLD guest reads differently with section 8 present than stripped (its story, its party
    sections, each of sections 4-7: battlewire's s103 walker twins) or cannot step past it (a SENTINEL section appended
    after section 8 must still read, the story and party sections unmoved). ``expect``: None, the body every frame must
    carry (bytes), or a function ``payload -> bytes`` giving each frame's OWN expected body (``disagree`` counts the
    frames whose body is not theirs). ``ok`` -- the wire carries section 8 as s139 says: at least one frame, every one with
    section 8 after section 7 and last, every body parsed, no old-reader difference, and every body the expected one."""
    frames = [payload for _r, wtype, payload in host_frames(records) if wtype == TYPE_STATE]
    out = {"frames": len(frames), "with8": 0, "after7": 0, "last": 0, "malformed": 0, "old_diff": 0, "bodies": {},
           "disagree": 0, "first_bad": None, "first_disagree": None}
    per_frame = callable(expect)
    for payload in frames:
        secs, truncated = BW.walk_sections(payload)
        ids = [sid for sid, _b in secs]
        if BW.SECTION_DRESS not in ids:
            continue
        out["with8"] += 1
        k = ids.index(BW.SECTION_DRESS)
        body = secs[k][1]
        if BW.SECTION_DIALOG in ids and ids.index(BW.SECTION_DIALOG) == k - 1:
            out["after7"] += 1
        if k == len(ids) - 1 and not truncated:
            out["last"] += 1
        if BW.parse_dress_section(body) is None:
            out["malformed"] += 1
        key = BW.hex_bytes(body)
        out["bodies"][key] = out["bodies"].get(key, 0) + 1
        if per_frame:
            mine = expect(payload)
            if mine is None or bytes(body) != bytes(mine):
                out["disagree"] += 1
                if out["first_disagree"] is None:
                    out["first_disagree"] = (f"section 8 {key} on a frame whose own party "
                                             f"{BW.frame_slot_chars(payload)} gives "
                                             f"{BW.hex_bytes(mine) if mine is not None else 'no expectation'}")
        bare = strip_section(payload, BW.SECTION_DRESS)
        past = BW.append_section(payload, SENTINEL_SECTION, SENTINEL_BODY)
        same = (BW.old_apply_story(payload) == BW.old_apply_story(bare)
                and BW.old_party_sections(payload) == BW.old_party_sections(bare)
                and all(BW.old_try_read_section(payload, sid) == BW.old_try_read_section(bare, sid)
                        for sid in (BW.SECTION_INTENT, BW.SECTION_EVENT, BW.SECTION_TALK, BW.SECTION_DIALOG))
                and BW.old_try_read_section(past, SENTINEL_SECTION) == SENTINEL_BODY
                and BW.old_apply_story(past) == BW.old_apply_story(payload)
                and BW.old_party_sections(past) == BW.old_party_sections(payload))
        if not same:
            out["old_diff"] += 1
            if out["first_bad"] is None:
                out["first_bad"] = f"an old reader differs on a frame with section 8 {key}"
    n = out["with8"]
    want = None if expect is None or per_frame else BW.hex_bytes(expect)
    out["ok"] = bool(out["frames"]) and n == out["frames"] == out["after7"] == out["last"] and not out["malformed"] \
        and not out["old_diff"] and not out["disagree"] and (want is None or out["bodies"] == {want: n})
    return out


# ======================================================================================== [ff9mapkit netsync s144] b6 / b7
def tape_where(records) -> dict:
    """Section 7's b6 HfWorld / b7 HfTitle on a tape's HOST type-5 frames (PURE over the records) -- WHERE AN OFF-FIELD HOST
    SAYS IT STANDS (studies/world-coop/S144-DESIGN.md decision 7): each frame's flags byte through TryParseHostSection's twin
    (battlewire.parse_dialog_section: it copies the byte unvalidated), against the host's field off the LAST position frame
    before it. ``frames`` / ``with7`` / ``refused`` (a section 7 the parser rejects); ``world`` / ``title`` (frames with the
    bit) and how many of those the host's position lane put ON a real field (``world_on_field`` / ``title_on_field`` -- an
    s144 host never says "world" there: b6 is its strict onWorld); ``off_field`` (frames while the lane reads field 0 /
    65535) and how many said where (``off_field_said``); ``parity_diff`` (PARSER-TWIN PARITY: frames whose body parses
    differently through battlewire's twin with b6 / b7 masked off -- a codec check of the twin, which reads the flags byte
    unvalidated, NOT the old guest's reader: that one's claim is its single-bit reads, pinned against the live stack by
    tests/test_world_coop.py and the engine's own 'overlay text selftest'); ``first_world`` / ``first_title`` (the tape second
    each first shows); ``stage`` ("s144" when a bit ever rides, else an s143-or-older host -- an old tape parses exactly as
    before)."""
    out = {"frames": 0, "with7": 0, "refused": 0, "world": 0, "title": 0, "world_on_field": 0, "title_on_field": 0,
           "off_field": 0, "off_field_said": 0, "parity_diff": 0, "first_world": None, "first_title": None}
    field = None
    for r, wtype, payload in host_frames(records):
        if wtype == TYPE_POS:
            p = parse_pos_payload(payload)
            if p is not None:
                field = p["field"]
            continue
        if wtype != TYPE_STATE:
            continue
        out["frames"] += 1
        body = BW.old_try_read_section(payload, BW.SECTION_DIALOG)
        if body is None:
            continue
        out["with7"] += 1
        view = BW.parse_dialog_section(body)
        if view is None:
            out["refused"] += 1
            continue
        f = view["flags"]
        old = BW.parse_dialog_section(bytes(body[:5]) + bytes([f & BW.HF_OLD_SIX]) + bytes(body[6:]))
        if old is None or {k: v for k, v in old.items() if k != "flags"} != {k: v for k, v in view.items() if k != "flags"} \
                or old["flags"] != f & BW.HF_OLD_SIX:
            out["parity_diff"] += 1
        on_field = field is not None and 0 < field < FIELD_SENTINEL
        if f & BW.HF_WORLD:
            out["world"] += 1
            out["world_on_field"] += on_field
            if out["first_world"] is None:
                out["first_world"] = round(r.t, 3)
        if f & BW.HF_TITLE:
            out["title"] += 1
            out["title_on_field"] += on_field
            if out["first_title"] is None:
                out["first_title"] = round(r.t, 3)
        if field is not None and not on_field:
            out["off_field"] += 1
            out["off_field_said"] += bool(f & (BW.HF_WORLD | BW.HF_TITLE))
    out["stage"] = "s144" if out["world"] or out["title"] else "s143-or-older (no b6 / b7)"
    return out


#: `where --want`: what the tape's host must have said (the verdict's own rule over tape_where's counts)
WHERE_WANTS = ("world", "title", "none", "any")


def where_ok(d: dict, want: str) -> bool:
    """`where`'s verdict: ``world`` / ``title`` -- the bit rode at least one frame and never one the host's lane put on a
    real field; ``none`` -- an s143-or-older host's tape (section 7 rode, no b6 / b7: the calibration); ``any`` -- the tape
    parsed. Every verdict needs host state frames and no refused section (the parser-twin parity count is reported, never
    judged: it cannot fail -- the twin copies the flags byte unvalidated)."""
    if not d["frames"] or d["refused"]:
        return False
    if want == "world":
        return d["world"] > 0 and d["world_on_field"] == 0
    if want == "title":
        return d["title"] > 0 and d["title_on_field"] == 0
    if want == "none":
        return d["with7"] > 0 and d["world"] == d["title"] == 0
    return want == "any"


def tape_where_lines(path, want: str = "any") -> tuple:
    """(ok, the ``where`` report's lines) for a tape file."""
    if want not in WHERE_WANTS:
        raise ValueError(f"--want is one of {WHERE_WANTS}, not {want!r}")
    header, records, torn = read_tape(path)
    d = tape_where(records)
    ok = where_ok(d, want)
    lines = [f"tape {path}",
             f"host type-5 frames: {d['frames']}; with section 7: {d['with7']} (refused: {d['refused']})"
             + (f"; TORN tail {torn} B" if torn else ""),
             f"b6 world: {d['world']} frame(s) (on a real field: {d['world_on_field']}; first at {d['first_world']}); "
             f"b7 title: {d['title']} (on a real field: {d['title_on_field']}; first at {d['first_title']})",
             f"while the host's lane reads field 0 / 65535: {d['off_field']} frame(s), {d['off_field_said']} saying where",
             f"parser-twin parity (the body with b6 / b7 masked off): {d['with7'] - d['refused'] - d['parity_diff']} "
             f"identical, {d['parity_diff']} different (a codec check, not the old guest's reader)",
             f"the recording host: {d['stage']}",
             f"VERDICT (--want {want}): " + ("OK" if ok else "FAIL")]
    return ok, lines


def cmd_where(args) -> int:
    found, tried = resolve_tape(args.tape)
    if found is None:
        print(f"ERROR: no tape {args.tape!r} -- tried {', '.join(str(t) for t in tried)}", file=sys.stderr)
        return 2
    try:
        ok, lines = tape_where_lines(found, args.want)
    except (OSError, TapeError, ValueError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0 if ok else 1


#: [ff9mapkit netsync s140] `dress --stage`: the host engine a tape was RECORDED on -> the dress rules its producer ran
#: (battlewire.dress_rules: s139's frozen rules -- Cinna..Beatrix undressed, 00 00 FF -- or the live s140 table, rows 9-12)
DRESS_STAGES = {"s139": "dresshost", "s140": "dressself"}


def frame_expect(ghost_as, guest_slots: int, rules=None, leader: int = -1):
    """``payload -> bytes``: each host frame's OWN expected section 8 -- the twin's body for the host's ``ghost_as`` /
    ``guest_slots`` over the party THAT frame carries in its section 1 (its CharId bytes are PLAYER.info.slot_no, the very
    PLAYER.Index the host's LiveSlotChars reads); None when the frame has no readable section 1. [ff9mapkit netsync s140]
    ``rules``: the recording engine's dress rules (:data:`DRESS_STAGES` -> battlewire.dress_rules; None = the live s140
    table) -- an s139 tape with a CharacterId 8-11 member carried 00 00 FF, an s140 one 6B 00 08 .. CC 00 0B.
    [ff9mapkit netsync s143] ``leader``: an s143 host's leader (the CharacterId of its controlled field body; -1 = none / an
    s139-s141 host: the positional rule) -- its HostDress guards the mask over the frame's party first (FieldGuardMask)."""
    R = rules or BW
    kw = {"leader": int(leader)} if int(leader) >= 0 else {}

    def expect(payload):
        party = BW.frame_slot_chars(payload)
        if party is None:
            return None
        return R.host_dress_section(ghost_as, int(guest_slots), "host", False, party, **kw)
    return expect


def tape_dress_lines(path, expect=None) -> tuple:
    """(ok, the ``dress`` report's lines) for a tape file (``expect`` as :func:`tape_dress`)."""
    header, records, torn = read_tape(path)
    d = tape_dress(records, expect)
    if callable(expect):
        want = (f" (each frame's own party: {d['with8'] - d['disagree']} agree, {d['disagree']} disagree"
                + (f" -- first: {d['first_disagree']}" if d["first_disagree"] else "") + ")")
    else:
        want = "" if expect is None else f" (want {BW.hex_bytes(expect)} -- {BW.dress_section_text(expect)})"
    lines = [f"tape {path}", f"host type-5 frames: {d['frames']}; with section 8: {d['with8']} (right after section 7: "
             f"{d['after7']}, last: {d['last']}, malformed: {d['malformed']})" + (f"; TORN tail {torn} B" if torn else ""),
             "section 8 bodies: " + (", ".join(f"{k} x{v} ({BW.dress_section_text(bytes.fromhex(k))})"
                                               for k, v in d["bodies"].items()) or "none -- an s138-or-older host") + want,
             f"old-guest readers (story, party sections, sections 4-7, a section past it) with section 8 vs stripped: "
             f"{d['with8'] - d['old_diff']} identical, {d['old_diff']} different"
             + (f" ({d['first_bad']})" if d["first_bad"] else ""),
             "VERDICT: " + ("OK -- section 8 rides every host state frame, after section 7, and an old guest skips it"
                            if d["ok"] else "FAIL")]
    return d["ok"], lines


def _dress_expect(args):
    """The ``dress`` verb's expectation: ``--expect HEX``; or, with ``--ghost-as`` (which REQUIRES ``--guest-slots``: a
    default would silently mean a spectator), ``--party`` given -> one body for the whole tape, omitted -> each frame's own
    party off its section 1 (:func:`frame_expect`); None = no body check."""
    if args.expect:
        return bytes(int(t, 16) for t in args.expect.replace("-", " ").split())
    if args.ghost_as is None:
        return None
    if args.guest_slots is None:
        raise ValueError("--ghost-as needs --guest-slots (the host's GuestSlots; 0 = a spectator: the moogle under auto)")
    rules = BW.dress_rules(DRESS_STAGES[getattr(args, "stage", None) or "s140"])
    leader = int(getattr(args, "leader", None) if getattr(args, "leader", None) is not None else -1)
    if leader >= 0 and rules is not BW:
        raise ValueError("--leader is an s143 host's (its leader guard); a --stage s139 host has none")
    kw = {"leader": leader} if leader >= 0 else {}             # [ff9mapkit netsync s143]
    if args.party:
        party = [int(x) for x in args.party.split(",")]
        return rules.host_dress_section(args.ghost_as, int(args.guest_slots), "host", False, party, **kw)
    return frame_expect(args.ghost_as, int(args.guest_slots), rules, leader)
def tape_home() -> Path:
    """Where the recorded tapes live: COOP_TAPE_DIR, else <the MAIN repo>/.harness-runs/coop-tapes -- the rule
    studies/test-harness/scenarios/_coop_peer_bench.tape_dir() records them by (gitignored, outliving any worktree). The
    main repo is tools/repo_root.main_repo_root (git's common dir); this checkout when git cannot answer."""
    env = os.environ.get("COOP_TAPE_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    try:
        tools = str(_REPO / "tools")
        if tools not in sys.path:
            sys.path.insert(0, tools)
        from repo_root import main_repo_root
        main = Path(main_repo_root(start=_REPO / "tools", fallback=_REPO))
    except Exception:                                      # noqa: BLE001 -- a gitless machine keeps this checkout
        main = _REPO
    return main / ".harness-runs" / "coop-tapes"


def resolve_tape(path) -> tuple:
    """[ff9mapkit netsync s139] (the tape file to read, the places tried): ``path`` as given (against the cwd) when it is a
    file; else, for a RELATIVE path, the same path under the main repo (``.harness-runs/coop-tapes/<name>`` written from a
    worktree, where that directory does not exist) and its bare name under :func:`tape_home`. The first file found wins;
    none -> (None, tried) -- the caller says every place it looked."""
    p = Path(path).expanduser()
    tried = [p]
    if p.is_file():
        return p, tried
    if not p.is_absolute():
        home = tape_home()
        for cand in (home.parent.parent / p, home / p.name):
            if cand not in tried:
                tried.append(cand)
                if cand.is_file():
                    return cand, tried
    return None, tried


def cmd_offer(args) -> int:
    found, tried = resolve_tape(args.tape)
    if found is None:
        print(f"ERROR: no tape {args.tape!r} -- tried {', '.join(str(t) for t in tried)}", file=sys.stderr)
        return 2
    try:
        ok, lines = tape_offer_lines(found, args.want)
    except (OSError, TapeError, ValueError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0 if ok else 1


def cmd_dress(args) -> int:
    found, tried = resolve_tape(args.tape)
    if found is None:
        print(f"ERROR: no tape {args.tape!r} -- tried {', '.join(str(t) for t in tried)}", file=sys.stderr)
        return 2
    try:
        ok, lines = tape_dress_lines(found, _dress_expect(args))
    except (OSError, TapeError, ValueError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0 if ok else 1


def _add_guest_options(p) -> None:
    p.add_argument("--report", choices=sorted(REPORTS), default="off",
                   help="the type-3 control frame while the host's battle lane is live: off (none, default), legacy "
                        "(2-byte, pre-R3), or an s114 fmt-1 report on the host's current nonce "
                        "(none/booting/live/declined/busy)")
    p.add_argument("--menu", type=_parse_menu, default=0,
                   help="the control frame's byte 1: 0 shut (default), 1 legacy, 2 root, 3 deep (or the name)")
    p.add_argument("--live-after", type=float, default=0.0, metavar="S",
                   help="report BOOTING for the first S s of each battle nonce, then --report (a diorama booting)")
    p.add_argument("--field", type=_parse_field, default=None,
                   help="the type-0 field: 'mirror' (default: the host's own, 0 in its battles) or a fixed id")
    p.add_argument("--offset", type=_parse_offset, default=(0.0, 0.0, 0.0), metavar="DX,DY,DZ",
                   help="added to the mirrored host position (the ghost's spot on the host's screen)")
    p.add_argument("--tap", metavar="FILE", help="record every frame both ways to this tape (.f9tape)")
    p.add_argument("--status", type=float, default=5.0, metavar="S", help="a status line every S s (default 5)")
    p.add_argument("--log", metavar="FILE", help="tee every line to this file too")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="coop_peer", description="Solo two-role bench peer for FF9 co-op netsync "
                                 "(NOT the production bridge). See the module docstring for the benches.")
    sub = ap.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("serve-guest", help="be the GUEST of a host game that dials this port; tape the host")
    p.add_argument("--port", type=int, default=49201, help="the game's RelayUrl port (default 49201)")
    _add_guest_options(p)
    p.set_defaults(func=cmd_serve_guest)

    p = sub.add_parser("fake-guest-client", help="dial a relay as role=guest and be a fake guest there")
    p.add_argument("--relay", default="ws://127.0.0.1:7777", help="relay URL (default ws://127.0.0.1:7777)")
    p.add_argument("--code", required=True, help="the session code (the host's SessionCode)")
    p.add_argument("--insecure", action="store_true", help="skip TLS verification (wss:// only)")
    p.add_argument("--once", action="store_true", help="exit when the connection ends instead of redialling")
    _add_guest_options(p)
    p.set_defaults(func=cmd_fake_guest_client)

    p = sub.add_parser("replay-host", help="replay a recorded host tape into a GUEST game that dials this port")
    p.add_argument("tape", help="a tape recorded by serve-guest / fake-guest-client / relay --tap")
    p.add_argument("--port", type=int, default=49201, help="the game's RelayUrl port (default 49201)")
    p.add_argument("--dial", metavar="URL", help="instead of listening, dial this relay as role=host (needs --code)")
    p.add_argument("--code", help="the session code (required with --dial; checked against the guest's otherwise)")
    p.add_argument("--insecure", action="store_true", help="skip TLS verification (wss:// only)")
    p.add_argument("--from", dest="from_", metavar="T", help="start at tape time T (default: the first host frame)")
    p.add_argument("--stop-at", metavar="T", help="stop sending at tape time T")
    p.add_argument("--blackhole-at", action="append", default=[], metavar="T",
                   help="begin a cut at tape time T (seconds, or battle[N][.end][+-S]); repeatable")
    p.add_argument("--blackhole-for", action="append", default=[], metavar="N",
                   help="the cut's length in seconds (one per --blackhole-at, or one for all)")
    p.add_argument("--at-end", choices=("hold", "close"), default="hold",
                   help="after the tape: hold the link open and silent (default; a host quit behind the bridge) or "
                        "close it with code 1000")
    p.add_argument("--linger", type=float, default=0.0, metavar="S",
                   help="exit S s after the end (default: hold until Ctrl+C; 'close' exits at once)")
    p.add_argument("--tap", metavar="FILE", help="record what was sent + everything the guest sent to this tape")
    p.add_argument("--log", metavar="FILE", help="tee every line to this file too")
    p.set_defaults(func=cmd_replay_host)

    p = sub.add_parser("relay", help="a minimal local relay pairing role=host and role=guest by session code")
    p.add_argument("--port", type=int, default=7777, help="listen port (default 7777, the relay's own)")
    p.add_argument("--pair-wait", type=float, default=60.0, metavar="S")
    p.add_argument("--rejoin-grace", type=float, default=60.0, metavar="S")
    p.add_argument("--idle", type=float, default=90.0, metavar="S")
    p.add_argument("--tap", metavar="FILE", help="record every forwarded message (dir = the sender's role)")
    p.add_argument("--status", type=float, default=10.0, metavar="S", help="a per-session line every S s (0 = off)")
    p.add_argument("--log", metavar="FILE", help="tee every line to this file too")
    p.set_defaults(func=cmd_relay)

    p = sub.add_parser("info", help="summarise a tape: frame counts, field edges, battles (the time anchors)")
    p.add_argument("tape")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("dump", help="one line per tape record")
    p.add_argument("tape")
    p.add_argument("--dir", choices=("host", "guest", "note"))
    p.add_argument("--type", type=int, help="only this NetSyncWire type")
    p.add_argument("--hex", action="store_true", help="append the raw frame bytes")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=cmd_dump)

    p = sub.add_parser("dress", help="[s139] section 8 on a tape's host state frames: present, after section 7, its body, "
                                     "skipped by the old readers")
    p.add_argument("tape", help="the tape: a path (against the cwd), else -- when relative -- the same path under the "
                                "MAIN repo, else its name under COOP_TAPE_DIR / <main repo>/.harness-runs/coop-tapes")
    p.add_argument("--expect", metavar="HEX", help="the body every frame must carry, e.g. '08 00 01' (Vivi)")
    p.add_argument("--ghost-as", default=None, help="...or the host's [Netsync] GhostAs (the twin computes the body)")
    p.add_argument("--guest-slots", type=int, default=None, help="the host's GuestSlots (REQUIRED with --ghost-as)")
    p.add_argument("--party", default=None, metavar="C0,C1,C2,C3",
                   help="the host's party slots' CharacterIds, -1 empty (with --ghost-as auto), e.g. 0,1,2,3; omitted = "
                        "each frame's OWN party, read off its section 1")
    p.add_argument("--stage", choices=tuple(DRESS_STAGES), default="s140",
                   help="[s140] the host engine the tape was RECORDED on (with --ghost-as): s139's rules leave Cinna.."
                        "Beatrix undressed (00 00 FF), s140's dress them (rigs 9-12) -- default s140")
    p.add_argument("--leader", type=int, default=None, metavar="CHAR",
                   help="[s143] the host's LEADER (the CharacterId its controlled field body is: 0 = Zidane) -- an s143 "
                        "host's section 8 names whom its leader guard hands the guest (with --ghost-as auto); omitted = "
                        "the positional rule (an s139-s141 host)")
    p.set_defaults(func=cmd_dress)

    p = sub.add_parser("offer", help="[s143] the type-1 header's guest mask (the host's offer) on every battle frame from "
                                     "the first Ready one on")
    p.add_argument("tape", help="the tape (resolved as `dress` resolves it)")
    p.add_argument("--want", type=int, required=True, metavar="MASK",
                   help="the offer every such frame must carry: an s143 host at a seat whose leader sits in the guest's "
                        "bit offers the MOVED mask (Plant Brain's party, GuestSlots 2: 4); an s141 host the raw one (2)")
    p.set_defaults(func=cmd_offer)

    p = sub.add_parser("where", help="[s144] section 7's b6 world / b7 title on a tape's host state frames (where an "
                                     "off-field host says it stands), the old readers unmoved")
    p.add_argument("tape", help="the tape (resolved as `dress` resolves it)")
    p.add_argument("--want", choices=WHERE_WANTS, default="any",
                   help="world / title: the bit rode, never on a real field; none: an s143-or-older host (the "
                        "calibration); any: report only")
    p.set_defaults(func=cmd_where)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
