"""The co-op bridge's hang sentinel + auto-dump (battle co-op R3 tooling T1; hangdump.py + the netsync_bridge
wiring). Pins:

  * the log line is wall-clock stamped (local time, ms) and teed to a per-run session file;
  * the sentinel fires ONCE when the game->bridge hop goes silent past the threshold, never for a 30 Hz
    peer, re-arms only after frames RESUME, and re-baselines (no fire) when the BRIDGE itself stalled;
  * dumps happen only when enabled, at most once per bridge run, on a worker thread, with the game's
    output_log.txt + Memoria.log copied beside them; disabled -> nothing resolved, copied or written;
  * PID-resolution / writer failures are LOGGED, never raised, and forwarding keeps going;
  * the real Win32 plumbing (iphlpapi owner-PID, toolhelp, image path, dbghelp) works -- calibrated
    against THIS process and a throwaway child, never the game (Windows only).

The dump writer is always mocked except in the Windows calibration test, which writes a MiniDumpNormal
(~30 KB) of a child python into tmp_path. Nothing here touches the real %LOCALAPPDATA% (pinned to
tmp_path), the game install, or a fixed port.
"""
from __future__ import annotations

import base64
import os
import re
import socket
import subprocess
import sys
import threading
import time
import types

import pytest

from ff9mapkit import hangdump as H
from ff9mapkit import netsync_bridge as NB

TIMEOUT = 5
STAMP = r"\d\d:\d\d:\d\d\.\d{3}"


def _ws_frame(payload, *, mask=True):
    payload = bytes(payload)
    out = bytearray([0x82, (0x80 if mask else 0) | len(payload)])
    if mask:
        key = os.urandom(4)
        out += key
        out += bytes(payload[i] ^ key[i % 4] for i in range(len(payload)))
    else:
        out += payload
    return bytes(out)


def _wait(cond, timeout=TIMEOUT, step=0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(step)
    return cond()


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    """Pin %LOCALAPPDATA% (the data root) to tmp and make sure FF9_HANG_DUMP is not inherited."""
    root = tmp_path / "LocalAppData"
    root.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(root))
    monkeypatch.delenv(H.ENV_ENABLE, raising=False)
    return root


# --------------------------------------------------------------------------- log stamping + tee

def test_wallclock_is_local_time_with_ms():
    t = time.mktime((2026, 10, 14, 10, 38, 43, 0, 0, -1)) + 0.4129
    assert H.wallclock(t) == "10:38:43.412"
    assert re.fullmatch(STAMP, H.wallclock())
    assert re.fullmatch(r"\d{8}-\d{6}", H.file_stamp())


def test_log_line_is_stamped_and_teed_to_a_per_run_file(appdata, capsys):
    path = NB.open_session_log()
    try:
        assert path is not None
        assert os.path.dirname(path) == str(appdata / "ff9mapkit" / "bridge-logs")
        assert re.fullmatch(r"bridge-\d{8}-\d{6}(-\d+)?\.log", os.path.basename(path))
        assert NB.session_log_path() == path
        NB.log("tee me please")
    finally:
        NB.close_session_log()
    out = capsys.readouterr().out
    assert re.search(r"^\[bridge\] %s tee me please$" % STAMP, out, re.M), out
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert re.search(r"^\[bridge\] %s tee me please$" % STAMP, text, re.M), text
    # closed -> later lines stay console-only
    NB.log("after close")
    with open(path, encoding="utf-8") as f:
        assert "after close" not in f.read()


def test_session_log_explicit_path_appends(tmp_path):
    target = tmp_path / "sub" / "my-bridge.log"
    target.parent.mkdir()
    target.write_text("earlier run\n", encoding="utf-8")
    assert NB.open_session_log(str(target)) == str(target)
    try:
        NB.log("second run")
    finally:
        NB.close_session_log()
    text = target.read_text(encoding="utf-8")
    assert text.startswith("earlier run\n") and "second run" in text


def test_two_runs_in_one_second_get_distinct_files(tmp_path):
    a = H.unique_path(str(tmp_path), "bridge-x", ".log")
    open(a, "w").close()
    b = H.unique_path(str(tmp_path), "bridge-x", ".log")
    assert a != b and b.endswith("bridge-x-2.log")


