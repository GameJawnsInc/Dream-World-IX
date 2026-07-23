import refkit, collections
pe=refkit.load(); base=refkit.image_base(pe)
fns=refkit.functions(pe)
tgt={0x145a0:'resolve_position',0x148f0:'lookup_anchor',0x14450:'shake',0x14c30:'lookat_matrix',0x14350:'?0x14350',0x13030:'parse_camblock'}
out=collections.defaultdict(list)
for ins in refkit.iter_instructions(pe,fns):
    if ins.mnemonic=='call' and ins.op_str.startswith('0x'):
        try: t=int(ins.op_str,16)-base
        except: continue
        if t in tgt: out[t].append(ins.address-base)
for t,n in tgt.items():
    print(n, hex(t), "callers:", [hex(x) for x in out.get(t,[])])
