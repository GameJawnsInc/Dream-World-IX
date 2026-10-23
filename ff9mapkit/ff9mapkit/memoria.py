"""Detect a Memoria install in an FF9 folder, and (opt-in) install the Dream World IX engine bundle.

Memoria auto-detects mod folders by their ``ModDescription.xml`` and writes ``Memoria.ini`` itself
(in-game verified 2026-06-29: a dropped-in folder is auto-added to ``FolderNames``, enabled), so NOTHING
in this module touches ``Memoria.ini``. The only game-mutating operation is the *optional* engine-DLL swap
(:func:`install_engine_bundle`) -- which BACKS UP the originals first and is fully reversible.

A **novel** field runs on stock Memoria; only a **forked** field needs the Dream World IX engine bundle
(the s23-s33 fork-fidelity patch suite, shipped as ``dwix-custom-memoria-*.zip``: three patched managed
DLLs, plus since b20 the leak-fixed native SaXAudio.dll). The bundle is a separate release asset, never redistributed by the toolkit itself.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from datetime import date, timedelta
from pathlib import Path

from . import fsutil

# The three managed DLLs the Dream World IX engine bundle replaces (a patched Memoria build).
ENGINE_DLLS = ("Assembly-CSharp.dll", "Memoria.Prime.dll", "UnityEngine.UI.dll")

# The native plugins a bundle MAY also carry, per arch, under ``Plugins/<arch>/<name>`` in the zip. Since
# b20 that is Memoria's SaXAudio.dll built from upstream's leak-fixed source (tools/build_saxaudio.py):
# stock's July-2025 build leaks ~0.7 MB per sound effect. Optional, so an older managed-only bundle
# still installs; they land in ``<arch>/FF9_Data/Plugins``, next to Managed.
ENGINE_PLUGINS = ("SaXAudio.dll",)
PLUGIN_ARCHES = ("x64", "x86")

# The Memoria base commit the shipped engine bundle is built against (for the install-time notice).
# Memoria stamps no commit hash into its DLLs (Assembly-CSharp is AssemblyVersion("1.1.*") -> a
# build-DATE-derived FileVersion; Memoria.Prime is hardcoded 1.0.0.0), so we can't read the user's
# commit -- but Assembly-CSharp's FileVersion DOES tell our patched build apart from a stock one.
BASE_COMMIT = "6b8bb2d5"

# The calendar date of BASE_COMMIT. Memoria's Assembly-CSharp is AssemblyVersion("1.1.*"), and .NET
# wildcard versioning fills the BUILD field with days-since-2000-01-01 -- so a DLL's FileVersion IS its
# compile date, decodable with arithmetic alone (this is the same number Memoria.log prints as
# "[Initialization] Memoria version: YYYY-MM-DD"). BASE_COMMIT was the main commit nearest this date.
BASE_COMMIT_DATE = date(2025, 7, 13)

# How far an installed engine's compile date may drift from BASE_COMMIT_DATE before we mention that the
# prebuilt bundle may not be a clean match. Rough, advisory: the bundle replaces the 3 MANAGED DLLs and
# the SaXAudio plugin, never the rest of Memoria's native side, so a big drift is a real (if not certain) mismatch risk -- see docs/ENGINE.md
# ("pinned to a specific Memoria base -- if you run a much newer Memoria and hit crashes, build from source").
STALE_WARNING_DAYS = 180


def assembly_build_date(version: str | None) -> date | None:
    """The compile date encoded in a ``"1.1.<build>.<revision>"`` FileVersion, or ``None`` if the string
    isn't that 4-part numeric shape. See :data:`BASE_COMMIT_DATE` for why build == days since 2000-01-01."""
    if not version:
        return None
    parts = str(version).split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        return None
    try:
        return date(2000, 1, 1) + timedelta(days=int(parts[2]))
    except (OverflowError, ValueError):                 # a nonsense build number, e.g. 9999999
        return None


