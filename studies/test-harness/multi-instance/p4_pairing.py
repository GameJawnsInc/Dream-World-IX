"""Multi-instance probe P4: the two instance roots PAIR over loopback -- a real host game and a real guest game.

    py studies/test-harness/multi-instance/p4_pairing.py --leg relay     # T-relay-direct: both games dial the relay
    py studies/test-harness/multi-instance/p4_pairing.py --leg bridge    # T-bridge-local: one bridge per player -> relay
    py studies/test-harness/multi-instance/p4_pairing.py --leg bridge --cut-for 6     # P5: + a 6 s host-side cut (K1-K5)

A local `coop_peer relay` on a private port (7787) with --tap; for --leg bridge, one netsync_bridge PROCESS per player on
49211 / 49212 (--relay ws://127.0.0.1:7787). A FRESH SessionCode per run (never the owner's). Each root's OWN Memoria.ini gets
its role's [Netsync] values through _coop_peer_bench.IniGuard (backed up to the run dir, restored on the way out; the real
install's ini is never touched). Checks, in order -- the leg STOPS at the first red (the owner's rule: stop at a surprise):
  C1 the relay (and bridges) listening   C2 each game's own config line (role, url, code)   C3 'relay connected ...?role='
  for host AND guest   C4 the guest 'paired on the host's field (250)'   C5 a ghost spawned on 250 in BOTH games   C6 the
  guest 'state-mirror ARMED'   C7 the guest's story byte 1121 reads the HOST's 0xA5   C8 the host's own battle published
  ('battle intro:') and the guest 'diorama BOOT scene=67' + 'diorama LIVE' on its nonce. Informational: the host's s114 start
  hold lines (a REAL guest report now).
Prereqs: both roots built (instance_root.py), no FF9 running, no controller connected, nobody at the keyboard.
"""
import argparse
import contextlib
import ctypes
import datetime as _dt
import json
import random
import re
import string
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "tools"))
sys.path.insert(0, str(WT / "ff9mapkit"))
sys.path.insert(0, str(WT / "studies" / "test-harness" / "scenarios"))
import harness                                                     # noqa: E402
assert Path(harness.__file__).resolve().is_relative_to(WT), harness.__file__
from harness import Session                                        # noqa: E402
from harness.session import ff9_pids                               # noqa: E402
from ff9mapkit.hangdump import process_image_path                  # noqa: E402
import _coop_battle as cb                                          # noqa: E402
import _coop_peer_bench as pb                                      # noqa: E402

HOST, GUEST = Path(r"C:\gd\ff9-inst\host"), Path(r"C:\gd\ff9-inst\guest")
FIELD, SCENE = 250, 67
RELAY_PORT, BRIDGE_PORTS = 7787, {"host": 49211, "guest": 49212}
BRIDGE = WT / "ff9mapkit" / "ff9mapkit" / "netsync_bridge.py"
RELAY_LISTENING = re.compile(r"^relay listening on ws://127\.0\.0\.1:(\d+)")      # coop_peer.py's relay mode banner


class Red(Exception):
    pass


def probe_for(root: Path):
    exe = (root / "x64" / "FF9.exe").resolve()

    def probe() -> list:
        out = []
        for pid in ff9_pids():
            try:
                if Path(process_image_path(pid)).resolve() == exe:
                    out.append(pid)
            except OSError:
                pass
        return out
    return probe


def wait_hits(eng: pb.EngineLog, name: str, timeout: float, pred=None, after=None) -> list:
    t0 = time.time()
    while time.time() - t0 < timeout:
        found = pb.hits(eng.lines(), name, pred=pred, after=after)
        if found:
            return found
        time.sleep(0.25)
    return []


def wait_bound(port: int, timeout: float) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not pb.port_free(port)[0]:
            return True
        time.sleep(0.2)
    return False


SITTING_A = WT / ".harness-runs" / "sittingA-20261014" / "laptop-Memoria.log"     # gitignored archive (s117 guest)
_K32 = ctypes.WinDLL("kernel32", use_last_error=True)
_K32.OpenProcess.restype = wintypes.HANDLE
_K32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
_NT = ctypes.WinDLL("ntdll")
_NT.NtSuspendProcess.argtypes = _NT.NtResumeProcess.argtypes = (wintypes.HANDLE,)


