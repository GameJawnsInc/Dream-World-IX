"""V-M1-07 step E: the root fold-in tail 0x7de7..0x80c0."""
import refkit
pe = refkit.load()
for ins in refkit.disasm(pe, 0x7de7, 0x80c0):
    print(f"  {hex(ins.address-0x180000000)}: {ins.mnemonic}\t{ins.op_str}")
