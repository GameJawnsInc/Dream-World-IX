#!/usr/bin/env python3
"""ws->wss bridge for the FF9 co-op ghost sync (netsync).

FF9's ancient Unity Mono runtime has no TLS 1.2, so the game cannot reach the
public wss:// relay directly. Each player runs this tiny bridge next to the
game instead:

    FF9 (Memoria.ini: RelayUrl = ws://127.0.0.1:49201)
      -> this bridge (plaintext WebSocket on loopback)
      -> the public relay (WebSocket over TLS)

The bridge terminates the WebSocket HTTP handshake on both hops (the request
path -- which carries the session code + role -- is forwarded verbatim), then
pumps bytes unchanged in both directions: client->server frames are masked on
both hops and server->client frames are unmasked on both hops, so no frame
rewriting is needed.

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


def open_upstream(relay, path, insecure):
    """Dial the relay and complete a WebSocket client handshake for `path`."""
    secure, host, port = parse_ws_url(relay)
    sock = socket.create_connection((host, port), timeout=10)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    if secure:
        ctx = ssl.create_default_context()
        if insecure:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
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


def pump(src, dst, activity=None):
    """Copy bytes src->dst until either side dies, then tear both down. With `activity`
    given, the session is reaped after IDLE_TIMEOUT of silence on BOTH directions -- the
    clock is shared, since one quiet direction is normal (the relay sends nothing to a
    host waiting for its peer to pair)."""
    try:
        while True:
            if activity is not None:
                src.settimeout(min(5.0, IDLE_TIMEOUT))
                try:
                    data = src.recv(4096)
                except socket.timeout:
                    if activity.idle_for() >= IDLE_TIMEOUT:
                        log("session idle %.0fs on both directions, closing" % activity.idle_for())
                        break
                    continue
            else:
                data = src.recv(4096)
            if not data:
                break
            if activity is not None:
                activity.touch()
                _patient_sendall(dst, data, IDLE_TIMEOUT)
            else:
                dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def handle_client(client, addr, relay, insecure):
    upstream = None
    try:
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        req = read_http_headers(client)
        lines = req.split("\r\n")
        try:
            method, path, _ = lines[0].split(" ", 2)
        except ValueError:
            raise ConnectionError("malformed request line: %r" % lines[0])
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

        act = _Activity()
        t = threading.Thread(target=pump, args=(client, upstream, act), daemon=True)
        t.start()
        pump(upstream, client, act)
        t.join(timeout=5)
        log("session %s closed" % path)
    except Exception as err:
        log("connection from %s failed: %s" % (addr[0], err))
    finally:
        for s in (client, upstream):
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
            except OSError:
                return  # server socket closed

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
