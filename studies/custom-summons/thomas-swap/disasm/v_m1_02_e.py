"""V-M1-02 step E: widen the DATA+0x10 writer census.

Step B only matched the literal `[reg + 0x10]` form. A motion pointer could also land in an eff
DATA block via (a) an INDEXED store `[reg + reg*n + 0x10]`, (b) a block copy (`rep movs`) of a whole
0xC8-byte ModelData, or (c) memcpy with size 0xC8. Sweep for all three, over .pdata functions AND
the .pdata-invisible gaps.
"""
import re
import refkit
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)
md = Cs(CS_ARCH_X86, CS_MODE_64)

text = [s for s in pe.sections if s.Name.rstrip(b"\x00") == b".text"][0]
lo, hi = text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize
cov = sorted((b, e) for b, e in fns if b < hi and e > lo)
gaps, cur = [], lo
for b, e in cov:
    if b > cur:
        gaps.append((cur, b))
    cur = max(cur, e)
if cur < hi:
    gaps.append((cur, hi))


def all_ins():
    for i in refkit.iter_instructions(pe, fns):
        yield i, "pdata"
    for gb, ge in gaps:
        data = refkit.read_rva(pe, gb, ge - gb)
        seen = set()
        for off in range(0, ge - gb, 16):
            for i in md.disasm(data[off:], base + gb + off):
                if i.address in seen:
                    continue
                seen.add(i.address)
                yield i, "gap"


idx_store = re.compile(r"^qword ptr \[r[a-z0-9]+ \+ r[a-z0-9]+(\*\d)? \+ 0x10\], ")
movs, c8, indexed = [], [], []
for i, src in all_ins():
    rva = i.address - base
    if i.mnemonic.startswith("rep") or "movs" in i.mnemonic and i.mnemonic in ("movsb", "movsq", "movsd", "movsw"):
        if "movs" in i.mnemonic or "movs" in i.op_str:
            movs.append((rva, src, i.mnemonic, i.op_str))
    if idx_store.match(i.op_str):
        indexed.append((rva, src, i.mnemonic, i.op_str))
    if re.search(r"\b0xc8\b", i.op_str) and i.mnemonic in ("mov", "add", "cmp", "lea", "sub"):
        c8.append((rva, src, i.mnemonic, i.op_str))

print("INDEXED qword stores at disp 0x10:", len(indexed))
for r, s, m, o in indexed:
    f = refkit.func_of(fns, r)
    print("   %06x [%s] fn %06x  %s %s" % (r, s, f[0] if f else 0, m, o))

print("\nrep-movs / string-copy sites:", len(movs))
for r, s, m, o in movs:
    f = refkit.func_of(fns, r)
    print("   %06x [%s] fn %06x  %s %s" % (r, s, f[0] if f else 0, m, o))

print("\n0xC8 immediates (ModelData size) :", len(c8))
for r, s, m, o in c8:
    f = refkit.func_of(fns, r)
    print("   %06x [%s] fn %06x  %s %s" % (r, s, f[0] if f else 0, m, o))
