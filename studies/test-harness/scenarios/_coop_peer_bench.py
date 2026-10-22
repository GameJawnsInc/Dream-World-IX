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
  * [ff9mapkit netsync s131] THE CUT'S TAIL (:func:`tape_tail`, :func:`tap_tail`) and THE HOLD RULE (:func:`hold_rule`,
    :func:`readopt_reproduced`) -- R3-SITTING-A-FIXES.md "The hold-onset variance: the Pump null RE-ADOPT". The host
    re-sends its sticky type-1 slot every ~33 ms write tick and advances the seq per ~150 ms sample, so the final pre-cut
    seq's last receipt trails its first by 0/33/67/100/133 ms -- set by where the cut lands. A pre-s131 guest re-adopts
    that frozen frame once its seq-keyed freshness runs out whenever the tail outlasts its Updates: the hold opens
    ~(2000 - tail) ms late. So a hold is judged against the SAME run's outage plus THAT cut's tail -- never a nominal
    window (s119's 6 s cut sat 9 ms inside the tail-0 class: its old 3000-5500 window was green by placement luck).
    The tail comes off the tape at ``--blackhole-at`` (a T2 leg) or off the relay tap around a live cut (P5).
  * [ff9mapkit netsync s144] THE WORLD LEGS (coop_world_wait.py's T2 legs): :func:`world_tape_facts` (a host-on-world tape's
    three facts and its b6 verdict, coop_peer.tape_where), :func:`plan_world_leg` (world-rejoin off the field-250 tape,
    world-wait off a world tape), the world tape's own home (:func:`world_tape_dir`, :data:`WORLD_POINTER` -- never the
    default home's latest.json) and :func:`synthetic_world_tape` for the self-check's rows.
  * [ff9mapkit netsync s145] THE WORLD-BATTLE LEG (coop_world_battle.py's T2 leg): :func:`world_battle_tape_facts` (wb1-wb5:
    the pairing, the story, the DWELL, a world-map battle, the stay after it -- coop_peer.tape_battle_where's segments),
    :func:`plan_world_leg` ``world-battle`` (a dwell too short refuses), its own home (:func:`world_battle_tape_dir`,
    :data:`WORLD_BATTLE_POINTER`), :func:`synthetic_world_battle_tape`; and :func:`span_why`, the s120-world span's verdict
    by the guest's stage (stall_cap before s145, host_world from it on a tape whose host says b6).

Knobs (environment): COOP_PEER_PORT (default 49201, the game's RelayUrl port), COOP_TAPE (a tape path), COOP_TAPE_DIR
(where tapes land; default <main repo>/.harness-runs/coop-tapes), COOP_BACKUP_DIR (where the Memoria.ini backups land;
default <main repo>/backups), MEMORIA_SRC (the Memoria clone the self-check reads; default C:\\gd\\FFIX\\Memoria).
"""
from __future__ import annotations

import bisect
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
#: [ff9mapkit netsync s131] the arc's measured runs (gitignored, per machine): the T2 tape every tail was read off (in the
#: MAIN repo's coop-tapes), the no-engine-change confirmation (two T2 legs moved 70 ms on s121) and the live P5 cut
ARC_TAPE_NAME = "20261014-224827-host250-s117.f9tape"
CONFIRM_RUNS = {"s119": REPO / ".harness-runs" / "20261015-074620-confirm-s119",
                "s120-battle": REPO / ".harness-runs" / "20261015-074825-confirm-s120-battle"}
P5_RUN = REPO / ".harness-runs" / "20261015-043026-mi-p5-bridge"

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
#: [ff9mapkit netsync s132] THE BENCH'S grace, WRITTEN explicitly to Memoria.ini: every leg's durations (s120-battle 20 s
#: inside, s120-roam 20 s inside, s120-long 40 s past) were designed around 30 s. s132 moved the ENGINE's default to 40000,
#: which a bench never reads -- so the legs time the same on s131 and s132 (COOP_GRACE_MS still overrides).
BENCH_GRACE_MS = 30000
GRACE_DEFAULT_S = BENCH_GRACE_MS / 1000.0    # [s120] the bench grace in seconds (plan_leg / leg_windows' default)
SLACK_S = 1.0

# The cut_hold legs (COOP_CUT_LEG), in the run order the docstrings give.
LEGS = ("cal", "s119", "readopt", "s120-battle", "s120-long", "s120-roam", "span", "s121")
LEG_ALIASES = {"s120": "s120-battle", "s120-world": "span", "world": "span", "s120b": "s120-battle",
               "s120l": "s120-long", "s120r": "s120-roam", "calibrate": "cal",
               "s131": "readopt", "re-adopt": "readopt"}                 # [ff9mapkit netsync s131]
ROAM_LEAD_S = 15.0                           # a free-roam blackhole starts this long after the replay's first host frame
S119_AT_S, S119_FOR_S = 10.0, 6.0            # the sitting-A row: 6 s, 10 s into the recorded battle (the plan's T2 bench)
S120B_AT_S, S120B_FOR_S = 10.0, 20.0         # the plan's "20 s blackhole mid-battle"; [ff9mapkit netsync s131 cal] was 8.0,
                                             # which RACED the guest's 'diorama LIVE' (~8.0-8.3 s after its boot: run
                                             # 20261015-102824 lost it, S120B-I red); now the nearest re-adopt-class
                                             # placement at or after battle+10 s, like readopt (a deterministic s121 red)
LONG_FOR_S = 40.0                            # the plan's "40 s blackhole"
ROAM_FOR_S = 20.0                            # the plan's "20 s blackhole in free roam"
SPAN_LEAD_S, SPAN_TAIL_S = 4.0, 4.0          # a span cut starts this long before the end block turns terminal, ends after
S121_STOP_S = 25.0                           # the S121 replay stops this long after its first host frame (presses first)
RESUME_MARGIN_S = 6.0                        # tape room a leg needs after its blackhole before the next phase

# [ff9mapkit netsync s131] THE CUT'S TAIL and THE HOLD RULE (R3-SITTING-A-FIXES.md "The hold-onset variance"), in ms.
READOPT_TAIL_MS = 66.0                       # the re-adopt CLASS: a tail of two write ticks re-adopts at any Update rate
                                             # (0 never does; 33 does when the guest's Updates are quick enough: a maybe)
HOLD_RULE_MS = (-40.0, 70.0)                 # post-fix, a mid-fight resume: (hold - outage) in [tail - 40, tail + 70]
LEAVE_RULE_MS = (-55.0, 85.0)                # ...a leave-ended hold (the over-verdict): (hold - settle - outage), a
                                             # TickCount quantum wider (one more stamp in it)
READOPT_WINDOW_MS = 2000.0                   # the phantom live window a pre-s131 re-adopt adds (NetSyncBattle.StaleMs)
READOPT_RED_MS = (-35.0, 50.0)               # pre-s131, tail >= 66: (outage - hold) in [2000 - tail - 35, 2000 - tail + 50]
EXPIRED_MS_SLACK = (100.0, 35.0)             # s131 `peer.expired.ms` = the tail less up to two Updates (30 fps) and a
                                             # TickCount quantum: [tail - 100, tail + 35]
MENU_CLOSES_MAX = 1                          # 'closed all (ready mirror: no live peer battle lane)' per cut: the re-adopt's
                                             # second stale edge shuts the re-served menu again
READOPT_AT_S = S119_AT_S                     # the readopt leg: the s119 cut moved to the nearest tail >= 66 placement at or
READOPT_FOR_S = S119_FOR_S                   # after battle+10 s, the same 6 s long


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
    battlewire.parse_session_grace, the twin of NetSyncClient.ParseSessionGrace (quotes trimmed; empty keeps the engine's
    default quietly -- [ff9mapkit netsync s132] 40000; callers pass :data:`BENCH_GRACE_MS` instead of empty -- malformed
    keeps it with a note; outside 5000-40000 -- a 0 too: the grace has no off switch -- clamped, with the note the engine
    logs). A bench WRITES and JUDGES this value, never its raw knob: the engine's outage / give-up
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
#: [ff9mapkit netsync s131] `netsync.battle.peer.expired`: the guest that refuses the transport's repeats of its expired seq.
PEER_EXPIRED_KEY = "netsync.battle.peer.expired"
STAGE_KEYS = ((131, PEER_EXPIRED_KEY), (121, "netsync.menu_refusal"), (120, "netsync.session"),
              (119, "netsync.diorama.hold"), (117, "netsync.battle.end.follow_msg"))


def engine_stage(x) -> int:
    """The newest of s117/s119/s120/s121/s131 whose key this doc carries (0 = older than s117, or no netsync block). s118
    is host-side and adds nothing a guest bench reads; s122-s130 are group 2's reservation (none captured)."""
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

    def update(self, values: dict) -> str:
        """[ff9mapkit netsync s144 bench] A SECOND edit on top of the applied one (the T2 rejoin leg's code, set on the world map):
        ``values`` merged into the [Netsync] keys, written over the bench's own edit, read back -- the backups and the ORIGINAL
        stay the first apply's, so ``restore`` still puts the owner's file back byte-exact. Raises like ``apply`` (and refuses
        before an apply: there would be no original to restore)."""
        if not self.applied or self.edited is None:
            raise RuntimeError("IniGuard.update before apply: no backup, no original")
        now = self.ini.read_bytes() if self.ini.exists() else b""
        if now != self.edited:
            raise RuntimeError(f"{self.ini} changed under the bench since its edit -- not editing again")
        self.values.update(values)
        bom = b"\xef\xbb\xbf" if now.startswith(b"\xef\xbb\xbf") else b""
        text = now[len(bom):].decode("utf-8", "surrogateescape")
        new_text, changes = ini_edit(text, values)
        view = ini_read(new_text)
        bad = {k: view.get((INI_SECTION, k)) for k, v in values.items() if view.get((INI_SECTION, k)) != str(v)}
        if bad:
            raise RuntimeError(f"the edited [Netsync] would not read back as written: {bad}")
        self.edited = bom + new_text.encode("utf-8", "surrogateescape")
        self.changes += changes
        _write_atomic(self.ini, self.edited)
        if self.ini.read_bytes() != self.edited:
            raise OSError(f"{self.ini} does not read back as the edit")
        return f"{self.ini} [Netsync] updated {values} ({'; '.join(changes) or 'already so'})"

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
    # --- [ff9mapkit netsync s131] the expired seq -------------------------------------------- NetSyncBattle (any engine)
    # the ready mirror's close-all when its lane reads dead (B4 stage 8, every engine since): ONE per cut on s131, TWO on a
    # pre-s131 re-adopt with a guest slot Ready (the first stale frame, then the second stale edge after the phantom)
    "menu_close_nolane": re.compile(r"^\[NetSync\] stock menu: closed all \(ready mirror: no live peer battle lane\) -- "),
    # s131's refused re-adopt, one line per EPISODE (the first 3 of a host battle; NetSyncBattle.NoteRefusedReadopt)
    "readopt_refused": re.compile(r"^\[NetSync\] battle lane: the host's last frame \(nonce (-?\d+), seq (-?\d+)\) ran out "
                                  r"of freshness and the transport served it again -- not re-adopted: a repeat is never "
                                  r"news, the lane stays stale until a new frame \(a fight's end, a cut or a stalled "
                                  r"host\); refused=(\d+)$"),
}

#: The matchers only an s119+/s120+/s121/s131 engine can satisfy -- none may match a line an s117 engine wrote.
GREEN_ONLY = ("hold_cut", "hold_stall", "hold_resume", "hold_stall_cap", "watcher_why", "session_out", "session_back",
              "session_back_late", "session_gaveup", "menu_refused", "menu_fault", "readopt_refused")

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
    # [ff9mapkit netsync s131]
    "readopt_refused": ("NetSyncBattle.cs", (
        "[NetSync] battle lane: the host's last frame (nonce ", ", seq ", ") ran out of ",
        "freshness and the transport served it again -- not re-adopted: a repeat is never news, the lane stays stale ",
        "until a new frame (a fight's end, a cut or a stalled host); refused=")),
    # not GREEN-only (B4 stage 8 wrote it first), pinned all the same: the hold rule counts it per cut
    "menu_close_nolane": ("NetSyncBattle.StockMenu.cs", (
        "\"[NetSync] stock menu: closed all (\" + why + \") -- \"",
        "StockMenuCloseAll(\"ready mirror: \" + (owns ? \"waiting: \" + BenchMenuGateText(gate) : why));",
        "why = \"no live peer battle lane\";")),
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
    "readopt_refused": "[NetSync] battle lane: the host's last frame (nonce 1, seq 63) ran out of freshness and the "
                       "transport served it again -- not re-adopted: a repeat is never news, the lane stays stale until a "
                       "new frame (a fight's end, a cut or a stalled host); refused=1",
    "menu_close_nolane": "[NetSync] stock menu: closed all (ready mirror: no live peer battle lane) -- 1 slot(s) drained",
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
    facts = {"records": len(records), "host_frames": len(frames),
             "rx": battle_receipts(records, cp)}     # [ff9mapkit netsync s131] the battle receipts every cut's tail reads
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
    # [ff9mapkit netsync s145] does the host SAY it is back on the world map after the battle (section 7's b6 on its first state
    # frame after it: an s144+ host)? -- the s120-world span's verdict on an s145 guest (span_why)
    seg = next((sg for sg in cp.tape_battle_where(records)["battles"] if sg["nonce"] == b["nonce"]), None)
    facts["after_b6"] = bool(seg is not None and seg["said_after"] == "world")
    return facts


def facts_lines(facts: dict) -> list:
    names = {"f1": "F1 PAIR   (paired on the host's field)", "f2": "F2 MIRROR (state-mirror ARMED)",
             "f3": "F3 BOOT   (diorama BOOT)", "f4": "F4 LIVE   (diorama LIVE)", "f5": "F5 END    (the end-leave)"}
    return [f"{names[k]}: {'OK     ' if facts[k]['ok'] else 'MISSING'} -- {facts[k]['why']}" for k in names]


# ======================================================================================== the cut's tail + the hold rule
def battle_receipts(records, cp=None) -> list:
    """[ff9mapkit netsync s131] ``[(t, nonce, seq)]`` of every HOST type-1 frame on a tape or relay tap (dir 0, the v14
    codec's head), in receipt order -- what the cut's tail is read off."""
    cp = cp or coop_peer_module()
    out = []
    for rec, wtype, payload in cp.host_frames(records):
        if wtype != cp.TYPE_BATTLE:
            continue
        head = cp.parse_battle_head(payload)
        if head is not None:
            out.append((rec.t, head["nonce"], head["seq"]))
    out.sort(key=lambda r: r[0])             # stable: a tap's two legs stamp under one lock, so this is a no-op there
    return out


def _tail_core(rx, ts, at: float):
    """``(tail_ms, i, j)`` for a cut at ``at``: frame ``i`` = the last receipt with t < at, ``j`` = the FIRST receipt of
    its (nonce, seq) run, walked back while contiguous (a seq number repeats across battles: never a global min) --
    or None when no battle frame precedes ``at``."""
    i = bisect.bisect_left(ts, at) - 1
    if i < 0:
        return None
    key, j = rx[i][1:], i
    while j > 0 and rx[j - 1][1:] == key:
        j -= 1
    return round((ts[i] - ts[j]) * 1000.0, 1), i, j


def tail_at(rx, at: float, *, ts=None):
    """[ff9mapkit netsync s131] THE CUT'S TAIL, in ms, of a replay blackhole at TAPE second ``at`` over the receipts ``rx``
    (:func:`battle_receipts`): the final pre-cut seq's LAST receipt minus its FIRST. The replay drops ``at <= t`` (coop_peer
    Replayer.in_blackhole), so the final pre-cut frame is the last with ``t < at``. None = no live battle lane at the cut
    (no frame before it, or the last one already older than StaleMs: nothing for the guest's freshness to run out on)."""
    ts = ts if ts is not None else [r[0] for r in rx]
    got = _tail_core(rx, ts, at)
    if got is None or at - ts[got[1]] > STALE_S:
        return None
    return got[0]


def tape_tail(records, at: float, cp=None):
    """[ff9mapkit netsync s131] The PURE helper: a T2 tape's records and a ``--blackhole-at`` (tape seconds) -> the cut's
    tail in ms (None: no battle lane at the cut). The hold of THAT cut is judged against it (:func:`hold_rule`)."""
    return tail_at(battle_receipts(records, cp), at)


def tap_tail(records, header: dict, cut_start: _dt.datetime, cut_end: _dt.datetime, cp=None) -> tuple:
    """[ff9mapkit netsync s131] The RELAY-TAP variant (multi-instance P5: a live cut, the host's bridge suspended from
    ``cut_start`` to ``cut_end``, wall clock): ``(tail_ms | None, detail)``. A tap's ``t`` is seconds since its header's
    ``started`` (wall clock, ms; its monotonic zero follows within the open); the cut point is the MIDDLE of the suspend
    -- frames in flight at the suspend land within ms of it and a resumed bridge's backlog after the resume, so no
    clock offset of a few ms moves a frame across it. The relay stamps the host leg's frames at the RELAY, not at the
    guest; the tail is a DIFFERENCE of two receipts one hop apart, so the hop's latency cancels (its jitter does not:
    a few ms on loopback)."""
    try:
        started = _dt.datetime.fromisoformat(str(header.get("started")))
    except (TypeError, ValueError):
        return None, f"the tap header has no usable 'started' ({header.get('started')!r})"
    rx = battle_receipts(records, cp)
    if not rx:
        return None, "the tap holds no host battle frame"
    ts = [r[0] for r in rx]
    c0 = (cut_start - started).total_seconds()
    c1 = (cut_end - started).total_seconds()
    mid = (c0 + c1) / 2.0
    got = _tail_core(rx, ts, mid)
    if got is None:
        return None, f"no host battle frame before the cut (tap {c0:.3f} s)"
    tail, i, j = got
    if c0 - ts[i] > STALE_S:
        return None, (f"the host's battle lane was already silent {c0 - ts[i]:.2f} s before the cut (tap {c0:.3f} s): "
                      "nothing for the guest's freshness to run out on")
    nxt = ts[i + 1] - c1 if i + 1 < len(ts) else None
    return tail, (f"tail {tail:.1f} ms: the final pre-cut seq {rx[i][2]} (nonce {rx[i][1]}) first at tap {ts[j]:.3f} s, "
                  f"last at {ts[i]:.3f} s ({1000.0 * (c0 - ts[i]):+.1f} ms to the suspend at {c0:.3f} s); the next host "
                  "battle frame " + (f"{1000.0 * nxt:+.1f} ms from the resume" if nxt is not None else "never came"))


def tap_tail_file(tap_path, cut_start: _dt.datetime, cut_end: _dt.datetime) -> tuple:
    """:func:`tap_tail` on a tap file (a live relay's tap reads fine: TapeWriter flushes every 0.5 s and read_tape drops a
    torn last record) -> ``(tail_ms | None, detail)``; never raises."""
    try:
        cp = coop_peer_module()
        header, records, torn = cp.read_tape(tap_path)
    except Exception as err:                 # noqa: BLE001 -- the reason is the caller's check detail
        return None, f"the relay tap does not read back ({tap_path}: {err})"
    tail, why = tap_tail(records, header, cut_start, cut_end, cp)
    return tail, why + (f" ({torn} B torn tail skipped)" if torn else "")


def hold_rule(hold_ms, outage_ms, tail_ms, *, leave: bool = False) -> tuple:
    """[ff9mapkit netsync s131] THE HOLD RULE (post-fix): ``(ok, d, (lo, hi))``. A mid-fight resume: d = hold - outage, in
    [tail - 40, tail + 70] -- the hold opens at the battle lane's stale edge (L + StaleMs, L the final seq's FIRST receipt),
    the outage at the position lane's (R + StaleMs, R ~ the LAST receipt), both end at the resume. A leave-ended hold
    (the watcher's over-verdict, ``leave``): d = hold - SETTLE - outage, in [tail - 55, tail + 85]. A pre-s131 re-adopt
    reads d ~ tail - 2000 (:func:`readopt_reproduced`). Any figure None (a line never came) -> not ok."""
    if hold_ms is None or outage_ms is None or tail_ms is None:
        return False, None, None
    d = float(hold_ms) - float(outage_ms) - (SETTLE_S * 1000.0 if leave else 0.0)
    lo, hi = LEAVE_RULE_MS if leave else HOLD_RULE_MS
    win = (tail_ms + lo, tail_ms + hi)
    return win[0] <= d <= win[1], d, win


def readopt_reproduced(hold_ms, outage_ms, tail_ms) -> tuple:
    """[ff9mapkit netsync s131] THE PRE-s131 DEFECT, characterised (a mid-fight resume, tail >= 66): ``(ok, d, (lo, hi))``
    with d = outage - hold in [2000 - tail - 35, 2000 - tail + 50] -- the hold opened at the SECOND stale edge, after the
    phantom 2000 ms of the re-adopted frame. Mutually exclusive with :func:`hold_rule` at any tail >= 66. A tail under
    66 is not the re-adopt class (a tail-0 cut reads d in [-50, +35] on every engine) -> not ok."""
    if hold_ms is None or outage_ms is None or tail_ms is None or tail_ms < READOPT_TAIL_MS:
        return False, None, None
    d = float(outage_ms) - float(hold_ms)
    win = (READOPT_WINDOW_MS - tail_ms + READOPT_RED_MS[0], READOPT_WINDOW_MS - tail_ms + READOPT_RED_MS[1])
    return win[0] <= d <= win[1], d, win


def hold_rule_text(hold_ms, outage_ms, tail_ms, *, leave: bool = False) -> str:
    """A check detail for :func:`hold_rule`: the figures, the window, and what a pre-s131 re-adopt would read."""
    ok, d, win = hold_rule(hold_ms, outage_ms, tail_ms, leave=leave)
    if d is None:
        return (f"hold {hold_ms} ms, outage {outage_ms} ms, tail {tail_ms} ms -- a figure is missing (no resume / "
                "over-verdict line, no 'the host is back after M ms' line (pre-s120), or no battle lane at the cut)")
    settle = f" - {SETTLE_S * 1000.0:.0f} (the settle)" if leave else ""
    return (f"hold {hold_ms} - outage {outage_ms}{settle} = {d:+.0f} ms against tail {tail_ms:.1f} ms: want "
            f"{win[0]:+.0f}..{win[1]:+.0f}{'' if ok else ' -- OUTSIDE'} (a pre-s131 re-adopt reads ~"
            f"{tail_ms - READOPT_WINDOW_MS:+.0f}: the hold opening at the SECOND stale edge)")


# ======================================================================================== the leg plans
def canon_leg(name: str) -> str | None:
    n = (name or "cal").strip().lower()
    n = LEG_ALIASES.get(n, n)
    return n if n in LEGS else None


def readopt_placement(rx, lo: float, hi: float, *, min_tail: float = READOPT_TAIL_MS) -> tuple:
    """[ff9mapkit netsync s131] THE READOPT LEG'S CUT: the nearest placement at or after tape ``lo`` (and no later than
    ``hi``) whose tail (:func:`tail_at`) is >= ``min_tail`` -- scanned off the receipts ``rx``, stretch by stretch (a cut
    anywhere in (t_k, t_k+1] drops the same frames: the replay drops ``at <= t``). -> ``(at | None, why)``: ``at`` is the
    MIDDLE of the first such stretch (clamped to ``lo``; ms-rounded as --blackhole-at is written, then re-read through
    :func:`tail_at`), so the rounding never lands it on an edge."""
    ts = [r[0] for r in rx]
    seen: dict = {}
    k = max(bisect.bisect_left(ts, lo) - 1, 0)
    while k < len(rx):
        a_lo = ts[k]
        a_hi = ts[k + 1] if k + 1 < len(ts) else a_lo + STALE_S
        if a_lo >= hi:
            break
        if a_hi > lo:
            got = _tail_core(rx, ts, a_lo + 1e-9)
            tail = got[0] if got is not None else None
            if tail is not None:
                seen[round(tail)] = seen.get(round(tail), 0) + 1
            if tail is not None and tail >= min_tail:
                at = float(f"{max(lo, (a_lo + a_hi) / 2.0):.3f}")
                if a_lo < at <= min(a_hi, hi) and tail_at(rx, at, ts=ts) == tail:
                    return at, (f"tape {at:.3f} s, the nearest tail >= {min_tail:g} ms placement at or after "
                                f"{lo:.3f} s ({1000.0 * (at - lo):+.0f} ms): tail {tail:.1f} ms, the final pre-cut seq "
                                f"{rx[k][2]} (nonce {rx[k][1]}) last sent at {a_lo:.4f} s")
        k += 1
    census = ", ".join(f"{t} ms x{n}" for t, n in sorted(seen.items())) or "none (no battle frame there)"
    return None, (f"no cut placement in tape {lo:.3f}..{hi:.3f} s has a tail >= {min_tail:g} ms (stretch tails seen: "
                  f"{census}) -- a host that sends each seq once never re-adopts; record a real host's tape "
                  "(coop_tape_record.py)")


def plan_leg(leg: str, facts: dict, grace_s: float = GRACE_DEFAULT_S, *, world: bool = False) -> dict:
    """One leg's replay plan in TAPE seconds: ``{leg, ok, why, bh: (at, for)|None, stop_at, start, expect, tail_ms}``.
    ``ok`` False (with ``why``) = this tape cannot carry the leg. ``world`` = the leg was asked as s120-world (a world-map
    victory required). [ff9mapkit netsync s131] ``tail_ms`` = the cut's tail at its --blackhole-at as written (ms-rounded),
    for every cut of a live battle lane (s119, readopt, s120-battle, span); None otherwise."""
    plan = {"leg": leg, "ok": False, "why": "", "bh": None, "stop_at": None, "start": facts.get("start"),
            "expect": {}, "tail_ms": None}

    def tail_of(at_):
        return tail_at(facts.get("rx") or [], float(f"{at_:.3f}"))
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
        # [ff9mapkit netsync s145] the verdict BY THE GUEST'S STAGE (span_why): s145 reads section 7's b6 as "the host is back" --
        # a world victory whose host says b6 after it leaves at the settle as host_world there; stall_cap before s145
        plan["expect"] = {"why": "stall_cap" if after == 0 else "host_field",
                          "why_s145": ("host_world" if facts.get("after_b6") else "stall_cap") if after == 0 else "host_field",
                          "after_field": after}
        plan.update(ok=facts["f3"]["ok"], bh=(at_, dur), why="" if facts["f3"]["ok"] else facts["f3"]["why"],
                    tail_ms=tail_of(at_))
        return plan
    if leg == "s119":
        at_, dur = b["start"] + S119_AT_S, S119_FOR_S
    elif leg == "s120-battle":
        # [ff9mapkit netsync s131 cal] past the guest's LIVE (S120B_AT_S) and in the re-adopt class (tail >= 66), so
        # neither the instrument nor the s121 red is left to a race or the tail-0 knife edge
        # -- this leg's JOB is the 20 s grace, not the re-adopt (that is readopt's), so a tape with no such placement (a host
        # sending each seq once) falls back to battle+10 s as written, its hold check then a tail-0 maybe on s121
        dur = S120B_FOR_S
        at_, scan = readopt_placement(facts.get("rx") or [], b["start"] + S120B_AT_S, live_end - dur - 3.0)
        if at_ is None:
            at_, scan = b["start"] + S120B_AT_S, f"no re-adopt-class placement ({scan}) -- battle+{S120B_AT_S:g} s as written"
        plan["expect"] = {"placement": scan}
    elif leg == "readopt":
        # [ff9mapkit netsync s131] the s119 cut moved to the nearest re-adopt-class placement (tail >= 66 ms)
        dur = READOPT_FOR_S
        at_, scan = readopt_placement(facts.get("rx") or [], b["start"] + READOPT_AT_S, live_end - dur - 3.0)
        if at_ is None:
            plan["why"] = scan
            return plan
        plan["expect"] = {"placement": scan}
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
    plan.update(ok=pre_ok, bh=(at_, dur), why="" if pre_ok else "a pairing/mirror/boot fact is missing",
                tail_ms=tail_of(at_))
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


# ======================================================================================== [s144] the world legs
# [ff9mapkit netsync s144] coop_world_wait.py's two T2 legs (studies/world-coop/S144-DESIGN.md "The bench"):
#   world-rejoin  the desktop GUEST stands on its own world map (9011) when the EXISTING field-250 host tape starts: an
#                 s144 guest dials from the world HUD (decision 9) and rejoins the host's field through the world's own
#                 field entry (decision 3); an s143 guest never dials off a field and stays on the world map.
#   world-wait    an s144-recorded HOST-ON-WORLD tape (coop_tape_record.py COOP_TAPE_WORLD=1: the host on 6603, then out
#                 on the world map >= WAIT_NEED_S): the guest left on 6603 shows the waiting line (decision 5), walks out
#                 too, is frozen there (decision 1) and shows the same line (decision 7).
#: the host-on-world tape's field (the kit's FARSHORE, FF9CustomMap-world: its door is the proven field -> world exit)
WORLD_TAPE_FIELD = 6603
#: the owner's production bridge port (the game's default RelayUrl): the s144 legs NEVER bind it -- they write their own
#: RelayUrl, so a private port serves (duo.OWNER_PORT's law)
OWNER_PORT = 49201
#: the s144 legs' private bench port (COOP_PEER_PORT overrides; 49201 is refused)
WORLD_PORT = 49231
#: a world tape's pointer in its OWN dir (never the default home's latest.json, which coop_cut_hold's legs read)
WORLD_POINTER = "latest-world.json"
#: world-rejoin: the replay STOPS this long after its first host frame -- the dial, the 1.2 s serial floor, the world exit's
#: fade, the landing and the mirror's line fit with room; the field-250 tape's battle starts ~70 s in (it must not run)
REJOIN_SPAN_S = 45.0
#: ...and the host's first field must hold at least this long before the tape's battle (or its end)
REJOIN_NEED_S = 30.0
#: world-wait: the host's first field at least this long before its world exit (the pairing and the mirror's arm)
WORLD_PAIR_MIN_S = 10.0
#: ...and the host OFF-FIELD this long after it: the line on the field (+ the old-host debounce), the guest's own walk out
#: (calibrate + walk_to + the world's load), the freeze and the line on the world map, all inside it
WAIT_NEED_S = 60.0


def world_tape_dir() -> Path:
    """[ff9mapkit netsync s144] COOP_TAPE_DIR, else <the MAIN repo>/.harness-runs/coop-tapes/world -- a world tape's own home,
    so its pointer (:data:`WORLD_POINTER`) never moves coop_cut_hold's latest.json."""
    env = os.environ.get("COOP_TAPE_DIR", "").strip()
    return Path(env).expanduser().resolve() if env else main_repo() / ".harness-runs" / "coop-tapes" / "world"


def latest_world_tape() -> Path | None:
    """[ff9mapkit netsync s144] COOP_TAPE (absolute, as :func:`latest_tape`), else the world dir's pointer, else its newest
    ``*-world-*.f9tape``."""
    env = os.environ.get("COOP_TAPE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    d = world_tape_dir()
    try:
        p = Path(json.loads((d / WORLD_POINTER).read_text(encoding="utf-8"))["tape"])
        if p.exists():
            return p
    except (OSError, ValueError, KeyError, TypeError):
        pass
    tapes = sorted(d.glob("*-world-*.f9tape"), key=lambda p: p.stat().st_mtime) if d.is_dir() else []
    return tapes[-1] if tapes else None


def world_tape_facts(records, cp, *, field: int = WORLD_TAPE_FIELD, marker=(MARKER_BYTE, MARKER_VALUE)) -> dict:
    """[ff9mapkit netsync s144] THE WORLD TAPE's three facts (each ``wN`` = {ok, why}) and its anchors, off the host frames
    (PURE over the records):
      w1 PAIR   the host's FIRST field is ``field``, held >= WORLD_PAIR_MIN_S before its first off-field frame (the guest
                pairs there: the same-field kick), no battle in that stretch
      w2 STORY  type-5 story frames (2048 B section 0) within 3 s of the first position, the marker in them
      w3 WORLD  the host off-field (the position lane's 0) >= WAIT_NEED_S from that exit, section 7 riding its state frames
    and ``b6`` -- coop_peer.tape_where's verdict: does the host SAY "world map" (an s144 host's b6), or is it an s143-or-older
    host (none: the guest's waiting line is then the old-host fallback, 'host_away')."""
    frames = cp.host_frames(records)
    out = {"records": len(records), "host_frames": len(frames), "start": None, "exit_t": None, "back_t": None,
           "world_s": 0.0, "field": None, "b6": False, "where": None}
    pos = [(r.t, cp.parse_pos_payload(p)) for r, w, p in frames if w == cp.TYPE_POS]
    pos = [(t, d["field"]) for t, d in pos if d is not None]
    if not frames or not pos:
        for k in ("w1", "w2", "w3"):
            out[k] = {"ok": False, "why": "the tape holds no host position frame"}
        return out
    t0, f0 = pos[0]
    t_last = frames[-1][0].t
    out.update(start=t0, field=f0)
    exit_t = next((t for t, f in pos if t > t0 and f == 0), None)
    back_t = next((t for t, f in pos if exit_t is not None and t > exit_t and 0 < f < 65535), None)
    world_s = ((back_t if back_t is not None else t_last) - exit_t) if exit_t is not None else 0.0
    battles = [b for b in cp.tape_battles(records) if exit_t is None or b["start"] < exit_t]
    out.update(exit_t=exit_t, back_t=back_t, world_s=round(world_s, 2))
    field_s = (exit_t - t0) if exit_t is not None else None
    ok1 = f0 == field and field_s is not None and field_s >= WORLD_PAIR_MIN_S and not battles
    out["w1"] = {"ok": ok1, "why": (f"the host's first field is {f0}, not {field}" if f0 != field else
                                    "the host never leaves its field (no off-field position frame)" if exit_t is None else
                                    f"a battle runs on {f0} before the world exit (tape {battles[0]['start']:.2f} s)"
                                    if battles else
                                    f"only {field_s:.1f} s on {f0} before the world exit (the pairing needs "
                                    f">= {WORLD_PAIR_MIN_S:g})" if field_s < WORLD_PAIR_MIN_S else
                                    f"the host on {f0} from tape {t0:.2f} s, out to the world map at {exit_t:.2f} s "
                                    f"({field_s:.1f} s)")}
    story, t5 = None, None
    for r, w, p in frames:
        if w == cp.TYPE_STATE:
            sec = state_sections(p)
            if 0 in sec:
                story, t5 = sec[0], r.t
                break
    mval = story[marker[0]] if story is not None and marker is not None and len(story) > marker[0] else None
    ok2 = story is not None and len(story) == 2048 and t5 <= t0 + 3.0 and mval == (marker or (None, None))[1]
    out["w2"] = {"ok": ok2, "marker": mval, "why": ("no type-5 frame with a story section" if story is None else
                                                    f"the story section is {len(story)} B, not 2048" if len(story) != 2048
                                                    else f"the first story frame is at tape {t5:.2f} s, > 3 s in"
                                                    if t5 > t0 + 3.0 else
                                                    f"story byte {marker[0]} reads {mval!r}, not the marker"
                                                    if not ok2 else
                                                    f"story frames from tape {t5:.2f} s, byte {marker[0]} = 0x{mval:02X}")}
    where = cp.tape_where(records)
    out["where"] = {k: where.get(k) for k in ("frames", "with7", "world", "title", "world_on_field", "off_field",
                                               "off_field_said", "stage", "first_world")}
    out["b6"] = bool(cp.where_ok(where, "world"))
    said = where.get("with7", 0) > 0
    ok3 = exit_t is not None and world_s >= WAIT_NEED_S and said
    out["w3"] = {"ok": ok3, "why": ("no world exit on the tape" if exit_t is None else
                                    f"the host is off-field {world_s:.1f} s, under {WAIT_NEED_S:g} (record with a longer "
                                    "COOP_TAPE_WORLD_S)" if world_s < WAIT_NEED_S else
                                    "no section 7 on the host's state frames (a pre-ring host)" if not said else
                                    f"the host off-field {world_s:.1f} s from tape {exit_t:.2f} s; section 7 on "
                                    f"{where['with7']} frame(s); " + ("b6 rides (an s144 host: 'host_world')" if out["b6"]
                                                                     else "no b6 (an s143-or-older host: 'host_away')"))}
    return out


def plan_world_leg(leg: str, facts: dict) -> dict:
    """[ff9mapkit netsync s144] A world leg's replay plan in TAPE seconds: ``{leg, ok, why, stop_at, field, expect}``.
    ``world-rejoin`` reads :func:`tape_facts` (the field-250 tape): the host's first field real and held >= REJOIN_NEED_S
    before its battle, the story lane (F2), the replay stopped REJOIN_SPAN_S in (before any battle). ``world-wait`` reads
    :func:`world_tape_facts`: w1-w3, the whole tape (the replay holds at its end), ``expect`` the host's b6 (the line the
    guest must show) and its world exit."""
    plan = {"leg": leg, "ok": False, "why": "", "stop_at": None, "field": None, "expect": {}, "bh": None}
    start = facts.get("start")
    if start is None:
        plan["why"] = "the tape holds no host frame"
        return plan
    if leg == "world-rejoin":
        f1, f2 = facts.get("f1") or {}, facts.get("f2") or {}
        fld, t0 = f1.get("field"), f1.get("t")
        b = facts.get("battle")
        end = b["start"] if b else facts.get("end")
        held = (end - t0) if (end is not None and t0 is not None) else None
        real = fld is not None and 0 < fld < 65535
        ok = real and held is not None and held >= REJOIN_NEED_S and bool(f2.get("ok"))
        stop = min(start + REJOIN_SPAN_S, (b["start"] - 5.0) if b else (facts.get("end") or start + REJOIN_SPAN_S))
        plan.update(ok=ok, stop_at=stop, field=fld, expect={"field": fld},
                    why="" if ok else ("the host's first field is not a real field" if not real else
                                       f"the host holds field {fld} only {held or 0:.1f} s before its battle (needs "
                                       f">= {REJOIN_NEED_S:g})" if held is None or held < REJOIN_NEED_S else
                                       f"F2 {f2.get('why')}"))
        return plan
    if leg == "world-wait":
        bad = [f"{k} {facts[k]['why']}" for k in ("w1", "w2", "w3") if not facts.get(k, {}).get("ok")]
        plan.update(ok=not bad, field=facts.get("field"), why="; ".join(bad),
                    expect={"b6": bool(facts.get("b6")), "exit_t": facts.get("exit_t"), "world_s": facts.get("world_s")})
        return plan
    if leg == "world-battle":
        # [ff9mapkit netsync s145] reads :func:`world_battle_tape_facts`: wb1-wb5 (a dwell too short for the guest to pair, walk
        # out and settle refuses: wb3), the whole tape (the replay holds at its end); ``expect`` the world battle's anchors and
        # the guest's admissible over-verdicts (WB_LEAVE_WHYS -- never stall_cap)
        bad = [f"{k} {(facts.get(k) or {}).get('why', 'missing (not a world-battle tape: world_battle_tape_facts)')}"
               for k in ("wb1", "wb2", "wb3", "wb4", "wb5") if not (facts.get(k) or {}).get("ok")]
        b = facts.get("battle") or {}
        plan.update(ok=not bad, field=facts.get("field"), why="; ".join(bad),
                    expect={"b6": bool(facts.get("b6")), "exit_t": facts.get("exit_t"), "dwell_s": facts.get("dwell_s"),
                            "battle_start": b.get("start"), "battle_end": b.get("end"), "t_term": facts.get("t_term"),
                            "nonce": b.get("nonce"), "scene": b.get("map"), "after_s": facts.get("after_s"),
                            "leave_whys": WB_LEAVE_WHYS,
                            # [ff9mapkit netsync s145 bench] the host's entry after the stay (WB-300's rejoin; None = none)
                            "rejoin_field": (facts.get("enter") or {}).get("field"),
                            "enter_t": (facts.get("enter") or {}).get("t")})
        return plan
    plan["why"] = f"unknown world leg {leg!r}"
    return plan


def synthetic_world_tape(cp, *, field_s: float = 25.0, world_s: float = 90.0, field: int = WORLD_TAPE_FIELD,
                         b6: bool = True, back: int | None = None) -> list:
    """[ff9mapkit netsync s144] An in-memory HOST-ON-WORLD tape shaped like coop_tape_record.py's COOP_TAPE_WORLD one (10 Hz):
    the host on ``field`` (section 7: b3 on-field + b1 control) with the story marker, then off-field ``world_s`` -- the
    position lane's 0, section 7 b6 + b4 + b1 (an s144 host on its world HUD) or, ``b6`` False, b4 + b1 alone (an s143
    host) -- and, ``back``, on that field again for 5 s."""
    import harness.battlewire as BW          # noqa: E402 -- tools/ on sys.path (coop_peer_module put it there)
    R = cp.Record
    story = bytearray(2048)
    story[MARKER_BYTE] = MARKER_VALUE

    def state(flags, fld):
        sec0 = bytes([0, 0x00, 0x08]) + bytes(story)                    # section 0: [id][len u16 LE][2048 B]
        return cp.build_frame(cp.TYPE_STATE, BW.append_section(sec0, BW.SECTION_DIALOG,
                                                               BW.dialog_section(0x0144, 7, flags, 0, fld)))

    recs, t = [], 1.0
    on_field = BW.HF_ON_FIELD | BW.HF_CONTROL
    world = (BW.HF_WORLD if b6 else 0) | BW.HF_MENU | BW.HF_CONTROL
    for fld, flags, span in ((field, on_field, field_s), (0, world, world_s)) + (((back, on_field, 5.0),) if back else ()):
        end = t + span
        while t < end:
            recs += [R(t, 0, cp.build_pos_frame(fld, model=1, pos=(900.0, 0.0, -1400.0))), R(t, 0, state(flags, fld))]
            t += 0.1
    return recs


# ======================================================================================== [s145] the world-battle leg
# [ff9mapkit netsync s145] coop_world_battle.py's T2 leg (studies/world-coop/S145-DESIGN.md "The bench"): an s144-or-later HOST tape
# (coop_tape_record.py COOP_TAPE_WORLD_BATTLE=1: the host on 6603, out on the world map, a DWELL, then `battle 67 0 rand` on
# WorldHUD, won, then a stay on the world map). The guest left on 6603 pairs there, walks out too and settles frozen inside the
# dwell, then replays the host's world battle: an s145 guest boots its diorama from WorldHUD (BOOTING then LIVE), leaves on
# `terminal` or `host_world` (never `stall_cap`) and returns warm at its spot, still frozen; an s144 guest stays WorldHUD and
# reports NONE (the digit panel). The tape needs only s144 host features (the world battle verb, b6): it is recorded on the
# deployed s144 host.
#: the host OFF-FIELD at least this long between its world exit and its world battle's first type-1 frame: the guest's line on
#: 6603 (+ the old-host debounce), its own walk out (calibrate + walk_to + the world's load), the freeze, the bench's own setup
#: on the world map (the tile teleport, the camera turn, snapshot A) -- s144's WAIT_NEED_S (60 s) plus its 15 s of setup
WB_DWELL_NEED_S = 75.0
#: ...the battle LIVE at least this long (its first frame to the terminal end): the guest's boot (the swirl, the scene load),
#: its LIVE latch and a served stock menu all inside it
WB_LIVE_NEED_S = 15.0
#: ...and the host back on the world map (b6) at least this long after the battle: the guest's settle, leave, warm return and
#: the post-return witnesses (the place, the camera, the MAP digest, still frozen)
WB_AFTER_NEED_S = 25.0
#: the guest's admissible over-verdicts on a world battle (decision 9: the terminal latch, or the host back on the world map --
#: section 7's b6 -- never the 8 s stall cap)
WB_LEAVE_WHYS = ("terminal", "host_world")
#: a world-battle tape's pointer in its OWN dir (never latest.json, never latest-world.json)
WORLD_BATTLE_POINTER = "latest-world-battle.json"
#: [ff9mapkit netsync s145 bench] THE REJOIN AFTER THE STAY (coop_world_battle.py's WB-300): after its stay on the world map the
#: recorder's host enters the stock Ice Cavern (field 300, its world tile's Confirm -- coop_tape_record COOP_TAPE_WB_ENTER, on by
#: default) and stands there at least this long, so the replayed guest rejoins 300 from the world map (s144's rejoin) after its
#: warm world return -- and the leg can read that no second return is counted there. The only field a world-battle tape may enter
#: after its battle; a tape with no entry still plans (``expect.rejoin_field`` None: the leg's WB-300 cannot run on it)
WB_ENTER_FIELD = 300
WB_ENTER_NEED_S = 8.0


def world_battle_tape_dir() -> Path:
    """[ff9mapkit netsync s145] COOP_TAPE_DIR, else <the MAIN repo>/.harness-runs/coop-tapes/world-battle -- a world-battle tape's
    own home, so its pointer (:data:`WORLD_BATTLE_POINTER`) never moves coop_cut_hold's or the world-wait leg's."""
    env = os.environ.get("COOP_TAPE_DIR", "").strip()
    return Path(env).expanduser().resolve() if env else main_repo() / ".harness-runs" / "coop-tapes" / "world-battle"


def latest_world_battle_tape() -> Path | None:
    """[ff9mapkit netsync s145] COOP_TAPE (absolute), else the world-battle dir's pointer, else its newest
    ``*-world-battle-*.f9tape``."""
    env = os.environ.get("COOP_TAPE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    d = world_battle_tape_dir()
    try:
        p = Path(json.loads((d / WORLD_BATTLE_POINTER).read_text(encoding="utf-8"))["tape"])
        if p.exists():
            return p
    except (OSError, ValueError, KeyError, TypeError):
        pass
    tapes = sorted(d.glob("*-world-battle-*.f9tape"), key=lambda p: p.stat().st_mtime) if d.is_dir() else []
    return tapes[-1] if tapes else None


def world_battle_tape_facts(records, cp, *, field: int = WORLD_TAPE_FIELD, marker=(MARKER_BYTE, MARKER_VALUE)) -> dict:
    """[ff9mapkit netsync s145] THE WORLD-BATTLE TAPE's five facts (each ``wbN`` = {ok, why}) and its anchors (PURE over the
    records):
      wb1 PAIR    world_tape_facts' w1: the host's first field is ``field`` (6603), held >= WORLD_PAIR_MIN_S before its world
                  exit, no battle there
      wb2 STORY   w2: the story lane with the marker
      wb3 DWELL   the host off-field from its exit to its world battle >= WB_DWELL_NEED_S, section 7 riding with b6 (an s144+
                  host on its world HUD) -- the guest pairs, walks out and settles inside it
      wb4 BATTLE  a WORLD-MAP battle (coop_peer.tape_battle_where: b6 before and after it) published as F3 reads it (one nonce,
                  command-phase-gated caps), LIVE >= WB_LIVE_NEED_S with the seq advancing and a player Ready (F4's reads)
      wb5 AFTER   its end terminal and the result screen at Hide, then the host back on the world map (b6) >= WB_AFTER_NEED_S
                  before any field -- [s145 bench] and a field after that stay is only the Ice Cavern (WB_ENTER_FIELD), entered
                  once and stood on >= WB_ENTER_NEED_S (the rejoin coop_world_battle.py's WB-300 reads; no entry at all is fine)
    plus ``exit_t``, ``battle`` (its segment: start / end / nonce / map), ``t_term``, ``dwell_s``, ``after_s`` (the stay: the
    battle's end to the entry, or to the tape's end) and ``enter`` ({field, t, on_s} of the host's entry after the stay; None)."""
    base = world_tape_facts(records, cp, field=field, marker=marker)
    out = {"records": base["records"], "host_frames": base["host_frames"], "start": base["start"], "exit_t": base["exit_t"],
           "field": base["field"], "battle": None, "t_term": None, "dwell_s": None, "after_s": None, "b6": base["b6"],
           "enter": None, "wb1": dict(base["w1"]), "wb2": dict(base["w2"])}
    where = cp.tape_where(records)
    seg = next((b for b in where.get("battles") or [] if b["world"]), None)
    facts = tape_facts(records, cp, field=field, marker=marker) if base["start"] is not None else None
    exit_t = base["exit_t"]
    if seg is None or exit_t is None or facts is None:
        why = ("no world exit on the tape" if exit_t is None else
               f"no world-map battle on the tape (battles: {[(b['said_before'], b['said_after']) for b in where.get('battles') or []]})")
        for k in ("wb3", "wb4", "wb5"):
            out[k] = {"ok": False, "why": why}
        return out
    out["battle"] = {k: seg[k] for k in ("n", "nonce", "map", "start", "end")}
    dwell = seg["start"] - exit_t
    out["dwell_s"] = round(dwell, 2)
    first_said = (facts.get("battle") or {}).get("nonce") == seg["nonce"]
    ok3 = dwell >= WB_DWELL_NEED_S and base["b6"]
    out["wb3"] = {"ok": ok3, "why": (f"the host off-field only {dwell:.1f} s before its world battle (the guest's pairing, walk "
                                     f"out and setup need >= {WB_DWELL_NEED_S:g}: record with a longer COOP_TAPE_WB_DWELL_S)"
                                     if dwell < WB_DWELL_NEED_S else
                                     "no b6 on the host's state frames (an s143-or-older host: no world battle verb either)"
                                     if not base["b6"] else
                                     f"the host on the world map {dwell:.1f} s from tape {exit_t:.2f} s before its battle at "
                                     f"{seg['start']:.2f} s, b6 riding")}
    f3, f4, f5 = facts["f3"], facts["f4"], facts["f5"]
    t_term = f4.get("t_term")
    out["t_term"] = t_term
    live = ((t_term if t_term is not None else seg["end"]) - seg["start"])
    advanced = f4.get("seq") is not None and f4["seq"][0] != f4["seq"][1]
    ok4 = first_said and bool(f3["ok"]) and advanced and f4.get("ready_t") is not None and live >= WB_LIVE_NEED_S
    out["wb4"] = {"ok": ok4, "why": ("the world-map battle is not the tape's first (the facts read the first)" if not first_said else
                                     f"F3 {f3['why']}" if not f3["ok"] else
                                     "the battle seq never advanced" if not advanced else
                                     "no player Ready bit on the wire" if f4.get("ready_t") is None else
                                     f"only {live:.1f} s of live fight (the guest's boot, LIVE and menu need >= "
                                     f"{WB_LIVE_NEED_S:g}: COOP_TAPE_WB_FIGHT_S)" if live < WB_LIVE_NEED_S else
                                     f"a world-map battle (b6 before and after), nonce {seg['nonce']} scene {seg['map']}, "
                                     f"{live:.1f} s live from tape {seg['start']:.2f} s")}
    after = [(t, f) for t, f in (facts.get("fields") or []) if t > seg["end"]]
    t_last = max((r.t for r in records if r.dir == 0), default=seg["end"])
    # [ff9mapkit netsync s145 bench] the stay runs from the battle's end to the host's first real field after it (its entry into
    # the Ice Cavern: WB-300's rejoin) or to the tape's end; any other field, a second one, or too short a stand on it refuses
    real_after = [(t, f) for t, f in after if 0 < f < 65535]
    enter = real_after[0] if real_after else None
    after_s = (enter[0] if enter is not None else t_last) - seg["end"]
    out["after_s"] = round(after_s, 2)
    enter_bad = None
    if enter is not None:
        on_s = t_last - enter[0]
        out["enter"] = {"field": enter[1], "t": enter[0], "on_s": round(on_s, 2)}
        if enter[1] != WB_ENTER_FIELD or len(real_after) > 1:
            enter_bad = (f"the host enters {[f for _t, f in real_after]} after the battle -- a world-battle tape may enter only "
                         f"the Ice Cavern ({WB_ENTER_FIELD}), once (COOP_TAPE_WB_ENTER), after its stay")
        elif on_s < WB_ENTER_NEED_S:
            enter_bad = (f"the host stands on {enter[1]} only {on_s:.1f} s at the tape's end (the guest's rejoin needs >= "
                         f"{WB_ENTER_NEED_S:g}: COOP_TAPE_WB_ENTER_S)")
    term_ok = t_term is not None and f5.get("hide_t") is not None
    ok5 = term_ok and seg["said_after"] == "world" and enter_bad is None and after_s >= WB_AFTER_NEED_S
    out["wb5"] = {"ok": ok5, "why": ("the end block never read terminal, or the result screen never reached Hide"
                                     if not term_ok else
                                     f"after the battle the host says {seg['said_after']!r}, not the world map (b6)"
                                     if seg["said_after"] != "world" else
                                     f"only {after_s:.1f} s of host frames on the world map after the battle (needs >= "
                                     f"{WB_AFTER_NEED_S:g} before any field: COOP_TAPE_WB_POST_S)" if after_s < WB_AFTER_NEED_S
                                     else enter_bad if enter_bad is not None else
                                     f"terminal from tape {t_term:.2f} s, result-hide at {f5['hide_t']:.2f} s, the host on the "
                                     f"world map {after_s:.1f} s after"
                                     + (f", then on field {enter[1]} from tape {enter[0]:.2f} s ({out['enter']['on_s']:.1f} s)"
                                        if enter is not None else "; no field after it (no rejoin to read)"))}
    return out


#: [ff9mapkit netsync s145 fix1] the synthetic tapes' real shape around a battle (coop_peer.tape_battle_where's comment): the swirl
#: and the gMode-2 lead before the first type-1 frame, the world's load after the result tail (SHORTENED: a real one is ~4.4 s,
#: inside WHERE_AFTER_S; a few frames carry the shape, and the stand-in's diorama stall cap -- 120 frames at 600 fps -- stays
#: clear of it)
SYNTH_SWIRL_S = 1.0
SYNTH_LEAD_S = 0.2
SYNTH_LOAD_S = 0.3


def synthetic_world_battle_tape(cp, *, field_s: float = 25.0, dwell_s: float = 90.0, fight_s: float = 25.0,
                                post_s: float = 30.0, b6: bool = True, field: int = WORLD_TAPE_FIELD, nonce: int = 5,
                                scene: int = BENCH_SCENE, guest_ready: bool = False, enter_s: float = 0.0,
                                enter_field: int = WB_ENTER_FIELD) -> list:
    """[ff9mapkit netsync s145] An in-memory WORLD-BATTLE host tape shaped like coop_tape_record.py's COOP_TAPE_WORLD_BATTLE one
    (10 Hz): the host on ``field`` with the story marker, off-field ``dwell_s`` on its world HUD (b6 + b4 + b1; ``b6`` False =
    b4 + b1 alone), a world battle (fighting ``fight_s`` with a player Ready, then victory -> the result screen to Hide; b5 on
    its state frames), then ``post_s`` back on the world HUD. [ff9mapkit netsync s145 fix1] THE REAL SHAPE around the battle (every
    recorded host tape's): the last SYNTH_SWIRL_S of the dwell is the swirl (b1 alone: 'other') and SYNTH_LEAD_S the gMode-2
    lead (b4 + b5: 'battle') before the first type-1 frame; after the last one the result tail (b5 alone) and SYNTH_LOAD_S of
    the world's load ('other') before the world HUD -- so a reader of the ADJACENT frame never sees the place. [ff9mapkit netsync s145 bench] ``guest_ready`` adds the guest's
    slot (btl index 1, in the head's guest slots 2) as a player Ready from 4 s into the fight, as the recorder's COOPPARTY party
    puts Vivi there (the replayed guest's stock menu serves it); ``enter_s`` > 0 ends the tape with the host on ``enter_field``
    that long after the stay (COOP_TAPE_WB_ENTER: the rejoin WB-300 reads)."""
    import harness.battlewire as BW          # noqa: E402 -- tools/ on sys.path (coop_peer_module put it there)
    R = cp.Record
    story = bytearray(2048)
    story[MARKER_BYTE] = MARKER_VALUE

    def state(flags, fld):
        sec0 = bytes([0, 0x00, 0x08]) + bytes(story)
        return cp.build_frame(cp.TYPE_STATE, BW.append_section(sec0, BW.SECTION_DIALOG,
                                                               BW.dialog_section(0x0145, 7, flags, 0, fld)))

    roster = ((0, True, b"Zidane"), (1, True, b"Vivi"), (4, False, b"Goblin")) if guest_ready else \
        ((0, True, b"Zidane"), (4, False, b"Goblin"))

    def battle_frame(phase, seq_, result, ui, res, ready, guest=False):
        head = struct.pack("<HHBBBBBHB", seq_ & 0xFFFF, scene, 2, 0, 0, 0x03, nonce, 7, len(roster))
        units = b""
        for idx, player, name in roster:
            rdy = (ready and player and idx != 1) or (guest and idx == 1)
            info = (1 if player else 0) | 2 | (4 if rdy else 0)
            units += (bytes([idx, info]) + struct.pack("<IIIIHH", 100, 100, 10, 10, 0, 100) + bytes([len(name)]) + name
                      + b"\x00")
        block = cp.BW.make_block(phase, 0, result, ui=ui, state=res)
        return cp.build_frame(cp.TYPE_BATTLE, head + units + cp.BW.encode_trailer(block))

    recs, t, seq = [], 1.0, 0
    on_field = BW.HF_ON_FIELD | BW.HF_CONTROL
    world = (BW.HF_WORLD if b6 else 0) | BW.HF_MENU | BW.HF_CONTROL
    in_battle = BW.HF_BATTLE | BW.HF_MENU
    swirl_s, lead_s = min(SYNTH_SWIRL_S, dwell_s / 2.0), min(SYNTH_LEAD_S, dwell_s / 4.0)
    for fld, flags, span in ((field, on_field, field_s), (0, world, dwell_s - swirl_s - lead_s),
                             (0, BW.HF_CONTROL, swirl_s), (0, in_battle, lead_s)):      # [s145 fix1] the swirl, the lead
        end = t + span
        while t < end:
            recs += [R(t, 0, cp.build_pos_frame(fld, model=1, pos=(900.0, 0.0, -1400.0))), R(t, 0, state(flags, fld))]
            t += 0.1
    b0 = t
    while t < b0 + fight_s:
        seq += 1
        recs += [R(t, 0, cp.build_pos_frame(0)), R(t, 0, battle_frame(4, seq, 0, 0, 0, t > b0 + 3.0, t > b0 + 4.0)),
                 R(t, 0, state(in_battle, 0))]
        t += 0.1
    for phase, result, ui, res, n in ((5, 0, 0, 0, 10), (6, 1, 0, 0, 20), (6, 1, 1, 0, 30), (6, 1, 1, 7, 5)):
        for _ in range(n):
            seq += 1
            recs += [R(t, 0, cp.build_pos_frame(0)), R(t, 0, battle_frame(phase, seq, result, ui, res, False)),
                     R(t, 0, state(in_battle, 0))]
            t += 0.1
    recs.append(R(t, 0, state(BW.HF_BATTLE, 0)))             # [s145 fix1] the result tail (b5 alone) on the last frame's heels
    t += 0.1
    end = t + SYNTH_LOAD_S
    while t < end:                                           # [s145 fix1] the world's load: no place said
        recs += [R(t, 0, cp.build_pos_frame(0)), R(t, 0, state(BW.HF_CONTROL, 0))]
        t += 0.1
    end = t + post_s
    while t < end:
        recs += [R(t, 0, cp.build_pos_frame(0, model=1, pos=(900.0, 0.0, -1400.0))), R(t, 0, state(world, 0))]
        t += 0.1
    if enter_s > 0:                                          # [ff9mapkit netsync s145 bench] the entry after the stay
        end = t + enter_s
        while t < end:
            recs += [R(t, 0, cp.build_pos_frame(enter_field, model=1, pos=(0.0, 0.0, 0.0))), R(t, 0, state(on_field,
                                                                                                         enter_field))]
            t += 0.1
    return recs


def span_why(plan: dict, stage: int):
    """[ff9mapkit netsync s145] THE SPAN's expected over-verdict BY THE GUEST'S STAGE (the stage law): a world-map victory on a tape
    whose host says b6 after it leaves at the settle as `host_world` on an s145 guest (section 7's b6 is its over-signal), and at
    the 8 s stall cap (`stall_cap`) before s145 -- a field victory is `host_field` on both. None = the plan names none."""
    exp = (plan or {}).get("expect") or {}
    if int(stage or 0) >= 145 and exp.get("why_s145") is not None:
        return exp.get("why_s145")
    return exp.get("why")


def _world_battle_rows(cp) -> list:
    """[ff9mapkit netsync s145] THE WORLD-BATTLE LEG's facts and plan on synthetic tapes (no file), and the span's stage-keyed
    verdict: every row runs, each refusal pinned by its own short tape (every check can fail)."""
    rows = []

    def row(ok, what):
        rows.append((bool(ok), what))

    good = world_battle_tape_facts(synthetic_world_battle_tape(cp), cp)
    row(all(good[k]["ok"] for k in ("wb1", "wb2", "wb3", "wb4", "wb5")) and good["battle"]["map"] == BENCH_SCENE
        and good["dwell_s"] >= WB_DWELL_NEED_S and good["after_s"] >= WB_AFTER_NEED_S,
        "world-battle facts: the synthetic tape -- " + " | ".join(f"{k}:{good[k]['why']}" for k in
                                                                ("wb1", "wb2", "wb3", "wb4", "wb5")))
    gp = plan_world_leg("world-battle", good)
    row(gp["ok"] and gp["expect"]["leave_whys"] == WB_LEAVE_WHYS and gp["expect"]["battle_start"] == good["battle"]["start"]
        and gp["stop_at"] is None and gp["field"] == WORLD_TAPE_FIELD,
        f"world-battle plan: the whole tape, leave on {WB_LEAVE_WHYS} ({gp['why'] or 'ok'})")
    short = world_battle_tape_facts(synthetic_world_battle_tape(cp, dwell_s=40.0), cp)
    sp = plan_world_leg("world-battle", short)
    row(not sp["ok"] and not short["wb3"]["ok"] and "COOP_TAPE_WB_DWELL_S" in sp["why"],
        f"world-battle plan: a 40 s dwell refuses ({short['wb3']['why']})")
    quick = world_battle_tape_facts(synthetic_world_battle_tape(cp, fight_s=6.0), cp)
    brief = world_battle_tape_facts(synthetic_world_battle_tape(cp, post_s=8.0), cp)
    old = world_battle_tape_facts(synthetic_world_battle_tape(cp, b6=False), cp)
    row(not quick["wb4"]["ok"] and "COOP_TAPE_WB_FIGHT_S" in quick["wb4"]["why"]
        and not brief["wb5"]["ok"] and "COOP_TAPE_WB_POST_S" in brief["wb5"]["why"]
        and not old["wb3"]["ok"] and not plan_world_leg("world-battle", old)["ok"],
        f"world-battle facts: a 6 s fight, an 8 s stay after it and a host with no b6 each refuse ({quick['wb4']['why']} | "
        f"{brief['wb5']['why']} | {old['wb3']['why']})")
    plain = world_tape_facts(synthetic_world_tape(cp), cp)
    row(not plan_world_leg("world-battle", plain)["ok"],
        "world-battle plan: a world-WAIT tape (no battle) refuses")
    wd = cp.tape_where(synthetic_world_battle_tape(cp))
    row(wd["world_battles"] == 1 and wd["battles"][0]["said_before"] == wd["battles"][0]["said_after"] == "world"
        and cp.where_ok(wd, "world-battle") and not cp.where_ok(cp.tape_where(synthetic_world_tape(cp)), "world-battle"),
        "where: the battle segment says world before and after; a world-wait tape has no world battle")
    fw = {"expect": {"why": "stall_cap", "why_s145": "host_world", "after_field": 0}}
    ff = {"expect": {"why": "host_field", "why_s145": "host_field", "after_field": 250}}
    row(span_why(fw, 144) == "stall_cap" and span_why(fw, 145) == "host_world" and span_why(ff, 145) == "host_field"
        and span_why({"expect": {"why": "stall_cap"}}, 145) == "stall_cap",
        "span: a world victory's verdict is stall_cap before s145 and host_world from it (a tape with no b6 stays stall_cap)")
    held = os.environ.get("COOP_TAPE_DIR")
    try:
        os.environ.pop("COOP_TAPE_DIR", None)
        dflt = world_battle_tape_dir()
    finally:
        if held is not None:
            os.environ["COOP_TAPE_DIR"] = held
    row(dflt.name == "world-battle" and WORLD_BATTLE_POINTER not in ("latest.json", WORLD_POINTER),
        f"world-battle tapes: the default home is coop-tapes/world-battle ({dflt}); its pointer {WORLD_BATTLE_POINTER}")
    return rows


# ======================================================================================== the self-check (no game)
def synthetic_tape(cp, *, pre_s: float = 70.0, fight_s: float = 40.0, post_s: float = 30.0, field: int = BENCH_FIELD,
                   nonce: int = 3, scene: int = BENCH_SCENE, resend: int = 1, sec7: bool = False) -> list:
    """An in-memory host tape shaped like coop_tape_record.py's (10 Hz, not 30 -- the facts read edges, not rates):
    free roam on ``field`` with the story marker, a battle (fighting, a player Ready, then victory-pending -> victory ->
    the result screen to Hide), the host back on ``field``. [ff9mapkit netsync s131] ``resend`` = how many times each
    fighting seq goes out, one write tick (33 ms) apart -- the sticky slot's repeats a cut's tail is made of (1 = every
    tail 0; 3 = the last third of each 100 ms seq reads tail 66). [ff9mapkit netsync s145 fix1] ``sec7`` (opt-in: every older
    caller's tape is unchanged) adds section 7 to the state frames in a real field host's shape: b1 + b3 on the field, the
    swirl (b1 alone) and the gMode-2 lead (b4 + b5) before the first type-1 frame, the battle's own state frames (b4 + b5), the
    result tail (b5) after its last, then the field again."""
    import harness.battlewire as BW          # noqa: E402 -- tools/ on sys.path (coop_peer_module put it there)
    R = cp.Record
    recs = []
    story = bytearray(2048)
    story[MARKER_BYTE] = MARKER_VALUE
    plain = bytes([0, 0x00, 0x08]) + bytes(story)

    def st7(flags, fld):
        if not sec7:
            return cp.build_frame(cp.TYPE_STATE, plain)
        return cp.build_frame(cp.TYPE_STATE, BW.append_section(plain, BW.SECTION_DIALOG,
                                                               BW.dialog_section(0x0145, 7, flags, 0, fld)))
    on_field = BW.HF_ON_FIELD | BW.HF_CONTROL
    state = cp.build_frame(cp.TYPE_STATE, plain)
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

    if not sec7:
        while t < pre_s:
            recs += [R(t, 0, pos(field)), R(t, 0, state)]
            t += 0.1
    else:                                                    # [s145 fix1] the field, then the swirl and the lead
        for fld, flags, until in ((field, on_field, pre_s - SYNTH_SWIRL_S - SYNTH_LEAD_S), (field, BW.HF_CONTROL,
                                                                                           pre_s - SYNTH_LEAD_S),
                                  (0, BW.HF_BATTLE | BW.HF_MENU, pre_s)):
            while t < until:
                recs += [R(t, 0, pos(fld)), R(t, 0, st7(flags, fld))]
                t += 0.1
    b0 = t
    while t < b0 + fight_s:
        seq += 1
        frame = battle_frame(4, seq, 0, 0, 0, t > b0 + 3.0)
        recs += [R(t, 0, pos(0)), R(t, 0, frame)] + [R(t + k * 0.033, 0, frame) for k in range(1, resend)]
        if sec7:
            recs.append(R(t, 0, st7(BW.HF_BATTLE | BW.HF_MENU, 0)))
        t += 0.1
    for phase, result, ui, res, n in ((5, 0, 0, 0, 10), (6, 1, 0, 0, 20), (6, 1, 1, 0, 30), (6, 1, 1, 7, 5)):
        for _ in range(n):
            seq += 1
            recs += [R(t, 0, pos(0)), R(t, 0, battle_frame(phase, seq, result, ui, res, False))]
            if sec7:
                recs.append(R(t, 0, st7(BW.HF_BATTLE | BW.HF_MENU, 0)))
            t += 0.1
    if sec7:
        recs.append(R(t, 0, st7(BW.HF_BATTLE, 0)))           # [s145 fix1] the result tail (b5 alone)
    t += 0.5
    end = t + post_s
    while t < end:
        recs += [R(t, 0, pos(field)), R(t, 0, st7(on_field, field) if sec7 else state)]
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
        row(on("menu_close_nolane") == [156], f"s117 log: the ONE no-lane menu close is 156, sitting A's cut -- the "
            f"'end injected' / 'waiting' closes (57/106/154) are not it (got {on('menu_close_nolane')})")
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
    gbench = engine_grace(str(BENCH_GRACE_MS))
    # [ff9mapkit netsync s132] '' / malformed keep the ENGINE's default (40000 since s132) -- which is why the bench writes
    # its own 30000 (BENCH_GRACE_MS, = GRACE_DEFAULT_S) instead of leaving the key empty
    row(g45[0] == 40000 and "clamped to 40000 ms" in (g45[1] or "") and g0[0] == 5000 and gdef == (40000, None)
        and gbad[0] == 40000 and gbad[1] and engine_grace(" \"20000\" ") == (20000, None)
        and gbench == (30000, None) and GRACE_DEFAULT_S == 30.0,
        f"engine_grace: 45000 -> {g45[0]}, 0 -> {g0[0]}, '' -> {gdef[0]}, 'thirty' -> {gbad[0]}, the bench's "
        f"{BENCH_GRACE_MS} -> {gbench[0]} (ParseSessionGrace's clamp)")
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
    row(engine_stage({"netsync": {"menu_refusal": {}, "battle": {"peer": {"expired": {"count": 0}}}}}) == 131
        and engine_stage({"netsync": {"menu_refusal": {}, "battle": {"peer": {"live": False}}}}) == 121,
        "engine_stage: s131 = netsync.battle.peer.expired (a peer block without it is s121)")
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
    plans = {leg: plan_leg(leg, f) for leg in LEGS if leg != "readopt"}
    row(all(p["ok"] for p in plans.values()), "plans: every leg but readopt fits the synthetic tape: "
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
    row(canon_leg("s120-world") == "span" and canon_leg("") == "cal" and canon_leg("nope") is None
        and canon_leg("s131") == "readopt", "legs: aliases")
    rows.extend(_tail_rows(cp, f, plans))
    rows.extend(_world_rows(cp, f))                     # [ff9mapkit netsync s144] the world legs' facts and plans
    rows.extend(_world_battle_rows(cp))                 # [ff9mapkit netsync s145] the world-battle leg's facts and plan
    return rows


def _tail_rows(cp, f: dict, plans: dict) -> list:
    """[ff9mapkit netsync s131] THE CUT'S TAIL and THE HOLD RULE, off hand-built data (no file): every row runs."""
    rows = []

    def row(ok, what):
        rows.append((bool(ok), what))

    R = cp.Record

    def bf(seq, nonce=1):
        return cp.build_frame(cp.TYPE_BATTLE, struct.pack("<HHBBBBBHB", seq, BENCH_SCENE, 2, 0, 0, 0x03, nonce, 7, 0))

    # seq 7 x3 (33 ms ticks), seq 8 x2, seq 9, seq 8 AGAIN (a wrapped u16), nonce 2's seq 8 x2; a position frame and a
    # GUEST-dir battle frame between them (neither is the host's battle lane)
    hand = [R(1.000, 0, bf(7)), R(1.010, 0, cp.build_pos_frame(0)), R(1.033, 0, bf(7)), R(1.066, 0, bf(7)),
            R(1.100, 0, bf(8)), R(1.133, 0, bf(8)), R(1.140, 1, bf(99)), R(1.200, 0, bf(9)), R(1.300, 0, bf(8)),
            R(1.333, 0, bf(8)), R(2.000, 0, bf(8, nonce=2)), R(2.033, 0, bf(8, nonce=2))]
    want = {1.05: 33.0, 1.07: 66.0, 1.1: 66.0, 1.101: 0.0, 1.134: 33.0, 1.15: 33.0, 1.34: 33.0, 2.02: 0.0, 2.04: 33.0,
            0.9: None, 4.1: None}
    got = {at: tape_tail(hand, at, cp) for at in want}
    row(got == want, f"tape_tail: the final pre-cut seq's last receipt minus its first, the replay's 'at <= t' drop "
        f"(1.1 keeps 1.066), a contiguous (nonce, seq) run (a wrapped seq 8 at 1.30 is not 1.10's; nonce 2's seq 8 is "
        f"its own), only the host's battle frames; None before the lane and 2 s past it ({got})")
    started = _dt.datetime(2026, 10, 15, 4, 30, 0)
    head = {"started": started.isoformat(timespec="milliseconds")}
    tap = [R(10.000, 0, bf(5)), R(10.033, 0, bf(5)), R(10.066, 0, bf(5)), R(10.099, 0, bf(5)),
           R(10.1004, 0, bf(5)), R(16.1002, 0, bf(6)), R(16.133, 0, bf(6))]
    c0, c1 = started + _dt.timedelta(seconds=10.1), started + _dt.timedelta(seconds=16.1)
    t1, why1 = tap_tail(tap, head, c0, c1, cp)
    t2, why2 = tap_tail(tap[:1], head, c0 + _dt.timedelta(seconds=3), c1 + _dt.timedelta(seconds=3), cp)
    t3, _w3 = tap_tail(tap, {"started": "?"}, c0, c1, cp)
    row(t1 == 100.4 and "the next host battle frame +0.2 ms from the resume" in why1 and t2 is None
        and "already silent" in why2 and t3 is None,
        f"tap_tail: the cut point is the MIDDLE of the suspend (a frame in flight 0.4 ms after it counts, the resumed "
        f"backlog does not); a lane silent before the cut and a bad header read None ({t1}: {why1[:120]} | {why2[:80]})")
    # the plans: a tail-0 tape cannot carry the readopt leg; a re-sending host's can, at its nearest placement
    no = plan_leg("readopt", f)
    row(not no["ok"] and ">= 66 ms" in no["why"] and plans["s119"]["tail_ms"] == 0.0
        and all(plans[k]["tail_ms"] is None for k in ("cal", "s120-long", "s120-roam", "s121")),
        f"plans: readopt refuses a host that sends each seq once ({no['why'][:110]}); s119's tail 0.0; no tail off a "
        "battle lane")
    rs = synthetic_tape(cp, resend=3)
    fr = tape_facts(rs, cp)
    rp = plan_leg("readopt", fr)
    lo = fr["battle"]["start"] + READOPT_AT_S
    at_ = rp["bh"][0] if rp.get("bh") else None
    ts = [r[0] for r in fr["rx"]]
    k_at = _tail_core(fr["rx"], ts, at_)[1] if at_ else None
    # a qualifying ms placement before `at` in an EARLIER stretch (the same stretch is the same frame set: `at` is its middle)
    earlier = [x for x in (lo + k / 1000.0 for k in range(int((at_ - lo) * 1000) if at_ else 0))
               if (tail_at(fr["rx"], x, ts=ts) or 0.0) >= READOPT_TAIL_MS and _tail_core(fr["rx"], ts, x)[1] != k_at]
    args = plan_args(rp, port=DEFAULT_PORT, code=BENCH_CODE) if rp["ok"] else []
    row(rp["ok"] and at_ >= lo and rp["tail_ms"] >= READOPT_TAIL_MS and tape_tail(rs, at_, cp) == rp["tail_ms"]
        and not earlier and at_ - lo < 0.1 and rp["bh"][1] == READOPT_FOR_S and f"{at_:.3f}" in args,
        f"plans: readopt = the s119 cut moved to the NEAREST tail >= 66 placement at or after battle+10 s (at "
        f"{at_}, battle+10 = {lo:.3f}, tail {rp['tail_ms']}; qualifying placements in an earlier stretch: "
        f"{len(earlier)}): "
        f"{rp['why'] or rp['expect'].get('placement', '')[:90]}")
    # THE HOLD RULE against every hold the arc measured (R3-SITTING-A-FIXES.md "The hold-onset variance"), and the
    # pre-s131 characterisation; (hold, outage, tail, leave) -> (post-fix rule, pre-s131 re-adopt reproduced)
    cases = {
        "T2 s119 on s121 (tail 0), run 1": ((4047, 4031, 0.0, False), (True, False)),
        "T2 s119 on s121 (tail 0), run 2": ((4032, 4032, 0.0, False), (True, False)),
        "confirm s119 @81.66 on s121 (tail 67.3)": ((2094, 4032, 67.3, False), (False, True)),
        "confirm s120-battle @79.66 on s121 (tail 0)": ((18047, 18015, 0.0, False), (True, False)),
        "T2 s120-battle @79.59 on s121 (tail 66.5), run 1": ((16094, 18015, 66.5, False), (False, True)),
        "T2 s120-battle @79.59 on s121 (tail 66.5), run 2": ((16078, 18031, 66.5, False), (False, True)),
        "T2 span on s121 (leave-ended, tail 66.6), run 1": ((12015, 13453, 66.6, True), (False, None)),
        "T2 span on s121 (leave-ended, tail 66.6), run 2": ((12000, 13453, 66.6, True), (False, None)),
        "P5 live on s121 (tail 134.9)": ((2125, 4000, 134.9, False), (False, True)),
        "s131 as predicted, tail 67.3": ((4032 + 67, 4032, 67.3, False), (True, False)),
        "s131 as predicted, leave-ended, tail 66.6": ((13453 + 500 + 70, 13453, 66.6, True), (True, None)),
    }
    for name, ((h, o, t, lv), (want_rule, want_red)) in cases.items():
        ok_rule = hold_rule(h, o, t, leave=lv)[0]
        ok_red = readopt_reproduced(h, o, t)[0] if not lv else None
        row(ok_rule == want_rule and ok_red == want_red, f"hold rule: {name} -> post-fix {ok_rule} (want {want_rule}), "
            f"re-adopt reproduced {ok_red} (want {want_red}): {hold_rule_text(h, o, t, leave=lv)[:150]}")
    both = [(t, h) for t in (66.0, 67.3, 100.0, 133.3) for h in range(0, 6001)
            if hold_rule(h, 4000, t)[0] and readopt_reproduced(h, 4000, t)[0]]
    row(not both and hold_rule(None, 4000, 0.0)[0] is False and readopt_reproduced(2000, 4000, 33.3)[0] is False,
        f"hold rule: the post-fix window and the re-adopt window never overlap at a tail >= 66 ({both[:3]}); a missing "
        "figure is never ok; a tail-33 cut is no re-adopt-class verdict")
    return rows


def _world_rows(cp, f: dict) -> list:
    """[ff9mapkit netsync s144] THE WORLD LEGS' facts and plans on synthetic tapes (no file): every row runs. ``f`` = the field
    tape's facts (:func:`synthetic_tape`)."""
    rows = []

    def row(ok, what):
        rows.append((bool(ok), what))

    rp = plan_world_leg("world-rejoin", f)
    row(rp["ok"] and rp["field"] == BENCH_FIELD and rp["stop_at"] == f["start"] + REJOIN_SPAN_S
        and rp["stop_at"] < f["battle"]["start"] - 5.0 + 1e-9,
        f"world plans: world-rejoin fits the field-250 tape -- field {rp['field']}, the replay stopped at tape "
        f"{rp['stop_at']} (its battle at {f['battle']['start']:.2f}) ({rp['why'] or 'ok'})")
    short = tape_facts(synthetic_tape(cp, pre_s=20.0), cp)
    rs = plan_world_leg("world-rejoin", short)
    row(not rs["ok"] and "only" in rs["why"] and rs["stop_at"] <= short["battle"]["start"] - 5.0 + 1e-9,
        f"world plans: a host on its field 19 s before the battle refuses world-rejoin ({rs['why']})")
    new = world_tape_facts(synthetic_world_tape(cp), cp)
    old = world_tape_facts(synthetic_world_tape(cp, b6=False), cp)
    row(all(new[k]["ok"] for k in ("w1", "w2", "w3")) and new["b6"] is True and new["field"] == WORLD_TAPE_FIELD
        and abs(new["exit_t"] - 26.0) < 0.15 and new["world_s"] >= 89.0,
        "world facts: an s144 host-on-world tape -- " + " | ".join(f"{k}:{new[k]['why']}" for k in ("w1", "w2", "w3")))
    row(all(old[k]["ok"] for k in ("w1", "w2", "w3")) and old["b6"] is False and "host_away" in old["w3"]["why"],
        f"world facts: the same walk with no b6 (an s143 host) reads b6 False -- the old-host fallback ({old['w3']['why']})")
    pw, po = plan_world_leg("world-wait", new), plan_world_leg("world-wait", old)
    row(pw["ok"] and pw["expect"]["b6"] is True and po["ok"] and po["expect"]["b6"] is False
        and pw["stop_at"] is None and pw["field"] == WORLD_TAPE_FIELD,
        "world plans: world-wait fits both, the whole tape, its line keyed by the tape's b6")
    brief = world_tape_facts(synthetic_world_tape(cp, world_s=30.0), cp)
    other = world_tape_facts(synthetic_world_tape(cp, field=BENCH_FIELD), cp)
    quick = world_tape_facts(synthetic_world_tape(cp, field_s=5.0), cp)
    row(not brief["w3"]["ok"] and "COOP_TAPE_WORLD_S" in brief["w3"]["why"] and not plan_world_leg("world-wait", brief)["ok"]
        and not other["w1"]["ok"] and f"not {WORLD_TAPE_FIELD}" in other["w1"]["why"]
        and not quick["w1"]["ok"] and "only" in quick["w1"]["why"],
        f"world facts: a 30 s world stay, a tape on another field and a 4 s field stretch each refuse ({brief['w3']['why']} | "
        f"{other['w1']['why']} | {quick['w1']['why']})")
    back = world_tape_facts(synthetic_world_tape(cp, back=WORLD_TAPE_FIELD), cp)
    no5 = [r for r in synthetic_world_tape(cp) if not (r.dir == 0 and r.payload[2:3] == bytes([cp.TYPE_STATE]))]
    n5 = world_tape_facts(no5, cp)
    row(back["back_t"] is not None and abs(back["world_s"] - 90.0) < 0.2 and not n5["w2"]["ok"] and not n5["w3"]["ok"],
        f"world facts: the host back on its field ends the world span ({back['world_s']} s); no type-5 -> w2 and w3 missing")
    held = {k: os.environ.get(k) for k in ("COOP_TAPE", "COOP_TAPE_DIR")}
    try:
        os.environ.pop("COOP_TAPE", None)
        os.environ["COOP_TAPE_DIR"] = os.path.join("tapes", "w")
        wd = world_tape_dir()
        os.environ["COOP_TAPE"] = os.path.join("tapes", "x-world-s144.f9tape")
        lw = latest_world_tape()
    finally:
        for k, v in held.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    dflt = world_tape_dir()
    row(wd == (Path.cwd() / "tapes" / "w").resolve() and lw == (Path.cwd() / "tapes" / "x-world-s144.f9tape").resolve()
        and (held["COOP_TAPE_DIR"] is not None or dflt.name == "world") and WORLD_POINTER != "latest.json",
        f"world tapes: COOP_TAPE_DIR / COOP_TAPE resolve against this cwd; the default home is coop-tapes/world ({dflt}); "
        f"its pointer {WORLD_POINTER} never latest.json")
    row(plan_world_leg("nope", f)["ok"] is False and "unknown world leg" in plan_world_leg("nope", f)["why"],
        "world plans: an unknown leg refuses")
    return rows


def _calibration_rows() -> list:
    """[ff9mapkit netsync s131] THE TAIL AND THE HOLD RULE AGAINST THE ARC'S OWN RUNS (R3-SITTING-A-FIXES.md "The
    hold-onset variance"): the T2 tape's tails at every placement the arc ran, the readopt leg's plan on it, the
    no-engine-change confirmation (s119 at 81.66 -> red, s120-battle at 79.66 -> green, both on the deployed s121) and
    the live P5 cut off its relay tap. Each source is a gitignored run artifact of THIS machine: a missing one SKIPS its
    block as one row. Kept out of :func:`_self_rows` (the unit-test surface, which pins its own skip count): the
    no-game self-check (``__main__``) runs both."""
    rows = []

    def row(ok, what):
        rows.append((None if ok is SKIPPED else bool(ok), what))

    try:
        cp = coop_peer_module()
    except Exception as err:                 # noqa: BLE001
        row(False, f"coop_peer import: {err}")
        return rows
    tape = main_repo() / ".harness-runs" / "coop-tapes" / ARC_TAPE_NAME
    records = None
    if tape.exists():
        _h, records, _torn = cp.read_tape(tape)
        rx = battle_receipts(records, cp)
        tails = {at: tail_at(rx, at) for at in (81.590, 81.633, 81.660, 79.590, 79.660, 115.359)}
        row(tails[81.590] == 0.0 and 33.0 <= tails[81.633] <= 34.0 and 66.0 <= tails[81.660] <= 68.0
            and 66.0 <= tails[79.590] <= 67.0 and tails[79.660] == 0.0 and 66.0 <= tails[115.359] <= 67.0,
            f"arc tape: the tails the arc measured -- s119 81.59 -> 0, 81.633 -> 33, the confirmation's 81.66 -> ~67, "
            f"s120-battle 79.59 -> 66.5, its confirmation 79.66 -> 0, span 115.359 -> 66.6 ({tails})")
        facts = tape_facts(records, cp, field=None)
        pl = {leg: plan_leg(leg, facts) for leg in ("s119", "readopt", "s120-battle", "span")}
        ra = pl["readopt"]["bh"][0] if pl["readopt"].get("bh") else None
        ts = [r[0] for r in rx]
        same = ra is not None and _tail_core(rx, ts, ra)[1] == _tail_core(rx, ts, 81.660)[1]
        row(pl["s119"]["tail_ms"] == 0.0 and (pl["s120-battle"]["tail_ms"] or 0) >= READOPT_TAIL_MS
            and (pl["span"]["tail_ms"] or 0) >= READOPT_TAIL_MS and pl["readopt"]["ok"] and 81.59 < ra < 81.70
            and pl["readopt"]["tail_ms"] >= READOPT_TAIL_MS and same,
            f"arc tape: the plans' tails (s119 {pl['s119']['tail_ms']}, s120-battle {pl['s120-battle']['tail_ms']}, span "
            f"{pl['span']['tail_ms']}); readopt at {ra} (tail {pl['readopt']['tail_ms']}) -- the confirmation's 81.66 "
            f"stretch, the same frames: {same}")
    else:
        row(SKIPPED, f"the arc's T2 tape is not on this machine ({tape}) -- its tail rows did NOT run")
    for leg, rd in CONFIRM_RUNS.items():
        logs = sorted(rd.glob("Memoria-coop-cut-*.log")) if rd.is_dir() else []
        peer = sorted(rd.glob("coop_peer-replay-*.log")) if rd.is_dir() else []
        if not (logs and peer and records is not None):
            row(SKIPPED, f"the confirmation run {rd.name} (or the arc tape) is not on this machine -- its row did NOT run")
            continue
        eng = [x for x in (parse_engine_line(ln) for ln in logs[0].read_text(encoding="utf-8", errors="replace")
                           .splitlines()) if x is not None]
        bh = [m for m in (PEER["bh_begin"].match(x[1]) for x in
                          (parse_peer_line(ln, _dt.date.today()) for ln in peer[0].read_text(
                              encoding="utf-8", errors="replace").splitlines()) if x is not None) if m]
        at = float(bh[0].group(1)) if bh else None
        tail = tape_tail(records, at, cp) if at is not None else None
        res, back = hits(eng, "hold_resume"), hits(eng, "session_back")
        held = int(res[0][2].group(2)) if res else None
        om = int(back[0][2].group(1)) if back else None
        rule, red = hold_rule(held, om, tail)[0], readopt_reproduced(held, om, tail)[0]
        closes = hits(eng, "menu_close_nolane")
        want = (False, True) if leg == "s119" else (True, False)
        row((rule, red) == want and len(closes) <= MENU_CLOSES_MAX,
            f"confirmation {leg} on s121 (blackhole at tape {at}, tail {tail}): post-fix rule {rule}, re-adopt reproduced "
            f"{red} (want {want}) -- {hold_rule_text(held, om, tail)[:140]}; no-lane closes {len(closes)}")
    pj, tap = P5_RUN / "p4.json", P5_RUN / "relay.tap"
    if pj.exists() and tap.exists():
        doc = json.loads(pj.read_text(encoding="utf-8"))
        c0 = _dt.datetime.fromisoformat(doc["cut"]["start"])
        c1 = _dt.datetime.fromisoformat(doc["cut"]["end"])
        tail, why = tap_tail_file(tap, c0, c1)
        day = c0.date()
        eng = []
        for ln in doc.get("guest_window") or []:
            hh, mm, ss = (int(v) for v in ln[:8].split(":"))
            eng.append((_dt.datetime.combine(day, _dt.time(hh, mm, ss)), "M", ln[9:]))
        res, back, closes = hits(eng, "hold_resume"), hits(eng, "session_back"), hits(eng, "menu_close_nolane")
        held = int(res[0][2].group(2)) if res else None
        om = int(back[0][2].group(1)) if back else None
        row(tail is not None and 130.0 <= tail <= 140.0 and (held, om) == (2125, 4000)
            and not hold_rule(held, om, tail)[0] and readopt_reproduced(held, om, tail)[0] and len(closes) == 2,
            f"P5 on s121 off its relay tap: {why[:120]}; {hold_rule_text(held, om, tail)[:120]}; no-lane closes "
            f"{len(closes)} (K4 red twice over: the hold rule AND the second close)")
    else:
        row(SKIPPED, f"the P5 run is not on this machine ({P5_RUN}) -- its relay-tap row did NOT run")
    return rows


def self_check(verbose: bool = True) -> str:
    """-> "OK" | "PARTIAL" | "FAIL". [ff9mapkit netsync R3 T2] PARTIAL = nothing failed but a calibration source was
    missing (the archived sitting-A log is gitignored; the Memoria clone is per-machine; [s131] the arc's tape and runs
    are run artifacts) -- its rows did NOT run, so the verdict is not a calibrated pass and the exit code says so (2)."""
    try:
        rows = _self_rows() + _calibration_rows()
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
