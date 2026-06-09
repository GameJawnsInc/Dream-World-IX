#!/usr/bin/env python3
"""Build a battle.toml and deploy the custom battle map reversibly into the per-worktree mod folder.

Mirrors tools/deploy_field.py for the battle pillar: reads the gitignored .ff9deploy.toml (mod_folder)
at the repo root, builds the FBX + textures into a temp mod, copies the battleMap_all/<BBG>/ slot into
the live mod folder (zipping any prior contents into backups/ first), splices any BattleScene /
BattleBackground patch lines (filtering a prior same-BBG line), and writes a revert script.

A pure FBX/texture override needs NO relaunch (the FBX is read at battle start). A BattleScene mint or a
BattlePatch BattleBackground line needs ONE relaunch (DictionaryPatch/BattlePatch load at launch).

Usage:  py tools/deploy_battle.py <battle.toml> [--mod-folder NAME]
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
from ff9mapkit.config import find_game_path, ModLayout  # noqa: E402
from ff9mapkit.battle.build import BattleProject, build_battle_mod  # noqa: E402

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


_ap = argparse.ArgumentParser(description="Deploy a custom battle map reversibly into the per-worktree "
                                          "mod folder (.ff9deploy.toml). Reach the battle via field 5000.")
_ap.add_argument("battle", help="path to a battle.toml")
_ap.add_argument("--mod-folder", dest="mod_folder", default=_mod_folder_default(),
                 help="Memoria mod folder to deploy into (default from .ff9deploy.toml / FF9CustomMap)")
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
info = build_battle_mod([proj], tmp / "mod", mod_name=MOD)
src_slot = ModLayout(tmp / "mod").battlemap_dir(BBG)

live = ModLayout(find_game_path() / MOD)
live_slot = live.battlemap_dir(BBG)

# back up + replace the slot
if live_slot.exists() and any(live_slot.iterdir()):
    shutil.make_archive(str(BK / f"battlemap_{BBG}.{STAMP}"), "zip", str(live_slot))
shutil.rmtree(live_slot, ignore_errors=True)
shutil.copytree(src_slot, live_slot)
print(f"deployed {BBG} -> {live_slot}  (mod folder {MOD})")

# splice patch lines reversibly (filter a prior same-BBG line, then append)
relaunch = False
if info["dictionary"]:
    live.dictionary_patch.parent.mkdir(parents=True, exist_ok=True)
    if live.dictionary_patch.exists():
        shutil.copyfile(live.dictionary_patch, BK / f"DictionaryPatch.txt.preBATTLE.{STAMP}")
        cur = [ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        cur = []
    cur = [ln for ln in cur if not (ln.startswith("BattleScene") and ln.split()[3:4] == [BBG])]
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

# revert: remove the slot (and note the patch backups, restored manually if a line was spliced)
revert = OUT / f"revert_battle_{BBG}.py"
revert.write_text(
    "#!/usr/bin/env python3\nimport shutil, sys\nfrom pathlib import Path\n"
    f"sys.path.insert(0, r\"{KIT}\")\n"
    "from ff9mapkit.config import find_game_path, ModLayout\n"
    f"live = ModLayout(find_game_path() / {MOD!r})\n"
    f"shutil.rmtree(live.battlemap_dir({BBG!r}), ignore_errors=True)\n"
    f"print('reverted: removed battle map {BBG} from {MOD}')\n"
    f"print('NOTE: if this deploy spliced patch lines, restore backups/*.preBATTLE.{STAMP} manually.')\n",
    encoding="utf-8", newline="\n")
shutil.rmtree(tmp, ignore_errors=True)

for w in info["warnings"]:
    print(f"warning: {w}")
print(f"revert: py {revert}")
print("Relaunch the game (DictionaryPatch/BattlePatch load at launch)." if relaunch
      else "No relaunch needed (the FBX + textures are read at battle start).")
print(f"Then trigger a battle that uses {BBG} (field 5000's encounter, if it maps there).")
