"""ADVERSARIAL VERIFY (GA2 / GA14): the lane counts camera-place seams only under the ON-FOOT walk mask (WALK_OK).
Chocobos use type_cam 1, for which place 1 differs from places 0/2 (w_cameraElement[1,1].down = 3 vs 1). Their
topograph limit masks (ff9.cs w_moveCHRControl[1..5].limit, decoded with w_movementCheckTopographID: check[1] bit n
for topo n<32, check[0] bit n-32 for topo>=32) admit water/mountain topographs. Does STOCK let a chocobo cross a
place-1 <-> place-0/2 boundary between two samples it may stand on?

Masks are parsed from ff9.cs source, not transcribed. Uses out/stock_atlas.npz (all parts, any sample with area>=0).

Rerun: py studies/terrain-malleability/gap_area_layer/verify_choco_seams.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
src = Path(r"C:\gd\FFIX\Memoria\Assembly-CSharp\Global\ff9\ff9.cs").read_text(encoding="utf-8", errors="replace")
m = re.search(r"w_cameraArea2Place\s*=\s*new Byte\[\]\s*\{([^}]*)\}", src)
place_lut = np.array([int(v) for v in re.findall(r"\d+", m.group(1))])
blk = src[src.index("ff9.w_moveCHRControl = new ff9.s_moveCHRControl[12]"):]
blk = blk[:blk.index("ff9.w_moveCHRControl[0].type_cam = 0;")]
ctrls = re.split(r"new ff9\.s_moveCHRControl\s*//", blk)[1:]
masks = {}
for c in ctrls:
    name = c.splitlines()[0].strip()
    lm = re.search(r"limit = new UInt32\[\]\s*\{\s*(0x[0-9A-Fa-f]+)u,\s*(0x[0-9A-Fa-f]+|0)u", c)
    if not lm:
        continue
    c0, c1 = int(lm.group(1), 16), int(lm.group(2), 0)
    ok = {n for n in range(64) if ((c1 >> n) & 1 if n < 32 else (c0 >> (n - 32)) & 1)}
    masks[name] = ok
foot = masks["0: walking by foot"]
# flg_gake=1 (controls 2-5): a step water->ground or ground->water is REFUSED (ff9.cs ~:5702-5715), with
# w_movementWaterStatus {0x23ED0000,0} and w_movementGroundStatus {0x5C126670,0x18FF3CFF}
def _dec(c0, c1):
    return {n for n in range(64) if ((c1 >> n) & 1 if n < 32 else (c0 >> (n - 32)) & 1)}
WATER_T = np.array(sorted(_dec(0x23ED0000, 0)))
GROUND_T = np.array(sorted(_dec(0x5C126670, 0x18FF3CFF)))
print("water topos", WATER_T.tolist(), " ground topos", GROUND_T.tolist())
z = np.load(HERE / "out" / "stock_atlas.npz")
for name, ok in masks.items():
    if not name[0] in "12345":
        continue
    print(f"{name}: extra topos vs foot = {sorted(ok - foot)}")
    for d in (1, 4):
        area, topo = z[f"area_d{d}"], z[f"topo_d{d}"]
        walk = (area >= 0) & np.isin(topo, sorted(ok))
        p1 = np.where(area >= 0, place_lut[np.clip(area, 0, 63)] == 1, False)   # type_cam 1: place 1 vs not
        n = 0
        ex = Counter()
        for ax in (0, 1):
            nb1 = np.roll(p1, -1, axis=ax)
            nw = np.roll(walk, -1, axis=ax)
            nbarea = np.roll(area, -1, axis=ax)
            nt = np.roll(topo, -1, axis=ax)
            gake = name[0] in "2345"
            blocked = (np.isin(topo, WATER_T) & np.isin(nt, GROUND_T)) | (np.isin(topo, GROUND_T) & np.isin(nt, WATER_T))
            mm = walk & nw & (p1 != nb1) & (area >= 0) & (nbarea >= 0)
            mm_g = mm & ~blocked if gake else mm
            n_g = int(mm_g.sum())
            print(f"      axis {ax}: raw pairs {int(mm.sum())}, after flg_gake water<->ground refusal {n_g}")
            n += int(mm.sum())
            cc, rr = np.nonzero(mm)
            for c_, r_ in zip(cc, rr):
                a1, a2 = int(area[c_, r_]), int(nbarea[c_, r_])
                t1 = int(topo[c_, r_])
                t2 = int(np.roll(topo, -1, axis=ax)[c_, r_])
                ex[(min(a1, a2), max(a1, a2), tuple(sorted((t1, t2))))] += 1
        print(f"   disc {d}: chocobo-walkable type_cam-1 place seams = {n}; top (areas, topos): {ex.most_common(5)}")
