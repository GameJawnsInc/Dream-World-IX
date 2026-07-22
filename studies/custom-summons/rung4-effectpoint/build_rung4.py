"""Custom Summons -- rung 4: the EffectPoint RELOCATION probe.

Overrides the STOCK Bahamut cinematic's SHARED inner choreography file
(``Data/SpecialEffects/ef227/Sequence.seq``) with a mod-folder copy that relocates its damage
-application beat (the ``EffectPoint`` pair) from mid-flare to the opening blackout, to prove --
on the ALREADY-RUNNING game, no relaunch, no redeploy -- that:

  1. this SECOND, NESTED ``.seq`` load (``ef227/Sequence.seq``, loaded from *inside*
     ``PlayerSequence.seq``'s ``LoadSFX: SFX=Bahamut__Full`` line by the resolved effect id, NOT the
     caller's own folder id -- see rung 3) goes through the exact same mod-stacked, no-cache
     ``AssetManager.LoadString`` path rung 2 already proved for the OUTER ``PlayerSequence.seq`` load
     -- so a recast alone moves the damage beat, no ``~``, no relaunch;
  2. ``EffectPoint`` -- the actual damage-application trigger (``btl_cmd.ExecVfxCommand`` ->
     ``SBattleCalculator.CalcMain``) -- can be moved to an arbitrary point in the timeline and the
     rest of the cinematic keeps playing around it unmodified, because ``BattleAction.ExecuteLoop``'s
     only completion check is "all threads drained", never target HP (see the recon's
     ``safety_analysis``, corroborated directly against ``UnifiedBattleSequencer.cs:1194-1345`` in
     this rung's own re-read below).

THE EDIT (source-cited in ``studies/custom-summons/PLAN.md`` §5 rung 4 and the rung-4 recon
transcript this script was built from -- see README.md for the full citation trail):

  Remove, as one contiguous 3-line block, the damage beat that stock fires mid-flare (old tick 486,
  ~32.4s in):
      EffectPoint: Char=AllTargets ; Type=Effect
      Wait: Time=12
      EffectPoint: Char=Everyone ; Type=Figure
  and re-insert the SAME 3-line block, gap preserved, immediately after the opening blackout
  (``ShowMesh: Char=Everyone ; Enable=False ; IsDisappear=True``) and before the first
  ``StartThread`` block -- i.e. as the new tick-18 beat (~1.2s in), before Bahamut is even summoned
  on screen.

  Both ``EffectPoint`` lines move TOGETHER (the stock 12-tick internal gap is preserved) -- moving
  only one would either strand a ``Figure`` display ~31s after its ``Effect`` computation with an
  entire cinematic in between, or (in the other direction) risk decoupling the pair for no reason;
  the DSL supports 0-gap ``Type=Both`` elsewhere but nothing requires changing the gap, so this
  script doesn't.

  This is a MOVE, not a copy: the two lines vacate their old slot. The two flanking ``Wait`` lines
  that used to sandwich them (``Wait: Time=52`` before, ``Wait: Time=18`` after) become adjacent and
  are left completely untouched -- they still sum to the original 82-tick gap between the flare-ramp
  line and the lights-back-on line, so every beat from the flare onward still fires at its stock
  absolute tick. Only the beats strictly BETWEEN the insertion point and the old removal point (four
  roar/PlaySound clusters + two intermediate flash beats) shift later by a uniform +12 ticks (~0.8s
  at the user's live ``BattleTPS=15``) -- an imperceptible stretch, and not the thing under test.

PROVENANCE: the edited ``Sequence.seq`` this script writes is a modified copy of Square-Enix's own
shipped file -- SE-derived content, and is therefore NEVER written into the repo. This script is the
committable source of truth (regenerates the edit from the user's own install every run); the ONLY
record of the edit is the unified diff this script prints (and the edit-spec in this docstring and
README.md). The output lands directly in the LIVE mod folder (``<game>/FF9CustomMap/...``), never
under ``studies/``.

Run from anywhere (game may be OPEN -- no relaunch, no redeploy needed):

    py studies/custom-summons/rung4-effectpoint/build_rung4.py

Then: re-enter a battle on bench field 30300 and recast "Bahamut Cinema" from Iviv's Spark command.
See README.md for the full expect/failure-mode table and the revert instructions
(``revert_rung4.py``).
"""
from __future__ import annotations

