#!/usr/bin/env python3
"""Package the FF9 Map Kit Blender add-on into a distributable .zip.

Re-syncs the vendored scene math (cam/bgi/bgx) from the canonical `ff9mapkit/scene/` so the
add-on is self-contained in Blender (which won't have `ff9mapkit` pip-installed), then zips the
`ff9mapkit_blender/` package. Install the zip in Blender via Preferences > Add-ons > Install
from Disk (or drag-drop as an extension on 4.2+/5.x).

    python build_addon.py            # -> dist/ff9mapkit_blender-<ver>.zip
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent              # .../ff9mapkit/blender
PKG = HERE / "ff9mapkit_blender"
VENDOR = PKG / "vendor"
KIT = HERE.parent / "ff9mapkit"                     # .../ff9mapkit/ff9mapkit
SCENE = KIT / "scene"
VENDORED = ("cam.py", "bgi.py", "bgx.py", "guide.py", "placeholder.py", "paint.py")   # paint/placeholder = the content paint-template projector + stdlib rasterizer
# extra vendored modules from elsewhere in the kit, as (source_path, vendor_filename) pairs:
VENDORED_EXTRA = ((KIT / "battle" / "fbx.py", "battle_fbx.py"),)   # battle-map FBX emit/parse (pure)
VERSION = "0.9.15"
EXCLUDE_DIRS = {"__pycache__"}


def sync_version() -> None:
    """Force the SINGLE source of truth (VERSION) into BOTH blender_manifest.toml and __init__.py.

    Blender's extension system keys the installed version on the MANIFEST -- if the zip name bumps but
    the manifest doesn't, Blender sees the same version and may keep running the STALE installed code
    (the 0.9.6-stuck bug). Rewriting both here means a build can never ship a version desync again."""
    parts = tuple(int(x) for x in VERSION.split("."))
    man = PKG / "blender_manifest.toml"
    man.write_text(re.sub(r'(?m)^version = ".*"$', f'version = "{VERSION}"',
                          man.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    init = PKG / "__init__.py"
    init.write_text(re.sub(r'"version":\s*\(\d+,\s*\d+,\s*\d+\)',
                           f'"version": ({parts[0]}, {parts[1]}, {parts[2]})',
                           init.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    print(f"synced version -> {VERSION} (blender_manifest.toml + __init__.py)")


def sync_vendor() -> None:
    """Copy the canonical scene + battle math into vendor/ (keeps the add-on self-contained + in sync)."""
    VENDOR.mkdir(parents=True, exist_ok=True)
    for name in VENDORED:
        shutil.copyfile(SCENE / name, VENDOR / name)
    for src, dest in VENDORED_EXTRA:
        shutil.copyfile(src, VENDOR / dest)
    print(f"synced vendor/: {', '.join(VENDORED + tuple(d for _, d in VENDORED_EXTRA))}")


def package(out_dir: Path | None = None) -> Path:
    """Build a Blender 4.2+/5.x EXTENSION zip: blender_manifest.toml + the modules at the zip ROOT.

    Install via Blender: Preferences > Get Extensions > (v top-right) > Install from Disk...
    (or just drag-drop the zip onto the Blender window).
    """
    out_dir = out_dir or (HERE / "dist")
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"ff9mapkit_blender-{VERSION}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(PKG.rglob("*")):
            if any(part in EXCLUDE_DIRS for part in p.parts) or p.is_dir():
                continue
            if p.suffix in (".pyc",):
                continue
            zf.write(p, arcname=str(p.relative_to(PKG)))   # manifest + files at the ROOT (extension layout)
    return zip_path


if __name__ == "__main__":
    sync_version()
    sync_vendor()
    z = package()
    print(f"packaged add-on -> {z}")
