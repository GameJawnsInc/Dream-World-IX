"""THE SCRUB ARRANGEMENT PROBE -- is the ecotone 2x2 a parity-locked MACRO-TILE?

The ground-sampler playtest (2026-07-15) showed a scrub island as a raw tiling
mismatch ("tiling/wang mismatch") while stock scrub reads fine. Hypothesis: the scrub
2x2 is ONE 8x8u picture split into 4 quadrants that stock lays as whole repeating 2x2s
(quad = cell parity, one orientation) -- which the mint's grass-style avoid-repeat
placement would scramble.

VERDICT: FALSIFIED. Stock places scrub exactly like grass -- parity-lock best 31%
(chance floor = 25%), all 4 orientation forms uniform (58/56/56/53). Same for grass
(29%) and snow (28%) controls. The real explanation is ROLE, not arrangement: stock
only ever lays scrub as narrow SEAM strips between solid grass and dirt fields (~46
tris/block, border-shaped), where transition tiles read as "patchy edge" because real
fields flank them. A filled scrub island has no stock precedent -> scrub is a
TRANSITION vocabulary (GROUNDS cls="transition"), not an island fill.

Method: per tiled mains cell, decode (uh, vh) from the exact-affine rect origin and the
orientation form from the affine axis-map signs; score the best of the 8 parity/axis
phase choices for quad == cell parity.

    py studies/overworld-topography/scrub_arrangement_probe.py
"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

TILE_U, TILE_V = 0.0625, 0.03125
FAMS = [("grass", (0,), (0.0, 24.5)), ("scrub", (4, 5, 6), (4.0, 22.5)),
        ("snow", (27, 28), (0.0, 14.0))]
SPEC = {"grass": [(15, 15), (16, 14), (14, 15), (15, 16), (19, 12), (17, 15), (18, 15), (18, 12)],
        "scrub": [(18, 5), (5, 7), (5, 8), (16, 5), (17, 5), (14, 5), (12, 5), (15, 4)],
        "snow": [(6, 2), (7, 3), (6, 3), (7, 2), (7, 1), (8, 1), (5, 3), (4, 4)]}

for name, topos, (a0, b0) in FAMS:
    cells = {}
    for (bx, by) in SPEC[name]:
        bm = X.read_block(bx, by, disc=1, part="terrain")
        ct = defaultdict(list)
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            if X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"] not in topos:
                continue
            ws = [(bm.verts[j][0] + 64 * bx, bm.verts[j][2] - 64 * by) for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(p[0] for p in ws) / 3
            cz = sum(p[1] for p in ws) / 3
            ct[(math.floor(cx / 4), math.floor(cz / 4))].append((ws, uv))
        for cell, tl in ct.items():
            rows, ru, rv = [], [], []
            for ws, uv in tl:
                for (x, z), (u, v) in zip(ws, uv):
                    rows.append([x, z, 1.0])
                    ru.append(u)
                    rv.append(v)
            Am = np.array(rows)
            if len(rows) < 3 or np.linalg.matrix_rank(Am) < 3:
                continue
            cu, *_ = np.linalg.lstsq(Am, np.array(ru), rcond=None)
            cv, *_ = np.linalg.lstsq(Am, np.array(rv), rcond=None)
            if max(float(np.abs(Am @ cu - ru).max()),
                   float(np.abs(Am @ cv - rv).max())) > 1e-4:
                continue
            i, j = cell
            corn = [(4 * i, 4 * j), (4 * i + 4, 4 * j), (4 * i, 4 * j + 4), (4 * i + 4, 4 * j + 4)]
            us = [cu[0] * x + cu[1] * z + cu[2] for x, z in corn]
            vs = [cv[0] * x + cv[1] * z + cv[2] for x, z in corn]
            tile = (round(min(us) / TILE_U * 2) / 2, round(min(vs) / TILE_V * 2) / 2)
            if tile not in {(a0, b0), (a0 + 1, b0), (a0, b0 + 1), (a0 + 1, b0 + 1)}:
                continue
            uh, vh = int(tile[0] != a0), int(tile[1] != b0)
            u_ax = "x" if abs(cu[0]) > abs(cu[1]) else "z"
            v_ax = "x" if abs(cv[0]) > abs(cv[1]) else "z"
            su = "+" if (cu[0] if u_ax == "x" else cu[1]) > 0 else "-"
            sv = "+" if (cv[0] if v_ax == "x" else cv[1]) > 0 else "-"
            cells[cell] = (uh, vh, f"u{su}{u_ax}v{sv}{v_ax}")
    n = len(cells)
    scores = []
    for pu in (0, 1):
        for pv in (0, 1):
            scores.append(sum(1 for (i, j), (uh, vh, _) in cells.items()
                              if uh == (i + pu) % 2 and vh == (j + pv) % 2))
            scores.append(sum(1 for (i, j), (uh, vh, _) in cells.items()
                              if uh == (j + pu) % 2 and vh == (i + pv) % 2))
    oris = Counter(o for *_, o in cells.values())
    print(f"{name:7s} {n:4d} mains cells | parity-lock best {max(scores) / n:.0%} "
          f"(chance 25%) | ori forms: {dict(oris.most_common(4))}")
print("macro-tile hypothesis: FALSIFIED if every family sits at ~25-31% with uniform oris")
