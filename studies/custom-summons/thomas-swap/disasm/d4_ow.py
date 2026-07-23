import refkit
pe=refkit.load(); fns=refkit.functions(pe)
def owner(r):
    for f in fns:
        b,e=(f[0],f[1]) if isinstance(f,(tuple,list)) else (f['begin'],f['end'])
        if b<=r<e: return (b,e)
for r in (0x13fbd,0x140d7,0x14279,0x14313,0x1411b,0x13540,0x14350):
    o=owner(r); print(hex(r),"->", [hex(x) for x in o] if o else None)
