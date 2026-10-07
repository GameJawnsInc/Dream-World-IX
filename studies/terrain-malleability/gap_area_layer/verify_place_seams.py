"""ADVERSARIAL VERIFY (GA2 / GA5): is camera place really seam-free on stock walkable ground, and is the disc-4 area
change a RELABEL (same land, new label) or a geometry change?

Independent of the lane's parse: w_cameraArea2Place is re-parsed here straight from ff9.cs with its own regex.
Seams are counted under FOUR walkability definitions, widening the lane's (land part AND topo in WALK_OK):
  L  the lane's definition (Object/Terrain/Volcano part AND WALK_OK topo)
  B  any non-MISS sample with a WALK_OK topo (so Beach1/2, Sea rims with walkable topos count)
  A  any non-MISS LAND-part sample regardless of topograph (cliffs, 49s included)
  D  definition B with 8-neighbourhood (diagonals) AND a 2-sample reach (a 1u sliver of non-walkable between two
     walkable samples of different places counts)
Also a can-fail control: a synthetic place-1 stamp of a 20x20 patch inside a place-0 walkable region must register
seams under L.

Rerun: py studies/terrain-malleability/gap_area_layer/verify_place_seams.py
"""
import re
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import placement as P  # noqa: E402

src = Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp\Global\ff9\ff9.cs").read_text(encoding="utf-8", errors="replace")
m = re.search(r"w_cameraArea2Place\s*=\s*new Byte\[\]\s*\{([^}]*)\}", src)
place_lut = np.array([int(v) for v in re.findall(r"\d+", m.group(1))])
assert place_lut.size == 64, place_lut.size
print("place LUT len", place_lut.size)
for p in (0, 1, 2):
    a = np.nonzero(place_lut == p)[0]
    # compress to ranges
    rngs, s = [], a[0]
    for i in range(1, len(a) + 1):
        if i == len(a) or a[i] != a[i - 1] + 1:
            rngs.append(f"{s}-{a[i-1]}" if a[i - 1] != s else f"{s}")
            if i < len(a):
                s = a[i]
    print(f"  place {p}: areas {rngs}")

z = np.load(HERE / "out" / "stock_atlas.npz")
walk_ok = np.array(sorted(P.WALK_OK))


def seams(plg, walk, diag=False, reach2=False):
    tot = 0
    offs = [(1, 0), (0, 1)]
    if diag:
        offs += [(1, 1), (1, -1)]
    if reach2:
        offs += [(2, 0), (0, 2)]
    for dx, dz in offs:
        nb = np.roll(np.roll(plg, -dx, axis=0), -dz, axis=1)
        nw = np.roll(np.roll(walk, -dx, axis=0), -dz, axis=1)
        tot += int(((plg >= 0) & (nb >= 0) & (plg != nb) & walk & nw).sum())
    return tot


for d in (1, 4):
    area, topo, land = z[f"area_d{d}"], z[f"topo_d{d}"], z[f"land_d{d}"]
    plg = np.where(area >= 0, place_lut[np.clip(area, 0, 63)], -1)
    wl = land & (area >= 0) & np.isin(topo, walk_ok)
    wb = (area >= 0) & np.isin(topo, walk_ok)
    wa = land & (area >= 0)
    print(f"DISC {d}: L={seams(plg, wl)}  B={seams(plg, wb)}  A(land any topo)={seams(plg, wa)}  "
          f"D(B,diag+reach2)={seams(plg, wb, True, True)}")
    # where are the A seams (land-land, any topo) -- cliffs between continents?
    if seams(plg, wa):
        offs = [(1, 0), (0, 1)]
        ex = []
        for dx, dz in offs:
            nb = np.roll(np.roll(plg, -dx, axis=0), -dz, axis=1)
            nw = np.roll(np.roll(wa, -dx, axis=0), -dz, axis=1)
            mm = (plg >= 0) & (nb >= 0) & (plg != nb) & wa & nw
            cc, rr = np.nonzero(mm)
            for c, r in zip(cc, rr):
                ex.append((c // 64, r // 64))
        from collections import Counter
        print("   A-seam blocks:", Counter(ex).most_common(8))
    # can-fail control: stamp a place-1 patch into the largest place-0 walkable run
    cand = np.argwhere(wl & (plg == 0))
    ok = False
    for (c, r) in cand[:: max(1, len(cand) // 2000)]:
        sub = wl[c:c + 20, r:r + 20]
        if sub.shape == (20, 20) and sub.all():
            plg2 = plg.copy()
            plg2[c + 5:c + 15, r + 5:r + 15] = 1
            n = seams(plg2, wl)
            print(f"   control: synthetic place-1 10x10 stamp at sample ({c},{r}) -> L seams {n} (must be > 0)")
            ok = n > 0
            break
    assert ok, "control failed to fire"

# GA5: disc-4 relabel vs geometry change
a1, a4 = z["area_d1"], z["area_d4"]
l1, l4 = z["land_d1"], z["land_d4"]
both = l1 & l4 & (a1 >= 0) & (a4 >= 0)
diff = both & (a1 != a4)
print(f"\nGA5 disc1 vs disc4: samples land on both discs={int(both.sum())}, area differs on {int(diff.sum())}")
from collections import Counter
pairs = Counter(zip(a1[diff].tolist(), a4[diff].tolist()))
print("  top (area d1 -> area d4) relabels:", pairs.most_common(10))
only1 = l1 & ~l4
only4 = l4 & ~l1
print(f"  land only on d1: {int(only1.sum())} (of which area0: {int((only1 & (a1 == 0)).sum())}); "
      f"land only on d4: {int(only4.sum())}")
pl1 = np.where(a1 >= 0, place_lut[np.clip(a1, 0, 63)], -1)
pl4 = np.where(a4 >= 0, place_lut[np.clip(a4, 0, 63)], -1)
print("  relabels that change camera place:", int((diff & (pl1 != pl4)).sum()))
