"""RANKED EXPERIMENT O6 -- the interior T-junction census of disc-4 re-cut seams, and the gaps a replayed reshape
opens there (terrain study README section 7.2; completes the replay safety case, which G5 covered at block borders).

REGISTERED PREDICTION (README O6): "re-cut boundaries add interior T-junctions with small gaps (< 0.3 u for amount 4,
r >= 16)".

A T-junction is a vertex W resting inside another triangle's edge AB (plan distance < 2e-3, the kit's
meshedit.find_tjunctions rule) and on it in 3D (vertical offset < 0.01u; otherwise the surfaces are layered, e.g. a
bridge over a gully). Stock is watertight there in exact arithmetic. A reshape moves each Terrain vertex by a function
of its world XZ only -- delta(P) = amount * falloff(|P - c| / r) * taper(P), 0 for a vertex held by the seam pins
(mesh.deform_radial, mesh.StitchPins, terrain.SEAM_TAPER) -- and never moves a partner part. So W separates from AB by
|dW - lerp_s(dA, dB)|, with d = 0 for a partner (or pinned) vertex: second order inside the Terrain, first order where a
Terrain vertex sits on a partner edge.

Census per land cell (Terrain on both discs), each disc, over the cell's Terrain + its partner parts
(mesh.STITCH_PARTNER_PARTS): classes
  * terrain     W and AB both Terrain
  * on_partner  a Terrain-only W on a partner edge (the partner stays, W moves)
  * partner_on  a partner W on a Terrain edge (W stays, the edge moves)
Witnesses on a block border plane are G5's class, counted apart. A disc-4 junction is ADDED when disc 1 has no
junction with the same W/A/B plan positions, and RE-CUT when its edge or W belongs to a disc-4 Terrain triangle with
no disc-1 counterpart (lib cache `g4`).

Gap: for every junction and r in 8/16/24/32 (amount 4, smooth), the worst new vertical separation over reshape
centres on a 1u grid within r of W. The pins are the kit's own (mesh.stitch_pins over the 3x3 neighbourhood's partner
parts, taper 4u).

CALIBRATION (each must pass before a number is read):
  C1  the grid-indexed finder returns exactly meshedit.find_tjunctions' hits on 6 real Terrain blocks (plan);
  C2  on a synthetic 3-tri mesh with one known junction it finds that one, and none once W is moved off the edge;
  C3  the 3-point gap equals the gap measured after the REAL mesh.deform_radial (real pins, real taper) on the real
      block, at the worst centre of the largest disc-4 r16 junction (|diff| < 1e-6).
Writes out/o6_tjunctions.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py ../studies/terrain-malleability/gap_disc4_edit_reach/o6_tjunctions.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                          # noqa: E402
import numpy as np                                       # noqa: E402
from ff9mapkit.world import mesh as M, meshedit as ME    # noqa: E402
from ff9mapkit.world.terrain import SEAM_TAPER           # noqa: E402

import ff9mapkit                                         # noqa: E402
assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__

EPS_PLAN, EPS_3D, AMOUNT = 2e-3, 1e-2, 4.0
RADII = (8.0, 16.0, 24.0, 32.0)
PARTNERS = {p for p in M.STITCH_PARTNER_PARTS}
data = L.load_cache()
MESH = data["meshes"]
PAIRS = data["pairs"]


def origin(x, y):
    return 64.0 * x, -64.0 * y


def wpos(d, x, y, p):
    V = MESH[(d, x, y, p)]["V"].copy()
    ox, oz = origin(x, y)
    V[:, 0] += ox
    V[:, 2] += oz
    return V


def find(tris_by_label, eps=EPS_PLAN):
    """Grid-indexed meshedit.find_tjunctions over labelled meshes: [(W, A, B, s, off, edge_labels, w_labels)] with W/A/B
    3D world positions. Vertices and edges are deduplicated by exact position across labels."""
    vlab = defaultdict(set)                              # plan+height position -> labels
    for lab, (P, T) in tris_by_label.items():
        for v in P[np.unique(T)]:
            vlab[(float(v[0]), float(v[1]), float(v[2]))].add(lab)
    grid = defaultdict(list)
    for v in vlab:
        grid[(math.floor(v[0] / 2.0), math.floor(v[2] / 2.0))].append(v)
    edges = defaultdict(set)
    for lab, (P, T) in tris_by_label.items():
        for t in T:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                pa, pb = tuple(map(float, P[t[a]])), tuple(map(float, P[t[b]]))
                edges[(pa, pb) if pa <= pb else (pb, pa)].add(lab)
    hits = []
    for (pa, pb), elab in edges.items():
        dx, dz = pb[0] - pa[0], pb[2] - pa[2]
        L2 = dx * dx + dz * dz
        if L2 < 1e-12:
            continue
        x0, x1 = min(pa[0], pb[0]) - eps, max(pa[0], pb[0]) + eps
        z0, z1 = min(pa[2], pb[2]) - eps, max(pa[2], pb[2]) + eps
        for gx in range(math.floor(x0 / 2.0), math.floor(x1 / 2.0) + 1):
            for gz in range(math.floor(z0 / 2.0), math.floor(z1 / 2.0) + 1):
                for w in grid.get((gx, gz), ()):
                    if (w[0], w[2]) in ((pa[0], pa[2]), (pb[0], pb[2])):
                        continue
                    s = ((w[0] - pa[0]) * dx + (w[2] - pa[2]) * dz) / L2
                    if not (1e-5 < s < 1 - 1e-5):
                        continue
                    off = abs((w[0] - pa[0]) * dz - (w[2] - pa[2]) * dx) / math.sqrt(L2)
                    if off < eps:
                        hits.append((w, pa, pb, s, off, frozenset(elab), frozenset(vlab[w])))
    return hits


def on_border(w, x, y):
    ox, oz = origin(x, y)
    lx, lz = w[0] - ox, w[2] - oz
    return min(abs(lx), abs(lx - 64.0)) < 1e-3 or min(abs(lz), abs(lz + 64.0)) < 1e-3


def cell_meshes(d, x, y):
    out = {"terrain": (wpos(d, x, y, "terrain"), MESH[(d, x, y, "terrain")]["T"])}
    for p in PARTNERS:
        if (d, x, y, p) in MESH:
            out[p] = (wpos(d, x, y, p), MESH[(d, x, y, p)]["T"])
    return out


class _BM:                                               # what stitch_pins / deform_radial read: .verts
    def __init__(self, V):
        self.verts = [list(map(float, v)) for v in V]


def pins_for(d, x, y):
    partners = [(p, _BM(MESH[(d, xx, yy, p)]["V"]), origin(xx, yy))
                for xx in (x - 1, x, x + 1) for yy in (y - 1, y, y + 1) for p in PARTNERS if (d, xx, yy, p) in MESH]
    return M.stitch_pins(partners, [(_BM(MESH[(d, x, y, "terrain")]["V"]), origin(x, y))], taper=SEAM_TAPER)


def recut_positions(x, y):
    """Plan+height positions of disc-4 Terrain triangles with no disc-1 geometric counterpart."""
    pr = PAIRS.get((x, y, "terrain"))
    if pr is None:
        return set()
    P, T = wpos(4, x, y, "terrain"), MESH[(4, x, y, "terrain")]["T"]
    return {tuple(map(float, P[i])) for t in np.nonzero(~pr["g4"])[0] for i in T[t]}


def classify(h):
    """A W with any partner instance never moves (a welded Terrain instance is pinned); a Terrain edge moves."""
    w, pa, pb, s, off, elab, wlab = h
    if "terrain" in elab and wlab == {"terrain"}:
        return "terrain"
    if "terrain" not in elab and wlab == {"terrain"}:
        return "on_partner"
    if "terrain" in elab:
        return "partner_on"
    return None                                          # a partner edge under a partner/welded W: nothing moves


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return 1.0 - t * t * (3.0 - 2.0 * t)


def worst_gap(h, cls, pins, r):
    """max over centres (1u grid within r of W) of the new vertical separation, and that centre."""
    w, pa, pb, s, off, elab, wlab = h
    gx = np.arange(-r, r + 1e-9, 1.0)
    cx, cz = np.meshgrid(w[0] + gx, w[2] + gx)
    cx, cz = cx.ravel(), cz.ravel()
    keep = np.hypot(cx - w[0], cz - w[2]) <= r
    cx, cz = cx[keep], cz[keep]

    def delta(p, terrain):
        if not terrain or M.world_key(p) in pins:
            return np.zeros_like(cx)
        return AMOUNT * smooth(np.hypot(p[0] - cx, p[2] - cz) / r) * pins.scale(p[0], p[2])
    edge_t = cls in ("terrain", "partner_on")
    dw = delta(w, cls in ("terrain", "on_partner"))
    da, db = delta(pa, edge_t), delta(pb, edge_t)
    y0 = w[1] - (pa[1] + s * (pb[1] - pa[1]))
    g = np.abs(y0 + dw - ((1 - s) * da + s * db)) - abs(y0)
    i = int(np.argmax(g))
    return float(g[i]), (float(cx[i]), float(cz[i]))


# ------------------------------------------------------------------------------------------------ calibration
def inject(P, T, ti=None):
    """Split one interior Terrain triangle ABC at its AB midpoint M (ABC -> AMC + MBC) and leave the neighbour across
    AB whole: M rests inside the neighbour's edge AB, a known T-junction in a real mesh. -> (P', T', M)."""
    P, T = P.copy(), T.copy()
    for t in range(len(T)) if ti is None else [ti]:
        a, b, c = T[t]
        nb = [u for u in range(len(T)) if u != t and {a, b} <= set(T[u])]
        mx, mz = (P[a][0] + P[b][0]) / 2, (P[a][2] + P[b][2]) / 2
        if nb and 8 < (mx % 64) < 56 and 8 < (-mz % 64) < 56:
            break
    m = len(P)
    P = np.vstack([P, (P[a] + P[b]) / 2.0])
    T = np.vstack([np.delete(T, t, axis=0), [[a, m, c], [m, b, c]]])
    return P, T, tuple(map(float, P[m]))


