"""ws->wss loopback bridge for co-op netsync (netsync_bridge.py) -- pure-stdlib unit tests for the URL/
handshake primitives (parse_ws_url, ws_accept incl. the RFC 6455 vector, default_relay), an isolated test
of the frame reader (_FramedConn) via a bare socketpair, and an end-to-end harness that runs the REAL bridge
(run_server, bound to port 0) against hand-rolled mock relay sockets.

The mock relays are loopback TCP listeners that complete a WebSocket server handshake using the module's
own ``read_http_headers``/``ws_accept`` primitives, then hand the raw accepted socket to the test so it can
push/pull WS frames and prove the bridge forwards WHOLE frames verbatim (no rewriting) and terminates the
HTTP handshake independently on each hop (its own upstream Sec-WebSocket-Key, not the game's). ``ScriptedRelay``
additionally accepts a SEQUENCE of connections so the hop-decoupling contract can be exercised: an upstream
drop must NOT kill the loopback hop -- the bridge redials and frames resume, a partial frame is never split
across the drop, and only a permanent upstream (past the hard cap) closes the game hop.

Every socket gets a timeout and every thread is joined with a timeout -- a hang here would wedge the whole
suite (runs under ``pytest -n 6``); nothing here binds to a fixed port or touches anything but 127.0.0.1.
"""
from __future__ import annotations

import base64
import errno
import os
import socket
import threading
import time
import types

import pytest

from ff9mapkit import netsync_bridge as NB

TIMEOUT = 5


def _ws_frame(payload, *, mask=False):
    """Build one raw WebSocket frame (FIN + binary opcode) around `payload`. Client frames set the
    mask bit + a 4-byte key (RFC 6455 requires masking client->server); server frames are unmasked.
    The bridge forwards frames verbatim, so the exact bytes built here are what must arrive."""
    payload = bytes(payload)
    ln = len(payload)
    out = bytearray([0x82])                       # FIN=1, opcode=2 (binary)
    mbit = 0x80 if mask else 0x00
    if ln < 126:
        out.append(mbit | ln)
    elif ln < 65536:
        out.append(mbit | 126)
        out += ln.to_bytes(2, "big")
    else:
        out.append(mbit | 127)
        out += ln.to_bytes(8, "big")
    if mask:
        key = os.urandom(4)
        out += key
        out += bytes(payload[i] ^ key[i % 4] for i in range(ln))
    else:
        out += payload
    return bytes(out)


# --------------------------------------------------------------------------- 8: pure unit tests

def test_parse_ws_url_host_port_and_path_ignored():
    assert NB.parse_ws_url("ws://host:1234/x") == (False, "host", 1234)


def test_parse_ws_url_wss_default_port():
    assert NB.parse_ws_url("wss://host") == (True, "host", 443)


def test_parse_ws_url_ws_default_port():
    assert NB.parse_ws_url("ws://host") == (False, "host", 80)


def test_parse_ws_url_ipv6_brackets_stripped():
    # the brackets are URL syntax, not part of the address -- socket.create_connection and
    # ssl server_hostname (SNI/cert hostname check) both reject a bracketed literal.
    assert NB.parse_ws_url("ws://[::1]:9000") == (False, "::1", 9000)


def test_parse_ws_url_ipv6_no_port_defaults_by_scheme():
    assert NB.parse_ws_url("wss://[::1]") == (True, "::1", 443)
    assert NB.parse_ws_url("ws://[::1]") == (False, "::1", 80)


