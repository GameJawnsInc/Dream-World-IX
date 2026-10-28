"""s157 -- THE GHOST FRAME's WIRE HALF (studies/field-coop/GUEST-TRAVERSAL-TWO-PC.md Finding 1;
memoria-patches/s157-netsync-climb-anim.patch), one game + the Python peer. [ff9mapkit netsync s157]

coop_climb_anim.py proves the SAMPLING on the selftest mirror (its wire frame is the body's own, read locally). This bench
proves the WIRE: the game is the HOST (its instance root's ini: Role host, RelayUrl the bench port), and
tools/harness/coop_peer.py serve-guest is its GUEST -- it mirrors the host's own type-0 frame back at +250 x and sends the
s157 trailer [animFrame][frameN] the way `--frame` says (echo / none / F/N [--frame-step S]), with `--anim` / `--loco`
pinning the clip and its class. The host's ghost of that guest frame-follows exactly those bytes, and its
`netsync.ghostframe` block is the verdict. GhostAs "" (the ghost wears the peer's wire body raw: the host's own Zidane, 98)
and GuestSlots 0. ONE CHANGE PER LEG: the peer is restarted for each leg (the engine redials every 2 s); a restart first
waits for the port to bind again (an exclusive bind refuses while the old connection's TIME_WAIT lasts -- the wait is noted).
Never `netsync selftest` here: the host role has no lever -- the calibration is the peer's `--frame none`.

  W0        the setup: an --instance root (no --attach); the bench port (COOP_PEER_PORT, default 49257 -- never the owner's
            49201 nor the world bench's 49231) free; newgame; warp 207 (env slots zeroed, scenario 2000 under 2030 / 2225);
            noencounter; the post-init witness; the ECHO peer listening (`--frame echo --tap <run>/s157.f9tape`); the host
            values into the root's ini; a same-field re-warp; the engine's own 'config enabled=True role=host ...
            relay=ws://127.0.0.1:<port> code=ff9-S157PEER' line; the peer's 'HOST game connected' and the engine's relay line.
  P0        THE SENDER: the peer's first type-0 EDGE line is 'host type-0: 39 B -- the s157 frame bytes (frame F of N)'
            (coop_peer.HOST_TRAILER_LINE; J.judge_sender) and none says it stopped; netsync.session.ghost true and
            dress.ghost.model 98 (the host's ghost of the peer, raw).
  P-HOLD    the host's stock 207 climb up with a HANG (40 u past the mount, release, 2.5 s with no key): after 1 s the ghost
            HOLDS the echoed frame (J.judge_hold, wire_tol 1: the echo may trail the body by a tick).
  P-TRACK   that climb after the hang: the climb lands, and the ghost is driven (J.judge_track).
  P-TAPE    the echo peer's tape (read in-process -- what `py tools/harness/coop_peer.py dump <run>/s157.f9tape` prints):
            every HOST type-0 record carries the trailer (39 B: its dump line ends ' frame f/n').
  P-CAL-37  THE CALIBRATION RED, IN RUN: the peer restarted `--frame none` (a pre-s157 37-byte guest); the climb down with a
            hang: the ghost FREE-RUNS (J.frame_red_marker why "no_frame" over the hang, GREEN) and is never frozen over the
            climb (J.judge_freerun_guard why "no_frame", GREEN).
  P-GUARD   the host at rest; `--anim 10539 --loco 0` with `--frame 3/1`, `3/255`, `0/0` -> why "frame_n" each; then
            `--frame 5/12 --loco 1` -> why "loco" (J.judge_freerun_guard: follow false, speed 1, that why on every publish).
  P-PIN     `--anim 10539 --loco 0 --frame 5/12`, the host still: after 1 s the ghost holds 5 of 12 on the clip
            ANH_MAIN_F0_ZDN_LADDER_1_2 (BW.anim_name(10539); J.judge_pinned).
  P-SEAM    `--frame 10/12 --frame-step 1` then `--frame 1/12 --frame-step -1` (each 2.5 s after a 1 s settle): the ghost
            crosses the loop seam the wire's way (J.judge_seam: wraps +4, steps +40, at most one snap, time never against
            the direction over the JUDGED pairs -- a read gap the wire moved a quarter loop or more across is skipped, and at
            least 75% of the pairs must be judged).
  then      the peer stopped, the root's ini restored (Instance.restore_ini), Memoria.log archived (the peer logs and the
            tape are in the run dir already), and THE GAME QUIT (Session.quit; never an --attach'd game).

THE CALIBRATION. On the s156 DLL (no `netsync.ghostframe`) the bench calibrates AUTOMATICALLY: P-HOLD, P-TRACK, P-CAL-37,
P-GUARD, P-PIN and P-SEAM are DROPPED as N/A (not present: never scored); PREDICTED_S156 = P0 (the s156 host sends 37 B: the
peer logs NO trailer edge -- marker: connected, zero edges) and P-TAPE (every host type-0 record 37 B -- marker: >= 1 record,
none framed) red. K-CAL-M is green only when both carry their markers; K-CAL only when exactly those two are red.

THE PREREQS: as coop_climb_anim.py's (the owner's go, the s157 deploy + a relaunch; the instance root; no other FF9 from it;
no controller; nobody at the keyboard; outside 04:00-06:15); the bench port free (no production bridge, no other peer on
it). Never --attach or --keep-open.

    py tools/play.py studies/test-harness/scenarios/coop_climb_anim_peer.py --instance C:\\gd\\ff9-inst\\host
    COOP_PEER_PORT=49258 py tools/play.py studies/test-harness/scenarios/coop_climb_anim_peer.py --instance C:\\gd\\ff9-inst\\host

EXPECTED (tally(mode)): on the s156 DLL 3/5 (K-CAL-M + K-CAL green); on s157 9/9.

NOT PROVEN HERE: a REAL guest's sender (coop_peer echoes the host's own bytes; the duo -- coop_follow_race_duo -- and the
two-PC session prove a guest engine's 39-B frame); a dressed sender (the twin branch of FollowsWireAnim: coop_dress_wire).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _coop_battle as cb                                  # noqa: E402 - the shared bench helpers beside this file
import _coop_peer_bench as pb                              # noqa: E402 - the peer process, the engine log, the port probe
import _climb_anim_judges as J                             # noqa: E402 - the s157 pure judges
import coop_climb_anim as ca                               # noqa: E402 - the solo bench: the hang, the timeline, _quit
import coop_guest_traversal as gt                          # noqa: E402 - s156's climb drivers, geometry, recover

try:                                                       # play.py puts THIS worktree's tools/ first on sys.path
    from harness import battlewire as BW                   # noqa: E402
except ImportError:                                        # pragma: no cover - imported outside the driver
    sys.path.insert(0, str(cb.REPO / "tools"))
    from harness import battlewire as BW                   # noqa: E402

HarnessError = cb.HarnessError

FIELD = 207                              # Prima Vista/Cabin: the stock ladder the host climbs (its own Zidane, model 98)
PORT_ENV = "COOP_PEER_PORT"
DEFAULT_PORT = 49257                     # never pb.OWNER_PORT (49201) nor pb.WORLD_PORT (49231)
CODE = "ff9-S157PEER"                    # GenerateSessionCode's shape: "ff9-" + 8
OFFSET = "250,0,0"                       # the ghost's spot beside the host
PIN_ANIM = 10539                         # Zidane's LADDER_1_2 (BW.TWIN_ROWS' source id): a clip the ghost can follow
PIN = (5, 12)
GUARDS = (("3/1", 0, "frame_n"), ("3/255", 0, "frame_n"), ("0/0", 0, "frame_n"), ("5/12", 1, "loco"))
SEAMS = (("10/12", 1), ("1/12", -1))
SEAM_MIN_WRAPS, SEAM_MIN_STEPS = 4, 40
SETTLE_S = ca.SETTLE_S
SAMPLE_S = 1.5                           # a pinned / guarded window
SEAM_S = 2.5
LISTEN_S = 15.0
CONNECT_S = 25.0                         # the engine redials every 2 s
GHOST_S = 10.0                           # the new peer's bytes reach the ghost
REBIND_S = 240.0                         # the port binds again (an exclusive bind refuses during the old TIME_WAIT)
CONFIG_FIRST_S, CONFIG_SECOND_S = 6.0, 10.0
LEDGER_WIDTH = 2400

CLAIMS = {
    "W0": "the setup: an --instance root, a fresh process, the bench port free and not the owner's / world bench's, 207's "
          "post-init witness, the echo peer listening, the host values in the ROOT's ini, the engine's host config line on "
          "the bench relay + code, the peer's HOST connected and the engine's relay line",
    "P0": "the sender: the peer's first type-0 edge is the 39-B s157 trailer and none says it stopped; session.ghost true "
          "and dress.ghost.model the host's own body (98)",
    "P-HOLD": "the 207 climb's hang: after 1 s the host's ghost HOLDS the echoed frame (judge_hold, wire_tol 1)",
    "P-TRACK": "the climb after the hang: the climb lands and the ghost is driven (judge_track)",
    "P-TAPE": "the echo peer's tape: every HOST type-0 record carries the trailer (39 B)",
    "P-CAL-37": "the peer `--frame none` (37 B): over the hang frame_red_marker(why 'no_frame') GREEN and over the climb "
                "judge_freerun_guard(why 'no_frame') GREEN; the climb lands",
    "P-GUARD": "the host at rest, `--anim 10539 --loco 0`: frame 3/1, 3/255, 0/0 free-run with why 'frame_n'; frame 5/12 "
               "with loco 1 free-runs with why 'loco'",
    "P-PIN": "`--frame 5/12` pinned, the host still: the ghost holds 5 of 12 on ANH_MAIN_F0_ZDN_LADDER_1_2 (judge_pinned)",
    "P-SEAM": "`--frame 10/12 --frame-step 1` and `1/12 --frame-step -1`: the ghost crosses the loop seam the wire's way "
              "(judge_seam: wraps +4, steps +40, at most one snap; a read gap of a quarter loop or more is skipped)",
}
NA_S156 = ("P-HOLD", "P-TRACK", "P-CAL-37", "P-GUARD", "P-PIN", "P-SEAM")
PREDICTED_S156 = ("P0", "P-TAPE")
MARKER_TEXT = ("P0: the peer connected and logged ZERO trailer edges (a 37-B host); P-TAPE: >= 1 host type-0 record, none "
               "framed")
FINALS = ("K-CAL-M", "K-CAL")


def mode_of(s157: bool) -> str:
    return "plain" if s157 else "s156"


def predicted(mode: str) -> tuple:
    return PREDICTED_S156 if mode == "s156" else ()


def catalog(mode: str) -> dict:
    c = {k: v for k, v in CLAIMS.items() if not (mode == "s156" and k in NA_S156)}
    if mode == "s156":
        c["K-CAL-M"] = f"CALIBRATION: every predicted red carries its marker ({MARKER_TEXT})"
        c["K-CAL"] = f"CALIBRATION (the s156 DLL, automatic): exactly {', '.join(PREDICTED_S156)} red (K-CAL-M green)"
    return c


def tally(mode: str) -> tuple:
    n = len(catalog(mode))
    return n - len(predicted(mode)), n


def port_from_env() -> int:
    try:
        return int(os.environ.get(PORT_ENV, "") or DEFAULT_PORT)
    except ValueError:
        return DEFAULT_PORT


def host_values(port: int) -> dict:
    return {"Enabled": "1", "Role": "host", "RelayUrl": f"ws://127.0.0.1:{port}", "SessionCode": CODE, "GhostAs": "",
            "GuestSlots": "0"}


def peer_args(port: int, extra=()) -> list:
    """serve-guest's argv after the mode: the bench port, the +250 x offset, a status line every 5 s, then the leg's knobs."""
    return ["--port", str(port), "--offset", OFFSET, "--status", "5", *[str(a) for a in extra]]


def pinned_args(frame: str, *, loco: int = 0, step: int = 0) -> list:
    return ["--anim", str(PIN_ANIM), "--loco", str(loco), "--frame", frame] + (["--frame-step", str(step)] if step else [])


# ================================================================================================ the pure judges
def tape_frames(cp, path) -> dict:
    """The HOST's type-0 records of a serve-guest tape: {"n", "framed" (39 B and more: the s157 trailer), "sizes", "err"}."""
    out = {"n": 0, "framed": 0, "sizes": [], "err": None}
    try:
        _hdr, records, torn = cp.read_tape(path)
    except Exception as err:                             # noqa: BLE001 - an unreadable tape is a red, not a crash
        out["err"] = f"{type(err).__name__}: {str(err)[:160]}"
        return out
    sizes = set()
    for r in records:
        if r.dir != cp.DIR_HOST:
            continue
        got = cp.parse_frame(r.payload)
        if got is None or got[0] != cp.TYPE_POS:
            continue
        p = cp.parse_pos_payload(got[1])
        if p is None:
            continue
        out["n"] += 1
        out["framed"] += bool(p["has_frame"])
        sizes.add(len(got[1]))
    out["sizes"] = sorted(sizes)
    out["torn"] = torn
    return out


