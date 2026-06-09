#!/usr/bin/env python3
"""Build a battle.toml and deploy the custom battle map / minted scene reversibly into the per-worktree
mod folder.

Mirrors tools/deploy_field.py for the battle pillar: reads the gitignored .ff9deploy.toml (mod_folder) at
the repo root, builds into a temp mod, then copies EVERY emitted file (the FBX/textures slot AND -- for a
tier-c MINT -- the raw16/raw17 scene assets, per-lang battle eb + .mes, and the static INB) into the live
mod folder, backing up anything it overwrites. It splices any BattleScene / BattleBackground patch lines
and writes a revert script.

--trigger-field N: also repoint field N's deployed encounter (SetRandomBattles) at the minted scene_id so
you can immediately fight it (reversible). The field must already be deployed with an encounter.

A pure FBX/texture override needs NO relaunch. A MINT (new BattleScene id) or a BattlePatch line needs ONE
relaunch (DictionaryPatch/BattlePatch load at launch).

Usage:  py tools/deploy_battle.py <battle.toml> [--mod-folder NAME] [--trigger-field N]
"""
import argparse
import datetime
import os
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.config import find_game_path, ModLayout, LANGS  # noqa: E402
from ff9mapkit.battle.build import BattleProject, build_battle_mod  # noqa: E402
from ff9mapkit.eb import opcodes  # noqa: E402

REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _mod_folder_default():
    f = REPO / ".ff9deploy.toml"
    if f.is_file():
        try:
            mf = tomllib.loads(f.read_text(encoding="utf-8")).get("mod_folder")
            if mf:
                return mf
        except Exception:
            pass
    return os.environ.get("FF9_MOD_FOLDER") or "FF9CustomMap"


def _repoint_encounter(eb: bytes, new_id: int) -> bytes:
    """Repoint a field eb's SetRandomBattles(1, X,X,X,X) -> (1, new,new,new,new). Detects the current X by
    scanning for the ENCSCENE op with 4 equal scene words; returns the patched bytes (or raises)."""
    for x in range(0, 65536):
        old = opcodes.set_random_battles(1, x, x, x, x)
        if eb.count(old) == 1:
            return eb.replace(old, opcodes.set_random_battles(1, new_id, new_id, new_id, new_id))
    raise SystemExit("could not find a unique SetRandomBattles(1, X,X,X,X) in the field eb to repoint "
                     "(set your field.toml [encounter] scene manually instead)")


_ap = argparse.ArgumentParser(description="Deploy a custom battle map / minted scene reversibly into the "
                                          "per-worktree mod folder (.ff9deploy.toml).")
_ap.add_argument("battle", help="path to a battle.toml")
_ap.add_argument("--mod-folder", dest="mod_folder", default=_mod_folder_default(),
                 help="Memoria mod folder to deploy into (default from .ff9deploy.toml / FF9CustomMap)")
_ap.add_argument("--trigger-field", type=int, default=None, metavar="N",
                 help="repoint field N's deployed encounter at the minted scene_id (reversible)")
_args = _ap.parse_args()

proj = BattleProject.load(_args.battle)
BBG = proj.bbg
MOD = _args.mod_folder
OUT = Path(os.path.dirname(__file__)) / "scroll_out"
OUT.mkdir(exist_ok=True)
BK = REPO / "backups"
BK.mkdir(exist_ok=True)
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# build into a temp mod
tmp = Path(tempfile.mkdtemp(prefix="deploybattle_"))
stage_root = tmp / "mod"
info = build_battle_mod([proj], stage_root, mod_name=MOD)

live_root = find_game_path() / MOD
live_root.mkdir(parents=True, exist_ok=True)
bk_dir = BK / f"battle_predeploy.{STAMP}"     # holds the pre-deploy copy of any file we overwrite

# copy every emitted file into live, backing up overwrites; track created vs overwritten for the revert
created, overwritten = [], []
for abs_src in info["written"]:
    rel = Path(abs_src).relative_to(stage_root)
    dst = live_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        bdst = bk_dir / rel
        bdst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(dst, bdst)
        overwritten.append(str(rel))
    else:
        created.append(str(rel))
    shutil.copyfile(abs_src, dst)
