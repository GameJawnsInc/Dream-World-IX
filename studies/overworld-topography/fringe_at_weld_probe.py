"""THE FRINGE TARGET -- what fraction of stock's ground-weld LINE shows the painted
grass-fringe strip AT the weld.

Context: the band-seat round (level host) killed the seams/meadows/hills but the owner
called the base "a hard cut from ground to mountain" -- the level cut lands mid-course,
so the visible bottom fragments' sampled v stops SHORT of the atlas fringe strip. The
apron build (donor's own weld carried) had the lip intact. This instrument measures the
TARGET NUMBER any transition fix must hit: over stock disc-1's wall census (the same
crest-seeded topo-49/PLATEAU extraction as rock_wall_rim.py, banded components only),
the fraction of ground-weld LINE LENGTH whose wall-side foot tri samples atlas v
reaching >= row 11.0 (the registered criterion; the luminance-measured bright fringe
strip is v-rows ~[10.875, 11.09] -- rock_wall_rim.json r5.atlas_lum strip 7).

Splits: band (tile row 10/11) vs non-band bottom tris; per-tile-row breakdown; the
(15,14) mesa donor alone. Secondary: the GROUND side at/within 4u of the weld --
topo-class shares (grass-class?) + slope + whether foot-adjacent grass wears the same
mains tiles as far-field (the transition lives entirely in the wall-side art).

Read-only vs stock disc-1. Artifacts -> out/fringe_at_weld.json.
Regenerate: py -X utf8 fringe_at_weld_probe.py   (from studies/overworld-topography)
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

PLATEAU = {10, 11, 12}
GRASS_TOPO = {0, 1, 2, 3, 42}                               # terrace_wall_strip's class set
TILE_U, TILE_V = 0.0625, 0.03125
DONOR_BLK = (15, 14)
FRINGE_LO, FRINGE_HI = 10.875, 11.09                        # the bright strip (r5 lum, strip 7 + stock foot p-range)
ANNULUS_D = 4.0                                             # secondary: ground within 4u plan of the weld
ANNULUS_DY = 3.0                                            # |y - nearest weld| guard (excludes other storeys)
OUT = Path(__file__).with_name("out") / "fringe_at_weld.json"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731

PU, PV = json.loads((Path(__file__).with_name("out") / "rock_tiles.json").read_text())["phase"]


def vrow(v):
    return (v - PV) / TILE_V


def tile_row(vs):
    return int(math.floor((min(vs) - PV) / TILE_V + 0.5))


class Acc:
    """Length-weighted accumulator for one edge population."""

    def __init__(self):
        self.L = 0.0                                        # total weld length
        self.L_cross = 0.0                                  # vmin < 11.0 <= vmax (the registered criterion, scoped)
        self.L_raw = 0.0                                    # vmax >= 11.0 (unscoped -- distant-row contamination check)
        self.L_overlap = 0.0                                # tri v-interval overlaps the bright strip
        self.L_edge_fringe = 0.0                            # the WELD-EDGE verts themselves sample the strip
        self.n = 0
        self.edge_vmax = []                                 # sampled v-row AT the weld edge (max of the 2 verts)

    def add(self, L, vmin, vmax, ev_max):
        self.L += L
        self.n += 1
        if vmin < 11.0 - 1e-9 and vmax >= 11.0 - 1e-9:
            self.L_cross += L
        if vmax >= 11.0 - 1e-9:
            self.L_raw += L
        if vmin <= FRINGE_HI and vmax >= FRINGE_LO:
            self.L_overlap += L
        if ev_max >= FRINGE_LO:
            self.L_edge_fringe += L
        self.edge_vmax.append(round(ev_max, 3))

    def out(self):
        def pc(a, q):
            return round(float(np.percentile(a, q)), 2) if a else None
        return dict(
            n_edges=self.n, length=round(self.L, 1),
            fringe_cross=round(self.L_cross / self.L, 4) if self.L else None,
            fringe_raw=round(self.L_raw / self.L, 4) if self.L else None,
            fringe_overlap=round(self.L_overlap / self.L, 4) if self.L else None,
            edge_in_strip=round(self.L_edge_fringe / self.L, 4) if self.L else None,
            edge_vmax=dict(p10=pc(self.edge_vmax, 10), med=pc(self.edge_vmax, 50),
                           p90=pc(self.edge_vmax, 90)))


# population accumulators: (scope, split) -> Acc.  scope in {census, donor};
# split in {all, band, nonband, grass_side, grass_band, grass_nonband}
A = defaultdict(Acc)
row_len = defaultdict(lambda: defaultdict(float))           # scope -> tile row -> length
row_cross = defaultdict(lambda: defaultdict(float))         # scope -> tile row -> crossing length
gside_len = defaultdict(lambda: defaultdict(float))         # scope -> ground topo -> length
ann = defaultdict(lambda: dict(area=0.0, grass=0.0, topo=defaultdict(float), dips=[]))
gtile_foot = defaultdict(Counter)                           # scope -> (col,row) of foot-adjacent GRASS ground
gtile_far = defaultdict(Counter)                            # scope -> (col,row) of far-field grass (>8u)
n_blocks = n_comps = 0

for (bx, by) in X.list_blocks(disc=1):
    try:
        bm = X.read_block(bx, by, disc=1)
    except Exception:                                       # noqa: BLE001
        continue
    V, U, T = bm.verts, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    if not any(t in PLATEAU for t in topo):
        continue

    # ---- the census extraction, VERBATIM from rock_wall_rim.py ------------------------------
    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)
    crest49 = set()
    for e, ts in edge_tris.items():
        if len(ts) == 2:
            pair = {topo[ts[0]], topo[ts[1]]}
            if 49 in pair and pair & PLATEAU:
                crest49.add(ts[0] if topo[ts[0]] == 49 else ts[1])
    adj49 = defaultdict(set)
    for e, ts in edge_tris.items():
        r = [t for t in ts if topo[t] == 49]
        for i in range(len(r)):
            for j in range(i + 1, len(r)):
                adj49[r[i]].add(r[j])
                adj49[r[j]].add(r[i])
    comp_of = {}
    seen = set()
    for s in crest49:
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj49[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        for t in comp:
            comp_of[t] = s
    wall_tris = set(comp_of)
    if not wall_tris:
        continue
    comp_tris = defaultdict(list)
    for t in wall_tris:
        comp_tris[comp_of[t]].append(t)
    comp_band = {}
    for root, ts in comp_tris.items():
        ys = [V[i][1] for t in ts for i in tri_idx[t]]
        if max(ys) - min(ys) >= 6.0 and len(ts) >= 12:
            comp_band[root] = (min(ys), max(ys))

    foot_edges = []                                         # (edge, wall_tri, ground_tri)
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 1 or comp_of[w[0]] not in comp_band:
            continue
        o = [t for t in ts if t not in wall_tris]
        if any(topo[t] in PLATEAU for t in o):
            continue                                        # crest / next-tier plateau weld
        if o and all(topo[t] != 49 for t in o):
            foot_edges.append((e, w[0], o[0]))
    if not foot_edges:
        continue
    n_blocks += 1
    n_comps += len(comp_band)

    scopes = ["census"] + (["donor"] if (bx, by) == DONOR_BLK else [])

    weld_pts = []
    for e, wt, gt in foot_edges:
        L = math.hypot(e[1][0] - e[0][0], e[1][2] - e[0][2])
        if L < 1e-9:
            continue
        weld_pts.append(((e[0][0] + e[1][0]) / 2.0, (e[0][1] + e[1][1]) / 2.0,
                         (e[0][2] + e[1][2]) / 2.0))
        rows3 = [vrow(U[i][1]) for i in tri_idx[wt]]
        vmin, vmax = min(rows3), max(rows3)
        trow = tile_row([U[i][1] for i in tri_idx[wt]])
        ek = set(e)
        ev = [vrow(U[i][1]) for i in tri_idx[wt] if kk(V[i]) in ek]
        ev_max = max(ev) if ev else vmin
        band = trow in (10, 11)
        gtopo = topo[gt]
        grass = gtopo in GRASS_TOPO
        for sc in scopes:
            A[(sc, "all")].add(L, vmin, vmax, ev_max)
            A[(sc, "band" if band else "nonband")].add(L, vmin, vmax, ev_max)
            if grass:
                A[(sc, "grass_side")].add(L, vmin, vmax, ev_max)
                A[(sc, "grass_band" if band else "grass_nonband")].add(L, vmin, vmax, ev_max)
            row_len[sc][trow] += L
            if vmin < 11.0 - 1e-9 and vmax >= 11.0 - 1e-9:
                row_cross[sc][trow] += L
            gside_len[sc][gtopo] += L
            if grass:
                us = [U[i][0] for i in tri_idx[gt]]
                vs = [U[i][1] for i in tri_idx[gt]]
                gtile_foot[sc][(int(math.floor((min(us) - PU) / TILE_U + 0.5)),
                                tile_row(vs))] += 1

    # ---- secondary: the GROUND within 4u plan (and +-3u height) of the weld -----------------
    WP = np.array(weld_pts)
    far_seen = set()
    for t in range(ntri):
        if t in wall_tris or topo[t] == 49 or topo[t] in PLATEAU:
            continue
        c = np.mean([[V[i][0], V[i][1], V[i][2]] for i in tri_idx[t]], axis=0)
        dd = np.hypot(WP[:, 0] - c[0], WP[:, 2] - c[2])
        j = int(np.argmin(dd))
        a3, b3, c3 = (np.array(V[i], dtype=float) for i in tri_idx[t])
        if float(dd[j]) <= ANNULUS_D and abs(float(WP[j][1]) - c[1]) <= ANNULUS_DY:
            area = 0.5 * float(np.linalg.norm(np.cross(b3 - a3, c3 - a3)))
            nrm = np.cross(b3 - a3, c3 - a3)
            nl = float(np.linalg.norm(nrm))
            dip = math.degrees(math.acos(max(-1.0, min(1.0, abs(float(nrm[1])) / nl)))) \
                if nl > 1e-9 else 0.0
            for sc in scopes:
                ann[sc]["area"] += area
                ann[sc]["topo"][topo[t]] += area
                if topo[t] in GRASS_TOPO:
                    ann[sc]["grass"] += area
                    ann[sc]["dips"].append(round(dip, 1))
        elif float(dd[j]) > 8.0 and topo[t] in GRASS_TOPO and t not in far_seen:
            far_seen.add(t)
            us = [U[i][0] for i in tri_idx[t]]
            vs = [U[i][1] for i in tri_idx[t]]
            for sc in scopes:
                gtile_far[sc][(int(math.floor((min(us) - PU) / TILE_U + 0.5)),
                               tile_row(vs))] += 1


# ---- report ---------------------------------------------------------------------------------
def pc(a, q):
    return round(float(np.percentile(a, q)), 1) if a else None


print(f"population: {n_blocks} blocks with banded-component foot welds, {n_comps} components\n")
res = dict(population=dict(blocks=n_blocks, comps=n_comps),
           criteria=dict(cross="tri v-range crosses row 11.0 (registered)",
                         raw="tri vmax >= 11.0 (unscoped)",
                         overlap=f"tri v-range overlaps [{FRINGE_LO}, {FRINGE_HI}]",
                         edge_in_strip=f"weld-edge verts sample v-row >= {FRINGE_LO}"),
           scopes={})
for sc in ("census", "donor"):
    print(f"== {sc.upper()} {'(block ' + str(DONOR_BLK) + ')' if sc == 'donor' else '(stock disc-1 wall census)'} ==")
    scope_out = dict(splits={}, rows={}, ground_side={}, annulus={})
    for split in ("all", "band", "nonband", "grass_side", "grass_band", "grass_nonband"):
        acc = A.get((sc, split))
        if acc is None or not acc.n:
            continue
        o = acc.out()
        scope_out["splits"][split] = o
        print(f"   {split:14s}: {o['n_edges']:4d} edges {o['length']:7.1f}u | "
              f"fringe cross {o['fringe_cross']:.1%}  raw {o['fringe_raw']:.1%}  "
              f"overlap {o['fringe_overlap']:.1%}  edge-in-strip {o['edge_in_strip']:.1%} | "
              f"edge vmax p10/med/p90 {o['edge_vmax']['p10']}/{o['edge_vmax']['med']}"
              f"/{o['edge_vmax']['p90']}")
    rows = sorted(row_len[sc].items(), key=lambda kv: -kv[1])
    scope_out["rows"] = {str(r): dict(length=round(L, 1),
                                      cross=round(row_cross[sc][r] / L, 3))
                         for r, L in rows}
    print("   weld length by wall-side tile ROW (share of line | fringe-cross share):")
    tot = sum(row_len[sc].values()) or 1.0
    for r, L in rows[:8]:
        print(f"      row {r:3d}: {L:7.1f}u ({L / tot:5.1%})  cross {row_cross[sc][r] / L:.1%}")
    gtot = sum(gside_len[sc].values()) or 1.0
    gshare = sum(L for tp, L in gside_len[sc].items() if tp in GRASS_TOPO) / gtot
    scope_out["ground_side"] = dict(
        topo_len={str(tp): round(L, 1) for tp, L in
                  sorted(gside_len[sc].items(), key=lambda kv: -kv[1])},
        grass_share=round(gshare, 4))
    print(f"   ground side AT the weld (length-weighted): grass-class {gshare:.1%}; topo "
          f"{[(tp, round(L, 0)) for tp, L in sorted(gside_len[sc].items(), key=lambda kv: -kv[1])[:6]]}")
    an = ann[sc]
    if an["area"]:
        scope_out["annulus"] = dict(
            area=round(an["area"], 1),
            grass_share=round(an["grass"] / an["area"], 4),
            topo={str(tp): round(a / an["area"], 3) for tp, a in
                  sorted(an["topo"].items(), key=lambda kv: -kv[1])},
            grass_dip=dict(med=pc(an["dips"], 50), p90=pc(an["dips"], 90)))
        print(f"   ground within {ANNULUS_D}u of the weld: {an['area']:.0f}u2, grass-class "
              f"{an['grass'] / an['area']:.1%}; grass dip med {pc(an['dips'], 50)} deg "
              f"p90 {pc(an['dips'], 90)}")
    ftop = gtile_foot[sc].most_common(6)
    fartop = gtile_far[sc].most_common(6)
    scope_out["grass_tiles"] = dict(foot={f"{c},{r}": n for (c, r), n in ftop},
                                    far={f"{c},{r}": n for (c, r), n in fartop})
    print(f"   foot-adjacent GRASS tiles: {ftop}")
    print(f"   far-field (>8u) GRASS tiles: {fartop}\n")
    res["scopes"][sc] = scope_out

res["limits"] = [
    "foot edges exclude welds to lower-tier PLATEAU (census-classified as crest) and "
    "block-border once-edges: this is the interior welded foot line only",
    "single-block extraction (components and foot chains clip at 64u block borders), "
    "same as every census instrument in this arc",
    "fringe visibility is uv-interval arithmetic, not a render: no occlusion/backface "
    "check (J3: 96.7% of bottom-band edges are welded, so burial is rare)",
    f"annulus = plan <= {ANNULUS_D}u of a weld-edge midpoint AND |dy| <= {ANNULUS_DY}u "
    "(the dy guard excludes other terrace storeys sharing the plan footprint)",
]
OUT.write_text(json.dumps(res, indent=0))
print(f"artifacts -> {OUT}")