cal_cells = [c for c in sorted({(x, y) for (d, x, y, p) in MESH if p == "terrain" and d == 4})][::40][:6]
for (x, y) in cal_cells:
    P, T = wpos(4, x, y, "terrain"), MESH[(4, x, y, "terrain")]["T"]
    P, T, M_ = inject(P, T)                              # so the comparison is never two empty sets
    ref = {(w, frozenset((a, b))) for (w, a, b, _o) in
           ME.find_tjunctions([[(P[i][0], P[i][2]) for i in t] for t in T], eps=EPS_PLAN)}
    mine = {((h[0][0], h[0][2]), frozenset(((h[1][0], h[1][2]), (h[2][0], h[2][2]))))
            for h in find({"terrain": (P, T)})}
    assert mine == ref and (M_[0], M_[2]) in {k[0] for k in mine}, ("C1", (x, y), len(mine), len(ref))
print(f"C1 OK: finder == meshedit.find_tjunctions on {len(cal_cells)} real disc-4 Terrain blocks, each with one "
      f"injected junction (found by both)")
Ps = np.array([[0, 0, 0], [4, 0, 0], [0, 0, -4], [2, 0, 0], [4, 0, 4], [0, 0, 4]], float)
Ts = np.array([[0, 1, 2], [3, 4, 5], [0, 3, 5]])         # tri 0's edge (0,0)-(4,0) carries vertex (2,0): one junction
assert len(find({"terrain": (Ps, Ts)})) == 1, "C2"
Ps2 = Ps.copy()
Ps2[3, 2] = 0.5
assert find({"terrain": (Ps2, Ts)}) == [], "C2 off-edge"
print("C2 OK: a synthetic junction found; moved off the edge, none")

