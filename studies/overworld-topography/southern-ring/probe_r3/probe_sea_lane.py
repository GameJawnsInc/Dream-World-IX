"""R5 -- THE SEA-LANE PROBE: is the west arc sailable for the Blue Narciss class?

The ratified voyage: the junction island's west shore -> (the x=0/1536 wrap) -> around Lamplight ->
the horseshoe bench. Block-proven open at design time; this probes it at the TILE level against the
boat's real legality mask: TransportControls.csv row 'Blue Narciss' limit0=39845888/limit1=0 ->
legal topographs exactly {53, 54, 57} (decoded with the same bit convention that reproduces the
engine foot-walk table from the Walking row -- the mask oracle).

Method: sample every 8u along candidate polylines (a SOUTH and a NORTH passage around Lamplight),
query the STACKED live meshes (our overrides where present, stock otherwise) in the engine's
registration order (Object, Terrain, Beach1, Sea1, Sea2, Sea3, Sea5, Sea4 -- first up-facing hit
wins), and judge each sample's topograph against the mask. Reports per-passage verdicts + every
illegal span. Read-only; exits nonzero if NO passage is fully legal.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import extract as W   # noqa: E402
from ff9mapkit.world import mesh as M      # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
BOAT_TOPOS = {53, 54, 57}
PARTS_ORDER = ("Object", "Terrain", "Beach1", "Sea1", "Sea2", "Sea3", "Sea5", "Sea4")

# The two candidate passages (world coords; the run wraps in x -- handled by sampling mod 1536).
# Start SEAWARD of Ashvale's shore; end IN the west channel (x ~1360, between Lamplight's outline
# at 1387 and the horseshoe's east edge at 1344) -- the voyage's terminus is a sail-past, the boat
# cannot land (its mask has no land topos).
SOUTH = [(20, -1168), (-20, -1180), (-60, -1200), (-97, -1230),   # west off Ashvale, wrap
         (-140, -1245), (-190, -1240), (-230, -1210), (-260, -1190),  # south of Lamplight (x mod)
         (-176, -1215)]                                            # the west channel, south end
NORTH = [(20, -1168), (-24, -1162), (-60, -1125), (-100, -1110),   # cross the wrap at z~-1165:
         (-150, -1105), (-200, -1115), (-240, -1130),              # the junction's west wall
         (-176, -1140)]                                            # bulges to the wrap column
                                                                   # near z-1152..-1157, and its
                                                                   # R5e standoff belt (3.5u,
                                                                   # topo 55) closes the old
                                                                   # z~-1159 crossing. The west
                                                                   # channel, north end.

_cache: dict = {}


def load_parts(bx, by):
    key = (bx, by)
    if key in _cache:
        return _cache[key]
    parts = []
    for part in PARTS_ORDER:
        p = MOD / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"
        bm = None
        if p.is_file():
            try:
                bm = M.blockmesh_from_ff9mesh(str(p), disc=1, x=bx, y=by, part=part.lower())
            except Exception:
                bm = None
        else:
            try:
                bm = W.read_block(bx, by, disc=1, part=part.lower())
            except Exception:
                bm = None
        if bm is not None and len(bm.tris):
            parts.append((part, bm))
    _cache[key] = parts
    return parts


def query(wx, wz):
    wx %= 1536.0
    bx, by = math.floor(wx / 64), math.floor(-wz / 64)
    ox, oz = W.block_world_origin(bx, by)
    best = None
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
            return (nm, W.decode_id(int(round(bm.tangents[bm.tris[t][0]][0])))["topograph"])
    # No part contains the point. A cell with NO per-block mesh assets at all is PURE OPEN OCEAN:
    # the engine renders it via the runtime SeaBlockPrefab (generic full-cell deep sea, topograph
    # 57) -- there is no file to read, and the boat mask calls it legal. Distinguish that from a
    # cell that HAS parts but none covering the point (a real hole).
    if not load_parts(bx, by):
        return ("SeaBlockPrefab", 57)
    return best


def walk(name, pts):
    bad = []
    n = 0
    for i in range(len(pts) - 1):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        steps = max(1, int(math.hypot(x1 - x0, z1 - z0) / 8))
        for s in range(steps + 1):
            wx, wz = x0 + (x1-x0)*s/steps, z0 + (z1-z0)*s/steps
            n += 1
            g = query(wx, wz)
            if g is None:
                bad.append((round(wx % 1536, 1), round(wz, 1), "NO MESH"))
            elif g[1] not in BOAT_TOPOS:
                bad.append((round(wx % 1536, 1), round(wz, 1), f"{g[0]} topo {g[1]}"))
    ok = not bad
    print(f"{name}: {n} samples, {'FULLY SAILABLE' if ok else f'{len(bad)} illegal sample(s)'}")
    for b in bad[:12]:
        print("   !!", b)
    return ok


def main() -> int:
    s = walk("SOUTH passage (Ashvale -> wrap -> south of Lamplight -> horseshoe SE)", SOUTH)
    n = walk("NORTH passage (Ashvale -> wrap -> north of Lamplight -> horseshoe NE)", NORTH)
    print()
    print("VERDICT:", "the west arc is sailable" if (s or n) else "NO fully-legal passage")
    return 0 if (s or n) else 1


if __name__ == "__main__":
    sys.exit(main())
