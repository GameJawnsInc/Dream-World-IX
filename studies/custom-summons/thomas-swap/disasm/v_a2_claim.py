import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)
TARGET = 0x220830

print("=== SECTIONS: is 0x220830 zero-on-disk? ===")
for s in pe.sections:
    name = s.Name.rstrip(b"\x00").decode("latin-1")
    va = s.VirtualAddress
    vsz = s.Misc_VirtualSize
    raw = s.SizeOfRawData
    praw = s.PointerToRawData
    end_v = va + max(vsz, raw)
    hit = va <= TARGET < end_v
    print(f"  {name:8s} VA={hex(va):>10s} VSize={hex(vsz):>9s} RawSize={hex(raw):>9s} "
          f"PtrRaw={hex(praw):>9s} {'<== 0x220830 HERE' if hit else ''}")

sec = refkit._section_for_rva(pe, TARGET)
if sec:
    name = sec.Name.rstrip(b'\x00').decode('latin-1')
    off_in_sec = TARGET - sec.VirtualAddress
    has_raw = off_in_sec < sec.SizeOfRawData
    print(f"\n  0x220830 in section {name!r}: offset_in_section={hex(off_in_sec)} "
          f"SizeOfRawData={hex(sec.SizeOfRawData)} -> {'HAS on-disk bytes' if has_raw else 'BEYOND raw = ZERO on disk (bss)'}")

print("\n=== Try to read on-disk bytes at 0x220830 (and a span) ===")
for probe in (TARGET, TARGET-0x20, TARGET+0x38, TARGET+0x40):
    try:
        b = pe.get_data(probe, 0x10)
        print(f"  {hex(probe)}: {b.hex()}  ({'ALL ZERO' if b == b'\\x00'*len(b) else 'NONZERO!'})")
    except Exception as e:
        print(f"  {hex(probe)}: get_data raised {e!r} (past raw data => implicitly zero)")

print("\n=== WRITE #1: alloc store FUNC@0x30c20, expect mov [rip+..],rbx @0x30cc9 -> 0x220830 ===")
b, e = 0x30c20, None
f = refkit.func_of(fns, 0x30c20)
print("  func_of(0x30c20) =", (hex(f[0]), hex(f[1])) if f else None)
if f:
    for ins in refkit.disasm(pe, f[0], f[1]):
        t = refkit._rip_target(ins, base)
        if t == TARGET or (ins.address - base) in (0x30cc9,):
            print(f"  @{hex(ins.address-base)}: {ins.mnemonic} {ins.op_str}   rip_target={hex(t) if t else None}")

print("\n=== WRITE #2: clear FUNC@0xeea4, expect mov [rip+..],r12 @0xf90d -> 0x220830 ===")
f = refkit.func_of(fns, 0xeea4)
print("  func_of(0xeea4) =", (hex(f[0]), hex(f[1])) if f else None)
if f:
    for ins in refkit.disasm(pe, f[0], f[1]):
        t = refkit._rip_target(ins, base)
        if t == TARGET or (ins.address - base) in (0xf90d,):
            print(f"  @{hex(ins.address-base)}: {ins.mnemonic} {ins.op_str}   rip_target={hex(t) if t else None}")

print("\n=== ALL xrefs to 0x220830 (who touches the record base) ===")
for frm, mn, op in refkit.xrefs_to(pe, TARGET, fns):
    ff = refkit.func_of(fns, frm)
    print(f"  @{hex(frm)}: {mn} {op}   in FUNC[{hex(ff[0]) if ff else '?'}]")
