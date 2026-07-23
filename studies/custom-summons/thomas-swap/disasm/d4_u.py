import refkit
pe = refkit.load(); base=refkit.image_base(pe)
fns=refkit.functions(pe)
def owner(rva):
    for f in fns:
        b,e=(f[0],f[1]) if isinstance(f,(tuple,list)) else (f['begin'],f['end'])
        if b<=rva<e: return (b,e)
for r in (0x14450,0x14c30,0x145a0,0x148f0,0x14350):
    print(hex(r), [hex(x) for x in owner(r)])
print("=== 0x14450 head")
for i in refkit.disasm(pe, 0x14450, 0x14560): print(hex(i.address-base), i.mnemonic, i.op_str)