def test_ws_accept_rfc6455_vector():
    # The canonical RFC 6455 section 1.3 worked example.
    assert NB.ws_accept("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


def test_default_relay_is_a_ws_url():
    url = NB.default_relay()
    assert url.startswith("ws://") or url.startswith("wss://")
    # round-trips through the module's own parser without raising, and yields a real host/port
    secure, host, port = NB.parse_ws_url(url)
    assert host
    assert isinstance(port, int) and port > 0


# --------------------------------------------------------------------------- _FramedConn in isolation

def test_framed_conn_reassembles_whole_frames_across_tcp_segmentation():
    # TCP is a stream: a recv may split a frame or hold several. The reader must return WHOLE frames
    # regardless of where the byte boundaries fell. Covers 7-bit and 16-bit length encodings and both
    # masked (client) and unmasked (server) header sizes.
    a, b = socket.socketpair()
    reader = NB._FramedConn(b, NB._Activity(), threading.Event())
    f1 = _ws_frame(b"alpha", mask=True)               # short, masked -> 2 + 4 + 5 bytes
    f2 = _ws_frame(bytes(range(200)), mask=False)     # 200-byte payload -> 16-bit extended length
    blob = f1 + f2
    try:
        # deliberately split the stream mid-frame in a couple of places
        a.sendall(blob[:3])
        time.sleep(0.03)
        a.sendall(blob[3:len(f1) + 5])
        time.sleep(0.03)
        a.sendall(blob[len(f1) + 5:])
        assert reader.read_frame() == f1
        assert reader.read_frame() == f2
    finally:
        a.close()
        b.close()


def test_framed_conn_raises_closed_on_eof_flagging_mid_frame():
    a, b = socket.socketpair()
    reader = NB._FramedConn(b, NB._Activity(), threading.Event())
    try:
        # a lone partial header byte, then EOF -> _Closed with mid_frame=True (a byte was buffered)
        a.sendall(_ws_frame(b"x")[:1])
        a.close()
        with pytest.raises(NB._Closed) as ei:
            reader.read_frame()
        assert ei.value.mid_frame is True
    finally:
        b.close()


def test_framed_conn_clean_eof_at_boundary_is_not_mid_frame():
    a, b = socket.socketpair()
    reader = NB._FramedConn(b, NB._Activity(), threading.Event())
    try:
        a.close()                                     # EOF with an empty buffer -> at a frame boundary
        with pytest.raises(NB._Closed) as ei:
            reader.read_frame()
        assert ei.value.mid_frame is False
    finally:
        b.close()


# --------------------------------------------------------------------------- harness

def _unused_port():
    """Bind to port 0, read the OS-assigned port, then close -- yields a port nothing listens on
    (best-effort: nothing else grabs it in the tiny window before the caller dials it)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class MockRelay:
    """A minimal loopback WS relay: accepts ONE connection, completes the server-side handshake with the
    bridge module's own primitives, records the request line/headers, then exposes the raw accepted socket
    (``self.conn``) so the test can send/recv bytes directly to verify byte-transparent pumping."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(TIMEOUT)
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.url = "ws://127.0.0.1:%d" % self.port
        self.ready = threading.Event()
        self.conn = None
        self.request_line = None
        self.path = None
        self.headers = {}
        self.key = None
        self.error = None
        self._thread = threading.Thread(target=self._accept, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _accept(self):
        try:
            conn, _addr = self.sock.accept()
            conn.settimeout(TIMEOUT)
            req = NB.read_http_headers(conn)
            lines = req.split("\r\n")
            self.request_line = lines[0]
            _method, path, _proto = lines[0].split(" ", 2)
            self.path = path
            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    self.headers[k.strip().lower()] = v.strip()
            self.key = self.headers.get("sec-websocket-key")
            accept = NB.ws_accept(self.key)
            conn.sendall(
                (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    "Sec-WebSocket-Accept: %s\r\n\r\n" % accept
                ).encode("ascii")
            )
            self.conn = conn
        except Exception as err:  # noqa: BLE001 -- surfaced to the test via .error
            self.error = err
        finally:
            self.ready.set()

    def close(self):
        for s in (self.conn, self.sock):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass


class Bridge:
    """Runs the real ``run_server`` bound to port 0 (never a hardcoded port); tears itself down on close()."""

    def __init__(self, relay_url, insecure=False):
        self.server, self.thread = NB.run_server("127.0.0.1", 0, relay_url, insecure)
        self.port = self.server.getsockname()[1]

    def close(self):
        try:
            self.server.close()
        except OSError:
            pass
        self.thread.join(timeout=TIMEOUT)


def _connect_game(bridge_port, path="/s/ABC123?role=host", key=None):
    """Open a socket to the bridge and send a valid WebSocket upgrade GET for `path`. Returns (sock, key)."""
    if key is None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT)
    sock.connect(("127.0.0.1", bridge_port))
    req = (
        "GET %s HTTP/1.1\r\n"
        "Host: 127.0.0.1:%d\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: %s\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n" % (path, bridge_port, key)
    ).encode("ascii")
    sock.sendall(req)
    return sock, key


def _recv_exact(sock, n, timeout=TIMEOUT):
    """Read exactly n bytes (across multiple recv calls -- TCP is a stream) or raise."""
    sock.settimeout(timeout)
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise AssertionError("connection closed after %d/%d bytes" % (len(data), n))
        data += chunk
    return bytes(data)


def _recv_until_closed(sock, timeout=TIMEOUT):
    """Drain whatever the peer sends until EOF/close/error, returning the collected bytes."""
    sock.settimeout(timeout)
    data = bytearray()
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    except OSError:
        pass
    return bytes(data)


@pytest.fixture
def relay():
    r = MockRelay().start()
    yield r
    r.close()


class ScriptedRelay:
    """A loopback WS relay that accepts a SEQUENCE of connections (for the upstream-redial contract).
    Each accepted connection completes the server handshake, is appended to ``.conns`` in order, then
    its matching ``handlers[i](self, conn)`` runs (a handler that leaves the conn OPEN just returns;
    the accept loop keeps going with a short accept timeout). ``max_accepts`` closes the listener after
    that many accepts, so further (redial) connects are REFUSED -- the permanent-outage case."""

    def __init__(self, handlers=(), max_accepts=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.5)
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        self.url = "ws://127.0.0.1:%d" % self.port
        self.handlers = list(handlers)
        self.max_accepts = max_accepts
        self.conns = []
        self.accept_count = 0
        self.errors = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _serve(self):
        while not self._stop.is_set():
            try:
                conn, _addr = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return  # listener closed (max_accepts, or close())
            try:
                conn.settimeout(TIMEOUT)
                req = NB.read_http_headers(conn)
                headers = {}
                for line in req.split("\r\n")[1:]:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        headers[k.strip().lower()] = v.strip()
                accept = NB.ws_accept(headers.get("sec-websocket-key"))
                conn.sendall(
                    (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        "Sec-WebSocket-Accept: %s\r\n\r\n" % accept
                    ).encode("ascii")
                )
                idx = self.accept_count
                self.accept_count += 1
                self.conns.append(conn)
                if self.max_accepts is not None and self.accept_count >= self.max_accepts:
                    try:
                        self.sock.close()  # refuse every further (redial) connect
                    except OSError:
                        pass
                handler = self.handlers[idx] if idx < len(self.handlers) else None
                if handler is not None:
                    handler(self, conn)
            except Exception as err:  # noqa: BLE001 -- surfaced to the test via .errors
                self.errors.append(err)

    def close(self):
        self._stop.set()
        for s in [self.sock] + self.conns:
            try:
                s.close()
            except OSError:
                pass
        self._thread.join(timeout=TIMEOUT)


def _h_send(*frames):
    """Handler: send these frames, then RETURN leaving the connection open (stays in .conns)."""
    def handler(relay, conn):
        for f in frames:
            conn.sendall(f)
    return handler


def _h_send_then_close(*frames):
    """Handler: send these frames, then CLOSE the connection (a clean upstream drop)."""
    def handler(relay, conn):
        for f in frames:
            conn.sendall(f)
        conn.close()
    return handler


def _h_send_partial_then_close(frame, cut):
    """Handler: send only the first `cut` bytes of `frame` (mid-frame), then CLOSE -- a drop that
    orphans a partial frame the bridge must discard rather than forward."""
    def handler(relay, conn):
        conn.sendall(frame[:cut])
        conn.close()
    return handler


# --------------------------------------------------------------------------- 1+2: handshake forwarding

def test_handshake_forwards_path_and_terminates_both_hops(relay):
    bridge = Bridge(relay.url)
    try:
        path = "/s/ABC123?role=host"
        game, game_key = _connect_game(bridge.port, path=path)
        resp = NB.read_http_headers(game)

        assert relay.ready.wait(timeout=TIMEOUT), "mock relay never completed its accept/handshake"
        assert relay.error is None, "mock relay handshake failed: %r" % (relay.error,)

        # 1a: the exact same path (session code + role) reached the relay verbatim.
        assert relay.path == path

        # 1b: what the relay received was a genuine upgrade request with a valid base64 16-byte key.
        assert relay.headers.get("upgrade", "").lower() == "websocket"
        assert relay.key is not None
        assert len(base64.b64decode(relay.key)) == 16

        # 1c: the bridge terminates the handshake on both hops -- its own upstream key, not the game's.
        assert relay.key != game_key

        # 2: the game receives a 101 whose Accept matches ITS OWN key (RFC 6455 rule), not the relay's.
        status_line = resp.split("\r\n", 1)[0]
        assert " 101 " in status_line
        assert NB.ws_accept(game_key) in resp
        game.close()
    finally:
        bridge.close()


# --------------------------------------------------------------------------- 3+4: frame pump both ways

def test_frames_game_to_relay_are_forwarded_verbatim(relay):
    # The bridge is frame-aware now, so the game speaks in WS frames (masked, as a real WS client
    # must). Each WHOLE frame must arrive at the relay byte-for-byte -- header, mask key, payload.
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)  # drain the 101; handshake complete on both hops
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        frames = [
            _ws_frame(b"hello co-op", mask=True),
            _ws_frame(bytes(range(256)), mask=True),          # 256-byte payload -> 16-bit ext length
            _ws_frame(b"\x00\x01\xff\xfe" * 40, mask=True),
        ]
        for f in frames:
            game.sendall(f)
            assert _recv_exact(relay.conn, len(f)) == f

        # a frame split across two sends still arrives whole and verbatim (boundary reassembly)
        big = _ws_frame(os.urandom(500), mask=True)
        game.sendall(big[:7])
        time.sleep(0.05)
        game.sendall(big[7:])
        assert _recv_exact(relay.conn, len(big)) == big
        game.close()
    finally:
        bridge.close()


