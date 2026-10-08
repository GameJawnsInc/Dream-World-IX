"""STOCK ENTRANCE AREA -- what area does stock give its own event (entrance) tiles? The grounding for defect 14's fix
(R2: world-entrance stamps the HOST ground's area, never area := case) and O4's stock-entrance negative control.

For every connected cluster of event tiles in the stock area atlas (out/stock_atlas.npz: the engine's first-hit
ground query at 1u, both discs), compare the cluster's area to:
  * RING   the dominant area of the walkable, non-event ground within 3u of the cluster (what the player stands on
           just before stepping onto the trigger);
  * BLOCK  the dominant area of the block's walkable, non-event, non-canopy ground (the rule the Southern Ring's
           host-area stamp used, southern-ring REVERT.md section 32);
  * CASE   the dispatch case the cluster's cell tag routes to in the stock dispatchers (Map.Byte[39]), & 0x3F --
           what world-entrance stamps by default today.

Calibration: the tag join must resolve (a cell tag with a Byte[39] case) for at least one cluster, and the RING rule
must reproduce the Ring's own live failure as a mismatch when fed the pre-fix (19,18) Cleyra tiles (area 12 inside
area-14 ground) -- checked by area_lint's C-a, not repeated here.

Rerun:  py studies/terrain-malleability/gap_area_layer/stock_entrance_area.py   -> out/stock_entrance_area.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "ff9mapkit"))
import numpy as np                                   # noqa: E402
from scipy import ndimage                            # noqa: E402
from ff9mapkit.world import entrance as EN           # noqa: E402
from ff9mapkit.world.placement import WALK_OK        # noqa: E402

CANOPY = {36, 37, 38}
RING = 3


def tag_cases():
    """{cell tag: {case}} over every stock dispatcher's object-0 cell-tag functions (US)."""
    from ff9mapkit.eb.model import EbScript
    out = defaultdict(set)
    for name, data in EN.load_world_dispatchers().items():
        s = EbScript(data)
        for f in s.entry(0).funcs:
            if EN.unpack_cell_tag(f.tag) is None:
                continue
            c = EN.byte39_value(data[f.abs_start:f.abs_end])
            out[f.tag].add(c)
    return out


def dominant(values):
    c = Counter(values.tolist())
    return (c.most_common(1)[0][0] if c else None), dict(c)


def census(z, d, tags):
    area, topo, event = z[f"area_d{d}"], z[f"topo_d{d}"], z[f"event_d{d}"]
    walk = np.isin(topo, sorted(WALK_OK))
    ev = event > 0
    lab, n = ndimage.label(ev, structure=np.ones((3, 3), bool))
    ground = walk & (event == 0)
    rows = []
    for k in range(1, n + 1):
        m = lab == k
        xs, zs = np.nonzero(m)
        cl_area, cl_hist = dominant(area[m])
        ring = ndimage.binary_dilation(m, iterations=RING) & ~m & ground
        ring_area, ring_hist = dominant(area[ring])
        bx, by = int(xs.mean() // 64), int(zs.mean() // 64)
        sl = (slice(bx * 64, bx * 64 + 64), slice(by * 64, by * 64 + 64))
        bmask = ground[sl] & ~np.isin(topo[sl], sorted(CANOPY))
        block_area, block_hist = dominant(area[sl][bmask])
        cases = set()
        for x, zz in zip(xs, zs):
            t = EN.pack_cell_tag(int(x) // 32, int(zz) // 32, int(event[x, zz]))
            cases |= {c for c in tags.get(t, ()) if c is not None}
        rows.append({"cluster": k, "samples": int(m.sum()), "block": [bx, by],
                     "cells": sorted({(int(x) // 32, int(zz) // 32) for x, zz in zip(xs, zs)}),
                     "area": cl_area, "area_hist": cl_hist, "mixed": len(cl_hist) > 1,
                     "ring_area": ring_area, "ring_hist": ring_hist, "ring_samples": int(ring.sum()),
                     "block_area": block_area, "cases": sorted(cases),
                     "eq_ring": cl_area == ring_area, "eq_block": cl_area == block_area,
                     "eq_case": bool(cases) and any((c & 0x3F) == cl_area for c in cases)})
    return rows


def summarise(rows):
    has_ring = [r for r in rows if r["ring_area"] is not None]
    has_case = [r for r in rows if r["cases"]]
    return {"clusters": len(rows), "samples": sum(r["samples"] for r in rows),
            "mixed_area_clusters": sum(r["mixed"] for r in rows),
            "with_ring": len(has_ring), "eq_ring": sum(r["eq_ring"] for r in has_ring),
            "eq_ring_samples": f'{sum(r["samples"] for r in has_ring if r["eq_ring"])}/'
                               f'{sum(r["samples"] for r in has_ring)}',
            "eq_block": sum(r["eq_block"] for r in rows),
            "with_case": len(has_case), "eq_case": sum(r["eq_case"] for r in has_case),
            "ring_mismatches": [{k: r[k] for k in ("block", "cells", "samples", "area", "area_hist", "ring_hist",
                                                   "block_area", "cases")}
                                for r in has_ring if not r["eq_ring"]]}


def main():
    z = np.load(HERE / "out" / "stock_atlas.npz")
    tags = tag_cases()
    res = {"ring_u": RING, "cell_tags_with_case": sum(1 for v in tags.values() if v - {None})}
    for d in (1, 4):
        rows = census(z, d, tags)
        res[f"disc{d}"] = {"summary": summarise(rows), "rows": rows}
        s = res[f"disc{d}"]["summary"]
        print(f"disc {d}: {s['clusters']} clusters ({s['samples']} samples), mixed-area {s['mixed_area_clusters']}; "
              f"area == RING {s['eq_ring']}/{s['with_ring']} (samples {s['eq_ring_samples']}); "
              f"== BLOCK {s['eq_block']}/{s['clusters']}; == CASE&0x3F {s['eq_case']}/{s['with_case']}")
        for r in s["ring_mismatches"]:
            print("   ring mismatch:", r)
    ok = res["cell_tags_with_case"] > 0 and any(res[f"disc{d}"]["summary"]["with_case"] for d in (1, 4))
    res["calibration_ok"] = ok
    (HERE / "out" / "stock_entrance_area.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("calibration (the tag join resolves):", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
