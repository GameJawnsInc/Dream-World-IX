"""V-M1-10: which functions touch EFFARR (0x220230) vs SUMARR (0x220830)?"""
import collections, refkit

pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)
md = refkit._md(pe)
TARGETS = {0x220230: "EFFARR", 0x220830: "SUMARR"}
hits = collections.defaultdict(set)
detail = collections.defaultdict(list)
for b, e in fns:
    try:
        code = refkit.read_rva(pe, b, e - b)
    except Exception:
        continue
    for ins in md.disasm(code, base + b):
        t = refkit._rip_target(ins, base)
        if t in TARGETS:
            hits[b].add(TARGETS[t])
            detail[b].append((ins.address - base, TARGETS[t], ins.mnemonic, ins.op_str))
for b in sorted(hits):
    print(f"fn 0x{b:<8x} {sorted(hits[b])}")
    for d in detail[b][:4]:
        print(f"    @0x{d[0]:x} {d[1]}  {d[2]} {d[3]}")
