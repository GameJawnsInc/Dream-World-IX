"""Regenerate ``_effectnames.py`` (battle special-effect id -> name) from a Memoria checkout.

A *maintainer* tool, not part of the runtime. The install's own ``SpecialEffectMetaData.txt`` says
WHICH sounds each battle effect loads, but only by number; the names live in Memoria's enum:

    python -m ff9mapkit._regen_effectnames --memoria "C:/path/to/Memoria"

It reads ``Assembly-CSharp/Memoria/Data/Battle/SpecialEffect.cs`` (``Fire__Single = 0, ...``) and
emits ``EFFECT_NAMES = {id: "Fire__Single"}`` -- the enum's own spelling, verbatim, because a
``.seq`` file names effects that way; :func:`ff9mapkit.soundcat.effect_title` is what makes one
readable. Where two names share a value the FIRST is kept; ``Special_No_Effect = -1`` is skipped.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from ._regen_stamp import memoria_stamp

_MEMBER = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?\d+)\s*,", re.M)


def parse_names(memoria_root: Path) -> dict:
    src = (memoria_root / "Assembly-CSharp" / "Memoria" / "Data" / "Battle" / "SpecialEffect.cs"
           ).read_text(encoding="utf-8-sig", errors="replace")
    out: dict = {}
    for m in _MEMBER.finditer(src):
        value = int(m.group(2))
        if value >= 0:
            out.setdefault(value, m.group(1))
    if len(out) < 300:
        raise ValueError(f"only {len(out)} enum members parsed -- the file layout changed?")
    return out


def render(names: dict, *, stamp: str) -> str:
    header = ('"""Auto-generated: battle special-effect id -> its name in Memoria\'s ``SpecialEffect`` enum.\n\n'
              "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit._regen_effectnames\n"
              "Source: Memoria  Assembly-CSharp/Memoria/Data/Battle/SpecialEffect.cs\n\n"
              "  EFFECT_NAMES[effect_id] = 'Fire__Single'   -- the enum's spelling, verbatim (what a .seq\n"
              "  file writes); ff9mapkit.soundcat.effect_title turns one into 'Fire (single)'.\n"
              '"""\n')
    lines = [header + stamp + "\n", "", "EFFECT_NAMES = {"]
    for eid in sorted(names):
        lines.append(f"    {eid}: {names[eid]!r},")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate _effectnames.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    names = parse_names(Path(args.memoria))
    target = Path(__file__).with_name("_effectnames.py")
    target.write_text(render(names, stamp=memoria_stamp(Path(args.memoria), "_regen_effectnames.py")),
                      encoding="utf-8", newline="\n")
    print(f"wrote {target}  ({len(names)} effect names)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
