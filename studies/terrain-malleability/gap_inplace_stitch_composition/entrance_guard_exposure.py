"""EXPOSURE of the entrance guard (terrain study defect 6, 2026-10-08): how often does a random land edit refuse?

Two rules, judged on stock disc-1 Terrain for smooth radial edits at every land point of an 8u lattice:
  BLOCK  world-deploy's old rule: refuse when any block the edit changes carries walk-on entrance tiles;
  KIT    ``mesh.entrance_guard`` now: refuse when the edit RAISES a vertex by more than ``ENTRANCE_RISE`` (1.17u)
         within ``ENTRANCE_CLEARANCE`` (8u) of an entrance-tile vertex or a stock door arrival
         (``entrance.door_arrivals``), or drops a tile (a deform never does). A tile lowered or raised less still
         fires and still lands the player: reported, not refused. Lowering near an entrance passes (the player
         drops). TILE = how often the edit moves a tile at all (the stricter rule the kit first tried).
"Moves" = every Terrain vertex strictly inside the radius, at amount x the smooth falloff (the stitch pins hold some
of them, which this ignores -- an upper bound for both rules).
Writes out/entrance_guard_exposure.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/entrance_guard_exposure.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
from ff9mapkit.world import entrance as EN             # noqa: E402
from ff9mapkit.world import extract as X               # noqa: E402
from ff9mapkit.world import mesh as M                  # noqa: E402

RADII = (8, 16, 24, 48, 96)
AMOUNTS = (1.0, 3.0, 6.0, -3.0)
STEP = 8.0


def main():
    C, RISE = M.ENTRANCE_CLEARANCE, M.ENTRANCE_RISE
    verts, vblock, tile_v, ent_blocks = [], [], set(), set()
    for (bx, by, *_r) in X.list_blocks(disc=1, game=S.GAME):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain", game=S.GAME)
        except (ValueError, FileNotFoundError):
            continue
        pos = M.world_positions(bm, X.block_world_origin(bx, by))
        for i, ps, _q in M.bm_tiles(bm, pos):
            if i not in M.WALK_SKIP_IDS and X.decode_id(i)["event"]:
                tile_v.update((round(p[0], 3), round(p[2], 3)) for p in ps)
                ent_blocks.add((bx, by))
        for p in {(round(p[0], 3), round(p[2], 3)) for p in pos}:
            verts.append(p)
            vblock.append((bx, by))
    arrivals = list(EN.door_arrivals(S.GAME))
    g = {}
    for (x, z) in list(tile_v) + arrivals:
        g.setdefault((math.floor(x / C), math.floor(z / C)), []).append((x, z))

    def _danger(x, z):
        gx, gz = math.floor(x / C), math.floor(z / C)
        return any(math.hypot(x - a, z - b) <= C for dx in (-1, 0, 1) for dz in (-1, 0, 1)
                   for (a, b) in g.get((gx + dx, gz + dz), ()))
    dv = [_danger(x, z) for (x, z) in verts]
    tv = [p in tile_v for p in verts]
    R = 16.0
    vg = {}
    for k, (x, z) in enumerate(verts):
        vg.setdefault((math.floor(x / R), math.floor(z / R)), []).append(k)
    land = sorted({(math.floor(x / STEP) * STEP + STEP / 2, math.floor(z / STEP) * STEP + STEP / 2) for (x, z) in verts})
    res = {"clearance": C, "rise": RISE, "door_arrivals": len(arrivals), "entrance_blocks": len(ent_blocks),
           "centres": len(land), "block_rule": {}, "tile_rule": {}, "kit_rule": {}}
    for r in RADII:
        span = int(math.ceil(r / R))
        n_block, n_tile, n_kit = 0, 0, {a: 0 for a in AMOUNTS}
        for (cx, cz) in land:
            gx, gz = math.floor(cx / R), math.floor(cz / R)
            inside = []
            for dx in range(-span, span + 1):
                for dz in range(-span, span + 1):
                    for k in vg.get((gx + dx, gz + dz), ()):
                        d = math.hypot(verts[k][0] - cx, verts[k][1] - cz)
                        if d < r:
                            inside.append((k, M._falloff(d / r)))
            if any(vblock[k] in ent_blocks for k, _w in inside):
                n_block += 1
            if any(tv[k] for k, w in inside if w > 0):
                n_tile += 1
            for a in AMOUNTS:
                if a > 0 and any(dv[k] and a * w > RISE for k, w in inside):
                    n_kit[a] += 1
        res["block_rule"][r] = round(n_block / len(land), 4)
        res["tile_rule"][r] = round(n_tile / len(land), 4)
        res["kit_rule"][r] = {f"{a:+g}": round(n / len(land), 4) for a, n in n_kit.items()}
        print(f"r{r}: block rule {100 * n_block / len(land):.1f}% | moves a tile {100 * n_tile / len(land):.1f}% | "
              f"kit rule " + ", ".join(f"{a:+g}: {100 * n / len(land):.1f}%" for a, n in n_kit.items()), flush=True)
    p = S.OUT / "entrance_guard_exposure.json"
    p.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("->", p)


if __name__ == "__main__":
    main()
