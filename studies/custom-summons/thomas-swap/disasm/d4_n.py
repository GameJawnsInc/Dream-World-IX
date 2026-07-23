import refkit
pe = refkit.load(); base=refkit.image_base(pe)
fns = refkit.functions(pe)
def owner(rva):
    for f in fns:
        b,e = (f[0],f[1]) if isinstance(f,(tuple,list)) else (f['begin'],f['end'])
        if b<=rva<e: return b,e
print("owner 0x3bbd0", [hex(x) for x in owner(0x3bbd0)])
for i in refkit.disasm(pe, 0x3bbd0, 0x3bd00): print(hex(i.address-base), i.mnemonic, i.op_str)
