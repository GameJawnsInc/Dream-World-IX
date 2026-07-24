#!/usr/bin/env python3
"""ws->wss bridge for the FF9 co-op ghost sync (netsync).

FF9's ancient Unity Mono runtime has no TLS 1.2, so the game cannot reach the
public wss:// relay directly. Each player runs this tiny bridge next to the
game instead:

    FF9 (Memoria.ini: RelayUrl = ws://127.0.0.1:49201)
      -> this bridge (plaintext WebSocket on loopback)
      -> the public relay (WebSocket over TLS)

The bridge terminates the WebSocket HTTP handshake on both hops (the request
path -- which carries the session code + role -- is replayed verbatim onto the
upstream GET), then forwards WebSocket frames in both directions. It owns the
upstream handshake completely (its own Sec-WebSocket-Key, not the game's), so
it can re-establish the upstream hop at any time without the game noticing.

**The two hops are DECOUPLED.** The game<->bridge loopback hop stays alive across
a momentary bridge<->relay wobble: on an upstream read/write error or EOF the
bridge closes ONLY the upstream socket, redials it (immediate first try, then a
short capped backoff, giving up only after a hard cap), and resumes -- the game
never sees the ~2.5-3s disconnect/despawn/re-pair ritual a full teardown forced.
The wire is latest-state at ~30Hz, so frames lost during the gap are harmless:
game->relay frames are dropped while upstream is down (never queued), and nothing
arrives relay->game during the outage.

Forwarding is WS-frame-aware (not a raw byte pipe) precisely so a redial is safe:
each hop forwards WHOLE frames, so a partial frame is never split across two
upstream connections, and a partial frame from a dying upstream is never handed
to the game (whose reader would desync). Frames are otherwise byte-transparent --
masked client frames and unmasked server frames alike ride through untouched; the
bridge reads only each frame's length header, it never unmasks or rewrites.

Pure stdlib, no dependencies. This module is the canonical copy (the file in
`tools/netsync-bridge/` is a standalone-friendly shim). Most users never run
it directly -- `ff9mapkit coop host` / `coop join` start it in-process. Usage:

    ff9mapkit coop bridge                            # listen on ws://127.0.0.1:49201
    ff9mapkit coop bridge --port 49300               # different local port
    ff9mapkit coop bridge --relay ws://<ip>:7777     # different relay

The default relay endpoint is baked in lightly obfuscated -- that only keeps
the URL out of dumb GitHub string-scrapers, it is NOT a secret (the real
access gate is the random per-session code in the URL path). Override it
freely with --relay.
"""

import argparse
import base64
import hashlib
import os
import re
import socket
import ssl
import sys
import threading
import time

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# XOR(0x5A) + base64 of the default relay URL (see module docstring).
_OBF_KEY = 0x5A
_OBF_RELAY = "LSkpYHV1KD82OyN0MDstNCkuNTR0OTU3"

# Concurrency cap. Normal use is ONE local game client; the cap only matters when
# something floods the port -- past it we refuse instead of spawning unboundedly
# (CPython eventually fails thread creation, which must never kill the accept loop).
MAX_CLIENTS = 32

# Handshake + idle bounds. A real handshake is a handful of small reads well under a
# second; HANDSHAKE_TIMEOUT caps the CUMULATIVE header read, so a peer trickling one
# byte per recv cannot hold a thread past it. IDLE_TIMEOUT reaps a session once BOTH
# directions have been silent that long: the engine keepalives at ~30 Hz from its own
# thread even in menus (s36 WriteLoop), and the longest engineered ONE-direction
# silence is the relay's ~60s pairing window (the engine's own ReceiveTimeout is 75s
# for it) -- so the clock is shared across both pumps and 120s of two-way silence
# means the game is gone, not quiet.
HANDSHAKE_TIMEOUT = 20.0
IDLE_TIMEOUT = 120.0

# Upstream redial policy (the hop-decoupling contract). A momentary relay/Caddy wobble
# (two-machine play saw upstream EOFs every 10-36s) must NOT tear down the healthy
# loopback hop. On an upstream failure the upstream->game reader redials -- an IMMEDIATE
# first attempt, then a short capped backoff after each subsequent failure -- and only
# gives up (closing the game hop) after UPSTREAM_REDIAL_HARD_CAP seconds with no upstream.
UPSTREAM_REDIAL_HARD_CAP = 45.0
_REDIAL_BACKOFFS = (0.25, 0.5, 1.0, 2.0)   # sleep after the Nth *failed* dial; last value repeats

