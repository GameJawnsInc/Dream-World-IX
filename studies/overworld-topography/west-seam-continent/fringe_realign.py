"""R4 take 7, move 2 -- THE FRINGE RE-ALIGN: the SW arc's high course drops its green
tufty transition tiles (r6 c4-7, lawful only against a VISIBLE grass contact; the bowl
terrace above is hidden from the lawn) for the pale ladder rock (r7 c6-9). Whole-tile UV
translation (u += 2*TILE_U, v += TILE_V) preserving every fractional inset; geometry,
topo, normals untouched. SHOULDER-HEURISTICS.md addendum is the license.

    py fringe_realign.py --dry-run
    py fringe_realign.py
"""
import argparse
import datetime
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import mesh as M                      # noqa: E402

WM = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX") \
    / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
BLOCKS = [(22, 6), (22, 7), (23, 6), (23, 7)]
WINDOW = (1412.0, -492.0, 1442.0, -460.0)
TU, TV, PU, PV = 0.0625, 0.03125, 0.015625, 0.01953125


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    edits = {}
    for bx, by in BLOCKS:
        p = WM / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        d = bytearray(p.read_bytes())
        _, vc, _, fl = struct.unpack_from("<iiii", d, 4)
        off = 20 + vc * 12 + (vc * 12 if fl & 1 else 0)
        uo, to = off, off + vc * 8
        n = 0
        for t in range(vc // 3):
            i = t * 3
            idall = int(round(struct.unpack_from("<f", d, to + i * 16)[0]))
            if (idall >> 2) & 0x3F != 49:
                continue
            vs = [struct.unpack_from("<fff", d, 20 + (i + k) * 12) for k in range(3)]
            cx = bx * 64 + sum(v[0] for v in vs) / 3
            cz = sum(v[2] for v in vs) / 3 - by * 64
            if not (WINDOW[0] <= cx <= WINDOW[2] and WINDOW[1] <= cz <= WINDOW[3]):
                continue
            us = [struct.unpack_from("<ff", d, uo + (i + k) * 8) for k in range(3)]
            uc = sum(u[0] for u in us) / 3
            vcen = sum(u[1] for u in us) / 3
            row, col = int((vcen - PV) / TV), int((uc - PU) / TU)
            if row == 6 and col in (4, 5, 6, 7):
                # whole-tile translation, then CLAMP into the target tile rect: the r6
                # course's tuft overshoot pokes past the band after translation and
                # samples Moguri's transparent gutters (white streaks -- caught by the
                # offline eye). Edge-TOUCHING is safe per the Moguri-gutter law.
                tc = col + 2
                # clamp into the MEASURED PAINTED extent of the target tile (Moguri
                # r7c6 is painted from u 0.392578, 4px inside its grid edge), inset by
                # 0.75 texel so bilinear never touches a transparent neighbor
                DU, DV = 0.75 / 2048.0, 0.75 / 4096.0
                u_lo = (0.392578 if tc == 6 else PU + tc * TU) + DU
                u_hi = PU + (tc + 1) * TU - DU
                v_lo, v_hi = PV + 7 * TV + DV, PV + 8 * TV - DV
                if not a.dry_run:
                    for k in range(3):
                        nu = min(u_hi, max(u_lo, us[k][0] + 2 * TU))
                        nv = min(v_hi, max(v_lo, us[k][1] + TV))
                        struct.pack_into("<ff", d, uo + (i + k) * 8, nu, nv)
                n += 1
        if n:
            edits[(bx, by)] = (bytes(d), n)
    print({k: v[1] for k, v in edits.items()}, "tris r6c4-7 -> r7c6-9")
    if a.dry_run:
        print("DRY RUN")
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = REPO / "backups" / "west-seam-continent" / f"fringe-realign-pre.{stamp}"
    for (bx, by), (raw, n) in sorted(edits.items()):
        p1 = WM / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        p4 = WM / "Disc4" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        assert p1.read_bytes() == p4.read_bytes(), f"parity broken pre-edit at {(bx, by)}"
        for d_, p in ((1, p1), (4, p4)):
            bdir = bak / f"Disc{d_}"
            bdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, bdir / p.name)
            p.write_bytes(raw)
            M.record_ledger_write(p, cell=(bx, by), part="Terrain", write_disc=d_)
        print(f"  {(bx, by)}: {n} tris, both discs, ledgered")
    print(f"backup -> {bak}")


if __name__ == "__main__":
    main()
