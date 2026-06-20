"""Regenerate ff9mapkit/ff9mapkit/_narrowmap_data.py from the Memoria source.

The narrow-map screen WIDTHS (Memoria's NarrowMapList.MapWidthList) are open modding data -- the community's
per-field PSX-width measurements, not Square-Enix bytes -- so the kit bakes them in (the same provenance-clean
pattern as the opcode tables in eb/_optables.py), shipping the derived data so fork-report works without the
Memoria clone. Run this when the Memoria source's MapWidthList changes.

    py tools/bake_narrowmap.py [<path to NarrowMapList.cs>]
"""
import os
import re
import sys
from pathlib import Path

# Point FF9_MEMORIA_SRC at the root of your Memoria source clone (the dir holding Assembly-CSharp/),
# or pass the NarrowMapList.cs path as the first argument.
_MEMORIA_SRC = os.environ.get("FF9_MEMORIA_SRC")
DEFAULT_SRC = (Path(_MEMORIA_SRC) / "Assembly-CSharp/Global/Field/Map/NarrowMapList.cs"
               if _MEMORIA_SRC else None)
OUT = Path(__file__).resolve().parent.parent / "ff9mapkit" / "ff9mapkit" / "_narrowmap_data.py"

HEADER = '''"""Field PSX screen-WIDTHS, baked from Memoria NarrowMapList.MapWidthList (provenance-clean: Memoria
open modding data, like the opcode tables -- ships zero Square-Enix bytes). A field whose real width is
narrower than widescreen is letterboxed in-game; a forked custom id defaults to width 500 (widescreen), so it
LOSES that letterbox masking -- the 'narrow-map' lost-on-mint behavior (the engine NarrowMapList is fldMapNo-
keyed; see docs/FORK_FIDELITY.md + project-ff9-narrow-map-fork-letterbox). Regenerate with tools/bake_narrowmap.py.
"""

FORK_DEFAULT_WIDTH = 500   # NarrowMapList.MapWidth() returns this for an unlisted (custom) id
'''


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    if src is None:
        raise SystemExit("usage: py tools/bake_narrowmap.py <path to NarrowMapList.cs>  "
                         "(or set FF9_MEMORIA_SRC to your Memoria clone root)")
    text = src.read_text(encoding="utf-8", errors="replace")
    block = re.search(r"MapWidthList\s*=\s*\{(.*?)\};", text, re.S)
    if not block:
        raise SystemExit(f"MapWidthList not found in {src}")
    pairs = re.findall(r"\[\s*(\d+)\s*,\s*(\d+)\s*\]", block.group(1))
    widths = {int(a): int(b) for a, b in pairs}
    items = ", ".join(f"{k}: {v}" for k, v in sorted(widths.items()))
    OUT.write_text(HEADER + "\nWIDTHS = {" + items + "}\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(widths)} field widths, {min(widths.values())}-{max(widths.values())})")


if __name__ == "__main__":
    main()
