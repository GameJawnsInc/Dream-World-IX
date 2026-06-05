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

# revert the PRIOR field deploy only (our own revert_deploy.py) -- NOT other tools' reverts
# (e.g. revert_alex_fast_warp.py): the Alexandria fast-warp points at 4003 and must SURVIVE a
# field deploy, so we never run it here.
prior = OUT / "revert_deploy.py"
if prior.exists():
    import subprocess
    _flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0   # no console flash when called by the GUI
    subprocess.run([sys.executable, str(prior)], creationflags=_flags)

# build
tmp = Path(tempfile.mkdtemp(prefix="deployfield_"))
info = B.build_mod([B.FieldProject.load(TOML)], tmp / "mod", mod_name="FF9CustomMap")
FBG = info["fields"][0]
name = info["dictionary"][0].split()[4]                     # script/field name (field 4: ...area MAPID NAME textid)
text_block = int(info["dictionary"][0].split()[5])          # textid (field 5) -> dialogue .mes block
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
    lm = live.mes_path(L, text_block)
    if lm.exists():
        shutil.copyfile(lm, BK / f"{L}-{text_block}.mes.preDEPLOY.{STAMP}")
src_fm = tl.fieldmap_dir(FBG)
if src_fm.exists() and any(src_fm.iterdir()):          # borrow fields ship no scene -> skip
    shutil.rmtree(live.fieldmap_dir(FBG), ignore_errors=True)
    shutil.copytree(src_fm, live.fieldmap_dir(FBG))
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
for L in LANGS:
    p = live.eb_path(L, "EVT_HUT_INT.eb.bytes"); eb = p.read_bytes(); s = EbScript.from_bytes(eb)
    has_field = False
    for ent in s.entries:
        for fn in ent.funcs:
            for ins in disasm.iter_code(eb, fn.abs_start, fn.abs_end):
                if ins.op == 0x2B:
                    has_field = True
                    if ins.imm(0) != FID:                       # already-FID is fine (idempotent)
                        eb = edit.patch_bytes(eb, (ins.end - ins.length) + 2, struct.pack("<H", FID),
                                              expect=struct.pack("<H", ins.imm(0)))
    assert has_field, f"{L}: no interior Field() at all"
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
    mb=BK/f"{{L}}-{text_block}.mes.preDEPLOY.{{STAMP}}"
    if mb.exists(): shutil.copyfile(mb, live.mes_path(L,{text_block}))
print("reverted: interior door + DictionaryPatch + dialogue restored; {name} removed.")
'''
(OUT / "revert_deploy.py").write_text(revert, encoding="utf-8", newline="\n")
shutil.rmtree(tmp, ignore_errors=True)
print(f"revert: {OUT/'revert_deploy.py'}")
print(f"\n=== Reach it: Alexandria -> hut exterior -> interior DOOR -> {name} (4003). ===")
