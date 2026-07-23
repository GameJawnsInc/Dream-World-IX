import refkit,re,struct
pe=refkit.load()
d=refkit.read_rva(pe,0x4f860,0x4200)
print("0x4f860 nonzero bytes:",sum(1 for x in d if x),"of",len(d))
def dis(a,b):
    for i in refkit.disasm(pe,a,b):
        t=""
        m=re.search(r"rip \+ (0x[0-9a-f]+)|rip - (0x[0-9a-f]+)",i.op_str)
        if m:
            dd=int(m.group(1),16) if m.group(1) else -int(m.group(2),16)
            t="   ; -> rva %06x"%((i.address+i.size+dd)-0x180000000)
        print(hex(i.address),i.mnemonic,i.op_str,t)
print("== id-3 handler 0x3e13a"); dis(0x3e13a,0x3e1c0)
