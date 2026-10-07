"""STEP 5 -- the REACH census: how much of the refused real land each disc-4 strategy can lawfully carry an edit onto.

SYNTHETIC EDIT POPULATION (per the lane brief): at every 4u lattice point (64*bx + 4i, -(64*by + 4j)), i,j in
0..15, of each of the 189 gate-refused LAND cells whose DISC-1 ground (placement.place, engine-faithful) is
walkable (placement.WALK_OK), the edits
    raise  +4u   radius 8/16/24   (terrain.reshape -> mesh.deform_radial, smooth falloff)
    lower  -4u   radius 8/16/24
    retarget     radius 8/16/24   (mesh.retarget_tiles: tris whose centroid is within r; IDALL only)
Each edit touches every block the kit itself would write: reshape = blocks with a terrain vertex strictly inside r
(w > 0); retarget = blocks with a terrain-tri centroid within r (the library's per-block test applied to every
block -- the CLI verb itself takes one --block).
An edit is in the population only if it is LAWFUL ON DISC 1 (the operator's own one-way-wall gate,
terrain._walk_gate, passes on disc 1); disc-1-refused edits are counted separately.

STRATEGIES (each judged ATOMICALLY over every touched block -- a partial carry is a crack, see CRACK below):
  shipped   the current gate (discmirror.py:276-289, byte identity per cell): the edit reaches disc 4 only if
            EVERY touched cell is eligible.
  orderinv  strategy (i): the order-invariant gate (exact all-channel permutation per part).
  replay    strategy (ii): re-run the same op on disc-4 stock. LAWFUL = the op's own gate passes on disc 4
            (one-way wall for reshape; >=1 tri selected for retarget). CLEAN = lawful AND the support misses
            every disc-4 HAZARD tri (s2 layers RIDGE / LAND2SEA / ENTR_LOST / ENTR_NEW / OBJECT; exact
            point-to-triangle distance < r).
  delta_v   strategy (iii), parametric-exact: no unmatched terrain corner (either disc) strictly inside r
            (retarget: no unmatched centroid within r). Calibrated (s4 K5): exactly when delta bytes == replay bytes.
  delta_fM  strategy (iii) as a BYTE-CARRIED footprint gate: distance from the edit centre to the union of
            unmatched terrain tris > r + M, for M in 0/4/8 -- what a verb with no replay would have to use.
  partgate  strategy (i-b): order-invariant gate on the EDITED PART only (Terrain an exact permutation).
CRACK: under shipped/orderinv/partgate, an edit that touches an eligible cell A and a refused cell B sharing a border, and
moves a border vertex, is mirrored on A and skipped on B -> a step on disc 4 at that border (the current design).
Writes out/reach.json (per cell x strategy x edit class) and out/reach_summary.json.
CALIBRATION (asserted): V1 the vectorized one-way-wall gate agrees with terrain.reshape(dry_run=True) on a
sample (both discs); V2 delta_v agrees with lib.delta_transfer(support=...) + replay byte equality on a sample of
single-block edits; V3 an edit placed ON a RIDGE tri is replay-HAZARD and delta-refused.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s5_reach.py
"""
import copy
import json
import math
import pickle
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402
from scipy.spatial import cKDTree                     # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402
from ff9mapkit.world import terrain as TER           # noqa: E402

t0 = time.time()
G = L.GAME
data = L.load_cache()
meshes, pairs = data["meshes"], data["pairs"]
layers = pickle.load(open(L.CACHE_DIR / "s2_layers.pkl", "rb"))
s1g = json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))
rows = {tuple(map(int, k.split(","))): r for k, r in s1g["rows"].items()}
elig_ship = {c for c, r in rows.items() if r["shipped"].startswith("PASS")}
elig_oi = {c for c, r in rows.items() if r["orderinv"].startswith("PASS")}
# strategy (i-b) PER-PART order-invariant gate: the edited part (Terrain) alone must be an exact permutation;
# other parts may differ (the s34 override is per part, so they keep rendering their own disc-4 bytes)
elig_part = {(x, y) for (x, y, p), pr in pairs.items() if p == "terrain" and pr["perm"]}
refused = sorted(c for c, r in rows.items() if r["land"] and r["shipped"].startswith("SKIP"))
assert len(refused) == 189
AMT, RADII = 4.0, (8.0, 16.0, 24.0)
WALL = L.P.WALK_RAY_START / L.P.WALK_SPEED

