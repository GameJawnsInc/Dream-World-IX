"""Custom Summons -- rung 3 REVERT: remove the fresh-id private donor copy.

Removes exactly what ``build_rung3.py`` staged in the LIVE mod folder:

  the ``ef084/`` tree -- ``FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/`` (both
  ``PlayerSequence.seq`` and ``Sequence.seq``, regardless of which mode built them), + the now-empty
  ``ef084/`` and (if nothing else occupies it) ``SpecialEffects/`` directories it created -- mirrors
  ``rung2-seq-hot-edit/revert_rung2.py``'s empty-dir cleanup exactly, including stopping at
  ``SpecialEffects/`` and never touching ``Data/`` itself (that folder also holds this bench's own
  ``Battle``/``Characters``/``Items``/``Text`` overrides -- rung 3 must never remove those).

Does **NOT** touch the rung-2 staged chime (its manifest row at
``FF9_Data/EmbeddedAsset/Manifest/Sounds/SoundEffectMetaData.txt`` and its ``.ogg`` asset at
``StreamingAssets/Assets/Resources/Sounds/Sounds02/SE00/rung2chime.ogg``) -- that belongs to the
rung-2 artifact set (``rung2-seq-hot-edit/revert_rung2.py`` owns it) and rung 3 only ever *read*
its id (100000) as a numeric ``PlaySound`` argument; it never re-derives or re-mints it.

After this, ``ef084`` no longer exists in any mod folder -- id 84 is back to being genuinely unused,
exactly as it was before this rung. Stock ``ef227`` was never touched by rung 3 in the first place.

Run from anywhere:

    py studies/custom-summons/rung3-fresh-id/revert_rung3.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung3-fresh-id -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config                # noqa: E402

from build_rung3 import FRESH_EF_ID, PLAYER_SEQ_NAME, SEQ_NAME   # noqa: E402


def remove_fresh_id_copy(mod_root: Path) -> dict:
    ef_dir = mod_root / "StreamingAssets" / "Data" / "SpecialEffects" / f"ef{FRESH_EF_ID:03d}"
    removed = {"player_seq": False, "seq": False, "ef_dir": False, "specialeffects_dir": False}

    player_seq = ef_dir / PLAYER_SEQ_NAME
    if player_seq.exists():
        player_seq.unlink()
        removed["player_seq"] = True

    seq = ef_dir / SEQ_NAME
    if seq.exists():
        seq.unlink()
        removed["seq"] = True

    if ef_dir.is_dir() and not any(ef_dir.iterdir()):
        ef_dir.rmdir()
        removed["ef_dir"] = True

    se_dir = ef_dir.parent   # .../StreamingAssets/Data/SpecialEffects
    if se_dir.is_dir() and se_dir.name == "SpecialEffects" and not any(se_dir.iterdir()):
        se_dir.rmdir()
        removed["specialeffects_dir"] = True

    return removed


def main() -> int:
    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print()

    removed = remove_fresh_id_copy(mod_root)
    print(f"=== ef{FRESH_EF_ID:03d}/ (rung 3's fresh-id private copy) ===")
    ef_dir_path = mod_root / "StreamingAssets" / "Data" / "SpecialEffects" / f"ef{FRESH_EF_ID:03d}"
    if removed["player_seq"]:
        print(f"removed: {ef_dir_path / PLAYER_SEQ_NAME}")
    else:
        print(f"nothing to remove -- {PLAYER_SEQ_NAME} was not present")
    if removed["seq"]:
        print(f"removed: {ef_dir_path / SEQ_NAME}")
    else:
        print(f"nothing to remove -- {SEQ_NAME} was not present")
    if removed["ef_dir"]:
        print(f"removed now-empty dir: ef{FRESH_EF_ID:03d}/")
    if removed["specialeffects_dir"]:
        print("removed now-empty dir: SpecialEffects/ (nothing else in the mod folder uses it)")

    print()
    print("Not touched (belongs to the rung-2 artifact set -- revert with rung2-seq-hot-edit/")
    print("revert_rung2.py if you want it gone too): the staged chime manifest row + its .ogg,")
    print("and stock ef227 (rung 3 never wrote there).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