def judge_tape(f: dict) -> tuple:
    ok = f.get("err") is None and f.get("n", 0) > 0 and f.get("framed") == f.get("n")
    return ok, (f"{f.get('framed')}/{f.get('n')} host type-0 records framed (payload sizes {f.get('sizes')})"
                + (f"; {f['err']}" if f.get("err") else ""))


def tape_marker(f: dict) -> tuple:
    ok = f.get("err") is None and f.get("n", 0) > 0 and f.get("framed") == 0
    return ok, f"{f.get('n')} host type-0 records, {f.get('framed')} framed (sizes {f.get('sizes')})"


def sender_marker(rec: dict) -> tuple:
    """P0's predicted red on an s156 host: the peer CONNECTED (the instrument ran) and logged no trailer edge at all."""
    edges = J.host_trailer_edges(rec.get("lines") or [])
    ok = bool(rec.get("connected")) and not edges
    return ok, f"connected {bool(rec.get('connected'))}, {len(edges)} trailer edge(s)"


def judge_markers(marks: dict) -> tuple:
    seen = {"P0": sender_marker(marks.get("P0") or {}), "P-TAPE": tape_marker(marks.get("P-TAPE") or {})}
    return all(ok for ok, _ in seen.values()), "; ".join(f"{c} SEEN" if ok else f"{c} NOT seen ({w})"
                                                         for c, (ok, w) in seen.items())


