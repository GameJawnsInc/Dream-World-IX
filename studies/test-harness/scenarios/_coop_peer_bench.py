"""Shared helpers for the R3 T2 TWO-ROLE BENCHES -- coop_tape_record.py (the desktop as HOST, taped) and coop_cut_hold.py
(the desktop as GUEST, the tape replayed with blackholes). [ff9mapkit netsync R3 T2]

NOT A SCENARIO (no ``run(g)``). Everything that can be pure is, so ``py studies/test-harness/scenarios/_coop_peer_bench.py``
runs the SELF-CHECK below with no game: the INI edit's rows, every log matcher against the archived sitting-A guest log
(.harness-runs/sittingA-20261014/laptop-Memoria.log -- the s117 engine's real output, the matchers' calibration source)
and against hand-built lines whose literal fragments are looked up in the engine's own C# (the shared Memoria clone), the
leg timing windows against sitting A's measured stamps, the tape facts and the leg plans on synthetic tapes. Its verdict
is OK (exit 0), FAIL (1) or PARTIAL (2): the archive is gitignored and the clone per-machine, so where either is missing
its rows are SKIPPED and counted apart -- never read as a pass.

What lives here, and why once:
  * THE INI GUARD (:class:`IniGuard`). The T2 benches need a REAL transport -- `netsync selftest` has none, and
    IsMirroringStory needs a socket (R3-SITTING-A-FIXES.md T2) -- so, unlike every selftest bench, they write the
    install's Memoria.ini [Netsync]: the engine hot-reloads it (NetSyncClient.LoadConfigIfChanged, mtime-gated, polled every
    2 s and at each field load), so the edit lands in the RUNNING game. The guard backs the file up FIRST (the MAIN repo's
    backups/ -- tools/repo_root.main_repo_root, never a worktree's -- and the run dir), edits only the named [Netsync]
    keys the way Memoria.IniFile reads them (case-sensitive section and key, last occurrence wins, so EVERY occurrence is
    rewritten; a value is everything after '=', so no inline comment is ever written), and restores the original BYTES
    (and its mtime) in the scenario's ``finally``, verified by sha256. The install is shared with the owner and every
    worktree: a leaked [Netsync] edit hands their next launch someone else's role.
  * THE PEER PROCESS (:class:`PeerProc`): tools/harness/coop_peer.py as a SUBPROCESS (its own process: a 30 Hz pump in
    the driver's process would jitter under the state polling), started through a two-line launcher that maps Windows'
    CTRL_BREAK to KeyboardInterrupt -- so a stop runs coop_peer's own ``except KeyboardInterrupt`` path (the listener
    closed, the tape flushed and closed, its "tape ...: N record(s)" line) instead of a kill that tears the tape's tail.
    Its ``--log`` tee is read incrementally: every coop-peer line carries a wall-clock ms stamp, so a BLACKHOLE edge is
    the anchor every engine-line window below is measured from.
  * THE LOG MATCHERS (:data:`MATCHERS`): one anchored regex per engine line the legs judge, written from the engine's
    format strings (NetSyncClient.cs, NetSyncDiorama.cs, NetSyncField.cs, NetSyncState.cs, NetSyncBattle.StockMenu.cs) and
    calibrated against the archived s117 log: the S119 RED pair (laptop-Memoria.log 155 + 159) and the five CAL facts
    must match there verbatim, and no s119-s121 GREEN matcher may match anything an s117 engine wrote. The exit ramp
    has TWO lines -- the own-autosave reload and its no-autosave fallback to the title -- and every "no session end"
    check reads both (:func:`session_ends`).
  * THE WINDOWS (:func:`leg_windows`, :func:`in_window`): the engine's clocks -- StaleMs 2000 (both lanes), the s119
    settle 500, the s117 ramp debounce 3000, the s120 grace (SessionGraceMs, 30000), the s56 ghost hold 5000 -- turned into
    "seconds after the blackhole" windows. Memoria.log stamps are whole seconds (truncated), the coop-peer's are ms: a
    window test floors its low edge to the second.
  * THE TAPE FACTS (:func:`tape_facts`): the five facts a replay must find on a tape before its CAL leg can pass -- the
    host on a real field (the pairing), the type-5 story lane (the mirror; with the story MARKER the roam leg reads), a
    published own battle (the boot), its live command phase (LIVE), its terminal end and the host back on its field (the
    end-leave) -- read with coop_peer's own codec and battlewire's end-block reader.
  * THE LEG PLANS (:func:`plan_leg`): each cut_hold leg's blackhole (or stop) in TAPE seconds, from those facts, with
    the reason a tape cannot carry a leg.
  * THE CAL SIDECAR (``<tape>.cal.json``): the CAL leg's verdict, keyed by the tape's sha256 -- every later leg reads it,
    and reads "not reached" until the instrument has passed on that tape.

Knobs (environment): COOP_PEER_PORT (default 49201, the game's RelayUrl port), COOP_TAPE (a tape path), COOP_TAPE_DIR
(where tapes land; default <main repo>/.harness-runs/coop-tapes), COOP_BACKUP_DIR (where the Memoria.ini backups land;
default <main repo>/backups), MEMORIA_SRC (the Memoria clone the self-check reads; default C:\\gd\\FFIX\\Memoria).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                       # studies/test-harness/scenarios -> the worktree root
TOOLS = REPO / "tools"
HARNESS_DIR = TOOLS / "harness"
COOP_PEER = HARNESS_DIR / "coop_peer.py"
SITTING_A = REPO / ".harness-runs" / "sittingA-20261014"

# ======================================================================================== the bench constants
BENCH_FIELD = 250                            # Evil Forest/Trail: sitting A's meeting field (warm: Main_Reinit)
BENCH_SCENE = 67                             # BSC_EF_R007 (one Goblin) -- the scene sitting A fought on 250
BENCH_CODE = "ff9-T2BENCH1"                  # a bench SessionCode ("ff9-" + 8, GenerateSessionCode's shape): never empty,
                                             # so a host never generates one and writes it back into Memoria.ini
DEFAULT_PORT = 49201                         # the game's RelayUrl port (the production bridge's): the peer REPLACES it
MARKER_BYTE = 1121                           # gEventGlobal byte 1121 = bits 8968-8975 (the campaign lane, >= FIRST_SAFE_FLAG)
MARKER_VALUE = 0xA5                          # 1010 0101: a palindrome, so either bit order reads it; a New-Game save holds 0
MARKER_BITS = tuple(MARKER_BYTE * 8 + b for b in range(8) if MARKER_VALUE >> b & 1)

# The engine's clocks (seconds), each by its C# name.
STALE_S = 2.0                                # NetSyncFrames.StaleMs / NetSyncBattle.StaleMs: a lane silent this long is gone
SETTLE_S = 0.5                               # [s119] NetSyncClient.DioramaSettleMs: a hold is counted at this stale age
OLD_RAMP_S = 3.0                             # [s117] ExitRampDebounceMs: the link-loss ramp arms 3 s after the pos lane dies
OLD_HOLD_CAP_S = 8.0                         # [s119] DioramaBlipHoldMs (the s119-alone hold cap)
STALL_CAP_S = 8.0                            # [s120] DioramaStallCapMs: a peer alive for the settle that says nothing
GHOST_GRACE_S = 5.0                          # s56 GhostGraceMs: on a field the reconnecting overlay waits for the ghost hold
GRACE_DEFAULT_S = 30.0                       # [s120] SessionGraceDefaultMs (owner decision)
SLACK_S = 1.0

# The cut_hold legs (COOP_CUT_LEG), in the run order the docstrings give.
LEGS = ("cal", "s119", "s120-battle", "s120-long", "s120-roam", "span", "s121")
LEG_ALIASES = {"s120": "s120-battle", "s120-world": "span", "world": "span", "s120b": "s120-battle",
               "s120l": "s120-long", "s120r": "s120-roam", "calibrate": "cal"}
ROAM_LEAD_S = 15.0                           # a free-roam blackhole starts this long after the replay's first host frame
S119_AT_S, S119_FOR_S = 10.0, 6.0            # the sitting-A row: 6 s, 10 s into the recorded battle (the plan's T2 bench)
S120B_AT_S, S120B_FOR_S = 8.0, 20.0          # the plan's "20 s blackhole mid-battle"
LONG_FOR_S = 40.0                            # the plan's "40 s blackhole"
ROAM_FOR_S = 20.0                            # the plan's "20 s blackhole in free roam"
SPAN_LEAD_S, SPAN_TAIL_S = 4.0, 4.0          # a span cut starts this long before the end block turns terminal, ends after
S121_STOP_S = 25.0                           # the S121 replay stops this long after its first host frame (presses first)
RESUME_MARGIN_S = 6.0                        # tape room a leg needs after its blackhole before the next phase


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip() not in ("", "0")


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def engine_grace(raw) -> tuple:
    """[ff9mapkit netsync R3 s120] a [Netsync] SessionGraceMs value as the ENGINE will read it -> ``(grace_ms, note)``:
    battlewire.parse_session_grace, the twin of NetSyncClient.ParseSessionGrace (quotes trimmed; empty keeps 30000
    quietly, malformed keeps it with a note; outside 5000-40000 -- a 0 too: the grace has no off switch -- clamped, with
    the note the engine logs). A bench WRITES and JUDGES this value, never its raw knob: the engine's outage / give-up
    lines print the clamped grace, so windows built on a raw COOP_GRACE_MS=45000 would read a correct s120 as red."""
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    from harness import battlewire as BW     # noqa: E402 -- tools/ on sys.path (play.py puts it first)
    return BW.parse_session_grace(raw)


# ======================================================================================== small doc readers
def raw(x) -> dict:
    return x.raw if hasattr(x, "raw") else (x or {})


def path(x, dotted: str, default=None):
    """``path(st, "netsync.session.state")`` -- None-safe; an ABSENT key reads ``default`` (never a value)."""
    cur = raw(x)
    for key in dotted.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


_ABSENT = object()


def has(x, dotted: str) -> bool:
    return path(x, dotted, _ABSENT) is not _ABSENT


#: The guest-side capability ladder these benches read, by the KEY each patch added (protocol 5, additive).
STAGE_KEYS = ((121, "netsync.menu_refusal"), (120, "netsync.session"), (119, "netsync.diorama.hold"),
              (117, "netsync.battle.end.follow_msg"))


def engine_stage(x) -> int:
    """The newest of s117/s119/s120/s121 whose key this doc carries (0 = older than s117, or no netsync block). s118 is
    host-side and adds nothing a guest bench reads."""
    for stage, key in STAGE_KEYS:
        if has(x, key):
            return stage
    return 0


def marker_value(x) -> int | None:
    """The story marker byte as the WATCHED bits publish it (``flags``; LSB-first, the palindrome reads either way);
    None when any of the byte's eight bits is not watched/published."""
    flags = raw(x).get("flags") or {}
    val = 0
    for b in range(8):
        bit = flags.get(str(MARKER_BYTE * 8 + b))
        if bit is None:
            return None
        if bit:
            val |= 1 << b
    return val


# ======================================================================================== Memoria.ini (the guard)
INI_SECTION = "Netsync"


