import sys, refkit, re
pe = refkit.load('x64'); base = refkit.image_base(pe)
b=int(sys.argv[1],16); e=int(sys.argv[2],16)
from collections import Counter
c=Counter()
for ins in refkit.disasm(pe,b,e):
    t = refkit._rip_target(ins, base)
    if t is not None:
        c[t]+=1
for t,n in sorted(c.items()):
    print(f"{t:#x}  x{n}")