# ================================================================================================ acting
class Ctx:
    def __init__(self, mode: str, s157: bool, has_gl: bool, port: int):
        self.mode, self.s157, self.port = mode, s157, port
        self.g = gt.Ctx("plain", has_gl)
        self.peer = None
        self.peers: list = []
        self.eng = None
        self.ini_edited = False
        self.tape = None
        self.marks: dict = {}
        self.setup_ok = False


def _run_dir(g) -> Path:
    return Path(getattr(g, "scenario_dir", None) or g.run_dir)


def _config_hits(ctx: Ctx) -> list:
    return pb.hits(ctx.eng.lines(), "config", pred=lambda m: m.group(1) == "True" and m.group(2) == "host"
                   and m.group(5) == f"ws://127.0.0.1:{ctx.port}" and m.group(6) == CODE)


def _scenario_207(g):
    return gt.SC_SAFE_207 if g.state.scenario in gt.SC_UNARMED_207 else None


def _arrive(g, why: str) -> tuple:
    ca._warp(g, FIELD, _scenario_207(g))
    st = cb.poll(g, lambda s: gt.arrived(s, FIELD)[0], ca.ARRIVE_S, f"207's post-init witness ({why})")
    return gt.arrived(st or g.state, FIELD)


def stop_peer(g, ctx: Ctx) -> None:
    if ctx.peer is not None and ctx.peer.how_ended is None:
        g.note(f"coop_peer serve-guest ({ctx.peer.log_path.name}): {ctx.peer.stop()}")