print(f"deployed {BBG}{' + minted scene ' + str(proj.scene_id) if proj.is_mint else ''} -> {MOD} "
      f"({len(created)} new, {len(overwritten)} replaced)")

live = ModLayout(live_root)

# splice patch lines reversibly (filter a prior same-BBG / same-scene line, then append)
relaunch = False
if info["dictionary"]:
    if live.dictionary_patch.exists():
        shutil.copyfile(live.dictionary_patch, BK / f"DictionaryPatch.txt.preBATTLE.{STAMP}")
        cur = [ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        cur = []
    sid = str(proj.scene_id) if proj.is_mint else None
    cur = [ln for ln in cur if not (ln.startswith("BattleScene")
                                    and (ln.split()[3:4] == [BBG] or ln.split()[1:2] == [sid]))]
    cur += info["dictionary"]
    live.dictionary_patch.write_text("\n".join(cur) + "\n", encoding="utf-8", newline="\n")
    relaunch = True
if info["battle_patch"]:
    if live.battle_patch.exists():
        shutil.copyfile(live.battle_patch, BK / f"BattlePatch.txt.preBATTLE.{STAMP}")
        cur = [ln for ln in live.battle_patch.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        cur = []
    cur += info["battle_patch"]
    live.battle_patch.write_text("\n".join(cur) + "\n", encoding="utf-8", newline="\n")
    relaunch = True

# optional: repoint a trigger field's encounter at the minted scene (back it up like any overwrite, so
# the revert's restore loop handles it)
if _args.trigger_field is not None and proj.is_mint:
    field_name = None
    for ln in (live.dictionary_patch.read_text(encoding="utf-8").splitlines()
               if live.dictionary_patch.exists() else []):
        p = ln.split()
        if p[:1] == ["FieldScene"] and p[1:2] == [str(_args.trigger_field)]:
            field_name = p[4] if len(p) > 4 else None
    if not field_name:
        print(f"warning: field {_args.trigger_field} not found in DictionaryPatch; skipping trigger wiring")
    else:
        n = 0
        for lang in LANGS:
            for ebp in [live.root / "StreamingAssets" / "Assets" / "Resources" / "CommonAsset"
                        / "EventEngine" / "EventBinary" / "Field" / lang / f"EVT_{field_name}.eb.bytes",
                        live.eb_path(lang, f"EVT_{field_name}.eb.bytes")]:
                if not ebp.exists():
                    continue
                rel = ebp.relative_to(live_root)
                bdst = bk_dir / rel
                bdst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ebp, bdst)
                overwritten.append(str(rel))
                ebp.write_bytes(_repoint_encounter(ebp.read_bytes(), int(proj.scene_id)))
                n += 1
                break
        print(f"repointed field {_args.trigger_field} ({field_name}) encounter -> scene {proj.scene_id} "
              f"(x{n} langs)")
        relaunch = True

# revert script: delete created files, restore overwritten (incl. any trigger-field ebs) from the backup
revert = OUT / f"revert_battle_{BBG}.py"
revert.write_text(
    "#!/usr/bin/env python3\nimport shutil\nfrom pathlib import Path\n"
    f"LIVE = Path(r{str(live_root)!r})\nBK = Path(r{str(bk_dir)!r})\n"
    f"CREATED = {created!r}\nOVERWRITTEN = {overwritten!r}\n"
    "for rel in CREATED:\n"
    "    (LIVE/rel).unlink(missing_ok=True)\n"
    "for rel in OVERWRITTEN:\n"
    "    b = BK/rel\n"
    "    if b.exists(): shutil.copyfile(b, LIVE/rel)\n"
    f"print('reverted battle deploy for {BBG}. If patch lines were spliced, restore "
    f"backups/*.preBATTLE.{STAMP}; relaunch FF9.')\n",
    encoding="utf-8", newline="\n")
shutil.rmtree(tmp, ignore_errors=True)

for w in info["warnings"]:
    print(f"warning: {w}")
print(f"revert: py {revert}")
print("Relaunch the game (DictionaryPatch/BattlePatch load at launch)." if relaunch
      else "No relaunch needed (the FBX + textures are read at battle start).")
if proj.is_mint and _args.trigger_field is None:
    print(f"Trigger: set a field's [encounter] scene = {proj.scene_id}, or re-run with --trigger-field N.")
