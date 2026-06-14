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
_ap.add_argument("--text-block", dest="text_block", type=int, default=_cfg.get("text_block"),
                 help="override the field's dialogue .mes block (mesID). Pin a worktree-unique block in "
                      ".ff9deploy.toml (text_block = N) to avoid the shared-1073 text-shadow collision when "
                      "several worktree mod folders stack in Memoria.ini FolderNames.")
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
if _args.text_block is not None:                            # worktree-unique mesID (avoids the shared-1073 shadow)
    proj.raw["field"]["text_block"] = int(_args.text_block)
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
GAME = find_game_path()
live = ModLayout(GAME / MOD_FOLDER)
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
# Item-data CSV deltas: mod-GLOBAL files build_mod emits when the field carries [start_inventory]/[[equipment]]
# (the new-game starting bag/gear, read at NEW-GAME init) or [[shop]] (custom shop inventories, merged by id).
# Deployed only when present, each reversibly (backup pre-existing / delete a newly-created one on revert).
csv_reverts = []
for src_csv, live_csv, label in ((tl.initial_items_csv, live.initial_items_csv, "InitialItems"),
                                 (tl.default_equipment_csv, live.default_equipment_csv, "DefaultEquipment"),
                                 (tl.shop_items_csv, live.shop_items_csv, "ShopItems"),
                                 (tl.synthesis_csv, live.synthesis_csv, "Synthesis"),
                                 (tl.weapons_csv, live.weapons_csv, "Weapons"),
                                 (tl.armors_csv, live.armors_csv, "Armors"),
                                 (tl.items_csv, live.items_csv, "Items"),
                                 (tl.stats_csv, live.stats_csv, "Stats"),
                                 (tl.item_effects_csv, live.item_effects_csv, "ItemEffects"),
                                 (tl.actions_csv, live.actions_csv, "Actions"),
                                 (tl.status_data_csv, live.status_data_csv, "StatusData"),
                                 (tl.status_sets_csv, live.status_sets_csv, "StatusSets"),
                                 (tl.magic_sword_sets_csv, live.magic_sword_sets_csv, "MagicSwordSets"),
                                 (tl.base_stats_csv, live.base_stats_csv, "BaseStats"),
                                 (tl.leveling_csv, live.leveling_csv, "Leveling"),
                                 (tl.ability_gems_csv, live.ability_gems_csv, "AbilityGems"),
                                 (tl.ability_features_txt, live.ability_features_txt, "AbilityFeatures")):
    if not src_csv.exists():
        continue
    ext = src_csv.suffix                                  # .csv for the deltas; .txt for AbilityFeatures
    live_csv.parent.mkdir(parents=True, exist_ok=True)
    had = live_csv.exists()
    if had:
        shutil.copyfile(live_csv, BK / f"{label}{ext}.preDEPLOY.{STAMP}")
    shutil.copyfile(src_csv, live_csv)
    csv_reverts.append((label, str(live_csv), had))
    print(f"  + {label}{ext} (data delta)")
csv_revert_code = ""
for _label, _live, _had in csv_reverts:
    _ext = Path(_live).suffix                             # backup keeps the real extension (.csv / .txt)
    if _had:
        csv_revert_code += f'\nshutil.copyfile(BK/f"{_label}{_ext}.preDEPLOY.{{STAMP}}", Path(r"{_live}"))'
    else:
        csv_revert_code += f'\n_p = Path(r"{_live}")\nif _p.exists(): _p.unlink()'
# These CSVs are read ONCE at engine startup (static ctors: ff9weap/ff9armor/ff9item) or at New-Game init -- F6
# Reload re-reads only the field's .eb/.mes/scene/walkmesh, NOT item/stat data -> a change needs a RELAUNCH.
_STARTUP_CSVS = {"Weapons", "Armors", "Items", "Stats", "ItemEffects", "InitialItems", "ShopItems", "Synthesis",
                 "DefaultEquipment", "Actions", "StatusData", "StatusSets", "BaseStats", "Leveling", "AbilityGems",
                 "AbilityFeatures", "MagicSwordSets"}