def ini_line_kind(line: str):
    """Memoria.IniFile.Init's reading of ONE line (after Trim): ``("section", name)`` | ``("key", key)`` | None (blank,
    a comment, junk). A '[' before any '=' or ';'/'#' opens a section; '=' first makes a key (everything before it,
    TrimEnd); ';' or '#' first makes the line a comment. A '[' with no ']' throws in the engine (the whole config load
    fails) -- read here as ``("bad-section", line)``."""
    s = line.strip()
    for i, ch in enumerate(s):
        if ch in ";#":
            return None
        if ch == "[":
            j = s.find("]", i)
            return ("section", s[i + 1:j]) if j >= 0 else ("bad-section", s)
        if ch == "=":
            return ("key", s[:i].rstrip())
    return None


def ini_read(text: str) -> dict:
    """The (section, key) -> value map the ENGINE would build from ``text``: case-sensitive, the last occurrence wins,
    the value everything after the first '=' (Trim) -- an inline ``; comment`` IS part of the value."""
    out, section = {}, None
    for line in text.splitlines():
        kind = ini_line_kind(line)
        if kind is None:
            continue
        if kind[0] == "section":
            section = kind[1]
        elif kind[0] == "key" and section:
            s = line.strip()
            out[(section, kind[1])] = s[s.index("=") + 1:].strip()
    return out


def ini_autosave_moogle_only(text: str) -> bool:
    """[ff9mapkit netsync R3 T2] [SaveFile] AutoSaveOnlyAtMoogle as Memoria reads it (IniValue.TryParseBoolean: exactly
    "1" is on; the last occurrence wins). ON, a field with no save point never autosaves (EventEngine's noSave), so the
    guest's own Continue slot holds no autosave of the bench field: its exit ramp falls back to the TITLE ('session
    ended, no autosave to resume -> title screen') or resumes an OLDER autosave elsewhere -- an instrument fault, never an
    engine verdict, so a guest leg refuses to run on it."""
    return ini_read(text).get(("SaveFile", "AutoSaveOnlyAtMoogle"), "") == "1"


def ini_edit(text: str, values: dict, section: str = INI_SECTION) -> tuple:
    """Set ``values`` (key -> value, the engine's casing) in every ``[section]`` of ``text``. Every occurrence of a key in
    a matching section is rewritten as ``Key = Value`` (the engine reads the LAST; rewriting all leaves no older value to
    win), each line keeping its own line ending; a key no matching section holds is appended after the last content line
    of the LAST matching section; with no such section one is appended at the end. -> (new text, [change notes])."""
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    out = list(lines)
    want = {str(k): str(v) for k, v in values.items()}
    found: set = set()
    changes: list = []
    cur = None
    last_content = None                          # the last content line of the LAST matching section
    for i, rawline in enumerate(lines):
        body = rawline.rstrip("\r\n")
        ending = rawline[len(body):]
        kind = ini_line_kind(body)
        if kind is not None and kind[0] == "section":
            cur = kind[1]
            if cur == section:
                last_content = i
            continue
        if cur != section:
            continue
        if body.strip():
            last_content = i
        if kind is not None and kind[0] == "key" and kind[1] in want:
            key = kind[1]
            new = f"{key} = {want[key]}"
            if body != new:
                changes.append(f"{body.strip()!r} -> {new!r}")
            out[i] = new + ending
            found.add(key)
    missing = [k for k in want if k not in found]
    if missing:
        add = "".join(f"{k} = {want[k]}{nl}" for k in missing)
        changes.extend(f"+ {k} = {want[k]}" for k in missing)
        if last_content is None:
            head = "".join(out)
            sep = "" if not head or head.endswith(("\n", "\r")) else nl
            out = [head + sep + (nl if head.strip() else "") + f"[{section}]{nl}" + add]
        else:
            row = out[last_content]
            if not row.endswith(("\n", "\r")):
                out[last_content] = row + nl
            out.insert(last_content + 1, add)
    return "".join(out), changes


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_atomic(target: Path, data: bytes, *, tries: int = 25, wait: float = 0.1) -> None:
    """Write ``data`` over ``target`` through a sibling temp + os.replace, retried: the engine opens Memoria.ini (share-read)
    for a moment whenever its mtime changes, and Windows refuses a replace over an open file."""
    tmp = target.with_name(target.name + ".t2-tmp")
    last = None
    for _ in range(tries):
        try:
            tmp.write_bytes(data)
            os.replace(tmp, target)
            return
        except OSError as err:
            last = err
            time.sleep(wait)
    try:
        tmp.unlink()
    except OSError:
        pass
    raise OSError(f"could not write {target} after {tries} tries ({last})")


def main_repo() -> Path:
    """The MAIN repo root (tools/repo_root.main_repo_root: the parent of git's common dir) -- where backups and tapes live,
    so a cleaned worktree never takes them along. Falls back to this checkout."""
    try:
        if str(TOOLS) not in sys.path:
            sys.path.insert(0, str(TOOLS))
        from repo_root import main_repo_root
        return Path(main_repo_root(start=TOOLS, fallback=REPO))
    except Exception:                        # noqa: BLE001 -- a gitless machine keeps the checkout
        return REPO


def backup_dir() -> Path:
    env = os.environ.get("COOP_BACKUP_DIR", "").strip()
    return Path(env) if env else main_repo() / "backups"


class IniGuard:
    """Back up Memoria.ini, set ``values`` in its [Netsync] section, restore the original bytes in ``restore``.

    ``apply`` never edits before both backups exist; ``restore`` never raises (it answers ``(ok, detail)``; a failed
    restore names the backup to copy back by hand). Also restores the original mtime (atime too), so the owner's file is
    the file it was -- the engine still sees an mtime CHANGE (against the edit's) and re-reads it, which is the point:
    the running game drops the bench role at once."""

    def __init__(self, ini: Path, values: dict, *, label: str, run_dir: Path | None = None,
                 backup_root: Path | None = None):
        self.ini = Path(ini)
        self.values = dict(values)
        self.label = re.sub(r"[^A-Za-z0-9_.-]", "_", label)
        self.run_dir = Path(run_dir) if run_dir else None
        self.backup_root = Path(backup_root) if backup_root else backup_dir()
        self.original = None                 # bytes, or None = there was no file
        self.stat = None
        self.edited = None
        self.backups: list = []
        self.changes: list = []
        self.applied = False
        self.restored = None                 # (ok, detail) once restore ran

    def apply(self) -> str:
        """Back up, edit, verify the engine-view read-back. Raises OSError/RuntimeError on any failure (nothing edited
        then, or the original already put back by the caller's ``restore``)."""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        if self.ini.exists():
            self.original = self.ini.read_bytes()
            st = self.ini.stat()
            self.stat = (st.st_atime_ns, st.st_mtime_ns)
            for d in [self.backup_root] + ([self.run_dir] if self.run_dir else []):
                d.mkdir(parents=True, exist_ok=True)
                dest = d / f"{self.ini.name}.pre-{self.label}.{stamp}"
                dest.write_bytes(self.original)
                if dest.read_bytes() != self.original:
                    raise OSError(f"the backup {dest} does not read back byte-exact")
                self.backups.append(dest)
        data = self.original or b""
        bom = b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b""
        text = data[len(bom):].decode("utf-8", "surrogateescape")
        new_text, self.changes = ini_edit(text, self.values)
        self.edited = bom + new_text.encode("utf-8", "surrogateescape")
        view = ini_read(new_text)
        bad = {k: view.get((INI_SECTION, k)) for k, v in self.values.items() if view.get((INI_SECTION, k)) != str(v)}
        if bad:
            raise RuntimeError(f"the edited [Netsync] would not read back as written: {bad}")
        self.applied = True                  # from here on restore() owes the original back
        _write_atomic(self.ini, self.edited)
        if self.ini.read_bytes() != self.edited:
            raise OSError(f"{self.ini} does not read back as the edit")
        return (f"{self.ini} [Netsync] set {self.values} ({'; '.join(self.changes) or 'already so'}); backups: "
                + (", ".join(str(b) for b in self.backups) or "none (there was no file)"))

    def restore(self) -> tuple:
        if not self.applied:
            self.restored = (True, "nothing was edited")
            return self.restored
        notes = []
        try:
            now = self.ini.read_bytes() if self.ini.exists() else None
            if now is not None and now != self.edited:
                notes.append("the file changed under the bench (the engine or a human wrote it) -- the original is "
                             "restored over that")
            if self.original is None:
                if self.ini.exists():
                    self.ini.unlink()
                ok = not self.ini.exists()
                detail = "removed the file the bench created" if ok else "could not remove the file the bench created"
            else:
                _write_atomic(self.ini, self.original)
                if self.stat is not None:
                    try:
                        os.utime(self.ini, ns=self.stat)
                    except OSError as err:
                        notes.append(f"mtime not restored ({err})")
                back = self.ini.read_bytes()
                ok = back == self.original
                detail = (f"restored byte-exact (sha256 {_sha(back)[:16]}, {len(back)} B)" if ok else
                          f"RESTORE MISMATCH: sha256 {_sha(back)[:16]} != {_sha(self.original)[:16]}")
        except OSError as err:
            ok, detail = False, f"RESTORE FAILED: {err}"
        if not ok and self.backups:
            detail += f" -- copy {self.backups[0]} back over {self.ini} by hand"
        self.restored = (ok, "; ".join([detail] + notes))
        self.applied = not ok
        return self.restored


