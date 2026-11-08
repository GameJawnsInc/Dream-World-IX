"""s168 ROUND GM -- the runners' Python half (studies/field-coop/s168/round_gm_lib.sh): the pure guards and the proof-block diff, pinned
offline by ff9mapkit/tests/test_coop_guest_menu_runners.py. Nothing here launches, deploys, writes an ini or listens: the port probe binds
127.0.0.1 only (never Any), never calls listen(), and closes at once; the ini reader is read-only.

    py round_gm_guard.py window <HHMM now> <not_after> <not_before>   0 = a leg may start; 1 = inside the gate window (the line says so)
    py round_gm_guard.py ports <port> [<port> ...]                     0 = every port clear; 1 = one refusal line per port
    py round_gm_guard.py ini <Memoria.ini> <section> <key>             the value the engine obeys (the LAST one), or nothing
    py round_gm_guard.py sources                                       the s167 / s168 proof tallies the judges derive; 1 = a s167 source
                                                                       that is really the s168 clone (FF9_S167_CLONE carrying the s168 tag)
    py round_gm_guard.py tape                                          the COOP_TAPE_GUEST_MENU the T tape legs would replay, or nothing
    py round_gm_guard.py proofs <game root> <since epoch> <out>        the newest Memoria.log's proof block (written since the leg began)
    py round_gm_guard.py proofdiff <reference> <got> <old|bracket|new> the block against s167's: only the round's movers may move
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]                                    # studies/field-coop/s168 -> the worktree root

#: [ff9mapkit netsync s168] the gate window: no leg STARTS from NOT_AFTER until NOT_BEFORE (local time; wraps midnight). The s159 law names
#: the 03:00 gate; the scheduled task runs daily at 04:00 and holds the machine to about 06:10 (tools/nightly_gate.md) -- 0230..0700
#: covers both with a leg's length to spare
NOT_AFTER_DEFAULT = "0230"
NOT_BEFORE_DEFAULT = "0700"
OWNER_PORT = 49201                                      # the owner's Workspace bridge: never a bench port (bridge_down guards it)
#: the proof heads whose line must be IDENTICAL to s167's (GM0-BRACKET: SeatSelfTest's line and the containment selftest's; decision 34:
#: MenuRefusalSelfTest stays at its pinned 14 rows) -- every other unmoved head is a NOTE when it differs (a line that carries a measured
#: value would otherwise red a correct engine)
MUST_EQUAL = ("diorama seat selftest", "diorama containment selftest", "main menu refusal selftest")
#: the proof heads s168 moves (decision 34's three lines): the new seat bracket line (W1a, so the pinned W1a/b build carries it too), the
#: new guest menu line and the world walk line (W1d's two caps rows and two mutants) -- each judged against the s168 source's tallies
HEAD_WORLD_WALK, HEAD_SEAT_BRACKET, HEAD_GUEST_MENU = "world walk selftest", "seat bracket selftest", "guest menu selftest"
PROOF_RE = re.compile(r"\[NetSync\] (?P<head>[A-Za-z0-9][A-Za-z0-9 +&'/-]{0,80}? selftest): (?P<tail>.*?)\s*$")


# ================================================================================================ the window
def hhmm(text) -> int | None:
    """'0230' / '230' / '2:30' -> minutes after midnight; '' / 'off' / anything else -> None."""
    raw = str(text or "").strip().lower().replace(":", "")
    if not raw.isdigit() or not 1 <= len(raw) <= 4:
        return None
    raw = raw.zfill(4)
    h, m = int(raw[:2]), int(raw[2:])
    return h * 60 + m if h < 24 and m < 60 else None


def in_window(now: int, start: int | None, end: int | None) -> bool:
    """(PURE) ``now`` (minutes) inside [start, end): wrapping midnight when start > end; never with either end off or start == end."""
    if start is None or end is None or start == end:
        return False
    if start < end:
        return start <= now < end
    return now >= start or now < end


def window_verdict(now_text, not_after, not_before) -> tuple:
    """(PURE) (may_start, why) for the lib's per-leg cutoff."""
    now, a, b = hhmm(now_text), hhmm(not_after), hhmm(not_before)
    if now is None:
        return False, f"the clock read {now_text!r} is not HHMM -- refusing (a cutoff that cannot be read guards nothing)"
    if a is None or b is None:
        return True, f"the gate window is off (ROUND_GM_NOT_AFTER {not_after!r}, ROUND_GM_NOT_BEFORE {not_before!r})"
    if in_window(now, a, b):
        return False, (f"it is {now // 60:02d}:{now % 60:02d}, inside the nightly gate's window {a // 60:02d}:{a % 60:02d}-"
                       f"{b // 60:02d}:{b % 60:02d} (THE s159 LAW: never bench under the gate's suite)")
    return True, f"outside the gate window {a // 60:02d}:{a % 60:02d}-{b // 60:02d}:{b % 60:02d}"


