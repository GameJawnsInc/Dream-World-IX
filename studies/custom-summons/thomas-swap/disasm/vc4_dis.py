import sys, refkit
pe = refkit.load()
fns = refkit.functions(pe)
def fnof(rva):
    for b,e in fns:
        if b<=rva<e: return (b,e)
    return None
for target in [int(a,16) for a in sys.argv[1:]]:
    f = fnof(target)
    print("=== fn covering", hex(target), "->", [hex(x) for x in f] if f else None)
    if not f: continue
    for ins in refkit.disasm(pe, f[0], f[1]):
        print(hex(ins.address), ins.mnemonic, ins.op_str)
