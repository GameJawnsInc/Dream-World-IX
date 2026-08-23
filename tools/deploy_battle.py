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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # tools/ -- for repo_root
from repo_root import main_repo_root  # noqa: E402
from ff9mapkit.config import find_game_path, ModLayout, LANGS  # noqa: E402
from ff9mapkit.battle.build import BattleProject, build_battle_mod  # noqa: E402
from ff9mapkit.eb import opcodes  # noqa: E402
from ff9mapkit.fsutil import FileLockTimeout, atomic_write_text, locked_sidecar  # noqa: E402

# TWO roots, deliberately distinct (the same split as tools/deploy_field.py): REPO is the RUNNING checkout
# and owns the per-worktree .ff9deploy.toml deploy pin; MAIN is the main repo and owns backups/ +
# tools/scroll_out. Rooting those at REPO parked a deploy's ONLY pre-deploy backups and its revert script
# in an ephemeral agent worktree -- the live install kept the deploy while its undo evaporated with the
# tree (project-ff9-worktree-parked-backups). One shared scroll_out also means a battle's prior
# revert_battle_<BBG>.py is findable no matter which worktree wrote it.
REPO = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
MAIN = main_repo_root()


def _mod_folder_default():
    f = REPO / ".ff9deploy.toml"
    if f.is_file():
        try:
            mf = tomllib.loads(f.read_text(encoding="utf-8")).get("mod_folder")
            if mf:
                return mf
        except Exception as e:
            # a malformed pin must not silently drop this checkout into the SHARED default folder --
            # that clobber is the exact hazard the pin exists to prevent (same rule as deploy_field).
            print(f"!! {f} is unreadable/malformed ({e})\n"
                  f"!! refusing to guess a deploy target -- fix the file, or delete it to accept the "
                  f"shared defaults deliberately.", file=sys.stderr)
            raise SystemExit(2)
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
OUT = MAIN / "tools" / "scroll_out"
OUT.mkdir(parents=True, exist_ok=True)
BK = MAIN / "backups"
BK.mkdir(parents=True, exist_ok=True)              # gitignored -- absent in a fresh clone
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
    # LOCKED read->merge->write: hold <DictionaryPatch>.lock across the whole window (same lock as
    # deploy_field and the generated reverts). Two unserialised rewrites into ONE folder silently drop
    # whichever lines the other read past -- a lost FieldScene/BattleScene line is the null-.eb black
    # screen. A lock TIMEOUT aborts LOUDLY below rather than proceeding unlocked.
    try:
        with locked_sidecar(live.dictionary_patch):
            if live.dictionary_patch.exists():
                shutil.copyfile(live.dictionary_patch, BK / f"DictionaryPatch.txt.preBATTLE.{STAMP}")
                cur = [ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines() if ln.strip()]
            else:
                cur = []
            sid = str(proj.scene_id) if proj.is_mint else None
            # NOTE: this filter is LINE-SHAPE sensitive -- it assumes `BattleScene <id> <NAME> <BBG>` (BBG in
            # column 4). It predates dictpatch._registration_identity and is deliberately left alone here; the
            # identity-based filter lives in build_battle_mod, which owns the built dist.
            cur = [ln for ln in cur if not (ln.startswith("BattleScene")
                                            and (ln.split()[3:4] == [BBG] or ln.split()[1:2] == [sid]))]
            cur += info["dictionary"]
            # ATOMIC: a half-written DictionaryPatch unregisters every field/battle in the folder at the next launch
            atomic_write_text(live.dictionary_patch, "\n".join(cur) + "\n", newline="\n")
    except FileLockTimeout as _lke:
        print(f"!! {_lke}\n"
              f"!! NOT splicing the BattleScene registration into {live.dictionary_patch} -- the battle "
              f"assets are copied but UNREGISTERED. Re-run this deploy once the other writer finishes.",
              file=sys.stderr)
        sys.exit(2)
    relaunch = True