# WS frame-length awareness. Forwarding whole frames is what makes a redial safe (see the
# module docstring). netsync frames are a few KB; a header claiming more than this is
# corruption we cannot resync from, so we abort rather than attempt an unbounded read.
WS_MAX_FRAME = 1 << 20   # 1 MiB payload cap

# Request-line tokens are re-emitted verbatim into the upstream GET (open_upstream)
# and into log lines -- printable ASCII only, or an embedded bare LF becomes header
# injection in the outbound request. The \A...\Z anchors are load-bearing: $ without
# re.MULTILINE still matches immediately before a single trailing \n, so a token
# ENDING in LF would slip past ^[!-~]+$ -- \Z has no such trailing-newline exemption.
_REQ_TOKEN_RE = re.compile(r"\A[!-~]+\Z")


def default_relay():
    return bytes(b ^ _OBF_KEY for b in base64.b64decode(_OBF_RELAY)).decode("ascii")


def parse_ws_url(url):
    """'ws(s)://host[:port][/ignored]' -> (secure, host, port). An IPv6 literal host's '[...]'
    brackets are URL syntax, not part of the address -- stripped here so `host` is a bare literal
    every socket/ssl call accepts (neither create_connection nor server_hostname take brackets)."""
    url = url.strip()
    secure = False
    if "://" in url:
        scheme, url = url.split("://", 1)
        secure = scheme.lower() == "wss"
    url = url.split("/", 1)[0]
    if url.startswith("["):
        host, _, rest = url[1:].partition("]")
        port = int(rest[1:]) if rest.startswith(":") else (443 if secure else 80)
        return secure, host, port
    if ":" in url:
        host, port = url.rsplit(":", 1)
        return secure, host, int(port)
    return secure, url, 443 if secure else 80


def read_http_headers(sock, cap=16384, timeout=None):
    """Read exactly up to the blank line ending the HTTP headers (never past it --
    bytes after it are WebSocket frame data). Byte-by-byte like the game does.
    The deadline is CUMULATIVE across the whole read, not per-recv -- a peer trickling
    one byte per call cannot ride it out past `timeout` regardless of the cap."""
    if timeout is None:
        timeout = HANDSHAKE_TIMEOUT
    deadline = time.monotonic() + timeout
    data = bytearray()
    while not data.endswith(b"\r\n\r\n"):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ConnectionError("HTTP handshake took longer than %.0fs" % timeout)
        sock.settimeout(remaining)
        b = sock.recv(1)
        if not b:
            raise ConnectionError("peer closed during HTTP handshake")
        data += b
        if len(data) > cap:
            raise ConnectionError("HTTP handshake headers too large")
    return data.decode("latin-1")


def ws_accept(key):
    return base64.b64encode(hashlib.sha1((key + _WS_GUID).encode("ascii")).digest()).decode("ascii")


_SSL_LOCK = threading.Lock()
_SSL_CONTEXTS = {}


def _ssl_context(insecure):
    """One shared SSLContext per verification mode, reused across every (re)dial. Building a fresh
    ssl.create_default_context() per dial reloads the system trust store each time -- wasteful when
    a wobbly relay makes us redial often."""
    with _SSL_LOCK:
        ctx = _SSL_CONTEXTS.get(insecure)
        if ctx is None:
            ctx = ssl.create_default_context()
            if insecure:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            _SSL_CONTEXTS[insecure] = ctx
        return ctx