def start_peer(g, ctx: Ctx, name: str, extra=()) -> tuple:
    """ONE change: stop the running peer, wait for the port to bind again, start ``extra``'s peer, wait for it to listen and
    for the host to dial it. (ok, why)."""
    stop_peer(g, ctx)
    t0 = time.time()
    free, why = pb.port_free(ctx.port)
    while not free and time.time() - t0 < REBIND_S:
        time.sleep(1.0)
        free, why = pb.port_free(ctx.port)
    waited = time.time() - t0
    if not free:
        return False, f"the port never bound again within {REBIND_S:g} s: {why}"
    rd = _run_dir(g)
    p = pb.PeerProc("serve-guest", peer_args(ctx.port, extra), log_path=rd / f"coop_peer-{name}.log",
                    out_path=rd / f"coop_peer-{name}.out")
    g.note(f"starting ({name}{f', after {waited:.0f} s for the port' if waited >= 1 else ''}): {p.command_text()}")
    p.start()
    ctx.peer = p
    ctx.peers.append(p)
    up = p.wait_for(pb.PEER["listening"], LISTEN_S)
    err = p.first(pb.PEER["error"])
    if up is None or err is not None:
        return False, f"the peer never listened ({err[1] if err else p.tail()})"
    conn = p.wait_for(pb.PEER["host_connected"], CONNECT_S)
    if conn is None or conn[2].group(1) != CODE:
        return False, f"the host never dialled the peer ({conn[1] if conn else p.tail()})"
    return True, conn[1]


def _ghost_reads(g, pred, what: str):
    return cb.poll(g, pred, GHOST_S, what)


def _gf(x, key):
    return cb.path(x, ca.GF_KEY + "." + key)


