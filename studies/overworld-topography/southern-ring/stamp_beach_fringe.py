"""R5c -- THE BEACHABLE-FRINGE STAMP: give each ring island the topo-53 water fringe the engine
dismount gate demands.

⚠ SUPERSEDED by stamp_coast_nav.py (R5d, same day): the hand boxes below UNDER-COVER the real
landmasses (the junction spans blocks (0-4,16-19); the R4 bench is at (1-2,1-3)), and 53-within-
16u-of-ANY-ground is wrong at cliffs (stock 53 fronts beaches only) and under land (it made the
sail-through worse). The v2 stamp re-derives all three navigation classes (53/54/56) over every
deployed sea cell; re-running THIS script against the v2 state is a near-no-op (it only touches
all-57 tris) but don't -- keep it as the R5c record.

WHY: ff9.w_movementGetGetoff (mode 7 -- the Narciss class) refuses unless the tile ahead of the
hull reads topograph 53 (beach-front water). Stock coasts grade Sea1/Sea2 topo-53 at the sand
(block (7,17) proves it: 53 at the sand line, 54/55/56/57 grading out). The ring's islands were
minted/carried GROUND-only -- their coasts are pure Sea4 topo-57 to the shoreline (deep sea laps
the sand), so the boat can land NOWHERE but the stock islet (probe_r3/probe_landings.py, first run).

THE LAWFUL MECHANISM (coast-mosaic LAW INDEX): "navigation and render are SEPARABLE -- topo =
tangent.x, look = UV+material". This stamp rewrites ONLY the topograph bits (IDALL bits 2-7,
mask 0xFC) of near-shore Sea4 verts from 57 -> 53, byte-in-place: verts/uvs/normals/indices and
every other IDALL field (event/area/flags) are untouched. Zero visual change; the shallow-LOOK
ladder (real Sea1/Sea2 rings) stays a separate fidelity arc.

Rule: a Sea4 tri qualifies iff ALL THREE verts read topo 57 AND its centroid lies within
FRINGE_R of any GROUND sample (stacked-mesh query, non-water topo) of that island; every vert of
a qualifying tri is stamped (the engine reads a hit tri's id off a vertex tangent -- stamping all
three covers either diagonal convention). Vert leak to an adjacent outer tri only widens legal-53
water -- sailable either way, and the getoff sweep still requires real ground, so it errs safe.

Cells: only blocks that HAVE a deployed Sea4 override (THE ABSENT-PART / DIVERT-ARM laws -- a
cell without one renders the runtime SeaBlockPrefab and has no file to edit). Disc4 parity is
asserted before and restored after. Backups -> backups/r3-lamplight.20260726-r3lamplight/
pre-fringe-sea4/. Dry run by default; --deploy writes.
"""
from __future__ import annotations

import argparse
import math
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE / "probe_r3"))

from probe_sea_lane import BOAT_TOPOS, query, GAME, MOD  # noqa: E402

FRINGE_R = 16.0        # world units ground->water reach; the stock (7,17) 53-band's own scale
OLD_TOPO, NEW_TOPO = 57, 53
STEP = 4.0
BACKUP = ROOT / "backups" / "r3-lamplight.20260726-r3lamplight" / "pre-fringe-sea4"

# The ring islands (probe_landings' boxes minus the stock islet -- (7,17) already carries 53).
BOXES = {
    "Ashvale":       (20, 80, -1195, -1135),
    "Tidefall":      (390, 450, -1255, -1195),
    "Grimhorn":      (1175, 1235, -1215, -1155),
    "Larkspur":      (670, 730, -640, -580),
    "Lamplight":     (1395, 1455, -1195, -1135),
    "the horseshoe": (1260, 1360, -1230, -1120),
}


def ground_samples(box):
    x0, x1, z0, z1 = box
    pts = []
    x = x0
    while x <= x1:
        z = z0
        while z <= z1:
            g = query(x, z)
            if g is not None and g[1] not in BOAT_TOPOS and g[1] not in (55, 56):
                pts.append((x % 1536.0, z))
            z += STEP
        x += STEP
    return pts


