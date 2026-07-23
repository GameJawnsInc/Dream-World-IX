import refkit
pe = refkit.load(); base=refkit.image_base(pe)
print("=== 0x14450..0x14595")
for i in refkit.disasm(pe, 0x14450, 0x14595): print(hex(i.address-base), i.mnemonic, i.op_str)
