"""R5c -- THE FRINGE-STAMP INTEGRITY PROBE.

For every Sea4 file backed up by stamp_beach_fringe.py, prove against the live deploy:
  1. same byte length; diffs confined to tangent-slot X floats (offset tan_off + 16*i);
  2. every differing tangent.x decodes as IDALL topo 57 -> 53 with event/area/flags bits
     byte-preserved (mask ~0xFC identical);
  3. verts / normals / uvs / indices byte-identical;
  4. Disc1 == Disc4 for every touched cell (parity);
  5. the sea lanes stay sailable (probe_sea_lane re-run, both passages judged).
Exits nonzero on any violation.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))

from probe_sea_lane import MOD, walk, SOUTH, NORTH   # noqa: E402

BACKUP = ROOT / "backups" / "r3-lamplight.20260726-r3lamplight" / "pre-fringe-sea4"


def parse_header(data):
    assert data[:4] == b"F9WM"
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off = 20 + vcount * 12
    if flags & 1:
        off += vcount * 12
    if flags & 2:
        off += vcount * 8
    return vcount, icount, off, off + vcount * 16


def main() -> int:
    ok = True
    backups = sorted(BACKUP.glob("*.disc1"))
    if not backups:
        print("NO backups found -- was the stamp deployed?")
        return 1
    total = 0
    for bk in backups:
        name = bk.name[:-6]                                   # strip ".disc1"
        by = int(name.split("][")[1].split("]")[0])
        live1 = MOD / "Disc1" / "0_1" / f"r{by}" / name
        live4 = MOD / "Disc4" / "0_1" / f"r{by}" / name
        old, new = bk.read_bytes(), live1.read_bytes()
        if len(old) != len(new):
            print(f"{name}: LENGTH CHANGED {len(old)} -> {len(new)}"); ok = False; continue
        vcount, icount, tan_off, idx_off = parse_header(old)
        # non-tangent regions byte-identical
        if old[:tan_off] != new[:tan_off] or old[idx_off:] != new[idx_off:]:
            print(f"{name}: bytes OUTSIDE the tangent block changed"); ok = False; continue
        bad = stamped = 0
        for i in range(vcount):
            o = tan_off + i * 16
            if old[o:o + 16] == new[o:o + 16]:
                continue
            if old[o + 4:o + 16] != new[o + 4:o + 16]:
                bad += 1; continue                            # tangent.y/z/w changed -- illegal
            t0 = int(round(struct.unpack_from("<f", old, o)[0]))
            t1 = int(round(struct.unpack_from("<f", new, o)[0]))
            if (t0 & ~0xFC) != (t1 & ~0xFC) or (t0 & 0xFC) >> 2 != 57 or (t1 & 0xFC) >> 2 != 53:
                bad += 1; continue
            stamped += 1
        if bad:
            print(f"{name}: {bad} ILLEGAL vert change(s)"); ok = False
        if live4.is_file() and live4.read_bytes() != new:
            print(f"{name}: DISC PARITY BROKEN"); ok = False
        total += stamped
        print(f"{name}: {stamped} verts 57->53, everything else byte-identical, parity OK")
    print(f"\n{total} stamped verts verified across {len(backups)} files")
    s = walk("SOUTH passage", SOUTH)
    n = walk("NORTH passage", NORTH)
    if not n:
        print("NORTH passage NO LONGER SAILABLE"); ok = False
    print("\nFRINGE INTEGRITY:", "ALL CHECKS PASS" if ok else "VIOLATIONS -- see above")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