# --------------------------------------------------------------------------- the sentinel (pure, fake clock)

class _Clock:
    def __init__(self):
        self.t = 1000.0
        self.last = self.t

    def now(self):
        return self.t


def _sentinel(after_s=10.0, on_hang=None):
    clk = _Clock()
    lines = []
    s = H.HangSentinel(clk, after_s, lines.append, on_hang=on_hang, now=clk.now)
    return clk, s, lines


def _quiet_until(clk, s, t_end, step=1.0):
    while clk.t < t_end:
        clk.t = min(t_end, clk.t + step)
        s.on_quiet()


def test_sentinel_fires_once_at_the_threshold_and_stays_quiet_while_silent():
    hangs = []
    clk, s, lines = _sentinel(on_hang=hangs.append)
    _quiet_until(clk, s, 1009.0)
    assert lines == [] and hangs == []
    _quiet_until(clk, s, 1010.0)                       # exactly 10 s of silence -> trips (>=)
    assert len(lines) == 1 and "game hop SILENT 10.0 s" in lines[0]
    assert hangs == [10.0]
    _quiet_until(clk, s, 1060.0)                       # still silent: no second line, no second hook
    assert len(lines) == 1 and len(hangs) == 1 and s.trips == 1


def test_sentinel_rearms_only_after_resume():
    hangs = []
    clk, s, lines = _sentinel(on_hang=hangs.append)
    _quiet_until(clk, s, 1015.0)
    assert s.tripped and len(hangs) == 1
    clk.last = clk.t                                    # a frame arrives (the clock stamps first) ...
    s.on_frame()                                        # ... then the watch hears it
    assert not s.tripped
    assert lines[-1] == "game hop resumed after 15.0 s (frames flowing again)"
    _quiet_until(clk, s, clk.t + 9.0)
    assert len(hangs) == 1                              # 9 s after resume: not yet
    _quiet_until(clk, s, clk.t + 1.0)
    assert len(hangs) == 2 and s.trips == 2             # a NEW silence trips again


def test_sentinel_never_trips_on_a_30hz_peer():
    clk, s, lines = _sentinel()
    end = clk.t + 60.0
    n = 0
    while clk.t < end:
        clk.t += 1.0 / 30
        clk.last = clk.t
        s.on_frame()
        n += 1
        if n % 30 == 0:
            s.on_quiet()                                # a poll timeout now and then changes nothing
    assert lines == [] and s.trips == 0


def test_sentinel_rebaselines_when_the_bridge_itself_stalled():
    # system sleep: no tick for 60 s, then the bridge wakes before the game's next frame. That gap is
    # the bridge not running, not evidence about the game -- no fire, a re-baseline line instead.
    hangs = []
    clk, s, lines = _sentinel(on_hang=hangs.append)
    clk.t += 60.0
    s.on_quiet()
    assert hangs == [] and s.stalls == 1 and "stalled 60.0 s" in lines[-1]
    _quiet_until(clk, s, clk.t + 9.0)
    assert hangs == []                                  # silence counts from the re-baseline
    _quiet_until(clk, s, clk.t + 1.0)
    assert len(hangs) == 1


def test_sentinel_hook_error_is_logged_not_raised():
    def boom(_s):
        raise RuntimeError("hook blew up")
    clk, s, lines = _sentinel(on_hang=boom)
    _quiet_until(clk, s, 1010.0)                        # must not raise
    assert any("hang hook failed (ignored): hook blew up" in ln for ln in lines)


def test_sentinel_poll_bounds_the_line_latency():
    assert H.HangSentinel(_Clock(), 10.0, print).poll == 1.0
    assert H.HangSentinel(_Clock(), 0.8, print).poll == pytest.approx(0.2)


# --------------------------------------------------------------------------- the sentinel on a real socket

