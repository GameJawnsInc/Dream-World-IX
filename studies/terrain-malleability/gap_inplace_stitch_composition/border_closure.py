"""The STOCK block-border CLOSURE census -- the instrument the 17/443 count needed (disc4/VERIFY.md D4-06).

weld_gap.py's top-polyline metric (and stitch_census.py's gap_mutual, which reproduces it) reads a VERTICAL FACE
LYING IN THE BORDER PLANE (a "curtain" tri on one side only, e.g. a rock side that sits exactly on x=64k) as a
1.95-3.39u gap -- see the three inspected cases in NOTES.md. A crack is something else: a place where the surface
reaches the border plane on one side and nothing meets it on the other.

Instrument: for each torus-adjacent pair of land blocks and each side, take every triangle edge lying in the
shared border plane from ALL registered parts (Terrain, Beach*, Sea*, River*, Falls, Stream, Object, Volcano*) and
keep the CROSSING edges -- those whose owning tri has a vertex OFF the plane (the surface arrives at the border);
edges of in-plane tris are curtains and need no partner. Every crossing edge of side A is sampled at 9 points in
the (along, y) plane; a sample is CLOSED if it lies within 1e-3 of some crossing edge of side B (any part).
Unmatched samples on either side are OPEN stretches (length-weighted). Reported per disc: pairs fully closed,
pairs with an open Terrain-to-anything stretch, total open length, the largest opening (distance to the nearest
partner edge in-plane).
Calibration: deleting one real (7,11) Terrain tri that owns a crossing S-border edge must open that edge's length.
Writes out/border_closure.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/border_closure.py
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402

PLANE_EPS = 1e-4
ON_EPS = 1e-3


def side_frame(side):
    """(on-plane test, along coord) in block-LOCAL coords."""
    if side == "E":
        return (lambda v: abs(v[0] - 64.0) < PLANE_EPS), (lambda v: v[2])
    if side == "W":
        return (lambda v: abs(v[0]) < PLANE_EPS), (lambda v: v[2])
    if side == "N":
        return (lambda v: abs(v[2]) < PLANE_EPS), (lambda v: v[0])
    return (lambda v: abs(v[2] + 64.0) < PLANE_EPS), (lambda v: v[0])


def curtains(M, blk, side):
    """in-plane (curtain) tris of every part on this side, as (along, y) triangles."""
    on, al = side_frame(side)
    out = []
    for (x, y, p), m in M.items():
        if (x, y) != blk:
            continue
        lv, fi = m.lv, m.fi
        for t in range(len(fi) // 3):
            cs = [lv[fi[3 * t + k]] for k in range(3)]
            if all(on(c) for c in cs):
                out.append((p, [(al(c), c[1]) for c in cs]))
    return out


def in_tri2(q, tri, eps=1e-6):
    (ax, ay), (bx, by), (cx, cy) = tri
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(d) < 1e-12:
        return False
    w0 = ((by - cy) * (q[0] - cx) + (cx - bx) * (q[1] - cy)) / d
    w1 = ((cy - ay) * (q[0] - cx) + (ax - cx) * (q[1] - cy)) / d
    return min(w0, w1, 1 - w0 - w1) >= -eps


def crossing_edges(M, blk, side):
    on, al = side_frame(side)
    out = []                                            # (part, (a0,y0), (a1,y1))
    for (x, y, p), m in M.items():
        if (x, y) != blk:
            continue
        lv, fi = m.lv, m.fi
        seen = set()
        for t in range(len(fi) // 3):
            cs = [lv[fi[3 * t + k]] for k in range(3)]
            flags = [on(c) for c in cs]
            if all(flags):
                continue                                # an in-plane (curtain) tri
            for i, j in ((0, 1), (1, 2), (2, 0)):
                if flags[i] and flags[j]:
                    e = ((al(cs[i]), cs[i][1]), (al(cs[j]), cs[j][1]))
                    k = tuple(sorted(e))
                    if k in seen:
                        continue
                    seen.add(k)
                    out.append((p, e[0], e[1]))
    return out


def d_seg(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(p[0] - ax, p[1] - ay)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def open_stretches(EA, EB, curt=(), corner_ok=None):
    """length-weighted unmatched samples of EA's edges against EB's edges; a sample inside a curtain tri of
    either side (``curt``) is CLOSED (an in-plane riser), and ``corner_ok(q)`` may close a sample that sits
    on the block-corner line (its partner lives in the diagonal block)."""
    res = []
    for (p, a, b) in EA:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-9:
            continue
        miss, worst = 0, 0.0
        for k in range(9):
            t = (k + 0.5) / 9
            q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            dmin = min((d_seg(q, c, d) for (_p, c, d) in EB), default=float("inf"))
            if dmin > ON_EPS and any(in_tri2(q, tri) for (_p, tri) in curt):
                dmin = 0.0
            if dmin > ON_EPS and corner_ok is not None and corner_ok(q):
                dmin = 0.0
            if dmin > ON_EPS:
                miss += 1
                worst = max(worst, dmin)
        if miss:
            res.append({"part": p, "a": a, "b": b, "open_len": L * miss / 9, "max_open": worst})
    return res


def corner_closer(M, blk, side):
    """closes a sample on the border's END line (along 0 / +-64: the 4-block corner) if ANY edge of ANY part
    of the 4 blocks around that corner contains the 3D point (world frame)."""
    x, y = blk
    if side == "E":
        X0 = (x + 1) * 64.0
        to3 = lambda q: (X0, q[1], q[0] - y * 64.0)            # along = local z
    else:                                                       # S
        Z0 = -(y + 1) * 64.0
        to3 = lambda q: (q[0] + x * 64.0, q[1], Z0)            # along = local x
    edges_cache = {}

    def edges_of(k):
        if k not in edges_cache:
            edges_cache[k] = list(S.mesh_edges(M[k]).keys())
        return edges_cache[k]

    def ok(q):
        if not (abs(q[0]) < 1e-6 or abs(abs(q[0]) - 64.0) < 1e-6):
            return False
        P = to3(q)
        bx0, by0 = math.floor(P[0] / 64.0 - 0.5), math.floor(-P[2] / 64.0 - 0.5)
        for (kx, ky, kp) in M:
            if kx in (bx0, bx0 + 1) and ky in (by0, by0 + 1):
                for (a, b) in edges_of((kx, ky, kp)):
                    if S.seg_point_dist(P, a, b)[0] < ON_EPS:
                        return True
        return False
    return ok


def census(M):
    land = {(x, y) for (x, y, p) in M if p == "terrain"}
    have = {(x, y) for (x, y, p) in M}
    rows = []
    for (x, y) in sorted(land):
        for (nx, ny, side) in S.neighbours(x, y)[::2]:
            if (nx, ny) not in have:
                continue
            opp = {"E": "W", "S": "N"}[side]
            EA, EB = crossing_edges(M, (x, y), side), crossing_edges(M, (nx, ny), opp)
            cu = curtains(M, (x, y), side) + curtains(M, (nx, ny), opp)
            ck = corner_closer(M, (x, y), side)
            oa = open_stretches(EA, EB, cu, ck)
            ob = open_stretches(EB, EA, cu, ck)
            raw = open_stretches(EA, EB) + open_stretches(EB, EA)
            rows.append({"a": [x, y, side], "b": [nx, ny, opp], "b_is_land": (nx, ny) in land,
                         "open_len_naive": round(sum(r["open_len"] for r in raw), 3),
                         "nA": len(EA), "nB": len(EB),
                         "open_A": oa, "open_B": ob,
                         "open_len": round(sum(r["open_len"] for r in oa + ob), 3),
                         "open_terrain_len": round(sum(r["open_len"] for r in oa + ob if r["part"] == "terrain"), 3),
                         "max_open": round(max([r["max_open"] for r in oa + ob if r["max_open"] < 1e9] or [0.0]), 3)})
    return rows


def summarize(rows, label):
    ll = [r for r in rows if r["b_is_land"]]
    opn = [r for r in rows if r["open_len"] > 1e-6]
    opt = [r for r in rows if r["open_terrain_len"] > 1e-6]
    s = {"pairs_all": len(rows), "pairs_land_land": len(ll),
         "pairs_open_naive(no curtain/corner closure)": sum(1 for r in rows if r["open_len_naive"] > 1e-6),
         "land_land_closed": sum(1 for r in ll if r["open_len"] <= 1e-6),
         "pairs_with_open": len(opn), "pairs_with_open_terrain": len(opt),
         "open_len_total": round(sum(r["open_len"] for r in rows), 2),
         "open_rows": [{k: r[k] for k in ("a", "b", "b_is_land", "open_len", "open_terrain_len", "max_open")}
                       for r in opn]}
    print(f"{label}: {s['pairs_all']} adjacent pairs with a land side ({s['pairs_land_land']} land|land, "
          f"{s['land_land_closed']} of those fully closed); pairs with an OPEN crossing edge {s['pairs_with_open']} "
          f"(Terrain-owned {s['pairs_with_open_terrain']}), open length {s['open_len_total']}u")
    for r in s["open_rows"][:30]:
        print("    ", r)
    return s


def main():
    res = {}
    # calibration on disc 1: delete a (7,11) terrain tri owning a crossing S-border edge
    M1 = S.load_disc(1)
    EA = crossing_edges(M1, (7, 11), "S")
    tgt = next(e for e in EA if e[0] == "terrain" and abs(e[1][0] - e[2][0]) > 1.0)
    m = M1[(7, 11, "terrain")]
    on, al = side_frame("S")
    fi = list(m.fi)
    kill = None
    for t in range(len(fi) // 3):
        cs = [m.lv[fi[3 * t + k]] for k in range(3)]
        es = {tuple(sorted(((al(cs[i]), cs[i][1]), (al(cs[j]), cs[j][1])))) for i, j in ((0, 1), (1, 2), (2, 0))
              if on(cs[i]) and on(cs[j])}
        if tuple(sorted((tgt[1], tgt[2]))) in es:
            kill = t
            break
    del fi[3 * kill:3 * kill + 3]
    M2 = dict(M1)
    M2[(7, 11, "terrain")] = S.Mesh(1, 7, 11, "terrain", m.name, m.lv, m.idall, fi)
    def _open(Mx):
        EA, EB = crossing_edges(Mx, (7, 11), "S"), crossing_edges(Mx, (7, 12), "N")
        cu = curtains(Mx, (7, 11), "S") + curtains(Mx, (7, 12), "N")
        ck = corner_closer(Mx, (7, 11), "S")
        return open_stretches(EA, EB, cu, ck) + open_stretches(EB, EA, cu, ck)
    base = _open(M1)
    cut = _open(M2)
    elen = math.hypot(tgt[2][0] - tgt[1][0], tgt[2][1] - tgt[1][1])
    print(f"CALIBRATION: (7,12)N vs (7,11)S open length stock {sum(r['open_len'] for r in base):.3f}u; "
          f"one (7,11) border tri deleted -> {sum(r['open_len'] for r in cut):.3f}u (edge length {elen:.3f}u)")
    res["calibration"] = {"stock_open": sum(r["open_len"] for r in base), "deleted_open": sum(r["open_len"] for r in cut),
                          "edge_len": elen}
    for d in (1, 4):
        M = S.load_disc(d) if d != 1 else M1
        rows = census(M)
        res[f"disc{d}"] = summarize(rows, f"disc {d}")
    p = S.save_json("border_closure.json", res)
    print("->", p)


if __name__ == "__main__":
    main()
