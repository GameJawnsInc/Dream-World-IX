import refkit
pe = refkit.load(); base=refkit.image_base(pe)
fns = refkit.functions(pe)
def owner(rva):
    for f in fns:
        b,e = (f[0],f[1]) if isinstance(f,(tuple,list)) else (f['begin'],f['end'])
        if b<=rva<e: return b,e
print("owner 0x12df0", [hex(x) for x in owner(0x12df0)])
o=owner(0x12df0)
for i in refkit.disasm(pe, o[0], min(o[1], o[0]+0x300)): print(hex(i.address-base), i.mnemonic, i.op_str)
