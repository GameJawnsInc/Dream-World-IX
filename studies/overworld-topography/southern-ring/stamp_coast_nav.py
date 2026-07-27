"""R5d -- THE COAST NAVIGATION STAMP (v2; supersedes stamp_beach_fringe.py's boxes).

THE SAIL-THROUGH BUG (owner playtest 2026-07-26): the boat sails straight through kit-island
cliffs. Root cause: kit cells ship a FULL-CELL ocean under the land. `w_movementRoundCheck`
(ff9.cs:5633) probes the NEXT position via `w_cellHit` with the actor's tri CACHE -- sailing, the
cache is full of water tris, so at an under-land position the probe hits the underlying water
(53/57, in the Narciss mask {53,54,57}) and the move is LEGAL. Stock never has water under land
(the conforming-waterline grammar): the probe there hits rock/land (mask-illegal) or nothing --
blocked. Stock survey (blocks (9,17)/(10,18)/(3,13)/(16,17)/(7,17)): **topo 53 fronts BEACHES
ONLY; cliff-front water is 54/55/56/57** -- stock stops boats at cliffs by geometry, and 53 is
the landable class exactly as the getoff gate treats it.

THE FIX (navigation-only, "topo = tangent.x, look = UV+material"): re-derive every water tri's
navigation class in EVERY deployed kit sea cell (all Sea1..Sea5 override parts -- no hand boxes,
so the junction landmass, the R4 bench, Sandreach etc. are all covered):

  * under HIGH ground (top-query at centroid = ground with y >= 1.5u)  -> **56 KEEL-BLOCK**
    (water-class, outside the Narciss mask AND foot-illegal: the interior seals; also fixes the
    R5c fringe having made under-land water 53)
  * under LOW ground (< 1.5u -- the beach-apron waterline overlap)      -> **53 beach-front**
  * open water within 16u of LOW ground                                 -> **53 beach-front**
  * open water within 16u of ONLY HIGH ground                           -> **54 cliff-front**
    (sailable right up to the rock, stock feel -- but NOT 53, killing the cliff-face dismount
    exploit where the getoff sweep would beam the player up the cliff top)
  * open sea                                                            -> unchanged

Shared verts across class boundaries resolve by priority 53 > 56 > 54 (err landable at the
beach/keel seam -- the keel is many tris thick; err sealed at the keel/cliff seam). Topo bits
only (IDALL mask 0xFC); geometry/UV/material/event/area/flags byte-preserved. Disc parity
asserted before, restored after. Backups -> backups/r3-lamplight.20260726-r3lamplight/
pre-coastnav-sea/. Dry run by default; --deploy writes. Probe: probe_r3/probe_coast_nav.py.
"""
from __future__ import annotations

import argparse
import math
import re
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE / "probe_r3"))

from probe_sea_lane import MOD, load_parts   # noqa: E402
from ff9mapkit.world import extract as W     # noqa: E402

WATER = {53, 54, 55, 56, 57}
SEA_PARTS = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
HIGH_Y = 1.5           # ground at/above this = cliff/interior; below = beach apron
FRINGE_R = 16.0
STEP = 4.0
KEEL, BEACH, CLIFF = 56, 53, 54
# KEEL wins shared verts: the engine reads a hit tri's id off a vertex tangent, so a beach-claimed
# vert on a keel-boundary tri is a first-vert HOLE in the seal (probe round 1 found 23 of them).
# The cost -- a keel-adjacent beach tri can read 56 and refuse a landing at that exact spot -- is
# bounded and visible in the landing probe; a leak lets the boat cross the island. Seal wins.
PRIORITY = {KEEL: 0, BEACH: 1, CLIFF: 2}     # lower wins at shared verts
BACKUP = ROOT / "backups" / "r3-lamplight.20260726-r3lamplight" / "pre-coastnav-sea"


def query_top(wx, wz):
    """First part in registration order containing (wx,wz) -> (part, topo, y) or None.
    Object/Terrain precede the seas, so a hit on them = ground above any water there."""
    wx %= 1536.0
    bx, by = math.floor(wx / 64), math.floor(-wz / 64)
    ox, oz = W.block_world_origin(bx, by)
    for nm, bm in load_parts(bx, by):
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


def parse_header(data):
    assert data[:4] == b"F9WM", "bad magic"
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off = 20 + vcount * 12
    if flags & 1:
        off += vcount * 12
    if flags & 2:
        off += vcount * 8
    assert flags & 4, "sea override without tangents?!"
    return vcount, icount, off, off + vcount * 16


