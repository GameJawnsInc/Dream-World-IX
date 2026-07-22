"""Custom Summons -- rung 4 REVERT: restore pure-stock ``ef227/Sequence.seq`` resolution.

Removes exactly what ``build_rung4.py`` staged in the LIVE mod folder:

  the ``.seq`` override -- ``FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef227/Sequence.seq``
  (+ the now-empty ``ef227/`` directory it created, mirroring
  ``rung2-seq-hot-edit/revert_rung2.py``'s cleanup of the SAME folder). ``SpecialEffects/`` itself is
  only removed if it is ALSO left empty -- on this bench it is not: rung 3's ``ef084/`` (the private
  fresh-id donor copy) lives in the same parent and must survive this revert untouched.

Does **NOT** touch: ``ef084/`` (rung 3's artifact -- a completely different id/folder; owned by
``rung3-fresh-id/revert_rung3.py``), the rung-2 staged chime manifest row/``.ogg`` (owned by
``rung2-seq-hot-edit/revert_rung2.py``), or stock ``ef227/PlayerSequence.seq`` (rung 4 never writes
that file -- only the SIBLING ``Sequence.seq`` in the same folder).

After this, both the outer (``PlayerSequence.seq``) and inner (``Sequence.seq``) resolution for
``ef227`` are pure stock again -- vanilla Garnet/Eiko Bahamut casts see the damage beat back at its
original mid-flare tick.

Run from anywhere:

    py studies/custom-summons/rung4-effectpoint/revert_rung4.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung4-effectpoint -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config                # noqa: E402

from build_rung4 import EF_ID               # noqa: E402

SEQ_NAME = "Sequence.seq"


def remove_seq_override(mod_root: Path) -> dict:
    ef_dir = mod_root / "StreamingAssets" / "Data" / "SpecialEffects" / f"ef{EF_ID:03d}"
    seq_file = ef_dir / SEQ_NAME
    removed = {"seq_file": False, "ef_dir": False, "specialeffects_dir": False}

    if seq_file.exists():
        seq_file.unlink()
        removed["seq_file"] = True

    # Only remove ef227/ if rung 4 was the sole occupant (it never wrote PlayerSequence.seq here --
    # if a stray PlayerSequence.seq override exists from elsewhere, leave the directory alone).
    if ef_dir.is_dir() and not any(ef_dir.iterdir()):
        ef_dir.rmdir()
        removed["ef_dir"] = True

    # SpecialEffects/ is shared with rung 3's ef084/ -- only remove it if NOTHING else occupies it
    # (never true on this bench while ef084/ exists, by design; the check is still made explicit
    # rather than assumed, so this script is safe to run standalone in any state).
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

    removed = remove_seq_override(mod_root)
    ef_dir_path = mod_root / "StreamingAssets" / "Data" / "SpecialEffects" / f"ef{EF_ID:03d}"
    print(f"=== ef{EF_ID:03d}/{SEQ_NAME} override ===")
    if removed["seq_file"]:
        print(f"removed: {ef_dir_path / SEQ_NAME}")
    else:
        print("nothing to remove -- no override was present")
    if removed["ef_dir"]:
        print(f"removed now-empty dir: ef{EF_ID:03d}/")
    else:
        print(f"kept dir: ef{EF_ID:03d}/ (not empty -- something else still lives there)")
    if removed["specialeffects_dir"]:
        print("removed now-empty dir: SpecialEffects/")
    else:
        print("kept dir: SpecialEffects/ (rung 3's ef084/ -- or other content -- still lives there)")

    print()
    print("Not touched: ef084/ (rung 3's private fresh-id copy -- revert with")
    print("rung3-fresh-id/revert_rung3.py if you want it gone too), the rung-2 staged chime, and")
    print("ef227/PlayerSequence.seq (a different file; rung 4 never wrote it).")
    print()
    print("Pure-stock ef227/Sequence.seq resolution restored: the damage beat is back at its")
    print("original mid-flare tick for every cast that resolves Bahamut__Full by name (vanilla")
    print("Garnet/Eiko AND this bench's ef084 borrow, per rung 3's nested-load law).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