def sea4_path(disc, bx, by):
    return MOD / f"Disc{disc}" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Sea4.ff9mesh"


def parse_header(data):
    assert data[:4] == b"F9WM", "bad magic"
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off = 20 + vcount * 12                       # verts
    if flags & 1:
        off += vcount * 12                       # normals
    if flags & 2:
        off += vcount * 8                        # uvs
    assert flags & 4, "Sea4 override without tangents?!"
    tan_off = off
    idx_off = tan_off + vcount * 16
    return vcount, icount, tan_off, idx_off


def stamp_block(bx, by, grounds, deploy):
    """Returns (touched_verts, qual_tris) for this block, writing if deploy."""
    p1, p4 = sea4_path(1, bx, by), sea4_path(4, bx, by)
    if not p1.is_file():
        return 0, 0
    d1 = bytearray(p1.read_bytes())
    if p4.is_file():
        assert p4.read_bytes() == bytes(d1), f"Disc parity ALREADY broken at {p1.name} -- refusing"
    vcount, icount, tan_off, idx_off = parse_header(bytes(d1))
    verts = [struct.unpack_from("<3f", d1, 20 + i * 12) for i in range(vcount)]
    idx = struct.unpack_from(f"<{icount}i", d1, idx_off)
    from ff9mapkit.world import extract as W          # world origin per the probe's own convention
    ox, oz = W.block_world_origin(bx, by)

    def topo_of(vi):
        t = struct.unpack_from("<4f", d1, tan_off + vi * 16)[0]
        return (int(round(t)) & 0xFC) >> 2

    to_stamp, qual = set(), 0
    for t in range(icount // 3):
        tri = idx[t * 3:t * 3 + 3]
        if any(topo_of(vi) != OLD_TOPO for vi in tri):
            continue
        cx = sum(verts[vi][0] for vi in tri) / 3 + ox
        cz = sum(verts[vi][2] for vi in tri) / 3 + oz
        if any(math.hypot(cx - gx, cz - gz) <= FRINGE_R for gx, gz in grounds):
            qual += 1
            to_stamp.update(tri)
    if not to_stamp:
        return 0, 0
    if deploy:
        BACKUP.mkdir(parents=True, exist_ok=True)
        for src in (p1, p4):
            if src.is_file():
                bk = BACKUP / f"{src.name}.disc{src.parent.parent.parent.name[-1]}"
                if not bk.exists():
                    shutil.copy2(src, bk)
        for vi in sorted(to_stamp):
            o = tan_off + vi * 16
            old = int(round(struct.unpack_from("<f", d1, o)[0]))
            new = (old & ~0xFC) | (NEW_TOPO << 2)
            struct.pack_into("<f", d1, o, float(new))
        p1.write_bytes(bytes(d1))
        if p4.is_file():
            p4.write_bytes(bytes(d1))            # restore parity with the patched bytes
    return len(to_stamp), qual


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()
    total_v = total_t = 0
    for name, box in BOXES.items():
        grounds = ground_samples(box)
        x0, x1, z0, z1 = box
        blocks = {(int((x % 1536.0) // 64), int(-z // 64))
                  for x in range(int(x0) - 16, int(x1) + 17, 8)
                  for z in range(int(z0) - 16, int(z1) + 17, 8)}
        got = []
        for bx, by in sorted(blocks):
            nv, nt = stamp_block(bx, by, grounds, args.deploy)
            if nv:
                got.append(f"({bx},{by}):{nv}v/{nt}t")
                total_v += nv
                total_t += nt
        print(f"{name}: {' '.join(got) if got else 'nothing to stamp'}")
    print(f"\nTOTAL: {total_v} verts / {total_t} tris {'STAMPED' if args.deploy else 'would stamp (dry run)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
