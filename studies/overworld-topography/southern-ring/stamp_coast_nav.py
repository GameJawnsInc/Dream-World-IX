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

  * under HIGH-LOCALE ground (any of centroid+3 corners; a cliff-BASE vertex at the waterline
    is high-locale, never a beach) -> **56 KEEL-BLOCK** (outside the Narciss mask AND
    foot-illegal: the interior seals)
  * under LOW-locale ground (the waterline overlap)                     -> **53 beach-front**
  * open water hugging HIGH-locale ground (exact tri distance <= 3.5u)  -> **55 THE STANDOFF
    BELT** (visual: the hull floats off the wall instead of burying its bow; 3.5 < the 4.375u
    getoff sweep, so dismount still lands OVER the belt -- THE COMPATIBILITY LAW at the
    constants below)
  * other open water within 16u of ANY ground                           -> **53 beach-front**
    (the ring's land-anywhere property, owner-confirmed; plateau isles have no unlandable
    shores by design)
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
HIGH_Y = 1.5           # a single ground SAMPLE at/above this is high...
LOCALE_R = 3.0         # ...but a sample's CLASS is its LOCALE: low only if NO ground within
LOCALE_HIGH_Y = 2.0    # LOCALE_R rises to LOCALE_HIGH_Y. A cliff-base vertex sits at the
                       # waterline (y<1.5) yet is NOT a beach -- round 3's "boat noses into the
                       # rock" came from cliff bases classifying as low ground and painting
                       # landable 53 right against the face. THE TRIM MEASURE (round 3e/3f, from
                       # the Ashvale-vs-stock transects): kit shores are a ~2u low TRIM then a
                       # 3.0u plateau EVERYWHERE -- geometry can't do beach-vs-cliff at 4.5u+
                       # (6.0/4.5 killed every landing). 3.0u on a 2u ground grid keeps a low
                       # strip WIDER than a wall's base trim landable (real aprons like the
                       # (7,17)-family sand) and belts the thin wall trims the owner's
                       # screenshots complained about.
STEP_G = 2.0           # the ground scan's own step -- finer than the water STEP so LOCALE_R=3.0
                       # actually sees neighbors (a 4u grid has none within 3u).
FRINGE_R = 16.0
STEP = 4.0
# THE COMPATIBILITY LAW (v2.3 -- the round-3 endgame): the getoff GATE reads the tile UNDER THE
# HULL (w_movementRoundCheck at speed 0) and the landing SWEEP reaches at most
# S(radius*8/4) = S(1120) = 4.375u from the hull (Narciss radius=560, ff9.S = /256). So a
# standoff belt WIDER than ~4.4u makes a shore unlandable -- and the ring's islands are PLATEAU
# islands (a ~2u trim then a 3.0u wall, the Ashvale transects): under stock grammar they would be
# unlandable cliff isles, but land-anywhere is the ring's confirmed-fun property (owner: "get off
# at any beach I please"). Resolution: the belt is exactly the widest standoff compatible with
# landing -- 3.5u < 4.375u. The hull now floats ~3.5u off a wall (the bow no longer buries in the
# rock) and dismount still lands over the belt everywhere.
BELT_R = 3.5           # THE STANDOFF BELT (visual): mask-illegal water hugging HIGH-locale
                       # fronts. MUST stay under the 4.375u sweep reach or landings die.
KEEL, BEACH, BELT = 56, 53, 55
# Shared-vert priority: KEEL first (round 1: beach-claimed verts left 23 first-vert holes in the
# seal). BEACH beats BELT at the seam: the gate reads the tile under the hull, so a belt-claimed
# vert on a 53 ring tri would refuse the landing there -- landing survival outranks the last
# half-tri of standoff.
PRIORITY = {KEEL: 0, BEACH: 1, BELT: 2}
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
    """Ground samples over the cell +/- an 18u margin, at STEP, classified by LOCALE:
    a sample is LOW only if no ground within LOCALE_R rises to LOCALE_HIGH_Y (a cliff-base
    vertex at the waterline is HIGH ground by locale, never a beach)."""
    # ⚠ THE ORIGIN CONVENTION (round 3d -- the instrument bug): block_world_origin returns the
    # cell's WEST,NORTH corner; the cell spans z from oz DOWN to oz-64. The first three rounds
    # scanned oz..oz+64 -- the NEIGHBOR ROW -- so every ground list (and the probe's seal grid)
    # was displaced one row north; v1's box-based 53s masked it at the landing sites.
    ox, oz = W.block_world_origin(bx, by)
    raw = []
    x = ox - 18.0
    while x <= ox + 64 + 18.0:
        z = oz + 18.0
        while z >= oz - 64.0 - 18.0:
            g = query_top(x, z)
            if g is not None and g[1] not in WATER:
                raw.append((x % 1536.0, z, g[2]))
            z -= STEP_G
        x += STEP_G
    lows, highs = [], []
    for gx, gz, gy in raw:
        near_hi = any(abs(gx - px) <= LOCALE_R and abs(gz - pz) <= LOCALE_R
                      and math.hypot(gx - px, gz - pz) <= LOCALE_R and py >= LOCALE_HIGH_Y
                      for px, pz, py in raw)
        (highs if near_hi else lows).append((gx, gz))
    return lows, highs


