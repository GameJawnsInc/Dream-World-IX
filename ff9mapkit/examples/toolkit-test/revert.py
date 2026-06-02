#!/usr/bin/env python3
"""Revert the TESTROOM (field 4003) in-game test.

Restores the interior exit door (4003 -> 4000) and the DictionaryPatch from the pre-test
backups, and removes the TESTROOM assets. Run:  py -3 ff9mapkit/examples/toolkit-test/revert.py
"""
import shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo/ff9mapkit
from ff9mapkit.config import find_game_path, ModLayout, LANGS

STAMP = "20260602-153427"
REPO = Path(__file__).resolve().parents[3]   # C:/gd/FFIX
BKP = REPO / "backups"
mod = ModLayout(find_game_path() / "FF9CustomMap")

# 1) restore DictionaryPatch (drops the 4003 line) + interior ebs (un-repoints the door)
shutil.copyfile(BKP / f"DictionaryPatch.txt.preTESTROOM.{STAMP}", mod.dictionary_patch)
for L in LANGS:
    shutil.copyfile(BKP / f"{L}-EVT_HUT_INT.eb.bytes.preTESTROOM.{STAMP}",
                    mod.eb_path(L, "EVT_HUT_INT.eb.bytes"))

# 2) remove TESTROOM assets
shutil.rmtree(mod.fieldmap_dir("FBG_N11_TESTROOM"), ignore_errors=True)
for L in LANGS:
    p = mod.eb_path(L, "EVT_TESTROOM.eb.bytes")
    if p.exists():
        p.unlink()

print("reverted: interior door -> 4000, DictionaryPatch restored, TESTROOM assets removed.")
