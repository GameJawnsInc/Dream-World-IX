"""A1: export -> Hi_ reachability via forward call graph BFS."""
import sys, re
sys.path.insert(0, r'C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/studies/custom-summons/thomas-swap/disasm')
import refkit

pe = refkit.load(); fns = refkit.functions(pe); base = refkit.image_base(pe)
absimm = re.compile(r'^0x([0-9a-f]+)$')

def fb(rva):
    f = refkit.func_of(fns, rva); return f[0] if f else None

# forward direct-call graph: func_begin -> set(callee begins)
callg = {}
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic == 'call' or ins.mnemonic.startswith('j'):
        mm = absimm.match(ins.op_str.strip())
        if mm:
            src = fb(ins.address - base); tgt = mm.group(1)
            trva = int(tgt,16) - base
            tb = fb(trva)
            if src is not None and tb is not None and tb != src:
                callg.setdefault(src, set()).add(tb)

# Hi_ function entry begins (map begin -> name). Use the classification: the function whose
# .pdata range references the Hi_ string. Entry = lowest contiguous range that flows to it.
hi_str = {rva: t.replace('()','').replace(' ','') for rva,t in refkit.find_strings(pe,'Hi_')}
name_of_begin = {}
for ins in refkit.iter_instructions(pe, fns):
    t = refkit._rip_target(ins, base)
    if t in hi_str:
        b = fb(ins.address - base)
        if b is not None:
            name_of_begin.setdefault(b, set()).add(hi_str[t])

exp = refkit.exports(pe)
# resolve export thunk: an export body is often 'jmp real'
def resolve(rva):
    f = refkit.func_of(fns, rva)
    if not f: return rva
    ins_list = list(refkit.disasm(pe, f[0], f[1]))
    if len(ins_list)==1 and ins_list[0].mnemonic=='jmp':
        mm = absimm.match(ins_list[0].op_str.strip())
        if mm: return int(mm.group(1),16)-base
    return f[0]

print("### exports:")
for n,r in sorted(exp.items(), key=lambda x:x[1]):
    print(f"   {n:22s} rva={hex(r)} -> body {hex(resolve(r))}")

# BFS from each export, collect reachable Hi_ begins
def bfs(start):
    seen=set(); stack=[start]; hi=set()
    while stack:
        x=stack.pop()
        if x in seen: continue
        seen.add(x)
        if x in name_of_begin: hi |= name_of_begin[x]
        for c in callg.get(x,()):
            if c not in seen: stack.append(c)
    return hi, seen

print("\n### Hi_ reachable from each export (forward call graph):")
for n,r in sorted(exp.items(), key=lambda x:x[1]):
    body = resolve(r)
    hi, seen = bfs(body)
    if hi:
        print(f"\n-- {n} ({len(seen)} funcs reached) touches:")
        for h in sorted(hi): print(f"     {h}")
