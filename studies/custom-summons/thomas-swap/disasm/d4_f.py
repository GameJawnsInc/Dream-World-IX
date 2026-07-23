import refkit
pe = refkit.load()
for lo,hi,tag in ((0x15ee0,0x16140,'Register'),(0x30c80,0x30d50,'alloc?')):
    print("===",tag)
    for i in refkit.disasm(pe, lo, hi):
        s=i.op_str
        if '+ 0x20]' in s or '+ 0x10]' in s or '+ 0x38]' in s or '+ 0x40]' in s:
            print(hex(i.address-0x180000000), i.mnemonic, s)