def test_frames_relay_to_game_are_forwarded_verbatim(relay):
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        frames = [
            _ws_frame(b"welcome to the relay"),                # server frames are unmasked
            _ws_frame(bytes(range(255, -1, -1))),
            _ws_frame(b"\xde\xad\xbe\xef" * 32),
        ]
        for f in frames:
            relay.conn.sendall(f)
            assert _recv_exact(game, len(f)) == f

        big = _ws_frame(os.urandom(600))
        relay.conn.sendall(big[:5])
        time.sleep(0.05)
        relay.conn.sendall(big[5:])
        assert _recv_exact(game, len(big)) == big
        game.close()
    finally:
        bridge.close()


# --------------------------------------------------------------------------- 5: teardown contract
# The hop-decoupling contract: a GAME-side close still ends the whole session (a quitting game
# SHOULD tear down upstream), but an UPSTREAM close must NOT kill the game hop -- the bridge redials.

def test_game_close_tears_down_upstream(relay):
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        # prove the pipe is live before tearing it down
        ping = _ws_frame(b"ping", mask=True)
        game.sendall(ping)
        assert _recv_exact(relay.conn, len(ping)) == ping

        game.close()
        # the relay side must observe EOF (b"") within the timeout, not hang -- the game quit.
        relay.conn.settimeout(TIMEOUT)
        assert relay.conn.recv(4096) == b""
    finally:
        bridge.close()


