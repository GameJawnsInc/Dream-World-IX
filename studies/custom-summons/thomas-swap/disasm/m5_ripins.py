import sys, refkit
pe = refkit.load('x64'); base = refkit.image_base(pe)
b=int(sys.argv[1],16); e=int(sys.argv[2],16); lo=int(sys.argv[3],16); hi=int(sys.argv[4],16)
for ins in refkit.disasm(pe,b,e):
    t = refkit._rip_target(ins, base)
    if t is not None and lo<=t<hi:
        print(f"{ins.address-base:#x}: {ins.mnemonic}\t{ins.op_str}   -> {t:#x}")
