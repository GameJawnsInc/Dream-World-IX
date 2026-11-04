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

  serve-guest        the HOST game dials in (GET /sess/<code>?role=host). This tool IS its guest: a type-0
                     position frame at 30 Hz on the host's field (the engine's own WriteLoop cadence), optionally a
                     type-3 control frame carrying an s114 fmt-1 report on the host's current battle nonce
                     (``--report live``) -- and it RECORDS every frame the host sends to a tape (``--tap FILE``).
                     [ff9mapkit netsync s157] Its type-0 frame carries the s157 trailing [animFrame][frameN] the way
                     ``--frame`` says (echo: the host's own; none: a pre-s157 37-byte guest; F/N [--frame-step S]: a pinned
                     or stepping frame), with ``--anim`` / ``--loco`` pinning the clip and its class -- the GHOST FRAME's wire
                     bench: the host's ghost of this guest frame-follows exactly these bytes (netsync.ghostframe).
                     [ff9mapkit netsync s166] It sends at the wire the host's FIRST HEADER names (nothing before it;
                     ``--wire N`` pins it), and at v15 every 39-byte type-0 frame carries decision 4's world trailer
                     (``--trailer off``: a capless v15 peer; ``--no-follow``: its flags b0 clear). ``--walk roam`` sends a
                     WALKING v15 guest's world record instead (the follow-out, the load with its seq frozen, then a
                     SYNTHETIC walk over the ROAM route on 9011 until COOP_TAPE_WORLD_ROAM is recorded; ``--scene-at``,
                     ``--state``), and ``--gap-at S --gap-for N`` sends nothing for N s (the host's lane-gap instrument).
  replay-host        the GUEST game dials in (role=guest). This tool replays a recorded host tape with its original
                     timing. ``--blackhole-at T --blackhole-for N`` keeps the TCP open and sends NOTHING for N s -- what
                     a Wi-Fi cut looks like behind the decoupled bridge (netsync_bridge.py's docstring: the loopback hop
                     stays up, frames are dropped, never queued). ``--stop-at T`` ends the host there. Everything the
                     guest sends is logged decoded (position field edges, control menu byte + fmt-1 nonce/boot, commands)
                     and can be taped too. ``--dial URL --code C`` replays through a relay as role=host instead.
                     [ff9mapkit netsync s166] It sends at the wire the GUEST's first header names (``--wire auto``: a v14
                     tape is RESTAMPED to a v15 guest -- byte 1 only, sound under decision 2's law: exactly a capless v15
                     host), as recorded (``--wire tape``: the A-WIRE calibration) or pinned (``--wire 15``), and says so
                     in one line before REPLAY start (GUEST_WIRE_LINE: every T2 leg asserts it before judging).
                     ``--freeze-at T --freeze-for N`` keeps the link open and RE-SENDS the host's last slot frames
                     byte-identical every tick (the writer's real re-send while its game sits in a sync load: the seq
                     frozen) -- the guest-side HANG / "Lost contact" instrument a blackhole cannot be.
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
                     [ff9mapkit netsync s145] ...and each host BATTLE's segment: where the host said it stood before and
                     after it (``--want world-battle``: a world-map battle, b6 on both sides -- the s145 T2 tape's).
                     [ff9mapkit netsync s165] ``--pose`` adds WHERE THE HOST STOOD per state frame: section 0's on-foot anchor
                     (x = s24(64)/256, y = -s16(67)/256, z = s24(69)/256, yaw = b72*360/256), [102] [190] [2..3] [181],
                     section 7's heartbeat and b6/b1, the tape second (``--every S`` thins, every edge kept; ``--near X,Z``
                     adds the TORUS distance) -- the world follow-out's oracle on COOP_TAPE_WORLD_WALK.

THE TAPE (``.f9tape``) -- stdlib, binary, append-only, crash-tolerant (a torn tail is reported, never fatal):
  ``F9TAPE01`` | u32 LE header length | UTF-8 JSON header | records ``[t f64 LE][dir u8][len u32 LE][payload]``.
  ``t`` = seconds since the tape opened (monotonic); ``dir`` = WHO SENT IT: 0 the host, 1 the guest, 2 a note (UTF-8
  text: connections, blackhole edges). ``payload`` = the WebSocket message, UNMASKED = one whole NetSyncWire frame
  ``[0xF9][version][type][len u16 LE][payload]``. A replay sends only the dir-0 records. [ff9mapkit netsync s166] The header's
  ``wire`` is the first HOST frame's version byte (``wires``: each direction's), written from the frames; a pre-s166 writer
  stamped its constant 14 there (every such tape is v14).

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

LAWS IT KEEPS. Wire v14 and v15 (NetSyncWire.Version; [ff9mapkit netsync s166] it reads both and sends the one the game
speaks, never a constant) -- it builds frames exactly as NetSyncWire.BuildFrame/BuildPosPayload and accepts exactly what
NetSyncRelay.ReadLoop accepts; it sends nothing a real peer would not (the fake guest never sends a
battle lane, a roster or a state frame). The containment law is the ENGINE's, not this tool's: a replayed host is a
recording, and the guest still computes nothing of its own. Stdlib only; the WebSocket handshake primitives are the
production bridge's own (``ff9mapkit.netsync_bridge``: read_http_headers / ws_accept / open_upstream), imported, not
copied; the control-frame codec is tools/harness/battlewire.py's. The framing here UNMASKS (the bridge deliberately never
does), which is why it carries its own small codec -- cross-checked in the tests against
tools/netsync-bridge/test_relay_roundtrip.py's send_binary/recv_frame.

HONEST LIMITS. An instrument, calibrated before it judges: a replayed host does not answer the guest (its commands land
nowhere), replaying one tape twice into ONE guest session repeats the host's dialogue epoch (relaunch the guest between
replays), and a tape recorded on one engine build replays that build's wire -- [ff9mapkit netsync s166] restamped UP to a v15
guest (a capless host: never the trailer a v15 host would send), never down. The walking guest record is SYNTHETIC (a constant
y, anim 0 unless --anim) until the ROAM tape is recorded on the s166 host.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import math
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

# ======================================================================================== the wire (NetSyncWire v14 / v15)
# NetSyncSocket.cs NetSyncWire: every message is ONE frame [magic 0xF9][version u8][type u8][len u16 LE][payload].
WIRE_MAGIC = 0xF9
# [ff9mapkit netsync s166] THE v15 LAW (studies/world-coop/S166-DESIGN.md decision 2): NetSyncWire.Version 14 -> 15, and no v14 byte
# changes meaning -- every v15 feature is additive (the type-0 world trailer, decision 4) and gated on the PEER's caps word. An engine
# still rejects every frame whose version byte is not its own (TryParseHeader: the relay drops it silently, TCP disconnects), so a v15
# guest drops every frame of an unrestamped v14 tape and reads "never pairs". This peer READS both, and SENDS at the version the game
# speaks: serve-guest / fake-guest-client at the host's first header, replay-host at the guest's first header (restamping byte 1 of
# a v14 tape -- sound only under the law: a restamped v14 tape is exactly a capless v15 host), or at `--wire N` (the probed
# `netsync.wire`). NO SEND PATH READS A CONSTANT. WIRE_DEFAULT is the PURE codec's default when a caller names no wire (offline
# vectors, synthetic tapes): every tape recorded before s166 is v14.
WIRE_V14, WIRE_V15 = 14, 15
WIRE_VERSIONS = (WIRE_V14, WIRE_V15)
WIRE_DEFAULT = WIRE_V14
#: the version byte's offset in a frame (NetSyncWire.BuildFrame's frame[1] = Version)
WIRE_BYTE = 1
HEADER_SIZE = 5
MAX_PAYLOAD = 8192
TYPE_POS, TYPE_BATTLE, TYPE_COMMAND, TYPE_CONTROL, TYPE_ROSTER, TYPE_STATE, TYPE_ACTION, TYPE_DIALOG = range(8)
TYPE_NAMES = {TYPE_POS: "pos", TYPE_BATTLE: "battle", TYPE_COMMAND: "command", TYPE_CONTROL: "control",
              TYPE_ROSTER: "roster", TYPE_STATE: "state", TYPE_ACTION: "action", TYPE_DIALOG: "dialog"}
#: NetSyncFrames.StaleMs / NetSyncBattle.StaleMs: a lane with no fresh frame this long is gone
STALE_S = 2.0
#: NetSyncRelay.WriteLoop: Thread.Sleep(33) between ticks (~30 Hz)
TICK_S = 0.033
#: [ff9mapkit netsync s166] NetSyncFrames.CollectOutgoing's LATEST SLOTS, in its order (pos, battle, control, roster, state): what the
#: writer re-sends every tick while its game runs no Update (`replay-host --freeze-at`); the queued lanes drain once and are never
#: re-sent. A slot is live at a freeze when its last frame went out within FREEZE_SLOT_LIVE_S before it (a live slot rides every tick).
FREEZE_SLOT_ORDER = (TYPE_POS, TYPE_BATTLE, TYPE_CONTROL, TYPE_ROSTER, TYPE_STATE)
FREEZE_SLOT_LIVE_S = 0.5
#: NetSyncRelay's constructor sentinel: field 65535 = "not on a field yet" (the peer filters it as "not here")
FIELD_SENTINEL = 65535
#: [ff9mapkit netsync s157] serve-guest's EDGE line for the host's type-0 trailer (GuestModel.on_host_frame: logged when the host
#: starts or stops sending it, never per frame) -- the ghost frame's WIRE-half witness in a run's --log: an s157 host always sends
#: 39 B (frameN 0 on its field-0 / 65535 sentinels), an s156-or-older host 37 B (no line: an unframed host is the starting state)
HOST_TRAILER_LINE = "host type-0: {n} B -- the s157 frame bytes (frame {f} of {fn})"
HOST_NO_TRAILER_LINE = "host type-0: {n} B -- no frame bytes"
#: [ff9mapkit netsync s166] the host's v15 WORLD trailer as an EDGE (its kind, place, world, caps or flags changed): a v14 / capless
#: host logs none until a trailer first shows, then "capless" when it goes
HOST_WORLD_TRAILER_LINE = "host world trailer: {text}"
#: ...and the REAL guest's, in replay-host's watch
GUEST_WORLD_TRAILER_LINE = "guest world trailer: {text}"

# BuildPosPayload: field u16, anim u16, model u16, meshVis u16, loco u8, pos 3f, rot 4f (x y z w) -- 37 bytes, LE.
_POS = struct.Struct("<HHHHB3f4f")
POS_LEN = _POS.size
# [ff9mapkit netsync s157] ...then the sender's controlled actor's animFrame and frameN as TRAILING bytes, [animFrame u8][frameN u8]
# -> 39 bytes (NetSyncWire.PosLenFrame; POS_LEN stays the 37-byte record every v14 reader requires, NetSyncWire.PosLenBase). No
# version bump: a v14 reader takes the first 37 bytes and ignores the rest; an s157 reader reads a 37-byte frame as "no frame".
# An s157 engine ALWAYS writes 39 (frameN 0 = no frame: its field-0 / 65535 sentinels); build_pos_payload writes 37 unless a
# frame is given -- the pre-s157 peer, the wire half's calibration red.
_POS_FRAME = struct.Struct("<BB")
POS_FRAME_LEN = POS_LEN + _POS_FRAME.size
# NetSyncBattle.SampleOwnBattle / ParseView's head: seq u16, mapNo u16, guestSlots u8, patNum u8, startType u8,
# flags u8, nonce u8, songId u16 (v10), unitCount u8 -- the unit records and the 0xB5 trailer follow.
_BATTLE_HEAD = struct.Struct("<HHBBBBBHB")
BATTLE_HEAD_LEN = _BATTLE_HEAD.size


def build_frame(wtype: int, payload=b"", wire: int = WIRE_DEFAULT) -> bytes:
    """NetSyncWire.BuildFrame: ``[0xF9][wire][type][len lo][len hi]`` + payload. A u16 length is all the header holds.
    [ff9mapkit netsync s166] ``wire`` is the version byte (the codec's default is the v14 tape wire; every SEND path passes the
    version the game speaks)."""
    payload = bytes(payload or b"")
    n = len(payload)
    if n > 0xFFFF:
        raise ValueError(f"a NetSyncWire payload of {n} bytes does not fit the u16 length")
    return bytes([WIRE_MAGIC, int(wire) & 0xFF, wtype & 0xFF, n & 0xFF, (n >> 8) & 0xFF]) + payload


def frame_wire(message) -> int | None:
    """[ff9mapkit netsync s166] The version byte of a message that starts with a NetSyncWire header (the magic, >= 5 bytes) -- any
    version, accepted or not (the peer-version line names it); None = no header at all (not our magic, or short)."""
    data = bytes(message or b"")
    if len(data) < HEADER_SIZE or data[0] != WIRE_MAGIC:
        return None
    return data[WIRE_BYTE]


def parse_frame(message, versions=WIRE_VERSIONS) -> tuple | None:
    """NetSyncRelay.ReadLoop's acceptance of one WS message: TryParseHeader (magic, the version, len <= MaxPayload) AND
    the header's length equal to the rest of the message. -> ``(type, payload)``, or None (a foreign or old peer's
    frame, which the engine drops silently). [ff9mapkit netsync s166] ``versions``: the version bytes accepted -- this peer reads
    v14 and v15 (WIRE_VERSIONS); an ENGINE accepts exactly its own one (pass ``(v,)`` to read as it reads)."""
    data = bytes(message or b"")
    if len(data) < HEADER_SIZE or data[0] != WIRE_MAGIC or data[1] not in versions:
        return None
    n = data[3] | (data[4] << 8)
    if n > MAX_PAYLOAD or n != len(data) - HEADER_SIZE:
        return None
    return data[2], data[HEADER_SIZE:]


def restamp(message, wire: int) -> bytes:
    """[ff9mapkit netsync s166] ``message`` with its version byte set to ``wire`` (a frame that does not start with our header is
    returned unchanged). Sound only UPWARD under decision 2's law: a v14 frame's every byte keeps its meaning under v15, so a
    restamped v14 frame is exactly a capless v15 peer's (no trailer). Every other byte is left byte-identical."""
    data = bytes(message or b"")
    if frame_wire(data) is None:
        return data
    return data[:WIRE_BYTE] + bytes([int(wire) & 0xFF]) + data[WIRE_BYTE + 1:]


