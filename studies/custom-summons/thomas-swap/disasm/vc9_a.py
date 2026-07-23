import refkit
pe=refkit.load(); fns=refkit.functions(pe)
f=refkit.func_of(fns,0x315f1)
print("fn range",hex(f[0]),hex(f[1]))
for i in refkit.disasm(pe,f[0],f[1]):
    print(hex(i.address), i.mnemonic, i.op_str)
