"""V-M1-14 step F: eff Draw decode of [DATA+8]; the other +0x38 writer @0x71f7; the Draw arg3 source."""
import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)
def raw(lo, hi, label):
    print(f"\n=== {label} [{hex(lo)}..{hex(hi)})")
    for ins in refkit.disasm(pe, lo, hi):
        print(f"  {hex(ins.address-base)}: {ins.mnemonic}\t{ins.op_str}")

raw(0x16184, 0x162e0, "Hi_DrawEffModel body head")
print("\n0x71f7 in chunk:", [(hex(b),hex(e)) for b,e in fns if b<=0x71f7<e])
raw(0x71c0, 0x7210, "the OTHER +0x38 writer")
raw(0x17840, 0x17880, "Hi_DrawSummonModel: arg3 to 0x7820")