def frame_header_text(message, versions=WIRE_VERSIONS) -> str:
    """A rejected message's first bytes, for the one log line that names WHY (magic / version / length)."""
    data = bytes(message or b"")
    if len(data) < HEADER_SIZE:
        return f"{len(data)} byte(s), shorter than the 5-byte header"
    n = data[3] | (data[4] << 8)
    speaks = "/".join(str(v) for v in versions)
    return (f"magic 0x{data[0]:02X} version {data[1]} type {data[2]} len {n} in a {len(data)}-byte message"
            + (f" -- a different wire version (this side reads {speaks}: mixed engine builds never sync)"
               if data[0] == WIRE_MAGIC and data[1] not in versions else ""))


def build_pos_payload(field: int, anim: int = 0, model: int = 0, mesh_vis: int = 0, loco: int = 0,
                      pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0, 1.0), anim_frame=None, frame_n=None) -> bytes:
    """NetSyncWire.BuildPosPayload (37 bytes; ``(UInt16)field`` truncates as the C# cast does). [ff9mapkit netsync s157] With
    ``anim_frame`` or ``frame_n`` given (the other None reads 0), the s157 record: + ``[animFrame u8][frameN u8]``, 39 bytes --
    what an s157 engine always writes; with neither, the pre-s157 37 bytes."""
    base = _POS.pack(int(field) & 0xFFFF, int(anim) & 0xFFFF, int(model) & 0xFFFF, int(mesh_vis) & 0xFFFF,
                     int(loco) & 0xFF, *(float(v) for v in pos), *(float(v) for v in rot))
    if anim_frame is None and frame_n is None:
        return base
    return base + _POS_FRAME.pack(int(anim_frame or 0) & 0xFF, int(frame_n or 0) & 0xFF)


def parse_pos_payload(payload) -> dict | None:
    """NetSyncWire.TryParsePosPayload: None under 37 bytes. [ff9mapkit netsync s157] ``has_frame`` = the payload carries the
    s157 trailer (39 bytes or more: ``anim_frame`` / ``frame_n``, both None on a 37-byte pre-s157 frame); bytes past the 39th
    are ignored by the s157 record, as a v14 engine ignores them. [ff9mapkit netsync s166] ``trailer`` = the v15 WORLD trailer at
    byte 39 (:func:`parse_world_trailer`; None = a capless peer: absent, tfmt 0 or short) and ``length`` the payload's size --
    the s157 record's every byte keeps its meaning beside it."""
    data = bytes(payload or b"")
    if len(data) < POS_LEN:
        return None
    f, anim, model, mesh, loco, px, py, pz, rx, ry, rz, rw = _POS.unpack_from(data)
    has = len(data) >= POS_FRAME_LEN
    af, fn = _POS_FRAME.unpack_from(data, POS_LEN) if has else (None, None)
    return {"field": f, "anim": anim, "model": model, "mesh_vis": mesh, "loco": loco,
            "pos": (px, py, pz), "rot": (rx, ry, rz, rw), "has_frame": has, "anim_frame": af, "frame_n": fn,
            "trailer": parse_world_trailer(data), "length": len(data)}       # [ff9mapkit netsync s166]


# ======================================================================================== [ff9mapkit netsync s166] the world trailer
#: [ff9mapkit netsync s166] THE WORLD TRAILER ON TYPE 0 (S166-DESIGN.md decision 4): the 39-byte s157 record is unchanged (Field stays 0
#: on the world map on both roles: eight readers take it as a field id) and a trailer follows it, LITTLE-ENDIAN, at payload byte 39:
#:   39 tfmt u8 (1; 0 or absent = a capless peer) | 40-41 caps u16 (decision 2's bits) | 42-43 seq u16 (+1 per sender Update; a
#:   re-send repeats it) | 44-47 ms u32 (the sender's NowMs, low 32 bits: only differences are used) | 48 place u8 | 49 state u8 |
#:   50 why u8 (high nibble the rule, low nibble its refusal code) | 51-52 world u16 (the live wldMapNo on place 4, else 0) |
#:   53-64 x, y, z f32 (w_moveActorPtr.RealPosition, canonical) | 65-80 rot 4 x f32 (that actor's transform.rotation) | 81 mode u8
#:   ([190]) | 82-83 model u16 | 84-85 anim u16 | 86 animFrame u8 | 87 frameN u8 (the walker's own) | 88-91 digest u32 (0 until
#:   s167's fingerprint) | 92 worldTps u8 (always filled) | 93 flags u8 (b0 I follow; b1-b7 zero)  -- 94 bytes in all.
#: The world block (51-87) is valid only on place 4 with a real walker; elsewhere the sender zeroes it.
TRAILER_AT = POS_FRAME_LEN
TRAILER_FMT = 1
_TRAILER = struct.Struct("<BHHIBBBH3f4fBHHBBIBB")
TRAILER_LEN = _TRAILER.size
#: the whole v15 type-0 payload with a fmt-1 trailer (the s157 record + the trailer)
POS_V15_LEN = TRAILER_AT + TRAILER_LEN
#: decision 2's caps bits (the PEER's capability word; re-read from every sample, never latched per link)
CAP_WORLD_POSE, CAP_WORLD_FP, CAP_COMMS, CAP_GUEST_MENU, CAP_CMD_V2 = 0x01, 0x02, 0x04, 0x08, 0x10
#: the place byte (48)
PLACE_NONE, PLACE_FIELD, PLACE_TRANSITION, PLACE_WORLD_LOADING, PLACE_WORLD, PLACE_BATTLE, PLACE_DIORAMA = range(7)
PLACE_NAMES = {PLACE_NONE: "none/title", PLACE_FIELD: "field live", PLACE_TRANSITION: "scene transition",
               PLACE_WORLD_LOADING: "world loading", PLACE_WORLD: "world live", PLACE_BATTLE: "battle",
               PLACE_DIORAMA: "world diorama"}
#: the state byte (49): b0 frozen (WorldFreezeNow), b1 walking free, b2 user control, b3 own full map open, b4 content mismatch,
#: b5 world-out in flight, b6 scene, b7 walker visible
(ST_FROZEN, ST_WALKING, ST_CONTROL, ST_FULLMAP, ST_MISMATCH, ST_WORLDOUT, ST_SCENE, ST_VISIBLE) = (1 << i for i in range(8))
#: the flags byte (93): b0 I follow (`_followHost` on the client role)
FLAG_FOLLOW = 0x01


def build_world_trailer(*, caps: int = CAP_WORLD_POSE, seq: int = 0, ms: int = 0, place: int = PLACE_NONE, state: int = 0,
                        why: int = 0, world: int = 0, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0, 0.0), mode: int = 0, model: int = 0,
                        anim: int = 0, anim_frame: int = 0, frame_n: int = 0, digest: int = 0, world_tps: int = 0, flags: int = 0,
                        tfmt: int = TRAILER_FMT) -> bytes:
    """[ff9mapkit netsync s166] Decision 4's trailer (55 bytes, little-endian), each field truncated to its width as the C# casts do.
    It writes what it is given: zeroing the world block off place 4 is the SENDER's rule (:func:`world_block_zeroed`)."""
    return _TRAILER.pack(int(tfmt) & 0xFF, int(caps) & 0xFFFF, int(seq) & 0xFFFF, int(ms) & 0xFFFFFFFF, int(place) & 0xFF,
                         int(state) & 0xFF, int(why) & 0xFF, int(world) & 0xFFFF, *(float(v) for v in pos),
                         *(float(v) for v in rot), int(mode) & 0xFF, int(model) & 0xFFFF, int(anim) & 0xFFFF,
                         int(anim_frame) & 0xFF, int(frame_n) & 0xFF, int(digest) & 0xFFFFFFFF, int(world_tps) & 0xFF,
                         int(flags) & 0xFF)


def world_block_zeroed(fields: dict) -> dict:
    """[ff9mapkit netsync s166] ``fields`` (build_world_trailer's keywords) with the world block (51-87: world, pos, rot, mode, model,
    anim, animFrame, frameN) zeroed unless the place is 4 -- the sender's rule (inside a diorama the walker belongs to an unloaded
    scene)."""
    out = dict(fields)
    if out.get("place") != PLACE_WORLD:
        out.update(world=0, pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0, 0.0), mode=0, model=0, anim=0, anim_frame=0, frame_n=0)
    return out


#: [ff9mapkit netsync s166] NetSyncWorldWalk.WriteTrailer with Fmt 0 (`worldwalk pose off`): the 55 bytes ALL zero -- a v15 peer whose
#: payload stays 94 B but reads capless (tfmt 0), "an s165-shaped v15 peer"
TFMT0_TRAILER = bytes(TRAILER_LEN)
#: serve-guest's `--trailer` modes: auto (decision 4's fmt 1), tfmt0 (the engine's `pose off`: 94 B, capless), off (39 B, no trailer:
#: a restamped v14 tape, or an A2-only engine's SetLocal frames)
TRAILER_MODES = ("auto", "tfmt0", "off")


def keepalive_trailer(world_tps: int) -> bytes:
    """[ff9mapkit netsync s166] NetSyncWire.KeepaliveTrailer: the trailer on the relay constructor's 65535 sentinel (every v15 frame
    carries one, the sentinel included -- decision 2): tfmt 1, caps OwnCaps (b0), place 0, seq / ms / state / why / flags 0, the
    world block and the digest zeroed, worldTps the sender's [Graphics] WorldTPS clamped to 0..255 (NetSyncWirePeer.OwnWorldTps).
    The writer re-sends that slot unchanged until the game's first SetLocal, so its seq never advances."""
    return build_world_trailer(caps=CAP_WORLD_POSE, place=PLACE_NONE, world_tps=max(0, min(255, int(world_tps))))


def keepalive_payload(world_tps: int) -> bytes:
    """[ff9mapkit netsync s166] The relay keepalive's whole v15 type-0 payload (94 B): BuildPosPayload(65535, 0, 0, 0, 0, zero,
    identity, 0, 0) -- the s157 record byte for byte -- then :func:`keepalive_trailer`."""
    return build_pos_payload(FIELD_SENTINEL, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0) + keepalive_trailer(world_tps)


def trailer_kind(payload) -> str:
    """[ff9mapkit netsync s166] What sits at a type-0 payload's byte 39: ``absent`` (39 bytes or fewer: an s157-s165 peer, a
    restamped v14 tape), ``tfmt0`` (a v15 peer with its pose off), ``short`` (tfmt >= 1 but under the 94 bytes fmt 1 needs) or
    ``fmt1`` (decision 4's whole trailer; a LATER fmt is read forward: its first 55 bytes are fmt 1's)."""
    data = bytes(payload or b"")
    if len(data) <= TRAILER_AT:
        return "absent"
    if data[TRAILER_AT] == 0:
        return "tfmt0"
    return "fmt1" if len(data) >= POS_V15_LEN else "short"


def parse_world_trailer(payload) -> dict | None:
    """[ff9mapkit netsync s166] The FORWARD parse of decision 4's trailer off a type-0 payload: None for a capless peer (absent, tfmt 0
    or short -- :func:`trailer_kind`), else every field by name plus ``yaw`` (the rotation's heading in degrees, [0, 360)),
    ``block_valid`` (place 4, caps b0 and a nonzero world: the world block means something -- NetSyncWorldWalk.WorldTrailer.BlockValid,
    where world 0 on place 4 is a sender that ZEROED the block: no real walker, the dummy or the bee scene), ``follows`` (flags b0),
    ``why_rule`` / ``why_code`` (the why byte's two nibbles). Bytes past the 94th are ignored (a later fmt's additions)."""
    data = bytes(payload or b"")
    if trailer_kind(data) != "fmt1":
        return None
    (tfmt, caps, seq, ms, place, state, why, world, x, y, z, rx, ry, rz, rw, mode, model, anim, af, fn, digest, tps,
     flags) = _TRAILER.unpack_from(data, TRAILER_AT)
    return {"tfmt": tfmt, "caps": caps, "seq": seq, "ms": ms, "place": place, "state": state, "why": why, "world": world,
            "pos": (x, y, z), "rot": (rx, ry, rz, rw), "mode": mode, "model": model, "anim": anim, "anim_frame": af,
            "frame_n": fn, "digest": digest, "world_tps": tps, "flags": flags, "yaw": quat_yaw((rx, ry, rz, rw)),
            "block_valid": place == PLACE_WORLD and bool(caps & CAP_WORLD_POSE) and world != 0,     # the engine's BlockValid
            "follows": bool(flags & FLAG_FOLLOW),
            "why_rule": why >> 4, "why_code": why & 0x0F}


def quat_yaw(rot) -> float:
    """[ff9mapkit netsync s166] A rotation's heading about +y in degrees, [0, 360) (Unity's eulerAngles.y for a level body: 0 faces
    +z, 90 faces +x); 0.0 for the zero quaternion (a zeroed world block)."""
    x, y, z, w = (float(v) for v in rot)
    if x == y == z == w == 0.0:
        return 0.0
    return math.degrees(math.atan2(2.0 * (w * y + x * z), 1.0 - 2.0 * (y * y + x * x))) % 360.0


def yaw_quat(deg: float) -> tuple:
    """[ff9mapkit netsync s166] :func:`quat_yaw`'s inverse for a level body: the quaternion (x, y, z, w) turned ``deg`` about +y."""
    h = math.radians(float(deg)) / 2.0
    return (0.0, math.sin(h), 0.0, math.cos(h))


def trailer_text(tr: dict | None, payload=None) -> str:
    """[ff9mapkit netsync s166] One trailer for a log line: ``place 4 (world live) world 9011 at (68.0, -444.0) yaw 90 mode 0 caps
    0x0001 seq 12 state 0x86 flags 0x01``; a capless peer reads ``capless (<kind>, <n> B)``."""
    if tr is None:
        data = bytes(payload or b"")
        return f"capless ({trailer_kind(data)}, {len(data)} B)"
    text = f"place {tr['place']} ({PLACE_NAMES.get(tr['place'], '?')})"
    if tr["place"] == PLACE_WORLD:
        x, _y, z = tr["pos"]
        text += f" world {tr['world']} at ({x:.1f}, {z:.1f}) yaw {tr['yaw']:.0f} mode {tr['mode']}"
    return text + f" caps 0x{tr['caps']:04X} seq {tr['seq']} state 0x{tr['state']:02X} flags 0x{tr['flags']:02X}"


