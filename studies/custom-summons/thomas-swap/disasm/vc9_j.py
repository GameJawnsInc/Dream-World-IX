import refkit
pe=refkit.load()
for rva in (0x39d60,0x3b3e0,0x3bb80,0x39d90,0x3b410):
    print("--- %06x"%rva)
    for k,i in enumerate(refkit.disasm(pe,rva,rva+0x28)):
        print("   ",hex(i.address),i.mnemonic,i.op_str)
        if k>6: break
    # what precedes?
    prev=refkit.read_rva(pe,rva-8,8)
    print("    preceding 8 bytes:",prev.hex())