# ------------------------------------------------------------------------------------------------ census
land = sorted({(x, y) for (d, x, y, p) in MESH if p == "terrain" and d == 1} &
              {(x, y) for (d, x, y, p) in MESH if p == "terrain" and d == 4})
res = {"cells": len(land), "eps_plan": EPS_PLAN, "eps_3d": EPS_3D, "amount": AMOUNT, "radii": RADII,
       "disc": {1: Counter(), 4: Counter()}, "added": Counter(), "added_recut": Counter(), "gap": {}, "worst": {}}
rows = {1: [], 4: []}
layered = {1: [], 4: []}                                 # (vertical offset, class, cell): is any a small crack?
for (x, y) in land:
    keys = {}
    for d in (1, 4):
        found = []
        for h in find(cell_meshes(d, x, y)):
            cls = classify(h)
            if cls is None:
                continue
            w, pa, pb, s = h[0], h[1], h[2], h[3]
            dy = abs(w[1] - (pa[1] + s * (pb[1] - pa[1])))
            if dy >= EPS_3D:
                res["disc"][d]["layered"] += 1
                layered[d].append((dy, cls, [x, y]))
                continue
            if on_border(w, x, y):
                res["disc"][d][f"border_{cls}"] += 1
                continue
            res["disc"][d][cls] += 1
            found.append((h, cls))
        keys[d] = {((h[0][0], h[0][2]), frozenset(((h[1][0], h[1][2]), (h[2][0], h[2][2])))) for h, _c in found}
        if d == 4:
            rc = recut_positions(x, y)
        pins = None
        for h, cls in found:
            k = ((h[0][0], h[0][2]), frozenset(((h[1][0], h[1][2]), (h[2][0], h[2][2]))))
            added = d == 4 and k not in keys.get(1, set())
            recut = d == 4 and bool({h[0], h[1], h[2]} & rc)
            if added:
                res["added"][cls] += 1
                res["added_recut"][cls] += recut
            pins = pins or pins_for(d, x, y)
            g = {r: worst_gap(h, cls, pins, r) for r in RADII}
            rows[d].append({"cell": [x, y], "cls": cls, "added": added, "recut": recut,
                            "w": h[0], "a": h[1], "b": h[2], "s": h[3],
                            "gap": {str(int(r)): round(v[0], 4) for r, v in g.items()},
                            "at": {str(int(r)): v[1] for r, v in g.items()}})
    print(f"  {x},{y}: d1 {len(keys[1])} d4 {len(keys[4])}", end="\r", flush=True)
