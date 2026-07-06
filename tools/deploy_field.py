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
# [[mint]] loose-model FBX tree (NEW additive GEO ids) -- ship the whole staged Models/ (merge into live)
src_models = tl.root / "StreamingAssets" / "Assets" / "Resources" / "Models"
if src_models.is_dir():
    shutil.copytree(src_models, live.root / "StreamingAssets" / "Assets" / "Resources" / "Models",
                    dirs_exist_ok=True)
# [[playable]] custom_battle_anims: a minted battle model's OWN animset (loose .anim at Animations/<mintId>/<key>).
# Ships alongside its `3DModelAnimation` DictionaryPatch lines (carried in mint_lines below). RELAUNCH to register.
src_anims = tl.root / "StreamingAssets" / "Assets" / "Resources" / "Animations"
if src_anims.is_dir():
    shutil.copytree(src_anims, live.root / "StreamingAssets" / "Assets" / "Resources" / "Animations",
                    dirs_exist_ok=True)

# [[playable]] portrait: the loose Face Atlas override (a custom avatar sprite, appended non-destructively).
src_atlas = tl.face_atlas_dir
if src_atlas.is_dir() and any(src_atlas.iterdir()):
    live.face_atlas_dir.mkdir(parents=True, exist_ok=True)
    for _af in src_atlas.iterdir():
        if _af.is_file():
            shutil.copyfile(_af, live.face_atlas_dir / _af.name)
    print("  + Face Atlas override (custom menu portrait) -> RELAUNCH to apply (read at launch, not F6)")

# [music] file = custom themes: ship the minted OGG(s) + the override MusicMetaData.txt (a NEW song id per
# theme). Merge the built manifest's custom (band >=1000) entries into any live override so successive
# deploys ACCUMULATE their themes. A minted new id needs no PriorityToOGG (no bundled .akb to lose to).
_src_sounds = tl.root / "StreamingAssets" / "Assets" / "Resources" / "Sounds"
if _src_sounds.is_dir():
    shutil.copytree(_src_sounds, live.root / "StreamingAssets" / "Assets" / "Resources" / "Sounds",
                    dirs_exist_ok=True)
_src_manifest = tl.root / "FF9_Data" / "EmbeddedAsset" / "Manifest" / "Sounds" / "MusicMetaData.txt"
if _src_manifest.is_file():
    from ff9mapkit import sound as _snd
    _live_manifest = live.root / "FF9_Data" / "EmbeddedAsset" / "Manifest" / "Sounds" / "MusicMetaData.txt"
    _built = _snd.parse_manifest(_src_manifest.read_text(encoding="utf-8"))
    if _live_manifest.exists():                       # merge: live (stock + prior mints) + this deploy's new ids
        _base = _snd.parse_manifest(_live_manifest.read_text(encoding="utf-8"))
        _have = {e["id"] for e in _base}
        _new = [e for e in _built if e["id"] >= _snd.MINT_ID_BASE["music"] and e["id"] not in _have]
        _text = _snd.serialize_manifest(_base + _new)
    else:
        _text = _src_manifest.read_text(encoding="utf-8")
    _live_manifest.parent.mkdir(parents=True, exist_ok=True)
    _live_manifest.write_text(_text, encoding="utf-8", newline="\n")
    print("  + custom [music] theme(s) -> RELAUNCH to register the new song id(s) + set MusicVolume > 0")
mint_lines = info.get("mint_lines", [])
# `3DModel <id> <NAME>` register a GEO id; `3DModelAnimation <key> <ANH_NAME>` register a custom anim (custom_battle_
# anims). Drop stale ids by GEO id, and stale anim registrations by the GEO middle-block their ANH name shares.
mint_ids = {ml.split()[1] for ml in mint_lines if ml.startswith("3DModel ") and len(ml.split()) >= 2}
mint_geo_blocks = {"_".join(ml.split()[2].split("_")[1:4]) for ml in mint_lines      # MAIN_B0_M100 from GEO_MAIN_B0_M100
                   if ml.startswith("3DModel ") and len(ml.split()) >= 3}
def _stale_anim(ln):                                       # a 3DModelAnimation line for a mint being redeployed
    p = ln.split()
    return (ln.startswith("3DModelAnimation ") and len(p) >= 3
            and "_".join(p[-1].split("_")[1:4]) in mint_geo_blocks)
charname_lines = info.get("charname_lines", [])   # [[playable]] CharacterDefaultName <id> <SYM> <name> (per-lang)
charname_keys = {(p[1], p[2]) for p in (ln.split() for ln in charname_lines) if len(p) >= 3}   # (char-id, lang)
dp = [ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines()
      if ln.strip() and ln.split()[1:2] != [str(FID)]           # drop this field's old FieldScene/LocationName
      and not (ln.startswith("3DModel ") and ln.split()[1:2] and ln.split()[1] in mint_ids)   # drop stale mint ids
      and not _stale_anim(ln)                                                                  # drop stale anim regs
      and not (ln.startswith("CharacterDefaultName ") and len(ln.split()) >= 3                 # drop stale names
               and (ln.split()[1], ln.split()[2]) in charname_keys)]
