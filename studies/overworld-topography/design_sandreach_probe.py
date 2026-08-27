"""ANGLE A probe: why the desert-fidelity isle yielded zero dock aprons.

Follow-up diagnostic on `design_dock_scan.py`, which reported Sandreach (blocks
(11,18),(11,19),(12,18),(12,19)) as **116 land samples, 0 miss, ZERO dock
candidates** while every other accepted island produced some. This samples the
same blocks at 4u and asks for full 8u pads directly.

★ ANSWERED (re-run 2026-08-27, reproducing the 2026-07-25 numbers exactly:
land 116 / miss 0). **Sandreach is not dockable, and the dock scan's zero was
correct rather than a bug.** Measured:

    land topo   {17: 88, 58: 17, 34: 7, 32: 4}
    y range     0.25 .. 6.49   over a land bbox of only 124u x 56u
    full 8u pads    2   (relief 4.99 and 5.45)

So the isle is a steep little crag, not a landable shore. Three independent
reasons a dock apron cannot sit here:

  * **topo 17 dominates (88/116)** = highland. THE BAKED-TERRAIN LAW: topo
    17/38/49 highland is a hand-painted MURAL with no tile language, and THE
    BAKED-TERRAIN REFUSAL means structural morphs refuse it (bow-only) -- so a
    dock apron cannot be morphed in either.
  * **topo 58 is 17/116** = the cliff lip, which THE ENGINE FOOT-WALK TABLE
    lists as foot-ILLEGAL. Those samples are land the player can never stand on.
  * **only 2 full 8u pads exist**, and both carry ~5u of relief across the pad --
    far outside the dock scan's low-relief admission.

Read-only: loads meshes and runs the ground query, never writes to the install.

THE SOURCE SEAM: `--src DIR` points the loader at a snapshot directory instead
of the live install, so the answer is reproducible after the shared install
drifts (same law as the deploy-target seam in the brief -- pin the path through
a seam, never read the real file). A snapshot dir holds the files flat; the
install nests them under r<by>/.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg
from ff9mapkit.world import mesh as M
from ff9mapkit.world import placement as P

BLOCK = 64.0
OUT = Path(__file__).resolve().parent / "out" / "world-design"

# registration order (placement.py rule 3)
PARTS = ["Object", "Terrain", "Beach1", "Beach2", "Stream", "River", "RiverJoint", "Falls",
         "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"]
LAND_MESH = {"Object", "Terrain", "Beach1", "Beach2"}

BLOCKS = [(11, 18), (11, 19), (12, 18), (12, 19)]


def mesh_root(src=None):
    """(root, flat) -- a snapshot dir is flat, the live install nests under r<by>/."""
    if src is not None:
        return Path(src), True
    gp = Path(_cfg.find_game_path(None))
    return gp / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1", False


def load(blocks, src=None):
    root, flat = mesh_root(src)
    out = []
    for part in PARTS:
        for (bx, by) in blocks:
            name = f"Block[{bx}][{by}] {part}.ff9mesh"
            p = root / name if flat else root / f"r{by}" / name
            if not p.exists():
                continue
            bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, lod="0_1", part=part.lower())
            for k in range(bm.vcount):
                v = bm.verts[k]
                bm.verts[k] = (v[0] + BLOCK * bx, v[1], v[2] - BLOCK * by)
            out.append((part, bm))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=None,
                    help="snapshot dir of .ff9mesh files (default: the live install)")
    args = ap.parse_args()

    ml = load(BLOCKS, args.src)
    print("parts loaded:", [n for n, _ in ml])

    grid = {}
    x = 704.0
    while x <= 832.0:
        z = -1280.0
        while z <= -1152.0:
            gy, mesh, idall, topo = P.place(ml, x, z, 0.0, sky=True)
            grid[(x, z)] = (gy, mesh, topo)
            z += 4.0
        x += 4.0

    land = {k: v for k, v in grid.items() if v[1] in LAND_MESH and v[0] > 0.25}
    n_miss = sum(1 for v in grid.values() if v[1] == "MISS")
    mesh_hist = collections.Counter(v[1] for v in grid.values())
    topo_hist = collections.Counter(v[2] for v in land.values())
    print("samples", len(grid), "land", len(land), "miss", n_miss)
    print("mesh hist", mesh_hist)
    print("land topo hist", topo_hist)

    ys = [v[0] for v in land.values()]
    if ys:
        print("y range", round(min(ys), 2), round(max(ys), 2))
    xs = [k[0] for k in land]
    zs = [k[1] for k in land]
    bbox = None
    if xs:
        bbox = dict(x0=min(xs), x1=max(xs), z0=min(zs), z1=max(zs))
        print("land bbox x", bbox["x0"], bbox["x1"], " z", bbox["z0"], bbox["z1"])

    best = []
    for (px, pz), (gy, mesh, topo) in land.items():
        pad = [(px + dx, pz + dz) for dx in (-8, -4, 0, 4, 8) for dz in (-8, -4, 0, 4, 8)]
        vals = [land.get((a, b)) for a, b in pad]
        if any(v is None for v in vals):
            continue
        rel = max(v[0] for v in vals) - min(v[0] for v in vals)
        best.append((round(rel, 2), px, pz, round(gy, 2), topo))
    best.sort()
    print("full 8u pads:", len(best))
    for b in best[:8]:
        print("   pad", b)

    OUT.mkdir(parents=True, exist_ok=True)
    rep = dict(
        source=("snapshot:" + str(args.src)) if args.src else "live install",
        blocks=BLOCKS,
        n_samples=len(grid), n_land=len(land), n_miss=n_miss,
        mesh_hist=dict(mesh_hist), land_topo_hist={str(k): v for k, v in topo_hist.items()},
        y_min=round(min(ys), 2) if ys else None, y_max=round(max(ys), 2) if ys else None,
        land_bbox=bbox,
        full_8u_pads=[dict(relief=r, x=px, z=pz, y=gy, topo=t) for r, px, pz, gy, t in best],
        verdict="NOT DOCKABLE -- steep topo-17 highland crag with a foot-illegal topo-58 lip; "
                "only 2 full 8u pads, both ~5u relief. design_dock_scan's zero was correct.",
    )
    (OUT / "design_sandreach_probe.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("wrote", OUT / "design_sandreach_probe.json")


if __name__ == "__main__":
    main()
