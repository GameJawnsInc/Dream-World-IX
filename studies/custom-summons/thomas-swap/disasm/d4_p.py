import refkit
pe = refkit.load(); base=refkit.image_base(pe)
fns = refkit.functions(pe)
def owner(rva):
    for f in fns:
        b,e = (f[0],f[1]) if isinstance(f,(tuple,list)) else (f['begin'],f['end'])
        if b<=rva<e: return b,e
o=owner(0x13030); print("owner", [hex(x) for x in o])
for i in refkit.disasm(pe, o[0], o[1]): print(hex(i.address-base), i.mnemonic, i.op_str)