def build_pos_frame(field: int, wire: int = WIRE_DEFAULT, trailer: bytes = b"", **kw) -> bytes:
    """[ff9mapkit netsync s166] + ``wire`` (the version byte) and ``trailer`` (decision 4's bytes, appended after a 39-byte record:
    a trailer needs the s157 bytes in front of it, so asking for one on a 37-byte record raises)."""
    payload = build_pos_payload(field, **kw)
    if trailer:
        if len(payload) != TRAILER_AT:
            raise ValueError("a world trailer rides after the 39-byte s157 record: give anim_frame / frame_n")
        payload += bytes(trailer)
    return build_frame(TYPE_POS, payload, wire=wire)


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
            return (f"{name} field {p['field']} model {p['model']} anim {p['anim']} at ({x:.0f}, {y:.0f}, {z:.0f})"
                    + (f" frame {p['anim_frame']}/{p['frame_n']}" if p["has_frame"] else "")    # [ff9mapkit netsync s157]
                    + (f" | trailer {trailer_text(p['trailer'])}" if p["trailer"] is not None else ""))   # [ff9mapkit netsync s166]
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
        # [ff9mapkit netsync s166] THE TAPE HEADER RECORDS THE WIRE FROM THE FRAMES, never a constant: ``wire`` is the first HOST
        # frame's version byte (what a replay of this tape sends unrestamped), ``wires`` each direction's first. Both are null until
        # that frame is written, then the header is rewritten IN PLACE (a number is never longer than ``null``, and JSON ignores the
        # trailing pad), so a killed run keeps a readable header and :func:`tape_wire` still reads the frames.
        header = {"tool": "coop_peer", "format": TAPE_FORMAT, "wire": None, "mode": mode,
                  "wires": {DIR_NAMES[DIR_HOST]: None, DIR_NAMES[DIR_GUEST]: None},
                  "started": datetime.datetime.now().isoformat(timespec="milliseconds"),
                  "dirs": {str(k): v for k, v in DIR_NAMES.items()}}
        header.update(extra or {})
        self.header = header
        blob = json.dumps(header, sort_keys=True).encode("utf-8")
        self._hlen = len(blob)
        self._f = open(self.path, "wb")
        self._f.write(TAPE_MAGIC + struct.pack("<I", len(blob)) + blob)
        self._t0 = clock()
        self._last_flush = self._t0
        self.records = 0
        self.bytes = 0

    def _note_wire(self, direction: int, data: bytes) -> None:
        """[ff9mapkit netsync s166] (lock held) The first framed record of each direction sets ``wires`` (and the host's ``wire``);
        the header is rewritten in place, padded to its original length."""
        wires = self.header.get("wires")
        name = DIR_NAMES.get(direction)
        if not isinstance(wires, dict) or name not in wires or wires[name] is not None:
            return
        v = frame_wire(data)
        if v is None:
            return
        wires[name] = v
        if direction == DIR_HOST and self.header.get("wire") is None:
            self.header["wire"] = v
        blob = json.dumps(self.header, sort_keys=True).encode("utf-8")
        if len(blob) > self._hlen:                         # never: a number is shorter than null -- keep the old header
            return
        at = self._f.tell()
        self._f.seek(len(TAPE_MAGIC) + 4)
        self._f.write(blob + b" " * (self._hlen - len(blob)))
        self._f.seek(at)

    def now(self) -> float:
        return self._clock() - self._t0

    def write(self, direction: int, payload, t: float | None = None) -> float:
        data = bytes(payload or b"")
        with self._lock:
            if self._f is None:
                return 0.0
            now = self._clock()
            stamp = (now - self._t0) if t is None else t
            if direction != DIR_NOTE:
                self._note_wire(direction, data)          # [ff9mapkit netsync s166] the header's wire, from the frames
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
    """The dir-0 records that parse as v14 or v15 frames, as ``(record, type, payload)`` (what a replay sends)."""
    out = []
    for r in records:
        if r.dir == DIR_HOST:
            got = parse_frame(r.payload)
            if got is not None:
                out.append((r, got[0], got[1]))
    return out


def tape_wire(records, direction: int = DIR_HOST) -> int | None:
    """[ff9mapkit netsync s166] The wire a tape's ``direction`` speaks, read off ITS FRAMES (the first record carrying our header's
    magic): the version a replay sends unrestamped. None = no such frame. Never the header's ``wire`` (a pre-s166 writer stamped
    its constant there)."""
    for r in records:
        if r.dir == direction:
            v = frame_wire(r.payload)
            if v is not None:
                return v
    return None


#: [ff9mapkit netsync s166] `replay-host --wire`: auto (default: the guest's first header), tape (as recorded: the A-WIRE row's
#: unrestamped calibration) or a version (the probed `netsync.wire`)
REPLAY_WIRE_MODES = ("auto", "tape") + tuple(str(v) for v in WIRE_VERSIONS)
#: the line replay-host logs once it knows what the guest speaks, before REPLAY start -- every T2 leg asserts it before judging
#: (_coop_peer_bench.wire_gate): a v15 guest dropping every v14 frame reads "never pairs", a red easy to misread as a regression
GUEST_WIRE_LINE = "guest header: wire {guest} -- the replay sends wire {send} ({how})"
#: ...and the fake guest's (serve-guest / fake-guest-client), once it knows what the host speaks
HOST_WIRE_LINE = "host header: wire {host} -- this fake guest sends wire {send} ({how})"


def replay_send_wire(mode, guest, tape) -> tuple:
    """[ff9mapkit netsync s166] (PURE) What replay-host sends, given ``mode`` ('auto' | 'tape' | a version), the GUEST's first header
    version ``guest`` (None = its first message carried none) and the tape's own ``tape`` (:func:`tape_wire`) -> ``(send, how)``:
    ``send`` the version byte every replayed frame carries, ``how`` the reason, ending in the warning when the guest will drop
    them. A restamp is only ever UPWARD (decision 2's law covers v14 -> v15; a v15 frame's trailer has no v14 meaning), so 'auto'
    never restamps down, and an explicit lower version is refused before listening (:func:`_replay_plan`)."""
    drop = (lambda send: "" if guest is None or guest == send else
            f" -- the guest speaks {guest}: it DROPS every frame and never pairs")
    if mode == "tape":
        return tape, "as recorded, --wire tape" + drop(tape)
    if mode != "auto":
        want = int(mode)
        how = "pinned --wire, as recorded" if want == tape else f"pinned --wire, restamped from the tape's {tape}"
        return want, how + drop(want)
    if guest is None:
        return tape, "as recorded: the guest's first message carried no NetSyncWire header" + drop(tape)
    if guest == tape:
        return tape, "as recorded"
    if guest in WIRE_VERSIONS and tape in WIRE_VERSIONS and guest > tape:
        return guest, f"restamped from the tape's {tape} to the guest's own"
    return tape, f"as recorded: the tape's {tape} cannot be restamped to the guest's {guest}" + drop(tape)


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

# ---------------------------------------------------------------------------------------- [ff9mapkit netsync s166] the walking v15 guest
#: [ff9mapkit netsync s166] THE ROAM ROUTE, SYNTHETIC (S166-DESIGN.md "Tapes": COOP_TAPE_WORLD_ROAM -- 6603, the walk out, the blocks, 3 s
#: at FS_LANDING, on-foot legs with stands, one leg across the x seam, then ICE_TILE for 20 s). The real tape is recorded on the s166 host
#: only (THE RECORDER DIALS THE OWNER); until then serve-guest's `--walk roam` walks these waypoints ``(x, z, stand seconds)`` on 9011 in
#: canonical world units: FS_LANDING (68, -444), two legs west with stands, one leg ACROSS the x seam (x 14 -> 1512 the short way:
#: 38 u west through x 0), then ICE_TILE (1197.37, -796.7). What it is NOT: terrain-true (y is one constant: the ghost's body takes
#: the wire's y), clip-true (the anim id is --anim's, else 0) or a recording of any walker.
FS_LANDING = (68.0, -444.0)
ICE_TILE = (1197.37, -796.7)
WORLD_ROAM_ROUTE = ((68.0, -444.0, 3.0), (44.0, -470.0, 1.5), (14.0, -512.0, 1.5), (1512.0, -548.0, 1.5),
                    (1197.37, -796.7, 20.0))
#: the synthetic walker's speed (world units a second) and the world it walks (kit 9011: the ROAM tape's)
WALK_UPS = 24.0
WALK_WORLD = 9011
#: decision 11: an undressed walker wears its own world model -- Dagger (309) on 9002, Zidane (310) on 9010 / 9011
WORLD_MODEL = {9002: 309}
WORLD_MODEL_DEFAULT = 310
#: the walking record's phases before it walks: the follow-out (place 2, state b5) and the world load (place 3: the first frame is
#: fresh, then the writer RE-SENDS it with a frozen seq -- A GAME PUBLISHES NOTHING DURING ITS OWN SYNC LOAD), in seconds
WALK_OUT_S = 1.0
WALK_LOAD_S = 2.0
#: the walking record's state byte by default: b1 walking free, b2 user control, b7 walker visible (a released guest's shape: b0
#: clear; `--state` sets any byte, e.g. 0x85 for a frozen one)
WALK_STATE = ST_WALKING | ST_CONTROL | ST_VISIBLE
#: the [Graphics] WorldTPS the fake guest reports (the trailer always fills it; the stock default)
WALK_TPS = 20


def torus_wrap(x: float, z: float) -> tuple:
    """[ff9mapkit netsync s166] (PURE) A world point folded onto the torus as RealPosition reports it: x in [0, 1536), z in (-1280, 0]."""
    xw = float(x) % 1536.0
    zw = -((-float(z)) % 1280.0)
    return xw, (0.0 if zw == 0.0 else zw)


def walk_pose(route, ups: float, s: float) -> tuple:
    """[ff9mapkit netsync s166] (PURE) Where a walker following ``route`` ((x, z, stand) waypoints) at ``ups`` units a second stands
    ``s`` seconds in: ``(x, z, yaw, moving)``, folded onto the torus. It stands ``stand`` seconds at each waypoint, then walks to the
    next the SHORT way round the torus (a leg across a seam crosses it); past the end it stands at the last point. ``yaw`` faces the
    current (or the last) leg; 0 before the first."""
    pts = [(float(x), float(z), float(st)) for x, z, st in route]
    if not pts:
        return 0.0, 0.0, 0.0, False
    s, yaw = max(0.0, float(s)), 0.0
    for i, (x, z, stand) in enumerate(pts):
        if s < stand or i == len(pts) - 1:
            return torus_wrap(x, z) + (yaw, False)
        s -= stand
        nx, nz, _ = pts[i + 1]
        dx = (nx - x + 768.0) % 1536.0 - 768.0              # the short way round: dx in [-768, 768), dz in [-640, 640)
        dz = (nz - z + 640.0) % 1280.0 - 640.0
        dist = math.hypot(dx, dz)
        yaw = math.degrees(math.atan2(dx, dz)) % 360.0
        leg = dist / ups if ups > 0 else float("inf")
        if s < leg:
            k = s / leg
            return torus_wrap(x + dx * k, z + dz * k) + (yaw, True)
        s -= leg
    return torus_wrap(pts[-1][0], pts[-1][1]) + (yaw, False)


def walker_heading(travel_deg: float) -> float:
    """[ff9mapkit netsync s166] (PURE) The heading a walker TRAVELLING along ``travel_deg`` (atan2(dx, dz), walk_pose's yaw) faces: its
    transform.rotation's eulerAngles.y, travel + 180 mod 360 (NetSyncWorldWalk.WalkerYaw; battlewire.ww_walker_yaw). The trailer
    carries THIS (A3's contract): a synthetic record that sent the travel heading would face its ghost backwards."""
    return (float(travel_deg) + 180.0) % 360.0


def in_windows(t: float, windows) -> bool:
    """[ff9mapkit netsync s166] (PURE) ``t`` inside any ``(at, for)`` window, ``[at, at + for)``."""
    return any(float(a) <= t < float(a) + float(n) for a, n in windows)


class WorldWalkPlan:
    """[ff9mapkit netsync s166] serve-guest's WALKING v15 GUEST RECORD (PURE: the session second in, the trailer's fields out). From
    the session's first send: the follow-out (place 2, state b5) for ``out_s``, the world load (place 3) for ``load_s``, then the
    world live (place 4) walking ``route`` at ``ups`` on ``world`` with ``state`` -- b6 scene (and b2 control cleared) inside
    ``scenes`` windows. ``follow`` False clears flags b0 (``--no-follow``: a peer that does not follow gets no host lines and no
    ghost). The 39-byte record in front stays the world sentinel every v15 engine sends there: field 0, a zero pose, identity
    rotation, frame 0 of 0."""

    def __init__(self, *, route=WORLD_ROAM_ROUTE, ups: float = WALK_UPS, world: int = WALK_WORLD, model: int | None = None,
                 anim: int = 0, out_s: float = WALK_OUT_S, load_s: float = WALK_LOAD_S, state: int = WALK_STATE, scenes=(),
                 follow: bool = True, y: float = 0.0, tps: int = WALK_TPS, caps: int = CAP_WORLD_POSE):
        self.route = tuple(route)
        self.ups = float(ups)
        self.world = int(world)
        self.model = WORLD_MODEL.get(self.world, WORLD_MODEL_DEFAULT) if model is None else int(model)
        self.anim = int(anim)
        self.out_s, self.load_s = float(out_s), float(load_s)
        self.state = int(state) & 0xFF
        self.scenes = tuple(scenes)
        self.follow = bool(follow)
        self.y = float(y)
        self.tps = int(tps)
        self.caps = int(caps)

    def phase(self, s: float) -> str:
        """'out' | 'load' | 'world' at session second ``s``."""
        if s < self.out_s:
            return "out"
        return "load" if s < self.out_s + self.load_s else "world"

    def fields(self, s: float) -> dict:
        """build_world_trailer's keywords at session second ``s`` (no seq / ms: the sender stamps those), the world block zeroed
        off place 4."""
        ph = self.phase(s)
        flags = FLAG_FOLLOW if self.follow else 0
        base = {"caps": self.caps, "world_tps": self.tps, "flags": flags}
        if ph == "out":
            return world_block_zeroed(dict(base, place=PLACE_TRANSITION, state=ST_WORLDOUT))
        if ph == "load":
            return world_block_zeroed(dict(base, place=PLACE_WORLD_LOADING, state=0))
        x, z, yaw, _moving = walk_pose(self.route, self.ups, s - self.out_s - self.load_s)
        state = self.state
        if in_windows(s, self.scenes):
            state = (state | ST_SCENE) & ~ST_CONTROL & 0xFF
        # [ff9mapkit netsync s166] the trailer's rot is the walker's transform.rotation: its HEADING, travel + 180 (NetSyncWorldWalk.
        # WalkerYaw: a walker at theta moves along (-sin, -cos)) -- walk_pose's yaw is the TRAVEL heading, 180 degrees off (A3's contract)
        return dict(base, place=PLACE_WORLD, state=state, world=self.world, pos=(x, self.y, z), rot=yaw_quat(walker_heading(yaw)),
                    mode=0, model=self.model, anim=self.anim, anim_frame=0, frame_n=0)

    def text(self) -> str:
        return (f"walking v15 guest on {self.world} (model {self.model}): {self.out_s:g} s following out, {self.load_s:g} s loading, "
                f"then {len(self.route)} waypoint(s) at {self.ups:g} u/s, state 0x{self.state:02X}"
                + (f", scene windows {list(self.scenes)}" if self.scenes else "") + ("" if self.follow else ", NOT following"))


