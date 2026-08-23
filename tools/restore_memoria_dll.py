#!/usr/bin/env python3
# Restore Memoria engine DLLs into the game's Managed folders (x64 + x86).
#
# WHY: Session 12 stood up a local Memoria build and deployed an edited Assembly-CSharp.dll.
# The Memoria build pipeline AUTO-DEPLOYS on build (the AfterBuild "Deploy" MSBuild task copies
# to the game), so there is no pristine original on disk -- the backups/ snapshots taken before
# each build are the only revert points.
#
# USAGE:
#   py tools/restore_memoria_dll.py <selector>   # restore the newest backup set matching <selector>
#   py tools/restore_memoria_dll.py baseline     # the historical no-edits-rebuild set (may be absent!)
#
# The selector is a substring of the backup file name -- usually a timestamp like
# "20260722-095733". Backup names in backups/ come in several conventions, ALL matched here:
#   Assembly-CSharp.dll.<label-or-timestamp>        arch-neutral -> restored to BOTH arches
#   Assembly-CSharp.dll.x64.<timestamp>             arch-specific (old convention)
#   Assembly-CSharp.dll.<label>-x64.<timestamp>     arch-specific (labeled)
#   Assembly-CSharp.x64.dll.<timestamp>             arch-specific (current build-lane convention)
#   Assembly-CSharp.x64.dll.<label>.<timestamp>     the CANONICAL form tools/backup_memoria_dll.py
#                                                   writes (that script is the standard way to take
#                                                   the pre-build snapshot -- all 3 DLLs x 2 arches)
# An arch-specific backup restores only to its own Managed folder; per arch the newest match
# (by mtime) wins. If NOTHING matches, the script says so LOUDLY and exits non-zero -- it used
# to print "Done." after restoring zero files (found the hard way 2026-07-22, s47 review).
#
# To get the TRUE original Memoria install back, re-run the Memoria patcher
# (Memoria.Patcher.exe) against the game folder, or Steam "Verify integrity of game files"
# then re-patch.
#
# Close FF9 first: the running game memory-maps the DLLs, so the copy fails (WinError 1224).
import glob, os, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # tools/ -- for repo_root (a spec-loaded run lacks it)
from repo_root import main_repo_root

# backups/ lives in the MAIN repo, resolved via git even from an agent worktree: a worktree-parked
# DLL snapshot evaporates with the tree while the game keeps the (possibly bad) build, and this
# script then finds nothing to restore (project-ff9-worktree-parked-backups). Falls back to this
# checkout's own backups/ when git cannot answer -- the pre-fix behavior.
BKP  = str(main_repo_root() / "backups")
GAME = r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
ARCHES = ("x64", "x86")
MANAGED = {a: f"{GAME}/{a}/FF9_Data/Managed" for a in ARCHES}
DLLS = ["Assembly-CSharp.dll", "Memoria.Prime.dll", "UnityEngine.UI.dll"]


def backup_arch(name):
    """Which arch a backup file is FOR: 'x64'/'x86' when the name carries that token, else None (= both)."""
    tokens = re.split(r"[._-]", name)
    for arch in ARCHES:
        if arch in tokens:
            return arch
    return None


def find_backups(dll, sel, bkp=BKP):
    """Backups of `dll` whose basename contains `sel`, newest (mtime) per arch.

    Returns {arch: path} with keys drawn from {'x64', 'x86', None}; None = arch-neutral.
    """
    stem, ext = os.path.splitext(dll)
    patterns = [dll + ".*"] + [f"{stem}.{arch}{ext}.*" for arch in ARCHES]
    paths = set()
    for pat in patterns:
        paths.update(glob.glob(os.path.join(bkp, pat)))
    by_arch = {}
    for p in sorted(paths, key=lambda p: (os.path.getmtime(p), os.path.basename(p))):
        if sel in os.path.basename(p):
            by_arch[backup_arch(os.path.basename(p))] = p  # later (newer) assignment wins
    return by_arch


def restore(sel, bkp=BKP, managed=MANAGED):
    """Copy the newest matching backup of each DLL into each arch's Managed folder.

    Returns (restored, failed) copy counts. A DLL with no matching backup is reported and
    skipped (the backups/ tree has never held all three DLLs at once); a copy ERROR counts
    as failed.
    """
    restored = failed = 0
    for dll in DLLS:
        by_arch = find_backups(dll, sel, bkp)
        if not by_arch:
            print(f"  !! no backup found for {dll} matching '{sel}' -- SKIPPED")
            continue
        for arch, mgd in managed.items():
            src = by_arch.get(arch) or by_arch.get(None)
            if not src:
                print(f"  !! {dll}: no {arch} or arch-neutral backup matching '{sel}' -- {arch} SKIPPED")
                continue
            try:
                shutil.copy2(src, os.path.join(mgd, dll))
            except OSError as e:
                print(f"  !! {dll} [{arch}]: COPY FAILED ({e}) -- is FF9 running? Close it and re-run.")
                failed += 1
                continue
            print(f"  {dll:<22} [{arch}] <- {os.path.basename(src)}")
            restored += 1
    return restored, failed


def newest_backups(bkp=BKP, per_dll=2):
    """The newest few backup basenames per DLL -- shown when a selector matches nothing."""
    lines = []
    for dll in DLLS:
        cands = sorted(find_backups(dll, "", bkp).values(),
                       key=os.path.getmtime, reverse=True)[:per_dll]
        lines += [f"    {os.path.basename(c)}" for c in cands]
    return lines


def main(argv):
    sel = argv[1] if len(argv) > 1 else "baseline"
    print(f"Restoring Memoria DLLs matching '{sel}' -> game Managed (x64 + x86)\n")
    restored, failed = restore(sel, BKP, MANAGED)   # pass the globals so tests can patch them
    if restored == 0 and failed == 0:
        print(f"\n!!! NOTHING RESTORED -- no backup in {os.path.abspath(BKP)} matches '{sel}'.")
        print("!!! The game's DLLs are UNCHANGED. Newest backups on disk:")
        hints = newest_backups(BKP)
        print("\n".join(hints) if hints else "    (none at all)")
        print("!!! For true stock, re-run Memoria.Patcher.exe against the game folder.")
        return 1
    if failed:
        print(f"\n!! PARTIAL: {restored} file(s) restored, {failed} FAILED. Close FF9 and re-run.")
        return 1
    print(f"\nDone: {restored} file(s) restored. Launch the game to test. "
          "(Edited build = run a fresh Memoria build to redeploy.)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
