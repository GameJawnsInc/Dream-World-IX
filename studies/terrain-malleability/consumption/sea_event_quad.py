"""THE OPEN-OCEAN EVENT QUAD -- every IsSea cell renders + walks SeaBlockPrefab's sea4f, whose one 4x4 quad at
local x[60,64] z[-48,-44] carries IDALL 16612 = event 1 / area 0 / topograph 57 (sea4f_vs_sea4.py). An event-bit
tile fires ff9.WorldEvent(cell x, cell z, 1) when the controlled actor's hit tri carries event != 0
(ff9.cs:5345-5352, STOCK), keyed on the walked CELL (w_worldPos2Cell: x/32, z/-32). So each IsSea block arms one
event-1 key at cell (2bx+1, 2by+1) -- it fires a script only if the world dispatcher has an object-0 trigger tag
for that cell+event.

This script asks: which IsSea blocks' event cells collide with a REAL trigger tag in the disc-1 dispatcher
(EVT_WORLD_WORLD00, decoded by ff9mapkit.world.locate.case_to_cells -- read-only on the install)?
Also: how many stock tris carry event bits outside water (context for the bit's normal use).

Calibration: the event-cell formula is checked on the measured quad itself (sea4f_vs_sea4.json extra tris at
block (12,0) must map to cell (25,1)), and case_to_cells must return a non-empty trigger set containing a known
multi-cell entrance (any case with >= 4 cells, e.g. Lindblum's Hunter's Gate per locate.py's docstring).
Rerun:  py studies/terrain-malleability/consumption/sea_event_quad.py   -> out/sea_event_quad.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import locate as LOC             # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def cell_of(wx, wz):
    return int(wx / 32.0), int(wz / -32.0)


def main():
    C = json.loads((OUT / "consumption_census.json").read_text(encoding="utf-8"))
    Q = json.loads((OUT / "sea4f_vs_sea4.json").read_text(encoding="utf-8"))
    ex = Q["sea4f_extra_tris"][0]
    # calibration 1: the measured quad at block (12,0) -> its cell (use the quad's interior point)
    qx = 12 * 64 + (ex["plan_x"][0] + ex["plan_x"][1]) / 2
    qz = -0 * 64 + (ex["plan_z"][0] + ex["plan_z"][1]) / 2
    c12 = cell_of(qx, qz)
    ok1 = c12 == (25, 1) and ex["idall"] == 16612
    print(f"CALIB quad at (12,0) -> cell {c12}, idall {ex['idall']} (event {(ex['idall'] >> 14) & 3}, "
          f"area {(ex['idall'] >> 8) & 63}, topo {(ex['idall'] >> 2) & 63}): {'OK' if ok1 else 'FAIL'}")
    trig = LOC.case_to_cells()
    ncells = sum(len(v) for v in trig.values())
    multi = [c for c, v in trig.items() if c is not None and len(v) >= 4]
    ok2 = ncells > 0 and bool(multi)
    print(f"CALIB dispatcher triggers: {ncells} cell tags over {len(trig)} cases; multi-cell cases {multi[:6]}: "
          f"{'OK' if ok2 else 'FAIL'}")
    tagset = {}
    for case, cells in trig.items():
        for (cx, cz, ev) in cells:
            tagset[(cx, cz, ev)] = case
    sea = [tuple(map(int, k.split(","))) for k, v in C["worlddisc"].items() if v["IsSea"]]
    armed = []
    for (bx, by) in sea:
        cx, cz = cell_of(bx * 64 + 62.0, -(by * 64) - 46.0)
        hit = tagset.get((cx, cz, 1))
        if hit is not None or (cx, cz, 1) in tagset:
            armed.append({"block": (bx, by), "cell": (cx, cz), "case": hit})
    # event bits in stock data, by part
    ev_by_part = {}
    for mk, m in C["meshes"].items():
        if "/0_1/" not in mk:
            continue
        part = mk.split("/")[3]
        for k, v in m.get("event_hist", {}).items():
            if int(k):
                ev_by_part[part] = ev_by_part.get(part, 0) + v
    # every real Sea6 tile: where is it, which event, does a trigger tag sit on its cell?
    sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
    from ff9mapkit.world import extract as X
    sea6 = []
    for mk, m in C["meshes"].items():
        if mk.endswith("/sea6") and mk.startswith("d1/0_1/"):
            bx, by = map(int, mk.split("/")[2].split(","))
            bm = X.read_block(bx, by, disc=1, part="sea6")
            xs = [v[0] for v in bm.verts]
            zs = [v[2] for v in bm.verts]
            idall = int(bm.tangents[bm.tris[0][0]][0])
            cx, cz = cell_of(bx * 64 + (min(xs) + max(xs)) / 2, -(by * 64) + (min(zs) + max(zs)) / 2)
            sea6.append({"block": (bx, by), "cell": (cx, cz), "idall": idall, "event": (idall >> 14) & 3,
                         "topo": (idall >> 2) & 63, "trigger_case": tagset.get((cx, cz, (idall >> 14) & 3), "none"),
                         "isSea_block": C["worlddisc"][f"{bx},{by}"]["IsSea"]})
    print(f"disc-1 Sea6 tiles: {sea6}")
    print(f"IsSea blocks: {len(sea)}; their event-1 quad cells that collide with a WORLD00 trigger tag: {len(armed)} {armed[:10]}")
    print(f"stock form-1 tris with event bits != 0, by part (both discs): {ev_by_part}")
    res = {"calib_ok": bool(ok1 and ok2), "isSea_blocks": len(sea), "colliding": armed, "event_tris_by_part": ev_by_part,
           "trigger_cells": ncells}
    (OUT / "sea_event_quad.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"wrote {OUT / 'sea_event_quad.json'}")
    return 0 if res["calib_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
