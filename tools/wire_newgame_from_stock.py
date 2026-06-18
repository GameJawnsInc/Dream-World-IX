#!/usr/bin/env python3
"""Create the field-70 New-Game override FROM STOCK and point it at a custom entry id -- PURE MOD, no DLL.

FF9's New Game is stock (`fldMapNo = 70`, EVT_ALEX1_TS_OPENING -- the theater-ship opening: BGM + intro FMV +
fade-to-black, ending in `Field(50)` to Prima Vista). A mod overrides field 70's `.eb` so its terminal `Field()`
lands on a custom entry instead. The existing drivers (`retarget_newgame_warp.py`, `newgame_warp.py`) only PATCH
an override that already exists -- but `deploy_campaign` WHOLESALE-REPLACES FF9CustomMap, so after a fresh
campaign deploy NO override exists and New Game boots the stock opening, not the fork. This tool fills that gap:
it extracts STOCK field 70 from p0data, repoints its `Field(<stock-dest>)` -> `Field(<target>)` (a 2-byte
length-preserving literal swap via the proven `content.verbatim.remap_fields`), and writes the override into the
mod folder for all 7 languages. The field-70 opening (FMV + fade) is PRESERVED -> New Game plays the faithful
intro, then warps into the fork (run `tools/skip_opening_fmv.py` afterward for a seamless no-FMV boot instead).

Field 70's `.eb` bytecode is language-identical (per-lang files differ only in the cosmetic 84-byte name, which
the engine ignores -- it loads by filename), so the one remapped script is written to all 7 lang paths (mirrors
how verbatim forks ship their `.eb`). No DictionaryPatch needed: field 70 is stock-registered; we only shadow its
script with a higher-priority `.eb`. The target MUST be a registered field (deploy the chain first) or New Game
warps to an unregistered id = black screen.

Usage:
    py tools/wire_newgame_from_stock.py 6000                 # New Game -> field 70 (faithful) -> Field(6000)
    py tools/wire_newgame_from_stock.py 6000 --mod-folder FF9CustomMap
    py tools/wire_newgame_from_stock.py 6000 --dry-run       # report only, write nothing

Reversible: writes tools/scroll_out/revert_newgame_from_stock.py (deletes the override / restores any prior copy).
Pairs with retarget_newgame_warp.py (re-point an already-created override) + skip_opening_fmv.py (strip the FMV).
Mechanism: memory project-ff9-new-game-entry.
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
from ff9mapkit import extract                                # noqa: E402
from ff9mapkit.config import find_game_path                  # noqa: E402
from ff9mapkit.content.verbatim import remap_fields, FIELD_OP   # noqa: E402
from ff9mapkit.eb import EbScript                            # noqa: E402

REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
BK = REPO / "backups"
SCROLL_OUT = Path(__file__).resolve().parent / "scroll_out"
LANGS = ["us", "uk", "fr", "gr", "it", "es", "jp"]
OVERRIDE_REL = ("StreamingAssets/assets/resources/commonasset/eventengine/"
                "eventbinary/field/{lang}/evt_alex1_ts_opening.eb.bytes")
NEWGAME_FIELD = 70   # stock New Game -> fldMapNo 70 (EVT_ALEX1_TS_OPENING)


def _stock_field_target(data: bytes) -> int | None:
    """The stock opening's destination: the first Field() warp in entry-0's Main_Init (tag 0)."""
    s = EbScript.from_bytes(data)
    f0 = s.entry(0).func_by_tag(0)
    if f0 is None:
        return None
    for ins in s.instrs(f0):
        if ins.op == FIELD_OP:
            return ins.imm(0)
    return None


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

    # (1) extract STOCK field 70 + find its current destination (expect Field(50) -> Prima Vista)
    data = extract.EventBundle(game=str(game)).eb_for_id(NEWGAME_FIELD)
    if not data:
        print(f"could not extract stock field {NEWGAME_FIELD} .eb from p0data", file=sys.stderr)
        return 2
    stock_dest = _stock_field_target(data)
    if stock_dest is None:
        print(f"stock field {NEWGAME_FIELD} has no Field() warp in Main_Init -- cannot wire", file=sys.stderr)
        return 2
    if stock_dest == args.target:
        print(f"stock field {NEWGAME_FIELD} already warps Field({args.target}); writing it verbatim as the override")
        out = data
    else:
        out = remap_fields(data, {stock_dest: args.target})
        if out == data:
            print(f"Field({stock_dest}) not found to patch (unexpected)", file=sys.stderr)
            return 2

    # verify the result
    new_dest = _stock_field_target(out)
    print(f"field {NEWGAME_FIELD} override: Field({stock_dest}) -> Field({new_dest})   "
          f"(New Game -> field {NEWGAME_FIELD} opening [FMV+fade preserved] -> Field({args.target}))")
    if new_dest != args.target:
        print("  verification FAILED: override does not warp to the target", file=sys.stderr)
        return 2

    paths = [Path(game) / args.mod_folder / OVERRIDE_REL.format(lang=L) for L in LANGS]
    if args.dry_run:
        print(f"[dry-run] WOULD write the override to {len(paths)} lang path(s) under {args.mod_folder}:")
        for p in paths:
            print(f"    {p}")
        return 0

    # (2) write to all 7 langs; back up any prior copy; record a revert
    BK.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    revert_pairs: list[tuple[str, str | None]] = []   # (live_path, backup_path_or_None=delete)
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_file():
            bkp = BK / f"{p.parent.name}-{p.name}.preWIRE.{stamp}"
            shutil.copyfile(p, bkp)
            revert_pairs.append((str(p), str(bkp)))
        else:
            revert_pairs.append((str(p), None))         # no prior -> revert deletes it
        p.write_bytes(out)
        print(f"  wrote {p.parent.name}/{p.name}  ({len(out)} bytes)")

    SCROLL_OUT.mkdir(exist_ok=True)
    rl = ['"""Revert the from-stock New-Game wiring: restore/delete the field-70 override copies."""',
          "import os, shutil", "PAIRS = ["]
    rl += [f"    ({live!r}, {bkp!r})," for live, bkp in revert_pairs]
    rl += ["]", "for live, bkp in PAIRS:",
           "    if bkp: shutil.copyfile(bkp, live); print('restored', live)",
           "    elif os.path.isfile(live): os.remove(live); print('removed', live)",
           f"print('reverted newgame-from-stock {stamp}')", ""]
    rev = SCROLL_OUT / "revert_newgame_from_stock.py"
    rev.write_text("\n".join(rl), encoding="utf-8")

    print(f"\nNew Game -> field {NEWGAME_FIELD} -> Field({args.target}).  RELAUNCH + New Game to test "
          f"(target {args.target} must be REGISTERED -- deploy the chain first).")
    print(f"  revert: py {rev.relative_to(REPO).as_posix()}")
    print(f"  seamless (skip the intro FMV): py tools/skip_opening_fmv.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
