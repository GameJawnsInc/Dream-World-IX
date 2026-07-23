"""V-C2 part 4: is fn 0xd390 (x64) / 0xbfc0 (x86) actually REACHED, or dead code?

Raw byte scan of .text for E8/E9 rel32 landing on the target, plus a scan of
.rdata/.data for the absolute VA (vtable / function-pointer table reference).
"""
import struct, sys
import refkit


def scan(arch, target_rva):
    pe = refkit.load(arch)
    ib = pe.OPTIONAL_HEADER.ImageBase
    print(f"\n=== {arch}  target rva {target_rva:#x}  VA {ib+target_rva:#x} ===")
    direct = []
    for s in pe.sections:
        nm = s.Name.rstrip(b"\x00").decode(errors="replace")
        d = s.get_data()
        rva0 = s.VirtualAddress
        if nm == ".text":
            for i in range(len(d) - 5):
                if d[i] in (0xE8, 0xE9):
                    rel = struct.unpack_from("<i", d, i + 1)[0]
                    if rva0 + i + 5 + rel == target_rva:
                        direct.append((rva0 + i, "call" if d[i] == 0xE8 else "jmp"))
        # absolute VA references anywhere (ptr tables)
        va = ib + target_rva
        pat = struct.pack("<Q", va) if arch == "x64" else struct.pack("<I", va)
        off = d.find(pat)
        while off != -1:
            print(f"  abs-VA ref in {nm} @rva {rva0+off:#x}")
            off = d.find(pat, off + 1)
    print("  direct E8/E9 sites:", [(hex(a), k) for a, k in direct] or "NONE")
    return direct


scan("x64", 0xD390)
scan("x86", 0xBFC0)

# x64: also check rip-relative LEA loading the address (indirect call setup)
pe = refkit.load("x64")
for s in pe.sections:
    if s.Name.rstrip(b"\x00") != b".text":
        continue
    d = s.get_data(); rva0 = s.VirtualAddress
    hits = []
    for ins in []:
        pass
    # brute: any rip-relative disp landing on 0xd390 with 7-byte lea (48 8d ?? disp32)
    import re
    for m in re.finditer(rb"\x48\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]", d):
        i = m.start()
        if i + 7 > len(d):
            continue
        disp = struct.unpack_from("<i", d, i + 3)[0]
        if rva0 + i + 7 + disp == 0xD390:
            hits.append(rva0 + i)
    print("\nx64 rip-relative LEA of 0xd390:", [hex(h) for h in hits] or "NONE")
