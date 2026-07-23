import sys, re, refkit
pe = refkit.load()
fns = refkit.functions(pe)
IB=0x180000000
targets = set(int(a,16) for a in sys.argv[1:])
hexpat = re.compile(r'0x([0-9a-f]+)')
for b,e in fns:
    ins_list = list(refkit.disasm(pe, b, e))
    for i,ins in enumerate(ins_list):
        hits=set()
        m = re.search(r'rip ([+-]) 0x([0-9a-f]+)', ins.op_str)
        if m:
            nxt = ins_list[i+1].address if i+1<len(ins_list) else ins.address+ins.size
            disp = int(m.group(2),16)*(1 if m.group(1)=='+' else -1)
            hits.add((nxt+disp)-IB)
        for h in hexpat.findall(ins.op_str):
            v=int(h,16)
            if v in targets: hits.add(v)
        if hits & targets:
            print("fn",hex(b),":",hex(ins.address-IB), ins.mnemonic, ins.op_str)
