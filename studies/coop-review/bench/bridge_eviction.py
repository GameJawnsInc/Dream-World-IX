#!/usr/bin/env python3
"""THE EVICTION PING-PONG BENCH -- two guests on one session code, through the REAL bridge (no game needed).

studies/coop-review/REVIEW.md 1.9: the relay REPLACES a leg when a second connection registers the same code + role,
and the bridge used to redial at once on every upstream EOF -- so two live clients on one code evicted each other at
handshake-RTT rate, forever, while both games' loopback hops stayed up. ff9mapkit/netsync_bridge.py's eviction guard
(FLAP_*) waits from the second short-lived leg and says why once.

The bench: tools/harness/coop_peer.py's local relay (it replaces a same-role occupant exactly as relay/main.go does) on a
private port; two bridges on private ports dialing it; two coop_peer fake-guest-clients, one per bridge, on ONE code.
After --seconds it reads the relay's "guest reconnected (replacing a stale connection)" lines and each bridge's
"keeps replacing this connection" line. THE METRIC IS THE BURST, not the total: the local relay caps its concurrent
connections, so a pre-guard storm (one eviction every ~15 ms) is cut off by "too many connections" after ~15 and a
total count cannot tell it from a guarded run. Green = at most --max-burst replacements inside any 1 s window and at
least one bridge saying why (the bridge whose legs keep dying young says it; the other's legs now live past FLAP_LIFE_S,
so to it each eviction looks like a wobble -- only a relay close code could tell it).

    py studies/coop-review/bench/bridge_eviction.py                      # the worktree's bridge: few replacements
    py studies/coop-review/bench/bridge_eviction.py --bridge <old.py>    # CALIBRATION: a pre-guard bridge storms

Exit 0 when the burst is <= --max-burst and a bridge warned; 1 otherwise. Stdlib only; every process it
starts is stopped before it exits. Ports are private (never 49201 / 7777).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
COOP_PEER = REPO / "tools" / "harness" / "coop_peer.py"
BRIDGE = REPO / "ff9mapkit" / "ff9mapkit" / "netsync_bridge.py"
RELAY_PORT = 7797
BRIDGE_PORTS = (49251, 49252)
CODE = "FF9-EVICTBNC"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bridge", default=str(BRIDGE), help="the netsync_bridge.py to run (default: this worktree's)")
    ap.add_argument("--seconds", type=float, default=45.0)
    ap.add_argument("--max-burst", type=int, default=4, help="most replacements allowed inside any 1 s window")
    ap.add_argument("--out", default=None, help="a directory for the logs (default: a temp dir)")
    args = ap.parse_args(argv)
    out = Path(args.out or tempfile.mkdtemp(prefix="bridge-eviction-"))
    out.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    procs = []

    def start(name, cmd):
        f = open(out / f"{name}.out", "w", encoding="utf-8", errors="replace")
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=str(REPO))
        procs.append((name, p, f))
        return p

    try:
        start("relay", [py, str(COOP_PEER), "relay", "--port", str(RELAY_PORT), "--status", "0",
                        "--log", str(out / "relay.log")])
        time.sleep(1.5)
        for i, port in enumerate(BRIDGE_PORTS):
            start(f"bridge{i}", [py, args.bridge, "--port", str(port), "--relay", f"ws://127.0.0.1:{RELAY_PORT}",
                                 "--log", str(out / f"bridge{i}.log")])
        time.sleep(1.5)
        for i, port in enumerate(BRIDGE_PORTS):
            start(f"guest{i}", [py, str(COOP_PEER), "fake-guest-client", "--relay", f"ws://127.0.0.1:{port}",
                                "--code", CODE])
            time.sleep(0.5)
        time.sleep(args.seconds)
    finally:
        for _name, p, _f in reversed(procs):
            if p.poll() is None:
                p.terminate()
        for _name, p, f in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
            f.close()

    def read(name):
        p = out / name
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    relay = read("relay.log") or read("relay.out")
    stamps = [_dt.datetime.strptime(m.group(1), "%H:%M:%S.%f") for m in
              re.finditer(r"^\[coop-peer (\d\d:\d\d:\d\d\.\d+)\] relay session \S+: guest reconnected \(replacing a stale "
                          r"connection\)", relay, re.M)]
    burst = max((sum(1 for u in stamps if 0 <= (u - t).total_seconds() < 1.0) for t in stamps), default=0)
    refused = relay.count("too many connections")
    warned = [("keeps replacing this connection" in (read(f"bridge{i}.log") + read(f"bridge{i}.out")))
              for i in range(len(BRIDGE_PORTS))]
    ok = burst <= args.max_burst and any(warned)
    print(json.dumps({"ok": ok, "bridge": args.bridge, "seconds": args.seconds, "replacements": len(stamps),
                      "max_burst_1s": burst, "max_burst_allowed": args.max_burst, "relay_refused_too_many": refused,
                      "bridges_warned": warned, "logs": str(out)}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
