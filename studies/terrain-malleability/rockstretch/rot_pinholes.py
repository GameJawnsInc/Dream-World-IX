"""Count pinholes in the grass of the rot-mountain stills: single bright, sky-coloured pixels whose surroundings
are grass, below the horizon band and outside the player's box. A crack between two surfaces that do not share an edge exactly shows the sky through it, one pixel at
a time; the sea's own sparkle is excluded by requiring grass all round (the 7x7 neighbourhood's median green).
Prints per still the count, and the pixel positions of the first few.
RUN:  py studies/terrain-malleability/rockstretch/rot_pinholes.py <run dir> [<run dir> ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import median_filter


def pinholes(path: Path):
    A = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    r, g, b = A[..., 0], A[..., 1], A[..., 2]
    bright = (r > 150) & (g > 160) & (b > 170) & (b >= g - 10)          # sky / white-ish, not green
    med = np.stack([median_filter(A[..., k], size=7) for k in range(3)], -1)
    grassy = (med[..., 1] > med[..., 0] + 8) & (med[..., 1] > med[..., 2] + 20) & (med[..., 1] < 170)
    hits = bright & grassy
    hits[:, :4] = hits[:, -4:] = False
    hits[:4] = hits[-4:] = False
    hits[:170] = False                       # the horizon band: far islands' grass against the sky
    hits[400:520, 590:690] = False           # the player
    ys, xs = np.nonzero(hits)
    return len(xs), list(zip(xs.tolist(), ys.tolist()))[:6]


def main(runs):
    for run in runs:
        for p in sorted(Path(run, "shots").glob("[ABC]-*-b.png")):
            n, where = pinholes(p)
            print(f"{Path(run).name[:30]:30s} {p.stem:12s} {n:4d}  {where}")


if __name__ == "__main__":
    main(sys.argv[1:])