# ------------------------------------------------------------------ per-block terrain arrays (both discs)
blk = {1: {}, 4: {}}
for (d, x, y, p), m in meshes.items():
    if p != "terrain":
        continue
    V = m["V"]
    T = m["T"]
    Vw = V.copy(); Vw[:, 0] += 64 * x; Vw[:, 2] -= 64 * y
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    Et = np.concatenate([np.arange(len(T))] * 3)
    blk[d][(x, y)] = {"V": V, "T": T, "E": E, "Et": Et, "XZ": Vw[:, [0, 2]],
                      "kd": cKDTree(Vw[:, [0, 2]]), "C": Vw[T][:, :, [0, 2]].mean(1)}
    blk[d][(x, y)]["kdc"] = cKDTree(blk[d][(x, y)]["C"])
ter_cells = sorted(blk[1])

# unmatched terrain geometry (global, world XZ)
UC, UT = [], []
for (x, y), g in layers["unmatched"].items():
    if "terrain" in g:
        for key in ("u1", "u4"):
            W = g["terrain"][key]
            if len(W):
                UT.append(W[:, :, [0, 2]])
                UC.append(W[:, :, [0, 2]].reshape(-1, 2))
UT = np.concatenate(UT); UC = np.concatenate(UC)
UTc = UT.mean(1)
kd_uc, kd_utc = cKDTree(UC), cKDTree(UTc)
ut_rad = float(np.max(np.linalg.norm(UT - UTc[:, None, :], axis=2)))
# hazard tris
HT, HL = [], []
for c, lay in layers["hazard"].items():
    for name, tris in lay.items():
        for tri in tris:
            HT.append(np.asarray(tri)[:, [0, 2]]); HL.append(name)
HT = np.array(HT); HL = np.array(HL)
HTc = HT.mean(1); kd_ht = cKDTree(HTc)
ht_rad = float(np.max(np.linalg.norm(HT - HTc[:, None, :], axis=2)))
print(f"unmatched terrain tris {len(UT)} (corner pts {len(UC)}), hazard tris {len(HT)}; {time.time() - t0:.0f}s")


def pt_tri_dist(p, tris):
    """2D distance from point p to each triangle (0 inside). tris (k,3,2)."""
    if len(tris) == 0:
        return np.zeros(0)
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    def cross(u, v):
        return u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    d1 = cross(b - a, p - a); d2 = cross(c - b, p - b); d3 = cross(a - c, p - c)
    inside = ((d1 >= 0) & (d2 >= 0) & (d3 >= 0)) | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))
    def seg(u, v):
        uv = v - u
        L2 = (uv ** 2).sum(1)
        t = np.clip(((p - u) * uv).sum(1) / np.where(L2 > 0, L2, 1), 0, 1)
        q = u + uv * t[:, None]
        return np.sqrt(((p - q) ** 2).sum(1))
    d = np.minimum(np.minimum(seg(a, b), seg(b, c)), seg(c, a))
    return np.where(inside, 0.0, d)


def dist_unmatched_tri(p, lim):
    idx = kd_utc.query_ball_point(p, lim + ut_rad)
    return float(pt_tri_dist(np.asarray(p), UT[idx]).min()) if idx else math.inf


def falloff(t):
    t = np.clip(t, 0, 1)
    return 1.0 - t * t * (3.0 - 2.0 * t)


def touched(d, p, r, kind):
    out = []
    bx, by = int(math.floor(p[0] / 64)), int(math.floor(-p[1] / 64))
    for c in ((bx + i, by + j) for i in (-1, 0, 1) for j in (-1, 0, 1)):
        if c not in blk[d]:
            continue
        b = blk[d][c]
        x0, z1 = 64 * c[0], -64 * c[1]
        dx = max(x0 - p[0], 0, p[0] - (x0 + 64)); dz = max((z1 - 64) - p[1], 0, p[1] - z1)
        if math.hypot(dx, dz) > r:
            continue
        if kind == "reshape":
            if b["kd"].query_ball_point(p, r * (1 - 1e-12), return_length=True) > 0:
                out.append(c)
        else:
            if b["kdc"].query_ball_point(p, r, return_length=True) > 0:
                out.append(c)
    return out


