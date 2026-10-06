"""THE GRASS-STEP STUDY -- registered in GRASS-STEP-STUDY.md (read it first; nothing here is a gate).

One 2u raster of every disc-1 terrain tri's TOP surface, then:
  A  the HOME EXEMPLAR -- the horseshoe donor's own neighbourhood, placed by the deployed carve
     transform and read relative to our lawn: outward transects from the forest-contact rim (P-A1)
     and tangential rings at 6u / 12u across the forest run's two ends (P-A2, P-A3);
  B  the STOCK VOCABULARY -- monotone all-grass transects between LEVEL grass cells 0.8-1.6u apart
     (P-B1), with co-location;
  C  THE COAST -- our west coast where the forest side faces it (P-C1, pre-massif host bytes) and
     stock coastal-cliff land heights (P-C2).

    py -X utf8 studies/overworld-topography/west-seam-continent/grass_step_study.py [--png OUT.png]
"""
import argparse
import json
import math
import statistics as S
import struct
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
from ff9mapkit.world import extract as X                  # noqa: E402
from ff9mapkit.world import interior as IN                # noqa: E402
from sector_map import read_ff9mesh, HOST_PRE, CENTRE, DONOR   # noqa: E402

CELL = 2.0
GX, GZ = 768, 640                                          # x 0..1536, z 0..-1280
LOWER_MAX = 14.0                                           # the lower altitude world (THE TERRACE LAW)
FOREST, MASSIF, CROCK, GRASS = {36, 37}, {49, 7, 62}, 58, 0
LAWN = 3.20                                                # the pre-massif host lawn at the site
LEVEL_RANGE = 0.2
STEP_MIN, STEP_MAX = 0.8, 1.6
MONO_TOL = 0.15
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1), (-1, 0), (0, -1), (-1, -1), (-1, 1)]
SITE = [(21, 5), (22, 5), (23, 5), (21, 6), (22, 6), (23, 6), (21, 7), (22, 7), (23, 7),
        (21, 8), (22, 8), (23, 8), (21, 9), (22, 9)]


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p / 100 * len(v)))] if v else float("nan")


def cell_of(x, z):
    return int(math.floor((x % 1536.0) / CELL)), int(math.floor(-z / CELL))


def raster():
    H = np.full((GZ, GX), -np.inf)
    TOP = np.full((GZ, GX), -1, dtype=np.int16)
    for bx, by in X.list_blocks(disc=1):
        try:
            bm = X.read_block(bx, by, disc=1)
        except Exception:
            continue
        ids = [((int(round(t4[0])) >> 2) & 0x3F) for t4 in bm.tangents]
        V = [(v[0] + 64 * bx, v[1], v[2] - 64 * by) for v in bm.verts]
        for (a, b, c) in bm.tris:
            p0, p1, p2 = V[a], V[b], V[c]
            d = (p1[2] - p2[2]) * (p0[0] - p2[0]) + (p2[0] - p1[0]) * (p0[2] - p2[2])
            if abs(d) < 1e-9:
                continue
            xs, zs = (p0[0], p1[0], p2[0]), (p0[2], p1[2], p2[2])
            for ci in range(int(math.floor(min(xs) / CELL)), int(math.floor(max(xs) / CELL)) + 1):
                for ri in range(int(math.floor(-max(zs) / CELL)), int(math.floor(-min(zs) / CELL)) + 1):
                    if not (0 <= ri < GZ):
                        continue
                    x, z = (ci + 0.5) * CELL, -(ri + 0.5) * CELL
                    w0 = ((p1[2] - p2[2]) * (x - p2[0]) + (p2[0] - p1[0]) * (z - p2[2])) / d
                    w1 = ((p2[2] - p0[2]) * (x - p2[0]) + (p0[0] - p2[0]) * (z - p2[2])) / d
                    w2 = 1.0 - w0 - w1
                    if min(w0, w1, w2) < -1e-6:
                        continue
                    y = w0 * p0[1] + w1 * p1[1] + w2 * p2[1]
                    cc = ci % GX
                    if y > H[ri, cc]:
                        H[ri, cc] = y
                        TOP[ri, cc] = ids[a]
    return H, TOP


