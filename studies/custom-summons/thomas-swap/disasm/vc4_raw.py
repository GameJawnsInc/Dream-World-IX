import sys, refkit
pe=refkit.load(); IB=pe.OPTIONAL_HEADER.ImageBase
lo=int(sys.argv[1],16); hi=int(sys.argv[2],16)
data=pe.get_data(lo, hi-lo)
print(" ".join(f"{b:02x}" for b in data))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
md=Cs(CS_ARCH_X86, CS_MODE_64)
for ins in md.disasm(data, IB+lo):
    print(hex(ins.address-IB), ins.mnemonic, ins.op_str)
