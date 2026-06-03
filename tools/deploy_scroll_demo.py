#!/usr/bin/env python3
"""Build + deploy the painted SCROLLDEMO room (field 4003) reversibly, reachable via the hut
interior door. The kit now auto-injects BGCACTIVE for [camera.scroll] fields, so this is just:
build -> copy assets -> merge DictionaryPatch -> repoint interior Field(...)->4003.

Run from a CLEAN 2-room state. Writes tools/scroll_out/revert_scroll_demo.py. Run:
    python tools/deploy_scroll_demo.py
"""
import os, sys, struct, shutil, tempfile, datetime
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import build as B
from ff9mapkit.config import find_game_path, ModLayout, LANGS
from ff9mapkit.eb import EbScript, edit, disasm

TOML = Path(KIT) / "examples" / "scroll-demo" / "scroll_demo.field.toml"
NAME = "SCROLLDEMO"
FID = 4003
OUT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out")))
OUT.mkdir(parents=True, exist_ok=True)

# ---- build via the kit (into a temp mod) ----
tmp = Path(tempfile.mkdtemp(prefix="scrolldemo_"))
info = B.build_mod([B.FieldProject.load(TOML)], tmp, mod_name="FF9CustomMap")
FBG = info["fields"][0]
tl = ModLayout(tmp)
# sanity: scroll fields must carry the BGCACTIVE enable
eb0 = tl.eb_path("us", f"EVT_{NAME}.eb.bytes").read_bytes()
s0 = EbScript.from_bytes(eb0); f0 = s0.entry(0).func_by_tag(0)
assert 0x71 in [i.op for i in disasm.iter_code(eb0, f0.abs_start, f0.abs_end)], "no BGCACTIVE"
print("built:", FBG, "| dict:", info["dictionary"][0], "| BGCACTIVE ok")

# ---- deploy reversibly ----
live = ModLayout(find_game_path() / "FF9CustomMap")
BK = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups")))
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copyfile(live.dictionary_patch, BK / f"DictionaryPatch.txt.preSCROLLDEMO.{STAMP}")
for L in LANGS:
    shutil.copyfile(live.eb_path(L, "EVT_HUT_INT.eb.bytes"),
                    BK / f"{L}-EVT_HUT_INT.eb.bytes.preSCROLLDEMO.{STAMP}")

# copy fieldmaps + EVTs
shutil.rmtree(live.fieldmap_dir(FBG), ignore_errors=True)
shutil.copytree(tl.fieldmap_dir(FBG), live.fieldmap_dir(FBG))
for L in LANGS:
    live.ensure_dirs(FBG, langs=[L])
    shutil.copyfile(tl.eb_path(L, f"EVT_{NAME}.eb.bytes"), live.eb_path(L, f"EVT_{NAME}.eb.bytes"))

# merge DictionaryPatch 4003 line (drop any stale 4003 entry, keep 4000/4002)
dp = [ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines()
      if ln.strip() and ln.split()[1:2] != [str(FID)]]
dp.append(info["dictionary"][0])
live.dictionary_patch.write_text("\n".join(dp) + "\n", encoding="utf-8", newline="\n")

# repoint the interior door (the single Field() in entry 3) -> 4003, all langs
for L in LANGS:
    p = live.eb_path(L, "EVT_HUT_INT.eb.bytes")
    eb = p.read_bytes(); s = EbScript.from_bytes(eb); patched = False
    for ent in s.entries:
        for fn in ent.funcs:
            for ins in disasm.iter_code(eb, fn.abs_start, fn.abs_end):
                if ins.op == 0x2B and ins.imm(0) != FID:           # Field(non-4003) -> 4003
                    argoff = (ins.end - ins.length) + 2
                    eb = edit.patch_bytes(eb, argoff, struct.pack("<H", FID),
                                          expect=struct.pack("<H", ins.imm(0)))
                    patched = True
    assert patched, f"{L}: no interior Field() to repoint"
    p.write_bytes(eb)
print("deployed SCROLLDEMO -> field 4003; interior door -> 4003; DictionaryPatch merged")

# ---- revert script ----
revert = f'''#!/usr/bin/env python3
"""Revert SCROLLDEMO (4003): restore interior door + DictionaryPatch, remove SCROLLDEMO."""
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
STAMP = "{STAMP}"; BK = Path(r"{BK}")
live = ModLayout(find_game_path() / "FF9CustomMap")
shutil.copyfile(BK / f"DictionaryPatch.txt.preSCROLLDEMO.{{STAMP}}", live.dictionary_patch)
for L in LANGS:
    shutil.copyfile(BK / f"{{L}}-EVT_HUT_INT.eb.bytes.preSCROLLDEMO.{{STAMP}}", live.eb_path(L, "EVT_HUT_INT.eb.bytes"))
shutil.rmtree(live.fieldmap_dir("{FBG}"), ignore_errors=True)
for L in LANGS:
    p = live.eb_path(L, "EVT_{NAME}.eb.bytes")
    if p.exists():
        p.unlink()
print("reverted: interior door + DictionaryPatch restored; SCROLLDEMO removed.")
'''
(OUT / "revert_scroll_demo.py").write_text(revert, encoding="utf-8", newline="\n")
shutil.rmtree(tmp, ignore_errors=True)
print(f"revert: {OUT/'revert_scroll_demo.py'}")
print("\n=== Reach it: Alexandria -> hut exterior -> interior DOOR -> SCROLLDEMO (4003). ===")
