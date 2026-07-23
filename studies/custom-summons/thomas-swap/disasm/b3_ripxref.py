import sys, refkit
pe = refkit.load()
fns = refkit.functions(pe)
def owner(rva):
    for (b,e) in fns:
        if b<=rva<e: return (b,e)
    return None
for a in sys.argv[1:]:
    t=int(a,16)
    refs = refkit.xrefs_to(pe, t)
    print(f"\n== xrefs_to 0x{t:x} : {len(refs)} ==")
    for frm,mnem,op in refs[:60]:
        o=owner(frm)
        os=f"FUNC[0x{o[0]:x}]" if o else "?"
        print(f"  0x{frm:x} {os}: {mnem} {op}")
