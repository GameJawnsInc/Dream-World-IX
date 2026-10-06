"""THE COAST-JOIN STUDY -- registered in COAST-JOIN-STUDY.md (read it first; nothing here is a gate).

S1 the fit (translate the rot-90 massif so its home forest-side coast lands on our coastline),
S2 stock cliff tops along a shore, S3 the two joins at the best seat, S4 the whole-island alternative.
Every part runs its positive control first; a failed control stops that part's report.

    py -X utf8 studies/overworld-topography/west-seam-continent/coast_join_study.py
"""
import json
import math
import re
import statistics as S
import struct
import sys
from collections import Counter, defaultdict
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
from rimwalk_stations import Ground                       # noqa: E402
from grass_step_study import raster, cell_of, GZ, GX       # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD_WM = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
FOREST, CROCK, GRASS = {36, 37}, 58, 0
HOST_BLOCKS = [(bx, by) for bx in (20, 21, 22, 23) for by in range(3, 11)]
HOME_BLOCKS = [(bx, by) for bx in range(3, 9) for by in range(13, 19)]
SEAS = ("sea1", "sea2", "sea3", "sea4", "sea5")
TOL_FIT = 4.0
END_PAD = 6


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p / 100 * len(v)))] if v else float("nan")


def verts_of(path, bx, by):
    if not path.is_file():
        return []
    d = path.read_bytes()
    _, vc, _, _ = struct.unpack_from("<iiii", d, 4)
    return [(lambda v: (v[0] + 64 * bx, v[1], v[2] - 64 * by))(struct.unpack_from("<fff", d, 20 + i * 12))
            for i in range(vc)]


def stock_tris(blocks):
    out = []
    for bx, by in blocks:
        try:
            bm = X.read_block(bx, by, disc=1)
        except Exception:
            continue
        ids = [((int(round(t4[0])) >> 2) & 0x3F) for t4 in bm.tangents]
        V = [(v[0] + 64 * bx, v[1], v[2] - 64 * by) for v in bm.verts]
        out.extend((V[a], V[b], V[c], ids[a]) for (a, b, c) in bm.tris)
    return out


def shore_edges(tris, skip_border=True):
    """grass|topo-58 shared edges and grass once-edges (grass straight onto the sea), as (p, q) pairs."""
    k = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))   # noqa: E731
    eds = defaultdict(list)
    for t in tris:
        p = t[:3]
        for i, j in ((0, 1), (1, 2), (2, 0)):
            eds[tuple(sorted((k(p[i]), k(p[j]))))].append(t[3])
    out = []
    for (a, b), tps in eds.items():
        if GRASS not in tps:
            continue
        others = [t for t in tps if t != GRASS]
        if len(tps) == 1:
            if skip_border and any(min(a[ax] % 64.0, 64 - a[ax] % 64.0) < 1e-3 and
                                   min(b[ax] % 64.0, 64 - b[ax] % 64.0) < 1e-3 for ax in (0, 2)):
                continue
            out.append((a, b))
        elif others and all(o == CROCK for o in others):
            out.append((a, b))
    return out


def chains(edges):
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    used, out = set(), []
    for a in adj:
        for b in adj[a]:
            e = tuple(sorted((a, b)))
            if e in used:
                continue
            used.add(e)
            ch = [a, b]
            for end in (1, 0):                             # extend from both ends through degree-2 verts
                while True:
                    tip = ch[-1] if end else ch[0]
                    prev = ch[-2] if end else ch[1]
                    nx = [n for n in adj[tip] if n != prev and tuple(sorted((tip, n))) not in used]
                    if len(adj[tip]) != 2 or not nx:
                        break
                    used.add(tuple(sorted((tip, nx[0]))))
                    if end:
                        ch.append(nx[0])
                    else:
                        ch.insert(0, nx[0])
                    if ch[0] == ch[-1]:
                        break
            out.append(ch)
    return out


