import refkit
pe = refkit.load(); base=refkit.image_base(pe)
ins = list(refkit.disasm(pe, 0x13540, 0x13c03))
for i in ins:
    a=i.address-base
    if 0x13930 <= a <= 0x13ae0:
        print(hex(a), i.mnemonic, i.op_str)