class GuestModel:
    """What the fake guest knows of the host and what it answers, as pure state (the clock is passed in):

    * type 0 -- every tick, ``[field][anim][model][meshVis][loco][pos][rot]``: ``field`` None mirrors the host's own
      field (0 while it fights, the 65535 sentinel until its first frame -- what a following guest's diorama and a
      pre-field engine send), with its model/anim/loco and its position plus ``offset``; an int pins a field.
      [ff9mapkit netsync s157] + the trailing ``[animFrame][frameN]`` per ``frame`` (see __init__), and ``anim`` / ``loco``
      pin those two bytes instead of mirroring the host's.
    * type 3 -- only while the host's battle lane is LIVE (its seq advanced within 2 s: NetSyncBattle.Pump's freshness
      rule, keyed on the seq, not on receipt) -- the guest Pump's ``live && !inBattle`` branch. ``report`` None sends
      none; ``"legacy"`` the pre-R3 2-byte ``[0][menu]``; a boot state the s114 ``[0][menu][1][nonce][boot]`` naming
      the host's CURRENT nonce. ``live_after`` > 0 reports BOOTING for that long after a nonce first appears (a diorama
      booting), then ``report``."""

    def __init__(self, *, field: int | None = None, offset=(0.0, 0.0, 0.0), report=None, menu: int = 0,
                 live_after: float = 0.0, anim: int | None = None, loco: int | None = None, frame="echo",
                 frame_step: int = 0, trailer: str = "auto", follow: bool = True, walk: WorldWalkPlan | None = None,
                 gaps=()):
        self._lock = threading.Lock()
        self.field = field
        # [ff9mapkit netsync s166] THE v15 RECORD: ``trailer`` "auto" appends decision 4's world trailer to every 39-byte type-0 frame
        # sent at wire >= 15 (a v15 engine always does: place 1 on a real field, else 0, the world block zeroed), "tfmt0" the engine's
        # `pose off` trailer (55 zero bytes: a capless v15 peer at 94 B; the 65535 sentinel keeps the relay keepalive's), "off" never (a
        # capless v15 peer: what a restamped v14 tape is); ``follow`` False clears its flags b0 (`--no-follow`); ``walk`` (a WorldWalkPlan)
        # replaces the mirrored record with the walking guest's world record; ``gaps`` ((at, for) session seconds) send NOTHING
        # (`--gap-at`: the arrivals stop, the host's lane-gap line's instrument). seq +1 per built frame, ms the session clock.
        self.trailer = trailer
        self.follow = bool(follow)
        self.walk = walk
        self.gaps = tuple(gaps)
        self._seq = 0
        self._t0 = None                                    # the session clock at the first outgoing() (the walk's zero)
        self._load_frame = None                            # the frozen frame a walk's sync load re-sends
        self.host_trailer_key = None                       # the host's world-trailer edge (kind, place, world, caps, flags)
        # [ff9mapkit netsync s157] THE GHOST FRAME's wire-half knobs (the HOST's ghost of this guest frame-follows what they send):
        # ``anim`` / ``loco`` None mirror the host's own, an int pins it (a ladder clip id; loco 0 = Other, the only class an s157
        # ghost follows); ``frame`` "echo" sends the host's own trailer when its frame had one (a pre-s157 host: 37 bytes, as
        # before), "none" always 37 bytes (a pre-s157 guest: the calibration red), (f, n) a pinned frame, advanced by
        # ``frame_step`` per tick (30 Hz) mod n -- negative runs backwards, so it crosses the seam both ways.
        self.anim = None if anim is None else int(anim) & 0xFFFF
        self.loco = None if loco is None else int(loco) & 0xFF
        self.frame = frame
        self.frame_step = int(frame_step)
        self._frame_now = int(frame[0]) if isinstance(frame, tuple) else None
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
                    # [ff9mapkit netsync s157] the trailer's EDGE (HOST_TRAILER_LINE / HOST_NO_TRAILER_LINE), never per frame
                    if p["has_frame"] != bool(self.host_pos and self.host_pos.get("has_frame")):
                        ev.append(HOST_TRAILER_LINE.format(n=len(payload), f=p["anim_frame"], fn=p["frame_n"]) if p["has_frame"]
                                  else HOST_NO_TRAILER_LINE.format(n=len(payload)))
                    # [ff9mapkit netsync s166] the host's WORLD trailer as an EDGE (kind, place, world, caps, flags): never per frame
                    tr = p["trailer"]
                    key = (trailer_kind(payload),) + ((tr["place"], tr["world"], tr["caps"], tr["flags"]) if tr else ())
                    if key != self.host_trailer_key and (self.host_trailer_key is not None or tr is not None):
                        ev.append(HOST_WORLD_TRAILER_LINE.format(text=trailer_text(tr, payload)))
                    self.host_trailer_key = key
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

    def _frame_kw(self, hp) -> dict:
        """[ff9mapkit netsync s157] This tick's trailing frame (call with the lock held): {} (the 37-byte pre-s157 record), the
        host's own (``echo``: only when its frame carried one), or the pin -- which then advances by ``frame_step``, mod its n."""
        if self.frame == "none":
            return {}
        if self.frame == "echo":
            if not hp.get("has_frame"):
                return {}
            return {"anim_frame": hp["anim_frame"], "frame_n": hp["frame_n"]}
        n = int(self.frame[1])
        now = self._frame_now
        if n > 0 and self.frame_step:
            self._frame_now = (now + self.frame_step) % n
        return {"anim_frame": now, "frame_n": n}

    def _stamp(self, fields: dict, now: float) -> bytes:
        """[ff9mapkit netsync s166] (lock held) One trailer: ``fields`` + this frame's seq (+1 per built frame) and ms (the session
        clock's milliseconds, low 32 bits)."""
        self._seq = (self._seq + 1) & 0xFFFF
        return build_world_trailer(seq=self._seq, ms=int(float(now) * 1000.0), **fields)

    def _trailer_for(self, fields: dict, now: float) -> bytes:
        """[ff9mapkit netsync s166] (lock held) The trailer bytes ``trailer`` asks for: none ("off"), the engine's tfmt-0 trailer
        ("tfmt0": `worldwalk pose off`, the seq still counted as the sender's Update runs) or a stamped fmt-1 one ("auto")."""
        if self.trailer == "off":
            return b""
        stamped = self._stamp(fields, now)
        return TFMT0_TRAILER if self.trailer == "tfmt0" else stamped

    def _walk_frame(self, now: float, wire: int) -> bytes:
        """[ff9mapkit netsync s166] (lock held) The walking guest's record at ``now``: the world sentinel's 39 bytes + the plan's
        trailer -- except inside the world LOAD after its first frame, where the writer re-sends that frame byte-identical (the seq
        and ms frozen: a game publishes nothing during its own sync load)."""
        s = now - self._t0
        fields = self.walk.fields(s)
        if self.walk.phase(s) == "load":
            if self._load_frame is None or self._load_frame[WIRE_BYTE] != (int(wire) & 0xFF):
                self._load_frame = build_pos_frame(0, wire=wire, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0,
                                                   trailer=self._trailer_for(fields, now))
            return self._load_frame
        tr = self._trailer_for(fields, now)
        return build_pos_frame(0, wire=wire, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0, trailer=tr)

    def pos_frame(self, now: float = 0.0, wire: int = WIRE_DEFAULT) -> bytes:
        """The type-0 frame due at ``now``, framed at ``wire``. [ff9mapkit netsync s166] At wire >= 15 a 39-byte record carries the
        world trailer (``trailer`` "auto"), and the walk plan replaces the mirrored record."""
        with self._lock:
            if self._t0 is None:
                self._t0 = float(now)
            if self.walk is not None:
                return self._walk_frame(float(now), wire)
            hp = self.host_pos
            if self.field is not None:
                field = self.field
            else:
                field = hp["field"] if hp else FIELD_SENTINEL
            if hp is None:                                 # the relay's 65535 sentinel (v15: 39 B + a place-0 trailer)
                kw = {"anim_frame": 0, "frame_n": 0} if int(wire) >= WIRE_V15 else {}
            else:
                x, y, z = hp["pos"]
                dx, dy, dz = self.offset
                kw = dict(anim=hp["anim"] if self.anim is None else self.anim, model=hp["model"], mesh_vis=hp["mesh_vis"],
                          loco=hp["loco"] if self.loco is None else self.loco, pos=(x + dx, y + dy, z + dz), rot=hp["rot"],
                          **self._frame_kw(hp))                                                 # [ff9mapkit netsync s157]
            tr = b""
            if int(wire) >= WIRE_V15 and self.trailer != "off" and field == FIELD_SENTINEL:
                # [ff9mapkit netsync s166] the relay keepalive byte for byte (the engine's constructor slot: no seq, no follow flag)
                tr = keepalive_trailer(WALK_TPS)
            elif int(wire) >= WIRE_V15 and self.trailer != "off" and "frame_n" in kw:
                place = PLACE_FIELD if 0 < field < FIELD_SENTINEL else PLACE_NONE
                tr = self._trailer_for(world_block_zeroed({"caps": CAP_WORLD_POSE, "place": place, "state": ST_CONTROL,
                                                           "world_tps": WALK_TPS,
                                                           "flags": FLAG_FOLLOW if self.follow else 0}), now)
            return build_pos_frame(field, wire=wire, trailer=tr, **kw)

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

    def in_gap(self, now: float) -> bool:
        """[ff9mapkit netsync s166] Inside a ``gaps`` window (session seconds from the first outgoing): the record sends nothing."""
        with self._lock:
            return self._t0 is not None and in_windows(float(now) - self._t0, self.gaps)

    def outgoing(self, now: float, wire: int = WIRE_DEFAULT) -> list:
        """The NetSyncWire frames due this tick: the position slot, then (when declared) the control slot --
        NetSyncFrames.CollectOutgoing's order. [ff9mapkit netsync s166] Framed at ``wire`` (the session passes the version the host
        speaks); nothing at all inside a ``gaps`` window."""
        frames = [self.pos_frame(now, wire)]
        if self.in_gap(now):
            return []
        ctl = self.control_payload(now)
        if ctl is not None:
            frames.append(build_frame(TYPE_CONTROL, ctl, wire=wire))
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
                 clock=time.monotonic, sleep=None, tick: float = TICK_S, status_every: float = 5.0, wire: int | None = None):
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
        # [ff9mapkit netsync s166] THE SEND WIRE: ``wire`` pins it (`--wire N`, the probed netsync.wire); None adopts the HOST's first
        # accepted header -- until then this guest sends NOTHING (a v15 host would count every v14 frame as a mismatched peer and
        # print its once-per-process version line). Once set, a host frame of another version is DROPPED, as an engine that speaks
        # the send wire drops it (one line).
        self.send_wire = wire
        self.host_wire = None
        self._mismatch_logged = False
        self._waiting_logged = False

    def stop(self, why: str) -> None:
        if self.why is None:
            self.why = why
        self._stop.set()

    def _note_host_wire(self, v: int) -> bool:
        """[ff9mapkit netsync s166] (reader thread) The host's header version ``v`` on an accepted frame, BEFORE the model reads it:
        the first one logs HOST_WIRE_LINE; False = a send wire is set and differs (pinned: the engine drops it, so does this)."""
        if self.host_wire is None:
            self.host_wire = v
            if self.send_wire is None:
                self.log(HOST_WIRE_LINE.format(host=v, send=v, how="the host's own"))
            else:
                self.log(HOST_WIRE_LINE.format(host=v, send=self.send_wire, how="pinned by --wire" + (
                    "" if v == self.send_wire else " -- the host DROPS every frame this guest sends: they never pair")))
        if self.send_wire is None or v == self.send_wire:
            return True
        with self._count_lock:
            self.rx["foreign"] += 1
        if not self._mismatch_logged:
            self._mismatch_logged = True
            self.log(f"host frame at wire {v} DROPPED: this fake guest speaks {self.send_wire} (mixed engine versions never sync; "
                     "logged once)")
        return False

    def _adopt_host_wire(self, v: int) -> None:
        """[ff9mapkit netsync s166] (reader thread) AFTER the model read the host's first frame: the send wire, when none is set -- so
        the first frame this guest sends already mirrors the host (never a sentinel framed at the new wire)."""
        if self.send_wire is None:
            self.send_wire = v

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
                if not self._note_host_wire(payload[WIRE_BYTE]):     # [ff9mapkit netsync s166]
                    continue
                wtype, body = got
                with self._count_lock:
                    self.rx[wtype] += 1
                for ev in self.model.on_host_frame(wtype, body, self._clock()):
                    self.log(ev)
                self._adopt_host_wire(payload[WIRE_BYTE])            # [ff9mapkit netsync s166] after the model has the frame
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
                wire = self.send_wire                      # [ff9mapkit netsync s166] none yet: wait for the host's header
                if wire is None:
                    if not self._waiting_logged:
                        self._waiting_logged = True
                        self.log("waiting for the host's first header to pick the send wire (--wire N pins it)")
                    frames = []
                else:
                    frames = self.model.outgoing(now, wire)
                ctl = frames[1] if len(frames) > 1 else None
                if not frames:                             # nothing due (no wire yet, or a --gap-at window): no lane edge
                    ctl = self._last_ctl
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
            rates += f" DROPPED {rx['foreign'] - rx_mark['foreign']}"     # [ff9mapkit netsync s166] not v14/v15, or not the send wire
        tap = f" | tap {self.tap.records} rec {self.tap.bytes / 1e6:.1f} MB" if self.tap is not None else ""
        return (f"status: host field {_field_text(hp)} | battle {lane} | rx {rates.strip() or 'nothing'} | "
                f"tx pos {rate(tx, tx_mark, TYPE_POS):.0f}/s ctl {rate(tx, tx_mark, TYPE_CONTROL):.0f}/s"
                f" | wire {self.send_wire if self.send_wire is not None else 'none yet'}{tap}")   # [ff9mapkit netsync s166]


