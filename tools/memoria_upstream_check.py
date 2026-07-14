#!/usr/bin/env python3
"""Watch upstream Memoria for drift under our engine patches, and preserve the
known-good working copy the kit builds against.

WHY THIS EXISTS
---------------
Dream World IX pins its engine to ONE upstream Memoria commit (memoria-patches/
BASE_COMMIT) and carries a stack of local patches (s22-s37) on top. Albeoris keeps
developing Memoria; we do NOT auto-follow. Two risks this tool manages:

  1. DRIFT -- upstream lands changes under files we patch, so a future rebase (when
     we choose to bump the pin) will conflict. We want to SEE that coming, on our
     own schedule, as a deliberate decision -- never a surprise.

  2. A BREAKING UPSTREAM UPDATE -- if the shared clone (C:/gd/FFIX/Memoria) gets
     pulled forward and no longer builds a compatible Assembly-CSharp.dll, we must
     still be able to reproduce the EXACT engine the kit currently ships. This tool
     snapshots the pinned source tree AND the deployed binaries so the known-good
     engine is preserved independently of the clone's HEAD.

SCOPE / CONTRIBUTION POLICY
---------------------------
This is DWIX-internal monitoring + preservation tooling. It is READ-ONLY toward the
Memoria clone (it fetches remote refs and reads history; it never pulls, checks out,
or edits the clone's working tree). It does NOT author engine changes and does NOT
produce anything for upstream submission -- Memoria DLL work is done by the humans on
this project, by hand.

USAGE
-----
  py tools/memoria_upstream_check.py check        # drift report (default)
  py tools/memoria_upstream_check.py check --no-fetch
  py tools/memoria_upstream_check.py snapshot      # preserve pinned source + deployed DLLs
  py tools/memoria_upstream_check.py list          # list saved snapshots
  py tools/memoria_upstream_check.py restore <id>  # redeploy a snapshot's DLLs to the game

Exit codes (check): 0 = every live patch still applies to upstream; 2 = at least one
live patch would conflict on the current upstream tip (a rebase is pending); 1 = error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --- Configuration ---------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
PATCH_DIR = REPO_ROOT / "memoria-patches"
BASE_COMMIT_FILE = PATCH_DIR / "BASE_COMMIT"
SNAP_DIR = REPO_ROOT / "backups" / "memoria-snapshots"

# The Memoria source clone (gitignored, shared). Override with $FF9_MEMORIA_CLONE.
CLONE = Path(os.environ.get("FF9_MEMORIA_CLONE", r"C:/gd/FFIX/Memoria"))

# The game's Managed folders -- where the built engine DLLs live (source of truth
# for "the working copy the kit is using"). Override with $FF9_GAME_DIR.
GAME = Path(os.environ.get("FF9_GAME_DIR", r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"))
MANAGED = [GAME / "x64/FF9_Data/Managed", GAME / "x86/FF9_Data/Managed"]
ENGINE_DLLS = ["Assembly-CSharp.dll", "Memoria.Prime.dll", "UnityEngine.UI.dll"]

# Patch files that are dev history, NOT part of the live stack (README.md ->
# "Superseded / historical"). Everything else matching s*.patch is live.
HISTORICAL_PREFIXES = ("s12", "s18", "s21")

C_RESET, C_BOLD, C_RED, C_YEL, C_GRN, C_DIM = (
    ("\033[0m", "\033[1m", "\033[31m", "\033[33m", "\033[32m", "\033[2m")
    if sys.stdout.isatty() else ("", "", "", "", "", "")
)


# --- Small helpers ---------------------------------------------------------

def die(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"{C_RED}error:{C_RESET} {msg}", file=sys.stderr)
    sys.exit(1)


def git(*args: str, cwd: Path | None = None, check: bool = True) -> str:
    """Run git and return stdout (text). Never touches the working tree unless the
    caller explicitly asks (this module only ever fetches / reads / uses worktrees)."""
    cp = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True, text=True,
    )
    if check and cp.returncode != 0:
        die(f"git {' '.join(args)}\n{cp.stderr.strip()}")
    return cp.stdout.strip()


def read_base_commit() -> str:
    if not BASE_COMMIT_FILE.exists():
        die(f"missing pin file: {BASE_COMMIT_FILE}")
    for line in BASE_COMMIT_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line.split()[0]
    die(f"no commit-ish found in {BASE_COMMIT_FILE}")


def require_clone() -> None:
    if not (CLONE / ".git").exists():
        die(f"Memoria clone not found at {CLONE}\n"
            f"       set $FF9_MEMORIA_CLONE to your clone path.")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def live_patches() -> list[Path]:
    out = []
    for p in sorted(PATCH_DIR.glob("s*.patch")):
        if not p.name.startswith(HISTORICAL_PREFIXES):
            out.append(p)
    return out


def files_touched(patch: Path) -> list[str]:
    """Repo-relative paths a patch modifies (from its '+++ b/<path>' lines)."""
    files: list[str] = []
    for line in patch.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip().split("\t")[0]
            if target in ("/dev/null",):
                continue
            if target.startswith("b/"):
                target = target[2:]
            files.append(target)
    return files


def resolve_upstream_ref() -> str:
    """The upstream default-branch ref (origin/main or origin/master)."""
    try:
        head = git("symbolic-ref", "refs/remotes/origin/HEAD", cwd=CLONE, check=True)
        return head.replace("refs/remotes/", "")
    except SystemExit:
        pass
    for cand in ("origin/main", "origin/master"):
        cp = subprocess.run(["git", "rev-parse", "--verify", "--quiet", cand],
                            cwd=str(CLONE), capture_output=True, text=True)
        if cp.returncode == 0:
            return cand
    die("could not resolve upstream default branch (origin/main or origin/master)")


# --- check -----------------------------------------------------------------

def cmd_check(args: argparse.Namespace) -> int:
    require_clone()
    base = read_base_commit()

    print(f"{C_BOLD}Memoria upstream drift check{C_RESET}")
    print(f"  clone      {CLONE}")
    print(f"  pinned base {C_BOLD}{base}{C_RESET}  ({BASE_COMMIT_FILE.relative_to(REPO_ROOT)})")

    # Warn if the shared clone has drifted off our pin -- a build done now would
    # not match what the patches expect.
    clone_head = git("rev-parse", "HEAD", cwd=CLONE)
    base_full = git("rev-parse", base, cwd=CLONE)
    if clone_head != base_full:
        print(f"  {C_YEL}NOTE{C_RESET} clone HEAD is {clone_head[:10]}, not the pin "
              f"{base_full[:10]} -- checkout the pin before building the pinned engine.")

    if args.no_fetch:
        print(f"  {C_YEL}--no-fetch: upstream refs may be stale{C_RESET}")
    else:
        print("  fetching origin ...")
        git("fetch", "--quiet", "origin", cwd=CLONE)

    upstream = resolve_upstream_ref()
    up_sha = git("rev-parse", upstream, cwd=CLONE)
    behind = git("rev-list", "--count", f"{base}..{upstream}", cwd=CLONE)
    print(f"  upstream   {upstream} @ {up_sha[:10]}  ({behind} commit(s) ahead of the pin)\n")

    if base_full == up_sha:
        print(f"{C_GRN}Up to date -- the pin is upstream tip. No drift.{C_RESET}")
        return 0

    # Union of files our live patches touch, and which upstream commits moved them.
    patches = live_patches()
    touched: dict[str, list[Path]] = {}
    for p in patches:
        for f in files_touched(p):
            touched.setdefault(f, []).append(p)

    print(f"{C_BOLD}Upstream changes under patched files ({base[:10]}..{upstream}){C_RESET}")
    drifted_files = 0
    for f in sorted(touched):
        log = git("log", "--oneline", "--no-decorate", f"{base}..{upstream}", "--", f,
                  cwd=CLONE, check=False)
        if log:
            drifted_files += 1
            owners = ", ".join(sorted({p.stem.split("-")[0] for p in touched[f]}))
            print(f"  {C_YEL}{f}{C_RESET}  {C_DIM}[{owners}]{C_RESET}")
            for line in log.splitlines():
                print(f"      {line}")
    if drifted_files == 0:
        print(f"  {C_GRN}none -- upstream moved but not under any patched file.{C_RESET}")
    print()

    # Does each live patch still apply to the current upstream tip? Test in a
    # throwaway worktree so the primary checkout is never touched.
    print(f"{C_BOLD}Would each live patch still apply to {upstream}?{C_RESET}")
    conflicts = _apply_check_all(patches, up_sha)

    print()
    if conflicts:
        print(f"{C_YEL}{len(conflicts)} patch(es) would conflict on the current upstream tip.{C_RESET}")
        print("A rebase is pending IF/WHEN you decide to bump the pin. Until then the")
        print("shipped engine is unaffected -- it builds from the pinned base.")
        return 2
    print(f"{C_GRN}All live patches still apply cleanly to upstream tip.{C_RESET}")
    return 0


def _apply_check_all(patches: list[Path], up_sha: str) -> list[str]:
    conflicts: list[str] = []
    wt = Path(tempfile.mkdtemp(prefix="memoria-drift-"))
    try:
        git("worktree", "add", "--quiet", "--detach", str(wt), up_sha, cwd=CLONE)
        for p in patches:
            status = _apply_check_one(wt, p)
            conflicts.append(p.name) if status == "CONFLICT" else None
            color = {"clean": C_GRN, "clean*": C_YEL, "CONFLICT": C_RED}[status]
            print(f"  {color}{status:<9}{C_RESET} {p.name}")
    finally:
        git("worktree", "remove", "--force", str(wt), cwd=CLONE, check=False)
        shutil.rmtree(wt, ignore_errors=True)
    return conflicts


def _apply_check_one(worktree: Path, patch: Path) -> str:
    """'clean' (applies), 'clean*' (applies only with --ignore-whitespace, e.g. a
    CRLF/LF mismatch), or 'CONFLICT'."""
    strict = subprocess.run(
        ["git", "apply", "--check", "-p1", str(patch)],
        cwd=str(worktree), capture_output=True, text=True)
    if strict.returncode == 0:
        return "clean"
    loose = subprocess.run(
        ["git", "apply", "--check", "-p1", "--ignore-whitespace", str(patch)],
        cwd=str(worktree), capture_output=True, text=True)
    return "clean*" if loose.returncode == 0 else "CONFLICT"


# --- snapshot / list / restore --------------------------------------------

def cmd_snapshot(args: argparse.Namespace) -> int:
    """Preserve the known-good engine: the pinned SOURCE tree (as a git archive of
    the pinned commit, independent of the clone's future HEAD) + the currently
    DEPLOYED DLLs + a manifest of hashes. This is the insurance against an upstream
    update that later breaks compat."""
    require_clone()
    base = read_base_commit()
    base_full = git("rev-parse", base, cwd=CLONE)
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    snap = SNAP_DIR / f"{base_full[:10]}.{ts}"
    snap.mkdir(parents=True, exist_ok=True)

    print(f"{C_BOLD}Snapshotting the pinned Memoria engine{C_RESET}")
    print(f"  pin  {base_full[:10]}")
    print(f"  into {snap.relative_to(REPO_ROOT)}\n")

    # 1. Source tree at the pinned commit (zip, independent of the clone).
    src_zip = snap / f"memoria-source-{base_full[:10]}.zip"
    with open(src_zip, "wb") as fh:
        cp = subprocess.run(["git", "archive", "--format=zip", base_full],
                            cwd=str(CLONE), stdout=fh)
    if cp.returncode != 0:
        die("git archive of the pinned source failed")
    print(f"  source  {src_zip.name}  ({src_zip.stat().st_size // 1024} KiB)")

    # 2. The deployed engine DLLs (the actual working binaries) + hashes.
    manifest = {
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        "pinned_base": base_full,
        "upstream_remote": git("remote", "get-url", "origin", cwd=CLONE, check=False),
        "clone_head_at_snapshot": git("rev-parse", "HEAD", cwd=CLONE),
        "source_archive": src_zip.name,
        "dlls": {},
    }
    dll_out = snap / "dlls-x64"
    dll_out.mkdir(exist_ok=True)
    src_managed = MANAGED[0]
    for dll in ENGINE_DLLS:
        srcp = src_managed / dll
        if not srcp.exists():
            print(f"  {C_YEL}dll     {dll}: not deployed, skipped{C_RESET}")
            continue
        digest = sha256(srcp)
        if not args.no_binaries:
            shutil.copy2(srcp, dll_out / dll)
        manifest["dlls"][dll] = {"sha256": digest, "size": srcp.stat().st_size}
        kept = "copied" if not args.no_binaries else "hash-only"
        print(f"  dll     {dll:<22} {digest[:16]}...  ({kept})")

    (snap / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{C_GRN}Snapshot saved.{C_RESET} Restore the engine binaries with:")
    print(f"  py tools/memoria_upstream_check.py restore {snap.name}")
    return 0


def _snapshots() -> list[Path]:
    if not SNAP_DIR.exists():
        return []
    return sorted((d for d in SNAP_DIR.iterdir() if (d / "MANIFEST.json").exists()))


def cmd_list(_args: argparse.Namespace) -> int:
    snaps = _snapshots()
    if not snaps:
        print("No snapshots yet. Create one with:  py tools/memoria_upstream_check.py snapshot")
        return 0
    print(f"{C_BOLD}Memoria engine snapshots{C_RESET}  ({SNAP_DIR.relative_to(REPO_ROOT)})")
    for s in snaps:
        m = json.loads((s / "MANIFEST.json").read_text(encoding="utf-8"))
        has_bin = any((s / "dlls-x64" / d).exists() for d in ENGINE_DLLS)
        tag = "binaries" if has_bin else "hash-only"
        print(f"  {s.name:<28} base {m['pinned_base'][:10]}  {m['created']}  [{tag}]")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    snap = SNAP_DIR / args.snapshot
    if not (snap / "MANIFEST.json").exists():
        die(f"no snapshot '{args.snapshot}' (see: memoria_upstream_check.py list)")
    m = json.loads((snap / "MANIFEST.json").read_text(encoding="utf-8"))
    dll_dir = snap / "dlls-x64"
    present = [d for d in ENGINE_DLLS if (dll_dir / d).exists()]
    if not present:
        die(f"snapshot '{args.snapshot}' is hash-only (no binaries) -- rebuild from its\n"
            f"       source archive ({m['source_archive']}) at pin {m['pinned_base'][:10]} instead.")

    print(f"{C_BOLD}Restoring engine DLLs from {snap.name}{C_RESET}  (base {m['pinned_base'][:10]})")
    # Back up what's live now before overwriting, mirroring restore_memoria_dll.py.
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    bkp = REPO_ROOT / "backups"
    bkp.mkdir(exist_ok=True)
    for dll in present:
        for mgd in MANAGED:
            dst = mgd / dll
            if dst.exists():
                shutil.copy2(dst, bkp / f"{dll}.preRESTORE.{stamp}")
                break
        for mgd in MANAGED:
            shutil.copy2(dll_dir / dll, mgd / dll)
        print(f"  {dll:<22} restored to x64 + x86")
    print(f"\n{C_GRN}Done.{C_RESET} Relaunch FF9 to load the restored engine.")
    return 0


# --- main ------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Monitor upstream Memoria drift and preserve the pinned engine.")
    sub = ap.add_subparsers(dest="cmd")

    p_check = sub.add_parser("check", help="report upstream drift under our patches (default)")
    p_check.add_argument("--no-fetch", action="store_true",
                         help="skip 'git fetch' (use already-fetched refs)")
    p_check.set_defaults(func=cmd_check)

    p_snap = sub.add_parser("snapshot", help="preserve the pinned source + deployed DLLs")
    p_snap.add_argument("--no-binaries", action="store_true",
                        help="record DLL hashes only, don't copy the binaries")
    p_snap.set_defaults(func=cmd_snapshot)

    sub.add_parser("list", help="list saved snapshots").set_defaults(func=cmd_list)

    p_rest = sub.add_parser("restore", help="redeploy a snapshot's DLLs to the game")
    p_rest.add_argument("snapshot", help="snapshot id (see: list)")
    p_rest.set_defaults(func=cmd_restore)

    args = ap.parse_args()
    if not getattr(args, "func", None):
        args = ap.parse_args(["check"])
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
