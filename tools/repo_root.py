#!/usr/bin/env python3
"""Resolve the MAIN repo root -- the checkout that owns the real ``.git`` directory.

WHY: tools that back up GAME-INSTALL state (deploy_field's pre-deploy snapshots + generated
revert_deploy_<id>.py, the Memoria DLL snapshots, the New-Game override backups) used to root
those dirs at the checkout they ran from (``Path(__file__)/..``). Run from an agent WORKTREE
that is the worktree -- which is EPHEMERAL: when the worktree is cleaned, the live game install
keeps the deploy while its only backups and revert scripts evaporate, and from every other tree
the deploy reads as unrevertable (memory: project-ff9-worktree-parked-backups; it fired twice on
2026-07-30). Backups of shared mutable state belong in the ONE main repo -- and sharing one
tools/scroll_out also lets a redeploy find a slot's prior revert regardless of which worktree
wrote it (the deploy prelude looks up revert_deploy_<id>.py by path).

MECHANISM: ``git rev-parse --git-common-dir`` answers ``<main>/.git`` from the main repo AND
from every linked worktree; its parent is the main repo root. When git cannot answer (not
installed, not a repo, an odd common-dir name), fall back to the checkout this file runs from --
the scripts' historical behavior, so a gitless environment loses nothing it had.
"""
import subprocess
from pathlib import Path

_HERE = Path(__file__).resolve().parent                     # tools/ in the RUNNING checkout

# Bound at import so a test can swap the `subprocess` NAME on its module instance without the
# except clause then dereferencing the stub (project-ff9-global-module-monkeypatch: swap names,
# never patch a shared module's attributes).
_GIT_ERRORS = (OSError, subprocess.TimeoutExpired)


def _git_common_dir(start: Path):
    """``git rev-parse --git-common-dir`` from ``start``, as an absolute Path -- or None when git
    is unavailable / ``start`` is not inside a repo / the answer is not a ``.git`` dir."""
    try:
        out = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=30)
    except _GIT_ERRORS:
        return None
    if out.returncode != 0:
        return None
    common = Path(out.stdout.strip())
    if common.name != ".git" or not common.is_dir():
        return None
    return common


def main_repo_root(start=None, fallback=None) -> Path:
    """The main repo root as an absolute Path.

    ``start``: directory to resolve from (default: this file's tools/ dir).
    ``fallback``: returned when git cannot answer (default: ``start``'s parent -- i.e. the
    checkout the calling script runs from, the pre-fix behavior)."""
    start = Path(start) if start is not None else _HERE
    if fallback is None:
        fallback = start.parent
    common = _git_common_dir(start)
    if common is not None:
        return common.parent
    return Path(fallback)
