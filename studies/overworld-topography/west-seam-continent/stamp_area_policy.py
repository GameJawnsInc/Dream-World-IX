"""R3 -- THE SAFE-ROAD AREA STAMP for the west-seam continent (area 14, the R4b precedent).

THE TABLE IS THE LAW (southern-ring REVERT.md section 26): encounters resolve zone x topograph x
fog off the WALKED TILE's area bits, and safety is a TABLE HOLE. Area 14 -> zone 6, whose only
records are topos 10/36 -- a hole for every topograph our open ground carries. The rule, per
Terrain vert-tangent on the continent's 26 blocks x BOTH discs (52 files):

    event == 0 AND topo in {36,37,38}  -> area := 0    (canopy: zone 0 = Python/Goblin/Mu --
                                                        undoes any donor-imported area after the
                                                        R6 forest carries; a no-op until then)
    event == 0 AND topo not in {36,37,38} -> area := 14 (zone 6's hole = no encounters)
    event != 0                          -> UNTOUCHED   (the R2 entrance tiles survive byte-for-byte)

Pure bit surgery on the area field (idall bits 8-13, extract.encode_id) applied to the raw
tangent.x floats in place -- topo/event/flags and every other byte of the file are preserved BY
CONSTRUCTION, not by promise. Idempotent: a second run changes zero bytes. RE-RUN THIS after
every later terrain-writing rung (R4-R7 re-emit whole blocks at kit-default area 0).

Writes: a pre-stamp backup of every file it will touch into the MAIN repo's backups/ (undo =
restore it), then the stamped bytes, then a deploy-ledger row per changed file
(record_ledger_write -- an in-place rewrite of a deployed override MUST ledger, or the next
deploy_override at that cell refuses our own bytes as foreign; the fix_triangle lesson).

    py stamp_area_policy.py --dry-run     # report only
    py stamp_area_policy.py               # backup + stamp + ledger, both discs

Verify afterwards:  py probe_area14.py
"""
from __future__ import annotations

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

G = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX") \
    / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
BACKUP_ROOT = REPO / "backups" / "west-seam-continent"

# the R1 mint's 26 blocks (PLAN.md; wrapped cols {21,22,23,0,1} x rows 4-9)
BLOCKS = [(0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (1, 5), (1, 6), (1, 7), (1, 8),
          (21, 5), (21, 6), (21, 7), (21, 8), (22, 4), (22, 5), (22, 6), (22, 7), (22, 8),
          (22, 9), (23, 4), (23, 5), (23, 6), (23, 7), (23, 8), (23, 9)]

ENC = {36, 37, 38}
SAFE_AREA = 14
AREA_MASK = 0x3F << 8                                      # extract.encode_id: area = bits 8-13


def tangent_x_offset(data: bytes):
    """Byte offset of tangent[0].x + the per-vert stride, from the header (mesh.read_ff9mesh's
    layout: 20B header, verts 12B/v, then normals/uvs/tangents per the flags bits)."""
    if data[:4] != b"F9WM":
        raise SystemExit("not a .ff9mesh (bad magic)")
    _, vcount, _, flags = struct.unpack_from("<iiii", data, 4)
    off = 20 + vcount * 12
    if flags & 1:
        off += vcount * 12
    if flags & 2:
        off += vcount * 8
    if not flags & 4:
        raise SystemExit("terrain mesh without tangents?!")
    return off, vcount


def stamp_file(path: Path, *, write: bool):
    data = bytearray(path.read_bytes())
    base, vcount = tangent_x_offset(data)
    n_safe = n_canopy = n_event = 0
    changed = 0
    for i in range(vcount):
        o = base + i * 16
        idall = int(round(struct.unpack_from("<f", data, o)[0]))
        event = (idall >> 14) & 3
        topo = (idall >> 2) & 0x3F
        area = (idall >> 8) & 0x3F
        if event:
            n_event += 1
            continue
        want = 0 if topo in ENC else SAFE_AREA
        if topo in ENC:
            n_canopy += 1
        else:
            n_safe += 1
        if area != want:
            changed += 1
            if write:
                struct.pack_into("<f", data, o, float((idall & ~AREA_MASK) | (want << 8)))
    if write and changed:
        path.write_bytes(bytes(data))
    return changed, n_safe, n_canopy, n_event, vcount


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="report; write nothing")
    a = ap.parse_args()

    files = []
    for disc in (1, 4):
        for bx, by in BLOCKS:
            p = G / f"Disc{disc}" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
            if not p.is_file():
                raise SystemExit(f"MISSING deployed Terrain: {p} -- the R1 mint should own it")
            files.append((disc, bx, by, p))
    print(f"{len(files)} Terrain files across both discs")

    bak = None
    if not a.dry_run:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = BACKUP_ROOT / f"r3-pre-area14.{stamp}"
        for disc, bx, by, p in files:
            d = bak / f"Disc{disc}"
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, d / f"r{by}_{p.name}")
        print(f"pre-stamp backup -> {bak}")

    tot_changed = tot_safe = tot_canopy = tot_event = 0
    for disc, bx, by, p in files:
        changed, n_safe, n_canopy, n_event, vcount = stamp_file(p, write=not a.dry_run)
        tot_changed += changed
        tot_safe += n_safe
        tot_canopy += n_canopy
        tot_event += n_event
        if changed and not a.dry_run:
            M.record_ledger_write(p, cell=(bx, by), part="Terrain", write_disc=disc)
        if changed:
            print(f"  Disc{disc} ({bx:2},{by}) : {changed:5} verts stamped  "
                  f"(open {n_safe}, canopy {n_canopy}, event {n_event})")

    verb = "would stamp" if a.dry_run else "stamped"
    print(f"\n{verb} {tot_changed} verts across {len(files)} files "
          f"(open-ground {tot_safe}, canopy-kept {tot_canopy}, event-kept {tot_event})")
    if not a.dry_run:
        print(f"undo: restore {bak}  (area bits only -- the probe's invariant d proves it)")
        print("verify: py probe_area14.py")


if __name__ == "__main__":
    main()
