import refkit
pe = refkit.load(); base=refkit.image_base(pe)
fns = refkit.functions(pe)
def owner(rva):
    for f in fns:
        b,e = (f[0],f[1]) if isinstance(f,(tuple,list)) else (f['begin'],f['end'])
        if b<=rva<e: return b,e
    return None
for r in (0x30cc9, 0x47449, 0xf906):
    print(hex(r), "->", [hex(x) for x in (owner(r) or [])])
