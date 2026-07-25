"""ANGLE A design probe -- DOCK-SITE scan on the ACCEPTED (immovable) islands.

Read-only. For each accepted cluster, sky-casts the engine ground query
(world.placement.place, byte-exact simulator) over the deployed blocks and reports
LANDABLE APRON candidates: a land sample with a walkable 8u pad around it, low local
relief, and open water within ~16u on the ring-facing side -- i.e. where a dock
entrance trigger + its `arrive` apron can lawfully sit.

Prints the best few per island; writes out/world-design/design_dock_scan.json.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg
from ff9mapkit.world import mesh as M
from ff9mapkit.world import placement as P

BLOCK = 64.0
GP = Path(_cfg.find_game_path(None))
MODW = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
OUT = Path(__file__).resolve().parent / "out" / "world-design"

# registration order (placement.py rule 3)
PARTS = ["Object", "Terrain", "Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls",
         "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"]
LAND_MESH = {"Object", "Terrain", "Beach1", "Beach2"}

ISLANDS = {
    "Ashvale (junction, accepted)": [(bx, by) for bx in range(0, 5) for by in range(16, 20)],
    "Tidefall (first-continent remnant)": [(6, 18), (6, 19), (7, 18), (7, 19), (8, 19)],
    "Sandreach (desert-fidelity isle)": [(11, 18), (11, 19), (12, 18), (12, 19)],
    "Grimhorn (horseshoe/crag bench)": [(bx, by) for bx in range(18, 21) for by in range(17, 20)],
    "Larkspur (relief-demo isle)": [(9, 9), (10, 8), (10, 9), (10, 10), (11, 8), (11, 9)],
}


def load_world_meshlist(blocks):
    """One world-frame meshlist: every part of every block, in registration order,
    verts translated into world coordinates."""
    out = []
    for part in PARTS:
        for (bx, by) in blocks:
            p = MODW / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"
            if not p.exists():
                continue
            bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, lod="0_1",
                                          part=part.lower())
            for k in range(bm.vcount):
                v = bm.verts[k]
                bm.verts[k] = (v[0] + BLOCK * bx, v[1], v[2] - BLOCK * by)
            out.append((part, bm))
    return out


def scan(name, blocks):
    ml = load_world_meshlist(blocks)
    xs = [bx for bx, _ in blocks]
    zs = [by for _, by in blocks]
    x0, x1 = BLOCK * min(xs), BLOCK * (max(xs) + 1)
    z1, z0 = -BLOCK * min(zs), -BLOCK * (max(zs) + 1)
    STEP = 4.0
    grid = {}
    x = x0
    while x <= x1:
        z = z0
        while z <= z1:
            gy, mesh, idall, topo = P.place(ml, x, z, 0.0, sky=True)
            grid[(round(x), round(z))] = (gy, mesh, topo)
            z += STEP
        x += STEP
    land = {k: v for k, v in grid.items() if v[1] in LAND_MESH and v[0] > 0.25}
    water = {k for k, v in grid.items() if k not in land}
    miss = [k for k, v in grid.items() if v[1] == "MISS"]

    cands = []
    for (px, pz), (gy, mesh, topo) in land.items():
        pad = [(px + dx, pz + dz) for dx in (-8, -4, 0, 4, 8) for dz in (-8, -4, 0, 4, 8)]
        padvals = [land.get((round(a), round(b))) for a, b in pad]
        if any(v is None for v in padvals):
            continue                                   # pad not fully land -> not an 8u apron
        ys = [v[0] for v in padvals]
        relief = max(ys) - min(ys)
        if relief > 2.0:
            continue                                   # want a flat apron
        # nearest open water
        best = 1e9
        for r in range(4, 40, 4):
            ring = [(px + r * math.cos(a * math.pi / 8), pz + r * math.sin(a * math.pi / 8))
                    for a in range(16)]
            if any((round(a / 4) * 4, round(b / 4) * 4) in water for a, b in ring):
                best = r
                break
        if best > 24:
            continue
        cands.append((round(relief, 2), best, px, pz, round(gy, 2), topo, mesh))
    # rank: closest to water, then flattest
    cands.sort(key=lambda c: (c[1], c[0]))
    return dict(n_land=len(land), n_water=len(water), n_miss=len(miss),
                candidates=[dict(x=c[2], z=c[3], y=c[4], water_dist=c[1], relief=c[0],
                                 topo=c[5], mesh=c[6]) for c in cands[:400]])


report = {}
for name, blocks in ISLANDS.items():
    r = scan(name, blocks)
    report[name] = r
    print(f"\n=== {name}: land={r['n_land']} water={r['n_water']} miss={r['n_miss']} "
          f"apron-candidates={len(r['candidates'])}")
    seen = []
    for c in r["candidates"]:
        if all(math.hypot(c["x"] - s["x"], c["z"] - s["z"]) > 40 for s in seen):
            seen.append(c)
            print(f"   apron ({c['x']:.0f},{c['z']:.0f}) y={c['y']:.2f} topo={c['topo']} "
                  f"mesh={c['mesh']} water@{c['water_dist']}u relief={c['relief']}")
        if len(seen) >= 6:
            break

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "design_dock_scan.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
print("\nwrote", OUT / "design_dock_scan.json")
