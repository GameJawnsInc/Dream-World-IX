"""THE BRAWN BENCH — the per-unit-brain backend's parity cast (30423).

The SAME plaza, the SAME 14-unit brawl, the SAME trees as THE ISLES BENCH
(30416, owner-proven: "the brawl runs clean, crier lines all fire") — the ONLY
change is ``[behavior] brains = true``. Every unit's tree segment now lives in
its own Seq brain (spawned from its tag-1 head, dispatching onto itself via
uid 255) instead of the central ticker; the residual ticker keeps the shared
lanes (warm-up, mirrors, clocks, the fallen counter, the crier's scan reads).

WHAT A PASS LOOKS LIKE — *the same fight*: the two arcs converge after the
warm-up, melee resolves, the wounded break off for their corners, the crier's
counter lines land, dead units vanish (their die bodies now StopSharedScript
first — 14 brains dying mid-battle IS the orphan-law stress test), no freeze
for the whole fight, and ~ -> Reload restarts clean. Any behavioral DIFFERENCE
from the remembered 30416 brawl is a finding.

Usage (repo root):  py studies/behavior-trees/brains_bench.py gen | probe | deploy
30423 is a NEW id -> the FIRST deploy needs a game RELAUNCH, then ~ -> Warp.
Revert: py tools/scroll_out/revert_deploy_30423.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import island_bench as ib                                          # noqa: E402

ib.BRAINS = True
ib.FIELD_ID = 30423
ib.FIELD_NAME = "BRAWN"
ib.BENCH_TOML = ib.BENCH / "BRAWN.field.toml"
ib.REPORT = ib.BENCH / "behavior-report-brains.txt"


def deploy() -> None:
    if not ib.BENCH_TOML.exists():
        ib.gen()
    r = subprocess.run([sys.executable, str(ib.REPO / "tools" / "deploy_field.py"),
                        str(ib.BENCH_TOML), "--id", str(ib.FIELD_ID),
                        "--name", ib.FIELD_NAME,
                        "--text-block", str(ib.FIELD_ID),
                        "--mod-folder", ib.MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    print(f"""
PLAYTEST ({ib.FIELD_ID} is a NEW id -> RELAUNCH once, then ~ -> Warp -> {ib.FIELD_ID}):
  THE POINT: this is the ISLES brawl (30416) re-run on the per-unit-brain
  backend -- 15 Seq brains instead of one central ticker. The verdict is
  PARITY: the fight should look and resolve the SAME.
  1 after the ~4s warm-up both arcs charge and the melee starts;
  2 wounded units (1 hp) BREAK OFF and run -- knights east, Mus northwest;
  3 dead units VANISH cleanly (each die stops its own brain first -- a crash
    here means the orphan law failed at scale);
  4 the crier calls "First blood" / "Half the brawl has fallen" / (if it runs
    down) "ONE LEFT STANDING";
  5 no freeze through the whole fight; ~ -> Reload restarts the brawl clean.
  Any DIFFERENCE from the remembered 30416 fight is a finding -- report it.
  Revert: py tools/scroll_out/revert_deploy_{ib.FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": ib.gen, "probe": ib.probe, "deploy": deploy}[v]()
