"""C10 verification step B: disassemble an arbitrary RVA range (for functions whose
.pdata entry is chained/split -- the known leaf blindspot)."""
import sys
import refkit

pe = refkit.load(sys.argv[3] if len(sys.argv) > 3 else "x64")
base = refkit.image_base(pe)
lo = int(sys.argv[1], 16)
hi = int(sys.argv[2], 16)
for ins in refkit.disasm(pe, lo, hi):
    print(f"  {hex(ins.address - base)}: {ins.mnemonic:10s} {ins.op_str}")
