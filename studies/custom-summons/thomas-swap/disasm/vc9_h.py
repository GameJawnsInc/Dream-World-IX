import refkit,re
pe=refkit.load(); fns=refkit.functions(pe)
def dump(rva,lim=None):
    f=refkit.func_of(fns,rva); 
    if f is None: print("no pdata for",hex(rva)); return
    print("== fn",hex(f[0]),hex(f[1]))
    n=0
    for i in refkit.disasm(pe,f[0],f[1]):
        t=""
        m=re.search(r"rip \+ (0x[0-9a-f]+)|rip - (0x[0-9a-f]+)",i.op_str)
        if m:
            d=int(m.group(1),16) if m.group(1) else -int(m.group(2),16)
            t="   ; -> rva %06x"%((i.address+i.size+d)-0x180000000)
        print(hex(i.address), i.mnemonic, i.op_str, t); n+=1
        if lim and n>lim: break
dump(0x490d0,60)
print()
dump(0x31470,40)
