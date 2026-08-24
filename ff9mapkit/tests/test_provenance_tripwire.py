"""THE PROVENANCE TRIPWIRE -- the enforcement call site for docs/PROVENANCE.md's zero-SE-bytes gate.

The gate ("ff9mapkit contains no Final Fantasy IX game data") was a claim in a document with no check
that could fail: .gitignore fences the known extraction paths, but gitignore does not stop an explicit
add in a NEW location -- which is exactly how the Lane F audit (2026-08-23) found ``release/FF9CustomMap``:
a committed, distributable mod folder whose BUILT ``.eb`` files embed the SE-derived blank-field template
verbatim (39 of 55 sampled 64-byte windows of ``data/blank_field/us.eb.bytes`` appear inside the tracked
``EVT_HUT_EXT.eb.bytes``). The author reasonably believed the bundle clean ("hand-built rooms") because
the subtlety -- every kit BUILD bakes the game-derived blank into its output, the very reason the build
goldens are SHA-256 hashes rather than bytes -- was articulated in PROVENANCE.md only for goldens.

These tests are the law's call site: the tracked tree and any locally built dists are scanned for the
game-derived byte CLASSES, against a justified allowlist. Repo-layout only (an installed package has no
tree to scan); skipped cleanly when git is absent.
"""
from __future__ import annotations

import glob
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Byte classes that are game-derived BY FORMAT (an .eb/.mes/.bgx/... in the tree is either extracted
# from p0data or built ON the extracted templates -- both SE-derived unless proven kit-authored):
_ONE = {".eb", ".mes", ".bgx", ".bgi", ".raw16", ".raw17", ".akb", ".inb", ".ff9mesh", ".strings"}
_TWO = {".eb.bytes", ".bgi.bytes", ".raw16.bytes", ".raw17.bytes"}
_NAME_FRAGS = ("p0data",)

# Tracked files of a flagged CLASS that are provably the KIT'S OWN bytes (each with its provenance):
_ALLOWED = {
    # the from-scratch hut's walkmesh, BUILT by the kit from authored geometry -- deliberately
    # un-ignored in ff9mapkit/.gitignore (`!tests/fixtures/hut_ext.bgi.bytes`)
    "ff9mapkit/tests/fixtures/hut_ext.bgi.bytes",
    # the same hut's camera, SYNTHESIZED by the kit for a novel scene (no borrow); moved out of the
    # release bundle by the Lane F audit because the bundle's .eb files are NOT clean
    "art/hut/FBG_N11_HUT_INT.bgx",
}

# CONFIRMED VIOLATION, REMOVAL PENDING THE OWNER'S CALL (Lane F, 2026-08-23): the committed demo mod
# folder. Its .mes/.bgx/.bgi are kit-authored, but its 28 built .eb files embed the SE-derived
# blank-field template (measured -- see the module docstring). The folder is publicly distributed, so
# removing it -- and whether to scrub history -- is the owner's outward-facing decision, not a test's.
# When the folder is removed, DELETE this prefix so the tripwire becomes the permanent guard there.
_PENDING_OWNER_REMOVAL_PREFIX = "release/FF9CustomMap/"


_SOURCE_SUFFIXES = {".py", ".md", ".toml", ".txt", ".json", ".rst", ".ps1", ".yml", ".yaml", ".cfg", ".in"}


def _flagged(name: str) -> bool:
    n = name.lower()
    p = Path(n)
    if p.suffix in _ONE:
        return True
    if "".join(p.suffixes[-2:]) in _TWO:
        return True
    # name fragments flag DATA files only -- a source file ABOUT p0data (tools/spike_p0data.py) is code
    return p.suffix not in _SOURCE_SUFFIXES and any(f in n for f in _NAME_FRAGS)


def _tracked_files() -> list:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git not on PATH")
    r = subprocess.run([git, "-C", str(REPO), "ls-files"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        pytest.skip("not a git checkout (installed-package layout)")
    return r.stdout.splitlines()


def test_tracked_tree_carries_no_new_game_derived_bytes():
    hits = {f for f in _tracked_files() if _flagged(f)}
    pending = {f for f in hits if f.startswith(_PENDING_OWNER_REMOVAL_PREFIX)}
    fresh = sorted(hits - _ALLOWED - pending)
    assert not fresh, (
        "PROVENANCE: tracked file(s) of a game-derived byte class are not in the allowlist. Either the "
        "file carries Square-Enix-derived bytes (remove it -- the repo is PUBLIC and the gate is ZERO, "
        "docs/PROVENANCE.md) or it is provably kit-authored (add it to _ALLOWED here WITH its provenance "
        "story, like the hut walkmesh):\n  " + "\n  ".join(fresh))


def test_the_allowlist_is_live_not_stale():
    # a stale allowlist row outlives its file and quietly widens the gate; every entry must exist
    tracked = set(_tracked_files())
    dead = sorted(f for f in _ALLOWED if f not in tracked)
    assert not dead, f"allowlisted file(s) no longer tracked -- delete the row(s): {dead}"


def test_wheel_package_data_stays_pinned_to_provenance_clean_files():
    """PROVENANCE.md's boldest claim -- 'a build can never bundle FF9 bytes, even on a machine where
    extract-templates has been run' -- rests on the package-data allowlist naming ONLY kit-authored
    files. Verified empirically in the Lane F audit (wheel AND sdist built on a fully-provisioned
    machine: zero flagged entries); this pin keeps the allowlist from drifting."""
    py = (REPO / "ff9mapkit" / "pyproject.toml").read_text(encoding="utf-8")
    assert "data/provenance/*.patch" in py
    section = py.split("[tool.setuptools.package-data]", 1)[1].split("[", 1)[0]
    code = "\n".join(ln for ln in section.splitlines() if not ln.lstrip().startswith("#"))
    for banned in ("blank_field", "region_template.bin", "data/*.bin", "fixtures"):
        assert banned not in code, \
            f"package-data must never glob {banned!r} -- that is how a wheel bundles FF9 bytes"


def test_built_dists_carry_no_game_derived_entries():
    """Scan any locally built dist archives (ff9mapkit/dist/*). data/provenance/ entries are the CLEAN
    mechanism (copy/insert patches + hashes) and are exempt by path."""
    arcs = glob.glob(str(REPO / "ff9mapkit" / "dist" / "*.whl")) + \
        glob.glob(str(REPO / "ff9mapkit" / "dist" / "*.tar.gz"))
    if not arcs:
        pytest.skip("no built dists present (ff9mapkit/dist/)")
    for a in arcs:
        if a.endswith(".tar.gz"):
            with tarfile.open(a) as t:
                names = t.getnames()
        else:
            with zipfile.ZipFile(a) as z:
                names = z.namelist()
        bad = sorted(n for n in names
                     if "data/provenance/" not in n.replace("\\", "/")
                     and (_flagged(n) or "blank_field" in n or "region_template.bin" in n))
        assert not bad, f"{Path(a).name} packages game-derived entries:\n  " + "\n  ".join(bad)