def test_upstream_close_does_not_kill_game_hop_bridge_redials():
    # THE contract inversion (was test_relay_close_propagates_eof_to_game): a single upstream drop
    # used to tear down the healthy loopback hop, forcing the engine's full ~2.5-3s re-pair. Now the
    # bridge redials and the SAME game socket keeps serving frames -- both ways.
    first = _ws_frame(b"before-drop")
    after = _ws_frame(b"after-redial")
    relay = ScriptedRelay(handlers=[
        _h_send_then_close(first),           # conn #1: deliver a frame, then DROP the upstream
        _h_send(after),                      # conn #2 (the redial): deliver another frame, stay open
    ]).start()
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)

        # frame from conn #1 arrives, then conn #1 drops -- the game hop must NOT close.
        assert _recv_exact(game, len(first)) == first
        # the redial's frame reaches the SAME game socket (never reconnected).
        assert _recv_exact(game, len(after)) == after

        # and the hop is still bidirectional: a game frame reaches the redialed upstream (conn #2),
        # proving the writer picked up the new upstream socket too.
        deadline = time.monotonic() + TIMEOUT
        while len(relay.conns) < 2 and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(relay.conns) >= 2, "bridge never redialed a second upstream connection"
        up = _ws_frame(b"up-after-redial", mask=True)
        game.sendall(up)
        assert _recv_exact(relay.conns[1], len(up)) == up
        game.close()
    finally:
        bridge.close()
        relay.close()


# --------------------------------------------------------------------------- 5b: redial correctness

