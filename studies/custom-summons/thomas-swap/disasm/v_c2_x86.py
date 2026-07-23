"""V-C2 part 3: x86 cross-check -- find the 32-bit build's resource-table walker.

The 32-bit PE has no .pdata, so we locate the walker by its two signature
constants: `mov <r32>, 0x800` (cursor seed) near a `shl <r32>, 0xb` (sizeSectors<<11).
Then disassemble a window around each hit and look for the id==2 / info!=0 arm.
"""
import refkit, re

pe = refkit.load("x86")
sec = None
for s in pe.sections:
    if s.Name.rstrip(b"\x00") == b".text":
        sec = s
data = sec.get_data()
base_rva = sec.VirtualAddress
print("x86 .text rva", hex(base_rva), "size", hex(len(data)))

# shl eax,0xb == c1 e0 0b ; shl exx,0xb == c1 e?/f? 0b  (opcode C1 /4 ib)
hits = []
for m in re.finditer(rb"\xc1[\xe0-\xe7]\x0b", data):
    hits.append(base_rva + m.start())
print("shl r32,0xb sites:", len(hits), [hex(h) for h in hits[:40]])

# Now: which hits sit near an immediate 0x800 load? scan +-0x80 bytes for b8..bf 00 08 00 00
cands = []
for h in hits:
    off = h - base_rva
    win = data[max(0, off - 0x100): off + 0x100]
    if re.search(rb"[\xb8-\xbf]\x00\x08\x00\x00", win):
        cands.append(h)
print("\ncandidates near a 0x800 immediate:", [hex(c) for c in cands])

for c in cands:
    lo = c - 0x90
    hi = c + 0x140
    print("\n===== window around", hex(c), "=====")
    try:
        for ins in refkit.disasm(pe, lo, hi):
            print(ins)
    except Exception as e:
        print("disasm fail", e)
