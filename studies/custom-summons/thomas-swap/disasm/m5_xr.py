import sys, refkit
pe = refkit.load('x64'); fns=refkit.functions(pe)
idx = refkit.xref_index(pe, int(sys.argv[1],16), int(sys.argv[2],16), fns)
for t in sorted(idx):
    print(f"{t:#x}:")
    for fr,m,o in idx[t]:
        print(f"   {fr:#x}  {m} {o}")
