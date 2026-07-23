"""M1 -- every RIP-relative reference into the EFFARR / summon-array region, grouped by function.

Committable analysis helper; reads the user's own DLL, prints RVAs only.
"""
from __future__ import annotations
import argparse
import refkit

LO, HI = 0x220200, 0x220900


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", default="x64")
    ap.add_argument("--lo", default=hex(LO))
    ap.add_argument("--hi", default=hex(HI))
    a = ap.parse_args()
    pe = refkit.load(a.arch)
    fns = refkit.functions(pe)
    idx = refkit.xref_index(pe, int(a.lo, 16), int(a.hi, 16), fns)
    rows = []
    for tgt, hits in idx.items():
        for frm, mn, ops in hits:
            f = refkit.func_of(fns, frm)
            rows.append((f[0] if f else -1, frm, tgt, mn, ops, f))
    rows.sort()
    cur = None
    for fb, frm, tgt, mn, ops, f in rows:
        if fb != cur:
            cur = fb
            sz = (f[1] - f[0]) if f else 0
            print(f"\n### FUNC {hex(fb)}..{hex(f[1]) if f else '?'} sz={sz}")
        print(f"   {hex(frm)}  {mn} {ops}   ; ->{hex(tgt)}")


if __name__ == "__main__":
    main()
