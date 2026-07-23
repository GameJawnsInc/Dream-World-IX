import sys, refkit
pe = refkit.load('x64'); fns = refkit.functions(pe)
for a in sys.argv[1:]:
    r = int(a,16); f = refkit.func_of(fns, r)
    print(a, "->", (hex(f[0]), hex(f[1]), f[1]-f[0]) if f else None)