# ======================================================================================== the recorded HOST (replay)
class Replayer:
    """Replays host frames on their original timing against an injectable clock: frame ``t`` is due at
    ``wall0 + (t - start)``. A BLACKHOLE ``[at, at+for)`` drops every frame in it (the TCP stays open, nothing is sent,
    nothing is queued -- latest-state wire, as the decoupled bridge drops game->relay frames while its upstream is down)
    and resumes on the original timeline after it. ``stop_at`` ends the host there. ``send(payload) -> bool`` reports
    whether a guest connection took it (False = none attached: the frame is lost, counted)."""

    def __init__(self, frames, *, start: float, stop_at: float | None = None, blackholes=(), send, log,
                 clock=time.monotonic, sleep=time.sleep, on_sent=None, on_note=None, progress_every: float = 10.0,
                 lag_warn: float = 0.25, freezes=(), wire: int | None = None):
        self.frames = [f for f in frames if f[0].t >= start and (stop_at is None or f[0].t < stop_at)]
        self.start = start
        self.stop_at = stop_at
        self.blackholes = sorted((float(a), float(a) + float(n)) for a, n in blackholes)
        # [ff9mapkit netsync s166] ``wire``: every frame goes out with this version byte (None = as recorded; replay_send_wire
        # decides it). ``freezes`` [at, at+for): the link stays open and the host RE-SENDS ITS LAST SLOTS byte-identical every tick
        # (the writer's real re-send while its game sits in a synchronous load: CollectOutgoing's latest slots, the seq frozen) --
        # the guest-side HANG and "Lost contact" instrument a blackhole cannot be (a blackhole trips the guest's 2 s session
        # overlay first). The tape's own frames inside the window are dropped (counted ``frozen``); its timeline resumes after.
        self.wire = wire
        self.freezes = sorted((float(a), float(a) + float(n)) for a, n in freezes)
        self.frozen = 0
        self.resent = 0
        self._slots = {}                                   # wtype -> (rec, payload) of the last SENT latest-slot frame
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

    def in_freeze(self, t: float) -> bool:
        """[ff9mapkit netsync s166] ``t`` inside a freeze window."""
        return any(a <= t < b for a, b in self.freezes)

    def stamped(self, payload: bytes) -> bytes:
        """[ff9mapkit netsync s166] ``payload`` as it goes out: restamped to ``wire`` when one is set and differs (byte 1 only)."""
        if self.wire is None or frame_wire(payload) in (None, self.wire):
            return payload
        return restamp(payload, self.wire)

    def _events(self) -> list:
        # priorities at one tape second: the ends (0), the begins (1), a freeze tick (2), a frame (3), the stop (4)
        ev = []
        for a, b in self.blackholes:
            if b > self.start and (self.stop_at is None or a < self.stop_at):
                ev.append((max(a, self.start), 1, "bh-begin", (a, b)))
                ev.append((b, 0, "bh-end", (a, b)))
        for a, b in self.freezes:                          # [ff9mapkit netsync s166] a tick every TICK_S inside the window
            if b > self.start and (self.stop_at is None or a < self.stop_at):
                a0 = max(a, self.start)
                ev.append((a0, 1, "fz-begin", (a, b)))
                ev.append((b, 0, "fz-end", (a, b)))
                k = 0
                while a0 + k * TICK_S < b and (self.stop_at is None or a0 + k * TICK_S < self.stop_at):
                    ev.append((a0 + k * TICK_S, 2, "fz-tick", (a, b)))
                    k += 1
        if self.stop_at is not None:
            ev.append((self.stop_at, 4, "stop", None))
        ev.extend((f[0].t, 3, "frame", f) for f in self.frames)
        ev.sort(key=lambda e: (e[0], e[1]))
        return ev

    def _resend_slots(self, at: float) -> None:
        """[ff9mapkit netsync s166] One writer tick inside a freeze: each LATEST SLOT the host was sending when the freeze began
        (its last frame within FREEZE_SLOT_LIVE_S of the start), byte-identical, in CollectOutgoing's slot order (pos, battle,
        control, roster, state). The queued lanes (commands, actions, dialogue) are never re-sent: they drain once."""
        for wtype in FREEZE_SLOT_ORDER:
            got = self._slots.get(wtype)
            if got is None or got[0].t < at - FREEZE_SLOT_LIVE_S:
                continue
            rec, payload = got
            if self._send(self.stamped(rec.payload)):
                self.resent += 1
                if self._on_sent is not None:
                    self._on_sent(rec, wtype, payload)
            else:
                self.unsent += 1

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
                if self.in_freeze(t):                      # [ff9mapkit netsync s166] the tape's own frame: the writer re-sends instead
                    self.frozen += 1
                    continue
                if lag > self._lag_warn and not lag_logged:
                    lag_logged = True
                    self._log(f"replay running {lag:.2f} s late at tape {t:.2f} (the guest is not reading fast "
                              "enough? frames go out back to back to catch up; logged once)")
                if self._send(self.stamped(rec.payload)):  # [ff9mapkit netsync s166] restamped to the send wire
                    self.sent += 1
                    if wtype in FREEZE_SLOT_ORDER:
                        self._slots[wtype] = (rec, payload)
                    if self._on_sent is not None:
                        self._on_sent(rec, wtype, payload)
                else:
                    self.unsent += 1
                self._track(wtype, payload, t)
            elif kind == "fz-tick":
                if not self.in_blackhole(t):
                    self._resend_slots(item[0])
            elif kind == "fz-begin":
                a, b = item
                live = [TYPE_NAMES[w] for w in FREEZE_SLOT_ORDER
                        if w in self._slots and self._slots[w][0].t >= a - FREEZE_SLOT_LIVE_S]
                self._note(f"FREEZE at tape {t:.2f} s: the link stays open and the host RE-SENDS its last frame(s) byte-identical "
                           f"for {b - t:.2f} s (its game in a synchronous load: the writer re-sends its latest slots, the seq "
                           f"frozen) -- slots: {', '.join(live) or 'none sent yet'}")
            elif kind == "fz-end":
                self._note(f"FREEZE over at tape {t:.2f} s: host frames resume ({self.resent} re-sent, {self.frozen} tape "
                           "frame(s) dropped so far)")
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
                "max_lag": self.max_lag, "frozen": self.frozen, "resent": self.resent}   # [ff9mapkit netsync s166] + the freeze


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
        self.guest_wire = None                             # [ff9mapkit netsync s166] the guest's first header version (any)
        self.trailer_key = None                            # ...and its world trailer's edge (kind, place, world, caps, flags)

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
            if self.guest_wire is None:                    # [ff9mapkit netsync s166] what the guest speaks: its first header
                self.guest_wire = frame_wire(message)
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
                    # [ff9mapkit netsync s166] the guest's world trailer as an EDGE (a v14 / capless guest logs none)
                    tr = p["trailer"]
                    key = (trailer_kind(payload),) + ((tr["place"], tr["world"], tr["caps"], tr["flags"]) if tr else ())
                    if key != self.trailer_key and (self.trailer_key is not None or tr is not None):
                        ev.append(GUEST_WORLD_TRAILER_LINE.format(text=trailer_text(tr, payload)))
                    self.trailer_key = key
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


def _parse_frame(text: str):
    """[ff9mapkit netsync s157] ``--frame``: "echo" | "none" | "F/N" (two bytes, 0-255 each: F past N and N 0 / 1 / 255 are
    allowed on purpose -- the engine's clamp and its three frame-count guards are what they drive)."""
    t = text.strip().lower()
    if t in ("echo", "none"):
        return t
    m = re.fullmatch(r"(\d+)\s*/\s*(\d+)", t)
    if not m or int(m.group(1)) > 255 or int(m.group(2)) > 255:
        raise argparse.ArgumentTypeError("--frame is echo, none or F/N (each 0-255)")
    return int(m.group(1)), int(m.group(2))


def _parse_menu(text: str) -> int:
    t = text.strip().lower()
    if t in MENU_NAMES:
        return MENU_NAMES[t]
    v = int(t, 0)
    if not 0 <= v <= 255:
        raise argparse.ArgumentTypeError("--menu is a byte (or shut/legacy/root/deep)")
    return v


def _walk_from(args) -> WorldWalkPlan | None:
    """[ff9mapkit netsync s166] serve-guest's `--walk` plan (None = the mirrored record)."""
    if not getattr(args, "walk", None):
        return None
    route = WORLD_ROAM_ROUTE if args.walk == "roam" else args.walk
    return WorldWalkPlan(route=route, ups=args.walk_ups, world=args.world, model=args.world_model,
                         anim=args.anim if args.anim is not None else 0, out_s=args.walk_out, load_s=args.walk_load,
                         state=args.state, scenes=_windows(args.scene_at, args.scene_for, "--scene"),
                         follow=not args.no_follow, tps=args.world_tps)


def _windows(ats, fors, name: str) -> list:
    """[ff9mapkit netsync s166] ``(at, for)`` windows from repeatable ``--X-at`` / ``--X-for`` (one for, or one per at; > 0 s)."""
    ats = [float(a) for a in (ats or [])]
    fors = [float(f) for f in (fors or [])]
    if len(fors) == 1 and len(ats) > 1:
        fors = fors * len(ats)
    if len(ats) != len(fors) or any(f <= 0 for f in fors):
        raise ValueError(f"give one {name}-for (> 0 s) per {name}-at (or one for all)")
    return list(zip(ats, fors))


def _model_from(args) -> GuestModel:
    return GuestModel(field=args.field, offset=args.offset, report=REPORTS[args.report], menu=args.menu,
                      live_after=args.live_after, anim=args.anim, loco=args.loco, frame=args.frame,   # [ff9mapkit netsync s157]
                      frame_step=args.frame_step,
                      trailer=args.trailer, follow=not args.no_follow, walk=_walk_from(args),         # [ff9mapkit netsync s166]
                      gaps=_windows(args.gap_at, args.gap_for, "--gap"))


def _record_text(args) -> str:
    """[ff9mapkit netsync s166] The banner's record line (never raises: a bad window is refused right after the banner)."""
    try:
        text = _walk_from(args).text() if args.walk else "the host mirrored"
        gaps = _windows(args.gap_at, args.gap_for, "--gap")
    except ValueError as err:
        return f"REFUSED ({err})"
    return text + (f"; GAPS (nothing sent) {gaps}" if gaps else "")


def _send_wire_arg(args) -> int | None:
    """[ff9mapkit netsync s166] `--wire`: auto -> None (the host's first header), else the pinned version."""
    w = getattr(args, "wire", "auto") or "auto"
    return None if w == "auto" else int(w)


def _guest_lines(args) -> list:
    report = ("none (no type-3 control frame)" if args.report == "off" else
              f"{args.report} on the host's current battle nonce, menu byte {args.menu}"
              + (f", BOOTING for the first {args.live_after:g} s of each battle" if args.live_after > 0 else ""))
    return [f"position: type-0 at 30 Hz on {'the HOST field (mirrored)' if args.field is None else f'field {args.field}'}"
            f"{'' if args.offset == (0.0, 0.0, 0.0) else f', offset {args.offset}'}",
            f"report: {report}",
            f"frame: {_frame_text(args)}",                                   # [ff9mapkit netsync s157]
            # [ff9mapkit netsync s166] the send wire, the trailer, the walk, the gaps
            f"wire: {'the HOST its first header names (--wire pins it)' if args.wire == 'auto' else f'{args.wire} (pinned)'}; "
            f"v15 trailer: {args.trailer}{'' if not args.no_follow else ', flags b0 CLEAR (--no-follow)'}",
            f"record: {_record_text(args)}",
            f"tap: {args.tap or 'off (pass --tap FILE to record the host)'}"]


def _frame_text(args) -> str:
    """[ff9mapkit netsync s157] The banner's type-0 anim / loco / trailing-frame line."""
    frame = {"echo": "echo (the host's own trailer; 37 B from a pre-s157 host)",
             "none": "none (always 37 B: a pre-s157 guest -- the calibration red)"}.get(args.frame) if isinstance(args.frame, str) else None
    if frame is None:
        frame = f"pinned {args.frame[0]}/{args.frame[1]}" + (f", {args.frame_step:+d} per tick" if args.frame_step else "")
    return (f"{frame}; anim {'mirrored' if args.anim is None else args.anim}, "
            f"loco {'mirrored' if args.loco is None else args.loco}")


