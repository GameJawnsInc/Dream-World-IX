import refkit
pe=refkit.load()
# import names for the two calls in 0xd1a0
for name,rip_ins,disp in (("free?",0xd1d2,0x3cf40),("malloc?",0xd1f9,0x3cf21)):
    pass
imp={}
for e in pe.DIRECTORY_ENTRY_IMPORT:
    for i in e.imports:
        if i.address: imp[i.address-pe.OPTIONAL_HEADER.ImageBase]=(e.dll.decode(), i.name and i.name.decode())
print("call@d1d2 ->", imp.get(0xd1d8+0x3cf40))
print("call@d1f9 ->", imp.get(0xd1ff+0x3cf21))
print()
print("=== 0xd5d0..0xd736 (search memset/rep stos) ===")
for i in refkit.disasm(pe,0xd680,0xd6e0): print("%05x  %-10s %s"%(i.address,i.mnemonic,i.op_str))
