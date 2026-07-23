"""M4 helper: disassemble an arbitrary RVA range (or the .pdata function covering an RVA).

Usage:
  py m4_dis.py 0x15ee0 0x16070          # explicit range
  py m4_dis.py --at 0x58f9              # the .pdata function covering that rva, whole body
  py m4_dis.py --at 0x58f9 --grep movzx
Reads the user's own installed DLL; prints RVAs/mnemonics only (no game bytes).
"""
from __future__ import annotations
import argparse
import refkit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("begin", nargs="?")
    ap.add_argument("end", nargs="?")
    ap.add_argument("--at", help="rva; disassemble the .pdata function covering it")
    ap.add_argument("--arch", default="x64")
    ap.add_argument("--grep", default=None)
    ap.add_argument("--max", type=int, default=100000)
    a = ap.parse_args()
    pe = refkit.load(a.arch)
    base = refkit.image_base(pe)
    if a.at:
        fns = refkit.functions(pe)
        f = refkit.func_of(fns, int(a.at, 0))
        if not f:
            print("no .pdata function covers", a.at)
            return
        b, e = f
        print(f"FUNC [{hex(b)}..{hex(e)}] size={e-b}")
    else:
        b, e = int(a.begin, 0), int(a.end, 0)
    n = 0
    for ins in refkit.disasm(pe, b, e):
        line = f"{hex(ins.address - base)}: {ins.mnemonic}\t{ins.op_str}"
        if a.grep and a.grep not in line:
            continue
        print(line)
        n += 1
        if n >= a.max:
            print("...truncated")
            break


if __name__ == "__main__":
    main()
