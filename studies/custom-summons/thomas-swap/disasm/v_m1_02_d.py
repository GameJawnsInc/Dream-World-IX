"""V-M1-02 step D: close the .pdata blind spot.

refkit.iter_instructions walks ONLY .pdata ranges, so no-unwind LEAF functions are invisible
(proven: Hi_InitEffModel@0x15940 has no .pdata entry). Any "nothing writes X" claim therefore
needs a sweep of the .text bytes NOT covered by .pdata. Strategy: for every uncovered gap,
disassemble from EVERY 16-byte-aligned anchor inside it (MSVC aligns leaf bodies) and union the
decoded instructions -- a real instruction is decoded from at least one correctly-phased anchor.
Report every `mov qword ptr [reg+0x10], <src>` found in the gaps.
"""
import re
import refkit
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)
md = Cs(CS_ARCH_X86, CS_MODE_64)

text = [s for s in pe.sections if s.Name.rstrip(b"\x00") == b".text"][0]
lo = text.VirtualAddress
hi = lo + text.Misc_VirtualSize
print(".text  %06x..%06x" % (lo, hi))

cov = sorted((b, e) for b, e in fns if b < hi and e > lo)
gaps = []
cur = lo
for b, e in cov:
    if b > cur:
        gaps.append((cur, b))
    cur = max(cur, e)
if cur < hi:
    gaps.append((cur, hi))
print("gaps not covered by .pdata: %d, total %d bytes" % (gaps and len(gaps) or 0,
                                                          sum(e - b for b, e in gaps)))

pat = re.compile(r"^qword ptr \[(r[a-z0-9]+) \+ 0x10\], (.+)$")
found = {}
for gb, ge in gaps:
    size = ge - gb
    if size <= 0:
        continue
    data = refkit.read_rva(pe, gb, size)
    for off in range(0, size, 16):
        for ins in md.disasm(data[off:], base + gb + off):
            if ins.mnemonic == "mov":
                m = pat.match(ins.op_str)
                if m:
                    found[ins.address - base] = (m.group(1), m.group(2), gb, ge)

print("\n[reg+0x10] qword stores inside .pdata-INVISIBLE gaps:", len(found))
for rva in sorted(found):
    reg, src, gb, ge = found[rva]
    print("  %06x  [%s+0x10] <- %-8s   (gap %06x..%06x)" % (rva, reg, src, gb, ge))
