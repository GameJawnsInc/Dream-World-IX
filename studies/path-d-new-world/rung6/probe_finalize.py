"""RUNG 6 -- finalize the LANDING POINT + EXIT-TRIGGER CELL and emit site.json.

Read-only. Everything is measured from the DEPLOYED bytes:
  * the world .eb (EVT_WORLD_WORLD13.eb.bytes, us) -- object-0 cell tags inherited from WORLD11
  * every Disc9 Terrain override -- the tiles that actually carry event bits
  * the six V-shore bench blocks -- the walk instrument's ground query, stack census, and the
    real deflection-fan stepper for the route.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY.parent.parent / "ff9mapkit"))
import walk_sim as W                                          # noqa: E402
import probe_site as PS                                       # noqa: E402  (rung6/ is on sys.path via __main__)
from ff9mapkit.world import entrance as E                     # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import mesh as M                         # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD = "FF9CustomMap-world"
DISC9 = GAME / MOD / "FF9_Data" / "WorldMap" / "Disc9" / "0_1"
EB13 = (GAME / MOD / "StreamingAssets" / "assets" / "resources" / "commonasset"
        / "eventengine" / "eventbinary" / "world" / "us" / "EVT_WORLD_WORLD13.eb.bytes")

ALL_BLOCKS = [(0, 4), (1, 4), (2, 4), (3, 4), (0, 5), (1, 5), (2, 5), (3, 5),
              (5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8),
              (12, 9), (11, 10), (12, 10), (13, 10), (12, 11),
              (11, 12), (14, 12), (15, 12), (10, 13), (11, 13), (14, 13), (15, 13),
              (10, 14), (11, 14), (13, 15),
              (0, 16), (1, 16), (2, 16), (3, 16), (4, 16),
              (0, 17), (1, 17), (2, 17), (3, 17), (4, 17), (18, 17), (19, 17), (20, 17), (21, 17),
              (0, 18), (1, 18), (2, 18), (3, 18), (4, 18), (18, 18), (19, 18), (20, 18), (21, 18),
              (0, 19), (1, 19), (2, 19), (3, 19), (4, 19), (19, 0), (20, 0)]

BENCH = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]


# ---------------------------------------------------------------- the .eb cell tags
def eb13_cell_tags():
    from ff9mapkit.eb.model import EbScript
    s = EbScript(EB13.read_bytes())
    tags = []
    for f in s.entry(0).funcs:
        c = E.unpack_cell_tag(f.tag)
        if c is not None:
            tags.append(c)
    return sorted(tags)


# ---------------------------------------------------------------- the event-bearing tiles
def event_cells():
    """Every Disc9 Terrain tile whose IDALL carries event bits, keyed to its CELL."""
    out = Counter()
    for (bx, by) in ALL_BLOCKS:
        p = DISC9 / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if not p.is_file():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=9, x=bx, y=by, part="terrain")
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            d = X.decode_id(int(round(bm.tangents[tri[0]][0])))
            if not d["event"]:
                continue
            cx = (bm.verts[tri[0]][0] + bm.verts[tri[1]][0] + bm.verts[tri[2]][0]) / 3.0 + ox
            cz = (bm.verts[tri[0]][2] + bm.verts[tri[1]][2] + bm.verts[tri[2]][2]) / 3.0 + oz
            out[(int(cx // 32), int(-cz // 32), d["event"])] += 1
    return out


# ---------------------------------------------------------------- clean-ground components
def components(clean):
    seen, comps = set(), []
    for k in clean:
        if k in seen:
            continue
        q, comp = deque([k]), []
        seen.add(k)
        while q:
            c = q.popleft()
            comp.append(c)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    n = (c[0] + di, c[1] + dj)
                    if n in clean and n not in seen:
                        seen.add(n)
                        q.append(n)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps


def main():
    print("=== A. WORLD13 .eb object-0 cell tags (inherited from stock WORLD11) ===")
    tags = eb13_cell_tags()
    print(f"   {len(tags)} cell-tag trigger functions")
    xs = [t[0] for t in tags]; zs = [t[1] for t in tags]
    print(f"   cell_x {min(xs)}..{max(xs)}   cell_z {min(zs)}..{max(zs)}   events {sorted({t[2] for t in tags})}")

    print("\n=== B. event-bearing TILES over every deployed Disc9 Terrain override ===")
    ev = event_cells()
    for k in sorted(ev):
        print(f"   cell ({k[0]},{k[1]}) event={k[2]}  {ev[k]} tri(s)   block {E.cell_to_block(k[0], k[1])}")

    print("\n=== C. the V-shore bench island ===")
    W.CELLS = BENCH
    world = W.load_world()
    clean, ground, topo_of, stacked, (x0, z0, nx, nz) = PS.build_map(world)
    comps = components(clean)
    print(f"   clean samples {len(clean)}, stacked-walkable {len(stacked)}, "
          f"components {[len(c) for c in comps[:6]]}")
    main_comp = set(comps[0])
    dist = PS.margins(clean, nx, nz)
    rel = PS.relief(clean, ground)

    def at(x, z):
        return (int(round((x - x0) / PS.GRID)), int(round((z - z0) / PS.GRID)))

    # ---------------- candidate pairs -------------------------------------------
    LAND = (420.0, -475.0)
    cands = []
    for (cx, cz) in [(cx, cz) for cx in range(10, 16) for cz in range(14, 18)]:
        cwx, cwz = E.cell_world_center(cx, cz)
        k = at(cwx, cwz)
        d = math.hypot(cwx - LAND[0], cwz - LAND[1])
        incomp = k in main_comp
        cell_clean = sum(1 for kk in clean
                         if x0 + kk[0] * PS.GRID // 1 >= 0
                         and int((x0 + kk[0] * PS.GRID) // 32) == cx
                         and int(-(z0 + kk[1] * PS.GRID) // 32) == cz)
        cands.append(dict(cell=(cx, cz), centre=(cwx, cwz), dist=round(d, 1),
                          centre_clean=incomp, clean=cell_clean,
                          centre_y=round(ground.get(k, float('nan')), 3) if k in ground else None,
                          centre_topo=topo_of.get(k),
                          centre_margin=dist.get(k, 0)))
    print(f"\n   candidate trigger cells (distance from landing {LAND}):")
    for c in sorted(cands, key=lambda c: -c["clean"]):
        if c["clean"] < 40:
            continue
        print(f"      cell {c['cell']} centre {c['centre']}  d={c['dist']:6.1f}u  "
              f"clean={c['clean']:4d}  centre-on-main-lawn={c['centre_clean']}  "
              f"centre y={c['centre_y']} topo={c['centre_topo']} margin={c['centre_margin']}u")
    return world, clean, ground, topo_of, dist, rel, main_comp, (x0, z0), tags, ev, cands


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
