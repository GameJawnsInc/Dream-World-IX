#!/usr/bin/env python3
"""Install the two-room demo (GROTTO 4004 + TRENO_RES 4005) PERMANENTLY into the live FF9CustomMap,
wiping the old hut rooms (HUT_EXT 4000 / HUT_INT 4002), the 4003 TESTROOM dev sandbox, and the
leftover ROOM01_BASE art. BG-borrow fields ship only their EVT script (the engine renders the real
borrowed field's art/walkmesh/camera), so install = drop the EVTs + set DictionaryPatch to the two
new lines.

This is the multi-field PERMANENT install the kit lacks a first-class command for: deploy_field.py
only sandboxes ONE field into the 4003 slot, so a coexisting connected pair needs this.

Fully reversible: snapshots the entire FF9CustomMap first and writes a one-command full-restore at
tools/scroll_out/revert_tworoom.py (rmtree + restore the snapshot -- undoes the field swap AND any
warp repoint done afterward).

After running:  py tools/newgame_warp.py 4004 --stock   (point New Game at the grotto)
"""
import datetime
import os
import shutil
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.config import LANGS, ModLayout, find_game_path  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "tworoom" / "dist"
NEW_FIELDS = ["GROTTO", "TRENO_RES"]                              # EVT_<name> to install (from DIST)
OLD_EVT = ["HUT_EXT", "HUT_INT", "TESTROOM"]                      # EVT_<name> to remove
OLD_FBG = ["FBG_N11_HUT_EXT", "FBG_N11_HUT_INT",
           "FBG_N11_TESTROOM", "FBG_N11_ROOM01_BASE"]            # FieldMaps dirs to remove


def main():
    game = find_game_path()
    live_root = game / "FF9CustomMap"
    live = ModLayout(live_root)
    dist = ModLayout(DIST)
    if not dist.dictionary_patch.is_file():
        raise SystemExit(f"build the mod first: {DIST} has no DictionaryPatch.txt")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bk = REPO / "backups" / f"FF9CustomMap.pre-tworoom.{stamp}"

    # 1. full snapshot (bulletproof revert)
    shutil.copytree(live_root, bk)
    print(f"snapshot {live_root} -> {bk}")

    # 2. wipe old fields
    for name in OLD_EVT:
        n = 0
        for L in LANGS:
            p = live.eb_path(L, f"EVT_{name}.eb.bytes")
            if p.exists():
                p.unlink()
                n += 1
        print(f"  removed EVT_{name} ({n} langs)")
    for fbg in OLD_FBG:
        d = live.fieldmap_dir(fbg)
        if d.exists():
            shutil.rmtree(d)
            print(f"  removed FieldMaps/{fbg}")

    # 3. install new fields (BG-borrow -> EVT only, no scene)
    for name in NEW_FIELDS:
        for L in LANGS:
            src = dist.eb_path(L, f"EVT_{name}.eb.bytes")
            dst = live.eb_path(L, f"EVT_{name}.eb.bytes")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        print(f"  installed EVT_{name} ({len(LANGS)} langs)")

    # 4. DictionaryPatch = exactly the two new lines (drops the old 4000/4002/4003 lines)
    shutil.copyfile(dist.dictionary_patch, live.dictionary_patch)
    print("  DictionaryPatch -> " + live.dictionary_patch.read_text(encoding="utf-8").strip().replace("\n", " | "))

    # 5. revert script (full restore from the snapshot)
    rev = REPO / "tools" / "scroll_out" / "revert_tworoom.py"
    rev.parent.mkdir(parents=True, exist_ok=True)
    rev.write_text(
        '"""Full restore of FF9CustomMap to the pre-tworoom snapshot (undoes the field swap + warp)."""\n'
        "import shutil\nfrom pathlib import Path\n"
        f"live = Path(r{str(live_root)!r})\nbk = Path(r{str(bk)!r})\n"
        "shutil.rmtree(live, ignore_errors=True)\nshutil.copytree(bk, live)\n"
        f"print('reverted FF9CustomMap to pre-tworoom snapshot {stamp}')\n",
        encoding="utf-8", newline="\n")
    print(f"\nrevert: py {rev.relative_to(REPO).as_posix()}")
    print("NEXT:   py tools/newgame_warp.py 4004 --stock   (point New Game at the grotto)")


if __name__ == "__main__":
    main()
