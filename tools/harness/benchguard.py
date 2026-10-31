"""THE BENCH GUARD: a live game bench refuses to start under a running test suite.

THE LAW (memory project-ff9-multiplayer-injector, s159): NEVER BENCH UNDER A RUNNING TEST SUITE. Six pytest workers swung the
frame rate 35-84 fps and red-flagged timing legs on a correct engine; idle, every red was a predicted one. It fired again on
2026-10-30: the s164 solo regression set and the first s164 duo ran 04:00-06:08 under the nightly gate's `-n 6` suite, and
coop_step_out N-DWELL and coop_climb_anim GF207-TRACK went red at 30 fps on a correct engine (green idle, at 60).

Two signals; either one refuses:

* THE GATE LOCK -- ``<main repo>/.test-gate/lock`` (tools/nightly_gate.py's ``acquire_lock`` writes ``{"pid", "started"}``),
  present for the nightly's whole run (~04:00-06:10). The main repo, never this checkout: a worktree has no ``.test-gate``.
  A lock whose holder pid is provably dead is stale (the gate removes it itself on its next start): noted, never refused.
  A lock that cannot be read refuses (the gate may be mid-write).
* A LIVE PYTEST -- any process whose command line runs pytest (``-m pytest``, ``pytest.exe``, ``py.test``) or an execnet
  worker (xdist's ``exec(eval(sys.stdin.readline()))`` bootstrap), this process and its parent excepted. Each is named with
  its pid and command line, so an ORPHANED xdist worker -- a ``timeout``-killed launcher leaves its workers alive
  (tools/nightly_gate.md) -- can be found and killed. A probe that cannot list processes says so and refuses nothing (the
  lock is still read).

Only the CLI entry points call this (``tools/play.py`` and ``tools/harness/duo.py``'s ``main``). The offline suite drives
Session and Duo directly UNDER pytest, so the guard never sits in ``Session.start``.
"""
from __future__ import annotations

import ctypes
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]

#: a command line that runs pytest, or an execnet (xdist) worker's bootstrap
PYTEST_RX = re.compile(r"(?:-m\s+pytest\b|[\\/\s\"']py\.?test(?:\.exe)?[\s\"']|^py\.?test(?:\.exe)?\b|"
                       r"exec\(eval\(sys\.stdin\.readline\(\)\)\))", re.I)

#: the image names a python test process can run under
_IMAGES = ("python.exe", "pythonw.exe", "py.exe", "pytest.exe", "python3.exe")


def gate_lock_path() -> Path:
    """``<main repo>/.test-gate/lock`` (tools/repo_root.py: the checkout that owns the real ``.git``, from any worktree)."""
    spec = importlib.util.spec_from_file_location("_benchguard_repo_root", TOOLS / "repo_root.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return Path(mod.main_repo_root(TOOLS)) / ".test-gate" / "lock"


def pid_alive(pid: int) -> bool:
    """Windows-safe liveness (nightly_gate.pid_alive's probe). NEVER os.kill(pid, 0) on Windows: that TERMINATES. Off Windows,
    signal 0 is the probe. Can't tell -> True (assume alive: refuse rather than bench under a live gate)."""
    if os.name != "nt":
        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            return False
        except OSError:
            return True
        return True
    try:
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))     # PROCESS_QUERY_LIMITED_INFORMATION
    except (OSError, AttributeError):
        return True
    if h:
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    return ctypes.get_last_error() == 5                                        # ERROR_ACCESS_DENIED: exists, protected


def list_processes() -> list[tuple[int, int, str]] | None:
    """Every python-ish process as (pid, parent pid, command line); None when the probe cannot list them.

    Windows: one CIM query as JSON (tasklist carries no command line, psutil is not a kit dependency, and a command line
    can hold newlines -- `py -c "..."` -- so no line-split format survives). Elsewhere: ``ps``."""
    try:
        if os.name == "nt":
            names = " or ".join(f"Name='{n}'" for n in _IMAGES)
            ps = (f"Get-CimInstance Win32_Process -Filter \"{names}\" | "
                  "Select-Object ProcessId, ParentProcessId, CommandLine | ConvertTo-Json -Compress")
            out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True,
                                 text=True, errors="replace", timeout=30)
        else:
            out = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    if os.name == "nt":
        return parse_cim_json(out.stdout)
    rows = []
    for ln in out.stdout.splitlines():
        parts = ln.split(None, 2)
        if len(parts) < 2:
            continue
        try:
            rows.append((int(parts[0]), int(parts[1]), parts[2].strip() if len(parts) > 2 else ""))
        except ValueError:
            continue
    return rows


