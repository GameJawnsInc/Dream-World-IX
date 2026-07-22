"""Thomas swap REVERT: alias of ``build_thomas.py --restore`` (house convention -- every rung/build in
this study ships both a ``--restore``-style flag on its build script AND a standalone
``revert_<name>.py`` calling the SAME code path, so there is exactly one implementation of "undo this
build"). Mirrors ``rung7-creature/revert_rung7.py`` exactly.

Restores ``ef084/`` to rung 7's own proven resting state (FileList.txt + creature_manifest.sfxmodel +
PlayerSequence.seq all back to rung 7's committed content) and fully removes Thomas's GEO mint (the
``Models/3/6200/`` folder + its ``3DModel`` DictionaryPatch line) -- unlike rung 7's own Iviv-clone
asset (pre-existing, never this study's to manage), Thomas's mint is wholly new content this build
introduced, so a true restore removes it too.

Does NOT touch: ``ef227/`` (the shared Bahamut donor -- never written by this build in the first
place), ``ef084/Sequence.seq`` / ``ef084/RisingRing.sfxmodel`` (rung 3/5's leftovers, inert either
way, matching rung 7's own revert scope), or any other mint/mod-folder content.

Run from anywhere:

    py studies/custom-summons/thomas-swap/revert_thomas.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/thomas-swap -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config                # noqa: E402

from build_thomas import ThomasAssetError, DriftError, restore  # noqa: E402


def main() -> int:
    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print()

    try:
        result = restore(mod_root, game_path)
    except (DriftError, ThomasAssetError) as e:
        print(f"REFUSING TO RESTORE:\n  {e}", file=sys.stderr)
        return 1

    r7 = result["rung7"]
    print("=== StreamingAssets/Data/SpecialEffects/ef084/ (FileList.txt + creature_manifest.sfxmodel + PlayerSequence.seq) ===")
    print(f"restored to rung 7's resting state, PlayerSequence.seq sha256 = {r7['seq_sha256']}")

    um = result["unmint"]
    print()
    print("=== Thomas GEO mint ===")
    print(f"model dir removed            : {um['removed_dir']}  ({um['dest']})")
    print(f"DictionaryPatch line removed : {um['directive_removed']}  ({um['directive']!r})")

    print()
    print("ef084/ is back to rung 7's own proven resting state. Thomas's mint is fully removed.")
    print("Not touched: ef227/ (the shared Bahamut donor), ef084/Sequence.seq, ef084/RisingRing.sfxmodel,")
    print("Iviv's own GEO 6100 asset (never this build's to manage).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
