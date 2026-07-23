import refkit,re
pe=refkit.load(); fns=refkit.functions(pe)
for rva in (0x4aff0,0x4b070,0x4ab80,0x4ad00,0x31f58):
    s=refkit._section_for_rva(pe,rva)
    print(hex(rva), s.Name.decode().rstrip('\x00'))
print(repr(refkit.read_rva(pe,0x4b070,64)))
print("--- fn 0x49170 (the >=0x80 handler) ---")
f=refkit.func_of(fns,0x49170); print("pdata range:",f and (hex(f[0]),hex(f[1])))
for i in refkit.disasm(pe,0x49170,0x491d0):
    t=""
    m=re.search(r"rip \+ (0x[0-9a-f]+)|rip - (0x[0-9a-f]+)",i.op_str)
    if m:
        d=int(m.group(1),16) if m.group(1) else -int(m.group(2),16)
        t="   ; -> rva %06x"%((i.address+i.size+d)-0x180000000)
    print(hex(i.address), i.mnemonic, i.op_str,t)
