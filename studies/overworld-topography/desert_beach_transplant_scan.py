"""THE DESERT-BEACH TRANSPLANT SCAN -- the island-B pattern's donor + target hunt.

The in-place path is closed (frame x relief pincer -- see desert_beach_window_scan).
The vehicle: TRANSPLANT a desert-coast donor rect into the archipelago's open ocean,
then bank_lower + virgin_mint a NEW desert beach on the copy (tweaks ride placements;
the sidecar fallback finds a beach-bearing divert prefab automatically -- the island-B
mechanism, Donor.txt=(7,17) on its beach cell).

  A. TARGETS -- probe candidate open-ocean windows for TRUE open ocean (the sea-only
     prefab trap): every cell must carry NO stock part at all.
  B. DONORS -- for each desert beach block, try small rects (1x1 .. 2x2) through
     transplant/transplant_region DRY-RUNS (shift="auto"): the land-fit gate is the
     real filter (a continent fragment's land runs off the rect; only self-contained
     land passes). The builders are the oracle.

    py studies/overworld-topography/desert_beach_transplant_scan.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import transplant as TR                # noqa: E402

OUTD = Path(__file__).with_name("out")
PARTS = ["terrain", "sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "object",
         "falls", "river", "riverjoint", "stream"]
DES_BEACH = [(13, 2), (13, 3), (14, 1), (14, 4), (15, 1), (15, 7), (16, 1), (16, 5),
             (16, 7), (17, 3), (19, 5), (20, 4), (20, 5), (20, 6), (20, 7)]
out = {}


def true_ocean(bx, by):
    for p in PARTS:
        try:
            X.read_block(bx, by, disc=1, part=p)
            return False
        except ValueError:
            continue
    return True


# ---- A. targets ---------------------------------------------------------------------------------
def rect_free(bx, by, nx, ny):
    return all(true_ocean(bx + i, by + j) for i in range(nx) for j in range(ny))


targets = {}
for (tx, ty, nx, ny) in ((10, 14, 2, 2), (9, 15, 2, 2), (9, 15, 3, 2), (10, 14, 2, 3),
                         (3, 19, 2, 1), (17, 17, 1, 2), (10, 15, 2, 2)):
    ok = rect_free(tx, ty, nx, ny)
    targets[(tx, ty, nx, ny)] = ok
    print(f"A. target ({tx},{ty}) {nx}x{ny}: {'TRUE OPEN OCEAN' if ok else 'blocked'}")
out["targets"] = {f"{k[0]},{k[1]} {k[2]}x{k[3]}": v for k, v in targets.items()}
t11 = next((k for k, v in targets.items() if v and (k[2], k[3]) == (2, 1)), None)
t22 = next((k for k, v in targets.items() if v and (k[2], k[3]) == (2, 2)), None)

# ---- B. donors ----------------------------------------------------------------------------------
print("\nB. donor rects (dry-run transplants; land-fit is the filter)")
hits = []
for (bx, by) in DES_BEACH:
    rects = [((bx, by), (1, 1))]
    for (dx2, dy2, nx, ny) in ((bx - 1, by, 2, 1), (bx, by, 2, 1), (bx, by - 1, 1, 2),
                               (bx, by, 1, 2), (bx - 1, by - 1, 2, 2), (bx, by, 2, 2),
                               (bx - 1, by, 2, 2), (bx, by - 1, 2, 2)):
        exists = True
        for i in range(nx):
            for j in range(ny):
                try:
                    X.read_block(dx2 + i, dy2 + j, disc=1, part="terrain")
                except ValueError:
                    exists = False
        if exists:
            rects.append(((dx2, dy2), (nx, ny)))
    seen = set()
    for (dnr, size) in rects:
        if (dnr, size) in seen:
            continue
        seen.add((dnr, size))
        nx, ny = size
        tgt = None
        if (nx, ny) == (1, 1):
            tgt = (t11[0], t11[1]) if t11 else None
        elif t22 and nx <= t22[2] and ny <= t22[3]:
            tgt = (t22[0], t22[1])
        elif t11 and (nx, ny) == (2, 1):
            tgt = (t11[0], t11[1])
        if tgt is None:
            continue
        try:
            kw = dict(cell=tgt, donor=dnr, tweaks=(), disc=1, dry_run=True)
            if (nx, ny) == (1, 1):
                s = TR.transplant("FF9CustomMap-world", **kw)
            else:
                s = TR.transplant_region("FF9CustomMap-world", size=size, **kw)
            bad = [g for g in s.get("gates", []) if not g.get("ok", True)]
            if not bad:
                print(f"   {dnr} {nx}x{ny} -> {tgt}: CLEAN")
                hits.append(dict(donor=list(dnr), size=list(size), target=list(tgt)))
            else:
                names = ",".join(g["gate"] for g in bad)
                print(f"   {dnr} {nx}x{ny}: gates fail [{names}]")
        except (ValueError, KeyError, IndexError) as ex:
            print(f"   {dnr} {nx}x{ny}: refused -- {str(ex)[:80]}")

out["donor_hits"] = hits
OUTD.mkdir(exist_ok=True)
(OUTD / "desert_beach_transplant.json").write_text(json.dumps(out, indent=1))
print(f"\n{len(hits)} clean donor rect(s) -> {OUTD / 'desert_beach_transplant.json'}")
