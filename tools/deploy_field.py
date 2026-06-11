#!/usr/bin/env python3
"""Build any field.toml and deploy it to a custom field id (default 4003) reversibly. Reverts THIS id's
prior test first; OTHER ids' deploys are untouched, so multiple ids coexist in the shared install -- give
a branch/worktree its own slot:  python tools/deploy_field.py my.field.toml --id 5000

DEV LOOP (no relaunch): after deploying, press F6 in-game to open the ff9mapkit debug menu, then
"Reload field" (re-reads the current field's mod files -- .eb / .mes / scene / walkmesh / art) or
"Warp to field" -> <id> to hop straight to this slot. So: edit field.toml -> deploy_field.py -> F6 ->
Reload/Warp. Only the FIRST use of a NEW id needs one relaunch (to register it in DictionaryPatch);
BattlePatch + engine DLL changes also need a relaunch.

Usage:  python tools/deploy_field.py <field.toml> [--id N] [--name NAME]
"""
import os, sys, struct, shutil, tempfile, datetime, glob
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import build as B
from ff9mapkit.config import find_game_path, ModLayout, LANGS
from ff9mapkit.eb import EbScript, edit, disasm

import argparse, tomllib
# Per-worktree deploy target: a gitignored .ff9deploy.toml at the repo root pins each worktree's OWN
# mod folder + slot id, so worktrees never share a DictionaryPatch.txt and can't clobber each other's
# registrations. Resolution order: CLI flag > $FF9_MOD_FOLDER > .ff9deploy.toml > defaults.
_REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
def _worktree_cfg():
    f = _REPO / ".ff9deploy.toml"
    if f.is_file():
        try:
            return tomllib.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}
_cfg = _worktree_cfg()
_def_folder = os.environ.get("FF9_MOD_FOLDER") or _cfg.get("mod_folder") or "FF9CustomMap"
_def_id = int(_cfg.get("id", 4003))
_ap = argparse.ArgumentParser(description="Build a field.toml and deploy it reversibly to a custom field "
                                          "id, inside a per-worktree Memoria mod folder. Reach it via the "
                                          "F6 debug menu's 'Warp to field'.")
_ap.add_argument("toml", help="path to the field.toml")
_ap.add_argument("--id", type=int, default=_def_id,
                 help="custom field id to deploy into (e.g. 5000 to give a branch/worktree its own slot)")
_ap.add_argument("--name", default=None,
                 help="internal field name (default TESTROOM for 4003, else TEST<id>)")
_ap.add_argument("--mod-folder", dest="mod_folder", default=_def_folder,
                 help="Memoria mod folder to deploy into (per-worktree isolation; default from "
                      ".ff9deploy.toml / $FF9_MOD_FOLDER / FF9CustomMap)")
_args = _ap.parse_args()
TOML = Path(_args.toml)
FID = _args.id
MOD_FOLDER = _args.mod_folder
# The custom-field slot is a SANDBOX: force the test build to id FID + a fixed name so ANY field.toml
# (any id/name) tests here without colliding with a live field. Each id gets a DISTINCT name -> distinct
# FBG dir + EVT file, so multiple ids coexist in the shared install (e.g. 4003 master + 5000 a branch),
# and a field named like a live one (e.g. HUT_INT) can't overwrite the real field. 4003 stays TESTROOM
# for back-compat (the New-Game auto-warp + existing reverts).
TEST_NAME = _args.name or ("TESTROOM" if FID == 4003 else f"TEST{FID}")
OUT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out")))
OUT.mkdir(exist_ok=True)

# revert THIS id's prior deploy only (revert_deploy_<id>.py) -- NOT another id's deploy (so deploying
# 5000 never reverts 4003) and NOT other tools' reverts (e.g. revert_alex_fast_warp.py: the Alexandria
# fast-warp points at a slot and must SURVIVE a field deploy).
prior = OUT / f"revert_deploy_{FID}.py"
if prior.exists():
    import subprocess
    _flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0   # no console flash when called by the GUI
    subprocess.run([sys.executable, str(prior)], creationflags=_flags)

# build -- forced into the 4003 sandbox identity (id + name), so a field that declares id 4002 or a
# live-colliding name still tests safely. The on-disk field.toml is untouched (override is in-memory).
tmp = Path(tempfile.mkdtemp(prefix="deployfield_"))
proj = B.FieldProject.load(TOML)
_orig_id, _orig_name = proj.field.get("id"), proj.field.get("name")
proj.raw.setdefault("field", {})["id"] = FID
proj.raw["field"]["name"] = TEST_NAME
if (_orig_id, _orig_name) != (FID, TEST_NAME):
    print(f"sandbox: {_orig_name} (id {_orig_id}) -> {TEST_NAME} (id {FID}) for the test slot")
