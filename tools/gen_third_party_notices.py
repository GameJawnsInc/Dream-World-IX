#!/usr/bin/env python3
"""Generate a THIRD-PARTY-NOTICES.txt aggregating the license text of every dependency
ff9mapkit pulls in, so a redistributed installer / portable build is license-compliant.

Almost the whole dependency stack is permissive (MIT / BSD / HPND / PSF / Apache) -- compliance is
"reproduce the license + copyright notice." This script automates that by reading the license files
the wheels already ship in their ``*.dist-info`` (via ``pip-licenses``), then appends the handful of
items that automated scrapers MISS (they read package METADATA, which is blind to bundled binaries):

  * PySide6 / Qt6 -- LGPLv3 (the only copyleft dep): needs a WRITTEN OFFER for Qt's source + the user
    must be able to relink/replace the Qt DLLs. Only relevant if you BUNDLE Qt (a freeze/portable
    build); the recommended uv-bootstrap installer redistributes nothing, so this never attaches.
  * Pillow -- its wheels statically bundle native libs (libjpeg-turbo, zlib, ...) whose notices live
    in the wheel's dist-info but are easy to drop.
  * fmod_toolkit (pulled transitively by UnityPy) -- an MIT wrapper that BUNDLES proprietary FMOD
    Engine binaries (Firelight EULA: non-commercial only + a mandatory credit line). Metadata says
    "MIT", so scrapers miss it. EXCLUDE the FMOD libs from any frozen build (the kit never extracts
    audio), or bundle the EULA + credit line.

Run it against the SHIPPED environment (the one whose binaries you actually distribute):

    py -m pip install pip-licenses
    py -m pip install -e ".[gui,save,assets]"        # from the ff9mapkit/ package dir
    py tools/gen_third_party_notices.py -o THIRD-PARTY-NOTICES.txt

(In the uv-bootstrap model you redistribute nothing, so this file is a courtesy aggregate. In a
freeze/portable build it is a compliance REQUIREMENT -- generate it on the same OS/Python you ship.)
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Packages that are the project itself or pure build/dev tooling -- not redistributed deps.
IGNORE = [
    "ff9mapkit",
    "pip",
    "setuptools",
    "wheel",
    "pip-licenses",
    "prettytable",
    "wcwidth",
    "tomli",  # build-time only
]

HEADER = """\
================================================================================
 THIRD-PARTY NOTICES -- Dream World IX / ff9mapkit
================================================================================

This product bundles unmodified copies of the third-party software listed below.
Each component is distributed under its own license; the full texts follow.

  Python ......... PSF License (Python Software Foundation)
  Pillow ......... MIT-CMU (HPND-class) + bundled native libs (libjpeg-turbo, zlib, ...)
  UnityPy ........ MIT (+ permissive native deps: lz4, brotli, etcpak, astc-encoder/Apache-2.0, ...)
  pycryptodome ... BSD-2-Clause + Public Domain
  PySide6/Qt ..... LGPLv3 (the only copyleft component) -- see the appendix below

Python copyright (c) 2001 Python Software Foundation; All Rights Reserved.

Dream World IX / ff9mapkit itself is licensed under the MIT License (see LICENSE).
It grants no rights to FINAL FANTASY IX game data, which belongs to Square Enix.
================================================================================

"""

APPENDIX = """\

================================================================================
 APPENDIX -- obligations automated scrapers do NOT capture (manual review)
================================================================================

These items are NOT visible from package metadata. Confirm them whenever you
REDISTRIBUTE the dependency binaries (a frozen .exe or a portable zip). The
recommended uv-bootstrap installer redistributes nothing -- the user's own
pip/uv fetches every dependency from PyPI -- so none of these attach to it.

1. PySide6 / Qt6 (LGPLv3) -- the only copyleft dependency.
   If you bundle Qt, the LGPLv3 requires that you:
     (a) keep the Qt shared libraries dynamically linked and USER-REPLACEABLE
         (=> use PyInstaller --onedir, never --onefile);
     (b) ship the LGPLv3 license text and a clear notice that the app uses Qt
         under the LGPL;
     (c) provide the corresponding Qt source, or a WRITTEN OFFER / link to it,
         e.g.:  "The Qt source corresponding to the PySide6/Qt libraries bundled
         with this product is available at https://download.qt.io/ ."
   Pin the GUI extra to PySide6-Essentials (done) so no GPL-only Qt module
   (QtCharts/QtDataVisualization/QtGraphs, which live in PySide6-Addons) ever
   ships and forces the whole app to GPL.

2. Pillow bundled native libraries.
   Pillow wheels statically bundle libjpeg-turbo, zlib (and possibly libtiff,
   libwebp, freetype, lcms2, openjpeg). Their notices live in the wheel at
   Pillow-<ver>.dist-info/licenses/ -- copy that whole folder. All are
   permissive (BSD/zlib/IJG-style); no source offer required.

3. fmod_toolkit -> proprietary FMOD Engine binaries (pulled transitively by UnityPy).
   The MIT wrapper bundles FMOD Engine binaries under Firelight Technologies'
   EULA: the free tier is NON-COMMERCIAL only and requires a credit line
   ("FMOD Studio, (c) Firelight Technologies Pty Ltd"). Package metadata reports
   only "MIT", so the aggregate above MISSES this. For a frozen/portable build
   EITHER exclude the FMOD native libs (UnityPy needs them only for audio
   extraction, which ff9mapkit never invokes) OR bundle the FMOD EULA and add
   the credit line. EXCLUDING is recommended and matches the "ship zero game
   bytes" ethos.
================================================================================
"""


def _piplicenses_cmd() -> list[str]:
    """The pip-licenses invocation for the CURRENT interpreter, or exit with guidance."""
    if shutil.which("pip-licenses"):
        return ["pip-licenses"]
    # Fall back to the module form so we always target THIS interpreter's environment.
    try:
        import piplicenses  # noqa: F401
    except ImportError:
        sys.exit(
            "pip-licenses is not installed in this interpreter.\n"
            f"  {Path(sys.executable).name} -m pip install pip-licenses\n"
            "Then re-run this script with the SAME interpreter that has the deps installed."
        )
    return [sys.executable, "-m", "piplicenses"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Aggregate third-party license notices for a redistributable build.")
    ap.add_argument("-o", "--output", default="THIRD-PARTY-NOTICES.txt", help="output file (default: %(default)s)")
    ap.add_argument(
        "--no-appendix",
        action="store_true",
        help="omit the manual-review appendix (Qt LGPL offer / Pillow libs / FMOD) -- not recommended",
    )
    args = ap.parse_args(argv)

    cmd = _piplicenses_cmd() + [
        "--with-license-file",
        "--with-notice-file",
        "--with-urls",
        "--with-authors",
        "--format=plain-vertical",
        "--ignore-packages",
        *IGNORE,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return proc.returncode

    out = Path(args.output)
    parts = [HEADER, proc.stdout]
    if not args.no_appendix:
        parts.append(APPENDIX)
    out.write_text("".join(parts), encoding="utf-8")

    n = proc.stdout.count("\nName: ") + (1 if proc.stdout.startswith("Name: ") else 0)
    print(
        f"Wrote {out} ({out.stat().st_size:,} bytes, ~{n} packages) "
        f"on {platform.system()} / Python {platform.python_version()}."
    )
    if not args.no_appendix:
        print("Appendix included: PySide6 LGPL offer, Pillow native libs, fmod_toolkit/FMOD review item.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