import difflib
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung4-effectpoint -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config, fsutil          # noqa: E402

# --------------------------------------------------------------------------- the .seq edit
EF_ID = 227                                 # Bahamut__Full's shared effect folder (SpecialEffect.cs:99)
SEQ_REL_PATH = f"StreamingAssets/Data/SpecialEffects/ef{EF_ID:03d}/Sequence.seq"

# The exact sha256 of the stock file this script (and the rung-4 recon) read. If the user's install
# has a different Memoria/mod version with a changed ef227/Sequence.seq, this differs and we refuse
# to guess at an edit against unknown content -- the drift guard. Matches
# rung3-fresh-id/build_rung3.py's independently-verified EXPECTED_SHA256[SEQ_NAME] for the same file.
EXPECTED_SHA256 = "0452a785e90c206c21f5c9b5464310f6d73186fe001dfd12abf60eda292611d0"

# The damage-application beat, moved as one contiguous unit -- the stock 12-tick internal gap between
# the two EffectPoint lines is preserved verbatim (see safety_analysis in the recon: moving only one
# would strand its sibling, and nothing requires changing the gap).
EFFECTPOINT_BLOCK = [
    "EffectPoint: Char=AllTargets ; Type=Effect\r\n",
    "Wait: Time=12\r\n",
    "EffectPoint: Char=Everyone ; Type=Figure\r\n",
]

# The insertion anchor: the opening-blackout ShowMesh line immediately followed by the first
# StartThread block. This exact two-line ADJACENT pair occurs exactly once in the stock file (a
# second "StartThread: Condition=SFXUseCamera && AreTargetsPlayers" line exists near the end, but its
# preceding line is a SetBackgroundIntensity, not this ShowMesh -- so anchoring on the PAIR, not
# either line alone, is what makes the match unique).
INSERT_ANCHOR_PAIR = [
    "ShowMesh: Char=Everyone ; Enable=False ; IsDisappear=True\r\n",
    "StartThread: Condition=SFXUseCamera && AreTargetsPlayers\r\n",
]


class DriftError(RuntimeError):
    """The stock file's bytes -- or its expected line shape -- don't match what this script was
    built against."""


def _find_unique_block(lines: list[str], block: list[str], desc: str) -> int:
    """Return the single start index where ``lines[i:i+len(block)] == block``. Raises DriftError if
    the block is missing or ambiguous (more than one match) -- abort rather than guess which one."""
    n = len(block)
    matches = [i for i in range(len(lines) - n + 1) if lines[i:i + n] == block]
    if len(matches) != 1:
        raise DriftError(
            f"expected exactly one occurrence of {desc} ({block!r}), found {len(matches)} -- "
            "the stock file's shape has changed since this script's edit was derived; abort rather "
            "than guess"
        )
    return matches[0]


def apply_edits(stock_text: str) -> str:
    """Apply exactly the one documented move to the stock ``.seq`` text: relocate the 3-line
    EffectPoint block from mid-flare to right after the opening blackout. Raises ``DriftError`` if
    either anchor is missing or ambiguous (the stock file has changed shape since this script's edit
    was derived)."""
    lines = stock_text.splitlines(keepends=True)

    remove_idx = _find_unique_block(
        lines, EFFECTPOINT_BLOCK, "the damage-application EffectPoint block"
    )
    del lines[remove_idx:remove_idx + len(EFFECTPOINT_BLOCK)]

    # The insertion anchor sits earlier in the file (index ~4) than the removal site (index ~62), so
    # removing the later block first cannot disturb the anchor's indices.
    insert_idx = _find_unique_block(
        lines, INSERT_ANCHOR_PAIR, "the opening-blackout ShowMesh / StartThread pair"
    )
    # insert_idx is the ShowMesh line; the new block lands BETWEEN it and the following StartThread.
    lines[insert_idx + 1:insert_idx + 1] = EFFECTPOINT_BLOCK

    return "".join(lines)


