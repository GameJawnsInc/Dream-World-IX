#!/usr/bin/env python3
# Build (and auto-deploy) the local Memoria engine THROUGH the safety rails.
#
# WHY: the csproj AfterBuild task deploys the built DLLs straight over the live install, so the
# raw msbuild invocation carried FOUR hand-enforced laws with no call site (adversarial review
# Lane H, 2026-08-24):
#   1. Snapshot the live DLLs FIRST (tools/backup_memoria_dll.py) -- forgotten once historically;
#      without it the only way back is re-running Memoria.Patcher.exe.
#   2. Dash-style switches from any MSYS shell -- bash path-converts `/t:`/`/m` into paths ->
#      MSB1008 (bit the owner's own manual run, s60). A list-args subprocess sidesteps the whole
#      class: no shell, no conversion.
#   3. `-p:SolutionDir=<clone>\` with the TRAILING backslash -- omitted, the machine's .NET 4.0
#      mscorlib leaks in -> CS1703/CS0433 duplicate-type errors.
#   4. Verify the deploy LANDED: Output bytes == both arches' Managed copies -- until now checked
#      by hand in every memoria-patches README row. A build while FF9 runs can fail the Deploy
#      task PARTWAY (locked DLLs), leaving a mixed deploy; the verification names exactly which
#      targets carry the new build.
# It also SURFACES the shared-clone reality before building: C:\gd\FFIX\Memoria is one working
# tree shared by every concurrent session, and a build deploys whatever in-flight edits it holds
# (this has shipped another session's changes before -- see the s50 README row). The report is
# advisory, not a block: sharing the tree is the established workflow.
#
# USAGE:
#   py tools/build_memoria.py [--label L] [--no-deploy] [--skip-backup] [--clone PATH]
#
#   --label L      label for the pre-build backup set (letters/digits/hyphens, e.g. pre-s81)
#   --no-deploy    compile-check only: passes -p:DWIXNoDeploy=true (the s45 + s91 csproj lever).
#                  REFUSED unless EVERY Deploy task in Assembly-CSharp's ProjectReference closure
#                  is gated on it -- msbuild builds Memoria.Prime + UnityEngine.UI first, and before
#                  s91 their own AfterBuild deployed them on every "compile-check". Then a TRIPWIRE:
#                  every live DLL + .mdb is sha-compared before/after the build; any change exits 4,
#                  names the files, and keeps the drifted DLLs' pre-run bytes for restore_memoria_dll.
#   --skip-backup  allowed only when a FULL backup set (all 3 DLLs x both arches) newer than
#                  24h already exists in backups/ -- otherwise refused. Prefer the default.
#   --clone PATH   the Memoria source clone (default $MEMORIA_CLONE or C:\gd\FFIX\Memoria)
#
# A DLL change needs a full game RELAUNCH (~ Reload is not enough) and a human playtest.
import argparse
import hashlib
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # tools/ -- sibling imports
from backup_memoria_dll import backup as take_backup, canonical_name, check_label
from restore_memoria_dll import ARCHES, BKP, DLLS, MANAGED, find_backups

DEFAULT_CLONE = os.environ.get("MEMORIA_CLONE", r"C:\gd\FFIX\Memoria")
DEFAULT_MSBUILD = os.environ.get(
    "MSBUILD_EXE",
    r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\amd64\MSBuild.exe")
BASE_COMMIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                                "memoria-patches", "BASE_COMMIT")
FRESH_BACKUP_MAX_AGE_S = 24 * 3600
NO_DEPLOY_GATE = re.compile(r"'\$\(DWIXNoDeploy\)'\s*!=\s*'true'")   # the s45/s91 Condition
LIVE_FILES = [n for dll in DLLS for n in (dll, dll + ".mdb")]         # what a Deploy task writes
RUN = subprocess.run                              # seam: tests monkeypatch this


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def base_commit(path=BASE_COMMIT_FILE):
    """The pinned upstream commit-ish from memoria-patches/BASE_COMMIT (first non-comment token)."""
    try:
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                return ln.split()[0]
    except OSError:
        pass
    return None


def msbuild_args(msbuild, csproj, clone, no_deploy=False):
    """The exact invocation the recipe mandates, as a LIST (no shell => no MSYS mangling).

    The SolutionDir trailing backslash is load-bearing: without it FrameworkPathOverride
    breaks and the machine's .NET 4.0 mscorlib leaks in (CS1703/CS0433).
    """
    soldir = clone.rstrip("\\/") + "\\"
    args = [msbuild, csproj, "-t:Build", "-p:Configuration=Release",
            f"-p:SolutionDir={soldir}", "-m"]
    if no_deploy:
        args.append("-p:DWIXNoDeploy=true")
    return args


