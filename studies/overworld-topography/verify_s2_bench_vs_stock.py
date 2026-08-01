"""PASS 2 of the S2 adversarial re-measurement -- the CORRECTION.

T1 established that the LIVE round-8 bench holds ZERO grass.D (4212 grass.main + 10
grass.B + 3 residual over 4225 ground tris), so the claim's headline build implication
(a) "FORBIDDEN: grass.main|grass.D" targets a boundary that is not in the build. That
kills the corollary but leaves the real question open, so this pass measures the axis
the claim declared closed:

  P1 WITHIN-grass.main CONTRAST. The claim's corollary says a grass.main-to-grass.main
     boundary "is this instrument's own invisible control", so the seam cannot be a
     tiling problem. Test it in the claim's OWN currency: the per-edge atlas-luminance
     step between two grass.main tris, stock disc-1 vs the deployed bench. If the
     bench's own within-main butts are hotter than stock's, the tiling IS still off
     at the art-set-internal level.

  P2 THE QUADRANT / TILE VOCABULARY. grass.main is a 2x2 quadrant set. Which quadrants
     does stock use, in what mix, and with what neighbour policy? Which does the bench
     use? A same-set boundary is invisible only if the QUADRANT PAIRING is in-language.

  P3 THE 4u-CELL / ONE-TILE INVARIANT. Per 4u cell, how many distinct main quadrants
     do the tris sample -- stock vs bench? A cell that mixes quadrants cuts a tile
     boundary through the cell interior (grassland.py's own "MIXED cells" note).

  P4 THE >64u OPEN-GROUND COUNTEREXAMPLE, sized. The claim forbids an art-set boundary
     bounding a field >32u across (93.8% <=32u). T5 found 30 disc-1 open featureless
     edges bounding a >64u patch. Measure those sites properly: both sides' patch
     extents, the contiguous run length, and the same for the whole desert|scrub
     ecotone -- the longest art-set boundary stock ships.

Read-only. Artifact -> out/verify_s2_bench_vs_stock.json
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit import config                                   # noqa: E402
from ff9mapkit.world import atlas as A                         # noqa: E402
from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import grassland as G                     # noqa: E402
from ff9mapkit.world import mesh as MSH                        # noqa: E402

OUT = Path(__file__).with_name("out") / "verify_s2_bench_vs_stock.json"

GU, GV = G.GRASS_U_HALF, G.GRASS_V_HALF
MAIN = G.FAM_REGION["main"]
GRASS_TOPO = {0, 1, 2, 3, 10, 11, 12, 13, 42, 59}

_im = A.load_atlas("terrain")
if isinstance(_im, tuple):
    _im = _im[0]
AR = np.asarray(_im.convert("RGB"), dtype=float)
AH, AW = AR.shape[:2]


def tri_L(uvs):
    u = sum(q[0] for q in uvs) / 3.0
    v = sum(q[1] for q in uvs) / 3.0
    px = int((u % 1.0) * AW) % AW
    py = int((1.0 - (v % 1.0)) * AH) % AH
    r, g, b = AR[py, px]
    return 0.299 * r + 0.587 * g + 0.114 * b


def quad_of(uvs):
    """Which of grass.main's 4 quadrants does the tri's uv CENTROID sit in? (None = outside.)"""
    u = sum(q[0] for q in uvs) / 3.0
    v = sum(q[1] for q in uvs) / 3.0
    qu = 0 if GU[0][0] <= u <= GU[0][1] else 1 if GU[1][0] <= u <= GU[1][1] else None
    qv = 0 if GV[0][0] <= v <= GV[0][1] else 1 if GV[1][0] <= v <= GV[1][1] else None
    if qu is None or qv is None:
        return "gutter" if MAIN[0] <= u <= MAIN[2] and MAIN[1] <= v <= MAIN[3] else None
    return f"q{qu}{qv}"


kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))       # noqa: E731
pct = lambda a, q: round(float(np.percentile(a, q)), 2) if len(a) else None   # noqa: E731


def collect(blocks, reader, label):
    tris = []                        # (world verts, uv, topo, L, quad)
    edge = defaultdict(list)
    for (bx, by) in blocks:
        try:
            bm = reader(bx, by)
        except Exception:                                          # noqa: BLE001
            continue
        if bm is None:
            continue
        V, U, T, fi = bm.verts, bm.uvs, bm.tangents, bm.flat_index
        ox, oz = 64.0 * bx, -64.0 * by
        for t in range(len(fi) // 3):
            idx = fi[3 * t:3 * t + 3]
            topo = X.decode_id(int(round(T[idx[0]][0])))["topograph"]
            if topo not in GRASS_TOPO:
                continue
            uv = [(float(U[j][0]), float(U[j][1])) for j in idx]
            u = sum(q[0] for q in uv) / 3.0
            v = sum(q[1] for q in uv) / 3.0
            if not (MAIN[0] <= u <= MAIN[2] and MAIN[1] <= v <= MAIN[3]):
                continue                                  # grass.main ONLY (B/D excluded)
            w = [(V[j][0] + ox, V[j][1], V[j][2] + oz) for j in idx]
            gi = len(tris)
            tris.append((w, uv, topo, tri_L(uv), quad_of(uv)))
            ks = [kk(p) for p in w]
            for i in range(3):
                e = tuple(sorted((ks[i], ks[(i + 1) % 3])))
                if e[0] != e[1]:
                    edge[e].append(gi)
    print(f"[{label}] grass.main tris {len(tris)}")
    return tris, edge


def report(tris, edge, label):
    # P1 -- within-grass.main per-edge luminance step
    dLs, same_q, diff_q = [], [], []
    for e, o in edge.items():
        if len(o) != 2:
            continue
        a, b = o
        d = abs(tris[a][3] - tris[b][3])
        dLs.append(d)
        (same_q if tris[a][4] == tris[b][4] else diff_q).append(d)
    print(f"   P1 within-grass.main dL: n={len(dLs)} med {pct(dLs, 50)} p75 {pct(dLs, 75)} "
          f"p90 {pct(dLs, 90)} mean {round(float(np.mean(dLs)), 2)}")
    print(f"      same-quadrant butts n={len(same_q)} med {pct(same_q, 50)}  |  "
          f"cross-quadrant butts n={len(diff_q)} med {pct(diff_q, 50)}  "
          f"(cross-quadrant share {len(diff_q) / max(1, len(dLs)):.1%})")
    # P2 -- quadrant mix + neighbour policy
    qc = Counter(t[4] for t in tris)
    tot = max(1, sum(qc.values()))
    print(f"   P2 quadrant mix: " + ", ".join(f"{k}={v}({v / tot:.1%})" for k, v in qc.most_common()))
    # P3 -- distinct quadrants per 4u cell
    cellq = defaultdict(set)
    for (w, uv, topo, L, q) in tris:
        cx = int(sum(p[0] for p in w) / 3.0 // 4)
        cz = int(sum(p[2] for p in w) / 3.0 // 4)
        cellq[(cx, cz)].add(q)
    nc = Counter(len(v) for v in cellq.values())
    ncells = max(1, len(cellq))
    mixed = sum(v for k, v in nc.items() if k > 1)
    print(f"   P3 4u cells {ncells}; distinct main quadrants per cell {dict(sorted(nc.items()))}; "
          f"MIXED-quadrant cells {mixed} = {mixed / ncells:.1%}")
    # uv rate: duv per world unit (density check)
    dens = []
    for (w, uv, topo, L, q) in tris:
        for i in range(3):
            j = (i + 1) % 3
            dp = math.hypot(w[j][0] - w[i][0], w[j][2] - w[i][2])
            du = math.hypot(uv[j][0] - uv[i][0], uv[j][1] - uv[i][1])
            if dp > 0.5:
                dens.append(du / dp)
    print(f"   uv density (per plan unit): n={len(dens)} med {round(float(np.median(dens)), 5)} "
          f"p10 {round(float(np.percentile(dens, 10)), 5)} "
          f"p90 {round(float(np.percentile(dens, 90)), 5)}  (stock constant 0.01087)")
    return dict(n_tris=len(tris), dL=dict(n=len(dLs), med=pct(dLs, 50), p75=pct(dLs, 75),
                                          p90=pct(dLs, 90),
                                          mean=round(float(np.mean(dLs)), 2) if dLs else None),
                dL_same_quad=dict(n=len(same_q), med=pct(same_q, 50)),
                dL_cross_quad=dict(n=len(diff_q), med=pct(diff_q, 50),
                                   share=round(len(diff_q) / max(1, len(dLs)), 4)),
                quad_mix={str(k): v for k, v in qc.most_common()},
                cells=ncells, quads_per_cell={str(k): v for k, v in sorted(nc.items())},
                mixed_cell_share=round(mixed / ncells, 4),
                uv_density=dict(med=round(float(np.median(dens)), 5) if dens else None,
                                p10=round(float(np.percentile(dens, 10)), 5) if dens else None,
                                p90=round(float(np.percentile(dens, 90)), 5) if dens else None))


t0 = time.time()
RES = {}
GAME = config.find_game_path(None)


def bench_reader(bx, by):
    p = GAME / "FF9CustomMap-world" / MSH.override_relpath(9, bx, by, "0_1", "Terrain")
    return (MSH.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, lod="0_1", part="terrain")
            if p.is_file() else None)


print("=" * 92)
print("STOCK DISC 1 -- grass.main only")
st, se = collect(X.list_blocks(disc=1), lambda a, b: X.read_block(a, b, disc=1), "stock d1")
RES["stock_disc1"] = report(st, se, "stock d1")

print("\nDONOR BLOCK (15,14) alone -- the mesa's own grass")
dn, de = collect([(15, 14)], lambda a, b: X.read_block(a, b, disc=1), "donor 15,14")
RES["donor_15_14"] = report(dn, de, "donor")

print("\n" + "=" * 92)
print("THE LIVE ROUND-8 BENCH (deployed Disc9 (5..7)x(7..8))")
bt, be = collect([(x, y) for x in (5, 6, 7) for y in (7, 8)], bench_reader, "bench d9")
RES["bench_round8"] = report(bt, be, "bench")

# ---- P4 the >64u open-ground counterexample, sized ------------------------------------------
print("\n" + "=" * 92)
print("P4  THE >64u OPEN-GROUND ART-SET BOUNDARY (build_implication (b)'s counterexample)")
print("=" * 92)
prev = json.loads((Path(__file__).with_name("out") / "verify_s2_family_boundary.json").read_text())
for disc, node in (("disc1", prev["T3_disc1"]["centroid"]), ("disc4", prev["T2_disc4"]["centroid"])):
    pe = node["per_set_patch_extent"]
    print(f"   {disc} per-set largest contiguous patch EXTENT (u across):")
    for s, v in sorted(pe.items(), key=lambda q: -(q[1]["max"] or 0)):
        print(f"      {s:12s} patches {v['n']:4d}  extent med {v['med']}u  MAX {v['max']}u")
    print(f"   {disc} featureless-open boundary: smaller-side patch extent med "
          f"{node['open_ext_min']['med']}u p90 {node['open_ext_min']['p90']}u  >64u "
          f"{node['open_ext_min']['gt64']:.1%} (n={node['open_ext_min']['n']})")
    print(f"   {disc} open-ground CHAINS: n={node['open_chains']['n']} med "
          f"{node['open_chains']['med']}u p90 {node['open_chains']['p90']}u MAX "
          f"{node['open_chains']['max']}u")
    print(f"   {disc} >64u sites: {node['big_open_sites'][:8]}")
RES["P4"] = dict(note="see verify_s2_family_boundary.json per_set_patch_extent / open_chains")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(RES, indent=0, default=str))
print(f"\nartifact -> {OUT}\ntotal {time.time() - t0:.0f}s")