if any(_l in _STARTUP_CSVS for _l, _, _ in csv_reverts):
    print("  !! item/stat CSVs load at game startup (or New-Game init) -> RELAUNCH to apply (F6 Reload won't)")

# BattlePatch.txt: the field's Phase-4 enemy/attack/scene tuning ([[battle_patch]] / [[battle_enemy]] /
# [[battle_attack]]) + any per-encounter BGM. build_mod emits the COMPLETE block into the built mod; we SPLICE
# it into the live file under this field's `//` sentinel markers -- NON-clobbering (a co-deployed battle's
# BGM/repoint lines + a stacked worktree's lines survive) and reversible. The engine skips `//` lines, and
# BattlePatch is parsed once at startup -> a battle-tuning change needs a RELAUNCH (not just F6 Reload).
from ff9mapkit.battle import battlepatch as _bp
_live_bp_text = live.battle_patch.read_text(encoding="utf-8") if live.battle_patch.exists() else ""
_built_block = ([ln for ln in tl.battle_patch.read_text(encoding="utf-8").splitlines() if ln.strip()]
                if tl.battle_patch.exists() else [])
bp_revert_code = ""
if _built_block or f"ff9mapkit field {FID}" in _live_bp_text:
    _had_bp = live.battle_patch.exists()
    if _had_bp:
        shutil.copyfile(live.battle_patch, BK / f"BattlePatch.txt.preDEPLOY.{STAMP}")
    _merged = _bp.merge_battle_patch(_live_bp_text, _built_block, FID)
    if _merged:
        live.battle_patch.write_text(_merged, encoding="utf-8", newline="\n")
    elif live.battle_patch.exists():
        live.battle_patch.unlink()
    bp_revert_code = ('\nshutil.copyfile(BK/f"BattlePatch.txt.preDEPLOY.{STAMP}", live.battle_patch)' if _had_bp
                      else '\n_pb = live.battle_patch\nif _pb.exists(): _pb.unlink()')
    if _built_block:
        print(f"  + BattlePatch.txt (battle tuning + BGM, merged under field-{FID} markers; RELAUNCH to apply)")

# TextPatch.txt: the field's item NAME/DESCRIPTION overrides ([[item_text]] -> >DATABASE find/replace).
# Same non-clobbering splice-under-`//`-markers as BattlePatch (another field's item text + a stacked
# worktree's lines survive) and reversible. The engine skips `//` lines; TextPatch is read once at
# DataPatchers.Initialize (AssetManager bring-up) -> a text change needs a RELAUNCH (not just F6 Reload).
from ff9mapkit.content import itemtext as _itxt
_live_tp_text = live.text_patch.read_text(encoding="utf-8") if live.text_patch.exists() else ""
_built_tp = ([ln for ln in tl.text_patch.read_text(encoding="utf-8").splitlines() if ln.strip()]
             if tl.text_patch.exists() else [])
tp_revert_code = ""
if _built_tp or f"ff9mapkit field {FID}" in _live_tp_text:
    _had_tp = live.text_patch.exists()
    if _had_tp:
        shutil.copyfile(live.text_patch, BK / f"TextPatch.txt.preDEPLOY.{STAMP}")
    _merged_tp = _itxt.merge_text_patch(_live_tp_text, _built_tp, FID)
    if _merged_tp:
        live.text_patch.write_text(_merged_tp, encoding="utf-8", newline="\n")
    elif live.text_patch.exists():
        live.text_patch.unlink()
    tp_revert_code = ('\nshutil.copyfile(BK/f"TextPatch.txt.preDEPLOY.{STAMP}", live.text_patch)' if _had_tp
                      else '\n_pt = live.text_patch\nif _pt.exists(): _pt.unlink()')
    if _built_tp:
        print(f"  + TextPatch.txt (item name/desc, merged under field-{FID} markers; RELAUNCH to apply)")
print(f"deployed {name} -> field {FID} (reachable via the New-Game auto-warp)")

