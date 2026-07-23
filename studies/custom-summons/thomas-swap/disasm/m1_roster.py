"""M1 helper -- locate the Eff-model family real bodies + dump their disassembly.

Committable: pure analysis over the user's own installed DLL. Emits RVAs/mnemonics only.
"""
from __future__ import annotations
import argparse
import sys

import refkit

NAMES = [
    "Hi_FreeEffModel", "Hi_RegisterSolidEffModel", "Hi_RegisterGouEffModel",
    "Hi_RegisterTexEffModel", "Hi_RegisterTexListModel", "Hi_RegisterTexPtrModel",
    "Hi_RegisterSummonModel",
    "Hi_DrawEffModel", "Hi_DrawSliceEffModel", "Hi_DrawEffModelByBone",
    "Hi_DrawMorphEffModel", "Hi_DrawMorphModelByBone", "Hi_DrawSummonModel",
    "Hi_SplitMdlVertex", "Hi_GetSplitMdlVertex", "Hi_GetMdlVertexPtr",
    "Hi_ModifyEffModelAbr", "Hi_ModifyEffModelRGB",
    "Hi_SetEffModelOffset", "Hi_SetEffModelSlice",
]


def roster(arch="x64"):
    pe = refkit.load(arch)
    fns = refkit.functions(pe)
    smap = refkit.string_rvas(pe)
    targets = {}
    for rva, txt in smap.items():
        for n in NAMES:
            if txt.startswith(n):
                targets.setdefault(rva, []).append(n)
    lo, hi = min(targets), max(targets) + 1
    idx = refkit.xref_index(pe, lo, hi, fns)
    print(f"arch={arch} funcs={len(fns)}")
    for rva in sorted(targets):
        names = "/".join(targets[rva])
        hits = idx.get(rva, [])
        print(f"\n== {names}  str@{hex(rva)}  xrefs={len(hits)}")
        for frm, mn, ops in hits:
            f = refkit.func_of(fns, frm)
            fs = f"FUNC[{hex(f[0])}..{hex(f[1])}] sz={f[1]-f[0]}" if f else "no-pdata-func"
            print(f"    from {hex(frm)}  {mn} {ops}   {fs}")


def dis(arch, begin, end, maxi=100000, pe=None):
    pe = pe or refkit.load(arch)
    base = refkit.image_base(pe)
    smap = None
    for i, ins in enumerate(refkit.disasm(pe, begin, end)):
        if i >= maxi:
            print("...")
            break
        note = ""
        t = refkit._rip_target(ins, base)
        if t is not None:
            note = f"   ; ->RVA {hex(t)}"
            if smap is None:
                smap = refkit.string_rvas(pe)
            if t in smap:
                note += f"  {smap[t]!r}"
        print(f"{hex(ins.address - base):>8s}: {ins.mnemonic}\t{ins.op_str}{note}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", default="x64")
    ap.add_argument("--dis", help="BEGIN:END hex rvas")
    ap.add_argument("--fn", help="hex rva -- disassemble the whole .pdata function containing it")
    ap.add_argument("--max", type=int, default=100000)
    a = ap.parse_args()
    if a.dis:
        b, e = [int(x, 16) for x in a.dis.split(":")]
        dis(a.arch, b, e, a.max)
        return
    if a.fn:
        pe = refkit.load(a.arch)
        fns = refkit.functions(pe)
        f = refkit.func_of(fns, int(a.fn, 16))
        if not f:
            print("no function"); return
        print(f"FUNC[{hex(f[0])}..{hex(f[1])}] sz={f[1]-f[0]}")
        dis(a.arch, f[0], f[1], a.max)
        return
    roster(a.arch)


if __name__ == "__main__":
    main()