info = B.build_mod([proj], tmp / "mod", mod_name=MOD_FOLDER)
FBG = info["fields"][0]
name = info["dictionary"][0].split()[4]                     # script/field name (field 4: ...area MAPID NAME textid)
text_block = int(info["dictionary"][0].split()[5])          # textid (field 5) -> dialogue .mes block
tl = ModLayout(tmp / "mod")
eb0 = tl.eb_path("us", f"EVT_{name}.eb.bytes").read_bytes()
s0 = EbScript.from_bytes(eb0); f0 = s0.entry(0).func_by_tag(0)
scroll = 0x71 in [i.op for i in disasm.iter_code(eb0, f0.abs_start, f0.abs_end)]
print(f"built {FBG} | {info['dictionary'][0]} | scroll={scroll}")

# deploy reversibly
live = ModLayout(find_game_path() / MOD_FOLDER)
# bootstrap a fresh per-worktree mod folder: give it a ModDescription.xml (so Memoria's Mod Manager
# recognizes it) and an empty DictionaryPatch.txt (so the backup/read steps below have a file).
live.root.mkdir(parents=True, exist_ok=True)
if not live.mod_description.exists():
    live.mod_description.write_text(
        f"<Mod>\n    <Name>{MOD_FOLDER}</Name>\n    <Author></Author>\n"
        f"    <InstallationPath>{MOD_FOLDER}</InstallationPath>\n    <Category></Category>\n"
        f"    <Description></Description>\n</Mod>\n", encoding="utf-8", newline="\n")
if not live.dictionary_patch.exists():
    live.dictionary_patch.write_text("", encoding="utf-8", newline="\n")
BK = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups")))
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copyfile(live.dictionary_patch, BK / f"DictionaryPatch.txt.preDEPLOY.{STAMP}")
for L in LANGS:
    lm = live.mes_path(L, text_block)
    if lm.exists():
        shutil.copyfile(lm, BK / f"{L}-{text_block}.mes.preDEPLOY.{STAMP}")
src_fm = tl.fieldmap_dir(FBG)
if src_fm.exists() and any(src_fm.iterdir()):          # borrow fields ship no scene -> skip
    shutil.rmtree(live.fieldmap_dir(FBG), ignore_errors=True)
    shutil.copytree(src_fm, live.fieldmap_dir(FBG))
mc_src = tl.mapconfig_path(f"EVT_{name}")              # native fork: the 3D-model LIGHTING config (optional)
if mc_src.exists():
    live.mapconfig_path(f"EVT_{name}").parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mc_src, live.mapconfig_path(f"EVT_{name}"))
for L in LANGS:
    live.ensure_dirs(FBG, langs=[L])
    shutil.copyfile(tl.eb_path(L, f"EVT_{name}.eb.bytes"), live.eb_path(L, f"EVT_{name}.eb.bytes"))
    sm = tl.mes_path(L, text_block)
    if sm.exists():                                        # dialogue: deploy the field's .mes block
        live.mes_path(L, text_block).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sm, live.mes_path(L, text_block))
dp = [ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines()
      if ln.strip() and ln.split()[1:2] != [str(FID)]]
dp.append(info["dictionary"][0])
live.dictionary_patch.write_text("\n".join(dp) + "\n", encoding="utf-8", newline="\n")
print(f"deployed {name} -> field {FID} (reachable via the New-Game auto-warp)")

revert = f'''#!/usr/bin/env python3
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
STAMP="{STAMP}"; BK=Path(r"{BK}"); live=ModLayout(find_game_path()/"{MOD_FOLDER}")
shutil.copyfile(BK/f"DictionaryPatch.txt.preDEPLOY.{{STAMP}}", live.dictionary_patch)
shutil.rmtree(live.fieldmap_dir("{FBG}"), ignore_errors=True)
mc=live.mapconfig_path("EVT_{name}")
if mc.exists(): mc.unlink()
for L in LANGS:
    p=live.eb_path(L,"EVT_{name}.eb.bytes")
    if p.exists(): p.unlink()
    mb=BK/f"{{L}}-{text_block}.mes.preDEPLOY.{{STAMP}}"
    if mb.exists(): shutil.copyfile(mb, live.mes_path(L,{text_block}))
print("reverted: DictionaryPatch + dialogue restored; {name} removed.")
'''
(OUT / f"revert_deploy_{FID}.py").write_text(revert, encoding="utf-8", newline="\n")    # per-id revert
(OUT / "revert_deploy.py").write_text(revert, encoding="utf-8", newline="\n")            # generic = latest deploy
shutil.rmtree(tmp, ignore_errors=True)
print(f"revert: {OUT / ('revert_deploy_%d.py' % FID)}  (or revert_deploy.py for the latest)")
print(f"\n=== Reach it in-game: F6 -> debug menu -> Warp to field {FID} "
      f"(or New Game, if the auto-warp targets {FID}). ===")
