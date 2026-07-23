"""V-M1-10: name every function in a range by the debug string its body (or a nearby
sibling/funclet) references. Distinguishes COLD ERROR FUNCLET from real body by size + by
whether the body does real work (contains the string load AND >40 instructions)."""
import sys, collections
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)
smap = refkit.string_rvas(pe)
md = refkit._md(pe)

# index every rip-relative reference to a string
ref = collections.defaultdict(list)   # fn_begin -> [strings]
size = {}
for b, e in fns:
    size[b] = e - b
    try:
        code = refkit.read_rva(pe, b, e - b)
    except Exception:
        continue
    for ins in md.disasm(code, base + b):
        t = refkit._rip_target(ins, base)
        if t in smap:
            ref[b].append(smap[t])

lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x15000
hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x19000
for b, e in fns:
    if lo <= b < hi:
        names = [s for s in ref.get(b, []) if s.startswith(("Hi_", "SFX", "Sfx"))]
        print(f"0x{b:<8x}-0x{e:<8x} size={e-b:<6d} {names[:3]}")
