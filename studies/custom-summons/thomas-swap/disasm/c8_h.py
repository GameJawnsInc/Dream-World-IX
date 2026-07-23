import refkit
pe=refkit.load()
for i in refkit.disasm(pe,0xd390,0xd4e0): print("%05x  %-10s %s"%(i.address,i.mnemonic,i.op_str))