def pose_host(g, ctx: Ctx, leg: str, pose: str) -> tuple:
    """coop_guest_traversal.ensure_pose's ladder branch WITHOUT `bench 0` (the bench is a selftest-role verb; this game is a
    host, every climb already the stock one): the far end's press region, a stock repositioning climb (a NOTE), the stand."""
    spec, regions = gt.LADDERS[FIELD], gt.GEOM[FIELD]["regions"]
    st = gt.rest(g)
    want = regions[spec["entry_up"] if pose == "bottom" else spec["entry_down"]]
    if gt.floor_of(st, FIELD) != pose:
        src_stand, src_entry = ((spec["stand_bottom"], spec["entry_up"]) if pose == "top"
                                else (spec["stand_top"], spec["entry_down"]))
        p = gt.pos(st)
        if p is None or not gt.in_quad(p[0], p[2], regions[src_entry]):
            ok, why = gt.go_to(g, FIELD, src_stand, regions[src_entry])
            if not ok:
                return False, f"the reposition could not reach its press region: {why}"
        way = "up" if pose == "top" else "down"
        res = gt.ladder_run(g, ctx.g, f"{leg}:reposition", FIELD, way, act=False)
        land = spec["land_top"] if way == "up" else spec["land_bottom"]
        landed = res.get("land") is not None and gt.landed_at(res["land"], land)
        g.note(f"reposition for {leg}: a stock climb {way} on {FIELD} (a note, not a check) -> "
               f"{'landed' if landed else 'DID NOT LAND'}")
        if not landed:
            if not gt.control(g.state):
                gt.recover(g, FIELD)
            return False, f"the reposition {way} did not land"
    p = gt.pos(gt.rest(g))
    if p is None or not gt.in_quad(p[0], p[2], want):
        return gt.go_to(g, FIELD, spec["stand_bottom"] if pose == "bottom" else spec["stand_top"], want)
    return True, ""


def climb_host(g, ctx: Ctx, leg: str, direction: str, pose: str) -> dict:
    """The host's own stock climb with a hang (coop_climb_anim's hang_on_mount: a SEEN mount first)."""
    ok, why = pose_host(g, ctx, leg, pose)
    if not ok:
        return {"pose_why": f"its start pose ({pose} on {FIELD}) was not reached: {why}"}
    spec = gt.LADDERS[FIELD]
    res = gt.ladder_run(g, ctx.g, leg, FIELD, direction, act=False, on_mount=ca.hang_on_mount(None, FIELD, direction))
    res["climb"] = gt.judge_ladder(res, spec, direction, act=False, has_key=False)
    res["climb_mid"] = gt.mid_samples(ca._after_hang(res), spec)
    if not gt.control(g.state):
        gt.recover(g, FIELD)
    return res


def _window(g, seconds: float) -> list:
    """SETTLE_S of nothing, then ``seconds`` of raw publishes (a ghost judge's window)."""
    cb.hold_for(g, SETTLE_S)
    return [cb.raw(s) for s in cb.hold_for(g, seconds)]