# ================================================================================================ the ports
def parse_excluded(text: str) -> list:
    """(PURE) `netsh int ipv4 show excludedportrange protocol=tcp` -> [(lo, hi)] (the administered '*' suffix ignored)."""
    out = []
    for ln in str(text or "").splitlines():
        m = re.match(r"^\s*(\d{1,5})\s+(\d{1,5})\b", ln)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo <= hi:
                out.append((lo, hi))
    return out


def port_refusals(ports, ranges, probe) -> list:
    """(PURE over ``probe``) One refusal per port that a duo / peer leg could not use: the owner's port, a port inside an excluded range
    (THE EXCLUDED PORT RANGE: WinError 10013 at bind), or one ``probe(port)`` -> (bindable, accepting) finds held by another program
    (Parsec held 49211 on 11-04: every duo leg refused at C0)."""
    why = []
    for p in ports:
        p = int(p)
        if p == OWNER_PORT:
            why.append(f"port {p} is the owner's Workspace bridge port -- never a bench port")
            continue
        hit = next(((lo, hi) for lo, hi in ranges if lo <= p <= hi), None)
        if hit is not None:
            why.append(f"port {p} is inside the excluded range {hit[0]}-{hit[1]} (THE EXCLUDED PORT RANGE) -- pick another with "
                       "ROUND_GM_DUO_PORTS / ROUND_GM_PEER_PORT / ROUND_GM_RELAY_PORT")
            continue
        bindable, accepting = probe(p)
        if accepting:
            why.append(f"port {p} already ACCEPTS on 127.0.0.1 -- another program listens there (close it, or pick another port)")
        elif not bindable:
            why.append(f"port {p} cannot be bound on 127.0.0.1 -- another program holds it (pick another port)")
    return why


def probe_port(port: int) -> tuple:
    """(bindable, accepting) on 127.0.0.1 -- a bind with no listen (closed at once) and a connect. Never Any, never a listener."""
    accepting = False
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c.settimeout(0.3)
    try:
        accepting = c.connect_ex(("127.0.0.1", int(port))) == 0
    except OSError:
        accepting = False
    finally:
        c.close()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind(("127.0.0.1", int(port)))
        bindable = True
    except OSError:
        bindable = False
    finally:
        s.close()
    return bindable, accepting


def excluded_now() -> tuple:
    """(ranges, note): the OS's excluded TCP ranges, or [] and why the probe could not read them (it then refuses nothing itself: the
    bind probe still catches an excluded port)."""
    try:
        out = subprocess.run(["netsh", "int", "ipv4", "show", "excludedportrange", "protocol=tcp"], capture_output=True, text=True,
                             timeout=10)
    except (OSError, subprocess.SubprocessError) as err:
        return [], f"netsh unavailable ({type(err).__name__}): only the bind probe judged"
    return parse_excluded(out.stdout), ""


# ================================================================================================ the ini (read-only)
def ini_value(text: str, section: str, key: str) -> str | None:
    """(PURE) The value the engine obeys: the LAST `key = value` of the LAST matching section (Memoria reads last-wins), comments and
    case of the names ignored; None when absent."""
    cur, got = None, None
    for raw in str(text or "").splitlines():
        ln = raw.strip()
        if not ln or ln.startswith((";", "#")):
            continue
        m = re.match(r"^\[(.+?)\]$", ln)
        if m:
            cur = m.group(1).strip().lower()
            continue
        if cur == section.lower() and "=" in ln:
            k, v = ln.split("=", 1)
            if k.strip().lower() == key.lower():
                got = v.split(";", 1)[0].strip().strip('"')
    return got


