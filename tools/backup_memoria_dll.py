#!/usr/bin/env python3
# Snapshot the game's live Memoria engine DLLs into backups/ BEFORE an engine build.
#
# WHY: the Memoria build pipeline AUTO-DEPLOYS on build with NO backup (the csproj AfterBuild
# copies into both Managed folders), so the pre-build snapshot is the only revert point.
# Historically this step was a hand-typed copy command, which produced four different naming
# conventions in backups/ and never once captured Memoria.Prime.dll / UnityEngine.UI.dll.
# This script IS the standard now: one canonical name, all 3 DLLs, both arches, one shared
# timestamp so a single selector restores the whole set.
#
# USAGE:
#   py tools/backup_memoria_dll.py [label]     # label: letters/digits/hyphens, e.g. pre-s48
#
# Writes  backups/<stem>.<arch>.dll[.<label>].<YYYYMMDD-HHMMSS>
# e.g.    backups/Assembly-CSharp.x64.dll.pre-s48.20260722-101500
# and prints the matching restore one-liner. Exits non-zero unless the FULL set (3 DLLs x
# 2 arches) was captured -- a partial backup is partial safety, and this says so loudly.
#
# backups/ resolves to the MAIN repo's backups/ via BKP (restore_memoria_dll -> repo_root), so a
# worktree run no longer parks the snapshot in an ephemeral tree. The created-dir warning below
# fires only on the gitless fallback (or a fresh clone), where BKP is this checkout's own.
import os, re, shutil, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from restore_memoria_dll import ARCHES, BKP, DLLS, MANAGED  # one source of truth


def canonical_name(dll, arch, ts, label=""):
    stem, ext = os.path.splitext(dll)
    mid = f".{label}" if label else ""
    return f"{stem}.{arch}{ext}{mid}.{ts}"


def check_label(label):
    """Reject a label that would break the restore side: arch tokens misclassify the backup
    (restore routes on delimited x64/x86 tokens anywhere in the name), and anything outside
    letters/digits/hyphens breaks the [._-] tokenization contract."""
    if not label:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", label):
        return f"label '{label}' -- use letters/digits/hyphens only"
    if set(label.split("-")) & set(ARCHES):
        return f"label '{label}' contains an arch token ({'/'.join(ARCHES)}) -- it would misroute the backup on restore"
    return None


def backup(ts, label="", bkp=BKP, managed=MANAGED):
    """Copy each arch's live DLLs into `bkp` under the canonical name.

    Returns (done, missing, failed): missing = source DLL absent, failed = copy error or an
    already-existing destination (never overwritten -- a backup that clobbers a backup is
    worse than none).
    """
    done = missing = failed = 0
    for dll in DLLS:
        for arch, mgd in managed.items():
            src = os.path.join(mgd, dll)
            if not os.path.isfile(src):
                print(f"  !! {dll} [{arch}]: not found at {src} -- SKIPPED")
                missing += 1
                continue
            dst = os.path.join(bkp, canonical_name(dll, arch, ts, label))
            if os.path.exists(dst):
                print(f"  !! {dll} [{arch}]: {os.path.basename(dst)} already exists -- NOT overwritten")
                failed += 1
                continue
            try:
                shutil.copy2(src, dst)
            except OSError as e:
                print(f"  !! {dll} [{arch}]: COPY FAILED ({e})")
                failed += 1
                continue
            print(f"  {os.path.basename(dst)}")
            done += 1
    return done, missing, failed


def main(argv):
    label = argv[1] if len(argv) > 1 else ""
    err = check_label(label)
    if err:
        print(f"!!! REFUSED: {err}. Nothing backed up.")
        return 1
    ts = time.strftime("%Y%m%d-%H%M%S")
    print(f"Backing up live Memoria DLLs -> {os.path.abspath(BKP)}  (set: {ts})\n")
    if not os.path.isdir(BKP):
        os.makedirs(BKP)
        print(f"  !! created {os.path.abspath(BKP)} -- if this is a WORKTREE, prefer the main repo\n")
    done, missing, failed = backup(ts, label, BKP, MANAGED)
    expected = len(DLLS) * len(MANAGED)
    if done == 0:
        print(f"\n!!! NOTHING BACKED UP ({missing} missing, {failed} failed). Do NOT build until this works.")
        return 1
    if missing or failed:
        print(f"\n!! PARTIAL: {done}/{expected} captured ({missing} missing, {failed} failed) -- partial backup = partial safety.")
        print(f"!! Restore what WAS captured with: py tools/restore_memoria_dll.py {ts}")
        return 1
    print(f"\nDone: full set captured ({done}/{expected}).")
    print(f"Restore with: py tools/restore_memoria_dll.py {ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
