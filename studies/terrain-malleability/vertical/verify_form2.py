"""VERIFIER: the lane's census reads ONLY the `0_1` mesh set. The bundle also ships a `0_2` set (26 terrain /
26 object blocks per disc -- the FORM-2 meshes of switchable blocks, WMBlock.Form2WalkMeshes, made active by
ResetBlockForms after story events). Does including them change any vertical claim?

Per disc and part of the 0_2 set: vertex y min/max, the topo ids present (vs the 14 flight-blocked ids of V12),
sea verts off y=0, sub-zero up-facing foot-legal tris, and the tallest block per part.
Read-only. Writes out/verify_form2.json.
Run: py studies/terrain-malleability/vertical/verify_form2.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                   # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
EB = json.loads((OUT / "engine_bounds.json").read_text())["derived"]
FLIGHT_BLOCKED = set(EB["flight_blocked_topos"])
res = {}
for disc in (1, 4):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/0_2/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[m.group(3)].add((int(m.group(1)), int(m.group(2))))
    rd = {"parts": {}, "topo_presence": Counter(), "flight_blocked_present": {}, "subzero_footlegal_up_tris": [],
          "blocks": sorted({b for v in per.values() for b in v})}
    for part, blocks in sorted(per.items()):
        ymin, ymax, best, offz = 1e9, -1e9, None, 0
        for (bx, by) in sorted(blocks):
            bm = X.read_block(bx, by, disc=disc, lod="0_2", part=part)
            V = np.asarray(bm.verts, dtype=float)
            if V.size == 0:
                continue
            F = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
            T = bm.tangents
            ids = np.array([int(round(T[i][0])) for i in F[:, 0]]) if T is not None else np.zeros(len(F), int)
            topo = (ids & 0xFC) >> 2
            rd["topo_presence"].update(int(t) for t in topo)
            if V[:, 1].min() < ymin:
                ymin = float(V[:, 1].min())
            if V[:, 1].max() > ymax:
                ymax = float(V[:, 1].max()); best = [bx, by]
            if part.startswith("sea"):
                offz += int((np.abs(V[:, 1]) > 1e-6).sum())
            a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
            cr = np.cross(b - a, c - a)
            L = np.linalg.norm(cr, axis=1)
            ny = np.where(L > 0, cr[:, 1] / np.where(L > 0, L, 1), 0)
            ys = np.stack([a[:, 1], b[:, 1], c[:, 1]], 1)
            sz = (ys.min(1) < 0) & (ny > 0.1) & np.isin(topo, list(P.WALK_OK))
            if sz.any():
                rd["subzero_footlegal_up_tris"].append({"part": part, "block": [bx, by], "tris": int(sz.sum()),
                                                         "min_y": round(float(ys.min(1)[sz].min()), 3)})
        rd["parts"][part] = {"blocks": len(blocks), "vert_y_min": round(ymin, 3), "vert_y_max": round(ymax, 3),
                             "tallest_block": best, **({"sea_verts_off_zero": offz} if part.startswith("sea") else {})}
    rd["flight_blocked_present"] = {t: rd["topo_presence"][t] for t in sorted(FLIGHT_BLOCKED) if rd["topo_presence"].get(t)}
    rd["topo_presence"] = dict(sorted(rd["topo_presence"].items()))
    res[f"disc{disc}"] = rd
    print(f"== disc {disc} 0_2 set: {len(rd['blocks'])} blocks {rd['blocks']}")
    for p, v in rd["parts"].items():
        print("  ", p, v)
    print("   topo presence:", rd["topo_presence"])
    print("   FLIGHT-BLOCKED present:", rd["flight_blocked_present"] or "NONE")
    print("   sub-zero foot-legal up-facing tris:", rd["subzero_footlegal_up_tris"])
(OUT / "verify_form2.json").write_text(json.dumps(res, indent=1, default=str))
print("wrote", OUT / "verify_form2.json")
