import refkit
pe = refkit.load(); base=refkit.image_base(pe)
ins=list(refkit.disasm(pe, 0x17740, 0x179f2))
for i in ins:
    a=i.address-base
    if 0x17840 <= a <= 0x178a8: print(hex(a), i.mnemonic, i.op_str)
