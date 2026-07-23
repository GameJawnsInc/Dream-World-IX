import refkit
pe = refkit.load(); base=refkit.image_base(pe)
for i in refkit.disasm(pe, 0x134d6, 0x13532): print(hex(i.address-base), i.mnemonic, i.op_str)