print()


def summary(rs):
    out = {}
    for r in RADII:
        k = str(int(r))
        v = [q["gap"][k] for q in rs]
        out[k] = {"n": len(v), "max": round(max(v), 4) if v else None,
                  "p95": round(float(np.percentile(v, 95)), 4) if v else None,
                  "over_0.3": sum(1 for q in v if q > 0.3)}
    return out


for d in (1, 4):
    res["gap"][f"disc{d}_all"] = summary(rows[d])
    for cls in ("terrain", "on_partner", "partner_on"):
        res["gap"][f"disc{d}_{cls}"] = summary([q for q in rows[d] if q["cls"] == cls])
res["gap"]["disc4_added"] = summary([q for q in rows[4] if q["added"]])
res["gap"]["disc4_added_recut"] = summary([q for q in rows[4] if q["added"] and q["recut"]])
for d in (1, 4):
    top = sorted(rows[d], key=lambda q: -q["gap"]["16"])[:12]
    res["worst"][f"disc{d}"] = top
    dys = sorted(q[0] for q in layered[d])
    res[f"layered_disc{d}"] = {
        "n": len(dys), "min": round(dys[0], 4) if dys else None,
        "under_0.1": sum(1 for v in dys if v < 0.1), "under_0.5": sum(1 for v in dys if v < 0.5),
        "by_class": dict(Counter(q[1] for q in layered[d])),
        "smallest": [[round(q[0], 4), q[1], q[2]] for q in sorted(layered[d])[:8]]}

