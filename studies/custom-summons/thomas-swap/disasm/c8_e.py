import refkit
pe=refkit.load()
print("=== 0xd1a0..0xd2b0 ===")
for i in refkit.disasm(pe,0xd1a0,0xd2c0): print("%05x  %-10s %s"%(i.address,i.mnemonic,i.op_str))
