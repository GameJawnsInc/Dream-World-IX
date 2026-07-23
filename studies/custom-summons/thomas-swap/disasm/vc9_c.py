import refkit
pe=refkit.load()
for i in refkit.disasm(pe,0x31a69,0x31ab0):
    print(hex(i.address), i.mnemonic, i.op_str)
