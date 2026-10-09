"""LAND -> SEA, the pool (2026-10-09): every disc-1 island ASSEMBLY map-wide, joined ACROSS cell borders.

The excise's unit (vertex-connected tris over terrain, beach1, sea1, sea2, sea3, sea5) traced over the whole map, so an
island whose shallow ring crosses a cell border is one assembly over all its cells (stock welds exactly at block
borders). For each: land tris, land area, cells spanned, whether every spanned cell's prefab carries sea4 (the fill's
part), Objects standing on it, entrance (event) tiles on its land. Small assemblies are the sink's candidate pool; the
continents are listed only by size. Reads stock only. Writes out/island_pool.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/island_pool.py [disc]
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))


def main():
    import ff9mapkit
    from ff9mapkit.world import extract as X, meshedit as ME, transplant as TR
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    disc = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    tagged, sea4cells, objs = [], set(), {}
    for (bx, by) in sorted(X.list_blocks(disc=disc)):
        for p in TR.PARTS:
            got = TR.world_tris(bx, by, p, disc=disc)
            if p == "sea4":
                if got:
                    sea4cells.add((bx, by))
            else:
                tagged += [(p, (bx, by), t) for t in got]
        objs[(bx, by)] = TR.world_tris(bx, by, "object", disc=disc)
    part_of = {id(t): (p, c) for p, c, t in tagged}
    comps = ME.vertex_components([t for _, _, t in tagged])
    rows = []
    for c in comps:
        land = [t for t in c if part_of[id(t)][0] in TR.LAND_PARTS]
        if not land:
            continue
        cells = sorted({part_of[id(t)][1] for t in c})
        area = sum(abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                       - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2])) / 2.0 for t in land)
        events = sum(1 for t in land if X.decode_id(int(round(t[0][3][0])))["event"])
        xs = [v[0][0] for t in land for v in t]
        zs = [v[0][2] for t in land for v in t]
        bbox = (min(xs), max(xs), min(zs), max(zs))
        on = 0
        for cc in cells:
            for t in objs.get(cc, ()):
                cx, cz = TR._plan_centroid(t)
                if bbox[0] <= cx <= bbox[1] and bbox[2] <= cz <= bbox[3] and any(TR._tri_has(l, (cx, cz))
                                                                              for l in land):
                    on += 1
        rows.append({"land_tris": len(land), "land_u2": round(area, 1), "tris": len(c), "cells": cells,
                     "no_sea4": [cc for cc in cells if cc not in sea4cells], "objects_on": on, "event_tris": events,
                     "max_y": round(max(v[0][1] for t in land for v in t), 2),
                     "at": [round(v, 3) for v in TR._plan_centroid(max(land, key=lambda t: abs(
                         (t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                         - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2]))))],
                     "parts": sorted({part_of[id(t)][0] for t in c})})
    rows.sort(key=lambda r: r["land_u2"])
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / f"island_pool_d{disc}.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    print(f"{len(rows)} land assemblies on disc {disc}")
    for r in rows:
        flag = []
        if r["no_sea4"]:
            flag.append(f"no sea4 in {r['no_sea4']}")
        if r["objects_on"]:
            flag.append(f"{r['objects_on']} object tris")
        if r["event_tris"]:
            flag.append(f"{r['event_tris']} entrance tris")
        print(f"  {r['land_u2']:9.1f}u2 land {r['land_tris']:5d} cells {len(r['cells']):3d} {r['cells'][:4]}"
              f"{'...' if len(r['cells']) > 4 else ''} parts {','.join(r['parts'])}  {'; '.join(flag)}")


if __name__ == "__main__":
    main()
