"""C10 verification step F: x86 cross-check (same source, different codegen).

Anchor on the psxBase immediate 0x801E7700 (the id-3 chunk-record builder) and on
the 0x5000 psx-slot stride, then disassemble around each hit. x86 has no .pdata, so
disassemble from a few bytes before each anchor and accept only the aligned stream.
"""
import struct
import sys

import refkit
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

pe = refkit.load("x86")
base = refkit.image_base(pe)
data = pe.__data__

needle = struct.pack("<I", 0x801E7700)
hits = []
off = 0
while True:
    i = data.find(needle, off)
    if i < 0:
        break
    off = i + 1
    for s in pe.sections:
        if s.PointerToRawData <= i < s.PointerToRawData + s.SizeOfRawData:
            hits.append((s.VirtualAddress + (i - s.PointerToRawData), s.Name.rstrip(b"\0").decode()))
            break
print("0x801E7700 occurrences:", [(hex(r), sec) for r, sec in hits])

md = Cs(CS_ARCH_X86, CS_MODE_32)
for rva, sec in hits:
    if not sec.startswith(".text"):
        continue
    lo = rva - 0x60
    print("=" * 70)
    print(f"context around {hex(rva)} in {sec}")
    code = refkit.read_rva(pe, lo, 0x140)
    for ins in md.disasm(code, base + lo):
        print(f"  {hex(ins.address - base)}: {ins.mnemonic:10s} {ins.op_str}")
