"""V-M1-07 step F: 0x80aa..0x83c7 -- the bone-hierarchy propagation loop (is bone0 parentless root?)."""
import refkit
pe = refkit.load()
for ins in refkit.disasm(pe, 0x80aa, 0x83c7):
    print(f"  {hex(ins.address-0x180000000)}: {ins.mnemonic}\t{ins.op_str}")
