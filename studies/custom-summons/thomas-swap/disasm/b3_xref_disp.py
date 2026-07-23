import sys, refkit
pe = refkit.load()
IB = 0x180000000
fns = refkit.functions(pe)
def owner(rva):
    for (b,e) in fns:
        if b<=rva<e: return (b,e)
    return None
# find instructions that reference a given absolute RVA via [reg + imagebase-reg + disp] OR [rip+disp]
# Strategy: scan all funcs, for each instruction check if the target RVA appears as a disp constant.
targets = [int(a,16) for a in sys.argv[1:]]
hits = {t:[] for t in targets}
for (b,e) in fns:
    if e-b>20000: continue
    try:
        for ins in refkit.disasm(pe,b,e):
            ops = ins.op_str
            for t in targets:
                # match hex disp equal to target (as +0xRVA in [.. + 0xRVA])
                h = f"0x{t:x}"
                if h in ops:
                    hits[t].append((ins.address-IB, ins.mnemonic, ops))
    except Exception:
        pass
for t in targets:
    print(f"\n== refs to 0x{t:x} : {len(hits[t])} ==")
    for a,m,o in hits[t][:40]:
        o2=owner(a)
        os=f"[FUNC 0x{o2[0]:x}]" if o2 else ""
        print(f"  0x{a:x} {os}: {m} {o}")
