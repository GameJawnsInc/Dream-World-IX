import sys, refkit
pe = refkit.load(sys.argv[3] if len(sys.argv)>3 else 'x64')
b = int(sys.argv[1],16); e = int(sys.argv[2],16)
for ins in refkit.disasm(pe, b, e):
    print(f"{ins.address-refkit.image_base(pe):#x}: {ins.mnemonic}\t{ins.op_str}")
