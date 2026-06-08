"""Regenerate ``_scenedb.py`` (FF9 battle-scene name -> encounter id) from a Memoria checkout.

A *maintainer* tool, not part of the runtime. Same provenance category as ``_fieldtable.py``: it
transcribes Memoria's OPEN-SOURCE ``FF9BattleDB.SceneData`` name<->id table, NOT extracted game data
(no battle binary, enemy stats, or roster bytes are read or shipped -- only the id<->name labels).

    python -m ff9mapkit._regen_scenedb --memoria "C:/path/to/Memoria"

It reads ``Global/ff9/Battle/FF9BattleDB.SceneData.cs`` -> ``SceneData`` ("BSC_<region>_<n>" <-> id).
A scene id is what a field encounter points at (``SetRandomBattles`` slots); the name encodes the
region (BSC_AC_* = Alexandria Castle, BSC_B3_* = a disc-3 battle, ...). This is a *reference* catalog
for picking/identifying encounter ids by name; enemy rosters/stats are NOT here (they live in p0data).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_PAIR = re.compile(r'\{\s*"(BSC_[^"]+)"\s*,\s*(\d+)\s*\}')


def parse_table(memoria_root: Path) -> dict:
    src = (memoria_root / "Assembly-CSharp" / "Global" / "ff9" / "Battle" / "FF9BattleDB.SceneData.cs"
           ).read_text(encoding="utf-8", errors="replace")
    return {name: int(i) for name, i in _PAIR.findall(src)}


def render(table: dict) -> str:
    header = ('"""Auto-generated FF9 battle-scene registry: scene name -> encounter id.\n\n'
              "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_scenedb --memoria <path>\n"
              "Source: Memoria Assembly-CSharp/Global/ff9/Battle/FF9BattleDB.SceneData.cs (SceneData,\n"
              "open-source) -- the same id<->name table Memoria publishes; NOT extracted game data.\n\n"
              "SCENES['BSC_<region>_<n>'] = encounter_id. A field's encounter points SetRandomBattles at\n"
              "these ids; the name encodes the region. Enemy rosters/stats are NOT here (they're in p0data).\n"
              '"""\n')
    lines = [header, "", "SCENES = {"]
    for name in sorted(table):
        lines.append(f"    {name!r}: {table[name]},")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate _scenedb.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    table = parse_table(Path(args.memoria))
    target = Path(__file__).with_name("_scenedb.py")
    target.write_text(render(table), encoding="utf-8", newline="\n")
    print(f"wrote {target}  ({len(table)} battle scenes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