def port_free(port: int, host: str = "127.0.0.1") -> tuple:
    """(free, why): can this port be bound EXCLUSIVELY right now (what coop_peer's Listener does)?"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((host, port))
        return True, ""
    except OSError as err:
        return False, (f"{host}:{port} is taken ({err}) -- the production bridge (`ff9mapkit coop host/join/bridge`) or "
                       f"another coop_peer is listening there; stop it first (this bench peer REPLACES the bridge)")
    finally:
        sock.close()


# ======================================================================================== the peer process
_PEER_LINE = re.compile(r"^\[coop-peer (\d\d):(\d\d):(\d\d)\.(\d{3})\] (.*)$")
_LAUNCH = ("import os, runpy, signal, sys\n"
           "if hasattr(signal, 'SIGBREAK'):\n"
           "    signal.signal(signal.SIGBREAK, signal.default_int_handler)\n"
           "script = sys.argv[1]\n"
           "sys.path.insert(0, os.path.dirname(script))\n"
           "sys.argv = sys.argv[1:]\n"
           "runpy.run_path(script, run_name='__main__')\n")


def parse_peer_line(line: str, day: _dt.date, after: _dt.datetime | None = None):
    """``[coop-peer HH:MM:SS.mmm] msg`` -> (datetime, msg) on ``day`` (the next day when it reads >1 h before
    ``after``: a run across midnight); None for any other line."""
    m = _PEER_LINE.match(line.rstrip("\r\n"))
    if not m:
        return None
    h, mi, s, ms = (int(v) for v in m.groups()[:4])
    t = _dt.datetime.combine(day, _dt.time(h, mi, s, ms * 1000))
    if after is not None and t < after - _dt.timedelta(hours=1):
        t += _dt.timedelta(days=1)
    return t, m.group(5)


class PeerProc:
    """One coop_peer mode as a subprocess, its ``--log`` tee read incrementally (``lines``)."""

    def __init__(self, mode: str, args, *, log_path: Path, out_path: Path, python: str | None = None):
        self.mode = mode
        self.args = [str(a) for a in args]
        self.log_path = Path(log_path)
        self.out_path = Path(out_path)
        self.python = python or sys.executable
        self.proc = None
        self.started = None
        self._out = None
        self._off = 0
        self._partial = ""
        self._lines: list = []
        self.how_ended = None

    @property
    def argv(self) -> list:
        return [self.python, "-u", "-c", _LAUNCH, str(COOP_PEER), self.mode, *self.args, "--log", str(self.log_path)]

    def command_text(self) -> str:
        return "py tools/harness/coop_peer.py " + " ".join([self.mode, *self.args])

    def start(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        self.started = _dt.datetime.now()
        self._out = open(self.out_path, "ab")
        self.proc = subprocess.Popen(self.argv, cwd=str(REPO), stdout=self._out, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags)

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def lines(self) -> list:
        """Every coop-peer line so far: ``[(datetime, msg)]``."""
        try:
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._off)
                chunk = f.read()
                self._off = f.tell()
        except OSError:
            return self._lines
        text = self._partial + chunk
        parts = text.split("\n")
        self._partial = parts.pop()
        day = (self.started or _dt.datetime.now()).date()
        for ln in parts:
            got = parse_peer_line(ln, day, self.started)
            if got is not None:
                self._lines.append(got)
        return self._lines

    def find(self, pattern, *, after: _dt.datetime | None = None) -> list:
        rx = re.compile(pattern) if isinstance(pattern, str) else pattern
        out = []
        for t, msg in self.lines():
            if after is not None and t < after:
                continue
            m = rx.search(msg)
            if m:
                out.append((t, msg, m))
        return out

    def first(self, pattern, *, after: _dt.datetime | None = None):
        found = self.find(pattern, after=after)
        return found[0] if found else None

    def wait_for(self, pattern, timeout: float, *, after: _dt.datetime | None = None, poll: float = 0.1, tick=None):
        """The first line matching ``pattern`` (waiting up to ``timeout``), or None -- also None as soon as the process
        has exited without it. ``tick()`` runs every poll (a caller's sampler)."""
        deadline = time.time() + timeout
        while True:
            hit = self.first(pattern, after=after)
            if hit is not None:
                return hit
            if not self.alive() or time.time() >= deadline:
                return self.first(pattern, after=after)
            if tick is not None:
                tick()
            time.sleep(poll)

    def tail(self, n: int = 6) -> str:
        return " | ".join(m for _, m in self.lines()[-n:])[:900]

    def stop(self, timeout: float = 10.0) -> str:
        """CTRL_BREAK (Windows; SIGINT elsewhere) -> coop_peer's own KeyboardInterrupt path; terminate/kill after
        ``timeout``. Returns how it ended (also kept in ``how_ended``)."""
        if self.proc is None:
            self.how_ended = "never started"
            return self.how_ended
        if self.proc.poll() is not None:
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
                self.how_ended = (f"TERMINATED after {timeout:g} s with no clean stop (code {self.proc.returncode}) -- "
                                  "a tape's tail may be torn (read_tape reports and skips it)")
        try:
            if self._out is not None:
                self._out.close()
        except OSError:
            pass
        self.lines()
        return self.how_ended


# coop_peer's own lines the benches anchor on (tools/harness/coop_peer.py; `[coop-peer HH:MM:SS.mmm] ` stripped)
PEER = {
    "listening": re.compile(r"^listening on ws://127\.0\.0\.1:(\d+)"),
    "error": re.compile(r"^ERROR: (.*)$"),
    "host_connected": re.compile(r"^HOST game connected \(session (.+)\) -- this tool is its guest now$"),
    "host_ended": re.compile(r"^host connection ended: (.*)$"),
    "host_lane_up": re.compile(r"^host battle lane UP: nonce (\d+) map (\d+) pattern (\d+) guest slots (\d+) "
                               r"flags 0x([0-9A-F]{2}) song (\d+)$"),
    "host_lane_stale": re.compile(r"^host battle lane STALE: nonce (\d+)"),
    "host_pos": re.compile(r"^host pos: field (\d+) "),
    "state_up": re.compile(r"^host story-state lane \(type 5\) up, (\d+) B$"),
    "tape_summary": re.compile(r"^tape (.+): (\d+) record\(s\), ([\d.]+) MB$"),
    "guest_connected": re.compile(r"^GUEST game connected \(session (.+)\)"),
    "guest_ended": re.compile(r"^guest connection ended: (.*)$"),
    "replay_start": re.compile(r"^REPLAY start: tape ([\d.]+) s -> now; (\d+) host frame\(s\) up to tape ([\d.]+) s$"),
    "bh_begin": re.compile(r"^BLACKHOLE at tape ([\d.]+) s: the link stays open and the host sends NOTHING for "
                           r"([\d.]+) s"),
    "bh_end": re.compile(r"^BLACKHOLE over at tape ([\d.]+) s: host frames resume \((\d+) dropped so far\)$"),
    "stop_at": re.compile(r"^STOP-AT tape ([\d.]+) s reached: the host sends nothing more$"),
    "replay_done": re.compile(r"^replay done \(([^)]*)\): sent (\d+), dropped in blackholes (\d+), unsent \(no guest "
                              r"attached\) (\d+), max lag ([\d.]+) s$"),
    "tape_nonce": re.compile(r"^tape ([\d.]+): host battle nonce (\d+) \(map (\d+), pattern (\d+)\) on the wire$"),
    "tape_field": re.compile(r"^tape ([\d.]+): host field (.+?) -> (\d+)"),
    "lag": re.compile(r"^replay running ([\d.]+) s late at tape ([\d.]+)"),
}


# ======================================================================================== the engine log
_ENGINE_LINE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2}):(\d{2}) \|(\w)\| (.*)$")


def parse_engine_line(line: str):
    """``dd.MM.yyyy HH:mm:ss |L| msg`` -> (datetime, level, msg); None for a continuation line (an exception's stack)."""
    m = _ENGINE_LINE.match(line.rstrip("\r\n"))
    if not m:
        return None
    d, mo, y, h, mi, s = (int(v) for v in m.groups()[:6])
    return _dt.datetime(y, mo, d, h, mi, s), m.group(7), m.group(8)


class EngineLog:
    """Memoria.log from a byte offset (taken at ``mark``), read incrementally: ``lines()`` -> [(datetime, level, msg)].
    A file that SHRANK (a relaunch truncated it) is re-read from its start."""

    def __init__(self, log_path: Path | None):
        self.path = Path(log_path) if log_path else None
        self._off = 0
        self._partial = b""
        self._lines: list = []
        self.mark()

    def mark(self) -> None:
        self._lines = []
        self._partial = b""
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
                self._off, self._partial = 0, b""
            with open(self.path, "rb") as f:
                f.seek(self._off)
                chunk = f.read()
                self._off = f.tell()
        except OSError:
            return self._lines
        data = self._partial + chunk
        parts = data.split(b"\n")
        self._partial = parts.pop()
        for p in parts:
            got = parse_engine_line(p.decode("utf-8", "replace"))
            if got is not None:
                self._lines.append(got)
        return self._lines


# Every engine line a leg judges, one anchored regex on the MESSAGE (the `dd.MM.yyyy HH:mm:ss |M| ` prefix stripped),
# written from the format strings; FRAGMENTS (below) pins each GREEN one's literal pieces to the engine's C#.
MATCHERS = {
    # --- the transport and the pairing (any engine) ---------------------------------------- NetSyncClient / NetSyncRelay
    "config": re.compile(r"^\[NetSync\] config enabled=(True|False) role=(\S+) field=(-?\d+)(.*?)"
                         r"(?: relay=(\S+) code=(\S*)| peer=(\S+))$"),
    "config_live": re.compile(r"^\[NetSync\] config change applied live"),
    "relay_up": re.compile(r"^\[NetSync\] relay connected (wss?://\S+?)/sess/(\S+)\?role=(host|guest)$"),
    "relay_down": re.compile(r"^\[NetSync\] relay disconnected; retrying"),
    "paired": re.compile(r"^\[NetSync\] paired on the host's field \((\d+)\) -- reloading it once so the state mirror "
                         r"arms$"),
    "armed": re.compile(r"^\[NetSync\] state-mirror ARMED -- this guest's fields now stage the HOST's story$"),
    "ghost": re.compile(r"^\[NetSync\] ghost spawned as (\S+) on field (\d+) \(ui=(\w+)\)$"),
    "map": re.compile(r"^Map: (\d+) \| Scenario counter: (\d+)$"),
    "intro": re.compile(r"^\[NetSync\] battle intro: (SKIPPED|PLAYED|unreadable)"),                          # the host
    # --- the diorama lifecycle (any engine) ------------------------------------------------ NetSyncDiorama / NetSyncClient
    "boot": re.compile(r"^\[NetSync\] diorama BOOT scene=(\d+) pattern=(\d+) start=(\S+)( rand)? intro=(\S+) "
                       r"swirl=(-?\d+) clamp=(.+)$"),
    "wire_boot": re.compile(r"^\[NetSync\] diorama wire boot stamped nonce=(\d+)$"),
    "live": re.compile(r"^\[NetSync\] diorama LIVE (\d+) ms after the boot \(host battle nonce (-?\d+), booted from "
                       r"(?:wire nonce (\d+)|no wire nonce)\) -- the start-hold report for this battle now reads LIVE$"),
    "serving": re.compile(r"^\[NetSync\] stock menu: the ready mirror is SERVING -- the host's Ready bits open the stock "
                          r"command menu for the guest's slots \(the digit panel only for a stranded slot; logged once per "
                          r"boot\)$"),
    "end_leave": re.compile(r"^\[NetSync\] diorama END: end-leave attempt (\d+), (\d+) ms after the host's (.+) -- "
                            r"Leave\(\) follows$"),
    "finished": re.compile(r"^\[NetSync\] diorama END: leaving a finished fight \((.+?); the host's "),
    "leave": re.compile(r"^\[NetSync\] diorama LEAVE requested -> FieldMap \(mode (\d+)\)$"),
    "torn_down": re.compile(r"^\[NetSync\] diorama torn down -- state restored, isDebug cleared; r9_refused=(\d+)$"),
    "watcher_settled": re.compile(r"^\[NetSync\] diorama watcher-leave settled \(nonce (-?\d+)\) -- the same fight won't "
                                  r"re-boot on reconnect$"),
    "leave_noted": re.compile(r"^\[NetSync\] diorama leave noted \(nonce (-?\d+)\) -- the watcher won't re-boot this "
                              r"battle$"),
    "return": re.compile(r"^\[NetSync\] diorama RETURN \((warm|cold|reinit-missing)\) -> field (\d+) "),
    "ramp": re.compile(r"^\[NetSync\] session ended -> reloading own autosave \(Continue\)$"),               # NetSyncState
    # [ff9mapkit netsync R3 T2] the SAME exit ramp's other branch (ExitMirrorToOwnSave's Autoload failed: no autosave to
    # resume): the session ended all the same, so every "no session end" check reads it too (session_ends), and a run
    # that logs it is the INSTRUMENT's fault (the guest had no own autosave on the bench field -- T2-SAVE)
    "ramp_failed": re.compile(r"^\[NetSync\] session ended, no autosave to resume -> title screen$"),       # NetSyncState
    # --- [ff9mapkit netsync R3 s119] the diorama hold on the peer ---------------------------------------- NetSyncClient
    "hold_cut": re.compile(r"^\[NetSync\] diorama: peer silent mid-battle -- holding the scene frozen at its last applied "
                           r"state \(nonce (-?\d+); the battle lane and the peer's position lane both silent, stale (\d+) "
                           r"ms: a cut; up to (\d+)s\) rather than leaving; holds=(\d+)$"),
    "hold_stall": re.compile(r"^\[NetSync\] diorama: the host's battle lane stalled mid-battle with the peer alive on field "
                             r"(-?\d+) \(its position lane still flowing: a host stall, not a cut\) -- holding the scene "
                             r"frozen at its last applied state \(nonce (-?\d+); stale (\d+) ms; up to (\d+)s\) rather than "
                             r"leaving; holds=(\d+)$"),
    "hold_resume": re.compile(r"^\[NetSync\] diorama: the host's battle lane is back on the same fight \(nonce (-?\d+)\) "
                              r"after a (\d+) ms hold -- resuming; resumes=(\d+)$"),
    "hold_cap": re.compile(r"^\[NetSync\] diorama: the host's battle lane is still silent after (\d+)s \(nonce (-?\d+), "
                           r"peer (?:alive on field (-?\d+)|silent)\) -- leaving to the spectate panel$"),
    "hold_stall_cap": re.compile(r"^\[NetSync\] diorama: the host's battle lane is still silent after (\d+)s with the peer "
                                 r"alive on field (-?\d+) \(nonce (-?\d+): its battle lane stalled, or its fight ended "
                                 r"unseen inside a cut\) -- leaving to the spectate panel$"),
    "watcher_why": re.compile(r"^\[NetSync\] diorama watcher: (.+) -- leaving \(nonce (-?\d+)(?:, after a (\d+) ms "
                              r"hold)?; logged once per boot\)$"),
    # --- [ff9mapkit netsync R3 s120] the session grace --------------------------------------------------- NetSyncClient
    "session_out": re.compile(r"^\[NetSync\] session: the host went silent \((the hop is up: a cut or a stall upstream|the "
                              r"link is down)\) -- holding the session for up to (\d+) s, reconnecting(.*); outages=(\d+)$"),
    "session_back": re.compile(r"^\[NetSync\] session: the host is back after (\d+) ms -- inside the (\d+) s grace, the "
                               r"session continues \(([^)]*)\)(.*); resumes=(\d+)$"),
    "session_back_late": re.compile(r"^\[NetSync\] session: the host is back after (\d+) ms -- past the (\d+) s grace: that "
                                    r"session had ended \((.+)\)$"),
    "session_gaveup": re.compile(r"^\[NetSync\] session: the host has been silent for (\d+) ms, past the (\d+) s grace -- "
                                 r"the session ended(.*); gaveup=(\d+)$"),
    # --- [ff9mapkit netsync R3 s121] the audible menu refusal --------------------------------------------- NetSyncField
    "menu_refused": re.compile(r"^\[NetSync\] main menu suppressed \(following guest\) on (field|world map) (-?\d+)$"),
    "menu_fault": re.compile(r"^\[NetSync\] main menu refusal failed \(the menu stays closed\): "),
}

