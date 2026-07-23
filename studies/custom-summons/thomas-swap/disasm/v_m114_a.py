"""V-M1-14 step A: fresh disassembly around the cited RVAs. Independent re-derivation."""
import sys, refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)
print("image_base", hex(base), "pdata fns", len(fns))

def show(lo, hi, label):
    f = refkit.func_of(fns, lo)
    print(f"\n=== {label}  window [{hex(lo)}..{hex(hi)})  containing FUNC={f and (hex(f[0]),hex(f[1]))}")
    if not f:
        print("  !! no .pdata function covers this rva -- leaf/no-unwind")
        return
    for ins in refkit.disasm(pe, f[0], f[1]):
        r = ins.address - base
        if lo <= r < hi:
            print(f"  {hex(r)}: {ins.mnemonic}\t{ins.op_str}")

# cited: Register eff writes [DATA+8] at 0x15b11 after call 0x12940
show(0x15ae0, 0x15b40, "Hi_RegisterSolidEffModel tail (DATA+8 write)")
# cited: summon register 0x15f3f
show(0x15f00, 0x15f70, "Hi_RegisterSummonModel (DATA+8 write @0x15f3f)")