def test_upstream_drop_midstream_local_hop_stays_open_and_frames_resume():
    # (a) An upstream drop AFTER frames were already flowing: the loopback hop stays open, the bridge
    # redials a fresh upstream, and frames flow again in both directions.
    a1 = _ws_frame(b"pre-drop-server")
    a2 = _ws_frame(b"post-redial-server")
    relay = ScriptedRelay(handlers=[
        _h_send_then_close(a1),
        _h_send(a2),
    ]).start()
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)

        # a frame flowed both ways BEFORE the drop
        assert _recv_exact(game, len(a1)) == a1
        # after the drop the bridge redials and the next server frame still arrives
        assert _recv_exact(game, len(a2)) == a2

        # bidirectional liveness after the redial
        deadline = time.monotonic() + TIMEOUT
        while len(relay.conns) < 2 and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(relay.conns) >= 2
        g = _ws_frame(b"game-after-redial", mask=True)
        game.sendall(g)
        assert _recv_exact(relay.conns[1], len(g)) == g
        game.close()
    finally:
        bridge.close()
        relay.close()


def test_frame_split_across_the_drop_is_never_delivered_partially():
    # (b) The WS-frame-boundary guarantee: a partial frame from a dying upstream must NEVER reach the
    # game (its reader would desync). conn #1 sends only a PREFIX of a frame then drops; the game must
    # see ONLY the whole frame the redial (conn #2) delivers -- never the orphaned prefix.
    doomed = _ws_frame(b"PARTIAL-NEVER-SEEN")
    cut = len(doomed) - 5                              # send all but the last 5 bytes -> mid-frame
    complete = _ws_frame(b"WHOLE-FRAME-AFTER-REDIAL")
    relay = ScriptedRelay(handlers=[
        _h_send_partial_then_close(doomed, cut),
        _h_send(complete),
    ]).start()
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)

        # the FIRST bytes the game ever receives are the complete post-redial frame, exactly.
        got = _recv_exact(game, len(complete))
        assert got == complete
        assert b"PARTIAL" not in got                   # the orphaned prefix never leaked through
        game.close()
    finally:
        bridge.close()
        relay.close()


def test_upstream_permanently_gone_closes_game_hop_after_hard_cap(monkeypatch):
    # (c) The hard cap: if the upstream never comes back, the bridge keeps the game hop alive while it
    # retries, then closes it once UPSTREAM_REDIAL_HARD_CAP elapses (shrunk here for test speed).
    monkeypatch.setattr(NB, "UPSTREAM_REDIAL_HARD_CAP", 2.0)
    first = _ws_frame(b"one-then-gone")
    # max_accepts=1: after the first upstream connection the listener closes, so every redial is
    # REFUSED (fast ConnectionRefused on loopback) -- the upstream is permanently unreachable.
    relay = ScriptedRelay(handlers=[_h_send_then_close(first)], max_accepts=1).start()
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)
        assert _recv_exact(game, len(first)) == first  # the pre-drop frame arrived

        game.settimeout(TIMEOUT + 3)
        start = time.monotonic()
        try:
            reaped = (game.recv(4096) == b"")
        except (ConnectionResetError, ConnectionAbortedError):
            reaped = True
        except socket.timeout:
            reaped = False
        elapsed = time.monotonic() - start

        assert reaped, "game hop was never closed after the upstream became permanently unreachable"
        # NOT instant (proves the bridge tried to redial rather than tearing down on the first drop,
        # the old both-hops-die bug) and bounded near the hard cap.
        assert 0.5 <= elapsed <= 6.0, "hard-cap close timing off: %.2fs" % elapsed
        game.close()
    finally:
        bridge.close()
        relay.close()


# --------------------------------------------------------------------------- 6: relay unreachable

def test_relay_unreachable_closes_game_without_101():
    dead_port = _unused_port()
    bridge = Bridge("ws://127.0.0.1:%d" % dead_port)
    try:
        game, _key = _connect_game(bridge.port)
        data = _recv_until_closed(game)
        # the bridge dials upstream BEFORE replying -- a refused upstream means the game never
        # sees any bytes at all, let alone a 101.
        assert data == b""
        assert b"101" not in data
    finally:
        bridge.close()


# --------------------------------------------------------------------------- 7: non-websocket request

def test_non_websocket_request_is_closed_without_101(relay):
    # Isolates the ONE check being pinned (handle_client's method/Upgrade guard) from its
    # neighbors: a VALID Sec-WebSocket-Key is supplied (so this can't be confused with the
    # separate missing-key rejection a few lines below it in the module), and the bridge points
    # at a LIVE, reachable MockRelay -- not an unreachable dead_port (test 6's scenario) -- so
    # that a connection ever reaching the relay is observable and distinguishes "rejected for not
    # being a websocket upgrade" from "rejected because the relay was unreachable".
    bridge = Bridge(relay.url)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect(("127.0.0.1", bridge.port))
        sock.sendall(
            (
                "GET /s/ABC123 HTTP/1.1\r\n"
                "Host: 127.0.0.1:%d\r\n"
                "Sec-WebSocket-Key: %s\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n" % (bridge.port, key)
            ).encode("ascii")
        )
        data = _recv_until_closed(sock)
        assert data == b""
        assert b"101" not in data

        # The real proof: open_upstream was never called, so the relay never saw a connection at
        # all. Without this assertion, the test can't be told apart from the dead-relay path --
        # this is exactly what the adversarial review caught.
        assert not relay.ready.wait(timeout=1), "bridge dialed the relay despite a non-upgrade request"
        assert relay.conn is None
    finally:
        bridge.close()


