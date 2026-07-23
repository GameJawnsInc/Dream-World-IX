"""M4 scanner: find every site that DECODES a packed resource handle read from a given struct offset.

The plugin's handle->pointer decoder is a fixed inline idiom:
    mov e??, dword ptr [<reg> + <off>]   ; load the packed handle
    ...
    cmp e??, 0x80                        ; band select (within ~12 instructions)
    ...
    and e??, 0x3fffff / 0xfffffff
This locates "who dereferences struct field +off as a resource handle" without guessing.

Usage:  py m4_scan.py 0xc            # every `+0xc` handle decode in the image
        py m4_scan.py 0x14 0x18 0x1c # several offsets at once
Reads the user's own installed DLL; prints RVAs only.
"""
from __future__ import annotations
import re
import sys
import refkit

LOAD = re.compile(r"^dword ptr \[(r[a-z0-9]+) \+ (0x[0-9a-f]+|\d+)\]$")


def main():
    offs = {int(a, 0) for a in sys.argv[1:]} or {0xC}
    pe = refkit.load()
    base = refkit.image_base(pe)
    fns = refkit.functions(pe)
    for b, e in fns:
        try:
            ins = list(refkit.disasm(pe, b, e))
        except Exception:
            continue
        for i, x in enumerate(ins):
            if x.mnemonic != "mov":
                continue
            parts = x.op_str.split(", ", 1)
            if len(parts) != 2:
                continue
            m = LOAD.match(parts[1])
            if not m or int(m.group(2), 16) not in offs:
                continue
            win = ins[i + 1: i + 14]
            if any(y.mnemonic == "cmp" and y.op_str.endswith(", 0x80") for y in win):
                print(f"FUNC[{hex(b)}..{hex(e)}]  {hex(x.address - base)}: "
                      f"{x.mnemonic} {x.op_str}")


if __name__ == "__main__":
    main()
