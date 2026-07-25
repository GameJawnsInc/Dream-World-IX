"""Regenerate ``_optables.py`` from a local Memoria source checkout.

This is a *maintainer* tool, not part of the runtime. The opcode tables are baked into
``_optables.py`` so the kit needs no Memoria source at runtime. Run this only when updating
to a newer Memoria that changed the opcode tables:

    python -m ff9mapkit.eb._regen_optables --memoria "C:/path/to/Memoria"

It reads ``Assembly-CSharp/Global/Event/Engine/EventEngineUtils.cs`` (opArgCount, opArgSize)
and ``EventEngine.DoEventCode.cs`` (opcode names) and rewrites ``_optables.py`` in place.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# ---- Memoria's custom extended opcodes (the 0xFF page, ops >= 0x112) ----
# The engine dispatches these ad hoc and reads EVERY operand with getv3()
# (3-byte immediates, expression-flagged like any arg) — they never appear in
# the static opArgCount/opArgSize tables this script parses, so they are
# declared here, transcribed from the EventEngine.DoEventCode.cs case bodies
# (verified against base 6b8bb2d5, 2026-07-25). Names = Memoria's own quoted
# names where the case comment carries one.
CUSTOM_EXTENDED = {
    0x112: ("SetCharacterEquipment", [3, 3, 3]),        # char, slot, item
    0x113: ("SetCharacterLevel", [3, 3]),               # char, level
    0x114: ("SetCharacterExp", [3, 3]),                 # char, exp
    0x115: ("AddShopItem", [3, 3, 3]),                  # shopId, item, add?
    0x116: ("AddShopSynthesis", [3, 3, 3]),             # shopId, synthId, add?
    0x117: ("WalkEx", [3, 3, 3, 3, 3, 3]),              # obj, speed, x, y, z, flags
    0x118: ("TurnTowardObjectEx", [3, 3, 3]),           # turner, target, speed
    0x119: ("SetLogicalAnimationEx", [3, 3, 3]),        # obj, kind, anim
    0x11A: ("ClearMemoriaVector", [3]),                 # vector id
    0x11B: ("ClearMemoriaDictionary", [3]),             # dictionary id
    0x11C: ("SetTilePositionTimed", [3, 3, 3, 3, 3]),   # overlay, dx, dy, dz, frames
    0x11D: ("AddBattleStatus", [3, 3, 3, 3, 3, 3]),     # target, status, perm?, a1, a2, a3
    0x11E: ("RemoveBattleStatus", [3, 3, 3]),           # target, status, perm?
}


def parse_tables(memoria_root: Path):
    utils = memoria_root / "Assembly-CSharp" / "Global" / "Event" / "Engine" / "EventEngineUtils.cs"
    doc = memoria_root / "Assembly-CSharp" / "Global" / "Event" / "Engine" / "EventEngine.DoEventCode.cs"
    src = utils.read_text(encoding="utf-8", errors="replace")

    m = re.search(r"opArgCount\s*=\s*new\s+SByte\[\]\s*\{(.*?)\}", src, re.S)
    op_arg_count = [int(x) for x in re.findall(r"-?\d+", m.group(1))]

    m = re.search(r"opArgSize\s*=\s*new\s+Byte\[\]\[\]\s*\{(.*?)\n\s*\};", src, re.S)
    body = (m.group(1).replace("new Byte[]{", "[").replace("new Byte[] {", "[")
            .replace("}", "]").replace("null", "None"))
    op_arg_size = eval("[" + body + "]")  # noqa: S307 - trusted, generated from source we control

    names: dict[int, str] = {}
    for line in doc.read_text(encoding="utf-8", errors="replace").splitlines():
        mm = re.search(r'case EBin\.event_code_binary\.(\w+):\s*//\s*(0x[0-9A-Fa-f]+),\s*"([^"]+)"', line)
        if mm:
            names[int(mm.group(2), 16)] = mm.group(3)
    # the custom extended page (see CUSTOM_EXTENDED): appended past the static
    # tables, which end exactly at 0x111
    assert len(op_arg_count) == 0x112 and len(op_arg_size) == 0x112, \
        f"static tables end at {len(op_arg_count):#x}, expected 0x112 — re-derive CUSTOM_EXTENDED"
    for op in sorted(CUSTOM_EXTENDED):
        nm, sizes = CUSTOM_EXTENDED[op]
        assert op == len(op_arg_count), f"CUSTOM_EXTENDED gap at {op:#x}"
        op_arg_count.append(len(sizes))
        op_arg_size.append(list(sizes))
        names[op] = nm
    # extended-page ops with no parsed name keep their hex placeholder (the
    # historical convention for the BS*/BA* block)
    for k in range(0x100, len(op_arg_count)):
        names.setdefault(k, f"0x{k:X}")
    return op_arg_count, op_arg_size, names


def render(op_arg_count, op_arg_size, names) -> str:
    def fmt_count(lst, perline=20):
        rows = []
        for i in range(0, len(lst), perline):
            rows.append("    " + ", ".join(repr(x) for x in lst[i:i + perline]) + ",")
        return "\n".join(rows)

    header = ('"""Auto-generated FF9 event-script opcode tables (snapshot of Memoria source).\n\n'
              "DO NOT EDIT BY HAND. Regenerate with:  python -m ff9mapkit.eb._regen_optables\n"
              "Source: Memoria  Assembly-CSharp/Global/Event/Engine/EventEngineUtils.cs (opArgCount, opArgSize)\n"
              "        and EventEngine.DoEventCode.cs (opcode names).\n\n"
              "  OP_ARG_COUNT[op]  : number of operands. Negative => variable (count read from the stream).\n"
              "  OP_ARG_SIZE[op]   : per-operand byte width (None where unused / variable).\n"
              "  OP_NAMES[op]      : human-readable mnemonic (cosmetic; missing entries fall back to op_XX).\n"
              '"""\n')
    out = header + "\n"
    out += "OP_ARG_COUNT = [\n" + fmt_count(op_arg_count) + "\n]\n\n"
    out += "OP_ARG_SIZE = [\n" + "\n".join(f"    {x!r}," for x in op_arg_size) + "\n]\n\n"
    out += "OP_NAMES = {\n" + "\n".join(f"    0x{k:02X}: {v!r}," for k, v in sorted(names.items())) + "\n}\n"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate eb/_optables.py from Memoria source.")
    ap.add_argument("--memoria", required=True, help="path to a Memoria source checkout")
    args = ap.parse_args(argv)
    counts, sizes, names = parse_tables(Path(args.memoria))
    text = render(counts, sizes, names)
    target = Path(__file__).with_name("_optables.py")
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {target}  (OP_ARG_COUNT={len(counts)}, OP_ARG_SIZE={len(sizes)}, OP_NAMES={len(names)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
