import refkit, collections
pe = refkit.load(); base=refkit.image_base(pe)
fns = refkit.functions(pe)
callers = collections.defaultdict(list)
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic=='call' and ins.op_str.startswith('0x'):
        try: t=int(ins.op_str,16)-base
        except: continue
        callers[t].append(ins.address-base)
print("callers of 0x47330:", [hex(x) for x in callers.get(0x47330,[])])
print("callers of 0x15a20:", [hex(x) for x in callers.get(0x15a20,[])])
print("=== context 0x3e350..0x3e3e0")
for i in refkit.disasm(pe, 0x3e350, 0x3e3e0): print(hex(i.address-base), i.mnemonic, i.op_str)
