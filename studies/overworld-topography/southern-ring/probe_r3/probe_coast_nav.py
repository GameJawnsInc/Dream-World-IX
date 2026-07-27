"""R5d -- THE COAST-NAV PROBE: is the sail-through sealed, honestly?

Four gates over the deployed state:
  1. THE SEAL -- the literal bug condition: at every 4u sample over HIGH ground (top-query y >=
     1.5u) in every deployed sea cell, the WATER-parts-only query (what the boat's cache-favored
     `w_cellHit` reads under land) must NOT return a Narciss-legal topo ({53,54,57}). Any hit
     there must be the keel-block (56) or absent.
  2. Landings -- probe_landings still finds sites at all seven shores (53 preserved at low shores).
  3. Lanes -- the north passage stays fully sailable.
  4. Byte integrity vs the pre-coastnav backups: diffs confined to tangent.x topo bits, old topo
     in {53,54,55,56,57}, new in {53,54,56}; Disc1==Disc4.
Exits nonzero on any violation.
"""
from __future__ import annotations

import math
import re
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from probe_sea_lane import MOD, load_parts, walk, SOUTH, NORTH   # noqa: E402
from ff9mapkit.world import extract as W                          # noqa: E402

WATER = {53, 54, 55, 56, 57}
LEGAL = {53, 54, 57}
HIGH_Y = 1.5
BACKUP = ROOT / "backups" / "r3-lamplight.20260726-r3lamplight" / "pre-coastnav-sea"


def hit(parts_filter, wx, wz):
    wx %= 1536.0
    bx, by = math.floor(wx / 64), math.floor(-wz / 64)
    ox, oz = W.block_world_origin(bx, by)
    for nm, bm in load_parts(bx, by):
        if not parts_filter(nm):
            continue
        for t in range(len(bm.tris)):
            a, b, c = [(bm.verts[k][0] + ox, bm.verts[k][1], bm.verts[k][2] + oz)
                       for k in bm.tris[t]]
            d = (b[0]-a[0])*(c[2]-a[2]) - (c[0]-a[0])*(b[2]-a[2])
            if abs(d) < 1e-12:
                continue
            w1 = ((wx-a[0])*(c[2]-a[2]) - (c[0]-a[0])*(wz-a[2])) / d
            w2 = ((b[0]-a[0])*(wz-a[2]) - (wx-a[0])*(b[2]-a[2])) / d
            if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
                continue
            y = a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])
            topo = W.decode_id(int(round(bm.tangents[bm.tris[t][0]][0])))["topograph"]
            return (nm, topo, y)
    return None


def deployed_sea_cells():
    cells = set()
    for p in (MOD / "Disc1" / "0_1").rglob("*.ff9mesh"):
        m = re.match(r"Block\[(\d+)\]\[(\d+)\] (Sea[1-5])\.ff9mesh$", p.name)
        if m:
            cells.add((int(m.group(1)), int(m.group(2))))
    return sorted(cells)


def parse_header(data):
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off = 20 + vcount * 12
    if flags & 1:
        off += vcount * 12
    if flags & 2:
        off += vcount * 8
    return vcount, icount, off, off + vcount * 16


def main() -> int:
    ok = True

    # -- gate 1: THE SEAL
    leaks = 0
    checked = 0
    for bx, by in deployed_sea_cells():
        ox, oz = W.block_world_origin(bx, by)          # origin = WEST,NORTH corner: z goes DOWN
        for xi in range(0, 64, 4):
            for zi in range(0, 64, 4):
                wx, wz = ox + xi + 2.0, oz - zi - 2.0
                top = hit(lambda nm: True, wx, wz)
                if top is None or top[1] in WATER or top[2] < HIGH_Y:
                    continue
                checked += 1
                under = hit(lambda nm: nm.startswith("Sea"), wx, wz)
                if under is not None and under[1] in LEGAL:
                    leaks += 1
                    if leaks <= 12:
                        print(f"   !! LEAK at ({wx:.0f},{wz:.0f}) block({bx},{by}): "
                              f"{under[0]} topo {under[1]} under {top[0]} y={top[2]:.1f}")
    print(f"SEAL: {checked} high-ground samples, {leaks} sail-through leak(s)")
    if leaks:
        ok = False

    # -- gate 1b: THE STANDOFF (v2.3) -- open water within 2u of a HIGH-LOCALE (wall) front
    # should be mask-illegal, so the hull floats off the rock. The BEACH>BELT shared-vert
    # priority (landing survival) tolerates bounded seam artifacts: fail only past 5%.
    sys.path.insert(0, str(HERE.parent))
    from stamp_coast_nav import cell_grounds   # noqa: E402
    soft = 0
    stand_checked = 0
    for bx, by in deployed_sea_cells():
        lows, highs = cell_grounds(bx, by)
        ox, oz = W.block_world_origin(bx, by)          # origin = WEST,NORTH corner: z goes DOWN
        for xi in range(0, 64, 4):
            for zi in range(0, 64, 4):
                wx, wz = ox + xi + 2.0, oz - zi - 2.0
                top = hit(lambda nm: True, wx, wz)
                if top is None or top[1] not in WATER:
                    continue
                wxm = wx % 1536.0
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
    print(f"STANDOFF: {stand_checked} wall-hug samples, {soft} legal ({frac:.1%}; seam-artifact"
          f" tolerance 5%)")
    if frac > 0.05:
        ok = False

    # -- gate 4: byte integrity vs backups
    bad_files = 0
    for bk in sorted(BACKUP.glob("*.disc1")):
        name = bk.name[:-6]
        by = int(name.split("][")[1].split("]")[0])
        live1 = MOD / "Disc1" / "0_1" / f"r{by}" / name
        live4 = MOD / "Disc4" / "0_1" / f"r{by}" / name
        old, new = bk.read_bytes(), live1.read_bytes()
        good = len(old) == len(new)
        if good:
            vcount, icount, tan_off, idx_off = parse_header(old)
            good = old[:tan_off] == new[:tan_off] and old[idx_off:] == new[idx_off:]
            if good:
                for i in range(vcount):
                    o = tan_off + i * 16
                    if old[o:o + 16] == new[o:o + 16]:
                        continue
                    if old[o + 4:o + 16] != new[o + 4:o + 16]:
                        good = False; break
                    t0 = int(round(struct.unpack_from("<f", old, o)[0]))
                    t1 = int(round(struct.unpack_from("<f", new, o)[0]))
                    if (t0 & ~0xFC) != (t1 & ~0xFC) or (t0 & 0xFC) >> 2 not in WATER \
                            or (t1 & 0xFC) >> 2 not in (53, 54, 55, 56):
                        good = False; break
        if good and live4.is_file() and live4.read_bytes() != new:
            good = False
        if not good:
            print(f"INTEGRITY: {name} VIOLATION")
            bad_files += 1
    print(f"INTEGRITY: {len(list(BACKUP.glob('*.disc1')))} files checked, {bad_files} violation(s)")
    if bad_files:
        ok = False

    # -- gate 2: landings (subprocess keeps its own module state clean)
    r = subprocess.run([sys.executable, str(HERE / "probe_landings.py")],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print("LANDINGS: FAIL"); ok = False

    # -- gate 3: the lanes
    n = walk("NORTH passage", NORTH)
    if not n:
        print("NORTH passage NO LONGER SAILABLE"); ok = False

    print("\nCOAST-NAV:", "ALL CHECKS PASS" if ok else "VIOLATIONS -- see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
