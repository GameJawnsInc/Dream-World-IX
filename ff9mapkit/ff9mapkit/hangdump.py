"""Hang sentinel + auto-dump for the co-op bridge (battle co-op R3, tooling T1).

Why this exists: sitting A's host FF9.exe froze WHOLE inside a Unity scene-load asset GC -- the main
thread and both NetSync socket threads stopped together -- and Windows closed the hung window five
minutes later with no dump anywhere. Nothing short of a full-memory dump of the frozen process can
name the thread that held the lock (studies/battle-coop/R3-SITTING-A-FIXES.md, "The host freeze").

The signal: the engine's relay WriteLoop runs on its OWN thread and sends at least ~30 frames/s,
even in menus and scene loads. So when the game->bridge hop of an open game connection carries no
frame for ``HANG_AFTER_S`` (10 s), the FF9 process has stopped -- hung or suspended -- not gone
quiet. :class:`HangSentinel` turns that silence into one log line (and a 'resumed after N s' line if
frames come back); :class:`HangDumper` -- only when hang dumps are ENABLED -- writes ONE full
minidump of the game per bridge run plus copies of its ``output_log.txt`` and ``Memoria.log``.

Default OFF: a full dump of FF9 is 1-3 GB, and public PyPI users must never get one unasked. Enable
with ``--hang-dump`` (``ff9mapkit coop bridge|host|join``) or the env ``FF9_HANG_DUMP=1``.

Everything Windows-specific (iphlpapi, toolhelp, dbghelp via ctypes) is resolved lazily inside the
functions that need it, so importing this module is safe on any OS; on a non-Windows host those
functions raise :class:`HangDumpUnsupported`, which the callers log. Nothing here may block or raise
into the bridge's forwarding loop: the sentinel's hooks are O(1) and the PID resolution + dump run
on worker threads that log every failure.

Reading the dump (WinDbg): ``~*kb`` and ``!locks`` with the MS symbol server (+ Unity's, if it has
5.2.3p2); look for the main thread under GarbageCollectSharedAssets / mono GC_stop_world and which
suspended thread owns what it waits on (NetSync-relay(-write), the SaXAudio/XAudio2 callback, the
FileSystemWatcher thread, or Unity-internal).
"""

from __future__ import annotations

import ctypes
import os
import shutil
import socket
import struct
import threading
import time
from collections import namedtuple

HANG_AFTER_S = 10.0                 # game-hop silence that means "the FF9 process stopped sending"
MIN_HANG_AFTER_S = 1.0              # CLI floor: under ~1 s a GC pause or a loaded machine is noise
GAME_EXE = "FF9.exe"                # the only image a hang dump is ever taken of
ENV_ENABLE = "FF9_HANG_DUMP"        # FF9_HANG_DUMP=1 arms dumps without the CLI flag
MIN_FREE_BYTES = 4 << 30            # a full FF9 dump runs 1-3 GB: refuse below 4 GiB free

# dbghelp MINIDUMP_TYPE bits (minidumpapiset.h)
MiniDumpNormal = 0x00000000
MiniDumpWithFullMemory = 0x00000002
MiniDumpWithHandleData = 0x00000004
MiniDumpWithUnloadedModules = 0x00000020
MiniDumpWithThreadInfo = 0x00001000
FULL_DUMP_FLAGS = (MiniDumpWithFullMemory | MiniDumpWithHandleData
                   | MiniDumpWithThreadInfo | MiniDumpWithUnloadedModules)


class HangDumpUnsupported(OSError):
    """The Windows APIs this needs (iphlpapi / toolhelp / dbghelp) are not available here."""


GameProcess = namedtuple("GameProcess", "pid image exe how")
"""A resolved game process: pid, full image path (or None), image basename, and how it was found."""


# --------------------------------------------------------------------------- clocks + paths


def wallclock(t=None):
    """Local wall-clock time with milliseconds, 'HH:MM:SS.mmm' (the bridge log's line stamp)."""
    t = time.time() if t is None else t
    return time.strftime("%H:%M:%S", time.localtime(t)) + ".%03d" % (int(t * 1000) % 1000)


def file_stamp(t=None):
    """'YYYYmmdd-HHMMSS' local time, for per-session file names."""
    return time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time() if t is None else t))