def suspend_for(pid: int, secs: float) -> tuple:
    """NtSuspendProcess the bridge for `secs`: its game hop and relay leg stay OPEN, nothing flows (a Wi-Fi cut behind the
    decoupled bridge). ALWAYS resumed. Returns the (suspend, resume) wall-clock datetimes."""
    h = _K32.OpenProcess(0x0800, False, pid)                       # PROCESS_SUSPEND_RESUME
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        t0 = _dt.datetime.now()
        _NT.NtSuspendProcess(h)
        try:
            time.sleep(secs)
        finally:
            _NT.NtResumeProcess(h)
            t1 = _dt.datetime.now()
    finally:
        _K32.CloseHandle(h)
    return t0, t1


def cut(a, res: dict, check, engs: dict, host_bridge) -> None:
    """P5: a cut_for-second host-side cut cut_at s after LIVE; the guest's s119/s120 lines vs sitting A's s117 pair."""
    time.sleep(a.cut_at)
    print(f"[p5] suspending the HOST's bridge (pid {host_bridge.pid}) for {a.cut_for:g} s")
    t0, t1 = suspend_for(host_bridge.pid, a.cut_for)
    res["cut"] = {"start": t0.isoformat(timespec="milliseconds"), "end": t1.isoformat(timespec="milliseconds")}
    print(f"[p5] resumed at {t1:%H:%M:%S.%f}"[:-3] + f" ({(t1 - t0).total_seconds():.2f} s)")
    time.sleep(8.0)
    lo = t0 - _dt.timedelta(seconds=1)
    gl = engs["guest"].lines()
    found = {n: pb.hits(gl, n, after=lo) for n in ("leave", "watcher_settled", "ramp", "hold_cut", "hold_stall",
                                                      "hold_resume", "session_out", "session_back", "hold_cap", "serving")}
    window = [f"{d:%H:%M:%S} {m}" for d, _, m in gl if d >= lo and "[NetSync]" in m]
    res["guest_window"] = window
    hostw = [f"{d:%H:%M:%S} {m}" for d, _, m in engs["host"].lines() if d >= lo and "[NetSync]" in m]
    res["host_window"] = hostw
    sa = [ln.rstrip() for ln in SITTING_A.read_text(encoding="utf-8", errors="replace").splitlines()[154:166]]         if SITTING_A.exists() else ["<the sitting-A archive is not in this checkout>"]
    res["sitting_a_155_166"] = sa
    print("[p5] ---- guest [NetSync] lines from the cut on (this run, s121) ----")
    for ln in window:
        print("   " + ln[:210])
    print("[p5] ---- sitting A, laptop-Memoria.log 155-166 (s117, a 6 s physical cut) ----")
    for ln in sa:
        print("   " + ln[11:220])
    print("[p5] ---- host [NetSync] lines from the cut on ----")
    for ln in hostw[:14]:
        print("   " + ln[:210])
    bad = found["leave"] + found["watcher_settled"] + found["ramp"] + found["hold_cap"]
    check("K1", not bad, "none of sitting A's lines (LEAVE requested / watcher-leave settled / session ended) nor a cap "
          f"leave: {pb.show(bad) if bad else 'none'}")
    check("K2", len(found["hold_cut"]) == 1 and not found["hold_stall"],
          f"one CUT-variant hold line: {pb.show(found['hold_cut'])}; stall variant {len(found['hold_stall'])}")
    check("K3", len(found["session_out"]) == 1, f"one session outage line: {pb.show(found['session_out'])}")
    rs = found["hold_resume"]
    held = int(rs[0][2].group(2)) if rs else -1
    lo_ms, hi_ms = a.cut_for * 1000 - 3500, a.cut_for * 1000 + 500
    check("K4", len(rs) == 1 and lo_ms <= held <= hi_ms,
          f"one same-nonce resume, held {held} ms (want {lo_ms:.0f}..{hi_ms:.0f}: the cut minus the ~2 s stale "
          f"detection): {pb.show(rs)}")
    sb = found["session_back"]
    check("K5", len(sb) == 1, f"the session back inside the grace: {pb.show(sb)}")
    res["serving_after_resume"] = pb.show(found["serving"]) if found["serving"] else None
    print(f"[p5] info: ready mirror SERVING after the resume: {res['serving_after_resume']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leg", choices=("relay", "bridge"), required=True)
    ap.add_argument("--cut-for", type=float, default=0.0,
                    help="P5: after LIVE, suspend the HOST's bridge process this many seconds (0 = no cut; bridge leg only)")
    ap.add_argument("--cut-at", type=float, default=10.0, help="P5: seconds after the guest's LIVE line to start the cut")
    a = ap.parse_args()
    if a.cut_for and a.leg != "bridge":
        ap.error("--cut-for needs --leg bridge (the cut suspends the host's bridge process)")
    tag = "p5" if a.cut_for else "p4"
    code = "ff9-DUO" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    rd = WT / ".harness-runs" / f"{stamp}-mi-{tag}-{a.leg}"
    rd.mkdir(parents=True)
    url = {r: (f"ws://127.0.0.1:{RELAY_PORT}" if a.leg == "relay" else f"ws://127.0.0.1:{BRIDGE_PORTS[r]}")
           for r in ("host", "guest")}
    values = {
        "host": {"Enabled": "1", "Role": "host", "RelayUrl": url["host"], "SessionCode": code, "GuestSlots": "2",
                 "FollowHost": "0", "TargetField": "0", "StartHoldMs": "8000"},
        "guest": {"Enabled": "1", "Role": "client", "RelayUrl": url["guest"], "SessionCode": code, "FollowHost": "1",
                  "TargetField": "0", "GuestSlots": "0", "GuestStockMenu": "1", "AutoTeleport": "0"},
    }
    res = {"leg": a.leg, "code": code, "urls": url, "checks": [], "run_dir": str(rd)}

    def check(cid: str, ok: bool, detail: str) -> None:
        res["checks"].append({"id": cid, "ok": bool(ok), "detail": detail})
        print(f"[p4] {'PASS' if ok else 'FAIL'}  {cid}: {detail[:400]}")
        if not ok:
            raise Red(cid)

    procs, guards, gs, bridges = [], {}, {}, {}
    try:
        with contextlib.ExitStack() as stack:
            # C1 -- the relay (and bridges) on private ports
            ports = [RELAY_PORT] + (list(BRIDGE_PORTS.values()) if a.leg == "bridge" else [])
            busy = [p for p in ports if not pb.port_free(p)[0]]
            check("C0", not busy, f"ports {ports} free (busy: {busy})")
            relay = pb.PeerProc("relay", ["--port", RELAY_PORT, "--tap", rd / "relay.tap", "--status", "5"],
                                log_path=rd / "relay.log", out_path=rd / "relay.out")
            relay.start()
            procs.append(relay)
            up = relay.wait_for(RELAY_LISTENING, 15.0)        # relay mode says 'relay listening on ...'
            check("C1-relay", up is not None, up[1] if up else f"no listening line; tail {relay.tail()}")
            if a.leg == "bridge":
                for r, port in BRIDGE_PORTS.items():
                    p = subprocess.Popen([sys.executable, "-u", str(BRIDGE), "--port", str(port), "--relay",
                                          f"ws://127.0.0.1:{RELAY_PORT}", "--log", str(rd / f"bridge-{r}.log")],
                                         stdout=open(rd / f"bridge-{r}.out", "w"), stderr=subprocess.STDOUT)
                    procs.append(p)
                    bridges[r] = p
                    check(f"C1-bridge-{r}", wait_bound(port, 15.0), f"bridge on {port} bound")
            # the two games: each New Game -> 250, then its role's ini (hot-reloaded), host first
            engs = {}
            for role, root in (("host", HOST), ("guest", GUEST)):
                g = stack.enter_context(Session(label=f"mi-{tag}-{a.leg}-{role}", game_path=root,
                                                pid_probe=probe_for(root), window_size=(960, 540)))
                gs[role] = g
                g.newgame()
                if role == "host":
                    g.note(cb.seed_party(g, back_to=FIELD))
                if g.state.field_id != FIELD:
                    g.warp(FIELD)
                with contextlib.suppress(Exception):
                    g.no_encounters(True)
                if role == "host":
                    g.poke(pb.MARKER_BYTE, pb.MARKER_VALUE)
                else:
                    g.watch(*(pb.MARKER_BYTE * 8 + b for b in range(8)))
                engs[role] = pb.EngineLog(g.engine_log())
                guards[role] = pb.IniGuard(root / "Memoria.ini", values[role], label=f"mi-p4-{role}", run_dir=rd,
                                           backup_root=rd)
                print(f"[p4] {role}: {guards[role].apply()}")
                want = (lambda m, r=role: m.group(1) == "True" and m.group(2) == {"host": "host", "guest": "client"}[r]
                        and m.group(5) == url[r] and m.group(6) == code)
                # booted with Enabled=0 there is no NetSyncClient polling the ini: only a field load's Ensure() reads it
                # (coop_tape_record._wait_config's recipe) -- so a short wait, then ONE same-field warp, then wait again
                cfg = wait_hits(engs[role], "config", 6.0, pred=want)
                if not cfg:
                    g.warp(FIELD)
                    cfg = wait_hits(engs[role], "config", 10.0, pred=want)
                check(f"C2-{role}", bool(cfg), pb.show(cfg) if cfg else f"no matching config line; seen "
                      f"{pb.show(pb.hits(engs[role].lines(), 'config'))}")
            # C3 -- both legs connected
            for role in ("host", "guest"):
                rel = wait_hits(engs[role], "relay_up", 30.0,
                                pred=lambda m, r=role: m.group(3) == r and m.group(2) == code)
                check(f"C3-{role}", bool(rel), pb.show(rel) if rel else f"no 'relay connected ...role={role}'")
            # C4..C7 -- pairing, ghosts both ways, the mirror, the host's story on the guest
            pr = wait_hits(engs["guest"], "paired", 45.0, pred=lambda m: int(m.group(1)) == FIELD)
            check("C4", bool(pr), pb.show(pr) if pr else "no 'paired on the host's field (250)' on the guest")
            for role in ("host", "guest"):
                gh = wait_hits(engs[role], "ghost", 30.0, pred=lambda m: int(m.group(2)) == FIELD)
                check(f"C5-{role}", bool(gh), pb.show(gh) if gh else f"no ghost spawned on {FIELD} in the {role}")
            arm = wait_hits(engs["guest"], "armed", 30.0)
            check("C6", bool(arm), pb.show(arm) if arm else "no 'state-mirror ARMED' on the guest")
            st = cb.poll(gs["guest"], lambda s: pb.marker_value(s) == pb.MARKER_VALUE, 20.0, "the host's story marker")
            mv = pb.marker_value(st or gs["guest"].state)
            check("C7", mv == pb.MARKER_VALUE, f"guest byte {pb.MARKER_BYTE} reads {mv!r} (host 0xA5; own save 0)")
            # C8 -- the host's own battle, the guest's diorama
            at = _dt.datetime.now() - _dt.timedelta(seconds=1)
            gh = gs["host"]
            gh.start_battle(SCENE, group=-1, rand=bool(getattr(gh.state, "coop_intro_mirror", False)))
            intro = wait_hits(engs["host"], "intro", 20.0, after=at)
            check("C8-intro", bool(intro), pb.show(intro) if intro else "no host 'battle intro:' line (not published?)")
            boot = wait_hits(engs["guest"], "boot", 30.0, after=at, pred=lambda m: int(m.group(1)) == SCENE)
            check("C8-boot", bool(boot), pb.show(boot) if boot else "no guest 'diorama BOOT scene=67'")
            live = wait_hits(engs["guest"], "live", 30.0, after=at)
            check("C8-live", bool(live), pb.show(live) if live else "no guest 'diorama LIVE'")
            hold = [m for _, _, m in engs["host"].lines() if "start hold" in m]
            res["host_start_hold"] = hold[:6]
            print("[p4] host start-hold lines: " + " | ".join(h[:160] for h in hold[:6]))
            if a.cut_for:
                cut(a, res, check, engs, bridges["host"])
            time.sleep(3.0)
            res["final_ui"] = {r: g.state.ui_state for r, g in gs.items()}
            for role, g in gs.items():
                with contextlib.suppress(Exception):
                    res[f"{role}_log"] = str(cb.archive_log(g, f"mi-{tag}-{a.leg}-{role}"))
            print("[p4] ALL GREEN")
            for role, gd in guards.items():
                ok, why = gd.restore()
                res[f"ini_restored_{role}"] = [ok, why]
            guards.clear()
    except Red as r:
        res["stopped_at"] = str(r)
        print(f"[p4] STOPPED at {r} -- the owner's rule: stop at the first surprise")
    finally:
        for role, gd in guards.items():
            ok, why = gd.restore()
            res[f"ini_restored_{role}"] = [ok, why]
        for p in procs:
            with contextlib.suppress(Exception):
                if isinstance(p, pb.PeerProc):
                    res["relay_stop"] = p.stop()
                else:
                    p.terminate()
                    p.wait(10)
        res["left_after"] = {r: probe_for(p)() for r, p in (("host", HOST), ("guest", GUEST))}
        (rd / "p4.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        print(f"[p4] results -> {rd / 'p4.json'}; games left {res['left_after']}")
    return 0 if "stopped_at" not in res else 1


if __name__ == "__main__":
    raise SystemExit(main())
