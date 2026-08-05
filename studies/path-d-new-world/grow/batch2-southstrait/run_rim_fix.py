#!/usr/bin/env python
"""run_rim_fix.py -- terminate the horseshoe carry's cropped shallow rim (Disc9 blocks 5-7 x 10-11).

WHY THIS SCRIPT AND NOT THE PLAIN CLI
-------------------------------------
`world-rim-retile --cells 5-7,10-11 --donor 5,15 --size 3x2` REFUSED with
``deep-set(s) ['EW', 'NS', 'NSW'] have no verbatim donor tile``. Two independent causes, both now
diagnosed against stock bytes:

* **NSW** -- a HARVEST-POOL defect, not a stock gap. Stock disc 1 ships 104 NSW tiles across 60
  blocks, and all six carry donors contain one; but ``harvest_variants`` (rimretile.py:118-123)
  DROPS a variant whose pooled instances disagree by >1e-4, and donor (5,16) cell (5,6) carries an
  NSW tile whose v-rect is offset by half a texel (0.503937 vs 0.496063) from the other seven. One
  outlier annihilates the whole variant. Fix: harvest from **(7,15) alone** -- the one carry donor
  that holds ALL 16 variants self-consistently. Widening the pool is the WRONG direction: a harvest
  over all 140 stock sea5 blocks yields ZERO variants.
* **EW / NS** -- structurally unrepresentable: they are not keys of ``water.DEEPSET2TILE``
  (water.py:75-80) at all. Handled by THE OPPOSITE-PINCH RULE now in ``rimretile.representable``
  (rimretile.py, after ``deepset``), which folds an opposite pinch onto the containing 3-deep tile
  exactly as stock does at all 5 of its own EW pinches.

WHAT IT WRITES
--------------
Only ``Sea3``/``Sea5`` meshes of the six cells (proven sea-only on a scratch copy: Terrain and
Donor.txt byte-identical, Sea4 byte-identical). The module also drops a ``.ff9mesh.prerim`` beside
each file and ledgers the in-place write.

USAGE
-----
    py run_rim_fix.py              # dry run (default) -- reads only, prints the report
    py run_rim_fix.py --write      # back up to C:\\gd\\Dream-World-IX\\backups\\ then write

RELAUNCH (or exit + re-enter the overworld) after --write; then playtest the rim.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

KIT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a\ff9mapkit")
BACKUP_ROOT = Path(r"C:\gd\Dream-World-IX\backups")
MOD_FOLDER = "FF9CustomMap-world"
CELLS = [(bx, by) for by in (10, 11) for bx in (5, 6, 7)]
DONORS = [(7, 15)]                      # NOT the 3x2 rect -- see the module docstring above
DISC, TARGET_DISC, LOD = 1, 9, "0_1"
PARTS = ("Sea3", "Sea4", "Sea5", "Terrain")

sys.path.insert(0, str(KIT))


def _root(game):
    from ff9mapkit import config
    return (config.find_game_path(game) / MOD_FOLDER / "FF9_Data" / "WorldMap"
            / f"Disc{TARGET_DISC}" / LOD)


def backup(game) -> Path:
    """Snapshot every touched cell into the MAIN repo's backups/ (worktree-parked backups vanish
    with the worktree -- project-ff9-worktree-parked-backups)."""
    root = _root(game)
    dest = BACKUP_ROOT / f"rim-retile-disc9-5to7x10to11-{datetime.now():%Y%m%d-%H%M%S}"
    n = 0
    for (bx, by) in CELLS:
        for part in PARTS + ("Donor",):
            ext = ".txt" if part == "Donor" else ".ff9mesh"
            src = root / f"r{by}" / f"Block[{bx}][{by}] {part}{ext}"
            if src.exists():
                out = dest / f"r{by}"
                out.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out / src.name)
                n += 1
    print(f"  backed up {n} file(s) -> {dest}")
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="actually write (default is a dry run that touches nothing)")
    ap.add_argument("--dry-run", action="store_true", help="explicit no-op default")
    ap.add_argument("--game", default=None, help="FF9 install path override")
    args = ap.parse_args(argv)
    apply = bool(args.write) and not args.dry_run

    from ff9mapkit.world import rimretile as RR

    print(f"rim-retile  cells={CELLS}")
    print(f"            donors={DONORS}  disc={DISC} -> target_disc={TARGET_DISC}")
    print(f"            mod_folder={MOD_FOLDER}  mode={'WRITE' if apply else 'DRY RUN'}")
    if apply:
        backup(args.game)

    rep = RR.rim_retile(MOD_FOLDER, CELLS, DONORS, disc=DISC, target_disc=TARGET_DISC,
                        lod=LOD, game=args.game, apply=apply)
    if rep.get("refused"):
        print(f"REFUSED: {rep['refused']}")
        return 1
    b, a = rep["before"], rep["after"]
    print(f"  {rep['variants']} verbatim donor variants; passes={rep['passes']} "
          f"({rep['quads']} quad re-tiles)")
    print(f"  HARD SEAMS (uv under-covers the deep it faces): {b['under']} -> {a['under']}")
    print(f"  soft over-cover (a transition facing shallow):  {b['over']} -> {a['over']}"
          f"   of {a['tiles']} rim tiles")
    if a["under"]:
        print("  !! WARNING: hard seams remain -- review in-game before shipping")
    if rep.get("dry_run"):
        print("  dry run -- nothing written")
        return 0

    # post-write gate: re-read every file from disk and run the engine's own loader predicates
    import re
    from ff9mapkit.world import mesh as M
    bad = []
    for p in rep["written"]:
        p = Path(p)
        m = re.match(r"Block\[(\d+)\]\[(\d+)\] (\w+)", p.stem)
        bx, by, part = int(m.group(1)), int(m.group(2)), m.group(3).lower()
        try:
            bm = M.blockmesh_from_ff9mesh(str(p), disc=TARGET_DISC, x=bx, y=by, lod=LOD, part=part)
            M.validate_blockmesh(bm)
        except Exception as e:                                  # noqa: BLE001
            bad.append((p.name, str(e)))
    print(f"  wrote {len(rep['written'])} file(s); .prerim backups kept")
    print(f"  validate_blockmesh on re-read: {'FAILED ' + str(bad) if bad else 'PASS (all files)'}")
    non_sea = [Path(p).name for p in rep["written"] if "Sea" not in Path(p).name]
    print(f"  non-Sea files written: {non_sea or 'NONE -- sea-only edit'}")
    print("  RELAUNCH (or exit + re-enter the overworld) to load, then playtest the rim.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
