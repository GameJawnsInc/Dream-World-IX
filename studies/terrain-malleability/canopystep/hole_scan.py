"""THE COAST HOLES: where a lab island's own parts leave the plan uncovered, so the game shows sky through the sea.

The owner saw "multiple slivers/seams in the water next to the coast wall" in round 23; the stills put each at a
cove's inner corner, and the sliver's colour is the sky's (205, 217, 247): a hole, not paint. The lab islands sit on
open-ocean blocks with no prefab, so the island's own override parts (Terrain + every Sea/Beach part it writes) are all
that renders there: any plan point inside those blocks that no tri covers is a hole. This rasterises every written
part on a 0.25u grid and reports the uncovered points, clustered, with the parts round each cluster.
  RUN:  py studies/terrain-malleability/canopystep/hole_scan.py MOD_FOLDER [MOD_FOLDER ...]
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import mesh as M  # noqa: E402

STEP = 0.25
PAT = re.compile(r"Block\[(\d+)\]\[(\d+)\] (\w+)\.ff9mesh$")


def scan(folder: Path):
    root = folder / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    parts = {}
    for p in root.rglob("*.ff9mesh"):
        m = PAT.search(p.name)
        if not m:
            continue
        bx, by, part = int(m[1]), int(m[2]), m[3]
        d = M.read_ff9mesh(p)
        if not d["indices"]:
            continue
        V = np.asarray(d["verts"], float) + np.array([64.0 * bx, 0.0, -64.0 * by])
        T = V[np.asarray(d["indices"]).reshape(-1, 3)]
        if T[:, :, 1].max() < -50:                       # a hidden stub (the kit's y -80 blanks)
            continue
        parts.setdefault((bx, by), []).append((part, T))
    holes = []
    for (bx, by), plist in sorted(parts.items()):
        xs = np.arange(64.0 * bx + STEP / 2, 64.0 * bx + 64.0, STEP)
        zs = np.arange(-64.0 * by - STEP / 2, -64.0 * by - 64.0, -STEP)
        X, Z = np.meshgrid(xs, zs)
        P = np.stack([X.ravel(), Z.ravel()], 1)
        covered = np.zeros(len(P), bool)
        for _, T in plist:
            a, b, c = T[:, 0, [0, 2]], T[:, 1, [0, 2]], T[:, 2, [0, 2]]
            for k in range(len(T)):
                lo = np.minimum(np.minimum(a[k], b[k]), c[k]) - 1e-6
                hi = np.maximum(np.maximum(a[k], b[k]), c[k]) + 1e-6
                sel = np.where((P[:, 0] >= lo[0]) & (P[:, 0] <= hi[0]) & (P[:, 1] >= lo[1]) & (P[:, 1] <= hi[1])
                               & ~covered)[0]
                if not len(sel):
                    continue
                q = P[sel]
                d = (b[k][1] - c[k][1]) * (a[k][0] - c[k][0]) + (c[k][0] - b[k][0]) * (a[k][1] - c[k][1])
                if abs(d) < 1e-12:
                    continue
                l1 = ((b[k][1] - c[k][1]) * (q[:, 0] - c[k][0]) + (c[k][0] - b[k][0]) * (q[:, 1] - c[k][1])) / d
                l2 = ((c[k][1] - a[k][1]) * (q[:, 0] - c[k][0]) + (a[k][0] - c[k][0]) * (q[:, 1] - c[k][1])) / d
                inside = (l1 >= -1e-9) & (l2 >= -1e-9) & (1 - l1 - l2 >= -1e-9)
                covered[sel[inside]] = True
        for x, z in P[~covered]:
            holes.append((float(x), float(z), bx, by, sorted({pt for pt, _ in plist})))
    # cluster the uncovered points (8-neighbour on the grid)
    key = {(round(x / STEP), round(z / STEP)): i for i, (x, z, *_) in enumerate(holes)}
    seen, clusters = set(), []
    for k0 in key:
        if k0 in seen:
            continue
        st, comp = [k0], []
        seen.add(k0)
        while st:
            k = st.pop()
            comp.append(key[k])
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    n = (k[0] + dx, k[1] + dz)
                    if n in key and n not in seen:
                        seen.add(n)
                        st.append(n)
        pts = np.array([holes[i][:2] for i in comp])
        clusters.append({"points": len(comp), "area": round(len(comp) * STEP * STEP, 3),
                         "centre": [round(float(pts[:, 0].mean()), 2), round(float(pts[:, 1].mean()), 2)],
                         "box": [round(float(pts[:, 0].min()), 2), round(float(pts[:, 0].max()), 2),
                                 round(float(pts[:, 1].min()), 2), round(float(pts[:, 1].max()), 2)],
                         "block": list(holes[comp[0]][2:4]), "parts": holes[comp[0]][4]})
    clusters.sort(key=lambda c: -c["points"])
    return {"folder": str(folder), "blocks": sorted(parts), "holes": len(holes), "clusters": clusters}


def main():
    out = []
    for f in sys.argv[1:]:
        r = scan(Path(f))
        out.append(r)
        print(f"{Path(f).parent.name}/{Path(f).name}: {len(r['blocks'])} blocks, {r['holes']} uncovered grid points in "
              f"{len(r['clusters'])} cluster(s)")
        for c in r["clusters"][:10]:
            print(f"   {c['points']:>4} pts ({c['area']} u2) at {c['centre']} block {c['block']} box {c['box']}")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "hole_scan.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
