"""R4b -- verify THE SAFE-ROAD AREA STAMP (area 14) across every kit island, both discs.

Read-only. The fix for the in-game falsification of the "topo 36-38 engine law": encounters
resolve zone x topograph x fog off the WALKED TILE's area bits, and safety is a TABLE HOLE --
so every kit island's open walkable ground is stamped area 14 (zone 6, whose only records are
topos 10/36: a hole for every topograph our ground carries). Invariants:

  (a) NON-event, NON-encounter-topo tiles carry area 14 -- everywhere, both discs;
  (b) encounter-topo tiles (36/37/38 -- the canopy) keep area 0 (zone 0: Python/Goblin/Mu);
  (c) EVENT tiles are byte-identical to the pre-stamp backup (ours stay area 0; the horseshoe
      carry's stock event tiles keep whatever areas they always carried);
  (d) the stamp changed ONLY area bits (topo/event/flags identical to the backup);
  (e) Disc1/Disc4 parity.

Exits non-zero on any violation.
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import extract as W   # noqa: E402
from ff9mapkit.world import mesh as M      # noqa: E402

G = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX") \
    / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
B = Path(r"C:\gd\Dream-World-IX\backups\r3-lamplight.20260726-r3lamplight\pre-area14-terrains")
ROWS = [0, 1, 2, 3, 4, 8, 9, 10, 16, 17, 18, 19]
ENC = {36, 37, 38}
SAFE_AREA = 14


def main() -> int:
    viol = []
    ev_areas = collections.Counter()
    n_open = n_enc = n_ev = 0
    for disc in (1, 4):
        for r in ROWS:
            d = G / f"Disc{disc}" / "0_1" / f"r{r}"
            if not d.is_dir():
                continue
            for f in sorted(d.glob("Block*Terrain.ff9mesh")):
                bx = int(f.name.split("[")[1].split("]")[0])
                by = int(f.name.split("[")[2].split("]")[0])
                bm = M.blockmesh_from_ff9mesh(str(f), disc=disc, x=bx, y=by, part="terrain")
                pre_f = B / f"Disc{disc}" / f"r{by}_{f.name}"
                pre = (M.blockmesh_from_ff9mesh(str(pre_f), disc=disc, x=bx, y=by, part="terrain")
                       if pre_f.is_file() else None)
                for k in range(len(bm.tangents)):
                    idall = int(round(bm.tangents[k][0]))
                    dd = W.decode_id(idall)
                    pre_idall = int(round(pre.tangents[k][0])) if pre else None
                    if dd["event"]:
                        n_ev += 1
                        ev_areas[dd["area"]] += 1
                        if pre_idall is not None and pre_idall != idall:
                            viol.append((disc, f.name, k, "event tile changed"))
                    elif dd["topograph"] in ENC:
                        n_enc += 1
                        if dd["area"] != 0:
                            viol.append((disc, f.name, k, f"canopy area {dd['area']}"))
                    else:
                        n_open += 1
                        if dd["area"] != SAFE_AREA:
                            viol.append((disc, f.name, k, f"open ground area {dd['area']}"))
                        if pre_idall is not None:
                            pd = W.decode_id(pre_idall)
                            if (pd["topograph"], pd["event"], pd["flags"]) != \
                               (dd["topograph"], dd["event"], dd["flags"]):
                                viol.append((disc, f.name, k, "non-area bits changed"))
    print(f"open-ground verts area-{SAFE_AREA}: {n_open}  canopy verts area-0: {n_enc}  "
          f"event verts untouched: {n_ev}")
    print("event-tile areas (incl. the horseshoe carry's stock tiles):", dict(sorted(ev_areas.items())))
    mism = []
    for r in ROWS:
        d1 = G / "Disc1" / "0_1" / f"r{r}"
        if not d1.is_dir():
            continue
        for f1 in sorted(d1.glob("Block*Terrain.ff9mesh")):
            f4 = G / "Disc4" / "0_1" / f"r{r}" / f1.name
            if not f4.is_file() or f1.read_bytes() != f4.read_bytes():
                mism.append(f"r{r}/{f1.name}")
    if mism:
        viol.append(("parity", mism[:4]))
    if viol:
        print(f"VIOLATIONS ({len(viol)}):")
        for v in viol[:8]:
            print("  !!", v)
        return 1
    print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