#: The matchers only an s119+/s120+/s121 engine can satisfy -- none may match a line an s117 engine wrote.
GREEN_ONLY = ("hold_cut", "hold_stall", "hold_resume", "hold_stall_cap", "watcher_why", "session_out", "session_back",
              "session_back_late", "session_gaveup", "menu_refused", "menu_fault")

#: Each GREEN matcher's LITERAL pieces as the engine's C# writes them (string literals, byte for byte), by source file
#: under the Memoria clone's Assembly-CSharp/Memoria/Netsync/. The self-check looks every piece up in the source -- an
#: engine edit that rewords a line turns its matcher red here, before a bench reads a wrong verdict.
FRAGMENTS = {
    "hold_cut": ("NetSyncClient.cs", (
        "[NetSync] diorama: peer silent mid-battle -- holding the scene frozen at its last applied state (nonce ",
        "; the battle lane and the peer's position lane both silent, stale ", " ms: a cut; up to ",
        "s) rather than leaving; holds=")),
    "hold_stall": ("NetSyncClient.cs", (
        "[NetSync] diorama: the host's battle lane stalled mid-battle with the peer alive on field ",
        " (its position lane still flowing: a host stall, not a cut) -- holding the scene frozen at its last ",
        "applied state (nonce ", "; stale ", " ms; up to ", "s) rather than leaving; holds=")),
    "hold_resume": ("NetSyncClient.cs", (
        "[NetSync] diorama: the host's battle lane is back on the same fight (nonce ", ") after a ",
        " ms hold -- resuming; resumes=")),
    "hold_cap": ("NetSyncClient.cs", (
        "[NetSync] diorama: the host's battle lane is still silent after ", "s (nonce ", ", peer ", "alive on field ",
        "silent", ") -- leaving to the spectate panel")),
    "hold_stall_cap": ("NetSyncClient.cs", (
        "[NetSync] diorama: the host's battle lane is still silent after ", "s with the peer alive on field ",
        " (nonce ", ": its battle lane stalled, or its fight ended unseen inside a cut) -- leaving to the ",
        "spectate panel")),
    "watcher_why": ("NetSyncClient.cs", (
        "[NetSync] diorama watcher: ", " -- leaving (nonce ", ", after a ", " ms hold", "; logged once per boot)",
        "the host's fight is over (the peer is alive and back on field ", "the hold passed its stall cap")),
    "session_out": ("NetSyncClient.cs", (
        "[NetSync] session: the host went silent (", "the hop is up: a cut or a stall upstream", "the link is down",
        ") -- holding the session for up to ", " s, reconnecting", " (the story mirror stays armed, saving stays off)",
        " (the diorama holds)", "; outages=")),
    "session_back": ("NetSyncClient.cs", (
        "[NetSync] session: the host is back after ", " ms -- inside the ", " s grace, the session continues (",
        "no exit ramp", "; still mirroring", "; resumes=")),
    "session_back_late": ("NetSyncClient.cs", (
        "[NetSync] session: the host is back after ", " ms -- past the ", " s grace: that session had ended (")),
    "session_gaveup": ("NetSyncClient.cs", (
        "[NetSync] session: the host has been silent for ", " ms, past the ", " s grace -- the session ended",
        "; the exit ramp reloads your own autosave once you are free-standing", " (the held diorama leaves first)",
        "; gaveup=")),
    "menu_refused": ("NetSyncField.cs", (
        "\"[NetSync] \" + what + \" suppressed (following guest) on \" + where", "DeclineOnce(\"main menu\")",
        "\"field \" + fld", "\"world map \" + place")),
    "menu_fault": ("NetSyncField.cs", ("[NetSync] main menu refusal failed (the menu stays closed): ",)),
}

#: One hand-built line per GREEN matcher, composed exactly as the C# concatenates it (the variable parts filled in).
GREEN_SAMPLES = {
    "hold_cut": "[NetSync] diorama: peer silent mid-battle -- holding the scene frozen at its last applied state (nonce 3; "
                "the battle lane and the peer's position lane both silent, stale 512 ms: a cut; up to 30s) rather than "
                "leaving; holds=1",
    "hold_stall": "[NetSync] diorama: the host's battle lane stalled mid-battle with the peer alive on field 0 (its position "
                  "lane still flowing: a host stall, not a cut) -- holding the scene frozen at its last applied state "
                  "(nonce 3; stale 640 ms; up to 8s) rather than leaving; holds=2",
    "hold_resume": "[NetSync] diorama: the host's battle lane is back on the same fight (nonce 3) after a 4021 ms hold -- "
                   "resuming; resumes=1",
    "hold_cap": "[NetSync] diorama: the host's battle lane is still silent after 30s (nonce 3, peer silent) -- leaving to "
                "the spectate panel",
    "hold_stall_cap": "[NetSync] diorama: the host's battle lane is still silent after 8s with the peer alive on field 0 "
                      "(nonce 3: its battle lane stalled, or its fight ended unseen inside a cut) -- leaving to the "
                      "spectate panel",
    "watcher_why": "[NetSync] diorama watcher: the host's fight is over (the peer is alive and back on field 250) -- "
                   "leaving (nonce 3, after a 17412 ms hold; logged once per boot)",
    "session_out": "[NetSync] session: the host went silent (the hop is up: a cut or a stall upstream) -- holding the "
                   "session for up to 30 s, reconnecting (the story mirror stays armed, saving stays off) (the diorama "
                   "holds); outages=1",
    "session_back": "[NetSync] session: the host is back after 18012 ms -- inside the 30 s grace, the session continues (no "
                    "exit ramp; still mirroring); the dialogue lock lapsed during it -- lines opened meanwhile were local, "
                    "and the host's story re-applies at the next field load; resumes=1",
    "session_back_late": "[NetSync] session: the host is back after 38020 ms -- past the 30 s grace: that session had "
                         "ended (its exit ramp has run, if it had a mirror to undo)",
    "session_gaveup": "[NetSync] session: the host has been silent for 30016 ms, past the 30 s grace -- the session ended; "
                      "the exit ramp reloads your own autosave once you are free-standing; gaveup=1",
    "menu_refused": "[NetSync] main menu suppressed (following guest) on field 250",
    "menu_fault": "[NetSync] main menu refusal failed (the menu stays closed): System.NullReferenceException",
}


def hits(lines, name: str, *, after: _dt.datetime | None = None, before: _dt.datetime | None = None, pred=None) -> list:
    """[(datetime, msg, match)] of the engine ``lines`` that ``name`` matches, inside [after, before] (whole seconds:
    ``after`` is floored, as the engine stamps are)."""
    lo = floor_s(after) if after is not None else None
    out = []
    for t, _lvl, msg in lines:
        if lo is not None and t < lo:
            continue
        if before is not None and t > before:
            continue
        m = MATCHERS[name].search(msg)
        if m and (pred is None or pred(m)):
            out.append((t, msg, m))
    return out


def session_ends(lines, *, after: _dt.datetime | None = None, before: _dt.datetime | None = None) -> list:
    """[ff9mapkit netsync R3 T2] Every exit-ramp line in [after, before], in log order: the own-autosave reload ("ramp")
    AND its no-autosave fallback to the title ("ramp_failed") -- either one means the session ENDED. A "no session end"
    check reads this, never "ramp" alone (a guest with no autosave would read green there)."""
    return sorted(hits(lines, "ramp", after=after, before=before) + hits(lines, "ramp_failed", after=after, before=before),
                  key=lambda h: h[0])


def short(msg: str, n: int = 150) -> str:
    return msg if len(msg) <= n else msg[:n] + "..."


def show(found, n: int = 2) -> str:
    """A check detail's view of matched engine lines: ``HH:MM:SS msg`` for the first ``n``."""
    return " || ".join(f"{t:%H:%M:%S} {short(m, 140)}" for t, m, _ in found[:n]) or "none"


# ======================================================================================== the windows
def floor_s(t: _dt.datetime) -> _dt.datetime:
    return t.replace(microsecond=0)


def in_window(stamp: _dt.datetime, anchor: _dt.datetime, lo: float, hi: float) -> bool:
    """Whether an ENGINE stamp (whole seconds, truncated) can be a moment in [anchor+lo, anchor+hi]: the true moment T
    satisfies stamp <= T < stamp + 1 s, so T in the window iff floor(anchor+lo) <= stamp <= anchor+hi."""
    a = anchor + _dt.timedelta(seconds=lo)
    b = anchor + _dt.timedelta(seconds=hi)
    return floor_s(a) <= stamp <= b


