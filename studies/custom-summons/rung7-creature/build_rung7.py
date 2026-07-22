"""Custom Summons -- rung 7: THE CREATURE RUNG (Tier 3's central bet, zero precedent anywhere).

Deploys, under the bench's PRIVATE fresh-id folder (``Data/SpecialEffects/ef084/`` -- rung 3's own
folder, never the shared donor ``ef227``), the first-ever exercise of the ``FileList.txt``/``Model``
route in this study (and, per the recon's own census, in ANY of FF9's 487 shipped effect folders, and
in no community mod ever found):

  1. ``ef084/FileList.txt`` -- one line, ``Model creature_manifest.sfxmodel``. Read by
     ``SFXData.LoadSFXFromInfo`` (SFXData.cs:244-279), reachable ONLY from a ``.seq`` ``LoadSFX`` op.
  2. ``ef084/creature_manifest.sfxmodel`` -- a JSON ``ModelSequence`` with one ``FBX`` entry whose
     ``Path`` is the bare registered GEO name ``GEO_MAIN_B0_M100`` (Iviv's minted battle-model clone,
     GEO id 6100, ALREADY loaded live in this exact mod folder every time Iviv fights -- rungs 1-6
     proved it, this rung reuses it, copies nothing new). Per the traced resolution chain
     (``ModelFactory.cs`` ``CheckUpscale``/``GetRenameModelPath``/``GetGEOID``/``GetModelType``), only
     the FILENAME token is used to reverse-look up the GEO id via the SAME ``3DModel <id> <NAME>``
     ``DictionaryPatch.txt`` line ordinary battle-model loading already uses -- the ``.sfxmodel``'s own
     directory is irrelevant once the name resolves. ``Movement`` anchors the model to
     ``CasterPosition{X,Y,Z}`` with a static (Origin==Destination) forward+up offset -- an explicit
     ADDITION beyond the recon's minimal proposed entry (which omitted Movement entirely), because the
     recon's own schema notes flag that omitting Movement/Rotation/Scaling leaves the model motionless
     at WORLD ORIGIN (Vector3.zero) -- "wrong place, not invisible" -- which would make a genuine
     mechanism success visually indistinguishable from an off-camera no-op. See README.md "Design
     decisions" for the full rationale.
  3. ``ef084/PlayerSequence.seq`` -- rung 6's own proven 25-line bare sequence
     (``rung6-bare-sequence/bare_player_sequence.seq``, read directly from that sibling directory, never
     duplicated) PLUS exactly one new ``LoadSFX``/``WaitSFXLoaded``/``PlaySFX``/``WaitSFXDone`` quartet
     targeting id 84 -- placed so the creature reveals and holds entirely INSIDE the still-active
     ``SetBackgroundIntensity=0`` blackout window rung 6 already established (the chain recon's
     ``blackout_scope`` finding: the blackout only disables MeshRenderers under ``battlebg.btlModel``,
     never an independently-created FBX GameObject) -- the same reveal-from-black-void staging native
     summons already use, now exercised data-only for the first time.

``UseCamera=False`` on the new ``LoadSFX`` line (a reasoned addition beyond the recon's own minimal
proposed line, which omitted the key) keeps ``SFXDataCamera.currentCameraEngine`` from ever leaving
``NONE`` -- id 84 has no native ``ef###.bytes`` payload to feed the camera plugin, and PLAN.md §3.5
traces camera-owning effects as re-invoking ``FF9SpecialEffectPlugin.dll`` live every frame; this rung
deliberately does not introduce that as a second, unrelated untested variable alongside the FBX-loader
bet. ``SkipSequence=True`` on ``PlaySFX`` prevents ``ef084/Sequence.seq`` (rung 3's still-present,
byte-identical leftover copy of Bahamut's OWN nested choreography -- unconditionally re-read by
``SFXData.LoadSFX`` regardless of the FileList.txt/JSON-mesh branch, SFXData.cs:174) from re-arming as a
second, duplicate-damage parallel thread alongside this file's own ``EffectPoint`` pair.

FBX ASSET DEPENDENCY (verified, not deployed by this script): Iviv's ``GEO_MAIN_B0_M100`` (id 6100) is
staged by the bench's OWN ``[[playable]]`` deploy (``examples/thirteenth-character/iviv.field.toml``) --
this script only VERIFIES its presence (the .fbx, the idle .anim, and the two DictionaryPatch.txt
registration lines) and warns loudly if any piece is missing; it never copies or mints it. If it's ever
absent, re-run the bench's own field deploy first.

Modes:

  --creature   (default) deploy the rung-7 test: FileList.txt + creature_manifest.sfxmodel + the
               29-line rung-7 sequence + (re)deploy the reused RisingRing.sfxmodel + verify the GEO
               6100 asset is present.
  --restore    undo rung 7's own additions ONLY, landing back on RUNG 6's proven bare state (NOT rung
               3's donor-copy baseline -- unlike every earlier rung's own --restore, rung 7's sequence
               is layered on rung 6's committed content, not on a stock SE-derived file, so "restore"
               here means "rung 6 again"): removes FileList.txt and creature_manifest.sfxmodel,
               rewrites PlayerSequence.seq back to rung 6's own bare_player_sequence.seq (sha-guarded
               against that file's known-good hash), and leaves RisingRing.sfxmodel deployed (rung 6's
               bare sequence still references it).

Idempotent in every mode: every write re-derives its content from this directory's (or a named
sibling's) committed repo copy every run, never edits in place, and verifies the write landed byte-exact
(feedback-verify-the-cache-write-lands).

Usage (game already running -- recast-only, no relaunch, no redeploy -- SAME as rungs 2-6):

    py studies/custom-summons/rung7-creature/build_rung7.py             # default = --creature (this rung's test)
    py studies/custom-summons/rung7-creature/build_rung7.py --creature  # deploy FileList.txt + manifest + sequence
    py studies/custom-summons/rung7-creature/build_rung7.py --restore   # back to rung 6's bare state

See README.md for the full test procedure, the beat-by-beat expected experience, the failure-mode
table (CRASH-class vs NO-OP-class, per the chain recon's risk register), and ``revert_rung7.py``.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung7-creature -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config, fsutil          # noqa: E402

# --------------------------------------------------------------------------- ids / paths
FRESH_EF_ID = 84                            # rung 3's private fresh-id folder (Unused_84) -- reused, not re-minted
FRESH_REL_DIR = f"StreamingAssets/Data/SpecialEffects/ef{FRESH_EF_ID:03d}"
PLAYER_SEQ_NAME = "PlayerSequence.seq"
PLAYER_SEQ_REL = f"{FRESH_REL_DIR}/{PLAYER_SEQ_NAME}"

# --------------------------------------------------------------------------- rung 6's bare sequence (read, not copied)
RUNG6_DIR = REPO / "studies" / "custom-summons" / "rung6-bare-sequence"
RUNG6_BARE_SEQ_REPO_PATH = RUNG6_DIR / "bare_player_sequence.seq"
# The exact sha256 of rung 6's committed file at the time this script was written (independently
# confirmed this session to match the LIVE deployed ef084/PlayerSequence.seq byte-for-byte) -- the
# drift guard for --restore, which re-derives ef084's content from this file every run.
RUNG6_BARE_SEQ_SHA256 = "ae869ec52b5169681f00637dc8358cd8c23a77af3b96e788b159d39cc225329b"

# --------------------------------------------------------------------------- rung 7's own committed sources
RUNG7_SEQ_REPO_PATH = HERE / "rung7_player_sequence.seq"          # committed, 100% our content (rung 6 + delta)
CREATURE_MANIFEST_REPO_PATH = HERE / "creature_manifest.sfxmodel"  # committed, 100% our content
FILELIST_REPO_PATH = HERE / "FileList.txt"                         # committed, 100% our content

CREATURE_MANIFEST_NAME = "creature_manifest.sfxmodel"
FILELIST_NAME = "FileList.txt"
CREATURE_MANIFEST_REL = f"{FRESH_REL_DIR}/{CREATURE_MANIFEST_NAME}"
FILELIST_REL = f"{FRESH_REL_DIR}/{FILELIST_NAME}"

# --------------------------------------------------------------------------- the reused rung-5 sprite (same as rung 6)
RUNG5_DIR = REPO / "studies" / "custom-summons" / "rung5-particles"
BESPOKE_SPRITE_REPO_PATH = RUNG5_DIR / "rung5_sprite.sfxmodel"
BESPOKE_SPRITE_NAME = "RisingRing.sfxmodel"
BESPOKE_SPRITE_REL = f"{FRESH_REL_DIR}/{BESPOKE_SPRITE_NAME}"

# --------------------------------------------------------------------------- the verified-not-deployed FBX asset
# Iviv's custom_battle_model (content/playable.py mint, base id 6100) -- staged by the bench's own
# [[playable]] deploy, NOT by this script. Presence-checked only.
GEO_FBX_REL = "StreamingAssets/Assets/Resources/Models/2/6100/6100.fbx"
GEO_ANIM_REL = "StreamingAssets/Assets/Resources/Animations/6100/1010000.anim"
DICT_PATCH_REL = "DictionaryPatch.txt"
DICT_MODEL_LINE = "3DModel 6100 GEO_MAIN_B0_M100"
DICT_ANIM_LINE = "3DModelAnimation 1010000 ANH_MAIN_B0_M100_000"


class DriftError(RuntimeError):
    """A file this script reads (but doesn't own) doesn't match the bytes it was derived against."""


def _read_verified(path: Path, expected_sha256: str, desc: str) -> tuple[bytes, str]:
    if not path.exists():
        raise FileNotFoundError(f"{desc} not found: {path}")
    raw = path.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != expected_sha256:
        raise DriftError(
            f"{path} sha256 {got} != expected {expected_sha256} -- {desc} has changed since this "
            "script was derived against it; refusing to build against unverified content."
        )
    return raw, raw.decode("utf-8")


def _read_repo_file(path: Path, desc: str) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"{desc} not found in repo: {path}")
    return path.read_bytes()


def _write(dest: Path, data: bytes) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_bytes(dest, data)
    readback = dest.read_bytes()
    if readback != data:
        raise RuntimeError(f"write verification failed at {dest} -- readback != what we wrote")
    return hashlib.sha256(data).hexdigest()


def _remove_if_present(dest: Path) -> bool:
    if dest.exists():
        dest.unlink()
        return True
    return False


def check_fbx_asset(game_path: Path, mod_root: Path) -> dict:
    """Presence-only check for Iviv's GEO 6100 (fbx + idle anim + the two DictionaryPatch.txt
    registration lines). Informational -- prints a loud warning if anything is missing, but (matching
    rung 5's own precedent for its stock-aura existence check) does not abort the deploy: a missing
    asset is a bench-state problem outside this rung's own job to fix."""
    fbx_path = mod_root / GEO_FBX_REL
    anim_path = mod_root / GEO_ANIM_REL
    dict_path = mod_root / DICT_PATCH_REL

    fbx_exists = fbx_path.exists()
    anim_exists = anim_path.exists()
    dict_text = dict_path.read_text(encoding="utf-8", errors="replace") if dict_path.exists() else ""
    model_line_present = DICT_MODEL_LINE in dict_text
    anim_line_present = DICT_ANIM_LINE in dict_text

    return {
        "fbx_path": str(fbx_path), "fbx_exists": fbx_exists,
        "anim_path": str(anim_path), "anim_exists": anim_exists,
        "dict_path": str(dict_path),
        "model_line_present": model_line_present,
        "anim_line_present": anim_line_present,
        "all_ok": fbx_exists and anim_exists and model_line_present and anim_line_present,
    }


def build(mod_root: Path, game_path: Path, mode: str) -> dict:
    """mode: "creature" (this rung's test -- FileList.txt + manifest + the rung-7 sequence + the
    reused rung-5 sprite) | "restore" (back to rung 6's own proven bare state -- FileList.txt and the
    manifest removed, sequence = rung 6's bare_player_sequence.seq verbatim, sprite still deployed
    since rung 6's own sequence still references it)."""
    assert mode in ("creature", "restore"), mode

    rung6_bytes, rung6_text = _read_verified(
        RUNG6_BARE_SEQ_REPO_PATH, RUNG6_BARE_SEQ_SHA256, "rung 6's committed bare_player_sequence.seq"
    )

    if mode == "creature":
        out_bytes = _read_repo_file(RUNG7_SEQ_REPO_PATH, "rung 7's player sequence")
        out_text = out_bytes.decode("utf-8")
        seq_source = str(RUNG7_SEQ_REPO_PATH)
    else:
        out_bytes, out_text = rung6_bytes, rung6_text
        seq_source = str(RUNG6_BARE_SEQ_REPO_PATH)

    dest = mod_root / FRESH_REL_DIR / PLAYER_SEQ_NAME
    seq_sha256 = _write(dest, out_bytes)

    diff = "".join(difflib.unified_diff(
        rung6_text.splitlines(keepends=True), out_text.splitlines(keepends=True),
        fromfile=f"rung6/{RUNG6_BARE_SEQ_REPO_PATH.name}",
        tofile=f"FF9CustomMap/{PLAYER_SEQ_REL}",
    ))

    result: dict = {
        "mode": mode,
        "seq_source": seq_source,
        "seq_dest": str(dest),
        "seq_sha256": seq_sha256,
        "seq_is_rung6_bare": out_bytes == rung6_bytes,
        "seq_diff_vs_rung6": diff,
        "filelist": None, "filelist_removed": False,
        "manifest": None, "manifest_removed": False,
        "sprite": None,
    }

    # RisingRing.sfxmodel: deployed in BOTH modes -- rung 6's bare sequence (the --restore target)
    # references it too, unlike rung 6's own --restore which went further back to rung 3's baseline
    # (which never had any CreateVisualEffect line at all).
    sprite_data = _read_repo_file(BESPOKE_SPRITE_REPO_PATH, "rung 5's bespoke sprite")
    sprite_dest = mod_root / BESPOKE_SPRITE_REL
    sprite_sha256 = _write(sprite_dest, sprite_data)
    result["sprite"] = {
        "repo_path": str(BESPOKE_SPRITE_REPO_PATH), "dest_path": str(sprite_dest), "sha256": sprite_sha256,
    }

    if mode == "creature":
        filelist_data = _read_repo_file(FILELIST_REPO_PATH, "FileList.txt")
        filelist_dest = mod_root / FILELIST_REL
        filelist_sha256 = _write(filelist_dest, filelist_data)
        result["filelist"] = {
            "repo_path": str(FILELIST_REPO_PATH), "dest_path": str(filelist_dest), "sha256": filelist_sha256,
        }

        manifest_data = _read_repo_file(CREATURE_MANIFEST_REPO_PATH, "creature_manifest.sfxmodel")
        manifest_dest = mod_root / CREATURE_MANIFEST_REL
        manifest_sha256 = _write(manifest_dest, manifest_data)
        result["manifest"] = {
            "repo_path": str(CREATURE_MANIFEST_REPO_PATH), "dest_path": str(manifest_dest), "sha256": manifest_sha256,
        }
    else:
        result["filelist_removed"] = _remove_if_present(mod_root / FILELIST_REL)
        result["manifest_removed"] = _remove_if_present(mod_root / CREATURE_MANIFEST_REL)

    result["fbx_check"] = check_fbx_asset(game_path, mod_root)

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--creature", action="store_true",
        help="deploy the rung-7 test: FileList.txt + creature_manifest.sfxmodel + the 29-line rung-7 "
             "sequence + the reused RisingRing.sfxmodel. DEFAULT if no flag given.",
    )
    group.add_argument(
        "--restore", action="store_true",
        help="undo rung 7's own additions -- back to rung 6's proven bare sequence (FileList.txt and "
             "the manifest removed; RisingRing.sfxmodel stays deployed, rung 6 still uses it).",
    )
    args = parser.parse_args()

    mode = "restore" if args.restore else "creature"   # creature is the default -- this rung's test

    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)   # FF9CustomMap -- the bench's own mod folder

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print(f"private id   : ef{FRESH_EF_ID:03d} (rung 3's fresh-id folder -- the file this rung edits)")
    print(f"mode         : {'CREATURE (rung-7 test)' if mode == 'creature' else 'RESTORE (rung-6 bare state)'}")
    print()

    try:
        result = build(mod_root, game_path, mode)
    except DriftError as e:
        print(f"DRIFT GUARD TRIPPED -- refusing to build against unexpected content:\n  {e}",
              file=sys.stderr)
        return 1

    print(f"=== {PLAYER_SEQ_REL} ===")
    print(f"source       : {result['seq_source']}")
    print(f"written      : {result['seq_dest']}")
    print(f"  sha256     : {result['seq_sha256']}")
    tag = "BYTE-IDENTICAL to rung 6's bare_player_sequence.seq" if result["seq_is_rung6_bare"] \
        else "RUNG 7 (rung 6's 25 lines + the LoadSFX/WaitSFXLoaded/PlaySFX/WaitSFXDone quartet)"
    print(f"  [{tag}]")
    print()
    print("--- unified diff vs rung 6's bare_player_sequence.seq ---")
    print(result["seq_diff_vs_rung6"] if result["seq_diff_vs_rung6"] else "(no diff -- byte-identical to rung 6)")

    sp = result["sprite"]
    print()
    print("=== bespoke sprite deploy (reused from rung 5, same as rung 6) ===")
    print(f"repo copy    : {sp['repo_path']}")
    print(f"deployed to  : {sp['dest_path']}")
    print(f"  sha256     : {sp['sha256']}")

    if result["filelist"] is not None:
        fl = result["filelist"]
        print()
        print(f"=== {FILELIST_REL} (FIRST-EVER FileList.txt in this study) ===")
        print(f"repo copy    : {fl['repo_path']}")
        print(f"deployed to  : {fl['dest_path']}")
        print(f"  sha256     : {fl['sha256']}")
    elif result["filelist_removed"]:
        print()
        print(f"(removed the deployed ef{FRESH_EF_ID:03d}/{FILELIST_NAME})")

    if result["manifest"] is not None:
        mf = result["manifest"]
        print()
        print(f"=== {CREATURE_MANIFEST_REL} ===")
        print(f"repo copy    : {mf['repo_path']}")
        print(f"deployed to  : {mf['dest_path']}")
        print(f"  sha256     : {mf['sha256']}")
    elif result["manifest_removed"]:
        print()
        print(f"(removed the deployed ef{FRESH_EF_ID:03d}/{CREATURE_MANIFEST_NAME})")

    fc = result["fbx_check"]
    print()
    print("=== GEO 6100 asset presence check (verified only -- never copied by this script) ===")
    print(f"fbx    : {fc['fbx_path']}")
    print(f"         exists = {fc['fbx_exists']}")
    print(f"anim   : {fc['anim_path']}")
    print(f"         exists = {fc['anim_exists']}")
    print(f"DictionaryPatch.txt model line present : {fc['model_line_present']}  ({DICT_MODEL_LINE!r})")
    print(f"DictionaryPatch.txt anim  line present : {fc['anim_line_present']}  ({DICT_ANIM_LINE!r})")
    if fc["all_ok"]:
        print("  [OK -- the creature asset is fully staged; PlaySFX should find it]")
    else:
        print("  ** MISSING PIECE(S) -- the creature will silently fail to render (a NO-OP, not a crash) **")
        print("  ** re-run the bench's own [[playable]] field deploy (iviv.field.toml) before casting **")

    print()
    if mode == "creature":
        print(f"ef{FRESH_EF_ID:03d}/ now carries FileList.txt + creature_manifest.sfxmodel + the 29-op rung-7")
        print("sequence. Re-enter a battle on bench field 30300 (game already running -- no relaunch, no")
        print("redeploy) and recast \"Bahamut Cinema\" from Iviv's Spark command.")
    else:
        print(f"ef{FRESH_EF_ID:03d}/ is back to rung 6's own proven bare state: no FileList.txt, no")
        print("creature_manifest.sfxmodel, PlayerSequence.seq byte-identical to rung 6's committed file.")
    print()
    print("Reminder: ef227 (the shared Bahamut donor), ef084/Sequence.seq (rung 3's leftover, never")
    print("read by either state), and the rung-2 staged chime are all UNTOUCHED by this script.")
    print("See README.md for the full test procedure, expected experience, failure modes, and")
    print("revert_rung7.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
