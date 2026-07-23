import refkit, collections
pe = refkit.load(); base=refkit.image_base(pe)
fns = refkit.functions(pe)
def owner(rva):
    for f in fns:
        b,e = (f[0],f[1]) if isinstance(f,(tuple,list)) else (f['begin'],f['end'])
        if b<=rva<e: return (b,e)
for r in (0x139a5,0x13aa7,0x1e80,0x2581):
    print(hex(r), [hex(x) for x in owner(r)])
callers = collections.defaultdict(list)
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic=='call' and ins.op_str.startswith('0x'):
        try: t=int(ins.op_str,16)-base
        except: continue
        callers[t].append(ins.address-base)
for t in (owner(0x139a5)[0], 0x13030, 0x12df0):
    print("callers of", hex(t), [hex(x) for x in callers.get(t,[])])