def _local(tag):
    return tag.rsplit("}", 1)[-1]                  # the msbuild/2003 namespace, or none


def deploy_gate_audit(csproj_path):
    """Every `<Deploy>` task in the ProjectReference closure of `csproj_path`, split by whether
    -p:DWIXNoDeploy=true switches it off. Returns (gated, ungated, problems), each a list of
    labels like 'Memoria.Prime/Memoria.Prime.csproj: AfterBuild'.

    WHY THE CLOSURE: s45 gated only Assembly-CSharp.csproj, but msbuild BUILDS its
    ProjectReferences first, and Memoria.Prime + UnityEngine.UI each carry their own AfterBuild
    Deploy (s91 gates those) -- so every --no-deploy run still copied both siblings' .dll and a
    fresh .dll.mdb over the live install. A property on the command line reaches the referenced
    builds too, so a Deploy is off when its own Condition or its Target's names it."""
    gated, ungated, problems = [], [], []
    root = os.path.dirname(os.path.dirname(os.path.abspath(csproj_path)))  # the clone
    todo, seen = [os.path.abspath(csproj_path)], set()
    while todo:
        path = todo.pop(0)
        key = os.path.normcase(path)
        if key in seen:
            continue
        seen.add(key)
        rel = os.path.relpath(path, root).replace("\\", "/")
        try:
            tree = ET.parse(path)
        except (OSError, ET.ParseError) as e:
            problems.append(f"{rel}: unreadable ({e})")
            continue
        for tgt in tree.getroot().iter():
            if _local(tgt.tag) != "Target":
                continue
            for el in tgt.iter():
                if _local(el.tag) != "Deploy":
                    continue
                label = f"{rel}: {tgt.get('Name', '?')}"
                on = any(NO_DEPLOY_GATE.search(c or "") for c in (tgt.get("Condition"), el.get("Condition")))
                (gated if on else ungated).append(label)
        for ref in tree.getroot().iter():
            if _local(ref.tag) == "ProjectReference" and ref.get("Include"):
                todo.append(os.path.normpath(os.path.join(os.path.dirname(path),
                                                          ref.get("Include").replace("\\", os.sep))))
    if not gated and not ungated and not problems:
        problems.append("no <Deploy> task found anywhere in the reference closure -- cannot tell "
                        "what the build deploys, so cannot promise it deploys nothing")
    return gated, ungated, problems


def no_deploy_supported(csproj_path):
    """True when EVERY Deploy the build reaches is gated on DWIXNoDeploy (s45 + s91). Otherwise
    -p:DWIXNoDeploy=true is ignored somewhere and the build DEPLOYS anyway -- so --no-deploy must
    be refused rather than become a false promise."""
    gated, ungated, problems = deploy_gate_audit(csproj_path)
    return bool(gated) and not ungated and not problems


def live_snapshot(managed=None, names=None):
    """{(name, arch): bytes or None} for every live engine file a Deploy task writes: each DLL and
    the .dll.mdb pdb2mdb regenerates beside it (a fresh one per deploy, so the .mdb is what shows a
    deploy of unchanged DLL bytes). The bytes are kept so a drifted DLL can be put back."""
    managed = MANAGED if managed is None else managed
    names = LIVE_FILES if names is None else names
    snap = {}
    for arch, mgd in managed.items():
        for name in names:
            try:
                with open(os.path.join(mgd, name), "rb") as f:
                    snap[(name, arch)] = f.read()
            except FileNotFoundError:
                snap[(name, arch)] = None
    return snap


def live_drift(before, after):
    """'<name> [<arch>]' for every live file whose bytes changed, appeared or vanished."""
    return [f"{name} [{arch}]" for (name, arch), b in before.items() if after.get((name, arch)) != b]


def keep_preimages(before, after, ts, bkp=None):
    """Write each DRIFTED DLL's pre-run bytes to `bkp` under the canonical backup name (label
    'pre-nodeploy-drift'), so `restore_memoria_dll.py <ts>` puts them back. The .mdb is not kept,
    as the pre-build backup regime never keeps it: it is debug line info, regenerated per deploy.
    Returns the written paths."""
    bkp = BKP if bkp is None else bkp
    written = []
    for (name, arch), b in before.items():
        if b is None or not name.endswith(".dll") or after.get((name, arch)) == b:
            continue
        dst = os.path.join(bkp, canonical_name(name, arch, ts, "pre-nodeploy-drift"))
        if not os.path.exists(dst):
            with open(dst, "wb") as f:
                f.write(b)
            written.append(dst)
    return written