# --------------------------------------------------------------------------- 9: flood / thread-spawn hardening

def test_flood_beyond_cap_is_refused_not_fatal(relay, monkeypatch):
    monkeypatch.setattr(NB, "MAX_CLIENTS", 2)
    bridge = Bridge(relay.url)
    holder1 = holder2 = third = None
    try:
        # 2 bare connections that send nothing -- each holds a slot inside read_http_headers.
        holder1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder1.settimeout(TIMEOUT)
        holder1.connect(("127.0.0.1", bridge.port))
        time.sleep(0.2)  # let the accept loop claim the slot

        holder2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder2.settimeout(TIMEOUT)
        holder2.connect(("127.0.0.1", bridge.port))
        time.sleep(0.2)

        # both slots taken -- a 3rd connection must be REFUSED (bridge closes it promptly),
        # not merely accepted-and-left-idle. _recv_until_closed can't tell those apart: an
        # accepted-but-idle socket blocks inside read_http_headers and ALSO eventually reads
        # back b"" once HANDSHAKE_TIMEOUT expires, so a deleted cap would still pass a plain
        # EOF check. Discriminate on WHEN the close happens: TIMEOUT(5) < HANDSHAKE_TIMEOUT(20),
        # so a refused socket hits EOF almost at once while an accepted-idle one blocks the
        # full 5s (recv times out instead of returning).
        third = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        third.settimeout(TIMEOUT)
        third.connect(("127.0.0.1", bridge.port))
        third.settimeout(TIMEOUT)     # TIMEOUT(5) < default HANDSHAKE_TIMEOUT(20): an ACCEPTED idle
                                      # socket blocks the full 5s; a REFUSED one is closed at once.
        try:
            refused = (third.recv(100) == b"")        # bridge.close() -> clean FIN -> EOF
        except (ConnectionResetError, ConnectionAbortedError):
            refused = True                            # Windows may surface the close as RST
        except socket.timeout:
            refused = False                           # still open & idle -> the cap did NOT fire
        assert refused, "over-cap connection was left open instead of refused -- cap not enforced"
        third.close()
        third = None

        # freeing both holders releases their slots -- the accept loop must still be alive to reuse them.
        holder1.close()
        holder2.close()
        holder1 = holder2 = None

        game = game_key = resp = None
        last_err = None
        deadline = time.monotonic() + TIMEOUT
        while resp is None and time.monotonic() < deadline:
            try:
                game, game_key = _connect_game(bridge.port)
                resp = NB.read_http_headers(game)
            except (ConnectionError, OSError) as err:
                last_err = err
                time.sleep(0.1)
        assert resp is not None, "handshake never recovered after slots should have freed: %r" % (last_err,)
        assert " 101 " in resp.split("\r\n", 1)[0]
        assert NB.ws_accept(game_key) in resp
        game.close()
    finally:
        for s in (holder1, holder2, third):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
        bridge.close()


def test_thread_spawn_failure_closes_client_and_loop_survives(relay, monkeypatch):
    bridge = Bridge(relay.url)  # constructed with real threading, before the swap below
    client = None
    try:
        class _Boom:
            def __init__(self, *a, **k):
                raise RuntimeError("can't start new thread")

        # accept_loop resolves "threading" through NB's module globals at call time, so only
        # the bridge's own spawns are affected -- this test's fixtures/threads are untouched.
        monkeypatch.setattr(NB, "threading", types.SimpleNamespace(Thread=_Boom))

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(TIMEOUT)
        client.connect(("127.0.0.1", bridge.port))
        assert _recv_until_closed(client) == b""  # closed, not leaked, loop alive
        client.close()
        client = None

        monkeypatch.setattr(NB, "threading", threading)  # restore -- the loop must still spawn

        game, game_key = _connect_game(bridge.port)
        resp = NB.read_http_headers(game)
        assert " 101 " in resp.split("\r\n", 1)[0]
        assert NB.ws_accept(game_key) in resp
        game.close()
    finally:
        if client is not None:
            try:
                client.close()
            except OSError:
                pass
        bridge.close()


