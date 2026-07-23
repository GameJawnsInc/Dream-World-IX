import sys, refkit
pe = refkit.load('x64'); fns = refkit.functions(pe)
lo=int(sys.argv[1],16); hi=int(sys.argv[2],16)
for b,e in fns:
    if lo<=b<hi: print(hex(b), hex(e), e-b)