def wall_gate(d, cells, p, r, amt):
    """terrain._walk_gate, vectorized: per block, max rise/run over edges of tris with a moved vertex."""
    for c in cells:
        b = blk[d][c]
        dist = np.hypot(b["XZ"][:, 0] - p[0], b["XZ"][:, 1] - p[1])
        w = falloff(dist / r)
        moved = w > 0
        if not moved.any():
            continue
        y = b["V"][:, 1] + amt * w
        tri_m = moved[b["T"]].any(1)
        sel = tri_m[b["Et"]]
        E = b["E"][sel]
        va, vb = E[:, 0], E[:, 1]
        rise = np.abs(y[vb] - y[va])
        run = np.hypot(b["V"][vb, 0] - b["V"][va, 0], b["V"][vb, 2] - b["V"][va, 2])
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(run > 1e-9, rise / np.where(run > 1e-9, run, 1), np.where(rise > 1e-9, np.inf, 0.0))
        if t.max() > WALL:
            return False, c
    return True, None


def crack(eligible, cells, p, r):
    """A 4-adjacent touched pair (eligible, refused) whose shared border has a disc-1 vertex strictly inside r."""
    cs = set(cells)
    for c in cells:
        if c not in eligible:
            continue
        for dx, dy, side in ((1, 0, "E"), (-1, 0, "W"), (0, 1, "S"), (0, -1, "N")):
            nb = (c[0] + dx, c[1] + dy)
            if nb not in cs or nb in eligible:
                continue
            V = blk[1][c]["V"]
            if side == "E":
                on = np.abs(V[:, 0] - 64) < 1e-3
            elif side == "W":
                on = np.abs(V[:, 0]) < 1e-3
            elif side == "S":
                on = np.abs(V[:, 2] + 64) < 1e-3
            else:
                on = np.abs(V[:, 2]) < 1e-3
            XZ = blk[1][c]["XZ"][on]
            if len(XZ):
                dd = np.hypot(XZ[:, 0] - p[0], XZ[:, 1] - p[1])
                if (dd < r).any():
                    return float(abs(AMT) * falloff(dd.min() / r))      # the step height at the border
    return 0.0


# ------------------------------------------------------------------ the population
objs = L.mesh_objects()
gfn = {}


def ground(d, c, lx, lz):
    if (d, c) not in gfn:
        parts = L.blockmeshes(d, c[0], c[1], objs)
        ml = L.walk_meshlist(parts)
        gfn[(d, c)] = (ml, [L.P.build_index(bm) for _, bm in ml])
    ml, ix = gfn[(d, c)]
    return L.P.place(ml, lx, lz, 0.0, sky=True, index=ix)


centers = []
for c in refused:
    for i in range(16):
        for j in range(16):
            lx, lz = 4 * i + 0.013, -(4 * j) - 0.017
            g1 = ground(1, c, lx, lz)
            if g1[3] is None or g1[3] not in L.P.WALK_OK or g1[1] == "MISS":
                continue
            g4 = ground(4, c, lx, lz)
            centers.append((c, (64 * c[0] + 4 * i, -(64 * c[1] + 4 * j)),
                            bool(g4[3] is not None and g4[3] in L.P.WALK_OK and g4[1] != "MISS")))
print(f"walkable centres: {len(centers)} over {len({c for c, _, _ in centers})} refused cells; {time.time() - t0:.0f}s")

