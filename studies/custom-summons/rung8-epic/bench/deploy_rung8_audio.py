#!/usr/bin/env python3
"""RUNG 8 -- deploy the three minted NIMBRA sfx ids (100001-100003) into a live mod folder.

    py studies/custom-summons/rung8-epic/bench/deploy_rung8_audio.py --mod-folder FF9CustomMap
    py studies/custom-summons/rung8-epic/bench/deploy_rung8_audio.py --dry-run --out <dir>   # staged

WHY THIS SCRIPT EXISTS AT ALL. Every other rung-8 deploy step has a CLI verb (``deploy_field.py``,
``ff9mapkit summon-deploy``). The audio does not, for one reason: ``ff9mapkit audio-import --new-song``
cannot pin a RESOURCE ID, so it would mint our cues as ``Sounds02/SE00/custom100001`` instead of the
``Sounds02/SE00/nimbra_drone`` the storyboard, the audio lane's ``manifest_fragment.json`` and the staged
bench all name. The id is what the ``.seq`` plays, so a mismatched resource id would still WORK -- and
would quietly make the deployed tree disagree with every artefact describing it. This script pins both.

IT IS IDEMPOTENT. ``sound.mint_song`` refuses an id already in the manifest (by design -- silently
re-pointing a live id is how you lose one). Re-running this instead REPLACES the ``.ogg`` in place and
leaves the manifest row alone, which is what "I re-rendered the drone, push it again" actually means.

THE RELAUNCH LAW (STORYBOARD 5.2). ``SoundMetaData``'s id table is read ONCE at process start. A brand-new
id needs ONE relaunch before its first cast -- the same relaunch that registers the ``3DModel 6400`` line.
REPLACING the bytes at an already-registered id is assumed to need one too (unproven; assume yes).
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNG8 = HERE.parent
REPO = RUNG8.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(RUNG8 / "audio"))

from ff9mapkit import config, sound              # noqa: E402

WAV_DIR = RUNG8 / "stage" / "audio" / "wav"
MODULES = ("make_nimbra_drone", "make_nimbra_whispers", "make_nimbra_strike")


def cues() -> list:
    out = []
    for name in MODULES:
        m = importlib.import_module(name)
        out.append((m.SOUND_ID, m.RESOURCE_ID, WAV_DIR / f"{m.NAME}.wav"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod-folder", default=config.DEFAULT_MOD_FOLDER,
                    help=f"mod folder NAME under the install (default {config.DEFAULT_MOD_FOLDER}) -- the "
                         f"same default `summon-deploy` uses, so the three deploy steps land together")
    ap.add_argument("--game", default=None, help="path to the FF9 install (default: auto-detect)")
    ap.add_argument("--out", default=None,
                    help="write into THIS directory instead of the live mod folder (staging)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be written; write nothing")
    ap.add_argument("--set-priority", action="store_true",
                    help="also set Memoria.ini [Audio] PriorityToOGG = 1 (backed up first). REQUIRED for a "
                         "loose .ogg override to beat the bundled asset -- skip only if it is already 1.")
    args = ap.parse_args()

    if args.out:
        mod_root, game = Path(args.out), None
    else:
        game = config.find_game_path(args.game)
        mod_root = config.find_mod_root(game, args.mod_folder)
    print(f"mod folder: {mod_root}")

    rows = cues()
    missing = [str(w) for _i, _r, w in rows if not w.is_file()]
    if missing:
        print("the audio lane has not been built -- missing master WAV(s):\n  " + "\n  ".join(missing)
              + "\n  run: py studies/custom-summons/rung8-epic/audio/build_audio.py", file=sys.stderr)
        return 2

    existing = {e["id"] for e in sound.base_entries(mod_root, "sfx", game=game)}
    for sid, rid, wav in rows:
        verb = "REPLACE (already registered)" if sid in existing else "MINT (new id -- RELAUNCH)"
        print(f"  {sid} -> {rid}  [{verb}]  <- {wav.name}")
        if args.dry_run:
            continue
        if sid in existing:
            dest = mod_root / sound.override_rel_path(rid)
            sound.encode_ogg(wav, dest, quality=6)
            stale = dest.with_name(dest.stem + ".akb.bytes")     # the engine's runtime cache beside the ogg
            if stale.exists():
                stale.unlink()
        else:
            sound.mint_song(wav, mod_root, kind="sfx", new_id=sid, resource_id=rid, quality=6,
                            set_priority=False, game=game)

    if args.dry_run:
        print("\nDRY RUN -- nothing written.")
        return 0
    if args.set_priority and game is not None:
        res = sound.set_priority_to_ogg(game=game)
        print(f"  Memoria.ini [Audio] PriorityToOGG = 1  (backup: {res.get('backup')})")
    elif game is not None:
        print("  Memoria.ini NOT touched -- confirm [Audio] PriorityToOGG = 1 yourself, or re-run with "
              "--set-priority (it backs the ini up first).")
    print(f"\nmanifest: {sound.manifest_override_path(mod_root, 'sfx')}")
    print("RELAUNCH FF9 before the first cast -- SoundMetaData's id table loads once at process start.")
    print("Silence on cast 1 with everything else working = a missed relaunch, not a design failure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
