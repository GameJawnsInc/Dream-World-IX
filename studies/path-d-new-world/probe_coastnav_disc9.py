"""Path D -- THE DISC9 COAST-NAV PROBE: is the cliffs-refuse stamp honest, offline?

Re-points the Southern Ring's R5d gate suite (probe_r3/probe_coast_nav.py) at the Path D
synthetic namespace (Disc9), sharing the kit's OWN instruments (`coastnav._Loader` /
`_query_top` / `_cell_grounds`) so the origin convention, the IDALL skip set and the up-facing
filter cannot diverge from the stamp that wrote the classes.

Gates:
  0. CALIBRATE -- the spatial index added to `_query_top` (2026-07-30) must return byte-identical
     (part, topo, y) to the original linear scan on sampled points, full-stack AND seas-only.
     A probe with an uncalibrated accelerator cannot falsify anything.
  1. THE SEAL -- at every 4u sample over HIGH ground (y >= 1.5), the seas-only query (what the
     boat's cache-favoured `w_cellHit` reads under land) must NOT return a Narciss-legal topo
     ({53, 54, 57}); any hit must be keel (56) / belt (55) or absent.
  2. THE STANDOFF -- open water within 2u of a HIGH-locale wall front must be mask-illegal
     (seam-artifact tolerance 5%, per R5e's BEACH>BELT shared-vert priority).
  3. LANDINGS / CENSUS -- policy `cliffs-refuse`, and the Rung-5a island has no low shore, so
     landable 53 must not exist AT ALL: zero verts changed to 53 vs the backup, zero 53 live.
     Reports the changed-class census (deploy said KEEL 468 / BELT 282 / CLIFF 1128).
  4. INTEGRITY -- vs backups/coastnav-disc9-20260730-140045: diffs confined to tangent.x topo
     bits, old topo water-class, new in {53, 54, 55, 56}; no mirror disc (synthetic namespace).

The Southern Ring probe's gates 2 (seven landable shores) and 3 (the north sea lane) do NOT
carry over: under the owner's cliffs-refuse ruling the island is deliberately unlandable, and
Disc9 has no ratified voyage polyline yet -- the sail-around playtest owns that half.

Read-only. Exits nonzero on any violation.
"""
from __future__ import annotations

import math
import random
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit.world import coastnav as CN            # noqa: E402
from ff9mapkit.world import extract as W              # noqa: E402
from ff9mapkit.world.placement import IDALL_SKIP      # noqa: E402

MOD_FOLDER = "FF9CustomMap-world"
DISC = 9
LEGAL = {53, 54, 57}                                  # the Narciss mask
SEAS = tuple(CN.SEA_PARTS)
# ABSOLUTE, main repo -- the deploy run's default parked this in a worktree; consolidated
# 2026-07-30 (see stamp_coast_nav.py's BACKUP note for the same lesson on disc 1).
BACKUP = Path(r"C:\gd\Dream-World-IX\backups\coastnav-disc9-20260730-140045")


def _query_top_linear(loader, wx, wz, parts=None):
    """The ORIGINAL un-indexed scan, verbatim -- the calibration reference for gate 0."""
    wx %= CN.WORLD_W
    bx, by = math.floor(wx / CN.BLOCK), math.floor(-wz / CN.BLOCK)
    ox, oz = W.block_world_origin(bx, by)
    for nm, bm, _grid in loader.parts(bx, by):
        if parts is not None and nm not in parts:
            continue
        for t in range(len(bm.tris)):
            tri = bm.tris[t]
            if int(round(bm.tangents[tri[0]][0])) in IDALL_SKIP:
                continue
            a, b, c = [(bm.verts[k][0] + ox, bm.verts[k][1], bm.verts[k][2] + oz) for k in tri]
            d = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
            if abs(d) < 1e-12:
                continue
            w1 = ((wx - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (wz - a[2])) / d
            w2 = ((b[0] - a[0]) * (wz - a[2]) - (wx - a[0]) * (b[2] - a[2])) / d
            if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
                continue
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            ny = uz * vx - ux * vz
            if ny <= 0.0:
                continue
            L2 = (uy * vz - uz * vy) ** 2 + ny * ny + (ux * vy - uy * vx) ** 2
            if ny * ny <= 0.01 * L2:
                continue
            y = a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])
            topo = W.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            return (nm, topo, y)
    return None