def open_upstream(relay, path, insecure, ssl_ctx=None, connect_timeout=10):
    """Dial the relay and complete a WebSocket client handshake for `path`. The bridge OWNS this
    handshake (its own fresh Sec-WebSocket-Key), so calling it again -- on redial -- replays the
    same upgrade for the same session code + role without ever touching the game's own WS session.
    `connect_timeout` bounds the TCP connect so a redial cannot overshoot the hard cap on a
    black-holed relay."""
    secure, host, port = parse_ws_url(relay)
    sock = socket.create_connection((host, port), timeout=connect_timeout)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    if secure:
        ctx = ssl_ctx or _ssl_context(insecure)
        sock = ctx.wrap_socket(sock, server_hostname=host)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        host_lit = "[%s]" % host if ":" in host else host   # Host: header needs IPv6 back in brackets
        host_hdr = host_lit if port == (443 if secure else 80) else "%s:%d" % (host_lit, port)
        req = (
            "GET %s HTTP/1.1\r\n"
            "Host: %s\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n" % (path, host_hdr, key)
        )
        sock.sendall(req.encode("ascii"))
        resp = read_http_headers(sock)
        status = resp.split("\r\n", 1)[0]
        if " 101" not in status:
            raise ConnectionError("relay refused upgrade: %s" % status)
        if ws_accept(key) not in resp:
            raise ConnectionError("relay sent a bad Sec-WebSocket-Accept")
        sock.settimeout(None)
        return sock
    except Exception:
        sock.close()
        raise


class _Activity:
    """Monotonic last-traffic clock shared by a session's two pump threads.
    A float store is atomic under the GIL -- no lock."""
    __slots__ = ("_last",)

    def __init__(self):
        self._last = time.monotonic()

    def touch(self):
        self._last = time.monotonic()

    def idle_for(self):
        return time.monotonic() - self._last


def _patient_sendall(dst, data, patience):
    """sendall that tolerates the poll-sized recv timeout the session's OTHER pump
    thread keeps on dst (settimeout is per-socket, not per-direction): short send
    stalls just retry; only 'patience' seconds with NO forward progress is fatal."""
    view = memoryview(data)
    deadline = time.monotonic() + patience
    while view:
        try:
            sent = dst.send(view)
        except socket.timeout:
            if time.monotonic() >= deadline:
                raise
            continue
        if sent:
            view = view[sent:]
            deadline = time.monotonic() + patience


# --------------------------------------------------------------------------- frame-aware pumping


class _Closed(Exception):
    """The socket this reader was reading hit EOF / reset (or the session was told to stop)."""

    def __init__(self, mid_frame):
        super().__init__("mid-frame" if mid_frame else "at frame boundary")
        self.mid_frame = mid_frame


class _IdleReap(Exception):
    """Both directions have been silent for IDLE_TIMEOUT -- reap the session."""


class _ProtocolError(Exception):
    """A WS frame header claimed an implausible length -- cannot resync safely."""


class _FramedConn:
    """Reads WHOLE WebSocket frames off a socket, buffering any bytes read past a frame boundary
    (TCP is a stream: one recv may hold several frames or a partial one). The socket is swappable
    (upstream redial) via replace(), which DROPS the partial-frame buffer -- those bytes belonged to
    the dead connection and must never reach the far side. Shares the session's activity clock
    (touched on every recv) and stop event (set => reads raise _Closed so the pump unwinds promptly).

    Frames are returned verbatim (header + payload, including any 4-byte mask key + masked payload):
    the reader inspects only the length header to find the boundary, it never unmasks or rewrites."""

    __slots__ = ("sock", "buf", "activity", "stop")

    def __init__(self, sock, activity, stop):
        self.sock = sock
        self.buf = bytearray()
        self.activity = activity
        self.stop = stop

    def replace(self, sock):
        self.sock = sock
        self.buf = bytearray()   # leftover belonged to the dead upstream connection -- discard

    def _poll(self):
        return min(5.0, IDLE_TIMEOUT)

    def _pull(self):
        """One recv with a poll-sized timeout. True if bytes arrived (and were buffered), False on
        a poll timeout. Raises _Closed on EOF/reset. (socket.timeout is an OSError subclass, so it
        is caught FIRST -- a real reset must fall through to _Closed.)"""
        self.sock.settimeout(self._poll())
        try:
            chunk = self.sock.recv(4096)
        except socket.timeout:
            return False
        except OSError:
            raise _Closed(len(self.buf) > 0)
        if not chunk:
            raise _Closed(len(self.buf) > 0)
        self.buf += chunk
        self.activity.touch()
        return True

    def _ensure(self, n):
        """Fill the buffer to at least n bytes. Honors stop (raises _Closed); does NOT idle-reap --
        we are mid-frame here, which is a stalled peer, not an idle session."""
        while len(self.buf) < n:
            if self.stop.is_set():
                raise _Closed(True)
            self._pull()

    def read_frame(self):
        """Return one whole frame's raw bytes. Raises _Closed on EOF/stop, _IdleReap on a two-way
        idle session, _ProtocolError on an implausibly large length."""
        # Wait for the first 2 header bytes. This is the ONLY place idle-reaping applies: an empty
        # buffer on a poll timeout means this direction is genuinely quiet at a frame boundary.
        while len(self.buf) < 2:
            if self.stop.is_set():
                raise _Closed(len(self.buf) > 0)
            if not self._pull():
                if len(self.buf) == 0 and self.activity.idle_for() >= IDLE_TIMEOUT:
                    raise _IdleReap()
        b1 = self.buf[1]
        n = b1 & 0x7F
        hlen = 2 + (2 if n == 126 else 8 if n == 127 else 0) + (4 if (b1 & 0x80) else 0)
        self._ensure(hlen)
        if n == 126:
            plen = int.from_bytes(self.buf[2:4], "big")
        elif n == 127:
            plen = int.from_bytes(self.buf[2:10], "big")
        else:
            plen = n
        if plen > WS_MAX_FRAME:
            raise _ProtocolError("ws frame payload %d exceeds the %d-byte cap" % (plen, WS_MAX_FRAME))
        total = hlen + plen
        self._ensure(total)
        frame = bytes(self.buf[:total])
        del self.buf[:total]
        return frame


