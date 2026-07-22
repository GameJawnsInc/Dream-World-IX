"""Custom Summons -- rung 6 REVERT: restore ef084 to rung 3's verbatim baseline.

Alias of ``build_rung6.py --restore`` (house convention -- every rung in this study ships both a
``--restore``/``--stage``-style flag on its build script AND a standalone ``revert_rungN.py`` that
calls the SAME code path, so there is exactly one implementation of "undo this rung", not two that
could drift apart. Mirrors ``rung5-particles/revert_rung5.py`` exactly.

Removes exactly what ``build_rung6.py --bare`` staged in the LIVE mod folder, beyond rung 3's own
baseline:

  1. Rewrites ``FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/PlayerSequence.seq`` back to
     a pure byte-identical copy of stock ``ef227/PlayerSequence.seq`` (sha-guarded) -- undoes the
     rung-6 bare sequence entirely.
  2. Deletes the DEPLOYED bespoke sprite -- ``ef084/RisingRing.sfxmodel`` -- from the mod folder.
     Does **NOT** touch either repo copy of the sprite (``rung5-particles/rung5_sprite.sfxmodel``,
     the source of truth this rung reused verbatim) -- that file is rung 5's own committed content,
     not this rung's deploy output, and stays in the repo regardless of revert state.

Does **NOT** touch: ``ef084/Sequence.seq`` (rung 3's own file; this rung never writes it, and the
bare sequence never loads it -- no ``LoadSFX`` line exists to nest-load it), ``ef227/`` (the shared
Bahamut donor folder -- rung 6 never wrote there), the rung-2 staged chime (a separate artifact set
owned by ``rung2-seq-hot-edit/revert_rung2.py``), or this directory's own repo copy of
``bare_player_sequence.seq`` (OUR committed content -- not deploy output; that file IS the source
``build_rung6.py --bare`` re-derives the deploy from, every run).

After this, ``ef084/`` is back to exactly rung 3's own baseline: a byte-identical copy of stock
``ef227``'s two ``.seq`` files, no bare-sequence content, no ``RisingRing.sfxmodel`` sitting
alongside it.

Run from anywhere:

    py studies/custom-summons/rung6-bare-sequence/revert_rung6.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung6-bare-sequence -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config                # noqa: E402

from build_rung6 import (                   # noqa: E402
    BESPOKE_SPRITE_REL, DriftError, FRESH_EF_ID, PLAYER_SEQ_REL, build,
)


def main() -> int:
    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print()

    try:
        result = build(mod_root, game_path, "restore")
    except DriftError as e:
        print(f"DRIFT GUARD TRIPPED -- refusing to restore against unexpected content:\n  {e}",
              file=sys.stderr)
        return 1

    print(f"=== {PLAYER_SEQ_REL} ===")
    print(f"restored to : {result['dest_path']}")
    print(f"  sha256    : {result['dest_sha256']}")
    tag = "BYTE-IDENTICAL to stock" if result["byte_identical_to_stock"] else "STILL MODIFIED (unexpected)"
    print(f"  [{tag}]")

    print()
    dest_path = mod_root / BESPOKE_SPRITE_REL
    print(f"=== ef{FRESH_EF_ID:03d}/RisingRing.sfxmodel (rung 6's reused sprite deploy) ===")
    if result["sprite_removed"]:
        print(f"removed: {dest_path}")
    else:
        print(f"nothing to remove -- {dest_path} was not present")

    print()
    print("Not touched: ef084/Sequence.seq (rung 3's file, never read by a bare sequence with no")
    print("LoadSFX line), ef227/ (the shared Bahamut donor folder -- untouched by rung 6), the rung-2")
    print("staged chime, and rung 5's own repo copy of rung5_sprite.sfxmodel (that rung's committed")
    print("content, reused here verbatim -- not this rung's deploy output).")
    print()
    print(f"ef{FRESH_EF_ID:03d}/ is back to rung 3's own baseline: verbatim ef227 copy, no bare-sequence")
    print("content, no RisingRing.sfxmodel alongside it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
