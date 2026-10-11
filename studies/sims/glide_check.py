"""THE GLIDE CHECK -- does Bilba WALK off a pose, or slide? (owner report after sims feel test 1; fix 495dabaa)

    py studies/sims/sims_bench2.py deploy --variant rung6   # bench 30435
    py tools/play.py studies/sims/glide_check.py             # this

Cause: the pose's undo ended in RunAnimation(stand), which sets afExec; the engine swaps a MOVING actor to its walk
clip only while afExec is clear, so she slid on the stand clip until it ended. The undo is now flags(0,0) + the NPC's own
stand/walk and nothing else.

The harness publishes no object's playing CLIP, so this proves the MECHANISM from state (the meal ends, she moves off
the pot) and shoots a frame every ~0.2 s through the first seconds of the walk; the LOOK -- legs cycling vs a standing
body sliding -- is read from the PNGs (`.harness-runs/*-glide_check/shots`).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sims_bench2 as B                                  # noqa: E402

B.configure("rung6")                                     # BEFORE rung2_day reads FIELD_ID / the report
import rung2_day as R                                    # noqa: E402


def run(g) -> None:
    assert R.FID == 30435, R.FID
    R.T0 = time.monotonic()
    g.newgame()
    g.warp(R.FID)
    g.watch(*R.FLAG.values())
    st = g.wait_for(lambda s: R._needs(s) is not None and s.objects_status == "listed", timeout=15,
                    what="the HUD strip and the object list")
    bu = sorted(st.objects, key=lambda o: R._d(o["x"], o["z"], *B.HOME))[0]["uid"]

    POSED = ("hunger", "energy", "fun")                 # the use tiers that hold a posed clip
    prev, trail, shots = set(), [], 0
    end = time.monotonic() + 150
    release = None
    while time.monotonic() < end and release is None:
        r = R._sample(g, bu, "watch")
        cur = {t for t in r["tasks"] if t in POSED}
        gone = prev - cur
        if gone and r["bx"] is not None:
            release = (sorted(gone)[0], r)
        prev = cur
        time.sleep(0.1)
    g.check(release is not None, "G1: a posed task ends on its own (a use tier retires)", str(R.LOG[-1]))
    if release is None:
        return
    need, r0 = release
    print(f"[glide] {need} pose released at ({r0['bx']}, {r0['bz']}) -- shooting the walk-off")
    last = (r0["bx"], r0["bz"])
    for i in range(10):
        g.shot(f"2-walkoff-{need}-{i:02d}")
        r = R._sample(g, bu, "walk-off")
        o = R._obj(g.state, bu) or {}
        step = R._d(r["bx"], r["bz"], *last) if r["bx"] is not None else 0.0
        last = (r["bx"], r["bz"])
        trail.append((i, round(step), r["bx"], r["bz"], o.get("moving"), r["frame"]))
    print("[glide] (i, step_u, x, z, moving, frame):", trail)
    moved = sum(t[1] for t in trail)
    g.check(moved > 100, "G2: she walked away after the pose", f"{round(moved)}u over {len(trail)} frames")
    # baseline: the same body walking with no pose just ended, for the eye to compare
    time.sleep(2)
    for i in range(3):
        o = R._obj(g.state, bu) or {}
        if o.get("moving"):
            g.shot(f"3-baseline-walk-{i}")
        time.sleep(1.5)
