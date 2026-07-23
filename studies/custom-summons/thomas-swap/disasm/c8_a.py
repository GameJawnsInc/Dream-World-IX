import refkit
pe=refkit.load()
fns=refkit.functions(pe)
for target in (0xd1a0,0xe210,0xd5d0,0xd820,0xd390,0xed18):
    f=refkit.func_of(fns,target)
    print("target %x -> fn %s"%(target, f and (hex(f[0]),hex(f[1]))))
