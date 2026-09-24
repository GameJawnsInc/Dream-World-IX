"""THE SINE KIT -- does a field whose ONLY mover is a HOLD draw it?  (bench 30949, bench/sine1h.field.toml)

``motion = { height = N }`` alone is a hold, and a field whose only movers are holds builds a motion daemon with
NO locals (no clock prelude, no advance: the 0xAD, Wait(1) and JMP only) -- a shape no clocked field builds, so
30948's proof (a hold beside clocked movers) does not cover it. 30948's camera and depth, two red balloons: L static
on the floor, C held at height 300. Every in-engine shot is segmented for red pixels (rung1_render._red_blobs);
D = row(L) - row(C) is what 300 world units of height draw as at this depth.

  H0  two red blobs in every shot; L and C move <= 0.2 D across the shots (the balloon's own idle sway only)
  H1  C is drawn ABOVE L by D >= 20 px: the hold's height is drawn
  H2  D is within 10% of D_REF, 30948's measured D for the same 300 u at the same depth and camera: the hold draws
      at 300, not merely off the floor

  py tools/deploy_field.py studies/sine-kit/bench/sine1h.field.toml --id 30949
  py tools/play.py studies/sine-kit/rung1_hold.py --label sine-hold
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rung1_render import _red_blobs  # noqa: E402

FIELD = 30949
SHOTS = 12
GAP_S = 0.37
D_REF = 76.2                # 30948's C (height 300) above L at z -900, 720p: runs 1-3 measured 76.2 / 76.3 px


def run(g) -> None:
    g.note("sine kit -- a hold-only field (the zero-clock daemon)")
    g.newgame()
    g.warp(FIELD)
    g.wait_frames(90)
    rows, bad = [], []
    for i in range(SHOTS):
        png = g.shot(f"h{i:02d}")
        blobs = _red_blobs(png)
        if len(blobs) != 2:
            bad.append((i, [(round(x), round(y), n) for x, y, n in blobs]))
        else:
            rows.append([y for _x, y, _n in blobs])
        time.sleep(GAP_S)
    g.check(not bad and len(rows) == SHOTS, "H0a: two red blobs (L, C) in every shot",
            f"{len(rows)}/{SHOTS} shots with 2 blobs; odd shots {bad[:4]}")
    if len(rows) < 4:
        return
    L, C = [r[0] for r in rows], [r[1] for r in rows]
    span = lambda v: max(v) - min(v)                         # noqa: E731
    mean = lambda v: sum(v) / len(v)                         # noqa: E731
    D = mean(L) - mean(C)                                    # screen y grows DOWN: higher = smaller row
    print(f"[sine-hold] rows L {[round(v, 1) for v in L]}")
    print(f"[sine-hold] rows C {[round(v, 1) for v in C]}")
    print(f"[sine-hold] D = {D:.1f} px (30948: {D_REF} px)")
    g.check(D >= 20 and max(span(L), span(C)) <= 0.2 * D,
            "H0b: L and C move <= 0.2 D across the shots -- idle sway only, the hold does not drift",
            f"L span {span(L):.1f}, C span {span(C):.1f} px vs 0.2 D = {0.2 * D:.1f} px")
    g.check(D >= 20, "H1: C (a hold at 300) is drawn ABOVE L (the floor) by D >= 20 px -- the hold's height is drawn",
            f"D = {D:.1f} px (row L {mean(L):.1f}, row C {mean(C):.1f})")
    g.check(abs(D - D_REF) <= 0.1 * D_REF,
            "H2: D is within 10% of 30948's D for the same 300 u -- the hold draws AT 300",
            f"D = {D:.1f} px vs D_REF {D_REF} px (|diff| {abs(D - D_REF):.1f} <= {0.1 * D_REF:.1f})")
