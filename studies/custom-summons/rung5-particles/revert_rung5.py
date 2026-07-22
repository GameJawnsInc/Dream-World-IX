"""Custom Summons -- rung 5 REVERT: restore verbatim ef084 + remove the deployed bespoke sprite.

Removes exactly what ``build_rung5.py`` staged in the LIVE mod folder, beyond rung 3's own baseline:

  1. Rewrites ``FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/PlayerSequence.seq`` back to
     a pure byte-identical copy of stock ``ef227/PlayerSequence.seq`` (sha-guarded) -- undoes
     whichever ``CreateVisualEffect`` line (stage A or stage B) was last inserted. This is the exact
     same rewrite ``build_rung5.py`` (no flags) already performs -- this script calls it directly so
     there is one code path for "restore verbatim", not two copies that could drift apart.
  2. Deletes the DEPLOYED bespoke sprite -- ``ef084/RisingRing.sfxmodel`` -- from the mod folder.
     Does **NOT** touch the repo copy (``rung5-particles/rung5_sprite.sfxmodel``) -- that file is
     OUR committed content and is the source `build_rung5.py --stage-b` re-derives the deploy from;
     it is not test-run output and stays in the repo regardless of revert state.

Does **NOT** touch: ``ef084/Sequence.seq`` (rung 3's own file; this rung never writes it),
``ef227/`` (the shared Bahamut donor folder -- rung 5 never wrote there, and rung 4's own override
of ``ef227/Sequence.seq`` was already reverted before this rung began -- verified on disk), or the
rung-2 staged chime (a completely separate artifact set, owned by
``rung2-seq-hot-edit/revert_rung2.py``).

After this, ``ef084/`` is back to exactly rung 3's own baseline: a byte-identical copy of stock
``ef227``'s two ``.seq`` files, no ``CreateVisualEffect`` line, no ``RisingRing.sfxmodel`` sitting
alongside it.

Run from anywhere:

    py studies/custom-summons/rung5-particles/revert_rung5.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung5-particles -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config                # noqa: E402

from build_rung5 import (                   # noqa: E402
    BESPOKE_SPRITE_REL, DriftError, FRESH_EF_ID, PLAYER_SEQ_REL, build,
)


def remove_bespoke_sprite(mod_root: Path) -> dict:
    dest = mod_root / BESPOKE_SPRITE_REL
    removed = {"sprite_file": False}
    if dest.exists():
        dest.unlink()
        removed["sprite_file"] = True
    return removed


def main() -> int:
    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print()

    try:
        seq_result = build(mod_root, game_path, "none")
    except DriftError as e:
        print(f"DRIFT GUARD TRIPPED -- refusing to restore against unexpected content:\n  {e}",
              file=sys.stderr)
        return 1

    print(f"=== {PLAYER_SEQ_REL} ===")
    print(f"restored to : {seq_result['dest_path']}")
    print(f"  sha256    : {seq_result['dest_sha256']}")
    tag = "BYTE-IDENTICAL to stock" if seq_result["byte_identical_to_stock"] else "STILL MODIFIED (unexpected)"
    print(f"  [{tag}]")

    sprite_removed = remove_bespoke_sprite(mod_root)
    print()
    print(f"=== ef{FRESH_EF_ID:03d}/RisingRing.sfxmodel (rung 5's bespoke sprite deploy) ===")
    dest_path = mod_root / BESPOKE_SPRITE_REL
    if sprite_removed["sprite_file"]:
        print(f"removed: {dest_path}")
    else:
        print(f"nothing to remove -- {dest_path} was not present")

    print()
    print("Not touched: ef084/Sequence.seq (rung 3's file, this rung never writes it), ef227/ (the")
    print("shared Bahamut donor folder -- untouched by rung 5; rung 4's own ef227/Sequence.seq")
    print("override should already be reverted separately, per rung4-effectpoint/revert_rung4.py),")
    print("the rung-2 staged chime, and this directory's own repo copy of rung5_sprite.sfxmodel (OUR")
    print("committed content -- not deploy output).")
    print()
    print("ef084/ is back to rung 3's own baseline: verbatim ef227 copy, no CreateVisualEffect line,")
    print("no RisingRing.sfxmodel alongside it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
