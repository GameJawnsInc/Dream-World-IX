#!/usr/bin/env python
"""Strip the opening-movie FMV from an opening-field override so a New Game lands in the target field
*instantly*.

FF9's New Game is stock (`fldMapNo = 70`, the opening-FMV field). A custom mod can override field 70
(`EVT_ALEX1_TS_OPENING`) to warp to a custom field (`Field(4003)`) -- but the override still plays the field's
opening `Cinematic` ops (the ~2 s "Garnet on the boat") before the warp. This tool NOPs those pre-warp
cinematics (in place, length-preserving `0x00` -- engine-confirmed "do nothing") so the override flows straight
to its `Field()` warp. **Pure mod, no DLL** -- the whole New-Game-into-a-fork path stays engine-independent.
(Mechanism + verification: memory `project-ff9-new-game-entry`; the kit primitive is `eb.edit.nop_cinematics`.)

Usage:
    py tools/skip_opening_fmv.py                       # auto-find the live opening override (all langs), patch
    py tools/skip_opening_fmv.py --dry-run             # report what WOULD be stripped, write nothing
    py tools/skip_opening_fmv.py <path-to-eb.bytes>... # patch specific .eb file(s)
    py tools/skip_opening_fmv.py --name evt_foo_open   # auto-find a differently-named opening override

Each patched file is backed up to ``backups/<name>.preFMVSKIP.<timestamp>`` first.
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.eb import edit                                   # noqa: E402
from ff9mapkit.config import find_game_path                     # noqa: E402

REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
BK = REPO / "backups"
DEFAULT_NAME = "evt_alex1_ts_opening"   # the field-70 opening override (EVT_ALEX1_TS_OPENING == field id 70)


def _live_overrides(name: str) -> list[Path]:
    """Every per-language copy of ``<name>.eb.bytes`` under the live mod folders (Memoria.ini FolderNames)."""
    game = find_game_path()
    if game is None:
        return []
    hits: list[Path] = []
    for mod in Path(game).glob("FF9CustomMap*"):
        hits += list(mod.rglob(f"{name}.eb.bytes"))
    return sorted(set(hits))


def _strip(path: Path, *, dry_run: bool) -> int:
    """Strip pre-warp cinematics from one ``.eb``. Returns the number of cinematics NOPed (0 = nothing to do)."""
    data = path.read_bytes()
    out, n = edit.nop_cinematics(data)
    if n == 0:
        print(f"  {path.name}: no pre-warp cinematics (already clean / not an opening override)")
        return 0
    if dry_run:
        print(f"  {path.name}: WOULD strip {n} cinematic(s)  [{path}]")
        return n
    BK.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    # include the parent dir (the language folder) so per-language copies never collide on one backup name
    backup = BK / f"{path.parent.name}-{path.name}.preFMVSKIP.{stamp}"
    shutil.copyfile(path, backup)
    path.write_bytes(out)
    print(f"  {path.name}: stripped {n} cinematic(s)  (backup: {backup.name})")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Strip the opening-FMV from an opening-field override.")
    ap.add_argument("paths", nargs="*", help="specific .eb.bytes file(s); omit to auto-find the live override")
    ap.add_argument("--name", default=DEFAULT_NAME, help=f"override base name to auto-find (default {DEFAULT_NAME})")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    targets = [Path(p) for p in args.paths] if args.paths else _live_overrides(args.name)
    if not targets:
        print(f"no targets: pass a path, or ensure a live mod folder contains {args.name}.eb.bytes "
              f"(Memoria.ini FolderNames). Nothing to do.")
        return 1
    print(f"{'[dry-run] ' if args.dry_run else ''}stripping opening FMV from {len(targets)} file(s):")
    total = sum(_strip(p, dry_run=args.dry_run) for p in targets if p.exists())
    missing = [p for p in targets if not p.exists()]
    for p in missing:
        print(f"  MISSING: {p}")
    print(f"done -- {total} cinematic op(s) {'would be ' if args.dry_run else ''}NOPed."
          + ("" if args.dry_run else "  RELAUNCH + New Game to test the instant entry."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
