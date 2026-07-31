"""THE STRIP CARRY, round 5 -- the registered prediction's test (STRIP-CARRY-PREDICTION.md).

Profile-carry (round 4) scored FAIL-on-form with the shape verdict improved: carried
silhouettes fixed the massing, but course-depth sampling flattened the ledge relief the
fringe tiles advertise, and the un-clipped apron stretched the base grass. This round
carries the WHOLE MESH -- verts + uvs + tangents, geometry and texture inseparable:

  * THREE STRIPS of real wall mesh (topo-49), cut at column boundaries from the donor
    inventory's top composition (probe_strip_donors.py): blk [22,14] / [17,12] / [14,16],
    closing 360 deg at R~22.5u with ~+2 deg of kink per seam (stock per-column turn median:
    24.2 deg). Each strip: ONE rigid pose (yaw about Y + translation), k = 1.0, no scaling.
  * SEAMS: the incoming strip's cut loop SNAPS onto the outgoing loop (<= 1.5u, gated);
    both sides' boundary tris are refined at the union of loop y-breakpoints through ONE
    canonical interpolation, so the weld is exact (no T-junctions, watertight clean).
    Juxtaposed atlas columns are gated against the anatomy artifact's h_pairs table --
    the decoded tile language serving as a seam-legality ORACLE, not a generator.
  * SEAT: the burial amendment unchanged -- crest-anchored at one TOP_Y in the stock shelf
    band, every column's surplus buried below the bench floor. The wall PIERCES the flat
    lowland grass (the round-4 read that earned "shape and coherence is better").
  * GROUND: **no apron.** The bench grass is cut along a rim polygon inset 1.5u INSIDE the
    wall's ground-level face line -- the cut edge hides behind the face sheet. The cut is
    an exact partition (general-line slices; crossings computed once per line so adjacent
    fragments weld bit-exact); fragments keep their cell's own L3 window via ground_uv, so
    NO grass stretches (round 4's finding 4 is deleted, not repaired).
  * TOP: T1's proven lattice fill (cell clip + centroid fan + T-conformance), L3-seeded
    from the bench's own grass, welded to the carried crest polyline by refining the wall's
    crest-edge tris at the fill's boundary verts (same canonical-interpolation trick).

Gates before any write: seam displacement, h_pairs seam legality, winding, watertight
(0 new once-edges save the DECLARED hole rim + sub-ground seam residue, each audited),
massing foot-line numbers, census MISS=0, bench reach. --apply deploys to the Disc9 bench
(backing the cells up under the MAIN repo's backups/) only when green.

The bench likely needs a wider island (the ring reads ~R22.5 + foot flare): the script
computes the needed radius and REFUSES until the bench matches. Re-mint with the same
center so `backups/terrace-t1-prewall.20260730-203328` stays the revert point.

Run from the repo root:  py -X utf8 studies/path-d-new-world/terrace_wall_strip.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                # noqa: E402
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402
from ff9mapkit.world import interior as IN                  # noqa: E402
from ff9mapkit.world import mesh as M                       # noqa: E402

GAME = Path(config.find_game_path(None))
MOD = "FF9CustomMap-world"
DISC = 9
CELLS = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]
CENTER = (416.0, -512.0)
BLOCK, CELL = 64.0, 4.0
TILE_U, TILE_V = 0.0625, 0.03125
SEED = 7005

LOWLAND = 3.2
SHELF_BAND = (15.7, 18.3)
GRASS_TOPO = {0, 1, 2, 3, 42}
ROCK = 49
SHELF = 13
PLATEAU = {10, 11, 12}
STEP_MAX = 9.0                                              # the probe's same-wall chain gate
RIM_INSET = 1.5                                             # hole rim inside the face line (u)
SEAM_GAP = 1.7                                              # the mortar column's base width (u)
KINK_MAX = 25.0

# The AMENDED composition (the tier-gated inventory's top line): four LEVEL chains.
# Window = [a, b] INCLUSIVE column indices on the probe's FULL-chain ordering; n_chain
# selects WHICH chain in the block (lengths are unique per donor block). Cut shifts of
# <= 2 columns are the registration's declared freedom, used ONLY if h_pairs gates red.
# ((22,14) starts at col 1, not the probe's 0: col 0 is the component's TAPERED natural
# end -- 5-12u tall, below the burial seat's feasibility bar -- so the cut moves one
# column in (the registered <=2-column shift) and becomes a true full-height wall|wall cut)
DONORS = [((17, 12), 5, 14, 17), ((22, 14), 1, 7, 10),
          ((13, 16), 0, 8, 19), ((18, 9), 2, 9, 12)]

OUTD = HERE / "out" / "terrace_strip"
MASSING = ROOT / "studies" / "overworld-topography" / "out" / "rock_wall_massing.json"
ANATOMY = ROOT / "studies" / "overworld-topography" / "out" / "rock_tile_instances.json"
DECODE = ROOT / "studies" / "overworld-topography" / "out" / "rock_tiles.json"

kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))   # noqa: E731


# ---------------------------------------------------------------- geometry helpers (T1 lift)
def pinp(px, pz, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i][0], poly[i][1]
        x2, z2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        if (z1 > pz) != (z2 > pz) and px < (x2 - x1) * (pz - z1) / (z2 - z1) + x1:
            inside = not inside
    return inside


def poly_area2(pg):
    s = 0.0
    for i in range(len(pg)):
        p, q = pg[i], pg[(i + 1) % len(pg)]
        s += p[0] * q[-1] - q[0] * p[-1]
    return abs(s) / 2.0


def centroid_fan(pg):
    pg = list(pg)
    if len(pg) == 3:
        return [tuple(pg)]
    cx = sum(p[0] for p in pg) / len(pg)
    cz = sum(p[-1] for p in pg) / len(pg)
    c = (cx, cz) if len(pg[0]) == 2 else (cx, pg[0][1], cz)
    return [(c, pg[i], pg[(i + 1) % len(pg)]) for i in range(len(pg))]


def clip_cell(poly, cx0, cz0):
    out = [(p[0], p[1]) for p in poly]
    for (ax, side) in ((0, cx0), (0, cx0 + CELL), (1, cz0), (1, cz0 + CELL)):
        if not out:
            return []
        keepge = side in (cx0, cz0)
        nxt = []
        for i in range(len(out)):
            a, b = out[i], out[(i + 1) % len(out)]
            ain = (a[ax] >= side) if keepge else (a[ax] <= side)
            bin_ = (b[ax] >= side) if keepge else (b[ax] <= side)
            if ain:
                nxt.append(a)
            if ain != bin_:
                t = (side - a[ax]) / (b[ax] - a[ax])
                nxt.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        out = nxt
    return out


def signed_turn(a, b, c):
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    L1, L2 = math.hypot(*v1), math.hypot(*v2)
    if L1 < 1e-9 or L2 < 1e-9:
        return 0.0
    return math.degrees(math.atan2(v1[0] * v2[1] - v1[1] * v2[0],
                                   v1[0] * v2[0] + v1[1] * v2[1]))


# ---------------------------------------------------------------- the bench
def load_bench():
    root = GAME / MOD / "FF9_Data" / "WorldMap" / f"Disc{DISC}" / "0_1"
    tris, bms = [], {}
    for (bx, by) in CELLS:
        p = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not p.is_file():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=DISC, x=bx, y=by, part="terrain")
        bms[(bx, by)] = (p, bm)
        pos = bm.chan_arrays[X.CH_POS]
        nrm = bm.chan_arrays[X.CH_NRM]
        uv = bm.chan_arrays[X.CH_UV]
        tan = bm.chan_arrays[X.CH_TAN]
        ox, oz = BLOCK * bx, -BLOCK * by
        for t in bm.tris:
            w = [(pos[i][0] + ox, pos[i][1], pos[i][2] + oz) for i in t]
            topo = X.decode_id(int(round(tan[t[0]][0])))["topograph"]
            tris.append(dict(blk=(bx, by), w=w, n=[list(nrm[i]) for i in t],
                             uv=[list(uv[i]) for i in t], tan=[list(tan[i]) for i in t],
                             topo=topo,
                             cen=tuple(np.mean([w[k][j] for k in range(3)]) for j in range(3))))
    return tris, bms


# ---------------------------------------------------------------- the massing instrument
# Component + instance + column extraction VERBATIM from rock_wall_massing.py (the three
# tile studies and this builder share one instrument); returns enough to cut strip MESH.
def extract_wall(bx, by):
    bm = X.read_block(bx, by, disc=1, part="terrain")
    V = bm.chan_arrays[X.CH_POS]
    U = bm.chan_arrays[X.CH_UV]
    N = bm.chan_arrays[X.CH_NRM]
    T = bm.chan_arrays[X.CH_TAN]
    ntri = len(bm.flat_index) // 3
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
    ox, oz = BLOCK * bx, -BLOCK * by

    edge_tris = defaultdict(list)
    for t, idx in enumerate(tri_idx):
        ps = [kk(V[i]) for i in idx]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_tris[tuple(sorted((ps[a], ps[b])))].append(t)

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

    parent = {t: t for t in wall_tris}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    def bbox_of(ts):
        us = [U[i][0] for t in ts for i in tri_idx[t]]
        vs = [U[i][1] for t in ts for i in tri_idx[t]]
        return min(us), min(vs), max(us), max(vs)

    members = {t: {t} for t in wall_tris}
    for e, ts in edge_tris.items():
        w = [t for t in ts if t in wall_tris]
        if len(w) != 2:
            continue
        t1, t2 = w
        uv1 = {kk(V[i]): tuple(np.round(U[i], 5)) for i in tri_idx[t1]}
        uv2 = {kk(V[i]): tuple(np.round(U[i], 5)) for i in tri_idx[t2]}
        if not all(uv1.get(p) == uv2.get(p) for p in e):
            continue
        r1, r2 = find(t1), find(t2)
        if r1 == r2:
            continue
        u0, v0, u1, v1 = bbox_of(members[r1] | members[r2])
        if (u1 - u0) > TILE_U + 1e-4 or (v1 - v0) > TILE_V + 1e-4:
            continue
        parent[r2] = r1
        members[r1] |= members[r2]
        del members[r2]

    inst_of_tri = {}
    inst_data = {}
    for r, ts in members.items():
        pts = np.array([[V[i][0], V[i][1], V[i][2]] for t in ts for i in tri_idx[t]])
        n_sum = np.zeros(3)
        for t in ts:
            a, b, c = (np.array(V[i]) for i in tri_idx[t])
            n_sum += np.cross(b - a, c - a)
        us = [U[i][0] for t in ts for i in tri_idx[t]]
        vs = [U[i][1] for t in ts for i in tri_idx[t]]
        inst_data[r] = dict(cen=pts.mean(axis=0), n=n_sum, comp=comp_of[next(iter(ts))],
                            ymin=float(pts[:, 1].min()), ymax=float(pts[:, 1].max()),
                            tris=set(ts), u0=min(us), v0=min(vs))
        for t in ts:
            inst_of_tri[t] = r

    v_adj = defaultdict(set)
    seen_p = set()
    for e, ts in edge_tris.items():
        w = sorted({inst_of_tri[t] for t in ts if t in inst_of_tri})
        if len(w) != 2 or tuple(w) in seen_p:
            continue
        seen_p.add(tuple(w))
        A, B = inst_data[w[0]], inst_data[w[1]]
        d = B["cen"] - A["cen"]
        if abs(d[1]) > math.hypot(d[0], d[2]):
            lo, hi = (w[0], w[1]) if A["cen"][1] <= B["cen"][1] else (w[1], w[0])
            v_adj[lo].add(hi)

    # columns: the massing F walk, keeping the member instance list per column
    roots_here = [r for r in inst_data if inst_data[r]["ymax"] - inst_data[r]["ymin"] > 1.0]
    has_below = {hi for lo in v_adj for hi in v_adj[lo]}
    columns = []
    for r in roots_here:
        if r in has_below:
            continue
        chain = [r]
        while chain[-1] in v_adj and v_adj[chain[-1]]:
            chain.append(sorted(v_adj[chain[-1]], key=lambda q: inst_data[q]["cen"][1])[0])
            if len(chain) > 12:
                break
        if len(chain) < 3:
            continue
        base = inst_data[chain[0]]
        nm = base["n"].copy()
        nm[1] = 0.0
        L = np.linalg.norm(nm)
        if L < 1e-6:
            continue
        nm /= L
        columns.append(dict(
            insts=chain, comp=base["comp"],
            cen=(float(base["cen"][0] + ox), float(base["cen"][1]),
                 float(base["cen"][2] + oz)),
            nrm=(float(nm[0]), float(nm[2])),
            ymax=max(inst_data[q]["ymax"] for q in chain),
            ymin=min(inst_data[q]["ymin"] for q in chain)))
    return dict(bm=bm, V=V, U=U, N=N, T=T, tri_idx=tri_idx, topo=topo, ox=ox, oz=oz,
                comp_of=comp_of, wall_tris=wall_tris, inst_data=inst_data,
                inst_of_tri=inst_of_tri, columns=columns, edge_tris=edge_tris)


def chain_columns(columns):
    """The probe's nearest-neighbour chaining, verbatim semantics: greedy both ends,
    step <= STEP_MAX, then the nrm-on-right traversal flip. Returns the list of chains,
    each a list of column indices, longest first."""
    pts = [(c["cen"][0], c["cen"][2]) for c in columns]
    n = len(columns)
    used = [False] * n
    chains = []
    for s in range(n):
        if used[s]:
            continue
        chain = [s]
        used[s] = True
        for _dirn in (1, -1):
            while True:
                tail = chain[-1] if _dirn == 1 else chain[0]
                cand = [(math.dist(pts[tail], pts[j]), j) for j in range(n) if not used[j]]
                cand = [c for c in cand if c[0] <= STEP_MAX]
                if not cand:
                    break
                _, j = min(cand)
                used[j] = True
                (chain.append if _dirn == 1 else lambda x: chain.insert(0, x))(j)
        if len(chain) < 6:
            continue
        P = [pts[i] for i in chain]
        sides = []
        for ci in range(len(chain) - 1):
            t = (P[ci + 1][0] - P[ci][0], P[ci + 1][1] - P[ci][1])
            nr = columns[chain[ci]]["nrm"]
            sides.append(t[0] * nr[1] - t[1] * nr[0])
        if sides and float(np.median(sides)) > 0:
            chain.reverse()
        chains.append(chain)
    chains.sort(key=len, reverse=True)
    return chains


# ---------------------------------------------------------------- strip cutting
def cut_strip(blk, a, b, n_chain):
    """Carve window columns [a..b] (probe chain ordering) of the block's longest chain out
    of the donor mesh, WHOLE: every topo-49 tri whose instance belongs to (or attaches by
    arclength to) the window. Returns the strip dict (verbatim vertex records + loops)."""
    W = extract_wall(*blk)
    chains = chain_columns(W["columns"])
    match = [c for c in chains if len(c) == n_chain]
    assert len(match) == 1, (f"blk {blk}: {len(match)} chains of length {n_chain} "
                             f"(have {[len(c) for c in chains]}) -- ambiguous window")
    chain = match[0]
    assert b < len(chain), f"blk {blk}: window [{a},{b}] beyond chain length {len(chain)}"
    win = chain[a:b + 1]
    cols = [W["columns"][i] for i in win]
    comp = Counter(c["comp"] for c in cols).most_common(1)[0][0]
    assert all(c["comp"] == comp for c in cols), f"blk {blk}: window spans two components"

    # FULL chain polyline (all columns) -- every instance of the component is assigned to
    # its nearest chain COLUMN by arclength, and the strip is columns [a..b] complete. A
    # window-only polyline rakes distant instances in on curved walls and leaves a jagged
    # multi-column cut; column assignment cuts at the mesh's own vertical boundary.
    all_cols = [W["columns"][i] for i in chain]
    PF = [(c["cen"][0], c["cen"][2]) for c in all_cols]
    sF = [0.0]
    for i in range(1, len(PF)):
        sF.append(sF[-1] + math.dist(PF[i - 1], PF[i]))

    def proj_sF(px, pz):
        best = None
        for i in range(len(PF) - 1):
            ax, az = PF[i]
            bx2, bz2 = PF[i + 1]
            dx, dz = bx2 - ax, bz2 - az
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0,
                                                    ((px - ax) * dx + (pz - az) * dz) / L2))
            qx, qz = ax + t * dx, az + t * dz
            d = math.hypot(px - qx, pz - qz)
            s = sF[i] + t * math.hypot(dx, dz)
            if best is None or d < best[0]:
                best = (d, s)
        return best

    P = [(c["cen"][0], c["cen"][2]) for c in cols]
    s_of = [sF[i] - sF[a] for i in range(a, b + 1)]
    st_med = float(np.median(np.diff(s_of))) if len(s_of) > 1 else 4.4

    col_of_inst = {}
    s_of_inst = {}
    for c_i, c in enumerate(all_cols):
        for r in c["insts"]:
            col_of_inst[r] = c_i
            s_of_inst[r] = sF[c_i]
    for r, d in W["inst_data"].items():
        if r in col_of_inst or d["comp"] != comp:
            continue
        px, pz = float(d["cen"][0] + W["ox"]), float(d["cen"][2] + W["oz"])
        dd, s = proj_sF(px, pz)
        if dd <= STEP_MAX:
            col_of_inst[r] = int(np.argmin([abs(s - sF[q]) for q in range(len(sF))]))
            s_of_inst[r] = s

    # membership bounded by the window's OWN arclength span -- nearest-column alone lets
    # an unprofiled tail past an end column ride along and drag the cut a station+ out
    member_insts = {r for r, c_i in col_of_inst.items()
                    if a <= c_i <= b
                    and sF[a] - 0.6 * st_med <= s_of_inst[r] <= sF[b] + 0.6 * st_med}

    tris = set()
    for r in member_insts:
        tris.update(W["inst_data"][r]["tris"])
    # EMBEDDED POCKETS: the donor face sheet interleaves non-49 tris (grass on ledges --
    # the very "ledge vegetation" the finer-carrier finding named). A topo-only carry
    # leaves REAL HOLES there. Grow the strip over any tri sharing >= 2 edges with it,
    # capped below the crest so the plateau-top fringe stays out.
    crest_cap = max(W["V"][i][1] for t in tris for i in W["tri_idx"][t]) - 1.0
    grown = True
    n_pocket = 0
    while grown:
        grown = False
        share = Counter()
        for e, ts in W["edge_tris"].items():
            ins = [t for t in ts if t in tris]
            if not ins:
                continue
            for t in ts:
                if t not in tris:
                    share[t] += 1
        for t, n_sh in share.items():
            if n_sh < 2 or max(W["V"][i][1] for i in W["tri_idx"][t]) >= crest_cap:
                continue
            idx = W["tri_idx"][t]
            cx = float(np.mean([W["V"][i][0] for i in idx])) + W["ox"]
            cz = float(np.mean([W["V"][i][2] for i in idx])) + W["oz"]
            _, s = proj_sF(cx, cz)
            if not (sF[a] - st_med <= s <= sF[b] + st_med):
                continue                                    # no creep past the cut
            tris.add(t)
            n_pocket += 1
            grown = True

    # cut loops: edges shared with SAME-component wall tris outside the strip
    lo_s, lo_e = [], []
    for e, ts in W["edge_tris"].items():
        ins = [t for t in ts if t in tris]
        outs = [t for t in ts if t in W["wall_tris"] and t not in tris]
        if not (ins and outs):
            continue
        mx = (e[0][0] + e[1][0]) / 2 + W["ox"]
        mz = (e[0][2] + e[1][2]) / 2 + W["oz"]
        _, s = proj_sF(mx, mz)
        (lo_s if s < (sF[a] + sF[b]) / 2 else lo_e).append(e)
    # NATURAL END: a window starting/ending at the component's own end (a block-boundary
    # cut or a true terminus) has no wall|wall edges there -- the cross-section is the
    # strip's OWN boundary edges near that end, VERTICAL ones (crest/foot chains run along
    # the wall and are horizontal-ish; the end section descends crest -> foot).
    e_cnt = Counter()
    for t in tris:
        idx = W["tri_idx"][t]
        ps = [kk(W["V"][i]) for i in idx]
        for a2, b2 in ((0, 1), (1, 2), (2, 0)):
            e_cnt[tuple(sorted((ps[a2], ps[b2])))] += 1
    for e, n_e in e_cnt.items():
        if n_e != 1:
            continue
        dy = abs(e[0][1] - e[1][1])
        dxz = math.hypot(e[0][0] - e[1][0], e[0][2] - e[1][2])
        if dy < dxz:
            continue                                        # horizontal-ish: crest/foot
        mx = (e[0][0] + e[1][0]) / 2 + W["ox"]
        mz = (e[0][2] + e[1][2]) / 2 + W["oz"]
        _, s = proj_sF(mx, mz)
        s0 = s - sF[a]
        if s0 < st_med * 1.1:
            lo_s.append(e)
        elif s0 > s_of[-1] - st_med * 1.1:
            lo_e.append(e)
    assert lo_s and lo_e, f"blk {blk}: an end cross-section is still empty"

    bnd_adj = defaultdict(list)                             # the strip's OWN boundary graph
    for e, n_e in e_cnt.items():
        if n_e == 1:
            bnd_adj[e[0]].append(e[1])
            bnd_adj[e[1]].append(e[0])
    crest_top = max(W["V"][i][1] for t in tris for i in W["tri_idx"][t])

    def loop_pts(edges):
        """The cut cross-section as its ACTUAL boundary path (chained edges, walked from
        the bottom end) -- NOT a y-sort: a ledge in the cut column breaks y-monotonicity,
        and the mortar bridge must traverse the strip's real boundary edges to pair them.
        If the path tops out below the crest (a SHORT neighbour column beyond the cut
        leaves the upper side face exposed), EXTEND it up the strip's own boundary --
        otherwise the mortar leaves an open window between its top and the crest."""
        eset = {tuple(sorted(e)) for e in edges}
        adj_l = defaultdict(list)
        for a2, b2 in eset:
            adj_l[a2].append(b2)
            adj_l[b2].append(a2)
        ends = [p for p, l in adj_l.items() if len(l) == 1]
        if not ends:                                        # degenerate: fall back to sort
            path = sorted({p for e in eset for p in e}, key=lambda q: q[1])
        else:
            start = min(ends, key=lambda p: p[1])
            path = [start]
            prev = None
            while True:
                nxts = [p for p in adj_l[path[-1]] if p != prev]
                if not nxts:
                    break
                prev = path[-1]
                path.append(nxts[0])
                if len(path) > 400:
                    break
            if path[-1][1] < path[0][1]:                    # keep bottom -> top
                path.reverse()
        for _ in range(6):
            if path[-1][1] >= crest_top - 2.5:
                break
            cur = path[-1]
            cands = [q for q in bnd_adj[cur]
                     if q not in path and q[1] > cur[1] + 0.2
                     and abs(q[1] - cur[1]) >= 0.4 * math.hypot(q[0] - cur[0],
                                                                q[2] - cur[2])]
            if not cands:
                break
            path.append(max(cands, key=lambda q: q[1]))
        return [(p[0] + W["ox"], p[1], p[2] + W["oz"]) for p in path]

    # verbatim vertex records for the strip
    recs = []                                               # per tri: [(w, uv, nrm, tan)]
    for t in sorted(tris):
        idx = W["tri_idx"][t]
        rec = []
        for i in idx:
            w = (W["V"][i][0] + W["ox"], W["V"][i][1], W["V"][i][2] + W["oz"])
            rec.append((w, tuple(W["U"][i]), tuple(W["N"][i]), tuple(W["T"][i])))
        recs.append(rec)

    if n_pocket:
        print(f"  blk {blk}: {n_pocket} embedded pocket tris carried (ledge vegetation)")
    ymaxs = [c["ymax"] for c in cols]
    depths = [c["ymax"] - c["ymin"] for c in cols]
    turns = [signed_turn(P[i - 1], P[i], P[i + 1]) for i in range(1, len(P) - 1)]
    # seam tiles: the two cut columns' instances (atlas col,row per instance, phase-derived)
    pu, pv = json.loads(DECODE.read_text())["phase"]

    def col_tiles(c):
        out = []
        for r in c["insts"]:
            d = W["inst_data"][r]
            out.append((round((d["u0"] - pu) / TILE_U), round((d["v0"] - pv) / TILE_V),
                        d["ymin"], d["ymax"]))
        return out

    return dict(blk=blk, n=len(cols), P=P, s_of=s_of, st=st_med, turns=turns,
                bend=sum(turns), length=s_of[-1], recs=recs,
                loop_s=loop_pts(lo_s), loop_e=loop_pts(lo_e),
                crest_y=float(np.median(ymaxs)), depth_min=float(min(depths)),
                tiles_s=col_tiles(cols[0]), tiles_e=col_tiles(cols[-1]))


# ---------------------------------------------------------------- pose + closure
def solve_ring(strips):
    """Chain the three strips loop-to-loop; distribute the bearing residual as seam kinks
    (k1, k2 searched, k3 = residual) minimising the position-closure gap. Returns per-strip
    (yaw, tx, tz) with the ring centred on CENTER, plus the per-seam kinks and the gap."""
    def bearing(p, q):
        return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))

    # canonical per-strip geometry: the BASE polyline with half-station COLINEAR anchor
    # extensions at both ends. (Loop CENTROIDS sit at mid-height of a battered face --
    # displaced outward from the base line -- and added ~13 deg of spurious turn per
    # joint; colinear anchors add zero turn, and the loops meet at the shared anchor by
    # the seam snap.)
    geos = []
    for s in strips:
        P = s["P"]
        half = s["st"] / 2.0

        def ext(p_end, p_prev):
            d = (p_end[0] - p_prev[0], p_end[1] - p_prev[1])
            L = math.hypot(*d) or 1.0
            return (p_end[0] + d[0] / L * half, p_end[1] + d[1] / L * half)
        # COLINEAR half-station extensions to the actual cut planes (bearing-neutral):
        # column centroids sit half a station short of the cut on each side, and without
        # the ext the mortar seam is a station wider than SEAM_GAP
        pl = [ext(P[0], P[1])] + P + [ext(P[-1], P[-2])]
        b_in = bearing(pl[0], pl[1])
        b_out = bearing(pl[-2], pl[-1])
        bend_eff = sum(signed_turn(pl[i - 1], pl[i], pl[i + 1])
                       for i in range(1, len(pl) - 1))
        # TRANSLATION chains on the cut-loop CENTROIDS (the cross-sections weld face to
        # face, as stock corners share a column); BEARINGS chain on the base line + kinks.
        # Base-point chaining splays the crests apart: each face leans ~10u inward by its
        # own batter, so kink rotation + batter spread separated matched-y verts by 6-16u.
        lc_in = (float(np.mean([p[0] for p in s["loop_s"]])),
                 float(np.mean([p[2] for p in s["loop_s"]])))
        lc_out = (float(np.mean([p[0] for p in s["loop_e"]])),
                  float(np.mean([p[2] for p in s["loop_e"]])))
        geos.append(dict(pl=pl, b_in=b_in, b_out=b_out, bend_eff=bend_eff,
                         lc_in=lc_in, lc_out=lc_out))

    def place(ks, geos_o):
        """Returns (poses, gap): poses = per strip (yaw_deg, pivot, target) mapping donor
        xz -> ring xz. Chaining anchors on the BASE polyline endpoints + the mortar gap;
        the cross-sections splay with lean/kink and the mortar bridge spans whatever
        results (bounded by the width gate). Loop-centroid chaining skews when a cut
        loop is partial-height and broke position closure."""
        poses = []
        cur_pt = (0.0, 0.0)
        cur_bear = 0.0
        first_in = None
        for i, g in enumerate(geos_o):
            yaw = cur_bear - g["b_in"]
            r = math.radians(yaw)
            cs, sn = math.cos(r), math.sin(r)
            p0 = g["pl"][0]

            def xf(p, cs=cs, sn=sn, p0=p0, cur_pt=cur_pt):
                dx, dz = p[0] - p0[0], p[1] - p0[1]
                return (cur_pt[0] + dx * cs - dz * sn, cur_pt[1] + dx * sn + dz * cs)
            poses.append((yaw, p0, cur_pt))
            if first_in is None:
                first_in = cur_pt
            cur_pt = xf(g["pl"][-1])
            exit_bear = g["b_out"] + yaw
            cur_bear = exit_bear + ks[i]
            # the mortar column's width: step across the seam along the kink bisector
            mid = math.radians(exit_bear + ks[i] / 2)
            cur_pt = (cur_pt[0] + SEAM_GAP * math.cos(mid),
                      cur_pt[1] + SEAM_GAP * math.sin(mid))
        gap = math.hypot(cur_pt[0] - first_in[0], cur_pt[1] - first_in[1])
        return poses, gap

    # total ring turn = per-strip loop-to-loop bend (the unwrapped b_out - b_in) + kinks.
    # THE ORDER IS OURS: bend is lumpy along real strips, so position closure depends on
    # the cyclic order -- search all (S-1)! orders, then kinks coarse-to-fine per order.
    import itertools as _it
    S = len(strips)
    resid = 360.0 - sum(g["bend_eff"] for g in geos)
    best_all = None
    for order in [(0,) + perm for perm in _it.permutations(range(1, S))]:
        geos_o = [geos[i] for i in order]
        best = None
        for step in (5.0, 1.0, 0.1):
            if best is None:
                spans = [np.arange(-KINK_MAX, KINK_MAX + 0.1, 5.0)] * (S - 1)
            else:
                spans = [np.arange(k0 - step * 4.5, k0 + step * 4.55, step)
                         for k0 in best[1][:-1]]
            for combo in _it.product(*spans):
                klast = resid - sum(combo)
                ks = tuple(float(k) for k in combo) + (round(float(klast), 2),)
                if any(abs(k) > KINK_MAX for k in ks):
                    continue
                _, gap = place(ks, geos_o)
                # uniform kinks are the lawful look (and bound the corner warp) -- a soft
                # penalty keeps the solve from slamming kinks to the budget edge
                score = gap + 0.02 * sum(abs(k - resid / S) for k in ks)
                if best is None or score < best[0]:
                    best = (score, ks, gap)
            if best is None:
                break
        if best is not None and (best_all is None or best[0] < best_all[0]):
            best_all = (best[0], best[1], best[2], order)
    assert best_all is not None, "no order + kink assignment within the budget"
    _, kinks_t, gap, order = best_all
    geos_o = [geos[i] for i in order]
    poses, _ = place(kinks_t, geos_o)

    # centre the ring: transform all column points, shift centroid to CENTER
    ring_pts = []
    for g, (yaw, p0, t0) in zip(geos_o, poses):
        r = math.radians(yaw)
        cs, sn = math.cos(r), math.sin(r)
        for p in g["pl"]:
            dx, dz = p[0] - p0[0], p[1] - p0[1]
            ring_pts.append((t0[0] + dx * cs - dz * sn, t0[1] + dx * sn + dz * cs))
    cx = float(np.mean([p[0] for p in ring_pts]))
    cz = float(np.mean([p[1] for p in ring_pts]))
    shift = (CENTER[0] - cx, CENTER[1] - cz)
    return order, poses, shift, kinks_t, gap


def xf_point(p, yaw, p0, t0, shift, dy):
    """Donor world (x,y,z) -> bench world, for a strip posed by solve_ring."""
    r = math.radians(yaw)
    cs, sn = math.cos(r), math.sin(r)
    dx, dz = p[0] - p0[0], p[2] - p0[1]
    return (t0[0] + dx * cs - dz * sn + shift[0], p[1] + dy,
            t0[1] + dx * sn + dz * cs + shift[1])


def xf_nrm(n3, yaw):
    r = math.radians(yaw)
    cs, sn = math.cos(r), math.sin(r)
    return (n3[0] * cs - n3[2] * sn, n3[1], n3[0] * sn + n3[2] * cs)


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    OUTD.mkdir(parents=True, exist_ok=True)

    tris, bms = load_bench()
    assert tris, "bench island not deployed at Disc9 (run the world-island mint first)"
    grass_r = max(math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
                  for t in tris if t["topo"] in GRASS_TOPO)
    print(f"bench: {len(tris)} tris across {len(bms)} cells; grass reach ~{grass_r:.1f}u")

    strips = [cut_strip(blk, a, b, n) for (blk, a, b, n) in DONORS]
    for s in strips:
        print(f"strip blk {s['blk']}: {s['n']} cols, {len(s['recs'])} tris, "
              f"len {s['length']:.1f}u bend {s['bend']:+.1f} deg, depth_min "
              f"{s['depth_min']:.1f}u, loops {len(s['loop_s'])}/{len(s['loop_e'])} verts")

    # ---- the burial seat (the round-4 amendment, unchanged) --------------------------------
    drop = min(min(s["depth_min"] for s in strips) - 0.3, SHELF_BAND[1] - LOWLAND)
    assert drop >= SHELF_BAND[0] - LOWLAND, \
        f"a window column is too short for the shelf band (drop {drop:.1f})"
    top_y = LOWLAND + drop
    print(f"seat: TOP_Y {top_y:.2f} (drop {drop:.2f}), k=1.0 rigid, surplus buried")

    # ---- pose + closure (the cyclic ORDER is part of the solve) ----------------------------
    order, poses, shift, kinks, gap = solve_ring(strips)
    strips = [strips[i] for i in order]
    print(f"closure: order {[strips[i]['blk'] for i in range(len(strips))]}, kinks "
          f"{tuple(round(k, 1) for k in kinks)} deg, position gap {gap:.2f}u "
          f"(absorbed by the final mortar column's width)")

    # ---- h_pairs seam legality (the decoded language as an ORACLE), on the CHOSEN order ----
    hp = json.loads(ANATOMY.read_text())["h_pairs"]
    legal = {tuple(sorted((tuple(e["a"]), tuple(e["b"])))) for e in hp}
    seam_report = []
    S = len(strips)
    for i in range(S):
        te = strips[i]["tiles_e"]
        ts_ = strips[(i + 1) % S]["tiles_s"]
        # pair instances across the seam by y-overlap (donor y is course-comparable only
        # after crest anchoring -- compare in crest-anchored depth)
        ce = strips[i]["crest_y"]
        cs2 = strips[(i + 1) % S]["crest_y"]
        n_ok = n_bad = 0
        bad = []
        for (c1, r1, y0a, y1a) in te:
            da0, da1 = ce - y1a, ce - y0a                   # depth range below crest
            for (c2, r2, y0b, y1b) in ts_:
                db0, db1 = cs2 - y1b, cs2 - y0b
                ov = min(da1, db1) - max(da0, db0)
                if ov < 0.5 * min(da1 - da0, db1 - db0, 4.6):
                    continue
                if tuple(sorted(((c1, r1), (c2, r2)))) in legal:
                    n_ok += 1
                else:
                    n_bad += 1
                    bad.append(((c1, r1), (c2, r2)))
        seam_report.append((n_ok, n_bad, bad[:3]))
        print(f"seam {i}: h_pairs {n_ok} lawful / {n_bad} unlawful"
              + (f" (e.g. {bad[:2]})" if bad else ""))

    posed = []                                              # per strip: list of tri records
    for s, (yaw, p0, t0) in zip(strips, poses):
        dy = top_y - s["crest_y"]
        out = []
        for rec in s["recs"]:
            out.append([(xf_point(w, yaw, p0, t0, shift, dy), uv,
                         xf_nrm(n3, yaw), t4) for (w, uv, n3, t4) in rec])
        posed.append(out)
        s["_pose"] = (yaw, p0, t0, dy)

    # ---- THE MORTAR BRIDGES: butt-joint seams, zero deformation of carried mesh ------------
    # The snap/taper/refine weld model assumed cross-sections are y-graphs; a ledge in a
    # cut column breaks that, and a battered kinked seam separates matched-y verts by the
    # corner warp anyway. Stock's own answer is the CORNER COLUMN: one column whose quads
    # absorb the turn. We mint it explicitly -- a one-column bridge zipped (the SPUR walk)
    # between the two cut paths, traversing the strips' REAL boundary edges so both loops'
    # once-edges are consumed exactly. Carried geometry moves ZERO.
    def posed_loop(s, which):
        yaw, p0, t0, dy = s["_pose"]
        return [xf_point(p, yaw, p0, t0, shift, dy) for p in
                (s["loop_s"] if which == "s" else s["loop_e"])]

    def K2(p):
        """2-decimal key: loop verts pass through donor-precision kk before posing, rec
        verts do not, so 3-decimal keys occasionally disagree; verts are >=1u apart."""
        return (round(p[0], 2), round(p[1], 2), round(p[2], 2))

    def loop_attrs(strip_idx, loop):
        """K2(posed vert) -> (exact rec vert, uv, n, tan) from the strip's carried recs.
        The EXACT position matters: loop verts pass through donor-precision kk, and the
        ~0.001u disagreement splits 3-decimal keys downstream (crest chaining)."""
        keys = {K2(p) for p in loop}
        m = {}
        for rec in posed[strip_idx]:
            for (w, uv, n3, t4) in rec:
                k2 = K2(w)
                if k2 in keys and k2 not in m:
                    m[k2] = (w, uv, n3, t4)
        return m

    bridges = []                                            # rec-style tris (mortar)
    bridge_stats = []
    seam_pts = []                                           # all loop verts (mortar zones)
    pu_ph, pv_ph = json.loads(DECODE.read_text())["phase"]
    for i in range(S):
        j = (i + 1) % S
        lo = posed_loop(strips[i], "e")                     # bottom -> top real paths
        hi = posed_loop(strips[j], "s")
        at_lo = loop_attrs(i, lo)
        at_hi = loop_attrs(j, hi)
        lo = [at_lo[K2(p)][0] if K2(p) in at_lo else p for p in lo]
        hi = [at_hi[K2(p)][0] if K2(p) in at_hi else p for p in hi]
        seam_pts.extend(lo + hi)
        widths = [min(math.hypot(p[0] - q[0], p[2] - q[2]) for q in hi) for p in lo
                  if p[1] > LOWLAND - 0.2]
        bridge_stats.append((min(widths), max(widths)))
        # outward at this seam: radial from the ring centre (star-shaped at the seams)
        sx = float(np.mean([p[0] for p in lo + hi]))
        sz = float(np.mean([p[2] for p in lo + hi]))
        ow = (sx - CENTER[0], sz - CENTER[1])
        Lo = math.hypot(*ow) or 1.0
        ow = (ow[0] / Lo, ow[1] / Lo)

        # the lo chain's course-correct (y -> u, v) map: each segment between consecutive
        # lo verts is one course (one tile), so lerping within a segment stays in-tile
        # and the tile changes at course boundaries exactly as a real column's does
        lo_yuv = sorted(((q[1],) + tuple(at_lo[K2(q)][1]) for q in lo if K2(q) in at_lo
                         and X.decode_id(int(round(at_lo[K2(q)][3][0])))
                         ["topograph"] == ROCK))
        if not lo_yuv:
            lo_yuv = sorted(((q[1],) + tuple(at_lo[K2(q)][1]) for q in lo
                             if K2(q) in at_lo))

        def u_cont(p_hi, _unused=None):
            """The mortar continues the OUT column's tile: v follows the column's own
            course structure at the vert's y; u pushes into the tile (LAW-2 mirror) and
            CLAMPS inside the window -- an overshoot lands in the atlas's transparent
            gutters (the in-game white spikes)."""
            y = p_hi[1]
            if y <= lo_yuv[0][0]:
                _, u_e, v_e = lo_yuv[0]
            elif y >= lo_yuv[-1][0]:
                _, u_e, v_e = lo_yuv[-1]
            else:
                for q1 in range(1, len(lo_yuv)):
                    if lo_yuv[q1][0] >= y:
                        y0, u0, v0 = lo_yuv[q1 - 1]
                        y1, u1, v1 = lo_yuv[q1]
                        tt = 0.0 if y1 <= y0 else (y - y0) / (y1 - y0)
                        u_e, v_e = u0 + tt * (u1 - u0), v0 + tt * (v1 - v0)
                        break
            t_u0 = pu_ph + math.floor((u_e - pu_ph) / TILE_U) * TILE_U
            d = min(math.hypot(p_hi[0] - q[0], p_hi[2] - q[2]) for q in lo)
            du = min(d / max(strips[i]["st"], 1e-6), 0.95) * TILE_U
            centre = t_u0 + TILE_U / 2
            sign = 1.0 if u_e < centre else -1.0
            u_out = min(t_u0 + TILE_U - 0.002, max(t_u0 + 0.002, u_e + sign * du))
            return (u_out, v_e)
        i2 = j2 = 0
        while i2 < len(lo) - 1 or j2 < len(hi) - 1:
            ci, cj = i2 < len(lo) - 1, j2 < len(hi) - 1
            if ci and cj:
                step_lo = (math.dist(lo[i2 + 1], hi[j2]) <=
                           math.dist(lo[i2], hi[j2 + 1]))
            else:
                step_lo = ci
            if step_lo:
                tri = [lo[i2], lo[i2 + 1], hi[j2]]
            else:
                tri = [lo[i2], hi[j2 + 1], hi[j2]]
            if len({kk(p) for p in tri}) == 3:
                a2, b2, c2 = (np.array(p) for p in tri)
                fn = np.cross(b2 - a2, c2 - a2)
                if fn[0] * ow[0] + fn[2] * ow[1] < 0:
                    tri = [tri[0], tri[2], tri[1]]
                rec = []
                for p in tri:
                    k2 = K2(p)
                    if k2 in at_lo:
                        _, uv, n3, t4 = at_lo[k2]
                        rec.append((p, uv, n3, t4))
                    else:
                        _, uv_h, n3, t4 = at_hi.get(k2, (p, (0.5, 0.5),
                                                         (ow[0], 0.0, ow[1]),
                                                         (0.0, 0.0, 0.0, 1.0)))
                        # anchor u/v on the nearest ROCK lo vert's uv (a pocket vert's
                        # grass uv would smear garbage across the mortar)
                        cand = [q for q in lo if K2(q) in at_lo and
                                X.decode_id(int(round(at_lo[K2(q)][3][0])))
                                ["topograph"] == ROCK]
                        if not cand:
                            cand = [q for q in lo if K2(q) in at_lo]
                        qn = min(cand, key=lambda q: abs(q[1] - p[1]) * 2 +
                                 math.hypot(q[0] - p[0], q[2] - p[2]))
                        uv_lo = at_lo[K2(qn)][1]
                        rec.append((p, u_cont(p, uv_lo), n3, t4))
                bridges.append(rec)
            if step_lo:
                i2 += 1
            else:
                j2 += 1
    print(f"mortar bridges: {len(bridges)} tris over {S} seams; widths "
          f"{[(round(w0, 1), round(w1, 1)) for w0, w1 in bridge_stats]}u")

    wall = [rec for sp in posed for rec in sp] + bridges

    # ---- the crest polyline (the top fill's clip polygon) ----------------------------------
    cnt = defaultdict(int)
    for rec in wall:
        ps = [kk(r[0]) for r in rec]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt[tuple(sorted((ps[a], ps[b])))] += 1
    crest_edges = [e for e, n in cnt.items()
                   if n == 1 and min(e[0][1], e[1][1]) > top_y - 4.0]
    adj = defaultdict(list)
    for a, b in crest_edges:
        adj[a].append(b)
        adj[b].append(a)
    deg_bad = [p for p, l in adj.items() if len(l) != 2]
    if len(deg_bad) == 2 and math.dist(deg_bad[0], deg_bad[1]) <= 5.0:
        # a crest NOTCH at one mortar top (the natural-end loop topped out one jittered
        # edge below the true crest end): stitch the polyline across it -- the top fill
        # then spans the notch and the sliver capper closes the residual loop
        a2, b2 = deg_bad
        adj[a2].append(b2)
        adj[b2].append(a2)
        print(f"crest: stitched a {math.dist(a2, b2):.2f}u notch at one seam top")
        deg_bad = []
    if deg_bad:
        for p in deg_bad[:8]:
            print(f"  DBG crest degree-{len(adj[p])} at {p}: nbrs {adj[p][:3]}")
            near = sorted(adj.keys(), key=lambda q: math.dist(q, p))[1:3]
            for q in near:
                print(f"      nearest crest pt {q} d={math.dist(q, p):.3f}")
    assert not deg_bad, (f"crest not a simple cycle ({len(deg_bad)} odd-degree pts, "
                         f"e.g. {deg_bad[:3]})")
    start = crest_edges[0][0]
    crest = [start]
    prev = None
    while True:
        nxts = [p for p in adj[crest[-1]] if p != prev]
        if not nxts or nxts[0] == start:
            break
        prev = crest[-1]
        crest.append(nxts[0])
    assert len(crest) == len({kk(p) for p in crest}), "crest revisits a vertex"
    th0 = [math.atan2(p[2] - CENTER[1], p[0] - CENTER[0]) for p in crest]
    if np.diff(np.unwrap(th0)).sum() < 0:
        crest = crest[::-1]
    crest_poly = [(p[0], p[2]) for p in crest]
    crest_y_of = {}
    for i2 in range(len(crest)):
        crest_y_of[(round(crest[i2][0], 3), round(crest[i2][2], 3))] = crest[i2][1]
    print(f"crest polyline: {len(crest)} verts, closed")

    # ---- the top fill (T1 machinery, welded to the CARRIED crest) --------------------------
    def crest_y_at(px, pz):
        best = None
        n2 = len(crest)
        for i2 in range(n2):
            a, b = crest[i2], crest[(i2 + 1) % n2]
            dx, dz = b[0] - a[0], b[2] - a[2]
            L2 = dx * dx + dz * dz
            t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0,
                                                    ((px - a[0]) * dx + (pz - a[2]) * dz) / L2))
            qx, qz = a[0] + t * dx, a[2] + t * dz
            d = math.hypot(px - qx, pz - qz)
            y = a[1] + t * (b[1] - a[1])
            if best is None or d < best[0]:
                best = (d, y, i2, t)
        return best

    def y_top(px, pz):
        """ONE y rule for every top vert -- a lattice corner ON the crest curve must get
        the crest y in EVERY cell that references it, or the shared edge splits in y."""
        db, yb, _, _ = crest_y_at(px, pz)
        return yb if db < 0.05 else top_y

    xs = [p[0] for p in crest_poly]
    zs = [p[1] for p in crest_poly]
    top_tris = []
    x = math.floor(min(xs) / CELL) * CELL
    while x < max(xs):
        z = math.floor(min(zs) / CELL) * CELL
        while z < max(zs):
            corners = [(x, z), (x + CELL, z), (x + CELL, z + CELL), (x, z + CELL)]
            ins = [pinp(px, pz, crest_poly) for (px, pz) in corners]
            if all(ins):
                a, b, c, d = [(px, y_top(px, pz), pz) for (px, pz) in corners]
                top_tris += [[a, b, c], [a, c, d]]
            else:
                # clip even when NO corner is inside: the crest can dip through a cell
                # without capturing a corner, and a skipped sliver leaves the wall's
                # crest edge with no top counterpart
                pg = clip_cell(crest_poly, x, z)
                if len(pg) >= 3 and poly_area2(pg) > 1e-6:
                    pg3 = [(p[0], y_top(p[0], p[1]), p[1]) for p in pg]
                    for t3 in centroid_fan(pg3):
                        top_tris.append([tuple(q) for q in t3])
            z += CELL
        x += CELL
    fixed = []
    for t3 in top_tris:
        a, b, c = (np.array(p) for p in t3)
        if np.cross(b - a, c - a)[1] < 0:
            t3 = [t3[0], t3[2], t3[1]]
        fixed.append(t3)
    top_tris = fixed

    # T-vertex conformance (y-aware): split any top edge carrying another top vert
    allv = {}
    for t3 in top_tris:
        for p in t3:
            allv[(round(p[0], 3), round(p[2], 3))] = p[1]

    def _on_seg(p2, a, b):
        ax, az, bx, bz = a[0], a[2], b[0], b[2]
        px, pz = p2
        cross = (bx - ax) * (pz - az) - (bz - az) * (px - ax)
        if abs(cross) > 1e-3:
            return None
        L2 = (bx - ax) ** 2 + (bz - az) ** 2
        if L2 < 1e-9:
            return None
        t = ((px - ax) * (bx - ax) + (pz - az) * (bz - az)) / L2
        return t if 1e-4 < t < 1 - 1e-4 else None

    conformed = []
    n_split = 0
    for t3 in top_tris:
        pg = []
        for k3 in range(3):
            a, b = t3[k3], t3[(k3 + 1) % 3]
            pg.append(a)
            ins = []
            for p2, py in allv.items():
                if (round(a[0], 3), round(a[2], 3)) == p2 or \
                        (round(b[0], 3), round(b[2], 3)) == p2:
                    continue
                t = _on_seg(p2, a, b)
                if t is not None:
                    ins.append((t, (p2[0], py, p2[1])))
            for _, p3 in sorted(ins):
                pg.append(p3)
                n_split += 1
        if len(pg) == 3:
            conformed.append(t3)
        else:
            for tt in centroid_fan(pg):
                conformed.append(list(tt))
    top_tris = conformed
    print(f"top: {len(top_tris)} shelf tris ({n_split} T-splits conformed)")

    # weld the WALL to the top: split wall crest-edge tris at top boundary verts that lie
    # on carried crest segments (canonical positions -- crest_y_at's own lerp)
    crest_set = {kk(p) for p in crest}
    top_bverts = []
    for t3 in top_tris:
        for p in t3:
            db, yb, i2, t = crest_y_at(p[0], p[2])
            if db < 0.05 and kk((p[0], yb, p[2])) not in crest_set:
                top_bverts.append((i2, t, (p[0], yb, p[2])))
    seg_pts = defaultdict(list)
    for i2, t, p3 in top_bverts:
        seg_pts[i2].append((t, p3))
    refined_wall = []
    for rec in wall:
        done = False
        for (ea, eb) in ((0, 1), (1, 2), (2, 0)):
            wa, wb = rec[ea][0], rec[eb][0]
            ka, kb2 = kk(wa), kk(wb)
            if ka in crest_set and kb2 in crest_set and not done:
                n2 = len(crest)
                ia = next((q for q in range(n2) if kk(crest[q]) == ka), None)
                if ia is None:
                    continue
                fwd = kk(crest[(ia + 1) % n2]) == kb2
                bwd = kk(crest[(ia - 1) % n2]) == kb2
                if not (fwd or bwd):
                    continue
                i2 = ia if fwd else (ia - 1) % n2
                pts = sorted(seg_pts.get(i2, []))
                if not pts:
                    continue
                if bwd:
                    pts = pts[::-1]
                ec = 3 - ea - eb
                seen_w = {kk(wa), kk(wb)}
                seq = [rec[ea]]
                eL = math.dist(wa, wb) or 1.0
                for _, p3 in pts:
                    if kk(p3) not in seen_w:                # no zero-length edges
                        # LERP uv+normal along the edge -- endpoint-A's uv verbatim
                        # smears every split tri (the in-game "stretched crest band")
                        tt = min(1.0, max(0.0, math.dist(wa, p3) / eL))
                        uv_m = tuple(rec[ea][1][j] + tt * (rec[eb][1][j] - rec[ea][1][j])
                                     for j in range(2))
                        n_m = tuple(rec[ea][2][j] + tt * (rec[eb][2][j] - rec[ea][2][j])
                                    for j in range(3))
                        seq.append((p3, uv_m, n_m, rec[ea][3]))
                        seen_w.add(kk(p3))
                seq.append(rec[eb])
                if len(seq) == 2:
                    refined_wall.append(rec)
                    done = True
                    continue
                for q0 in range(len(seq) - 1):
                    refined_wall.append([seq[q0], seq[q0 + 1], rec[ec]])
                done = True
        if not done:
            refined_wall.append(rec)
    n_crest_split = len(refined_wall) - len(wall)
    wall = refined_wall
    print(f"crest weld: {n_crest_split} wall tris split at top boundary verts")

    # ---- the ground: rim polygon + exact cut of the bench grass ----------------------------
    # the y = LOWLAND cross-section of the carried faces -> closed contour -> inset inward
    segs = []
    for rec in wall:
        w3 = [r[0] for r in rec]
        ys2 = [p[1] for p in w3]
        if min(ys2) >= LOWLAND or max(ys2) <= LOWLAND:
            continue
        pts2 = []
        for (a, b) in ((0, 1), (1, 2), (2, 0)):
            ya, yb = w3[a][1], w3[b][1]
            if (ya - LOWLAND) * (yb - LOWLAND) < 0:
                t = (LOWLAND - ya) / (yb - ya)
                pts2.append((w3[a][0] + t * (w3[b][0] - w3[a][0]),
                             w3[a][2] + t * (w3[b][2] - w3[a][2])))
        if len(pts2) == 2:
            segs.append(pts2)
    # chain the contour
    padj = defaultdict(list)
    for a, b in segs:
        ka, kb2 = (round(a[0], 2), round(a[1], 2)), (round(b[0], 2), round(b[1], 2))
        padj[ka].append(kb2)
        padj[kb2].append(ka)
    loops = []
    visited = set()
    for start in list(padj):
        if start in visited:
            continue
        loop = [start]
        prev = None
        while True:
            nxts = [p for p in padj[loop[-1]] if p != prev]
            if not nxts or nxts[0] == start:
                break
            prev = loop[-1]
            loop.append(nxts[0])
        visited.update(loop)
        loops.append(loop)
    loops.sort(key=len, reverse=True)
    contour = loops[0]
    print(f"ground contour: {len(contour)} pts from {len(segs)} face crossings "
          f"({len(loops)} loop(s); shorter ones are ledge-dip crossings, ignored)")
    assert len(contour) >= 12, "ground contour did not chain"
    # resample ~2u + inset inward
    res = []
    accum = 0.0
    for i2 in range(len(contour)):
        a, b = contour[i2], contour[(i2 + 1) % len(contour)]
        if not res:
            res.append(a)
        d = math.dist(a, b)
        accum += d
        if accum >= 2.0:
            res.append(b)
            accum = 0.0
    res = [p for i2, p in enumerate(res) if math.dist(p, res[(i2 + 1) % len(res)]) > 1e-6]
    area = 0.0
    for i2 in range(len(res)):
        p, q = res[i2], res[(i2 + 1) % len(res)]
        area += p[0] * q[1] - q[0] * p[1]
    ccw = area > 0
    P_rim = []
    n2 = len(res)
    for i2 in range(n2):
        a, b, c = res[(i2 - 1) % n2], res[i2], res[(i2 + 1) % n2]
        tx, tz = c[0] - a[0], c[1] - a[1]
        L = math.hypot(tx, tz) or 1.0
        # inward = left of travel for CCW
        nx, nz = (-tz / L, tx / L) if ccw else (tz / L, -tx / L)
        P_rim.append((b[0] + nx * RIM_INSET, b[1] + nz * RIM_INSET))

    # exact cut: general-line slices with crossings computed once per (line, edge)
    def slice_line(pg, o, dvec):
        keep_pos, keep_neg = [], []
        n3 = len(pg)
        dd = [((p[0] - o[0]) * dvec[1] - (p[1] - o[1]) * dvec[0]) for p in pg]
        for i3 in range(n3):
            a, b = pg[i3], pg[(i3 + 1) % n3]
            da, db = dd[i3], dd[(i3 + 1) % n3]
            if da >= -1e-12:
                keep_pos.append(a)
            if da <= 1e-12:
                keep_neg.append(a)
            if (da > 1e-12 and db < -1e-12) or (da < -1e-12 and db > 1e-12):
                t = da / (da - db)
                m = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
                keep_pos.append(m)
                keep_neg.append(m)
        return keep_pos, keep_neg

    rim_lines = [(P_rim[i2], (P_rim[(i2 + 1) % len(P_rim)][0] - P_rim[i2][0],
                              P_rim[(i2 + 1) % len(P_rim)][1] - P_rim[i2][1]))
                 for i2 in range(len(P_rim))]
    grass_keep, grass_cut, dropped = [], [], 0
    rim_r_max = max(math.hypot(p[0] - CENTER[0], p[1] - CENTER[1]) for p in P_rim)
    for ti, t in enumerate(tris):
        if t["topo"] not in GRASS_TOPO:
            grass_keep.append(ti)
            continue
        d0 = math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
        if d0 > rim_r_max + 8.0:
            grass_keep.append(ti)
            continue
        # EVERY zone tri goes through the SAME slice pipeline -- an all-inside "drop
        # whole" shortcut loses the bay portions where the rim polygon crosses a tri
        # edge twice (both endpoints inside), and any per-tri shortcut gives neighbours
        # different subdivisions -> T-junctions. Distant lines leave a polygon intact.
        pieces = [[(p[0], p[2]) for p in t["w"]]]
        for (o, dvec) in rim_lines:
            nxt = []
            for pg in pieces:
                pos_, neg_ = slice_line(pg, o, dvec)
                for part in (pos_, neg_):
                    # keep SLIVERS: an area filter drops them on one side of a shared
                    # edge only, unpairing every neighbour (T1's 92-edge apron failure)
                    if len(part) >= 3 and poly_area2(part) > 1e-14:
                        nxt.append(part)
            pieces = nxt
        kept_pieces = [pg for pg in pieces
                       if not pinp(sum(p[0] for p in pg) / len(pg),
                                   sum(p[1] for p in pg) / len(pg), P_rim)]
        if len(pieces) == 1 and kept_pieces:
            grass_keep.append(ti)                           # untouched: no line crossed it
        else:
            # subdivided (even if fully kept): emit the pieces, so shared-edge crossings
            # stay consistent with the neighbours' subdivisions
            grass_cut.append((ti, kept_pieces))
            dropped += 0 if kept_pieces else 1
    print(f"ground: {dropped} grass tris dropped inside the rim, {len(grass_cut)} cut, "
          f"{len(grass_keep)} untouched")

    # KEPT-TRI CONFORMANCE: a kept-whole tri sharing an edge with a cut tri must split at
    # the cut's crossing points, or the rim cut mints T-junctions against it (the exact
    # failure class the T1 apron partition hit; here the geometry is flat and two-party,
    # so the split is geometry-neutral).
    frag_verts2 = {}
    for ti, pieces in grass_cut:
        for pg in pieces:
            for q in pg:
                frag_verts2[(round(q[0], 3), round(q[1], 3))] = q

    def affine_attr(t, p2, chan):
        (x1, z1), (x2, z2), (x3, z3) = ((t["w"][k][0], t["w"][k][2]) for k in range(3))
        det = (x2 - x1) * (z3 - z1) - (x3 - x1) * (z2 - z1)
        if abs(det) < 1e-12:
            return list(t[chan][0])
        w2 = ((p2[0] - x1) * (z3 - z1) - (x3 - x1) * (p2[1] - z1)) / det
        w3 = ((x2 - x1) * (p2[1] - z1) - (p2[0] - x1) * (z2 - z1)) / det
        w1 = 1 - w2 - w3
        return [w1 * t[chan][0][j] + w2 * t[chan][1][j] + w3 * t[chan][2][j]
                for j in range(len(t[chan][0]))]

    def _on_seg2(p2, a, b):
        ax, az, bx, bz = a[0], a[2], b[0], b[2]
        cross = (bx - ax) * (p2[1] - az) - (bz - az) * (p2[0] - ax)
        if abs(cross) > 1e-3:
            return None
        L2 = (bx - ax) ** 2 + (bz - az) ** 2
        if L2 < 1e-9:
            return None
        t = ((p2[0] - ax) * (bx - ax) + (p2[1] - az) * (bz - az)) / L2
        return t if 1e-4 < t < 1 - 1e-4 else None

    kept_out = []                                           # (t3, uv3, n3, tan3, blk)
    n_kept_split = 0
    for ti in grass_keep:
        t = tris[ti]
        d0 = math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
        # conformance covers grass AND the coast-nav stamp classes (53-56): a stamped or
        # sloped tri neighbouring zone grass must still split at shared crossings. +16,
        # NOT +9: the mint's coast-fan tris are large and irregular.
        if t["topo"] not in (GRASS_TOPO | {53, 54, 55, 56}) or d0 > rim_r_max + 16.0:
            kept_out.append((t["w"], t["uv"], t["n"], t["tan"], t["blk"]))
            continue
        pg = []
        inserted = False
        for k3 in range(3):
            a, b = t["w"][k3], t["w"][(k3 + 1) % 3]
            pg.append((a, t["uv"][k3], t["n"][k3], t["tan"][k3]))
            ins = []
            for p2 in frag_verts2:
                if (round(a[0], 3), round(a[2], 3)) == p2 or \
                        (round(b[0], 3), round(b[2], 3)) == p2:
                    continue
                tt = _on_seg2(p2, a, b)
                if tt is not None:
                    ins.append((tt, p2))
            for tt, p2 in sorted(ins):
                p3 = (p2[0], a[1] + tt * (b[1] - a[1]), p2[1])  # edge-lerped y (slopes!)
                pg.append((p3, affine_attr(t, p2, "uv"), affine_attr(t, p2, "n"),
                           affine_attr(t, p2, "tan")))
                inserted = True
                n_kept_split += 1
        if not inserted:
            kept_out.append((t["w"], t["uv"], t["n"], t["tan"], t["blk"]))
            continue
        cx = sum(q[0][0] for q in pg) / len(pg)
        cy = sum(q[0][1] for q in pg) / len(pg)
        cz = sum(q[0][2] for q in pg) / len(pg)
        cen_rec = ((cx, cy, cz), affine_attr(t, (cx, cz), "uv"),
                   affine_attr(t, (cx, cz), "n"), affine_attr(t, (cx, cz), "tan"))
        for q0 in range(len(pg)):
            a_r, b_r = pg[q0], pg[(q0 + 1) % len(pg)]
            t3 = [cen_rec[0], a_r[0], b_r[0]]
            if np.cross(np.array(t3[1]) - np.array(t3[0]),
                        np.array(t3[2]) - np.array(t3[0]))[1] < 0:
                a_r, b_r = b_r, a_r
                t3 = [cen_rec[0], a_r[0], b_r[0]]
            kept_out.append((t3, [cen_rec[1], a_r[1], b_r[1]],
                             [cen_rec[2], a_r[2], b_r[2]],
                             [cen_rec[3], a_r[3], b_r[3]], t["blk"]))
    print(f"kept conformance: {n_kept_split} edge splits on kept grass")

    # ---- L3 for the top (T1 verbatim: seeded from the bench's own kept grass) --------------
    sys.path.insert(0, str(ROOT / "studies" / "overworld-topography"))
    import uvf_fix2 as UF                                   # noqa: E402

    def tri_cell(t3):
        """FLOOR-z cells: mains_uv computes fz = (z - 4j)/4, so j = floor(z/4) (negative
        south of origin). The negated int(-z//4) convention fed it fz ~ -256 -> clamp ->
        every u collapsed (THE ROUND-3 'BANDED TOP', root-caused offline: decode rate
        0/354 with the negated key, 59/60 with this one)."""
        cx4 = float(np.mean([p[0] for p in t3]))
        cz4 = float(np.mean([p[2] for p in t3]))
        return (math.floor(cx4 / CELL), math.floor(cz4 / CELL))

    pre_quad, pre_ori = {}, {}
    kept_set = set(grass_keep)
    for ti, t in enumerate(tris):
        if ti not in kept_set or t["topo"] not in GRASS_TOPO:
            continue
        ccell = tri_cell(t["w"])
        if ccell in pre_quad:
            continue
        if math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1]) > rim_r_max + 26.0:
            continue
        qo = UF.decode_quad_ori(ccell, t["w"], [tuple(u2) for u2 in t["uv"]])
        if qo is not None:
            pre_quad[ccell], pre_ori[ccell] = qo
    top_cells = sorted({tri_cell(t3) for t3 in top_tris})
    q2, o2 = UF.assign_mains_seeded([c for c in top_cells if c not in pre_quad],
                                    dict(pre_quad), dict(pre_ori), seed=SEED ^ 0xF92)
    cell_qo = {c: (pre_quad[c], pre_ori[c]) for c in top_cells if c in pre_quad}
    cell_qo.update({c: (q2[c], o2[c]) for c in q2 if c in set(top_cells)})
    print(f"L3 top: {len(pre_quad)} cells decoded from bench grass, {len(q2)} policy-resolved")
    top_out = []
    for t3 in top_tris:
        ccell = tri_cell(t3)
        quad, ori = cell_qo[ccell]
        top_out.append((t3, [G.ground_uv(p[0], p[2], ccell, quad, ori) for p in t3]))

    # cut grass pieces take their UVs AFFINELY from the parent tri -- the exact
    # continuation of the cell's own mapping, no window decode needed, no stretch
    cut_out = []
    for ti, pieces in grass_cut:
        t = tris[ti]
        for pg in pieces:
            for tt in centroid_fan(pg):
                t3 = [(q[0], LOWLAND, q[1]) for q in tt]
                a, b, c = (np.array(p) for p in t3)
                if np.cross(b - a, c - a)[1] < 0:
                    t3 = [t3[0], t3[2], t3[1]]
                uvt = [affine_attr(t, (p[0], p[2]), "uv") for p in t3]
                cut_out.append((t3, uvt, t))
    print(f"ground cut fragments: {len(cut_out)} tris re-emitted (parent-affine UVs)")

    # ---- gates ------------------------------------------------------------------------------
    fails = []
    # the mortar bound: the corner warp (a kink k rotates the ~12u batter lean) plus the
    # base gap is the column's widest lawful extent; a crossed (0-width) pair would fold
    warp_bound = 2 * 12.0 * math.sin(math.radians(max(abs(k) for k in kinks)) / 2) \
        + SEAM_GAP + 4.0
    if gap > 2.5:
        fails.append(f"closure gap {gap:.2f}u exceeds the final-mortar absorption budget")
    for si, (w0, w1) in enumerate(bridge_stats):
        if w0 < 0.15:
            fails.append(f"mortar {si}: crossing cross-sections (min width {w0:.2f}u)")
        if w1 > warp_bound:
            fails.append(f"mortar {si}: width {w1:.1f}u exceeds the warp bound "
                         f"{warp_bound:.1f}u")
    for i, (n_ok, n_bad, bad) in enumerate(seam_report):
        if n_bad > n_ok:
            fails.append(f"seam {i}: h_pairs mostly unlawful ({n_bad} vs {n_ok}) {bad}")

    def outward_of(px, pz):
        d = (px - CENTER[0], pz - CENTER[1])
        L = math.hypot(*d) or 1.0
        return (d[0] / L, d[1] / L)

    n_degen = 0
    for rec in wall:
        t3 = [r[0] for r in rec]
        a, b, c = (np.array(p) for p in t3)
        fn = np.cross(b - a, c - a)
        L = float(np.linalg.norm(fn))
        if L < 2e-2:
            n_degen += 1
            continue
        if max(p[1] for p in t3) < LOWLAND - 0.2:
            continue                                        # buried: never visible
        rad = outward_of(float(np.mean([p[0] for p in t3])),
                         float(np.mean([p[2] for p in t3])))
        horiz = math.hypot(fn[0], fn[2])
        if horiz > 0.3 * L and (fn[0] * rad[0] + fn[2] * rad[1]) / max(horiz, 1e-9) < -0.6:
            fails.append(f"winding: a visible wall tri faces INWARD at {kk(t3[0])}")
        if fn[1] < -0.5 * L:
            fails.append(f"winding: a visible wall tri faces DOWN at {kk(t3[0])}")
    for t3, _ in top_out:
        a, b, c = (np.array(p) for p in t3)
        fn = np.cross(b - a, c - a)
        if fn[1] < 0 and float(np.linalg.norm(fn)) > 2e-2:
            fails.append(f"winding: a top tri faces DOWN at {kk(t3[0])}")
    print(f"winding: {n_degen} near-degenerate wall tris exempt")

    # watertight: kept + cut + wall + top; allowed once-edges = rim lines + sub-ground
    cnt3 = defaultdict(int)

    def _acc(t3):
        ps = [kk(p) for p in t3]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt3[tuple(sorted((ps[a], ps[b])))] += 1
    pre_once = set()
    cnt0 = defaultdict(int)
    for t in tris:
        ps = [kk(p) for p in t["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt0[tuple(sorted((ps[a], ps[b])))] += 1
    pre_once = {e for e, n in cnt0.items() if n == 1}
    for t3, _, _, _, _ in kept_out:
        _acc(t3)
    for t3, _, _ in cut_out:
        _acc(t3)
    for rec in wall:
        _acc([r[0] for r in rec])
    for t3, _ in top_out:
        _acc(t3)
    post_once = {e for e, n in cnt3.items() if n == 1}
    grew = post_once - pre_once

    def rim_ok(e):
        """The hole boundary: ground-level once-edges inside (or on) the rim polygon --
        all hidden under the wall body / plateau interior."""
        if not (abs(e[0][1] - LOWLAND) < 0.05 and abs(e[1][1] - LOWLAND) < 0.05):
            return False
        for p in e:
            if pinp(p[0], p[2], P_rim):
                continue
            d = min(math.hypot(p[0] - q[0], p[2] - q[1]) for q in P_rim)
            if d > 2.6:
                return False
        return True

    def sub_ok(e):
        return max(e[0][1], e[1][1]) < LOWLAND - 0.2

    def degen(e):
        return e[0] == e[1]

    def mortar_ok(e):
        """Boundary residue enclosed in a mortar zone: a skipped ledge-arm of a cut path
        sits between the two cross-sections, behind the bridge sheet."""
        return all(any(math.hypot(p[0] - q[0], p[2] - q[2]) <= 3.0 for q in seam_pts)
                   for p in e)

    grew_bad = [e for e in grew if not (rim_ok(e) or sub_ok(e) or degen(e)
                                        or mortar_ok(e))]
    # THE SLIVER CAPPER: exact-partition corner cases (crest tangencies, cut slivers)
    # leave tiny closed boundary loops. Cap any undeclared loop of <= 10 edges spanning
    # <= 4u -- the cap IS the missing sliver, attributes from an adjacent existing tri.
    if grew_bad:
        # union-find the undeclared edges into components; a small component is a hole
        # (closed ring, forked ring, or a chain straddling another declaration class) --
        # fan-cap its angularly-ordered point set in its dominant plane. Coplanar overlap
        # with existing flat ground renders identically; at the crest the cap IS the fill.
        parent = {}

        def find(p):
            while parent[p] != p:
                parent[p] = parent[parent[p]]
                p = parent[p]
            return p
        for e in grew_bad:
            for p in e:
                parent.setdefault(p, p)
            ra, rb = find(e[0]), find(e[1])
            if ra != rb:
                parent[ra] = rb
        # merge components whose points are within 1.0u (a hole split across classes)
        roots = defaultdict(list)
        for p in parent:
            roots[find(p)].append(p)
        rlist = list(roots.items())
        for i1 in range(len(rlist)):
            for j1 in range(i1 + 1, len(rlist)):
                if any(math.dist(p, q) <= 2.0
                       for p in rlist[i1][1] for q in rlist[j1][1]):
                    parent[find(rlist[i1][0])] = find(rlist[j1][0])
        comps = defaultdict(list)
        for e in grew_bad:
            comps[find(e[0])].append(e)
        capped_edges = set()
        caps = []

        def near_attr(p, want_rock):
            """Rock caps sample ROCK wall records only (a pocket's dirt uv painted the
            orange spikes); ground caps sample the GRASS ground records."""
            best = None
            if want_rock:
                for rec in wall:
                    for (w, uv, n3, t4) in rec:
                        if X.decode_id(int(round(t4[0])))["topograph"] != ROCK:
                            continue
                        d = math.dist(w, p)
                        if best is None or d < best[0]:
                            best = (d, uv, n3, t4)
                        if best[0] < 0.05:
                            return best
                return best
            for t3g, uv3g, n3g, tan3g, _ in kept_out:
                for k3g in range(3):
                    d = math.dist(t3g[k3g], p)
                    if best is None or d < best[0]:
                        best = (d, uv3g[k3g], n3g[k3g], tan3g[k3g])
                    if best[0] < 0.05:
                        return best
            for t3g, uv3g, srcg in cut_out:
                for k3g in range(3):
                    d = math.dist(t3g[k3g], p)
                    if best is None or d < best[0]:
                        best = (d, uv3g[k3g], srcg["n"][0], srcg["tan"][0])
                    if best[0] < 0.05:
                        return best
            return best
        for root, es in comps.items():
            pts = sorted({p for e in es for p in e})
            if len(pts) < 3 or len(es) > 16:
                continue
            dia = max(math.dist(p, q) for p in pts for q in pts)
            if dia > 9.0:
                continue
            cen = tuple(float(np.mean([p[j] for p in pts])) for j in range(3))
            spans = [max(p[j] for p in pts) - min(p[j] for p in pts) for j in range(3)]
            ax = sorted(range(3), key=lambda j: -spans[j])[:2]
            ring = sorted(pts, key=lambda p: math.atan2(p[ax[1]] - cen[ax[1]],
                                                        p[ax[0]] - cen[ax[0]]))
            for e in es:
                capped_edges.add(e)
            want_rock = cen[1] > LOWLAND + 1.0              # crest caps rock, ground grass
            for q0 in range(len(ring)):
                t3 = [cen, ring[q0], ring[(q0 + 1) % len(ring)]]
                rec = []
                for p in t3:
                    got = near_attr(p, want_rock) or near_attr(p, not want_rock)
                    _, uv, n3, t4 = got
                    rec.append((tuple(p), uv, n3, t4))
                caps.append(rec)
                # DOUBLE-SIDED: a single-winding membrane backface-culls from one side
                # in game -- a hole from here, a floating flake from there
                caps.append([rec[0], rec[2], rec[1]])
        if caps:
            wall.extend(caps)
            grew_bad = [e for e in grew_bad if e not in capped_edges]
            print(f"   sliver caps: {len(caps)} tris cap "
                  f"{len(capped_edges)} boundary edges; {len(grew_bad)} remain")
    n_rim = sum(1 for e in grew if rim_ok(e))
    n_sub = sum(1 for e in grew if sub_ok(e) and not rim_ok(e))
    n_dg = sum(1 for e in grew if degen(e))
    n_mz = sum(1 for e in grew if mortar_ok(e) and not (rim_ok(e) or sub_ok(e)
                                                        or degen(e)))
    if n_mz > 24:
        fails.append(f"mortar-zone residue {n_mz} exceeds the declared bound 24")
    print(f"watertight: {len(grew)} new once-edges = {n_rim} hole-rim (hidden) + {n_sub} "
          f"sub-ground (buried) + {n_dg} degenerate + {n_mz} mortar-zone (enclosed) + "
          f"{len(grew_bad)} UNDECLARED")
    if grew_bad:
        fails.append(f"watertight: {len(grew_bad)} undeclared once-edges "
                     f"(sample {grew_bad[:3]})")
        edge_owner = defaultdict(list)

        def _tag(t3, tag):
            ps = [kk(p) for p in t3]
            for a2, b2 in ((0, 1), (1, 2), (2, 0)):
                edge_owner[tuple(sorted((ps[a2], ps[b2])))].append(tag)
        for sp_i, sp in enumerate(posed):
            for rec in sp:
                _tag([r[0] for r in rec], f"strip{sp_i}")
        for rec in bridges:
            _tag([r[0] for r in rec], "bridge")
        for t3, _ in top_out:
            _tag(t3, "top")
        for t3, _, _ in cut_out:
            _tag(t3, "cut")
        for t3, _, _, _, _ in kept_out:
            _tag(t3, "kept")
        hist = Counter(tuple(sorted(set(edge_owner.get(e, ["?"])))) for e in grew_bad)
        print(f"   undeclared owners: {dict(hist)}")
        for e in grew_bad[:6]:
            print(f"   BAD {edge_owner.get(e, ['?'])} {e}")
        # targeted forensics: everything emitted near the first bad edge's midpoint
        e0 = grew_bad[0]
        mid0 = ((e0[0][0] + e0[1][0]) / 2, (e0[0][2] + e0[1][2]) / 2)
        print(f"   FORENSICS around {mid0}:")
        for tag, t3s in (("cut", [t3 for t3, _, _ in cut_out]),
                         ("kept", [t3 for t3, _, _, _, _ in kept_out])):
            for t3 in t3s:
                cx = float(np.mean([p[0] for p in t3]))
                cz = float(np.mean([p[2] for p in t3]))
                if math.hypot(cx - mid0[0], cz - mid0[1]) < 3.0:
                    print(f"     {tag}: {[kk(p) for p in t3]}")

    # massing gates on the composed ground line (the visible foot)
    fturn = [signed_turn(contour[(i2 - 1) % len(contour)], contour[i2],
                         contour[(i2 + 1) % len(contour)])
             for i2 in range(len(contour))]
    fabs = [abs(a2) for a2 in fturn]
    med_t = float(np.median(fabs))
    n_right = sum(1 for a2 in fabs if 80 <= a2 <= 100)
    if med_t > 30.0 or n_right > len(fabs) * 0.03:
        fails.append(f"massing: ground line med turn {med_t:.1f} deg / {n_right} right angles")
    print(f"massing: ground-line turn med {med_t:.1f} deg, right angles {n_right}"
          f"/{len(fabs)}")

    # bench reach: the VISIBLE ring needs a flat annulus before the coast; buried verts
    # only need to stay under the island's ground sheet
    reach_vis = max((math.hypot(r[0][0] - CENTER[0], r[0][2] - CENTER[1])
                     for rec in wall for r in rec if r[0][1] > LOWLAND - 0.2), default=0)
    reach_bur = max(math.hypot(r[0][0] - CENTER[0], r[0][2] - CENTER[1])
                    for rec in wall for r in rec)
    need_r = max(reach_vis + 6.0, reach_bur + 1.5)
    print(f"reach: visible {reach_vis:.1f}u / buried {reach_bur:.1f}u -> island radius "
          f"needed ~{need_r:.0f}u (bench grass ~{grass_r:.1f}u)")
    if grass_r < need_r - 2.0:
        fails.append(f"bench too small: re-mint the island at radius "
                     f"{math.ceil(need_r - 2.5)} (same center, same six blocks)")

    # ---- assemble ---------------------------------------------------------------------------
    ID_SHELF = float(X.encode_id(topograph=SHELF))
    by_cell = defaultdict(lambda: ([], [], [], []))

    def emit(cell, p, u2, n2, t4):
        pos, nrm, uv, tan = by_cell[cell]
        pos.append([p[0] - BLOCK * cell[0], p[1], p[2] + BLOCK * cell[1]])
        nrm.append(list(n2))
        uv.append(list(u2))
        tan.append(list(t4))

    def cell_of(t3):
        cx = float(np.mean([p[0] for p in t3]))
        cz = float(np.mean([p[2] for p in t3]))
        return (int(cx // BLOCK), int(-cz // BLOCK))

    for t3, uv3, n3, tan3, blk in kept_out:
        for k3 in range(3):
            emit(blk, t3[k3], uv3[k3], n3[k3], tan3[k3])
    for t3, uvt, src in cut_out:
        c = cell_of(t3)
        for k3 in range(3):
            emit(c, t3[k3], uvt[k3], src["n"][0], src["tan"][0])
    # top-face normal for the shelf; carried normals for the wall
    for rec in wall:
        t3 = [r[0] for r in rec]
        c = cell_of(t3)
        for k3 in range(3):
            emit(c, t3[k3], rec[k3][1], rec[k3][2], rec[k3][3])
    for t3, uvt in top_out:
        c = cell_of(t3)
        for k3 in range(3):
            emit(c, t3[k3], uvt[k3], (0.0, 1.0, 0.0), [ID_SHELF, 0.0, 0.0, 1.0])

    changed = {}
    for cell, (pos, nrm, uv, tan) in by_cell.items():
        flat = list(range(len(pos)))
        changed[cell] = X.BlockMesh(
            name=f"Block[{cell[0]}][{cell[1]}] Terrain", disc=DISC, x=cell[0], y=cell[1],
            lod="0_1", vcount=len(pos), stride=48,
            channels={X.CH_POS: (0, 3), X.CH_NRM: (12, 3), X.CH_UV: (24, 2), X.CH_TAN: (32, 4)},
            chan_arrays={X.CH_POS: pos, X.CH_NRM: nrm, X.CH_UV: uv, X.CH_TAN: tan},
            flat_index=flat, tris=[flat[3 * t2:3 * t2 + 3] for t2 in range(len(flat) // 3)],
            raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    IN.census_gate(changed, disc=1)
    print(f"census MISS=0 across {len(changed)} changed cells")

    # ---- renders ----------------------------------------------------------------------------
    render(wall, top_out, cut_out, kept_out)

    print(f"gates: {len(fails)} failure(s)")
    for f in fails[:10]:
        print("  !!", f)
    if fails:
        print("\nSTRIP: GATES RED -- not deployable")
        return 1
    if not args.apply:
        print("\nSTRIP: gates green (offline). Review the renders; --apply to deploy.")
        return 0

    ts = time.strftime("%Y%m%d-%H%M%S")
    bdir = Path(r"C:\gd\Dream-World-IX\backups") / f"terrace-strip-prewall.{ts}"
    bdir.mkdir(parents=True, exist_ok=True)
    for cell, (p, _bm) in bms.items():
        shutil.copy2(p, bdir / p.name)
    for cell, bm in sorted(changed.items()):
        w = M.deploy_override(bm, mod_folder=MOD, disc=DISC, part="Terrain")
        print(f"deployed -> {w} ({len(bm.tris)} tris)")
    print(f"pre-wall bench backed up -> {bdir}")
    print("in game: ~ -> Go -> 9013 -> World -> teleport (416, -512); re-enter the world.")
    return 0


def _cell_window(ccell, ti, tris, pre_quad, pre_ori, UF):
    """The (quad, ori) window of a CUT cell: decoded from the cell's own pre-cut tri."""
    if ccell in pre_quad:
        return pre_quad[ccell], pre_ori[ccell]
    t = tris[ti]
    qo = UF.decode_quad_ori(ccell, t["w"], [tuple(u2) for u2 in t["uv"]])
    if qo is None:
        raise ValueError("no window")
    pre_quad[ccell], pre_ori[ccell] = qo
    return qo


def render(wall, top_out, cut_out, kept_out):
    atlas_p = GAME / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / \
        "worldmap" / "textures" / "res(1_24)_terrain.png"
    atlas = Image.open(atlas_p).convert("RGBA")
    AW, AH = atlas.size
    APX = atlas.load()

    def at_b(u2, v2):
        fx = (u2 % 1.0) * AW - 0.5
        fy = (1.0 - v2 % 1.0) * AH - 0.5
        x0, y0 = int(math.floor(fx)), int(math.floor(fy))
        tx, ty = fx - x0, fy - y0
        a4 = [0.0, 0.0, 0.0]
        for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                             (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
            px_, py_ = min(max(x0 + dx, 0), AW - 1), min(max(y0 + dy, 0), AH - 1)
            r, g2, b2, _ = APX[px_, py_]
            a4[0] += r * wg
            a4[1] += g2 * wg
            a4[2] += b2 * wg
        return tuple(int(v) for v in a4)
    LDIR = (-0.5, 0.7, -0.3)
    _l = math.sqrt(sum(q * q for q in LDIR))
    LDIR = tuple(q / _l for q in LDIR)

    def render_strip(items, path, center, bearing, HW=44.0, HH=23.0, SC=12):
        RW, RH = int(2 * HW * SC), int(HH * SC)
        img = Image.new("RGB", (RW, RH), (152, 178, 208))
        zbuf = np.full((RW, RH), -1e9)
        tvec = (-math.sin(bearing), math.cos(bearing))
        for tri, uvt, nrm3 in items:
            pts = []
            for p, u2 in zip(tri, uvt):
                s2 = (p[0] - center[0]) * tvec[0] + (p[2] - center[1]) * tvec[1]
                d2 = (p[0] - center[0]) * math.cos(bearing) + \
                    (p[2] - center[1]) * math.sin(bearing)
                pts.append((s2, p[1], d2, u2))
            if all(p[2] < 0 for p in pts):
                continue
            lams = [max(0.25, float(np.dot(np.array(n2), LDIR)) * 0.6 + 0.55) for n2 in nrm3]
            xs = [int((p[0] + HW) * SC) for p in pts]
            ys = [int((HH - p[1]) * SC) for p in pts]
            if max(xs) < 0 or min(xs) >= RW or max(ys) < 0 or min(ys) >= RH:
                continue
            a2, b2, c2 = (np.array((pts[k][0], pts[k][1])) for k in range(3))
            det = float(np.cross(b2 - a2, c2 - a2))
            if abs(det) < 1e-9:
                continue
            for px_ in range(max(0, min(xs)), min(RW - 1, max(xs)) + 1):
                for py_ in range(max(0, min(ys)), min(RH - 1, max(ys)) + 1):
                    sx = px_ / SC - HW
                    sy = HH - py_ / SC
                    pv2 = np.array((sx, sy))
                    w1 = float(np.cross(b2 - pv2, c2 - pv2)) / det
                    w2 = float(np.cross(c2 - pv2, a2 - pv2)) / det
                    w3 = 1 - w1 - w2
                    if w1 < -1e-6 or w2 < -1e-6 or w3 < -1e-6:
                        continue
                    dep = w1 * pts[0][2] + w2 * pts[1][2] + w3 * pts[2][2]
                    if dep <= zbuf[px_, py_]:
                        continue
                    zbuf[px_, py_] = dep
                    uu = w1 * pts[0][3][0] + w2 * pts[1][3][0] + w3 * pts[2][3][0]
                    vv = w1 * pts[0][3][1] + w2 * pts[1][3][1] + w3 * pts[2][3][1]
                    lam = w1 * lams[0] + w2 * lams[1] + w3 * lams[2]
                    col2 = at_b(uu, vv)
                    img.putpixel((px_, py_), tuple(int(ch * lam) for ch in col2))
        img.save(path)

    items = [([r[0] for r in rec], [r[1] for r in rec], [r[2] for r in rec])
             for rec in wall]
    items += [(t3, uvt, [(0, 1, 0)] * 3) for t3, uvt in top_out]
    items += [(t3, uvt, [(0, 1, 0)] * 3) for t3, uvt, _ in cut_out]
    for t3, uv3, n3, _, _ in kept_out:
        cx = float(np.mean([p[0] for p in t3]))
        cz = float(np.mean([p[2] for p in t3]))
        if math.hypot(cx - CENTER[0], cz - CENTER[1]) < 52.0:
            items.append((t3, [tuple(u2) for u2 in uv3], n3))
    for name, bearing in (("E", 0.0), ("N", math.pi / 2), ("W", math.pi),
                          ("S", -math.pi / 2)):
        render_strip(items, OUTD / f"face_{name}.png", CENTER, bearing)

    # top-down plan (highest surface wins) -- the seam/wing forensics view
    HW2, SC2 = 52.0, 9
    RW2 = int(2 * HW2 * SC2)
    img2 = Image.new("RGB", (RW2, RW2), (60, 70, 90))
    ybuf = np.full((RW2, RW2), -1e9)
    for tri, uvt, nrm3 in items:
        xs = [int((p[0] - CENTER[0] + HW2) * SC2) for p in tri]
        zs = [int((p[2] - CENTER[1] + HW2) * SC2) for p in tri]
        if max(xs) < 0 or min(xs) >= RW2 or max(zs) < 0 or min(zs) >= RW2:
            continue
        a2 = np.array((tri[0][0], tri[0][2]))
        b2 = np.array((tri[1][0], tri[1][2]))
        c2 = np.array((tri[2][0], tri[2][2]))
        det = float(np.cross(b2 - a2, c2 - a2))
        if abs(det) < 1e-9:
            continue
        for px_ in range(max(0, min(xs)), min(RW2 - 1, max(xs)) + 1):
            for pz_ in range(max(0, min(zs)), min(RW2 - 1, max(zs)) + 1):
                wx = px_ / SC2 - HW2 + CENTER[0]
                wz = pz_ / SC2 - HW2 + CENTER[1]
                pv2 = np.array((wx, wz))
                w1 = float(np.cross(b2 - pv2, c2 - pv2)) / det
                w2 = float(np.cross(c2 - pv2, a2 - pv2)) / det
                w3 = 1 - w1 - w2
                if w1 < -1e-6 or w2 < -1e-6 or w3 < -1e-6:
                    continue
                yy = w1 * tri[0][1] + w2 * tri[1][1] + w3 * tri[2][1]
                if yy <= ybuf[px_, pz_]:
                    continue
                ybuf[px_, pz_] = yy
                uu = w1 * uvt[0][0] + w2 * uvt[1][0] + w3 * uvt[2][0]
                vv = w1 * uvt[0][1] + w2 * uvt[1][1] + w3 * uvt[2][1]
                img2.putpixel((px_, pz_), at_b(uu, vv))
    img2.save(OUTD / "plan.png")
    print(f"renders -> {OUTD}")


if __name__ == "__main__":
    sys.exit(main())