def main() -> int:
    ok = True
    loader = CN._Loader(MOD_FOLDER, DISC)
    cells = CN.deployed_sea_cells(MOD_FOLDER, DISC)
    print(f"Disc{DISC} deployed sea cells: {cells}")
    if not cells:
        print("NO DEPLOYED SEA CELLS -- nothing to probe"); return 1

    # -- gate 0: CALIBRATE the indexed query against the linear scan
    rng = random.Random(20260730)
    mism = 0
    n_cal = 0
    for bx, by in cells:
        ox, oz = W.block_world_origin(bx, by)
        for _ in range(150):
            wx = ox + rng.uniform(-2.0, CN.BLOCK + 2.0)
            wz = oz - rng.uniform(-2.0, CN.BLOCK + 2.0)
            for parts in (None, SEAS):
                n_cal += 1
                a = CN._query_top(loader, wx, wz, parts=parts)
                b = _query_top_linear(loader, wx, wz, parts=parts)
                if a != b:
                    mism += 1
                    if mism <= 8:
                        print(f"   !! CALIBRATION mismatch at ({wx:.2f},{wz:.2f}) "
                              f"parts={'seas' if parts else 'all'}: indexed={a} linear={b}")
    print(f"CALIBRATE: {n_cal} paired queries, {mism} mismatch(es)")
    if mism:
        print("COAST-NAV DISC9: instrument uncalibrated -- aborting before the real gates")
        return 1

    # -- gate 1: THE SEAL
    leaks = 0
    checked = 0
    for bx, by in cells:
        ox, oz = W.block_world_origin(bx, by)          # origin = WEST,NORTH corner: z goes DOWN
        for xi in range(0, 64, 4):
            for zi in range(0, 64, 4):
                wx, wz = ox + xi + 2.0, oz - zi - 2.0
                top = CN._query_top(loader, wx, wz)
                if top is None or top[1] in CN.WATER or top[2] < CN.HIGH_Y:
                    continue
                checked += 1
                under = CN._query_top(loader, wx, wz, parts=SEAS)
                if under is not None and under[1] in LEGAL:
                    leaks += 1
                    if leaks <= 12:
                        print(f"   !! LEAK at ({wx:.0f},{wz:.0f}) block({bx},{by}): "
                              f"{under[0]} topo {under[1]} under {top[0]} y={top[2]:.1f}")
    print(f"SEAL: {checked} high-ground samples, {leaks} sail-through leak(s)")
    if leaks:
        ok = False

    # -- gate 2: THE STANDOFF
    soft = 0
    stand_checked = 0
    for bx, by in cells:
        lows, highs = CN._cell_grounds(loader, bx, by)
        ox, oz = W.block_world_origin(bx, by)
        for xi in range(0, 64, 4):
            for zi in range(0, 64, 4):
                wx, wz = ox + xi + 2.0, oz - zi - 2.0
                top = CN._query_top(loader, wx, wz)
                if top is None or top[1] not in CN.WATER:
                    continue
                wxm = wx % CN.WORLD_W
                dh = min((math.hypot(wxm - gx, wz - gz) for gx, gz in highs), default=99)
                if dh > 2.0:
                    continue
                stand_checked += 1
                if top[1] in LEGAL:
                    soft += 1
                    if soft <= 10:
                        print(f"   !! wall-hug legal water at ({wx:.0f},{wz:.0f}) "
                              f"block({bx},{by}): {top[0]} topo {top[1]} {dh:.1f}u off the wall")
    frac = soft / stand_checked if stand_checked else 0.0
    print(f"STANDOFF: {stand_checked} wall-hug samples, {soft} legal ({frac:.1%};"
          f" seam-artifact tolerance 5%)")
    if frac > 0.05:
        ok = False

    # -- gates 3+4: LANDINGS/CENSUS + byte INTEGRITY vs the backup
    root = CN._worldmap_root(MOD_FOLDER)
    census: dict[int, int] = {}
    live53 = 0
    bad_files = 0
    n_files = 0
    for bk in sorted(BACKUP.glob(f"*.disc{DISC}")):
        n_files += 1
        name = bk.name[:-(len(f".disc{DISC}"))]
        by = int(name.split("][")[1].split("]")[0])
        live = root / f"Disc{DISC}" / "0_1" / f"r{by}" / name
        old, new = bk.read_bytes(), live.read_bytes()
        good = len(old) == len(new)
        if good:
            vcount, icount, tan_off, idx_off = CN._parse_header(old)
            good = old[:tan_off] == new[:tan_off] and old[idx_off:] == new[idx_off:]
            if good:
                for i in range(vcount):
                    o = tan_off + i * 16
                    t1 = int(round(struct.unpack_from("<f", new, o)[0]))
                    topo1 = (t1 & 0xFC) >> 2
                    if topo1 == 53:
                        live53 += 1
                    if old[o:o + 16] == new[o:o + 16]:
                        continue
                    if old[o + 4:o + 16] != new[o + 4:o + 16]:
                        good = False; break
                    t0 = int(round(struct.unpack_from("<f", old, o)[0]))
                    topo0 = (t0 & 0xFC) >> 2
                    if (t0 & ~0xFC) != (t1 & ~0xFC) or topo0 not in CN.WATER \
                            or topo1 not in (53, 54, 55, 56):
                        good = False; break
                    census[topo1] = census.get(topo1, 0) + 1
        if not good:
            print(f"INTEGRITY: {name} VIOLATION")
            bad_files += 1
    names = {53: "BEACH", 54: "CLIFF", 55: "BELT", 56: "KEEL"}
    bits = " ".join(f"{names[c]}({c})={n}" for c, n in sorted(census.items()))
    print(f"INTEGRITY: {n_files} files checked, {bad_files} violation(s)")
    print(f"CENSUS of changed verts: {bits or 'none'}  (deploy said CLIFF 1128 / BELT 282 /"
          f" KEEL 468 / BEACH 0)")
    print(f"LANDINGS: {census.get(53, 0)} verts changed to 53, {live53} live 53 verts"
          f" (cliffs-refuse + no low shore -> both must be 0)")
    if bad_files or census.get(53, 0) or live53:
        ok = False

    print("\nCOAST-NAV DISC9:", "ALL CHECKS PASS" if ok else "VIOLATIONS -- see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
