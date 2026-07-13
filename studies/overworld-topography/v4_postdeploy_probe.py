"""V4 POST-DEPLOY PROBE -- verify the deployed bytes + mint teleport spots.

Loads the DEPLOYED .ff9mesh overrides for cells (1-3,16-17), runs the engine-true
placement sim on a grid, and reports: lowland topo-0 spots (south coast), topo-13
bowl spots (the hanging terrace), and the walkable census. All coordinates WORLD,
mid-cell (the lattice-edge teleport trap). Run from the repo root.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                       # noqa: E402
from ff9mapkit.world import mesh as M                      # noqa: E402
from ff9mapkit.world import placement as P                 # noqa: E402

GP = Path(_cfg.find_game_path(None))
MOD = GP / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
CELLS = [(1, 16), (2, 16), (3, 16), (1, 17), (2, 17), (3, 17)]

# one placement sim per block cell (the engine grounds per-block)
best = {"low": [], "bowl": []}
for (bx, by) in CELLS:
    parts = []
    for part in ("Terrain", "Sea3", "Sea5", "Sea4"):
        p = MOD / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"
        if p.exists():
            parts.append((part, M.blockmesh_from_ff9mesh(
                p, disc=1, x=bx, y=by, part=part.lower())))
    ox, oz = bx * 64.0, -by * 64.0
    n_ok = n_miss = 0
    for ix in range(2, 63, 3):
        for iz in range(2, 63, 3):
            lx, lz = ix + 0.5, -(iz + 0.5)
            gy, nm, _, topo = P.place(parts, lx, lz)
            if nm == "MISS":
                n_miss += 1
                continue
            n_ok += 1
            wx, wz = ox + lx, oz + lz
            if topo == 0 and 1.0 <= gy <= 6.0:
                best["low"].append((round(wx, 1), round(wz, 1), round(gy, 2)))
            if topo == 13 and 12.0 <= gy <= 18.0:
                best["bowl"].append((round(wx, 1), round(wz, 1), round(gy, 2)))
    print(f"cell ({bx},{by}): grounded {n_ok}, no-hit {n_miss}")

print(f"\nlowland topo-0 spots ({len(best['low'])}):", best["low"][:6])
print(f"bowl topo-13 spots ({len(best['bowl'])}):", best["bowl"][:6])