def rim_change(chain_pts, dy=1.2, cap=64.0, win=4.0):
    """Per point: the shortest along-shore distance to a point dy higher/lower (None if not within cap),
    and the max |rim change| within +-win of shore."""
    s = [0.0]
    for p, q in zip(chain_pts, chain_pts[1:]):
        s.append(s[-1] + math.hypot(q[0] - p[0], q[2] - p[2]))
    ys = [p[1] for p in chain_pts]
    dist, mx = [], []
    n = len(chain_pts)
    for i in range(n):
        best = None
        m4 = 0.0
        for step_ in (1, -1):
            j = i + step_
            while 0 <= j < n and abs(s[j] - s[i]) <= cap:
                d = abs(s[j] - s[i])
                dd = abs(ys[j] - ys[i])
                if d <= win:
                    m4 = max(m4, dd)
                if dd >= dy:
                    if best is None or d < best:
                        best = d
                    if d > win:
                        break
                j += step_
        dist.append(best)
        mx.append(m4)
    return dist, mx, s[-1]


def main():
    # ================= S2 first (stock-only): its control, then the census =================
    print("==== S2: STOCK CLIFF TOPS ALONG A SHORE ====")
    step = [(float(i), 3.0 if i < 20 else 4.5, 0.0) for i in range(40)]
    ramp = [(float(i), 3.0 + 1.5 * min(1.0, max(0.0, (i - 20) / 16.0)), 0.0) for i in range(60)]
    ds, _, _ = rim_change(step)
    dr, _, _ = rim_change(ramp)
    c_step = min(d for d in ds if d is not None)
    c_ramp = min(d for d in dr if d is not None)
    s2_ctl = c_step <= 1.5 and 11.0 <= c_ramp <= 15.0
    print(f"  CONTROL: step reads {c_step:.1f}u, 16u ramp reads {c_ramp:.1f}u -> {'PASS' if s2_ctl else 'FAIL'}")
    allt = stock_tris(X.list_blocks(disc=1))
    ch = [c for c in chains(shore_edges(allt)) if len(c) >= 4]
    D, M, used = [], [], 0
    for c in ch:
        L = sum(math.hypot(q[0] - p[0], q[2] - p[2]) for p, q in zip(c, c[1:]))
        if L < 20.0 or max(p[1] for p in c) > 14.0:
            continue
        used += 1
        d_, m_, _ = rim_change(c)
        D += d_
        M += m_
    found = [d for d in D if d is not None]
    if s2_ctl and found:
        print(f"  {used} stock shore chains >= 20u; {len(D)} rim points. Distance to a >= 1.2u change: found on "
              f"{len(found) / len(D):.0%}; p10 {pct(found, 10):.1f} p50 {pct(found, 50):.1f}u. Max change per 4u: "
              f"p50 {pct(M, 50):.2f} p90 {pct(M, 90):.2f} p99 {pct(M, 99):.2f}u")
        s2 = pct(found, 10) >= 8.0 and pct(M, 90) <= 1.0
        print(f"  P-S2 -> {'HOLDS' if s2 else 'FAILS'}")
        rims = [p[1] for c in ch for p in c if p[1] <= 14.0]
        print(f"  stock shore rim height p10 {pct(rims, 10):.2f} p50 {pct(rims, 50):.2f} p90 {pct(rims, 90):.2f}")

    # ================= the frames: home (stock) + host (pre-massif) =================
    cal = json.loads((HERE / "sector_map.json").read_text(encoding="utf-8"))["calibration"]
    DY, rot = cal["DY"], cal["rot"] // 90
    B = IN._mountain_blob(DONOR, rock_topos=frozenset({49}), alcove_box=None, disc=1, log=lambda *_: None)
    rim, d_edge, blob, dtopo = B["rim"], B["d_edge"], B["blob"], B["dtopo"]
    c0, c1 = B["c_local"]
    ta, tb = B["ta"], B["tb"]

    def rot_v(dx, dz):
        for _ in range(rot):
            dx, dz = dz, -dx
        return dx, dz

    def place(x, y, z, T=(0.0, 0.0)):
        dx, dz = rot_v(x - c0, z - c1)
        return ((CENTRE[0] + T[0] + dx) % 1536.0, y - ta * (x - c0) - tb * (z - c1) + DY, CENTRE[1] + T[1] + dz)

    home = Ground([t for t in stock_tris(HOME_BLOCKS)])
    host_t = []
    for bx, by in HOST_BLOCKS:
        host_t.extend(read_ff9mesh(HOST_PRE / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh", bx, by))
    host = Ground(host_t)
    our_coast = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2) for a, b in shore_edges(host_t)]
    from scipy.spatial import cKDTree
    tree = cKDTree(np.array([(q[0], q[2]) for q in our_coast]))

    def coast_dist(x, z):
        """signed distance to our coastline: + inland (on host land), - seaward."""
        d, i = tree.query((x, z))
        on_land = host.top(x, z) is not None
        return (d if on_land else -d), our_coast[i]

    # rim stations (home frame) + outward normals, as in the grass-step study
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
            hx, hz, hy = pa[0] + ex * L * f, pa[2] + ez * L * f, pa[1] + (pb[1] - pa[1]) * f
            ox, oz = ez, -ex
            if IN.pip(hx + ox * 0.5, hz + oz * 0.5, rim_poly):
                ox, oz = -ox, -oz
            st.append({"x": hx, "y": hy, "z": hz, "ox": ox, "oz": oz, "forest": C in FOREST})
    n_st = len(st)
    run = [k for k in range(n_st) if st[k]["forest"]]
    # contiguous run in ring order (the sector map: ONE run); handle the wrap
    if run and run[0] == 0 and run[-1] == n_st - 1:
        gaps = [k for k in range(1, len(run)) if run[k] != run[k - 1] + 1]
        cut = gaps[0] if gaps else 0
        run = run[cut:] + run[:cut]
    fs, fe = run[0], run[-1]

    def home_coast(k, dmax=40.0):
        """march outward from station k at home: last grass before coastal rock/sea -> (x, y, z) home frame."""
        s = st[k]
        last = None
        d = 0.5
        while d <= dmax:
            x, z = s["x"] + s["ox"] * d, s["z"] + s["oz"] * d
            t = home.top(x, z)
            if t is None or t[1] == CROCK:
                return last
            if t[1] == GRASS:
                last = (x, t[0], z)
            d += 0.5
        return None

    fcoast = [(k, home_coast(k)) for k in run]
    fcoast = [(k, p) for k, p in fcoast if p is not None]
    print(f"\n==== S1: THE FIT ({len(fcoast)} of {len(run)} forest stations reach a home coast within 40u) ====")
    # the forest side's mean outward direction, placed
    ux = S.mean(rot_v(st[k]["ox"], st[k]["oz"])[0] for k in run)
    uz = S.mean(rot_v(st[k]["ox"], st[k]["oz"])[1] for k in run)
    L = math.hypot(ux, uz)
    ux, uz = ux / L, uz / L
    px, pz = -uz, ux
    # CONTROL: at T = 0 the home coast must read 40-65u inland of ours
    d0 = [coast_dist(*[place(*p)[i] for i in (0, 2)])[0] for _, p in fcoast]
    d0 = [d for d in d0 if d is not None]
    s1_ctl = bool(d0) and 40.0 <= S.median(d0) <= 65.0
    print(f"  CONTROL at T=0: home coast {S.median(d0):+.1f}u from our coastline (p10 {pct(d0, 10):+.1f}, p90 "
          f"{pct(d0, 90):+.1f}; + = inland) -> {'PASS' if s1_ctl else 'FAIL'}")
    ends = set(range(fs - END_PAD, fs + 1)) | set(range(fe, fe + END_PAD + 1))
    ends = {k % n_st for k in ends}
    body = [k for k in range(n_st) if not st[k]["forest"] and k not in ends]
    best, table = None, []
    for s_ in range(0, 82, 2):
        for l_ in range(-20, 24, 4):
            T = (ux * s_ + px * l_, uz * s_ + pz * l_)
            dd = [coast_dist(*[place(*p, T)[i] for i in (0, 2)])[0] for _, p in fcoast]
            share = sum(1 for d in dd if d is not None and abs(d) <= TOL_FIT) / len(fcoast)
            ok_body = True
            for k in body[::3]:
                q = place(st[k]["x"], st[k]["y"], st[k]["z"], T)
                cd, _ = coast_dist(q[0], q[2])
                if cd is None or cd < 6.0:
                    ok_body = False
                    break
            xs = [place(st[k]["x"], st[k]["y"], st[k]["z"], T)[0] for k in range(0, n_st, 4)]
            ok_seam = max(xs) <= 1536.0 - 8.0 and min(xs) > 64.0     # no wrap across the seam
            row = {"s": s_, "l": l_, "T": [round(T[0], 2), round(T[1], 2)], "share": round(share, 3),
                   "body_inside": ok_body, "seam_ok": ok_seam}
            table.append(row)
            if ok_body and ok_seam and (best is None or share > best["share"] + 1e-9
                                        or (abs(share - best["share"]) < 1e-9 and s_ < best["s"])):
                best = row
    top = sorted([r for r in table if r["body_inside"] and r["seam_ok"]], key=lambda r: -r["share"])[:5]
    for r in top:
        print(f"  seat s {r['s']:2d}u l {r['l']:+3d}u T ({r['T'][0]:+.1f},{r['T'][1]:+.1f}): {r['share']:.0%} of the home "
              f"coast within +-{TOL_FIT:.0f}u of ours")
    blocked = Counter(("body" if not r["body_inside"] else "") + ("seam" if not r["seam_ok"] else "")
                      for r in table if not (r["body_inside"] and r["seam_ok"]))
    print(f"  {len(table)} candidate seats; refused: {dict(blocked)}")
    s1 = bool(best) and best["share"] >= 0.6 and best["s"] <= 60
    print(f"  P-S1 -> {'HOLDS' if s1 and s1_ctl else 'FAILS'}" + ("" if best else " (no seat satisfies the constraints)"))

    # ================= S3: THE JOINS =================
    print("\n==== S3: THE JOINS AT THE BEST SEAT ====")
    our_y = S.median(q[1] for q in our_coast)
    home_fy = S.median(place(*p)[1] for _, p in fcoast)
    s3_ctl = abs(our_y - 3.20) <= 0.05 and 1.0 <= home_fy <= 1.8
    print(f"  CALIBRATION: our rim y p50 {our_y:.2f} (want 3.20); home forest-side rim (placed) p50 {home_fy:.2f} "
          f"(want ~1.4) -> {'PASS' if s3_ctl else 'FAIL'}")
    sea_home = {}
    for p_ in SEAS:
        vs = []
        for bx, by in HOME_BLOCKS:
            try:
                bm = X.read_block(bx, by, disc=1, part=p_)
            except Exception:
                continue
            vs += [(v[0] + 64 * bx, v[1], v[2] - 64 * by) for v in bm.verts]
        sea_home[p_] = vs
    sea_ours = {p_: [v for bx, by in HOST_BLOCKS for v in verts_of(HOST_PRE / f"r{by}" / f"Block[{bx}][{by}] {p_.capitalize()}.ff9mesh", bx, by)]
                for p_ in SEAS}

    def parts_near(pool, x, z, r=4.0):
        return sorted(p_ for p_, vs in pool.items() if any(math.hypot(v[0] - x, v[2] - z) <= r for v in vs))
    s3_rows = []
    if best:
        T = tuple(best["T"])
        for name, k in (("NW end", (fs - END_PAD) % n_st), ("SE end", (fe + END_PAD) % n_st)):
            hc = home_coast(k)
            if hc is None:
                print(f"  {name}: no home coast on the cut ray")
                continue
            q = place(*hc, T)
            cd, qc = coast_dist(q[0], q[2])
            # apron just inland: halfway along the ray at home
            s = st[k]
            dh = math.hypot(hc[0] - s["x"], hc[2] - s["z"]) / 2
            ht = home.top(s["x"] + s["ox"] * dh, s["z"] + s["oz"] * dh)
            ap = place(s["x"] + s["ox"] * dh, ht[0], s["z"] + s["oz"] * dh, T) if ht else None
            hl = host.top(ap[0], ap[2]) if ap else None
            hp = parts_near(sea_home, hc[0], hc[2])
            op = parts_near(sea_ours, qc[0], qc[2]) if qc else []
            dr = q[1] - (qc[1] if qc else 3.2)
            s3_rows.append({"end": name, "home_rim": round(q[1], 2), "our_rim": round(qc[1], 2) if qc else None,
                            "d_rim": round(dr, 2), "coast_gap": None if cd is None else round(cd, 1),
                            "apron": None if not ap else round(ap[1], 2), "lawn": None if not hl else round(hl[0], 2),
                            "apron_topo": None if not ht else ht[1], "home_seas": hp, "our_seas": op})
            print(f"  {name} (station {k}): home rim {q[1]:.2f} vs ours {qc[1] if qc else float('nan'):.2f} "
                  f"(delta {dr:+.2f}); home coast lands {cd:+.1f}u from ours; apron {ap[1] if ap else float('nan'):.2f} "
                  f"(topo {ht[1] if ht else None}) vs lawn {hl[0] if hl else float('nan'):.2f}; seas home {hp} / ours {op}")
        both = len(s3_rows) == 2 and all(r["home_rim"] <= 2.2 and abs(r["d_rim"]) >= 1.0 for r in s3_rows)
        print(f"  P-S3 -> {'HOLDS' if both and s3_ctl else 'FAILS'}")

    # ================= S4: THE WHOLE-ISLAND ALTERNATIVE =================
    print("\n==== S4: CARRY THE WHOLE HOME ISLAND ====")
    env = X._worldmap_env(1, None)
    pat = re.compile(r"worldmap/disc1/0_1/r\d+/block\[(\d+)\]\[(\d+)\] (\w+)")
    stock_parts = defaultdict(set)
    for k_ in env.container:
        m = pat.search((k_ or "").lower())
        if m:
            stock_parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))

    def mod_parts(bx, by):
        d = MOD_WM / f"r{by}"
        return sorted(p.name.split("] ", 1)[1].rsplit(".", 1)[0].lower() for p in d.glob(f"Block[[]{bx}[]][[]{by}[]] *.ff9mesh")) if d.is_dir() else []
    ctl = (21, 7)
    s4_ctl = "terrain" not in stock_parts.get(ctl, set()) and "terrain" in mod_parts(*ctl)
    print(f"  CONTROL block {ctl}: stock parts {sorted(stock_parts.get(ctl, set()))}, mod parts {mod_parts(*ctl)} "
          f"-> {'PASS' if s4_ctl else 'FAIL'}")
    H, TOP = raster()
    present = np.isfinite(H)
    lab, _ = ndi.label(present)
    ci, ri = cell_of(c0, c1)
    iid = lab[ri, ci]
    if iid == 0:                                           # the centre may sit on an aperture; take the rim
        ci, ri = cell_of(rim[0][0], rim[0][2])
        iid = lab[ri, ci]
    isl = lab == iid
    rr, cc = np.nonzero(isl)
    bxs = sorted({int(c * 2 // 64) for c in cc})
    bys = sorted({int(r * 2 // 64) for r in rr})
    foot = [(bx, by) for bx in range(min(bxs), max(bxs) + 1) for by in range(min(bys), max(bys) + 1)]
    foreign = 0
    for bx, by in foot:
        sl = (slice(by * 32, by * 32 + 32), slice(bx * 32, bx * 32 + 32))
        foreign += int((present[sl] & ~isl[sl]).sum())
    print(f"  the home island: {int(isl.sum())} land cells (~{isl.sum() * 4:.0f}u^2), x {cc.min() * 2}-{cc.max() * 2 + 2}, "
          f"z -{rr.max() * 2 + 2}..-{rr.min() * 2}; block footprint {len(bxs)}x{len(bys)} = {foot}; FOREIGN land "
          f"cells in that footprint: {foreign} (~{foreign * 4}u^2)")
    free = {}
    for bx in range(16, 21):
        for by in range(2, 12):
            free[(bx, by)] = not stock_parts.get((bx, by)) and not mod_parts(bx, by)
    print("  free blocks west of the continent (stock: no parts; mod: no overrides), cols 16-20 x rows 2-11:")
    for by in range(2, 12):
        print("    row %2d: " % by + " ".join(("." if free[(bx, by)] else "#") + str(bx) for bx in range(16, 21)))
    need = (len(bxs), len(bys))
    wins = []
    for bx in range(16, 21 - need[0] + 1):
        for by in range(2, 12 - need[1] + 1):
            if all(free.get((bx + i, by + j), False) for i in range(need[0]) for j in range(need[1])):
                wins.append((bx, by))
    print(f"  free {need[0]}x{need[1]} windows: {wins}")
    s4 = len(bxs) <= 3 and len(bys) <= 3 and foreign > 0 and bool(wins)
    print(f"  P-S4 -> {'HOLDS' if s4 and s4_ctl else 'FAILS'}")

    out = HERE / "coast_join_study.json"
    out.write_text(json.dumps({"fit_table": table, "best": best, "joins": s3_rows,
                               "island": {"footprint": foot, "foreign_cells": foreign, "free_windows": wins}},
                              indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