def _redial_backoff(failed_attempts):
    """Seconds to wait after the Nth failed dial (1-based). The last entry repeats forever."""
    return _REDIAL_BACKOFFS[min(failed_attempts, len(_REDIAL_BACKOFFS)) - 1]


class _Upstream:
    """The redialable upstream hop, shared by a session's two pump threads. The upstream->game
    reader OWNS redial (it is the thread that must block waiting for a fresh socket anyway); the
    game->upstream writer only SIGNALS a write failure via mark_failed(), which flips the state and
    shuts the socket so the reader's blocked recv returns and it redials. Exactly one thread ever
    dials, so there is no dial race.

    state: 'up' (sock live) | 'down' (failed, awaiting/undergoing redial) | 'dead' (hard cap hit)."""

    def __init__(self, sock, relay, path, insecure, stop):
        self.relay = relay
        self.path = path
        self.insecure = insecure
        self.stop = stop
        self._lock = threading.Lock()
        self.sock = sock
        self.gen = 0
        self.state = "up"

    def snapshot(self):
        with self._lock:
            return self.sock, self.gen, self.state

    def mark_failed(self, gen):
        """Signal (from the writer) that a send to generation `gen` failed. Flip up->down and shut
        the socket so the reader's blocked recv returns EOF and it redials. Idempotent, and a no-op
        once the reader has already moved past `gen` (so it never shuts a freshly redialed socket)."""
        with self._lock:
            if self.state == "up" and self.gen == gen:
                self.state = "down"
                doomed = self.sock
            else:
                doomed = None
        if doomed is not None:
            try:
                doomed.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def redial(self, gen):
        """Called by the reader after upstream `gen` died. Close the old socket, then re-open the
        upstream WS handshake (same relay/path/role, fresh key) -- an immediate first try, then a
        capped backoff after each failure, until it succeeds or the hard cap elapses. Returns
        (sock, gen); sock is None when the hard cap OR a session stop ended the attempt."""
        with self._lock:
            if self.state == "dead":
                return None, self.gen
            self.state = "down"
            old = self.sock
            self.sock = None
        if old is not None:
            try:
                old.close()
            except OSError:
                pass
        started = time.monotonic()
        deadline = started + UPSTREAM_REDIAL_HARD_CAP
        failed = 0
        while not self.stop.is_set():
            try:
                # Bound each attempt's connect by the remaining budget so the hard cap is meaningful.
                budget = max(0.25, deadline - time.monotonic())
                new = open_upstream(self.relay, self.path, self.insecure,
                                    connect_timeout=min(10.0, budget))
            except Exception as err:            # noqa: BLE001 -- any dial/handshake failure retries
                failed += 1
                now = time.monotonic()
                if now >= deadline:
                    with self._lock:
                        self.state = "dead"
                    log("upstream hard cap reached (%.0fs, %d tries), closing session"
                        % (UPSTREAM_REDIAL_HARD_CAP, failed))
                    return None, gen
                delay = min(_redial_backoff(failed), max(0.0, deadline - now))
                log("upstream redial %d failed (%s), retrying in %.2fs" % (failed, err, delay))
                self.stop.wait(delay)
                continue
            with self._lock:
                self.sock = new
                self.gen += 1
                self.state = "up"
                newgen = self.gen
            log("upstream restored after %d ms (redial %d)"
                % (int((time.monotonic() - started) * 1000), failed + 1))
            return new, newgen
        # stop was set mid-redial -- the session is ending for another reason.
        with self._lock:
            self.state = "dead"
        return None, gen