def _pump_in_thread(conn, stop):
    def run():
        try:
            while not stop.is_set():
                conn.read_frame()
        except Exception:                               # noqa: BLE001 -- _Closed at teardown
            pass
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def test_socketpair_silent_peer_trips_at_the_threshold():
    a, b = socket.socketpair()
    stop = threading.Event()
    lines = []
    fired = []
    clock = NB._FrameClock()
    sent = H.HangSentinel(clock, 0.6, lines.append, on_hang=lambda s: fired.append(time.monotonic()))
    conn = NB._FramedConn(b, NB._Activity(), stop, clock=clock, watch=sent)
    t0 = time.monotonic()
    a.sendall(_ws_frame(b"one frame, then nothing"))
    th = _pump_in_thread(conn, stop)
    try:
        assert _wait(lambda: fired, timeout=TIMEOUT), "a silent game hop never tripped the sentinel"
        assert 0.55 <= fired[0] - t0 < 3.0, "tripped at %.2fs, threshold 0.6s" % (fired[0] - t0)
        time.sleep(0.8)
        assert len(fired) == 1 and sum("SILENT" in ln for ln in lines) == 1
        assert clock.frames == 1
    finally:
        stop.set()
        a.close()
        b.close()
        th.join(timeout=TIMEOUT)


def test_socketpair_30hz_peer_never_trips():
    a, b = socket.socketpair()
    stop = threading.Event()
    lines = []
    clock = NB._FrameClock()
    sent = H.HangSentinel(clock, 1.0, lines.append)
    conn = NB._FramedConn(b, NB._Activity(), stop, clock=clock, watch=sent)
    th = _pump_in_thread(conn, stop)
    try:
        end = time.monotonic() + 2.5
        n = 0
        while time.monotonic() < end:
            a.sendall(_ws_frame(b"pos"))
            n += 1
            time.sleep(1.0 / 30)
        assert _wait(lambda: clock.frames == n)
        assert sent.trips == 0 and not any("SILENT" in ln for ln in lines), lines
    finally:
        stop.set()
        a.close()
        b.close()
        th.join(timeout=TIMEOUT)


def test_a_watch_that_raises_never_breaks_the_reader():
    a, b = socket.socketpair()
    try:
        bad = types.SimpleNamespace(poll=0.05, on_frame=lambda: 1 / 0, on_quiet=lambda: 1 / 0)
        conn = NB._FramedConn(b, NB._Activity(), threading.Event(), clock=NB._FrameClock(), watch=bad)
        f1, f2 = _ws_frame(b"x"), _ws_frame(b"y")
        a.sendall(f1)
        assert conn.read_frame() == f1
        threading.Timer(0.3, lambda: a.sendall(f2)).start()   # a few quiet polls first
        assert conn.read_frame() == f2
    finally:
        a.close()
        b.close()


# --------------------------------------------------------------------------- end to end through run_server

class _Relay:
    """One-connection loopback WS relay (server handshake via the bridge's own primitives); drains
    whatever the bridge forwards so the game->relay direction can never back up."""

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(TIMEOUT)
        self.sock.listen(1)
        self.url = "ws://127.0.0.1:%d" % self.sock.getsockname()[1]
        self.got = bytearray()
        self.conn = None
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    def _serve(self):
        try:
            conn, _ = self.sock.accept()
            conn.settimeout(TIMEOUT)
            req = NB.read_http_headers(conn)
            key = [ln.split(":", 1)[1].strip() for ln in req.split("\r\n")
                   if ln.lower().startswith("sec-websocket-key:")][0]
            conn.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                          "Sec-WebSocket-Accept: %s\r\n\r\n" % NB.ws_accept(key)).encode("ascii"))
            self.conn = conn
            conn.settimeout(0.2)
            while True:
                try:
                    chunk = conn.recv(65536)
                except socket.timeout:
                    continue
                if not chunk:
                    return
                self.got += chunk
        except OSError:
            return

    def close(self):
        for s in (self.conn, self.sock):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass


def _connect_game(port):
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    g = socket.create_connection(("127.0.0.1", port), timeout=TIMEOUT)
    g.sendall(("GET /s/HANG01?role=host HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\n"
               "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
               % key).encode("ascii"))
    assert " 101 " in NB.read_http_headers(g).split("\r\n", 1)[0]
    return g


def _send_for(game, seconds, hz=30):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        game.sendall(_ws_frame(b"pos-keepalive"))
        time.sleep(1.0 / hz)


def _fake_install(tmp_path):
    """A fake FF9 layout: <root>\\x64\\FF9.exe, its Unity output_log, and the root Memoria.log."""
    root = tmp_path / "FINAL FANTASY IX"
    (root / "x64" / "FF9_Data").mkdir(parents=True)
    (root / "x64" / "FF9_Data" / "output_log.txt").write_text("UnloadTime: 0.571200 ms\n", encoding="utf-8")
    (root / "Memoria.log").write_text("[NetSync] last line\n", encoding="utf-8")
    return str(root / "x64" / "FF9.exe")


