"""V-M1-02 step C: (1) every function that RIP-references the EFFARR band [0x220230,0x220830)
   -- i.e. every place an EffData* can be obtained; (2) confirm the two non-zero writers of
   DATA+0x10 (0x15f35, 0x17a10) index the SUMMON array (base 0x220830, stride 0x58), not EFFARR.
"""
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)

EFF_LO, EFF_HI = 0x220230, 0x220830
idx = refkit.xref_index(pe, EFF_LO, EFF_HI + 0x60, fns)
byfn = {}
for tgt, lst in idx.items():
    for rva, mn, ops in lst:
        f = refkit.func_of(fns, rva)
        byfn.setdefault(f[0] if f else 0, []).append((rva, tgt, mn, ops))
print("functions referencing 0x220230..0x220890:")
for fb in sorted(byfn):
    tags = sorted({t for _, t, _, _ in byfn[fb]})
    print("  fn %06x  ->  %s" % (fb, ", ".join(hex(t) for t in tags)))

print()
for name, (b, e) in [("summon-register-work@15f35", (0x15f35, 0x16090)),
                     ("Hi_SetSummonMotion@17a10", (0x17a10, 0x17a70))]:
    print("=" * 70)
    print(name)
    for i in refkit.disasm(pe, b, e):
        t = refkit._rip_target(i, base)
        extra = "   ; -> %s" % hex(t) if t is not None else ""
        print(" %06x  %-9s %s%s" % (i.address - base, i.mnemonic, i.op_str, extra))