def dwix_backup_dirs(game) -> list[Path]:
    """The per-install ``<game>/dwix-engine-backups/<stamp>/`` dirs, sorted (oldest stamp first).

    Their presence is the cheap, reliable signal that OUR installer applied the engine bundle here --
    :func:`install_engine_bundle` is the only thing that creates them. Fingerprinting the live DLL bytes
    would be stronger but needs a bundle to compare against, which ``doctor`` doesn't have."""
    root = Path(game) / "dwix-engine-backups"
    if not root.is_dir():
        return []
    return sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name)


def engine_report(game) -> dict:
    """Everything ``doctor`` (and the GUI's Setup & Health page) needs to explain the engine situation in
    plain language, with no bundle zip in hand. Purely read-only + advisory; every field may be ``None``.

    Returns ``{memoria_installed, assembly_version, assembly_build_date, base_commit_date,
    dwix_bundle_applied, dwix_backup_count}``."""
    game = Path(game)
    installed = memoria_status(game)["installed"]
    version = read_assembly_version(managed_dirs(game)[0] / "Assembly-CSharp.dll") if installed else None
    backups = dwix_backup_dirs(game)
    return {
        "memoria_installed": installed,
        "assembly_version": version,
        "assembly_build_date": assembly_build_date(version),
        "base_commit_date": BASE_COMMIT_DATE,
        "dwix_bundle_applied": bool(installed and backups),
        "dwix_backup_count": len(backups),
    }