class _Recorder:
    def __init__(self, image, exe="FF9.exe", fail=None):
        self.image, self.exe, self.fail = image, exe, fail
        self.resolves = []
        self.writes = []

    def resolver(self, cport, sport, game_exe):
        self.resolves.append((cport, sport, game_exe))
        if self.fail is not None:
            raise self.fail
        return H.GameProcess(4242, self.image, self.exe, "test seam")

    def writer(self, pid, path):
        self.writes.append((pid, path))
        with open(path, "wb") as f:
            f.write(b"MDMP fake dump")


def _bridge(relay, dumper):
    server, thread = NB.run_server("127.0.0.1", 0, relay.url, False, hang=dumper)
    return server, thread, server.getsockname()[1]


def test_enabled_hang_writes_one_dump_plus_logs_and_logs_resume(tmp_path, appdata):
    rec = _Recorder(_fake_install(tmp_path))
    lines = []
    dump_dir = tmp_path / "dumps"
    dumper = H.HangDumper(True, str(dump_dir), after_s=0.8, log=lines.append,
                          writer=rec.writer, resolver=rec.resolver, min_free=0)
    relay = _Relay()
    server, thread, port = _bridge(relay, dumper)
    game = None
    try:
        game = _connect_game(port)
        _send_for(game, 0.3)
        assert _wait(lambda: any("ARMED" in ln for ln in lines)), lines   # the connect-time probe
        assert _wait(lambda: dumper.dumps, timeout=TIMEOUT), lines         # silence -> one dump
        assert sum("SILENT" in ln for ln in lines) == 1
        assert len(rec.writes) == 1 and rec.writes[0][0] == 4242
        dmp = dumper.dumps[0]
        assert os.path.dirname(dmp) == str(dump_dir)
        assert re.fullmatch(r"FF9-\d{8}-\d{6}(-\d+)?\.dmp", os.path.basename(dmp))
        stem = dmp[:-4]
        with open(dmp, "rb") as f:
            assert f.read() == b"MDMP fake dump"
        with open(stem + ".output_log.txt", encoding="utf-8") as f:
            assert "UnloadTime" in f.read()
        with open(stem + ".Memoria.log", encoding="utf-8") as f:
            assert "[NetSync] last line" in f.read()
        assert not [p for p in os.listdir(dump_dir) if p.endswith(".partial")]
        # the resolver ran on the probe thread at connect; it is the game's ephemeral port -> our listen port
        assert rec.resolves[0][1] == port and rec.resolves[0][2] == "FF9.exe"

        # frames come back -> one resumed line; forwarding never stopped working
        before = len(relay.got)
        _send_for(game, 0.3)
        assert _wait(lambda: any("resumed after" in ln for ln in lines)), lines
        assert _wait(lambda: len(relay.got) > before)

        # a SECOND hang in the same bridge run: logged again, but the run's one dump is spent
        assert _wait(lambda: sum("SILENT" in ln for ln in lines) == 2, timeout=TIMEOUT), lines
        assert _wait(lambda: any("already took 1" in ln for ln in lines)), lines
        time.sleep(0.2)
        assert len(rec.writes) == 1 and len(dumper.dumps) == 1
    finally:
        if game is not None:
            game.close()
        server.close()
        thread.join(timeout=TIMEOUT)
        relay.close()
        for t in dumper.threads:
            t.join(timeout=TIMEOUT)


def test_disabled_never_resolves_copies_or_dumps(tmp_path, appdata):
    rec = _Recorder(_fake_install(tmp_path))
    lines = []
    dump_dir = tmp_path / "dumps"
    dumper = H.HangDumper(False, str(dump_dir), after_s=0.8, log=lines.append,
                          writer=rec.writer, resolver=rec.resolver, min_free=0)
    relay = _Relay()
    server, thread, port = _bridge(relay, dumper)
    game = None
    try:
        game = _connect_game(port)
        _send_for(game, 0.2)
        assert _wait(lambda: any("SILENT" in ln for ln in lines)), lines
        silent = [ln for ln in lines if "SILENT" in ln]
        assert len(silent) == 1 and "hang dumps OFF" in silent[0]
        time.sleep(0.5)
        assert rec.resolves == [] and rec.writes == [] and dumper.threads == []
        assert not dump_dir.exists()
    finally:
        if game is not None:
            game.close()
        server.close()
        thread.join(timeout=TIMEOUT)
        relay.close()