class ServeGuest:
    """serve-guest's connection handler: each HOST game connection gets its own GuestSession and a fresh model (the
    engine redials every 2 s after a drop; a newer connection replaces an older one, as the relay replaces a stale leg)."""

    def __init__(self, model_factory, *, log: Log, tap: TapeWriter | None = None, status_every: float = 5.0,
                 tick: float = TICK_S, wire: int | None = None):
        self._model_factory = model_factory
        self.wire = wire                                   # [ff9mapkit netsync s166] None: each connection adopts its host's header
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
                            tick=self._tick, wire=self.wire)                   # [ff9mapkit netsync s166]
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
        _model_from(args)                                  # [ff9mapkit netsync s166] a bad window refuses BEFORE listening
        tap = TapeWriter(args.tap, mode="serve-guest") if args.tap else None
    except (OSError, ValueError) as err:
        log(f"ERROR: {err}")
        return 2
    served = ServeGuest(lambda: _model_from(args), log=log, tap=tap, status_every=args.status,
                        wire=_send_wire_arg(args))                             # [ff9mapkit netsync s166]
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
        _model_from(args)                                  # [ff9mapkit netsync s166] a bad window refuses BEFORE dialling
        tap = TapeWriter(args.tap, mode="fake-guest-client", extra={"relay": args.relay, "code": args.code}) \
            if args.tap else None
    except (OSError, ValueError) as err:
        log(f"ERROR: {err}")
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
            why = GuestSession(conn, _model_from(args), log=log, tap=tap, status_every=args.status,
                               wire=_send_wire_arg(args)).run()                # [ff9mapkit netsync s166]
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
                 tap: TapeWriter | None = None, code: str | None = None, clock=time.monotonic, sleep=time.sleep,
                 wire="auto", freezes=()):
        self.frames = frames
        self.start = start
        self.stop_at = stop_at
        self.blackholes = list(blackholes)
        # [ff9mapkit netsync s166] the send wire: ``wire`` 'auto' (the guest's first header), 'tape' (as recorded) or a version;
        # decided at the guest's first message (replay_send_wire) and logged as GUEST_WIRE_LINE before REPLAY start
        self.wire = wire
        self.freezes = list(freezes)
        self.tape_wire = next((frame_wire(f[0].payload) for f in frames if frame_wire(f[0].payload) is not None), None)
        self.send_wire = None
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
                evs = self.watch.on_guest_message(payload, self._clock())
                self.seen.set()                            # [ff9mapkit netsync s166] AFTER the watch: run() reads its guest_wire
                for ev in evs:
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
        if self.tap is not None:                           # [ff9mapkit netsync s166] what went out: restamped to the send wire
            self.tap.write(DIR_HOST, rec.payload if self.send_wire is None else
                           (restamp(rec.payload, self.send_wire) if frame_wire(rec.payload) not in (None, self.send_wire)
                            else rec.payload))

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
        # [ff9mapkit netsync s166] the send wire, from the guest's first header (or --wire), stated BEFORE the replay starts
        send, how = replay_send_wire(self.wire, self.watch.guest_wire, self.tape_wire)
        self.send_wire = send
        line = GUEST_WIRE_LINE.format(guest=self.watch.guest_wire if self.watch.guest_wire is not None else "none", send=send,
                                      how=how)
        self.log(line)
        if self.tap is not None:
            self.tap.note(line)
        rep = Replayer(self.frames, start=self.start, stop_at=self.stop_at, blackholes=self.blackholes,
                       send=self.port.send, log=self.log, clock=self._clock, sleep=self._sleep, on_sent=self._on_sent,
                       on_note=self._on_note, freezes=self.freezes, wire=send)
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
        if self.freezes:                                   # [ff9mapkit netsync s166] its own line: replay_done's shape is anchored
            self.log(f"freezes: {result.get('resent', 0)} slot frame(s) re-sent byte-identical, {result.get('frozen', 0)} tape "
                     "frame(s) held back")
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


def _replay_extras(args, records, battles) -> tuple:
    """[ff9mapkit netsync s166] The replay's freezes and send-wire mode from the CLI -> ``(freezes, wire, tape)``; raises ValueError:
    a --freeze-for per --freeze-at (or one for all, > 0 s), and never a restamp DOWN (``--wire 14`` on a v15 tape: its trailer has no
    v14 meaning -- decision 2's law covers v14 -> v15 only)."""
    ats = [resolve_time(a, battles) for a in (getattr(args, "freeze_at", None) or [])]
    fors = [float(f) for f in (getattr(args, "freeze_for", None) or [])]
    if len(fors) == 1 and len(ats) > 1:
        fors = fors * len(ats)
    if len(ats) != len(fors) or any(f <= 0 for f in fors):
        raise ValueError("give one --freeze-for (> 0 s) per --freeze-at (or one for all)")
    wire = getattr(args, "wire", None) or "auto"
    tape = tape_wire(records)
    if wire not in ("auto", "tape") and tape is not None and int(wire) < tape:
        raise ValueError(f"--wire {wire} would restamp a wire-{tape} tape DOWN: only v14 -> v15 keeps every byte's meaning")
    return list(zip(ats, fors)), wire, tape


def cmd_replay_host(args) -> int:
    log = Log(args.log)
    try:
        header, records, torn = read_tape(args.tape)
        frames, battles, start, stop_at, blackholes = _replay_plan(args, records)
        freezes, wire, twire = _replay_extras(args, records, battles)              # [ff9mapkit netsync s166]
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
    for a, n in freezes:                                   # [ff9mapkit netsync s166]
        lines.append(f"FREEZE tape {a:.2f}..{a + n:.2f} s ({n:g} s): the TCP stays open, the last slots re-sent byte-identical")
    lines.append(f"wire: the tape speaks {twire}; the replay sends "                       # [ff9mapkit netsync s166]
                 + {"auto": "the GUEST's own (its first header; a v14 tape restamped up to a v15 guest)",
                    "tape": "it as recorded (--wire tape: never restamped)"}.get(wire, f"wire {wire} (pinned --wire)"))
    banner(log, "replay-host", lines)

    try:
        tap = TapeWriter(args.tap, mode="replay-host", extra={"source_tape": str(args.tape), "blackholes": blackholes,
                                                              "from": start, "stop_at": stop_at, "freezes": freezes,
                                                              "source_wire": twire, "wire_mode": wire}) \
            if args.tap else None                          # [ff9mapkit netsync s166] + freezes, the source's wire, the mode
    except OSError as err:
        log(f"ERROR: cannot open the tape: {err}")
        log.close()
        return 2
    rh = ReplayHost(frames, start=start, stop_at=stop_at, blackholes=blackholes, log=log, tap=tap, code=args.code,
                    wire=wire, freezes=freezes)                                   # [ff9mapkit netsync s166]
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
    # [ff9mapkit netsync s166] the wire each side SPOKE, off the frames (a pre-s166 writer stamped its constant in the header)
    out.append(f"wire (from the frames): host {tape_wire(records, DIR_HOST)}, guest {tape_wire(records, DIR_GUEST)}")
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
        out.append(f"  {d:5} NOT v14/15 {n:5d} message(s) (the engine would drop these)")   # [ff9mapkit netsync s166]
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
                line = f"{r.t:10.3f} {DIR_NAMES.get(r.dir, r.dir):5} NOT v14/15: {frame_header_text(r.payload)}"
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
    out.update(tape_battle_where(records))          # [ff9mapkit netsync s145] the battle segments
    return out


def _said(flags) -> str | None:
    """Where one section-7 flags byte says the host stands: 'world' (b6) | 'title' (b7) | 'battle' (b5) | 'field' (b3) |
    'other' (none of them); None = no readable section 7."""
    if flags is None:
        return None
    if flags & BW.HF_WORLD:
        return "world"
    if flags & BW.HF_TITLE:
        return "title"
    if flags & BW.HF_BATTLE:
        return "battle"
    if flags & BW.HF_ON_FIELD:
        return "field"
    return "other"


#: [ff9mapkit netsync s145 fix1] THE PLACE AROUND A BATTLE: the host's state frames ADJACENT to its type-1 run never carry it -- a
#: real host tape reads the swirl ('other', ~1 s: SwirlScene, no b3 / b6) and the gMode-2 lead ('battle', b4 + b5, ~0.15 s) before
#: the first type-1 frame, and the result tail ('battle', b5) plus, from the world map, its ~4.4 s load ('other') after the last.
#: So the place is read past them: the LAST place frame within WHERE_BEFORE_S before the battle, the FIRST within WHERE_AFTER_S
#: after it (a place = 'world' / 'field' / 'title').
WHERE_BEFORE_S = 5.0
WHERE_AFTER_S = 10.0
WHERE_PLACES = ("world", "field", "title")


def tape_battle_where(records) -> dict:
    """[ff9mapkit netsync s145] THE BATTLE SEGMENTS (PURE over the records): each host battle on the tape (:func:`tape_battles`)
    with WHERE the host says it stood around it -- section 7's place ('world' / 'title' / 'field') on the LAST host state frame
    that says one within WHERE_BEFORE_S before the battle's first type-1 frame (``said_before``) and on the FIRST within
    WHERE_AFTER_S after its last (``said_after``) -- never the adjacent frame, which is the swirl / the gMode-2 lead / the result
    tail / the world's load ('other' / 'battle') on every real tape; None = no place said there (or no section 7) -- the
    position lane's field then (``field_before`` / ``field_after``), and ``world`` -- a WORLD-MAP BATTLE: b6 on both sides (an
    s144+ host on its world HUD before the swirl and back on it after the victory; the field lane 0 both times).
    ``world_battles`` counts them; ``first_world_battle`` is the first one's index (None = none). The s145 T2 tape
    (coop_tape_record.py COOP_TAPE_WORLD_BATTLE=1) carries exactly one; a field tape's battle reads 'field' before and after."""
    raw = tape_battles(records)
    segs = [{"n": b["n"], "nonce": b["nonce"], "map": b["map"], "start": round(b["start"], 3), "end": round(b["end"], 3),
             "said_before": None, "said_after": None, "field_before": None, "field_after": None, "world": False}
            for b in raw]
    field, flags_seen = None, None
    for r, wtype, payload in host_frames(records):
        if wtype == TYPE_POS:
            p = parse_pos_payload(payload)
            if p is not None:
                field = p["field"]
            continue
        if wtype != TYPE_STATE:
            continue
        body = BW.old_try_read_section(payload, BW.SECTION_DIALOG)
        view = BW.parse_dialog_section(body) if body is not None else None
        flags_seen = view["flags"] if view is not None else None
        said = _said(flags_seen)
        if said not in WHERE_PLACES:                 # [s145 fix1] the swirl, the lead, the tail, a load: no place
            continue
        for sg, b in zip(segs, raw):                # the RAW record times (the rounded ones are for the report)
            if r.t < b["start"]:
                if b["start"] - r.t <= WHERE_BEFORE_S:
                    sg["said_before"], sg["field_before"] = said, field
            elif r.t > b["end"] and sg["said_after"] is None and r.t - b["end"] <= WHERE_AFTER_S:
                sg["said_after"], sg["field_after"] = said, field
    for sg in segs:
        sg["world"] = sg["said_before"] == "world" and sg["said_after"] == "world"
    worlds = [sg["n"] for sg in segs if sg["world"]]
    return {"battles": segs, "world_battles": len(worlds), "first_world_battle": worlds[0] if worlds else None}


#: `where --want`: what the tape's host must have said (the verdict's own rule over tape_where's counts) -- [ff9mapkit netsync
#: s145] + `world-battle`: a world-map battle on the tape (b6 before and after it), b6 never on a real field
WHERE_WANTS = ("world", "title", "none", "any", "world-battle")


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
    if want == "world-battle":                      # [ff9mapkit netsync s145]
        return d.get("world_battles", 0) > 0 and d["world_on_field"] == 0
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
             # [ff9mapkit netsync s145] the battle segments: where the host said it stood around each battle
             f"battles: {len(d.get('battles') or [])}; world-map battles (b6 before and after): {d.get('world_battles', 0)}"]
    for sg in d.get("battles") or []:
        lines.append(f"  battle {sg['n']} (nonce {sg['nonce']}, map {sg['map']}) tape {sg['start']:.2f}-{sg['end']:.2f} s: "
                     f"before {sg['said_before']} (field {sg['field_before']}), after {sg['said_after']} (field "
                     f"{sg['field_after']}){' -- A WORLD-MAP BATTLE' if sg['world'] else ''}")
    lines.append(f"VERDICT (--want {want}): " + ("OK" if ok else "FAIL"))
    return ok, lines


# ======================================================================================== [ff9mapkit netsync s165] the host's world pose
#: [ff9mapkit netsync s165] THE HOST'S WORLD POSE ON SECTION 0 (studies/world-coop/S165-DESIGN.md K1; the lane-H recon F4): the on-foot
#: anchor the host's world dispatcher rewrites every frame it walks (WORLD11's entry-14 loop: only on foot, [190] == 0, and only while
#: no request sequence runs) -- the bytes the guest's follow-out lands on and its minimap dot reads, carried by EVERY host type-5 frame
#: in its 2048-byte story section, so no wire byte is added. The record is in absolute, unwrapped world units x 256 (RealPosition
#: un-wraps the torus): Int24 [64..66] = x * 256, Int16 [67..68] = -y * 256 (getvobj negates f[1]; MoveInstantXZY negates it back),
#: Int24 [69..71] = z * 256 (always negative: 24-bit sign extension), Byte [72] = the facing, 256 steps a turn.
POSE_X, POSE_Y, POSE_Z, POSE_YAW = 64, 67, 69, 72
#: ...and its neighbours a follow-out reads: the story counter (UInt16 [0..1]; the minimap's map band: 5990 and up the whole torus),
#: FieldEntrance (Int16 [2..3]: 35 = the kit's POSITION_PRESET_KEY, 0 the dispatcher default, 9995-9999 the world sentinels), the
#: navi mode ([100]: 0 = the minimap off, a New Game's), the world index ([102]: the dispatcher's own, 9000 + it = the world id), the
#: Choco call ([181]: Gysahl Greens, nonzero while it runs in) and the travel mode ([190]: 0 on foot)
POSE_STORY, POSE_ENTRANCE, POSE_NAVI, POSE_IDX, POSE_CHOCO, POSE_MODE = 0, 2, 100, 102, 181, 190
#: the bytes section 0 must hold to read every pose field (the travel mode at 190); a whole story is NetSyncState.StoryLen (2048)
POSE_NEED = POSE_MODE + 1
#: WMWorld.Width / Height: the torus a pose wraps on (x in [0, 1536), z in (-1280, 0]); a same-spot test is a TORUS distance
WORLD_W, WORLD_H = 1536, 1280
#: `where --pose`: one row a second by default (a host sends a type-5 frame every write tick: ~30 a second)
POSE_EVERY_S = 1.0


