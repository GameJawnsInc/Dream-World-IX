#!/usr/bin/env python3
# Build stock Memoria's native audio plugin SaXAudio.dll from upstream source, and install/restore it
# THROUGH the same rails as build_memoria.py (backup first, sha-verify the landing).
#
# WHY: every sound effect leaks ~0.75 MB in the July-2025 SaXAudio.dll the Memoria patcher installs
# (studies/menu-leak/FINDINGS.md). Upstream fixed it natively (#1388, + #1391/#1404 voice fixes), and the
# native exports are unchanged, so a DLL built from upstream source drops in under our Assembly-CSharp with
# no C# change (studies/menu-leak/FIX-OPTIONS.md, option A1).
#
# The source is exported with `git archive` at a PINNED commit -- the shared clone's working tree (at our
# base 6b8bb2d5, which predates the vendored SaXAudio/ dir) is never touched or checked out.
#
# USAGE:
#   py tools/build_saxaudio.py                     build x64 + x86 into <main repo>/build/saxaudio/<commit>/
#   py tools/build_saxaudio.py --install [--label L]   build if needed, back up live Plugins, install, verify
#   py tools/build_saxaudio.py --restore [TS]      put the newest (or TS-stamped) backup back
#
#   --commit C   upstream commit to build (default PINNED_COMMIT)
#   --clone PATH the Memoria clone (default $MEMORIA_CLONE or C:\gd\FFIX\Memoria)
#
# The plugin loads at launch: install/restore need FF9 CLOSED and a full RELAUNCH, and change audio for
# every session sharing the install -- an owner call.
import argparse
import glob
import io
import os
import shutil
import subprocess
import sys
import tarfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # tools/ -- sibling imports
from backup_memoria_dll import canonical_name, check_label
from build_memoria import DEFAULT_CLONE, DEFAULT_MSBUILD, sha256
from restore_memoria_dll import ARCHES, BKP, GAME, main_repo_root

# The last upstream commit touching SaXAudio/ (origin/main, #1404). Bump deliberately, never "origin/main".
PINNED_COMMIT = "5b49756ce04e752f38173544bcab74254217500d"
DLL = "SaXAudio.dll"
PLUGINS = {a: f"{GAME}/{a}/FF9_Data/Plugins" for a in ARCHES}
MSBUILD_PLATFORM = {"x64": "x64", "x86": "Win32"}
# The vcxproj asks for v143; Build Tools 2026 ships v145, which targets the same vcruntime140 ABI.
TOOLSET = os.environ.get("SAXAUDIO_TOOLSET", "v145")
RUN = subprocess.run                              # seam: tests monkeypatch this


def work_dir(commit):
    return os.path.join(str(main_repo_root()), "build", "saxaudio", commit[:12])


def export_source(clone, commit, dest):
    """`git archive <commit> SaXAudio` into dest/SaXAudio (fresh each time)."""
    src = os.path.join(dest, "SaXAudio")
    shutil.rmtree(src, ignore_errors=True)
    blob = RUN(["git", "-C", clone, "archive", "--format=tar", commit, "SaXAudio"],
               capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(blob)) as tf:
        tf.extractall(dest)
    return os.path.join(src, "SaXAudio.vcxproj")


def msbuild_args(msbuild, vcxproj, arch, out_dir, int_dir):
    # Dash-style switches + list args: no MSYS path-conversion (the s60 lesson). Trailing slashes required.
    return [msbuild, vcxproj, "-t:Build", "-p:Configuration=Release",
            f"-p:Platform={MSBUILD_PLATFORM[arch]}", f"-p:PlatformToolset={TOOLSET}",
            f"-p:OutDir={out_dir}{os.sep}", f"-p:IntDir={int_dir}{os.sep}",
            "-m", "-nologo", "-v:minimal"]


def built_paths(commit):
    return {a: os.path.join(work_dir(commit), "out", a, DLL) for a in ARCHES}


def build(clone, commit):
    wd = work_dir(commit)
    os.makedirs(wd, exist_ok=True)
    vcxproj = export_source(clone, commit, wd)
    for arch in ARCHES:
        out = os.path.join(wd, "out", arch)
        obj = os.path.join(wd, "obj", arch)
        print(f"--- building {DLL} {arch} @ {commit[:12]} (toolset {TOOLSET})")
        r = RUN(msbuild_args(DEFAULT_MSBUILD, vcxproj, arch, out, obj))
        if r.returncode != 0:
            sys.exit(f"!!! BUILD FAILED for {arch} (msbuild exit {r.returncode}).")
    for arch, p in built_paths(commit).items():
        print(f"  {arch}: {p}  sha256 {sha256(p)[:16]}")
    return built_paths(commit)


def ff9_running():
    r = RUN(["tasklist", "/FI", "IMAGENAME eq FF9.exe", "/NH"], capture_output=True, text=True)
    return "FF9.exe" in (r.stdout or "")


def install(paths, label=""):
    if ff9_running():
        sys.exit("!!! FF9.exe is running -- the plugin is locked. Close the game first.")
    ts = time.strftime("%Y%m%d-%H%M%S")
    os.makedirs(BKP, exist_ok=True)
    for arch in ARCHES:
        live = os.path.join(PLUGINS[arch], DLL)
        bk = os.path.join(BKP, canonical_name(DLL, arch, ts, label))
        shutil.copy2(live, bk)
        print(f"  backed up {arch}: {bk}")
    for arch in ARCHES:
        shutil.copy2(paths[arch], os.path.join(PLUGINS[arch], DLL))
    return verify(paths)


def verify(paths):
    ok = True
    for arch in ARCHES:
        want, live = sha256(paths[arch]), os.path.join(PLUGINS[arch], DLL)
        got = sha256(live)
        print(f"  {arch}: {'OK' if got == want else 'MISMATCH'}  live {got[:16]}")
        ok &= got == want
    return ok


def find_backup(arch, ts=None):
    pat = os.path.join(BKP, f"SaXAudio.{arch}.dll.*{ts or ''}*")
    hits = sorted(glob.glob(pat), key=os.path.getmtime)
    return hits[-1] if hits else None


def restore(ts=None):
    if ff9_running():
        sys.exit("!!! FF9.exe is running -- the plugin is locked. Close the game first.")
    picks = {a: find_backup(a, ts) for a in ARCHES}
    if not all(picks.values()):
        sys.exit(f"!!! no SaXAudio backup for every arch in {BKP} (ts={ts!r}): {picks}")
    for arch, bk in picks.items():
        shutil.copy2(bk, os.path.join(PLUGINS[arch], DLL))
        print(f"  restored {arch} <- {bk}")
    return verify(picks)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", default=PINNED_COMMIT)
    ap.add_argument("--clone", default=DEFAULT_CLONE)
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--label", default="")
    ap.add_argument("--restore", nargs="?", const="", default=None, metavar="TS")
    a = ap.parse_args(argv)
    if a.restore is not None:
        return 0 if restore(a.restore or None) else 3
    check_label(a.label)
    paths = built_paths(a.commit)
    if not (a.install and all(os.path.isfile(p) for p in paths.values())):
        paths = build(a.clone, a.commit)
    if a.install:
        if not install(paths, a.label):
            print("!!! the install did NOT fully land.")
            return 3
        print("Installed. RELAUNCH FF9 to load it; revert with --restore.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