def detect_steps(H, grass, D):
    """P-B1's detector, shape-generic so the self-test can run it on synthetic ground."""
    gz, gx = H.shape
    Hg = np.where(grass, H, np.nan)
    allg = ndi.uniform_filter(grass.astype(float), size=3, mode="wrap") > 0.999
    hmax = ndi.maximum_filter(np.where(grass, H, -1e9), size=3, mode="wrap")
    hmin = ndi.minimum_filter(np.where(grass, H, 1e9), size=3, mode="wrap")
    level = grass & allg & ((hmax - hmin) <= LEVEL_RANGE)
    steps, seen = [], set()
    for (dx, dz) in DIRS:
        stepu = CELL * math.hypot(dx, dz)
        kmax = int(40.0 // stepu)
        stack = [np.roll(np.roll(Hg, -j * dz, axis=0), -j * dx, axis=1) for j in range(kmax + 1)]
        gst = [np.roll(np.roll(grass, -j * dz, axis=0), -j * dx, axis=1) for j in range(kmax + 1)]
        lvk = [np.roll(np.roll(level, -j * dz, axis=0), -j * dx, axis=1) for j in range(kmax + 1)]
        rows = np.arange(gz)[:, None]
        found = np.zeros((gz, gx), bool)
        allg_up = gst[0].copy()
        H0 = stack[0]
        for k in range(1, kmax + 1):
            allg_up &= gst[k]
            if k * stepu < 8.0:
                continue
            valid_rows = (rows + k * dz >= 0) & (rows + k * dz < gz) & (rows >= 0)
            dH = stack[k] - H0
            cand = (~found) & level & lvk[k] & allg_up & valid_rows & (np.abs(dH) >= STEP_MIN) & (np.abs(dH) <= STEP_MAX)
            if not cand.any():
                continue
            sgn = np.sign(dH)
            mono = cand.copy()
            for j in range(0, k):
                stepd = sgn * (stack[j + 1] - stack[j])
                lo = sgn * (stack[j + 1] - H0)
                hi = sgn * (stack[k] - stack[j + 1])
                mono &= (stepd >= -MONO_TOL) & (lo >= -MONO_TOL) & (hi >= -MONO_TOL)
            for ri, ci in zip(*np.nonzero(mono)):
                prof = [stack[j][ri, ci] for j in range(k + 1)]
                Dlt = prof[-1] - prof[0]
                s_ = 1.0 if Dlt > 0 else -1.0
                frac = [s_ * (p - prof[0]) / abs(Dlt) for p in prof]
                j10 = next(j for j, f in enumerate(frac) if f >= 0.1)
                j50 = next(j for j, f in enumerate(frac) if f >= 0.5)
                j90 = next(j for j, f in enumerate(frac) if f >= 0.9)
                width = (j90 - j10) * stepu
                smax = max(math.degrees(math.atan(abs(prof[j + 1] - prof[j]) / stepu)) for j in range(k))
                mr, mc = ri + j50 * dz, (ci + j50 * dx) % gx
                key = (DIRS.index((dx, dz)) % 4, mr // 4, mc // 4)
                if key in seen:
                    continue
                seen.add(key)
                mx, mz = (mc + 0.5) * CELL, -(mr + 0.5) * CELL
                bdist = min(min(mx % 64.0, 64 - mx % 64.0), min((-mz) % 64.0, 64 - (-mz) % 64.0))
                steps.append({"at": (round(mx, 1), round(mz, 1)), "dH": round(abs(Dlt), 2), "len": round(k * stepu, 1),
                              "width": round(width, 1), "smax": round(smax, 1), "y_lo": round(min(prof[0], prof[-1]), 2),
                              "forest": float(D["forest"][mr, mc]), "massif": float(D["massif"][mr, mc]),
                              "crock": float(D["crock"][mr, mc]), "sea": float(D["sea"][mr, mc]), "border": bdist})
            found |= mono
    return steps, int(level.sum())


def selftest():
    """THE POSITIVE CONTROL: a detector that cannot see a lip cannot say stock has none. Synthetic ground:
    rows 5-25 a 1.2u LIP (one cell), rows 35-55 a 1.2u RAMP over 12u; everything else non-grass."""
    gz, gx = 60, 100
    H = np.full((gz, gx), 3.2)
    grass = np.zeros((gz, gx), bool)
    grass[5:26, 10:90] = True
    grass[35:56, 10:90] = True
    H[5:26, 50:] = 4.4                                      # the lip
    for c in range(44, 51):                                 # the ramp: 3.2 -> 4.4 over cols 44..50 (12u)
        H[35:56, c] = 3.2 + 1.2 * (c - 44) / 6.0
    H[35:56, 51:] = 4.4
    D = {k: np.full((gz, gx), 99.0) for k in ("forest", "massif", "crock", "sea")}
    steps, _ = detect_steps(H, grass, D)
    lip = [s for s in steps if -52.0 <= s["at"][1] <= -10.0]
    ramp = [s for s in steps if -112.0 <= s["at"][1] <= -70.0]
    lw = sorted({s["width"] for s in lip})
    rw = sorted({s["width"] for s in ramp})
    ok = bool(lip) and bool(ramp) and max(lw) <= 4.0 and min(rw) >= 8.0
    print(f"SELF-TEST: lip transects {len(lip)} widths {lw}; ramp transects {len(ramp)} widths {rw} -> "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if not selftest():
        sys.exit("the step detector failed its positive control -- nothing below would mean anything")
    if a.selftest:
        return
    H, TOP = raster()
    present = np.isfinite(H)
    lower = present & (H <= LOWER_MAX)
    grass = lower & (TOP == GRASS)
    forest = present & np.isin(TOP, list(FOREST))
    massif = present & np.isin(TOP, list(MASSIF))
    crock = present & (TOP == CROCK)
    sea = ~present
    print(f"raster {GX}x{GZ} @ {CELL}u: present {present.sum()}, lower-world grass {grass.sum()}, "
          f"forest {forest.sum()}, massif {massif.sum()}, coastal rock {crock.sum()}, sea {sea.sum()}")

    def dist(mask):                                        # u to the nearest mask cell (x wraps: pad)
        pad = np.concatenate([mask[:, -64:], mask, mask[:, :64]], axis=1)
        d = ndi.distance_transform_edt(~pad) * CELL
        return d[:, 64:-64]
    D = {"forest": dist(forest), "massif": dist(massif), "crock": dist(crock), "sea": dist(sea)}

    # ================= B: THE STOCK VOCABULARY =================
    steps, n_level = detect_steps(H, grass, D)
    print(f"level grass cells: {n_level}")
    print(f"\n==== B: STOCK OPEN-GRASS STEPS 0.8-1.6u between level grass: {len(steps)} (de-duplicated) ====")
    if steps:
        W = [s["width"] for s in steps]
        SM = [s["smax"] for s in steps]
        lips = sum(1 for w in W if w <= 4.0) / len(W)
        print(f"  width (10-90%) p10 {pct(W, 10):.1f} p25 {pct(W, 25):.1f} p50 {pct(W, 50):.1f} p75 {pct(W, 75):.1f} "
              f"p90 {pct(W, 90):.1f}u; lips (<= 4u) {lips:.0%}")
        print(f"  max slope p50 {pct(SM, 50):.1f} p90 {pct(SM, 90):.1f} deg; dH p50 {pct([s['dH'] for s in steps], 50):.2f}")
        verdict = pct(W, 50) >= 8.0 and pct(SM, 90) <= 20.0 and lips < 0.10
        print(f"  P-B1 -> {'HOLDS' if verdict else 'FAILS'}")
        co = Counter()
        for s in steps:
            tags = [t for t, ok in (("forest<=4u", s["forest"] <= 4), ("massif<=4u", s["massif"] <= 4),
                                    ("coastrock<=6u", s["crock"] <= 6), ("sea<=8u", s["sea"] <= 8),
                                    ("border<=2u", s["border"] <= 2)) if ok]
            co[" + ".join(tags) if tags else "open"] += 1
        print("  co-location: " + ", ".join(f"{k} {v / len(steps):.0%}" for k, v in co.most_common(8)))
        near_sea = [s for s in steps if s["sea"] <= 24]
        if near_sea:
            print(f"  steps within 24u of the sea: {len(near_sea)}, width p50 {pct([s['width'] for s in near_sea], 50):.1f}u, "
                  f"lower side y p50 {pct([s['y_lo'] for s in near_sea], 50):.2f}")
        near_f = [s for s in steps if s["forest"] <= 4]
        if near_f:
            print(f"  steps within 4u of a forest: {len(near_f)}, width p50 {pct([s['width'] for s in near_f], 50):.1f}u")

    # ================= A: THE HOME EXEMPLAR =================
    cal = json.loads((HERE / "sector_map.json").read_text(encoding="utf-8"))["calibration"]
    DY, rot = cal["DY"], cal["rot"] // 90
    B = IN._mountain_blob(DONOR, rock_topos=frozenset({49}), alcove_box=None, disc=1, log=lambda *_: None)
    rim, d_edge, blob, dtopo = B["rim"], B["d_edge"], B["blob"], B["dtopo"]
    c0, c1 = B["c_local"]
    ta, tb = B["ta"], B["tb"]

    def rel(x, y, z):
        return (y - ta * (x - c0) - tb * (z - c1) + DY) - LAWN

    def sample(x, z):
        ci, ri = cell_of(x, z)
        if not (0 <= ri < GZ):
            return "none", None
        if sea[ri, ci]:
            return "sea", None
        y = H[ri, ci]
        t = TOP[ri, ci]
        cls = ("forest" if t in FOREST else "massif" if t in MASSIF else "crock" if t == CROCK
               else "grass" if t == GRASS else f"topo{t}")
        return cls, rel(x, y, z)

    rim_poly = [(p[0], p[2]) for p in rim]
    st = []
    for i in range(len(rim)):
        pa, pb = rim[i], rim[(i + 1) % len(rim)]
        L = math.hypot(pb[0] - pa[0], pb[2] - pa[2])
        if L < 1e-6:
            continue
        out = [t for t in d_edge.get(tuple(sorted((pa, pb))), []) if t not in blob]
        C = dtopo[out[0]] if out else None
        ex, ez = (pb[0] - pa[0]) / L, (pb[2] - pa[2]) / L
        n = max(1, int(math.ceil(L)))
        for s in range(n):
            f = (s + 0.5) / n
            hx, hz = pa[0] + ex * L * f, pa[2] + ez * L * f
            ox, oz = ez, -ex
            if IN.pip(hx + ox * 0.5, hz + oz * 0.5, rim_poly):
                ox, oz = -ox, -oz
            st.append({"x": hx, "z": hz, "ox": ox, "oz": oz, "forest": C in FOREST})
    fidx = [k for k, s in enumerate(st) if s["forest"]]
    # the forest run is contiguous (the sector map): its two ends in ring order
    n_st = len(st)
    runs, cur = [], []
    for k in range(n_st):
        if st[k]["forest"]:
            cur.append(k)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    if len(runs) > 1 and st[0]["forest"] and st[-1]["forest"]:
        runs[0] = runs.pop() + runs[0]
    run = max(runs, key=len)
    fs, fe = run[0], run[-1]
    print(f"\n==== A: THE HOME EXEMPLAR (horseshoe, placed: rot {rot * 90}, DY {DY:+.4f}; rel to our lawn {LAWN}) ====")
    print(f"  rim stations {n_st}; forest-contact run {len(run)} stations (ring idx {fs}..{fe})")

    # P-A1: outward transects from the forest run
    a1_ok, a1_rows = 0, []
    for k in run:
        s = st[k]
        came_back = reached = False
        prof = []
        for d in range(2, 42, 2):
            cls, r_ = sample(s["x"] + s["ox"] * d, s["z"] + s["oz"] * d)
            prof.append((d, cls, None if r_ is None else round(r_, 2)))
            if cls in ("crock", "sea"):
                reached = True
                break
            if cls == "grass" and r_ is not None and r_ >= -0.3:
                came_back = True
                break
        a1_ok += (not came_back)
        a1_rows.append({"k": k, "came_back": came_back, "reached_coast": reached, "prof": prof})
    a1 = a1_ok / len(run)
    print(f"  P-A1 outward: no return to terrace on {a1:.0%} of {len(run)} forest-run stations; reached coast rock/sea "
          f"within 40u on {sum(r['reached_coast'] for r in a1_rows) / len(run):.0%}  -> {'HOLDS' if a1 >= 0.8 else 'FAILS'}")
    for r in a1_rows[::max(1, len(a1_rows) // 6)]:
        print("    " + " ".join(f"{d}:{c[0]}{'' if v is None else f'{v:+.1f}'}" for d, c, v in r["prof"]))

    # P-A2 / P-A3: tangential rings at 6u and 12u across the run's two ends
    a2_cov, a3_widths, ring_rows = [], [], []
    for off in (6.0, 12.0):
        ring = []
        for k in range(n_st):
            s = st[k]
            x, z = s["x"] + s["ox"] * off, s["z"] + s["oz"] * off
            cls, r_ = sample(x, z)
            ring.append((x, z, cls, r_))
        for end, direction in (("NW/start", +1), ("SE/end", -1)):
            e0 = fs if direction > 0 else fe
            # walk from 25 stations on the grass side, INTO the run, to 25 stations past the end
            idxs = [(e0 - direction * 25 + direction * j) % n_st for j in range(0, 51 + len(run))]
            i_hi = None
            for pos, k in enumerate(idxs):
                cls, r_ = ring[k][2], ring[k][3]
                if cls == "grass" and r_ is not None and r_ >= -0.3:
                    i_hi = pos
                if pos > 25 + 4 and i_hi is not None:
                    break
            if i_hi is None:
                ring_rows.append((off, end, "no terrace-level grass on this ring", None))
                continue
            i_lo = next((pos for pos in range(i_hi + 1, len(idxs))
                         if ring[idxs[pos]][2] == "grass" and ring[idxs[pos]][3] is not None
                         and ring[idxs[pos]][3] <= -0.9), None)
            span = idxs[i_hi + 1:(i_lo if i_lo is not None else len(idxs))]
            if not span:
                continue
            cov = sum(1 for k in span if ring[k][2] == "forest") / len(span)
            vis = [k for k in span if ring[k][2] == "grass" and ring[k][3] is not None and -0.9 < ring[k][3] < -0.3]
            vis_w = sum(math.hypot(ring[k][0] - ring[(k + 1) % n_st][0], ring[k][1] - ring[(k + 1) % n_st][1]) for k in vis)
            a2_cov.append(cov)
            if vis:
                a3_widths.append(vis_w)
            ring_rows.append((off, end, f"crossing over {len(span)} samples "
                                        f"({'reaches shelf grass' if i_lo is not None else 'shelf grass never surfaces on this ring'}): "
                                        f"forest-covered {cov:.0%}, open-grass transition {vis_w:.1f}u", cov))
    for off, end, txt, _ in ring_rows:
        print(f"  ring {off:.0f}u {end}: {txt}")
    a2 = bool(a2_cov) and min(a2_cov) >= 0.7
    print(f"  P-A2 -> {'HOLDS' if a2 else 'FAILS'} (min coverage {min(a2_cov) if a2_cov else float('nan'):.0%})")
    print(f"  P-A3 -> " + ("n/a (no open-grass part)" if not a3_widths else
                           f"{'HOLDS' if min(a3_widths) >= 8 else 'FAILS'} (open-grass widths {[round(w, 1) for w in a3_widths]})"))

    # ================= C: THE COAST =================
    host = []
    for bx, by in SITE:
        host.extend(read_ff9mesh(HOST_PRE / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh", bx, by))
    beach = []
    for bx, by in SITE:
        p = HOST_PRE / f"r{by}" / f"Block[{bx}][{by}] Beach1.ff9mesh"
        if p.is_file():
            d = p.read_bytes()
            _, vc, _, _ = struct.unpack_from("<iiii", d, 4)
            for i in range(vc):
                v = struct.unpack_from("<fff", d, 20 + i * 12)
                beach.append((v[0] + 64 * bx, v[1], v[2] - 64 * by))
    from rimwalk_stations import Ground
    hg = Ground(host)
    sm = json.loads((HERE / "sector_map.json").read_text(encoding="utf-8"))["stations"]
    rays = [s for s in sm if s["forest"]]
    c1_ok, c_rows = 0, []
    for s in rays:
        x, z = s["w"]
        ux, uz = x - CENTRE[0], z - CENTRE[1]
        L = math.hypot(ux, uz)
        ux, uz = ux / L, uz / L
        last, lastd, tail = None, None, []
        for d in np.arange(1.0, 160.0, 0.5):
            t = hg.top(x + ux * d, z + uz * d)
            if t is None:
                break
            last, lastd = t, d
            tail.append((d, t[0], t[1]))
        tail10 = [q for q in tail if q[0] >= lastd - 10]
        flat = max(q[1] for q in tail10) - min(q[1] for q in tail10) if tail10 else None
        edge = (x + ux * lastd, z + uz * lastd)
        nb = min((math.hypot(b[0] - edge[0], b[2] - edge[1]) for b in beach), default=float("inf"))
        topos = Counter(q[2] for q in tail10)
        cliff = flat is not None and flat <= 1.0 and nb > 8.0
        c1_ok += cliff
        c_rows.append({"edge": edge, "dist": lastd, "tail10_range": flat, "tail_topos": dict(topos),
                       "beach_dist": nb, "edge_y": last[0] if last else None})
    print(f"\n==== C: THE COAST ====")
    print(f"  our west coast, {len(rays)} forest-side rays: edge at {pct([r['dist'] for r in c_rows], 50):.0f}u from the rim "
          f"(p10 {pct([r['dist'] for r in c_rows], 10):.0f}, p90 {pct([r['dist'] for r in c_rows], 90):.0f}); last-10u height range "
          f"p50 {pct([r['tail10_range'] for r in c_rows], 50):.2f}; edge y p50 {pct([r['edge_y'] for r in c_rows], 50):.2f}; "
          f"nearest Beach1 vert p50 {pct([r['beach_dist'] for r in c_rows], 50):.1f}u; tail topos {sum((Counter(r['tail_topos']) for r in c_rows), Counter()).most_common(4)}")
    print(f"  P-C1 cliff-class on {c1_ok / len(rays):.0%}  -> {'HOLDS' if c1_ok / len(rays) >= 0.7 else 'FAILS'}")
    # grass within 6u of a coastal-rock cell that is itself within 6u of sea
    crock_coastal = crock & (D["sea"] <= 6.0)
    dcc = dist(crock_coastal)
    cl = H[grass & (dcc <= 6.0)]
    print(f"  stock coastal-cliff land (grass within 6u of sea-side topo-58): n {cl.size}, height p10 {np.percentile(cl, 10):.2f} "
          f"p25 {np.percentile(cl, 25):.2f} p50 {np.percentile(cl, 50):.2f} p90 {np.percentile(cl, 90):.2f}; share <= 2.2u "
          f"{(cl <= 2.2).mean():.0%}  -> P-C2 {'HOLDS' if np.percentile(cl, 10) <= 2.2 else 'FAILS'}")
    # the home's own coastal drop (abs height of the shelf grass just before coastal rock on the A1 transects)
    home_shelf = []
    for r in a1_rows:
        g_ = [v for d, c, v in r["prof"] if c == "grass" and v is not None]
        if r["reached_coast"] and g_:
            home_shelf.append(g_[-1] + LAWN)
    if home_shelf:
        print(f"  the home shelf's last grass before its coastal drop: abs y p50 {S.median(home_shelf):.2f} "
              f"(n {len(home_shelf)}) -- vs our coast's edge y above")

    out = HERE / "grass_step_study.json"
    out.write_text(json.dumps({"steps": steps, "home_outward": a1_rows,
                               "rings": [(o, e, t) for o, e, t, _ in ring_rows], "coast": c_rows},
                              indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {out}")

    if a.png:
        from PIL import Image, ImageDraw
        xs = [s["x"] for s in st]
        zs = [s["z"] for s in st]
        x0, x1, z0, z1 = min(xs) - 45, max(xs) + 45, min(zs) - 45, max(zs) + 45
        sc = 6
        Wd, Ht = int((x1 - x0) * sc), int((z1 - z0) * sc)
        im = Image.new("RGB", (Wd, Ht), (20, 30, 60))
        dr = ImageDraw.Draw(im)
        for ri in range(int(-z1 // CELL), int(-z0 // CELL) + 1):
            for ci in range(int(x0 // CELL), int(x1 // CELL) + 1):
                if not (0 <= ri < GZ):
                    continue
                cc = ci % GX
                x, z = (ci + 0.5) * CELL, -(ri + 0.5) * CELL
                px, pz = (x - x0) * sc, (z1 - z) * sc
                box = [px - CELL * sc / 2, pz - CELL * sc / 2, px + CELL * sc / 2, pz + CELL * sc / 2]
                if sea[ri, cc]:
                    continue
                t = TOP[ri, cc]
                r_ = rel(x, H[ri, cc], z)
                if t in FOREST:
                    col = (20, 90, 35)
                elif t in MASSIF:
                    col = (110, 105, 100)
                elif t == CROCK:
                    col = (150, 120, 90)
                else:                                       # grass: terrace (>= -0.3) light, shelf (<= -0.9) dark
                    k_ = max(0.0, min(1.0, (r_ + 1.5) / 2.0))
                    col = (int(60 + 150 * k_), int(110 + 120 * k_), int(40 + 60 * k_))
                    if -0.9 < r_ < -0.3:
                        col = (230, 120, 40)                # the transition band, highlighted
                dr.rectangle(box, fill=col)
        for s in st:
            px, pz = (s["x"] - x0) * sc, (z1 - s["z"]) * sc
            dr.ellipse([px - 2, pz - 2, px + 2, pz + 2], fill=(220, 60, 200) if s["forest"] else (240, 220, 80))
        dr.text((6, 6), "HOME (stock), north up -- grass shaded by height vs our lawn (light = terrace, dark = shelf), "
                        "orange = transition grass -0.9..-0.3, dark green = forest, grey = massif, tan = coastal rock, "
                        "blue = sea; rim dots magenta = forest contact", fill=(255, 255, 255))
        im.save(a.png)
        print(f"wrote {a.png}")


if __name__ == "__main__":
    main()
