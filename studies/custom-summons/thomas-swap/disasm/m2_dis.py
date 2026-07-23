"""M2 helper: disassemble a function by RVA with RIP targets resolved to RVAs.

Reads the user's own installed FF9SpecialEffectPlugin.dll via refkit; prints RVAs/mnemonics only.
Usage:  py m2_dis.py <rva-hex> [--arch x64] [--max N] [--raw begin end]
"""
from __future__ import annotations
import argparse
import refkit


def show(pe, b, e, limit=100000, tag=""):
    base = refkit.image_base(pe)
    print(f"--- FUNC {tag} [{hex(b)}..{hex(e)}] size={e-b}")
    for i, ins in enumerate(refkit.disasm(pe, b, e)):
        if i >= limit:
            print("   ... truncated")
            break
        rva = ins.address - base
        t = refkit._rip_target(ins, base)
        extra = f"   ; -> {hex(t)}" if t is not None else ""
        if ins.mnemonic in ("call", "jmp") and ins.op_str.startswith("0x"):
            extra = f"   ; -> {hex(int(ins.op_str, 16) - base)}"
        print(f"  {hex(rva):>8s}: {ins.mnemonic:<7s} {ins.op_str}{extra}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rva", help="hex RVA inside the function")
    ap.add_argument("--arch", default="x64")
    ap.add_argument("--max", type=int, default=100000)
    ap.add_argument("--span", type=int, default=0, help="disassemble N bytes from rva instead of the pdata func")
    a = ap.parse_args()
    pe = refkit.load(a.arch)
    rva = int(a.rva, 16)
    if a.span:
        show(pe, rva, rva + a.span, a.max, tag="(span)")
        return
    fns = refkit.functions(pe)
    f = refkit.func_of(fns, rva)
    if not f:
        print(f"no .pdata function covers {hex(rva)}")
        return
    show(pe, f[0], f[1], a.max, tag=a.rva)


if __name__ == "__main__":
    main()
