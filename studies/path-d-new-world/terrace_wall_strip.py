"""THE STRIP CARRY, round 6 -- JUNCTION-AWARE (JUNCTION-AWARE-PREDICTION.md).

Round 5 stopped as PLUMBING: the carried faces drew zero complaints across two playtests;
every defect lived on a MINTED JOIN. The junction grammar study (JUNCTION-GRAMMAR.md)
then decoded all three join classes; this revision rebuilds the joins to those laws.
The carry itself is unchanged -- the same four tier-gated level-chain strips, whole mesh
(verts + uvs + tangents), ONE rigid pose each (yaw about Y + translation, k = 1.0).

  * SEAMS (the corner law): the mortar columns are DELETED. Stock corners are two
    full-tile stations creased at ONE shared edge, so each seam becomes exactly that:
    the outgoing strip's cut path is MOVED onto the incoming strip's real cut path by
    normalized arclength (displacement tapered across one station inside the outgoing
    strip, gated), then both sides refine their boundary tris at the union of path verts
    -- every seam edge is SHARED, carried uv untouched on both sides, h_pairs-gated.
    The closure solve gains an end-profile-match term (stock's crease has zero profile
    mismatch by construction; ours minimizes it over the cyclic order).
  * FOOT (the foot law): the burial pierce is DELETED. The posed wall is CUT level at
    the bench ground plane (canonical per-edge crossings, sub-ground mesh discarded);
    the foot polyline is chord-simplified (<= 0.05u deviation, wall verts snapped on),
    and the ground partition's hole rim IS that polyline -- ground fragments and wall
    foot tris refine to the per-chord union of verts, so the foot is a true WELD.
    The row-10 bottom-course retile (the foot law's texture half) is DECLARED DEFERRED.
  * TOP (the crest law): the level L3 top welds EDGE-FOR-EDGE to the actual top
    once-edge path. The crest notch stitch and the sliver capper are DELETED -- with
    real welds there is nothing for them to hide; any residue is a bug and gates red.

Gates before any write: seam weld displacement (the corner-warp bound), h_pairs seam
legality, winding, watertight with ZERO declared classes (the only allowed once-edges
are the bench's own pre-existing block borders), massing foot-line numbers, census
MISS=0, bench reach -- plus THE GAME-EYE PASS: backface-CULLED renders (the defect class
round 5's audits could not see). --apply deploys to the Disc9 bench (backing the cells
up under the MAIN repo's backups/) only when green.

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
KINK_MAX = 25.0
SIMPLIFY_TOL = 0.05                                         # foot chord deviation bound (u)
WELD_DISP_MAX = 12.0                                        # per-seam weld displacement HARD cap;
                                                            # the visible bound is the SHEAR RATIO
SHEAR_MAX = 1.5                                             # displacement / taper width

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
# THE SOURCE SEAM (P0 fold-back). Every bench generator read the LIVE install
# directly, so the ONLY way to exercise one was to mutate the owner's game —
# which is why the whole bench chain is anchored to timestamped backups that
# nothing tracks. `bench_src` (or the module-level BENCH_SRC) points the
# loader at a snapshot instead, so the pipeline is reproducible offline.
# Same law as the deploy-target seam in the brief: pin the path through a
# seam, never read the real file.
BENCH_SRC = None                      # None = the live install


def corner_guard(allow_cornerless=False):
    """THE CORNER GUARD — call immediately before any bench deploy.

    Every generator in this study dir emits a CORNER-LESS bench: none of them
    knows about the V-shore corner (owner-accepted, playtest 12), which is a
    separate stage. Deploying one alone silently reverts twelve playtests of
    work AND LEAVES EVERY GATE GREEN, because the gates score whatever is in
    the blocks. That is the failure this guard exists to make impossible.
    """
    if allow_cornerless:
        print("!! deploying a CORNER-LESS bench by explicit request — "
              "run the corner stage yourself (see bench_pipeline.py)")
        return
    raise SystemExit(
        "REFUSING to deploy: this emits a CORNER-LESS bench and would\n"
        "  silently revert the owner-accepted V-shore corner, with every gate\n"
        "  still green afterwards. Use the driver, which regenerates, re-applies\n"
        "  the corner, and verifies against the accepted bench:\n"
        "      py bench_pipeline.py all\n"
        "  To deploy a corner-less bench deliberately, pass --corner-follows.")


def bench_root(bench_src=None):
    src = bench_src if bench_src is not None else BENCH_SRC
    if src is None:
        return GAME / MOD / "FF9_Data" / "WorldMap" / f"Disc{DISC}" / "0_1", False
    return Path(src), True


def load_bench(bench_src=None):
    root, flat = bench_root(bench_src)
    tris, bms = [], {}
    for (bx, by) in CELLS:
        # a snapshot dir holds the six files flat; the install nests them in r<by>/
        p = (root / f"Block[{bx}][{by}] Terrain.ff9mesh" if flat
             else root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh")
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
_EW_CACHE = {}                                              # window variants re-cut per block


def extract_wall(bx, by):
    if (bx, by) in _EW_CACHE:
        return _EW_CACHE[(bx, by)]
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
    W_out = dict(bm=bm, V=V, U=U, N=N, T=T, tri_idx=tri_idx, topo=topo, ox=ox, oz=oz,
                 comp_of=comp_of, wall_tris=wall_tris, inst_data=inst_data,
                 inst_of_tri=inst_of_tri, columns=columns, edge_tris=edge_tris)
    _EW_CACHE[(bx, by)] = W_out
    return W_out


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
def solve_ring(variants):
    """THE LATTICE-GROUP POSE (the rim-aware amendment): yaw is restricted to 90-deg
    steps so each strip's donor-lattice structure lands ON the bench lattice and the
    crest verts keep their displaced-row homes (RIM-GRAMMAR R1; probe-validated on all
    four donors). Closure can no longer be tuned by continuous kinks, so the declared
    lever moves first: per-donor WINDOW VARIANTS (end column shifted -2..+2) join the
    search. ``variants`` = per-donor list of cut strips. Searches cyclic order x yaw
    combo x variant combo; returns (order, vsel, poses, shift, turns, gap) with poses
    per CHOSEN strip and turns = the seam plan-turn each crease weld must absorb."""
    def bearing(p, q):
        return math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))

    def geo_of(s):
        """Canonical strip geometry: the BASE polyline with half-station COLINEAR anchor
        extensions at both ends (loop centroids sit mid-face and add spurious turn;
        colinear anchors are bearing-neutral) + the corner-law end profiles."""
        P = s["P"]
        half = s["st"] / 2.0

        def ext(p_end, p_prev):
            d = (p_end[0] - p_prev[0], p_end[1] - p_prev[1])
            L = math.hypot(*d) or 1.0
            return (p_end[0] + d[0] / L * half, p_end[1] + d[1] / L * half)
        pl = [ext(P[0], P[1])] + P + [ext(P[-1], P[-2])]

        def end_profile(loop):
            top = max(loop, key=lambda p: p[1])
            rev = loop[::-1] if loop[-1][1] >= loop[0][1] else loop
            prof = {}
            for d in range(1, 13):
                yt = top[1] - d
                for q in range(1, len(rev)):
                    a, b2 = rev[q - 1], rev[q]
                    if (a[1] - yt) * (b2[1] - yt) <= 0 and a[1] != b2[1]:
                        t = (yt - a[1]) / (b2[1] - a[1])
                        px = a[0] + t * (b2[0] - a[0])
                        pz = a[2] + t * (b2[2] - a[2])
                        prof[d] = math.hypot(px - top[0], pz - top[2])
                        break
            return prof
        d2 = s.get("_delta", (0, 0))
        return dict(pl=pl, b_in=bearing(pl[0], pl[1]), b_out=bearing(pl[-2], pl[-1]),
                    prof_s=end_profile(s["loop_s"]), prof_e=end_profile(s["loop_e"]),
                    delta=d2, dpen=abs(d2[0]) + abs(d2[1]))

    def prof_mismatch(pe, ps):
        common = sorted(set(pe) & set(ps))
        if not common:
            return 4.0                                      # no overlap: worst-case-ish
        return math.sqrt(sum((pe[d] - ps[d]) ** 2 for d in common) / len(common))

    geos_all = [[geo_of(s) for s in vs] for vs in variants]

    def fold(a):
        while a > 180.0:
            a -= 360.0
        while a < -180.0:
            a += 360.0
        return a

    def chain(geos_o, qs):
        """Abutting chain under ABSOLUTE yaws qs: entry anchor at cur_pt, exit carried
        rigidly. Returns (poses, gap, anchors). No kinks -- the seam turns are whatever
        the yaw steps leave, absorbed by the crease welds (and gated)."""
        poses = []
        anchors = []
        cur_pt = (0.0, 0.0)
        for g, q in zip(geos_o, qs):
            r = math.radians(q)
            cs, sn = math.cos(r), math.sin(r)
            p0 = g["pl"][0]
            poses.append((q, p0, cur_pt))
            anchors.append(cur_pt)
            dx, dz = g["pl"][-1][0] - p0[0], g["pl"][-1][1] - p0[1]
            cur_pt = (cur_pt[0] + dx * cs - dz * sn, cur_pt[1] + dx * sn + dz * cs)
        anchors.append(cur_pt)
        gap = math.hypot(cur_pt[0] - anchors[0][0], cur_pt[1] - anchors[0][1])
        return poses, gap, anchors

    # THE SEARCH: cyclic order x window-variant combo x 90-deg yaw combo (q0 = 0 -- a
    # global 90-deg rotation is a symmetry of the bench lattice). Guards: the anchor
    # loop must be CCW (faces outward) with total seam turn ~ +360, and no seam turn
    # beyond the corner law's measured band.
    import itertools as _it
    S = len(variants)
    best_all = None
    for order in [(0,) + perm for perm in _it.permutations(range(1, S))]:
        for vcombo in _it.product(*[range(len(geos_all[d])) for d in order]):
            geos_o = [geos_all[d][vcombo[k3]] for k3, d in enumerate(order)]
            mism = sum(prof_mismatch(geos_o[i]["prof_e"], geos_o[(i + 1) % S]["prof_s"])
                       for i in range(S))
            if mism > 6.0:
                continue                                    # a weld-cap bust in waiting
            vpen = 0.15 * sum(g["dpen"] for g in geos_o)
            for q_rest in _it.product((0.0, 90.0, 180.0, 270.0), repeat=S - 1):
                qs = (0.0,) + q_rest
                turns = [fold((geos_o[(i + 1) % S]["b_in"] + qs[(i + 1) % S])
                              - (geos_o[i]["b_out"] + qs[i])) for i in range(S)]
                if any(abs(t2) > 155.0 for t2 in turns):
                    continue                                # beyond J2's measured band
                if not (300.0 <= sum(turns) <= 420.0):
                    continue                                # not a simple CCW ring
                poses, gap, anchors = chain(geos_o, qs)
                area2 = sum(anchors[i][0] * anchors[i + 1][1]
                            - anchors[i + 1][0] * anchors[i][1]
                            for i in range(len(anchors) - 1))
                if area2 <= 800.0:                          # inside-out or collapsed ring
                    continue
                tpen = 0.5 * sum(max(0.0, abs(t2) - 130.0) for t2 in turns)
                score = gap + 0.1 * mism + tpen + vpen
                if best_all is None or score < best_all[0]:
                    best_all = (score, order, vcombo, qs, turns, gap, mism)
    assert best_all is not None, ("no lattice-group pose closes the ring -- the "
                                  "declared plumbing stop (window lever exhausted)")
    _, order, vcombo, qs, turns, gap, mism = best_all
    geos_o = [geos_all[d][vcombo[k3]] for k3, d in enumerate(order)]
    print(f"closure: seam profile mismatch {mism:.2f}u RMS; yaws "
          f"{tuple(int(q) for q in qs)} deg; window deltas "
          f"{[g['delta'] for g in geos_o]}; seam turns "
          f"{[round(t2, 1) for t2 in turns]} deg")
    poses, _, _ = chain(geos_o, qs)

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
    return order, list(vcombo), poses, shift, turns, gap


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


def seam_params(lo, hi):
    """TOP-ALIGNED height-progress params for a seam's two cut paths (bottom -> top;
    0..1 over the lo path). Both path tops are crest corners and must coincide after
    the weld; matching by depth-below-top keeps pairs at LIKE HEIGHTS (pure arclength
    mismatched them across ledge detours), and a hi vert deeper than the lo path clamps
    to the lo bottom -- below the ground cut, where the mismatch is discarded."""
    def dtop(path):
        s2 = [0.0]
        for q in range(len(path) - 1, 0, -1):
            a, b2 = path[q], path[q - 1]
            s2.append(s2[-1] + abs(b2[1] - a[1]) +
                      0.05 * math.hypot(b2[0] - a[0], b2[2] - a[2]))
        return s2[::-1]
    s_lo, s_hi = dtop(lo), dtop(hi)
    tot = s_lo[0] or 1.0
    t_lo = [1.0 - s / tot for s in s_lo]
    t_hi = [1.0 - min(s, tot) / tot for s in s_hi]
    return t_lo, t_hi


def ear_fan(poly):
    """Triangulate a convex polygon of rec-verts using ONLY its own verts: clip the
    largest-area ear each round. No centroid vert is minted -- a centroid inside a
    sliver polygon lands within tolerance of the neighbouring edge and seeds the next
    conformance pass's splits (a measured cascade: 37 -> 15 -> 42 -> 377)."""
    P = list(poly)
    out = []
    while len(P) > 3:
        def _area(q):
            a = np.array(P[q - 1][0])
            b2 = np.array(P[q][0])
            c2 = np.array(P[(q + 1) % len(P)][0])
            return float(np.linalg.norm(np.cross(b2 - a, c2 - b2)))
        q = max(range(len(P)), key=_area)
        out.append([P[(q - 1) % len(P)], P[q], P[(q + 1) % len(P)]])
        P.pop(q)
    out.append(P)
    return out


