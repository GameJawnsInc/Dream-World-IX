import sys, struct, refkit
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
pe = refkit.load('x86'); BASE = refkit.image_base(pe)
md = Cs(CS_ARCH_X86, CS_MODE_32)
b=int(sys.argv[1],16); n=int(sys.argv[2],0)
code = pe.get_data(b, n)
for ins in md.disasm(code, BASE+b):
    print(f"{ins.address-BASE:#x}: {ins.mnemonic}\t{ins.op_str}")
