#!/usr/bin/env python3
"""Build any field.toml and deploy it to field 4003 reversibly, reachable via the hut interior door.
Reverts any prior 4003 test first. Run:  python tools/deploy_field.py <path-to-field.toml>
"""
import os, sys, struct, shutil, tempfile, datetime, glob
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import build as B
from ff9mapkit.config import find_game_path, ModLayout, LANGS
from ff9mapkit.eb import EbScript, edit, disasm

TOML = Path(sys.argv[1])
FID = 4003
OUT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out")))
OUT.mkdir(exist_ok=True)

# revert whatever 4003 test is currently deployed (newest revert script wins)
reverts = sorted(glob.glob(str(OUT / "revert_*.py")), key=os.path.getmtime, reverse=True)
if reverts:
    os.system(f'py "{reverts[0]}"')

# build
tmp = Path(tempfile.mkdtemp(prefix="deployfield_"))
info = B.build_mod([B.FieldProject.load(TOML)], tmp / "mod", mod_name="FF9CustomMap")
FBG = info["fields"][0]
name = info["dictionary"][0].split()[3]                     # field name from the dict line
tl = ModLayout(tmp / "mod")
eb0 = tl.eb_path("us", f"EVT_{name}.eb.bytes").read_bytes()
s0 = EbScript.from_bytes(eb0); f0 = s0.entry(0).func_by_tag(0)
scroll = 0x71 in [i.op for i in disasm.iter_code(eb0, f0.abs_start, f0.abs_end)]
print(f"built {FBG} | {info['dictionary'][0]} | scroll={scroll}")

# deploy reversibly
live = ModLayout(find_game_path() / "FF9CustomMap")
BK = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups")))
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copyfile(live.dictionary_patch, BK / f"DictionaryPatch.txt.preDEPLOY.{STAMP}")
for L in LANGS:
    shutil.copyfile(live.eb_path(L, "EVT_HUT_INT.eb.bytes"),
                    BK / f"{L}-EVT_HUT_INT.eb.bytes.preDEPLOY.{STAMP}")
shutil.rmtree(live.fieldmap_dir(FBG), ignore_errors=True)
shutil.copytree(tl.fieldmap_dir(FBG), live.fieldmap_dir(FBG))
for L in LANGS:
    live.ensure_dirs(FBG, langs=[L])
    shutil.copyfile(tl.eb_path(L, f"EVT_{name}.eb.bytes"), live.eb_path(L, f"EVT_{name}.eb.bytes"))
dp = [ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines()
      if ln.strip() and ln.split()[1:2] != [str(FID)]]
dp.append(info["dictionary"][0])
live.dictionary_patch.write_text("\n".join(dp) + "\n", encoding="utf-8", newline="\n")
for L in LANGS:
    p = live.eb_path(L, "EVT_HUT_INT.eb.bytes"); eb = p.read_bytes(); s = EbScript.from_bytes(eb); ok = False
    for ent in s.entries:
        for fn in ent.funcs:
            for ins in disasm.iter_code(eb, fn.abs_start, fn.abs_end):
                if ins.op == 0x2B and ins.imm(0) != FID:
                    eb = edit.patch_bytes(eb, (ins.end - ins.length) + 2, struct.pack("<H", FID),
                                          expect=struct.pack("<H", ins.imm(0))); ok = True
    assert ok, f"{L}: no interior Field() to repoint"
    p.write_bytes(eb)
print(f"deployed {name} -> field {FID}; interior door -> {FID}")

revert = f'''#!/usr/bin/env python3
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
STAMP="{STAMP}"; BK=Path(r"{BK}"); live=ModLayout(find_game_path()/"FF9CustomMap")
shutil.copyfile(BK/f"DictionaryPatch.txt.preDEPLOY.{{STAMP}}", live.dictionary_patch)
for L in LANGS:
    shutil.copyfile(BK/f"{{L}}-EVT_HUT_INT.eb.bytes.preDEPLOY.{{STAMP}}", live.eb_path(L,"EVT_HUT_INT.eb.bytes"))
shutil.rmtree(live.fieldmap_dir("{FBG}"), ignore_errors=True)
for L in LANGS:
    p=live.eb_path(L,"EVT_{name}.eb.bytes")
    if p.exists(): p.unlink()
print("reverted: interior door + DictionaryPatch restored; {name} removed.")
'''
(OUT / "revert_deploy.py").write_text(revert, encoding="utf-8", newline="\n")
shutil.rmtree(tmp, ignore_errors=True)
print(f"revert: {OUT/'revert_deploy.py'}")
print(f"\n=== Reach it: Alexandria -> hut exterior -> interior DOOR -> {name} (4003). ===")
