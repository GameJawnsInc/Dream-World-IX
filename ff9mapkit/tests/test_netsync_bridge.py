"""ws->wss loopback bridge for co-op netsync (netsync_bridge.py) -- pure-stdlib unit tests for the URL/
handshake primitives (parse_ws_url, ws_accept incl. the RFC 6455 vector, default_relay), an isolated test
of pump() via a bare socketpair, and an end-to-end harness that runs the REAL bridge (run_server, bound to
port 0) against a hand-rolled mock relay socket.

The mock relay is a loopback TCP listener that completes a WebSocket server handshake using the module's
own ``read_http_headers``/``ws_accept`` primitives, then hands the raw accepted socket to the test so it
can push/pull bytes and prove the bridge is byte-transparent (no frame rewriting) and terminates the HTTP
handshake independently on each hop (its own upstream Sec-WebSocket-Key, not the game's).

Every socket gets a timeout and every thread is joined with a timeout -- a hang here would wedge the whole
suite (runs under ``pytest -n 6``); nothing here binds to a fixed port or touches anything but 127.0.0.1.
"""
from __future__ import annotations

import base64
import os
import socket
import threading

import pytest

from ff9mapkit import netsync_bridge as NB

TIMEOUT = 5


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


# --------------------------------------------------------------------------- pump() in isolation

def test_pump_copies_bytes_then_shuts_both_sides_down():
    a, b = socket.socketpair()
    c, d = socket.socketpair()
    a.sendall(b"hello")
    a.close()                        # b.recv() returns b"" next, ending the pump loop
    NB.pump(b, d)                    # src=b, dst=d -- copies b's queued bytes onto d
    assert c.recv(16) == b"hello"
    with pytest.raises(OSError):     # pump's finally shuts down both src and dst
        d.sendall(b"x")
    for s in (a, b, c, d):
        try:
            s.close()
        except OSError:
            pass


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


# --------------------------------------------------------------------------- 3+4: byte pump both ways

def test_pump_game_to_relay_is_byte_verbatim(relay):
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)  # drain the 101; handshake complete on both hops
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        chunks = [
            b"hello co-op",
            bytes(range(256)),          # full 0x00-0xFF binary sweep
            b"\x00\x01\xff\xfe" * 10,
        ]
        for chunk in chunks:
            game.sendall(chunk)
            assert _recv_exact(relay.conn, len(chunk)) == chunk
        game.close()
    finally:
        bridge.close()


def test_pump_relay_to_game_is_byte_verbatim(relay):
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        chunks = [
            b"welcome to the relay",
            bytes(range(255, -1, -1)),
            b"\xde\xad\xbe\xef" * 8,
        ]
        for chunk in chunks:
            relay.conn.sendall(chunk)
            assert _recv_exact(game, len(chunk)) == chunk
        game.close()
    finally:
        bridge.close()


# --------------------------------------------------------------------------- 5: teardown propagation

def test_game_close_propagates_eof_to_relay(relay):
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        # prove the pipe is live before tearing it down
        game.sendall(b"ping")
        assert _recv_exact(relay.conn, 4) == b"ping"

        game.close()
        # the relay side must observe EOF (b"") within the timeout, not hang.
        relay.conn.settimeout(TIMEOUT)
        assert relay.conn.recv(4096) == b""
    finally:
        bridge.close()


def test_relay_close_propagates_eof_to_game(relay):
    bridge = Bridge(relay.url)
    try:
        game, _game_key = _connect_game(bridge.port)
        NB.read_http_headers(game)
        assert relay.ready.wait(timeout=TIMEOUT)
        assert relay.conn is not None

        relay.conn.sendall(b"pong")
        assert _recv_exact(game, 4) == b"pong"

        relay.conn.close()
        game.settimeout(TIMEOUT)
        assert game.recv(4096) == b""
    finally:
        bridge.close()


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
