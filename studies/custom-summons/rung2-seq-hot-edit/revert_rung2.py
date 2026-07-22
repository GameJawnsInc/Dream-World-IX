"""Custom Summons -- rung 2 REVERT: restore pure-stock ``ef227`` resolution.

Removes exactly what ``build_rung2.py`` staged in the LIVE mod folder:

  1. the ``.seq`` override -- ``FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef227/
     PlayerSequence.seq`` (+ the now-empty ``ef227/`` and ``SpecialEffects/`` directories it
     created, since neither existed in a stock install -- recon confirmed
     ``FF9CustomMap\\StreamingAssets\\Data\\`` had NO ``SpecialEffects`` subfolder before rung 2);
  2. the minted probe-chime SFX -- its manifest row (surgically removed from the accumulated
     ``SoundEffectMetaData.txt`` override -- other kit-authored mints in the same file, if any, are
     left untouched) and its ``.ogg`` asset, deleting the override manifest FILE entirely only if
     removing our row leaves it identical to the stock table (nothing else layered on top).

After this, both the ``.seq`` (immediate) and the minted sound (arms on relaunch) resolve to pure
stock again -- vanilla Garnet/Eiko Bahamut casts stop hearing/seeing rung 2's edits.

Run from anywhere:

    py studies/custom-summons/rung2-seq-hot-edit/revert_rung2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config, fsutil, sound            # noqa: E402

from build_rung2 import EF_ID, SFX_FIXED_ID, SFX_KIND, SFX_RESOURCE_ID   # noqa: E402


def remove_seq_override(mod_root: Path) -> dict:
    ef_dir = mod_root / "StreamingAssets" / "Data" / "SpecialEffects" / f"ef{EF_ID:03d}"
    seq_file = ef_dir / "PlayerSequence.seq"
    removed = {"seq_file": False, "ef_dir": False, "specialeffects_dir": False}

    if seq_file.exists():
        seq_file.unlink()
        removed["seq_file"] = True

    if ef_dir.is_dir() and not any(ef_dir.iterdir()):
        ef_dir.rmdir()
        removed["ef_dir"] = True

    se_dir = ef_dir.parent   # .../StreamingAssets/Data/SpecialEffects
    if se_dir.is_dir() and se_dir.name == "SpecialEffects" and not any(se_dir.iterdir()):
        se_dir.rmdir()
        removed["specialeffects_dir"] = True

    return removed


def remove_minted_sound(mod_root: Path, game_path: Path) -> dict:
    mpath = sound.manifest_override_path(mod_root, SFX_KIND)
    dest_ogg = mod_root / sound.override_rel_path(SFX_RESOURCE_ID)
    removed = {"manifest_row": False, "manifest_deleted": False, "ogg": False, "manifest_kept": False}

    if mpath.exists():
        entries = sound.parse_manifest(mpath.read_text(encoding="utf-8"))
        before = len(entries)
        entries = [e for e in entries if not (e["id"] == SFX_FIXED_ID and e["resource_id"] == SFX_RESOURCE_ID)]
        if len(entries) != before:
            removed["manifest_row"] = True
            stock = sound.read_manifest(SFX_KIND, game=game_path)
            stock_ids = {e["id"] for e in stock}
            remaining_ids = {e["id"] for e in entries}
            if remaining_ids == stock_ids:
                # nothing but the stock table remains -- the override file is now redundant
                mpath.unlink()
                removed["manifest_deleted"] = True
            else:
                extra = sorted(remaining_ids - stock_ids)
                fsutil.atomic_write_text(mpath, sound.serialize_manifest(entries))
                removed["manifest_kept"] = True
                removed["other_custom_ids"] = extra

    if dest_ogg.exists():
        dest_ogg.unlink()
        removed["ogg"] = True
        # clean up the empty subfolders we created (Sounds02/SE00, Sounds02, Sounds), stop at "Sounds"
        d = dest_ogg.parent
        while d.name != "Sounds" and d.is_dir() and not any(d.iterdir()):
            parent = d.parent
            d.rmdir()
            d = parent

    return removed


def main() -> int:
    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print()

    seq_removed = remove_seq_override(mod_root)
    print("=== .seq override ===")
    if seq_removed["seq_file"]:
        print(f"removed: {mod_root / 'StreamingAssets/Data/SpecialEffects' / f'ef{EF_ID:03d}' / 'PlayerSequence.seq'}")
    else:
        print("nothing to remove -- no override was present")
    if seq_removed["ef_dir"]:
        print(f"removed now-empty dir: ef{EF_ID:03d}/")
    if seq_removed["specialeffects_dir"]:
        print("removed now-empty dir: SpecialEffects/ (didn't exist before rung 2)")
    print()

    sfx_removed = remove_minted_sound(mod_root, game_path)
    print("=== minted probe chime ===")
    if sfx_removed["manifest_row"]:
        print(f"removed manifest row: sfx id {SFX_FIXED_ID} = {SFX_RESOURCE_ID}")
        if sfx_removed["manifest_deleted"]:
            print("deleted the override manifest file entirely (nothing but stock remained)")
        elif sfx_removed["manifest_kept"]:
            print(f"kept the override manifest -- other custom sfx ids still present: {sfx_removed.get('other_custom_ids')}")
    else:
        print("nothing to remove -- no manifest row was present")
    if sfx_removed["ogg"]:
        print(f"removed ogg: {mod_root / sound.override_rel_path(SFX_RESOURCE_ID)}")
    else:
        print("nothing to remove -- no ogg asset was present")

    print()
    print("Pure-stock ef227 resolution restored (both engines fall back to the base install's own")
    print("StreamingAssets/Data/SpecialEffects/ef227/PlayerSequence.seq and stock SoundEffectMetaData).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