def test_pid_resolution_failure_is_logged_not_raised_and_forwarding_survives(tmp_path, appdata):
    rec = _Recorder(None, fail=LookupError("could not resolve the game pid (no TCP row; 0 running FF9.exe)"))
    lines = []
    dumper = H.HangDumper(True, str(tmp_path / "dumps"), after_s=0.8, log=lines.append,
                          writer=rec.writer, resolver=rec.resolver, min_free=0)
    relay = _Relay()
    server, thread, port = _bridge(relay, dumper)
    game = None
    try:
        game = _connect_game(port)
        _send_for(game, 0.2)
        assert _wait(lambda: any("not resolved yet" in ln for ln in lines)), lines     # the probe
        assert _wait(lambda: any("hang dump failed: could not resolve" in ln for ln in lines)), lines
        assert rec.writes == []
        before = len(relay.got)
        _send_for(game, 0.2)                                                           # still forwarding
        assert _wait(lambda: len(relay.got) > before)
    finally:
        if game is not None:
            game.close()
        server.close()
        thread.join(timeout=TIMEOUT)
        relay.close()
        for t in dumper.threads:
            t.join(timeout=TIMEOUT)


def _fire_direct(dumper, cport=50000, sport=49201):
    target = H.GameTarget(cport, sport)
    assert dumper.fire(target, 12.3) is True
    for t in dumper.threads:
        t.join(timeout=TIMEOUT)
    return target


def test_unexpected_resolver_error_is_logged(tmp_path):
    rec = _Recorder(None, fail=RuntimeError("iphlpapi exploded"))
    lines = []
    dumper = H.HangDumper(True, str(tmp_path), log=lines.append, writer=rec.writer, resolver=rec.resolver,
                          min_free=0)
    _fire_direct(dumper)
    assert lines == ["hang dump failed: iphlpapi exploded (the run's dump stays armed)"] and rec.writes == []


def test_not_the_game_is_never_dumped(tmp_path):
    rec = _Recorder(r"C:\Python\python.exe", exe="python.exe")
    lines = []
    dumper = H.HangDumper(True, str(tmp_path / "d"), log=lines.append, writer=rec.writer,
                          resolver=rec.resolver, min_free=0)
    _fire_direct(dumper)
    assert rec.writes == [] and "not FF9.exe" in lines[-1]
    assert not (tmp_path / "d").exists()


def test_a_hang_skipped_before_writing_never_spends_the_runs_one_dump(tmp_path):
    # Not the game, then an unresolvable pid, then a disk too full: none of them reached the writer, so the run's
    # ONE dump is still there for the real game's hang -- which spends it, and only then is the next hang refused.
    lines = []
    game = _Recorder(_fake_install(tmp_path))
    seams = {"resolver": _Recorder(r"C:\Python\python.exe", exe="python.exe").resolver}
    dumper = H.HangDumper(True, str(tmp_path / "d"), log=lines.append, writer=game.writer, min_free=0,
                          resolver=lambda *a: seams["resolver"](*a))
    _fire_direct(dumper)
    seams["resolver"] = _Recorder(None, fail=LookupError("could not resolve the game pid")).resolver
    _fire_direct(dumper)
    seams["resolver"] = game.resolver
    dumper.min_free = 1 << 62
    _fire_direct(dumper)
    assert game.writes == [] and sum("stays armed" in ln for ln in lines) == 3, lines
    dumper.min_free = 0
    _fire_direct(dumper)
    assert len(game.writes) == 1 and len(dumper.dumps) == 1
    assert dumper.fire(H.GameTarget(50000, 49201), 11.0) is False      # spent: restart the bridge to re-arm
    assert "already took 1" in lines[-1]