# ================================================================================================ the proof block
def proof_block(lines) -> dict:
    """(PURE) The selftest role's proof lines -> {head: tail} ('world walk selftest' -> 'OK (534 rows, 198 mutants)'), timestamps
    stripped, the LAST line per head kept (a re-armed role prints its block again)."""
    out = {}
    for ln in lines:
        m = PROOF_RE.search(str(ln))
        if m:
            out[m.group("head")] = m.group("tail")
    return out


def movers(kind: str, ww=None, sb=None, gm=None) -> dict:
    """(PURE) The heads ``kind`` may move, each with the exact tail it must read: old -- none (it IS the reference); bracket -- the seat
    bracket line alone (the pinned W1a/b build: everything else s167's); new -- the seat bracket, the guest menu and the world walk lines.
    ``ww`` / ``sb`` / ``gm`` the (rows, mutants) the s168 source derives."""
    if kind == "old":
        return {}
    out = {HEAD_SEAT_BRACKET: f"OK ({sb[0]} rows, {sb[1]} mutants caught)"}
    if kind == "new":
        out[HEAD_GUEST_MENU] = f"OK ({gm[0]} rows, {gm[1]} mutants caught)"
        out[HEAD_WORLD_WALK] = f"OK ({ww[0]} rows, {ww[1]} mutants)"
    elif kind != "bracket":
        raise ValueError(f"no proof kind {kind!r} (old, bracket, new)")
    return out


def proof_diff(ref, got: dict, moving: dict) -> tuple:
    """(PURE) (ok, lines): ``got`` against the s167 reference ``ref`` (None: never recorded). Red: a FAIL tail anywhere; a mover missing or
    off its want; a MUST_EQUAL head missing or different; with no reference, the MUST_EQUAL heads cannot be compared (red: NO REFERENCE).
    A NOTE (not red): any other head that differs, appears or disappears."""
    red, notes = [], []
    if not got:
        return False, ["RED no proof block in this leg's Memoria.log (not the selftest role, or the log is stale)"]
    for head, tail in sorted(got.items()):
        if tail.startswith("FAIL"):
            red.append(f"RED {head}: {tail[:160]}")
    for head, want in moving.items():
        have = got.get(head)
        if have != want:
            red.append(f"RED {head}: {have!r} (want {want!r}: the s168 source's)")
    if ref is None:
        red.append("RED NO REFERENCE: no s167 proof block recorded (round_gm_old.sh records it on the deployed s167) -- "
                   + ", ".join(MUST_EQUAL) + " not compared")
    else:
        for head in MUST_EQUAL:
            if head in moving:
                continue
            if ref.get(head) is None:
                notes.append(f"NOTE {head}: absent from the reference")
            elif got.get(head) != ref.get(head):
                red.append(f"RED {head}: {got.get(head)!r} (s167 {ref.get(head)!r}: must be identical)")
        for head in sorted(set(ref) | set(got)):
            if head in moving or head in MUST_EQUAL:
                continue
            if head not in got:
                notes.append(f"NOTE {head}: gone (s167 {ref[head][:80]!r})")
            elif head not in ref:
                notes.append(f"NOTE {head}: new ({got[head][:80]!r})")
            elif got[head] != ref[head]:
                notes.append(f"NOTE {head}: {got[head][:80]!r} (s167 {ref[head][:80]!r})")
    return not red, red + notes


def read_block(path) -> dict | None:
    """A saved block (one `head: tail` per line) -> {head: tail}; None when the file does not exist."""
    p = Path(path)
    if not p.is_file():
        return None
    out = {}
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if ": " in ln:
            h, t = ln.split(": ", 1)
            out[h] = t
    return out


def write_block(block: dict, path) -> None:
    Path(path).write_text("".join(f"{h}: {t}\n" for h, t in block.items()), encoding="utf-8")


def newest_log(game: Path, since: float) -> Path | None:
    """The engine log this leg wrote: the newest of <game>/Memoria.log and <game>/x64/Memoria.log (harness.session.engine_log's rule),
    and only when it was written at or after ``since`` (a stale log is never this leg's)."""
    cands = [p for p in (game / "Memoria.log", game / "x64" / "Memoria.log") if p.exists()]
    if not cands:
        return None
    p = max(cands, key=lambda q: q.stat().st_mtime)
    return p if p.stat().st_mtime >= float(since) else None


# ================================================================================================ the sources (THE STAGE LAW)
def _harness():
    sys.path.insert(0, str(WT / "tools"))
    sys.path.insert(0, str(WT / "studies" / "test-harness" / "scenarios"))
    from harness import battlewire as BW, fakegame as FG
    return BW, FG