def s24(data, off: int) -> int:
    """A little-endian signed 24-bit integer at ``off`` (the dispatchers' Int24 gEventGlobal reads)."""
    v = data[off] | (data[off + 1] << 8) | (data[off + 2] << 16)
    return v - 0x1000000 if v & 0x800000 else v


def s16(data, off: int) -> int:
    """A little-endian signed 16-bit integer at ``off`` (an Int16 gEventGlobal read)."""
    v = data[off] | (data[off + 1] << 8)
    return v - 0x10000 if v & 0x8000 else v


def story_pose(story) -> dict | None:
    """[ff9mapkit netsync s165] The host's world pose off its section-0 bytes (PURE): ``x`` = s24(64) / 256, ``y`` = -s16(67) / 256,
    ``z`` = s24(69) / 256, ``yaw`` = b72 * 360 / 256 degrees, the raw record (``raw``: x24, y16 as the u16 it is stored as, z24, b72),
    ``story`` [0..1], ``entrance`` [2..3], ``navi`` [100], ``idx`` [102], ``choco`` [181], ``mode`` [190]; ``torus`` -- the pose lies
    inside the world (0 <= x < 1536, -1280 < z <= 0: a second guard against field flags in 64-72 while b6 lies), ``whole`` -- a
    2048-byte story (the only one the guest applies). None when the bytes cannot hold the travel mode (shorter than POSE_NEED)."""
    b = bytes(story or b"")
    if len(b) < POSE_NEED:
        return None
    x24, y16, z24, yaw8 = s24(b, POSE_X), s16(b, POSE_Y), s24(b, POSE_Z), b[POSE_YAW]
    x, z = x24 / 256.0, z24 / 256.0
    return {"x": x, "y": -y16 / 256.0, "z": z, "yaw": yaw8 * 360.0 / 256.0,
            "raw": (x24, y16 & 0xFFFF, z24, yaw8),
            "story": b[POSE_STORY] | (b[POSE_STORY + 1] << 8), "entrance": s16(b, POSE_ENTRANCE), "navi": b[POSE_NAVI],
            "idx": b[POSE_IDX], "choco": b[POSE_CHOCO], "mode": b[POSE_MODE],
            "torus": 0.0 <= x < WORLD_W and -WORLD_H < z <= 0.0, "whole": len(b) == BW.STORY_LEN}


def story_with_pose(x: float, z: float, *, y: float = 0.0, yaw: float = 0.0, idx: int = 11, mode: int = 0, entrance: int = 35,
                    choco: int = 0, navi: int | None = None, story: int | None = None, base=None) -> bytes:
    """[ff9mapkit netsync s165] :func:`story_pose`'s inverse (PURE): a 2048-byte section 0 (``base`` copied, else zeros) with the pose
    written as the dispatcher writes it -- x / z * 256 rounded into Int24, -y * 256 into Int16, the facing rounded into 256 steps --
    and ``idx`` / ``mode`` / ``entrance`` / ``choco`` (and ``navi`` / ``story`` when given) at their bytes. A bench's fabricated host."""
    b = bytearray(bytes(base or b"")[:BW.STORY_LEN].ljust(BW.STORY_LEN, b"\0"))
    for off, val, n in ((POSE_X, int(round(x * 256.0)), 3), (POSE_Y, int(round(-y * 256.0)), 2),
                        (POSE_Z, int(round(z * 256.0)), 3), (POSE_ENTRANCE, int(entrance), 2)):
        val &= (1 << (8 * n)) - 1
        for k in range(n):
            b[off + k] = (val >> (8 * k)) & 0xFF
    b[POSE_YAW] = int(round(yaw * 256.0 / 360.0)) & 0xFF
    b[POSE_IDX], b[POSE_MODE], b[POSE_CHOCO] = idx & 0xFF, mode & 0xFF, choco & 0xFF
    if navi is not None:
        b[POSE_NAVI] = navi & 0xFF
    if story is not None:
        b[POSE_STORY], b[POSE_STORY + 1] = story & 0xFF, (story >> 8) & 0xFF
    return bytes(b)


def torus_delta(a, b) -> tuple:
    """[ff9mapkit netsync s165] (dx, dz) between two world points ``(x, z)`` the short way round the torus (PURE): dx = min(|dx|,
    1536 - |dx|), dz = min(|dz|, 1280 - |dz|) -- a host at x 1530 and a guest at x 5 stand 11 units apart, not 1525."""
    dx = abs(float(a[0]) - float(b[0])) % WORLD_W
    dz = abs(float(a[1]) - float(b[1])) % WORLD_H
    return min(dx, WORLD_W - dx), min(dz, WORLD_H - dz)


def torus_distance(a, b) -> float:
    """[ff9mapkit netsync s165] The torus distance between two world points ``(x, z)`` (PURE): the length of :func:`torus_delta`."""
    dx, dz = torus_delta(a, b)
    return (dx * dx + dz * dz) ** 0.5


def frame_pose(payload) -> dict:
    """[ff9mapkit netsync s165] One host type-5 payload's world-follow inputs (PURE), read as the guest's one reader reads them:
    ``pose`` (:func:`story_pose` of the FIRST id-0 section -- the old walker's TryReadSection; None = absent / short), ``whole``;
    section 7 through TryParseHostSection's twin: ``flags`` / ``hb`` (body[5] / body[3..4]; None = no readable section 7), ``b6``
    (HfWorld) and ``b1`` (HfControl); section 4: ``intent`` (None = absent, else {field, landed} -- a 3-byte body reads landed) and
    ``intent_unlanded`` (present and not landed: that intent belongs to the rejoin, never to a follow-out)."""
    story = BW.old_try_read_section(payload, BW.SECTION_STORY)
    pose = story_pose(story) if story is not None else None
    body = BW.old_try_read_section(payload, BW.SECTION_DIALOG)
    view = BW.parse_dialog_section(body) if body is not None else None
    flags = view["flags"] if view is not None else None
    sec4 = BW.old_try_read_section(payload, BW.SECTION_INTENT)
    intent = None
    if sec4 is not None and len(sec4) >= 2:
        intent = {"field": sec4[0] | (sec4[1] << 8), "landed": BW.intent_landed_of(sec4)}
    return {"pose": pose, "whole": story is not None and len(story) == BW.STORY_LEN,
            "flags": flags, "hb": view["heartbeat"] if view is not None else None,
            "b6": bool(flags is not None and flags & BW.HF_WORLD), "b1": bool(flags is not None and flags & BW.HF_CONTROL),
            "intent": intent, "intent_unlanded": intent is not None and not intent["landed"]}


def tape_poses(records) -> list:
    """[ff9mapkit netsync s165] Every HOST type-5 frame's :func:`frame_pose` in tape order (PURE over the records), each with its
    tape second ``t`` and the host's position-lane ``field`` off the LAST type-0 frame before it (None = none yet).
    [ff9mapkit netsync s166] ...and ``trailer``: that same type-0 frame's v15 WORLD trailer (:func:`parse_world_trailer`, decision 4's
    table, little-endian; None = a capless frame or no frame yet) beside its s157 record (``frame``: (animFrame, frameN), None on a
    37-byte one) -- the live pose a v15 host sends while section 0's anchor is parked (a ride, the kit voyage)."""
    out, field, trailer, frame = [], None, None, None
    for r, wtype, payload in host_frames(records):
        if wtype == TYPE_POS:
            p = parse_pos_payload(payload)
            if p is not None:
                field, trailer = p["field"], p["trailer"]
                frame = (p["anim_frame"], p["frame_n"]) if p["has_frame"] else None
            continue
        if wtype != TYPE_STATE:
            continue
        row = frame_pose(payload)
        row.update(t=r.t, field=field, trailer=trailer, frame=frame)
        out.append(row)
    return out


def pose_row_text(row: dict, near=None) -> str:
    """[ff9mapkit netsync s165] One `where --pose` row: the tape second, the lane's field, b6 / b1 and the heartbeat, the pose (x y z
    yaw, `!torus` when outside the world), [102] [190] [2..3] [181] [0..1], an unlanded intent, and -- with ``near`` (x, z) -- the
    torus distance to it."""
    p = row["pose"]
    head = (f"t {row['t']:8.2f}  field {row['field']}  b6 {int(row['b6'])} b1 {int(row['b1'])}  "
            f"hb {row['hb'] if row['hb'] is not None else '-'}")
    if p is None:
        return head + "  | no section 0"
    text = (f"{head}  | x {p['x']:8.2f} y {p['y']:7.2f} z {p['z']:8.2f} yaw {p['yaw']:6.1f}{'' if p['torus'] else ' !torus'}"
            f"  | idx {p['idx']} mode {p['mode']} entrance {p['entrance']} choco {p['choco']} story {p['story']}"
            + ("" if p["whole"] else " (short story)") + (" | intent UNLANDED" if row["intent_unlanded"] else ""))
    if near is not None:
        text += f"  | d {torus_distance((p['x'], p['z']), near):.1f}"
    return text + trailer_row_text(row, near)


def trailer_row_text(row: dict, near=None) -> str:
    """[ff9mapkit netsync s166] A `where --pose` row's v15 trailer column ('' when the type-0 frame carried none): its place, and on
    place 4 the world, the canonical x / y / z, the rotation's heading and [190]'s mode; caps, seq, state and flags; with ``near``
    the torus distance from the trailer's pose."""
    tr = row.get("trailer")
    if tr is None:
        return ""
    text = f"  | tr place {tr['place']}"
    if tr["place"] == PLACE_WORLD:
        x, y, z = tr["pos"]
        text += f" world {tr['world']} x {x:8.2f} y {y:7.2f} z {z:8.2f} yaw {tr['yaw']:6.1f} mode {tr['mode']}"
        if near is not None:
            text += f" d {torus_distance((x, z), near):.1f}"
    return text + f" caps 0x{tr['caps']:04X} seq {tr['seq']} state 0x{tr['state']:02X} flags 0x{tr['flags']:02X}"


def pose_rows_thinned(rows, every: float = POSE_EVERY_S) -> list:
    """[ff9mapkit netsync s165] ``rows`` thinned to one per ``every`` seconds (0 = every frame), keeping every EDGE: the first and
    the last frame, and any frame whose b6, b1, [102], [190], [181] or [2..3] differs from the frame before it."""
    out, last_t, prev = [], None, None
    keys = lambda r: ((r["b6"], r["b1"]) + ((None,) * 4 if r["pose"] is None else      # noqa: E731
                                           (r["pose"]["idx"], r["pose"]["mode"], r["pose"]["choco"], r["pose"]["entrance"]))
                      + _trailer_edge(r.get("trailer")))     # [ff9mapkit netsync s166] + the trailer's place / world / mode
    for i, r in enumerate(rows):
        edge = prev is None or keys(r) != keys(prev) or i == len(rows) - 1
        if edge or every <= 0 or last_t is None or r["t"] - last_t >= every:
            out.append(r)
            last_t = r["t"]
        prev = r
    return out


def _trailer_edge(tr) -> tuple:
    """[ff9mapkit netsync s166] The trailer's part of a `where --pose` edge: its place, world and mode (() when absent: an s165 tape's
    rows thin exactly as before)."""
    return () if tr is None else (tr["place"], tr["world"], tr["mode"])


def tape_pose_lines(path, every: float = POSE_EVERY_S, near=None) -> tuple:
    """[ff9mapkit netsync s165] (ok, the `where --pose` table's lines) for a tape file: the header, how many host state frames carry
    a pose (and with b6), then one row per frame (:func:`pose_rows_thinned`, :func:`pose_row_text`). ``ok`` -- at least one frame
    carries a pose."""
    _header, records, torn = read_tape(path)
    rows = tape_poses(records)
    posed = [r for r in rows if r["pose"] is not None]
    trailed = [r for r in rows if r.get("trailer") is not None]              # [ff9mapkit netsync s166]
    lines = [f"POSE (section 0 64-72, [102] [190] [2..3] [181]; section 7 heartbeat, b6 / b1): {len(rows)} host state frame(s), "
             f"{len(posed)} with a pose, {sum(1 for r in posed if r['b6'])} of them with b6"
             + (f"; {len(trailed)} beside a v15 type-0 trailer (`tr`: decision 4's world block), "
                f"{sum(1 for r in trailed if r['trailer']['block_valid'])} with a valid block" if trailed else "")
             + (f"; TORN tail {torn} B" if torn else "")
             + (f"; d = the torus distance to ({near[0]:g}, {near[1]:g})" if near is not None else "")]
    lines += [pose_row_text(r, near) for r in pose_rows_thinned(rows, every)]
    return bool(posed), lines


