"""V-M1-02 step B: image-wide census of EVERY store into [reg+0x10] (qword) --
the motion-clip field of a ModelData block. Refutation hunt: does ANY site write a
non-zero motion pointer that could reach an EFFARR slot's DATA block?
"""
import re
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)

# qword stores to [reg + 0x10]
pat = re.compile(r"^qword ptr \[(r[a-z0-9]+) \+ 0x10\], (.+)$")
hits = []
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic != "mov":
        continue
    m = pat.match(ins.op_str)
    if m:
        hits.append((ins.address - base, m.group(1), m.group(2)))

print("qword [reg+0x10] stores:", len(hits))
for rva, reg, src in hits:
    f = refkit.func_of(fns, rva)
    print("  %06x  in fn %06x  [%s+0x10] <- %s" % (rva, f[0] if f else 0, reg, src))

# also: dword/any store to +0x10 that is a pointer-ish write is impossible on x64 (ptr = qword),
# but catch lea-based writes via xmm too
pat2 = re.compile(r"^xmmword ptr \[(r[a-z0-9]+) \+ 0x10\], (.+)$")
print("\nxmmword [reg+0x10] stores (could clobber +0x10..+0x1f):")
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic in ("movups", "movdqu", "movaps", "movdqa"):
        m = pat2.match(ins.op_str)
        if m:
            f = refkit.func_of(fns, ins.address - base)
            print("  %06x in fn %06x  %s" % (ins.address - base, f[0] if f else 0, ins.op_str))
