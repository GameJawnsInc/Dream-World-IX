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
BK.mkdir(parents=True, exist_ok=True)                 # gitignored -- absent in a fresh clone/worktree
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
# [[mint]] loose-model FBX tree (NEW additive GEO ids) -- ship the whole staged Models/ (merge into live).
# Weapons (type 6, e.g. a [[weapon]] model mint) stage under BattleMap/BattleModel/ instead -- ship that too.
for _sub in (("Models",), ("BattleMap", "BattleModel")):
    src_models = tl.root.joinpath("StreamingAssets", "Assets", "Resources", *_sub)
    if src_models.is_dir():
        shutil.copytree(src_models, live.root.joinpath("StreamingAssets", "Assets", "Resources", *_sub),
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
# anims). Drop stale registrations by the EXACT GEO id / anim key THIS deploy owns (carried in mint_lines) -- NEVER
# by the GEO middle-block an ANH name shares. A block-wide drop also wiped a FOREIGN `3DModelAnimation` line that
# merely shares a minted model's block -- e.g. a clip `ff9mapkit model-anim-new` wrote straight into DictionaryPatch
# BETWEEN deploys (the vanished key 60001 on field 30057). Exact id/key matching leaves those foreign lines intact.
from ff9mapkit import dictpatch as _dp
mint_ids = _dp.mint_model_ids(mint_lines)
mint_anim_keys = _dp.mint_anim_keys(mint_lines)
charname_lines = info.get("charname_lines", [])   # [[playable]] CharacterDefaultName <id> <SYM> <name> (per-lang)
charname_keys = {(p[1], p[2]) for p in (ln.split() for ln in charname_lines) if len(p) >= 3}   # (char-id, lang)
status_icon_lines = info.get("status_icon_lines", [])   # [[playable]] custom-status Buff/DebuffIcon <statusId> <sprite>
status_icon_ids = {p[1] for p in (ln.split() for ln in status_icon_lines) if len(p) >= 2}       # status ids being re-set
_dp_before = live.dictionary_patch.read_text(encoding="utf-8").splitlines()
# A live DictionaryPatch line THIS deploy owns -- filtered out below and re-appended fresh, and handed to the
# foreign-drop guard as its `owned=` predicate. ONE rule, from the library, deliberately: the hand-rolled copy
# that used to sit here matched on column 2 alone, so deploying a field in the 6000s claimed another session's
# `3DModel <same number>` (mint GEO ids start at 6000, the custom field band is 4000-9899 -- they OVERLAP),
# stripped it from the rewrite AND silenced the warning about it. See dictpatch.owned_predicate.
# `MessageFile <block>` for a CUSTOM (non-real) mesID. WITHOUT this the field's FieldScene line lands but
# DataPatchers' `!FF9DBAll.MesDB.ContainsKey(mesID)` gate fails and it SKIPS the whole scene -> the field is
# never registered -> BLACK SCREEN with no in-game error (only "invalid message file ID N" in Memoria.log).
# Owned by BLOCK, not by FID: they coincide for a derived block but not for an explicit one (field 4005 sits
# on block 30110), so a redeploy replaces its own line and a foreign folder's survives.
message_file_lines = info.get("message_file_lines", [])
message_blocks = {p[1] for p in (ln.split() for ln in message_file_lines) if len(p) >= 2}
_dp_owned = _dp.owned_predicate(fid=FID, model_ids=mint_ids, anim_keys=mint_anim_keys,
                                status_icon_ids=status_icon_ids, charname_keys=charname_keys,
                                text_blocks=message_blocks)
dp = [ln for ln in _dp_before if ln.strip() and not _dp_owned(ln)]
dp += message_file_lines                       # `MessageFile <block>` -- MUST precede the FieldScene line
dp += mint_lines                               # `3DModel <id> <name>` -- register minted ids (read at launch)
dp += charname_lines                           # `CharacterDefaultName <id> <SYM> <name>` -- 13th+ char name (launch)
dp += status_icon_lines                        # `BuffIcon/DebuffIcon <statusId> <sprite>` -- custom-status HUD icon (launch)
# a MINTED text block (register_text_block, e.g. a mognet field's roster block) needs its MessageFile
# registration or DataPatchers' FieldScene gate (!MesDB.ContainsKey(mesID)) refuses the field. build_mod
# wrote it into the tmp mod's own DictionaryPatch; carry any line the live patch doesn't have yet, and
# BEFORE the FieldScene line (registration first -- build._dictionary_patch_lines order).
_mes_lines = [ln for ln in (tmp / "mod" / "DictionaryPatch.txt").read_text(encoding="utf-8").splitlines()
              if ln.startswith("MessageFile ") and ln not in dp]
dp += _mes_lines
dp.append(info["dictionary"][0])
dp += info.get("location_lines", [])           # [field] location -> LocationName <id> <title> (id-keyed, removed above with the FieldScene line)
live.dictionary_patch.write_text("\n".join(dp) + "\n", encoding="utf-8", newline="\n")
_dropped = _dp.foreign_registrations_dropped(_dp_before, dp, owned=_dp_owned)   # a line this deploy does NOT own
if _dropped:
    print("  !! WARNING: this deploy dropped DictionaryPatch registration(s) it does not own. A foreign "
          "`FieldScene <id>` means that field id is NO LONGER REGISTERED -- the engine loads a null .eb and "
          "the field BLACK-SCREENS in game with no error. A foreign 3DModel/3DModelAnimation (e.g. a "
          "`model-anim-new` clip) is a lost model/clip. RE-ADD them now, or re-deploy the owning field:")
    for _dl in _dropped:
        print(f"       {_dl}")
_n_model = sum(1 for ml in mint_lines if ml.startswith("3DModel "))
_n_anim = sum(1 for ml in mint_lines if ml.startswith("3DModelAnimation "))
if _n_model:
    print(f"  + {_n_model} mint 3DModel line(s) + staged Models/ -> RELAUNCH to register the new id(s)")
if _n_anim:
    print(f"  + {_n_anim} 3DModelAnimation line(s) + staged Animations/ (custom_battle_anims) -> RELAUNCH to register")
if charname_lines:
    print(f"  + {len(charname_lines)} CharacterDefaultName line(s) ([[playable]]) -> RELAUNCH to apply the name")
if status_icon_lines:
    print(f"  + {len(status_icon_lines)} custom-status icon line(s) (Buff/DebuffIcon) -> RELAUNCH to apply")
if message_file_lines:
    print(f"  + {message_file_lines[0]}  -> RELAUNCH to register the custom text block "
          f"(DictionaryPatch is read once at launch, not on F6)")
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
                                 (tl.commands_csv, live.commands_csv, "Commands"),
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
# [playable.abilities] minted unique command -> a per-lang com_name.mes NAME overlay (FF9_Data/embeddedasset/text/
# <lang>/command/). Each lang's file gets its own reversible backup/restore (joins csv_reverts). WITHOUT this the
# Commands.csv pool + CommandSets slot deploy (the command works) but shows a blank/placeholder name, not the mint.
for _lang in LANGS:
    _src_cn = tl.command_name_mes(_lang)
    if not _src_cn.exists():
        continue
    _live_cn = live.command_name_mes(_lang)
    _live_cn.parent.mkdir(parents=True, exist_ok=True)
    _had = _live_cn.exists()
    if _had:
        shutil.copyfile(_live_cn, BK / f"com_name-{_lang}.mes.preDEPLOY.{STAMP}")
    shutil.copyfile(_src_cn, _live_cn)
    csv_reverts.append((f"com_name-{_lang}", str(_live_cn), _had))
    print(f"  + text/{_lang}/command/com_name.mes (command name)")
# [playable.abilities] inline custom ability -> a per-lang aa_name.mes NAME overlay (the Actions.csv row itself rides
# the "Actions" CSV sync above). Same reversible backup/restore pattern as com_name.
for _lang in LANGS:
    _src_an = tl.ability_name_mes(_lang)
    if not _src_an.exists():
        continue
    _live_an = live.ability_name_mes(_lang)
    _live_an.parent.mkdir(parents=True, exist_ok=True)
    _had = _live_an.exists()
    if _had:
        shutil.copyfile(_live_an, BK / f"aa_name-{_lang}.mes.preDEPLOY.{STAMP}")
    shutil.copyfile(_src_an, _live_an)
    csv_reverts.append((f"aa_name-{_lang}", str(_live_an), _had))
    print(f"  + text/{_lang}/ability/aa_name.mes (ability name)")
# [playable.abilities] SCRIPTED custom ability (`script = {template/body}`) -> the minted battle-FORMULA DLL
# (Memoria.Scripts.<MOD>.dll) the engine Assembly.LoadFile's IN ADDITION to its base (project-ff9-scripts-dll).
# The DLL is the load-bearing artifact -> ship it reversibly (backup/restore/delete, like the CSVs; it joins
# csv_reverts). Its C# Sources are runtime-INERT -> copied additively for provenance + a future recompile. The
# Actions.csv scriptId repoint rides the "Actions" sync above. LOADED ONCE AT THE TITLE SCREEN -> RELAUNCH (not F6).
_src_dll = tl.scripts_dll(MOD_FOLDER)
if _src_dll.exists():
    from ff9mapkit.battle import scriptcompile as _scomp
    _live_dll = live.scripts_dll(MOD_FOLDER)
    _live_dll.parent.mkdir(parents=True, exist_ok=True)
    _had_dll = _live_dll.exists()
    if _had_dll:
        shutil.copyfile(_live_dll, BK / f"{_src_dll.name}.preDEPLOY.{STAMP}")
    try:
        shutil.copyfile(_src_dll, _live_dll)
    except OSError as _dllerr:
        # A running FF9 process memory-maps its loaded Scripts DLL (Assembly.LoadFile) -> Windows refuses to
        # open it for writing (surfaces as a confusing errno, not a plain PermissionError). The backup above
        # already succeeded and nothing live was touched -- just a blocked write, not a corrupted deploy.
        print(f"\n!! could not write {_live_dll.name}: {_dllerr}\n"
              f"   FF9 is very likely still RUNNING with this DLL loaded (it stays mapped even at the title "
              f"screen). Fully QUIT the game (not just return to title), then re-run this deploy.", file=sys.stderr)
        sys.exit(2)
    csv_reverts.append((_src_dll.stem, str(_live_dll), _had_dll))    # stem+".dll" -> the revert codegen's {label}{ext}
    # carry the build stamp (which engine the DLL was compiled against) so the health check / a redeploy can WARN
    # on version drift before the game throws a MissingMemberException at cast (project-ff9-scripts-dll).
    _src_stamp, _live_stamp = _scomp._stamp_path(_src_dll), _scomp._stamp_path(_live_dll)
    if _src_stamp.exists():
        _had_stamp = _live_stamp.exists()
        if _had_stamp:
            shutil.copyfile(_live_stamp, BK / f"{_live_stamp.name}.preDEPLOY.{STAMP}")
        shutil.copyfile(_src_stamp, _live_stamp)
        csv_reverts.append((_live_stamp.stem, str(_live_stamp), _had_stamp))    # stem+".json" -> revert {label}{ext}
    # Sources are runtime-INERT (the game loads only the DLL) -- shipped for provenance + live recompiles.
    # BUILD-owned dirs (Battle formulas, [difficulty], the Overload hub) are REPLACED wholesale: a stale live
    # copy of a removed feature would silently resurrect it at the next live recompile. LIVE-owned feature
    # dirs (battle telemetry) are never touched by the copy.
    from ff9mapkit.battle import overload as _ovl
    _src_srcroot = tl.scripts_dir / "Sources"
    _build_dirs = set(_ovl.build_owned_dirs())
    if _src_srcroot.is_dir():                             # anything the BUILD emitted is build-owned by definition
        _build_dirs |= {d.name for d in _src_srcroot.iterdir() if d.is_dir()}
    for _dname in sorted(_build_dirs):
        _src_d, _live_d = _src_srcroot / _dname, live.scripts_dir / "Sources" / _dname
        shutil.rmtree(_live_d, ignore_errors=True)
        if _src_d.is_dir():
            shutil.copytree(_src_d, _live_d)
    print(f"  + {_src_dll.name} (mod scripts DLL) -> RELAUNCH to load (once at title, not F6)")
    # HOOK STICKINESS (generic -- one path for telemetry + whatever Overload feature comes next): the build's
    # DLL was compiled from the BUILD's sources alone, so a LIVE-owned Overload feature (battle telemetry)
    # would be silently dropped by the copy above -> regenerate the hub + recompile the live DLL from ALL
    # live sources to fold it back in (ff9mapkit.battle.overload.compile_live).
    if _ovl.has_live_extras(live):
        _names = ", ".join(f["name"] for f in _ovl.live_extras(live))
        try:
            _ovl.compile_live(live.root, game=GAME)
            print(f"  + recompiled {_live_dll.name} WITH the live Overload feature(s): {_names} (they stay on)")
        except _scomp.ScriptCompileError as _te:
            print(f"  !! could not fold the live Overload feature(s) ({_names}) back into {_live_dll.name}: {_te}")
    _drift = _scomp.engine_drift_warning(_live_dll, game=GAME)       # normally quiet (just built vs this install)
    if _drift:
        print(f"  !! {_drift}")
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
                 "AbilityFeatures", "MagicSwordSets", "CharacterParameters", "BattleParameters", "CommandSets",
                 "Commands"}
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