def parse_cim_json(text: str) -> list[tuple[int, int, str]] | None:
    """ConvertTo-Json's output (PURE): one object for a single match, a list for several, nothing for none. None when it
    does not parse."""
    text = (text or "").strip()
    if not text:
        return []
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    rows = []
    for o in doc if isinstance(doc, list) else [doc]:
        try:
            rows.append((int(o.get("ProcessId")), int(o.get("ParentProcessId")), str(o.get("CommandLine") or "")))
        except (TypeError, ValueError, AttributeError):
            continue
    return rows


def is_pytest(cmdline: str) -> bool:
    """Whether a command line runs pytest or is an xdist worker (PURE)."""
    return bool(cmdline) and PYTEST_RX.search(" " + cmdline + " ") is not None


def read_lock(lock: Path, alive=pid_alive) -> tuple[str | None, str | None]:
    """The gate lock's verdict (``refuse``, ``note``): (None, None) when absent; a live (or unreadable) holder refuses; a dead
    holder is only noted (stale)."""
    if not lock.exists():
        return None, None
    try:
        holder = json.loads(lock.read_text(encoding="utf-8", errors="replace"))
        pid = int(holder.get("pid", -1))
        started = holder.get("started", "?")
    except (ValueError, OSError, AttributeError):
        return f"the nightly gate's lock {lock} exists and cannot be read (the gate may be writing it)", None
    if pid > 0 and not alive(pid):
        return None, f"a stale gate lock {lock} (pid {pid}, started {started}, not alive) -- ignored"
    return (f"the nightly test gate is running: {lock} (pid {pid}, started {started}). It runs ~04:00-06:10; read "
            f"{lock.parent / 'latest.json'} for its last length"), None


def bench_blockers(*, lock: Path | None = None, procs=list_processes, alive=pid_alive,
                   me: tuple[int, ...] | None = None) -> tuple[list[str], list[str]]:
    """(refusals, notes) for starting a live bench now. ``lock`` / ``procs`` / ``alive`` / ``me`` are the test seams: a test
    pins every one (never the real lock, never the real process table)."""
    refusals, notes = [], []
    try:
        lock = gate_lock_path() if lock is None else Path(lock)
    except Exception as err:                                  # noqa: BLE001 - a git-less checkout still probes pytest
        notes.append(f"the gate lock could not be located ({err})")
        lock = None
    if lock is not None:
        why, note = read_lock(lock, alive)
        if why:
            refusals.append(why)
        if note:
            notes.append(note)
    me = tuple(me) if me is not None else (os.getpid(), os.getppid())
    rows = procs() if procs is not None else None
    if rows is None:
        notes.append("the process probe could not list processes: a live pytest run is unchecked")
    else:
        live = [(pid, cmd) for pid, _ppid, cmd in rows if pid not in me and is_pytest(cmd)]
        if live:
            shown = "; ".join(f"pid {pid}: {cmd[:160]}" for pid, cmd in live[:6])
            refusals.append(f"{len(live)} pytest process(es) are running ({shown}{'; ...' if len(live) > 6 else ''}). Wait for "
                            f"them, or kill an ORPHANED xdist worker (a `timeout`-killed launcher leaves its workers alive)")
    return refusals, notes


def refuse_message(refusals: list[str]) -> str:
    return ("!!! refusing to start a live bench -- NEVER BENCH UNDER A RUNNING TEST SUITE (the s159 law: a loaded machine "
            "swings the frame rate and reds timing legs on a correct engine):\n" + "\n".join(f"  - {r}" for r in refusals))
