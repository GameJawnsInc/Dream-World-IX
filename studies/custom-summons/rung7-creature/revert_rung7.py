"""Custom Summons -- rung 7 REVERT: restore ef084 to rung 6's proven bare state.

Alias of ``build_rung7.py --restore`` (house convention -- every rung in this study ships both a
``--restore``-style flag on its build script AND a standalone ``revert_rungN.py`` that calls the SAME
code path, so there is exactly one implementation of "undo this rung". Mirrors
``rung6-bare-sequence/revert_rung6.py`` exactly.

Unlike rung 6's own revert (which went all the way back to rung 3's donor-copy baseline), rung 7's
sequence is layered directly on rung 6's OWN committed content, not on a Square-Enix-derived file -- so
"restore" here specifically means "rung 6's proven bare state again", not "the stock ef227 copy".

Removes exactly what ``build_rung7.py --creature`` staged in the LIVE mod folder, beyond rung 6's own
state:

  1. Deletes ``FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/FileList.txt`` -- the first-ever
     FileList.txt this study wrote.
  2. Deletes ``ef084/creature_manifest.sfxmodel``.
  3. Rewrites ``ef084/PlayerSequence.seq`` back to a byte-identical copy of rung 6's own committed
     ``rung6-bare-sequence/bare_player_sequence.seq`` (sha-guarded).

Does **NOT** touch: ``ef084/RisingRing.sfxmodel`` (rung 6's bare sequence still references it -- stays
deployed), ``ef084/Sequence.seq`` (rung 3's own file, never read by either rung 6's or rung 7's sequence
in a way that matters -- rung 7 defuses it via ``SkipSequence=True`` rather than touching it), ``ef227/``
(the shared Bahamut donor folder -- rung 7 never wrote there), the rung-2 staged chime, Iviv's GEO 6100
asset (verified-only, never this script's to manage), or any repo copy of rung 6's/rung 5's own committed
content.

Run from anywhere:

    py studies/custom-summons/rung7-creature/revert_rung7.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung7-creature -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config                # noqa: E402

from build_rung7 import (                   # noqa: E402
    CREATURE_MANIFEST_REL, DriftError, FILELIST_REL, FRESH_EF_ID, PLAYER_SEQ_REL, build,
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
    print(f"restored to : {result['seq_dest']}")
    print(f"  sha256    : {result['seq_sha256']}")
    tag = "BYTE-IDENTICAL to rung 6's bare_player_sequence.seq" if result["seq_is_rung6_bare"] \
        else "STILL MODIFIED (unexpected)"
    print(f"  [{tag}]")

    print()
    print(f"=== ef{FRESH_EF_ID:03d}/{FILELIST_REL.rsplit('/', 1)[-1]} ===")
    if result["filelist_removed"]:
        print(f"removed: {mod_root / FILELIST_REL}")
    else:
        print(f"nothing to remove -- {mod_root / FILELIST_REL} was not present")

    print()
    print(f"=== {CREATURE_MANIFEST_REL} ===")
    if result["manifest_removed"]:
        print(f"removed: {mod_root / CREATURE_MANIFEST_REL}")
    else:
        print(f"nothing to remove -- {mod_root / CREATURE_MANIFEST_REL} was not present")

    print()
    print("Not touched: ef084/RisingRing.sfxmodel (rung 6's bare sequence still references it -- stays")
    print("deployed), ef084/Sequence.seq (rung 3's leftover, still inert), ef227/ (the shared Bahamut")
    print("donor -- untouched by rung 7), the rung-2 staged chime, and Iviv's GEO 6100 asset (verified")
    print("only, never this script's to manage).")
    print()
    print(f"ef{FRESH_EF_ID:03d}/ is back to rung 6's own proven bare state: no FileList.txt, no")
    print("creature_manifest.sfxmodel, PlayerSequence.seq byte-identical to rung 6's committed file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
