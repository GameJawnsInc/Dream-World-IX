"""ADVERSARIAL VERIFY (GA7): can the lead_1918 "no dispatcher tag matches" verdict FAIL?

lead_1918.py reports the live (19,18) event cells 38-39 x 36-37 e1 match no object-0 cell tag of any live dispatcher.
That check has never been shown able to fire. CONTROL: the SAME 45 tris at their STOCK position (Cleyra, disc-1
blocks (13-14,11-12)) must match a stock dispatcher's object-0 cell tag -- otherwise the tag join is broken and
'inert' is unproven.

Also re-derives, independently of lead_1918.py: every stock tri (both discs, EVERY lod and part in the exact-container
index) carrying IDALL 19620, and the IDALL census of the horseshoe donor at its widest documented rect (5-7,15-16,
donor_qualify_scan.py KNOWN_DONORS) -- so the "horseshoe carries 0 tris of 19620" claim is not limited to 5-6.

Rerun: py studies/terrain-malleability/gap_area_layer/verify_1918.py
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arealib as A                                  # noqa: E402
from ff9mapkit.eb.model import EbScript              # noqa: E402
from ff9mapkit.world import entrance as EN           # noqa: E402

TID = 19620
alld = EN.load_all_dispatchers()
stock_tags = {}
for n, langs in alld.items():
    s = EbScript(langs["us"])
    for f in s.entry(0).funcs:
        c = EN.unpack_cell_tag(f.tag)
        if c is not None:
            stock_tags.setdefault(c, []).append(n)

# every stock tri with IDALL 19620, any lod/part/disc
hits = Counter()
cells = Counter()
for (d, lod, x, y, part) in sorted(A._objs()):
    V, ids = A.stock_mesh(f"d{d}/{lod}/{x},{y}/{part}")
    m = ids == TID
    if m.any():
        hits[(d, lod, x, y, part)] += int(m.sum())
        if lod == "0_1":
            cen = V[m].mean(axis=1)
            for c in cen:
                wx, wz = x * 64 + c[0], -y * 64 + c[2]
                cells[(int(wx // 32), int(wz // -32), d)] += 1
print("stock tris with IDALL 19620 (disc, lod, x, y, part): n")
for k, v in sorted(hits.items()):
    print("   ", k, v)
print("stock 19620 tri cells (cx, cz, disc):", dict(cells))
for (cx, cz, d), n in cells.items():
    print(f"   CONTROL cell ({cx},{cz}) e1 disc{d}: stock dispatcher tags -> {stock_tags.get((cx, cz, 1), 'NONE')}")
for (cx, cz) in ((38, 36), (38, 37), (39, 36), (39, 37)):
    print(f"   LIVE cell ({cx},{cz}) e1: stock dispatcher tags -> {stock_tags.get((cx, cz, 1), 'NONE')}")

# horseshoe donor widest rect
for d in (1,):
    agg = Counter()
    for (dd, lod, x, y, part) in A._objs():
        if dd != d or lod != "0_1" or not (5 <= x <= 7 and 15 <= y <= 16):
            continue
        V, ids = A.stock_mesh(f"d{dd}/{lod}/{x},{y}/{part}")
        for i in ids.tolist():
            agg[((i & 0x3F00) >> 8, (i & 0xC000) >> 14)] += 1
    print(f"horseshoe rect (5-7,15-16) disc{d} all parts: (area, event) tri counts:", sorted(agg.items()))
    print("   tris with IDALL 19620 in rect:", sum(v for k, v in hits.items() if k[0] == d and k[1] == '0_1'
                                                   and 5 <= k[2] <= 7 and 15 <= k[3] <= 16))