# BattlePatch: SPLICE under this battle's `//` sentinel markers instead of appending. The old code appended
# the built lines to the live file blindly, so deploying the same battle twice left two copies of its
# Battle:/BattleBackground block in the live file -- and there was no way to REMOVE a block once the toml
# stopped emitting it. merge_battle_patch replaces our own block, preserves every other line (a co-deployed
# field's block under `field <id>` markers, another battle's, a stacked worktree's), and is idempotent.
# Same pattern as tools/deploy_field.py. BattlePatch is parsed once at startup -> a change needs a RELAUNCH.
from ff9mapkit.battle import battlepatch as _bp  # noqa: E402
_bp_owner = _bp.battle_owner(BBG, proj.scene_id if proj.is_mint else None)
_live_bp_text = live.battle_patch.read_text(encoding="utf-8") if live.battle_patch.exists() else ""
bp_revert_code = ""
# trigger on the EXACT begin marker, never a substring: a bare battle_owner token is a PREFIX of the same
# battle's with-scene token, so `_bp_owner in text` armed on a block this deploy does not own.
if info["battle_patch"] or _bp.has_block(_live_bp_text, _bp_owner):
    if live.battle_patch.exists():
        shutil.copyfile(live.battle_patch, BK / f"BattlePatch.txt.preBATTLE.{STAMP}")
    _merged = _bp.merge_battle_patch(_live_bp_text, info["battle_patch"], _bp_owner)
    if _merged:
        atomic_write_text(live.battle_patch, _merged, newline="\n")
    elif live.battle_patch.exists():          # our last block went away and nothing else owns the file
        live.battle_patch.unlink()
    # SURGICAL revert (battlepatch.revert_splice): restore OUR pre-deploy block into the file as it stands
    # AT REVERT TIME -- the old snapshot restore re-clobbered every block another deploy spliced in between
    # (and it looked for the backup under the generated script's BK = bk_dir, while the deploy wrote it to
    # the backups ROOT above -- the restore branch crashed on FileNotFoundError whenever it was needed).
    # The backup path is interpolated ABSOLUTE at generation time so the two can never disagree again.
    bp_revert_code = (
        '\nfrom ff9mapkit.battle import battlepatch as _bpm'
        '\nfrom ff9mapkit.fsutil import atomic_write_text as _awt'
        f'\n_bpb = Path({str(BK / f"BattlePatch.txt.preBATTLE.{STAMP}")!r})'
        '\n_bpl = LIVE/"BattlePatch.txt"'
        '\n_bpn = _bpm.revert_splice(_bpl.read_text(encoding="utf-8") if _bpl.exists() else "",'
        f'\n                         _bpb.read_text(encoding="utf-8") if _bpb.exists() else "", {_bp_owner!r})'
        '\nif _bpn: _awt(_bpl, _bpn, newline="\\n")'
        '\nelif _bpl.exists(): _bpl.unlink()')
    if info["battle_patch"]:
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
    "#!/usr/bin/env python3\nimport shutil, sys\nfrom pathlib import Path\n"
    f"sys.path.insert(0, {KIT!r})\n"                       # the bp fragment imports ff9mapkit modules
    f"LIVE = Path(r{str(live_root)!r})\nBK = Path(r{str(bk_dir)!r})\n"
    f"CREATED = {created!r}\nOVERWRITTEN = {overwritten!r}\n"
    "for rel in CREATED:\n"
    "    (LIVE/rel).unlink(missing_ok=True)\n"
    "for rel in OVERWRITTEN:\n"
    "    b = BK/rel\n"
    "    if b.exists(): shutil.copyfile(b, LIVE/rel)\n"
    + bp_revert_code +
    f"\nprint('reverted battle deploy for {BBG}"
    f"{' (incl. its BattlePatch block)' if bp_revert_code else ''}. If DictionaryPatch lines were "
    f"spliced, restore {BK.as_posix()}/*.preBATTLE.{STAMP}; relaunch FF9.')\n",
    encoding="utf-8", newline="\n")
shutil.rmtree(tmp, ignore_errors=True)

for w in info["warnings"]:
    print(f"warning: {w}")
print(f"revert: py {revert}")
print("Relaunch the game (DictionaryPatch/BattlePatch load at launch)." if relaunch
      else "No relaunch needed (the FBX + textures are read at battle start).")
if proj.is_mint and _args.trigger_field is None:
    print(f"Trigger: set a field's [encounter] scene = {proj.scene_id}, or re-run with --trigger-field N.")
