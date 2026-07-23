import sys, refkit
pe = refkit.load()
fns = refkit.functions(pe)
def fnof(rva):
    for b,e in fns:
        if b<=rva<e: return (b,e)
    return None
lo=int(sys.argv[1],16); hi=int(sys.argv[2],16)
f=fnof(lo)
print("fn:", [hex(x) for x in f] if f else None)
for ins in refkit.disasm(pe, f[0], f[1]):
    if lo <= ins.address - 0x180000000 <= hi:
        print(hex(ins.address-0x180000000), ins.mnemonic, ins.op_str)