def test_transient_accept_error_keeps_the_loop_alive(relay, monkeypatch):
    bridge = Bridge(relay.url)
    try:
        # The accept loop is blocked in its FIRST server.accept() right now. Shadowing the
        # BOUND method on the instance (bridge.server.accept = ...) raises AttributeError on
        # this Python -- socket.socket instances treat `accept` as read-only. Patch the CLASS
        # method instead, discriminating by identity so every OTHER live socket (the relay's,
        # later game connections) keeps the real accept: only bridge.server's NEXT accept()
        # raises a transient OSError once, then delegates -- proving the loop logs+continues
        # rather than returning (which the pre-fix code did for any OSError).
        real_accept = socket.socket.accept
        fired = {"n": 0}
        def flaky_accept(self, *a, **k):
            if self is bridge.server and fired["n"] == 0:
                fired["n"] = 1
                raise OSError(errno.ECONNABORTED, "simulated transient accept abort")
            return real_accept(self, *a, **k)
        monkeypatch.setattr(socket.socket, "accept", flaky_accept)
        # Trip the currently-blocked real accept with a throwaway conn so the loop advances
        # to the next iteration and picks up flaky_accept (which raises the transient error).
        throwaway = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        throwaway.settimeout(TIMEOUT)
        throwaway.connect(("127.0.0.1", bridge.port))
        # Prove the loop is still alive AFTER the injected transient error: a real handshake
        # must still complete through the (still-unused) MockRelay.
        deadline = time.monotonic() + TIMEOUT
        got_101 = False
        game = None
        while time.monotonic() < deadline and not got_101:
            try:
                game, _k = _connect_game(bridge.port)
                resp = NB.read_http_headers(game)
                got_101 = " 101 " in resp.split("\r\n", 1)[0]
            except (OSError, ConnectionError):
                if game is not None:
                    game.close()
                    game = None
                time.sleep(0.1)
        assert fired["n"] == 1, "flaky_accept never fired -- test did not exercise the transient path"
        assert got_101, "accept loop died after a transient accept error (no 101 served afterward)"
        throwaway.close()
        if game is not None:
            game.close()
    finally:
        bridge.close()


# --------------------------------------------------------------------------- 10: slow-loris + idle reaping

def test_slow_loris_handshake_is_cumulatively_bounded(monkeypatch):
    monkeypatch.setattr(NB, "HANDSHAKE_TIMEOUT", 1.0)
    # upstream is never reached -- the cumulative bound is on the GAME's own handshake read.
    bridge = Bridge("ws://127.0.0.1:%d" % _unused_port())
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(TIMEOUT)
        sock.connect(("127.0.0.1", bridge.port))
        sock.settimeout(0.05)

        closed = False
        start = time.monotonic()
        while time.monotonic() - start < 5.0:
            try:
                sock.sendall(b"x")
            except OSError:
                closed = True
                break
            try:
                probe = sock.recv(1)
            except socket.timeout:
                time.sleep(0.15)
                continue
            except OSError:
                closed = True
                break
            if probe == b"":
                closed = True
                break
            time.sleep(0.15)

        # the trickle (~1 byte/0.15s) arrives far faster than any per-recv timeout could
        # ever expire on -- only a CUMULATIVE deadline explains the close within 5s.
        assert closed, "handshake was never cut off by the cumulative deadline"
    finally:
        try:
            sock.close()
        except OSError:
            pass
        bridge.close()


def test_idle_session_is_reaped(relay, monkeypatch):
    monkeypatch.setattr(NB, "IDLE_TIMEOUT", 1.0)
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        # both sides go silent -- the shared idle clock must end the session on its own.
        # pump's poll = min(5.0, IDLE_TIMEOUT) = 1.0s here, so a working reaper closes ~1-2s in.
        # The UPPER bound below is the real proof: a broken reaper (socket never closed) would
        # instead block until OUR OWN recv gives up -- so its timeout must exceed that bound.
        game.settimeout(10.0)         # MUST exceed the upper bound below, so a broken reaper
                                      # (socket stays open) blocks to 10s and FAILS the upper bound.
        start = time.monotonic()
        try:
            reaped = (game.recv(4096) == b"")
        except (ConnectionResetError, ConnectionAbortedError):
            reaped = True
        except socket.timeout:
            reaped = False
        elapsed = time.monotonic() - start
        assert reaped, "idle session was never torn down"
        assert elapsed < 5.0, "closed only when our own recv gave up, not by the reaper (%.2fs)" % elapsed

        relay.conn.settimeout(TIMEOUT)
        try:
            assert relay.conn.recv(4096) == b""
        except OSError:
            pass
    finally:
        bridge.close()