def test_a_failed_write_still_spends_the_runs_one_dump(tmp_path):
    rec = _Recorder(_fake_install(tmp_path))
    lines = []

    def bad_writer(pid, path):
        raise OSError(299, "MiniDumpWriteDump failed (error 0x8007012B)")

    dumper = H.HangDumper(True, str(tmp_path / "d"), log=lines.append, writer=bad_writer, resolver=rec.resolver,
                          min_free=0)
    _fire_direct(dumper)
    assert not any("stays armed" in ln for ln in lines), lines
    assert dumper.fire(H.GameTarget(50000, 49201), 11.0) is False      # the writer ran: the budget is gone


def test_writer_failure_is_logged_and_the_partial_removed(tmp_path):
    rec = _Recorder(_fake_install(tmp_path))
    lines = []
    calls = []

    def bad_writer(pid, path):
        calls.append(path)
        with open(path, "wb") as f:
            f.write(b"half a dump")
        raise OSError(299, "MiniDumpWriteDump failed (error 0x8007012B)")

    dumper = H.HangDumper(True, str(tmp_path / "d"), log=lines.append, writer=bad_writer,
                          resolver=rec.resolver, min_free=0)
    _fire_direct(dumper)
    assert len(calls) == 2 and any("retrying once" in ln for ln in lines), lines   # one retry, then give up
    assert any(ln.startswith("hang dump failed:") and "MiniDumpWriteDump" in ln for ln in lines), lines
    left = os.listdir(tmp_path / "d")
    assert not [p for p in left if p.endswith((".partial", ".dmp"))], left
    assert dumper.dumps == []


def test_low_disk_skips_the_dump_but_keeps_the_logs(tmp_path):
    rec = _Recorder(_fake_install(tmp_path))
    lines = []
    dumper = H.HangDumper(True, str(tmp_path / "d"), log=lines.append, writer=rec.writer,
                          resolver=rec.resolver, min_free=1 << 62)
    _fire_direct(dumper)
    assert rec.writes == [] and any("hang dump skipped: only" in ln for ln in lines), lines
    assert [p for p in os.listdir(tmp_path / "d") if p.endswith(".Memoria.log")]


def test_fire_is_inert_when_disabled(tmp_path):
    rec = _Recorder(None)
    dumper = H.HangDumper(False, str(tmp_path), writer=rec.writer, resolver=rec.resolver)
    assert dumper.fire(H.GameTarget(1, 2), 30.0) is False
    assert dumper.arm(1, 2).proc is None
    assert dumper.threads == [] and rec.resolves == []


# --------------------------------------------------------------------------- enablement (default OFF)

def test_enablement_default_off_flag_dir_env(tmp_path):
    env = {"LOCALAPPDATA": str(tmp_path)}
    off = H.HangDumper.from_options(environ=env)
    assert off.enabled is False and off.after_s == 10.0
    assert off.dump_dir == os.path.join(str(tmp_path), "ff9mapkit", "hangdumps")
    assert "hang dumps OFF" in off.describe()
    assert H.HangDumper.from_options(flag=True, environ=env).enabled
    on_dir = H.HangDumper.from_options(dump_dir=str(tmp_path / "x"), environ=env)
    assert on_dir.enabled and on_dir.dump_dir == str(tmp_path / "x")
    rel = H.HangDumper.from_options(dump_dir="dumps-here", environ=env)
    assert rel.dump_dir == os.path.abspath("dumps-here")         # pinned at parse time, named in full on the ON line
    for v in ("1", "true", "YES", "on"):
        assert H.HangDumper.from_options(environ=dict(env, FF9_HANG_DUMP=v)).enabled
    for v in ("", "0", "no", "off"):
        assert not H.HangDumper.from_options(environ=dict(env, FF9_HANG_DUMP=v)).enabled
    assert H.HangDumper.from_options(after_s=12, environ=env).after_s == 12.0
    for bad in (0, 0.5, -3, float("nan")):
        with pytest.raises(ValueError):
            H.HangDumper.from_options(after_s=bad, environ=env)


def test_run_server_default_reads_the_env(appdata, monkeypatch):
    seen = {}
    real = H.HangDumper.from_options

    def spy(*a, **k):
        d = real(*a, **k)
        seen["d"] = d
        return d
    monkeypatch.setattr(H.HangDumper, "from_options", spy)
    server, thread = NB.run_server("127.0.0.1", 0, "ws://127.0.0.1:9", False)
    server.close()
    thread.join(timeout=TIMEOUT)
    assert seen["d"].enabled is False                     # PyPI default: no dumps unasked
    monkeypatch.setenv("FF9_HANG_DUMP", "1")
    server, thread = NB.run_server("127.0.0.1", 0, "ws://127.0.0.1:9", False)
    server.close()
    thread.join(timeout=TIMEOUT)
    assert seen["d"].enabled is True


