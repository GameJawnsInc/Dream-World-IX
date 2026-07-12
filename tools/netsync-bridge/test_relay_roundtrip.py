#!/usr/bin/env python3
"""End-to-end bridge test WITHOUT the game: two minimal WebSocket clients
(one host, one guest -- speaking exactly like the engine's NetSyncRelay:
masked binary frames, 34-byte packets) connect through a local bridge
instance to the real relay under a random throwaway ff9- session code, and
each must receive the other's packet verbatim.

    py test_relay_roundtrip.py [--relay ws://host:port] [--insecure]

Exercises: both WS handshakes, TLS to the relay, host/guest pairing, and the
verbatim byte pump in both directions.
"""

import argparse
import base64
import hashlib
import os
import socket
import sys
import time

import netsync_bridge as bridge


def ws_client_connect(port, path):
    """Open a WebSocket connection to the local bridge, like NetSyncRelay does."""
    sock = socket.create_connection(("127.0.0.1", port), timeout=15)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    req = (
        "GET %s HTTP/1.1\r\n"
        "Host: 127.0.0.1:%d\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: %s\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n" % (path, port, key)
    )
    sock.sendall(req.encode("ascii"))
    resp = bridge.read_http_headers(sock)
    status = resp.split("\r\n", 1)[0]
    assert " 101" in status, "bridge refused upgrade: %s" % status
    expect = base64.b64encode(
        hashlib.sha1((key + bridge._WS_GUID).encode("ascii")).digest()
    ).decode("ascii")
    assert expect in resp, "bridge sent a bad Sec-WebSocket-Accept"
    return sock


def send_binary(sock, payload):
    """Client frames MUST be masked (RFC 6455) -- same framing NetSyncRelay emits."""
    assert len(payload) < 126
    mask = os.urandom(4)
    frame = bytearray([0x82, 0x80 | len(payload)]) + mask
    frame += bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
    sock.sendall(bytes(frame))


def recv_frame(sock, deadline):
    """Read one frame (server frames are unmasked); answer pings; return (opcode, payload)."""
    def read_full(n):
        buf = b""
        while len(buf) < n:
            sock.settimeout(max(0.1, deadline - time.time()))
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed mid-frame")
            buf += chunk
        return buf

    while True:
        hdr = read_full(2)
        opcode = hdr[0] & 0x0F
        masked = bool(hdr[1] & 0x80)
        length = hdr[1] & 0x7F
        if length == 126:
            ext = read_full(2)
            length = (ext[0] << 8) | ext[1]
        elif length == 127:
            length = int.from_bytes(read_full(8), "big")
        mask = read_full(4) if masked else None
        payload = read_full(length) if length else b""
        if mask:
            payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        if opcode == 0x9:  # ping -> pong (masked, we are a client)
            pmask = os.urandom(4)
            frame = bytearray([0x8A, 0x80 | len(payload)]) + pmask
            frame += bytes(b ^ pmask[i & 3] for i, b in enumerate(payload))
            sock.sendall(bytes(frame))
            continue
        if opcode == 0xA:  # pong
            continue
        return opcode, payload


def fake_packet(tag):
    """A NetSyncSocket-shaped 34-byte packet, tagged so the two directions differ."""
    body = bytes([0xF9, 0x01]) + tag.to_bytes(2, "little") + os.urandom(30)
    assert len(body) == 34
    return body


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--relay", default=None, help="relay URL override (default: the bridge's built-in)")
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args(argv)

    relay = args.relay or bridge.default_relay()
    server, _ = bridge.run_server("127.0.0.1", 0, relay, args.insecure)
    port = server.getsockname()[1]
    code = "ff9-test" + base64.b32encode(os.urandom(5)).decode("ascii").lower()
    print("bridge on 127.0.0.1:%d, session %s" % (port, code))

    host = ws_client_connect(port, "/sess/%s?role=host" % code)
    guest = ws_client_connect(port, "/sess/%s?role=guest" % code)
    print("both clients connected through the bridge")

    deadline = time.time() + 20
    pkt_h, pkt_g = fake_packet(1), fake_packet(2)
    send_binary(host, pkt_h)
    send_binary(guest, pkt_g)

    op, got_on_guest = recv_frame(guest, deadline)
    assert op == 0x2, "guest got opcode %#x" % op
    assert got_on_guest == pkt_h, "guest received corrupted host packet"
    print("host -> guest: 34 bytes verbatim OK")

    op, got_on_host = recv_frame(host, deadline)
    assert op == 0x2, "host got opcode %#x" % op
    assert got_on_host == pkt_g, "host received corrupted guest packet"
    print("guest -> host: 34 bytes verbatim OK")

    for s in (host, guest):
        s.close()
    server.close()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
