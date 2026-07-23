import sys, re, refkit
pe = refkit.load(); fns = refkit.functions(pe); IB=0x180000000
def fnof(r):
    for b,e in fns:
        if b<=r<e: return (b,e)
lo=int(sys.argv[1],16); hi=int(sys.argv[2],16)
f=fnof(lo); ins_list=list(refkit.disasm(pe,f[0],f[1]))
for i,ins in enumerate(ins_list):
    rva=ins.address-IB
    if not (lo<=rva<=hi): continue
    m=re.search(r'rip ([+-]) 0x([0-9a-f]+)', ins.op_str)
    t=""
    if m:
        nxt=ins_list[i+1].address if i+1<len(ins_list) else ins.address+ins.size
        d=int(m.group(2),16)*(1 if m.group(1)=='+' else -1)
        t="   -> RVA "+hex((nxt+d)-IB)
    print(hex(rva), ins.mnemonic, ins.op_str, t)
