"""Live smoke test for the v2 jawn-relay (rejoin grace).

Self-contained minimal WebSocket client (TLS + handshake + masked frames) so it
does not depend on the in-flux ff9mapkit bridge module. Exercises:
  1. pair + forward host->guest
  2. ABNORMAL guest kill (RST, no close frame) -> host leg must SURVIVE
  3. guest REJOIN with the same code -> forwarding resumes, both directions
  4. clean host close (1000) -> guest torn down promptly (no 60s hang)
"""

import base64
import os
import socket
import ssl
import struct
import sys
import time

HOST = "relay.jawnston.com"
PORT = 443
CODE = "FABLE-SMOKE-" + base64.b32encode(os.urandom(4)).decode().rstrip("=")


def connect(role, timeout=10.0):
    raw = socket.create_connection((HOST, PORT), timeout=timeout)
    ctx = ssl.create_default_context()
    s = ctx.wrap_socket(raw, server_hostname=HOST)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET /sess/{CODE}?role={role} HTTP/1.1\r\n"
        f"Host: {HOST}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = s.recv(4096)
        if not chunk:
            raise ConnectionError(f"{role}: handshake EOF")
        resp += chunk
    status = resp.split(b"\r\n", 1)[0].decode()
    if "101" not in status:
        raise ConnectionError(f"{role}: bad handshake: {status}")
    return s


def send_frame(s, payload, opcode=0x2):
    mask = os.urandom(4)
    header = bytes([0x80 | opcode])
    n = len(payload)
    if n < 126:
        header += bytes([0x80 | n])
    elif n < 65536:
        header += bytes([0x80 | 126]) + struct.pack(">H", n)
    else:
        header += bytes([0x80 | 127]) + struct.pack(">Q", n)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    s.sendall(header + mask + masked)


def recv_exact(s, n):
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("EOF")
        buf += chunk
    return buf


def recv_frame(s, timeout=5.0):
    """Returns (opcode, payload). Server frames are unmasked."""
    s.settimeout(timeout)
    b0, b1 = recv_exact(s, 2)
    opcode = b0 & 0x0F
    n = b1 & 0x7F
    if n == 126:
        n = struct.unpack(">H", recv_exact(s, 2))[0]
    elif n == 127:
        n = struct.unpack(">Q", recv_exact(s, 8))[0]
    payload = recv_exact(s, n) if n else b""
    return opcode, payload


def expect_data(s, want, who):
    op, payload = recv_frame(s)
    assert op == 0x2 and payload == want, f"{who}: got op={op} payload={payload!r}, want {want!r}"
    print(f"  PASS: {who} received {want!r}")


def main():
    print(f"session code: {CODE}")

    print("[1] pair + forward")
    host = connect("host")
    guest = connect("guest")
    time.sleep(0.5)
    send_frame(host, b"hello-1")
    expect_data(guest, b"hello-1", "guest")

    print("[2] abnormal guest kill (RST) -> host must survive")
    guest.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    guest.close()
    time.sleep(1.0)
    send_frame(host, b"hello-2")  # dropped server-side; must not error
    try:
        op, _ = recv_frame(host, timeout=2.0)
        assert op != 0x8, "host received a CLOSE frame -- session was torn down!"
        raise AssertionError(f"host unexpectedly received op={op}")
    except socket.timeout:
        print("  PASS: host leg still open (no close frame, no error) through the guest drop")

    print("[3] guest rejoin -> forwarding resumes both ways")
    guest2 = connect("guest")
    time.sleep(0.5)
    send_frame(host, b"hello-3")
    expect_data(guest2, b"hello-3", "rejoined guest")
    send_frame(guest2, b"back-1")
    expect_data(host, b"back-1", "host (reverse dir after rejoin)")

    print("[4] clean host close -> guest torn down promptly")
    send_frame(host, struct.pack(">H", 1000), opcode=0x8)
    t0 = time.time()
    try:
        op, _ = recv_frame(guest2, timeout=5.0)
        took = time.time() - t0
        assert op == 0x8, f"guest got op={op}, expected CLOSE"
        print(f"  PASS: guest received CLOSE {took:.2f}s after the host's clean quit")
    except ConnectionError:
        took = time.time() - t0
        print(f"  PASS: guest connection ended {took:.2f}s after the host's clean quit (EOF)")
    host.close()
    guest2.close()

    print("ALL PASS")


if __name__ == "__main__":
    sys.exit(main())
