"""V-M1-14 step I: +0x38 readers dereference it; DrawSummonModel's r8 provenance; x86 cross-check."""
import refkit, re
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)
def raw(lo, hi, label, p=pe, b=base):
    print(f"\n=== {label} [{hex(lo)}..{hex(hi)})")
    for ins in refkit.disasm(p, lo, hi):
        print(f"  {hex(ins.address-b)}: {ins.mnemonic}\t{ins.op_str}")

raw(0x185c0, 0x185f0, "Hi_GetSummonBonePos: deref +0x38")
raw(0x18640, 0x18675, "Hi_GetSummonBoneMatrix: deref +0x38")
raw(0x168e0, 0x16935, "DrawEffModelByBone: reads SummonData->bones")
raw(0x17800, 0x17872, "Hi_DrawSummonModel: r8 (arg3) provenance for 0x7820")

# x86 cross-check: DATA+8 read + decode, and the +0x38 analogue (x86 DATA offsets are -4 per pointer)
pe86 = refkit.load('x86'); b86 = refkit.image_base(pe86)
print("\n\n########## x86 build, image_base", hex(b86))
raw(0x13550, 0x13600, "x86 Hi_DrawEffModelByBone", pe86, b86)
