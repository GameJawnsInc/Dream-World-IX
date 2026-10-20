"""R1, reframed: cluster C's river as an ENSEMBLE (its water parts + the topo-62 banks welded to them), lifted out the
way a canopy blob is -- and every edge of its boundary classified by what it welds to at home.

Why reframed: cluster C sits on a 97-block landmass (the east Mist Continent, blocks x 11-22, y 8-18). Every region
rect round it crosses land on 66-79% of its perimeter (370u of coast to mint for the tightest 2x2), and THE FUSE LAW
forbids authored land closure (the ladder mint is falsified). So the lawful unit is the river's own ensemble.
The unit: every Stream / RiverJoint part of (16,14), (16,15), (17,14) plus the Terrain tris of topograph 62 that are
welded (share a vertex, transitively through other bank tris) to them.
Boundary classes, by the stock tri across each once-edge of the unit:
  LAWN  grass / forest / other walkable ground -> the canopy-carry zip (proven machinery)
  SEA   a sea or beach part                   -> the MOUTH: a coast splice (new)
  ROCK  topo 49 / 7 / 58                      -> a massif foot contact (the source, if the river rises there)
  OPEN  nothing across (a block-frame edge or a true hole)
RUN:  py studies/terrain-malleability/watercarry/ensemble.py   (writes out/ensemble.json)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world.interior import kk3  # noqa: E402

UNIT_BLOCKS = [(16, 14), (16, 15), (17, 14)]
NEIGH = [(bx, by) for bx in range(15, 19) for by in range(13, 17)]
WATER = ("stream", "riverjoint", "river", "falls")
SEA = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1")
ROCKY = {49, 7, 58}


def tris(bx, by, part):
    try:
        bm = X.read_block(bx, by, disc=1, part=part)
    except Exception:                                                           # noqa: BLE001
        return []
    V = np.asarray(bm.verts, dtype=float) + np.array([64.0 * bx, 0.0, -64.0 * by])
    tan = bm.chan_arrays[X.CH_TAN]
    out = []
    for t in bm.tris:
        idall = int(round(tan[t[0]][0]))
        out.append({"blk": (bx, by), "part": part, "P": V[t], "idall": idall,
                    "topo": X.decode_id(idall)["topograph"]})
    return out


def edges(T):
    return [tuple(sorted((kk3(T["P"][a]), kk3(T["P"][b])))) for a, b in ((0, 1), (1, 2), (2, 0))]


def main():
    bp = X.block_parts(disc=1)
    allt = []
    for b in NEIGH:
        for part in ("terrain",) + WATER + SEA + ("object",):
            if part in bp.get(b, ()):
                allt += tris(*b, part)
    water = [t for t in allt if t["part"] in WATER and t["blk"] in UNIT_BLOCKS]
    # the banks AND the Terrain's own water tris (the channel markers; one plugs the source end), welded to the parts
    banks = [t for t in allt if t["part"] == "terrain" and t["topo"] in (62, 48, 50, 51) and t["blk"] in UNIT_BLOCKS]
    # ... and the river's crossing: Object tris welded to it (the 40-tri bridge at (16,14); never the separate structure)
    banks += [t for t in allt if t["part"] == "object" and t["blk"] in UNIT_BLOCKS]
    # grow the bank set: bank tris that share a vertex with the unit, transitively
    keys = {kk3(p) for t in water for p in t["P"]}
    unit_banks, changed = [], True
    left = {id(t): t for t in banks}
    while changed:
        changed = False
        for k, t in list(left.items()):
            if any(kk3(p) in keys for p in t["P"]):
                unit_banks.append(t)
                del left[k]
                keys |= {kk3(p) for p in t["P"]}
                changed = True
    unit = water + unit_banks
    uid = {id(t) for t in unit}
    e_count = Counter(e for t in unit for e in edges(t))
    once = {e for e, n in e_count.items() if n == 1}
    across = defaultdict(list)                       # once-edge -> stock tris outside the unit sharing it
    for t in allt:
        if id(t) in uid:
            continue
        for e in edges(t):
            if e in once:
                across[e].append(t)
    cls_len, cls_samples = Counter(), defaultdict(list)
    for e in once:
        L = math.dist(e[0], e[1])
        nb = across.get(e, [])
        if not nb:
            c = "OPEN"
        elif any(t["part"] in SEA for t in nb):
            c = "SEA"
        elif any(t["part"] == "terrain" and t["topo"] in ROCKY for t in nb):
            c = "ROCK"
        else:
            c = "LAWN"
        cls_len[c] += L
        cls_samples[c].append(((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2))
    lawn_topos = Counter(t["topo"] for e in once for t in across.get(e, ()) if t["part"] == "terrain"
                         and t["topo"] not in ROCKY)
    rep = {"water_tris": len(water), "bank_tris": len(unit_banks), "bank_tris_left_out": len(left),
           "boundary_len": {k: round(v, 1) for k, v in cls_len.items()},
           "lawn_topos": dict(lawn_topos.most_common(6)),
           "where": {k: [round(float(np.mean([s[0] for s in v])), 1), round(float(np.mean([s[1] for s in v])), 1),
                         round(float(min(s[0] for s in v)), 1), round(float(max(s[0] for s in v)), 1),
                         round(float(min(s[1] for s in v)), 1), round(float(max(s[1] for s in v)), 1)]
                     for k, v in cls_samples.items()},
           "skipped_banks": sum(1 for t in unit_banks if t["idall"] in (4088, 2040, 4078))}
    print(json.dumps(rep, indent=1))
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "ensemble.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