def full_backup_set_age_s(bkp=BKP, now=None):
    """Age (seconds) of the newest FULL backup set: for each DLL x arch, the newest matching
    backup (arch-specific or neutral); the set's age is the OLDEST of those. None when any
    target has no backup at all -- a partial set is partial safety."""
    now = time.time() if now is None else now
    newest = []
    for dll in DLLS:
        by_arch = find_backups(dll, "", bkp)
        for arch in ARCHES:
            p = by_arch.get(arch) or by_arch.get(None)
            if not p:
                return None
            newest.append(os.path.getmtime(p))
    return now - min(newest)


def preflight_report(clone, runner=None):
    """Advisory: what tree is about to be built+deployed. The clone is SHARED across sessions,
    so foreign in-flight edits ride along -- say so, loudly, before the deploy happens."""
    runner = runner or RUN
    try:
        head = runner(["git", "-C", clone, "rev-parse", "--short", "HEAD"],
                      capture_output=True, text=True, timeout=30).stdout.strip()
        dirty = runner(["git", "-C", clone, "status", "--porcelain"],
                       capture_output=True, text=True, timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        print("  (git unavailable -- cannot report the clone's state)")
        return
    base = base_commit()
    pin = ""
    if base and head and not head.startswith(base[:len(head)]) and not base.startswith(head):
        pin = f"  !! HEAD {head} != the BASE_COMMIT pin {base} -- the patch stack is authored against the pin"
    print(f"  clone: {clone} @ {head or '?'}"
          + (f" ({len(dirty)} modified/untracked file(s) -- the SHARED tree's in-flight edits, "
             "possibly other sessions'; the build deploys them too)" if dirty else " (clean)"))
    if pin:
        print(pin)


def verify_deploy(output_dir, managed=MANAGED, dlls=DLLS):
    """Compare each built DLL in Output against both arches' live Managed copies by sha256.
    Returns (ok, mismatched, absent): lists of '<dll> [<arch>]' labels; absent = the live copy
    or the Output file is missing."""
    ok, mismatched, absent = [], [], []
    for dll in dlls:
        src = os.path.join(output_dir, dll)
        if not os.path.isfile(src):
            absent.extend(f"{dll} [{arch}] (no Output file)" for arch in managed)
            continue
        want = sha256(src)
        for arch, mgd in managed.items():
            dst = os.path.join(mgd, dll)
            label = f"{dll} [{arch}]"
            if not os.path.isfile(dst):
                absent.append(label + " (no live copy)")
            elif sha256(dst) == want:
                ok.append(label)
            else:
                mismatched.append(label)
    return ok, mismatched, absent


def main(argv):
    ap = argparse.ArgumentParser(description="Build the local Memoria engine through the safety "
                                             "rails (pre-build backup, exact msbuild flags, "
                                             "post-deploy verification).")
    ap.add_argument("--label", default="", help="label for the pre-build backup set")
    ap.add_argument("--no-deploy", action="store_true", help="compile-check only (DWIXNoDeploy)")
    ap.add_argument("--skip-backup", action="store_true",
                    help="skip the snapshot -- allowed only when a full set <24h old exists")
    ap.add_argument("--clone", default=DEFAULT_CLONE, help="Memoria source clone")
    args = ap.parse_args(argv[1:])

    clone = args.clone
    csproj = os.path.join(clone, "Assembly-CSharp", "Assembly-CSharp.csproj")
    output_dir = os.path.join(clone, "Output")
    if not os.path.isfile(csproj):
        print(f"!!! no csproj at {csproj} -- wrong --clone / $MEMORIA_CLONE?")
        return 2
    if not os.path.isfile(DEFAULT_MSBUILD):
        print(f"!!! MSBuild not found at {DEFAULT_MSBUILD} -- set $MSBUILD_EXE")
        return 2
    err = check_label(args.label)
    if err:
        print(f"!!! REFUSED: {err}. Nothing built.")
        return 2
    if args.no_deploy:
        gated, ungated, problems = deploy_gate_audit(csproj)
        if ungated or problems or not gated:
            print("!!! --no-deploy REFUSED: the build reaches a Deploy task that DWIXNoDeploy does "
                  "not switch off, so the flag would be ignored there and the build WOULD deploy:")
            for label in ungated:
                print(f"      ungated  {label}")
            for label in problems:
                print(f"      ??       {label}")
            print("    Apply the s45 (Assembly-CSharp) + s91 (Memoria.Prime, UnityEngine.UI) csproj "
                  "hunks, or build without --no-deploy after a backup.")
            return 2

    print("Pre-flight:")
    preflight_report(clone)

    ts = None
    if not args.no_deploy:
        # THE BACKUP LAW'S CALL SITE: the build deploys over the live install, so it does not
        # start until the full 3x2 snapshot exists. --skip-backup only honors a recent FULL set.
        if args.skip_backup:
            age = full_backup_set_age_s(BKP)
            if age is None or age > FRESH_BACKUP_MAX_AGE_S:
                print("!!! --skip-backup REFUSED: no FULL backup set (3 DLLs x 2 arches) newer "
                      f"than {FRESH_BACKUP_MAX_AGE_S // 3600}h in {os.path.abspath(BKP)}. "
                      "Run without --skip-backup.")
                return 2
            print(f"  backup: skipped (full set {age / 3600:.1f}h old exists)")
        else:
            ts = time.strftime("%Y%m%d-%H%M%S")
            print(f"  backup: snapshotting the live DLLs (set {ts})")
            done, missing, failed = take_backup(ts, args.label, BKP, MANAGED)
            if done != len(DLLS) * len(MANAGED):
                print(f"!!! backup INCOMPLETE ({done} captured, {missing} missing, {failed} "
                      "failed) -- NOT building: a partial backup is partial safety.")
                return 2

    # THE --no-deploy TRIPWIRE: the gate audit above reads the csprojs; this reads the install. Every
    # live DLL + .mdb is fingerprinted before the build and compared after it, on the failure path
    # too (a sibling deploys BEFORE Assembly-CSharp compiles, so a failed build can still deploy).
    before = live_snapshot(MANAGED) if args.no_deploy else None
    print(f"\nBuilding ({'compile-check only' if args.no_deploy else 'auto-deploys on success'}):")
    argv_ms = msbuild_args(DEFAULT_MSBUILD, csproj, clone, args.no_deploy)
    r = RUN(argv_ms, capture_output=True, text=True)
    tail = "\n".join((r.stdout or "").splitlines()[-12:])
    print(tail)
    if args.no_deploy:
        after = live_snapshot(MANAGED)
        drift = live_drift(before, after)
        if drift:
            ts = time.strftime("%Y%m%d-%H%M%S")
            kept = keep_preimages(before, after, ts, BKP)
            print(f"\n!!! --no-deploy DEPLOYED ANYWAY: {len(drift)} live engine file(s) changed during "
                  "the build (or another session's deploying build landed in the same window -- "
                  "check before restoring):")
            for label in drift:
                print(f"      CHANGED  {label}")
            if kept:
                print(f"!!! the pre-run DLL bytes were kept ({len(kept)} file(s)); put them back with: "
                      f"py tools/restore_memoria_dll.py {ts}")
            else:
                print("!!! no DLL bytes changed -- only .mdb debug symbols (no behavior change); the "
                      "DWIXNoDeploy gate still leaked and must be fixed.")
            if r.returncode:
                print(f"!!! and the build FAILED (msbuild exit {r.returncode}).")
            return 4
    if r.returncode:
        print(f"\n!!! BUILD FAILED (msbuild exit {r.returncode}).")
        if not args.no_deploy:
            # a failure INSIDE the AfterBuild Deploy task (e.g. FF9 running -> locked DLLs) can
            # leave a PARTIAL deploy; the verification names exactly which targets took the build
            ok, mism, absent = verify_deploy(output_dir, MANAGED)   # pass the global so tests can patch it
            if ok:
                print(f"!!! {len(ok)} live target(s) already MATCH the new Output (partial "
                      "deploy?): " + ", ".join(ok))
                if ts:
                    print(f"!!! restore the pre-build state: py tools/restore_memoria_dll.py {ts}")
        return r.returncode or 1

    if args.no_deploy:
        absent = sum(b is None for b in before.values())
        print(f"\nDone: compile-check clean; NOTHING deployed -- verified: all {len(before)} live "
              "engine files (each DLL + its .mdb, every arch) are byte-identical before and after "
              "the build" + (f" ({absent} absent both times)." if absent else "."))
        return 0

    ok, mism, absent = verify_deploy(output_dir, MANAGED)       # pass the global so tests can patch it
    print("\nDeploy verification (Output sha256 == live Managed):")
    for label in ok:
        print(f"  OK        {label}")
    for label in mism:
        print(f"  MISMATCH  {label}")
    for label in absent:
        print(f"  ABSENT    {label}")
    if mism or absent:
        print("\n!!! the deploy did NOT fully land (FF9 running? locked DLLs?) -- the live "
              "install may be a MIXED set. Close FF9, rebuild"
              + (f", or restore: py tools/restore_memoria_dll.py {ts}" if ts else "."))
        return 3
    print("\nDone: built + deployed + verified (both arches). RELAUNCH the game to load it"
          + (f"; revert with: py tools/restore_memoria_dll.py {ts}" if ts else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