def at(anchor: _dt.datetime, seconds: float) -> _dt.datetime:
    return anchor + _dt.timedelta(seconds=seconds)


def leg_windows(bh_for: float, grace_s: float = GRACE_DEFAULT_S) -> dict:
    """Each judged moment as (lo, hi) SECONDS AFTER THE BLACKHOLE's start (the coop-peer's 'BLACKHOLE at tape' line),
    from the engine's clocks. The cut silences both lanes at once: the position lane (GetRemote, receipt-based) dies at
    +STALE; the battle lane (seq-keyed, a new seq every SampleMs 150) at +STALE-0.15..+STALE. ``*_ms`` entries are the
    expected millisecond figures the lines print."""
    st, sl = STALE_S, SLACK_S
    return {
        # s117 (the sitting-A pair): stale + the loopback up = over -> LEAVE, the teardown's skip stamp the same tick
        "red_leave": (1.0, st + 2.5),
        # s117: the 3 s link-loss debounce, then the ramp at the next settled tick
        "old_ramp": (st + OLD_RAMP_S - 1.5, st + OLD_RAMP_S + 4.0),
        # s119: counted at the settle (500 ms of stale), logged once
        "hold": (st - 0.5, st + SETTLE_S + 2.0),
        # s119 / s120: the lanes come back with the first resumed frame (a later seq on the same nonce)
        "resume": (bh_for - 0.5, bh_for + 3.0),
        "held_ms": ((bh_for - st - sl) * 1000.0, (bh_for - st + 0.5 + sl) * 1000.0),
        # s120: the outage starts when PEER-ALIVE drops (the pos lane's StaleMs)
        "out": (st - 0.5, st + 2.0),
        "out_ms": ((bh_for - st - sl) * 1000.0, (bh_for - st + sl) * 1000.0),
        # s120: past the grace -- the give-up line, then the ramp once free-standing
        "gaveup": (st + grace_s - 1.0, st + grace_s + 2.5),
        "gaveup_ms": (grace_s * 1000.0, grace_s * 1000.0 + 1500.0),
        "new_ramp": (st + grace_s - 1.0, st + grace_s + 5.0),
        # s120 on a field: the reconnecting overlay shows after the 5 s ghost hold (on a field, PEER-ALIVE off)
        "overlay": (st + GHOST_GRACE_S + 1.0, bh_for - 0.5),
        # s119+ span: the watcher's over-verdict needs the peer alive for the settle after the resume
        "span_leave": (bh_for - 0.5, bh_for + SETTLE_S + 4.0),
    }


# ======================================================================================== the tape
def coop_peer_module():
    """tools/harness/coop_peer.py -- imported as ``harness.coop_peer`` (its codec, its tape reader). Raises ImportError
    with the reason when it cannot load (the kit's netsync_bridge is a dependency)."""
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    from harness import coop_peer as cp      # noqa: E402 -- tools/ on sys.path (play.py puts it first)
    return cp


def battle_detail(payload, cp) -> dict | None:
    """NetSyncBattle.ParseView over one type-1 payload: the head, the unit records (at most 8, as the reader stops), and
    the 0xB5 trailer's end block (battlewire.read_trailer at the reader's position). None under the 12-byte head."""
    head = cp.parse_battle_head(payload)
    if head is None:
        return None
    data = bytes(payload)
    p = cp.BATTLE_HEAD_LEN
    units = []
    for _ in range(min(head["units"], 8)):
        if p + 23 > len(data):
            return dict(head, unit_list=units, end=None, end_why="the unit records overran the frame")
        info = data[p + 1]
        hp, hp_max = struct.unpack_from("<II", data, p + 2)
        n = data[p + 22]
        if p + 24 + n > len(data):
            return dict(head, unit_list=units, end=None, end_why="the unit records overran the frame")
        units.append({"index": data[p], "player": bool(info & 1), "alive": bool(info & 2), "ready": bool(info & 4),
                      "hp": hp, "hp_max": hp_max, "name": data[p + 23:p + 23 + n].decode("utf-8", "replace")})
        p += 24 + n
    end, why, _skipped = cp.BW.read_trailer(data, p)
    return dict(head, unit_list=units, end=end, end_why=why)


def state_sections(payload) -> dict:
    """The type-5 payload's sections (NetSyncState: ``[id u8][len u16 LE][bytes]``+) -> {id: bytes}; a torn tail stops."""
    data = bytes(payload or b"")
    out, p = {}, 0
    while p + 3 <= len(data):
        sid, n = data[p], data[p + 1] | (data[p + 2] << 8)
        if p + 3 + n > len(data):
            break
        out[sid] = data[p + 3:p + 3 + n]
        p += 3 + n
    return out


def tape_facts(records, cp, *, field: int | None = BENCH_FIELD, marker=(MARKER_BYTE, MARKER_VALUE)) -> dict:
    """THE FIVE CALIBRATION FACTS of a host tape -- what a replay needs before its CAL leg can show 'paired', 'state-mirror
    ARMED', 'diorama BOOT', 'diorama LIVE' and the end-leave (each ``fN`` = {ok, why, ...}), plus the anchors the leg
    plans read. ``field`` None accepts any real first field."""
    frames = cp.host_frames(records)
    facts = {"records": len(records), "host_frames": len(frames)}
    if not frames:
        why = "the tape holds no host (dir 0) v14 frame"
        for k in ("f1", "f2", "f3", "f4", "f5"):
            facts[k] = {"ok": False, "why": why}
        facts.update(start=None, end=None, battle=None, battles=0, after_field=None, after_real_t=None, after_span=0.0)
        return facts
    t_first, t_last = frames[0][0].t, frames[-1][0].t
    battles = cp.tape_battles(records)
    b = battles[0] if battles else None
    fields = cp.tape_fields(records)
    facts.update(start=t_first, end=t_last, battles=len(battles), battle=dict(b) if b else None,
                 fields=[(round(t, 2), f) for t, f in fields[:40]])
    # F1 -- the host on a real field before its battle (the guest pairs there: the same-field kick)
    pos = [(r.t, cp.parse_pos_payload(p)) for r, w, p in frames if w == cp.TYPE_POS]
    pos = [(t, d) for t, d in pos if d is not None]
    f0 = pos[0][1]["field"] if pos else None
    t0 = pos[0][0] if pos else None
    pre = (b["start"] - t0) if (b and t0 is not None) else None
    real = f0 is not None and 0 < f0 < 65535
    ok1 = real and (field is None or f0 == field) and pre is not None and pre >= 10.0
    facts["f1"] = {"ok": ok1, "field": f0, "t": t0, "pre_s": pre,
                   "why": ("no host position frame" if f0 is None else
                           f"the host's first field is {f0}, not a real field" if not real else
                           f"the host's first field is {f0}, not {field}" if field is not None and f0 != field else
                           "no battle on the tape" if pre is None else
                           f"only {pre:.1f} s of free roam before the battle (the pairing needs >= 10)" if pre < 10.0 else
                           f"the host on field {f0} from tape {t0:.2f} s, {pre:.1f} s before its battle")}
    # F2 -- the type-5 story lane (the mirror arms from it at the kick's reload) and the marker it carries
    st5 = [(r.t, p) for r, w, p in frames if w == cp.TYPE_STATE]
    story, mval, t5 = None, None, None
    for t, p in st5:
        sec = state_sections(p)
        if 0 in sec:
            story, t5 = sec[0], t
            break
    if story is not None and marker is not None and len(story) > marker[0]:
        mval = story[marker[0]]
    ok2 = story is not None and len(story) == 2048 and t0 is not None and t5 <= t0 + 3.0
    facts["f2"] = {"ok": ok2, "frames": len(st5), "first": t5, "story_len": len(story) if story is not None else None,
                   "marker": mval, "marker_ok": marker is not None and mval == marker[1],
                   "why": ("no type-5 frame with a story section" if story is None else
                           f"the story section is {len(story)} B, not 2048" if len(story) != 2048 else
                           "no host position frame to time it against" if t0 is None else
                           f"the first story frame is at tape {t5:.2f} s, > 3 s after the first position" if not ok2 else
                           f"{len(st5)} type-5 frame(s) from tape {t5:.2f} s; story byte {marker[0]} = "
                           f"0x{mval:02X}" + (" (the bench marker)" if mval == marker[1] else
                                              f" (NOT the marker 0x{marker[1]:02X}: the roam leg's story check is blind)"))}
    # F3 / F4 / F5 -- the first battle, decoded frame by frame
    if b is None:
        for k in ("f3", "f4", "f5"):
            facts[k] = {"ok": False, "why": "no battle (type-1 run) on the tape"}
        facts.update(after_field=None, after_real_t=None, after_span=0.0)
        return facts
    bf = []
    for r, w, p in frames:
        if w == cp.TYPE_BATTLE and b["start"] <= r.t <= b["end"]:
            d = battle_detail(p, cp)
            if d is not None and d["nonce"] == b["nonce"]:
                bf.append((r.t, d))
    first = bf[0][1] if bf else {}
    gated = bool(first.get("flags", 0) & 2)
    facts["f3"] = {"ok": bool(bf) and gated, "nonce": b["nonce"], "map": b["map"], "pattern": first.get("pattern"),
                   "slots": first.get("guest_slots"), "flags": first.get("flags"), "start": b["start"],
                   "why": (f"battle1 nonce {b['nonce']} scene {b['map']} pattern {first.get('pattern')} from tape "
                           f"{b['start']:.2f} s, guest slots {first.get('guest_slots')}, flags 0x{first.get('flags', 0):02X}"
                           + ("" if gated else " -- NO command-phase-gated cap (bit 1): a pre-s100 host; the ready "
                                               "mirror never serves its replay"))}
    t_ready = next((t for t, d in bf if any(u["player"] and u["ready"] for u in d["unit_list"])), None)
    t_term = next((t for t, d in bf if d["end"] is not None and cp.BW.is_terminal(d["end"]["kind"], d["end"]["ui"])),
                  None)
    fight_s = (t_term if t_term is not None else b["end"]) - b["start"]
    advanced = b["seq_last"] != b["seq_first"]
    ok4 = advanced and t_ready is not None and fight_s >= 20.0
    facts["f4"] = {"ok": ok4, "fight_s": round(fight_s, 2), "frames": b["frames"], "seq": (b["seq_first"], b["seq_last"]),
                   "ready_t": t_ready, "t_term": t_term,
                   "why": ("the battle seq never advanced" if not advanced else
                           "no player Ready bit on the wire (the host never reached its command phase)" if t_ready is None
                           else f"only {fight_s:.1f} s of live fight before the end (the s119 leg needs >= 20)"
                           if fight_s < 20.0 else
                           f"{fight_s:.1f} s of live fight (tape {b['start']:.2f}..{(t_term or b['end']):.2f} s), "
                           f"{b['frames']} frame(s), seq {b['seq_first']}..{b['seq_last']}, a player Ready from tape "
                           f"{t_ready:.2f} s")}
    term = next((d["end"] for t, d in bf if t == t_term), None) if t_term is not None else None
    t_hide = next((t for t, d in bf if d["end"] is not None and
                   cp.BW.host_exit_trigger(d["end"]["ui"], d["end"]["res_byte"]) == cp.BW.TRIGGER_RESULT_HIDE), None)
    after = [(t, d["field"]) for t, d in pos if t > b["end"]]
    # where the host went: its first REAL field after the battle (a field load reads 0 for a moment first), else 0 when it
    # stays off-field (the world map) for the rest of the tape; None = no host frames after the battle
    real = [(t, f) for t, f in after if 0 < f < 65535]
    after_field = real[0][1] if real else (0 if after and all(f == 0 for _, f in after) else None)
    t_back = next((t for t, f in after if f0 is not None and f == f0), None)
    after_span = (after[-1][0] - after[0][0]) if after else 0.0
    ok5 = term is not None and t_hide is not None and t_back is not None
    facts["after_field"] = after_field
    facts["after_real_t"] = real[0][0] if real else None
    facts["after_span"] = round(after_span, 2)
    facts["f5"] = {"ok": ok5, "t_term": t_term, "kind": term["kind"] if term else None,
                   "result": term["result"] if term else None, "hide_t": t_hide, "back_t": t_back,
                   "after_field": after_field,
                   "why": ("the end block never read terminal (no victory on the tape)" if term is None else
                           "the host's result screen never reached Hide (no result-hide: the end-leave's trigger)"
                           if t_hide is None else
                           f"after the battle the host reads field {after_field}, never {f0} again" if t_back is None else
                           f"{cp.BW.kind_name(term['kind'])} from tape {t_term:.2f} s (result {term['result']}), "
                           f"result-hide at {t_hide:.2f} s, the host back on field {f0} at {t_back:.2f} s; "
                           f"{after_span:.1f} s of host frames after the battle")}
    return facts