def read_assembly_version(dll_path) -> str | None:
    """The FileVersion of a managed DLL (e.g. ``'1.1.9670.29463'``), read from its Win32
    ``VS_VERSIONINFO`` resource in pure stdlib (ctypes) -- no .NET runtime, no ``pefile``.

    The resource lives in the PE ``.rsrc`` section and is readable WITHOUT loading the assembly into a
    CLR. Windows-only; returns ``None`` off Windows, on a missing file, or if the resource is absent
    (so every caller treats a version as best-effort/advisory, never load-bearing)."""
    if sys.platform != "win32":
        return None
    p = Path(dll_path)
    if not p.is_file():
        return None
    try:
        import ctypes
        from ctypes import wintypes

        ver = ctypes.windll.version
        ver.GetFileVersionInfoSizeW.restype = wintypes.DWORD
        ver.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        ver.GetFileVersionInfoW.restype = wintypes.BOOL
        ver.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
        ver.VerQueryValueW.restype = wintypes.BOOL
        ver.VerQueryValueW.argtypes = [
            ctypes.c_void_p, wintypes.LPCWSTR,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]

        size = ver.GetFileVersionInfoSizeW(str(p), None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ver.GetFileVersionInfoW(str(p), 0, size, buf):
            return None
        ptr = ctypes.c_void_p()
        length = wintypes.UINT()
        if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(length)) or not length.value:
            return None

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD), ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD), ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD), ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD), ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD), ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD), ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD)]

        ffi = ctypes.cast(ptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        ms, ls = ffi.dwFileVersionMS, ffi.dwFileVersionLS
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:                                       # noqa: BLE001 - version read is advisory
        return None


def bundle_assembly_version(zip_path) -> str | None:
    """The FileVersion of the engine bundle's own ``Assembly-CSharp.dll`` (best-effort, Windows-only).

    Extracts just that member to a temp file (the bundle is fixed, so this is a stable identity of our
    patched build) and reads its :func:`read_assembly_version`. Returns ``None`` if unreadable."""
    try:
        member = bundle_dll_members(zip_path)["Assembly-CSharp.dll"]
    except (ValueError, OSError):
        return None
    with zipfile.ZipFile(zip_path) as z, tempfile.TemporaryDirectory() as td:
        out = Path(td) / "Assembly-CSharp.dll"
        with z.open(member) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return read_assembly_version(out)


def engine_compat(game, zip_path) -> dict:
    """Compare the INSTALLED Memoria engine version with the Dream World IX bundle's, to tell whether
    our patches are already in place vs need (re)applying.

    Returns ``{installed, bundle, already_applied}`` -- ``already_applied`` is True iff both versions
    read and are equal (i.e. the live Assembly-CSharp IS our patched build). Versions are ``None`` off
    Windows / if unreadable, in which case ``already_applied`` is False and the caller just installs.
    The signal also catches a Memoria RE-PATCH: that reverts the live DLL to stock, so a later run sees
    ``installed != bundle`` and reapplies."""
    asm = managed_dirs(Path(game))[0] / "Assembly-CSharp.dll"   # x64 is the canonical probe
    installed = read_assembly_version(asm)
    bundle = bundle_assembly_version(zip_path)
    return {"installed": installed, "bundle": bundle,
            "already_applied": bool(installed and bundle and installed == bundle)}


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


def bundle_plugin_members(zip_path) -> dict:
    """Map ``(arch, plugin)`` to its member path for each :data:`ENGINE_PLUGINS` the bundle carries at
    ``Plugins/<arch>/<plugin>`` (optionally nested in a folder, like the DLLs). Empty for a managed-only
    bundle. Raises ``ValueError`` when a plugin is present for one arch but not the other -- installing
    it into a single arch would leave x64 and x86 playing different audio engines."""
    with zipfile.ZipFile(zip_path) as z:
        names = [n.replace("\\", "/") for n in z.namelist()]
    found: dict[tuple[str, str], str] = {}
    for plugin in ENGINE_PLUGINS:
        for arch in PLUGIN_ARCHES:
            tail = f"plugins/{arch}/{plugin}".lower()
            cand = [n for n in names if n.lower() == tail or n.lower().endswith("/" + tail)]
            if cand:
                found[(arch, plugin)] = cand[0]
        arches = [a for a in PLUGIN_ARCHES if (a, plugin) in found]
        if arches and len(arches) != len(PLUGIN_ARCHES):
            raise ValueError(f"{Path(zip_path).name} carries {plugin} for {', '.join(arches)} only -- "
                             f"a bundle must ship it for every arch ({', '.join(PLUGIN_ARCHES)}).")
    return found


def install_engine_bundle(game, zip_path, *, stamp: str) -> dict:
    """Install the Dream World IX engine bundle (the 3 patched managed DLLs) into BOTH the x64 and x86
    ``FF9_Data/Managed`` dirs, backing up the originals first to ``<game>/dwix-engine-backups/<stamp>/``.
    A bundle that carries native plugins (:func:`bundle_plugin_members`) also installs each into
    ``<arch>/FF9_Data/Plugins``, backed up to ``<stamp>/<arch>/Plugins/``.

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
    plugins = bundle_plugin_members(zip_path)
    backup_root = game / "dwix-engine-backups" / stamp
    report: dict = {"backup_root": backup_root, "backed_up": [], "installed": []}

    def _swap(z, member, dst, bdir):
        if dst.is_file():                              # back up the original before overwriting
            bdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, bdir / dst.name)
            report["backed_up"].append(str(bdir / dst.name))
        with z.open(member) as src:                     # a DLL is a few MB -- fine to hold whole so the
            data = src.read()                           # write-out below can go through the atomic tmp+replace
        fsutil.atomic_write_bytes(dst, data)             # path (a live DLL must never be observed truncated)
        report["installed"].append(str(dst))

    with zipfile.ZipFile(zip_path) as z:
        for mgd in managed_dirs(game):
            if not mgd.is_dir():
                continue
            arch = mgd.parent.parent.name              # "x64" / "x86"
            for dll, member in members.items():
                _swap(z, member, mgd / dll, backup_root / arch)
            plug = mgd.parent / "Plugins"
            for (parch, plugin), member in plugins.items():
                if parch == arch and plug.is_dir():
                    _swap(z, member, plug / plugin, backup_root / arch / "Plugins")
    return report
