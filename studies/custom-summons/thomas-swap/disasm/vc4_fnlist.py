import sys, refkit
pe=refkit.load(); fns=refkit.functions(pe)
lo=int(sys.argv[1],16); hi=int(sys.argv[2],16)
for b,e in fns:
    if b<hi and e>lo: print(hex(b),hex(e))
