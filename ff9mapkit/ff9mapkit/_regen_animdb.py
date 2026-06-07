"""Regenerate ``_animdb.py`` (FF9 main-character animation id -> name) from a Memoria checkout.

A *maintainer* tool, not part of the runtime -- the table is baked into ``_animdb.py`` so the kit can
offer an author-facing animation catalog (pick a cutscene gesture by name) with no Memoria source at
runtime. Same provenance category as ``_fieldtable.py``: it's Memoria's OPEN-SOURCE ``AnimationDB``
mapping (Memoria's reverse-engineered labels for FF9's anim resource ids), not extracted game data.

    python -m ff9mapkit._regen_animdb --memoria "C:/path/to/Memoria"

It reads ``Global/ff9/FF9DBAll.Animation.cs`` -> ``AnimationDB`` (id <-> "ANH_..") and keeps only the
8 playable characters' anims (the cutscene presets). Anim names encode model + action:
``ANH_MAIN_F0_VIV_TALK_3_1`` -> model token ``VIV`` (Vivi), form ``F0``, action ``TALK_3_1``. The
engine loads an anim by name->id onto the matching model on demand (AnimationFactory), so any anim
tokened to a character's model plays on that model. To widen coverage (NPC/monster models), add their
tokens to ``MAIN_TOKENS`` below.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# the 8 playable characters' anim-name tokens (ZDN Zidane, VIV Vivi, GRN Garnet/Dagger, STN Steiner,
# FRJ Freya, KUI Quina, EIK Eiko, SLM Amarant "Salamander"). Field cutscene presets draw from these.
MAIN_TOKENS = ("ZDN", "VIV", "GRN", "STN", "FRJ", "KUI", "EIK", "SLM")

_PAIR = re.compile(r'\{\s*(\d+)\s*,\s*"(ANH_[^"]+)"\s*\}')


def parse_table(memoria_root: Path) -> dict:
    src = (memoria_root / "Assembly-CSharp" / "Global" / "ff9" / "FF9DBAll.Animation.cs"
           ).read_text(encoding="utf-8", errors="replace")
    keep = re.compile(r"^ANH_MAIN_F\d_(?:" + "|".join(MAIN_TOKENS) + r")_")
    table = {}
    for i, name in _PAIR.findall(src):
        if keep.match(name):
            table[int(i)] = name
    return table


def render(table: dict) -> str:
    header = ('"""Auto-generated FF9 main-character animation table: anim id -> name.\n\n'
              "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_animdb --memoria <path>\n"
              "Source: Memoria Assembly-CSharp/Global/ff9/FF9DBAll.Animation.cs (AnimationDB, open-source).\n\n"
              "Names encode model + action: ANH_MAIN_F0_VIV_TALK_3_1 -> Vivi ('VIV'), form F0, action\n"
              "TALK_3_1. Limited to the 8 playable characters (the field cutscene presets). The catalog\n"
              "in ff9mapkit.animations turns these into pick-by-name gestures.\n"
              '"""\n')
    lines = [header, "", "MAIN_ANIMATIONS = {"]
    for anim_id in sorted(table, key=lambda i: (table[i], i)):   # by name (groups by character), then id
        lines.append(f'    {anim_id}: {table[anim_id]!r},')
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate _animdb.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    table = parse_table(Path(args.memoria))
    target = Path(__file__).with_name("_animdb.py")
    target.write_text(render(table), encoding="utf-8", newline="\n")
    per = {}
    for name in table.values():
        per[name.split("_")[3]] = per.get(name.split("_")[3], 0) + 1
    print(f"wrote {target}  ({len(table)} anims: " + ", ".join(f"{t}={per.get(t, 0)}" for t in MAIN_TOKENS) + ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
