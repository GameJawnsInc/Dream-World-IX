"""A1: full Hi_* roster + call graph mapping. Prints a table for the blackboard."""
import sys, json
sys.path.insert(0, r'C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/studies/custom-summons/thomas-swap/disasm')
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)

# 1) all Hi_ strings
hi_strings = refkit.find_strings(pe, "Hi_")
print(f"# {len(hi_strings)} Hi_ strings")
lo = min(r for r, _ in hi_strings)
hi = max(r for r, _ in hi_strings) + 64

# 2) one image walk: xref index over the whole Hi_ string region
idx = refkit.xref_index(pe, lo, hi, fns)

# 3) for each string, find referencing functions (the "stub" or callers)
def func_of(rva):
    return refkit.func_of(fns, rva)

rows = []
for srva, txt in hi_strings:
    name = txt.replace("()", "").replace(" ", "")
    refs = idx.get(srva, [])
    ref_funcs = []
    for from_rva, mnem, op in refs:
        f = func_of(from_rva)
        ref_funcs.append((from_rva, f))
    rows.append((name, srva, txt, refs, ref_funcs))

for name, srva, txt, refs, ref_funcs in rows:
    print(f"\n=== {name}  str@{hex(srva)}  ({len(refs)} xref) ===")
    for (from_rva, mnem, op), (fr, f) in zip(refs, ref_funcs):
        frange = f"[{hex(f[0])}..{hex(f[1])}] sz={f[1]-f[0]}" if f else "NO-FUNC"
        print(f"   xref@{hex(from_rva)} {mnem} {op}  in {frange}")