# ------------------------------------------------------------------------------------------------ C3: the real deform
def c3(x, y, Pw, h, cls, r=16.0):
    """The 3-point worst gap vs the gap measured after the REAL deform_radial (real pins + taper) on block (x, y)
    whose world positions are ``Pw``, at the worst centre the 3-point model chose."""
    pins = pins_for(4, x, y)
    pred, (cx, cz) = worst_gap(h, cls, pins, r)
    ox, oz = origin(x, y)
    bm = _BM(Pw - np.array([ox, 0.0, oz]))
    pre = [v[:] for v in bm.verts]
    M.deform_radial(bm, amount=AMOUNT, radius=r, center=(cx, cz), world_origin=(ox, oz), pinned=pins)

    def post_y(p):                                       # a Terrain vertex's post-deform height, or the fixed partner
        for v0, v1 in zip(pre, bm.verts):
            if abs(v0[0] + ox - p[0]) < 1e-6 and abs(v0[2] + oz - p[2]) < 1e-6 and abs(v0[1] - p[1]) < 1e-6:
                return v1[1]
        return p[1]
    w, a, b, s = h[0], h[1], h[2], h[3]
    yw = post_y(w) if cls in ("terrain", "on_partner") else w[1]
    ya, yb = (post_y(a), post_y(b)) if cls in ("terrain", "partner_on") else (a[1], b[1])
    measured = abs(yw - (ya + s * (yb - ya))) - abs(w[1] - (a[1] + s * (b[1] - a[1])))
    assert pred > 1e-3 and abs(measured - pred) < 1e-6, ("C3", (x, y), measured, pred)
    return {"cell": [x, y], "centre": [cx, cz], "predicted": round(pred, 6), "measured": round(measured, 6)}


res["c3"] = []
top = res["worst"]["disc4"][0] if res["worst"]["disc4"] else None
if top:                                                  # the largest real disc-4 junction
    x, y = top["cell"]
    h = (tuple(top["w"]), tuple(top["a"]), tuple(top["b"]), top["s"], 0.0, None, None)
    Pw = wpos(4, x, y, "terrain")
    res["c3"].append(c3(x, y, Pw, h, top["cls"]))
for (x, y) in cal_cells[:3]:                             # and always an injected one in a real block
    Pw, Tw, M_ = inject(wpos(4, x, y, "terrain"), MESH[(4, x, y, "terrain")]["T"])
    (h,) = [h for h in find({"terrain": (Pw, Tw)}) if h[0] == M_]
    res["c3"].append(c3(x, y, Pw, h, "terrain"))
for c in res["c3"]:
    print(f"C3 OK: real deform_radial at {c['cell']} c={c['centre']} r16 measured {c['measured']} "
          f"vs predicted {c['predicted']}")

res["disc"] = {str(k): dict(v) for k, v in res["disc"].items()}
res["added"], res["added_recut"] = dict(res["added"]), dict(res["added_recut"])
out = L.OUT / "o6_tjunctions.json"
out.write_text(json.dumps(res, indent=1, default=list), encoding="utf-8")
print(json.dumps({k: res[k] for k in ("cells", "disc", "added", "added_recut", "layered_disc1", "layered_disc4")},
                 default=list))
for k, v in res["gap"].items():
    print(f"  {k:24s} " + "  ".join(f"r{r}: n{s['n']} max {s['max']} p95 {s['p95']} >0.3 {s['over_0.3']}"
                                     for r, s in v.items()))
print("->", out)