def tri_dist2d(px, pz, a, b, c):
    """Exact 2D distance from point (px,pz) to triangle abc (0 inside). Point-probing a big tri's
    corners+centroid misses mid-EDGE approaches to a cliff (round-3c: tris hugging the rock along
    an edge read sailable) -- the belt test needs the true distance."""
    d = (b[0]-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(b[1]-a[1])
    if abs(d) > 1e-12:
        w1 = ((px-a[0])*(c[1]-a[1]) - (c[0]-a[0])*(pz-a[1])) / d
        w2 = ((b[0]-a[0])*(pz-a[1]) - (px-a[0])*(b[1]-a[1])) / d
        if w1 >= 0 and w2 >= 0 and w1 + w2 <= 1:
            return 0.0
    best = float("inf")
    for p, q in ((a, b), (b, c), (c, a)):
        vx, vz = q[0]-p[0], q[1]-p[1]
        L2 = vx*vx + vz*vz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px-p[0])*vx + (pz-p[1])*vz) / L2))
        best = min(best, math.hypot(px - (p[0] + t*vx), pz - (p[1] + t*vz)))
    return best


def locale_of(px, pz, lows, highs):
    """LOCALE class of the ground at a probe point: True=high / False=low, by the nearest
    classified ground sample within ~7u (probe points sit <=~3u from a scan sample); None if
    somehow no sample is near (caller falls back to the probe's own height)."""
    px %= 1536.0
    best_d, best_cls = 7.0, None
    for cls, pts in ((True, highs), (False, lows)):
        for gx, gz in pts:
            if abs(px - gx) >= best_d or abs(pz - gz) >= best_d:
                continue
            d = math.hypot(px - gx, pz - gz)
            if d < best_d:
                best_d, best_cls = d, cls
    return best_cls


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
            # high-LOCALE ground makes the whole tri keel (round-1 leak class: centroid aliasing;
            # round-3: a cliff-base vertex is low-HEIGHT but high-LOCALE, never a beach).
            probes = [(cx, cz)] + [(verts[vi][0] + ox, verts[vi][2] + oz) for vi in tri]
            tops = [query_top(px, pz) for px, pz in probes]
            grounded = [(px, pz, t) for (px, pz), t in zip(probes, tops)
                        if t is not None and t[1] not in WATER]
            if grounded:
                # KEEL on raw height OR locale: raw >= 1.5 alone seals mid-height banks the
                # 2.0-locale misses (round 3g: a 1.8u bank read 53 underneath); locale alone
                # seals under thin wall trims (raw < 1.5 at the base of a 3u wall).
                def is_high(px, pz, t):
                    if t[2] >= HIGH_Y:
                        return True
                    loc = locale_of(px, pz, lows, highs)
                    return bool(loc)
                cls = KEEL if any(is_high(px, pz, t) for px, pz, t in grounded) else BEACH
            else:
                # BELT by the EXACT tri-to-sample distance (rounds 3b/3c: corner- and even
                # edge-aliasing on big tris left sailable reads at the rock). Everything else
                # within the fringe of ANY ground is 53 -- the ring's land-anywhere property
                # (v2.3; the 54 "cliff-front" class is gone: plateau isles have no unlandable
                # shores by design).
                ta, tb, tc = [((verts[vi][0] + ox) % 1536.0, verts[vi][2] + oz) for vi in tri]
                cxm = cx % 1536.0
                reach = BELT_R + max(math.hypot(cxm - p[0], cz - p[1]) for p in (ta, tb, tc))
                hug = any(math.hypot(cxm - gx, cz - gz) <= reach
                          and tri_dist2d(gx, gz, ta, tb, tc) <= BELT_R
                          for gx, gz in highs)
                if hug:
                    cls = BELT          # THE STANDOFF BELT: mask-illegal, holds the hull off rock
                elif any(math.hypot(cxm - gx, cz - gz) <= FRINGE_R for gx, gz in lows) or \
                        any(math.hypot(cxm - gx, cz - gz) <= FRINGE_R for gx, gz in highs):
                    cls = BEACH
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
          f"  (classes: 53=beach-front 55=standoff-belt 56=keel-block)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