STRATS = ["shipped", "orderinv", "partgate", "replay", "replay_clean", "delta_v", "delta_f0", "delta_f4", "delta_f8"]
per_cell = defaultdict(lambda: defaultdict(lambda: Counter()))
tot = defaultdict(Counter)
crack_ct = defaultdict(Counter)
d1_refused = Counter()
haz_hist = defaultdict(Counter)
dv_haz = defaultdict(Counter)
d4_center_unwalkable = Counter()
samples_for_v = []
for ci, (cell, p, w4) in enumerate(centers):
    pa = np.asarray(p, float)
    dmin_uc = kd_uc.query(pa)[0]
    for r in RADII:
        dtri = dist_unmatched_tri(p, r + 8.0)
        hidx = kd_ht.query_ball_point(p, r + ht_rad)
        hd = pt_tri_dist(pa, HT[hidx]) if hidx else np.zeros(0)
        hz = sorted(set(HL[np.array(hidx)[hd < r]])) if hidx else []
        for op in ("raise", "lower", "retarget"):
            kind = "retarget" if op == "retarget" else "reshape"
            cls = f"{op}{int(r)}"
            T1 = touched(1, p, r, kind)
            if not T1:
                continue
            amt = AMT if op == "raise" else -AMT
            if kind == "reshape":
                ok1, _ = wall_gate(1, T1, p, r, amt)
                if not ok1:
                    d1_refused[cls] += 1
                    continue
            T4 = touched(4, p, r, kind)
            v = {}
            v["shipped"] = all(c in elig_ship for c in T1)
            v["orderinv"] = all(c in elig_oi for c in T1)
            v["partgate"] = all(c in elig_part for c in T1)
            if kind == "reshape":
                v["replay"] = bool(T4) and wall_gate(4, T4, p, r, amt)[0]
                v["delta_v"] = dmin_uc >= r
            else:
                v["replay"] = bool(T4)
                v["delta_v"] = not kd_utc.query_ball_point(p, r, return_length=True)
            v["replay_clean"] = v["replay"] and not hz
            for m in (0, 4, 8):
                v[f"delta_f{m}"] = dtri > r + m
            for s in STRATS:
                per_cell[cell][s][cls + ":n"] += 1
                per_cell[cell][s][cls + ":ok"] += bool(v[s])
                tot[s][cls + ":n"] += 1
                tot[s][cls + ":ok"] += bool(v[s])
            for h in hz:
                haz_hist[cls][h] += 1
                if v["delta_v"]:
                    dv_haz[cls][h] += 1             # a parametric-exact delta that still touches a hazard layer
            if not w4:
                d4_center_unwalkable[cls] += 1
            if kind == "reshape":
                for gname, el in (("shipped", elig_ship), ("orderinv", elig_oi), ("partgate", elig_part)):
                    mix = any(c in el for c in T1) and any(c not in el for c in T1)
                    crack_ct[gname][cls + ":partial"] += mix
                    stp = crack(el, T1, p, r) if mix else 0.0
                    crack_ct[gname][cls + ":crack"] += stp > 0
                    crack_ct[gname][cls + ":crack_ge0.1"] += stp >= 0.1
                    crack_ct[gname][cls + ":crack_ge1"] += stp >= 1.0
            if op == "raise" and len(T1) == 1 and len(T4) == 1 and T1 == T4:
                samples_for_v.append((cell, p, r, v["delta_v"], v["replay"]))
    if ci % 2000 == 0:
        print(f"  {ci}/{len(centers)} centres, {time.time() - t0:.0f}s", flush=True)

# ------------------------------------------------------------------ calibration V1-V3 (asserted)
rng = random.Random(11)
v1 = {"n": 0, "agree": 0}
for (cell, p, r, dv, rp) in rng.sample(samples_for_v, 40):
    for d in (1, 4):
        try:
            TER.reshape(str(L.CACHE_DIR / "v1_dry"), radius=r, at=p, amount=AMT, disc=d, game=G, dry_run=True)
            kit_ok = True
        except ValueError as e:
            if "ONE-WAY WALL" not in str(e):
                raise
            kit_ok = False
        mine = wall_gate(d, touched(d, p, r, "reshape"), p, r, AMT)[0]
        v1["n"] += 1
        v1["agree"] += kit_ok == mine
print("V1 wall-gate agreement vs terrain.reshape(dry_run):", v1)
assert v1["agree"] == v1["n"], "V1: vectorized gate must agree with the kit"
v2 = {"n": 0, "agree": 0, "lawful": 0}
for (cell, p, r, dv, rp) in rng.sample(samples_for_v, 150):
    x, y = cell
    S1 = L.decode(objs[(1, "0_1", x, y, "terrain")], 1, x, y)
    S4 = L.decode(objs[(4, "0_1", x, y, "terrain")], 4, x, y)
    E1, R4 = copy.deepcopy(S1), copy.deepcopy(S4)
    M.deform_radial(E1, amount=AMT, radius=r, center=p, world_origin=(64 * x, -64 * y))
    M.deform_radial(R4, amount=AMT, radius=r, center=p, world_origin=(64 * x, -64 * y))
    ok, why, D, _ = L.delta_transfer(S1, E1, S4, ring=0, support=(p[0] - 64 * x, p[1] + 64 * y, r))
    real = ok and M.ff9mesh_bytes(D) == M.ff9mesh_bytes(R4)
    v2["n"] += 1
    v2["agree"] += real == dv
    v2["lawful"] += real