def deployed_sea_cells():
    cells = set()
    for p in (MOD / "Disc1" / "0_1").rglob("*.ff9mesh"):
        m = re.match(r"Block\[(\d+)\]\[(\d+)\] (Sea[1-5])\.ff9mesh$", p.name)
        if m:
            cells.add((int(m.group(1)), int(m.group(2))))
    return sorted(cells)


def cell_grounds(bx, by):
    """Ground samples (x, z, y) over the cell +/- an 18u margin, at STEP."""
    ox, oz = W.block_world_origin(bx, by)
    lows, highs = [], []
    x = ox - 18.0
    while x <= ox + 64 + 18.0:
        z = oz - 18.0
        while z <= oz + 64 + 18.0:
            g = query_top(x, z)
            if g is not None and g[1] not in WATER:
                (lows if g[2] < HIGH_Y else highs).append((x % 1536.0, z))
            z += STEP
        x += STEP
    return lows, highs


def stamp_cell(bx, by, deploy):
    lows = highs = None
    out = []
    for part in SEA_PARTS:
        p1 = MOD / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"
        p4 = MOD / "Disc4" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"
        if not p1.is_file():
            continue
        d1 = bytearray(p1.read_bytes())
        if p4.is_file():
            assert p4.read_bytes() == bytes(d1), f"Disc parity ALREADY broken: {p1.name} -- refusing"
        vcount, icount, tan_off, idx_off = parse_header(bytes(d1))
        if icount == 0:
            continue
        if lows is None:
            lows, highs = cell_grounds(bx, by)
        verts = [struct.unpack_from("<3f", d1, 20 + i * 12) for i in range(vcount)]
        idx = struct.unpack_from(f"<{icount}i", d1, idx_off)
        ox, oz = W.block_world_origin(bx, by)

        def topo_of(vi):
            return (int(round(struct.unpack_from("<f", d1, tan_off + vi * 16)[0])) & 0xFC) >> 2

        want = {}                                     # vert -> target class
        for t in range(icount // 3):
            tri = idx[t * 3:t * 3 + 3]
            if any(topo_of(vi) not in WATER for vi in tri):
                continue
            cx = sum(verts[vi][0] for vi in tri) / 3 + ox
            cz = sum(verts[vi][2] for vi in tri) / 3 + oz
            # Probe the centroid AND all three corners: a big straddling tri whose centroid sits
            # over the beach/open water can still extend under the cliff -- ANY probe point under
            # high ground makes the whole tri keel (round-1 leak class: centroid aliasing).
            probes = [(cx, cz)] + [(verts[vi][0] + ox, verts[vi][2] + oz) for vi in tri]
            tops = [query_top(px, pz) for px, pz in probes]
            grounded = [t for t in tops if t is not None and t[1] not in WATER]
            if any(t[2] >= HIGH_Y for t in grounded):
                cls = KEEL
            elif grounded:
                cls = BEACH
            else:
                if any(math.hypot(cx % 1536.0 - gx, cz - gz) <= FRINGE_R for gx, gz in lows):
                    cls = BEACH
                elif any(math.hypot(cx % 1536.0 - gx, cz - gz) <= FRINGE_R for gx, gz in highs):
                    cls = CLIFF
                else:
                    continue
            for vi in tri:
                if vi not in want or PRIORITY[cls] < PRIORITY[want[vi]]:
                    want[vi] = cls
        changed = {vi: cls for vi, cls in want.items() if topo_of(vi) != cls}
        if not changed:
            continue
        if deploy:
            BACKUP.mkdir(parents=True, exist_ok=True)
            for src, tag in ((p1, "disc1"), (p4, "disc4")):
                if src.is_file():
                    bk = BACKUP / f"{src.name}.{tag}"
                    if not bk.exists():
                        shutil.copy2(src, bk)
            for vi, cls in changed.items():
                o = tan_off + vi * 16
                old = int(round(struct.unpack_from("<f", d1, o)[0]))
                struct.pack_into("<f", d1, o, float((old & ~0xFC) | (cls << 2)))
            p1.write_bytes(bytes(d1))
            if p4.is_file():
                p4.write_bytes(bytes(d1))
        by_cls = {}
        for cls in changed.values():
            by_cls[cls] = by_cls.get(cls, 0) + 1
        out.append((part, len(changed), by_cls))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()
    total = 0
    for bx, by in deployed_sea_cells():
        res = stamp_cell(bx, by, args.deploy)
        if res:
            bits = " ".join(f"{part}:{n}v{cls}" for part, n, cls in res)
            print(f"({bx},{by}): {bits}")
            total += sum(n for _, n, _ in res)
    print(f"\nTOTAL: {total} verts {'STAMPED' if args.deploy else 'would change (dry run)'}"
          f"  (classes: 53=beach-front 54=cliff-front 56=keel-block)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
