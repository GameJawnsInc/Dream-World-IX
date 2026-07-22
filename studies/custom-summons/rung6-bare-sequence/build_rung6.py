"""Custom Summons -- rung 6: the FRESH-ID BARE SEQUENCE (Tier 3 no-native-content probe).

Overrides the bench's PRIVATE fresh-id copy (``Data/SpecialEffects/ef084/PlayerSequence.seq`` --
rung 3's own folder, never the shared donor ``ef227``) with a **wholly hand-authored** sequence that
contains **zero ``LoadSFX`` of any native id** -- no ``Bahamut__Full``, no stock creature, no stock
camera hookup, nothing Square-Enix at all in the presentation. Everything the cast plays is either
a stock caster ANIMATION name (``MP_IDLE_TO_CHANT``/``MP_CHANT``/``MP_MAGIC``/``Idle`` -- these are
just skeletal-clip identifiers on the caster's own model, not "native content" in the sense this rung
is testing) or kit-authored content: the rung-2 chime (``PlaySound: Sound=100000``) and the rung-5
bespoke sprite (``CreateVisualEffect: ... SFXModel=Data/SpecialEffects/ef084/RisingRing.sfxmodel``).

WHY THIS PROVES SOMETHING NEW (over rungs 1/3/4/5): every prior rung's cinematic ultimately runs
through the real Bahamut donor content -- ``LoadSFX: SFX=Bahamut__Full ; UseCamera=True`` (rung
1/3) and/or its nested ``ef227/Sequence.seq`` (rung 4). Rung 6 deletes that line (and every other
Bahamut-specific op) entirely and asks: does a summon-CLASS command (``cmd_no=46``, a minted command
menu entry) still play out gracefully -- caster animates in and out, sound plays, particle renders,
damage lands, control returns -- with **nothing native left to fall back on**? A "yes" answer settles
Tier 3 (PLAN.md §4/§9): a fully composed ORIGINAL summon needs no donor id at all, just a fresh
``ef###`` folder + a self-contained ``.seq``. It also incidentally observes the camera-ownerless
case (recon ``camera_verdict``): with no ``LoadSFX{UseCamera=True}`` ever called, ``SFXDataCamera.
currentCameraEngine`` never leaves ``NONE`` and the plain default battle camera runs the whole cast
-- this script deliberately omits ``PlayCamera``/``ResetCamera`` too (recon flagged calling
``PlayCamera`` bare as genuinely UNTESTED -- see README.md "Open risks" -- so this rung answers "what
does a camera-ownerless effect look like", not "is PlayCamera-without-LoadSFX safe").

ORCHESTRATOR DESIGN DECISION (recorded here, not re-litigated): PLAN.md's rung 6 wording ("id N")
could be read as requiring a SECOND fresh id distinct from 84. We reuse id 84 instead -- swapping
``ef084/PlayerSequence.seq``'s CONTENT for the bare sequence, recast-only, no relaunch, no redeploy.
The fresh-id HALF of rung 6's claim (a stock-unclaimed folder id resolves gracefully end-to-end) was
already fully proven by rung 3 (★★ 2026-07-21, both casts). What rung 6 actually adds is the
NO-NATIVE-CONTENT half -- and that only requires swapping what's IN the folder, not minting yet
another one. This also keeps the whole rung-3/5/6 lineage inside ONE bench folder, matching the
mod-folder shadowing law (deploying-ff9-mods skill): ``.seq`` content is zero-cache, re-read per
cast, so switching id 84's content between "verbatim Bahamut copy" (rung 3 baseline), "+ particle"
(rung 5), and "fully bare" (this rung) is always a pure recast, never a relaunch.

THE BARE SEQUENCE (``bare_player_sequence.seq``, this directory -- 100% hand-authored, COMMITTABLE,
unlike every other ``.seq`` this study has touched, which are all SE-derived copies/edits and are
therefore NEVER committed): 25 operation lines, composed from the recon's own protocol/content
split (grammar_reference) -- the content HALF (LoadSFX/PlaySFX/WaitSFXLoaded/WaitSFXDone, all
Bahamut-specific) is deleted outright; the protocol HALF (WaitAnimation/Message/SetupReflect/chant
animation/closeout Idle-turn) is kept verbatim, because the recon traced every one of those ops as
content-independent DSL plumbing, not summon-specific dressing. See README.md for the full
line-by-line rationale and the (deliberately reasoned) omissions vs the stock 36-line template.

WHAT THE SEQUENCE COMPOSES (see README.md "Expected experience" for the full beat-by-beat):
  - the caster's own chant animation cycle (``MP_IDLE_TO_CHANT`` -> ``MP_CHANT`` loop -> ``MP_MAGIC``
    -> ``Idle``) -- no summon creature ever appears;
  - the rung-2 chime (``PlaySound: Sound=100000``) and the rung-5 bespoke magenta ring
    (``CreateVisualEffect: ... RisingRing.sfxmodel``), both firing during the chant hold;
  - a partial background dim (0.5, not 0 -- a deliberate stylistic choice, unrelated to the
    FIGURE-VISIBILITY LAW below) during the hold, restored to full brightness (1.0) well BEFORE the
    damage beats fire;
  - ``EffectPoint: Char=AllTargets ; Type=Effect`` then ``EffectPoint: Char=Everyone ; Type=Figure``,
    both scheduled AFTER the brightness restore + a 12-tick settle (the FIGURE-VISIBILITY LAW from
    rung 4: a ``Type=Figure`` damage-number popup rendered while ``SetBackgroundIntensity=0`` is
    still in effect is invisibly washed out -- this sequence never lets that overlap happen);
  - the full stock closeout idiom (``PlayAnimation Idle`` / ``Turn BaseAngle=Default`` / ``WaitTurn``)
    kept verbatim -- ``Anim=Idle`` is the engine's own canonical "release this command's motion lock"
    signal (``UnifiedBattleSequencer.cs:505-516`` -> ``btl_mot.EndCommandMotion``), not a cosmetic
    choice; dropping it would leave ``cmd.info.cmd_motion`` stale (recon
    ``caster_animation_closeout``).

Because ``ef084/Sequence.seq`` (rung 3's private copy of the donor's nested file) is never loaded by
a sequence with no ``LoadSFX`` line, it stays completely unreferenced by this rung -- present on disk
(rung 3 left it there), inert, untouched, never read.

DEPENDS ON: rung 3's private ``ef084/`` folder + the bench's ``vfx1=84`` Actions.csv binding
(already deployed + relaunched once, per rung 3 -- no further relaunch needed); rung 5's bespoke
sprite (``rung5-particles/rung5_sprite.sfxmodel``, read directly from that sibling directory and
redeployed to ``ef084/RisingRing.sfxmodel`` -- the SAME file rung 5 already proved renders, not a
new copy); the rung-2 minted chime (``Sound=100000``, already armed in the manifest, untouched by
this script).

PROVENANCE: ``bare_player_sequence.seq`` (this directory) is 100% hand-authored text -- zero
Square-Enix bytes, zero derivation from any stock ``.seq`` file's CONTENT (only its DSL vocabulary,
which is not copyrightable expression any more than a TOML key name is) -- and IS committed, exactly
like rung 5's ``rung5_sprite.sfxmodel``. This is the ONE rung in the study so far whose PlayerSequence
deploy is fully our own text rather than an edited Square-Enix copy.

Usage (game already running -- recast-only, no relaunch, no redeploy):

    py studies/custom-summons/rung6-bare-sequence/build_rung6.py            # default = --bare (this rung's test)
    py studies/custom-summons/rung6-bare-sequence/build_rung6.py --bare     # deploy the bare sequence + sprite
    py studies/custom-summons/rung6-bare-sequence/build_rung6.py --restore  # verbatim rung-3 state, sprite removed

Idempotent in every mode: ``--bare`` re-copies ``bare_player_sequence.seq`` from this directory's repo
copy every run (never edited in place) and re-deploys rung 5's sprite from its own repo copy;
``--restore`` re-derives ``ef084/PlayerSequence.seq`` from the untouched stock ``ef227/
PlayerSequence.seq`` every run (sha-guarded, identical drift guard to ``rung3-fresh-id/build_rung3.py``
and ``rung5-particles/build_rung5.py``) and removes the sprite deploy if present.

See README.md for the full test procedure, the beat-by-beat expected experience, the failure-mode
table (incl. in-battle recovery if the cast never completes), and ``revert_rung6.py``.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung6-bare-sequence -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config, fsutil          # noqa: E402

# --------------------------------------------------------------------------- ids / paths
DONOR_EF_ID = 227                           # Bahamut__Full's real donor folder (SpecialEffect.cs:99)
FRESH_EF_ID = 84                            # rung 3's private fresh-id folder (Unused_84) -- reused, not re-minted

DONOR_REL_DIR = f"StreamingAssets/Data/SpecialEffects/ef{DONOR_EF_ID:03d}"
FRESH_REL_DIR = f"StreamingAssets/Data/SpecialEffects/ef{FRESH_EF_ID:03d}"
PLAYER_SEQ_NAME = "PlayerSequence.seq"
PLAYER_SEQ_REL = f"{FRESH_REL_DIR}/{PLAYER_SEQ_NAME}"

# The exact sha256 rung 3/5 independently verified for stock ef227/PlayerSequence.seq -- the drift
# guard for --restore (which re-derives the verbatim rung-3 baseline from this same stock file).
# --bare does NOT depend on this file's content at all (the bare sequence is wholly our own text),
# but we still read+report it for cross-rung sanity (confirms the shared donor is still untouched).
EXPECTED_SHA256 = "4bc643bfb3ec478dcc1f5b51261f59637faac9d775cccd38c0055afee14ece63"

# --------------------------------------------------------------------------- the bare sequence (OURS)
BARE_SEQ_REPO_PATH = HERE / "bare_player_sequence.seq"          # committed, 100% our content

# --------------------------------------------------------------------------- the reused rung-5 sprite
# Rung 6's bare sequence references the SAME bespoke sprite rung 5 already proved renders -- not a new
# copy. Read directly from the sibling rung5-particles/ directory (the repo's one source of truth for
# this asset) rather than duplicating the JSON here.
RUNG5_DIR = REPO / "studies" / "custom-summons" / "rung5-particles"
BESPOKE_SPRITE_REPO_PATH = RUNG5_DIR / "rung5_sprite.sfxmodel"
BESPOKE_SPRITE_NAME = "RisingRing.sfxmodel"
BESPOKE_SPRITE_REL = f"{FRESH_REL_DIR}/{BESPOKE_SPRITE_NAME}"   # mod-folder deploy path (relative to mod_root)
BESPOKE_SPRITE_SEQ_PATH = f"Data/SpecialEffects/ef{FRESH_EF_ID:03d}/{BESPOKE_SPRITE_NAME}"  # the .seq-line value


class DriftError(RuntimeError):
    """The stock donor's bytes don't match what rung 3/5/6 were derived against (--restore only)."""


def _read_verified_stock(game_path: Path) -> tuple[Path, bytes, str]:
    src = game_path / DONOR_REL_DIR / PLAYER_SEQ_NAME
    if not src.exists():
        raise FileNotFoundError(f"stock file not found: {src}")
    raw = src.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != EXPECTED_SHA256:
        raise DriftError(
            f"{src} sha256 {got} != expected {EXPECTED_SHA256} -- the stock file differs from what "
            "rungs 3/5/6 were derived against; refusing to restore against unverified content. "
            "Re-derive the baseline before re-running --restore."
        )
    return src, raw, raw.decode("utf-8")


def _read_bare_sequence() -> tuple[bytes, str]:
    if not BARE_SEQ_REPO_PATH.exists():
        raise FileNotFoundError(f"bare sequence not found in repo: {BARE_SEQ_REPO_PATH}")
    raw = BARE_SEQ_REPO_PATH.read_bytes()
    return raw, raw.decode("utf-8")


def deploy_bespoke_sprite(mod_root: Path) -> dict:
    """Copy rung 5's committed bespoke sprite JSON (read from its own directory, not duplicated
    here) to this rung's mod-folder path (ef084/RisingRing.sfxmodel -- the exact path the bare
    sequence's CreateVisualEffect line references). Idempotent, no drift guard needed -- it's our
    own content, re-derived from the repo copy every run."""
    if not BESPOKE_SPRITE_REPO_PATH.exists():
        raise FileNotFoundError(f"bespoke sprite not found in repo: {BESPOKE_SPRITE_REPO_PATH}")
    data = BESPOKE_SPRITE_REPO_PATH.read_bytes()

    dest = mod_root / BESPOKE_SPRITE_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_bytes(dest, data)

    readback = dest.read_bytes()
    if readback != data:
        raise RuntimeError(f"write verification failed at {dest} -- readback != what we wrote")

    return {
        "repo_path": str(BESPOKE_SPRITE_REPO_PATH),
        "dest_path": str(dest),
        "sha256": hashlib.sha256(data).hexdigest(),
        "seq_reference_path": BESPOKE_SPRITE_SEQ_PATH,
    }


def remove_bespoke_sprite(mod_root: Path) -> bool:
    """Delete a deployed ef084/RisingRing.sfxmodel, if present. Called by --restore so that
    reverting to rung 3's baseline doesn't leave the sprite sitting around unreferenced (harmless to
    gameplay once the .seq no longer names it, but "restore verbatim" should mean it). Returns
    whether a file was actually removed."""
    dest = mod_root / BESPOKE_SPRITE_REL
    if dest.exists():
        dest.unlink()
        return True
    return False


def build(mod_root: Path, game_path: Path, mode: str) -> dict:
    """mode: "bare" (this rung's test -- 100% hand-authored, no-native-content sequence + the
    reused rung-5 sprite) | "restore" (verbatim rung-3 baseline -- byte-identical copy of stock
    ef227/PlayerSequence.seq, sprite removed). Always rewrites ef084/PlayerSequence.seq from its
    respective source (never edited in place), so switching modes back and forth always converges
    on the same bytes."""
    assert mode in ("bare", "restore"), mode

    stock_path = game_path / DONOR_REL_DIR / PLAYER_SEQ_NAME
    stock_bytes, stock_text, stock_sha256 = b"", "", None
    bare_repo_path = None

    if mode == "restore":
        # load-bearing drift guard -- --restore's whole job is a verbatim copy of THIS file.
        _, stock_bytes, stock_text = _read_verified_stock(game_path)
        stock_sha256 = hashlib.sha256(stock_bytes).hexdigest()
        out_bytes, out_text = stock_bytes, stock_text
    else:
        # informational only for --bare -- confirms the shared donor is still untouched by every
        # prior rung; the bare sequence's own content never depends on these bytes.
        if stock_path.exists():
            stock_bytes = stock_path.read_bytes()
            stock_text = stock_bytes.decode("utf-8")
            stock_sha256 = hashlib.sha256(stock_bytes).hexdigest()
        out_bytes, out_text = _read_bare_sequence()
        bare_repo_path = str(BARE_SEQ_REPO_PATH)

    dest = mod_root / FRESH_REL_DIR / PLAYER_SEQ_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_bytes(dest, out_bytes)

    # verify the write landed byte-exact (feedback-verify-the-cache-write-lands)
    readback = dest.read_bytes()
    if readback != out_bytes:
        raise RuntimeError(f"write verification failed at {dest} -- readback != what we wrote")

    diff = "".join(difflib.unified_diff(
        stock_text.splitlines(keepends=True), out_text.splitlines(keepends=True),
        fromfile=f"stock/{DONOR_REL_DIR}/{PLAYER_SEQ_NAME}",
        tofile=f"FF9CustomMap/{FRESH_REL_DIR}/{PLAYER_SEQ_NAME}",
    ))

    result: dict = {
        "mode": mode,
        "stock_path": str(stock_path),
        "stock_sha256": stock_sha256,
        "bare_repo_path": bare_repo_path,
        "dest_path": str(dest),
        "dest_sha256": hashlib.sha256(out_bytes).hexdigest(),
        "byte_identical_to_stock": out_bytes == stock_bytes,
        "diff": diff,
        "sprite": None,
        "sprite_removed": False,
    }

    if mode == "bare":
        result["sprite"] = deploy_bespoke_sprite(mod_root)
    else:
        result["sprite_removed"] = remove_bespoke_sprite(mod_root)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--bare", action="store_true",
        help="deploy the rung-6 bare sequence (bare_player_sequence.seq) + the reused rung-5 sprite "
             "-- this rung's test. DEFAULT if no flag given.",
    )
    group.add_argument(
        "--restore", action="store_true",
        help="restore ef084/PlayerSequence.seq to rung 3's verbatim baseline (byte-identical copy of "
             "stock ef227) and remove the deployed RisingRing.sfxmodel.",
    )
    args = parser.parse_args()

    mode = "restore" if args.restore else "bare"   # bare is the default -- this rung's test

    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)   # FF9CustomMap -- the bench's own mod folder

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print(f"donor id     : ef{DONOR_EF_ID:03d} (Bahamut__Full, untouched by this rung)")
    print(f"private id   : ef{FRESH_EF_ID:03d} (rung 3's fresh-id folder -- the file this rung edits)")
    print(f"mode         : {'BARE (rung-6 test)' if mode == 'bare' else 'RESTORE (verbatim rung-3 baseline)'}")
    print()

    try:
        result = build(mod_root, game_path, mode)
    except DriftError as e:
        print(f"DRIFT GUARD TRIPPED -- refusing to build against unexpected content:\n  {e}",
              file=sys.stderr)
        return 1

    print(f"=== {PLAYER_SEQ_REL} ===")
    if result["stock_sha256"]:
        print(f"stock donor  : {result['stock_path']}")
        print(f"  sha256     : {result['stock_sha256']}")
    if result["bare_repo_path"]:
        print(f"bare source  : {result['bare_repo_path']}")
    print(f"written      : {result['dest_path']}")
    print(f"  sha256     : {result['dest_sha256']}")
    tag = "BYTE-IDENTICAL to stock (verbatim rung-3 baseline)" if result["byte_identical_to_stock"] \
        else "BARE (fully hand-authored, zero LoadSFX / zero native content)"
    print(f"  [{tag}]")
    print()
    print("--- unified diff vs stock ef227/PlayerSequence.seq ---")
    print(result["diff"] if result["diff"] else "(no diff -- byte-identical to stock)")

    if result["sprite"] is not None:
        sp = result["sprite"]
        print()
        print("=== bespoke sprite deploy (reused from rung 5) ===")
        print(f"repo copy    : {sp['repo_path']}")
        print(f"deployed to  : {sp['dest_path']}")
        print(f"  sha256     : {sp['sha256']}")
        print(f".seq reference value: SFXModel={sp['seq_reference_path']}")
    elif result["sprite_removed"]:
        print()
        print(f"(removed the deployed ef{FRESH_EF_ID:03d}/{BESPOKE_SPRITE_NAME} -- restore means it too.)")

    print()
    if mode == "bare":
        print(f"ef{FRESH_EF_ID:03d}/PlayerSequence.seq now runs the RUNG-6 BARE SEQUENCE -- 25 operation")
        print("lines, zero LoadSFX of any native id. Re-enter a battle on bench field 30300 (game")
        print("already running -- no relaunch, no redeploy) and recast \"Bahamut Cinema\" from Iviv's")
        print("Spark command. ef084/Sequence.seq exists on disk (rung 3's leftover) but is never read --")
        print("there is no LoadSFX line in this sequence to nest-load it.")
    else:
        print(f"ef{FRESH_EF_ID:03d}/ is back to rung 3's own baseline: a byte-identical copy of stock")
        print(f"ef{DONOR_EF_ID:03d}, no bare-sequence content, no RisingRing.sfxmodel alongside it.")
    print()
    print("Reminder: ef227 (the shared donor), the rung-2 chime manifest, and ef084/Sequence.seq are")
    print("all UNTOUCHED by this script either way. See README.md for the full test procedure,")
    print("expected experience, failure modes, and revert_rung6.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
