import sys, re, refkit
pe = refkit.load()
fns = refkit.functions(pe)
IB=0x180000000
def fnof(rva):
    for b,e in fns:
        if b<=rva<e: return (b,e)
    return None
targets = set(int(a,16) for a in sys.argv[2:])
f = fnof(int(sys.argv[1],16))
ins_list = list(refkit.disasm(pe, f[0], f[1]))
for i,ins in enumerate(ins_list):
    m = re.search(r'rip ([+-]) 0x([0-9a-f]+)', ins.op_str)
    if not m: continue
    nxt = ins_list[i+1].address if i+1 < len(ins_list) else ins.address+ins.size
    disp = int(m.group(2),16) * (1 if m.group(1)=='+' else -1)
    tgt = (nxt + disp) - IB
    if not targets or tgt in targets:
        print(hex(ins.address-IB), ins.mnemonic, ins.op_str, " -> RVA", hex(tgt))
