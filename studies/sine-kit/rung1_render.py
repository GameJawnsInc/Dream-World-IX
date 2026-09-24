"""THE SINE KIT, RUNG 1 -- is the motion's HEIGHT DRAWN?  (bench 30948, bench/sine1r.field.toml)

The rung-1 proof (rung1_motion.py) reads the EVENT pos an observer sees right after the daemon's 0xAD, in the same
event pass -- before HonoLateUpdate copies the controller's curPos back. It never measured the drawn frame, and the
owner saw no bob on the orbiting cask. This measures the frame itself.

Three red balloons at ONE depth (z -900): L static on the floor, C held at height 300, R bobbing 0..300 every
2 s. Every in-engine shot is segmented for red pixels; the three blobs are split by x and each blob's red centroid
row is its drawn height, projected. D = row(L) - row(C) is what 300 world units of height draw as at this depth, so
the check calibrates itself -- no camera math, no guessed scale.

  R0  three red blobs in every shot; L and C (no height change) move <= 0.2 D across the shots -- the balloon
      model's own idle sway only (run 1 measured ~10 px of it; a 3 px bound was wrong for an animated model)
  R1  C is drawn ABOVE L by D >= 20 px: a constant motion height is drawn
  R2  R's centroid span, LESS the larger idle sway of L and C, is >= 0.7 D across shots spread over several bob
      cycles: the bob is drawn (the sway rides on R too, so it is taken off before the comparison)
  R3  R stays inside [row(C) - 0.15 D, row(L) + 0.15 D]: it sweeps the same 0..300 band and no further

  py tools/deploy_field.py studies/sine-kit/bench/sine1r.field.toml --id 30948
  py tools/play.py studies/sine-kit/rung1_render.py --label sine-render
"""
from __future__ import annotations

import time

FIELD = 30948
SHOTS = 18                  # ~0.5 s apart in practice (the capture itself takes time): ~8.5 s, four 2 s bob cycles
GAP_S = 0.37
MIN_BLOB = 60               # red pixels a balloon must show to count


def _red_blobs(png) -> list:
    """[(x centroid, y centroid, pixel count)] of the red blobs in one frame, left to right. Red = the balloon's
    body/base: R high, G and B low -- the floor's orange (R-G ~ 50) and brown stay out."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB")).astype(np.int16)
    r, gch, b = a[..., 0], a[..., 1], a[..., 2]
    mask = (r > 140) & (r - gch > 90) & (r - b > 80)
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return []
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]
    cuts = np.nonzero(np.diff(xs) > 40)[0] + 1              # a 40 px empty gap separates two balloons
    out = []
    for gx, gy in zip(np.split(xs, cuts), np.split(ys, cuts)):
        if gx.size >= MIN_BLOB:
            out.append((float(gx.mean()), float(gy.mean()), int(gx.size)))
    return out


def run(g) -> None:
    g.note("sine kit rung 1 -- is the motion height drawn?")
    g.newgame()
    g.warp(FIELD)
    g.wait_frames(90)
    rows = []                                                # [(t, [L, C, R] rows)]
    bad = []
    for i in range(SHOTS):
        png = g.shot(f"r{i:02d}")
        blobs = _red_blobs(png)
        if len(blobs) != 3:
            bad.append((i, [(round(x), round(y), n) for x, y, n in blobs]))
        else:
            rows.append((time.time(), [y for _x, y, _n in blobs]))
        time.sleep(GAP_S)
    g.check(not bad and len(rows) == SHOTS, "R0a: three red blobs (L, C, R) in every shot",
            f"{len(rows)}/{SHOTS} shots with 3 blobs; odd shots {bad[:4]}")
    if len(rows) < 6:
        return
    L = [r[0] for _t, r in rows]
    C = [r[1] for _t, r in rows]
    R = [r[2] for _t, r in rows]
    span = lambda v: max(v) - min(v)                         # noqa: E731
    mean = lambda v: sum(v) / len(v)                         # noqa: E731
    print(f"[sine-render] rows L {[round(v, 1) for v in L]}")
    print(f"[sine-render] rows C {[round(v, 1) for v in C]}")
    print(f"[sine-render] rows R {[round(v, 1) for v in R]}")
    D = mean(L) - mean(C)                                    # screen y grows DOWN: higher = smaller row
    print(f"[sine-render] D (300 u of height at z -900) = {D:.1f} px; R span {span(R):.1f} px")
    sway = max(span(L), span(C))                             # the model's own idle animation, no height change
    g.check(D >= 20 and sway <= 0.2 * D,
            "R0b: L and C (no height change) move <= 0.2 D across the shots -- the balloon's own idle sway only",
            f"L span {span(L):.1f}, C span {span(C):.1f} px vs 0.2 D = {0.2 * D:.1f} px")
    g.check(D >= 20, "R1: C (height 300) is drawn ABOVE L (the floor) by D >= 20 px -- a constant motion height is drawn",
            f"D = {D:.1f} px (row L {mean(L):.1f}, row C {mean(C):.1f})")
    g.check(D >= 20 and span(R) - sway >= 0.7 * D,
            "R2: R's centroid span less the idle sway is >= 0.7 D across the shots (several bob cycles) -- the bob is drawn",
            f"R span {span(R):.1f} px - sway {sway:.1f} = {span(R) - sway:.1f} px vs D {D:.1f} px "
            f"({(span(R) - sway) / D if D else 0:.2f} D)")
    lo, hi = mean(C) - 0.15 * D, mean(L) + 0.15 * D
    g.check(D >= 20 and all(lo <= v <= hi for v in R),
            "R3: R stays inside [row(C) - 0.15 D, row(L) + 0.15 D] -- it sweeps the 0..300 band and no further",
            f"R rows {min(R):.1f}..{max(R):.1f} vs band {lo:.1f}..{hi:.1f}")
