"""THE SHAPE PROBE -- locate and measure stock FF9's OUTLINE vocabulary.

Six classes, each a morphology question asked of the land mask from shape_census.py:

  lagoon     sea not reachable from the open ocean            (enclosed water)
  bay        concavity closed by a mouth narrower than it     (gulf / cove / inlet)
  cape       land removed by an opening                       (peninsula / spit / horn)
  isthmus    a land neck whose cut would disconnect the mass  (land bridge)
  strait     a sea corridor with land on both sides           (channel / narrows)
  chain      a cluster of small masses within reach           (archipelago)

  py studies/coast-shape-language/shape_probe.py [--disc 1]

Every metric is in WORLD UNITS, and every instance reports the BLOCK it lives in,
because block (bx,by) is the unit every builder verb actually addresses.

THE WRAP IS NOT OPTIONAL. The world is a cylinder in x; a morphology op run on the
raw array invents a coastline down both map edges. Every op here runs on an
x-tiled pad and crops back.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
G, BLOCK = 4.0, 64.0
PAD = 48                                   # cells of x-wrap margin


def _disc(r: int):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def wrapped(fn):
    """Run a mask->mask op on an x-tiled pad so the cylinder seam is real."""
    def go(m, *a, **k):
        p = np.concatenate([m[:, -PAD:], m, m[:, :PAD]], axis=1)
        return fn(p, *a, **k)[:, PAD:-PAD]
    return go


close_ = wrapped(lambda m, r: ndi.binary_closing(m, _disc(r)))
open_ = wrapped(lambda m, r: ndi.binary_opening(m, _disc(r)))
dilate_ = wrapped(lambda m, r: ndi.binary_dilation(m, _disc(r)))


def labels(m):
    """Connected components with the x-wrap stitched."""
    lab, n = ndi.label(m)
    for z in range(m.shape[0]):                       # stitch the seam
        a, b = lab[z, 0], lab[z, -1]
        if a and b and a != b:
            lab[lab == b] = a
    return lab


def _cell_world(cz, cx):
    return round(cx * G + G / 2, 1), round(-(cz * G + G / 2), 1)


def _block(cz, cx):
    return [int(cx * G // BLOCK), int(cz * G // BLOCK)]


def _inst(kind, cells, land, foot, **extra):
    zs = np.array([c[0] for c in cells])
    xs = np.array([c[1] for c in cells])
    cz, cx = int(round(zs.mean())), int(round(xs.mean()))
    wx, wz = _cell_world(cz, cx)
    walk = float(np.mean([foot[z, x] for z, x in cells])) if kind in ("cape", "isthmus") else None
    d = dict(kind=kind, cells=len(cells), area_u2=round(len(cells) * G * G),
             at=[wx, wz], block=_block(cz, cx),
             span_u=[round((xs.max() - xs.min() + 1) * G),
                     round((zs.max() - zs.min() + 1) * G)])
    if walk is not None:
        d["walkable_frac"] = round(walk, 2)
    d.update(extra)
    return d


def find_lagoons(land, foot):
    sea = ~land
    lab = labels(sea)
    # the open ocean is the component touching the map's north or south edge
    ocean = set(lab[0][lab[0] > 0]) | set(lab[-1][lab[-1] > 0])
    out = []
    for i in range(1, lab.max() + 1):
        if i in ocean or not (lab == i).any():
            continue
        cells = list(zip(*np.where(lab == i)))
        if len(cells) < 4:                           # 64u^2 -- below this it is a pond
            continue
        out.append(_inst("lagoon", cells, land, foot))
    return sorted(out, key=lambda d: -d["cells"])


def find_bays(land, foot, r=7):
    """A bay = concavity filled by a closing of radius r (mouth < 2r wide)."""
    fill = close_(land, r) & ~land
    lab = labels(fill)
    out = []
    for i in range(1, lab.max() + 1):
        cells = list(zip(*np.where(lab == i)))
        if len(cells) < 12:
            continue
        m = np.zeros_like(land)
        for z, x in cells:
            m[z, x] = True
        # depth = how far the concavity reaches from its mouth
        depth = float(ndi.distance_transform_edt(m).max()) * G
        out.append(_inst("bay", cells, land, foot,
                         depth_u=round(depth, 1), mouth_max_u=2 * r * G))
    return sorted(out, key=lambda d: -d["cells"])


def find_capes(land, foot, r=5):
    """A cape = land an opening of radius r removes (a limb thinner than 2r).

    THE REACH MUST BE MEASURED INSIDE THE LIMB'S OWN MASS. The first cut ran one
    global distance transform to the opened core, so an islet with no core of its
    own scored its distance to ANOTHER CONTINENT: the top-left islet came back as
    a 357u cape, longer than any real headland in the game. A mass the opening
    erases entirely is an ISLET (a chain member), not a cape, and is skipped here.
    """
    core = open_(land, r)
    lab_land = labels(land)
    lab = labels(land & ~core)
    dcache: dict[int, np.ndarray] = {}

    def dist_to_core(mid):
        if mid not in dcache:
            own = core & (lab_land == mid)
            dcache[mid] = (ndi.distance_transform_edt(~own) if own.any() else None)
        return dcache[mid]

    out = []
    for i in range(1, lab.max() + 1):
        cells = list(zip(*np.where(lab == i)))
        if len(cells) < 12:
            continue
        mid = int(lab_land[cells[0][0], cells[0][1]])
        d = dist_to_core(mid)
        if d is None:                                 # coreless mass = an islet
            continue
        m = np.zeros_like(land)
        for z, x in cells:
            m[z, x] = True
        reach = float(max(d[z, x] for z, x in cells)) * G
        width = float(ndi.distance_transform_edt(m).max()) * 2 * G
        if reach < 12.0:                              # a bump, not a cape
            continue
        out.append(_inst("cape", cells, land, foot,
                         reach_u=round(reach, 1), width_u=round(width, 1),
                         slenderness=round(reach / max(width, 1e-6), 2),
                         mass=mid))
    return sorted(out, key=lambda d: -d["reach_u"])


def find_isthmuses(land, foot, max_w=10, min_side=60):
    """A neck: land whose removal splits its mass, narrower than max_w cells.

    ``min_side`` is what makes it an ISTHMUS rather than a pinch. Without it the
    probe returned 338 instances, mostly 64u2 rock fringes whose "cut" merely
    shaved a pebble off a coast. A land bridge joins two SUBSTANTIAL bodies, so
    both sides of the cut must survive at min_side cells.
    """
    lab = labels(land)
    out = []
    for i in range(1, lab.max() + 1):
        mass = lab == i
        if mass.sum() < 200:
            continue
        base = len(np.unique(labels(mass))) - 1
        d = ndi.distance_transform_edt(mass)
        # candidate necks: thin land (small distance) that is not just coast fringe.
        # DO NOT break at the first width that disconnects -- the first cut did, so
        # every mass reported only its very thinnest neck and every isthmus in the
        # world came back as exactly 8.0u wide. Necks of different widths coexist.
        seen = np.zeros_like(mass)
        for w in range(1, max_w + 1):
            thin = mass & (d <= w) & (d > w - 1) & ~seen
            if not thin.any():
                continue
            cut = mass & ~dilate_(thin, 1)
            if len(np.unique(labels(cut))) - 1 <= base:
                continue
            cl = labels(thin)
            for j in range(1, cl.max() + 1):
                cells = list(zip(*np.where(cl == j)))
                if len(cells) < 4:
                    continue
                test = mass & ~dilate_(cl == j, 1)
                tl = labels(test)
                sides = sorted((int((tl == k).sum()) for k in range(1, tl.max() + 1)),
                               reverse=True)
                if len(sides) < 2 or sides[1] < min_side:
                    continue                       # shaved a pebble, not a bridge
                seen |= dilate_(cl == j, 2)
                out.append(_inst("isthmus", cells, land, foot,
                                 width_u=round(2 * w * G, 1), mass=int(i),
                                 joins_u2=[round(s * G * G) for s in sides[:2]]))
    return sorted(out, key=lambda d: d["width_u"])


def find_straits(land, foot, max_gap=18, min_len=6, min_side=60):
    """The narrowest water between two DIFFERENT landmasses.

    The first cut took "sea within r of any land" as the corridor, which is a
    band around every shore in the world: it returned three 100k-u2 "straits"
    that were simply the whole coastal ring, and they passed the separates->=2
    test trivially because one ring touches many islands. A strait is not water
    near land, it is the GAP BETWEEN TWO MASSES -- so measure it as such, on the
    land-label Voronoi, and report the narrowest crossing per pair.
    """
    lab_land = labels(land)
    p = np.concatenate([lab_land[:, -PAD:], lab_land, lab_land[:, :PAD]], axis=1)
    d, idx = ndi.distance_transform_edt(p == 0, return_indices=True)
    owner = p[idx[0], idx[1]][:, PAD:-PAD]
    dist = d[:, PAD:-PAD]
    gh, gw = land.shape

    best: dict[tuple[int, int], tuple] = {}
    for z in range(gh):
        for x in range(gw):
            if land[z, x]:
                continue
            a = int(owner[z, x])
            if not a:
                continue
            for dz, dx in ((1, 0), (0, 1)):
                nz, nx = z + dz, (x + dx) % gw
                if nz >= gh or land[nz, nx]:
                    continue
                b = int(owner[nz, nx])
                if not b or b == a:
                    continue
                key = (min(a, b), max(a, b))
                w = (dist[z, x] + dist[nz, nx]) * G       # full crossing width
                if w > max_gap * G:
                    continue
                if key not in best or w < best[key][0]:
                    best[key] = (w, z, x)

    # a real strait is a RUN of medial cells, not one pinch point
    runs: dict[tuple[int, int], int] = {}
    for z in range(gh):
        for x in range(gw):
            if land[z, x]:
                continue
            a = int(owner[z, x])
            for dz, dx in ((1, 0), (0, 1)):
                nz, nx = z + dz, (x + dx) % gw
                if nz >= gh or land[nz, nx]:
                    continue
                b = int(owner[nz, nx])
                if not b or not a or b == a:
                    continue
                key = (min(a, b), max(a, b))
                if key in best and (dist[z, x] + dist[nz, nx]) * G <= max_gap * G:
                    runs[key] = runs.get(key, 0) + 1

    size = {int(i): int((lab_land == i).sum()) for i in np.unique(lab_land) if i}
    out = []
    for key, (w, z, x) in best.items():
        if runs.get(key, 0) < min_len:
            continue
        # both shores must be substantial, else it is a gap between two pebbles
        if min(size.get(key[0], 0), size.get(key[1], 0)) < min_side:
            continue
        out.append(_inst("strait", [(z, x)], land, foot,
                         width_u=round(w, 1), separates=list(key),
                         shores_u2=[round(size[k] * G * G) for k in key],
                         length_u=round(runs[key] * G, 1)))
    return sorted(out, key=lambda d: d["width_u"])


def find_chains(land, foot, gap=10, min_n=3):
    """An archipelago: >=min_n small masses whose dilations merge."""
    lab = labels(land)
    small = np.zeros_like(land)
    sizes = {}
    for i in range(1, lab.max() + 1):
        n = int((lab == i).sum())
        sizes[i] = n
        if 4 <= n <= 700:
            small |= lab == i
    grp = labels(dilate_(small, gap))
    out = []
    for i in range(1, grp.max() + 1):
        members = {int(lab[z, x]) for z, x in zip(*np.where((grp == i) & small))}
        if len(members) < min_n:
            continue
        cells = list(zip(*np.where((grp == i) & small)))
        out.append(_inst("chain", cells, land, foot, islands=len(members),
                         island_sizes=sorted((round(sizes[m] * G * G) for m in members),
                                             reverse=True)[:8]))
    return sorted(out, key=lambda d: -d["islands"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    d = np.load(HERE / "out" / f"landmask_d{args.disc}.npz")
    land, foot = d["land"], d["foot"]

    res = {}
    for name, fn in (("lagoon", find_lagoons), ("bay", find_bays),
                     ("cape", find_capes), ("isthmus", find_isthmuses),
                     ("strait", find_straits), ("chain", find_chains)):
        res[name] = fn(land, foot)
        print(f"{name:>8}: {len(res[name]):>3} instances")
        for x in res[name][:6]:
            extra = " ".join(f"{k}={v}" for k, v in x.items()
                             if k in ("reach_u", "width_u", "depth_u", "islands",
                                      "slenderness", "walkable_frac"))
            print(f"          {x['area_u2']:>7}u2 at {str(x['at']):>18} "
                  f"blk {x['block']}  {extra}")
    p = HERE / "out" / f"shapes_d{args.disc}.json"
    p.write_text(json.dumps(dict(disc=args.disc, **res), indent=1), encoding="utf-8")
    print(f"\n-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
