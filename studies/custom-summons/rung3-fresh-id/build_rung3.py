"""Custom Summons -- rung 3: the FRESH-ID private donor copy.

Ships a **byte-identical copy** of the stock Bahamut cinematic's two `.seq` files
(`Data/SpecialEffects/ef227/{PlayerSequence,Sequence}.seq`) into a brand-new, private effect
folder -- `FF9CustomMap/StreamingAssets/Data/SpecialEffects/ef084/` -- and repoints the bench
ability's `vfx1` at that fresh id (084) instead of the shared donor (227; see `rung3.field.toml`,
which is a byte-exact copy of rung 1's toml plus exactly that one value + a comment block).

WHY THIS PROVES SOMETHING NEW (over rung 1 and rung 2): rung 1 played the cinematic FROM the real
donor folder (227); rung 2 edited that SAME shared folder (throwaway by design -- vanilla
Garnet/Eiko Bahamut casts changed too, until reverted). Rung 3 is the first rung where the id the
bench ability points at (084) is NOT the donor id at all -- it is an id the base game's own
`StreamingAssets/Data/SpecialEffects/` tree has no folder for, and that `SpecialEffect.cs` itself
aliases as `Unused_84` (never referenced by any stock ability or enemy AI). The copied
`PlayerSequence.seq`'s own `LoadSFX: SFX=Bahamut__Full ; ... ; UseCamera=True` line is what actually
resolves the native creature + camera -- BY NAME (`Enum.Parse(SpecialEffect, "Bahamut__Full") == 227`,
`BattleActionCode.cs:176-206`), not by the containing folder's id -- so playing that same line from
inside folder 84 is expected to look and sound identical to rung 1, while stock `ef227` and every
vanilla Bahamut cast through it stay completely untouched. That closes the "the global namespace is
one shared folder tree" worry for good, and is also half of rung 6 (a fresh, engine-unclaimed id
resolves gracefully end-to-end) proven early, as a side effect.

ID CHOICE -- 84: the recon census cross-checked two independent sources and got the SAME 24-id set
both times: (1) a folder listing of `StreamingAssets/Data/SpecialEffects/ef###` (0-510) has exactly
487 present / 24 absent; (2) `Memoria/Assembly-CSharp/Memoria/Data/Battle/SpecialEffect.cs:496-519`
hand-aliases those exact 24 ids as `Unused_N` enum members with hand-written comments on what the
LEGACY (`SFXRework=0`) engine would do if one were ever cast: 18 -- "would apply effect instantly";
37, 39 -- "would never end" (the only true hang risk in the set); 80, 84, 91 -- "would run casting
animation & apply effect"; the remaining 18 (263-488) -- "would rerun last effect used". Our
install forces `SFXRework=1` (+ force-on at ATB Speed>=3 per Memoria.ini), where NONE of this
matters -- `UnifiedBattleSequencer`'s ctor (`UnifiedBattleSequencer.cs:105-126`) consumes the id
purely as a path string, never a bare enum cast -- but 84 was still picked over every other
candidate in its class to steer clear of the two genuinely bad ids (37, 39) as cheap
defense-in-depth against a user running the legacy engine. Full citation trail in this rung's
README.md.

PROVENANCE: both copied `.seq` files are VERBATIM Square-Enix content (a byte-identical copy of the
shipped `ef227` files) and are therefore NEVER written into the repo -- this script is the
committable source of truth (regenerates the copy from the user's own install every run, exactly
like `rung2-seq-hot-edit/build_rung2.py`). The output lands directly in the live mod folder
(`<game>/FF9CustomMap/...`), never under `studies/`.

Usage (game may be CLOSED or OPEN -- landing the files needs no relaunch by itself, but the bench
ability's `vfx1=84` value is Actions.csv, which IS startup-loaded; see README.md for the full
two-cast procedure):

    py studies/custom-summons/rung3-fresh-id/build_rung3.py                # CAST A: verbatim copy
    py studies/custom-summons/rung3-fresh-id/build_rung3.py --with-chime   # CAST B: + the rung-2
                                                                            # staged chime, hot-added

``--with-chime`` rebuilds `ef084/PlayerSequence.seq` with exactly one extra line --
``PlaySound: Sound=100000 ; SoundType=SoundEffect ; Volume=1.0`` (rung 2's proven syntax, id 100000
= the synthetic 880Hz chime rung 2 staged and left armed for this exact follow-up) -- inserted at
rung 2's own proven insertion point: immediately before the first `WaitAnimation: Char=Caster` line
(the file's first EXECUTABLE line, right after its leading comment + blank line). Re-running
WITHOUT the flag always restores the pure verbatim copy (both modes re-derive from the untouched
stock file every time -- nothing is ever edited in place), so this is a reversible, scripted step,
not a hand edit. `Sequence.seq` is never touched by either mode.

See README.md for the full expect/failure-mode table and `revert_rung3.py` for cleanup.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung3-fresh-id -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config, fsutil          # noqa: E402

# --------------------------------------------------------------------------- ids
DONOR_EF_ID = 227                           # Bahamut__Full's real effect folder (SpecialEffect.cs:99)
FRESH_EF_ID = 84                            # the recon's chosen unused id (Unused_84, SpecialEffect.cs:496-519)

DONOR_REL_DIR = f"StreamingAssets/Data/SpecialEffects/ef{DONOR_EF_ID:03d}"
FRESH_REL_DIR = f"StreamingAssets/Data/SpecialEffects/ef{FRESH_EF_ID:03d}"

PLAYER_SEQ_NAME = "PlayerSequence.seq"
SEQ_NAME = "Sequence.seq"

# The exact sha256 of the two stock files this script was built against (same install rung 2 read).
# If the user's install has a different Memoria/mod version with changed ef227 content, these
# differ and we refuse to guess at a "verbatim" copy against unknown content -- the drift guard.
EXPECTED_SHA256 = {
    PLAYER_SEQ_NAME: "4bc643bfb3ec478dcc1f5b51261f59637faac9d775cccd38c0055afee14ece63",
    SEQ_NAME: "0452a785e90c206c21f5c9b5464310f6d73186fe001dfd12abf60eda292611d0",
}

# --------------------------------------------------------------------------- the --with-chime edit
# Rung 2's proven insertion point: the file's first EXECUTABLE line (right after the leading
# `// comment` + blank line) -- see rung2-seq-hot-edit/build_rung2.py's FIRST_EXEC_LINE. Rung 2
# proved this exact syntax plays; rung 3 reuses it verbatim, just against the minted chime id
# (100000) instead of stock id 103.
FIRST_EXEC_LINE = "WaitAnimation: Char=Caster\r\n"
CHIME_SFX_ID = 100000                       # the rung-2-staged synthetic 880Hz chime (Sounds02/SE00/rung2chime)
CHIME_LINE = f"PlaySound: Sound={CHIME_SFX_ID} ; SoundType=SoundEffect ; Volume=1.0\r\n"


class DriftError(RuntimeError):
    """The stock file's bytes don't match what this script was built against."""


def _read_verified(src: Path, expected_sha256: str) -> bytes:
    if not src.exists():
        raise FileNotFoundError(f"stock file not found: {src}")
    raw = src.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != expected_sha256:
        raise DriftError(
            f"{src} sha256 {got} != expected {expected_sha256} -- "
            "the stock file differs from what rung 3 was derived against; refusing to ship a "
            "'verbatim' copy of content that isn't verified verbatim. Re-derive against the new "
            "content before re-running."
        )
    return raw


def apply_chime(player_seq_text: str) -> str:
    """Insert exactly one new line -- CHIME_LINE -- immediately before the first occurrence of
    FIRST_EXEC_LINE. Raises DriftError if that anchor line is missing (the stock shape changed
    since this script's insertion point was derived)."""
    lines = player_seq_text.splitlines(keepends=True)
    try:
        idx = lines.index(FIRST_EXEC_LINE)
    except ValueError:
        raise DriftError(
            f"expected line {FIRST_EXEC_LINE!r} not found in the copied file -- "
            "its shape has changed since rung 3's --with-chime insertion point was derived; abort "
            "rather than guess"
        ) from None
    lines.insert(idx, CHIME_LINE)
    return "".join(lines)


def build_fresh_id_copy(mod_root: Path, game_path: Path, with_chime: bool) -> dict:
    """Copy stock ef227's two .seq files verbatim to mod_root/ef084/, sha256-drift-guarded.
    If with_chime, ef084/PlayerSequence.seq additionally carries the one-line chime insertion
    (ef084/Sequence.seq is NEVER touched by either mode). Idempotent: always re-derives from the
    untouched stock files, so re-running with a different `with_chime` value flips the shipped
    content back and forth cleanly -- nothing is ever edited in place."""
    result: dict = {"files": {}}

    for name in (PLAYER_SEQ_NAME, SEQ_NAME):
        src = game_path / DONOR_REL_DIR / name
        stock_bytes = _read_verified(src, EXPECTED_SHA256[name])

        if name == PLAYER_SEQ_NAME and with_chime:
            stock_text = stock_bytes.decode("utf-8")
            out_text = apply_chime(stock_text)
            out_bytes = out_text.encode("utf-8")
        else:
            out_bytes = stock_bytes

        dest = mod_root / FRESH_REL_DIR / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        fsutil.atomic_write_bytes(dest, out_bytes)

        # verify the write landed byte-exact (feedback-verify-the-cache-write-lands)
        readback = dest.read_bytes()
        if readback != out_bytes:
            raise RuntimeError(f"write verification failed at {dest} -- readback != what we wrote")

        result["files"][name] = {
            "stock_path": str(src),
            "stock_sha256": hashlib.sha256(stock_bytes).hexdigest(),
            "dest_path": str(dest),
            "dest_sha256": hashlib.sha256(out_bytes).hexdigest(),
            "byte_identical_to_stock": out_bytes == stock_bytes,
        }

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-chime", action="store_true",
        help="hot-add the rung-2-staged chime (Sound=100000) as ef084/PlayerSequence.seq's new "
             "first executable line -- CAST B. Default (omitted) ships the pure verbatim copy -- CAST A.",
    )
    args = parser.parse_args()

    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)   # FF9CustomMap -- the bench's own mod folder

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print(f"donor id     : ef{DONOR_EF_ID:03d} (Bahamut__Full)")
    print(f"fresh id     : ef{FRESH_EF_ID:03d} (stock-absent; SpecialEffect.cs Unused_{FRESH_EF_ID})")
    print(f"mode         : {'--with-chime (CAST B)' if args.with_chime else 'verbatim (CAST A)'}")
    print()

    try:
        result = build_fresh_id_copy(mod_root, game_path, args.with_chime)
    except DriftError as e:
        print(f"DRIFT GUARD TRIPPED -- refusing to ship a copy against unexpected content:\n  {e}",
              file=sys.stderr)
        return 1

    for name, info in result["files"].items():
        print(f"=== {name} ===")
        print(f"stock   : {info['stock_path']}")
        print(f"  sha256: {info['stock_sha256']}")
        print(f"written : {info['dest_path']}")
        print(f"  sha256: {info['dest_sha256']}")
        tag = "BYTE-IDENTICAL to stock" if info["byte_identical_to_stock"] else "MODIFIED (chime inserted)"
        print(f"  [{tag}]")
        print()

    if args.with_chime:
        print(f"ef{FRESH_EF_ID:03d}/PlayerSequence.seq now fires 'PlaySound: Sound={CHIME_SFX_ID}' as its very")
        print(f"first executable line -- CAST B. ef{FRESH_EF_ID:03d}/Sequence.seq is untouched.")
    else:
        print(f"ef{FRESH_EF_ID:03d}/ is a pure byte-identical copy of stock ef{DONOR_EF_ID:03d} -- CAST A.")

    print()
    print("Reminder: this alone does NOT arm the bench's vfx1=84 binding -- that lives in")
    print("rung3.field.toml's Actions.csv row, which is STARTUP-loaded. Deploy + relaunch first")
    print("(see README.md). Re-running this script with/without --with-chime while the game is open")
    print("only changes which .seq CONTENT is on disk for the next cast -- it does not itself require")
    print("a relaunch or redeploy once the field/Actions.csv side has already landed once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
