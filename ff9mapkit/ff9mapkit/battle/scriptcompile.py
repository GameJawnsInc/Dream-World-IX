"""Compile the minted battle-formula sources into a mod-owned ``Memoria.Scripts.<Mod>.dll``.

Load-bearing fact (project-ff9-scripts-dll): the Memoria engine loads a prebuilt per-mod scripts DLL
(``Assembly.LoadFile``) IN ADDITION to its base ``Memoria.Scripts.dll`` -- it does **NOT** compile
``Sources/*.cs`` at runtime. So the kit compiles at BUILD/DEPLOY time against the INSTALLED engine's managed
DLLs and drops the result at ``layout.scripts_dll(mod_name)``. The DLL is engine-VERSION-COUPLED, so we always
compile against the LIVE install (never a checked-in ``Assembly-CSharp``); a stale build throws
``MissingMemberException`` at cast, not at load.

Driven NON-interactively via ``csc`` (the shipped ``Memoria.Compiler.exe`` is an interactive menu we don't shell
to). Back-ends probed in order: a VS-BuildTools **Roslyn** ``csc`` (the kit's engine-build toolchain), then the
always-present .NET **Framework** ``csc``. Override with ``$FF9_CSC``. The reference set + flags mirror the
shipped ``Memoria.Compiler`` (``/nostdlib+ /noconfig`` + an explicit Unity ``mscorlib`` -> no double-mscorlib).
Proven producing a loadable DLL in-game 2026-07-07.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


class ScriptCompileError(RuntimeError):
    pass


# The 7 references the shipped Memoria.Compiler passes (Compiler.cs), from the install's FF9_Data/Managed.
_REFERENCES = ("mscorlib.dll", "System.dll", "System.Core.dll", "Assembly-CSharp.dll",
               "Memoria.Prime.dll", "UnityEngine.dll", "XInputDotNetPure.dll")


def _managed_dir(game) -> Path:
    """The install's managed-DLL dir (``<game>/x64|x86/FF9_Data/Managed``) holding Assembly-CSharp.dll etc."""
    from ..config import find_game_path
    root = find_game_path(game)
    for arch in ("x64", "x86"):
        m = root / arch / "FF9_Data" / "Managed"
        if (m / "Assembly-CSharp.dll").exists():
            return m
    raise ScriptCompileError(
        f"could not find the FF9 managed DLLs (looked in {root}\\x64|x86\\FF9_Data\\Managed) -- scripted "
        f"abilities compile against the INSTALLED engine, so a working FF9 install is required to build them")


def find_csc() -> "Path | None":
    """Locate a C# compiler (``csc.exe``). ``$FF9_CSC`` wins; else a VS-BuildTools Roslyn csc, else the .NET
    Framework csc. Returns a Path or None (the caller raises a clear 'no toolchain' error)."""
    env = os.environ.get("FF9_CSC")
    if env and Path(env).exists():
        return Path(env)
    cands: list = []
    for base in (r"C:\Program Files (x86)\Microsoft Visual Studio", r"C:\Program Files\Microsoft Visual Studio"):
        b = Path(base)
        if b.exists():
            cands += sorted(b.glob("*/*/MSBuild/*/Bin/Roslyn/csc.exe"), reverse=True)
    for fw in ("Framework64", "Framework"):
        cands += sorted(Path(rf"C:\Windows\Microsoft.NET\{fw}").glob("v4.0.*/csc.exe"), reverse=True)
    return next((c for c in cands if c.exists()), None)


def toolchain_available() -> bool:
    """True if a C# compiler is findable (for a lint-time gate -- fail early, not mid-build)."""
    return find_csc() is not None


def compile_scripts(layout, mod_name: str, *, game=None) -> None:
    """Compile every ``.cs`` under ``layout.scripts_sources_dir`` -> ``layout.scripts_dll(mod_name)``.
    No sources -> a no-op. Raises :class:`ScriptCompileError` on a missing toolchain / install, or a compile
    failure (carrying the csc diagnostics). The DLL name MUST match the mod FolderNames entry -- ``mod_name``
    is the deploy folder (``ScriptsLoader`` derives ``Memoria.Scripts.<folder>.dll``)."""
    srcs = sorted(layout.scripts_sources_dir.glob("**/*.cs"))
    if not srcs:
        return
    csc = find_csc()
    if csc is None:
        raise ScriptCompileError(
            "scripted abilities (script = {...}) need a C# compiler to build the mod formula DLL, but none was "
            "found. Install Visual Studio Build Tools (Roslyn csc), or set $FF9_CSC to a csc.exe path. The "
            r"always-present .NET Framework csc (C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe) works too.")
    managed = _managed_dir(game)
    out_dll = layout.scripts_dll(mod_name)
    out_dll.parent.mkdir(parents=True, exist_ok=True)
    args = [str(csc), "/target:library", "/nostdlib+", "/noconfig", "/optimize+", f"/out:{out_dll}"]
    args += [f"/reference:{managed / r}" for r in _REFERENCES]
    args += [str(s) for s in srcs]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as ex:
        raise ScriptCompileError(f"failed to run the C# compiler ({csc}): {ex}")
    if proc.returncode != 0 or not out_dll.exists():
        diag = ((proc.stdout or "") + (proc.stderr or "")).strip()
        raise ScriptCompileError(
            f"compiling the mod formula DLL failed (csc exit {proc.returncode}) -- fix the script body / template:\n"
            f"{diag}")
