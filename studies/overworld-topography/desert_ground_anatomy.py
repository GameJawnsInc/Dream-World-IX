"""THE DESERT GROUND ANATOMY -- does topo-17 wasteland speak the grass MAINS grammar?

The crag carry's mechanism is in-game proven, but its foot fringe is painted against
topo-17 DESERT ground -- judging "reads native" needs a native-ground island, which
needs the desert tile language. The grass language (grassland.py, in-game proven) is:
ONE 2x2 quadrant tile-set at a fixed atlas region; ONE quadrant fills ONE 4u lattice
cell; UV EXACTLY linear in world XZ; 4 rotations, one handedness (rot_ab); a
same-quadrant-avoiding neighbour policy; never-flat relief. Per unknown:

  A. CENSUS -- which disc-1 blocks carry topo-17 (and topo-38) ground, how much, where.
  B. THE REGION -- corner-pure cells' uv values cluster at the quadrant-set edges:
     recover the desert U_HALF / V_HALF rects (the grass analogues).
  C. THE GRAMMAR GATE -- with the recovered rects, run the grass 16-hypothesis
     (quad, ori) exact decode per 4u cell: what fraction of desert cells decode EXACTLY
     (err < 1e-4)? ~1.0 => same grammar re-based => a desert ground is a PARAMETER, not
     new machinery.
  D. NEIGHBOUR POLICY -- same-quadrant / same-ori adjacency rates vs grass (12% / 49%).
  E. RELIEF -- per-4u |dY| + y-std vs the grass never-flat law.
  F. THE SHORE -- what rings a desert region: topo-38's role (uv region, y band,
     adjacency to 17/58/sea) + the rock foot fringe (which desert tiles touch topo-49).

Artifacts -> out/desert_ground.json. Run from the repo root:
    py studies/overworld-topography/desert_ground_anatomy.py
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
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
out = {}

# ---- A. map-wide census ---------------------------------------------------------------------
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
        if c.get(17) or c.get(38):
            census[(bx, by)] = dict(t17=c.get(17, 0), t38=c.get(38, 0),
                                    total=sum(c.values()))
top = sorted(census.items(), key=lambda kv: -kv[1]["t17"])
print(f"A. blocks with topo-17/38: {len(census)}; top by t17:")
for blk, c in top[:12]:
    print(f"   {blk}: t17 {c['t17']:4d}  t38 {c['t38']:4d}  (of {c['total']})")
out["census"] = {f"{k[0]},{k[1]}": v for k, v in census.items()}

SPECIMENS = [blk for blk, _ in top[:8]]
print(f"specimens: {SPECIMENS}")

# ---- load specimen tris (world frame) ---------------------------------------------------------
tris = []
for (bx, by) in SPECIMENS:
    bm = X.read_block(bx, by, disc=1, part="terrain")
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        tris.append(dict(
            w=[(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1],
                bm.verts[j][2] - BLOCK * by) for j in tri],
            uv=[(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri],
            topo=X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]))
d17 = [t for t in tris if t["topo"] == 17]
d38 = [t for t in tris if t["topo"] == 38]
print(f"specimen tris: {len(tris)} total, topo17 {len(d17)}, topo38 {len(d38)}")

# ---- B. the region: corner-pure cells --------------------------------------------------------
# corners sitting EXACTLY on the 4u lattice carry the quadrant rect's corner uvs
pure_u, pure_v = [], []
for t in d17:
    for (x, y, z), (u, v) in zip(t["w"], t["uv"]):
        if abs(x / 4.0 - round(x / 4.0)) < 1e-6 and abs(z / 4.0 - round(z / 4.0)) < 1e-6:
            pure_u.append(u)
            pure_v.append(v)
pu = np.array(sorted(pure_u))
pv = np.array(sorted(pure_v))
print(f"B. corner-pure samples: {len(pu)}; u [{pu.min():.5f},{pu.max():.5f}] "
      f"v [{pv.min():.5f},{pv.max():.5f}]")


def edges_of(vals, tol=0.0012):
    """Cluster sorted values -> cluster medians (the rect edges)."""
    cl = [[float(vals[0])]]
    for v in vals[1:]:
        if v - cl[-1][-1] > tol:
            cl.append([])
        cl[-1].append(float(v))
    return [round(float(np.median(c)), 5) for c in cl if len(c) >= max(3, len(vals) * 0.005)]


ue = edges_of(pu)
ve = edges_of(pv)
print(f"   u-edge clusters: {ue}")
print(f"   v-edge clusters: {ve}")
out["u_edges"] = ue
out["v_edges"] = ve

# The edge structure is NOT one 2x2 quadrant set (grass-style): many ~1-tile-wide pairs.
# Decode generally instead: per 4u cell, fit the EXACT affine u,v = A + B*x + C*z (the
# grass law says the map is linear-in-XZ; if desert obeys it too, the per-cell fit is
# exact) -> evaluate the cell's mapped RECT + orientation -> cluster rects into the
# actual tile vocabulary.

# ---- C. per-cell affine decode ------------------------------------------------------------------
cell_tris = defaultdict(list)
for ti, t in enumerate(d17):
    cx = sum(p[0] for p in t["w"]) / 3
    cz = sum(p[2] for p in t["w"]) / 3
    cell_tris[(math.floor(cx / 4.0), math.floor(cz / 4.0))].append(ti)
n_cells = len(cell_tris)
lin_ok = {}
for cell, tl in cell_tris.items():
    rows, ru, rv = [], [], []
    for ti in tl:
        t = d17[ti]
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
print(f"C. per-cell EXACT-LINEAR fit: {len(lin_ok)}/{n_cells} desert cells "
      f"({len(lin_ok) / max(1, n_cells):.0%}) obey the linear-in-XZ law")
out["linear"] = dict(cells=n_cells, exact=len(lin_ok))

# orientation + rect + density per linear cell
TILE_U, TILE_V = 0.0625, 0.03125
tiles = Counter()
oris_c = Counter()
dens_u, dens_v = [], []
cell_tile = {}
for (i, j), (cu, cv) in lin_ok.items():
    # evaluate the map at the cell's 4 corners
    corn = [(4.0 * i, 4.0 * j), (4.0 * (i + 1), 4.0 * j),
            (4.0 * i, 4.0 * (j + 1)), (4.0 * (i + 1), 4.0 * (j + 1))]
    us = [cu[0] * x + cu[1] * z + cu[2] for (x, z) in corn]
    vs = [cv[0] * x + cv[1] * z + cv[2] for (x, z) in corn]
    u0, u1 = min(us), max(us)
    v0, v1 = min(vs), max(vs)
    dens_u.append((u1 - u0) / 4.0)
    dens_v.append((v1 - v0) / 4.0)
    # orientation: which axis drives u (grass rot_ab families)
    if abs(cu[0]) > abs(cu[1]):
        oris_c[0 if cu[0] > 0 else 180] += 1
    else:
        oris_c[90 if cu[1] > 0 else 270] += 1
    tile = (round(u0 / TILE_U * 2) / 2, round(v0 / TILE_V * 2) / 2)  # half-tile snap
    tiles[tile] += 1
    cell_tile[(i, j)] = tile
print(f"   rect span/4u: du med {np.median(dens_u) * 4:.4f} dv med {np.median(dens_v) * 4:.4f} "
      f"(one 128px tile = {TILE_U:.4f} x {TILE_V:.4f})")
print(f"   orientations: {dict(oris_c)}")
print(f"   distinct half-tile-snapped rect origins: {len(tiles)}; top12:")
for tile, n in tiles.most_common(12):
    print(f"     u {tile[0] * TILE_U:.5f} v {tile[1] * TILE_V:.5f}: {n} cells")
out["tiles"] = {f"{t[0]},{t[1]}": n for t, n in tiles.most_common()}
out["density"] = dict(du4=round(float(np.median(dens_u) * 4), 5),
                      dv4=round(float(np.median(dens_v) * 4), 5))

# D. neighbour policy over the tile ids
same_t = pairs = 0
for (i, j), tile in cell_tile.items():
    for n in ((i + 1, j), (i, j + 1)):
        if n in cell_tile:
            pairs += 1
            same_t += cell_tile[n] == tile
if pairs:
    print(f"D. neighbour policy: same-tile {same_t / pairs:.0%} over {pairs} pairs "
          f"(grass same-quadrant: 12%)")
    out["neighbour"] = dict(pairs=pairs, same_tile=same_t)

# ---- C2. pin THE DESERT MAINS 2x2 rects at 5dp + the subset grammar gate ----------------------
# the four dominant origins form one 2x2 quadrant set (the grass-mains analogue)
MAINS_ORIGINS = {(10.5, 21.5), (10.5, 22.5), (11.5, 21.5), (11.5, 22.5)}
per_edge = defaultdict(list)                                # (axis, half, lo/hi) -> vals
for (i, j), (cu, cv) in lin_ok.items():
    tile = cell_tile.get((i, j))
    if tile not in MAINS_ORIGINS:
        continue
    corn = [(4.0 * i, 4.0 * j), (4.0 * (i + 1), 4.0 * j),
            (4.0 * i, 4.0 * (j + 1)), (4.0 * (i + 1), 4.0 * (j + 1))]
    us = [cu[0] * x + cu[1] * z + cu[2] for (x, z) in corn]
    vs = [cv[0] * x + cv[1] * z + cv[2] for (x, z) in corn]
    uh = 0 if tile[0] == 10.5 else 1
    vh = 0 if tile[1] == 21.5 else 1
    per_edge[("u", uh, "lo")].append(min(us))
    per_edge[("u", uh, "hi")].append(max(us))
    per_edge[("v", vh, "lo")].append(min(vs))
    per_edge[("v", vh, "hi")].append(max(vs))


def mode5(vals):
    """The sharpest (most repeated, 5dp) value -- corner-locked cells dominate; bleed
    cells scatter and lose the vote."""
    return Counter(round(v, 5) for v in vals).most_common(1)[0][0]


if all(("u", h, s) in per_edge and ("v", h, s) in per_edge
       for h in (0, 1) for s in ("lo", "hi")):
    DES_U_HALF = [(mode5(per_edge[("u", h, "lo")]), mode5(per_edge[("u", h, "hi")]))
                  for h in (0, 1)]
    DES_V_HALF = [(mode5(per_edge[("v", h, "lo")]), mode5(per_edge[("v", h, "hi")]))
                  for h in (0, 1)]
    print(f"C2. DESERT MAINS rects (5dp): U_HALF {DES_U_HALF}  V_HALF {DES_V_HALF}")
    print(f"    (grass shape: half width 0.06054/0.03028, gutter 0.00196/0.00097)")
    out["DESERT_U_HALF"] = DES_U_HALF
    out["DESERT_V_HALF"] = DES_V_HALF

    def dmains_uv(x, z, cell, quad, ori):
        """The grass mains map re-based to the desert rects, incl. the direction-aware
        bleed clamp (inward/cross-split only, never outside the 2x2 region)."""
        (i, j) = cell
        fx = (x - 4.0 * i) / 4.0
        fz = (z - 4.0 * j) / 4.0
        a, b = G.rot_ab(fx, fz, ori)
        uh, vh = quad
        a = max(0.0 if uh == 0 else -0.15, min(1.15 if uh == 0 else 1.0, a))
        b = max(0.0 if vh == 0 else -0.15, min(1.15 if vh == 0 else 1.0, b))
        u0, u1 = DES_U_HALF[uh]
        v0, v1 = DES_V_HALF[vh]
        return (u0 + a * (u1 - u0), v0 + b * (v1 - v0))

    QUADS = [(u, v) for u in (0, 1) for v in (0, 1)]
    mains_cells = [c for c, t in cell_tile.items() if t in MAINS_ORIGINS]
    n_exact = 0
    for cell in mains_cells:
        hit = False
        for quad in QUADS:
            for ori in G.ORIS:
                err = 0.0
                for ti in cell_tris[cell]:
                    t = d17[ti]
                    for (x, y, z), (u, v) in zip(t["w"], t["uv"]):
                        mu, mv = dmains_uv(x, z, cell, quad, ori)
                        err = max(err, abs(mu - u), abs(mv - v))
                if err < 1e-4:
                    hit = True
                    break
            if hit:
                break
        n_exact += hit
    print(f"    THE SUBSET GRAMMAR GATE: {n_exact}/{len(mains_cells)} desert-mains cells "
          f"decode EXACTLY under the grass grammar re-based to these rects "
          f"({n_exact / max(1, len(mains_cells)):.0%})")
    out["mains_gate"] = dict(cells=len(mains_cells), exact=n_exact)
    share = sum(tiles[t] for t in MAINS_ORIGINS) / max(1, sum(tiles.values()))
    print(f"    the mains set covers {share:.0%} of all decoded desert cells")
    out["mains_share"] = round(share, 3)

    # C2b. failure diagnostic: for failing mains cells, the min-max-err hypothesis and
    # its error magnitude (0.002-class = rect-width/gutter wrong; half-tile-class =
    # phase slides; a few corners only = bleed)
    fails = []
    for cell in mains_cells:
        best_err = 1e9
        for quad in QUADS:
            for ori in G.ORIS:
                err = 0.0
                for ti in cell_tris[cell]:
                    t = d17[ti]
                    for (x, y, z), (u, v) in zip(t["w"], t["uv"]):
                        mu, mv = dmains_uv(x, z, cell, quad, ori)
                        err = max(err, abs(mu - u), abs(mv - v))
                best_err = min(best_err, err)
        if best_err >= 1e-4:
            fails.append(best_err)
    if fails:
        fa = np.array(fails)
        print(f"    C2b failing-cell best-hypothesis err: med {np.median(fa):.5f} "
              f"p10 {np.percentile(fa, 10):.5f} p90 {np.percentile(fa, 90):.5f} "
              f"(gutter-class ~0.002, phase-class ~0.03+)")

    # C3. CHIRALITY -- classify each mains cell's affine axis-map directly (the 8
    # dihedral forms: u driven by +-x or +-z, v by the complementary axis). Grass
    # measured ONE handedness (100%); a ~50% subset-gate suggests desert uses BOTH.
    forms = Counter()
    for cell in mains_cells:
        cu, cv = lin_ok[cell]
        u_ax = "x" if abs(cu[0]) > abs(cu[1]) else "z"
        v_ax = "x" if abs(cv[0]) > abs(cv[1]) else "z"
        su = "+" if (cu[0] if u_ax == "x" else cu[1]) > 0 else "-"
        sv = "+" if (cv[0] if v_ax == "x" else cv[1]) > 0 else "-"
        forms[(f"u{su}{u_ax}", f"v{sv}{v_ax}")] += 1
    print(f"    C3 axis-map forms over mains cells: {dict(forms.most_common())}")
    # the rot_ab (grass) handedness = {(u+x,v-z),(u+z,v+x),(u-x,v+z),(u-z,v-x)}
    GRASS_FORMS = {("u+x", "v-z"), ("u+z", "v+x"), ("u-x", "v+z"), ("u-z", "v-x")}
    n_grass_hand = sum(n for f, n in forms.items() if f in GRASS_FORMS)
    print(f"    grass-handed {n_grass_hand} vs mirrored {sum(forms.values()) - n_grass_hand}")
    out["chirality"] = {str(k): v for k, v in forms.items()}

# ---- E. relief --------------------------------------------------------------------------------
ys_at = {}
for t in d17:
    for p in t["w"]:
        ys_at[(round(p[0], 3), round(p[2], 3))] = p[1]
dys = []
for (x, z), y in ys_at.items():
    for n in ((x + 4.0, z), (x, z + 4.0)):
        n = (round(n[0], 3), round(n[1], 3))
        if n in ys_at:
            dys.append(abs(ys_at[n] - y))
ally = list(ys_at.values())
print(f"E. relief: y std {np.std(ally):.2f}, 4u-neighbour |dY| med {np.median(dys):.2f} "
      f"p90 {np.percentile(dys, 90):.2f} (grass law: std 0.66-1.25, med ~0.2, p90 ~0.5-0.7)")
out["relief"] = dict(y_std=round(float(np.std(ally)), 2),
                     dy_med=round(float(np.median(dys)), 2),
                     dy_p90=round(float(np.percentile(dys, 90)), 2))

# ---- F. the shore + the rock fringe ------------------------------------------------------------
edge_tris = defaultdict(list)
for ti, t in enumerate(tris):
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)
adj17 = Counter()
for e, ts in edge_tris.items():
    tp = {tris[t]["topo"] for t in ts}
    if 17 in tp:
        for q in tp - {17}:
            adj17[q] += 1
print(f"F. topo-17 borders: {dict(adj17.most_common(8))}")
if d38:
    u38 = [u for t in d38 for (u, v) in t["uv"]]
    v38 = [v for t in d38 for (u, v) in t["uv"]]
    y38 = [p[1] for t in d38 for p in t["w"]]
    adj38 = Counter()
    for e, ts in edge_tris.items():
        tp = {tris[t]["topo"] for t in ts}
        if 38 in tp:
            for q in tp - {38}:
                adj38[q] += 1
    print(f"   topo-38: uv u[{min(u38):.3f},{max(u38):.3f}] v[{min(v38):.3f},{max(v38):.3f}] "
          f"y[{min(y38):.1f},{max(y38):.1f}]; borders {dict(adj38.most_common(8))}")
    out["t38"] = dict(u=[round(min(u38), 4), round(max(u38), 4)],
                      v=[round(min(v38), 4), round(max(v38), 4)],
                      y=[round(min(y38), 1), round(max(y38), 1)],
                      borders={str(k): v for k, v in adj38.items()})
# the rock fringe: desert cells whose tris touch topo-49 -- still exact-linear? and do
# they use the same tile vocabulary as open desert or a fringe set?
if lin_ok:
    rockside = set()
    for e, ts in edge_tris.items():
        tp = {tris[t]["topo"] for t in ts}
        if 17 in tp and 49 in tp:
            for p in e:
                rockside.add((math.floor(p[0] / 4.0), math.floor(p[2] / 4.0)))
    n_lin = sum(1 for c in rockside if c in lin_ok)
    fr_tiles = Counter(cell_tile[c] for c in rockside if c in cell_tile)
    open_top = {t for t, _ in tiles.most_common(6)}
    n_open = sum(n for t, n in fr_tiles.items() if t in open_top)
    print(f"   rock-adjacent desert cells: {len(rockside)}, exact-linear {n_lin}; "
          f"their tiles in the open-desert top6: {n_open}/{sum(fr_tiles.values())}")
    out["rock_fringe_cells"] = dict(n=len(rockside), linear=n_lin,
                                    in_open_top6=n_open, of=sum(fr_tiles.values()))

OUTD.mkdir(exist_ok=True)
(OUTD / "desert_ground.json").write_text(json.dumps(out, indent=1, default=str))
print(f"-> {OUTD / 'desert_ground.json'}")
