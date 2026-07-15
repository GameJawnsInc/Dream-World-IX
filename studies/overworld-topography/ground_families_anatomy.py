"""THE GROUND FAMILIES -- which walkable grounds are grass TRANSLATIONS?

The desert study (desert_ground_anatomy.py) proved topo-17 ground = the grass mains
grammar TRANSLATED in the atlas (mains +(0.65332,-0.09863), byte-exact 5dp) -- one
constant pair grew ``grassland.GROUNDS``. This study runs the SAME method over every
remaining walkable ground family from the 260-block census, plus controls:

  controls   grass0 (topo 0; must recover delta (0,0) exactly) and the grass
             gameplay variants (1/2/3/10/11/12/13/42; the family model says same look).
  candidates scrub (4/5/6) -- borders desert heavily; dirt-hillside (38) -- the
             walkable steep-slope class; snow (27/28) -- Lost Continent; canyon
             red-rock (45/46) -- Forgotten mid-tier; the dirt gameplay variants
             16/19/20/41 (the family model predicts they decode under the DESERT rects).

Per family: census -> top specimen blocks -> per-4u-cell EXACT affine decode (the
linear-in-XZ law) -> mural screen (murals are linear but low-density) -> half-tile
rect-origin clustering -> AUTO 2x2 quadrant-set detection -> 5dp rect recovery ->
width/gutter vs grass -> THE TRANSLATION FIT (all 8 edges must agree at 5dp) ->
the subset grammar gate (re-based grass 16-hypothesis exact decode) -> the WALL probe
(topo-58 tris edge-adjacent to the family: band extents vs the grass ROCK band).

Artifacts -> out/ground_families.json. Run from the repo root:
    py studies/overworld-topography/ground_families_anatomy.py
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
GRASS_WALL_U = (0.699, 0.947)                               # island.py ROCK_U (base band)
GRASS_WALL_V = (0.893, 0.923)                               # sorted ROCK_V
DESERT_WALL = dict(u=(0.42773, 0.67578), v=(0.87207, 0.90234))
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))

# (name, member-topos, expectation-note)
FAMILIES = [
    ("grass0", (0,), "CONTROL -- must fit delta (0,0)"),
    ("grassvar", (1, 2, 3, 10, 11, 12, 13, 42), "control -- family model says grass look"),
    ("scrub", (4, 5, 6), "candidate (borders desert)"),
    ("brush", (38,), "candidate (walkable steep-slope)"),
    ("snow", (27, 28), "candidate (Lost Continent)"),
    ("canyon", (45, 46), "candidate (Forgotten red tiers)"),
    ("dirt16", (16,), "dirt variant -- expect DESERT rects"),
    ("dirt19", (19,), "dirt variant -- expect DESERT rects"),
    ("dirt20", (20,), "dirt variant -- expect DESERT rects"),
    ("dirt41", (41,), "dirt variant -- expect DESERT rects"),
]

out = {}

# ---- A. one map-wide census pass (full topo counter per block) --------------------------------
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
print(f"A. census: {len(census)} blocks")
out["census_blocks"] = len(census)

_block_cache = {}


def load_tris(bx, by):
    """All terrain tris of a block in the world frame, with uv + topo."""
    if (bx, by) not in _block_cache:
        bm = X.read_block(bx, by, disc=1, part="terrain")
        tris = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            tris.append(dict(
                w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
                    bm.verts[j][2] - BLOCK * by) for j in tri],
                uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
                topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]))
        _block_cache[(bx, by)] = tris
    return _block_cache[(bx, by)]


def mode5(vals):
    return Counter(round(v, 5) for v in vals).most_common(1)[0][0]


def decode_family(name, topos, note):
    fam = {"note": note, "topos": list(topos)}
    counts = {blk: sum(c.get(t, 0) for t in topos) for blk, c in census.items()}
    spec = [blk for blk, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n >= 30][:8]
    total = sum(counts.values())
    fam["total_tris"] = total
    fam["specimens"] = [f"{b[0]},{b[1]}" for b in spec]
    print(f"\n== {name} {topos} -- {note}")
    print(f"   map total {total} tris over {sum(1 for n in counts.values() if n)} blocks; "
          f"specimens {spec}")
    if not spec:
        print("   TOO THIN -- no block with >=30 tris; skipping")
        fam["verdict"] = "too-thin"
        return fam

    ftris = [t for blk in spec for t in load_tris(*blk) if t["topo"] in topos]
    fam["specimen_tris"] = len(ftris)

    # per-4u-cell exact affine
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
    print(f"   exact-linear: {len(lin_ok)}/{n_cells} cells ({len(lin_ok) / max(1, n_cells):.0%})")
    fam["linear"] = dict(cells=n_cells, exact=len(lin_ok))

    # rect per cell + THE MURAL SCREEN (murals are linear but low-density)
    cell_rect = {}
    n_mural = 0
    for (i, j), (cu, cv) in lin_ok.items():
        corn = [(4.0 * i, 4.0 * j), (4.0 * (i + 1), 4.0 * j),
                (4.0 * i, 4.0 * (j + 1)), (4.0 * (i + 1), 4.0 * (j + 1))]
        us = [cu[0] * x + cu[1] * z + cu[2] for (x, z) in corn]
        vs = [cv[0] * x + cv[1] * z + cv[2] for (x, z) in corn]
        du4, dv4 = max(us) - min(us), max(vs) - min(vs)
        if du4 < TILE_U * 0.5 or dv4 < TILE_V * 0.5:
            n_mural += 1
            continue
        cell_rect[(i, j)] = (min(us), max(us), min(vs), max(vs))
    print(f"   mural/low-density screened: {n_mural}; tiled cells {len(cell_rect)}")
    fam["mural_cells"] = n_mural
    if len(cell_rect) < 24:
        print("   TOO FEW tiled cells for rect recovery -- likely mural-only")
        fam["verdict"] = "mural-only"
        return fam

    # half-tile-snapped origins -> AUTO 2x2
    cell_tile = {c: (round(r[0] / TILE_U * 2) / 2, round(r[2] / TILE_V * 2) / 2)
                 for c, r in cell_rect.items()}
    tiles = Counter(cell_tile.values())
    fam["tile_origins_top"] = [[t[0], t[1], n] for t, n in tiles.most_common(10)]
    best_base, best_n = None, 0
    for (a, b) in tiles:
        n = sum(tiles.get(o, 0) for o in ((a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)))
        if n > best_n:
            best_base, best_n = (a, b), n
    share = best_n / max(1, len(cell_tile))
    a, b = best_base
    mains_origins = {(a, b), (a + 1, b), (a, b + 1), (a + 1, b + 1)}
    print(f"   top origins: {[(t, n) for t, n in tiles.most_common(6)]}")
    print(f"   AUTO 2x2 base ({a},{b}) covers {best_n}/{len(cell_tile)} tiled cells "
          f"({share:.0%})")
    fam["mains_base"] = [a, b]
    fam["mains_share"] = round(share, 3)
    if share < 0.15:
        print("   NO dominant 2x2 -- not the grass mains structure")
        fam["verdict"] = "no-2x2"
        return fam

    # 5dp rect recovery over the mains cells
    per_edge = defaultdict(list)
    for cell, tile in cell_tile.items():
        if tile not in mains_origins:
            continue
        u0, u1, v0, v1 = cell_rect[cell]
        uh = 0 if tile[0] == a else 1
        vh = 0 if tile[1] == b else 1
        per_edge[("u", uh, "lo")].append(u0)
        per_edge[("u", uh, "hi")].append(u1)
        per_edge[("v", vh, "lo")].append(v0)
        per_edge[("v", vh, "hi")].append(v1)
    if not all(("u", h, s) in per_edge and ("v", h, s) in per_edge
               for h in (0, 1) for s in ("lo", "hi")):
        print("   2x2 detected but a quadrant half has no samples -- thin data")
        fam["verdict"] = "thin-2x2"
        return fam
    U_HALF = [(mode5(per_edge[("u", h, "lo")]), mode5(per_edge[("u", h, "hi")]))
              for h in (0, 1)]
    V_HALF = [(mode5(per_edge[("v", h, "lo")]), mode5(per_edge[("v", h, "hi")]))
              for h in (0, 1)]
    print(f"   rects (5dp): U_HALF {U_HALF}  V_HALF {V_HALF}")
    fam["U_HALF"], fam["V_HALF"] = U_HALF, V_HALF

    # THE TRANSLATION FIT on the 2x2 OUTER BOUNDS (bleed-immune -- the internal hi/lo
    # mode-edges are contaminated by the gutter-crossing window form, the desert
    # study's C2b "gutter-class" failures; the desert law itself came from lo edges)
    d_u = [U_HALF[0][0] - G.GRASS_U_HALF[0][0], U_HALF[1][1] - G.GRASS_U_HALF[1][1]]
    d_v = [V_HALF[0][0] - G.GRASS_V_HALF[0][0], V_HALF[1][1] - G.GRASS_V_HALF[1][1]]
    du_spread = max(d_u) - min(d_u)
    dv_spread = max(d_v) - min(d_v)
    du = round(float(np.median(d_u)), 5)
    dv = round(float(np.median(d_v)), 5)
    translation = du_spread < 2e-5 and dv_spread < 2e-5
    print(f"   TRANSLATION FIT (outer bounds): du {du} dv {dv}  spread u {du_spread:.6f} "
          f"v {dv_spread:.6f} -> {'EXACT TRANSLATION' if translation else 'NOT a pure translation'}")
    # internal-edge diagnostic: how far the mode hi-edges sit from the translated grass
    # rect edge (0 = rect-locked mode; +gutter = the window form dominates the vote)
    int_u = round(U_HALF[0][1] - (G.GRASS_U_HALF[0][1] + du), 5)
    int_v = round(V_HALF[0][1] - (G.GRASS_V_HALF[0][1] + dv), 5)
    print(f"   internal-edge modes vs locked form: u {int_u} v {int_v} "
          f"(gutter = 0.00196/0.00097)")
    fam["translation"] = dict(du=du, dv=dv, exact=bool(translation),
                              du_spread=round(du_spread, 6), dv_spread=round(dv_spread, 6),
                              internal_u=int_u, internal_v=int_v)

    # the subset grammar gate: the grass 16-hypothesis decode on the TRANSLATED GRASS
    # rects (exactly what the mint's ground_uv emits -- the locked-form share)
    def fam_uv(x, z, cell, quad, ori):
        (i, j) = cell
        fx = (x - 4.0 * i) / 4.0
        fz = (z - 4.0 * j) / 4.0
        aa, bb = G.rot_ab(fx, fz, ori)
        uh, vh = quad
        aa = max(0.0 if uh == 0 else -0.15, min(1.15 if uh == 0 else 1.0, aa))
        bb = max(0.0 if vh == 0 else -0.15, min(1.15 if vh == 0 else 1.0, bb))
        u0, u1 = G.GRASS_U_HALF[uh][0] + du, G.GRASS_U_HALF[uh][1] + du
        v0, v1 = G.GRASS_V_HALF[vh][0] + dv, G.GRASS_V_HALF[vh][1] + dv
        return (u0 + aa * (u1 - u0), v0 + bb * (v1 - v0))

    QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
    mains_cells = [c for c, t in cell_tile.items() if t in mains_origins]
    n_exact = 0
    for cell in mains_cells:
        hit = False
        for quad in QUADS:
            for ori in G.ORIS:
                err = 0.0
                for ti in cell_tris[cell]:
                    t = ftris[ti]
                    for (x, y, z), (u, v) in zip(t["w"], t["uv"]):
                        mu, mv = fam_uv(x, z, cell, quad, ori)
                        err = max(err, abs(mu - u), abs(mv - v))
                        if err >= 1e-4:
                            break
                    if err >= 1e-4:
                        break
                if err < 1e-4:
                    hit = True
                    break
            if hit:
                break
        n_exact += hit
    print(f"   GRAMMAR GATE: {n_exact}/{len(mains_cells)} mains cells decode EXACTLY "
          f"({n_exact / max(1, len(mains_cells)):.0%}) under the re-based grass grammar")
    fam["grammar_gate"] = dict(cells=len(mains_cells), exact=n_exact)
    fam["verdict"] = ("TRANSLATION" if translation else "2x2-but-not-translation")
    return fam


def wall_probe(name, topos, fam):
    """Topo-58 tris edge-adjacent to the family: the native cliff-wall band."""
    cand = sorted((blk for blk, c in census.items()
                   if sum(c.get(t, 0) for t in topos) >= 20 and c.get(58, 0) >= 6),
                  key=lambda blk: -census[blk].get(58, 0))[:8]
    if not cand:
        print("   wall probe: no family+58 co-blocks -- wall lever undetermined")
        fam["wall"] = None
        return
    us, vs = [], []
    for blk in cand:
        tris = load_tris(*blk)
        edge_tris = defaultdict(list)
        for ti, t in enumerate(tris):
            ps = [kk(v) for v in t["w"]]
            for a2, b2 in ((0, 1), (1, 2), (2, 0)):
                edge_tris[tuple(sorted((ps[a2], ps[b2])))].append(ti)
        picked = set()
        for e, ts in edge_tris.items():
            tp = {tris[t]["topo"] for t in ts}
            if 58 in tp and tp & set(topos):
                picked.update(t for t in ts if tris[t]["topo"] == 58)
        for ti in picked:
            for (u, v) in tris[ti]["uv"]:
                us.append(u)
                vs.append(v)
    if len(us) < 18:
        print(f"   wall probe: only {len(us) // 3} adjacent 58-tris -- too thin")
        fam["wall"] = dict(thin=True, corners=len(us))
        return
    ua = np.array(sorted(us))
    v_levels = Counter(round(v, 5) for v in vs).most_common(6)
    # the band rows = the two dominant v-level modes (base row v > top row v)
    rows = sorted(lv for lv, _ in v_levels[:2])
    u_lo, u_hi = round(float(ua[0]), 5), round(float(ua[-1]), 5)
    width_ok = abs((u_hi - u_lo) - 0.24805) < 2e-4
    # mint-convention deltas (vs ROCK_U[0]=0.699 / ROCK_V[0]=0.923 -- how GROUNDS
    # wall_du/wall_dv are applied in island.py)
    wdu = round(u_lo - 0.699, 5)
    wdv = round(rows[1] - 0.923, 5)
    print(f"   wall probe ({len(us) // 3} tris on {[f'{b[0]},{b[1]}' for b in cand]}): "
          f"u [{u_lo},{u_hi}] width {round(u_hi - u_lo, 5)} "
          f"({'=' if width_ok else '!='} the 0.24805 band) rows base {rows[1]} top {rows[0]}")
    print(f"   wall v-levels: {v_levels}")
    print(f"   candidate wall translation (mint conv): du {wdu} dv {wdv} "
          f"(grass 0/0; desert -0.27127/-0.02066)")
    fam["wall"] = dict(u=[u_lo, u_hi], rows=rows, du=wdu, dv=wdv, width_ok=bool(width_ok),
                       v_levels=[[lv, n] for lv, n in v_levels],
                       tris=len(us) // 3, blocks=[f"{b[0]},{b[1]}" for b in cand])


for name, topos, note in FAMILIES:
    fam = decode_family(name, topos, note)
    if fam.get("U_HALF"):
        wall_probe(name, topos, fam)
    out[name] = fam

# the dirt variants: also report their delta vs the DESERT rects directly
DES = G.GROUNDS["desert"]
print("\n== dirt variants vs the DESERT rects (family-model check)")
for name in ("dirt16", "dirt19", "dirt20", "dirt41"):
    fam = out.get(name) or {}
    tr = fam.get("translation")
    if tr:
        print(f"   {name}: delta vs desert du {round(tr['du'] - DES['mains_du'], 5)} "
              f"dv {round(tr['dv'] - DES['mains_dv'], 5)} (0/0 = same tile set)")

OUTD.mkdir(exist_ok=True)
(OUTD / "ground_families.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'ground_families.json'}")
