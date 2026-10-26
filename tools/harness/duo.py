#!/usr/bin/env python3
# Windows-first tool: invoke via the py launcher --  py tools/harness/duo.py <scenario.py>
"""Two FF9s on this desktop, PAIRED: a co-op host and a guest, each run from its own instance root, both harness-driven,
over the sittings' own bridge + relay path minus the internet -- two-role co-op benches without the laptop.

    py tools/harness/duo.py --smoke                      # pair on 250: config, relay, pairing, ghosts, mirror, story
    py tools/harness/duo.py <scenario.py>                # a scenario exposing run_duo(d), on a paired duo
    py tools/harness/duo.py <scenario.py> --topology relay --no-pair   # games dial the relay; the scenario pairs

A duo scenario is plain Python exposing ``run_duo(d)``; ``d`` is a :class:`Duo` with both games booted (and, unless
``--no-pair``, paired on the bench field -- ``d.pair(**PAIR)`` when the module defines a ``PAIR`` dict): ``d.host`` / ``d.guest`` are their :class:`~harness.session.Session` s, and the
cross-instance helpers -- :meth:`Duo.expect_line`, :meth:`Duo.expect_both`, :meth:`Duo.expect_parity`,
:meth:`Duo.expect_mirror` -- record each verdict on the duo AND on the Session(s) it concerns (so a red photographs the
game it was about). ``studies/test-harness/multi-instance/duo_p4.py`` is probe P4 re-expressed this way.

THE TOPOLOGY (studies/test-harness/multi-instance/RECON.md, "T-bridge-local"). ``tools/harness/coop_peer.py relay`` on a
private port with ``--tap`` (every forwarded frame, both directions, to ``relay.f9tape``); for ``bridge`` -- the
default, the sittings' own path -- one ``netsync_bridge`` PROCESS per player on its own private port, dialing that relay
and naming its game with ``--hang-pid``; for ``relay`` both games dial the relay directly. Each root's OWN Memoria.ini
gets its role's [Netsync] (``Role=client`` for the guest -- ``guest`` silently runs the selftest), through
:meth:`harness.instance.Instance.netsync` (the kit's writer), and the overlay is restored after the games quit.

THE LAWS IT ENFORCES (each from a probe or a hazard to the owner):

* **Private ports only**, never 49201 (the owner's bridge port: SO_REUSEADDR would co-bind beside it), and every port free
  BEFORE anything starts.
* **A fresh SessionCode** per duo, refused if it equals the owner's live one (it would evict the laptop's leg on the
  public relay).
* **Harness-armed launches only**, through instance roots (an unarmed root relaunches the REAL install via Steam).
* **Config at field load.** A root boots with Netsync OFF, so no NetSyncClient polls its ini: the role lands only at a
  field load. The recipe (coop_tape_record._wait_config, P4): a short wait for the config line, then ONE same-field warp.
* **Unattended = no controller connected and nobody at the keyboard** (a pad press paused a P3 host). Not checkable here;
  the banner says it.

Artifacts: ``.harness-runs/<stamp>-duo-<label>/`` -- ``host/`` and ``guest/`` (each Session's own run dir: both logs,
frames, report.json), ``relay.log`` + ``relay.f9tape``, ``bridge-<role>.log``, ``ini/`` (the [Netsync] backups) and
``duo.json`` (every duo check, the code, ports, pids, how each process ended, the roots' verify after).
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import importlib.util
import json
import os
import random
import re
import shutil
import signal
import socket
import string
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ""):                         # run as a script: make `harness` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "harness"

from .channel import HarnessError                    # noqa: E402
from .instance import INSTANCES_HOME, Instance       # noqa: E402
from .session import RUNS, Session                   # noqa: E402

REPO = Path(__file__).resolve().parents[2]
COOP_PEER = REPO / "tools" / "harness" / "coop_peer.py"
BRIDGE = REPO / "ff9mapkit" / "ff9mapkit" / "netsync_bridge.py"

ROLES = ("host", "guest")
DEFAULT_ROOTS = {"host": INSTANCES_HOME / "host", "guest": INSTANCES_HOME / "guest"}
RELAY_PORT = 7787
BRIDGE_PORTS = {"host": 49211, "guest": 49212}
#: Never bound by a duo: the owner's production bridge port (the game's default RelayUrl). SO_REUSEADDR co-binds.
OWNER_PORT = 49201
BENCH_FIELD = 250                    # Evil Forest/Trail: sitting A's meeting field, art + walkable (P3/P4)
BENCH_SCENE = 67                     # BSC_EF_R007, one Goblin -- the scene sitting A fought on 250
#: The story marker the host pokes and the guest must read back through the state mirror: gEventGlobal byte 1121 (bits
#: 8968-8975, the campaign lane, >= flags.FIRST_SAFE_FLAG), value 0xA5 (a palindrome: either bit order reads it).
MARKER_BYTE, MARKER_VALUE = 1121, 0xA5
WINDOW = (960, 540)

#: Each role's [Netsync] for a duo (P4's values). The guest is Role=client -- NOT guest, which runs the selftest.
ROLE_VALUES = {
    "host": {"Enabled": "1", "Role": "host", "GuestSlots": "2", "FollowHost": "0", "TargetField": "0",
             "StartHoldMs": "8000"},
    "guest": {"Enabled": "1", "Role": "client", "FollowHost": "1", "TargetField": "0", "GuestSlots": "0",
              "GuestStockMenu": "1", "AutoTeleport": "0"},
}
ENGINE_ROLE = {"host": "host", "guest": "client"}     # the config line's role= for each

# ------------------------------------------------------------------------------------------------ engine lines
#: The engine lines a duo judges, one anchored regex on the MESSAGE (the ``dd.MM.yyyy HH:mm:ss |L| `` prefix stripped).
#: VERBATIM copies of studies/test-harness/scenarios/_coop_peer_bench.py's MATCHERS, whose self-check pins them to the
#: engine's C#; test_harness_duo.py fails the day the two drift.
MATCHERS = {
    "config": re.compile(r"^\[NetSync\] config enabled=(True|False) role=(\S+) field=(-?\d+)(.*?)"
                         r"(?: relay=(\S+) code=(\S*)| peer=(\S+))$"),
    "config_live": re.compile(r"^\[NetSync\] config change applied live"),
    "relay_up": re.compile(r"^\[NetSync\] relay connected (wss?://\S+?)/sess/(\S+)\?role=(host|guest)$"),
    "relay_down": re.compile(r"^\[NetSync\] relay disconnected; retrying"),
    "paired": re.compile(r"^\[NetSync\] paired on the host's field \((\d+)\) -- reloading it once so the state mirror "
                         r"arms$"),
    "armed": re.compile(r"^\[NetSync\] state-mirror ARMED -- this guest's fields now stage the HOST's story$"),
    "ghost": re.compile(r"^\[NetSync\] ghost spawned as (\S+) on field (\d+) \(ui=(\w+)\)$"),
    "intro": re.compile(r"^\[NetSync\] battle intro: (SKIPPED|PLAYED|unreadable)"),
    "boot": re.compile(r"^\[NetSync\] diorama BOOT scene=(\d+) pattern=(\d+) start=(\S+)( rand)? intro=(\S+) "
                       r"swirl=(-?\d+) clamp=(.+)$"),
    "live": re.compile(r"^\[NetSync\] diorama LIVE (\d+) ms after the boot \(host battle nonce (-?\d+), booted from "
                       r"(?:wire nonce (\d+)|no wire nonce)\) -- the start-hold report for this battle now reads LIVE$"),
    "ramp": re.compile(r"^\[NetSync\] session ended -> reloading own autosave \(Continue\)$"),
    "ramp_failed": re.compile(r"^\[NetSync\] session ended, no autosave to resume -> title screen$"),
}

_ENGINE_LINE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}):(\d{2}) \|(\w)\| (.*)$")


def parse_engine_line(line: str):
    """``dd.MM.yyyy HH:mm:ss |L| msg`` -> (datetime, level, msg); None for a continuation line (a stack frame)."""
    m = _ENGINE_LINE.match(line.rstrip("\r\n"))
    if not m:
        return None
    d, mo, y, h, mi, s = (int(v) for v in m.groups()[:6])
    return _dt.datetime(y, mo, d, h, mi, s), m.group(7), m.group(8)


class EngineLog:
    """One game's Memoria.log, read incrementally from where :meth:`mark` left it: ``lines()`` -> [(datetime, level,
    msg)]. A file that SHRANK (a relaunch truncated it) is re-read from its start."""

    def __init__(self, path, *, from_start: bool = True):
        self.path = Path(path) if path else None
        self._off = 0
        self._partial = b""
        self._lines: list = []
        if not from_start:
            self.mark()

    def mark(self) -> None:
        self._lines, self._partial = [], b""
        try:
            self._off = self.path.stat().st_size if self.path else 0
        except OSError:
            self._off = 0

    def lines(self) -> list:
        if self.path is None:
            return self._lines
        try:
            size = self.path.stat().st_size
            if size < self._off:
                self._off, self._partial, self._lines = 0, b"", []
            with open(self.path, "rb") as f:
                f.seek(self._off)
                chunk = f.read()
                self._off = f.tell()
        except OSError:
            return self._lines
        parts = (self._partial + chunk).split(b"\n")
        self._partial = parts.pop()
        for p in parts:
            got = parse_engine_line(p.decode("utf-8", "replace"))
            if got is not None:
                self._lines.append(got)
        return self._lines


def hits(lines, name: str, *, after: _dt.datetime | None = None, pred=None, matchers=None) -> list:
    """``[(datetime, msg, match)]`` of ``lines`` that matcher ``name`` matches, at or after ``after`` (floored to the
    second: engine stamps are whole seconds, truncated)."""
    rx = (matchers or MATCHERS)[name]
    lo = after.replace(microsecond=0) if after is not None else None
    out = []
    for t, _lvl, msg in lines:
        if lo is not None and t < lo:
            continue
        m = rx.search(msg)
        if m and (pred is None or pred(m)):
            out.append((t, msg, m))
    return out


def show(found, n: int = 2) -> str:
    return " || ".join(f"{t:%H:%M:%S} {m[:150]}" for t, m, _ in found[:n]) or "none"


# ------------------------------------------------------------------------------------------------ helpers
def fresh_code() -> str:
    """``ff9-DUO`` + 5 (GenerateSessionCode's ``ff9-`` + 8 shape): new per duo, never anyone's live code."""
    return "ff9-DUO" + "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(5))


def owner_code(install) -> str | None:
    """The owner's live [Netsync] SessionCode (read-only, last key wins), or None."""
    from ff9mapkit.coop import read_ini_key
    try:
        return read_ini_key(Path(install, "Memoria.ini").read_text(encoding="utf-8-sig", errors="replace"),
                            "Netsync", "SessionCode")
    except OSError:
        return None


def port_free(port: int, host: str = "127.0.0.1") -> bool:
    """Can ``port`` be bound EXCLUSIVELY right now (what coop_peer's listener and the bridge do)?"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((host, int(port)))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def wait_bound(port: int, timeout: float, *, alive=None) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not port_free(port):
            return True
        if alive is not None and not alive():
            return False
        time.sleep(0.2)
    return not port_free(port)


#: Runs a tool script with Windows' CTRL_BREAK mapped to KeyboardInterrupt, so a stop takes the tool's own clean path
#: (coop_peer flushes and closes its tape; the bridge logs "stopped") instead of a kill that tears a tape's tail.
_LAUNCH = ("import os, runpy, signal, sys\n"
           "if hasattr(signal, 'SIGBREAK'):\n"
           "    signal.signal(signal.SIGBREAK, signal.default_int_handler)\n"
           "script = sys.argv[1]\n"
           "sys.path.insert(0, os.path.dirname(script))\n"
           "sys.argv = sys.argv[1:]\n"
           "runpy.run_path(script, run_name='__main__')\n")


class ToolProc:
    """A helper process (the relay, a bridge) with its own process group, its stdout captured to ``out_path`` and its
    ``--log`` tee readable as it grows."""

    def __init__(self, name: str, script: Path, args, *, log_path: Path, out_path: Path, python: str | None = None):
        self.name = name
        self.script = Path(script)
        self.args = [str(a) for a in args]
        self.log_path = Path(log_path)
        self.out_path = Path(out_path)
        self.python = python or sys.executable
        self.proc: subprocess.Popen | None = None
        self.how_ended: str | None = None
        self._out = None

    @property
    def argv(self) -> list:
        return [self.python, "-u", "-c", _LAUNCH, str(self.script), *self.args, "--log", str(self.log_path)]

    def start(self) -> "ToolProc":
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        self._out = open(self.out_path, "ab")
        self.proc = subprocess.Popen(self.argv, cwd=str(REPO), stdout=self._out, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags)
        return self

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def text(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def wait_for(self, pattern, timeout: float):
        rx = re.compile(pattern) if isinstance(pattern, str) else pattern
        deadline = time.time() + timeout
        while True:
            for line in self.text().splitlines():
                m = rx.search(line)
                if m:
                    return line
            if not self.alive() or time.time() >= deadline:
                return None
            time.sleep(0.1)

    def tail(self, n: int = 6) -> str:
        return " | ".join(self.text().splitlines()[-n:])[:900]

    def stop(self, timeout: float = 10.0) -> str:
        if self.proc is None:
            self.how_ended = "never started"
        elif self.proc.poll() is not None:
            self.how_ended = self.how_ended or f"had exited by itself (code {self.proc.returncode})"
        else:
            try:
                self.proc.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
            except (OSError, ValueError, AttributeError):
                pass
            try:
                self.proc.wait(timeout)
                self.how_ended = f"stopped cleanly (code {self.proc.returncode})"
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(3.0)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(3.0)
                self.how_ended = f"TERMINATED after {timeout:g} s with no clean stop (code {self.proc.returncode})"
        with contextlib.suppress(OSError, AttributeError):
            self._out.close()
        return self.how_ended


class DuoRed(HarnessError):
    """A strict duo check failed -- the run stops at its first surprise (the owner's rule for probes)."""


# ------------------------------------------------------------------------------------------------ the duo
class Duo:
    """Two instance-root games, a local relay, a bridge per player, and the checks that judge them together.

    ``session_factory(role, instance, run_dir, label)`` and ``procs`` are the test seams: the offline suite drives two
    FakeGames and starts no relay or bridge. Production leaves both alone."""

    def __init__(self, *, label: str = "duo", host=None, guest=None, topology: str = "bridge",
                 relay_port: int = RELAY_PORT, bridge_ports: dict | None = None, code: str | None = None,
                 field: int = BENCH_FIELD, window_size=WINDOW, run_dir=None, hang_dump: bool = False,
                 install=None, strict: bool = True, verbose: bool = True, procs: bool = True,
                 session_factory=None, instances: dict | None = None, boot_timeout: float = 240.0,
                 config_wait: float = 6.0):
        if topology not in ("bridge", "relay"):
            raise ValueError(f"topology must be 'bridge' or 'relay', not {topology!r}")
        self.label = re.sub(r"[^A-Za-z0-9_.-]", "_", label)
        self.topology = topology
        self.relay_port = int(relay_port)
        self.bridge_ports = dict(bridge_ports or BRIDGE_PORTS)
        self.field = int(field)
        self.window_size = tuple(window_size)
        self.hang_dump = hang_dump
        self.strict = strict
        self.verbose = verbose
        self.use_procs = procs
        self.boot_timeout = boot_timeout
        self.config_wait = float(config_wait)        # P4's "short wait" before the one same-field warp
        self._factory = session_factory
        if instances is not None:
            self.instances = dict(instances)
        else:
            roots = {"host": host or DEFAULT_ROOTS["host"], "guest": guest or DEFAULT_ROOTS["guest"]}
            self.instances = {r: Instance(roots[r], install=install, label=r) for r in ROLES}
        h, g = self.instances["host"].root, self.instances["guest"].root
        if os.path.normcase(str(h.resolve())) == os.path.normcase(str(g.resolve())):
            raise HarnessError(f"host and guest are the same root ({h}) -- a duo needs two")
        self.install = self.instances["host"].install
        self.code = code or fresh_code()
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.run_dir = Path(run_dir) if run_dir else RUNS / f"{stamp}-duo-{self.label}"
        self.sessions: dict[str, Session] = {}
        self.logs: dict[str, EngineLog] = {}
        self.pids: dict[str, int | None] = {}
        self.checks: list[dict] = []
        self.notes: list[str] = []
        self.relay: ToolProc | None = None
        self.bridges: dict[str, ToolProc] = {}
        self.ini_backups: dict[str, str | None] = {}
        #: [ff9mapkit netsync s139] a scenario's own [Netsync] keys per role ON TOP of ROLE_VALUES (``pair(role_extra=...)``,
        #: e.g. the host's GhostAs for coop_dress_wire.py) -- never Role, RelayUrl or SessionCode (the duo owns those)
        self.role_extra: dict = {}
        self.paired = False
        self._stack = contextlib.ExitStack()
        self._report: dict = {}
        self._started = None

    # -- logging + checks ------------------------------------------------------------------------
    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"[duo] {msg}", flush=True)

    def note(self, msg: str) -> None:
        self.notes.append(msg)
        self.log(msg)

    @property
    def host(self) -> Session:
        return self.sessions["host"]

    @property
    def guest(self) -> Session:
        return self.sessions["guest"]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c["ok"] for c in self.checks)

    def check(self, ok: bool, what: str, detail: str = "", *, role: str | None = None, cid: str | None = None) -> bool:
        """Record a duo verdict -- and on the Session(s) it concerns (``role``: one; None: both), so each game's report
        carries it and a red photographs that game. Strict (the default): a red raises :class:`DuoRed`."""
        row = {"id": cid, "ok": bool(ok), "what": what, "detail": detail, "role": role,
               "at": _dt.datetime.now().isoformat(timespec="milliseconds")}
        self.checks.append(row)
        self.log(f"{'PASS' if ok else 'FAIL'}  {(cid + ' ') if cid else ''}{what}" + (f"  [{detail[:300]}]" if detail
                                                                                         else ""))
        for r in ([role] if role else ROLES):
            g = self.sessions.get(r)
            if g is not None:
                with contextlib.suppress(Exception):
                    g.check(ok, f"[duo] {what}", detail)
        if not ok and self.strict:
            raise DuoRed(f"{cid or what}: {detail}"[:600])
        return bool(ok)

    # -- engine lines -----------------------------------------------------------------------------
    def lines(self, role: str) -> list:
        return self.logs[role].lines()

    def wait_line(self, role: str, name: str, timeout: float, *, pred=None, after=None) -> list:
        deadline = time.time() + timeout
        while True:
            found = hits(self.lines(role), name, pred=pred, after=after)
            if found or time.time() >= deadline:
                return found
            g = self.sessions.get(role)
            if g is not None:
                g._assert_alive()                  # a dead game is said as one, never a timeout
            time.sleep(0.25)

    def expect_line(self, role: str, name: str, what: str | None = None, *, timeout: float = 30.0, pred=None,
                    after=None, cid: str | None = None) -> list:
        """The ``role``'s engine log reaches a line ``name`` matches (and ``pred`` accepts) within ``timeout``."""
        found = self.wait_line(role, name, timeout, pred=pred, after=after)
        seen = hits(self.lines(role), name)
        self.check(bool(found), what or f"the {role} logs '{name}'",
                   show(found) if found else f"none within {timeout:g}s; '{name}' lines seen: {show(seen)}",
                   role=role, cid=cid)
        return found

    def expect_both(self, name: str, what: str | None = None, *, timeout: float = 30.0, pred=None, after=None,
                    cid: str | None = None) -> dict:
        """The same kind of line in BOTH games (one ``pred`` for both; a per-role test is two :meth:`expect_line`)."""
        return {r: self.expect_line(r, name, f"{what or name} ({r})", timeout=timeout, pred=pred, after=after,
                                    cid=f"{cid}-{r}" if cid else None) for r in ROLES}

    def expect_parity(self, what: str, read, *, timeout: float = 20.0, want=None, cid: str | None = None):
        """``read(state)`` gives the SAME value in both games (and ``want``, when given) within ``timeout``."""
        deadline = time.time() + timeout
        vals = {}
        while True:
            for r in ROLES:
                try:
                    vals[r] = read(self.sessions[r].state)
                except HarnessError:
                    raise
                except Exception as err:            # noqa: BLE001 - a reader's KeyError is "not yet", not a crash
                    vals[r] = f"<{type(err).__name__}>"
            ok = vals["host"] == vals["guest"] and (want is None or vals["host"] == want)
            if ok or time.time() >= deadline:
                break
            time.sleep(0.2)
        self.check(ok, what, f"host {vals['host']!r} guest {vals['guest']!r}" + (f" (want {want!r})" if want is not None
                                                                                 else ""), cid=cid)
        return vals

    def expect_mirror(self, byte: int = MARKER_BYTE, value: int = MARKER_VALUE, *, timeout: float = 20.0,
                      cid: str | None = None):
        """The GUEST reads the host's story byte through the state mirror: its watched bits of ``byte`` publish
        ``value`` (its own New-Game save holds 0). :meth:`pair` pokes and watches it when given ``marker=``."""
        deadline = time.time() + timeout
        got = None
        while time.time() < deadline:
            got = watched_byte(self.guest.state, byte)
            if got == value:
                break
            time.sleep(0.2)
        self.check(got == value, f"the guest's story byte {byte} reads the HOST's 0x{value:02X} (the state mirror)",
                   f"guest reads {got!r} (own save 0)", role="guest", cid=cid)
        return got

    def archive(self, tag: str) -> dict:
        """Snapshot both games' Memoria.log + output_log.txt into their run dirs NOW (memory
        feedback-archive-capture-logs-immediately); each Session archives them again at its teardown."""
        out = {}
        for r, g in self.sessions.items():
            dest = Path(g.run_dir)
            for path, name in ((g.engine_log(), "Memoria"), (g.unity_log(), "output_log")):
                if path is None:
                    continue
                try:
                    target = dest / f"{name}-{re.sub(r'[^A-Za-z0-9_.-]', '_', tag)}{path.suffix}"
                    shutil.copy2(path, target)
                    out[f"{r}-{name}"] = str(target)
                except OSError as err:
                    out[f"{r}-{name}"] = f"failed: {err}"
        return out

    def controller_lines(self) -> dict:
        """Each game's ``[ControllerWatcher]`` lines so far. "Device connected/disconnected" means a pad came or went
        mid-run -- and a DISCONNECT pauses FF9 (ControllerWatcher.RefreshControllers -> OnKeyPause) whatever the window
        focus or AlwaysCaptureGamepad: the unattended law's evidence, read off the logs instead of assumed."""
        out = {}
        for r, el in self.logs.items():
            with contextlib.suppress(Exception):
                out[r] = [f"{t:%H:%M:%S} {m}" for t, _l, m in el.lines() if m.startswith("[ControllerWatcher]")]
        return out

    # -- lifecycle --------------------------------------------------------------------------------
    def __enter__(self) -> "Duo":
        try:
            self.start()
        except BaseException as err:
            self.stop(failed=True, why=str(err))
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.stop(failed=exc is not None, why=str(exc) if exc else None)
        return False

    def _ports(self) -> list[int]:
        return [self.relay_port] + ([self.bridge_ports[r] for r in ROLES] if self.topology == "bridge" else [])

    def url(self, role: str) -> str:
        port = self.bridge_ports[role] if self.topology == "bridge" else self.relay_port
        return f"ws://127.0.0.1:{port}"

    def role_values(self, role: str) -> dict:
        vals = dict(ROLE_VALUES[role])
        extra = dict(self.role_extra.get(role) or {})
        owned = sorted(k for k in extra if k in ("Role", "RelayUrl", "SessionCode"))
        if owned:
            raise HarnessError(f"role_extra for the {role} names {owned}: the duo owns those keys")
        vals.update(extra)
        vals.update({"RelayUrl": self.url(role), "SessionCode": self.code})
        assert vals["Role"] in ("host", "client"), vals          # never "guest": that is the selftest
        return vals

    def start(self) -> None:
        self._started = time.time()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log(f"run dir {self.run_dir}; topology {self.topology}; code {self.code}; roots "
                 f"{self.instances['host'].root} + {self.instances['guest'].root}")
        self.log("UNATTENDED LAW: no controller connected, nobody at the keyboard while a game window is foreground")
        live = owner_code(self.install)
        if live and live == self.code:
            raise HarnessError(f"the duo's SessionCode {self.code} is the owner's live one -- refusing")
        if self.use_procs:
            ports = self._ports()
            bad = [p for p in ports if p == OWNER_PORT or p < 1024]
            if bad:
                raise HarnessError(f"ports {bad}: a duo binds PRIVATE ports only (never {OWNER_PORT}, the owner's "
                                   f"bridge)")
            busy = [p for p in ports if not port_free(p)]
            self.check(not busy, f"ports {ports} free before anything starts", f"busy: {busy}", cid="C0")
            self.relay = ToolProc("relay", COOP_PEER, ["relay", "--port", self.relay_port, "--tap",
                                                       self.run_dir / "relay.f9tape", "--status", "5"],
                                  log_path=self.run_dir / "relay.log", out_path=self.run_dir / "relay.out").start()
            up = self.relay.wait_for(r"relay listening on ws://127\.0\.0\.1:(\d+)", 15.0)
            self.check(up is not None, f"the local relay listens on {self.relay_port} (--tap relay.f9tape)",
                       up or f"no banner; tail {self.relay.tail()}", cid="C1-relay")
        for r in ROLES:
            self.instances[r].ensure(label=f"{self.label}-{r}")
        for r in ROLES:
            self._boot(r)
        if self.use_procs and self.topology == "bridge":
            for r in ROLES:
                self._start_bridge(r)

    def _boot(self, role: str) -> None:
        inst = self.instances[role]
        rd = self.run_dir / role
        label = f"{self.label}-{role}"
        if self._factory is not None:
            cm = self._factory(role, inst, rd, label)
        else:
            cm = Session(label=label, instance=inst, run_dir=rd, window_size=self.window_size,
                         boot_timeout=self.boot_timeout)
        t0 = time.time()
        g = self._stack.enter_context(cm)
        self.sessions[role] = g
        self.pids[role] = getattr(g, "pid", None)
        self.logs[role] = EngineLog(g.engine_log() or (inst.root / "Memoria.log"))
        self.note(f"{role} up in {time.time() - t0:.1f}s: pid {self.pids[role]}, channel {g.channel.dir}")

    def _start_bridge(self, role: str) -> None:
        port = self.bridge_ports[role]
        args = ["--port", port, "--relay", f"ws://127.0.0.1:{self.relay_port}"]
        if self.pids.get(role):
            args += ["--hang-pid", self.pids[role]]
        if self.hang_dump:
            args += ["--hang-dump", "--hang-dump-dir", self.run_dir / "hangdumps"]
        b = ToolProc(f"bridge-{role}", BRIDGE, args, log_path=self.run_dir / f"bridge-{role}.log",
                     out_path=self.run_dir / f"bridge-{role}.out").start()
        self.bridges[role] = b
        self.check(wait_bound(port, 15.0, alive=b.alive), f"the {role}'s bridge listens on {port} -> relay "
                   f"{self.relay_port} (--hang-pid {self.pids.get(role)})", b.tail(3), role=role,
                   cid=f"C1-bridge-{role}")

    # -- pairing (the P4 recipe) -------------------------------------------------------------------
    def apply_role(self, role: str, *, cid: str | None = None) -> list:
        """Write ``role``'s [Netsync] into its root's ini and see the engine take it: a short wait for the matching
        config line, then ONE same-field warp (a root booted with Netsync off reads its ini only at a field load)."""
        g = self.sessions[role]
        vals = self.role_values(role)
        bak = self.instances[role].netsync(vals, backup_to=self.run_dir / "ini")
        self.ini_backups[role] = str(bak) if bak else None
        url = vals["RelayUrl"]

        def want(m):
            return (m.group(1) == "True" and m.group(2) == ENGINE_ROLE[role] and m.group(5) == url
                    and m.group(6) == self.code)
        cfg = self.wait_line(role, "config", self.config_wait, pred=want)
        if not cfg:
            here = g.state.field_id
            self.log(f"{role}: no config line yet -- one same-field warp ({here}) so the field load reads the ini")
            g.warp(here)
            cfg = self.wait_line(role, "config", 10.0, pred=want)
        self.check(bool(cfg), f"the {role} took its role from its own ini (role {ENGINE_ROLE[role]}, {url}, "
                   f"{self.code})", show(cfg) if cfg else f"no matching config line; seen "
                   f"{show(hits(self.lines(role), 'config'))}", role=role, cid=cid)
        return cfg

    def set_netsync(self, role: str, updates: dict, *, timeout: float = 15.0, pred=None) -> list:
        """[ff9mapkit netsync s139] A LIVE [Netsync] edit on a running pair (coop_dress_wire.py steps the host's GuestSlots
        through its phases): ``updates`` folded into the role's scenario keys (:attr:`role_extra` -- never Role, RelayUrl
        or SessionCode, refused before anything is written) and the role's whole [Netsync] rewritten through the kit's
        writer -- the same values plus the edit, so the TRANSPORT signature is unchanged and the session survives: a
        BEHAVIOUR key (GuestSlots, GhostAs, ...: NetSyncClient's _cfgBehaviorSig) is applied live by its Update's 2 s ini
        poll -> ApplyBehaviorChange. Returns the engine's own echo -- this role's config lines logged at or after the
        write, on its relay URL and code, that ``pred`` (the match) accepts -- or [] when none within ``timeout``. The
        ini's backup lands in the run dir's ``ini/`` beside the pairing's (:attr:`ini_backups` keeps the pairing's);
        :meth:`stop` restores the root's ini as ever."""
        owned = sorted(k for k in updates if k in ("Role", "RelayUrl", "SessionCode"))
        if owned:
            raise HarnessError(f"set_netsync for the {role} names {owned}: the duo owns those keys")
        self.role_extra = dict(self.role_extra)
        self.role_extra[role] = dict(self.role_extra.get(role) or {}, **{k: str(v) for k, v in updates.items()})
        vals = self.role_values(role)
        at = _dt.datetime.now()
        self.instances[role].netsync(vals, backup_to=self.run_dir / "ini")
        url = vals["RelayUrl"]

        def want(m):
            return (m.group(1) == "True" and m.group(2) == ENGINE_ROLE[role] and m.group(5) == url
                    and m.group(6) == self.code and (pred is None or pred(m)))
        found = self.wait_line(role, "config", timeout, pred=want, after=at)
        self.log(f"{role}: [Netsync] {dict(updates)} written live -- "
                 + (f"the engine echoed it: {show(found, 1)}" if found else f"NO matching config line within {timeout:g}s"))
        return found

    def pair(self, *, field: int | None = None, host_setup=None, guest_setup=None,
             marker: tuple | None = (MARKER_BYTE, MARKER_VALUE), encounters_off: bool = True,
             role_extra: dict | None = None) -> None:
        """New Game in both, each onto ``field`` (host first; ``host_setup(g)`` / ``guest_setup(g)`` run after its New
        Game), the host poking ``marker`` and the guest watching it; then each role's ini, host first (C2); both legs
        on the relay (C3); the guest paired on the host's field (C4); a ghost on it in BOTH games (C5); the guest's
        state mirror ARMED (C6). ``expect_mirror`` (C7) is the caller's: it is the mirror's first proof, not setup.
        ``role_extra`` ({role: {key: value}}) adds a scenario's own [Netsync] keys to each role's (:attr:`role_extra`)."""
        fld = self.field if field is None else int(field)
        if role_extra is not None:
            self.role_extra = {r: dict(v or {}) for r, v in role_extra.items()}
            for r in self.role_extra:
                self.role_values(r)                 # refuse a key the duo owns BEFORE anything is written
        for r in ROLES:
            g = self.sessions[r]
            g.newgame()
            setup = host_setup if r == "host" else guest_setup
            if setup is not None:
                note = setup(g)
                if note:
                    g.note(str(note))
            if g.state.field_id != fld:
                g.warp(fld)
            if encounters_off:
                try:
                    g.no_encounters(True)
                except HarnessError as err:
                    g.note(f"noencounter refused ({str(err)[:120]}) -- a random battle may interrupt")
            if marker is not None:
                byte, value = marker
                if r == "host":
                    g.poke(byte, value)
                else:
                    g.watch(*(byte * 8 + b for b in range(8)))
        for r in ROLES:
            self.apply_role(r, cid=f"C2-{r}")
        for r in ROLES:
            self.expect_line(r, "relay_up", f"the {r} is connected to the relay as role={r}", timeout=30.0,
                             pred=lambda m, _r=r: m.group(3) == _r and m.group(2) == self.code, cid=f"C3-{r}")
        self.expect_line("guest", "paired", f"the guest paired on the host's field ({fld})", timeout=45.0,
                         pred=lambda m: int(m.group(1)) == fld, cid="C4")
        self.expect_both("ghost", f"a ghost spawned on {fld}", timeout=30.0, pred=lambda m: int(m.group(2)) == fld,
                         cid="C5")
        self.expect_line("guest", "armed", "the guest's state mirror ARMED", timeout=30.0, cid="C6")
        self.paired = True

    # -- teardown ---------------------------------------------------------------------------------
    def stop(self, *, failed: bool = False, why: str | None = None) -> None:
        """Games first (each Session quits its game, disarms, archives BOTH logs, releases its root), then the inis back
        to install + overlay, then the bridges and the relay (clean: the tape flushes), then duo.json. Every step runs
        whatever the one before it did."""
        rep = self._report
        rep["controller_lines"] = self.controller_lines()
        if any("Device" in m for lines in rep["controller_lines"].values() for m in lines):
            self.log("!! a controller connected or DISCONNECTED during the run: ControllerWatcher pauses the game on a "
                     "disconnect (a sleeping wireless pad too) -- see duo.json controller_lines")
        rep.update({"label": self.label, "topology": self.topology, "code": self.code, "field": self.field,
                    "relay_port": self.relay_port, "bridge_ports": self.bridge_ports if self.topology == "bridge"
                    else None, "roots": {r: str(i.root) for r, i in self.instances.items()},
                    "install": str(self.install), "pids": self.pids, "paired": self.paired})
        try:
            self._stack.close()
        except Exception as err:                                   # noqa: BLE001
            rep["session_close_error"] = str(err)
            self.log(f"closing the sessions raised: {err}")
        restored = {}
        for r, inst in self.instances.items():
            try:
                restored[r] = "rewritten to install + overlay" if inst.restore_ini() else "already install + overlay"
            except Exception as err:                               # noqa: BLE001
                restored[r] = f"FAILED: {err} -- the next refresh() regenerates it"
        rep["ini_restored"] = restored
        procs = {}
        for name, p in [(f"bridge-{r}", b) for r, b in self.bridges.items()] + [("relay", self.relay)]:
            if p is not None:
                try:
                    procs[name] = p.stop()
                except Exception as err:                           # noqa: BLE001
                    procs[name] = f"stop failed: {err}"
        rep["processes"] = procs
        left, verify = {}, {}
        for r, inst in self.instances.items():
            with contextlib.suppress(Exception):
                left[r] = inst.pids()
            with contextlib.suppress(Exception):
                verify[r] = inst.verify()
        rep.update({"games_left": left, "roots_verify_after": verify, "raised": failed, "why": why,
                    "checks": self.checks, "notes": self.notes,
                    "verdict": ("fail" if failed or not all(c["ok"] for c in self.checks) else
                                "pass" if self.checks else "proved-nothing"),
                    "seconds": round(time.time() - self._started, 1) if self._started else None,
                    "session_run_dirs": {r: str(g.run_dir) for r, g in self.sessions.items()}})
        try:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            (self.run_dir / "duo.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
        except OSError as err:
            self.log(f"duo.json not written ({err})")
        self.log(f"verdict {rep['verdict']}; games left {left}; processes {procs}; artifacts in {self.run_dir}")


def watched_byte(st, byte: int):
    """A story byte as the WATCHED bits publish it (``flags``, LSB first); None while any of its 8 bits is unwatched."""
    raw = st.raw if hasattr(st, "raw") else (st or {})
    flags = raw.get("flags") or {}
    val = 0
    for b in range(8):
        bit = flags.get(str(byte * 8 + b))
        if bit is None:
            return None
        if bit:
            val |= 1 << b
    return val


# ------------------------------------------------------------------------------------------------ CLI
def smoke(d: Duo) -> None:
    """Pair on the bench field and prove the mirror: C0-C7 of probe P4 (the battle leg C8 lives in duo_p4.py)."""
    if not d.paired:
        d.pair()
    d.expect_mirror(cid="C7")


def load_scenario(path: Path):
    spec = importlib.util.spec_from_file_location(f"duo_scenario_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise HarnessError(f"cannot import a duo scenario from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run_duo"):
        raise HarnessError(f"{path} defines no run_duo(d) function")
    return mod


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            stream.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", nargs="?", help="a Python file exposing run_duo(d)")
    ap.add_argument("--smoke", action="store_true", help="pair on the bench field and prove the mirror (C0-C7)")
    ap.add_argument("--host", default=None, help=f"the host's instance root (default {DEFAULT_ROOTS['host']})")
    ap.add_argument("--guest", default=None, help=f"the guest's instance root (default {DEFAULT_ROOTS['guest']})")
    ap.add_argument("--topology", choices=("bridge", "relay"), default="bridge",
                    help="bridge: one netsync_bridge per player -> the relay (default, the sittings' path); "
                         "relay: both games dial the relay directly")
    ap.add_argument("--relay-port", type=int, default=RELAY_PORT)
    ap.add_argument("--bridge-ports", default=f"{BRIDGE_PORTS['host']},{BRIDGE_PORTS['guest']}", metavar="H,G")
    ap.add_argument("--field", type=int, default=BENCH_FIELD, help="the field both games pair on")
    ap.add_argument("--no-pair", action="store_true", help="boot both, but leave pairing to the scenario")
    ap.add_argument("--hang-dump", action="store_true", help="let each bridge write ONE full dump of a hung game")
    ap.add_argument("--keep-going", action="store_true", help="record a red and continue (default: stop at it)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--timeout", type=float, default=240.0, help="seconds to wait for each agent")
    a = ap.parse_args(argv)
    if not a.smoke and not a.scenario:
        ap.error("give a duo scenario file or --smoke")
    scenario = load_scenario(Path(a.scenario)) if a.scenario else None
    bp = [int(x) for x in a.bridge_ports.split(",")]
    label = a.label or ("smoke" if a.smoke else Path(a.scenario).stem)
    d = Duo(label=label, host=a.host, guest=a.guest, topology=a.topology, relay_port=a.relay_port,
            bridge_ports={"host": bp[0], "guest": bp[1]}, field=a.field, hang_dump=a.hang_dump,
            strict=not a.keep_going, boot_timeout=a.timeout)
    try:
        with d:
            if not a.no_pair:
                d.pair(**(getattr(scenario, "PAIR", None) or {}))
            if a.smoke:
                smoke(d)
            if scenario is not None:
                scenario.run_duo(d)
    except DuoRed as red:
        print(f"\n!!! STOPPED at the first red -- {red}", file=sys.stderr)
    except HarnessError as err:
        print(f"\n!!! harness error: {err}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n!!! interrupted", file=sys.stderr)
        return 130
    failed = [c for c in d.checks if not c["ok"]]
    print(f"\n{'-' * 72}\nduo {label}: {len(d.checks) - len(failed)}/{len(d.checks)} checks passed")
    for c in failed:
        print(f"  FAIL  {c.get('id') or ''} {c['what']}\n        {c['detail'][:300]}")
    print(f"artifacts: {d.run_dir}")
    return 0 if d.passed and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
