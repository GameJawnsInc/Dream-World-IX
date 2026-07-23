"""V-M1-14 step J: DrawSummonModel from its chunk start; x86 Register + Draw use of the geom field."""
import refkit
pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)
print("=== Hi_DrawSummonModel 0x17740..0x17880 (from chunk start, no desync)")
for ins in refkit.disasm(pe, 0x17740, 0x17880):
    print(f"  {hex(ins.address-base)}: {ins.mnemonic}\t{ins.op_str}")

pe86 = refkit.load('x86'); b86 = refkit.image_base(pe86)
print("\n=== x86 Hi_RegisterSolidEffModel 0x12d80..0x12e00")
for ins in refkit.disasm(pe86, 0x12d80, 0x12e00):
    print(f"  {hex(ins.address-b86)}: {ins.mnemonic}\t{ins.op_str}")
print("\n=== x86 decode helper 0x10d0 head")
for ins in refkit.disasm(pe86, 0x10d0, 0x1130):
    print(f"  {hex(ins.address-b86)}: {ins.mnemonic}\t{ins.op_str}")