class _Session:
    """Decoupled two-hop pump. The game<->bridge loopback hop stays alive across a bridge<->relay
    wobble: on an upstream failure the upstream->game reader redials while the game->upstream writer
    drops frames (harmless -- the wire is latest-state at ~30Hz). Only a game-side close, an upstream
    hard cap, or a two-way idle timeout ends the whole session."""

    def __init__(self, game, upstream_sock, relay, path, insecure):
        self.game = game
        self.path = path
        self.activity = _Activity()
        self.stop = threading.Event()
        self.up = _Upstream(upstream_sock, relay, path, insecure, self.stop)

    def current_upstream(self):
        return self.up.snapshot()[0]

    def _end(self, why):
        newly = not self.stop.is_set()
        self.stop.set()
        if newly:
            log("session %s closing: %s" % (self.path, why))
        # Unblock both readers' recv()s by shutting their sockets down.
        for s in (self.game, self.up.snapshot()[0]):
            if s is not None:
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def _game_to_upstream(self):
        conn = _FramedConn(self.game, self.activity, self.stop)
        while not self.stop.is_set():
            try:
                frame = conn.read_frame()
            except _IdleReap:
                self._end("idle %.0fs on both directions" % IDLE_TIMEOUT)
                return
            except _Closed as end:
                self._end("game hop closed (game->relay reader EOF %s)" % end)
                return
            except _ProtocolError as err:
                self._end("game sent a malformed WS frame (game->relay): %s" % err)
                return
            sock, gen, state = self.up.snapshot()
            if state == "dead":
                self._end("upstream permanently gone (game->relay)")
                return
            if state != "up":
                continue                                 # upstream down/redialing -> drop (newest wins)
            try:
                _patient_sendall(sock, frame, IDLE_TIMEOUT)
            except OSError as err:
                log("upstream write error (game->relay), dropping frame + redialing: %s" % err)
                self.up.mark_failed(gen)                 # kick the reader to redial; frame dropped whole
                continue                                 # -> the next frame starts at a boundary

    def _upstream_to_game(self):
        sock, gen, _ = self.up.snapshot()
        conn = _FramedConn(sock, self.activity, self.stop)
        while not self.stop.is_set():
            try:
                frame = conn.read_frame()
            except _IdleReap:
                self._end("idle %.0fs on both directions" % IDLE_TIMEOUT)
                return
            except (_Closed, _ProtocolError) as err:
                if self.stop.is_set():
                    return
                if isinstance(err, _ProtocolError):
                    log("upstream sent a malformed WS frame (relay->game): %s; redialing" % err)
                else:
                    log("upstream EOF %s (relay->game); redialing"
                        % ("mid-frame" if err.mid_frame else "at boundary"))
                sock, gen = self.up.redial(gen)
                if sock is None:
                    if not self.stop.is_set():
                        self._end("upstream unreachable past the redial hard cap")
                    return
                conn.replace(sock)                       # the discarded partial frame never reaches the game
                continue
            try:
                _patient_sendall(self.game, frame, IDLE_TIMEOUT)
            except OSError as err:
                self._end("game hop closed (relay->game write: %s)" % err)
                return

    def run(self):
        writer = threading.Thread(target=self._game_to_upstream, daemon=True)
        writer.start()
        try:
            self._upstream_to_game()
        finally:
            self._end("session teardown")
            writer.join(timeout=5)


def _refuse(client):
    """Best-effort 400 before closing -- the game never triggers this; only foreign
    clients poking the port do."""
    try:
        client.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
    except OSError:
        pass


