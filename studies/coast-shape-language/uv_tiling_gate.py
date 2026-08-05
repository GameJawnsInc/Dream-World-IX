"""THE UV-TILING GATE -- does an authored water sheet tile the way stock's does?

The ring drop reached a playtest as a checkerboard because every gate in the stack scores
GEOMETRY (welds, holes, winding, census coverage) and not one scores TONE. The defect was
a per-TRIANGLE quadrant choice where stock chooses per 4u TILE, so a seam ran through
every tile -- geometrically perfect, visually broken.

This is the missing check, and it compares against stock rather than against a rule I
believe: it measures the same two statistics on a stock sea4 sheet and on the candidate,
and refuses if the candidate is off stock's own numbers.

  TILE COHERENCE  -- share of 4u tiles whose triangles all take one quadrant.
                     Stock: 99.3% (134 of 135 tiles over three blocks).
  QUADRANT SPREAD -- share of ADJACENT tile pairs taking different quadrants. Stock
                     varies constantly; a sheet that never varies is a flat repeat, and
                     one that varies every tile in lockstep is the checkerboard.

  py studies/coast-shape-language/uv_tiling_gate.py [--donor 6,6 --size 2x2]

Read-only. Exit 1 if the candidate is off stock.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
from ff9mapkit.world import meshedit as ME                   # noqa: E402
from ff9mapkit.world import transplant as TR                 # noqa: E402

UB, VB = 0.5039, 0.5079
TILE = 4.0
#: stock's own coherence, measured over blocks (7,6) (6,6) (9,5)
STOCK_COHERENCE = 0.993
COHERENCE_MIN = 0.95          # a sheet must be at least this tile-coherent
#: THRESHOLDS ARE RELATIVE TO STOCK, MEASURED IN THE SAME RUN -- not absolutes.
#: The first cut of this gate used a guessed band [0.35, 0.95] and PASSED a candidate at
#: 0.365 against stock's 0.880: the guessed floor let a broken sheet through by 0.015.
#: A gate calibrated on a number I invented is not a gate.
SPREAD_TOL = 0.20             # adjacent-variation must land within this of stock's
#: quadrant usage must be roughly even, as stock's is; a skewed sheet is a flat repeat
SKEW_MAX = 2.5                # max(count) / min(count) across the four quadrants
#: a 2x2 parity cell must NOT determine the quadrant (stock: it does not)
PARITY_MAX = 0.45


def quad_of(tri):
    mu = sum(v[2][0] for v in tri) / 3.0
    mv = sum(v[2][1] for v in tri) / 3.0
    return (1 if mu > UB else 0, 1 if mv > VB else 0)


def tile_of(tri):
    cx = sum(v[0][0] for v in tri) / 3.0
    cz = sum(v[0][2] for v in tri) / 3.0
    return (int(cx // TILE), int((-cz) // TILE))


def stats(tris, label):
    per = defaultdict(set)
    for t in tris:
        per[tile_of(t)].add(quad_of(t))
    if not per:
        return None
    coherent = sum(1 for qs in per.values() if len(qs) == 1)
    coherence = coherent / len(per)
    one = {c: next(iter(qs)) for c, qs in per.items() if len(qs) == 1}
    pairs = diff = 0
    for (gx, gz), q in one.items():
        for nb in ((gx + 1, gz), (gx, gz + 1)):
            if nb in one:
                pairs += 1
                diff += (one[nb] != q)
    spread = diff / pairs if pairs else 0.0
    print(f"  {label:22s} {len(per):>5} tiles  coherence {coherence:6.3f}  "
          f"adjacent-variation {spread:6.3f}  quadrants {dict(Counter(one.values()))}")
    cc = Counter(one.values())
    # How well does a small lattice cell predict the quadrant? 1.0 == a pure lattice.
    # TEST SEVERAL MODULI, not just parity: the first cut checked only (gx%2, gz%2) and
    # MISSED a mod-4 lattice -- a check too narrow to see the thing it was written for.
    pp = 0.0
    for m in (2, 3, 4):
        byp = defaultdict(Counter)
        for (gx, gz), q in one.items():
            byp[(gx % m, gz % m)][q] += 1
        if one:
            # penalise the cell count: a big modulus predicts well by memorising
            hit = sum(c.most_common(1)[0][1] for c in byp.values()) / len(one)
            base = len(byp) / len(one)          # what perfect memorisation alone buys
            pp = max(pp, hit - base)
    return dict(tiles=len(per), coherence=coherence, spread=spread, parity_predict=pp,
                quad_counts=[cc.get(q, 0) for q in
                             ((0, 0), (1, 0), (0, 1), (1, 1))])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", default="6,6")
    ap.add_argument("--size", default="2x2")
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    dx, dy = (int(v) for v in args.donor.split(","))
    nx, ny = (int(v) for v in args.size.lower().split("x"))

    print("STOCK reference sheets:")
    ref = []
    for blk in ((7, 6), (6, 6), (9, 5)):
        ref += TR.world_tris(*blk, "sea4", disc=args.disc)
    s_ref = stats(ref, "stock sea4")

    print("\nCANDIDATE -- the ring re-shaded as deep water:")
    shallow = []
    for j in range(ny):
        for i in range(nx):
            for p in ("sea1", "sea2", "sea3", "sea5"):
                shallow += TR.world_tris(dx + i, dy + j, p, disc=args.disc)
    if not shallow:
        print("  (this donor carries no shallow ring -- nothing to score)")
        return 0
    conv = ME.retag_flat(shallow, uv_quads=TR.SEA4_QUADS, idall=TR.SEA4_IDALL)
    s_cand = stats(conv, "converted ring")

    print("\nVERDICT")
    ok = True
    if s_cand["coherence"] < COHERENCE_MIN:
        print(f"  FAIL tile coherence {s_cand['coherence']:.3f} < {COHERENCE_MIN} "
              f"(stock {s_ref['coherence']:.3f}) -- triangles of a tile disagree, which "
              f"renders as a seam through every tile")
        ok = False
    else:
        print(f"  ok   tile coherence {s_cand['coherence']:.3f} "
              f"(stock {s_ref['coherence']:.3f})")
    d = abs(s_cand["spread"] - s_ref["spread"])
    if d > SPREAD_TOL:
        print(f"  FAIL adjacent-variation {s_cand['spread']:.3f} vs stock "
              f"{s_ref['spread']:.3f} (off by {d:.3f} > {SPREAD_TOL}) -- "
              f"{'a flat repeat' if s_cand['spread'] < s_ref['spread'] else 'over-varied'}")
        ok = False
    else:
        print(f"  ok   adjacent-variation {s_cand['spread']:.3f} "
              f"(stock {s_ref['spread']:.3f}, off by {d:.3f})")
    # THE REGULARITY CHECK -- the one the spread statistic cannot see. A perfectly
    # alternating lattice scores adjacent-variation 1.000, which sits WITHIN tolerance of
    # stock's 0.880 while being categorically different: regular where stock is irregular.
    # If tile PARITY predicts the quadrant, the sheet is a lattice, not a spread.
    pr = s_cand["parity_predict"]
    if pr > PARITY_MAX:
        print(f"  FAIL a small lattice predicts the quadrant {pr:.0%} of the time (> {PARITY_MAX:.0%}, "
              f"stock {s_ref['parity_predict']:.0%}) -- that is a LATTICE: the pattern "
              f"repeats on a 2x2 grid instead of spreading")
        ok = False
    else:
        print(f"  ok   lattice-predictability {pr:.0%} (stock {s_ref['parity_predict']:.0%})")
    cs = s_cand["quad_counts"]
    skew = max(cs) / max(1, min(cs))
    if skew > SKEW_MAX:
        print(f"  FAIL quadrant skew {skew:.1f}x > {SKEW_MAX}x {cs} -- stock spreads its "
              f"four quadrants evenly; a skewed sheet reads as one repeated tile")
        ok = False
    else:
        print(f"  ok   quadrant skew {skew:.1f}x {cs}")
    print("\n" + ("PASS -- the authored sheet tiles like stock's"
                  if ok else "REFUSED -- do not deploy this"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
