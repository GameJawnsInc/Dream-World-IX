import refkit, collections
pe = refkit.load(); base = refkit.image_base(pe)
fns = refkit.functions(pe)
callers = collections.defaultdict(list)
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
        try: t = int(ins.op_str,16) - base
        except: continue
        callers[t].append(ins.address-base)
for t in (0x187e0,0x18840,0x186a0,0x7820):
    print(hex(t), [hex(x) for x in callers.get(t,[])])