def facts_lines(facts: dict) -> list:
    names = {"f1": "F1 PAIR   (paired on the host's field)", "f2": "F2 MIRROR (state-mirror ARMED)",
             "f3": "F3 BOOT   (diorama BOOT)", "f4": "F4 LIVE   (diorama LIVE)", "f5": "F5 END    (the end-leave)"}
    return [f"{names[k]}: {'OK     ' if facts[k]['ok'] else 'MISSING'} -- {facts[k]['why']}" for k in names]


# ======================================================================================== the leg plans
def canon_leg(name: str) -> str | None:
    n = (name or "cal").strip().lower()
    n = LEG_ALIASES.get(n, n)
    return n if n in LEGS else None


def plan_leg(leg: str, facts: dict, grace_s: float = GRACE_DEFAULT_S, *, world: bool = False) -> dict:
    """One leg's replay plan in TAPE seconds: ``{leg, ok, why, bh: (at, for)|None, stop_at, start, expect}``. ``ok``
    False (with ``why``) = this tape cannot carry the leg. ``world`` = the leg was asked as s120-world (a world-map
    victory required)."""
    plan = {"leg": leg, "ok": False, "why": "", "bh": None, "stop_at": None, "start": facts.get("start"),
            "expect": {}}
    b = facts.get("battle")
    start = facts.get("start")
    if start is None:
        plan["why"] = "the tape holds no host frame"
        return plan
    if leg == "cal":
        plan.update(ok=all(facts[k]["ok"] for k in ("f1", "f2", "f3", "f4", "f5")),
                    why="; ".join(f"{k} {facts[k]['why']}" for k in ("f1", "f2", "f3", "f4", "f5")
                                  if not facts[k]["ok"]) or "the five facts are on the tape")
        return plan
    if leg == "s121":
        stop = start + S121_STOP_S
        if b is not None and stop > b["start"] - 3.0:
            plan["why"] = f"the battle starts at tape {b['start']:.2f} s, before the S121 stop {stop:.2f} s"
            return plan
        ok = facts["f1"]["ok"] and facts["f2"]["ok"]
        plan.update(ok=ok, stop_at=stop, why="" if ok else "the pairing or mirror fact is missing")
        return plan
    if leg in ("s120-long", "s120-roam"):
        dur = LONG_FOR_S if leg == "s120-long" else ROAM_FOR_S
        at_ = start + ROAM_LEAD_S
        roam_end = b["start"] if b else facts["end"]
        room = roam_end - (at_ + dur)
        if leg == "s120-long" and dur <= grace_s + STALE_S + 3.0:
            plan["why"] = f"a {dur:g} s cut does not outlast the {grace_s:g} s grace"
            return plan
        if leg == "s120-roam" and dur >= grace_s:
            plan["why"] = f"a {dur:g} s cut is not inside the {grace_s:g} s grace"
            return plan
        if room < RESUME_MARGIN_S:
            plan["why"] = (f"the free roam ends at tape {roam_end:.2f} s: a {dur:g} s cut at {at_:.2f} s leaves "
                           f"{room:.1f} s (needs {RESUME_MARGIN_S:g}; record with a longer COOP_TAPE_PRE_S)")
            return plan
        need_marker = leg == "s120-roam" and not facts["f2"].get("marker_ok")
        base_ok = facts["f1"]["ok"] and facts["f2"]["ok"]
        plan.update(ok=base_ok and not need_marker, bh=(at_, dur),
                    why=("the tape's story lane lacks the bench marker (re-record with coop_tape_record.py)"
                         if need_marker else "" if base_ok else "the pairing or mirror fact is missing"))
        return plan
    if b is None:
        plan["why"] = "no battle on the tape"
        return plan
    t_term = facts["f4"].get("t_term")
    live_end = t_term if t_term is not None else b["end"]
    if leg == "span":
        if t_term is None:
            plan["why"] = "the battle never reads terminal on the tape (no victory to span)"
            return plan
        at_ = t_term - SPAN_LEAD_S
        after = facts.get("after_field")
        resume = b["end"] + SPAN_TAIL_S
        if after and facts.get("after_real_t") is not None:
            resume = max(resume, facts["after_real_t"] + 2.0)    # the host's field must READ real at the resume
        dur = resume - at_
        if after is None or after == 65535 or (facts.get("end") or 0.0) < resume + 8.0:
            plan["why"] = "the tape ends too soon after the battle (or the host leaves for no field) to span its victory"
            return plan
        if world and after != 0:
            plan["why"] = (f"s120-world needs a WORLD-MAP victory (the host on field 0 after it); this tape's host returns "
                           f"to field {after} (that is the `span` leg: why=host_field). Record a world-map fight by hand "
                           "(coop_tape_record.py's docstring: the hand recording)")
            return plan
        if at_ < b["start"] + 4.0:
            plan["why"] = "the battle's live stretch is too short to cut before its end"
            return plan
        if dur >= grace_s - 2.0:
            plan["why"] = f"the span cut ({dur:.1f} s) does not fit inside the {grace_s:g} s grace"
            return plan
        plan["expect"] = {"why": "stall_cap" if after == 0 else "host_field", "after_field": after}
        plan.update(ok=facts["f3"]["ok"], bh=(at_, dur), why="" if facts["f3"]["ok"] else facts["f3"]["why"])
        return plan
    if leg == "s119":
        at_, dur = b["start"] + S119_AT_S, S119_FOR_S
    elif leg == "s120-battle":
        at_, dur = b["start"] + S120B_AT_S, S120B_FOR_S
    else:
        plan["why"] = f"unknown leg {leg!r}"
        return plan
    if at_ + dur + 3.0 > live_end:
        plan["why"] = (f"the battle's live stretch ends at tape {live_end:.2f} s: a {dur:g} s cut at {at_:.2f} s must "
                       "resume mid-battle (record a longer fight: COOP_TAPE_FIGHT_S)")
        return plan
    if dur >= grace_s:
        plan["why"] = f"a {dur:g} s cut is not inside the {grace_s:g} s grace"
        return plan
    pre_ok = all(facts[k]["ok"] for k in ("f1", "f2", "f3"))
    plan.update(ok=pre_ok, bh=(at_, dur), why="" if pre_ok else "a pairing/mirror/boot fact is missing")
    return plan


def plan_args(plan: dict, *, port: int, code: str) -> list:
    """coop_peer replay-host's arguments for a plan (after the tape path)."""
    args = ["--port", str(port), "--code", code, "--at-end", "hold"]
    if plan.get("bh"):
        at_, dur = plan["bh"]
        args += ["--blackhole-at", f"{at_:.3f}", "--blackhole-for", f"{dur:.3f}"]
    if plan.get("stop_at") is not None:
        args += ["--stop-at", f"{plan['stop_at']:.3f}"]
    return args


# ======================================================================================== tapes on disk + the CAL sidecar
def tape_dir() -> Path:
    """COOP_TAPE_DIR, else <the MAIN repo>/.harness-runs/coop-tapes -- gitignored (/.harness-runs/) and outliving any
    worktree. Tapes are run artifacts (10-20 MB: the 2 KB story snapshot rides every 33 ms tick) that replay one engine
    build's wire, so they never belong in git. An env path is resolved against THIS process's cwd (see latest_tape)."""
    env = os.environ.get("COOP_TAPE_DIR", "").strip()
    return Path(env).expanduser().resolve() if env else main_repo() / ".harness-runs" / "coop-tapes"


