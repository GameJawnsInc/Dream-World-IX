"""Regenerate ``_animdb_all.py`` (the FULL FF9 animation id -> name table) from a Memoria checkout.

A *maintainer* tool, not part of the runtime. Same provenance category as ``_animdb.py`` -- it
transcribes Memoria's OPEN-SOURCE ``AnimationDB`` (id<->"ANH_.." labels), NOT extracted game data; no
animation binary is read or shipped.

    python -m ff9mapkit._regen_animdb_all --memoria "C:/path/to/Memoria"

This is the COMPREHENSIVE table (every ``ANH_*`` animation, all model groups), used by
:mod:`ff9mapkit.catalog` to list any model's gestures via the (group, token) join. It is a superset of
``_animdb.py`` (which keeps only the 8 playable characters for the cutscene author-convenience and is
what the *build* path imports). They are regenerated independently on purpose so the build's animation
resolution is untouched by Info-Hub changes; a future cleanup could derive ``_animdb.py`` from this.

An anim name encodes model + action: ``ANH_<group>_<form>_<token>_<action>`` -- e.g.
``ANH_MAIN_F0_VIV_TALK_3_1`` (Vivi, field form, action TALK_3_1) or ``ANH_NPC_F0_BAR_*``.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_PAIR = re.compile(r'\{\s*(\d+)\s*,\s*"(ANH_[^"]+)"\s*\}')


def parse_table(memoria_root: Path) -> dict:
    src = (memoria_root / "Assembly-CSharp" / "Global" / "ff9" / "FF9DBAll.Animation.cs"
           ).read_text(encoding="utf-8", errors="replace")
    return {int(i): name for i, name in _PAIR.findall(src)}


def render(table: dict) -> str:
    header = ('"""Auto-generated FULL FF9 animation table: anim id -> name (all model groups).\n\n'
              "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_animdb_all --memoria <path>\n"
              "Source: Memoria Assembly-CSharp/Global/ff9/FF9DBAll.Animation.cs (AnimationDB, open-source) --\n"
              "the same id<->name table Memoria publishes; NOT extracted game data (see docs/PROVENANCE.md).\n\n"
              "ANIMATIONS[id] = 'ANH_<group>_<form>_<token>_<action>'. Superset of _animdb.py (which is the\n"
              "8-playable subset used by the build's cutscene path). ff9mapkit.catalog joins these to a\n"
              "model by (group, token) -> the model's gesture list.\n"
              '"""\n')
    lines = [header, "", "ANIMATIONS = {"]
    for anim_id in sorted(table, key=lambda i: (table[i], i)):   # by name (groups by model), then id
        lines.append(f"    {anim_id}: {table[anim_id]!r},")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate _animdb_all.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    table = parse_table(Path(args.memoria))
    target = Path(__file__).with_name("_animdb_all.py")
    target.write_text(render(table), encoding="utf-8", newline="\n")
    groups = {}
    for name in table.values():
        groups[name.split("_")[1]] = groups.get(name.split("_")[1], 0) + 1
    print(f"wrote {target}  ({len(table)} anims: "
          + ", ".join(f"{g}={n}" for g, n in sorted(groups.items())) + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
