import refkit
pe = refkit.load()
IB = 0x180000000
fns = refkit.functions(pe)
mm = pe.get_memory_mapped_image()
def owner(rva):
    for (b,e) in fns:
        if b<=rva<e: return (b,e)
    return None
# 1) find all idiv/div in code range and their owning function
print("== integer divides (perspective divide candidates) ==")
divowners={}
for (b,e) in fns:
    if e-b > 20000: continue
    try:
        for ins in refkit.disasm(pe,b,e):
            if ins.mnemonic in ('idiv','div'):
                divowners.setdefault((b,e),[]).append((ins.address,ins.mnemonic,ins.op_str))
    except Exception:
        pass
for (b,e),lst in sorted(divowners.items()):
    print(f"FUNC[0x{b:x}..0x{e:x}] ({e-b}B): "+", ".join(f"0x{a:x}:{m} {o}" for a,m,o in lst[:6]))