revert = f'''#!/usr/bin/env python3
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
STAMP="{STAMP}"; BK=Path(r"{BK}"); live=ModLayout(find_game_path()/"{MOD_FOLDER}")
# surgical DictionaryPatch revert: drop only THIS id's line from the CURRENT live file (preserving any line
# another tool -- e.g. deploy_battle's "BattleScene <sceneid>" registration -- added into the SAME mod folder
# since this deploy), then restore this id's prior registration from the pre-deploy backup if it had one. A
# wholesale snapshot-restore (the old behavior) re-clobbered those co-deployed lines -> a black screen.
_dpkeep=[ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines() if ln.strip() and ln.split()[1:2]!=["{FID}"]]
_dpbak=BK/f"DictionaryPatch.txt.preDEPLOY.{{STAMP}}"
if _dpbak.exists():
    _dpkeep+=[ln for ln in _dpbak.read_text(encoding="utf-8").splitlines() if ln.strip() and ln.split()[1:2]==["{FID}"]]
live.dictionary_patch.write_text("\\n".join(_dpkeep)+"\\n", encoding="utf-8", newline="\\n")
shutil.rmtree(live.fieldmap_dir("{FBG}"), ignore_errors=True)
mc=live.mapconfig_path("EVT_{name}")
if mc.exists(): mc.unlink()
for L in LANGS:
    p=live.eb_path(L,"EVT_{name}.eb.bytes")
    if p.exists(): p.unlink()
    mb=BK/f"{{L}}-{text_block}.mes.preDEPLOY.{{STAMP}}"
    if mb.exists(): shutil.copyfile(mb, live.mes_path(L,{text_block})){csv_revert_code}{bp_revert_code}{tp_revert_code}
print("reverted: DictionaryPatch + dialogue + start-state CSVs + BattlePatch + TextPatch restored; {name} removed.")
'''
(OUT / f"revert_deploy_{FID}.py").write_text(revert, encoding="utf-8", newline="\n")    # per-id revert
(OUT / "revert_deploy.py").write_text(revert, encoding="utf-8", newline="\n")            # generic = latest deploy
shutil.rmtree(tmp, ignore_errors=True)
print(f"revert: {OUT / ('revert_deploy_%d.py' % FID)}  (or revert_deploy.py for the latest)")

# text-shadow guard: warn if a HIGHER-priority mod folder in Memoria.ini FolderNames also defines this
# field's .mes block -- the engine would render THAT folder's text, not ours (the shared-1073 collision).
try:
    from ff9mapkit.deploystack import check_text_block_shadow, shadow_warning
    _warn = shadow_warning(check_text_block_shadow(GAME, MOD_FOLDER, text_block), MOD_FOLDER)
    if _warn:
        print(f"\n  !! {_warn}")
except Exception:
    pass                                                   # a missing/odd Memoria.ini must never break a deploy

# id-collision guard: this field id ALSO registered (as a FieldScene/BattleScene) by another stacked FolderNames
# folder collides in the GLOBAL FF9DBAll.EventDB -> one side loads the wrong .eb -> black screen (the 30011 vs
# -bb CAMKEYS bug). A loud WARN (not abort) -- single-field test deploys are iterative.
try:
    from ff9mapkit.deploystack import check_id_collisions, id_collision_warning
    _iw = id_collision_warning(check_id_collisions(GAME, MOD_FOLDER, {FID}), MOD_FOLDER)
    if _iw:
        print(f"\n  !! {_iw}")
except Exception:
    pass

# CSV-shadow guard: the starting bag (InitialItems.csv) is read HIGHEST-PRIORITY-WINS, so deploying it into a
# folder a HIGHER-priority FolderNames folder also ships silently drops it. (ShopItems/DefaultEquipment MERGE,
# so they don't whole-file-shadow.) Only check the ones this deploy actually shipped.
try:
    from ff9mapkit.deploystack import check_csv_shadow, HIGHEST_WINS_CSVS
    for _label, _live, _had in csv_reverts:
        for _rel in HIGHEST_WINS_CSVS:
            if _rel.rsplit("/", 1)[-1].lower().startswith(_label.lower()):
                _cw = check_csv_shadow(GAME, MOD_FOLDER, _rel)
                if _cw:
                    print(f"\n  !! {_cw}")
except Exception:
    pass

print(f"\n=== Reach it in-game: F6 -> debug menu -> Warp to field {FID} "
      f"(or New Game, if the auto-warp targets {FID}). ===")
