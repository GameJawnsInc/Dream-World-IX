"""THE PALETTE CENSUS -- what landmasses can we actually carry, now that excise v2 landed?

The first donor census asked "which rects contain a landmass WHOLE and clear of the
frame", because any frame-crossing neighbour shipped as a ruler-straight slice hanging in
mid-air. Excise changed the question: a foreign mass can now be dropped and the deep sheet
re-zipped over it, so a rect qualifies if it holds at least one mass whole -- whatever else
is in the way.

This re-enumerates the whole map under the new rule and ranks what it finds by what makes
a landmass worth carrying (measured in the outline census, not asserted):

  * AREA of the largest kept mass -- below ~500u2 an island reads as a rock, not a place
  * RELIEF (p95 height) -- the outline census found relief carries the horizon; plan shape
    does not read at the game camera
  * WALKABLE fraction -- a cape you cannot walk out onto is scenery
  * how much has to be EXCISED to get it -- authored surface, so less is better

Offline over the cached landmask, so it enumerates thousands of rects in seconds. It is a
SHORTLIST, not a verdict: excise also needs the foreign masses to be vertex-separable and
the fill to trianglulate, which only a real --dry-run proves. Verify the top rows.

  py studies/coast-shape-language/palette_census.py [--disc 1] [--top 20]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CELL = 4.0
BLK = 16                                  # 4u cells per 64u block
NX, NY = 24, 20


def label_wrapped(land):
    """4-connected components with x-wrap (the world is a cylinder)."""
    nz, nx = land.shape
    lab = np.zeros((nz, nx), np.int32)
    cur = 0
    for z0 in range(nz):
        for x0 in range(nx):
            if not land[z0, x0] or lab[z0, x0]:
                continue
            cur += 1
            stack = [(z0, x0)]
            lab[z0, x0] = cur
            while stack:
                z, x = stack.pop()
                for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nzz, nxx = z + dz, (x + dx) % nx
                    if 0 <= nzz < nz and land[nzz, nxx] and not lab[nzz, nxx]:
                        lab[nzz, nxx] = cur
                        stack.append((nzz, nxx))
    return lab, cur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=int, default=1)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--min-area", type=float, default=500.0)
    args = ap.parse_args()

    d = np.load(HERE / "out" / f"landmask_d{args.disc}.npz")
    land, foot, hgt = d["land"], d["foot"], d["hgt"]
    lab, n = label_wrapped(land)
    print(f"[disc {args.disc}] {n} landmasses on the LAND mask")

    # per-mass facts
    info = {}
    for i in range(1, n + 1):
        zz, xx = np.nonzero(lab == i)
        h = hgt[zz, xx]
        h = h[~np.isnan(h)]
        info[i] = dict(
            cells=len(zz), area=len(zz) * CELL * CELL,
            relief=float(np.percentile(h, 95)) if len(h) else 0.0,
            walk=float(foot[zz, xx].mean()),
            x0=int(xx.min()), x1=int(xx.max()), z0=int(zz.min()), z1=int(zz.max()))

    rows = []
    for ny in range(1, 5):
        for nx in range(1, 5):
            for by in range(0, NY - ny + 1):
                for bx in range(0, NX - nx + 1):
                    z0, z1 = by * BLK, (by + ny) * BLK
                    x0, x1 = bx * BLK, (bx + nx) * BLK
                    sub = lab[z0:z1, x0:x1]
                    present = set(np.unique(sub)) - {0}
                    if not present:
                        continue
                    kept, foreign, ex_cells = [], [], 0
                    for m in present:
                        f = info[m]
                        whole = (f["x0"] >= x0 and f["x1"] < x1
                                 and f["z0"] >= z0 and f["z1"] < z1)
                        # clearance: at least one cell of margin inside the frame
                        clear = whole and (f["x0"] > x0 and f["x1"] < x1 - 1
                                           and f["z0"] > z0 and f["z1"] < z1 - 1)
                        if clear:
                            kept.append(m)
                        else:
                            foreign.append(m)
                            ex_cells += int((sub == m).sum())
                    if not kept:
                        continue
                    best = max(kept, key=lambda m: info[m]["area"])
                    f = info[best]
                    if f["area"] < args.min_area:
                        continue
                    rows.append(dict(
                        donor=[bx, by], size=[nx, ny], mass=int(best),
                        area=f["area"], relief=round(f["relief"], 1),
                        walk=round(f["walk"], 2), kept=len(kept),
                        excise_cells=ex_cells, foreign=len(foreign)))

    # best rect per mass: smallest excise, then smallest rect
    bymass = {}
    for r in rows:
        k = r["mass"]
        cur = bymass.get(k)
        if cur is None or (r["excise_cells"], r["size"][0] * r["size"][1]) < \
                (cur["excise_cells"], cur["size"][0] * cur["size"][1]):
            bymass[k] = r
    best = sorted(bymass.values(), key=lambda r: -r["area"])

    print(f"   {len(rows)} qualifying rects -> {len(best)} distinct carryable masses "
          f"(>= {args.min_area:.0f}u2)\n")
    print(f"{'donor':>10} {'size':>5} {'area u2':>9} {'relief':>7} {'walk':>5} "
          f"{'excise':>7}  note")
    for r in best[:args.top]:
        note = "clean carry" if r["excise_cells"] == 0 else \
               f"excise {r['foreign']} foreign mass(es)"
        print(f"{str(tuple(r['donor'])):>10} {r['size'][0]}x{r['size'][1]:<3} "
              f"{r['area']:>9.0f} {r['relief']:>7.1f} {r['walk']:>5.2f} "
              f"{r['excise_cells']:>7}  {note}")

    out = HERE / "out" / f"palette_d{args.disc}.json"
    out.write_text(json.dumps(dict(masses=best, all_rects=len(rows)), indent=1),
                   encoding="utf-8")
    print(f"\n-> {out}")
    print("SHORTLIST ONLY -- excise also needs vertex-separable assemblies and a fill that "
          "triangulates.\nVerify a row with: world-transplant --donor BX,BY --size NXxNY "
          "--excise --dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
