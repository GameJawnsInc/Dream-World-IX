"""R3 -- verify THE SAFE-ROAD AREA STAMP on the west-seam continent (the R4b probe, re-scoped).

Read-only. Invariants (the southern-ring probe_area14_stamp.py battery, against the newest
pre-stamp backup stamp_area_policy.py parked):

  (a) NON-event, NON-canopy verts carry area 14 -- all 26 blocks, both discs;
  (b) canopy verts (topo 36/37/38) carry area 0;
  (c) EVENT verts are byte-identical to the pre-stamp backup (the R2 entrance survives);
  (d) the stamp changed ONLY area bits (topo/event/flags identical to the backup, and every
      non-tangent byte of every file identical);
  (e) Disc1/Disc4 parity of the area bits (NOT whole-file parity: the R2 entrance edits Disc1's
      (1,6) beacon block ahead of its mirror -- parity there is the mirror's job, not the stamp's).

Exits non-zero on any violation.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from stamp_area_policy import BLOCKS, ENC, G, SAFE_AREA, tangent_x_offset  # noqa: E402

BACKUP_ROOT = REPO / "backups" / "west-seam-continent"


def decode_all(path: Path):
    data = path.read_bytes()
    base, vcount = tangent_x_offset(data)
    out = []
    for i in range(vcount):
        idall = int(round(struct.unpack_from("<f", data, base + i * 16)[0]))
        out.append(((idall >> 14) & 3, (idall >> 8) & 0x3F, (idall >> 2) & 0x3F, idall & 3))
    return data, base, out                                  # (event, area, topo, flags) per vert


def main() -> int:
    baks = sorted(BACKUP_ROOT.glob("r3-pre-area14.*"))
    if not baks:
        print("no pre-stamp backup found -- run stamp_area_policy.py first")
        return 2
    bak = baks[-1]
    print(f"backup: {bak.name}")

    viol = []
    n_open = n_canopy = n_event = 0
    areas = {}
    for disc in (1, 4):
        for bx, by in BLOCKS:
            p = G / f"Disc{disc}" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
            data, base, cur = decode_all(p)
            pre_p = bak / f"Disc{disc}" / f"r{by}_{p.name}"
            pre_data, _, pre = decode_all(pre_p)
            if len(cur) != len(pre):
                viol.append(f"({bx},{by}) d{disc}: vcount changed?!")
                continue
            # (d) every non-tangent byte identical + per-vert non-area fields identical
            if data[:base] != pre_data[:base] or data[base + len(cur) * 16:] != pre_data[base + len(cur) * 16:]:
                viol.append(f"({bx},{by}) d{disc}: bytes OUTSIDE the tangent block changed")
            for i, ((ev, ar, tp, fl), (pev, par, ptp, pfl)) in enumerate(zip(cur, pre)):
                if (ev, tp, fl) != (pev, ptp, pfl):
                    viol.append(f"({bx},{by}) d{disc} v{i}: non-area field changed "
                                f"({pev},{ptp},{pfl}) -> ({ev},{tp},{fl})")
                # also the tangent's yzw floats must be untouched
                o = base + i * 16
                if data[o + 4:o + 16] != pre_data[o + 4:o + 16]:
                    viol.append(f"({bx},{by}) d{disc} v{i}: tangent yzw changed")
                if ev:
                    n_event += 1
                    if data[o:o + 16] != pre_data[o:o + 16]:
                        viol.append(f"({bx},{by}) d{disc} v{i}: EVENT vert not byte-identical")
                elif tp in ENC:
                    n_canopy += 1
                    if ar != 0:
                        viol.append(f"({bx},{by}) d{disc} v{i}: canopy topo {tp} area {ar} != 0")
                else:
                    n_open += 1
                    if ar != SAFE_AREA:
                        viol.append(f"({bx},{by}) d{disc} v{i}: open topo {tp} area {ar} != {SAFE_AREA}")
            areas[(disc, bx, by)] = [a for (_, a, _, _) in cur]

    # (e) area-bit parity across discs
    for bx, by in BLOCKS:
        if areas[(1, bx, by)] != areas[(4, bx, by)]:
            viol.append(f"({bx},{by}): Disc1/Disc4 AREA bits differ")

    print(f"verts: open {n_open}  canopy {n_canopy}  event {n_event}")
    if viol:
        print(f"\n{len(viol)} VIOLATION(S):")
        for v in viol[:20]:
            print("  ", v)
        return 1
    print("ALL CHECKS PASS (a-e)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
