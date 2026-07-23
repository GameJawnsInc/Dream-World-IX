import refkit
pe = refkit.load(); base=refkit.image_base(pe)
for i in refkit.disasm(pe, 0x47330, 0x474b5): print(hex(i.address-base), i.mnemonic, i.op_str)
