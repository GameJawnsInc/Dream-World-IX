"""Deploy a junction_compose STAGED TREE into the Path D synthetic namespace (Disc9).

The composer stages a Disc1-shaped tree (``FF9_Data/WorldMap/Disc1/0_1/r{y}/Block[x][y] *``,
meshes + Donor.txt sidecars) and never touches the install. This script re-roots that tree into
the live mod folder under ``Disc9`` -- the s74 sentinel namespace world 9013 resolves overrides
against. The Donor.txt CONTENT stays as staged ("dx,dy" naming a REAL coastal block): s74's
two-disc ``TryReadDonorPath`` reads the sidecar from the Disc9 namespace and resolves the donor
prefab in the real Resources tree, which is exactly the split it exists for.

Refuses if any destination file already exists (an unrelated deploy owns the cell) unless
``--force``. Writes a manifest + a delete-list revert script into the MAIN repo's backups/
(never a worktree path -- see memory project-ff9-worktree-parked-backups).

After deploying, this prints the follow-up steps (coast-nav stamp + gates + the in-game ask).
Nothing here needs a relaunch beyond the usual world re-entry for first-time blocks.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MAIN_REPO = Path(r"C:\gd\Dream-World-IX")
MOD_FOLDER = "FF9CustomMap-world"
DISC = 9


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", help="the staged tree root (contains FF9_Data/WorldMap/Disc1/...)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing destination files (they are backed up first)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stage = Path(args.stage)
    src_root = stage / "FF9_Data" / "WorldMap" / "Disc1"
    if not src_root.is_dir():
        print(f"not a staged tree (no {src_root})", file=sys.stderr)
        return 2
    files = sorted(p for p in src_root.rglob("*") if p.is_file())
    if not files:
        print("staged tree is empty", file=sys.stderr)
        return 2

    ts = time.strftime("%Y%m%d-%H%M%S")
    bdir = MAIN_REPO / "backups" / f"disc9-junction-deploy.{ts}"
    dst_root = GAME / MOD_FOLDER / "FF9_Data" / "WorldMap" / f"Disc{DISC}"
    cells = set()
    plan = []
    collisions = []
    for p in files:
        rel = p.relative_to(src_root)
        m = re.match(r"Block\[(\d+)\]\[(\d+)\]", p.name)
        if m:
            cells.add((int(m.group(1)), int(m.group(2))))
        dst = dst_root / rel
        if dst.exists():
            collisions.append(dst)
        plan.append((p, dst))

    print(f"{len(files)} staged files across {len(cells)} cells -> {dst_root}")
    if collisions and not args.force:
        print(f"REFUSING: {len(collisions)} destination file(s) already exist "
              f"(an unrelated deploy owns the cell?) -- first: {collisions[0]}", file=sys.stderr)
        return 2
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    bdir.mkdir(parents=True, exist_ok=True)
    for dst in collisions:                                   # --force: preserve what we overwrite
        keep = bdir / "overwritten" / dst.relative_to(dst_root)
        keep.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, keep)
    written = []
    for src, dst in plan:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written.append(str(dst))
    manifest = {"stage": str(stage), "deployed": written, "cells": sorted(map(list, cells)),
                "overwrote": [str(c) for c in collisions], "timestamp": ts}
    (bdir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    rv = bdir / "revert_disc9_junction.py"
    rv.write_text(
        "import json, pathlib\n"
        f"m = json.load(open(pathlib.Path(__file__).parent / 'manifest.json'))\n"
        "for f in m['deployed']:\n"
        "    p = pathlib.Path(f)\n"
        "    if p.exists(): p.unlink(); print('removed', p)\n"
        "ow = pathlib.Path(__file__).parent / 'overwritten'\n"
        "if ow.is_dir():\n"
        "    import shutil\n"
        f"    root = pathlib.Path(r'{dst_root}')\n"
        "    for f in ow.rglob('*'):\n"
        "        if f.is_file():\n"
        "            d = root / f.relative_to(ow); d.parent.mkdir(parents=True, exist_ok=True)\n"
        "            shutil.copy2(f, d); print('restored', d)\n",
        encoding="utf-8")
    print(f"deployed {len(written)} files; manifest + revert -> {bdir}")
    xs = sorted(c[0] for c in cells)
    ys = sorted(c[1] for c in cells)
    cellspec = f"{xs[0]}-{xs[-1]},{ys[0]}-{ys[-1]}"
    print("\nNEXT (in order):")
    print(f"  1. py -m ff9mapkit world-coastnav --mod-folder {MOD_FOLDER} --disc {DISC} "
          f"--cells '{cellspec}' --policy cliffs-refuse --deploy  (run from ff9mapkit/; "
          f"pass an explicit backup dir under {MAIN_REPO / 'backups'})")
    print("  2. py studies/path-d-new-world/probe_coastnav_disc9.py  (SEAL/STANDOFF over ALL "
          "Disc9 cells incl. these)")
    print("  3. in game: ~ -> Go -> 9013 -> World -> teleport to the site centre; re-enter the "
          "world for first-time blocks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
