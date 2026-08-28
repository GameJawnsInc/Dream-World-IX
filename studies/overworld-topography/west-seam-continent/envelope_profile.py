"""THE PROFILE INSTRUMENT — measure a mountain's 3D shape, not its triangles.

Owner's diagnosis (take-7 post-mortem): stock mountains climb at a slope in a
specific range from ground to rim; the R4 arc's base was authored as walls that
chord down steeply instead of CONTINUING the face's own slope. Per-tri angles
cannot see this (a benched 50-deg-tri face has a much shallower envelope).

Statistic, per rock-grass foot station:
  march horizontally UPHILL from the contact point, sample the terrain surface
  (max-y over covering tris) every 2u:
    A1 = envelope angle over d in [0, 8]    (the base course zone)
    A2 = envelope angle over d in [8, 16]   (the lower body)
    A3 = envelope angle over d in [8, 24]   (the body proper)
    kink = A1 - A2                          (>0 = base steeper than what's above)

Corpora: all stock disc-1 land blocks (census cache) / the deployed R4 massif
split into the FAILED SW-arc window vs THE REST (contains owner-passed faces).
"""
import math
import pickle
import struct
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
WM = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
CACHE = HERE / "stock_tris.pkl"                    # rebuilt from the install if absent
WINDOW = (1412.0, -492.0, 1442.0, -460.0)         # the failed SW-arc window
SITE_BLOCKS = [(21, 5), (22, 5), (23, 5), (21, 6), (22, 6), (23, 6),
               (21, 7), (22, 7), (23, 7), (21, 8), (22, 8), (23, 8)]
ROCK, GRASS = 49, 0
STEPS = [i * 2.0 for i in range(13)]               # 0..24u