# deploy LEDGER (diagnostics only, never load-bearing -- record() swallows filesystem failures). Written
# beside Memoria.ini, OUTSIDE every mod folder, so a deploy_campaign rmtree can't erase the history. What
# it buys: `ff9mapkit doctor` reconciles this against the live DictionaryPatches, so a registration that
# later VANISHES names the checkout + time that put it there -- the thing the 2026-07-18 field-4003 hunt
# had no way to learn (a retired line and a lost line are the same absent line).
from ff9mapkit import deploylog as _dlog
_dlog.record(GAME, _dlog.DEPLOYED, FID, MOD_FOLDER, checkout=_REPO, note=f"{name} <- {TOML.name}")

_mint_ids_repr = repr(sorted(mint_ids))              # this deploy's minted GEO ids (drop their 3DModel lines on revert)
_mint_anim_keys_repr = repr(sorted(mint_anim_keys))   # this deploy's OWN 3DModelAnimation keys (drop only THESE on revert)
_mes_blocks_repr = repr(sorted(message_blocks))        # this deploy's OWN registered text block(s)
revert = f'''#!/usr/bin/env python3
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
from ff9mapkit import dictpatch as _dp
from ff9mapkit import deploylog as _dlog   # NEEDED by the ledger call at the bottom -- a missing import here
#                                            NameErrors every generated revert, and a deploy RUNS the revert
#                                            as its prelude, so that would break deploying outright.
STAMP="{STAMP}"; BK=Path(r"{BK}"); _GAME=find_game_path(); live=ModLayout(_GAME/"{MOD_FOLDER}")
# surgical DictionaryPatch revert: drop THIS id's line + THIS deploy's OWN mint registrations (3DModel <mintId> by
# exact id and 3DModelAnimation <key> by exact key) from the CURRENT live file -- preserving any FOREIGN line another
# tool added into the SAME mod folder since this deploy (deploy_battle's "BattleScene <sceneid>", or a
# `model-anim-new` clip that merely SHARES a minted model's GEO block -- an exact-key drop leaves it be). Then
# restore this id's prior registration from the pre-deploy backup if it had one. A wholesale snapshot-restore (the
# old behavior) re-clobbered co-deployed lines; a GEO-BLOCK drop (the older-still behavior) wiped foreign clip lines
# like key 60001. (The staged Models//Animations/ FBX+clip trees are LEFT on disk -- inert once unregistered.)
_MINT_IDS=set({_mint_ids_repr}); _MINT_ANIM_KEYS=set({_mint_anim_keys_repr}); _MES_BLOCKS=set({_mes_blocks_repr})
_dp_before=live.dictionary_patch.read_text(encoding="utf-8").splitlines()
_dpbak=BK/f"DictionaryPatch.txt.preDEPLOY.{{STAMP}}"
_bak=_dpbak.read_text(encoding="utf-8").splitlines() if _dpbak.exists() else []
_dpkeep,_lost=_dp.revert_dictionary_patch(_dp_before, _bak, fid="{FID}", model_ids=_MINT_IDS, anim_keys=_MINT_ANIM_KEYS, text_blocks=_MES_BLOCKS)
live.dictionary_patch.write_text("\\n".join(_dpkeep)+"\\n", encoding="utf-8", newline="\\n")
for _dl in _lost:   # belt-and-suspenders: a foreign line this revert shouldn't have touched
    print(f"  !! WARNING: revert dropped a DictionaryPatch line it does not own: {{_dl}}")
shutil.rmtree(live.fieldmap_dir("{FBG}"), ignore_errors=True)
mc=live.mapconfig_path("EVT_{name}")
if mc.exists(): mc.unlink()
for L in LANGS:
    p=live.eb_path(L,"EVT_{name}.eb.bytes")
    if p.exists(): p.unlink()
    mb=BK/f"{{L}}-{text_block}.mes.preDEPLOY.{{STAMP}}"
    if mb.exists(): shutil.copyfile(mb, live.mes_path(L,{text_block})){csv_revert_code}{bp_revert_code}{tp_revert_code}{fork_revert_code}
# Ledger: this id is now deliberately UNregistered, so `doctor` won't cry "lost registration" over it. Note a
# deploy runs the prior revert as its PRELUDE, so most 'retired' rows are immediately followed by a 'deployed'
# row -- last-event-wins makes that read correctly. This call only helps NEWLY generated reverts; the ~30 older
# scripts on disk emit nothing, which is exactly why deploylog.reconcile() (not this line) is the mechanism.
_dlog.record(_GAME, _dlog.RETIRED, {FID}, "{MOD_FOLDER}", checkout=r"{_REPO}", note="revert_deploy_{FID}.py")
print("reverted: DictionaryPatch (incl. mint 3DModel/3DModelAnimation) + dialogue + start-state CSVs + BattlePatch + TextPatch + ForkDonorPatch restored; {name} removed. (staged Models//Animations/ trees left inert on disk)")
'''
(OUT / f"revert_deploy_{FID}.py").write_text(revert, encoding="utf-8", newline="\n")    # per-id revert
(OUT / "revert_deploy.py").write_text(revert, encoding="utf-8", newline="\n")            # generic = latest deploy
shutil.rmtree(tmp, ignore_errors=True)
print(f"revert: {OUT / ('revert_deploy_%d.py' % FID)}  (or revert_deploy.py for the latest)")

# text-block guard, BOTH axes: (1) a HIGHER-priority Memoria.ini FolderNames folder also defines this field's
# .mes block -> the engine renders THAT folder's text, not ours (the shared-1073 collision); (2) the block is a
# REAL FF9 location's -> we overwrite the shipping game's own dialogue (the base game is in the engine's
# cumulative text merge, so this needs no stacking at all). A VERBATIM fork re-ships its donor's own text on the
# donor's own block, so it is exempt from (2) -- the overwrite is a byte-identical no-op.
try:
    from ff9mapkit.deploystack import check_text_block_shadow, shadow_warning, donor_block_for
    # The exemption is the DONOR'S OWN BLOCK, not "is a fork": a fork left on the kit default really does
    # overwrite Black Mage Village, and a --native/BG-borrow fork (recorded as source_field/borrow_field,
    # NOT verbatim_eb) is just as entitled to its donor's block as a verbatim one.
    _donor_block = donor_block_for(proj.raw)
    _warn = shadow_warning(
        check_text_block_shadow(GAME, MOD_FOLDER, text_block,
                                verbatim_blocks=() if _donor_block is None else {_donor_block}),
        MOD_FOLDER)
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
