"""Regenerate ff9mapkit/ff9mapkit/_narrowmap_data.py from the Memoria source.

The narrow-map screen WIDTHS (Memoria's NarrowMapList.MapWidthList) and the per-camera restrictions
(NarrowMapList.RestrictedCams) are open modding data -- the community's per-field PSX-width measurements, not
Square-Enix bytes -- so the kit bakes them in (the same provenance-clean pattern as the opcode tables in
eb/_optables.py), shipping the derived data so fork-report works without the Memoria clone. Run this when the
Memoria source's MapWidthList or RestrictedCams changes.

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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ff9mapkit"))
from ff9mapkit._regen_stamp import memoria_stamp                     # noqa: E402

HEADER = '''"""Field PSX screen-WIDTHS, baked from Memoria NarrowMapList (provenance-clean: Memoria open modding data, like
the opcode tables -- ships zero Square-Enix bytes). Regenerate with tools/bake_narrowmap.py.

``WIDTHS`` (``MapWidthList``): a field narrower than widescreen is letterboxed in-game. The table is keyed on
``fldMapNo``, but the custom engine's s23 looks a fork up by its DONOR id (``EffectiveFieldId``, fed by a
ForkDonorPatch row), and s65 does the same for FieldMap's widescreen setup, so a fork that records its donor
gets the donor's exact width. With no donor row, s23 falls back to the loaded BG camera's own width.

``RESTRICTED_CAMS`` (``RestrictedCams``): one camera of a field held narrower than the field itself. It is read on
the RAW ``fldMapNo`` in ``PSXCameraAspect.LateUpdate``, which no patch touches, so a fork on a custom id renders
that camera at the field's width -- lost on a mint. See docs/FORK_FIDELITY.md.
"""
'''
TAIL = '''
# NarrowMapList.MapWidth() for an unlisted id on STOCK Memoria (a novel field). The custom engine returns the donor's
# width for a fork with a ForkDonorPatch row, else the loaded BG camera's width (s23).
FORK_DEFAULT_WIDTH = 500
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
    cams_block = re.search(r"RestrictedCams\s*=\s*\{(.*?)\};", text, re.S)
    if not cams_block:
        raise SystemExit(f"RestrictedCams not found in {src}")
    body = "\n".join(ln.split("//", 1)[0] for ln in cams_block.group(1).splitlines())   # drop commented-out rows
    cams = {}
    for f, cam, w in re.findall(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", body):     # [mapNo, cam, width]
        cams.setdefault(int(f), []).append((int(cam), int(w)))
    items = ", ".join(f"{k}: {v}" for k, v in sorted(widths.items()))
    cam_items = ", ".join(f"{k}: {tuple(v)!r}" for k, v in sorted(cams.items()))
    OUT.write_text(HEADER + memoria_stamp(src.parent, "tools/bake_narrowmap.py") + "\n" + TAIL
                   + "\nWIDTHS = {" + items + "}\n"
                   + "\n# field -> ((camera index, PSX width), ...)\nRESTRICTED_CAMS = {" + cam_items + "}\n",
                   encoding="utf-8")
    print(f"wrote {OUT} ({len(widths)} field widths, {min(widths.values())}-{max(widths.values())}; "
          f"{sum(map(len, cams.values()))} restricted cameras on {len(cams)} fields)")


if __name__ == "__main__":
    main()
