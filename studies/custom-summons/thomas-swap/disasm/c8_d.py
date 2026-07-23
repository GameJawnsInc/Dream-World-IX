import refkit
pe=refkit.load()
print("=== 0xe210..0xe240 (pdata head) ===")
for i in refkit.disasm(pe,0xe210,0xe240): print("%05x  %-10s %s"%(i.address,i.mnemonic,i.op_str))
print("=== 0xe240..0xe340 ===")
for i in refkit.disasm(pe,0xe240,0xe340): print("%05x  %-10s %s"%(i.address,i.mnemonic,i.op_str))