def handle_client(client, addr, relay, insecure):
    upstream = None
    sess = None
    try:
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        req = read_http_headers(client)
        lines = req.split("\r\n")
        try:
            method, path, version = lines[0].split(" ", 2)
        except ValueError:
            raise ConnectionError("malformed request line: %r" % lines[0])
        for tok in (method, path, version):
            if not _REQ_TOKEN_RE.match(tok):
                _refuse(client)
                raise ConnectionError("control bytes in request line: %r" % lines[0])
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        if method != "GET" or "websocket" not in headers.get("upgrade", "").lower():
            raise ConnectionError("not a WebSocket upgrade request")
        key = headers.get("sec-websocket-key")
        if not key:
            raise ConnectionError("missing Sec-WebSocket-Key")

        log("game connected, session %s" % path)
        # Upstream FIRST: if the relay is unreachable we just close, and the
        # game's own retry loop (every 2s) tries again.
        upstream = open_upstream(relay, path, insecure)
        client.sendall(
            (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Accept: %s\r\n\r\n" % ws_accept(key)
            ).encode("ascii")
        )
        client.settimeout(None)
        log("relay connected, pumping")

        sess = _Session(client, upstream, relay, path, insecure)
        sess.run()
        log("session %s closed" % path)
    except Exception as err:
        log("connection from %s failed: %s" % (addr[0], err))
    finally:
        # Close the game socket, the session's CURRENT (possibly redialed) upstream, and the
        # original upstream. All idempotent -- a socket already closed by a redial double-closes safely.
        closeables = [client]
        if sess is not None:
            closeables.append(sess.current_upstream())
        closeables.append(upstream)
        for s in closeables:
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass


def log(msg):
    print("[bridge] %s" % msg, flush=True)


def run_server(listen_host, listen_port, relay, insecure):
    """Bind + return the listening socket and the accept-loop thread (for tests)."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen_host, listen_port))
    server.listen(4)

    slots = threading.BoundedSemaphore(MAX_CLIENTS)

    def accept_loop():
        while True:
            try:
                client, addr = server.accept()
            except OSError as err:
                if server.fileno() == -1:
                    return  # the server socket was closed -- the ONLY intended way out
                # transient (ECONNABORTED, or EMFILE/ENOBUFS under a flood) -- must NOT kill
                # the loop; brief backoff so a persistent transient error can't busy-spin.
                log("accept error, continuing: %s" % err)
                time.sleep(0.05)
                continue

            if not slots.acquire(blocking=False):
                log("refusing %s: at MAX_CLIENTS (%d)" % (addr[0], MAX_CLIENTS))
                try:
                    client.close()
                except OSError:
                    pass
                continue

            def bridged(client=client, addr=addr):
                try:
                    handle_client(client, addr, relay, insecure)
                finally:
                    slots.release()

            # A spawn failure (e.g. RuntimeError: can't start new thread, under flood)
            # must never kill this loop -- release the slot, drop the client, keep accepting.
            try:
                threading.Thread(target=bridged, daemon=True).start()
            except Exception as err:
                slots.release()
                try:
                    client.close()
                except OSError:
                    pass
                log("failed to spawn handler for %s: %s" % (addr[0], err))
                continue

    thread = threading.Thread(target=accept_loop, daemon=True)
    thread.start()
    return server, thread


def main(argv=None):
    ap = argparse.ArgumentParser(description="ws->wss bridge for FF9 netsync co-op")
    ap.add_argument("--port", type=int, default=49201, help="local port to listen on (default 49201)")
    ap.add_argument("--relay", default=None, help="relay URL override, ws:// or wss:// (default: built in)")
    ap.add_argument("--insecure", action="store_true", help="skip TLS certificate verification")
    args = ap.parse_args(argv)

    relay = args.relay or default_relay()
    secure, host, port = parse_ws_url(relay)
    server, thread = run_server("127.0.0.1", args.port, relay, args.insecure)
    log("listening on ws://127.0.0.1:%d" % args.port)
    log("forwarding to %s://%s:%d" % ("wss" if secure else "ws", host, port))
    log("point FF9 at it:  Memoria.ini [Netsync] RelayUrl = ws://127.0.0.1:%d" % args.port)
    try:
        thread.join()
    except KeyboardInterrupt:
        log("stopped")
        server.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
