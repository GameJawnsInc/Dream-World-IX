"""V-M1-14 step D: 0x12940 tail (does it EMIT a PSX address?) + both Draw decode sites."""
import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)
def raw(lo, hi, label):
    print(f"\n=== {label} [{hex(lo)}..{hex(hi)})")
    for ins in refkit.disasm(pe, lo, hi):
        print(f"  {hex(ins.address-base)}: {ins.mnemonic}\t{ins.op_str}")
raw(0x129cc, 0x12af7, "0x12940 TAIL (encoder output)")
raw(0x16240, 0x162e0, "Hi_DrawEffModel: [DATA+8] decode + meshCount")
raw(0x17880, 0x17930, "Hi_DrawSummonModel: [DATA+8] decode + meshCount")
