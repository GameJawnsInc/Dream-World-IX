"""THE OUTLINE CENSUS -- what SHAPES does stock FF9 actually build its landmasses from?

The interior census (studies/overworld-topography/census.py) answered "what is inland
made of". This answers the orthogonal question the coast arc now needs: **what is the
stock world's OUTLINE vocabulary** -- capes, bays, isthmuses, straits, spits, lagoons,
archipelagos -- measured, not eyeballed off the painted map.

Reads the user's OWN install (no game bytes in the repo). Emits into --out:

  landmask.npz     per-4u-cell land mask + height + topo, disc 1 and disc 4
  outline.json     landmasses (connected components) with per-mass shape metrics
  shapes.json      the located shape INSTANCES (cape/bay/isthmus/strait/...)
  outline_map.png  the mask with every located instance annotated

  py studies/coast-shape-language/shape_census.py [--disc 1] [--out DIR]

TWO MASKS, AND THEY ARE NOT THE SAME QUESTION. The first cut of this script built only
the FOOT mask and reported 102 "landmasses" with circularity as low as 0.016 -- which is
not a coastline measurement at all. Mountain rock (topo 49) is foot-ILLEGAL and covers
164 of disc 1's 260 blocks, so the foot mask fragments every continent along its ranges:
it measures the WALKABLE PARTITION, not the outline. So:

  land  -- any Terrain tri in the cell (the Terrain part excludes sea/beach meshes
           by construction). This is the OUTLINE: what reads as land from offshore.
  foot  -- foot-legal topographs only. This is where a player can actually stand.

Coast-shape work wants ``land``; reachability work wants ``foot``; the interesting
design questions live in the DIFFERENCE (a cape you cannot walk out onto is scenery).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

# the engine on-foot topograph set (w_movementCheckTopographID masks)
FOOT = set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31} \
     | set(range(32, 39)) | {41, 42, 45, 46, 52}
G = 4.0                                  # the engine tile lattice
BLOCK = 64.0
NX, NY = 24, 20                          # the block grid
GW, GH = int(NX * BLOCK / G), int(NY * BLOCK / G)   # 384 x 320 cells


def wrapx(gx: int) -> int:
    """The world is a CYLINDER in x -- every neighbourhood op must wrap."""
    return gx % GW


def build_mask(disc: int = 1):
    """Per-cell land mask, foot mask, mean height and dominant topograph."""
    land = np.zeros((GH, GW), dtype=bool)
    foot = np.zeros((GH, GW), dtype=bool)
    hgt = np.full((GH, GW), np.nan, dtype=np.float32)
    topo = np.full((GH, GW), -1, dtype=np.int16)
    prio = np.zeros((GH, GW), dtype=np.float32)
    blocks = X.list_blocks(disc=disc)
    for n, (bx, by) in enumerate(blocks):
        bm = X.read_block(bx, by, disc=disc)
        v = np.asarray(bm.verts, dtype=np.float64)
        tan = bm.tangents
        ox, oz = BLOCK * bx, -BLOCK * by
        for tri in bm.tris:
            a, b, c = v[tri[0]], v[tri[1]], v[tri[2]]
            t = X.decode_id(int(tan[tri[0]][0]))["topograph"]
            # plan area, so a vertical cliff face cannot outvote the ground it abuts
            plan = 0.5 * abs((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2]))
            cx = (a[0] + b[0] + c[0]) / 3 + ox
            cz = (a[2] + b[2] + c[2]) / 3 + oz
            cy = (a[1] + b[1] + c[1]) / 3
            gx, gz = int(cx // G), int((-cz) // G)
            if not (0 <= gx < GW and 0 <= gz < GH):
                continue
            land[gz, gx] = True            # the Terrain part IS the land
            if t in FOOT:
                foot[gz, gx] = True
            if plan > prio[gz, gx]:
                prio[gz, gx] = plan
                topo[gz, gx] = t
                hgt[gz, gx] = cy
        if n % 40 == 0:
            print(f"   ...{n}/{len(blocks)} blocks", flush=True)
    return land, foot, hgt, topo


def components(mask):
    """Connected landmasses (4-connectivity, x wrapping)."""
    seen = np.zeros_like(mask, dtype=bool)
    comps = []
    for z0 in range(GH):
        for x0 in range(GW):
            if not mask[z0, x0] or seen[z0, x0]:
                continue
            stack, cells = [(z0, x0)], []
            seen[z0, x0] = True
            while stack:
                z, x = stack.pop()
                cells.append((z, x))
                for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nz, nx = z + dz, wrapx(x + dx)
                    if 0 <= nz < GH and mask[nz, nx] and not seen[nz, nx]:
                        seen[nz, nx] = True
                        stack.append((nz, nx))
            comps.append(cells)
    comps.sort(key=len, reverse=True)
    return comps


def _mass_metrics(cells, mask):
    """Shape descriptors for one landmass, all in world units."""
    cs = set(cells)
    area = len(cells) * G * G
    # perimeter = mask edges facing not-land
    per = 0
    for z, x in cells:
        for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nz, nx = z + dz, wrapx(x + dx)
            if not (0 <= nz < GH) or (nz, nx) not in cs:
                per += 1
    per_u = per * G
    zs = [z for z, _ in cells]
    # x extent must respect the wrap: measure the largest empty x-gap
    xs = sorted({x for _, x in cells})
    if len(xs) > 1:
        gaps = [(xs[i + 1] - xs[i]) for i in range(len(xs) - 1)] + [xs[0] + GW - xs[-1]]
        w = (GW - max(gaps) + 1) * G
    else:
        w = G
    h = (max(zs) - min(zs) + 1) * G
    # circularity: 1.0 = a disc, ->0 = a filament. The discriminant that separates
    # a compact island from a peninsula-rich continent.
    circ = 4 * math.pi * area / (per_u * per_u) if per_u else 0.0
    return dict(cells=len(cells), area_u2=round(area), perim_u=round(per_u),
                bbox_u=[round(w), round(h)], circularity=round(circ, 3),
                z_range=[min(zs) * G, (max(zs) + 1) * G])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=int, default=1)
    ap.add_argument("--out", default=str(Path(__file__).parent / "out"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[disc {args.disc}] building the masks...", flush=True)
    land, foot, hgt, topo = build_mask(args.disc)
    np.savez_compressed(out / f"landmask_d{args.disc}.npz",
                        land=land, foot=foot, hgt=hgt, topo=topo)
    tot = GW * GH
    print(f"   land {int(land.sum())} cells ({100.0 * land.sum() / tot:.1f}%), "
          f"foot {int(foot.sum())} ({100.0 * foot.sum() / tot:.1f}%) -- "
          f"{100.0 * (land.sum() - foot.sum()) / max(1, land.sum()):.0f}% of land is "
          f"un-standable (cliff/mountain)")

    report = {}
    for name, mask in (("land", land), ("foot", foot)):
        comps = components(mask)
        masses = []
        for i, c in enumerate(comps):
            m = _mass_metrics(c, mask)
            m["id"] = i
            zs = [z for z, _ in c]
            xs = [x for _, x in c]
            m["centroid_cell"] = [int(round(np.mean(xs))), int(round(np.mean(zs)))]
            masses.append(m)
        big = [m for m in masses if m["cells"] >= 16]
        print(f"   [{name}] {len(comps)} components, {len(big)} of >=16 cells")
        for m in big[:12]:
            print(f"      #{m['id']:<3} {m['cells']:>6} cells  {m['area_u2']:>8}u2  "
                  f"bbox {m['bbox_u'][0]:>4}x{m['bbox_u'][1]:<4}  "
                  f"circ {m['circularity']:.3f}")
        report[name] = masses
    (out / f"outline_d{args.disc}.json").write_text(
        json.dumps(dict(disc=args.disc, grid=[GW, GH], cell=G, **report), indent=1),
        encoding="utf-8")
    print(f"   -> {out / f'outline_d{args.disc}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
