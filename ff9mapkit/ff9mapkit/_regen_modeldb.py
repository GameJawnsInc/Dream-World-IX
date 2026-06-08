"""Regenerate ``_modeldb.py`` (FF9 actor/field model id -> GEO name) from a Memoria checkout.

A *maintainer* tool, not part of the runtime. Same provenance category as ``_fieldtable.py`` /
``_animdb.py``: it transcribes Memoria's OPEN-SOURCE ``FF9BattleDB.GEO`` id<->name table (Memoria's
reverse-engineered labels for FF9's model resource ids), NOT extracted game data -- no model geometry
is ever read or shipped.

    python -m ff9mapkit._regen_modeldb --memoria "C:/path/to/Memoria"

It reads ``Global/ff9/Battle/FF9BattleDB.GEO.cs`` -> ``GEO`` (model id <-> "GEO_<grp>_<form>_<token>").
A model name encodes group + form + token:
  * ``GEO_MAIN_F0_VIV`` -> group MAIN (playable), form F0 (field), token VIV (Vivi)
  * ``GEO_NPC_F0_BAR``  -> an NPC field model;  ``GEO_MON_F0_*`` a monster;  ``GEO_ACC_F0_*`` a prop
The token ties a model to its animations: an anim ``ANH_<grp>_<form>_<token>_<action>`` plays on the
model sharing (group, token). That join is what :mod:`ff9mapkit.catalog` uses for "this model's
gestures" (verified: model id 8 = ``GEO_MAIN_F0_VIV``, whose (MAIN, VIV) anims are 148/571/419/...).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_PAIR = re.compile(r'\{\s*(\d+)\s*,\s*"(GEO_[^"]+)"\s*\}')


def parse_table(memoria_root: Path) -> dict:
    src = (memoria_root / "Assembly-CSharp" / "Global" / "ff9" / "Battle" / "FF9BattleDB.GEO.cs"
           ).read_text(encoding="utf-8", errors="replace")
    return {int(i): name for i, name in _PAIR.findall(src)}


def render(table: dict) -> str:
    header = ('"""Auto-generated FF9 model registry: actor/field model id -> GEO resource name.\n\n'
              "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_modeldb --memoria <path>\n"
              "Source: Memoria Assembly-CSharp/Global/ff9/Battle/FF9BattleDB.GEO.cs (GEO, open-source) --\n"
              "the same id<->name table Memoria publishes; NOT extracted game data (see docs/PROVENANCE.md).\n\n"
              "MODELS[id] = 'GEO_<group>_<form>_<token>'. group: MAIN playable / NPC townsfolk / MON\n"
              "monster / ACC prop / SUB sub-character / WEP weapon. form: F* field, B* battle, W* world.\n"
              "The token links a model to its animations (ANH_<group>_*_<token>_<action>); see\n"
              "ff9mapkit.catalog.animations_for_model. The model id is the value SetModel() takes.\n"
              '"""\n')
    lines = [header, "", "MODELS = {"]
    for mid in sorted(table, key=lambda i: (table[i], i)):   # by name (groups by category), then id
        lines.append(f"    {mid}: {table[mid]!r},")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate _modeldb.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    table = parse_table(Path(args.memoria))
    target = Path(__file__).with_name("_modeldb.py")
    target.write_text(render(table), encoding="utf-8", newline="\n")
    groups = {}
    for name in table.values():
        groups[name.split("_")[1]] = groups.get(name.split("_")[1], 0) + 1
    print(f"wrote {target}  ({len(table)} models: "
          + ", ".join(f"{g}={n}" for g, n in sorted(groups.items())) + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
