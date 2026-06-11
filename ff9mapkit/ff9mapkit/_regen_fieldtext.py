"""Regenerate ``_fieldtext.py`` (field map-id -> text-block / MES id) from a Memoria checkout.

A maintainer tool, not part of the runtime -- the table is baked into ``_fieldtext.py`` so the kit
needs no Memoria source to find which ``<mes-id>.mes`` holds a real field's dialogue. The engine names a
field's text file by this id (``FF9TextTool.GetFieldTextFileName`` == the id as a string), and looks it up
exactly here -- ``EventEngineUtils.eventIDToMESID[fldMapNo]`` (used in FF9UIDataTool). Run it only when
updating to a newer Memoria whose registry changed:

    python -m ff9mapkit._regen_fieldtext --memoria "C:/path/to/Memoria"
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_PAIR = re.compile(r"\{\s*(\d+)\s*,\s*(\d+)\s*\}")


def _dict_block(src: str, name: str) -> str:
    """The body of a ``name = new Dictionary<Int32, Int32> { ... };`` literal (up to the first ``};``)."""
    m = re.search(re.escape(name) + r"\s*=\s*new\s+Dictionary<Int32,\s*Int32>\s*\(\s*\)\s*\{(.*?)\n\s*\};",
                  src, re.S)
    if not m:
        m = re.search(re.escape(name) + r"\s*=\s*new\s+Dictionary<Int32,\s*Int32>\s*\{(.*?)\n\s*\};", src, re.S)
    if not m:
        raise ValueError(f"could not find dictionary {name!r}")
    return m.group(1)


def parse_table(memoria_root: Path) -> dict:
    eng = (memoria_root / "Assembly-CSharp" / "Global" / "Event" / "Engine" / "EventEngineUtils.cs"
           ).read_text(encoding="utf-8", errors="replace")
    return {int(k): int(v) for k, v in _PAIR.findall(_dict_block(eng, "eventIDToMESID"))}


def render(table: dict) -> str:
    header = ('"""Auto-generated FF9 field text registry: field map-id -> text-block (MES) id.\n\n'
              "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_fieldtext\n"
              "Source:  Memoria  Assembly-CSharp/Global/Event/Engine/EventEngineUtils.cs  (eventIDToMESID)\n\n"
              "A field's dialogue lives in ``<mes-id>.mes`` (the engine names it by this id -- see\n"
              "FF9TextTool.GetFieldTextFileName / EventEngineUtils.eventIDToMESID). EVENT_ID_TO_MES[field_id]\n"
              "is how `dialogue-import` reads the RIGHT text block for a real field (txids are 0-based\n"
              "positions shared by every field, so the block can't be found by txid alone).\n"
              '"""\n')
    lines = [header, "", "EVENT_ID_TO_MES = {"]
    for fid in sorted(table):
        lines.append(f"    {fid}: {table[fid]},")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate _fieldtext.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    table = parse_table(Path(args.memoria))
    target = Path(__file__).with_name("_fieldtext.py")
    target.write_text(render(table), encoding="utf-8", newline="\n")
    print(f"wrote {target}  (eventIDToMESID entries={len(table)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