print("V2 delta_v vs real delta+replay byte equality:", v2)
assert v2["agree"] == v2["n"], "V2: vectorized delta criterion must agree with the real transfer"
rib = json.loads((L.D4OUT / "rock_ribbons.json").read_text(encoding="utf-8"))
v3 = []
for rb in rib[:10]:
    p = tuple(rb["centroid_world"])
    hidx = kd_ht.query_ball_point(p, 8 + ht_rad)
    hz = set(HL[np.array(hidx)[pt_tri_dist(np.asarray(p), HT[hidx]) < 8]]) if hidx else set()
    v3.append({"at": p, "hazards": sorted(hz), "delta_v": bool(kd_uc.query(np.asarray(p))[0] >= 8)})
print("V3 ridge probes:", v3)
assert all("RIDGE" in r["hazards"] and not r["delta_v"] for r in v3), "V3: a ridge edit must be HAZARD + delta-refused"

# ------------------------------------------------------------------ summaries
def frac(cn, cls_list):
    n = sum(cn[c + ":n"] for c in cls_list); k = sum(cn[c + ":ok"] for c in cls_list)
    return (k / n if n else None), n


classes = [f"{op}{int(r)}" for op in ("raise", "lower", "retarget") for r in RADII]
summary = {"population": {"centres": len(centers), "cells": len({c for c, _, _ in centers}),
                          "disc1_gate_refused": dict(d1_refused), "disc4_centre_unwalkable": dict(d4_center_unwalkable)},
           "overall": {}, "by_class": {}, "cells_recovered": {}, "crack_current_design": {}, "hazards_by_class": {}}
for s in STRATS:
    f, n = frac(tot[s], classes)
    summary["overall"][s] = round(f, 4)
    summary["by_class"][s] = {c: round(tot[s][c + ":ok"] / tot[s][c + ":n"], 4) for c in classes if tot[s][c + ":n"]}
    fr = [frac(per_cell[c][s], classes)[0] for c in per_cell]
    summary["cells_recovered"][s] = {"any": sum(1 for x in fr if x and x > 0), "ge50": sum(1 for x in fr if x and x >= 0.5),
                                     "all": sum(1 for x in fr if x == 1.0), "of": len(fr)}
for g, cn in crack_ct.items():
    summary["crack_current_design"][g] = {c: {"n": tot["shipped"][c + ":n"], "partial": cn[c + ":partial"],
                                              "crack": cn[c + ":crack"], "step_ge_0.1u": cn[c + ":crack_ge0.1"],
                                              "step_ge_1u": cn[c + ":crack_ge1"]}
                                          for c in classes if not c.startswith("retarget")}
summary["n_by_class"] = {c: tot["shipped"][c + ":n"] for c in classes}
summary["hazards_by_class"] = {c: dict(h) for c, h in haz_hist.items()}
summary["delta_v_lawful_but_touching_hazard"] = {c: dict(h) for c, h in dv_haz.items()}
summary["calibration"] = {"V1": v1, "V2": v2, "V3": v3}
print(json.dumps({k: summary[k] for k in ("population", "n_by_class", "overall", "by_class", "cells_recovered", "crack_current_design")}, indent=1))
cells_out = {f"{c[0]},{c[1]}": {s: {cl: [per_cell[c][s][cl + ':ok'], per_cell[c][s][cl + ':n']] for cl in classes}
                                for s in STRATS} for c in sorted(per_cell)}
(L.OUT / "reach.json").write_text(json.dumps({"legend": "cell -> strategy -> edit class -> [lawful, n]",
                                              "cells": cells_out}, indent=0), encoding="utf-8")
(L.OUT / "reach_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
print(f"done {time.time() - t0:.0f}s")
