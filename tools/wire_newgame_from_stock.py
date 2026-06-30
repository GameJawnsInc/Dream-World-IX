#!/usr/bin/env python3
"""Create the field-70 New-Game override FROM STOCK and point it at a custom entry id -- PURE MOD, no DLL.

Thin repo shim over :func:`ff9mapkit.newgame.wire_from_stock` (the logic now lives in the package so the
installed ``ff9mapkit`` CLI shares it). This wrapper just supplies the repo-flavored backup/revert dirs
(``backups/`` + ``tools/scroll_out/``) and the REPO-relative revert hint. The field-70 opening (FMV + fade)
is PRESERVED -> New Game plays the faithful intro, then warps into the fork. The target MUST be a registered
field (deploy the chain first) or New Game warps to an unregistered id = black screen.

Usage:
    py tools/wire_newgame_from_stock.py 6000                 # New Game -> field 70 (faithful) -> Field(6000)
    py tools/wire_newgame_from_stock.py 6000 --mod-folder FF9CustomMap
    py tools/wire_newgame_from_stock.py 6000 --dry-run       # report only, write nothing

Reversible: writes tools/scroll_out/revert_newgame_from_stock.py. Mechanism: memory project-ff9-new-game-entry.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import newgame                                # noqa: E402
from ff9mapkit.config import find_game_path                  # noqa: E402

REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def main() -> int:
    ap = argparse.ArgumentParser(description="Create the field-70 New-Game override from stock and point it at an id.")
    ap.add_argument("target", type=int, help="the entry field id New Game should warp into (e.g. the chain entry)")
    ap.add_argument("--mod-folder", default="FF9CustomMap", help="mod folder to install the override into (default FF9CustomMap)")
    ap.add_argument("--game", default=None, help="game install path (default: auto-detect)")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    game = Path(args.game) if args.game else find_game_path()
    if game is None or not Path(game).is_dir():
        print("could not find the FF9 install (pass --game)", file=sys.stderr)
        return 2

    res = newgame.wire_from_stock(game, args.target, mod_folder=args.mod_folder,
                                  backups_dir=REPO / "backups", reverts_dir=REPO / "tools" / "scroll_out",
                                  dry_run=args.dry_run)
    if res["revert"]:
        print(f"  revert: py {Path(res['revert']).relative_to(REPO).as_posix()}")
        print(f"  seamless (skip the intro FMV): py tools/skip_opening_fmv.py")
    return 0 if res["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
