"""R3 -- probe the DEPLOYED Lamplight mint (r44, seed 44, lobes 1 at (1432,-1176)).

Read-only. Verifies, on BOTH discs, from the deployed bytes (never the build output):
  (a) all 6 expected block Terrain overrides + Donor.txt sidecars exist;
  (b) the island centre grounds on walkable Terrain topo 0 at the plateau y (3.2);
  (c) the planned R3 entrance triple -- trigger (1424,-1168), beacon anchor (1424,-1160.2),
      arrive (1436,-1168) -- all ground on walkable topo-0 Terrain at the plateau y,
      in both query modes (walk and sky-cast/IgnoreExceptions), with no event bits yet;
  (d) a 16-point interior ring (r=20u) around the centre is uniformly walkable;
  (e) Disc1/Disc4 parity byte-for-byte on every minted file.

Frame + query primitives are copied from probe_marker/probe_quay_sites.py (the in-game-proven
instrument), never re-derived. Exits non-zero on any failure.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import extract as W   # noqa: E402
from ff9mapkit.world import mesh as M      # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"

CX, CZ = 1432.0, -1176.0
PLATEAU_Y = 3.2
BLOCKS = [(21, 17), (21, 18), (22, 17), (22, 18), (22, 19), (23, 18)]
TRIGGER = (1424.0, -1168.0)
ANCHOR = (1424.0, -1160.2)
ARRIVE = (1436.0, -1168.0)
IDALL_SKIP = {4078, 4088, 2040}
WALKABLE_TOPO = {0, 10, 13, 17, 36, 37}

FAILURES: list[str] = []


def check(ok, label, detail=""):
    if not ok:
        FAILURES.append(label)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")


def idall_of(bm, t):
    return int(round(bm.tangents[bm.tris[t][0]][0]))


def mk_tri_pts(ox, oz):
    def f(bm, t):
        return [(bm.verts[k][0] + ox, bm.verts[k][1], bm.verts[k][2] + oz) for k in bm.tris[t]]
    return f


def ny_of(pts):
    a, b, c = pts
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return ny / (math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0)


def hit(tri_pts, bm, t, wx, wz):
    a, b, c = tri_pts(bm, t)
    d = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
    if abs(d) < 1e-12:
        return None
    w1 = ((wx - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (wz - a[2])) / d
    w2 = ((b[0] - a[0]) * (wz - a[2]) - (wx - a[0]) * (b[2] - a[2])) / d
    if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
        return None
    return a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])


def ground(tri_pts, parts, wx, wz, *, ignore=False):
    """Object registers BEFORE Terrain, first tri in buffer order, up-facing winding."""
    for (nm, bm) in parts:
        for t in range(len(bm.tris)):
            i = idall_of(bm, t)
            if not ignore and i in IDALL_SKIP:
                continue
            if not ignore and ny_of(tri_pts(bm, t)) <= 0.1:
                continue
            y = hit(tri_pts, bm, t, wx, wz)
            if y is not None:
                return (nm, y, i, t)
    return None


def load_parts(disc, bx, by):
    """The block's deployed parts, Object first (registration order)."""
    d = MOD / f"Disc{disc}" / "0_1" / f"r{by}"
    parts = []
    for part in ("Object", "Terrain"):
        p = d / f"Block[{bx}][{by}] {part}.ff9mesh"
        if p.is_file():
            parts.append((part, M.blockmesh_from_ff9mesh(str(p), disc=disc, x=bx, y=by,
                                                         part=part.lower())))
    return parts


def query(disc, wx, wz, *, ignore=False):
    bx, by = math.floor(wx / 64), math.floor(-wz / 64)
    ox, oz = W.block_world_origin(bx, by)
    return ground(mk_tri_pts(ox, oz), load_parts(disc, bx, by), wx, wz, ignore=ignore)


def main() -> int:
    print("== R3 LAMPLIGHT MINT PROBE ==")
    for disc in (1, 4):
        print(f"-- Disc{disc}")
        for (bx, by) in BLOCKS:
            d = MOD / f"Disc{disc}" / "0_1" / f"r{by}"
            terr = d / f"Block[{bx}][{by}] Terrain.ff9mesh"
            donor = d / f"Block[{bx}][{by}] Donor.txt"
            check(terr.is_file(), f"D{disc} ({bx},{by}) Terrain override exists")
            check(donor.is_file(), f"D{disc} ({bx},{by}) Donor.txt exists",
                  donor.read_text().strip() if donor.is_file() else "")

        g = query(disc, CX, CZ)
        dec = W.decode_id(g[2]) if g else None
        check(g is not None and g[0] == "Terrain" and abs(g[1] - PLATEAU_Y) < 0.05
              and dec["topograph"] in WALKABLE_TOPO,
              f"D{disc} centre ({CX:.0f},{CZ:.0f}) walkable Terrain at plateau y", str(g))

        for label, (wx, wz) in (("trigger", TRIGGER), ("anchor", ANCHOR), ("arrive", ARRIVE)):
            for ig in (False, True):
                g = query(disc, wx, wz, ignore=ig)
                mode = "sky" if ig else "walk"
                check(g is not None and g[0] == "Terrain" and abs(g[1] - PLATEAU_Y) < 0.05,
                      f"D{disc} {label} ({wx:.0f},{wz:.0f}) [{mode}] grounds on Terrain at plateau y",
                      str(g))
                if g is not None and not ig:
                    d2 = W.decode_id(g[2])
                    check(d2["event"] == 0 and d2["area"] == 0 and d2["topograph"] == 0,
                          f"D{disc} {label} idall clean (no event/area bits, topo 0)", str(d2))

        ring_bad = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            wx, wz = CX + 20 * math.cos(a), CZ + 20 * math.sin(a)
            g = query(disc, wx, wz)
            if (g is None or g[0] != "Terrain"
                    or W.decode_id(g[2])["topograph"] not in WALKABLE_TOPO):
                ring_bad.append((round(wx, 1), round(wz, 1), g))
        check(not ring_bad, f"D{disc} 16-point r=20u interior ring uniformly walkable",
              str(ring_bad[:3]))

    mism = []
    for (bx, by) in BLOCKS:
        d1 = MOD / "Disc1" / "0_1" / f"r{by}"
        d4 = MOD / "Disc4" / "0_1" / f"r{by}"
        for f1 in sorted(d1.glob(f"Block[[]{bx}[]][[]{by}[]]*")):
            f4 = d4 / f1.name
            if not f4.is_file() or f1.read_bytes() != f4.read_bytes():
                mism.append(f1.name)
    check(not mism, "Disc1/Disc4 byte parity on every minted file", str(mism[:4]))

    print()
    if FAILURES:
        print(f"FAILURES: {len(FAILURES)}")
        for f in FAILURES:
            print("  !!", f)
        return 1
    print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
