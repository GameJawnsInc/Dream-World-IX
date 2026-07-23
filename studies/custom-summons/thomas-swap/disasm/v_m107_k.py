"""V-M1-07 step K: rule out the two other [reg+0x38] stores as ModelData writers."""
import refkit
pe = refkit.load()
fns = refkit.functions(pe)
BASE = refkit.image_base(pe)
for center in (0x39EF7, 0x49DEC):
    f = refkit.func_of(fns, center)
    print(f"=== fn {hex(f[0])}..{hex(f[1])} around {hex(center)} ===")
    for ins in refkit.disasm(pe, max(f[0], center - 0x60), min(f[1], center + 0x30)):
        mark = " <<<" if ins.address - BASE == center else ""
        print(f"  {hex(ins.address-BASE)}: {ins.mnemonic}\t{ins.op_str}{mark}")
    print()