def data_root(environ=None):
    """%LOCALAPPDATA%\\ff9mapkit (the per-user, never-roamed home of bridge logs + hang dumps). Tests
    pin it by setting LOCALAPPDATA; off Windows it falls back to $XDG_STATE_HOME / ~/.local/state."""
    env = os.environ if environ is None else environ
    base = env.get("LOCALAPPDATA")
    if not base:
        if os.name == "nt":
            base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
        else:
            base = env.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "ff9mapkit")


def default_dump_dir(environ=None):
    return os.path.join(data_root(environ), "hangdumps")


def default_log_dir(environ=None):
    return os.path.join(data_root(environ), "bridge-logs")


def unique_path(directory, stem, ext):
    """directory/stem+ext, or stem-2/-3/... if that name is taken (two runs inside one second)."""
    path = os.path.join(directory, stem + ext)
    n = 2
    while os.path.exists(path):
        path = os.path.join(directory, "%s-%d%s" % (stem, n, ext))
        n += 1
    return path


def env_enabled(environ=None):
    """True when FF9_HANG_DUMP is set to 1/true/yes/on (case-insensitive)."""
    env = os.environ if environ is None else environ
    return str(env.get(ENV_ENABLE, "")).strip().lower() in ("1", "true", "yes", "on")


# --------------------------------------------------------------------------- Windows APIs (lazy)

_WIN = None
_WIN_LOCK = threading.Lock()

_AF_INET = 2
_TCP_TABLE_OWNER_PID_CONNECTIONS = 4
_ERROR_INSUFFICIENT_BUFFER = 122
_ERROR_PARTIAL_COPY = 299
_TH32CS_SNAPPROCESS = 0x00000002
_PROCESS_QUERY_INFORMATION = 0x0400
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_PROCESS_VM_READ = 0x0010
_PROCESS_DUP_HANDLE = 0x0040
_MAX_PATH = 260