def read_loose(bx, by):
    p = WM / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
    if not p.is_file():
        return []
    d = p.read_bytes()
    _, vc, _, fl = struct.unpack_from("<iiii", d, 4)
    off = 20
    verts = [struct.unpack_from("<fff", d, off + i * 12) for i in range(vc)]
    off += vc * 12 + (vc * 12 if fl & 1 else 0) + vc * 8
    topos = [(int(round(struct.unpack_from("<f", d, off + i * 16)[0])) >> 2) & 0x3F
             for i in range(vc)]
    tris = []
    for t in range(vc // 3):
        i = t * 3
        p0, p1, p2 = ([bx * 64 + verts[i + k][0], verts[i + k][1],
                       verts[i + k][2] - by * 64] for k in range(3))
        tris.append((tuple(p0), tuple(p1), tuple(p2), topos[i]))
    return tris


class HeightField:
    """max-y surface over a triangle soup, 4u spatial hash on (x,z)."""

    def __init__(self, tris):
        self.tris = tris
        self.grid = defaultdict(list)
        for idx, (p0, p1, p2, tp) in enumerate(tris):
            xs = [p0[0], p1[0], p2[0]]
            zs = [p0[2], p1[2], p2[2]]
            for cx in range(int(min(xs) // 4), int(max(xs) // 4) + 1):
                for cz in range(int(min(zs) // 4), int(max(zs) // 4) + 1):
                    self.grid[(cx, cz)].append(idx)

    def h(self, x, z):
        best = None
        for idx in self.grid.get((int(x // 4), int(z // 4)), ()):
            p0, p1, p2, _ = self.tris[idx]
            d = ((p1[2] - p2[2]) * (p0[0] - p2[0])
                 + (p2[0] - p1[0]) * (p0[2] - p2[2]))
            if abs(d) < 1e-9:
                continue
            w0 = ((p1[2] - p2[2]) * (x - p2[0]) + (p2[0] - p1[0]) * (z - p2[2])) / d
            w1 = ((p2[2] - p0[2]) * (x - p2[0]) + (p0[0] - p2[0]) * (z - p2[2])) / d
            w2 = 1.0 - w0 - w1
            if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                continue
            y = w0 * p0[1] + w1 * p1[1] + w2 * p2[1]
            if best is None or y > best:
                best = y
        return best


def vkey(v):
    return (round(v[0], 3), round(v[1], 3), round(v[2], 3))


def stations(tris):
    """rock-grass shared edges -> (midpoint, uphill unit dir from the rock plane)."""
    edges = defaultdict(list)
    for ti, (p0, p1, p2, tp) in enumerate(tris):
        if tp not in (ROCK, GRASS):
            continue
        vs = (p0, p1, p2)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            k = tuple(sorted((vkey(vs[a]), vkey(vs[b]))))
            edges[k].append(ti)
    out = []
    for (ka, kb), tl in edges.items():
        tps = {tris[t][3] for t in tl}
        if tps != {ROCK, GRASS}:
            continue
        rt = next(t for t in tl if tris[t][3] == ROCK)
        p0, p1, p2, _ = tris[rt]
        # uphill = the rock plane's height-gradient direction
        ux = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        vx = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        nx = ux[1] * vx[2] - ux[2] * vx[1]
        ny = ux[2] * vx[0] - ux[0] * vx[2]
        nz = ux[0] * vx[1] - ux[1] * vx[0]
        if abs(ny) < 1e-9:
            continue
        gx, gz = -nx / ny, -nz / ny                  # grad of y(x,z) on the plane
        gl = math.hypot(gx, gz)
        if gl < 0.05:                                # near-flat rock: no uphill
            continue
        mx = (ka[0] + kb[0]) / 2.0
        mz = (ka[2] + kb[2]) / 2.0
        out.append((mx, mz, gx / gl, gz / gl))
    return out


def profiles(tris, keep=None):
    hf = HeightField([t for t in tris])
    res = []
    for mx, mz, dx, dz in stations(tris):
        if keep is not None and not keep(mx, mz):
            continue
        ys = []
        for d in STEPS:
            y = hf.h(mx + dx * d, mz + dz * d)
            if y is None:
                break
            ys.append(y)
        if len(ys) < 9:                              # need 0..16u at least
            continue
        a1 = math.degrees(math.atan2(ys[4] - ys[0], 8.0))
        a2 = math.degrees(math.atan2(ys[8] - ys[4], 8.0))
        a3 = math.degrees(math.atan2(ys[-1] - ys[4], STEPS[len(ys) - 1] - 8.0))
        rise16 = ys[8] - ys[0]
        res.append((mx, mz, a1, a2, a3, rise16))
    return res


def pct(v, p):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, int(p / 100.0 * len(s)))]


def report(name, rows, min_rise=4.0):
    rows = [r for r in rows if r[5] >= min_rise]     # real mountain feet only
    a1 = [r[2] for r in rows]
    a2 = [r[3] for r in rows]
    a3 = [r[4] for r in rows]
    kink = [r[2] - r[3] for r in rows]
    print(f"\n{name}: n={len(rows)} (feet rising >= {min_rise}u over 16u)")
    if not rows:
        return
    for lbl, v in (("A1 base 0-8u ", a1), ("A2 body 8-16u", a2),
                   ("A3 body 8-24u", a3), ("kink A1-A2   ", kink)):
        print(f"  {lbl}: p05 {pct(v, 5):6.1f}  p25 {pct(v, 25):6.1f}  "
              f"p50 {pct(v, 50):6.1f}  p75 {pct(v, 75):6.1f}  p95 {pct(v, 95):6.1f}")


def stock_tris():
    """all stock disc-1 land-block terrain tris as (p0, p1, p2, topo), cached."""
    if CACHE.is_file():
        with open(CACHE, "rb") as f:
            return pickle.load(f)
    sys.path.insert(0, str(REPO / "ff9mapkit"))
    from ff9mapkit.world import extract as X
    out = []
    for by in range(20):
        for bx in range(24):
            try:
                bm = X.read_block(bx, by, disc=1)
            except Exception:
                continue
            wv = [(bx * 64.0 + v[0], v[1], v[2] - by * 64.0) for v in bm.verts]
            ids = [int(round(t[0])) for t in bm.tangents]
            for a, b, c in bm.tris:
                out.append((wv[a], wv[b], wv[c], (ids[a] >> 2) & 0x3F))
    with open(CACHE, "wb") as f:
        pickle.dump(out, f, -1)
    return out


def main():
    stock = stock_tris()
    print(f"stock tris {len(stock)}")
    srows = profiles(stock)
    report("STOCK (all disc-1 rock feet)", srows)

    # the donor's home flank, as the nearest peer
    dset = {(5, 15), (5, 16), (6, 15), (6, 16)}
    dag = [r for r in srows
           if (int(r[0] // 64), int(math.floor(-r[1] / 64.0))) in dset]
    report("STOCK Daguerreo home flank", dag)

    site = []
    for bx, by in SITE_BLOCKS:
        site.extend(read_loose(bx, by))
    print(f"\nsite tris {len(site)}")
    rows = profiles(site)
    inw = [r for r in rows if WINDOW[0] <= r[0] <= WINDOW[2]
           and WINDOW[1] <= r[1] <= WINDOW[3]]
    outw = [r for r in rows if not (WINDOW[0] <= r[0] <= WINDOW[2]
                                    and WINDOW[1] <= r[1] <= WINDOW[3])]
    report("R4 massif — FAILED SW-arc window", inw)
    report("R4 massif — the rest (incl. owner-passed faces)", outw)
    # dump the window stations for a per-station look
    print("\nSW-window stations (x, z, A1, A2, A3, rise16):")
    for r in sorted(inw):
        print(f"  ({r[0]:7.1f},{r[1]:7.1f})  A1 {r[2]:5.1f}  A2 {r[3]:5.1f}  "
              f"A3 {r[4]:5.1f}  rise {r[5]:5.1f}")


if __name__ == "__main__":
    main()
