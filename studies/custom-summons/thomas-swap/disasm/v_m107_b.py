"""V-M1-07 step B: the rigid path 0x797a..0x7a31 (translation offsets) + what 0x7a20 is."""
import refkit
pe = refkit.load()
print("--- 0x7960..0x7a31 (rigid path + tail) ---")
for ins in refkit.disasm(pe, 0x7960, 0x7a31):
    print(f"  {hex(ins.address-0x180000000)}: {ins.mnemonic}\t{ins.op_str}")
