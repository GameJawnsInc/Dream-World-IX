import refkit
pe=refkit.load(); fns=refkit.functions(pe)
f=refkit.func_of(fns,0x31d31); print("fn",hex(f[0]),hex(f[1]))
for i in refkit.disasm(pe,f[0],f[1]):
    t=""
    if "rip" in i.op_str:
        import re
        m=re.search(r"rip \+ (0x[0-9a-f]+)|rip - (0x[0-9a-f]+)",i.op_str)
        if m:
            d=int(m.group(1),16) if m.group(1) else -int(m.group(2),16)
            t="   ; -> rva %06x"%((i.address+i.size+d)-0x180000000)
    print(hex(i.address), i.mnemonic, i.op_str, t)
