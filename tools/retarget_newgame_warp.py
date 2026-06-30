#!/usr/bin/env python
"""Point the New-Game entry at a custom field id -- retarget the field-70 opening override's ``Field()`` warp.

Thin repo shim over :func:`ff9mapkit.newgame.retarget` (the logic now lives in the package so the installed
``ff9mapkit`` CLI shares it). RE-POINTS an override that already exists (use ``wire_newgame_from_stock.py`` to
CREATE one from stock). Pure mod, no DLL. The target field MUST be registered first (deploy the chain/field),
or New Game warps to an unregistered id = black screen. Mechanism: memory ``project-ff9-new-game-entry``.

Usage:
    py tools/retarget_newgame_warp.py 4100              # field-70 override -> Field(4100), all langs
    py tools/retarget_newgame_warp.py 4100 --from 4003  # pin the current target (else auto-detected)
    py tools/retarget_newgame_warp.py 4100 --dry-run    # report only, write nothing

Backs up to ``backups/<lang>-<name>.preRETARGET.<ts>`` + writes ``tools/scroll_out/revert_newgame_retarget.py``.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import newgame                                # noqa: E402

REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def main() -> int:
    ap = argparse.ArgumentParser(description="Retarget the field-70 New-Game override to a custom field id.")
    ap.add_argument("target", type=int, help="the field id New Game should warp into (the chain's entry id)")
    ap.add_argument("--from", dest="frm", type=int, default=None,
                    help="the override's current target id (default: auto-detected from the override)")
    ap.add_argument("--name", default=newgame.DEFAULT_NAME, help=f"override base name (default {newgame.DEFAULT_NAME})")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    from ff9mapkit.config import find_game_path
    game = find_game_path()
    if game is None or not Path(game).is_dir():
        print("could not find the FF9 install", file=sys.stderr)
        return 2

    res = newgame.retarget(game, args.target, frm=args.frm, name=args.name,
                           backups_dir=REPO / "backups", reverts_dir=REPO / "tools" / "scroll_out",
                           dry_run=args.dry_run)
    if res["found"] == 0:
        return 1
    if res["revert"]:
        print(f"  RELAUNCH + New Game to test. (target {args.target} must be a REGISTERED field -- deploy it first.)")
        print(f"  revert: py {Path(res['revert']).relative_to(REPO).as_posix()}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