def stock_seq_path(game_path: Path) -> Path:
    return game_path / SEQ_REL_PATH


def build_seq_override(mod_root: Path, game_path: Path) -> dict:
    """Read the stock ``ef227/Sequence.seq``, verify its hash, apply the one relocation, and write
    the result to the mod-folder override path (created fresh -- this bench's ``ef227/`` doesn't
    exist yet; rung 2's earlier override of the SAME folder's ``PlayerSequence.seq`` was already
    reverted). Idempotent: re-running always re-derives from the untouched stock file and overwrites
    the override with identical bytes."""
    src = stock_seq_path(game_path)
    if not src.exists():
        raise FileNotFoundError(f"stock file not found: {src}")
    raw = src.read_bytes()
    got_hash = hashlib.sha256(raw).hexdigest()
    if got_hash != EXPECTED_SHA256:
        raise DriftError(
            f"{src} sha256 {got_hash} != expected {EXPECTED_SHA256} -- "
            "the stock file differs from what the rung-4 recon read; refusing to apply a blind edit. "
            "Re-derive the edit against the new content before re-running."
        )

    stock_text = raw.decode("utf-8")
    edited_text = apply_edits(stock_text)
    edited_bytes = edited_text.encode("utf-8")

    dest = mod_root / SEQ_REL_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_bytes(dest, edited_bytes)

    # verify the write landed byte-exact (feedback-verify-the-cache-write-lands)
    readback = dest.read_bytes()
    if readback != edited_bytes:
        raise RuntimeError(f"write verification failed at {dest} -- readback != what we wrote")

    diff = "".join(difflib.unified_diff(
        stock_text.splitlines(keepends=True), edited_text.splitlines(keepends=True),
        fromfile=f"stock/{SEQ_REL_PATH}", tofile=f"FF9CustomMap/{SEQ_REL_PATH}",
    ))
    return {
        "stock_path": str(src), "stock_sha256": got_hash,
        "override_path": str(dest), "override_sha256": hashlib.sha256(edited_bytes).hexdigest(),
        "diff": diff,
    }


def main() -> int:
    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)   # FF9CustomMap -- the bench's own mod folder

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print()

    try:
        seq_result = build_seq_override(mod_root, game_path)
    except DriftError as e:
        print(f"DRIFT GUARD TRIPPED -- refusing to write an edit against unexpected content:\n  {e}",
              file=sys.stderr)
        return 1

    print("=== ef227/Sequence.seq override (EffectPoint relocation, no relaunch needed) ===")
    print(f"stock sha256    : {seq_result['stock_sha256']}  (expected {EXPECTED_SHA256})")
    print(f"stock file      : {seq_result['stock_path']}")
    print(f"override written: {seq_result['override_path']}")
    print(f"override sha256 : {seq_result['override_sha256']}")
    print()
    print("--- unified diff (the ONLY record of the edit -- can't commit SE-derived content) ---")
    print(seq_result["diff"])

    print()
    print("SHARED-FOLDER CAVEAT: ef227 is the real Bahamut__Full donor -- every vanilla Garnet/Eiko")
    print("Bahamut cast on this install will ALSO see damage land near the opening blackout instead")
    print("of mid-flare, until reverted. Revert with revert_rung4.py before leaving the bench.")
    print()
    print("Next: re-enter a battle on bench field 30300 (game already running -- no relaunch, no")
    print("redeploy) and recast \"Bahamut Cinema\" from Iviv's Spark command. See README.md for the")
    print("full expect/failure-mode table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