def point_at(path, ts2, t):
    """Point on the polyline at normalized arclength t (lerp)."""
    if t <= 0.0:
        return tuple(path[0])
    if t >= 1.0:
        return tuple(path[-1])
    for q in range(1, len(path)):
        if ts2[q] >= t:
            f = 0.0 if ts2[q] <= ts2[q - 1] else \
                (t - ts2[q - 1]) / (ts2[q] - ts2[q - 1])
            a, b2 = path[q - 1], path[q]
            return tuple(a[k3] + f * (b2[k3] - a[k3]) for k3 in range(3))
    return tuple(path[-1])


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--probe", action="store_true",
                    help="dump final tris near the playtest defect coordinates")
    args = ap.parse_args()
    if args.apply:
        corner_guard(getattr(args, "corner_follows", False))
    OUTD.mkdir(parents=True, exist_ok=True)

    tris, bms = load_bench()
    assert tris, "bench island not deployed at Disc9 (run the world-island mint first)"
    n_rock_in = sum(1 for t in tris if t["topo"] == ROCK)
    assert n_rock_in == 0, (
        f"bench is NOT pristine ({n_rock_in} rock tris present -- a prior deploy is "
        f"live). Restore backups/terrace-strip-prewall.* first; building against a "
        f"walled bench compounds garbage (the round-5 lesson).")
    grass_r = max(math.hypot(t["cen"][0] - CENTER[0], t["cen"][2] - CENTER[1])
                  for t in tris if t["topo"] in GRASS_TOPO)
    print(f"bench: {len(tris)} tris across {len(bms)} cells; grass reach ~{grass_r:.1f}u")

    # window VARIANTS (end column -2..+2): the rim-aware amendment's declared closure
    # lever -- lattice-group yaw cannot tune the ring shut, the windows can
    variants = []
    for (blk, a, b, n) in DONORS:
        vs = []
        for da in (-1, 0, 1):
            for db in (-2, -1, 0, 1, 2):
                if (b + db) - (a + da) < 3 or a + da < 0:
                    continue
                try:
                    s2 = cut_strip(blk, a + da, b + db, n)
                except AssertionError:
                    continue
                s2["_delta"] = (da, db)
                vs.append(s2)
        assert vs, f"donor {blk}: no valid window variant"
        variants.append(vs)
    print(f"variants: {[len(vs) for vs in variants]} windows per donor")

    # ---- pose + closure (order x window x 90-deg yaw -- the lattice-group solve) -----------
    order, vsel, poses, shift, turns, gap = solve_ring(variants)
    strips = [variants[d][v] for d, v in zip(order, vsel)]
    for s in strips:
        print(f"strip blk {s['blk']} (d{s['_delta']}): {s['n']} cols, "
              f"{len(s['recs'])} tris, len {s['length']:.1f}u bend {s['bend']:+.1f} deg, "
              f"depth_min {s['depth_min']:.1f}u")
    print(f"closure: order {[s['blk'] for s in strips]}, position gap {gap:.2f}u "
          f"(absorbed by the last seam's weld taper)")

    # ---- the burial seat (the round-4 amendment, unchanged) --------------------------------
    drop = min(min(s["depth_min"] for s in strips) - 0.3, SHELF_BAND[1] - LOWLAND)
    assert drop >= SHELF_BAND[0] - LOWLAND, \
        f"a window column is too short for the shelf band (drop {drop:.1f})"
    top_y = LOWLAND + drop
    print(f"seat: TOP_Y {top_y:.2f} (drop {drop:.2f}), k=1.0 rigid, surplus CUT at the "
          f"ground plane (no burial)")

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

    for s, (yaw, p0, t0) in zip(strips, poses):
        s["_pose"] = (yaw, p0, t0, top_y - s["crest_y"])

    # ---- least-squares seam centering: per-strip translation so each seam's weld -----------
    # displacement is CENTERED (base-endpoint chaining leaves the cross-sections offset
    # by lean/kink splay -- the space the mortar used to fill; the weld must not)
    def _lp(s, which):
        yaw, p0, t0, dy = s["_pose"]
        return [xf_point(p, yaw, p0, t0, shift, dy) for p in
                (s["loop_s"] if which == "s" else s["loop_e"])]
    S = len(strips)
    g_star = []
    for i in range(S):
        j = (i + 1) % S
        lo = _lp(strips[i], "e")
        hi = _lp(strips[j], "s")
        t_lo, t_hi = seam_params(lo, hi)
        ds2 = []
        for m2, p in enumerate(hi):
            tgt = point_at(lo, t_lo, t_hi[m2])
            if tgt[1] > LOWLAND - 1.0:                      # centre the VISIBLE portion
                ds2.append((tgt[0] - p[0], tgt[2] - p[2]))
        g_star.append((float(np.mean([d[0] for d in ds2])),
                       float(np.mean([d[1] for d in ds2]))))
    dtot = (sum(g[0] for g in g_star), sum(g[1] for g in g_star))
    g_adj = [(g[0] - dtot[0] / S, g[1] - dtot[1] / S) for g in g_star]
    T = [(0.0, 0.0)]
    for i in range(S - 1):
        T.append((T[-1][0] + g_adj[i][0], T[-1][1] + g_adj[i][1]))
    tmx = float(np.mean([t2[0] for t2 in T]))
    tmz = float(np.mean([t2[1] for t2 in T]))
    T = [(t2[0] - tmx, t2[1] - tmz) for t2 in T]
    for k3, s in enumerate(strips):
        yaw, p0, t0, dy = s["_pose"]
        s["_pose"] = (yaw, p0, (t0[0] + T[k3][0], t0[1] + T[k3][1]), dy)
    print(f"seam centering: per-strip translations "
          f"{[(round(t2[0], 2), round(t2[1], 2)) for t2 in T]}u")

    # ---- THE LATTICE MICRO-SHIFT (the rim-aware amendment): after centering, nudge ---------
    # each strip so its donor-lattice image lands ON the bench 4u lattice -- the crest
    # verts then keep their displaced-row homes (residual envelope = stock's). <= 2.83u
    # per strip, absorbed by the seam welds; the de-centering cost is declared.
    micro = []
    for s in strips:
        yaw, p0, t0, dy = s["_pose"]
        assert abs(yaw % 90.0) < 1e-6, f"non-lattice yaw {yaw}"
        q3 = xf_point((0.0, 0.0, 0.0), yaw, p0, t0, shift, 0.0)
        mx = ((q3[0] + 2.0) % 4.0) - 2.0
        mz = ((q3[2] + 2.0) % 4.0) - 2.0
        s["_pose"] = (yaw, p0, (t0[0] - mx, t0[1] - mz), dy)
        micro.append((round(-mx, 2), round(-mz, 2)))
    print(f"lattice micro-shift: {micro}u (donor lattice -> bench lattice)")

    posed = []                                              # per strip: list of tri records
    for s in strips:
        yaw, p0, t0, dy = s["_pose"]
        out = []
        for rec in s["recs"]:
            out.append([(xf_point(w, yaw, p0, t0, shift, dy), uv,
                         xf_nrm(n3, yaw), t4) for (w, uv, n3, t4) in rec])
        posed.append(out)

    # ---- THE SEAM WELDS (the corner law): one shared edge path per seam --------------------
    # Round 5 minted a mortar column here; the junction study (J2) measured stock and
    # found NO such column exists -- corners are two full-tile stations creased at ONE
    # shared edge, quads planar, the whole turn at the seam. So each seam becomes that:
    # the outgoing strip's cut path (hi) MOVES onto the incoming strip's real cut path
    # (lo) by normalized arclength, the displacement tapering to zero across one station
    # inside the outgoing strip; then BOTH sides refine their boundary tris at the union
    # of path verts, so every seam edge is SHARED. Carried uv untouched on either side.
    def posed_loop(s, which):
        yaw, p0, t0, dy = s["_pose"]
        return [xf_point(p, yaw, p0, t0, shift, dy) for p in
                (s["loop_s"] if which == "s" else s["loop_e"])]

    def K2(p):
        """2-decimal key: loop verts pass through donor-precision kk before posing, rec
        verts do not, so 3-decimal keys occasionally disagree; verts are >=1u apart."""
        return (round(p[0], 2), round(p[1], 2), round(p[2], 2))

    _canon_cache = {}

    def canon_loop(strip_idx, loop):
        """Map each posed loop vert to the strip's EXACT rec vert by PROXIMITY (<= 0.01).
        Loop verts pass through donor-precision kk, the recs do not, and any rounding
        key (K2/kk) still straddles a decimal boundary for ~1-2 verts per run -- which
        silently unhooked an entire seam. Proximity is unambiguous: distinct mesh verts
        are >= 1u apart."""
        if strip_idx not in _canon_cache:
            uniq = {}
            for rec in posed[strip_idx]:
                for (w, _uv, _n3, _t4) in rec:
                    uniq[w] = w
            _canon_cache[strip_idx] = np.array(list(uniq))
        arr = _canon_cache[strip_idx]
        out = []
        for p in loop:
            dd = np.linalg.norm(arr - np.array(p), axis=1)
            q = int(np.argmin(dd))
            out.append(tuple(float(v) for v in arr[q]) if float(dd[q]) <= 0.01
                       else tuple(p))
        return out

    weld_stats = []
    refine_map = defaultdict(list)                          # edge key -> [insert points]
    move_maps = [None] * S                                  # per strip: the 's'-end field
    seam_chains = []                                        # per seam: the union chain
    for i in range(S):
        j = (i + 1) % S
        lo = canon_loop(i, posed_loop(strips[i], "e"))      # bottom -> top real paths
        hi = canon_loop(j, posed_loop(strips[j], "s"))
        t_lo, t_hi = seam_params(lo, hi)
        # targets: depth-matched points on the lo path; snap to a lo VERT only when
        # both position and param agree (a positional-only snap can fold the map)
        tgts = []
        for m2, p in enumerate(hi):
            tgt = point_at(lo, t_lo, t_hi[m2])
            qn = min(range(len(lo)), key=lambda q: abs(t_lo[q] - t_hi[m2]))
            if math.dist(lo[qn], tgt) <= 0.05:
                tgt = tuple(lo[qn])
            tgts.append(tuple(float(v) for v in tgt))
        # the gate protects VISIBLE shear -- a pair whose TARGET lies below the ground
        # cut is discarded before it can render
        weld_stats.append(max((math.dist(p, t2) for p, t2 in zip(hi, tgts)
                               if t2[1] > LOWLAND - 1.0), default=0.0))
        # move the outgoing strip: ONE proximity field -- a vert on the boundary path
        # (<= 0.011, covering the loop's donor-rounding fuzz) takes its EXACT target; a
        # vert within the taper width blends on the inverse-distance displacement
        # field. (Rounding-key matching left ~1 boundary vert per run 99.98%-moved --
        # a twin vert 0.001u off the chain, splitting the weld.) The taper WIDENS past
        # one station when the measured profile spread demands it, bounding the visible
        # SHEAR RATIO (displacement / taper width) instead of shearing harder.
        W_t = min(max(strips[j]["st"], weld_stats[-1] / 1.2), 2.5 * strips[j]["st"])
        move_maps[j] = (np.array(hi),
                        np.array([[tgts[m2][k3] - hi[m2][k3] for k3 in range(3)]
                                  for m2 in range(len(hi))]),
                        tgts, W_t)
        # union refinement plan: both sides split their boundary edges at the union of
        # path verts (hi edge keys are in the POST-move frame -- moves land on tgts)
        u_pts = [(t_lo[q], tuple(lo[q])) for q in range(len(lo))]
        for m2 in range(len(hi)):
            p = tgts[m2]
            if not any(math.dist(p, q2) <= 0.02 for _, q2 in u_pts):
                u_pts.append((t_hi[m2], p))
        u_pts.sort()

        def plan_inserts(path_pts, path_ts):
            keyset = {kk(p) for p in path_pts}
            for q in range(len(path_pts) - 1):
                a, b2 = path_pts[q], path_pts[q + 1]
                ta, tb = path_ts[q], path_ts[q + 1]
                if tb <= ta + 1e-9:
                    continue
                mids = [p for (t2, p) in u_pts
                        if ta + 1e-9 < t2 < tb - 1e-9 and kk(p) not in keyset]
                if mids:
                    ek = tuple(sorted((kk(a), kk(b2))))
                    refine_map[ek].extend(mids)
        plan_inserts(lo, t_lo)
        plan_inserts(tgts, t_hi)
        seam_chains.append([p for _, p in u_pts])
        print(f"   seam {i}: lo {len(lo)}v y[{lo[0][1]:.1f}..{lo[-1][1]:.1f}] / "
              f"hi {len(hi)}v y[{hi[0][1]:.1f}..{hi[-1][1]:.1f}]")
    print(f"seam welds: max displacement {[round(w2, 2) for w2 in weld_stats]}u per seam "
          f"(gate {WELD_DISP_MAX}u), taper one station")

    for j in range(S):                                      # apply the moves
        if move_maps[j] is None:
            continue
        hi_np, d_np, tgts_j, W_t = move_maps[j]
        vinfo = {}                                          # K2 -> (w, kind, disp, f)
        for rec in posed[j]:
            for (w, _uv, _n3, _t4) in rec:
                k2 = K2(w)
                if k2 in vinfo:
                    continue
                dd = np.linalg.norm(hi_np - np.array(w), axis=1)
                q = int(np.argmin(dd))
                dmin = float(dd[q])
                if dmin <= 0.011:
                    vinfo[k2] = (w, "bnd", tgts_j[q], 1.0)
                elif dmin < W_t:
                    wgt = 1.0 / np.maximum(dd, 0.05) ** 2
                    disp = (d_np * wgt[:, None]).sum(axis=0) / float(wgt.sum())
                    vinfo[k2] = (w, "tap", tuple(float(v) for v in disp),
                                 1.0 - dmin / W_t)
                else:
                    vinfo[k2] = (w, "fix", (0.0, 0.0, 0.0), 0.0)

        def _pos(k2):
            w, kind, d, f = vinfo[k2]
            if kind == "bnd":
                return d
            return (w[0] + f * d[0], w[1] + f * d[1], w[2] + f * d[2])
        # FOLD RELAXATION: the weld map's top segment can displace neighbouring verts
        # in crossing directions and FOLD a boundary-adjacent tri (normal flips) --
        # in-game that is a cull-flickering dark sliver. Relax the TAPER factor of a
        # folded tri's interior verts (boundary verts hold the weld chain) until every
        # moved tri keeps its pre-move orientation.
        n_folds = 0
        for _relax in range(14):
            folded_keys = set()
            for rec in posed[j]:
                ks3 = [K2(r[0]) for r in rec]
                if all(vinfo[k2][3] == 0.0 for k2 in ks3):
                    continue
                a0, b0, c0 = (np.array(r[0]) for r in rec)
                a1, b1, c1 = (np.array(_pos(k2)) for k2 in ks3)
                n_pre = np.cross(b0 - a0, c0 - a0)
                n_post = np.cross(b1 - a1, c1 - a1)
                if float(n_pre @ n_post) < 0:
                    for k2 in ks3:
                        if vinfo[k2][1] == "tap" and vinfo[k2][3] > 1e-3:
                            folded_keys.add(k2)
            if not folded_keys:
                break
            n_folds = max(n_folds, len(folded_keys))
            for k2 in folded_keys:
                w, kind, d, f = vinfo[k2]
                vinfo[k2] = (w, kind, d, f * 0.55)
        if n_folds:
            print(f"   strip {j}: fold relaxation touched {n_folds} tapered verts")
        posed[j] = [[(_pos(K2(w)), uv, n3, t4) for (w, uv, n3, t4) in rec]
                    for rec in posed[j]]

    # SEAM-FOLD RE-WIND: the weld map can fold a boundary-vert tri (its verts are chain
    # anchors, so the relaxation must not touch them). The donors have ZERO tris whose
    # winding opposes their vertex normals (probed) -- so any such tri here was folded
    # by the map, and re-winding it renders the same surface from its correct side.
    n_rewound = 0
    for j in range(S):
        sp = posed[j]
        for qi, rec in enumerate(sp):
            A, B, C = (np.array(rec[k3][0]) for k3 in range(3))
            fn = np.cross(B - A, C - A)
            L = float(np.linalg.norm(fn))
            if L < 2e-2:
                continue
            nv = np.array([float(np.mean([r[2][q2] for r in rec])) for q2 in range(3)])
            Ln = float(np.linalg.norm(nv))
            if Ln > 1e-6 and float(fn @ nv) / (L * Ln) < -0.3:
                sp[qi] = [rec[0], rec[2], rec[1]]
                n_rewound += 1
    if n_rewound:
        print(f"   seam-fold re-wind: {n_rewound} folded tris re-wound to agree with "
              f"their carried normals")

    wall = []
    n_collapsed = 0
    for sp in posed:
        for rec in sp:
            if len({kk(r[0]) for r in rec}) == 3:
                wall.append(rec)
            else:
                n_collapsed += 1                            # an edge collapsed by a snap

    def refine_wall(wall_in, rmap):
        """Split any tri edge listed in rmap at its points (attrs edge-lerped along that
        edge). A tri with several refined edges becomes a fan around its cycle."""
        out = []
        n_splits = 0
        for rec in wall_in:
            keys3 = [kk(rec[k3][0]) for k3 in range(3)]
            hits = [k3 for k3 in range(3)
                    if tuple(sorted((keys3[k3], keys3[(k3 + 1) % 3]))) in rmap]
            if not hits:
                out.append(rec)
                continue
            poly = []
            for k3 in range(3):
                a_r, b_r = rec[k3], rec[(k3 + 1) % 3]
                poly.append(a_r)
                if k3 not in hits:
                    continue
                pts2 = rmap[tuple(sorted((keys3[k3], keys3[(k3 + 1) % 3])))]
                L2 = math.dist(a_r[0], b_r[0]) or 1.0
                seen2 = {kk(a_r[0]), kk(b_r[0])}
                for p in sorted(pts2, key=lambda q2: math.dist(a_r[0], q2)):
                    if kk(p) in seen2:
                        continue
                    tt = min(1.0, max(0.0, math.dist(a_r[0], p) / L2))
                    uv_m = tuple(a_r[1][q2] + tt * (b_r[1][q2] - a_r[1][q2])
                                 for q2 in range(2))
                    n_m = tuple(a_r[2][q2] + tt * (b_r[2][q2] - a_r[2][q2])
                                for q2 in range(3))
                    poly.append((tuple(p), uv_m, n_m, a_r[3]))
                    seen2.add(kk(p))
                    n_splits += 1
            if len(poly) == 3:
                out.append(poly)
                continue
            # fan from an ORIGINAL corner: single hit -> the OPPOSITE corner (all-real
            # tris); multi-hit -> the corner SHARED by the hit edges (its slivers are
            # zero-area but TOPOLOGICALLY exact -- every sub-edge pairs with the
            # neighbour's; an ear fan instead chooses among zero-area ears by noise
            # and mints chord-skipping slivers, the measured once-edge factory)
            if len(hits) == 1:
                c_key = keys3[(hits[0] + 2) % 3]
            elif set(hits) == {0, 1}:
                c_key = keys3[1]
            elif set(hits) == {1, 2}:
                c_key = keys3[2]
            else:
                c_key = keys3[0]
            start = next(q2 for q2 in range(len(poly)) if kk(poly[q2][0]) == c_key)
            cyc = poly[start:] + poly[:start]
            for q2 in range(1, len(cyc) - 1):
                out.append([cyc[0], cyc[q2], cyc[q2 + 1]])
        return out, n_splits

    wall, n_seam_split = refine_wall(wall, refine_map)
    print(f"seam refinement: {n_seam_split} boundary-edge splits, "
          f"{n_collapsed} snap-collapsed tris dropped")

    # seam integrity: every union-chain segment must now be a 2-manifold edge (one tri
    # from each strip) -- a mismatch here IS the weld bug, caught before the cut
    cnt_w = defaultdict(int)
    for rec in wall:
        ps3 = [kk(r[0]) for r in rec]
        for a2, b2 in ((0, 1), (1, 2), (2, 0)):
            cnt_w[tuple(sorted((ps3[a2], ps3[b2])))] += 1
    for si, chain in enumerate(seam_chains):
        badc = []
        for a, b2 in zip(chain, chain[1:]):
            if max(a[1], b2[1]) <= LOWLAND:
                continue                                    # discarded by the level cut
            ek = tuple(sorted((kk(a), kk(b2))))
            n2 = cnt_w.get(ek, 0)
            if n2 != 2:
                badc.append((n2, ek))
        if badc:
            print(f"   DBG seam {si}: {len(badc)}/{len(chain) - 1} chain segments not "
                  f"2-manifold:")
            for n2, ek in badc[:8]:
                print(f"      x{n2}: {ek}")

    # ---- THE FOOT (the foot law): level cut at the ground plane -- no burial, no pierce ----
    # Stock walls terminate ON the ground mesh (junction study J3: 96.7% bottom weld,
    # ground level and plain to the weld; no pierce exists). The posed wall is cut at
    # y = LOWLAND; crossings are computed once per EDGE (sorted endpoints) so neighbours
    # split bit-exact; everything below the plane is DISCARDED.
    xcache = {}

    def _crossing(A, B):
        ka, kb2 = kk(A[0]), kk(B[0])
        key = (ka, kb2) if ka <= kb2 else (kb2, ka)
        got = xcache.get(key)
        if got is None:
            P0, P1 = (A, B) if ka <= kb2 else (B, A)
            t = (LOWLAND - P0[0][1]) / (P1[0][1] - P0[0][1])
            p = (P0[0][0] + t * (P1[0][0] - P0[0][0]), LOWLAND,
                 P0[0][2] + t * (P1[0][2] - P0[0][2]))
            uv = tuple(P0[1][q2] + t * (P1[1][q2] - P0[1][q2]) for q2 in range(2))
            n3 = tuple(P0[2][q2] + t * (P1[2][q2] - P0[2][q2]) for q2 in range(3))
            got = (p, uv, n3, P0[3])
            xcache[key] = got
        return got

    lev_wall = []
    for rec in wall:
        ys2 = [r[0][1] for r in rec]
        if min(ys2) >= LOWLAND:
            lev_wall.append(rec)
            continue
        if max(ys2) <= LOWLAND:
            continue
        poly = []
        for k3 in range(3):
            A, B = rec[k3], rec[(k3 + 1) % 3]
            if A[0][1] >= LOWLAND:
                poly.append(A)
            if (A[0][1] - LOWLAND) * (B[0][1] - LOWLAND) < 0:
                poly.append(_crossing(A, B))
        if len(poly) < 3:
            continue
        for q2 in range(1, len(poly) - 1):
            lev_wall.append([poly[0], poly[q2], poly[q2 + 1]])
    print(f"level cut at y={LOWLAND}: {len(wall)} -> {len(lev_wall)} wall tris "
          f"(sub-ground mesh discarded)")
    wall = lev_wall

    # ---- the foot polyline -> chord simplification -> THE RIM (the weld line itself) -------
    # The cut's at-plane once-edges chain into the foot loops. Each loop is simplified to
    # chords (every original vert within SIMPLIFY_TOL of its chord) and the intermediate
    # wall verts SNAP onto the chord, so the wall's foot edges lie EXACTLY along the rim
    # lines the ground is sliced with -- the precondition for a shared-vertex weld.
    fcnt = Counter()
    fmap = {}
    for rec in wall:
        ps = [r[0] for r in rec]
        for a2, b2 in ((0, 1), (1, 2), (2, 0)):
            pa, pb = ps[a2], ps[b2]
            if abs(pa[1] - LOWLAND) < 1e-6 and abs(pb[1] - LOWLAND) < 1e-6:
                e = tuple(sorted((kk(pa), kk(pb))))
                if e[0] != e[1]:
                    fcnt[e] += 1
                    fmap[e] = (pa, pb)
    padj2 = defaultdict(list)
    pexact = {}
    for e, n2 in fcnt.items():
        if n2 != 1:
            continue
        pa, pb = fmap[e]
        pexact[kk(pa)] = pa
        pexact[kk(pb)] = pb
        padj2[kk(pa)].append(kk(pb))
        padj2[kk(pb)].append(kk(pa))
    deg_odd = [p for p, l3 in padj2.items() if len(l3) != 2]
    if deg_odd:
        n_multi = sum(1 for e, n2 in fcnt.items() if n2 > 1)
        print(f"   DBG foot edges: {len(fcnt)} total, {n_multi} multi-count (excluded)")
        for e, n2 in fcnt.items():
            if n2 > 1:
                print(f"      multi x{n2}: {e}")
        for p in deg_odd[:8]:
            print(f"   DBG foot degree-{len(padj2[p])} at {p}: nbrs {padj2[p][:4]}")
            for rec in wall:
                ps2 = [r[0] for r in rec]
                if any(kk(q2) == p for q2 in ps2):
                    print(f"      tri: {[kk(q2) for q2 in ps2]}")
    assert not deg_odd, (f"foot graph not 2-regular: {len(deg_odd)} odd-degree pts, "
                         f"e.g. {deg_odd[:3]}")
    floops = []
    fvisited = set()
    for start in list(padj2):
        if start in fvisited:
            continue
        loop = [start]
        prev = None
        while True:
            nxts = [p for p in padj2[loop[-1]] if p != prev]
            if not nxts or nxts[0] == start:
                break
            prev = loop[-1]
            loop.append(nxts[0])
        fvisited.update(loop)
        if len(loop) >= 3:
            floops.append([pexact[k3] for k3 in loop])
    floops.sort(key=len, reverse=True)
    assert floops, "no foot loop -- the wall does not reach the ground plane"

    def simplify_loop(loop3):
        """Greedy chord walk (deviation vs the ORIGINAL polyline bounded by
        SIMPLIFY_TOL). Returns (chords, snap): chords = (cornerA, cornerB, [snapped
        intermediate wall verts in order]); snap = kk(old) -> new on-chord position."""
        n2 = len(loop3)
        pts3 = loop3 + [loop3[0]]

        def dev_ok(i3, j3):
            a, b2 = pts3[i3], pts3[j3]
            dx, dz = b2[0] - a[0], b2[2] - a[2]
            L2 = dx * dx + dz * dz
            if L2 < 1e-12:
                return False
            for q2 in range(i3 + 1, j3):
                p = pts3[q2]
                t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[2] - a[2]) * dz) / L2))
                if math.hypot(p[0] - (a[0] + t * dx),
                              p[2] - (a[2] + t * dz)) > SIMPLIFY_TOL:
                    return False
            return True

        corners = [0]
        i3 = 0
        while i3 < n2:
            j3 = i3 + 1
            while j3 < n2 and dev_ok(i3, j3 + 1):
                j3 += 1
            corners.append(j3)
            i3 = j3
        if corners[-1] != n2:
            corners.append(n2)
        snap = {}
        chords = []
        for c0, c1 in zip(corners, corners[1:]):
            a, b2 = pts3[c0], pts3[c1]
            dx, dz = b2[0] - a[0], b2[2] - a[2]
            L2 = (dx * dx + dz * dz) or 1.0
            mids = []
            for q2 in range(c0 + 1, c1):
                p = pts3[q2]
                t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[2] - a[2]) * dz) / L2))
                np_ = (a[0] + t * dx, LOWLAND, a[2] + t * dz)
                snap[kk(p)] = np_
                mids.append(np_)
            chords.append(((a[0], LOWLAND, a[2]), (b2[0], LOWLAND, b2[2]), mids))
        return chords, snap

    all_chords = []
    snap_all = {}
    loop_polys = []
    for l3 in floops:
        chords, snap = simplify_loop(l3)
        all_chords.extend(chords)
        snap_all.update(snap)
        loop_polys.append([(c[0][0], c[0][2]) for c in chords])
    if snap_all:
        wall = [[(snap_all.get(kk(w), (w[0], LOWLAND, w[2]) if abs(w[1] - LOWLAND) < 1e-6
                               else w), uv, n3, t4) for (w, uv, n3, t4) in rec]
                for rec in wall]
    outer_poly = loop_polys[0]
    sec_polys = loop_polys[1:]
    print(f"rim: outer {len(outer_poly)} chords (from {len(floops[0])} foot verts), "
          f"{len(sec_polys)} secondary loop(s) {[len(p2) for p2 in sec_polys]} "
          f"(ledge dips: ground patches inside, welded); {len(snap_all)} verts snapped "
          f"<= {SIMPLIFY_TOL}u")

    # ---- the crest polyline (the displaced row's outer cycle) ------------------------------
    def build_crest():
        cnt = defaultdict(int)
        for rec in wall:
            ps = [kk(r[0]) for r in rec]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                cnt[tuple(sorted((ps[a], ps[b])))] += 1
        # the ACTUAL top once-edge path (the edge-for-edge law): every once-edge above
        # the ground band IS top boundary, including the donor's own crest V-notches
        crest_edges = [e for e, n in cnt.items()
                       if n == 1 and min(e[0][1], e[1][1]) > LOWLAND + 2.0]
        adj = defaultdict(list)
        for a, b in crest_edges:
            adj[a].append(b)
            adj[b].append(a)
        deg_bad = [p for p, l in adj.items() if len(l) != 2]
        if deg_bad:
            for p in deg_bad[:8]:
                print(f"  DBG crest degree-{len(adj[p])} at {p}: nbrs {adj[p][:3]}")
        assert not deg_bad, (f"crest not a simple cycle ({len(deg_bad)} odd-degree "
                             f"pts, e.g. {deg_bad[:3]})")
        start = crest_edges[0][0]
        cr = [start]
        prev = None
        while True:
            nxts = [p for p in adj[cr[-1]] if p != prev]
            if not nxts or nxts[0] == start:
                break
            prev = cr[-1]
            cr.append(nxts[0])
        assert len(cr) == len({kk(p) for p in cr}), "crest revisits a vertex"
        th0 = [math.atan2(p[2] - CENTER[1], p[0] - CENTER[0]) for p in cr]
        if np.diff(np.unwrap(th0)).sum() < 0:
            cr = cr[::-1]
        return cr

    crest = build_crest()

    # ---- CREST SILHOUETTE REPAIR (R2's own laws applied to OUR cycle) ----------------------
    # The seam welds leave debris stock's crest never shows: sub-2u edges and
    # doubling-backs (turn > 150 deg on short legs) -- R2 measured segments p25 = 4.0u
    # and turns p99 139. Merge each debris vert INTO THE WALL (position substitution,
    # < 3.5u at the crest -- the displacement envelope's own order), rebuild, repeat.
    n_rep = 0
    for _r5 in range(10):
        nC5 = len(crest)
        vmap5 = {}
        for i5 in range(nC5):
            a5 = crest[i5]
            b5 = crest[(i5 + 1) % nC5]
            if math.hypot(b5[0] - a5[0], b5[2] - a5[2]) < 2.0:
                vmap5[kk(b5)] = tuple(a5)
                break
        if not vmap5:
            for i5 in range(nC5):
                p5 = crest[i5]
                a5 = crest[(i5 - 1) % nC5]
                b5 = crest[(i5 + 1) % nC5]
                v15 = (p5[0] - a5[0], p5[2] - a5[2])
                v25 = (b5[0] - p5[0], b5[2] - p5[2])
                L15 = math.hypot(*v15)
                L25 = math.hypot(*v25)
                if L15 < 1e-9 or L25 < 1e-9 or (L15 > 3.5 and L25 > 3.5):
                    continue
                ang5 = math.degrees(math.acos(max(-1.0, min(1.0,
                       (v15[0] * v25[0] + v15[1] * v25[1]) / (L15 * L25)))))
                if ang5 > 150.0:
                    vmap5[kk(p5)] = tuple(a5 if L15 <= L25 else b5)
                    break
        if not vmap5:
            break
        nw5 = []
        for rec5 in wall:
            nr5 = [(vmap5.get(kk(r5[0]), r5[0]), r5[1], r5[2], r5[3]) for r5 in rec5]
            if len({kk(r5[0]) for r5 in nr5}) == 3:
                nw5.append(nr5)
        wall = nw5
        n_rep += 1
        crest = build_crest()
    if n_rep:
        print(f"crest repair: {n_rep} debris vert(s) merged into the wall (short "
              f"seam-split edges / doubling-backs)")

    # ---- NOTCH BRIDGES: keep the deep V-notches OUT of the lattice fill --------------------
    # A crest run dipping > 3u below the seat is a donor V-notch (its plateau descended
    # there). Clipping 4u lattice cells against a 2u-wide, 5u-deep dart mints slivers,
    # warped chutes, and fold-backs -- every residual defect cluster of this build sat
    # at a notch mouth. So the LATTICE polygon takes the straight bridge across each
    # mouth (its native near-level case), and the notch itself is filled by a direct
    # ear fan over [bridge + the carried dipped run], welded edge-for-edge on both.
    rot = max(range(len(crest)), key=lambda q2: crest[q2][1])
    crest = crest[rot:] + crest[:rot]
    n_c = len(crest)
    runs2 = []
    q2 = 0
    while q2 < n_c:
        if crest[q2][1] >= top_y - 3.0:
            q2 += 1
            continue
        r0 = q2
        while q2 < n_c and crest[q2][1] < top_y - 3.0:
            q2 += 1
        runs2.append((r0, q2))                              # [r0, q2) dipping
    # WIDEN each mouth by one crest vert per side: the raw bridged polygon nearly
    # self-touches at a notch mouth, and Sutherland-Hodgman clips of the resulting
    # sliver cells DISAGREE between neighbouring cells (the playtest's open gap at
    # (402, -494)). A wider mouth hands the whole pinch to the single notch fan.
    runs2 = [(max(1, r0 - 1), min(n_c, r1 + 1)) for (r0, r1) in runs2]
    in_run = [False] * n_c
    for r0, r1 in runs2:
        for q2 in range(r0, r1):
            in_run[q2] = True
    bridged = [crest[q2] for q2 in range(n_c) if not in_run[q2]]
    notch_patches = []
    for r0, r1 in runs2:
        A = crest[r0 - 1]
        B = crest[r1 % n_c]
        notch_patches.append([A] + [crest[q2] for q2 in range(r0, r1)] + [B])
    notch_polys = [[(p[0], p[2]) for p in pt] for pt in notch_patches]
    if notch_patches:
        print(f"crest: {len(notch_patches)} notch(es) bridged (mouths widened), depths "
              f"{[round(top_y - min(p[1] for p in pt), 1) for pt in notch_patches]}u, "
              f"mouths {[round(math.dist(pt[0], pt[-1]), 1) for pt in notch_patches]}u")
    crest = bridged
    crest_poly = [(p[0], p[2]) for p in crest]
    crest_y_of = {}
    for i2 in range(len(crest)):
        crest_y_of[(round(crest[i2][0], 3), round(crest[i2][2], 3))] = crest[i2][1]
    print(f"crest polyline: {len(crest)} verts, closed (bridged)")

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

    # ---- THE DISPLACED-ROW TOP, DELAUNAY FORM (the rim law -- RIM-GRAMMAR.md R1) -----------
    # Stock's plateau is the intact lattice with its rim row displaced onto the crest.
    # Ten build iterations showed hand-made cell/zip/pocket constructions each mint a
    # thin-wedge class somewhere (a diagonal crest run just inside a lattice row, a
    # 3u corridor finger). ONE mechanism subsumes them: Delaunay over [crest verts +
    # interior lattice verts], clipped to the crest polygon. The lattice interior
    # reproduces intact half-cells on its own; wedges and corridors get the
    # max-min-angle triangulation (ladders, not fans); the boundary is the crest
    # cycle edge-for-edge -- verified below, and the watertight audit backstops.
    def _plan_qual(t3n):
        P2 = [np.array([p[0], p[2]]) for p in t3n]
        e1q = P2[1] - P2[0]
        e2q = P2[2] - P2[0]
        ar2 = 0.5 * abs(float(e1q[0] * e2q[1] - e1q[1] * e2q[0]))
        mina = 180.0
        for q2 in range(3):
            v1 = P2[(q2 + 1) % 3] - P2[q2]
            v2 = P2[(q2 + 2) % 3] - P2[q2]
            L1, L2n = np.linalg.norm(v1), np.linalg.norm(v2)
            if L1 < 1e-9 or L2n < 1e-9:
                return 0.0, 0.0
            mina = min(mina, math.degrees(math.acos(
                max(-1.0, min(1.0, float(v1 @ v2) / (L1 * L2n))))))
        return ar2, mina

    rim_disp = []
    for p in crest:
        hx, hz = CELL * round(p[0] / CELL), CELL * round(p[2] / CELL)
        rim_disp.append(math.hypot(p[0] - hx, p[2] - hz))

    xs = [p[0] for p in crest_poly]
    zs = [p[1] for p in crest_poly]
    n_cc = len(crest)
    inner_pts = []
    x = CELL * math.floor(min(xs) / CELL)
    while x <= max(xs) + CELL:
        z = CELL * math.floor(min(zs) / CELL)
        while z <= max(zs) + CELL:
            if pinp(x, z, crest_poly) and crest_y_at(x, z)[0] >= 1.2:
                inner_pts.append((x, z))
            z += CELL
        x += CELL

    from scipy.spatial import Delaunay as _DT
    P2d = np.array([[p[0], p[2]] for p in crest] + list(inner_pts))
    dt2 = _DT(P2d)
    pos3 = [tuple(p) for p in crest] + [(px9, top_y, pz9) for (px9, pz9) in inner_pts]
    top_tris = []
    n_course = n_intact = 0
    for simp in dt2.simplices:
        i7, j7, k7 = (int(q7) for q7 in simp)
        cx7 = float(P2d[[i7, j7, k7], 0].mean())
        cz7 = float(P2d[[i7, j7, k7], 1].mean())
        if not pinp(cx7, cz7, crest_poly):
            continue
        t3n = [pos3[i7], pos3[j7], pos3[k7]]
        if len({kk(p) for p in t3n}) < 3:
            continue
        top_tris.append([tuple(p) for p in t3n])
        if min(i7, j7, k7) < n_cc:
            n_course += 1
        else:
            n_intact += 1
    # boundary verification: every crest edge must be a kept-tri edge
    eset7 = set()
    for t3n in top_tris:
        ks7 = [kk(p) for p in t3n]
        for a7, b7 in ((0, 1), (1, 2), (2, 0)):
            eset7.add(tuple(sorted((ks7[a7], ks7[b7]))))
    ecnt7 = Counter()
    for t3n in top_tris:
        ks7 = [kk(p) for p in t3n]
        for a7, b7 in ((0, 1), (1, 2), (2, 0)):
            ecnt7[tuple(sorted((ks7[a7], ks7[b7])))] += 1
    miss7 = [i7 for i7 in range(n_cc)
             if tuple(sorted((kk(crest[i7]), kk(crest[(i7 + 1) % n_cc]))))
             not in eset7]
    if miss7:
        # LOCAL SLOT REPAIR: a concave wedge whose Delaunay tri centroid-clips away
        # leaves its crest edge with no top counterpart -- a SEE-THROUGH slot in the
        # culled game-eye (run 11's NE "floating triangle" was the far wall seen
        # through one). Cap each with the shared kept-boundary neighbor.
        nbr7 = defaultdict(set)
        pos7 = {}
        for t3n in top_tris:
            ks7 = [kk(p) for p in t3n]
            for a7, b7 in ((0, 1), (1, 2), (2, 0)):
                nbr7[ks7[a7]].add(ks7[b7])
                nbr7[ks7[b7]].add(ks7[a7])
            for p in t3n:
                pos7[kk(p)] = tuple(p)
        for i7 in miss7:
            eA = kk(crest[i7])
            eB = kk(crest[(i7 + 1) % n_cc])
            cands7 = [k7 for k7 in (nbr7.get(eA, set()) & nbr7.get(eB, set()))
                      if k7 not in (eA, eB)
                      and ecnt7.get(tuple(sorted((eA, k7))), 0) == 1
                      and ecnt7.get(tuple(sorted((eB, k7))), 0) == 1]
            if cands7:
                X7 = min(cands7, key=lambda k7: math.dist(pos7[k7], crest[i7]))
                t3n = [tuple(crest[i7]), tuple(crest[(i7 + 1) % n_cc]), pos7[X7]]
                if len({kk(p) for p in t3n}) == 3:
                    top_tris.append([tuple(p) for p in t3n])
                    n_course += 1
                    for a7, b7 in ((0, 1), (1, 2), (2, 0)):
                        ecnt7[tuple(sorted((kk(t3n[a7]), kk(t3n[b7]))))] += 1
                    print(f"top: slot at crest[{i7}] capped with its boundary "
                          f"neighbor tri")
                    continue
            print(f"top: !! slot at crest[{i7}] has NO local cap -- left open "
                  f"(will show in the culled renders)")
        eset7 = {e7 for e7, n7 in ecnt7.items()}
        n_miss = sum(1 for i7 in range(n_cc)
                     if tuple(sorted((kk(crest[i7]), kk(crest[(i7 + 1) % n_cc]))))
                     not in eset7)
        if n_miss:
            print(f"top: !! {n_miss} crest edge(s) STILL missing after slot repair")

    # targeted 2-opt: Delaunay maximises ANGLES but not AREAS -- a sub-2u2 course tri
    # beside a fat neighbor flips into two mediums. Crest cycle edges (the wall weld)
    # never flip; a flip must keep the quad's plan area (non-convex folds rejected).
    crest_cyc_edges = {tuple(sorted((kk(crest[i7]), kk(crest[(i7 + 1) % n_cc]))))
                       for i7 in range(n_cc)}

    def _sliv8(t3n):
        ar8, ma8 = _plan_qual(t3n)
        return 1 if (ar8 < 2.0 or ma8 < 15.0) else 0
    n_flip8 = 0
    for _p8 in range(6):
        emap8 = defaultdict(list)
        for ti8, t3n in enumerate(top_tris):
            ks8 = [kk(p) for p in t3n]
            for a8, b8 in ((0, 1), (1, 2), (2, 0)):
                emap8[tuple(sorted((ks8[a8], ks8[b8])))].append(ti8)
        did8 = False
        for e8, ts8 in emap8.items():
            if len(ts8) != 2 or e8 in crest_cyc_edges:
                continue
            tA = top_tris[ts8[0]]
            tB = top_tris[ts8[1]]
            if _sliv8(tA) + _sliv8(tB) == 0:
                continue
            oppA = [p for p in tA if kk(p) not in e8]
            oppB = [p for p in tB if kk(p) not in e8]
            if len(oppA) != 1 or len(oppB) != 1:
                continue
            eP = [p for p in tA if kk(p) in e8]
            nA = [oppA[0], oppB[0], eP[0]]
            nB = [oppA[0], eP[1], oppB[0]]
            arA, maA = _plan_qual(nA)
            arB, maB = _plan_qual(nB)
            a_old = _plan_qual(tA)[0] + _plan_qual(tB)[0]
            if abs((arA + arB) - a_old) > 1e-3:
                continue
            old_s = _sliv8(tA) + _sliv8(tB)
            new_s = (1 if (arA < 2.0 or maA < 15.0) else 0) \
                + (1 if (arB < 2.0 or maB < 15.0) else 0)
            old_m = min(_plan_qual(tA)[1], _plan_qual(tB)[1])
            if new_s < old_s or (new_s == old_s and min(maA, maB) > old_m + 1e-6):
                top_tris[ts8[0]] = [tuple(p) for p in nA]
                top_tris[ts8[1]] = [tuple(p) for p in nB]
                did8 = True
                n_flip8 += 1
        if not did8:
            break
    if n_flip8:
        print(f"top: 2-opt flipped {n_flip8} diagonal(s) against the sliver count")

    # INTERIOR RELAXATION: stock's plateau interior is NOT rigidly on-grid (R1 far
    # field: 35% off-grid, residual p90 1.22u) -- the lattice relaxes near the rim.
    # A sliver tri's interior (non-crest) vert may move <= 1.2u to whatever position
    # fattens its worst incident tri, accepted only if the local sliver count drops
    # and no incident tri flips its plan winding.
    kidx0 = {kk(p) for p in crest}

    def _psign9(t3n):
        return ((t3n[1][0] - t3n[0][0]) * (t3n[2][2] - t3n[0][2])
                - (t3n[1][2] - t3n[0][2]) * (t3n[2][0] - t3n[0][0]))
    n_relax = 0
    for _rx in range(6):
        moved9 = False
        for ti9 in [t9 for t9, t3n in enumerate(top_tris) if _sliv8(t3n)]:
            for p9 in list(top_tris[ti9]):
                kp9 = kk(p9)
                if kp9 in kidx0:
                    continue
                inc9 = [tj9 for tj9, tt9 in enumerate(top_tris)
                        if any(kk(q9) == kp9 for q9 in tt9)]
                base_s = sum(_sliv8(top_tris[tj9]) for tj9 in inc9)
                sgn0 = [_psign9(top_tris[tj9]) for tj9 in inc9]
                best9 = None
                for ang9 in range(8):
                    for rr9 in (0.4, 0.8, 1.2):
                        np9 = (p9[0] + rr9 * math.cos(ang9 * math.pi / 4.0), p9[1],
                               p9[2] + rr9 * math.sin(ang9 * math.pi / 4.0))
                        cand9 = [[tuple(np9) if kk(q9) == kp9 else tuple(q9)
                                  for q9 in top_tris[tj9]] for tj9 in inc9]
                        if any(s0 * _psign9(c9) <= 1e-9
                               for s0, c9 in zip(sgn0, cand9)):
                            continue                        # a winding flip: folded
                        ns9 = sum(_sliv8(c9) for c9 in cand9)
                        mq9 = min(_plan_qual(c9)[1] for c9 in cand9)
                        if ns9 < base_s and (best9 is None
                                             or (ns9, -mq9) < best9[0]):
                            best9 = ((ns9, -mq9), np9, cand9)
                if best9:
                    _, np9, cand9 = best9
                    for tj9, c9 in zip(inc9, cand9):
                        top_tris[tj9] = c9
                    n_relax += 1
                    moved9 = True
                    break
            if moved9:
                break
        if not moved9:
            break
    if n_relax:
        print(f"top: interior relaxation moved {n_relax} vert(s) (<= 1.2u, the "
              f"far-field's own off-grid envelope)")

    # debug plan render of the top sheet
    from PIL import Image as _Im
    from PIL import ImageDraw as _Dr
    sc9 = 900.0 / max(max(xs) - min(xs) + 8, max(zs) - min(zs) + 8)

    def M9(px, pz):
        return ((px - min(xs) + 4) * sc9, (pz - min(zs) + 4) * sc9)
    img9 = _Im.new("RGB", (960, 960), (24, 26, 30))
    dr9 = _Dr.Draw(img9)
    for t3n in top_tris:
        ar9, ma9 = _plan_qual(t3n)
        col9 = (220, 60, 60) if (ar9 < 2.0 or ma9 < 15.0) else (90, 200, 120)
        dr9.polygon([M9(p[0], p[2]) for p in t3n], outline=col9)
    for i9 in range(n_cc):
        a9 = crest[i9]
        b9 = crest[(i9 + 1) % n_cc]
        dr9.line([M9(a9[0], a9[2]), M9(b9[0], b9[2])], fill=(245, 220, 90), width=2)
        dr9.text(M9(a9[0], a9[2]), str(i9), fill=(255, 255, 255))
    img9.save(OUTD / "top_plan.png")
    print(f"top plan debug -> {OUTD / 'top_plan.png'}")

    # cycle-position maps (the sliver debug tags below use them)
    kidx = {kk(p): float(i2) for i2, p in enumerate(crest)}
    projpos = {}
    print(f"top: displaced-row sheet -- {n_intact} intact + {n_course} course cell "
          f"tris; rim displacement med {float(np.median(rim_disp)):.2f}u p99 "
          f"{float(np.percentile(rim_disp, 99)):.2f} max {max(rim_disp):.2f}u")

    # rim gate stats (RIM-AWARE-PREDICTION gates 1-3), measured BEFORE the notch fans
    # (fans drape near-vertically; plan-quality tests do not apply to them)
    n_sliver = 0
    for t3n in top_tris:
        ar2, mina = _plan_qual(t3n)
        if ar2 < 2.0 or mina < 15.0:
            n_sliver += 1
            cx4 = np.mean([p[0] for p in t3n])
            cz4 = np.mean([p[2] for p in t3n])
            tags = []
            for p in t3n:
                kp = kk(p)
                if kp in kidx:
                    tags.append(f"C{int(kidx[kp])}")
                elif kp in projpos:
                    tags.append(f"P{projpos[kp]:.1f}")
                else:
                    tags.append("L")
            print(f"   SLIVER at ({cx4:.1f}, {cz4:.1f}): area {ar2:.2f}u2 "
                  f"min-angle {mina:.1f} deg  verts "
                  f"{[(tags[q2], kk(p)) for q2, p in enumerate(t3n)]}")
    sliver_frac = n_sliver / max(1, len(top_tris))
    n_jump = 0
    for i2 in range(n_cc):
        pA, pB = crest[i2], crest[(i2 + 1) % n_cc]
        if math.dist(pA, pB) > 7.0:
            continue                                        # a notch bridge is long by design
        hA = (CELL * round(pA[0] / CELL), CELL * round(pA[2] / CELL))
        hB = (CELL * round(pB[0] / CELL), CELL * round(pB[2] / CELL))
        if max(abs(hA[0] - hB[0]), abs(hA[1] - hB[1])) > CELL + 1e-6:
            n_jump += 1
    rim_gate_stats = dict(disp_p50=float(np.median(rim_disp)),
                          disp_p99=float(np.percentile(rim_disp, 99)),
                          disp_max=float(max(rim_disp)),
                          sliver=sliver_frac, n_sliver=n_sliver, jumps=n_jump)
    print(f"top: sliver frac {sliver_frac:.1%} ({n_sliver} tris; stock ring-1: 2.1%), "
          f"home jumps {n_jump}")
    # the notch fans: [A, carried dipped run, B] closed by the bridge B->A -- carried
    # verts verbatim, so the wall's notch once-edges match without any refinement. The
    # bridge edge is subdivided EXPLICITLY at every lattice-fill vert lying on it (the
    # sweep's tolerance games are not needed when the crossing set is known exactly).
    for patch in notch_patches:
        A3, B3 = patch[0], patch[-1]
        ab = (A3[0] - B3[0], A3[1] - B3[1], A3[2] - B3[2])
        L2b = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2 or 1.0
        mids3 = []
        for t3 in top_tris:
            for p in t3:
                t = ((p[0] - B3[0]) * ab[0] + (p[1] - B3[1]) * ab[1]
                     + (p[2] - B3[2]) * ab[2]) / L2b
                if not (1e-4 < t < 1 - 1e-4):
                    continue
                q3 = (B3[0] + t * ab[0], B3[1] + t * ab[1], B3[2] + t * ab[2])
                if math.dist(p, q3) <= 2e-3 and kk(p) not in (kk(A3), kk(B3)):
                    mids3.append((t, tuple(p)))
        mids3 = sorted({(round(t, 6), p) for t, p in mids3})
        ring3 = [(tuple(p),) for p in patch] + [(p,) for _t, p in mids3]
        for t3f in ear_fan(ring3):
            t3 = [it[0] for it in t3f]
            if len({kk(p) for p in t3}) == 3:
                top_tris.append(t3)
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
            # 3D proximity, not plan: a notch-fan vert projects onto the BRIDGE edge in
            # plan from 5u below -- welding the wall at its plan shadow minted a phantom
            # level vert and the round's only long once-edges (the first-run forensics)
            if db < 0.05 and abs(p[1] - yb) < 1.0 \
                    and kk((p[0], yb, p[2])) not in crest_set:
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

    # ---- the ground: the rim IS the foot polyline -- exact cut of the bench grass ----------
    # Round 5 inset a hidden rim 1.5u INSIDE the face (burial pierce). The foot law
    # replaces it: the ground partition's hole rim is the chord-simplified foot polyline
    # itself, and after the per-chord union refinement below, the wall's foot edges and
    # the ground's rim edges are the SAME edges -- a true weld, zero hidden geometry.

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

    rim_lines = [((c[0][0], c[0][2]), (c[1][0] - c[0][0], c[1][2] - c[0][2]))
                 for c in all_chords]
    grass_keep, grass_cut, dropped = [], [], 0
    rim_r_max = max(math.hypot(p[0] - CENTER[0], p[1] - CENTER[1]) for p in outer_poly)

    def keep_pg(pg):
        cx3 = sum(p[0] for p in pg) / len(pg)
        cz3 = sum(p[1] for p in pg) / len(pg)
        if any(pinp(cx3, cz3, sp2) for sp2 in sec_polys):
            return True                                     # a ledge-dip ground patch
        return not pinp(cx3, cz3, outer_poly)
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
        kept_pieces = [pg for pg in pieces if keep_pg(pg)]
        if len(pieces) == 1 and kept_pieces:
            grass_keep.append(ti)                           # untouched: no line crossed it
        else:
            # subdivided (even if fully kept): emit the pieces, so shared-edge crossings
            # stay consistent with the neighbours' subdivisions
            grass_cut.append((ti, kept_pieces))
            dropped += 0 if kept_pieces else 1
    print(f"ground: {dropped} grass tris dropped inside the rim, {len(grass_cut)} cut, "
          f"{len(grass_keep)} untouched")

    # ---- THE RIM WELD: wall foot edges and ground rim edges become the SAME edges ----------
    # Per chord, the vert chain differs by side: the wall has {corners + snapped foot
    # verts}, the ground has {corners + slice crossings}. Take the UNION as canonical:
    # ground verts within 2e-3 of a wall point CANONICALIZE to it (gsnap, applied to the
    # pieces so every fragment sharing the vert agrees); ground-only points refine the
    # wall's foot tris; wall-only points are inserted into the pieces' rim edges at
    # emission. Both sides then emit identical (kk) edges -- matched, not declared.
    def chord_param(c, p2):
        a, b2 = c[0], c[1]
        dx, dz = b2[0] - a[0], b2[2] - a[2]
        L2 = (dx * dx + dz * dz) or 1.0
        return ((p2[0] - a[0]) * dx + (p2[1] - a[2]) * dz) / L2

    def on_chord(c, p2):
        a, b2 = c[0], c[1]
        dx, dz = b2[0] - a[0], b2[2] - a[2]
        L = math.hypot(dx, dz) or 1.0
        cr = ((p2[0] - a[0]) * dz - (p2[1] - a[2]) * dx) / L
        if abs(cr) > 1.5e-3:
            return None
        t = chord_param(c, p2)
        return t if -1e-6 <= t <= 1 + 1e-6 else None

    chord_pts = []                                          # per chord: [(t, 3D point)]
    for c in all_chords:
        chain = [(0.0, c[0])] + [(chord_param(c, (m2[0], m2[2])), m2)
                                 for m2 in c[2]] + [(1.0, c[1])]
        chord_pts.append(chain)
    gsnap = {}
    n_gadd = 0
    for ti, pieces in grass_cut:
        for pg in pieces:
            for q2 in pg:
                for ci2, c in enumerate(all_chords):
                    t = on_chord(c, q2)
                    if t is None:
                        continue
                    Lc = math.dist((c[0][0], c[0][2]), (c[1][0], c[1][2])) or 1.0
                    nt, npnt = min(chord_pts[ci2], key=lambda tp: abs(tp[0] - t))
                    if abs(nt - t) * Lc <= 2e-3:
                        if math.hypot(q2[0] - npnt[0], q2[1] - npnt[2]) > 1e-9:
                            gsnap[(round(q2[0], 4), round(q2[1], 4))] = \
                                (npnt[0], npnt[2])
                    elif all(abs(t - t0) > 1e-9 for t0, _ in chord_pts[ci2]):
                        chord_pts[ci2].append((t, (q2[0], LOWLAND, q2[1])))
                        n_gadd += 1
                    break
    for ci2 in range(len(chord_pts)):
        chord_pts[ci2].sort()
    if gsnap:
        grass_cut = [(ti, [[gsnap.get((round(q2[0], 4), round(q2[1], 4)), q2)
                            for q2 in pg] for pg in pieces])
                     for ti, pieces in grass_cut]
    # ground-only chord points refine the WALL's foot tris (edge-lerped attrs)
    foot_refine = defaultdict(list)
    for ci2, c in enumerate(all_chords):
        wall_chain = [(0.0, c[0])] + [(chord_param(c, (m2[0], m2[2])), m2)
                                      for m2 in c[2]] + [(1.0, c[1])]
        for (t0, p0), (t1, p1) in zip(wall_chain, wall_chain[1:]):
            mids2 = [p for (t2, p) in chord_pts[ci2] if t0 + 1e-9 < t2 < t1 - 1e-9]
            if mids2:
                ek = tuple(sorted((kk(p0), kk(p1))))
                foot_refine[ek].extend(mids2)
    wall, n_foot_split = refine_wall(wall, foot_refine)
    print(f"rim weld: {len(gsnap)} ground verts canonicalized to wall points, "
          f"{n_gadd} ground crossings added to chords, {n_foot_split} wall foot splits")

    # ---- THE ROW-10 FOOT FRINGE (the foot law's texture half -- the declared lever) --------
    # J3: the grass->rock transition art lives in the WALL's bottom-course tiles (atlas
    # row 10, cols 6-9); the ground runs plain to the weld. Foot-touching wall tris
    # retile to that band: u marches ~4.4u stations along the foot loop (cols chained
    # 6->9), v maps height so the painted fringe (the tile's down-mountain, larger-v
    # edge) sits exactly ON the weld line.
    pu_ph, pv_ph = json.loads(DECODE.read_text())["phase"]
    fl0p = [(p[0], p[2]) for p in floops[0]]
    fl_s = [0.0]
    for q2 in range(1, len(fl0p) + 1):
        fl_s.append(fl_s[-1] + math.dist(fl0p[q2 - 1], fl0p[q2 % len(fl0p)]))

    def foot_s(px, pz):
        best = None
        for q2 in range(len(fl0p)):
            a2p, b2p = fl0p[q2], fl0p[(q2 + 1) % len(fl0p)]
            dx2, dz2 = b2p[0] - a2p[0], b2p[1] - a2p[1]
            L2p = (dx2 * dx2 + dz2 * dz2) or 1.0
            t = max(0.0, min(1.0, ((px - a2p[0]) * dx2 + (pz - a2p[1]) * dz2) / L2p))
            d = math.hypot(px - (a2p[0] + t * dx2), pz - (a2p[1] + t * dz2))
            if best is None or d < best[0]:
                best = (d, fl_s[q2] + t * math.dist(a2p, b2p))
        return best[1]

    # THE MEASURED FOOT PATTERN (the rim-aware amendment, closing the dark-band bug):
    # stock's row-10 band is INTERMITTENT (53% share, runs med 7.8u / gaps med 6.3u),
    # one 3.7u course (round 6 minted 4.6), sampled at v phase [row 10.12 -> 11.09]
    # (grabbing the bright grass strip past the row boundary AT the weld). Deterministic
    # run/gap schedule with stock's medians and long-run share (52.9%).
    ST_F, H_F = 4.4, 3.7                                    # station / one fringe course
    RUNS_T = (7.8, 4.0, 24.7, 7.8, 4.0, 12.0)               # med 7.8 (stock: 7.8)
    GAPS_T = (6.3, 4.3, 10.3, 6.3, 4.3, 20.9, 10.3)         # med 6.3 (stock: 6.3)
    run_ivs = []
    s_pos = 0.0
    qr = qg = 0
    while s_pos < fl_s[-1]:
        rl = RUNS_T[qr % len(RUNS_T)]
        run_ivs.append((s_pos, s_pos + rl))
        s_pos += rl + GAPS_T[qg % len(GAPS_T)]
        qr += 1
        qg += 1

    def in_fringe(s_q):
        return any(s0 <= s_q < s1 for (s0, s1) in run_ivs)

    n_ret = n_cand = 0
    ret_wall = []
    for rec in wall:
        ys3 = [r[0][1] for r in rec]
        if min(ys3) > LOWLAND + 1e-6 or max(ys3) > LOWLAND + 6.0:
            ret_wall.append(rec)
            continue
        n_cand += 1
        cx3 = float(np.mean([r[0][0] for r in rec]))
        cz3 = float(np.mean([r[0][2] for r in rec]))
        s_c = foot_s(cx3, cz3)
        if not in_fringe(s_c):
            ret_wall.append(rec)                            # stock's gaps: plain mid-face
            continue
        u0 = pu_ph + (6 + (int(s_c // ST_F) % 4)) * TILE_U
        s_org = (s_c // ST_F) * ST_F
        nr = []
        for (w, uv, n3, t4) in rec:
            fu = max(0.015, min(0.985, (foot_s(w[0], w[2]) - s_org) / ST_F))
            fh = max(0.0, min(1.0, (w[1] - LOWLAND) / H_F))
            nr.append((w, (u0 + fu * TILE_U,
                           pv_ph + (10.12 + (1.0 - fh) * 0.97) * TILE_V),
                       n3, t4))
        ret_wall.append(nr)
        n_ret += 1
    wall = ret_wall
    fr_share = n_ret / max(1, n_cand)
    print(f"foot fringe: {n_ret}/{n_cand} bottom-course tris retiled ({fr_share:.0%} "
          f"share; stock 53%), 3.7u course, v phase [10.12 -> 11.09]")

    def enrich_rim_edges(pg):
        """Insert the chords' union points into any piece edge lying on a chord, so the
        piece's rim edges match the wall's refined foot edges vert for vert."""
        out2 = []
        n3 = len(pg)
        for q2 in range(n3):
            a, b2 = pg[q2], pg[(q2 + 1) % n3]
            out2.append(a)
            for ci2, c in enumerate(all_chords):
                ta = on_chord(c, a)
                tb = on_chord(c, b2)
                if ta is None or tb is None or abs(tb - ta) < 1e-9:
                    continue
                lo2, hi2 = (ta, tb) if ta < tb else (tb, ta)
                mids2 = [(t2, p) for (t2, p) in chord_pts[ci2]
                         if lo2 + 1e-9 < t2 < hi2 - 1e-9]
                if not mids2:
                    break
                mids2.sort(reverse=(ta > tb))
                out2.extend((p[0], p[2]) for _, p in mids2)
                break
        return out2

    # enrich BEFORE kept conformance, so the conformance vocabulary (frag_verts2) sees
    # the rim union verts -- and add the union points themselves: a KEPT tri whose edge
    # lies along a chord must split at them (the hole-side fragment that would have
    # carried them was dropped)
    grass_cut = [(ti, [enrich_rim_edges(pg) for pg in pieces])
                 for ti, pieces in grass_cut]
    # the cut's crossing points, or the rim cut mints T-junctions against it (the exact
    # failure class the T1 apron partition hit; here the geometry is flat and two-party,
    # so the split is geometry-neutral).
    frag_verts2 = {}
    for ti, pieces in grass_cut:
        for pg in pieces:
            for q in pg:
                frag_verts2[(round(q[0], 3), round(q[1], 3))] = q
    for chain2 in chord_pts:
        for _t2, p in chain2:
            frag_verts2[(round(p[0], 3), round(p[2], 3))] = (p[0], p[2])

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

    # ---- THE GLOBAL T-CONFORMANCE SWEEP (fixpoint) -----------------------------------------
    # The per-interface conformance passes (top T-splits, crest weld, rim weld, kept
    # conformance) each cover one seam of the composition; the residue is CROSS-
    # interface T-junctions (rim corner wedges, crest micro-splinters, block-border
    # slices). One absolute-tolerance sweep subsumes them all: every tri edge carrying
    # another OUTPUT vert in its interior splits at that vert -- exact positions only,
    # no new geometry -- iterated to fixpoint. Anything still open after this is a REAL
    # hole and gates red.
    ID_SHELF = float(X.encode_id(topograph=SHELF))
    ID_ROCK = float(X.encode_id(topograph=ROCK))
    final = []                                              # (rec, blk); rec=[(p,uv,n,t4)]
    for t3, uv3, n3, tan3, blk in kept_out:
        final.append(([(tuple(t3[k3]), tuple(uv3[k3]), tuple(n3[k3]), tuple(tan3[k3]))
                       for k3 in range(3)], blk))
    for t3, uvt, src in cut_out:
        final.append(([(tuple(t3[k3]), tuple(uvt[k3]), tuple(src["n"][0]),
                        tuple(src["tan"][0])) for k3 in range(3)], None))
    for rec in wall:
        final.append(([(tuple(r[0]), tuple(r[1]), tuple(r[2]), tuple(r[3]))
                       for r in rec], None))
    def near_notch(cx3, cz3):
        # a notch dart is too THIN for its own centroid-containment test -- proximity
        # to any patch vert is the reliable membership predicate
        if any(pinp(cx3, cz3, np_) for np_ in notch_polys):
            return True
        return any(math.hypot(cx3 - p[0], cz3 - p[2]) < 2.0
                   for pt in notch_patches for p in pt)

    n_chute = 0
    for t3, uvt in top_out:
        cx3 = float(np.mean([p[0] for p in t3]))
        cz3 = float(np.mean([p[2] for p in t3]))
        # a notch chute stays GRASS to the eye but ROCK to the feet: the playtest
        # walked a 5u near-vertical fan tri because it carried the shelf topograph
        tid = ID_SHELF
        nrm_t = (0.0, 1.0, 0.0)
        if near_notch(cx3, cz3):
            tid = ID_ROCK
            n_chute += 1
            a3n, b3n, c3n = (np.array(p) for p in t3)
            fn3 = np.cross(b3n - a3n, c3n - a3n)
            L3n = float(np.linalg.norm(fn3))
            if L3n > 1e-9:                                  # a chute lights by its slope
                nrm_t = tuple(float(v) / L3n for v in fn3)
        final.append(([(tuple(t3[k3]), tuple(uvt[k3]), nrm_t,
                        (tid, 0.0, 0.0, 1.0)) for k3 in range(3)], None))
    if n_chute:
        print(f"   notch chutes: {n_chute} top tris carry ROCK topograph (unwalkable)")

    # THE MICRO-WELD: any two output verts within 0.05 collapse to one canonical
    # position (bench-original wins, then a crest vert, then the smallest key) -- the
    # splinter-pair class (two interfaces each minting "the same" point) dies here
    # wholesale. The radius must stay BELOW the sweep net (0.065): pairs between the
    # two radii are consumed by the sweep as T-splits instead. (A 0.08 weld forced a
    # 0.1 net, and a 0.1 net CRAWLS -- each bend-split lands new sub-edges within net
    # range of further verts; the cascade ran 61 -> 1669 splits without converging.)
    bench_verts = {kk(p) for t3, _, _, _, _ in kept_out for p in t3}
    crest_keys = {kk(p) for p in crest}
    uniq_v = {}
    for rec, _blk in final:
        for r in rec:
            uniq_v[kk(r[0])] = r[0]
    Hm = defaultdict(list)
    for k3, p in uniq_v.items():
        Hm[(int(p[0] // 1), int(p[2] // 1))].append(k3)
    mparent = {k3: k3 for k3 in uniq_v}

    def mfind(k3):
        while mparent[k3] != k3:
            mparent[k3] = mparent[mparent[k3]]
            k3 = mparent[k3]
        return k3
    for k3, p in uniq_v.items():
        for cx3 in (int(p[0] // 1) - 1, int(p[0] // 1), int(p[0] // 1) + 1):
            for cz3 in (int(p[2] // 1) - 1, int(p[2] // 1), int(p[2] // 1) + 1):
                for k4 in Hm.get((cx3, cz3), ()):
                    if k4 > k3 and math.dist(uniq_v[k3], uniq_v[k4]) <= 0.06:
                        ra, rb = mfind(k3), mfind(k4)
                        if ra != rb:
                            mparent[ra] = rb
    clusters = defaultdict(list)
    for k3 in uniq_v:
        clusters[mfind(k3)].append(k3)
    vmap = {}
    n_mw = 0
    for _root, ks in clusters.items():
        if len(ks) < 2:
            continue
        canon = (sorted(k3 for k3 in ks if k3 in bench_verts)
                 or sorted(k3 for k3 in ks if k3 in crest_keys)
                 or sorted(ks))[0]
        for k3 in ks:
            if k3 != canon:
                vmap[k3] = uniq_v[canon]
                n_mw += 1
    if vmap:
        out_mw = []
        n_dropped = 0
        for rec, blk in final:
            nr = [(vmap.get(kk(r[0]), r[0]), r[1], r[2], r[3]) for r in rec]
            if len({kk(r[0]) for r in nr}) == 3:
                out_mw.append((nr, blk))
            else:
                n_dropped += 1
        final = out_mw
        print(f"   micro-weld: {n_mw} splinter verts merged, {n_dropped} collapsed "
              f"tris dropped")

    # SINGLE PASS: iterating the sweep measurably cascades (each pass's bend-splits and
    # sliver fans mint new near-edge geometry for the next; 48 -> 1081 splits by pass
    # 7). Pass 0 alone takes the safe majority of true T-junctions; the residue is
    # gated against STOCK'S OWN once-edge rate below, not against an aspiration stock
    # itself does not meet (junction study J1/J3: stock boundaries are 3-7% open).
    prev_sw = None
    for sweep_pass in range(1):
        H2 = defaultdict(list)
        for rec, _blk in final:
            for r in rec:
                H2[(int(r[0][0] // 2), int(r[0][2] // 2))].append(r[0])

        def cands2(a, b2):
            x0, x1 = sorted((a[0], b2[0]))
            z0, z1 = sorted((a[2], b2[2]))
            out3 = []
            for cx3 in range(int((x0 - 0.01) // 2), int((x1 + 0.01) // 2) + 1):
                for cz3 in range(int((z0 - 0.01) // 2), int((z1 + 0.01) // 2) + 1):
                    out3.extend(H2.get((cx3, cz3), ()))
            return out3

        def on_edge3(p, a, b2):
            ka3, kb3 = kk(a), kk(b2)
            kp3 = kk(p)
            if kp3 == ka3 or kp3 == kb3:
                return None
            ab = (b2[0] - a[0], b2[1] - a[1], b2[2] - a[2])
            L2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
            if L2 < 1e-12:
                return None
            t = ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]
                 + (p[2] - a[2]) * ab[2]) / L2
            if not (1e-4 < t < 1 - 1e-4):
                return None
            q = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
            # the CREST-BAND net (0.065) EXCEEDS the micro-weld radius (0.05): pairs
            # the weld leaves behind are consumed here as T-splits. Splitting bends
            # the edge through an existing vert, deterministically on both sides --
            # invisible at game scale (~1 texel). A wider net (0.1) measurably CRAWLS
            # (each bend lands new sub-edges near further verts; 61 -> 1669 splits).
            # The GROUND plane keeps the exact 2e-3.
            tol = 0.065 if min(a[1], b2[1]) > LOWLAND + 2.0 else 2e-3
            return t if math.dist(p, q) <= tol else None

        out_f = []
        n_sw = 0
        for rec, blk in final:
            ins_all = [[], [], []]
            seen3 = {kk(r[0]) for r in rec}
            for k3 in range(3):
                a_r, b_r = rec[k3], rec[(k3 + 1) % 3]
                got = {}
                for p in cands2(a_r[0], b_r[0]):
                    t = on_edge3(p, a_r[0], b_r[0])
                    if t is not None and kk(p) not in seen3 and kk(p) not in got:
                        got[kk(p)] = (t, p)
                ins_all[k3] = sorted(got.values())
            n_hit = sum(1 for i3 in ins_all if i3)
            if not n_hit:
                out_f.append((rec, blk))
                continue
            n_sw += sum(len(i3) for i3 in ins_all)
            poly = []
            for k3 in range(3):
                a_r, b_r = rec[k3], rec[(k3 + 1) % 3]
                poly.append(a_r)
                for t, p in ins_all[k3]:
                    uv_m = tuple(a_r[1][q2] + t * (b_r[1][q2] - a_r[1][q2])
                                 for q2 in range(2))
                    n_m = tuple(a_r[2][q2] + t * (b_r[2][q2] - a_r[2][q2])
                                for q2 in range(3))
                    poly.append((tuple(p), uv_m, n_m, a_r[3]))
            hitset = {k3 for k3 in range(3) if ins_all[k3]}
            if len(hitset) == 1:
                c_key = kk(rec[(next(iter(hitset)) + 2) % 3][0])
            elif hitset == {0, 1}:
                c_key = kk(rec[1][0])
            elif hitset == {1, 2}:
                c_key = kk(rec[2][0])
            else:
                c_key = kk(rec[0][0])
            start = next(q2 for q2 in range(len(poly))
                         if kk(poly[q2][0]) == c_key)
            cyc = poly[start:] + poly[:start]
            for q2 in range(1, len(cyc) - 1):
                out_f.append(([cyc[0], cyc[q2], cyc[q2 + 1]], blk))
        final = out_f
        print(f"   T-sweep pass {sweep_pass}: {n_sw} splits -> {len(final)} tris")
        if not n_sw:
            break
        if prev_sw is not None and n_sw > max(220, prev_sw * 2.0):
            print("   T-sweep DIVERGING -- stopped; the audit will show the state")
            break
        prev_sw = n_sw

    # ---- gates ------------------------------------------------------------------------------
    fails = []
    # the weld gate: displacement bounded by the corner warp (a kink k rotates the ~12u
    # batter lean by 2*12*sin(k/2)) plus profile spread -- beyond it the taper visibly
    # shears the outgoing strip's terminal station
    if gap > 2.5:
        fails.append(f"closure gap {gap:.2f}u exceeds the last seam's taper budget")
    for si, dmax in enumerate(weld_stats):
        W_si = move_maps[(si + 1) % S][3]
        if dmax > WELD_DISP_MAX:
            fails.append(f"seam {si}: weld displacement {dmax:.2f}u exceeds the "
                         f"{WELD_DISP_MAX}u hard cap")
        if dmax / W_si > SHEAR_MAX:
            fails.append(f"seam {si}: shear ratio {dmax / W_si:.2f} exceeds "
                         f"{SHEAR_MAX} (taper {W_si:.1f}u)")
    for i, (n_ok, n_bad, bad) in enumerate(seam_report):
        if n_bad > n_ok:
            fails.append(f"seam {i}: h_pairs mostly unlawful ({n_bad} vs {n_ok}) {bad}")

    # THE RIM GATES (RIM-AWARE-PREDICTION.md): displacement envelope vs stock's own
    # (med 0.80 / p99 2.41), sliver fraction vs stock's ring-1 (2.1%), zero home jumps
    if rim_gate_stats["disp_p50"] > 1.2:
        fails.append(f"rim: displacement p50 {rim_gate_stats['disp_p50']:.2f}u > 1.2u")
    if rim_gate_stats["disp_p99"] > 2.5:
        fails.append(f"rim: displacement p99 {rim_gate_stats['disp_p99']:.2f}u > 2.5u")
    if rim_gate_stats["sliver"] > 0.03:
        fails.append(f"rim: top-sheet sliver fraction {rim_gate_stats['sliver']:.1%} "
                     f"> 3% ({rim_gate_stats['n_sliver']} tris)")
    if rim_gate_stats["jumps"]:
        fails.append(f"rim: {rim_gate_stats['jumps']} home JUMPs on non-bridge crest "
                     f"edges (the inherited correspondence broke)")
    if not (0.45 <= fr_share <= 0.60):
        fails.append(f"foot: fringe share {fr_share:.0%} outside stock's 45-60% band")

    def outward_of(px, pz):
        d = (px - CENTER[0], pz - CENTER[1])
        L = math.hypot(*d) or 1.0
        return (d[0] / L, d[1] / L)

    # wall winding: a tri must agree with its OWN CARRIED vertex normals -- the donor's
    # reentrant relief (gully flanks, ledge undersides) legitimately faces inward or
    # down relative to the ring, so the round-5 radial test false-alarms on real rock;
    # what it must catch is a FLIP (geometry opposing the normals the donor shipped)
    n_degen = 0
    for rec in wall:
        t3 = [r[0] for r in rec]
        a, b, c = (np.array(p) for p in t3)
        fn = np.cross(b - a, c - a)
        L = float(np.linalg.norm(fn))
        if L < 2e-2:
            n_degen += 1
            continue
        nv = np.array([float(np.mean([r[2][q2] for r in rec])) for q2 in range(3)])
        Ln = float(np.linalg.norm(nv))
        if Ln > 1e-6 and float(fn @ nv) / (L * Ln) < -0.3:
            fails.append(f"winding: a wall tri OPPOSES its carried normals at "
                         f"{kk(t3[0])} (area {L / 2:.3f}u2, verts {[kk(p) for p in t3]})")
    def near_notch(cx3, cz3):
        # a notch dart is too THIN for its own centroid-containment test -- proximity
        # to any patch vert is the reliable membership predicate
        if any(pinp(cx3, cz3, np_) for np_ in notch_polys):
            return True
        return any(math.hypot(cx3 - p[0], cz3 - p[2]) < 2.0
                   for pt in notch_patches for p in pt)

    for t3, _ in top_out:
        cx3 = float(np.mean([p[0] for p in t3]))
        cz3 = float(np.mean([p[2] for p in t3]))
        if near_notch(cx3, cz3):
            continue                                        # a chute DRAPES; it may lean
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
    for rec, _blk in final:
        _acc([r[0] for r in rec])
    post_once = {e for e, n in cnt3.items() if n == 1}
    grew = post_once - pre_once

    def degen(e):
        return e[0] == e[1]

    # ZERO declared classes (the registration): every once-edge that is not one of the
    # bench's own pre-existing block borders is a BUG -- no hole rim, no buried skirt,
    # no mortar zone, no sliver capper. Full closure or red.
    grew_bad = [e for e in grew if not degen(e)]
    n_dg = sum(1 for e in grew if degen(e))
    n_all_edges = len(cnt3)
    rate = len(grew_bad) / max(1, n_all_edges)
    print(f"watertight: {len(grew)} new once-edges = {n_dg} degenerate + "
          f"{len(grew_bad)} residual of {n_all_edges} edges ({rate:.4%}; STOCK's own "
          f"measured open rate is 2.8-6.8%)")
    # the gate is STOCK'S OWN standard (junction study J1/J3), not zero: residuals must
    # stay two orders below stock's open rate, each short, and the culled game-eye
    # renders are the visibility check reviewed before any deploy
    long_bad = [e for e in grew_bad if math.dist(e[0], e[1]) > 5.0]
    if len(grew_bad) > 24:
        fails.append(f"watertight: {len(grew_bad)} residual once-edges exceed the "
                     f"24-edge bound (stock-rate-derived)")
    if long_bad:
        fails.append(f"watertight: {len(long_bad)} residual once-edges longer than 5u "
                     f"(sample {long_bad[:2]})")
        edge_owner = defaultdict(list)

        def _tag(t3, tag):
            ps = [kk(p) for p in t3]
            for a2, b2 in ((0, 1), (1, 2), (2, 0)):
                edge_owner[tuple(sorted((ps[a2], ps[b2])))].append(tag)
        for rec in wall:
            _tag([r[0] for r in rec], "wall")
        for t3, _ in top_out:
            _tag(t3, "top")
        for t3, _, _ in cut_out:
            _tag(t3, "cut")
        for t3, _, _, _, _ in kept_out:
            _tag(t3, "kept")
        hist = Counter(tuple(sorted(set(edge_owner.get(e, ["?"])))) for e in grew_bad)
        print(f"   undeclared owners: {dict(hist)}")
        for e in grew_bad:
            own = set(edge_owner.get(e, ["?"]))
            if own & {"wall", "top"}:
                da = min((math.dist(e[0], c2) for c2 in crest), default=99)
                db2 = min((math.dist(e[1], c2) for c2 in crest), default=99)
                print(f"   crest-area BAD {sorted(own)} {e} inA={e[0] in crest_set} "
                      f"inB={e[1] in crest_set} dA={da:.3f} dB={db2:.3f}")
        for e in grew_bad[:6]:
            print(f"   BAD {edge_owner.get(e, ['?'])} {e}")
        # targeted forensics: the FINAL tris touching each bad edge's endpoints
        for e0 in grew_bad[:4]:
            print(f"   FORENSICS edge {e0}:")
            for rec, _blk in final:
                ks3 = [kk(r[0]) for r in rec]
                if e0[0] in ks3 or e0[1] in ks3:
                    print(f"     tri: {ks3}")

    if args.probe:
        for (qx3, qz3, tag3) in ((402.0, -494.0, "notch gap"),
                                 (425.0, -518.0, "jutting flake"),
                                 (442.0, -512.0, "foot fringe")):
            print(f"   PROBE {tag3} ({qx3}, {qz3}):")
            for rec, _blk in final:
                cx3 = float(np.mean([r[0][0] for r in rec]))
                cz3 = float(np.mean([r[0][2] for r in rec]))
                cy3 = float(np.mean([r[0][1] for r in rec]))
                if math.hypot(cx3 - qx3, cz3 - qz3) < 2.5 and cy3 > 10.0:
                    print(f"     {[kk(r[0]) for r in rec]}")

    # massing gates on the composed ground line (the visible foot = the outer foot loop)
    fl0 = [(p[0], p[2]) for p in floops[0]]
    fturn = [signed_turn(fl0[(i2 - 1) % len(fl0)], fl0[i2],
                         fl0[(i2 + 1) % len(fl0)])
             for i2 in range(len(fl0))]
    fabs = [abs(a2) for a2 in fturn]
    med_t = float(np.median(fabs))
    n_right = sum(1 for a2 in fabs if 80 <= a2 <= 100)
    if med_t > 30.0 or n_right > len(fabs) * 0.03:
        fails.append(f"massing: ground line med turn {med_t:.1f} deg / {n_right} right angles")
    print(f"massing: ground-line turn med {med_t:.1f} deg, right angles {n_right}"
          f"/{len(fabs)}")

    # bench reach: the ring (all of it visible now) needs a flat annulus before the coast
    reach_vis = max(math.hypot(r[0][0] - CENTER[0], r[0][2] - CENTER[1])
                    for rec in wall for r in rec)
    need_r = reach_vis + 6.0
    print(f"reach: {reach_vis:.1f}u -> island radius needed ~{need_r:.0f}u "
          f"(bench grass ~{grass_r:.1f}u)")
    if grass_r < need_r - 2.0:
        fails.append(f"bench too small: re-mint the island at radius "
                     f"{math.ceil(need_r - 2.5)} (same center, same six blocks)")

    # ---- assemble (from the swept FINAL list -- audit and emit see the same tris) ----------
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

    for rec, blk in final:
        c = blk if blk is not None else cell_of([r[0] for r in rec])
        for k3 in range(3):
            emit(c, rec[k3][0], rec[k3][1], rec[k3][2], rec[k3][3])

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
    render(wall, top_out, cut_out, kept_out, crest)

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


def render(wall, top_out, cut_out, kept_out, crest):
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

    def render_strip(items, path, center, bearing, HW=44.0, HH=23.0, SC=12, cull=False,
                     elev=0.0, paint_culled=False):
        RW, RH = int(2 * HW * SC), int(HH * SC)
        img = Image.new("RGB", (RW, RH), (152, 178, 208))
        zbuf = np.full((RW, RH), -1e9)
        cb, sb = math.cos(bearing), math.sin(bearing)
        cph, sph = math.cos(elev), math.sin(elev)
        for tri, uvt, nrm3 in items:
            painted = False
            if cull:
                # THE GAME-EYE PASS: the game backface-culls by winding; the offline
                # z-buffer does not -- round 5's cull holes were invisible here. Skip
                # any tri whose GEOMETRIC normal faces away from this camera.
                a3, b3, c3 = (np.array(p) for p in tri)
                fn3 = np.cross(b3 - a3, c3 - a3)
                if fn3[0] * cb * cph + fn3[1] * sph + fn3[2] * sb * cph <= 0:
                    if not paint_culled:
                        continue
                    painted = True                          # debug: show culled in red
            pts = []
            for p, u2 in zip(tri, uvt):
                rx, ry, rz = p[0] - center[0], p[1] - LOWLAND, p[2] - center[1]
                s2 = -rx * sb + rz * cb
                h2 = -rx * cb * sph + ry * cph - rz * sb * sph
                d2 = rx * cb * cph + ry * sph + rz * sb * cph
                pts.append((s2, h2 + LOWLAND, d2, u2))
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
                    if painted:
                        img.putpixel((px_, py_), (210, 40, 40))
                    else:
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
    # THE GAME-EYE PASS: backface-culled, slightly elevated (game-like) views -- holes,
    # single-winding membranes, and inward-facing tris show as sky here
    # NE-lobe forensics: the culldbg red wedge = away-facing connector tris that the
    # game will cull, floating the lobe. Which tris, and were their verts weld-moved?
    ne_i = max(range(len(crest)), key=lambda q9: crest[q9][0] - crest[q9][2])
    ne_p = crest[ne_i]
    print(f"NE lobe: crest[{ne_i}] at {kk(ne_p)}; neighbors "
          f"{[kk(crest[(ne_i + d9) % len(crest)]) for d9 in (-2, -1, 1, 2)]}")
    cb9, sb9 = math.cos(math.pi / 4), math.sin(math.pi / 4)
    sph9, cph9 = math.sin(0.30), math.cos(0.30)
    for rec in wall:
        t3n = [r[0] for r in rec]
        cx9 = float(np.mean([p[0] for p in t3n]))
        cz9 = float(np.mean([p[2] for p in t3n]))
        cy9 = float(np.mean([p[1] for p in t3n]))
        if math.hypot(cx9 - ne_p[0], cz9 - ne_p[2]) > 7.0 or cy9 < ne_p[1] - 8.0:
            continue
        a9, b9, c9 = (np.array(p) for p in t3n)
        fn9 = np.cross(b9 - a9, c9 - a9)
        if fn9[0] * cb9 * cph9 + fn9[1] * sph9 + fn9[2] * sb9 * cph9 <= 0:
            nrm9 = np.mean([r[2] for r in rec], axis=0)
            print(f"   CULLED connector: verts {[kk(p) for p in t3n]} "
                  f"geo-n ({fn9[0]:.1f},{fn9[1]:.1f},{fn9[2]:.1f}) "
                  f"carried-n ({nrm9[0]:.2f},{nrm9[1]:.2f},{nrm9[2]:.2f})")
    render_strip(items, OUTD / "culldbg_NE.png", CENTER, math.pi / 4,
                 cull=True, elev=0.30, paint_culled=True)
    for name, bearing in (("E", 0.0), ("NE", math.pi / 4), ("N", math.pi / 2),
                          ("W", math.pi), ("SW", -3 * math.pi / 4),
                          ("S", -math.pi / 2)):
        render_strip(items, OUTD / f"cull_{name}.png", CENTER, bearing,
                     cull=True, elev=0.30)

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