def latest_tape() -> Path | None:
    """COOP_TAPE, else the pointer ``latest.json`` in :func:`tape_dir`, else the newest ``*.f9tape`` there.
    [ff9mapkit netsync R3 T2] ABSOLUTE always: the scenario reads the tape from its own cwd, but the coop-peer subprocess
    runs with cwd = the checkout (PeerProc.start), so a relative COOP_TAPE read back fine (T2-TAPE green) and then failed
    in the peer (T2-PEER 'never listened' -- a path fault that read as a port or engine fault)."""
    env = os.environ.get("COOP_TAPE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    d = tape_dir()
    try:
        doc = json.loads((d / "latest.json").read_text(encoding="utf-8"))
        p = Path(doc["tape"])
        if p.exists():
            return p
    except (OSError, ValueError, KeyError, TypeError):
        pass
    tapes = sorted(d.glob("*.f9tape"), key=lambda p: p.stat().st_mtime) if d.is_dir() else []
    return tapes[-1] if tapes else None


def file_sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar(tape: Path) -> Path:
    return Path(str(tape) + ".cal.json")


def read_cal(tape: Path) -> tuple:
    """(ok, why): did the CAL leg pass on THIS tape (sha256-keyed)?"""
    p = sidecar(tape)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        return False, f"no CAL verdict for this tape ({p.name}: {err.__class__.__name__}) -- run COOP_CUT_LEG=cal first"
    try:
        same = doc.get("sha256") == file_sha(tape)
    except OSError as err:
        return False, f"the tape cannot be read ({err})"
    if not same:
        return False, f"{p.name} names another tape (sha256 differs) -- re-run COOP_CUT_LEG=cal"
    if not doc.get("ok"):
        return False, f"the CAL leg FAILED on this tape ({doc.get('when')}): {str(doc.get('detail'))[:300]}"
    return True, f"the CAL leg passed on this tape ({doc.get('when')}, engine s{doc.get('stage')})"


def write_cal(tape: Path, ok: bool, *, stage: int, detail: str, facts: dict | None = None) -> Path:
    p = sidecar(tape)
    doc = {"tape": str(tape), "sha256": file_sha(tape), "ok": bool(ok), "stage": stage, "detail": detail,
           "when": _dt.datetime.now().isoformat(timespec="seconds"),
           "facts": {k: (facts or {}).get(k, {}).get("why") for k in ("f1", "f2", "f3", "f4", "f5")}}
    p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return p


# ======================================================================================== the self-check (no game)
def synthetic_tape(cp, *, pre_s: float = 70.0, fight_s: float = 40.0, post_s: float = 30.0, field: int = BENCH_FIELD,
                   nonce: int = 3, scene: int = BENCH_SCENE) -> list:
    """An in-memory host tape shaped like coop_tape_record.py's (10 Hz, not 30 -- the facts read edges, not rates):
    free roam on ``field`` with the story marker, a battle (fighting, a player Ready, then victory-pending -> victory ->
    the result screen to Hide), the host back on ``field``."""
    R = cp.Record
    recs = []
    story = bytearray(2048)
    story[MARKER_BYTE] = MARKER_VALUE
    state = bytes([0, 0x00, 0x08]) + bytes(story)
    t, seq = 1.0, 0

    def pos(f):
        return cp.build_pos_frame(f, model=1, pos=(100.0, 0.0, -200.0))

    def battle_frame(phase, seq_, result, ui, res, ready):
        head = struct.pack("<HHBBBBBHB", seq_ & 0xFFFF, scene, 2, 0, 0, 0x03, nonce, 7, 2)
        units = b""
        for idx, player, name in ((0, True, b"Zidane"), (4, False, b"Goblin")):
            info = (1 if player else 0) | 2 | (4 if (ready and player) else 0)
            units += (bytes([idx, info]) + struct.pack("<IIIIHH", 100, 100, 10, 10, 0, 100) + bytes([len(name)]) + name
                      + b"\x00")
        block = cp.BW.make_block(phase, 0, result, ui=ui, state=res)
        return cp.build_frame(cp.TYPE_BATTLE, head + units + cp.BW.encode_trailer(block))

    while t < pre_s:
        recs += [R(t, 0, pos(field)), R(t, 0, cp.build_frame(cp.TYPE_STATE, state))]
        t += 0.1
    b0 = t
    while t < b0 + fight_s:
        seq += 1
        recs += [R(t, 0, pos(0)), R(t, 0, battle_frame(4, seq, 0, 0, 0, t > b0 + 3.0))]
        t += 0.1
    for phase, result, ui, res, n in ((5, 0, 0, 0, 10), (6, 1, 0, 0, 20), (6, 1, 1, 0, 30), (6, 1, 1, 7, 5)):
        for _ in range(n):
            seq += 1
            recs += [R(t, 0, pos(0)), R(t, 0, battle_frame(phase, seq, result, ui, res, False))]
            t += 0.1
    t += 0.5
    end = t + post_s
    while t < end:
        recs += [R(t, 0, pos(field)), R(t, 0, cp.build_frame(cp.TYPE_STATE, state))]
        t += 0.1
    return recs


#: [ff9mapkit netsync R3 T2] a self-check row whose source is not on this machine: counted apart, never as a pass. A
#: sentinel, not None -- a row's own expression may BE None (a regex search that missed), and that is a FAIL.
SKIPPED = object()


def _self_rows() -> list:
    rows = []

    def row(ok, what):
        rows.append((None if ok is SKIPPED else bool(ok), what))

    # --- the ini edit
    crlf = ("; head\r\n[Mod]\r\nFolderNames = \"A\"\r\n[Netsync]\r\n; a comment = not a key\r\nEnabled = 0\r\n"
            "Role = host\r\nRole = selftest\r\nenabled = 0\r\n\r\n[Battle]\r\nSpeed = 5\r\n")
    new, _ = ini_edit(crlf, {"Enabled": 1, "Role": "client", "FollowHost": 1})
    view = ini_read(new)
    row(view[("Netsync", "Enabled")] == "1" and view[("Netsync", "Role")] == "client"
        and view[("Netsync", "FollowHost")] == "1", "ini: replaced + appended keys read back as the engine reads them")
    row("\n" not in new.replace("\r\n", ""), "ini: CRLF kept on every line, the inserted ones too")
    row(new.count("Role = client") == 2 and "selftest" not in new and "Role = host" not in new,
        "ini: BOTH Role lines rewritten (the engine reads the last occurrence)")
    row(view.get(("Netsync", "enabled")) == "0" and "enabled = 0" in new, "ini: a differently-cased key is left alone "
        "(case-sensitive, as IniFile)")
    row(new.index("FollowHost = 1") < new.index("[Battle]"), "ini: a missing key lands inside [Netsync]")
    row(view[("Battle", "Speed")] == "5" and view[("Mod", "FolderNames")] == "\"A\"", "ini: other sections untouched")
    row("; a comment = not a key" in new, "ini: a comment holding '=' is no key and stays")
    none, _ = ini_edit("[Mod]\nX = 1", {"Enabled": 1})
    row(ini_read(none).get(("Netsync", "Enabled")) == "1" and none.startswith("[Mod]\nX = 1\n"),
        "ini: no [Netsync] -> appended (after a final line with no newline)")
    two, _ = ini_edit("[Netsync]\nEnabled = 0\n[Other]\nA = 1\n[Netsync]\nRole = host\n", {"Enabled": 1, "Port": 9})
    v2 = ini_read(two)
    row(v2[("Netsync", "Enabled")] == "1" and v2[("Netsync", "Port")] == "9" and two.rstrip().endswith("Port = 9"),
        "ini: two [Netsync] sections -> every occurrence rewritten, a new key after the last one")
    row(ini_read("[Netsync]\nEnabled = 1 ; on\n")[("Netsync", "Enabled")] == "1 ; on",
        "ini: an inline comment IS part of the value for the engine (why none is ever written)")
    row(ini_line_kind("[Netsync") == ("bad-section", "[Netsync"), "ini: a '[' with no ']' is junk (the engine throws)")
    # --- the matchers against the archived s117 guest log (sitting A)
    lap = SITTING_A / "laptop-Memoria.log"
    if lap.exists():
        raw_lines = lap.read_text(encoding="utf-8", errors="replace").splitlines()
        parsed = [(i + 1, parse_engine_line(ln)) for i, ln in enumerate(raw_lines)]
        parsed = [(n, p) for n, p in parsed if p is not None]
        by_no = dict(parsed)

        def on(name):
            return [n for n, p in parsed if MATCHERS[name].search(p[2])]

        row(on("leave") == [79, 129, 155], f"s117 log: 'diorama LEAVE requested' at 79/129/155 (got {on('leave')})")
        row(on("watcher_settled") == [159], f"s117 log: the ONE watcher-leave line is 159 (got {on('watcher_settled')})")
        m159 = MATCHERS["watcher_settled"].search(by_no[159][2])
        row(m159 is not None and m159.group(1) == "3", "s117 log: line 159 names nonce 3")
        row(by_no[155][2] == "[NetSync] diorama LEAVE requested -> FieldMap (mode 1)" and by_no[159][2] ==
            "[NetSync] diorama watcher-leave settled (nonce 3) -- the same fight won't re-boot on reconnect",
            "s117 log: the S119 RED pair, verbatim (155 + 159)")
        row(on("paired") == [33, 175] and on("armed") == [35, 177], f"s117 log: paired {on('paired')} / ARMED "
            f"{on('armed')}")
        row(on("boot") == [40, 89, 139] and on("live") == [48, 97, 147], f"s117 log: BOOT {on('boot')} / LIVE "
            f"{on('live')}")
        row(on("end_leave") == [77, 127] and on("leave_noted") == [83, 133], f"s117 log: end-leave {on('end_leave')} / "
            f"leave noted {on('leave_noted')}")
        row(on("ramp") == [166, 188] and on("serving") == [49, 98, 148] and on("relay_up")[:1] == [31],
            f"s117 log: ramp {on('ramp')} / SERVING {on('serving')} / relay {on('relay_up')[:1]}")
        ends = [ln for ln in raw_lines if "[NetSync] session ended" in ln]
        row(on("ramp_failed") == [] and [t for t, _m, _x in session_ends([p for _n, p in parsed])] == [by_no[166][0],
            by_no[188][0]] and len(ends) == 2, f"s117 log: both session ends are the reload, none the title fallback "
            f"(ramp_failed {on('ramp_failed')}; 'session ended' lines {len(ends)})")
        cfg = MATCHERS["config"].search(by_no[29][2]) if 29 in by_no else None
        row(on("config") == [29] and cfg is not None and cfg.group(2) == "client" and cfg.group(6) == "ff9-0CA62LRC",
            "s117 log: the config line (role=client, the relay code) at 29")
        m162 = MATCHERS["return"].search(by_no[162][2])
        row(m162 is not None and m162.group(1, 2) == ("warm", "250"), "s117 log: the warm RETURN at 162")
        green = {g: on(g) for g in GREEN_ONLY}
        row(not any(green.values()), f"s117 log: no s119-s121 GREEN matcher matches an s117 line ({green})")
        w = leg_windows(6.0)
        for cut in (_dt.datetime(2026, 10, 14, 10, 37, 7, 0), _dt.datetime(2026, 10, 14, 10, 37, 7, 900000)):
            row(in_window(by_no[155][0], cut, *w["red_leave"]) and in_window(by_no[159][0], cut, *w["red_leave"])
                and in_window(by_no[166][0], cut, *w["old_ramp"]),
                f"windows: sitting A's LEAVE + watcher-leave (10:37:09) and ramp (10:37:12) fall in red_leave / old_ramp "
                f"of a cut at {cut.time()}")
    else:
        row(SKIPPED, f"the archived sitting-A log is not in this checkout ({lap}: /.harness-runs/ is gitignored) -- the s117 "
                  "calibration rows did NOT run")
    # --- the GREEN samples, and their literal pieces in the engine's C#
    for name, sample in GREEN_SAMPLES.items():
        row(MATCHERS[name].search(sample), f"green sample matches: {name}")
    fail_line = "[NetSync] session ended, no autosave to resume -> title screen"
    t0 = _dt.datetime(2026, 1, 1, 12, 0, 0)
    both = [(t0, "M", "[NetSync] session ended -> reloading own autosave (Continue)"),
            (_dt.datetime(2026, 1, 1, 12, 0, 5), "M", fail_line)]
    row(MATCHERS["ramp_failed"].search(fail_line) and not MATCHERS["ramp"].search(fail_line)
        and [m for _t, m, _x in session_ends(both)] == [both[0][2], fail_line]
        and session_ends(both, after=_dt.datetime(2026, 1, 1, 12, 0, 1))[0][1] == fail_line,
        "session_ends: the reload AND the no-autosave title fallback both end a session (ramp alone misses the second)")
    src_dir = Path(os.environ.get("MEMORIA_SRC", r"C:\gd\FFIX\Memoria")) / "Assembly-CSharp" / "Memoria" / "Netsync"
    if src_dir.is_dir():
        for name, (fname, frags) in FRAGMENTS.items():
            try:
                text = (src_dir / fname).read_text(encoding="utf-8", errors="replace")
            except OSError as err:
                row(False, f"engine source {fname}: {err}")
                continue
            missing = [f for f in frags if f not in text]
            row(not missing, f"engine source: {name}'s literal pieces are in {fname}" + (f" -- MISSING {missing}"
                                                                                          if missing else ""))
        texts = {f: (src_dir / f).read_text(encoding="utf-8", errors="replace")
                 for f in ("NetSyncDiorama.cs", "NetSyncClient.cs", "NetSyncState.cs") if (src_dir / f).exists()}
        for name, literal in (("leave", "\"[NetSync] diorama LEAVE requested -> FieldMap (mode \""),
                              ("watcher_settled", "\") -- the same fight won't re-boot on reconnect\""),
                              ("ramp", "[NetSync] session ended -> reloading own autosave (Continue)"),
                              ("ramp_failed", "[NetSync] session ended, no autosave to resume -> title screen"),
                              ("paired", "\") -- reloading it once so the state mirror arms\""),
                              ("armed", "[NetSync] state-mirror ARMED -- this guest's fields now stage the HOST's story")):
            row(any(literal in t for t in texts.values()), f"engine source: the {name} line's literal is still there")
    else:
        row(SKIPPED, f"the Memoria clone is not at {src_dir} -- the engine-wording rows did NOT run")
    # --- [ff9mapkit netsync R3 T2] the knobs the engine reads its own way
    g45, g0, gdef, gbad = engine_grace("45000"), engine_grace("0"), engine_grace(""), engine_grace("thirty")
    row(g45[0] == 40000 and "clamped to 40000 ms" in (g45[1] or "") and g0[0] == 5000 and gdef == (30000, None)
        and gbad[0] == 30000 and gbad[1] and engine_grace(" \"20000\" ") == (20000, None),
        f"engine_grace: 45000 -> {g45[0]}, 0 -> {g0[0]}, '' -> {gdef[0]}, 'thirty' -> {gbad[0]} (ParseSessionGrace's clamp)")
    row(ini_autosave_moogle_only("[SaveFile]\r\nAutoSaveOnlyAtMoogle = 1\r\n")
        and not ini_autosave_moogle_only("[SaveFile]\r\nAutoSaveOnlyAtMoogle = 0\r\n")
        and not ini_autosave_moogle_only("[Mod]\r\nX = 1\r\n")
        and not ini_autosave_moogle_only("[SaveFile]\nAutoSaveOnlyAtMoogle = 1\n[SaveFile]\nAutoSaveOnlyAtMoogle = 0\n")
        and not ini_autosave_moogle_only("[SaveFile]\nautosaveonlyatmoogle = 1\n")
        and not ini_autosave_moogle_only("[SaveFile]\nAutoSaveOnlyAtMoogle = true\n"),
        "ini: [SaveFile] AutoSaveOnlyAtMoogle reads on for exactly '1' (TryParseBoolean), the last occurrence, case-sensitive")
    held = os.environ.get("COOP_TAPE")
    try:
        os.environ["COOP_TAPE"] = os.path.join("tapes", "x.f9tape")
        lt = latest_tape()
    finally:
        if held is None:
            os.environ.pop("COOP_TAPE", None)
        else:
            os.environ["COOP_TAPE"] = held
    row(lt is not None and lt.is_absolute() and lt == (Path.cwd() / "tapes" / "x.f9tape").resolve(),
        f"latest_tape: a relative COOP_TAPE is resolved against this cwd before the peer (cwd = the checkout) sees it ({lt})")
    # --- the windows
    w = leg_windows(6.0)
    t = _dt.datetime(2026, 1, 1, 12, 0, 0, 500000)
    row(in_window(_dt.datetime(2026, 1, 1, 12, 0, 2), t, *w["red_leave"]), "windows: a LEAVE stamped +1.5 s is inside")
    row(not in_window(_dt.datetime(2026, 1, 1, 12, 0, 6), t, *w["red_leave"]), "windows: a LEAVE at +5.5 s is not")
    row(in_window(_dt.datetime(2026, 1, 1, 12, 0, 4), t, *w["red_leave"]), "windows: a LEAVE stamped +3.5 s (StaleMs, the "
        "teardown's fade, a 1 s rate-limit left over) is still the sitting-A pair")
    row(in_window(_dt.datetime(2026, 1, 1, 12, 0, 9), t, *w["old_ramp"]) and not in_window(
        _dt.datetime(2026, 1, 1, 12, 0, 2), t, *w["old_ramp"]), "windows: s117's ramp stamped +8.5 s is inside old_ramp; "
        "+1.5 s (before the 3 s debounce could end) is not")
    row(in_window(_dt.datetime(2026, 1, 1, 12, 0, 0), t, 0.2, 1.0), "windows: the low edge floors to the second")
    lw = leg_windows(40.0)
    row(lw["gaveup"][0] > lw["old_ramp"][1], "windows: the s120 give-up can never be read as s117's ramp (40 s cut)")
    rw = leg_windows(20.0)
    row(rw["overlay"][0] < rw["overlay"][1] and rw["resume"][0] > rw["out"][1], "windows: a 20 s roam cut has an overlay "
        "stretch, and its resume comes after its outage line")
    # --- engine_stage / marker
    row(engine_stage({"netsync": {"menu_refusal": {}, "session": {}}}) == 121 and engine_stage(
        {"netsync": {"diorama": {"hold": {}}}}) == 119 and engine_stage({"netsync": {"battle": {"end": {"follow_msg": None}}}})
        == 117 and engine_stage({}) == 0, "engine_stage: the key ladder (a null value is still a key)")
    flags = {str(b): (MARKER_VALUE >> (b - MARKER_BYTE * 8)) & 1 == 1 for b in range(MARKER_BYTE * 8, MARKER_BYTE * 8 + 8)}
    row(marker_value({"flags": flags}) == MARKER_VALUE and marker_value({"flags": {}}) is None
        and len(MARKER_BITS) == 4, "marker: the watched bits read 0xA5; unwatched reads None")
    # --- the tape facts and plans on synthetic tapes
    try:
        cp = coop_peer_module()
    except Exception as err:                 # noqa: BLE001
        row(False, f"coop_peer import: {err}")
        return rows
    good = synthetic_tape(cp)
    f = tape_facts(good, cp)
    row(all(f[k]["ok"] for k in ("f1", "f2", "f3", "f4", "f5")), "facts: a full synthetic tape has all five: "
        + " | ".join(f"{k}:{f[k]['why']}" for k in ("f1", "f2", "f3", "f4", "f5")))
    row(f["f2"]["marker"] == MARKER_VALUE and f["after_field"] == BENCH_FIELD, "facts: the marker and the field after")
    no5 = [r for r in good if not (r.dir == 0 and r.payload[2:3] == bytes([cp.TYPE_STATE]))]
    row(not tape_facts(no5, cp)["f2"]["ok"], "facts: no type-5 -> F2 missing")
    nob = [r for r in good if not (r.dir == 0 and r.payload[2:3] == bytes([cp.TYPE_BATTLE]))]
    fb = tape_facts(nob, cp)
    row(not fb["f3"]["ok"] and not fb["f5"]["ok"] and not fb["f1"]["ok"], "facts: no battle -> F1/F3/F4/F5 missing")
    short_fight = synthetic_tape(cp, fight_s=12.0)
    row(not tape_facts(short_fight, cp)["f4"]["ok"], "facts: a 12 s fight -> F4 missing (the s119 leg needs 20)")
    world = [r if not (r.dir == 0 and r.payload[2:3] == bytes([cp.TYPE_POS]) and r.t > f["battle"]["end"]) else
             cp.Record(r.t, 0, cp.build_pos_frame(0)) for r in good]     # the host stays on the world map (field 0)
    fw = tape_facts(world, cp)
    plans = {leg: plan_leg(leg, f) for leg in LEGS}
    row(all(p["ok"] for p in plans.values()), "plans: every leg fits the synthetic tape: "
        + " | ".join(f"{k}:{p['why'] or 'ok'}" for k, p in plans.items()))
    b = f["battle"]
    row(abs(plans["s119"]["bh"][0] - (b["start"] + 10.0)) < 1e-6 and plans["s119"]["bh"][1] == 6.0,
        "plans: s119 = 6 s at battle+10")
    row(plans["span"]["expect"].get("why") == "host_field" and plan_leg("span", f, world=True)["ok"] is False,
        "plans: a field tape spans as host_field; s120-world refuses it")
    wp = plan_leg("span", fw, world=True)
    row(fw["after_field"] == 0 and wp["ok"] and wp["expect"].get("why") == "stall_cap",
        f"plans: a world-map victory spans as stall_cap ({wp['why'] or 'ok'})")
    bend = f["battle"]["end"]
    gap = [r if not (r.dir == 0 and r.payload[2:3] == bytes([cp.TYPE_POS]) and bend < r.t <= bend + 6.0) else
           cp.Record(r.t, 0, cp.build_pos_frame(0)) for r in good]    # the host's field LOAD reads 0 for 6 s first
    fg = tape_facts(gap, cp)
    gp = plan_leg("span", fg)
    row(fg["after_field"] == BENCH_FIELD and gp["ok"] and gp["expect"].get("why") == "host_field"
        and gp["bh"][0] + gp["bh"][1] >= fg["after_real_t"] + 2.0 and plan_leg("span", fg, world=True)["ok"] is False,
        "plans: a field load reading 0 after the battle is still a FIELD victory, and the cut ends after the host reads "
        f"real again ({fg['after_real_t']}, resume {gp['bh'][0] + gp['bh'][1] if gp.get('bh') else None})")
    row(plan_leg("s120-battle", tape_facts(short_fight, cp))["ok"] is False, "plans: a short fight refuses s120-battle")
    row(plans["s120-long"]["bh"][1] == 40.0 and plans["s120-roam"]["bh"][1] == 20.0 and plans["s121"]["stop_at"]
        == f["start"] + S121_STOP_S, "plans: the 40 s / 20 s roam cuts and the S121 stop")
    args = plan_args(plans["s119"], port=49201, code=BENCH_CODE)
    row(args[:2] == ["--port", "49201"] and "--blackhole-at" in args and "--stop-at" not in args, "plans: replay args")
    row(canon_leg("s120-world") == "span" and canon_leg("") == "cal" and canon_leg("nope") is None, "legs: aliases")
    return rows


def self_check(verbose: bool = True) -> str:
    """-> "OK" | "PARTIAL" | "FAIL". [ff9mapkit netsync R3 T2] PARTIAL = nothing failed but a calibration source was
    missing (the archived sitting-A log is gitignored; the Memoria clone is per-machine) -- its rows did NOT run, so the
    verdict is not a calibrated pass and the exit code says so (2)."""
    try:
        rows = _self_rows()
    except Exception as err:                 # noqa: BLE001 -- a row that throws is a red row, never a pass
        rows = [(False, f"the self-check itself raised {type(err).__name__}: {err}")]
    bad = [w for ok, w in rows if ok is False]
    skipped = [w for ok, w in rows if ok is None]
    verdict = "FAIL" if bad else "PARTIAL" if skipped else "OK"
    if verbose:
        for ok, w in rows:
            print(("SKIP " if ok is None else "ok   " if ok else "FAIL ") + w)
        print(f"_coop_peer_bench self-check: {verdict} ({len(rows) - len(skipped)} rows, {len(bad)} failed"
              + (f"; {len(skipped)} calibration block(s) SKIPPED -- not a calibrated pass)" if skipped else ")"))
    return verdict


if __name__ == "__main__":
    sys.exit({"OK": 0, "FAIL": 1}.get(self_check(), 2))
