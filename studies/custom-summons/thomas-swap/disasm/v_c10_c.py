"""C10 verification step C: grep the whole per-function disassembly for a literal
substring in the operand text (e.g. an offset like '0xda8'). Prints fn + instruction."""
import sys
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)
needles = sys.argv[1:]
cur = None
for b, e in fns:
    try:
        code = refkit.read_rva(pe, b, e - b)
    except Exception:
        continue
    md = refkit._md(pe)
    for ins in md.disasm(code, base + b):
        txt = f"{ins.mnemonic} {ins.op_str}"
        if any(n in txt for n in needles):
            print(f"fn {hex(b)}  {hex(ins.address-base)}: {txt}")