def _win():
    """Bind the handful of Win32 entry points once (argtypes/restype set -- HANDLEs are pointer-sized
    on x64, so the default int restype would truncate them). Raises HangDumpUnsupported off Windows."""
    global _WIN
    if _WIN is not None:
        return _WIN
    if os.name != "nt":
        raise HangDumpUnsupported("hang dumps need Windows (iphlpapi / toolhelp / dbghelp)")
    with _WIN_LOCK:
        if _WIN is not None:
            return _WIN
        from ctypes import wintypes as W

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD), ("th32ProcessID", W.DWORD),
                        ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", W.DWORD),
                        ("cntThreads", W.DWORD), ("th32ParentProcessID", W.DWORD),
                        ("pcPriClassBase", W.LONG), ("dwFlags", W.DWORD),
                        ("szExeFile", W.WCHAR * _MAX_PATH)]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        iph = ctypes.WinDLL("iphlpapi", use_last_error=True)
        k32.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        k32.OpenProcess.restype = W.HANDLE
        k32.CloseHandle.argtypes = [W.HANDLE]
        k32.CloseHandle.restype = W.BOOL
        k32.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, ctypes.POINTER(W.DWORD)]
        k32.QueryFullProcessImageNameW.restype = W.BOOL
        k32.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
        k32.CreateToolhelp32Snapshot.restype = W.HANDLE
        k32.Process32FirstW.argtypes = [W.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        k32.Process32FirstW.restype = W.BOOL
        k32.Process32NextW.argtypes = [W.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        k32.Process32NextW.restype = W.BOOL
        iph.GetExtendedTcpTable.argtypes = [ctypes.c_void_p, ctypes.POINTER(W.DWORD), W.BOOL,
                                            W.ULONG, ctypes.c_int, W.ULONG]
        iph.GetExtendedTcpTable.restype = W.DWORD
        ns = type("Win32", (), {})()
        ns.W = W
        ns.k32 = k32
        ns.iph = iph
        ns.PROCESSENTRY32W = PROCESSENTRY32W
        ns.dbghelp = None                         # bound on first dump (dbghelp loads only if needed)
        _WIN = ns                                 # published only once complete (lock-free readers)
        return _WIN


def _invalid_handle(h):
    return h is None or h == 0 or h == ctypes.c_void_p(-1).value


def tcp4_owner_rows():
    """Every IPv4 TCP connection with its owning PID, via iphlpapi GetExtendedTcpTable
    (TCP_TABLE_OWNER_PID_CONNECTIONS). Rows are (state, local_ip, local_port, remote_ip, remote_port, pid)
    with ports in host order."""
    w = _win()
    size = w.W.DWORD(0)
    rc = w.iph.GetExtendedTcpTable(None, ctypes.byref(size), False, _AF_INET,
                                   _TCP_TABLE_OWNER_PID_CONNECTIONS, 0)
    for _attempt in range(5):
        if rc not in (0, _ERROR_INSUFFICIENT_BUFFER):
            raise OSError(rc, "GetExtendedTcpTable failed (error %d)" % rc)
        buf = ctypes.create_string_buffer(max(size.value, 4) + 4096)   # slack: the table can grow
        size = w.W.DWORD(len(buf))
        rc = w.iph.GetExtendedTcpTable(buf, ctypes.byref(size), False, _AF_INET,
                                       _TCP_TABLE_OWNER_PID_CONNECTIONS, 0)
        if rc == 0:
            raw = buf.raw
            count = struct.unpack_from("<I", raw, 0)[0]
            rows = []
            for i in range(count):
                state, laddr, lport, raddr, rport, pid = struct.unpack_from("<6I", raw, 4 + 24 * i)
                # addresses are network-order DWORDs; ports live in the LOW 16 bits, network order
                rows.append((state,
                             socket.inet_ntoa(struct.pack("<I", laddr)), socket.ntohs(lport & 0xFFFF),
                             socket.inet_ntoa(struct.pack("<I", raddr)), socket.ntohs(rport & 0xFFFF),
                             pid))
            return rows
    raise OSError(rc, "GetExtendedTcpTable kept outgrowing its buffer")


def pid_for_loopback_client(client_port, server_port, rows=None):
    """The PID that owns the CLIENT end of a loopback connection to us: the row whose local port is the
    client's ephemeral port and whose remote port is our listen port. None when no (single) row matches."""
    rows = tcp4_owner_rows() if rows is None else rows
    pids = {r[5] for r in rows if r[2] == client_port and r[4] == server_port and r[5]}
    return pids.pop() if len(pids) == 1 else None


def list_processes():
    """[(pid, exe_basename)] for every running process (toolhelp snapshot)."""
    w = _win()
    snap = w.k32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if _invalid_handle(snap):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = w.PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        out = []
        ok = w.k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            out.append((int(entry.th32ProcessID), entry.szExeFile))
            ok = w.k32.Process32NextW(snap, ctypes.byref(entry))
        return out
    finally:
        w.k32.CloseHandle(snap)


def find_processes(exe, procs=None):
    """PIDs whose image basename is `exe` (case-insensitive)."""
    procs = list_processes() if procs is None else procs
    want = exe.lower()
    return [pid for pid, name in procs if name.lower() == want]


def process_image_path(pid):
    """Full image path of `pid` (QueryFullProcessImageNameW). Raises OSError when it cannot be read."""
    w = _win()
    h = w.k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if _invalid_handle(h):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        buf = ctypes.create_unicode_buffer(32768)
        n = w.W.DWORD(len(buf))
        if not w.k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buf.value
    finally:
        w.k32.CloseHandle(h)


def resolve_game_process(client_port, server_port, game_exe=GAME_EXE, *, rows=None, procs=None,
                         image_of=None):
    """Find the game behind a loopback client socket. First the owner of the client's ephemeral port
    (exact: it IS the process on the other end of this connection), then -- if that fails -- the single
    running `game_exe`. Returns a GameProcess; raises LookupError naming every reason it failed.
    `rows`/`procs`/`image_of` are test seams (the TCP table, the process list, the image lookup)."""
    image_of = process_image_path if image_of is None else image_of
    reasons = []

    def _image(pid):
        try:
            return image_of(pid)
        except Exception as err:          # noqa: BLE001 -- a missing image path is reported, not fatal
            reasons.append("image path of pid %d: %s" % (pid, err))
            return None

    def _names():
        return list_processes() if procs is None else procs

    try:
        pid = pid_for_loopback_client(client_port, server_port, rows)
        if pid:
            image = _image(pid)
            exe = os.path.basename(image) if image else dict(_names()).get(pid, "")
            return GameProcess(pid, image, exe, "owner of loopback port %d" % client_port)
        reasons.append("no TCP row owns 127.0.0.1:%d -> :%d" % (client_port, server_port))
    except Exception as err:              # noqa: BLE001
        reasons.append("TCP table: %s" % err)
    try:
        pids = find_processes(game_exe, _names())
        if len(pids) == 1:
            image = _image(pids[0])
            return GameProcess(pids[0], image, game_exe, "the only running %s" % game_exe)
        reasons.append("%d running %s" % (len(pids), game_exe))
    except Exception as err:              # noqa: BLE001
        reasons.append("process scan: %s" % err)
    raise LookupError("could not resolve the game pid (%s)" % "; ".join(reasons))


def write_minidump(pid, path, flags=FULL_DUMP_FLAGS):
    """Write a minidump of `pid` to `path` via dbghelp MiniDumpWriteDump (default: full memory + handle
    data + thread info + unloaded modules). Blocks for as long as the dump takes -- call it on a worker
    thread. Raises OSError on failure (the caller removes the partial file)."""
    w = _win()
    W = w.W
    if w.dbghelp is None:
        dbg = ctypes.WinDLL("dbghelp", use_last_error=True)
        dbg.MiniDumpWriteDump.argtypes = [W.HANDLE, W.DWORD, W.HANDLE, W.DWORD,
                                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        dbg.MiniDumpWriteDump.restype = W.BOOL
        w.dbghelp = dbg
    import msvcrt   # Windows-only module: imported here, never at module import time

    access = _PROCESS_QUERY_INFORMATION | _PROCESS_VM_READ | _PROCESS_DUP_HANDLE
    h = w.k32.OpenProcess(access, False, pid)
    if _invalid_handle(h):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        with open(path, "wb") as f:
            fh = msvcrt.get_osfhandle(f.fileno())
            if not w.dbghelp.MiniDumpWriteDump(h, pid, fh, flags, None, None, None):
                err = ctypes.get_last_error()
                hint = ""
                if (err & 0xFFFF) == _ERROR_PARTIAL_COPY and struct.calcsize("P") == 4:
                    hint = " -- a 32-bit Python cannot dump the 64-bit game; run the bridge on 64-bit Python"
                raise OSError(err, "MiniDumpWriteDump failed (error 0x%08X)%s" % (err & 0xFFFFFFFF, hint))
    finally:
        w.k32.CloseHandle(h)


def game_log_sources(image):
    """(output_log.txt, Memoria.log) paths for the game whose image is `image` -- the newest existing
    candidate of each, or None. FF9.exe lives in <install>\\x64 (or x86); Unity writes
    <exe dir>\\FF9_Data\\output_log.txt and Memoria writes <install>\\Memoria.log (a stale copy can sit
    beside the exe, so the newest by mtime wins)."""
    exe_dir = os.path.dirname(image)
    root = os.path.dirname(exe_dir) if os.path.basename(exe_dir).lower() in ("x64", "x86") else exe_dir

    def newest(cands):
        seen, best, best_m = set(), None, None
        for c in cands:
            key = os.path.normcase(os.path.abspath(c))
            if key in seen:
                continue
            seen.add(key)
            try:
                m = os.path.getmtime(c)
            except OSError:
                continue
            if best is None or m > best_m:
                best, best_m = c, m
        return best

    out_log = newest([os.path.join(exe_dir, "FF9_Data", "output_log.txt"),
                      os.path.join(root, "x64", "FF9_Data", "output_log.txt"),
                      os.path.join(root, "x86", "FF9_Data", "output_log.txt")])
    mem_log = newest([os.path.join(root, "Memoria.log"), os.path.join(exe_dir, "Memoria.log")])
    return out_log, mem_log


# --------------------------------------------------------------------------- the sentinel


class HangSentinel:
    """Watches ONE direction's last-frame clock (anything with a monotonic ``.last``) and turns a silence
    of ``after_s`` into exactly one 'SILENT' line, then -- via ``on_hang(silent_s)`` -- whatever the
    dump policy says. It re-arms only after frames RESUME (logging 'resumed after N s'), so a hang is
    reported once, never once per poll.

    Driven by the forwarding loop: ``on_frame()`` after every whole frame, ``on_quiet()`` on every recv
    poll timeout (``poll`` seconds, so the line lands within ~poll of the threshold). Both are O(1).

    Self-calibration: the silence it measures is only evidence about the game if the BRIDGE kept running.
    A gap between two of its own ticks much longer than its poll means the bridge itself did not run
    (system sleep, a debugger, a starved machine) -- the clock is re-baselined instead of firing, so a
    laptop resuming from sleep cannot trigger a multi-GB dump."""

    def __init__(self, clock, after_s=HANG_AFTER_S, log=print, on_hang=None, hint="",
                 now=time.monotonic, label="game hop"):
        self.clock = clock
        self.after_s = float(after_s)
        self.log = log
        self.on_hang = on_hang
        self.hint = hint
        self.label = label
        self._now = now
        self.poll = max(0.05, min(1.0, self.after_s / 4.0))
        self.stall_s = max(5.0, 4.0 * self.poll)
        self.tripped = False
        self.trips = 0
        self.resumes = 0
        self.stalls = 0
        self._since = None
        t = now()
        self._last_tick = t
        self._baseline = t

    def on_frame(self):
        now = self._now()
        self._last_tick = now
        if self.tripped:
            self.tripped = False
            self.resumes += 1
            self.log("%s resumed after %.1f s (frames flowing again)" % (self.label, now - self._since))

    def on_quiet(self):
        now = self._now()
        gap = now - self._last_tick
        self._last_tick = now
        if gap >= self.stall_s:
            # the bridge itself was not scheduled for `gap` -- what it measured is not the game's silence
            self._baseline = now
            self.stalls += 1
            if not self.tripped:
                self.log("%s: the bridge itself stalled %.1f s (system sleep / debugger / load?) -- "
                         "hang clock re-baselined, not judging the game on it" % (self.label, gap))
            return
        if self.tripped:
            return
        since = max(self.clock.last, self._baseline)
        silent = now - since
        if silent < self.after_s:
            return
        self.tripped = True
        self.trips += 1
        self._since = since
        self.log("%s SILENT %.1f s: no game->bridge frame since %s -- the FF9 process stopped sending "
                 "(hung or suspended)%s" % (self.label, silent, wallclock(time.time() - silent), self.hint))
        if self.on_hang is not None:
            try:
                self.on_hang(silent)
            except Exception as err:      # noqa: BLE001 -- the instrument never breaks forwarding
                self.log("hang hook failed (ignored): %s" % err)


# --------------------------------------------------------------------------- the dump policy


class GameTarget:
    """One game connection's identity for the dumper: its loopback ports, and the process once resolved
    (filled by the arm-time probe thread; re-resolved by the dump worker if still missing)."""

    __slots__ = ("client_port", "server_port", "proc")

    def __init__(self, client_port, server_port):
        self.client_port = client_port
        self.server_port = server_port
        self.proc = None


class HangDumper:
    """One bridge run's hang-dump policy (create one per run; ``run_server`` holds it).

    Disabled (the default): the sentinel still logs the SILENT/resumed lines; nothing is resolved,
    copied or dumped. Enabled: each game connection is probed at connect time (its PID + image are
    logged -- calibrating the instrument before it is needed), and the first hang of the run writes
    ``FF9-<ts>.dmp`` + ``FF9-<ts>.output_log.txt`` + ``FF9-<ts>.Memoria.log`` into ``dump_dir``.
    ``max_dumps`` (1) bounds the run: restart the bridge to re-arm. Only a dump the writer ATTEMPTED spends it -- a
    hang skipped before writing (pid unresolved, not the game, disk too full) leaves the run armed.

    Every Windows call runs on a daemon worker thread and every failure is LOGGED, never raised.
    ``writer``/``resolver`` are seams for tests (signatures of write_minidump / resolve_game_process).

    ``pid`` (``--hang-pid``) names the game outright and skips the resolution: with two FF9s on one machine
    (tools/harness/duo.py) "the only running FF9.exe" fallback has no answer, and a driver that launched the game
    already knows which one this bridge serves. ``image_of`` is that path's seam (process_image_path)."""

    def __init__(self, enabled=False, dump_dir=None, *, after_s=HANG_AFTER_S, max_dumps=1,
                 game_exe=GAME_EXE, log=None, writer=None, resolver=None, min_free=MIN_FREE_BYTES,
                 pid=None, image_of=None):
        self.enabled = bool(enabled)
        self.dump_dir = dump_dir or default_dump_dir()
        self.after_s = float(after_s)
        self.max_dumps = int(max_dumps)
        self.game_exe = game_exe
        self.log_fn = log
        self.writer = writer or write_minidump
        self.resolver = resolver or resolve_game_process
        self.min_free = min_free
        self.pid = int(pid) if pid else None
        self.image_of = image_of or process_image_path
        self.dumps = []                     # paths of dumps written this run
        self.threads = []                   # worker threads (tests join them)
        self._lock = threading.Lock()
        self._claimed = 0

    @classmethod
    def from_options(cls, flag=False, dump_dir=None, after_s=None, *, environ=None, log=None, pid=None):
        """The CLI's view: dumps are ON when --hang-dump, --hang-dump-dir, or FF9_HANG_DUMP=1 says so.
        Raises ValueError for an --hang-after under MIN_HANG_AFTER_S, or a --hang-pid that is not a positive pid."""
        if pid is not None and not int(pid) > 0:
            raise ValueError("--hang-pid must be a positive process id, got %r" % (pid,))
        after = HANG_AFTER_S if after_s is None else float(after_s)
        if not after >= MIN_HANG_AFTER_S:
            raise ValueError("--hang-after must be at least %.0f second(s), got %r" % (MIN_HANG_AFTER_S, after_s))
        enabled = bool(flag) or bool(dump_dir) or env_enabled(environ)
        # absolute now: the ON line names the real folder, and a later cwd change cannot move the dump
        return cls(enabled, os.path.abspath(dump_dir) if dump_dir else default_dump_dir(environ), after_s=after,
                   log=log, pid=pid)

    # -- logging -------------------------------------------------------------------------------

    def log(self, msg):
        fn = self.log_fn
        try:
            (print if fn is None else fn)(msg)
        except Exception:                   # noqa: BLE001 -- a broken console must not kill a worker
            pass

    def describe(self):
        if self.enabled:
            return ("hang sentinel: game hop silent >= %.0f s is logged; hang dumps ON -> %s "
                    "(one full dump of %s per bridge run, 1-3 GB)%s" % (
                        self.after_s, self.dump_dir, self.game_exe,
                        "; the game is pid %d (--hang-pid)" % self.pid if self.pid else ""))
        return ("hang sentinel: game hop silent >= %.0f s is logged; hang dumps OFF "
                "(--hang-dump or %s=1 to capture one)" % (self.after_s, ENV_ENABLE))

    # -- per connection ------------------------------------------------------------------------

    def arm(self, client_port, server_port):
        """Called once per game connection. Returns its GameTarget; when enabled, probes the PID in the
        background so the log shows -- before any hang -- whether a dump COULD be taken."""
        target = GameTarget(client_port, server_port)
        if self.enabled:
            self._spawn(self._probe, target, name="ff9-hangdump-probe")
        return target

    def sentinel(self, clock, target=None, *, now=time.monotonic):
        """A HangSentinel on `clock` whose hang hook is this policy."""
        hint = "" if self.enabled else " [hang dumps OFF: --hang-dump or %s=1 captures one]" % ENV_ENABLE
        return HangSentinel(clock, self.after_s, self.log, on_hang=lambda s: self.fire(target, s),
                            hint=hint, now=now)

    def fire(self, target, silent_s):
        """The sentinel tripped. Disabled -> nothing (its line already says so). Enabled -> claim this
        run's dump budget and start the worker; never blocks the caller."""
        if not self.enabled:
            return False
        with self._lock:
            if self._claimed >= self.max_dumps:
                claimed = False
            else:
                self._claimed += 1
                claimed = True
        if not claimed:
            self.log("hang dump skipped: this bridge run already took %d (restart the bridge to re-arm)"
                     % self.max_dumps)
            return False
        self._spawn(self._dump, target, silent_s, name="ff9-hangdump")
        return True

    # -- workers -------------------------------------------------------------------------------

    def _spawn(self, fn, *args, name):
        try:
            t = threading.Thread(target=fn, args=args, name=name, daemon=True)
            t.start()
            with self._lock:                # finished workers are dropped: one probe per game connection must
                self.threads = [x for x in self.threads if x.is_alive()] + [t]    # not grow a long run's list
        except Exception as err:            # noqa: BLE001
            self.log("hang dump: could not start a worker thread: %s" % err)

    def _release(self):
        """Give back a claim the writer never spent. Only a dump the writer ATTEMPTED uses up the run's budget: an
        unresolved pid, a client that is not the game, or a full disk leaves the run armed for the next hang."""
        with self._lock:
            if self._claimed > 0:
                self._claimed -= 1

    def _resolve(self, target):
        if target is None:
            raise LookupError("no game connection to resolve")
        proc = target.proc
        if proc is None and self.pid:
            try:
                image = self.image_of(self.pid)
            except Exception as err:      # noqa: BLE001 -- reported in `how`; the dump still names the pid
                image = None
                how = "--hang-pid %d (image path unreadable: %s)" % (self.pid, err)
            else:
                how = "--hang-pid %d" % self.pid
            proc = GameProcess(self.pid, image, os.path.basename(image) if image else self.game_exe, how)
            target.proc = proc
        if proc is None:
            proc = self.resolver(target.client_port, target.server_port, self.game_exe)
            target.proc = proc
        return proc

    def _probe(self, target):
        try:
            proc = self._resolve(target)
            ok = (proc.exe or "").lower() == self.game_exe.lower()
            self.log("hang dumps ARMED for this connection: pid %d %s (%s)%s"
                     % (proc.pid, proc.image or proc.exe or "?", proc.how,
                        "" if ok else " -- NOT %s, a hang here will not be dumped" % self.game_exe))
        except Exception as err:            # noqa: BLE001 -- resolution failures are logged, not raised
            self.log("hang dumps armed, but the game pid is not resolved yet (%s) -- retrying at a hang" % err)

    def _dump(self, target, silent_s):
        partial = None
        attempted = False                                # set just before the writer runs: only then is the dump spent
        try:
            proc = self._resolve(target)
            if (proc.exe or "").lower() != self.game_exe.lower():
                self.log("hang dump skipped: pid %d is %r, not %s (the run's dump stays armed)"
                         % (proc.pid, proc.exe, self.game_exe))
                return
            os.makedirs(self.dump_dir, exist_ok=True)
            final = unique_path(self.dump_dir, "FF9-" + file_stamp(), ".dmp")
            stem = final[:-len(".dmp")]
            self._copy_logs(proc, stem)                  # small + frozen while hung: take them FIRST
            free = shutil.disk_usage(self.dump_dir).free
            if free < self.min_free:
                self.log("hang dump skipped: only %d MB free in %s (a full dump needs ~1-3 GB; the run's dump "
                         "stays armed)" % (free >> 20, self.dump_dir))
                return
            self.log("hang dump: writing a full dump of %s pid %d (silent %.1f s) -> %s"
                     % (self.game_exe, proc.pid, silent_s, final))
            partial = final + ".partial"
            attempted = True
            t0 = time.monotonic()
            for attempt in (1, 2):                       # one retry: the dump is the whole point
                try:
                    self.writer(proc.pid, partial)       # (re)opens + truncates the partial
                    break
                except OSError as err:
                    if attempt == 2:
                        raise
                    self.log("hang dump: attempt 1 failed (%s) -- retrying once in 1 s" % err)
                    time.sleep(1.0)
            os.replace(partial, final)
            partial = None
            self.dumps.append(final)
            self.log("hang dump written: %s (%d MB in %.1f s) -- WinDbg: ~*kb, !locks"
                     % (final, os.path.getsize(final) >> 20, time.monotonic() - t0))
        except Exception as err:            # noqa: BLE001 -- every failure is a log line, never a raise
            self.log("hang dump failed: %s%s" % (err, "" if attempted else " (the run's dump stays armed)"))
        finally:
            if partial is not None:
                try:
                    os.remove(partial)
                except OSError:
                    pass
            if not attempted:
                self._release()

    def _copy_logs(self, proc, stem):
        if not proc.image:
            self.log("hang dump: no image path for pid %d -- game logs not copied" % proc.pid)
            return
        out_log, mem_log = game_log_sources(proc.image)
        for src, suffix, what in ((out_log, ".output_log.txt", "output_log.txt"),
                                  (mem_log, ".Memoria.log", "Memoria.log")):
            if src is None:
                self.log("hang dump: no %s found beside %s" % (what, proc.image))
                continue
            try:
                shutil.copy2(src, stem + suffix)    # copy2 keeps the mtime: 'last written' is evidence
                self.log("hang dump: copied %s -> %s" % (src, stem + suffix))
            except OSError as err:
                self.log("hang dump: could not copy %s: %s" % (src, err))