def s168_wants() -> tuple:
    """(world walk, seat bracket, guest menu) tallies DERIVED from the s168 source ($FF9_S168_CLONE / an s168 patch), else the W1
    fallbacks -- the same readers GM0-PROOF uses."""
    _BW, FG = _harness()
    return (tuple(FG.world_walk_proof_tallies_s168()), tuple(FG.seat_bracket_proof_tallies()), tuple(FG.guest_menu_proof_tallies()))


def s167_clone_is_s168(env=None) -> str | None:
    """THE CLONE MOVED ON: $FF9_S167_CLONE naming a NetSyncWorldWalk.cs that carries the s168 tag (the shared clone holds s168 now) would
    make every s167 judge want s168's tallies (534 / 198, not 532 / 196) -- the path, or None."""
    env = os.environ if env is None else env
    raw = str(env.get("FF9_S167_CLONE", "") or "").strip()
    if not raw:
        return None
    hits = sorted(Path(raw).rglob("NetSyncWorldWalk.cs"))
    if hits and "[ff9mapkit netsync s168]" in hits[0].read_text(encoding="utf-8-sig", errors="replace"):
        return str(hits[0])
    return None


# ================================================================================================ the CLI
def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    if cmd == "window":
        ok, why = window_verdict(*(args + [NOT_AFTER_DEFAULT, NOT_BEFORE_DEFAULT])[:3])
        print(why)
        return 0 if ok else 1
    if cmd == "ports":
        ranges, note = excluded_now()
        if note:
            print("  note:", note)
        why = port_refusals([int(a) for a in args if str(a).strip().isdigit()], ranges, probe_port)
        for w in why:
            print(w)
        print(f"ports {' '.join(args)}: " + ("clear" if not why else f"{len(why)} refused"))
        return 0 if not why else 1
    if cmd == "ini":
        p = Path(args[0])
        val = ini_value(p.read_text(encoding="utf-8-sig", errors="replace"), args[1], args[2]) if p.is_file() else None
        print("" if val is None else val)
        return 0
    if cmd == "sources":
        BW, FG = _harness()
        moved = s167_clone_is_s168()
        s167 = FG.world_walk_engine_source(stage=167)
        print(f"   the s167 world walk source's tallies: {BW.world_walk_proof_counts(s167) if s167 else 'NO s167 source'} "
              f"(FF9_S167_CLONE={os.environ.get('FF9_S167_CLONE') or 'unset: the s167 patch post-image'})")
        ww, sb, gm = s168_wants()
        print(f"   the s168 source's tallies (FF9_S168_CLONE={os.environ.get('FF9_S168_CLONE') or 'unset'}): world walk {ww}, "
              f"seat bracket {sb}, guest menu {gm}")
        if moved:
            print(f"FF9_S167_CLONE names an s168 source ({moved}): every s167 judge would want s168's tallies -- unset it (the s167 "
                  "patch's post-image is the s167 source)")
            return 1
        return 0
    if cmd == "tape":
        sys.path.insert(0, str(WT / "tools"))
        sys.path.insert(0, str(WT / "studies" / "test-harness" / "scenarios"))
        import _coop_peer_bench as pb
        t = pb.latest_guest_menu_tape()
        print("" if t is None or not Path(t).is_file() else str(t))
        return 0
    if cmd == "proofs":
        game, since, out = Path(args[0]), float(args[1]), Path(args[2])
        log = newest_log(game, since)
        if log is None:
            print(f"   proofs: no Memoria.log written since the leg began under {game}")
            write_block({}, out)
            return 1
        block = proof_block(log.read_text(encoding="utf-8", errors="replace").splitlines())
        write_block(block, out)
        print(f"   proofs: {len(block)} proof line(s) from {log} -> {out.name}")
        return 0
    if cmd == "proofdiff":
        ref, got, kind = read_block(args[0]), read_block(args[1]) or {}, args[2]
        ww, sb, gm = s168_wants() if kind != "old" else (None, None, None)
        ok, lines = proof_diff(ref, got, movers(kind, ww, sb, gm))
        for ln in lines:
            print("     " + ln)
        print(f"   proof block {Path(args[1]).name} ({kind}): " + ("OK -- only the round's movers moved" if ok else "RED"))
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
