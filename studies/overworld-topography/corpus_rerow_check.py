"""CORPUS CROSS-CHECK -- does the apron round's DIRT RE-ROW land inside the grass
mains vocabulary the kit's own constants define?

Read-only against stock disc-1. No writes anywhere near the game install.

The re-row (studies/path-d-new-world/apron_carry.py:807-813) indexes GROUND uv on the
ROCK chart lattice (phase from out/rock_tiles.json, tile 0.0625 x 0.03125) and translates
a whole tile: col 5 -> col 0, row {8,10} -> 24 / {9,11} -> 25.  The grass mains
vocabulary is NOT that lattice -- it is grassland.GRASS_U_HALF x GRASS_V_HALF, a 2x2 of
inset rects with bleed gutters.  This measures the consequence on the DONOR's own tris.

Artifact: out/corpus_rerow_check.json
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import grassland as G        # noqa: E402

TILE_U, TILE_V = 0.0625, 0.03125
PU, PV = json.loads((ROOT / "studies/overworld-topography/out/rock_tiles.json")
                    .read_text())["phase"]
GRASS_TOPO = {0, 1, 2, 3, 42}
BLOCKS = [(15, 14), (14, 14), (16, 14), (15, 13), (15, 15)]   # apron_carry.py's own soup

MAIN = G.FAM_REGION["main"]
DREG = G.FAM_REGION["D"]
BREG = G.FAM_REGION["B"]
EPS = 1e-6


def in_rect(u, v, r):
    return r[0] - EPS <= u <= r[2] + EPS and r[1] - EPS <= v <= r[3] + EPS


def quadrant_of(u, v):
    """Which grass mains quadrant rect (if any) holds this corner exactly?"""
    for iu, (u0, u1) in enumerate(G.GRASS_U_HALF):
        for iv, (v0, v1) in enumerate(G.GRASS_V_HALF):
            if u0 - EPS <= u <= u1 + EPS and v0 - EPS <= v <= v1 + EPS:
                return (iu, iv)
    return None


rows = []
n_grass = 0
for (bx, by) in BLOCKS:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except Exception as exc:                                   # pragma: no cover
        rows.append(dict(block=[bx, by], error=str(exc)))
        continue
    V = bm.chan_arrays[X.CH_POS]
    U = bm.chan_arrays[X.CH_UV]
    T = bm.chan_arrays[X.CH_TAN]
    idx = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
    for tri in idx:
        topo = X.decode_id(int(round(T[tri[0]][0])))["topograph"]
        if topo not in GRASS_TOPO:
            continue
        n_grass += 1
        uv = [(float(U[j][0]), float(U[j][1])) for j in tri]
        us = [u for u, _ in uv]
        vs = [v for _, v in uv]
        ccol = int(math.floor((min(us) - PU) / TILE_U + 0.5))
        crow = int(math.floor((min(vs) - PV) / TILE_V + 0.5))
        if not (ccol == 5 and 8 <= crow <= 11):
            continue
        du = -5 * TILE_U
        dv = ((24 + (crow % 2)) - crow) * TILE_V
        out = [(u + du, v + dv) for (u, v) in uv]
        rows.append(dict(
            block=[bx, by], topo=topo, ccol=ccol, crow=crow,
            uv_before=uv, uv_after=out,
            corners_in_main=[in_rect(u, v, MAIN) for (u, v) in out],
            corners_in_D=[in_rect(u, v, DREG) for (u, v) in out],
            corners_in_B=[in_rect(u, v, BREG) for (u, v) in out],
            quadrants=[quadrant_of(u, v) for (u, v) in out],
        ))

n = len([r for r in rows if "error" not in r])
all_main = sum(1 for r in rows if "error" not in r and all(r["corners_in_main"]))
any_out_main = sum(1 for r in rows if "error" not in r and not all(r["corners_in_main"]))
any_D = sum(1 for r in rows if "error" not in r and any(r["corners_in_D"]))
multi_quad = 0
no_quad = 0
for r in rows:
    if "error" in r:
        continue
    qs = {tuple(q) if q else None for q in r["quadrants"]}
    if None in qs:
        no_quad += 1
    if len(qs - {None}) > 1:
        multi_quad += 1

# --- the lattice-misalignment arithmetic (independent of any tri) ------------------
lat = dict(
    rock_phase=[PU, PV],
    rock_col0_u=[PU + 0 * TILE_U, PU + 1 * TILE_U],
    rock_col1_u=[PU + 1 * TILE_U, PU + 2 * TILE_U],
    rock_row24_v=[PV + 24 * TILE_V, PV + 25 * TILE_V],
    rock_row25_v=[PV + 25 * TILE_V, PV + 26 * TILE_V],
    grass_u_half=G.GRASS_U_HALF, grass_v_half=G.GRASS_V_HALF,
    meadow_u_half=G.MEADOW_U_HALF,
    u_split_gutter=[G.GRASS_U_HALF[0][1], G.GRASS_U_HALF[1][0]],
    v_split_gutter=[G.GRASS_V_HALF[0][1], G.GRASS_V_HALF[1][0]],
)
lat["rock_col0_crosses_u_split"] = (lat["rock_col0_u"][0] < G.GRASS_U_HALF[0][1]
                                    < lat["rock_col0_u"][1])
lat["rock_row24_starts_below_grass"] = lat["rock_row24_v"][0] < G.GRASS_V_HALF[0][0]
lat["rock_row25_crosses_v_split"] = (lat["rock_row25_v"][0] < G.GRASS_V_HALF[0][1]
                                     < lat["rock_row25_v"][1])
lat["rock_col1_reaches_meadow"] = lat["rock_col1_u"][1] > G.MEADOW_U_HALF[0][0]

out = dict(
    blocks=BLOCKS, n_grass_tris=n_grass, n_rerow_candidates=n,
    all_corners_in_main=all_main, tris_with_a_corner_outside_main=any_out_main,
    tris_with_a_corner_in_meadow_D=any_D,
    tris_spanning_more_than_one_grass_quadrant=multi_quad,
    tris_with_a_corner_in_no_quadrant=no_quad,
    lattice=lat, samples=rows[:40],
)
(Path(__file__).resolve().parent / "out" / "corpus_rerow_check.json").write_text(
    json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "samples"}, indent=1))
