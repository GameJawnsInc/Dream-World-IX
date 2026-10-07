"""VERIFIER (adversarial) -- an INDEPENDENT T-junction / near-T / near-miss scan for S1, written from scratch
in numpy (brute force per block, no spatial hash, 8 torus neighbours instead of 4), so a bug in
stitch_census.tjunctions' grid bucketing / frame filter cannot hide a T-junction.

For every block: all unique edges of every part of the block (world frame, unwrapped); all unique vertex
positions of every part of the block AND its 8 torus neighbours, shifted into this block's unwrapped frame.
A vertex q is a T-vertex of edge ab iff its 3D distance to the open segment is < EPS_T, the foot parameter is
strictly inside (1e-6, 1-1e-6) and q is not (within 1e-4) an endpoint. Also histograms the vertex-edge distance
of every non-endpoint pair in (0, 0.1u) -- the margin above the lane's 1e-3 threshold.
Positive control: a synthetic vertex at the midpoint of a real (7,17) Terrain edge must be found.
Writes out/verify_tjunction_numpy.json.   Run: py <this file>
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402

EPS_T = 1e-3
BINS = [0, 1e-4, 1e-3, 5e-3, 1e-2, 5e-2, 1e-1]


def block_edges(M, blk):
    out = []                       # (part, a, b)
    for (x, y, p), m in M.items():
        if (x, y) != blk:
            continue
        seen = set()
        V, fi = m.wv, m.fi
        for t in range(len(fi) // 3):
            cs = [V[fi[3 * t + k]] for k in range(3)]
            for i, j in ((0, 1), (1, 2), (2, 0)):
                a, b = cs[i], cs[j]
                if a == b:
                    continue
                k = (a, b) if a < b else (b, a)
                if k in seen:
                    continue
                seen.add(k)
                out.append((p, k[0], k[1]))
    return out


def block_verts(M, blk, extra=()):
    x, y = blk
    out = {}
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            nx, ny = (x + dx) % S.GX, (y + dy) % S.GY
            sx = sz = 0.0
            if nx - x > 1:
                sx = -S.WX
            elif nx - x < -1:
                sx = S.WX
            if ny - y > 1:
                sz = S.WZ
            elif ny - y < -1:
                sz = -S.WZ
            for (bx, by, p), m in M.items():
                if (bx, by) != (nx, ny):
                    continue
                for v in m.wv:
                    q = (v[0] + sx, v[1], v[2] + sz)
                    out.setdefault(q, set()).add((bx, by, p))
    for q, own in extra:
        out.setdefault(q, set()).add(own)
    return out


def scan(M, blocks=None, extra=None):
    tj, near, hist = Counter(), Counter(), Counter()
    examples = []
    allb = sorted({(k[0], k[1]) for k in M}) if blocks is None else blocks
    for blk in allb:
        E = block_edges(M, blk)
        if not E:
            continue
        Vd = block_verts(M, blk, (extra or {}).get(blk, ()))
        ox0, oz1 = blk[0] * 64.0, -blk[1] * 64.0
        keys = [q for q in Vd if ox0 - 0.2 <= q[0] <= ox0 + 64.2 and oz1 - 64.2 <= q[2] <= oz1 + 0.2]
        if not keys:
            continue
        Q = np.array(keys, dtype=np.float64)
        A = np.array([e[1] for e in E], dtype=np.float64)
        B = np.array([e[2] for e in E], dtype=np.float64)
        for s in range(0, len(E), 400):
            a, b = A[s:s + 400], B[s:s + 400]
            D = b - a
            L2 = (D * D).sum(1)
            W = Q[None, :, :] - a[:, None, :]
            t = (W * D[:, None, :]).sum(2) / L2[:, None]
            F = a[:, None, :] + np.clip(t, 0, 1)[..., None] * D[:, None, :]
            d = np.sqrt(((Q[None, :, :] - F) ** 2).sum(2))
            da = np.sqrt(((Q[None, :, :] - a[:, None, :]) ** 2).sum(2))
            db = np.sqrt(((Q[None, :, :] - b[:, None, :]) ** 2).sum(2))
            inner = (t > 1e-6) & (t < 1 - 1e-6) & (da > 1e-4) & (db > 1e-4)
            cand = inner & (d < 0.1)
            for ei, qi in zip(*np.nonzero(cand)):
                dd = float(d[ei, qi])
                for lo, hi in zip(BINS[:-1], BINS[1:]):
                    if lo <= dd < hi:
                        hist[f"[{lo},{hi})"] += 1
                        break
                part = E[s + ei][0]
                owners = sorted(Vd[keys[qi]])
                key = f"{part}<-{'/'.join(sorted({o[2] for o in owners}))}"
                if dd < EPS_T:
                    tj[key] += 1
                    if len(examples) < 20:
                        examples.append({"block": list(blk), "edge_part": part, "q": keys[qi], "d": dd,
                                         "owners": owners})
                elif dd < S.TOL:
                    near[key] += 1
    return tj, near, hist, examples


def main():
    res = {}
    # positive control: midpoint of a real (7,17) terrain edge, injected as a foreign 'probe' vertex
    M1 = S.load_disc(1)
    m = M1[(7, 17, "terrain")]
    a, b = m.wv[m.fi[0]], m.wv[m.fi[1]]
    mid = tuple((a[i] + b[i]) / 2 for i in range(3))
    tjc, _n, _h, exc = scan(M1, blocks=[(7, 17)], extra={(7, 17): [(mid, (7, 17, "probe"))]})
    tj0, _n0, _h0, _e0 = scan(M1, blocks=[(7, 17)])
    res["control"] = {"with_probe": dict(tjc), "stock_7_17": dict(tj0)}
    print("control: probe ->", dict(tjc), " stock (7,17) ->", dict(tj0))
    assert sum(tjc.values()) >= 1, "positive control failed"
    for disc in (1, 4):
        M = M1 if disc == 1 else S.load_disc(4)
        tj, near, hist, ex = scan(M)
        res[f"disc{disc}"] = {"tjunctions": dict(tj), "near_T_1e-3_to_0.05": dict(near),
                              "dist_hist_nonendpoint_lt_0.1": dict(hist), "examples": ex}
        print(f"disc {disc}: T-junctions {dict(tj)}; near-T {dict(near)}; dist hist {dict(hist)}")
    out = S.OUT / "verify_tjunction_numpy.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
