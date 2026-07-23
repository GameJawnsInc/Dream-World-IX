import refkit,re
pe=refkit.load()
def d(a,b):
    for i in refkit.disasm(pe,a,b):
        t=""
        m=re.search(r"rip \+ (0x[0-9a-f]+)|rip - (0x[0-9a-f]+)",i.op_str)
        if m:
            dd=int(m.group(1),16) if m.group(1) else -int(m.group(2),16)
            t="   ; -> rva %06x"%((i.address+i.size+dd)-0x180000000)
        print(hex(i.address),i.mnemonic,i.op_str,t)
print("== 0x3de60..0x3dea0"); d(0x3de60,0x3dea0)
print("== 0x3e5c8..0x3e610"); d(0x3e5c8,0x3e610)
print("== 0x31b80..0x31bc0"); d(0x31b80,0x31bc0)
