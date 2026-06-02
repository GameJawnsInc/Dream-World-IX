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
