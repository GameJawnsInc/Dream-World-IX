#!/usr/bin/env python
"""Point the New-Game entry at a custom field id -- retarget the field-70 opening override's ``Field()`` warp.

FF9's New Game is stock (`fldMapNo = 70`, the opening field). A mod overrides field 70 (`EVT_ALEX1_TS_OPENING`)
to warp `Field(<id>)` instead of the stock destination -- the single-field capstone hand-authored that to 4003.
A forked CHAIN (or any campaign) lands its entry member on a DIFFERENT id, so the override's `Field()` literal
must be repointed at that id. This driver does exactly that: it rewrites the override's `Field()` destination in
place (a 2-byte literal, length-preserving) via the proven `content.verbatim.remap_fields`, across all 7 langs.
**Pure mod, no DLL** -- the whole New-Game-into-a-fork path stays engine-independent.

Pairs with `tools/skip_opening_fmv.py` (strip the opening FMV; they edit disjoint bytes, run order-independent).
The target field MUST be registered first (deploy the chain/field), or New Game warps to an unregistered id =
black screen. (Mechanism: memory `project-ff9-new-game-entry`; the kit lever is `verbatim.remap_fields`.)

★ The New-Game override is SINGLE-OWNER. For a standalone capstone test this tool points field-70 -> your slice.
A World Hub instead owns field-70 (-> the hub) and warps into the slice from a hub door -- in that case you do
NOT run this tool; the slice still self-seeds (its `[startup]`/`[party]` are baked into its `.eb`).

Usage:
    py tools/retarget_newgame_warp.py 4100              # field-70 override -> Field(4100), all langs
    py tools/retarget_newgame_warp.py 4100 --from 4003  # pin the current target (else auto-detected)
    py tools/retarget_newgame_warp.py 4100 --dry-run    # report only, write nothing

Each patched file is backed up to ``backups/<lang>-<name>.preRETARGET.<timestamp>`` and a revert script is
written to ``tools/scroll_out/revert_newgame_retarget.py``.
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
from ff9mapkit.config import find_game_path                # noqa: E402
from ff9mapkit.content.verbatim import remap_fields, FIELD_OP   # noqa: E402
from ff9mapkit.eb import EbScript                          # noqa: E402

REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
BK = REPO / "backups"
SCROLL_OUT = Path(__file__).resolve().parent / "scroll_out"
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


def _current_target(data: bytes) -> int | None:
    """The override's live New-Game destination: the first ``Field()`` warp in entry-0's Main_Init (tag 0)."""
    s = EbScript.from_bytes(data)
    f0 = s.entry(0).func_by_tag(0)
    if f0 is None:
        return None
    for ins in s.instrs(f0):
        if ins.op == FIELD_OP:
            return ins.imm(0)
    return None


def _retarget(path: Path, target: int, frm: int | None, *, dry_run: bool) -> tuple[int, int | None]:
    """Retarget one override copy. Returns (n_files_changed 0|1, the old id detected)."""
    data = path.read_bytes()
    old = frm if frm is not None else _current_target(data)
    if old is None:
        print(f"  {path.name}: no Field() warp in Main_Init -- not an opening override; skipped  [{path}]")
        return 0, None
    if old == target:
        print(f"  {path.name}: already warps Field({target}) -- nothing to do")
        return 0, old
    out = remap_fields(data, {old: target})
    if out == data:
        print(f"  {path.name}: Field({old}) not found to patch (unexpected); skipped")
        return 0, old
    if dry_run:
        print(f"  {path.name}: WOULD retarget Field({old}) -> Field({target})  [{path}]")
        return 1, old
    BK.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BK / f"{path.parent.name}-{path.name}.preRETARGET.{stamp}"   # parent (lang) dir avoids name collisions
    shutil.copyfile(path, backup)
    path.write_bytes(out)
    print(f"  {path.name}: Field({old}) -> Field({target})  (backup: {backup.name})")
    return 1, old


def _write_revert(backups: list[tuple[str, str]], stamp: str) -> Path:
    SCROLL_OUT.mkdir(exist_ok=True)
    lines = ['"""Revert the New-Game retarget: restore the field-70 override backups."""',
             "import shutil", "PAIRS = ["]
    lines += [f"    ({live!r}, {bkp!r})," for live, bkp in backups]
    lines += ["]", "for live, bkp in PAIRS:", "    shutil.copyfile(bkp, live); print('restored', live)",
              f"print('reverted newgame retarget {stamp}')", ""]
    p = SCROLL_OUT / "revert_newgame_retarget.py"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Retarget the field-70 New-Game override to a custom field id.")
    ap.add_argument("target", type=int, help="the field id New Game should warp into (the chain's entry id)")
    ap.add_argument("--from", dest="frm", type=int, default=None,
                    help="the override's current target id (default: auto-detected from the override)")
    ap.add_argument("--name", default=DEFAULT_NAME, help=f"override base name (default {DEFAULT_NAME})")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    targets = _live_overrides(args.name)
    if not targets:
        print(f"no live override found: ensure a mod folder contains {args.name}.eb.bytes "
              f"(Memoria.ini FolderNames). Nothing to do.")
        return 1
    print(f"{'[dry-run] ' if args.dry_run else ''}retargeting New Game -> Field({args.target}) "
          f"in {len(targets)} override file(s):")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    BK.mkdir(exist_ok=True)
    changed, backups = 0, []
    for p in targets:
        before = p.read_bytes() if p.exists() else None
        n, _old = _retarget(p, args.target, args.frm, dry_run=args.dry_run)
        changed += n
        if n and not args.dry_run and before is not None:
            # the backup name is deterministic per file -- recover it for the revert manifest
            bname = next((b.name for b in BK.glob(f"{p.parent.name}-{p.name}.preRETARGET.*")), None)
            if bname:
                backups.append((str(p), str(BK / bname)))
    rev = _write_revert(backups, stamp) if backups else None
    print(f"done -- {changed} override(s) {'would be ' if args.dry_run else ''}retargeted to Field({args.target}).")
    if not args.dry_run and changed:
        print(f"  RELAUNCH + New Game to test. (target {args.target} must be a REGISTERED field -- deploy it first.)")
        if rev:
            print(f"  revert: py {rev.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
