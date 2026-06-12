#!/usr/bin/env python3
"""One-off: remove the stale ORPHANED Dali fork files from the overworld worktree's live mod folder
``FF9CustomMap-ow`` (open follow-up #2). These ``DL_*`` EVT/FBG/mapconfig files are registered NOWHERE in
-ow's DictionaryPatch.txt (leftovers from an earlier overworld Dali experiment), yet -ow is HIGHER priority
than -sf, so they SHADOW the -sf Dali chain's same-named files by the by-name, highest-folder-wins resolution
-> a torn load / black screen (exactly what deploy_campaign's new name-collision guard flags).

REVERSIBLE: every removed file is first moved into ``backups/FF9CustomMap-ow.orphaned-dali.<ts>/`` preserving
its path under the mod folder, and a restore script is written to ``tools/scroll_out/restore_ow_orphans.py``.
Authorized by the user (cross-worktree cleanup of a live deploy folder, not a sibling's source tree).
"""
from __future__ import annotations

import datetime
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / "ff9mapkit"
sys.path.insert(0, str(KIT))
from ff9mapkit.config import find_game_path, ModLayout, LANGS  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OW = "FF9CustomMap-ow"
ORPHAN_NAMES = ["DL_INN", "DL_SHP", "DL_WHL", "VGDL_DL_INN"]   # the unregistered Dali forks


def main() -> int:
    game = find_game_path()
    root = game / OW
    if not root.is_dir():
        print(f"{OW} not found at {root}; nothing to do.")
        return 0
    # SAFETY: refuse to touch any name that IS registered in -ow's DictionaryPatch (would be a live field).
    dp = (root / "DictionaryPatch.txt").read_text(encoding="utf-8", errors="ignore") if (root / "DictionaryPatch.txt").is_file() else ""
    registered = {ln.split()[4] for ln in dp.splitlines() if ln.strip() and len(ln.split()) >= 5}
    live = ModLayout(root)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bk_root = REPO / "backups" / f"{OW}.orphaned-dali.{ts}"

    # collect every concrete path to remove (EVT per lang, FBG scene dir, mapconfig), skipping anything registered
    targets: list[Path] = []
    for name in ORPHAN_NAMES:
        if name in registered:
            print(f"  SKIP {name}: it IS registered in {OW}/DictionaryPatch.txt (live field, not an orphan)")
            continue
        for L in LANGS:
            p = live.eb_path(L, f"EVT_{name}.eb.bytes")
            if p.is_file():
                targets.append(p)
        mc = live.mapconfig_path(f"EVT_{name}")
        if mc.is_file():
            targets.append(mc)
        fbg = live.fieldmap_dir(f"FBG_N11_{name}")
        if fbg.is_dir():
            targets.append(fbg)

    if not targets:
        print("no orphaned Dali files found; nothing to do.")
        return 0

    moved: list[tuple[str, str]] = []   # (backup_abs, original_abs)
    for p in targets:
        rel = p.relative_to(root)
        dst = bk_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dst))          # move = back up + remove in one step (fully reversible)
        moved.append((str(dst), str(p)))
        print(f"  moved {rel}  ->  {dst.relative_to(REPO)}")

    # restore script (move each backup back to its original path)
    so = REPO / "tools" / "scroll_out"
    so.mkdir(parents=True, exist_ok=True)
    lines = [f'"""Restore the {OW} orphaned-Dali files removed {ts} (undo tools/clean_ow_orphans.py)."""',
             "import shutil", "from pathlib import Path", "PAIRS = ["]
    lines += [f"    ({bkp!r}, {orig!r})," for bkp, orig in moved]
    lines += ["]", "for bkp, orig in PAIRS:",
              "    orig = Path(orig); orig.parent.mkdir(parents=True, exist_ok=True)",
              "    shutil.move(bkp, str(orig)); print('restored', orig)",
              f'print("restored {len(moved)} {OW} orphan(s)")', ""]
    rev = so / "restore_ow_orphans.py"
    rev.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"\nremoved {len(moved)} orphaned file(s)/dir(s) from {OW}; backup -> {bk_root.relative_to(REPO)}")
    print(f"restore: py {rev.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