dp += mint_lines                               # `3DModel <id> <name>` -- register minted ids (read at launch)
dp += charname_lines                           # `CharacterDefaultName <id> <SYM> <name>` -- 13th+ char name (launch)
dp.append(info["dictionary"][0])
dp += info.get("location_lines", [])           # [field] location -> LocationName <id> <title> (id-keyed, removed above with the FieldScene line)
live.dictionary_patch.write_text("\n".join(dp) + "\n", encoding="utf-8", newline="\n")
_n_model = sum(1 for ml in mint_lines if ml.startswith("3DModel "))
_n_anim = sum(1 for ml in mint_lines if ml.startswith("3DModelAnimation "))
if _n_model:
    print(f"  + {_n_model} mint 3DModel line(s) + staged Models/ -> RELAUNCH to register the new id(s)")
if _n_anim:
    print(f"  + {_n_anim} 3DModelAnimation line(s) + staged Animations/ (custom_battle_anims) -> RELAUNCH to register")
if charname_lines:
    print(f"  + {len(charname_lines)} CharacterDefaultName line(s) ([[playable]]) -> RELAUNCH to apply the name")
if info.get("location_lines"):                  # the directive is read from DictionaryPatch at LAUNCH, not on F6
    print(f"  + {info['location_lines'][0]}  -> RELAUNCH to apply (DictionaryPatch is read at launch, not F6)")

# ForkDonorPatch.txt: ANY fork (verbatim OR native/synth) needs its `<forkId> <donorRealId>` mapping so the
# engine's fork-donor remap suite (s24-s33: off-mesh exemptions, the NAME-keyed overlay-occlusion offsets, scroll
# binds, ...) still fires for the custom id. deploy_field historically emitted it ONLY for verbatim forks, so a
# NATIVE/SYNTH fork lost ALL fork-donor behaviors -- most visibly, character-vs-overlay OCCLUSION broke for the
# whole donor field (s31 FieldMapExtraOffset can't resolve the fork name -> donor; the recurring hand-written
# `4003 1860`). The donor is now recorded by the import (`[verbatim_eb] donor` OR `[field] source_field`) and
# read by _verbatim_donor_id, so emit for both. Merged non-clobbering, reversible. Read at LAUNCH -> RELAUNCH.
fork_revert_code = ""
_donor = B._verbatim_donor_id(proj)
_fdp = live.root / "ForkDonorPatch.txt"
if _donor and _donor != FID:
    _had_fdp = _fdp.exists()
    if _had_fdp:
        shutil.copyfile(_fdp, BK / f"ForkDonorPatch.txt.preDEPLOY.{STAMP}")
    _cur = [ln for ln in (_fdp.read_text(encoding="utf-8").splitlines() if _had_fdp else [])
            if ln.strip() and not ln.lstrip().startswith("#") and ln.split()[0:1] != [str(FID)]]
    _cur.append(f"{FID} {_donor}")
    _fdp.write_text("# ff9mapkit fork-fidelity: <forkId> <donorRealId>\n" + "\n".join(_cur) + "\n",
                    encoding="utf-8", newline="\n")
    fork_revert_code = ('\nshutil.copyfile(BK/f"ForkDonorPatch.txt.preDEPLOY.{STAMP}", live.root/"ForkDonorPatch.txt")'
                        if _had_fdp else
                        '\n_pf = live.root/"ForkDonorPatch.txt"\nif _pf.exists(): _pf.unlink()')
    print(f"  + ForkDonorPatch.txt ({FID} -> donor {_donor}; RELAUNCH to apply -- read at launch, not F6)")
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
                                 (tl.character_parameters_csv, live.character_parameters_csv, "CharacterParameters"),
                                 (tl.battle_parameters_csv, live.battle_parameters_csv, "BattleParameters"),
                                 (tl.command_sets_csv, live.command_sets_csv, "CommandSets"),
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
# [[learn]] -> per-preset Abilities/<Name>.csv (a FILE SET, one whole file per touched preset). Walk the staging
# Abilities dir; each preset file gets its own reversible backup/restore (joins csv_reverts).
_PRESET_STEMS = {"Zidane", "Vivi", "Garnet", "Steiner", "Freya", "Quina", "Eiko", "Amarant", "Cinna1", "Cinna2",
                 "Marcus1", "Marcus2", "Blank1", "Blank2", "Beatrix1", "Beatrix2", "StageZidane", "StageCinna",
                 "StageMarcus", "StageBlank"}
