import refkit, collections
pe=refkit.load(); base=refkit.image_base(pe); fns=refkit.functions(pe)
out=collections.defaultdict(list)
for ins in refkit.iter_instructions(pe,fns):
    if ins.mnemonic in('call','jmp') and ins.op_str.startswith('0x'):
        try: t=int(ins.op_str,16)-base
        except: continue
        out[t].append((ins.address-base, ins.mnemonic))
for t in (0x13d40,0x13540,0x12df0,0x3bbd0):
    print(hex(t), [(hex(a),m) for a,m in out.get(t,[])])