def _parse_xz(text: str) -> tuple:
    """[ff9mapkit netsync s165] `--near X,Z` -> (x, z)."""
    try:
        x, z = (float(t) for t in str(text).replace(" ", "").split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected X,Z (e.g. 1197.37,-796.7), not {text!r}") from None
    return x, z


def cmd_where(args) -> int:
    found, tried = resolve_tape(args.tape)
    if found is None:
        print(f"ERROR: no tape {args.tape!r} -- tried {', '.join(str(t) for t in tried)}", file=sys.stderr)
        return 2
    try:
        ok, lines = tape_where_lines(found, args.want)
        if getattr(args, "pose", False):              # [ff9mapkit netsync s165] the pose table after the verdict (a report, no verdict)
            lines = lines + tape_pose_lines(found, args.every, args.near)[1]
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


# ======================================================================================== [ff9mapkit netsync s163] section 10
def speed_order_ok(ids) -> bool:
    """[ff9mapkit netsync s163] A host state frame's section ids in the order s163 builds them (NetSyncSpeed.SelfTest's
    live.frame_order row, with sections 5 / 8 optional on a tape): ONE section 10, after section 5 and the start lane (6 or 9)
    when they ride, before section 7 -- and section 8, when it rides, right after 7 and last (DressSelfTest, :func:`tape_dress`)."""
    ids = list(ids)
    if ids.count(BW.SECTION_SPEED) != 1 or BW.SECTION_DIALOG not in ids:
        return False
    k, k7 = ids.index(BW.SECTION_SPEED), ids.index(BW.SECTION_DIALOG)
    before = [i for i, sid in enumerate(ids) if sid in (BW.SECTION_EVENT, BW.SECTION_TALK, BW.SECTION_CHEST)]
    if any(i > k for i in before) or k > k7:
        return False
    if BW.SECTION_DRESS in ids:
        k8 = ids.index(BW.SECTION_DRESS)
        return k8 == k7 + 1 and k8 == len(ids) - 1
    return True


def tape_speed(records, expect=None) -> dict:
    """[ff9mapkit netsync s163] Section 10 on a tape's HOST type-5 frames (PURE over the records), modelled on :func:`tape_dress`:
    how many frames, how many carry section 10, how many in s163's ORDER (:func:`speed_order_ok`: one section 10 after 5 and the
    start lane, before 7, with 8 still right after 7 and last), how many bodies the reader refuses (battlewire.parse_speed_body:
    under 2 B or a zero byte), the bodies seen (hex -> count) and the host settings they say (setting -> count), and how many frames
    an OLD guest reads differently with section 10 present than stripped (its story, its party sections, each of sections 4-9:
    battlewire's s103 walker twins) or cannot step past it (a SENTINEL section appended after must still read). ``expect``: None,
    the body every frame must carry (bytes), or a function ``payload -> bytes`` giving each frame's OWN expected body (``disagree``
    counts the frames whose body is not theirs). ``ok`` -- the wire carries section 10 as s163 says: at least one frame, every one
    with section 10 in order, every body parsed, no old-reader difference, and every body the expected one. ``boosted`` -- frames
    whose setting is above 1 (the host's booster on)."""
    frames = [payload for _r, wtype, payload in host_frames(records) if wtype == TYPE_STATE]
    out = {"frames": len(frames), "with10": 0, "ordered": 0, "malformed": 0, "old_diff": 0, "bodies": {}, "settings": {},
           "boosted": 0, "disagree": 0, "first_bad": None, "first_disagree": None, "first_order": None}
    per_frame = callable(expect)
    old_ids = (BW.SECTION_INTENT, BW.SECTION_EVENT, BW.SECTION_TALK, BW.SECTION_DIALOG, BW.SECTION_DRESS, BW.SECTION_CHEST)
    for payload in frames:
        secs, truncated = BW.walk_sections(payload)
        ids = [sid for sid, _b in secs]
        if BW.SECTION_SPEED not in ids:
            continue
        out["with10"] += 1
        body = secs[ids.index(BW.SECTION_SPEED)][1]
        if not truncated and speed_order_ok(ids):
            out["ordered"] += 1
        elif out["first_order"] is None:
            out["first_order"] = "section ids " + ",".join(str(i) for i in ids) + (" (truncated)" if truncated else "")
        ok_body, setting, _tps = BW.parse_speed_body(body)
        if not ok_body:
            out["malformed"] += 1
        else:
            out["settings"][setting] = out["settings"].get(setting, 0) + 1
            out["boosted"] += setting > 1
        key = BW.hex_bytes(body)
        out["bodies"][key] = out["bodies"].get(key, 0) + 1
        if per_frame:
            mine = expect(payload)
            if mine is None or bytes(body) != bytes(mine):
                out["disagree"] += 1
                if out["first_disagree"] is None:
                    out["first_disagree"] = (f"section 10 {key} where the frame's own expectation is "
                                             f"{BW.hex_bytes(mine) if mine is not None else 'none'}")
        bare = strip_section(payload, BW.SECTION_SPEED)
        past = BW.append_section(payload, SENTINEL_SECTION, SENTINEL_BODY)
        same = (BW.old_apply_story(payload) == BW.old_apply_story(bare)
                and BW.old_party_sections(payload) == BW.old_party_sections(bare)
                and all(BW.old_try_read_section(payload, sid) == BW.old_try_read_section(bare, sid) for sid in old_ids)
                and BW.old_try_read_section(past, SENTINEL_SECTION) == SENTINEL_BODY
                and BW.old_apply_story(past) == BW.old_apply_story(payload)
                and BW.old_party_sections(past) == BW.old_party_sections(payload))
        if not same:
            out["old_diff"] += 1
            if out["first_bad"] is None:
                out["first_bad"] = f"an old reader differs on a frame with section 10 {key}"
    n = out["with10"]
    want = None if expect is None or per_frame else BW.hex_bytes(expect)
    out["ok"] = bool(out["frames"]) and n == out["frames"] == out["ordered"] and not out["malformed"] \
        and not out["old_diff"] and not out["disagree"] and (want is None or out["bodies"] == {want: n})
    return out


def tape_speed_lines(path, expect=None) -> tuple:
    """[ff9mapkit netsync s163] (ok, the ``speed`` report's lines) for a tape file (``expect`` as :func:`tape_speed`)."""
    header, records, torn = read_tape(path)
    d = tape_speed(records, expect)
    want = "" if expect is None or callable(expect) else f" (want {BW.hex_bytes(expect)})"
    lines = [f"tape {path}", f"host type-5 frames: {d['frames']}; with section 10: {d['with10']} (in s163's order: {d['ordered']}, "
             f"malformed: {d['malformed']})" + (f"; TORN tail {torn} B" if torn else "")
             + (f" -- first out of order: {d['first_order']}" if d["first_order"] else ""),
             "section 10 bodies: " + (", ".join(f"{k} x{v}" for k, v in d["bodies"].items()) or "none -- an s162-or-older host")
             + want,
             "host booster settings: " + (", ".join(f"{s} x{v}" for s, v in sorted(d["settings"].items())) or "none")
             + f" ({d['boosted']} frame(s) boosted)",
             f"old-guest readers (story, party sections, sections 4-9, a section past it) with section 10 vs stripped: "
             f"{d['with10'] - d['old_diff']} identical, {d['old_diff']} different"
             + (f" ({d['first_bad']})" if d["first_bad"] else ""),
             "VERDICT: " + ("OK -- section 10 rides every host state frame, before section 7, and an old guest skips it"
                            if d["ok"] else "FAIL")]
    return d["ok"], lines


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


def cmd_speed(args) -> int:
    """[ff9mapkit netsync s163] The ``speed`` verb: :func:`tape_speed_lines` on a resolved tape (``--expect HEX``: one body)."""
    found, tried = resolve_tape(args.tape)
    if found is None:
        print(f"ERROR: no tape {args.tape!r} -- tried {', '.join(str(t) for t in tried)}", file=sys.stderr)
        return 2
    try:
        expect = bytes(int(t, 16) for t in args.expect.replace("-", " ").split()) if args.expect else None
        ok, lines = tape_speed_lines(found, expect)
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
    # [ff9mapkit netsync s157] THE GHOST FRAME's wire half: what the host's ghost of this guest is asked to frame-follow
    p.add_argument("--anim", type=lambda t: int(t, 0), default=None, metavar="ID",
                   help="pin the type-0 anim id (default: the host's own, mirrored) -- e.g. 10539, Zidane's LADDER_1_2")
    p.add_argument("--loco", type=int, choices=range(6), default=None, metavar="0-5",
                   help="pin the type-0 loco byte (default: the host's own; 0 = Other, the only class an s157 ghost follows)")
    p.add_argument("--frame", type=_parse_frame, default="echo", metavar="echo|none|F/N",
                   help="the type-0 trailing frame: echo (default: the host's own; 37 B from a pre-s157 host), none (always "
                        "37 B: a pre-s157 guest, the calibration red) or F/N pinned")
    p.add_argument("--frame-step", type=int, default=0, metavar="S",
                   help="with --frame F/N: advance F by S per tick (30 Hz), mod N -- negative runs backwards (the seam both ways)")
    # [ff9mapkit netsync s166] THE v15 WIRE: the send version, the world trailer, the walking guest record, a gap in the record
    p.add_argument("--wire", choices=("auto",) + tuple(str(v) for v in WIRE_VERSIONS), default="auto",
                   help="the version byte this guest sends: auto (default: the host's first header -- nothing is sent before it) "
                        "or a pinned version (the probed netsync.wire); a host frame of another version is DROPPED, as the engine does")
    p.add_argument("--trailer", choices=TRAILER_MODES, default="auto",
                   help="the v15 world trailer on every 39-byte type-0 frame at wire >= 15: auto (default; a v15 engine always "
                        "sends one), tfmt0 (the engine's `worldwalk pose off`: 55 zero bytes, a capless peer at 94 B) or off (a "
                        "capless v15 peer at 39 B: what a restamped v14 tape is)")
    p.add_argument("--no-follow", action="store_true",
                   help="the trailer's flags b0 CLEAR: a peer that does not follow (the host draws no lines and no ghost for it)")
    p.add_argument("--walk", type=_parse_route, default=None, metavar="roam|X,Z,S;X,Z,S;...",
                   help="send a WALKING v15 guest's world record instead of mirroring the host: roam (the synthetic ROAM route on "
                        "9011: FS_LANDING, legs with stands, one across the x seam, ICE_TILE) or waypoints x,z,stand-seconds")
    p.add_argument("--walk-ups", type=float, default=WALK_UPS, metavar="U",
                   help=f"--walk speed in units a second (default {WALK_UPS:g})")
    p.add_argument("--walk-out", type=float, default=WALK_OUT_S, metavar="S",
                   help=f"--walk: seconds of the follow-out first (place 2, state b5; default {WALK_OUT_S:g})")
    p.add_argument("--walk-load", type=float, default=WALK_LOAD_S, metavar="S",
                   help=f"--walk: then seconds of the world load (place 3, ONE fresh frame then re-sent with the seq frozen; "
                        f"default {WALK_LOAD_S:g})")
    p.add_argument("--world", type=int, default=WALK_WORLD, metavar="ID", help=f"--walk: the world id (default {WALK_WORLD})")
    p.add_argument("--world-model", type=int, default=None, metavar="ID",
                   help="--walk: the walker's model (default decision 11's: 309 on 9002, 310 elsewhere)")
    p.add_argument("--world-tps", type=int, default=WALK_TPS, metavar="N", help=f"the trailer's WorldTPS (default {WALK_TPS})")
    p.add_argument("--state", type=lambda t: int(t, 0) & 0xFF, default=WALK_STATE, metavar="BITS",
                   help=f"--walk: the state byte while walking (default 0x{WALK_STATE:02X}: b1 walking, b2 control, b7 visible -- "
                        "a released guest; 0x85 a frozen one)")
    p.add_argument("--scene-at", action="append", default=[], metavar="S",
                   help="--walk: set state b6 (scene, control off) from session second S; repeatable")
    p.add_argument("--scene-for", action="append", default=[], metavar="N", help="the scene window's length (one per --scene-at)")
    p.add_argument("--gap-at", action="append", default=[], metavar="S",
                   help="send NOTHING from session second S (the record's own gap: the arrivals stop, its seq runs on); repeatable")
    p.add_argument("--gap-for", action="append", default=[], metavar="N", help="the gap's length (one per --gap-at, or one for all)")
    p.add_argument("--tap", metavar="FILE", help="record every frame both ways to this tape (.f9tape)")
    p.add_argument("--status", type=float, default=5.0, metavar="S", help="a status line every S s (default 5)")
    p.add_argument("--log", metavar="FILE", help="tee every line to this file too")


def _parse_route(text: str):
    """[ff9mapkit netsync s166] `--walk`: "roam" or waypoints "x,z,stand;x,z,stand;..." (at least two)."""
    t = text.strip().lower()
    if t == "roam":
        return "roam"
    try:
        pts = [tuple(float(v) for v in part.split(",")) for part in t.split(";") if part.strip()]
    except ValueError:
        pts = []
    if len(pts) < 2 or any(len(pt) != 3 or pt[2] < 0 for pt in pts):
        raise argparse.ArgumentTypeError("--walk is roam or two or more x,z,stand-seconds waypoints split by ';'")
    return tuple(pts)


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
    # [ff9mapkit netsync s166] the send wire and THE FREEZE (the writer's real re-send while its game sits in a sync load)
    p.add_argument("--wire", choices=REPLAY_WIRE_MODES, default="auto",
                   help="the version byte the replay sends: auto (default: the guest's first header -- a v14 tape is restamped "
                        "up to a v15 guest, exactly a capless v15 host), tape (as recorded: never restamped) or a version "
                        "(the probed netsync.wire; never below the tape's own)")
    p.add_argument("--freeze-at", action="append", default=[], metavar="T",
                   help="from tape time T the link stays open and the host RE-SENDS its last slot frames byte-identical every "
                        "tick (the seq frozen: a host in its own synchronous load); repeatable")
    p.add_argument("--freeze-for", action="append", default=[], metavar="N",
                   help="the freeze's length in seconds (one per --freeze-at, or one for all)")
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

    p = sub.add_parser("speed", help="[s163] section 10 (the host's booster) on a tape's host state frames: present, before "
                                     "section 7 with 8 still last, its body, skipped by the old readers")
    p.add_argument("tape", help="the tape (resolved as `dress` resolves it)")
    p.add_argument("--expect", metavar="HEX", help="the body every frame must carry, e.g. '03 1e' (setting 3, FieldTPS 30)")
    p.set_defaults(func=cmd_speed)

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
                        "calibration); any: report only; [s145] world-battle: a world-map battle (b6 before and after it)")
    # [ff9mapkit netsync s165] the host's world pose per frame (section 0's on-foot anchor): a report after the verdict
    p.add_argument("--pose", action="store_true",
                   help="[s165] also print the host's world pose per state frame: x/y/z/yaw off section 0 (64-72), [102] [190] "
                        "[2..3] [181] [0..1], section 7's heartbeat and b6/b1, the tape second (the exit code stays --want's); "
                        "[s166] and the last type-0 frame's v15 world trailer beside it (`tr`: place, world, x/y/z, yaw, mode, "
                        "caps, seq, state, flags)")
    p.add_argument("--every", type=float, default=POSE_EVERY_S, metavar="S",
                   help=f"with --pose: one row per S tape seconds (default {POSE_EVERY_S:g}; 0 = every frame) -- every edge "
                        "(b6, b1, [102], [190], [181], [2..3]) is kept")
    p.add_argument("--near", type=_parse_xz, default=None, metavar="X,Z",
                   help="with --pose: add the TORUS distance to this world point (e.g. 1197.37,-796.7, the Ice Cavern tile)")
    p.set_defaults(func=cmd_where)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
