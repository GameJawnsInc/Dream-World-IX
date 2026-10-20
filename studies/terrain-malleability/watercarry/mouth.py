"""The stock river MOUTH at (16,15): what the river ensemble's 20.6u SEA edge welds to, and the coast it cuts through.

R1's one new mechanism is a coast splice (RECON.md R1, step 2). Before designing one: what IS the mouth?
  WELD     -- per part, the stock tris across the ensemble's SEA once-edges (sea1..5, beach1);
  BANDS    -- the water bands within 6 / 12 / 24u of the mouth, by part (is the mouth shallow-bound? THE STRICT SHORE
              LAW: shallows are shore-bound, copy-only);
  BEACH    -- beach1 components (weld-connected) near the mouth, each one's extent and its nearest approach to the mouth:
              does the river split one beach arc, or end two?
  COAST    -- the land/sea boundary near the mouth: beach vs cliff (topo 58 lip) length within 24u.
RUN:  py studies/terrain-malleability/watercarry/mouth.py   (writes out/mouth.json)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world.interior import kk3  # noqa: E402
import seat_dryrun as S  # noqa: E402


def seg_dist(px, pz, a, b):
    ex, ez = b[0] - a[0], b[2] - a[2]
    L2 = ex * ex + ez * ez
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - a[0]) * ex + (pz - a[2]) * ez) / L2))
    return math.hypot(px - (a[0] + t * ex), pz - (a[2] + t * ez))


def main():
    water, banks, allt = S.unit()
    U = water + banks
    ec = Counter(e for t in U for e in S.edge_keys(t["P"]))
    once = {e for e, n in ec.items() if n == 1}
    uid = {id(t) for t in U}
    sea_edges, weld = set(), Counter()
    for t in allt:
        if id(t) in uid or t["part"] not in S.E.SEA:
            continue
        for e in S.edge_keys(t["P"]):
            if e in once:
                sea_edges.add(e)
                weld[t["part"]] += 1
    mouth_pts = [k for e in sea_edges for k in e]
    mx = float(np.mean([k[0] for k in mouth_pts]))
    mz = float(np.mean([k[2] for k in mouth_pts]))

    def dmouth(t):
        c = t["P"].mean(axis=0)
        return min(seg_dist(c[0], c[2], e[0], e[1]) for e in sea_edges)
    bands = {}
    for r in (6, 12, 24):
        bands[r] = dict(Counter(t["part"] for t in allt if id(t) not in uid and t["part"] in S.E.SEA
                                and dmouth(t) <= r))
    # beach1 components (weld-connected) within 40u of the mouth
    bt = [t for t in allt if t["part"] == "beach1" and dmouth(t) <= 40]
    par = list(range(len(bt)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    vk = defaultdict(list)
    for i, t in enumerate(bt):
        for p in t["P"]:
            vk[kk3(p)].append(i)
    for idx in vk.values():
        for j in idx[1:]:
            par[f(j)] = f(idx[0])
    comps = defaultdict(list)
    for i in range(len(bt)):
        comps[f(i)].append(bt[i])
    beach = []
    for c in comps.values():
        P = np.concatenate([t["P"] for t in c])
        beach.append({"tris": len(c), "x": [round(float(P[:, 0].min()), 1), round(float(P[:, 0].max()), 1)],
                      "z": [round(float(P[:, 2].min()), 1), round(float(P[:, 2].max()), 1)],
                      "nearest_to_mouth": round(min(dmouth(t) for t in c), 2)})
    beach.sort(key=lambda b: b["nearest_to_mouth"])
    # coast kind near the mouth: land tris (terrain) that weld to a sea/beach tri, by topograph, within 24u
    sea_keys = {kk3(p) for t in allt if t["part"] in S.E.SEA for p in t["P"]}
    coast = Counter()
    for t in allt:
        if t["part"] == "terrain" and dmouth(t) <= 24 and any(kk3(p) in sea_keys for p in t["P"]):
            coast[t["topo"]] += 1
    rep = {"mouth_centre": [round(mx, 1), round(mz, 1)], "sea_edges": len(sea_edges),
           "sea_edge_len": round(sum(math.dist(e[0], e[1]) for e in sea_edges), 1),
           "weld_parts": dict(weld), "bands_within": bands, "beach_components": beach,
           "coast_topos_within_24u": dict(coast.most_common(8))}
    print(json.dumps(rep, indent=1))
    (HERE / "out" / "mouth.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