def test_one_quiet_direction_is_not_reaped(relay, monkeypatch):
    # THE false-positive guard: a host alone, waiting for its peer, gets NOTHING back
    # from the relay for up to the ~60s pairing window -- that one quiet direction must
    # never trip the reaper while the other direction is still live.
    monkeypatch.setattr(NB, "IDLE_TIMEOUT", 2.0)
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        # the game keeps talking (like the engine's ~30Hz keepalive) while the relay stays
        # silent, for LONGER than the patched 2.0s IDLE_TIMEOUT -- a ~10x margin between the
        # 0.2s send interval and the 2.0s reap window (vs the old 4x), so a scheduling hiccup
        # under -n 6 would need to stall >1.8s to false-reap. Each keepalive is a real WS frame
        # (the bridge only forwards whole frames), and receiving it touches the shared idle clock.
        keepalive = _ws_frame(b"k", mask=True)
        sent = 0
        start = time.monotonic()
        while time.monotonic() - start < 2.6:
            game.sendall(keepalive)
            sent += 1
            time.sleep(0.2)

        assert _recv_exact(relay.conn, len(keepalive) * sent) == keepalive * sent

        # the session is still alive both ways.
        pong = _ws_frame(b"x")
        relay.conn.sendall(pong)
        assert _recv_exact(game, len(pong)) == pong
    finally:
        bridge.close()


# --------------------------------------------------------------------------- 11: request-line injection

@pytest.mark.parametrize("bad", [b"\n", b"\r", b"\x00", b"\x85"])
def test_control_bytes_in_request_line_get_400_and_never_reach_relay(relay, bad):
    # a bare LF (or a lone CR -- \r\n\r\n is the only header terminator, so a solo \r
    # survives into the parsed path exactly like \n) embedded in the path token would
    # otherwise be %-formatted verbatim into the outbound upstream GET (open_upstream),
    # i.e. header injection, and into log lines. Must be refused with a clean 400
    # before open_upstream is ever called.
    bridge = Bridge(relay.url)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect(("127.0.0.1", bridge.port))
        sock.sendall(
            b"GET /s/AB" + bad + b"C HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Key: " + key.encode("ascii") + b"\r\n"
            b"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        data = _recv_until_closed(sock)
        assert b"400" in data
        assert b"101" not in data

        # The real proof: open_upstream was never called, so the relay never saw a
        # connection at all -- same pattern as test 7.
        assert not relay.ready.wait(timeout=1), "bridge dialed the relay despite control bytes in the request line"
        assert relay.conn is None
    finally:
        bridge.close()


@pytest.mark.parametrize("reqline", [
    b"GET /s/ABC\n HTTP/1.1",     # trailing LF on the PATH token
    b"GET /s/ABC HTTP/1.1\n",     # trailing LF on the VERSION token (line ends at the next CRLF)
    b"GET\n /s/ABC HTTP/1.1",     # trailing LF on the METHOD token
])
def test_trailing_control_byte_in_request_line_is_refused(relay, reqline):
    # the middle-position test above never exercises a token whose LAST byte is the bad one --
    # a $ anchor without re.MULTILINE matches at end-of-string OR immediately before a single
    # trailing \n, so a token ENDING in LF used to slip past ^[!-~]+$ and reach open_upstream.
    # read_http_headers only terminates on the 4-byte \r\n\r\n, so the bare \n here never ends
    # the line early -- it survives into the parsed token exactly as if the game had sent it.
    bridge = Bridge(relay.url)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect(("127.0.0.1", bridge.port))
        sock.sendall(
            reqline + b"\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Key: " + key.encode("ascii") + b"\r\n"
            b"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        data = _recv_until_closed(sock)
        assert b"400" in data
        assert b"101" not in data

        # Same proof as test 7/11: the relay was never dialed.
        assert not relay.ready.wait(timeout=1), "bridge dialed the relay despite a trailing control byte in the request line"
        assert relay.conn is None
    finally:
        bridge.close()