def test_coop_cli_flags_reach_the_bridge(appdata, monkeypatch):
    from ff9mapkit import coop
    from ff9mapkit.cli import build_parser

    got = {}

    def fake_run_server(host, port, relay, insecure, hang=None):
        got["hang"] = hang
        got["tee"] = NB.session_log_path()
        dead = threading.Thread(target=lambda: None)
        dead.start()
        dead.join()
        return socket.socket(), dead

    monkeypatch.setattr(NB, "run_server", fake_run_server)
    args = build_parser().parse_args(["coop", "bridge", "--hang-dump", "--hang-after", "15"])
    out = []
    assert coop.run(args, out=out.append) == 0
    assert got["hang"].enabled and got["hang"].after_s == 15.0
    assert got["hang"].dump_dir == os.path.join(str(appdata), "ff9mapkit", "hangdumps")
    assert got["tee"] and got["tee"].startswith(os.path.join(str(appdata), "ff9mapkit", "bridge-logs"))
    assert NB.session_log_path() is None                  # closed when the bridge returns
    assert any("hang dumps ON" in ln for ln in out) and any("bridge log:" in ln for ln in out)

    args = build_parser().parse_args(["coop", "join", "ff9-ABCDEFGH", "--hang-dump"])
    assert args.code == "ff9-ABCDEFGH" and args.hang_dump      # the switch never eats the code
    args = build_parser().parse_args(["coop", "bridge"])
    assert coop.run(args, out=out.append) == 0
    assert got["hang"].enabled is False


def test_no_bridge_hint_carries_every_bridge_flag():
    """`coop host --no-bridge` prints the later `coop bridge` command: it must keep the relay, the dump arming and
    the log file the user gave, or the bridge started from it silently runs without them."""
    import shlex
    from ff9mapkit import coop
    from ff9mapkit.cli import build_parser

    given = ["coop", "host", "--no-bridge", "--relay", "ws://127.0.0.1:7777", "--hang-dump-dir", r"C:\My Dumps",
             "--hang-after", "15", "--bridge-log", "b.log", "--insecure"]
    hint = coop._bridge_flags_text(build_parser().parse_args(given))
    again = build_parser().parse_args(["coop", "bridge"] + shlex.split(hint))
    assert (again.relay, again.hang_dump_dir, again.hang_after, again.bridge_log, again.insecure) == (
        "ws://127.0.0.1:7777", r"C:\My Dumps", 15.0, "b.log", True)
    assert coop._bridge_flags_text(build_parser().parse_args(["coop", "host", "--hang-dump"])) == " --hang-dump"
    assert coop._bridge_flags_text(build_parser().parse_args(["coop", "host"])) == ""


# --------------------------------------------------------------------------- resolution logic (pure seams)

ROWS = [
    # state, local ip, local port, remote ip, remote port, pid
    (5, "127.0.0.1", 49201, "127.0.0.1", 50123, 111),     # the bridge's accepted end
    (5, "127.0.0.1", 50123, "127.0.0.1", 49201, 777),     # the GAME's end -- the one we want
    (5, "10.0.0.5", 50123, "1.2.3.4", 443, 999),          # same port number, unrelated connection
]
# The game's image as THIS OS spells it (C:\G\x64\FF9.exe on Windows, QueryFullProcessImageNameW's form): the resolver
# takes its basename with os.path, so a backslashed literal would be one whole path component on POSIX.
IMAGE = os.path.join(os.path.abspath(os.sep), "G", "x64", "FF9.exe")


def test_resolve_by_loopback_port_owner():
    p = H.resolve_game_process(50123, 49201, rows=ROWS, procs=[(777, "FF9.exe")],
                               image_of=lambda pid: IMAGE)
    assert (p.pid, p.image, p.exe) == (777, IMAGE, "FF9.exe")
    assert "loopback port 50123" in p.how


