"""V-M1-07 step D: motion path 0x7a20..0x7de7 -- root translation stores + bone loop."""
import refkit
pe = refkit.load()
for ins in refkit.disasm(pe, 0x7a20, 0x7de7):
    r = ins.address - 0x180000000
    print(f"  {hex(r)}: {ins.mnemonic}\t{ins.op_str}")
