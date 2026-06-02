#!/usr/bin/env python3
"""Package the FF9 Map Kit Blender add-on into a distributable .zip.

Re-syncs the vendored scene math (cam/bgi/bgx) from the canonical `ff9mapkit/scene/` so the
add-on is self-contained in Blender (which won't have `ff9mapkit` pip-installed), then zips the
`ff9mapkit_blender/` package. Install the zip in Blender via Preferences > Add-ons > Install
from Disk (or drag-drop as an extension on 4.2+/5.x).

    python build_addon.py            # -> dist/ff9mapkit_blender-<ver>.zip
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent              # .../ff9mapkit/blender
PKG = HERE / "ff9mapkit_blender"
VENDOR = PKG / "vendor"
SCENE = HERE.parent / "ff9mapkit" / "scene"         # .../ff9mapkit/ff9mapkit/scene
VENDORED = ("cam.py", "bgi.py", "bgx.py")
VERSION = "0.1.0"
EXCLUDE_DIRS = {"__pycache__"}


def sync_vendor() -> None:
    """Copy the canonical scene math into vendor/ (keeps the add-on self-contained + in sync)."""
    VENDOR.mkdir(parents=True, exist_ok=True)
    for name in VENDORED:
        shutil.copyfile(SCENE / name, VENDOR / name)
    print(f"synced vendor/: {', '.join(VENDORED)}")


def package(out_dir: Path | None = None) -> Path:
    out_dir = out_dir or (HERE / "dist")
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"ff9mapkit_blender-{VERSION}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(PKG.rglob("*")):
            if any(part in EXCLUDE_DIRS for part in p.parts) or p.is_dir():
                continue
            if p.suffix in (".pyc",):
                continue
            zf.write(p, arcname=str(p.relative_to(PKG.parent)))   # rooted at ff9mapkit_blender/
    return zip_path


if __name__ == "__main__":
    sync_vendor()
    z = package()
    print(f"packaged add-on -> {z}")
