"""V-M1-07 step H: DrawSummonModel entry chunk -- summon record base/stride/active/data offsets."""
import refkit
pe = refkit.load()
fns = refkit.functions(pe)
print("pdata funcs 0x17600..0x17800:")
for b, e in fns:
    if 0x17600 <= b < 0x17800:
        print("   ", hex(b), hex(e), e-b)
print()
for b, e in fns:
    if 0x17600 <= b < 0x17745:
        print(f"--- {hex(b)}..{hex(e)} ---")
        for ins in refkit.disasm(pe, b, e):
            print(f"  {hex(ins.address-0x180000000)}: {ins.mnemonic}\t{ins.op_str}")
