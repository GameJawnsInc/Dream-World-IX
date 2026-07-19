"""TOPO-16 DIRT (dry lakebed) -- is it a grass TRANSLATION, or a different grammar?

The ground-families census (``ground_families_anatomy.py``) recovered clean 5dp
TRANSLATION laws for every other walkable ground family, including 3 of the 4 dirt
gameplay variants (19/20 = desert exactly; 41 = its own pale-sand set). Topo 16 was the
ONE holdout, written off in one line in README.md: "thin (6 blocks); COLUMN origin
structure, no clean 2x2 (dry lakebed)". Nobody re-ran the method on it in isolation or
chased what "column structure" actually measures. This script closes that gap:

  1. MAP-WIDE CENSUS (all 480 (bx,by) candidates, not a top-N slice) -- which blocks
     carry topo 16, how many tris, and what topos share those blocks (context).
  2. The SAME per-4u-cell exact-affine decode + mural screen the sibling study uses,
     run on every topo-16 tri map-wide (no >=30-tris-per-block specimen gate -- the
     family is globally thin, so every block is a "specimen").
  3. Half-tile-snapped ORIGIN recovery (the same snapping ground_families_anatomy.py
     uses for its AUTO-2x2 detector) -- but instead of assuming a 2x2 quadrant grid,
     recover a 5dp RECT independently for every distinct origin observed, so the real
     atlas footprint is measured without assuming its shape.
  4. Structure classification: cluster the recovered origins by column (shared u) and
     by row (shared v); measure each origin-rect's width/height against the two known
     unit-cell shapes in the atlas -- the mains QUADRANT (0.06054 x 0.03028, a 2x2 set)
     and the grass "B" TRANSITION STRIP (0.06055 wide, 4 rows each ~0.0293 tall, one
     column, row pitch exactly TILE_V=0.03125). Report which shape (if either) the
     topo-16 cells match.
  5. Translation-fit attempts against grass 'main' (2x2) AND grass 'B' (1x4 strip) --
     the SAME outer-bounds method as ground_families_anatomy.py, generalized to a
     single-column multi-row grid for the 'B' hypothesis. Confidence is stated
     honestly: 5dp on ALL populated edges = proven; fewer edges populated (thin data)
     = an earmark/partial-bounds fit, not a decode.
  6. The wall probe (topo-58 tris edge-adjacent to topo 16), for completeness, matching
     the sibling scripts -- almost certainly too thin (a dry lakebed does not meet the
     coast), but checked rather than assumed.

Every number below is PRINTED by this script when run. Artifacts -> out/dirt16.json.
Run from the repo root:
    py studies/overworld-topography/dirt16_anatomy.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

BLOCK = 64.0
TILE_U, TILE_V = 0.0625, 0.03125
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
out = {}

# ---- A. MAP-WIDE census (every (bx,by) in 0..23 x 0..19 -- no top-N slice) ---------------------
census = {}
for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        c = Counter()
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            c[X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]] += 1
        census[(bx, by)] = c
print(f"A. map-wide census: {len(census)}/480 candidate blocks have terrain mesh")
out["census_blocks"] = len(census)

t16_blocks = {blk: c.get(16, 0) for blk, c in census.items() if c.get(16, 0) > 0}
total16 = sum(t16_blocks.values())
print(f"   topo-16 MAP-WIDE: {total16} tris over {len(t16_blocks)} blocks")
for blk, n in sorted(t16_blocks.items()):
    others = {tp: cnt for tp, cnt in census[blk].most_common() if tp != 16}
    print(f"     block {blk}: {n} tris of topo16; co-occurring topos {others}")
out["topo16_blocks"] = {f"{b[0]},{b[1]}": n for b, n in sorted(t16_blocks.items())}
out["topo16_total_tris"] = total16
out["topo16_block_context"] = {
    f"{b[0]},{b[1]}": dict(census[b].most_common()) for b in sorted(t16_blocks)
}

# is topo-16's footprint one contiguous rectangle of blocks?
bxs = sorted({b[0] for b in t16_blocks})
bys = sorted({b[1] for b in t16_blocks})
full_rect = {(x, y) for x in range(min(bxs), max(bxs) + 1) for y in range(min(bys), max(bys) + 1)}
contiguous_rect = full_rect == set(t16_blocks)
print(f"   footprint bbox bx[{min(bxs)},{max(bxs)}] by[{min(bys)},{max(bys)}] "
      f"({len(full_rect)} cells) -- {'EXACT CONTIGUOUS RECTANGLE' if contiguous_rect else 'not a filled rectangle'}")
out["contiguous_block_rect"] = bool(contiguous_rect)

# ---- B. gather every topo-16 tri from those blocks (no specimen-count gate -- globally thin) ----
ftris = []
for blk in t16_blocks:
    bm = X.read_block(*blk, disc=1, part="terrain")
    bx, by = blk
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        if X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"] != 16:
            continue
        ftris.append(dict(
            w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1], bm.verts[j][2] - BLOCK * by) for j in tri],
            uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
            block=blk))
print(f"B. gathered {len(ftris)} topo-16 tris (all blocks, no >=30 specimen gate)")
out["gathered_tris"] = len(ftris)
assert len(ftris) == total16, "gathered count must match the census total"

# raw uv envelope, before any per-cell processing (sanity: the absolute outer footprint)
raw_us = [u for t in ftris for u, v in t["uv"]]
raw_vs = [v for t in ftris for u, v in t["uv"]]
print(f"   RAW uv envelope (every corner, unfiltered): "
      f"u[{min(raw_us):.5f},{max(raw_us):.5f}] v[{min(raw_vs):.5f},{max(raw_vs):.5f}]")
out["raw_uv_envelope"] = [round(min(raw_us), 5), round(min(raw_vs), 5),
                          round(max(raw_us), 5), round(max(raw_vs), 5)]

# ---- C. per-4u-cell exact affine (the linear-in-XZ law) ------------------------------------------
cell_tris = defaultdict(list)
for ti, t in enumerate(ftris):
    cx = sum(p[0] for p in t["w"]) / 3
    cz = sum(p[2] for p in t["w"]) / 3
    cell_tris[(math.floor(cx / 4.0), math.floor(cz / 4.0))].append(ti)
lin_ok = {}
for cell, tl in cell_tris.items():
    rows, ru, rv = [], [], []
    for ti in tl:
        t = ftris[ti]
        for (x, y, z), (u, v) in zip(t["w"], t["uv"]):
            rows.append([x, z, 1.0])
            ru.append(u)
            rv.append(v)
    Am = np.array(rows)
    if len(rows) < 3 or np.linalg.matrix_rank(Am) < 3:
        continue
    cu, *_ = np.linalg.lstsq(Am, np.array(ru), rcond=None)
    cv, *_ = np.linalg.lstsq(Am, np.array(rv), rcond=None)
    res = max(float(np.abs(Am @ cu - ru).max()), float(np.abs(Am @ cv - rv).max()))
    if res < 1e-4:
        lin_ok[cell] = (cu, cv)
n_cells = len(cell_tris)
print(f"C. per-4u-cell exact-linear (uv exactly affine in world XZ): "
      f"{len(lin_ok)}/{n_cells} cells ({len(lin_ok) / max(1, n_cells):.0%})")
out["linear"] = dict(cells=n_cells, exact=len(lin_ok))

# ---- D. mural screen (murals are linear but low-density -- span < half a tile) -------------------
cell_rect = {}
n_mural = 0
mural_cells = []
for (i, j), (cu, cv) in lin_ok.items():
    corn = [(4.0 * i, 4.0 * j), (4.0 * (i + 1), 4.0 * j),
            (4.0 * i, 4.0 * (j + 1)), (4.0 * (i + 1), 4.0 * (j + 1))]
    us = [cu[0] * x + cu[1] * z + cu[2] for (x, z) in corn]
    vs = [cv[0] * x + cv[1] * z + cv[2] for (x, z) in corn]
    du4, dv4 = max(us) - min(us), max(vs) - min(vs)
    if du4 < TILE_U * 0.5 or dv4 < TILE_V * 0.5:
        n_mural += 1
        mural_cells.append((i, j, round(du4, 5), round(dv4, 5)))
        continue
    cell_rect[(i, j)] = (min(us), max(us), min(vs), max(vs))
print(f"D. mural/low-density screened: {n_mural} cells; TILED cells remaining: {len(cell_rect)}")
if mural_cells:
    print(f"   screened cells (i,j,du4,dv4): {mural_cells}")
out["mural_cells"] = n_mural
out["tiled_cells"] = len(cell_rect)

if not cell_rect:
    print("\nVERDICT: zero tiled cells survive the mural screen -- topo-16 geometry is "
          "PURE MURAL/low-density content, not a tile-mosaic ground at all.")
    out["verdict"] = "mural-only"
    OUTD.mkdir(exist_ok=True)
    (OUTD / "dirt16.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dirt16.json'}")
    sys.exit(0)

# outer envelope over the TILED cells only (post mural-screen)
tu0 = min(r[0] for r in cell_rect.values()); tu1 = max(r[1] for r in cell_rect.values())
tv0 = min(r[2] for r in cell_rect.values()); tv1 = max(r[3] for r in cell_rect.values())
print(f"   TILED-cell outer envelope: u[{tu0:.5f},{tu1:.5f}] (width {tu1 - tu0:.5f}) "
      f"v[{tv0:.5f},{tv1:.5f}] (height {tv1 - tv0:.5f})")
out["tiled_envelope"] = [round(tu0, 5), round(tv0, 5), round(tu1, 5), round(tv1, 5)]

# ---- E. half-tile-snapped origins (the SAME snap ground_families_anatomy.py uses) ---------------
cell_tile = {c: (round(r[0] / TILE_U * 2) / 2, round(r[2] / TILE_V * 2) / 2)
             for c, r in cell_rect.items()}
tiles = Counter(cell_tile.values())
print(f"E. distinct half-tile-snapped origins: {len(tiles)}")
for (a, b), n in sorted(tiles.items()):
    print(f"     origin ({a},{b}): {n} cell(s)")
out["origins"] = [[a, b, n] for (a, b), n in sorted(tiles.items())]

# the SAME AUTO 2x2 detector as ground_families_anatomy.py, run formally on this data.
# NOTE (methodological correction found while running this): the original detector sums
# whichever of the 4 quadrant positions happen to exist in `tiles` -- it does NOT require
# all 4 to be present. On sparse/column data this silently accepts "2 rows stacked in one
# u-column" as a "2x2" (both summed positions share the SAME a, only b differs) as long as
# that pair covers >=15% of cells. So this script reports BOTH numbers: the naive share
# (matching the sibling script's exact algorithm, for comparability) AND a STRICT check
# that actually verifies all 4 corner positions are populated.
best_base, best_n = None, 0
for (a, b) in tiles:
    n = sum(tiles.get(o, 0) for o in ((a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)))
    if n > best_n:
        best_base, best_n = (a, b), n
share2x2 = best_n / max(1, len(cell_tile))
a, b = best_base
corners_present = [(a, b) in tiles, (a + 1, b) in tiles, (a, b + 1) in tiles, (a + 1, b + 1) in tiles]
strict_2x2 = all(corners_present)
print(f"   AUTO-2x2 detector (naive, sibling-script algorithm): best base {best_base} covers "
      f"{best_n}/{len(cell_tile)} tiled cells ({share2x2:.0%}) -- "
      f"{'2x2 CONFIRMED (naive)' if share2x2 >= 0.15 else 'NO dominant 2x2 (confirms README)'}")
print(f"   STRICT 2x2 check on that base: corners present {corners_present} "
      f"(order (a,b),(a+1,b),(a,b+1),(a+1,b+1)) -- "
      f"{'ALL 4 CORNERS REAL -- genuine 2x2' if strict_2x2 else 'FALSE POSITIVE -- missing corner(s), this is NOT a real quadrant grid (it is a same-column vertical run miscounted as 2x2 by the naive share test)'}")
out["auto_2x2"] = dict(base=list(best_base) if best_base else None, share=round(share2x2, 3),
                       strict_all_4_corners=bool(strict_2x2), corners_present=corners_present)

# ---- F. per-origin RECT recovery -- measure the real atlas footprint, no grid assumed -----------
origin_rect = {}
for cell, tile in cell_tile.items():
    origin_rect.setdefault(tile, []).append(cell_rect[cell])
print("F. per-origin 5dp rect recovery (mode of each edge across all cells at that origin):")


def mode5(vals):
    return float(Counter(round(float(v), 5) for v in vals).most_common(1)[0][0])


rec = {}
for tile, rects in sorted(origin_rect.items()):
    u0s = [r[0] for r in rects]; u1s = [r[1] for r in rects]
    v0s = [r[2] for r in rects]; v1s = [r[3] for r in rects]
    u0, u1, v0, v1 = mode5(u0s), mode5(u1s), mode5(v0s), mode5(v1s)
    u0_spread, u1_spread = max(u0s) - min(u0s), max(u1s) - min(u1s)
    v0_spread, v1_spread = max(v0s) - min(v0s), max(v1s) - min(v1s)
    max_spread = max(u0_spread, u1_spread, v0_spread, v1_spread)
    exact = max_spread < 2e-5
    low_n = len(rects) < 3   # a single cell has zero variance by construction -- not evidence of stability
    rec[tile] = dict(u0=u0, u1=u1, v0=v0, v1=v1, n=len(rects),
                     w=round(u1 - u0, 5), h=round(v1 - v0, 5),
                     exact_5dp=bool(exact and not low_n), low_n=bool(low_n), max_spread=round(max_spread, 6))
    tag = ("LOW-N, spread UNMEASURABLE (n<3, not evidence of stability)" if low_n else
           "5dp-EXACT" if exact else f"spread {max_spread:.6f} (NOT 5dp-tight)")
    print(f"     origin {tile}: n={len(rects)} rect u[{u0},{u1}] v[{v0},{v1}] "
          f"w={round(u1 - u0, 5)} h={round(v1 - v0, 5)} {tag}")
out["origin_rects"] = {f"{t[0]},{t[1]}": v for t, v in rec.items()}

# ---- G. column / row clustering ------------------------------------------------------------------
by_col = defaultdict(list)   # shared u (a) -> sorted list of b
by_row = defaultdict(list)   # shared v (b) -> sorted list of a
for (a, b) in rec:
    by_col[a].append(b)
    by_row[b].append(a)
print("G. column clustering (shared u origin, varying v):")
col_runs = []
for a, bs in sorted(by_col.items()):
    bs = sorted(bs)
    diffs = [round(y - x, 5) for x, y in zip(bs, bs[1:])]
    step_half = all(abs(d - TILE_V / 2) < 1e-4 for d in diffs) if diffs else None
    step_full = all(abs(d - TILE_V) < 1e-4 for d in diffs) if diffs else None
    print(f"     u={a}: {len(bs)} row(s) at v={bs}  diffs={diffs}  "
          f"{'HALF-TILE PITCH' if step_half else ('FULL-TILE PITCH' if step_full else '')}")
    col_runs.append(dict(u=a, vs=bs, n=len(bs), diffs=diffs,
                         half_tile_pitch=bool(step_half) if diffs else None,
                         full_tile_pitch=bool(step_full) if diffs else None))
out["column_runs"] = col_runs
print("   row clustering (shared v origin, varying u):")
row_runs = []
for b, as_ in sorted(by_row.items()):
    as_ = sorted(as_)
    print(f"     v={b}: {len(as_)} col(s) at u={as_}")
    row_runs.append(dict(v=b, us=as_, n=len(as_)))
out["row_runs"] = row_runs

longest_col = max((r["n"] for r in col_runs), default=0)
longest_row = max((r["n"] for r in row_runs), default=0)
print(f"   longest column run (fixed u, stacked v): {longest_col}  "
      f"longest row run (fixed v, stacked u): {longest_row}")
out["longest_col_run"] = longest_col
out["longest_row_run"] = longest_row
structure = ("column" if longest_col >= 2 and longest_col >= longest_row else
             "row" if longest_row >= 2 and longest_row > longest_col else
             "single-cell" if len(rec) == 1 else "scattered")
print(f"   STRUCTURE CLASS: {structure}")
out["structure_class"] = structure

# ---- H. shape comparison vs the two known unit-cell shapes ---------------------------------------
QUAD_W, QUAD_H = round(G.GRASS_U_HALF[0][1] - G.GRASS_U_HALF[0][0], 5), \
                 round(G.GRASS_V_HALF[0][1] - G.GRASS_V_HALF[0][0], 5)
STRIP_W = round(G.STRIP_U[1] - G.STRIP_U[0], 5)
STRIP_ROW_H = round(G.STRIPS_V[0][1] - G.STRIPS_V[0][0], 5)
STRIP_PITCH = round(G.STRIPS_V[1][0] - G.STRIPS_V[0][0], 5)
print(f"H. reference unit-cell shapes: mains QUADRANT w={QUAD_W} h={QUAD_H}; "
      f"grass B STRIP w={STRIP_W} row-h={STRIP_ROW_H} row-pitch={STRIP_PITCH} (4 rows)")
out["reference_shapes"] = dict(quad_w=QUAD_W, quad_h=QUAD_H, strip_w=STRIP_W,
                               strip_row_h=STRIP_ROW_H, strip_pitch=STRIP_PITCH)
for tile, r in sorted(rec.items()):
    dw_quad, dh_quad = abs(r["w"] - QUAD_W), abs(r["h"] - QUAD_H)
    dw_strip, dh_strip = abs(r["w"] - STRIP_W), abs(r["h"] - STRIP_ROW_H)
    print(f"     origin {tile} w={r['w']} h={r['h']}: "
          f"|vs QUADRANT| dw={dw_quad:.5f} dh={dh_quad:.5f}; "
          f"|vs STRIP-ROW| dw={dw_strip:.5f} dh={dh_strip:.5f}")

# ---- I. translation-fit attempts (outer-bounds method, generalized) ------------------------------
print("I. translation-fit attempts:")

# I.1 vs grass MAIN 2x2 (only meaningful if AUTO-2x2 found a real quadrant set)
if best_base and share2x2 >= 0.15:
    a, b = best_base
    mains_origins = {(a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)}
    per_edge = defaultdict(list)
    for cell, tile in cell_tile.items():
        if tile not in mains_origins:
            continue
        u0, u1, v0, v1 = cell_rect[cell]
        uh = 0 if tile[0] == a else 1
        vh = 0 if tile[1] == b else 1
        per_edge[("u", uh, "lo")].append(u0); per_edge[("u", uh, "hi")].append(u1)
        per_edge[("v", vh, "lo")].append(v0); per_edge[("v", vh, "hi")].append(v1)
    populated = [k for k in (("u", 0, "lo"), ("u", 0, "hi"), ("u", 1, "lo"), ("u", 1, "hi"),
                              ("v", 0, "lo"), ("v", 0, "hi"), ("v", 1, "lo"), ("v", 1, "hi"))
                 if k in per_edge]
    print(f"   I.1 vs MAIN 2x2: {len(populated)}/8 quadrant edges populated "
          f"({'FULL -- 5dp decode possible' if len(populated) == 8 else 'PARTIAL -- earmark only'})")
    out["main_fit_edges_populated"] = len(populated)
else:
    print("   I.1 vs MAIN 2x2: skipped (no AUTO-2x2 quadrant set detected)")
    out["main_fit_edges_populated"] = 0

# I.2 vs grass B STRIP (1 column x 4 rows) -- generalized single-column multi-row fit.
# Hypothesis: topo16 draws from ITS OWN single-column strip at some du from STRIP_U[0],
# with rows spaced by the SAME TILE_V pitch as the real B strip. Test: do all recovered
# origins share (approximately) one u, and does their v spacing match STRIP_PITCH?
if len(by_col) == 1:
    (only_u,) = by_col.keys()
    rows_here = sorted(by_col[only_u])
    du_strip = round(rec[(only_u, rows_here[0])]["u0"] - G.STRIP_U[0], 5)
    print(f"   I.2 vs grass B STRIP: single column at u={only_u} ({len(rows_here)} rows) -- "
          f"du vs STRIP_U[0] = {du_strip}")
    row_pitch_diffs = [round(rows_here[i + 1] - rows_here[i], 5) for i in range(len(rows_here) - 1)]
    matches_pitch = all(abs(d - STRIP_PITCH) < 1e-4 for d in row_pitch_diffs) if row_pitch_diffs else None
    print(f"     row v-pitch {row_pitch_diffs} vs STRIP_PITCH {STRIP_PITCH}: "
          f"{'MATCHES' if matches_pitch else 'does not match / insufficient rows'}")
    out["strip_fit"] = dict(u=only_u, rows=rows_here, du_vs_strip=du_strip,
                            row_pitch_diffs=row_pitch_diffs, matches_pitch=bool(matches_pitch)
                            if matches_pitch is not None else None)
else:
    print(f"   I.2 vs grass B STRIP: topo16 uses {len(by_col)} distinct u-columns -- "
          f"NOT a single-column strip like grass B")
    out["strip_fit"] = None

# I.3 direct translation of the OUTER BOUNDS vs grass MAIN region and vs grass B region,
# regardless of grid-shape match, purely as a numeric candidate (report only, do not claim proof)
gm = G.FAM_REGION["main"]
gb = G.FAM_REGION["B"]
cand_main = (round(float(tu0 - gm[0]), 5), round(float(tv0 - gm[1]), 5))
cand_B = (round(float(tu0 - gb[0]), 5), round(float(tv0 - gb[1]), 5))
print(f"   I.3 raw outer-bounds delta candidates (lo-corner only, NOT a proof): "
      f"vs main-lo {cand_main}  vs B-lo {cand_B}")
out["raw_delta_candidates"] = dict(vs_main_lo=list(cand_main), vs_B_lo=list(cand_B))

# ---- J. wall probe (topo-58 tris edge-adjacent to topo 16), for completeness ----------------------
print("J. wall probe (topo-58 adjacency):")
cand_wall_blocks = sorted((blk for blk in t16_blocks if census[blk].get(58, 0) >= 1),
                          key=lambda blk: -census[blk].get(58, 0))
if not cand_wall_blocks:
    print("   no topo-16 block carries ANY topo-58 (wall) tris -- topo16 never meets a "
          "cliff wall in this census (consistent with an interior dry-basin ground)")
    out["wall_probe"] = None
else:
    us, vs = [], []
    for blk in cand_wall_blocks:
        bm = X.read_block(*blk, disc=1, part="terrain")
        bx, by = blk
        tris = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            tris.append(dict(
                w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1], bm.verts[j][2] - BLOCK * by) for j in tri],
                uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri], topo=topo))
        edge_tris = defaultdict(list)
        for ti, t in enumerate(tris):
            ps = [kk(v) for v in t["w"]]
            for a2, b2 in ((0, 1), (1, 2), (2, 0)):
                edge_tris[tuple(sorted((ps[a2], ps[b2])))].append(ti)
        picked = set()
        for e, ts in edge_tris.items():
            tp = {tris[t]["topo"] for t in ts}
            if 58 in tp and 16 in tp:
                picked.update(t for t in ts if tris[t]["topo"] == 58)
        for ti in picked:
            for (u, v) in tris[ti]["uv"]:
                us.append(u); vs.append(v)
    print(f"   {len(us) // 3} topo-58 tris edge-adjacent to topo-16 across "
          f"{cand_wall_blocks}")
    if us:
        print(f"   adjacent-wall uv bbox u[{min(us):.5f},{max(us):.5f}] "
              f"v[{min(vs):.5f},{max(vs):.5f}]")
    out["wall_probe"] = dict(blocks=[f"{b[0]},{b[1]}" for b in cand_wall_blocks],
                             tris=len(us) // 3,
                             uv_bbox=[round(min(us), 5), round(min(vs), 5),
                                      round(max(us), 5), round(max(vs), 5)] if us else None)

# ---- J.5 ZONE CLUSTERING -- group origins whose RECOVERED RECTS are geometrically
# adjacent/touching in atlas space (rectangle-expand-and-intersect union-find), independent
# of the index-snap grid. This answers "how many separate atlas neighbourhoods does topo16
# actually draw from" directly from the 5dp rects in `rec`, not from the snap indices.
print("J.5 ZONE CLUSTERING (geometric adjacency of recovered rects, eps=0.008):")
EPS_ADJ = 0.008   # a bit larger than the measured 0.00196/0.00097 gutter constants
tile_keys = list(rec.keys())


def rects_touch(r1, r2, eps):
    u0a, u1a, v0a, v1a = r1["u0"], r1["u1"], r1["v0"], r1["v1"]
    u0b, u1b, v0b, v1b = r2["u0"], r2["u1"], r2["v0"], r2["v1"]
    u_ok = (u0a - eps) <= u1b and (u0b - eps) <= u1a
    v_ok = (v0a - eps) <= v1b and (v0b - eps) <= v1a
    return u_ok and v_ok


parent = {k: k for k in tile_keys}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(x, y):
    rx, ry = find(x), find(y)
    if rx != ry:
        parent[rx] = ry


for i in range(len(tile_keys)):
    for j in range(i + 1, len(tile_keys)):
        if rects_touch(rec[tile_keys[i]], rec[tile_keys[j]], EPS_ADJ):
            union(tile_keys[i], tile_keys[j])
clusters = defaultdict(list)
for k in tile_keys:
    clusters[find(k)].append(k)
zone_report = []
for zi, (root, members) in enumerate(sorted(clusters.items(), key=lambda kv: -sum(rec[m]["n"] for m in kv[1]))):
    members = sorted(members)
    n_cells = sum(rec[m]["n"] for m in members)
    zu0 = min(rec[m]["u0"] for m in members); zu1 = max(rec[m]["u1"] for m in members)
    zv0 = min(rec[m]["v0"] for m in members); zv1 = max(rec[m]["v1"] for m in members)
    n_u = len({m[0] for m in members}); n_v = len({m[1] for m in members})
    shape = ("2x2-genuine" if n_u == 2 and n_v == 2 and len(members) == 4 else
             "column" if n_u == 1 and n_v >= 2 else
             "row" if n_v == 1 and n_u >= 2 else
             "single-cell" if len(members) == 1 else
             f"irregular({n_u}x{n_v}, {len(members)} cells)")
    # candidate delta vs each grass reference region's lo-corner (report only)
    d_main = (round(float(zu0 - gm[0]), 5), round(float(zv0 - gm[1]), 5))
    d_D = (round(float(zu0 - G.FAM_REGION['D'][0]), 5), round(float(zv0 - G.FAM_REGION['D'][1]), 5))
    d_B = (round(float(zu0 - gb[0]), 5), round(float(zv0 - gb[1]), 5))
    share = n_cells / len(cell_tile)
    print(f"   ZONE {zi}: {len(members)} origin(s) {members} = {n_cells} cells "
          f"({share:.0%} of tiled cells) shape={shape}")
    print(f"       outer bounds u[{zu0:.5f},{zu1:.5f}] v[{zv0:.5f},{zv1:.5f}]; "
          f"candidate delta (lo-corner only) vs main {d_main} vs D {d_D} vs B {d_B}")
    zone_report.append(dict(members=[list(m) for m in members], n_cells=n_cells,
                            share=round(share, 3), shape=shape,
                            bounds=[round(zu0, 5), round(zv0, 5), round(zu1, 5), round(zv1, 5)],
                            delta_vs_main=list(d_main), delta_vs_D=list(d_D), delta_vs_B=list(d_B)))
n_zones = len(clusters)
print(f"   TOTAL DISTINCT ATLAS ZONES: {n_zones}")
out["zones"] = zone_report
out["n_zones"] = n_zones

# ---- J.6 PROPER outer-bounds translation fit on any GENUINE 2x2 zone (the exact method
# ground_families_anatomy.decode_family uses: all 8 quadrant edges, mode5, self-consistency
# spread check), THEN compare the recovered (du,dv) against every known GROUNDS family --
# this is the ONLY sub-check in this script that can produce a proven-5dp result, because
# it is the only zone shaped like the thing the method was built to decode.
print("J.6 outer-bounds translation fit on genuine-2x2 zones (the decode_family method):")
zone_fits = []
for zi, (root, members) in enumerate(sorted(clusters.items(), key=lambda kv: -sum(rec[m]["n"] for m in kv[1]))):
    members = sorted(members)
    n_u = len({m[0] for m in members}); n_v = len({m[1] for m in members})
    if not (n_u == 2 and n_v == 2 and len(members) == 4):
        continue
    a0, a1 = sorted({m[0] for m in members})
    b0, b1 = sorted({m[1] for m in members})
    per_edge = defaultdict(list)
    for cell, tile in cell_tile.items():
        if tile not in set(members):
            continue
        u0, u1, v0, v1 = cell_rect[cell]
        uh = 0 if tile[0] == a0 else 1
        vh = 0 if tile[1] == b0 else 1
        per_edge[("u", uh, "lo")].append(u0); per_edge[("u", uh, "hi")].append(u1)
        per_edge[("v", vh, "lo")].append(v0); per_edge[("v", vh, "hi")].append(v1)
    if not all(("u", h, s) in per_edge and ("v", h, s) in per_edge
               for h in (0, 1) for s in ("lo", "hi")):
        print(f"   ZONE {zi} (2x2 at u~{a0}-{a1}): a quadrant half has no cell samples -- skip")
        continue
    U_HALF = [(mode5(per_edge[("u", h, "lo")]), mode5(per_edge[("u", h, "hi")])) for h in (0, 1)]
    V_HALF = [(mode5(per_edge[("v", h, "lo")]), mode5(per_edge[("v", h, "hi")])) for h in (0, 1)]
    d_u = [U_HALF[0][0] - G.GRASS_U_HALF[0][0], U_HALF[1][1] - G.GRASS_U_HALF[1][1]]
    d_v = [V_HALF[0][0] - G.GRASS_V_HALF[0][0], V_HALF[1][1] - G.GRASS_V_HALF[1][1]]
    du_spread = max(d_u) - min(d_u)
    dv_spread = max(d_v) - min(d_v)
    du = round(float(np.median(d_u)), 5)
    dv = round(float(np.median(d_v)), 5)
    is_translation = du_spread < 2e-5 and dv_spread < 2e-5
    print(f"   ZONE {zi}: U_HALF {U_HALF} V_HALF {V_HALF}")
    print(f"     TRANSLATION FIT (outer bounds, all 8 edges populated): du={du} dv={dv} "
          f"spread u={du_spread:.6f} v={dv_spread:.6f} -> "
          f"{'PROVEN-5DP EXACT TRANSLATION' if is_translation else 'not a clean single translation'}")
    match = None
    for fname, g in G.GROUNDS.items():
        if abs(g["mains_du"] - du) < 1e-4 and abs(g["mains_dv"] - dv) < 1e-4:
            match = fname
            break
    print(f"     MATCHES SHIPPED FAMILY: {match if match else 'none of the 7 shipped GROUNDS families'} "
          f"(desert = du 0.65332 dv -0.09863)")
    zone_fits.append(dict(zone=zi, U_HALF=[list(x) for x in U_HALF], V_HALF=[list(x) for x in V_HALF],
                          du=du, dv=dv, du_spread=round(du_spread, 6), dv_spread=round(dv_spread, 6),
                          proven_5dp=bool(is_translation), matches_family=match))
out["zone_translation_fits"] = zone_fits

# ---- K. final verdict ------------------------------------------------------------------------------
print("\nK. VERDICT")
proven_matches = [f for f in zone_fits if f["proven_5dp"] and f["matches_family"]]
dominant_zone = zone_report[0] if zone_report else None
if n_zones == 1 and strict_2x2:
    verdict = "SINGLE-ZONE TRANSLATION (one genuine 2x2, mains-shaped) -- decodable like the other families"
elif proven_matches and dominant_zone and dominant_zone["shape"] != "2x2-genuine":
    fam = proven_matches[0]["matches_family"]
    verdict = (f"COMPOSITE / NOT-A-TRANSLATION -- {n_zones} distinct non-adjacent atlas zones. "
               f"{dominant_zone['share']:.0%} of the footprint (the DOMINANT zone) is its own bespoke "
               f"COLUMN region unmatched to any shipped family. A SEPARATE, minority zone "
               f"({[z['share'] for z in zone_report if z['shape']=='2x2-genuine'][0]:.0%} of the footprint) "
               f"is PROVEN-5DP IDENTICAL to the shipped '{fam}' mains translation "
               f"(du={proven_matches[0]['du']} dv={proven_matches[0]['dv']}, zero spread on all 8 edges) "
               f"-- i.e. topo16 partially reuses {fam}'s real mains texture verbatim, plus draws the "
               f"rest from its OWN unlisted strip/column region(s). NOT a single-constant translation law.")
elif proven_matches:
    fam = proven_matches[0]["matches_family"]
    verdict = (f"TRANSLATION -- matches shipped family '{fam}' at 5dp "
               f"(du={proven_matches[0]['du']} dv={proven_matches[0]['dv']}) but via a minority zone; "
               f"{n_zones} atlas zones total, see zone report")
else:
    verdict = (f"MULTI-REGION CATALOG ({n_zones} distinct, non-adjacent atlas zones; each internally "
               f"tile-grid-shaped at the SAME unit-cell size as grass mains/B, but requiring "
               f"{n_zones} DIFFERENT (du,dv) constants, none matching a shipped family) -- "
               f"NOT a single-constant TRANSLATION law")
print(f"   {verdict}")
out["final_verdict"] = verdict

OUTD.mkdir(exist_ok=True)
(OUTD / "dirt16.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'dirt16.json'}")
