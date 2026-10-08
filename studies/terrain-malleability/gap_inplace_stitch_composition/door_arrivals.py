"""WHERE DOES A FIELD EXIT SET THE PLAYER DOWN ON THE WORLD MAP? (terrain study defect 6, 2026-10-08)

The world player's Init (every free-roam dispatcher, e.g. WORLD09 e13 tag0) places the player with
``MoveInstantXZY(Global.Int24[64], Global.Int16[67], Global.Int24[69])`` -- the persisted world-position record
(``content/worldexit._POS_ONFOOT``; the vehicle composite uses ``Int24[83]/Int16[86]/Int24[88]``). Only when the
entrance key ``D8:2`` is 0 does it first stamp a default. So the landing is either (a) a CONSTANT a field wrote into
the record before ``WorldMap()`` (a door arrival), or (b) whatever the record last held -- the player's own position
when they walked onto the entrance tile (the per-frame mirror). Case (b) puts the landing ON the entrance tiles.

This census reads every stock field event script (us) and lists every constant write to the on-foot or vehicle
record (``05 <class> <idx> 7E <i32> 2C 7F`` for x/z, ``05 D8 <idx> 7D <i16> 2C 7F`` for y): the door arrivals.
World units = record / 256; the record's y is the engine's, negated (world y = -y/256).
Writes out/door_arrivals.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/door_arrivals.py
"""
from __future__ import annotations

import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
from ff9mapkit import extract as FX                    # noqa: E402

BLOCKS = {"onfoot": ((0xC8, 0x40), (0xD8, 0x43), (0xC8, 0x45)),
          "vehicle": ((0xC8, 0x53), (0xD8, 0x56), (0xC8, 0x58))}


def writes(data: bytes):
    """Every constant record write, in byte order: (offset, (class, idx), value)."""
    out = []
    for m in re.finditer(rb"\x05([\xC8\xD8])(.)\x7E(.{4})\x2C\x7F", data, re.S):
        out.append((m.start(), (m.group(1)[0], m.group(2)[0]), struct.unpack("<i", m.group(3))[0]))
    for m in re.finditer(rb"\x05\xD8(.)\x7D(.{2})\x2C\x7F", data, re.S):
        out.append((m.start(), (0xD8, m.group(1)[0]), struct.unpack("<h", m.group(2))[0]))
    return sorted(out)


def main():
    env = FX._load_env(FX._streaming_assets(S.GAME) / FX._events_bundle(S.GAME))
    found, n = [], 0
    for k, obj in env.container.items():
        kl = k.lower()
        if "eventbinary/field/us/" not in kl or not kl.endswith(".eb.bytes"):
            continue
        n += 1
        data = FX._raw_bytes(obj.read())
        evt = kl.rsplit("/", 1)[1][:-len(".eb.bytes")]
        ws = writes(data)
        for name, ((xc, xi), (yc, yi), (zc, zi)) in BLOCKS.items():
            xs = [(o, v) for o, var, v in ws if var == (xc, xi)]
            for (ox, vx) in xs:                     # pair each x write with the next y and z writes after it
                vy = next((v for o, var, v in ws if var == (yc, yi) and o > ox), None)
                vz = next((v for o, var, v in ws if var == (zc, zi) and o > ox), None)
                if vz is None:
                    continue
                found.append({"event": evt, "block": name, "offset": ox, "x": round(vx / 256.0, 3),
                              "z": round(vz / 256.0, 3), "y": None if vy is None else round(-vy / 256.0, 3)})
    by_point = defaultdict(list)
    for f in found:
        by_point[(f["x"], f["z"])].append(f["event"])
    # how far is each arrival from the nearest walk-on entrance tile (event bits) on stock disc-1 ground?
    from ff9mapkit.world import extract as X, mesh as M
    tiles = {}

    def _tiles(bx, by):
        if (bx, by) not in tiles:
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain", game=S.GAME)
            except (ValueError, FileNotFoundError):
                tiles[(bx, by)] = []
                return tiles[(bx, by)]
            o = X.block_world_origin(bx, by)
            tiles[(bx, by)] = [ps for i, ps in M.bm_tiles(bm, M.world_positions(bm, o))
                               if i not in M.WALK_SKIP_IDS and X.decode_id(i)["event"]]
        return tiles[(bx, by)]
    rows = []
    for (x, z), evs in sorted(by_point.items()):
        bx, by = int(x // 64), int(-z // 64)
        pts = [p for dx in (-1, 0, 1) for dy in (-1, 0, 1) for ps in _tiles(bx + dx, by + dy) for p in ps]
        near = min((((p[0] - x) ** 2 + (p[2] - z) ** 2) ** 0.5 for p in pts), default=None)
        rows.append({"x": x, "z": z, "block": (bx, by), "events": sorted(set(evs)),
                     "nearest_entrance_tile": None if near is None else round(near, 1)})
    ds = sorted(r["nearest_entrance_tile"] for r in rows if r["nearest_entrance_tile"] is not None)
    res = {"field_scripts": n, "writes": len(found), "points": len(by_point),
           "fields_with_arrivals": len({f["event"] for f in found}),
           "distance_to_tile": {"n": len(ds), "no_tile_within_a_block": len(rows) - len(ds),
                                "max": ds[-1] if ds else None, "p50": ds[len(ds) // 2] if ds else None,
                                "within_4u": sum(1 for d in ds if d <= 4), "within_8u": sum(1 for d in ds if d <= 8),
                                "within_16u": sum(1 for d in ds if d <= 16)},
           "arrivals": rows}
    p = S.OUT / "door_arrivals.json"
    p.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print({k: v for k, v in res.items() if k != "arrivals"})
    for a in res["arrivals"][:80]:
        print("  ", a)
    print("->", p)


if __name__ == "__main__":
    main()
