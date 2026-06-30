"""Detect a Memoria install in an FF9 folder, and (opt-in) install the Dream World IX engine bundle.

Memoria auto-detects mod folders by their ``ModDescription.xml`` and writes ``Memoria.ini`` itself
(in-game verified 2026-06-29: a dropped-in folder is auto-added to ``FolderNames``, enabled), so NOTHING
in this module touches ``Memoria.ini``. The only game-mutating operation is the *optional* engine-DLL swap
(:func:`install_engine_bundle`) -- which BACKS UP the originals first and is fully reversible.

A **novel** field runs on stock Memoria; only a **forked** field needs the Dream World IX engine bundle
(the s23-s33 fork-fidelity patch suite, shipped as ``dwix-custom-memoria-*.zip``: three patched managed
DLLs). The bundle is a separate release asset, never redistributed by the toolkit itself.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

# The three managed DLLs the Dream World IX engine bundle replaces (a patched Memoria build).
ENGINE_DLLS = ("Assembly-CSharp.dll", "Memoria.Prime.dll", "UnityEngine.UI.dll")


def managed_dirs(game) -> list[Path]:
    """The x64 + x86 ``FF9_Data/Managed`` dirs where the engine DLLs live (both kept in lockstep)."""
    game = Path(game)
    return [game / "x64" / "FF9_Data" / "Managed", game / "x86" / "FF9_Data" / "Managed"]


def memoria_status(game) -> dict:
    """Read-only probe of whether Memoria is installed in ``game``. Touches nothing on disk.

    Returns ``{ini, managed_dirs, assembly, installed}`` -- ``installed`` is True iff ``Memoria.ini`` and
    BOTH arch ``Assembly-CSharp.dll`` are present (the minimal signature of a working Memoria install)."""
    game = Path(game)
    ini = game / "Memoria.ini"
    asm = [d / "Assembly-CSharp.dll" for d in managed_dirs(game)]
    return {
        "ini": ini.is_file(),
        "managed_dirs": [d for d in managed_dirs(game) if d.is_dir()],
        "assembly": [p for p in asm if p.is_file()],
        "installed": ini.is_file() and all(p.is_file() for p in asm),
    }


def bundle_dll_members(zip_path) -> dict:
    """Map each :data:`ENGINE_DLLS` name to its member path inside the bundle zip (it may nest them in a
    folder). Raises ``ValueError`` if any of the three is missing -- i.e. this isn't the engine bundle."""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
    found: dict[str, str] = {}
    for dll in ENGINE_DLLS:
        cand = [n for n in names if n.replace("\\", "/").rsplit("/", 1)[-1].lower() == dll.lower()]
        if not cand:
            raise ValueError(
                f"{Path(zip_path).name} is missing {dll} -- this doesn't look like a "
                f"dwix-custom-memoria engine bundle.")
        found[dll] = cand[0]
    return found


def install_engine_bundle(game, zip_path, *, stamp: str) -> dict:
    """Install the Dream World IX engine bundle (the 3 patched managed DLLs) into BOTH the x64 and x86
    ``FF9_Data/Managed`` dirs, backing up the originals first to ``<game>/dwix-engine-backups/<stamp>/``.

    Fully reversible (copy the backed-up DLLs back) and does NOT touch ``Memoria.ini``. Requires Memoria to
    be installed already (this swaps Memoria's managed DLLs for the patched build). Returns a report dict
    ``{backup_root, backed_up, installed}``. Raises ``RuntimeError`` if Memoria isn't installed or
    ``ValueError`` if the zip isn't the engine bundle."""
    game = Path(game)
    if not memoria_status(game)["installed"]:
        raise RuntimeError(
            "Memoria isn't installed in this FF9 folder (no Memoria.ini + Managed Assembly-CSharp.dll). "
            "Install Memoria first, then re-run with --install-engine.")
    members = bundle_dll_members(zip_path)              # validates the bundle before touching the game
    backup_root = game / "dwix-engine-backups" / stamp
    report: dict = {"backup_root": backup_root, "backed_up": [], "installed": []}
    with zipfile.ZipFile(zip_path) as z:
        for mgd in managed_dirs(game):
            if not mgd.is_dir():
                continue
            arch = mgd.parent.parent.name              # "x64" / "x86"
            for dll, member in members.items():
                dst = mgd / dll
                if dst.is_file():                      # back up the original before overwriting
                    bdir = backup_root / arch
                    bdir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dst, bdir / dll)
                    report["backed_up"].append(str(bdir / dll))
                with z.open(member) as src, open(dst, "wb") as out:
                    shutil.copyfileobj(src, out)
                report["installed"].append(str(dst))
    return report
