"""Unit tests for the ws->wss co-op bridge's URL parsing and socket pump.

Pure-logic / local-socket tests: no game install, no real relay, no network.
"""

import socket

import pytest

from ff9mapkit import netsync_bridge as bridge


# ---------------------------------------------------------------- parse_ws_url

def test_parse_ws_url_plain_host():
    assert bridge.parse_ws_url("ws://127.0.0.1:49201") == (False, "127.0.0.1", 49201)
    assert bridge.parse_ws_url("wss://example.com") == (True, "example.com", 443)
    assert bridge.parse_ws_url("ws://example.com") == (False, "example.com", 80)


def test_parse_ws_url_strips_ipv6_brackets():
    # the brackets are URL syntax, not part of the address -- socket.create_connection and
    # ssl server_hostname (SNI/cert hostname check) both reject a bracketed literal.
    assert bridge.parse_ws_url("wss://[::1]:7777") == (True, "::1", 7777)
    assert bridge.parse_ws_url("ws://[2001:db8::1]:80/session") == (False, "2001:db8::1", 80)


def test_parse_ws_url_ipv6_default_port():
    assert bridge.parse_ws_url("wss://[::1]") == (True, "::1", 443)
    assert bridge.parse_ws_url("ws://[::1]") == (False, "::1", 80)


# ---------------------------------------------------------------- pump

def test_pump_copies_bytes_then_shuts_both_sides_down():
    a, b = socket.socketpair()
    c, d = socket.socketpair()
    a.sendall(b"hello")
    a.close()                        # b.recv() returns b"" next, ending the pump loop
    bridge.pump(b, d)                # 2-arg call -- no `done` event to thread through
    assert c.recv(16) == b"hello"
    with pytest.raises(OSError):     # pump's finally shuts down both src and dst
        d.sendall(b"x")
    for s in (a, b, c, d):
        try:
            s.close()
        except OSError:
            pass