def _act(g, led: cb.Ledger, rows, fn) -> None:
    rows = [r for r in rows if r in led.catalog and r not in led.done]
    if not rows:
        return
    try:
        fn()
    except HarnessError as err:
        led.unreached(rows, f"the leg raised: {str(err)[:240]}")
        gt.recover(g, FIELD)
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the run goes on
        g.note(f"{rows[0]} FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        led.unreached(rows, f"the leg FAULTED (a bench bug): {err!r}"[:300])
        gt.recover(g, FIELD)
    led.unreached(rows, "the leg recorded nothing")


# ================================================================================================ the run
def run(g, field: int | None = None):
    st0 = cb.poll(g, lambda s: s.netsync is not None, 15.0, "the netsync block (protocol 5)") or g.state
    s157 = cb.has(st0, ca.GF_PROBE)
    ctx = Ctx(mode_of(s157), s157, cb.has(st0, gt.PROBE), port_from_env())
    led = cb.Ledger(g, catalog(ctx.mode), finals=FINALS, width=LEDGER_WIDTH)
    if field is not None:
        g.note(f"--field {field} is ignored: the wire half runs on {FIELD}")
    g.note(f"s157 ghost frame, the WIRE half: the game is the HOST, coop_peer serve-guest its guest on port {ctx.port}; the "
           f"engine reads as {'s157' if s157 else 's156 or older'}; expected {'%d/%d' % tally(ctx.mode)}")
    if not s157:
        g.note("s156: THE AUTOMATIC CALIBRATION -- no netsync.ghostframe: " + ", ".join(NA_S156) + " are dropped as N/A "
               "(never scored); predicted RED: " + ", ".join(PREDICTED_S156) + f" ({MARKER_TEXT})")
    try:
        ctx.setup_ok = _setup(g, ctx, led)
        if not ctx.setup_ok:
            led.close("not reached: W0 (the setup) refused")
            return
        _p0_hold_track(g, ctx, led)
        _act(g, led, ("P-TAPE",), lambda: _p_tape(g, ctx, led))
        _act(g, led, ("P-CAL-37",), lambda: _p_cal37(g, ctx, led))
        _act(g, led, ("P-GUARD",), lambda: _p_guard(g, ctx, led))
        _act(g, led, ("P-PIN",), lambda: _p_pin(g, ctx, led))
        _act(g, led, ("P-SEAM",), lambda: _p_seam(g, ctx, led))
    except HarnessError as err:
        g.note(f"the run raised: {str(err)[:400]}")
        led.close(f"not reached: the run raised ({str(err)[:200]})")
    except Exception as err:                             # noqa: BLE001 - a BENCH bug: red and loud, the finally still runs
        g.note(f"the run FAULTED (a bench bug, not a verdict): {err!r}"[:400])
        led.close(f"not reached: the run FAULTED (a bench bug): {err!r}"[:300])
    finally:
        _finish(g, ctx, led)


def _finish(g, ctx: Ctx, led: cb.Ledger) -> None:
    """THE TEARDOWN, every step guarded: the peer FIRST (its tape closes; a restored config dialling the same port must find
    nobody), the root's ini, the log, the calibration verdicts, the ledger -- and, LAST, the game quit."""
    try:
        ca._safe(g, "the key release", lambda: gt._release_all(g))
        ca._safe(g, "the peer stop", lambda: stop_peer(g, ctx))
        if ctx.ini_edited:
            ca._safe(g, "the ini restore", lambda: g.note(
                f"the instance root's Memoria.ini put back to install + overlay: "
                f"{'rewritten' if g.instance.restore_ini() else 'already so'}"))
        ca._safe(g, "the log archive", lambda: g.note(f"Memoria.log archived: {cb.archive_log(g, 'climb-anim-peer-' + ctx.mode)}"
                                                       f"; the peer logs: {[str(p.log_path) for p in ctx.peers]}"))
        if ctx.mode == "s156":
            led.close("not reached: the run ended before this check")
            ok, why = judge_markers(ctx.marks)
            led.check("K-CAL-M", ok, why)
            led.judge_calibration("K-CAL", PREDICTED_S156)
        led.close(final=True)
    finally:
        ca._quit(g)


def _setup(g, ctx: Ctx, led: cb.Ledger) -> bool:
    cb.provenance(g)
    if getattr(g, "attach", False):
        led.check("W0", False, "refused: --attach (a fresh process: the ghost-frame counters are per process)")
        return False
    if getattr(g, "instance", None) is None:
        led.check("W0", False, "refused: no --instance root (the bench writes the HOST values into an instance ROOT's "
                               "Memoria.ini, never the shared install's)")
        return False
    if ctx.port in (pb.OWNER_PORT, pb.WORLD_PORT):
        led.check("W0", False, f"refused: {PORT_ENV}={ctx.port} is the owner's bridge / the world bench's port")
        return False
    free, why = pb.port_free(ctx.port)
    if not free:
        led.check("W0", False, f"refused: {why} -- nothing was edited")
        return False
    try:
        g.newgame()
        a_ok, a_why = _arrive(g, "after New Game")
    except HarnessError as err:
        led.check("W0", False, f"newgame / warp {FIELD} failed: {str(err)[:300]}")
        return False
    try:
        g.no_encounters(True)
    except (HarnessError, AttributeError) as err:
        g.note(f"noencounter refused ({str(err)[:120]}) -- a random battle may interrupt a leg")
    if not a_ok:
        led.check("W0", False, f"no post-init witness on {FIELD}: {a_why}")
        return False
    ctx.eng = pb.EngineLog(g.engine_log())
    ctx.tape = _run_dir(g) / "s157.f9tape"
    rd = _run_dir(g)
    ctx.peer = pb.PeerProc("serve-guest", peer_args(ctx.port, ["--frame", "echo", "--tap", ctx.tape]),
                           log_path=rd / "coop_peer-echo.log", out_path=rd / "coop_peer-echo.out")
    g.note(f"starting FIRST: {ctx.peer.command_text()}")
    ctx.peer.start()
    ctx.peers.append(ctx.peer)
    up = ctx.peer.wait_for(pb.PEER["listening"], LISTEN_S)
    err = ctx.peer.first(pb.PEER["error"])
    if up is None or err is not None:
        led.check("W0", False, f"the echo peer never listened ({err[1] if err else ctx.peer.tail()}) -- nothing was edited")
        return False
    ctx.ini_edited = True
    try:
        bak = g.instance.netsync(host_values(ctx.port), backup_to=rd / "ini")
        g.note(f"the instance ini: [Netsync] {host_values(ctx.port)} (backup {bak})")
    except Exception as err:                             # noqa: BLE001 - an ini write never kills the run
        led.check("W0", False, f"the instance ini edit failed: {err!r}"[:400])
        return False
    a2_ok, a2_why = _arrive(g, "the same-field re-warp: Ensure reads the ini at a field load")
    cfg = _wait_config(g, ctx)
    conn = ctx.peer.wait_for(pb.PEER["host_connected"], CONNECT_S)
    relay = pb.hits(ctx.eng.lines(), "relay_up", pred=lambda m: m.group(3) == "host" and m.group(2) == CODE)
    ok = a2_ok and bool(cfg) and conn is not None and conn[2].group(1) == CODE and bool(relay)
    led.check("W0", ok, f"207: {a2_why}; config: {pb.show(cfg, 1)}; peer: {up[1]} / "
                        f"{conn[1] if conn else 'no HOST connection: ' + ctx.peer.tail(3)}; engine relay: {pb.show(relay, 1)}")
    return ok


def _wait_config(g, ctx: Ctx) -> list:
    """The engine's host config line on the bench relay + code; one more same-field re-warp if it is slow (a running
    NetSyncClient polls the ini every 2 s; without one only a field load's Ensure reads it)."""
    for i, wait in enumerate((CONFIG_FIRST_S, CONFIG_SECOND_S)):
        deadline = time.time() + wait
        while time.time() < deadline:
            found = _config_hits(ctx)
            if found:
                return found
            time.sleep(0.25)
        if i == 0:
            g.note("no host config line yet -- one more same-field re-warp")
            try:
                _arrive(g, "the config re-warp")
            except HarnessError as err:
                g.note(f"the config re-warp failed: {str(err)[:200]}")
    return _config_hits(ctx)


def _p0_hold_track(g, ctx: Ctx, led: cb.Ledger) -> None:
    """P0 on the echo peer that W0 started, then (s157) the climb with a hang -- P-HOLD and P-TRACK."""
    st = _ghost_reads(g, lambda s: cb.path(s, "netsync.session.ghost") is True
                      and cb.path(s, "netsync.dress.ghost.model") == gt.GEOM[FIELD]["body"], "the host's ghost of the peer")
    st = st or g.state
    time.sleep(0.5)                                      # the peer logs the first host frame's edge on receipt
    lines = [m for _, m in ctx.peer.lines()]
    s_ok, s_why = J.judge_sender(lines)
    gh, model = cb.path(st, "netsync.session.ghost"), cb.path(st, "netsync.dress.ghost.model")
    ctx.marks["P0"] = {"lines": lines, "connected": bool(ctx.peer.find(pb.PEER["host_connected"]))}
    led.check("P0", s_ok and gh is True and model == gt.GEOM[FIELD]["body"],
              f"{s_why}; session.ghost {gh!r}, dress.ghost.model {model!r} (want {gt.GEOM[FIELD]['body']})")
    if "P-HOLD" not in led.catalog:
        return

    def legs():
        res = climb_host(g, ctx, "P-HOLD", "up", "bottom")
        if "pose_why" in res:
            led.unreached(["P-HOLD", "P-TRACK"], res["pose_why"])
            return
        led.check("P-HOLD", *J.judge_hold(res.get("hang") or [], wire_tol=1))
        c_ok, c_why = res["climb"]
        t_ok, t_why = J.judge_track(res["climb_mid"])
        led.check("P-TRACK", c_ok and t_ok, f"climb: {c_why} || track: {t_why}")
    _act(g, led, ("P-HOLD", "P-TRACK"), legs)


def _p_tape(g, ctx: Ctx, led: cb.Ledger) -> None:
    """The echo peer's tape, read after its stop (the tape closes): every host type-0 record framed."""
    stop_peer(g, ctx)
    f = tape_frames(pb.coop_peer_module(), ctx.tape)
    ctx.marks["P-TAPE"] = f
    ok, why = judge_tape(f)
    led.check("P-TAPE", ok, why + f" -- py tools/harness/coop_peer.py dump {ctx.tape}")


def _p_cal37(g, ctx: Ctx, led: cb.Ledger) -> None:
    ok, why = start_peer(g, ctx, "none", ["--frame", "none"])
    if not ok:
        led.unreached(["P-CAL-37"], f"the 37-B peer: {why}")
        return
    st = _ghost_reads(g, lambda s: _gf(s, "has_frame") is False and cb.path(s, "netsync.session.ghost") is True,
                      "the ghost on 37-B frames")
    if st is None:
        led.check("P-CAL-37", False, "the ghost never read has_frame false on the 37-B peer")
        return
    res = climb_host(g, ctx, "P-CAL-37", "down", "top")
    if "pose_why" in res:
        led.unreached(["P-CAL-37"], res["pose_why"])
        return
    m_ok, m_why = J.frame_red_marker(res.get("hang") or [], why="no_frame")
    f_ok, f_why = J.judge_freerun_guard(res["climb_mid"], why="no_frame")
    c_ok, c_why = res["climb"]
    led.check("P-CAL-37", m_ok and f_ok and c_ok, f"hang: {m_why} || climb: {f_why} || {c_why}")


def _p_guard(g, ctx: Ctx, led: cb.Ledger) -> None:
    parts, why = [], []
    for frame, loco, want in GUARDS:
        f, n = (int(v) for v in frame.split("/"))
        ok, w = start_peer(g, ctx, f"guard-{frame.replace('/', 'of')}-loco{loco}", pinned_args(frame, loco=loco))
        if not ok:
            parts.append((f"{frame} loco {loco}", False))
            why.append(f"{frame} loco {loco}: the peer: {w}")
            continue
        st = _ghost_reads(g, lambda s, n=n, loco=loco: _gf(s, "wire_anim") == PIN_ANIM and _gf(s, "wire_frame_n") == n
                          and _gf(s, "wire_loco") == loco, f"the ghost on {frame} loco {loco}")
        s = _window(g, SAMPLE_S)
        ok, w = J.judge_freerun_guard(s, why=want)
        ok = ok and st is not None
        parts.append((f"{frame} loco {loco} -> {want}", ok))
        why.append(f"{frame} loco {loco}: {w}" + ("" if st is not None else " (the pinned bytes never reached the ghost)"))
    led.check("P-GUARD", bool(parts) and all(v for _, v in parts), gt._parts(parts) + " -- " + "; ".join(why))


def _p_pin(g, ctx: Ctx, led: cb.Ledger) -> None:
    f, n = PIN
    ok, why = start_peer(g, ctx, "pin", pinned_args(f"{f}/{n}"))
    if not ok:
        led.unreached(["P-PIN"], f"the pinned peer: {why}")
        return
    st = _ghost_reads(g, lambda s: _gf(s, "wire_frame") == f and _gf(s, "wire_frame_n") == n, "the pinned frame")
    s = _window(g, SAMPLE_S)
    ok, why = J.judge_pinned(s, f, n, clip=BW.anim_name(PIN_ANIM))
    led.check("P-PIN", ok and st is not None, why + ("" if st is not None else " (the pinned bytes never reached the ghost)"))


def _p_seam(g, ctx: Ctx, led: cb.Ledger) -> None:
    parts, why = [], []
    for frame, step in SEAMS:
        ok, w = start_peer(g, ctx, f"seam{step:+d}", pinned_args(frame, step=step))
        if not ok:
            parts.append((f"step {step:+d}", False))
            why.append(f"step {step:+d}: the peer: {w}")
            continue
        n = int(frame.split("/")[1])
        st = _ghost_reads(g, lambda s, n=n: _gf(s, "wire_anim") == PIN_ANIM and _gf(s, "wire_frame_n") == n
                          and _gf(s, "follow") is True, f"the ghost following the {step:+d} stepper")
        s = _window(g, SEAM_S)
        ok, w = J.judge_seam(s, direction=step, min_wraps=SEAM_MIN_WRAPS, min_steps=SEAM_MIN_STEPS)
        parts.append((f"step {step:+d}", ok and st is not None))
        why.append(f"step {step:+d}: {w}")
    led.check("P-SEAM", bool(parts) and all(v for _, v in parts), gt._parts(parts) + " -- " + "; ".join(why))