_abil_dir = tl.abilities_csv("Zidane").parent
if _abil_dir.is_dir():
    for _f in sorted(_abil_dir.glob("*.csv")):
        # base preset learn files by NAME, plus a 13th-char's OWN custom preset by NUMERIC name (Abilities/20.csv,
        # band 20-23; [playable.abilities]). Skip AbilityGems.csv (handled in the main loop above). WITHOUT the
        # custom-band case the learn file never deploys -> the engine's FF9Abil_HasAp is false -> the char knows
        # EVERY pool spell (no AP gating), which is exactly the "knows all black+white magic" bug.
        if _f.stem not in _PRESET_STEMS and not (_f.stem.isdigit() and 20 <= int(_f.stem) <= 23):
            continue
        _live_f = live.abilities_csv(_f.stem)
        _live_f.parent.mkdir(parents=True, exist_ok=True)
        _had = _live_f.exists()
        if _had:
            shutil.copyfile(_live_f, BK / f"{_f.stem}.csv.preDEPLOY.{STAMP}")
        shutil.copyfile(_f, _live_f)
        csv_reverts.append((_f.stem, str(_live_f), _had))
        print(f"  + Abilities/{_f.stem}.csv (learn list)")
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
                 "AbilityFeatures", "MagicSwordSets", "CharacterParameters", "BattleParameters", "CommandSets"}
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

_mint_ids_repr = repr(sorted(mint_ids))              # this deploy's minted GEO ids (drop their 3DModel lines on revert)
_mint_blk_repr = repr(sorted(mint_geo_blocks))        # their GEO middle-blocks (drop matching 3DModelAnimation lines)
revert = f'''#!/usr/bin/env python3
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
STAMP="{STAMP}"; BK=Path(r"{BK}"); live=ModLayout(find_game_path()/"{MOD_FOLDER}")
# surgical DictionaryPatch revert: drop THIS id's line + THIS deploy's mint registrations (3DModel <mintId> and
# 3DModelAnimation <key> <ANH_..middle..>) from the CURRENT live file (preserving any line another tool -- e.g.
# deploy_battle's "BattleScene <sceneid>" -- added into the SAME mod folder since this deploy), then restore this
# id's prior registration from the pre-deploy backup if it had one. A wholesale snapshot-restore (the old
# behavior) re-clobbered those co-deployed lines -> a black screen. (The staged Models//Animations/ FBX+clip
# trees are LEFT on disk -- inert once unregistered -- matching the mint deploy's copytree.)
_MINT_IDS=set({_mint_ids_repr}); _MINT_BLK=set({_mint_blk_repr})
def _revkeep(ln):
    p=ln.split()
    if not ln.strip(): return False
    if p[1:2]==["{FID}"]: return False
    if ln.startswith("3DModel ") and p[1:2] and p[1] in _MINT_IDS: return False
    if ln.startswith("3DModelAnimation ") and len(p)>=3 and "_".join(p[-1].split("_")[1:4]) in _MINT_BLK: return False
    return True
_dpkeep=[ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines() if _revkeep(ln)]
_dpbak=BK/f"DictionaryPatch.txt.preDEPLOY.{{STAMP}}"
if _dpbak.exists():
    # restore to the PRE-deploy state: re-add this id's prior FieldScene/LocationName AND any mint 3DModel/
    # 3DModelAnimation this revert dropped that PRE-EXISTED this deploy (so reverting one field can't strip a
    # registration another field had already made -- the shared-character-on-two-fields case). Lines THIS deploy
    # added fresh aren't in the backup, so they stay gone. (_revkeep is False for exactly the lines we dropped.)
    _seen=set(_dpkeep)
    for ln in _dpbak.read_text(encoding="utf-8").splitlines():
        if ln.strip() and not _revkeep(ln) and ln not in _seen:
            _dpkeep.append(ln); _seen.add(ln)
live.dictionary_patch.write_text("\\n".join(_dpkeep)+"\\n", encoding="utf-8", newline="\\n")
shutil.rmtree(live.fieldmap_dir("{FBG}"), ignore_errors=True)
mc=live.mapconfig_path("EVT_{name}")
if mc.exists(): mc.unlink()
for L in LANGS:
    p=live.eb_path(L,"EVT_{name}.eb.bytes")
    if p.exists(): p.unlink()
    mb=BK/f"{{L}}-{text_block}.mes.preDEPLOY.{{STAMP}}"
    if mb.exists(): shutil.copyfile(mb, live.mes_path(L,{text_block})){csv_revert_code}{bp_revert_code}{tp_revert_code}{fork_revert_code}
print("reverted: DictionaryPatch (incl. mint 3DModel/3DModelAnimation) + dialogue + start-state CSVs + BattlePatch + TextPatch + ForkDonorPatch restored; {name} removed. (staged Models//Animations/ trees left inert on disk)")
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