def test_resolve_falls_back_to_the_single_running_game():
    p = H.resolve_game_process(50999, 49201, rows=ROWS, procs=[(5, "explorer.exe"), (888, "ff9.EXE")],
                               image_of=lambda pid: IMAGE)
    assert p.pid == 888 and "only running FF9.exe" in p.how


def test_resolve_failure_names_every_reason():
    with pytest.raises(LookupError) as ei:
        H.resolve_game_process(50999, 49201, rows=ROWS, procs=[(1, "FF9.exe"), (2, "FF9.exe")],
                               image_of=lambda pid: "x")
    msg = str(ei.value)
    assert "no TCP row owns 127.0.0.1:50999 -> :49201" in msg and "2 running FF9.exe" in msg


def test_resolve_keeps_the_pid_when_the_image_path_is_unreadable():
    def denied(pid):
        raise PermissionError(5, "Access is denied")
    p = H.resolve_game_process(50123, 49201, rows=ROWS, procs=[(777, "FF9.exe")], image_of=denied)
    assert p.pid == 777 and p.image is None and p.exe == "FF9.exe"


def test_game_log_sources_prefer_the_newest_candidate(tmp_path):
    image = _fake_install(tmp_path)
    root = os.path.dirname(os.path.dirname(image))
    stale = os.path.join(root, "x64", "Memoria.log")
    with open(stale, "w") as f:
        f.write("stale")
    os.utime(stale, (1, 1))
    out_log, mem_log = H.game_log_sources(image)
    assert out_log == os.path.join(root, "x64", "FF9_Data", "output_log.txt")
    assert mem_log == os.path.join(root, "Memoria.log")
    assert H.game_log_sources(str(tmp_path / "nowhere" / "FF9.exe")) == (None, None)


def test_non_windows_is_reported_not_crashed(monkeypatch):
    monkeypatch.setattr(H, "_WIN", None)
    monkeypatch.setattr(H, "os", types.SimpleNamespace(name="posix", path=os.path))
    with pytest.raises(H.HangDumpUnsupported):
        H.tcp4_owner_rows()
    with pytest.raises(LookupError) as ei:
        H.resolve_game_process(1, 2, image_of=lambda pid: None)
    assert "need Windows" in str(ei.value)


# --------------------------------------------------------------------------- Windows calibration (real APIs)

win_only = pytest.mark.skipif(os.name != "nt", reason="iphlpapi / toolhelp / dbghelp are Windows APIs")


@win_only
def test_real_tcp_table_names_the_owner_of_a_loopback_client():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    cli = socket.create_connection(srv.getsockname(), timeout=TIMEOUT)
    acc, _ = srv.accept()
    try:
        assert H.pid_for_loopback_client(cli.getsockname()[1], srv.getsockname()[1]) == os.getpid()
        p = H.resolve_game_process(cli.getsockname()[1], srv.getsockname()[1])
        assert p.pid == os.getpid() and p.exe.lower().endswith(".exe") and os.path.isfile(p.image)
    finally:
        for s in (cli, acc, srv):
            s.close()


@win_only
def test_real_process_snapshot_and_image_path():
    me = os.getpid()
    names = dict(H.list_processes())
    assert me in names and names[me].lower().endswith(".exe")
    assert me in H.find_processes(names[me].upper())
    assert os.path.basename(H.process_image_path(me)).lower() == names[me].lower()


@win_only
def test_real_minidump_of_a_child_process(tmp_path):
    # The child must be fully started first: dbghelp fails a process still in loader init with
    # ERROR_BAD_LENGTH (0x80070018) -- a race the real target (a game running for minutes) never has.
    child = subprocess.Popen([sys.executable, "-c", "import sys, time; print('ready', flush=True); time.sleep(60)"],
                             stdout=subprocess.PIPE)
    try:
        assert child.stdout.readline().strip() == b"ready"
        out = tmp_path / "child.dmp"
        H.write_minidump(child.pid, str(out), H.MiniDumpNormal)     # small: proves the dbghelp plumbing
        with open(out, "rb") as f:
            assert f.read(4) == b"MDMP"
        assert H.FULL_DUMP_FLAGS == 0x1026                          # FullMemory|HandleData|ThreadInfo|Unloaded
    finally:
        child.kill()
        child.wait(timeout=TIMEOUT)
        child.stdout.close()
