#!/usr/bin/env python3
# Restore Memoria engine DLLs into the game's Managed folders (x64 + x86).
#
# WHY: Session 12 stood up a local Memoria build and deployed an edited Assembly-CSharp.dll
# (fade texture-cache + booster auto-enable). The Memoria build pipeline AUTO-DEPLOYS on build
# (the AfterBuild "Deploy" MSBuild task copies to the game), so there is no pristine original on
# disk. The closest no-edits revert point is the UNMODIFIED 6b8bb2d5 rebuild, backed up under
# backups/ as *.baseline-rebuild-6b8bb2d5.*.
#
# USAGE:
#   py tools/restore_memoria_dll.py baseline   # revert to no-edits rebuild (isolates my edits)
#   py tools/restore_memoria_dll.py <suffix>   # restore any backup set matching that timestamp suffix
#
# To get the TRUE original Memoria 2025-07-13 install back, re-run the Memoria patcher
# (Memoria.Patcher.exe) against the game folder, or Steam "Verify integrity of game files"
# then re-patch. (The on-disk 06-01 DLLs are functionally equivalent: same source commit.)
import os, sys, glob, shutil

BKP  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backups")
GAME = r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
MANAGED = [GAME + "/x64/FF9_Data/Managed", GAME + "/x86/FF9_Data/Managed"]
DLLS = ["Assembly-CSharp.dll", "Memoria.Prime.dll", "UnityEngine.UI.dll"]

def find_backup(dll, sel):
    # backups are named "<dll>.<label>.<timestamp>"
    cands = sorted(glob.glob(os.path.join(BKP, dll + ".*" + sel + "*")))
    return cands[-1] if cands else None

def main():
    sel = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    print(f"Restoring Memoria DLLs matching '{sel}' -> game Managed (x64 + x86)\n")
    for dll in DLLS:
        src = find_backup(dll, sel)
        if not src:
            print(f"  !! no backup found for {dll} matching '{sel}' -- SKIPPED")
            continue
        for mgd in MANAGED:
            dst = os.path.join(mgd, dll)
            shutil.copy2(src, dst)
        print(f"  {dll:<22} <- {os.path.basename(src)}")
    print("\nDone. Launch the game to test. (Edited build = run a fresh Memoria build to redeploy.)")

if __name__ == "__main__":
    main()
